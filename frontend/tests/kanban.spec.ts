import { expect, test } from "@playwright/test";

test("loads the kanban board", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const cardTitle = `Playwright card ${Date.now()}`;
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(cardTitle);
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText(cardTitle)).toBeVisible();

  await page.reload();
  const firstColumnAfterReload = page.locator('[data-testid^="column-"]').first();
  await expect(firstColumnAfterReload.getByText(cardTitle)).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const cardTitle = `Drag card ${Date.now()}`;
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(cardTitle);
  await firstColumn.getByPlaceholder("Details").fill("Drag-and-drop e2e card.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();

  const card = page.locator('[data-testid^="card-"]', { hasText: cardTitle }).first();
  await expect(card).toBeVisible();
  await card.scrollIntoViewIfNeeded();
  const targetColumn = page.getByTestId("column-col-review");
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  const viewport = page.viewportSize();
  if (!cardBox || !columnBox || !viewport) {
    throw new Error("Unable to resolve drag coordinates.");
  }
  // The board accumulates cards across runs, so the page may be scrolled;
  // drop in the middle of the target column's on-screen portion.
  const visibleTop = Math.max(columnBox.y, 0);
  const visibleBottom = Math.min(columnBox.y + columnBox.height, viewport.height);

  await page.mouse.move(
    cardBox.x + cardBox.width / 2,
    cardBox.y + cardBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    columnBox.x + columnBox.width / 2,
    (visibleTop + visibleBottom) / 2,
    { steps: 12 }
  );
  await page.mouse.up();
  await expect(targetColumn.getByText(cardTitle)).toBeVisible();
});

test("requires login and supports logout", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();

  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();

  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("persists board updates through backend api", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();

  const request = page.context().request;
  const boardResponse = await request.get("/api/board");
  expect(boardResponse.ok()).toBeTruthy();

  const board = (await boardResponse.json()) as {
    columns: Array<{ id: string; title: string; cardIds: string[] }>;
    cards: Record<string, { id: string; title: string; details: string }>;
  };

  board.columns[0].title = "API Updated Backlog";
  const updateResponse = await request.put("/api/board", { data: board });
  expect(updateResponse.ok()).toBeTruthy();

  await page.reload();

  const nextBoardResponse = await request.get("/api/board");
  const nextBoard = (await nextBoardResponse.json()) as {
    columns: Array<{ id: string; title: string; cardIds: string[] }>;
  };
  expect(nextBoard.columns[0].title).toBe("API Updated Backlog");
});

test("openrouter smoke endpoint returns result when key is set", async ({ page }) => {
  test.skip(!process.env.OPENROUTER_API_KEY, "OPENROUTER_API_KEY is not set");

  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();

  const response = await page.request.post("/api/ai/smoke");
  expect(response.ok()).toBeTruthy();

  const payload = (await response.json()) as {
    status: string;
    response: string;
    model: string;
  };

  expect(payload.status).toBe("ok");
  expect(payload.model).toBe("openai/gpt-oss-120b");
});

test("shows ai sidebar and handles missing key error", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();

  await page.route("**/api/ai/chat", async (route) => {
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "OPENROUTER_API_KEY is not set." }),
    });
  });

  await expect(page.getByTestId("ai-sidebar")).toBeVisible();
  await page.getByLabel("AI message").fill("Rename Backlog to Ideas");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByTestId("ai-error")).toContainText("OPENROUTER_API_KEY");
});

test("renders non-mutating ai response in sidebar", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();

  const beforeBoardResponse = await page.request.get("/api/board");
  expect(beforeBoardResponse.ok()).toBeTruthy();
  const beforeBoard = (await beforeBoardResponse.json()) as {
    columns: Array<{ id: string; title: string; cardIds: string[] }>;
    cards: Record<string, { id: string; title: string; details: string }>;
  };

  await page.route("**/api/ai/chat", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        assistantMessage: "No updates needed right now.",
        appliedOperations: [],
        board: beforeBoard,
      }),
    });
  });

  await page.getByLabel("AI message").fill("What should I do next?");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("No updates needed right now.")).toBeVisible();
  const backlogTitle = beforeBoard.columns.find((column) => column.id === "col-backlog")?.title;
  expect(backlogTitle).toBeTruthy();
  await expect(page.locator(`input[value="${String(backlogTitle)}"]`).first()).toBeVisible();
});

test("applies mutating ai response to board immediately", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();

  const beforeBoardResponse = await page.request.get("/api/board");
  expect(beforeBoardResponse.ok()).toBeTruthy();
  const beforeBoard = (await beforeBoardResponse.json()) as {
    columns: Array<{ id: string; title: string; cardIds: string[] }>;
    cards: Record<string, { id: string; title: string; details: string }>;
  };

  const updatedBoard = {
    ...beforeBoard,
    columns: beforeBoard.columns.map((column) =>
      column.id === "col-backlog"
        ? { ...column, title: "AI Ideas" }
        : column
    ),
  };

  await page.route("**/api/ai/chat", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        assistantMessage: "Backlog renamed to AI Ideas.",
        appliedOperations: [
          {
            type: "rename_column",
            columnId: "col-backlog",
            newTitle: "AI Ideas",
          },
        ],
        board: updatedBoard,
      }),
    });
  });

  await page.getByLabel("AI message").fill("Rename backlog to AI Ideas");
  await page.getByRole("button", { name: "Send" }).click();

  await expect(page.getByText("Backlog renamed to AI Ideas.")).toBeVisible();
  await expect(page.locator('input[value="AI Ideas"]').first()).toBeVisible();
});

test("deletes a card with the trash icon", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const cardTitle = `Delete card ${Date.now()}`;
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(cardTitle);
  await firstColumn.getByRole("button", { name: /add card/i }).click();

  const card = page.locator('[data-testid^="card-"]', { hasText: cardTitle });
  await card.hover();
  const deleteButton = card.getByRole("button", { name: `Delete ${cardTitle}` });
  await expect(deleteButton).toBeVisible();
  await deleteButton.click();
  await expect(card).toHaveCount(0);

  await page.reload();
  await expect(page.locator('[data-testid^="card-"]', { hasText: cardTitle })).toHaveCount(0);
});

test("collapses and reopens the ai sidebar", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();

  const lastColumn = page.locator('[data-testid^="column-"]').last();
  await expect(lastColumn).toBeVisible();
  const widthBefore = (await lastColumn.boundingBox())?.width ?? 0;

  await page.getByRole("button", { name: "Collapse AI assistant" }).click();
  await expect(page.getByLabel("AI message")).toHaveCount(0);
  const widthAfter = (await lastColumn.boundingBox())?.width ?? 0;
  expect(widthAfter).toBeGreaterThan(widthBefore);

  await page.getByRole("button", { name: "Open AI assistant" }).click();
  await expect(page.getByLabel("AI message")).toBeVisible();
});

test("board fills the viewport width on wide screens", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();

  const sidebar = page.getByTestId("ai-sidebar");
  await expect(sidebar).toBeVisible();
  const sidebarBox = await sidebar.boundingBox();
  expect(sidebarBox).not.toBeNull();
  expect(sidebarBox!.x + sidebarBox!.width).toBeGreaterThan(1850);

  const columns = page.locator('[data-testid^="column-"]');
  for (let index = 0; index < 5; index += 1) {
    const box = await columns.nth(index).boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThan(240);
    expect(box!.x + box!.width).toBeLessThanOrEqual(sidebarBox!.x);
  }
});
