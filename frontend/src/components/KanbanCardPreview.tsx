import type { Card } from "@/lib/kanban";

type KanbanCardPreviewProps = {
  card: Card;
};

export const KanbanCardPreview = ({ card }: KanbanCardPreviewProps) => (
  <article className="cursor-grabbing rounded-xl border border-[var(--primary-blue)] bg-white p-3 shadow-[0_18px_32px_rgba(3,33,71,0.18)] rotate-[1.5deg]">
    <h4 className="font-display text-sm font-semibold leading-5 text-[var(--navy-dark)] [overflow-wrap:anywhere]">
      {card.title}
    </h4>
    {card.details ? (
      <p className="mt-1 text-[13px] leading-5 text-[var(--gray-text)] [overflow-wrap:anywhere]">
        {card.details}
      </p>
    ) : null}
  </article>
);
