import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";
import { TrashIcon } from "@/components/icons";

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => void;
};

export const KanbanCard = ({ card, onDelete }: KanbanCardProps) => {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "group relative cursor-grab rounded-xl border border-[var(--stroke)] bg-white p-3 shadow-[0_1px_2px_rgba(3,33,71,0.06)]",
        "transition-[box-shadow,border-color,opacity] duration-150 hover:border-[rgba(32,157,215,0.35)] hover:shadow-[0_6px_16px_rgba(3,33,71,0.08)]",
        isDragging && "opacity-40"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <h4 className="pr-7 font-display text-sm font-semibold leading-5 text-[var(--navy-dark)] [overflow-wrap:anywhere]">
        {card.title}
      </h4>
      {card.details ? (
        <p className="mt-1 text-[13px] leading-5 text-[var(--gray-text)] [overflow-wrap:anywhere]">
          {card.details}
        </p>
      ) : null}
      <button
        type="button"
        onClick={() => onDelete(card.id)}
        onPointerDown={(event) => event.stopPropagation()}
        className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-lg text-[var(--gray-text)] opacity-0 transition hover:bg-[#fef3f2] hover:text-[#b42318] focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-[var(--primary-blue)] group-hover:opacity-100 [@media(hover:none)]:opacity-100"
        aria-label={`Delete ${card.title}`}
        title="Delete card"
      >
        <TrashIcon width={15} height={15} />
      </button>
    </article>
  );
};
