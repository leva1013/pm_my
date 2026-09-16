import type { BoardData } from "@/lib/kanban";

export type ChatMessage = {
  role: "user" | "assistant" | "system";
  content: string;
};

export type AiChatResponse = {
  assistantMessage: string;
  appliedOperations: Array<Record<string, unknown>>;
  board: BoardData;
};

export const sendAiChat = async (
  message: string,
  history: ChatMessage[]
): Promise<AiChatResponse> => {
  const response = await fetch("/api/ai/chat", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      history,
    }),
  });

  if (!response.ok) {
    let detail = "AI request failed.";
    try {
      const payload = (await response.json()) as { detail?: string };
      if (typeof payload.detail === "string" && payload.detail.trim()) {
        detail = payload.detail;
      }
    } catch {
      // Ignore parse failures and use default detail.
    }
    throw new Error(detail);
  }

  return (await response.json()) as AiChatResponse;
};
