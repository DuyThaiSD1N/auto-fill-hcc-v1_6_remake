import type { Rating } from "./types";

// Mặt cười theo mức hài lòng (5→1) + màu khớp thang mức của trợ lý (mockup 5).
export const RATING_FACE: Record<number, { emoji: string; color: string }> = {
  5: { emoji: "😄", color: "#1b8f57" },
  4: { emoji: "🙂", color: "#5da76a" },
  3: { emoji: "😐", color: "#c2941f" },
  2: { emoji: "🙁", color: "#c4702f" },
  1: { emoji: "😞", color: "#bd3b2e" },
};

// Ô gọn cho bảng danh sách: mặt cười + mức, tooltip là lý do.
// 3 trạng thái: chưa có (—) · bỏ qua · có mức.
export function RatingCell({ rating }: { rating?: Rating | null }) {
  if (!rating) return <span className="muted">—</span>;
  if (rating.level == null) return <span className="muted">Bỏ qua</span>;
  const f = RATING_FACE[rating.level] || RATING_FACE[3];
  const title = rating.reasons.length ? rating.reasons.join(", ") : rating.note || "";
  return (
    <span className="rating-cell" title={title} style={{ color: f.color }}>
      <span className="rating-emoji" aria-hidden="true">{f.emoji}</span>
      <span className="rating-lv">{rating.levelLabel || rating.level}</span>
    </span>
  );
}

// Bản đầy đủ cho drawer chi tiết: mặt cười + mức + chip lý do + ý kiến (nếu nói).
export function RatingDetail({ rating }: { rating?: Rating | null }) {
  if (!rating) return <span className="muted">Chưa có</span>;
  if (rating.level == null) return <span className="muted">Công dân bỏ qua</span>;
  const f = RATING_FACE[rating.level] || RATING_FACE[3];
  return (
    <div className="rating-detail">
      <span className="rating-cell" style={{ color: f.color }}>
        <span className="rating-emoji" aria-hidden="true">{f.emoji}</span>
        <b>{rating.levelLabel || rating.level}</b>
      </span>
      {rating.reasons.length > 0 && (
        <div className="rating-reasons">
          {rating.reasons.map((r, i) => (
            <span key={i} className="rating-tag">{r}</span>
          ))}
        </div>
      )}
      {rating.note && <div className="rating-note-text">“{rating.note}”</div>}
    </div>
  );
}
