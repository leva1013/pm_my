"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { sendAiChat, type ChatMessage } from "@/lib/aiChatApi";
import type { BoardData } from "@/lib/kanban";
import { PanelCloseIcon, SendIcon, SparklesIcon } from "@/components/icons";

type AiSidebarProps = {
  onBoardUpdate: (board: BoardData) => void;
};

export const AiSidebar = ({ onBoardUpdate }: AiSidebarProps) => {
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(true);
  const messagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = messagesRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }, [history, isSending, isOpen]);

  const submitMessage = async () => {
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

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void submitMessage();
  };

  if (!isOpen) {
    return (
      <aside
        className="flex shrink-0 items-start justify-center self-start rounded-2xl border border-[var(--stroke)] bg-white p-2 shadow-[var(--shadow)] lg:w-14 lg:py-3"
        data-testid="ai-sidebar"
      >
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold text-[var(--secondary-purple)] transition hover:bg-[var(--surface)] lg:h-10 lg:w-10 lg:justify-center lg:p-0"
          aria-label="Open AI assistant"
          title="Open AI assistant"
        >
          <SparklesIcon width={20} height={20} />
          <span className="lg:hidden">AI assistant</span>
        </button>
      </aside>
    );
  }

  return (
    <aside
      className="flex h-[560px] w-full shrink-0 flex-col overflow-hidden rounded-2xl border border-[var(--stroke)] bg-white shadow-[var(--shadow)] lg:h-full lg:w-[320px] 2xl:w-[380px]"
      data-testid="ai-sidebar"
    >
      <header className="flex items-center gap-3 border-b border-[var(--stroke)] px-4 py-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--secondary-purple)] text-white">
          <SparklesIcon width={17} height={17} />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-[15px] font-semibold leading-5 text-[var(--navy-dark)]">
            Board Assistant
          </h2>
          <p className="truncate text-xs text-[var(--gray-text)]">
            Updates your board directly
          </p>
        </div>
        <button
          type="button"
          onClick={() => setIsOpen(false)}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[var(--gray-text)] transition hover:bg-[var(--surface)] hover:text-[var(--navy-dark)]"
          aria-label="Collapse AI assistant"
          title="Collapse AI assistant"
        >
          <PanelCloseIcon width={17} height={17} />
        </button>
      </header>

      <div
        ref={messagesRef}
        className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto bg-[var(--surface)] px-4 py-4"
        data-testid="ai-messages"
      >
        {history.length === 0 ? (
          <div className="m-auto max-w-[260px] text-center">
            <p className="text-sm font-semibold text-[var(--navy-dark)]">
              Ask for card and column changes in plain language.
            </p>
            <p className="mt-2 text-xs leading-5 text-[var(--gray-text)]">
              Try &quot;Move the QA card to Done&quot; or &quot;Rename Backlog to Ideas&quot;.
            </p>
          </div>
        ) : (
          history.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={
                message.role === "user"
                  ? "ml-auto max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-[var(--primary-blue)] px-3 py-2 text-sm text-white"
                  : "mr-auto max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-bl-md border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)]"
              }
            >
              {message.content}
            </div>
          ))
        )}
        {isSending ? (
          <div
            className="mr-auto flex gap-1 rounded-2xl rounded-bl-md border border-[var(--stroke)] bg-white px-3 py-3"
            aria-label="Assistant is thinking"
            role="status"
          >
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--gray-text)]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--gray-text)] [animation-delay:150ms]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-[var(--gray-text)] [animation-delay:300ms]" />
          </div>
        ) : null}
      </div>

      {error ? (
        <p
          className="border-t border-[#fecdca] bg-[#fef3f2] px-4 py-2 text-xs font-medium text-[#b42318]"
          data-testid="ai-error"
        >
          {error}
        </p>
      ) : null}

      <form onSubmit={handleSubmit} className="border-t border-[var(--stroke)] p-3">
        <div className="flex items-end gap-2 rounded-xl border border-[var(--stroke)] bg-white p-1.5 transition focus-within:border-[var(--primary-blue)]">
          <textarea
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void submitMessage();
              }
            }}
            placeholder="Ask AI to update your board"
            rows={2}
            className="max-h-32 min-h-10 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-[var(--navy-dark)] outline-none"
            aria-label="AI message"
          />
          <button
            type="submit"
            disabled={isSending || !inputValue.trim()}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--secondary-purple)] text-white transition enabled:hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Send"
            title="Send (Enter)"
          >
            <SendIcon width={16} height={16} />
          </button>
        </div>
        <p className="mt-1.5 px-1 text-[11px] text-[var(--gray-text)]">
          Enter to send, Shift+Enter for a new line
        </p>
      </form>
    </aside>
  );
};
