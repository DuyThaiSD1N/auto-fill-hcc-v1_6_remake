import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getWardSummary, type WardSummary, type WardUser, ApiError } from "./api";
import Seal from "./Seal";
import { Donut, RankBars, DayColumns, buildSlices } from "./charts";

type Preset = "all" | "today" | "7" | "30" | "custom";

const PRESETS: { key: Preset; label: string }[] = [
  { key: "all", label: "Tất cả" },
  { key: "today", label: "Hôm nay" },
  { key: "7", label: "7 ngày" },
  { key: "30", label: "30 ngày" },
  { key: "custom", label: "Tùy chỉnh" },
];

const isoDay = (d: Date) => d.toISOString().slice(0, 10);
const fmtNum = (n: number) => n.toLocaleString("vi-VN");

function presetRange(preset: Preset): { from?: string; to?: string } {
  if (preset === "all" || preset === "custom") return {};
  const now = new Date();
  if (preset === "today") return { from: isoDay(now), to: isoDay(now) };
  const back = preset === "7" ? 6 : 29;
  const from = new Date(now);
  from.setDate(from.getDate() - back);
  return { from: isoDay(from), to: isoDay(now) };
}

const prefersReduced = () =>
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// Đếm tăng dần cho số KPI (tôn trọng reduced-motion → hiện thẳng số cuối).
function useCountUp(target: number, run: boolean): number {
  const [val, setVal] = useState(0);
  const raf = useRef(0);
  useEffect(() => {
    if (!run || prefersReduced()) {
      setVal(target);
      return;
    }
    const start = performance.now();
    const dur = 650;
    const tick = (t: number) => {
      const p = Math.min((t - start) / dur, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(Math.round(target * eased));
      if (p < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [target, run]);
  return val;
}

function Kpi({ label, value, accent, animate }: { label: string; value: number; accent?: boolean; animate: boolean }) {
  const shown = useCountUp(value, animate);
  return (
    <div className={`kpi ${accent ? "kpi-accent" : ""}`}>
      <span className="kpi-num">{fmtNum(shown)}</span>
      <span className="kpi-label">{label}</span>
    </div>
  );
}

interface Props {
  user: WardUser;
  onLogout: () => void;
}

export default function Dashboard({ user, onLogout }: Props) {
  const [preset, setPreset] = useState<Preset>("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [data, setData] = useState<WardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notAssigned, setNotAssigned] = useState(false);
  const [updatedAt, setUpdatedAt] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  const range = useMemo(() => {
    if (preset === "custom") return { from: dateFrom || undefined, to: dateTo || undefined };
    return presetRange(preset);
  }, [preset, dateFrom, dateTo]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    setNotAssigned(false);
    try {
      const res = await getWardSummary(range.from, range.to);
      setData(res);
      setUpdatedAt(new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" }));
    } catch (e) {
      if (e instanceof ApiError && e.code === "WARD_NOT_ASSIGNED") setNotAssigned(true);
      else setError(e instanceof Error ? e.message : "Không tải được số liệu.");
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => {
    load();
  }, [load, reloadKey]);

  const wardName = data?.ward.name || user.name || user.username;
  const kpis = data?.kpis;
  const byProc = data?.byProcedure ?? [];
  const byDay = data?.byDay ?? [];
  const slices = useMemo(() => buildSlices(byProc), [byProc]);
  const hasData = !!kpis && kpis.dossiers > 0;
  const animKey = `${preset}-${range.from ?? ""}-${range.to ?? ""}-${reloadKey}`;

  return (
    <div className="dash">
      <header className="masthead">
        <div className="mast-brand">
          <Seal size={54} bottom="THỐNG KÊ HỒ SƠ" />
          <div className="mast-titles">
            <span className="mast-eyebrow">Trợ lý người dân toàn trình</span>
            <h1 className="mast-ward">{wardName}</h1>
            <span className="mast-place">{data?.ward.tinh || user.tinh || "—"}</span>
          </div>
        </div>
        <button className="logout" onClick={onLogout}>
          Đăng xuất
        </button>
      </header>

      <div className="toolbar">
        <div className="seg" role="tablist" aria-label="Khoảng thời gian">
          {PRESETS.map((p) => (
            <button
              key={p.key}
              role="tab"
              aria-selected={preset === p.key}
              className={`seg-btn ${preset === p.key ? "active" : ""}`}
              onClick={() => setPreset(p.key)}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="toolbar-right">
          {updatedAt && <span className="stamp">Số liệu tính đến {updatedAt}</span>}
          <button className="refresh" onClick={() => setReloadKey((k) => k + 1)} disabled={loading}>
            <span className={`refresh-ico ${loading ? "spin" : ""}`} aria-hidden="true">↻</span>
            Làm mới
          </button>
        </div>
      </div>

      {preset === "custom" && (
        <div className="custom-range">
          <label>
            Từ ngày
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </label>
          <label>
            Đến ngày
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </label>
        </div>
      )}

      <main className="dash-body">
        {notAssigned ? (
          <div className="notice">
            <Seal size={64} tone="ink" bottom="THỐNG KÊ HỒ SƠ" />
            <h2>Tài khoản chưa gán phường</h2>
            <p>Tài khoản này chưa được gán tỉnh/xã nên chưa có phạm vi số liệu. Vui lòng liên hệ quản trị để cập nhật.</p>
          </div>
        ) : error ? (
          <div className="notice">
            <h2>Không tải được số liệu</h2>
            <p>{error}</p>
            <button className="refresh" onClick={() => setReloadKey((k) => k + 1)}>
              Thử lại
            </button>
          </div>
        ) : (
          <>
            <section className="kpi-row" key={animKey}>
              <Kpi label="Hồ sơ" value={kpis?.dossiers ?? 0} accent animate={!loading} />
              <Kpi label="Loại thủ tục" value={kpis?.procedureTypes ?? 0} animate={!loading} />
              <div className="kpi kpi-top">
                <span className="kpi-top-label" title={kpis?.topProcedure?.label || ""}>
                  {kpis?.topProcedure?.label || "—"}
                </span>
                <span className="kpi-label">
                  Thủ tục nhiều nhất{kpis?.topProcedure ? ` · ${fmtNum(kpis.topProcedure.count)} hồ sơ` : ""}
                </span>
              </div>
            </section>

            {!hasData && !loading ? (
              <div className="notice soft">
                <Seal size={56} tone="ink" bottom="THỐNG KÊ HỒ SƠ" />
                <h2>Chưa có hồ sơ nào</h2>
                <p>Không có hồ sơ nào chạy qua Trợ lý trong khoảng thời gian này.</p>
              </div>
            ) : (
              <>
                <div className="panel-grid">
                  <section className="card">
                    <div className="card-head">
                      <span className="card-eyebrow">Cơ cấu</span>
                      <h2>Tỷ trọng theo thủ tục</h2>
                    </div>
                    <Donut slices={slices} total={kpis?.dossiers ?? 0} />
                  </section>

                  <section className="card">
                    <div className="card-head">
                      <span className="card-eyebrow">Diễn biến</span>
                      <h2>Lượt hồ sơ theo ngày</h2>
                    </div>
                    {byDay.length > 0 ? (
                      <DayColumns data={byDay} />
                    ) : (
                      <p className="empty-inline">Chưa đủ dữ liệu theo ngày.</p>
                    )}
                  </section>
                </div>

                <section className="card">
                  <div className="card-head">
                    <span className="card-eyebrow">Xếp hạng</span>
                    <h2>Số hồ sơ theo từng thủ tục</h2>
                    <span className="card-meta">{byProc.length} loại</span>
                  </div>
                  <RankBars items={byProc} />
                </section>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
