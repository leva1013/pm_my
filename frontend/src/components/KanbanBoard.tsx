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
import { fetchBoard, saveBoard } from "@/lib/boardApi";
import { createId, moveCard, type BoardData } from "@/lib/kanban";

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

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
              <button
                type="button"
                onClick={handleLogout}
                className="mt-4 rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
              >
                Log out
              </button>
              {isSaving ? (
                <p className="mt-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                  Saving...
                </p>
              ) : null}
              {saveError ? (
                <p className="mt-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#b42318]">
                  {saveError}
                </p>
              ) : null}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px] xl:items-start">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="grid gap-6 lg:grid-cols-5">
              {board.columns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId])}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                />
              ))}
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>

          <AiSidebar onBoardUpdate={handleAiBoardUpdate} />
        </div>
      </main>
    </div>
  );
};
