import { useEffect, useState } from "react";
import { getTrace } from "../api";
import type { TraceDetail } from "../types";
import { goToTrace } from "../nav";
import TraceInfo from "./TraceInfo";

// Drawer XEM NHANH một trace; "Xem chi tiết" mở trang riêng #/trace/<id> (cùng thông tin, rộng hơn).
export default function TraceDetailPanel({ id, onClose }: { id: string; onClose: () => void }) {
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
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <h2>Chi tiết trace</h2>
          <div className="drawer-head-actions">
            <button className="btn-primary sm" onClick={() => goToTrace(id)}>
              Xem chi tiết →
            </button>
            <button className="ghost" onClick={onClose} aria-label="Đóng">
              ✕
            </button>
          </div>
        </div>

        {error && <div className="error">{error}</div>}
        {!trace && !error && <div className="muted">Đang tải…</div>}
        {trace && (
          <div className="drawer-body">
            <TraceInfo trace={trace} />
          </div>
        )}
      </aside>
    </div>
  );
}
