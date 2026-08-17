import { useCallback, useEffect, useMemo, useState } from "react";
import { getStats } from "../api";
import type { StatsResp, StatsWard, User } from "../types";
import TopBar, { type View } from "../components/TopBar";

type Preset = "all" | "today" | "7" | "30" | "custom";

interface Props {
  user: User;
  onLogout: () => void;
  view: View;
  onNavigate: (v: View) => void;
}

const PRESETS: { key: Preset; label: string }[] = [
  { key: "all", label: "Tất cả" },
  { key: "today", label: "Hôm nay" },
  { key: "7", label: "7 ngày" },
  { key: "30", label: "30 ngày" },
  { key: "custom", label: "Tùy chỉnh" },
];

const isoDay = (d: Date) => d.toISOString().slice(0, 10);
const fmtNum = (n: number) => n.toLocaleString("vi-VN");

// Tên thủ tục rất dài → rút gọn còn N từ rồi "…" (giữ full ở title khi hover).
const truncWords = (s: string, n = 6): string => {
  const words = s.trim().split(/\s+/);
  return words.length <= n ? s : words.slice(0, n).join(" ") + "…";
};

function presetRange(preset: Preset): { from?: string; to?: string } {
  if (preset === "all" || preset === "custom") return {};
  const now = new Date();
  if (preset === "today") return { from: isoDay(now), to: isoDay(now) };
  const back = preset === "7" ? 6 : 29;
  const from = new Date(now);
  from.setDate(from.getDate() - back);
  return { from: isoDay(from), to: isoDay(now) };
}

export default function Stats({ user, onLogout, view, onNavigate }: Props) {
  const [preset, setPreset] = useState<Preset>("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [data, setData] = useState<StatsResp | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [openWards, setOpenWards] = useState<Set<string>>(new Set());

  const range = useMemo(() => {
    if (preset === "custom") return { from: dateFrom || undefined, to: dateTo || undefined };
    return presetRange(preset);
  }, [preset, dateFrom, dateTo]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getStats(
        range.from ? `${range.from}T00:00:00` : undefined,
        range.to ? `${range.to}T23:59:59` : undefined,
      );
      setData(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi tải dữ liệu");
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => {
    load();
  }, [load]);

  function toggleWard(id: string) {
    setOpenWards((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const procs = data?.procedures ?? [];
  const wards = data?.wards ?? [];
  const maxProc = procs[0]?.count ?? 0;
  const maxWard = wards[0]?.total ?? 0;
  const dedupPct =
    data && data.totalRequests > 0
      ? Math.round((1 - data.totalDossiers / data.totalRequests) * 100)
      : 0;

  return (
    <div className="app">
      <TopBar user={user} view={view} onNavigate={onNavigate} onLogout={onLogout} />

      <div className="stats-head">
        <div>
          <h1 className="page-title">Thống kê hồ sơ</h1>
          <p className="muted page-sub">Số hồ sơ riêng biệt theo phường/xã và thủ tục</p>
        </div>
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
      </div>

      {preset === "custom" && (
        <section className="filters custom-range">
          <label>
            Từ ngày
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </label>
          <label>
            Đến ngày
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </label>
        </section>
      )}

      {error && <div className="error bar">{error}</div>}

      <section className="kpi-grid">
        <div className="kpi-card accent-primary">
          <span className="kpi-label">Hồ sơ riêng biệt</span>
          <span className="kpi-num">{data ? fmtNum(data.totalDossiers) : "—"}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Lượt bấm</span>
          <span className="kpi-num">{data ? fmtNum(data.totalRequests) : "—"}</span>
          {data && data.totalRequests > 0 && (
            <span className="kpi-foot">gộp trùng {dedupPct}%</span>
          )}
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Phường/xã</span>
          <span className="kpi-num">{data ? fmtNum(wards.length) : "—"}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Loại thủ tục</span>
          <span className="kpi-num">{data ? fmtNum(procs.length) : "—"}</span>
        </div>
      </section>

      <div className="panel-grid">
        <section className="panel">
          <div className="panel-head">
            <h2>Theo thủ tục</h2>
            <span className="muted">{procs.length} loại</span>
          </div>
          <div className="bar-list">
            {procs.map((p) => (
              <div className="bar-row" key={p.key}>
                <span className="bar-label" title={p.label}>
                  {truncWords(p.label)}
                </span>
                <span className="bar-track">
                  <span
                    className="bar-fill"
                    style={{ width: `${maxProc ? (p.count / maxProc) * 100 : 0}%` }}
                  />
                </span>
                <span className="bar-val">{fmtNum(p.count)}</span>
              </div>
            ))}
            {!loading && procs.length === 0 && <p className="empty">Chưa có hồ sơ nào</p>}
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>Theo phường/xã</h2>
            <span className="muted">bấm để xem chi tiết</span>
          </div>
          <div className="bar-list">
            {wards.map((w: StatsWard) => {
              const open = openWards.has(w.userId);
              return (
                <div className={`ward-item ${open ? "open" : ""}`} key={w.userId}>
                  <button className="ward-head" onClick={() => toggleWard(w.userId)} aria-expanded={open}>
                    <svg className="chev" viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">
                      <path d="M7 5l6 5-6 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span className="bar-label" title={w.name}>
                      {w.name}
                    </span>
                    <span className="bar-track">
                      <span
                        className="bar-fill ward"
                        style={{ width: `${maxWard ? (w.total / maxWard) * 100 : 0}%` }}
                      />
                    </span>
                    <span className="bar-val">{fmtNum(w.total)}</span>
                  </button>
                  {open && (
                    <div className="ward-detail">
                      {w.procedures.map((p) => (
                        <div className="detail-row" key={p.key}>
                          <span className="detail-label" title={p.label}>
                            {truncWords(p.label)}
                          </span>
                          <span className="detail-val">
                            {fmtNum(p.count)}
                            <span className="muted"> hồ sơ</span>
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
            {!loading && wards.length === 0 && <p className="empty">Chưa có hồ sơ nào</p>}
          </div>
        </section>
      </div>

      <p className="stat-note muted">
        <strong>Hồ sơ riêng biệt:</strong> các lần bấm cùng một bộ giấy tờ (tập file trùng nhau hoặc
        là con của nhau) trong cùng phường + thủ tục được gom thành 1 hồ sơ; autofill và đính kèm cũng
        gộp nếu file trùng/là con của nhau.
      </p>
    </div>
  );
}
