import { useEffect, useState } from "react";
import { getDossier } from "../api";
import type { DossierDetail } from "../types";
import { fmtDateTime, fmtDuration } from "../format";
import { goToTrace } from "../nav";
import { RatingDetail } from "../rating";

// Drawer nhật ký MỘT hồ sơ: các lượt điền/đính kèm + các lần bấm "Gửi hồ sơ", theo thứ tự
// thời gian. Khác drawer trace (một LƯỢT gọi API) — đây là cả vòng đời hồ sơ.
type Entry =
  | { at: string; kind: "trace"; traceId: string; label: string; note: string }
  | { at: string; kind: "start" | "submit" | "close"; label: string; note: string };

// Lý do phiên kết thúc mà KHÔNG qua đường nộp (dossiers.close_reason).
const CLOSE_REASON: Record<string, string> = {
  manual: "cán bộ mở phiên mới",
  idle: "rảnh quá lâu, tự kết thúc",
  "dvc-home": "quay về trang chủ DVC",
  continue: "nộp xong, làm hồ sơ tiếp",
  new_procedure: "đổi sang thủ tục khác",
  "procedure-change": "đổi sang thủ tục khác",
};

function buildTimeline(d: DossierDetail): Entry[] {
  const entries: Entry[] = [
    // Mốc mở đầu: Handfree là lúc chốt thủ tục, Auto Fill là lượt điền/đính kèm đầu tiên.
    // Không có dòng này thì không thấy được khoảng chờ trước lượt xử lý đầu tiên.
    { at: d.startedAt, kind: "start", label: "Bắt đầu hồ sơ", note: "" },
    ...d.traces.map((t) => ({
      at: t.created_at,
      kind: "trace" as const,
      traceId: t.id,
      label: t.kind === "attach" ? "Đính kèm" : "Điền biểu mẫu",
      note: `${t.attachments?.length ?? 0} tệp${t.status === "error" ? " · lỗi" : ""}`,
    })),
    ...d.submitEvents.map((e) => ({
      at: e.at,
      kind: "submit" as const,
      label: "Nộp hồ sơ",
      note: e.ref ? `mã ${e.ref}` : e.host || "",
    })),
  ];
  if (d.closedAt) {
    entries.push({
      at: d.closedAt,
      kind: "close",
      label: "Kết thúc phiên",
      note: CLOSE_REASON[d.closeReason || ""] || d.closeReason || "",
    });
  }
  return entries.sort((a, b) => +new Date(a.at) - +new Date(b.at));
}

export default function DossierDetailPanel({ id, onClose }: { id: string; onClose: () => void }) {
  const [dossier, setDossier] = useState<DossierDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    setDossier(null);
    setError("");
    getDossier(id)
      .then((d) => alive && setDossier(d))
      .catch((e) => alive && setError(e instanceof Error ? e.message : "Lỗi tải chi tiết"));
    return () => {
      alive = false;
    };
  }, [id]);

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <h2>Nhật ký hồ sơ</h2>
          <button className="ghost" onClick={onClose} aria-label="Đóng">
            ✕
          </button>
        </div>

        {error && <div className="error">{error}</div>}
        {!dossier && !error && <div className="muted">Đang tải…</div>}

        {dossier && (
          <div className="drawer-body">
            {/* Dùng lại dl.meta của drawer trace — cùng ngôn ngữ thị giác, khỏi đẻ class mới. */}
            <dl className="meta">
              <div>
                <dt>Thủ tục</dt>
                <dd>{dossier.procedureLabel || dossier.procedure || "—"}</dd>
              </div>
              <div>
                <dt>Người làm thủ tục</dt>
                <dd>{dossier.applicantName || "—"}</dd>
              </div>
              <div>
                <dt>Đơn vị</dt>
                <dd>{dossier.name || "—"}</dd>
              </div>
              <div>
                <dt>Loại</dt>
                <dd>{dossier.experience === "handfree" ? "Handfree" : "No handfree"}</dd>
              </div>
              <div>
                <dt>Bắt đầu</dt>
                <dd>{fmtDateTime(dossier.startedAt)}</dd>
              </div>
              <div>
                <dt>Nộp lần cuối</dt>
                <dd>{dossier.submittedAt ? fmtDateTime(dossier.submittedAt) : "chưa nộp"}</dd>
              </div>
              <div>
                <dt>Thời gian làm</dt>
                <dd>{fmtDuration(dossier.durationMs)}</dd>
              </div>
              <div>
                <dt>Số lần nộp</dt>
                {/* Chứng thực tách nhiều tab dùng chung một hồ sơ và nộp nhiều lần — đây mới
                    là số hồ sơ thật của lượt đó. */}
                <dd>{dossier.submitCount || 0}</dd>
              </div>
              {/* Đánh giá trải nghiệm (Handfree) — chỉ hiện khi hồ sơ có phiếu. */}
              {dossier.rating && (
                <div className="rating-meta">
                  <dt>Đánh giá</dt>
                  <dd><RatingDetail rating={dossier.rating} /></dd>
                </div>
              )}
            </dl>

            <h3>Diễn biến</h3>
            <ul className="timeline">
              {buildTimeline(dossier).map((e, i) => (
                <li key={`${e.kind}-${i}`} className={`timeline-item ${e.kind}`}>
                  <span className="timeline-time">{fmtDateTime(e.at)}</span>
                  <span className="timeline-label">{e.label}</span>
                  <span className="muted">{e.note}</span>
                  {e.kind === "trace" && (
                    <button className="link-btn" onClick={() => goToTrace(e.traceId)}>
                      xem trace →
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </aside>
    </div>
  );
}
