import clsx from "clsx";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Card, Column } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  accentColor: string;
  onRename: (columnId: string, title: string) => void;
  onAddCard: (columnId: string, title: string, details: string) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
};

export const KanbanColumn = ({
  column,
  cards,
  accentColor,
  onRename,
  onAddCard,
  onDeleteCard,
}: KanbanColumnProps) => {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "flex min-h-[420px] min-w-[78vw] flex-1 basis-0 snap-start flex-col sm:min-w-[200px] rounded-2xl border border-[var(--stroke)] bg-[var(--column-bg)] transition lg:min-h-0",
        isOver && "border-[var(--accent-yellow)] ring-2 ring-[var(--accent-yellow)]/60"
      )}
      data-testid={`column-${column.id}`}
    >
      <header className="flex items-center gap-2 px-3 pb-2 pt-3">
        <span
          className="h-2.5 w-2.5 shrink-0 rounded-full"
          style={{ backgroundColor: accentColor }}
          aria-hidden="true"
        />
        <input
          value={column.title}
          onChange={(event) => onRename(column.id, event.target.value)}
          className="min-w-0 flex-1 truncate rounded-md bg-transparent px-1 py-0.5 font-display text-[15px] font-semibold text-[var(--navy-dark)] outline-none transition hover:bg-white/70 focus:bg-white focus:ring-2 focus:ring-[var(--primary-blue)]/40"
          aria-label="Column title"
        />
        <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold tabular-nums text-[var(--gray-text)]">
          {cards.length}
          <span className="sr-only">{cards.length === 1 ? " card" : " cards"}</span>
        </span>
      </header>
      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-3 pb-1 pt-1">
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <KanbanCard
              key={card.id}
              card={card}
              onDelete={(cardId) => onDeleteCard(column.id, cardId)}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="flex flex-1 items-center justify-center rounded-xl border border-dashed border-[rgba(3,33,71,0.15)] px-3 py-8 text-center text-xs font-medium text-[var(--gray-text)]">
            Drop a card here
          </div>
        )}
      </div>
      <div className="px-3 pb-3 pt-2">
        <NewCardForm onAdd={(title, details) => onAddCard(column.id, title, details)} />
      </div>
    </section>
  );
};
