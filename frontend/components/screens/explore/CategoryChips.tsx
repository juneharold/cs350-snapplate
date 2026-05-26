"use client";

import { useEffect, useRef, useState } from "react";
import { Plus, X } from "lucide-react";
import clsx from "clsx";

/**
 * Horizontally-scrollable category chips for the home screen.
 *
 * Behavior:
 *  • The seed list is computed from whatever categories actually appear
 *    in the nearby restaurants, so chips can't pick filters that would
 *    always return zero results.
 *  • Users can add their own chips via the "+ Add" pill at the end. We
 *    persist these in localStorage so they survive reloads.
 *  • Custom chips have a small × to remove them.
 *  • Tapping a chip toggles the active filter; "All" clears it.
 */

const STORAGE_KEY = "snapplate.custom-categories.v1";

function loadCustom(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function saveCustom(list: string[]) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  } catch {
    /* quota — ignore */
  }
}

export type CategoryChipsProps = {
  seedCategories: string[];
  active: string | null;
  onChange: (next: string | null) => void;
  /** Notified whenever the custom list changes so the parent can refilter. */
  onCustomChange?: (custom: string[]) => void;
};

export function CategoryChips({
  seedCategories,
  active,
  onChange,
  onCustomChange,
}: CategoryChipsProps) {
  const [custom, setCustom] = useState<string[]>([]);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const initial = loadCustom();
    setCustom(initial);
    onCustomChange?.(initial);
    // We only want to hydrate from localStorage once.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (adding) inputRef.current?.focus();
  }, [adding]);

  function commit() {
    const next = draft.trim();
    if (
      next &&
      next.length <= 24 &&
      !custom.includes(next) &&
      !seedCategories.includes(next)
    ) {
      const updated = [...custom, next];
      setCustom(updated);
      saveCustom(updated);
      onCustomChange?.(updated);
    }
    setDraft("");
    setAdding(false);
  }

  function cancelAdding() {
    setDraft("");
    setAdding(false);
  }

  function remove(cat: string) {
    const updated = custom.filter((c) => c !== cat);
    setCustom(updated);
    saveCustom(updated);
    onCustomChange?.(updated);
    if (active === cat) onChange(null);
  }

  return (
    <div
      className="chip-row flex items-center gap-2"
      style={{ overflowX: "auto", padding: "0 22px 6px" }}
    >
      <Chip
        active={active === null}
        onClick={() => onChange(null)}
        label="All"
      />
      {seedCategories.map((c) => (
        <Chip
          key={c}
          active={active === c}
          onClick={() => onChange(active === c ? null : c)}
          label={c}
        />
      ))}
      {custom.map((c) => (
        <CustomChip
          key={c}
          label={c}
          active={active === c}
          onClick={() => onChange(active === c ? null : c)}
          onRemove={() => remove(c)}
        />
      ))}
      {adding ? (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            commit();
          }}
          className="flex items-center"
          style={{ flexShrink: 0 }}
        >
          <input
            ref={inputRef}
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => {
              if (e.key === "Escape") cancelAdding();
            }}
            placeholder="Name it…"
            maxLength={24}
            className="chip"
            style={{
              width: 130,
              height: 30,
              padding: "0 12px",
              border: "1px solid var(--color-olive-700)",
              background: "var(--color-surface-2)",
              outline: "none",
              color: "var(--color-ink)",
              fontSize: 12.5,
              fontWeight: 500,
            }}
          />
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setAdding(true)}
          aria-label="Add a category"
          className="chip"
          style={{
            flexShrink: 0,
            gap: 4,
            color: "var(--color-olive-700)",
            borderStyle: "dashed",
            borderColor: "var(--color-olive-300)",
            background: "transparent",
          }}
        >
          <Plus size={12} strokeWidth={2.2} />
          Add
        </button>
      )}
    </div>
  );
}

function Chip({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx("chip", active && "chip-solid")}
      style={{ flexShrink: 0 }}
    >
      {label}
    </button>
  );
}

function CustomChip({
  active,
  onClick,
  label,
  onRemove,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  onRemove: () => void;
}) {
  return (
    <span
      className={clsx("chip", active && "chip-solid")}
      style={{
        flexShrink: 0,
        paddingRight: 6,
        gap: 4,
      }}
    >
      <button
        type="button"
        onClick={onClick}
        style={{
          background: "transparent",
          color: "inherit",
          fontWeight: 500,
          fontSize: 12.5,
        }}
      >
        {label}
      </button>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        aria-label={`Remove ${label}`}
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: 18,
          height: 18,
          borderRadius: 999,
          background: active ? "rgba(244,240,222,0.18)" : "transparent",
          color: "inherit",
          opacity: 0.8,
        }}
      >
        <X size={12} strokeWidth={2} />
      </button>
    </span>
  );
}
