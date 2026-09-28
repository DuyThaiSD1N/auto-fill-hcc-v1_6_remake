import { useEffect, useState } from "react";
import { getTrace } from "../api";
import type { TraceDetail, User } from "../types";
import { goToList } from "../nav";
import TopBar, { type View } from "./TopBar";
import TraceInfo from "./TraceInfo";

interface Props {
  id: string;
  user: User;
  onLogout: () => void;
  onNavigate: (v: View) => void;
}

// Trang chi tiết trace (URL riêng #/trace/<id>) — mở từ nút "Xem chi tiết" trên drawer. Cùng thông tin với
// drawer, bố cục rộng hơn. Không có nội dung giấy tờ (xem TraceInfo).
export default function TraceDetailPage({ id, user, onLogout, onNavigate }: Props) {
  const [trace, setTrace] = useState<TraceDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    setTrace(null);
    setError("");
    getTrace(id)
      .then((t) => alive && setTrace(t))
      .catch((e) => alive && setError(e instanceof Error ? e.message : "Lỗi tải chi tiết"));
    return () => {
      alive = false;
    };
  }, [id]);

  return (
    <div className="app">
      <TopBar user={user} view="traces" onNavigate={onNavigate} onLogout={onLogout} />

      <button className="back-link" onClick={goToList}>
        ← Nhật ký
      </button>

      {error && <div className="error bar">{error}</div>}
      {!trace && !error && <div className="muted">Đang tải…</div>}

      {trace && (
        <>
          <div className="detail-head">
            <h1 className="detail-title">{trace.procedure_label || trace.procedure}</h1>
            <div className="detail-badges">
              <span className={`badge source-${trace.experience || "autofill"}`}>
                {trace.experience === "handfree" ? "Handfree" : "No handfree"}
              </span>
              <span className={`badge ${trace.kind === "attach" ? "warn" : "ok"}`}>
                {trace.kind === "attach" ? "Đính kèm" : "Auto-fill"}
              </span>
              {trace.ocr_label && (
                <span className={`badge ocr-${trace.ocr_provider}`}>{trace.ocr_label}</span>
              )}
              <span className={`badge ${trace.status === "done" ? "ok" : "warn"}`}>
                {trace.status}
              </span>
            </div>
            {trace.applicant_name && (
              <p className="muted detail-sub">Người làm thủ tục: {trace.applicant_name}</p>
            )}
          </div>

          <section className="panel detail-section">
            <TraceInfo trace={trace} wide />
          </section>
        </>
      )}
    </div>
  );
}
