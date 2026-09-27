"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { AiSidebar } from "@/components/AiSidebar";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { LogOutIcon } from "@/components/icons";
import { fetchBoard, saveBoard } from "@/lib/boardApi";
import { createId, moveCard, type BoardData } from "@/lib/kanban";

const COLUMN_ACCENTS = [
  "var(--gray-text)",
  "var(--secondary-purple)",
  "var(--primary-blue)",
  "var(--accent-yellow)",
  "#12b76a",
];

export const KanbanBoard = () => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const saveQueueRef = useRef(Promise.resolve());

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board?.cards ?? {}, [board]);

  const loadBoard = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const nextBoard = await fetchBoard();
      setBoard(nextBoard);
    } catch {
      setLoadError("Could not load your board. Please refresh and try again.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadBoard();
  }, [loadBoard]);

  const enqueueSave = useCallback((nextBoard: BoardData) => {
    setIsSaving(true);
    setSaveError(null);
    saveQueueRef.current = saveQueueRef.current
      .then(async () => {
        await saveBoard(nextBoard);
      })
      .catch(() => {
        setSaveError("Could not save your latest changes.");
      })
      .finally(() => {
        setIsSaving(false);
      });
  }, []);

  const applyBoardUpdate = useCallback(
    (updater: (prev: BoardData) => BoardData) => {
      setBoard((prev) => {
        if (!prev) {
          return prev;
        }

        const next = updater(prev);
        enqueueSave(next);
        return next;
      });
    },
    [enqueueSave]
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    applyBoardUpdate((prev) => ({
      ...prev,
      columns: moveCard(prev.columns, active.id as string, over.id as string),
    }));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    applyBoardUpdate((prev) => ({
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    applyBoardUpdate((prev) => ({
      ...prev,
      cards: {
        ...prev.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    applyBoardUpdate((prev) => {
      return {
        ...prev,
        cards: Object.fromEntries(
          Object.entries(prev.cards).filter(([id]) => id !== cardId)
        ),
        columns: prev.columns.map((column) =>
          column.id === columnId
            ? {
                ...column,
                cardIds: column.cardIds.filter((id) => id !== cardId),
              }
            : column
        ),
      };
    });
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  const handleLogout = async () => {
    await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
    window.location.href = "/";
  };

  const handleAiBoardUpdate = (nextBoard: BoardData) => {
    setBoard(nextBoard);
    setSaveError(null);
    setIsSaving(false);
  };

  if (isLoading) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-[860px] items-center justify-center px-6 py-12">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Loading board...
        </p>
      </main>
    );
  }

  if (loadError || !board) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-[860px] flex-col items-center justify-center gap-4 px-6 py-12 text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)]">
          {loadError ?? "Board unavailable"}
        </p>
        <button
          type="button"
          onClick={() => {
            void loadBoard();
          }}
          className="rounded-full bg-[var(--secondary-purple)] px-5 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:brightness-110"
        >
          Retry
        </button>
      </main>
    );
  }

  const totalCards = Object.keys(board.cards).length;

  return (
    <div className="flex min-h-screen flex-col lg:h-screen">
      <header className="flex shrink-0 items-center gap-4 border-b border-[var(--stroke)] bg-white/90 px-4 py-3 backdrop-blur sm:px-6">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[var(--navy-dark)] font-display text-sm font-bold text-[var(--accent-yellow)]">
          KS
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="font-display text-lg font-semibold leading-6 text-[var(--navy-dark)]">
            Kanban Studio
          </h1>
          <p className="truncate text-xs text-[var(--gray-text)]">
            {board.columns.length} columns · {totalCards} {totalCards === 1 ? "card" : "cards"} · Drag cards between stages, click a title to rename
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-3">
          {saveError ? (
            <p className="text-xs font-medium text-[#b42318]" role="alert">
              {saveError}
            </p>
          ) : (
            <p
              className="hidden items-center gap-1.5 text-xs font-medium text-[var(--gray-text)] sm:flex"
              aria-live="polite"
            >
              <span
                className={
                  isSaving
                    ? "h-2 w-2 animate-pulse rounded-full bg-[var(--accent-yellow)]"
                    : "h-2 w-2 rounded-full bg-[#12b76a]"
                }
              />
              {isSaving ? "Saving..." : "All changes saved"}
            </p>
          )}
          <button
            type="button"
            onClick={handleLogout}
            className="flex items-center gap-1.5 rounded-lg border border-[var(--stroke)] px-3 py-1.5 text-xs font-semibold text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
          >
            <LogOutIcon width={14} height={14} />
            Log out
          </button>
        </div>
      </header>

      <main className="flex min-h-0 flex-1 flex-col gap-4 p-4 sm:px-6 lg:flex-row">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section
            className="flex min-h-0 min-w-0 flex-1 snap-x gap-3 overflow-x-auto pb-2"
            aria-label="Board columns"
          >
            {board.columns.map((column, index) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId])}
                accentColor={COLUMN_ACCENTS[index % COLUMN_ACCENTS.length]}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
              />
            ))}
          </section>
          <DragOverlay>
            {activeCard ? <KanbanCardPreview card={activeCard} /> : null}
          </DragOverlay>
        </DndContext>

        <AiSidebar onBoardUpdate={handleAiBoardUpdate} />
      </main>
    </div>
  );
};
