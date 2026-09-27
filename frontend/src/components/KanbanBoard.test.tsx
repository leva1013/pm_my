import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData, type BoardData } from "@/lib/kanban";

const cloneBoard = (board: BoardData): BoardData =>
  JSON.parse(JSON.stringify(board)) as BoardData;

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

describe("KanbanBoard", () => {
  let currentBoard: BoardData;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    currentBoard = cloneBoard(initialData);
    fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";

      if (url.endsWith("/api/board") && method === "GET") {
        return new Response(JSON.stringify(currentBoard), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.endsWith("/api/board") && method === "PUT") {
        currentBoard = JSON.parse(String(init?.body ?? "{}")) as BoardData;
        return new Response(JSON.stringify(currentBoard), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.endsWith("/api/auth/logout") && method === "POST") {
        return new Response("", { status: 200 });
      }

      return new Response("not found", { status: 404 });
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders five columns", async () => {
    render(<KanbanBoard />);
    expect(await screen.findAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("shows a pluralized card count per column", async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);
    const column = getFirstColumn();
    const expected = currentBoard.columns[0].cardIds.length;
    const label = `${expected} ${expected === 1 ? "card" : "cards"}`;
    expect(
      within(column).getByText((_, element) => element?.tagName === "SPAN" && element.textContent === label)
    ).toBeInTheDocument();
  });

  it("collapses and reopens the ai sidebar", async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);

    await userEvent.click(screen.getByRole("button", { name: "Collapse AI assistant" }));
    expect(screen.queryByLabelText("AI message")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Open AI assistant" }));
    expect(screen.getByLabelText("AI message")).toBeInTheDocument();
  });

  it("disables ai send until a message is typed", async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);
    const sendButton = screen.getByRole("button", { name: "Send" });
    expect(sendButton).toBeDisabled();
    await userEvent.type(screen.getByLabelText("AI message"), "hi");
    expect(sendButton).toBeEnabled();
  });

  it("cancels the add card form", async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);
    const column = getFirstColumn();
    await userEvent.click(within(column).getByRole("button", { name: /add a card/i }));
    await userEvent.click(within(column).getByRole("button", { name: "Cancel" }));
    expect(within(column).queryByPlaceholderText(/card title/i)).not.toBeInTheDocument();
    expect(within(column).getByRole("button", { name: /add a card/i })).toBeInTheDocument();
  });

  it("renames a column", async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/board",
      expect.objectContaining({ method: "PUT" })
    );
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);
    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("applies board updates returned from ai chat", async () => {
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";

      if (url.endsWith("/api/board") && method === "GET") {
        return new Response(JSON.stringify(currentBoard), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      if (url.endsWith("/api/ai/chat") && method === "POST") {
        const updatedBoard = cloneBoard(currentBoard);
        updatedBoard.columns[0].title = "Ideas";
        currentBoard = updatedBoard;
        return new Response(
          JSON.stringify({
            assistantMessage: "Backlog renamed to Ideas.",
            appliedOperations: [
              {
                type: "rename_column",
                columnId: "col-backlog",
                newTitle: "Ideas",
              },
            ],
            board: updatedBoard,
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }
        );
      }

      if (url.endsWith("/api/board") && method === "PUT") {
        currentBoard = JSON.parse(String(init?.body ?? "{}")) as BoardData;
        return new Response(JSON.stringify(currentBoard), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      return new Response("not found", { status: 404 });
    });

    render(<KanbanBoard />);

    await screen.findAllByTestId(/column-/i);

    await userEvent.type(screen.getByLabelText("AI message"), "Rename backlog to Ideas");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Backlog renamed to Ideas.")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Ideas")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("AI message"), "Rename again{Enter}");
    expect(await screen.findByText("Rename again")).toBeInTheDocument();
    expect(screen.getByLabelText("AI message")).toHaveValue("");
  });
});
