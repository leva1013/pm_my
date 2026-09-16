import type { BoardData } from "@/lib/kanban";

const BOARD_ENDPOINT = "/api/board";

export const fetchBoard = async (): Promise<BoardData> => {
  const response = await fetch(BOARD_ENDPOINT, {
    method: "GET",
    credentials: "same-origin",
  });

  if (!response.ok) {
    throw new Error("Failed to fetch board");
  }

  return (await response.json()) as BoardData;
};

export const saveBoard = async (board: BoardData): Promise<BoardData> => {
  const response = await fetch(BOARD_ENDPOINT, {
    method: "PUT",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(board),
  });

  if (!response.ok) {
    throw new Error("Failed to save board");
  }

  return (await response.json()) as BoardData;
};
