import { useState, type FormEvent } from "react";
import { CloseIcon, PlusIcon } from "@/components/icons";

const initialFormState = { title: "", details: "" };

type NewCardFormProps = {
  onAdd: (title: string, details: string) => void;
};

export const NewCardForm = ({ onAdd }: NewCardFormProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [formState, setFormState] = useState(initialFormState);

  const close = () => {
    setIsOpen(false);
    setFormState(initialFormState);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.title.trim()) {
      return;
    }
    onAdd(formState.title.trim(), formState.details.trim());
    close();
  };

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="flex w-full items-center gap-1.5 rounded-lg px-2 py-1.5 text-[13px] font-semibold text-[var(--gray-text)] transition hover:bg-white hover:text-[var(--primary-blue)]"
      >
        <PlusIcon width={15} height={15} />
        Add a card
      </button>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          close();
        }
      }}
      className="space-y-2 rounded-xl border border-[var(--stroke)] bg-white p-2 shadow-[0_1px_2px_rgba(3,33,71,0.06)]"
    >
      <input
        value={formState.title}
        onChange={(event) => setFormState((prev) => ({ ...prev, title: event.target.value }))}
        placeholder="Card title"
        aria-label="Card title"
        className="w-full rounded-lg border border-[var(--stroke)] px-2.5 py-1.5 text-sm font-medium text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
        autoFocus
        required
      />
      <textarea
        value={formState.details}
        onChange={(event) => setFormState((prev) => ({ ...prev, details: event.target.value }))}
        placeholder="Details"
        aria-label="Card details"
        rows={2}
        className="w-full resize-none rounded-lg border border-[var(--stroke)] px-2.5 py-1.5 text-[13px] text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
      />
      <div className="flex items-center gap-1.5">
        <button
          type="submit"
          className="rounded-lg bg-[var(--secondary-purple)] px-3 py-1.5 text-xs font-semibold text-white transition hover:brightness-110"
        >
          Add card
        </button>
        <button
          type="button"
          onClick={close}
          className="flex h-7 w-7 items-center justify-center rounded-lg text-[var(--gray-text)] transition hover:bg-[var(--surface)] hover:text-[var(--navy-dark)]"
          aria-label="Cancel"
          title="Cancel"
        >
          <CloseIcon width={15} height={15} />
        </button>
      </div>
    </form>
  );
};
