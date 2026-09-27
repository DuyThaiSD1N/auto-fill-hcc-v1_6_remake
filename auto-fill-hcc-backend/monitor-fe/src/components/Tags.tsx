import { KIND_LABELS, OUTCOME_LABELS, SOURCE_LABELS } from "../stages";
import Icon from "./Icon";

export function OutcomeBadge({ outcome, compact = false }: { outcome?: string | null; compact?: boolean }) {
  const o = outcome === "error" || outcome === "partial" ? outcome : "ok";
  const icon = o === "ok" ? "check" : o === "partial" ? "alert" : "x";
  return (
    <span className={`outcome outcome--${o}`} title={OUTCOME_LABELS[o]}>
      <span className="outcome__dot"><Icon name={icon} size={12} /></span>
      {compact ? <span className="sr-only">{OUTCOME_LABELS[o]}</span> : OUTCOME_LABELS[o]}
    </span>
  );
}

export function KindTag({ kind }: { kind?: string | null }) {
  return <span className="tag">{KIND_LABELS[kind ?? ""] ?? kind ?? "—"}</span>;
}

export function SourceTag({ source }: { source?: string | null }) {
  return <span className={`tag${source === "handfree" ? " tag--hf" : ""}`}>{SOURCE_LABELS[source ?? ""] ?? "Auto Fill"}</span>;
}
