"use client";

import { useState, type FormEvent } from "react";
import { sendAiChat, type ChatMessage } from "@/lib/aiChatApi";
import type { BoardData } from "@/lib/kanban";

type AiSidebarProps = {
  onBoardUpdate: (board: BoardData) => void;
};

export const AiSidebar = ({ onBoardUpdate }: AiSidebarProps) => {
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = inputValue.trim();
    if (!message || isSending) {
      return;
    }

    setInputValue("");
    setError(null);

    const userMessage: ChatMessage = { role: "user", content: message };
    const nextHistory = [...history, userMessage];
    setHistory(nextHistory);
    setIsSending(true);

    try {
      const result = await sendAiChat(message, history);
      setHistory((prev) => [
        ...prev,
        { role: "assistant", content: result.assistantMessage },
      ]);
      onBoardUpdate(result.board);
    } catch (submitError) {
      const messageText =
        submitError instanceof Error ? submitError.message : "AI request failed.";
      setError(messageText);
      setHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I could not process that request right now. Please try again.",
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <aside className="w-full rounded-[28px] border border-[var(--stroke)] bg-white/85 p-5 shadow-[var(--shadow)] backdrop-blur lg:sticky lg:top-8 lg:max-h-[calc(100vh-4rem)] lg:overflow-hidden" data-testid="ai-sidebar">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--gray-text)]">
            AI Copilot
          </p>
          <h2 className="mt-2 font-display text-2xl font-semibold text-[var(--navy-dark)]">
            Board Assistant
          </h2>
        </div>
        <span className="rounded-full bg-[var(--accent-yellow)] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.15em] text-[var(--navy-dark)]">
          Live
        </span>
      </div>

      <p className="mt-3 text-sm leading-6 text-[var(--gray-text)]">
        Ask for card and column changes in plain language. Approved updates apply to your board immediately.
      </p>

      <div className="mt-4 space-y-3 rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] p-3" data-testid="ai-messages">
        {history.length === 0 ? (
          <p className="text-sm text-[var(--gray-text)]">
            Try: &quot;Move card-1 to Review&quot; or &quot;Rename Backlog to Ideas&quot;.
          </p>
        ) : (
          history.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={
                message.role === "user"
                  ? "ml-auto max-w-[90%] rounded-2xl bg-[var(--primary-blue)] px-3 py-2 text-sm text-white"
                  : "max-w-[90%] rounded-2xl bg-white px-3 py-2 text-sm text-[var(--navy-dark)]"
              }
            >
              {message.content}
            </div>
          ))
        )}
      </div>

      {error ? (
        <p className="mt-3 text-xs font-semibold uppercase tracking-[0.08em] text-[#b42318]" data-testid="ai-error">
          {error}
        </p>
      ) : null}

      <form onSubmit={handleSubmit} className="mt-4 space-y-3">
        <textarea
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          placeholder="Ask AI to update your board"
          rows={4}
          className="w-full resize-none rounded-2xl border border-[var(--stroke)] bg-white px-3 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
          aria-label="AI message"
        />
        <button
          type="submit"
          disabled={isSending}
          className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-white transition enabled:hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSending ? "Sending..." : "Send"}
        </button>
      </form>
    </aside>
  );
};
