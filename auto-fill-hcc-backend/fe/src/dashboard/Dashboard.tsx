import { useCallback, useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import {
  getScope,
  getSummary,
  getLogs,
  exportExcel,
  ApiError,
  type WardUser,
  type ScopeResp,
  type SummaryResp,
  type LogsResp,
} from "./api";
import { DonutMini, BarDays, WeekColumns, buildSlices, PAL, PALBG, fmt } from "./charts";

type View = "tq" | "dv" | "tt" | "nk";
type Preset = "all" | "today" | "7" | "30" | "custom";

const PRESETS: { key: Preset; label: string }[] = [
  { key: "all", label: "Tất cả" },
  { key: "today", label: "Hôm nay" },
  { key: "7", label: "7 ngày" },
  { key: "30", label: "30 ngày" },
  { key: "custom", label: "Tùy chỉnh" },
];

// Ngày theo LỊCH ĐỊA PHƯƠNG (giờ VN của người dùng), KHÔNG dùng toISOString (UTC) — nếu không
// "Hôm nay" lúc rạng sáng sẽ lệch sang hôm qua và backend (đếm theo giờ VN) trả sai ngày.
const isoDay = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
function presetRange(preset: Preset): { from?: string; to?: string } {
  if (preset === "all" || preset === "custom") return {};
  const now = new Date();
  if (preset === "today") return { from: isoDay(now), to: isoDay(now) };
  const from = new Date(now);
  from.setDate(from.getDate() - (preset === "7" ? 6 : 29));
  return { from: isoDay(from), to: isoDay(now) };
}

// Cấp đơn vị suy từ tên xã/phường (chỉ để gắn nhãn, không ảnh hưởng số liệu).
function unitLevel(xa?: string | null): { label: string; cls: string } {
  const t = (xa || "").trim().toLowerCase();
  if (t.startsWith("phường") || t.startsWith("phuong")) return { label: "Phường", cls: "k-phuong" };
  if (t.startsWith("xã") || t.startsWith("xa")) return { label: "Xã", cls: "k-xa" };
  if (t.startsWith("thị") || t.startsWith("thi")) return { label: "Thị trấn", cls: "k-xa" };
  return { label: "Đơn vị", cls: "" };
}

const ICON: Record<string, string> = {
  grid: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7.5" height="7.5" rx="1.8"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="1.8"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="1.8"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.8"/></svg>',
  bank: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18M5 21V6l7-3v18M12 21V10l7 2.5V21"/></svg>',
  list: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.5 6h10M9.5 12h10M9.5 18h10"/><circle cx="4.8" cy="6" r="1.5"/><circle cx="4.8" cy="12" r="1.5"/><circle cx="4.8" cy="18" r="1.5"/></svg>',
  book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 1 6.5 18H20v3H6.5A2.5 2.5 0 0 1 4 20.5z"/></svg>',
  users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3.4"/><path d="M2.8 20a6.2 6.2 0 0 1 12.4 0M16 5.2a3.4 3.4 0 0 1 0 6.6M17.5 14.4A6.2 6.2 0 0 1 21.2 20"/></svg>',
  cog: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3.2"/><path d="M12 2.6l1.5 2.6 3-.5.5 3 2.6 1.5-1.4 2.7 1.4 2.7-2.6 1.5-.5 3-3-.5L12 21.4l-1.5-2.6-3 .5-.5-3L4.4 14.8l1.4-2.7-1.4-2.7 2.6-1.5.5-3 3 .5z"/></svg>',
  doc: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="3" width="14" height="18" rx="2.4"/><path d="M8.5 8h7M8.5 12h7M8.5 16h4"/></svg>',
  cal: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="5" width="17" height="16" rx="2.4"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg>',
  cup: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="9" r="5.4"/><path d="M8.3 13.4L7 21l5-2.7L17 21l-1.3-7.6"/></svg>',
  gauge: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3.6 17a9 9 0 1 1 16.8 0"/><path d="M12 13.5l4-3.6"/><circle cx="12" cy="16" r="1.6"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.8l7.2 2.7v6c0 4.6-3 8.4-7.2 9.7-4.2-1.3-7.2-5.1-7.2-9.7v-6z"/><path d="M9 12l2.2 2.2L15.4 10"/></svg>',
  lock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><rect x="4.5" y="10.5" width="15" height="10" rx="2"/><path d="M8 10.5V7a4 4 0 0 1 8 0v3.5"/></svg>',
  refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M20 11A8 8 0 1 0 18 16.5M20 5v6h-6"/></svg>',
  logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 17l5-5-5-5M15 12H3"/></svg>',
  download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12M7 10l5 5 5-5M5 21h14"/></svg>',
  info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9.2"/><path d="M12 11v5.5M12 7.6v.1"/></svg>',
};

function Ic({ n }: { n: string }) {
  return <span style={{ display: "contents" }} dangerouslySetInnerHTML={{ __html: ICON[n] || "" }} />;
}

interface KpiSpec {
  icon: string;
  color: string;
  bg: string;
  label: string;
  value: string;
  vs?: string;
  foot?: ReactNode;
}

function Kpi({ spec }: { spec: KpiSpec }) {
  return (
    <div className="kpi" style={{ ["--kc" as string]: spec.color, ["--kb" as string]: spec.bg } as CSSProperties}>
      <div className="top">
        <div className="kt">{spec.label}</div>
        <div className="ki">
          <Ic n={spec.icon} />
        </div>
      </div>
      <div className="mid">
        <div className="kv num">{spec.value}</div>
        {spec.vs && <span className="kvs num">{spec.vs}</span>}
      </div>
      {spec.foot != null && <div className="kf">{spec.foot}</div>}
    </div>
  );
}

function Card({
  title,
  sub,
  right,
  children,
}: {
  title: string;
  sub?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="card">
      <div className="ch bd">
        <div>
          <h2>{title}</h2>
          {sub != null && <div className="cs">{sub}</div>}
        </div>
        {right != null && <div className="rt">{right}</div>}
      </div>
      {children}
    </div>
  );
}

interface Props {
  user: WardUser;
  onLogout: () => void;
}

export default function Dashboard({ user, onLogout }: Props) {
  const [scope, setScope] = useState<ScopeResp | null>(null);
  const [view, setView] = useState<View>("tq");
  const [preset, setPreset] = useState<Preset>("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selectedUnit, setSelectedUnit] = useState("all");

  const [summary, setSummary] = useState<SummaryResp | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notAssigned, setNotAssigned] = useState(false);
  const [updatedAt, setUpdatedAt] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [collapsed, setCollapsed] = useState(false);

  const [sortDv, setSortDv] = useState<{ k: "name" | "dossiers" | "procedureTypes"; d: 1 | -1 }>({ k: "dossiers", d: -1 });
  const [sortTt, setSortTt] = useState<{ k: "label" | "count" | "units"; d: 1 | -1 }>({ k: "count", d: -1 });
  const [qUnit, setQUnit] = useState("");
  const [qProc, setQProc] = useState("");

  const [logs, setLogs] = useState<LogsResp | null>(null);
  const [logsLoading, setLogsLoading] = useState(false);
  const [nkPage, setNkPage] = useState(1);
  const [exporting, setExporting] = useState(false);
  const [showExport, setShowExport] = useState(false);

  const range = useMemo(() => {
    if (preset === "custom") return { from: dateFrom || undefined, to: dateTo || undefined };
    return presetRange(preset);
  }, [preset, dateFrom, dateTo]);

  useEffect(() => {
    let alive = true;
    getScope()
      .then((s) => {
        if (!alive) return;
        setScope(s);
        if (!s.canViewUnits) setSelectedUnit("all");
      })
      .catch((e) => {
        if (!alive) return;
        if (e instanceof ApiError && e.code === "DASHBOARD_NOT_ASSIGNED") setNotAssigned(true);
        else setError(e instanceof Error ? e.message : "Không tải được phạm vi tài khoản.");
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const load = useCallback(async () => {
    if (!scope || notAssigned) return;
    setLoading(true);
    setError("");
    try {
      const unitParam = scope.canViewUnits ? selectedUnit : "all";
      const sum = await getSummary(range.from, range.to, unitParam);
      setSummary(sum);
      setUpdatedAt(
        new Date().toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được số liệu.");
    } finally {
      setLoading(false);
    }
  }, [scope, notAssigned, range, selectedUnit, reloadKey]);

  useEffect(() => {
    load();
  }, [load]);

  // Đổi khoảng/đơn vị → nhật ký về trang 1.
  useEffect(() => {
    setNkPage(1);
  }, [range, selectedUnit]);

  const loadLogs = useCallback(async () => {
    if (!scope || notAssigned) return;
    setLogsLoading(true);
    try {
      const unitParam = scope.canViewUnits ? selectedUnit : "all";
      const res = await getLogs(range.from, range.to, unitParam, nkPage, 15);
      setLogs(res);
    } catch {
      /* giữ trang cũ nếu lỗi tạm thời */
    } finally {
      setLogsLoading(false);
    }
  }, [scope, notAssigned, range, selectedUnit, nkPage, reloadKey]);

  useEffect(() => {
    if (view === "nk") loadLogs();
  }, [view, loadLogs]);

  useEffect(() => {
    if (!showExport) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !exporting) setShowExport(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [showExport, exporting]);

  async function handleExport() {
    if (exporting || !scope) return;
    setExporting(true);
    try {
      const unitParam = scope.canViewUnits ? selectedUnit : "all";
      const { blob, filename } = await exportExcel(range.from, range.to, unitParam);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setShowExport(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không xuất được Excel.");
      setShowExport(false);
    } finally {
      setExporting(false);
    }
  }

  // ── Số liệu dẫn xuất ────────────────────────────────────────────────────────
  const canViewUnits = !!scope?.canViewUnits;
  const kpis = summary?.kpis;
  const byProc = summary?.byProcedure ?? [];
  const byDay = summary?.byDay ?? [];
  const units = summary?.units ?? [];
  const handfreeMissing = summary != null && summary.sources?.handfree === false;
  const scopeTotal = units.reduce((a, b) => a + b.dossiers, 0);
  const unitsWithData = units.filter((u) => u.dossiers > 0).length;
  const slices = useMemo(() => buildSlices(byProc), [byProc]);
  const provinceName = scope?.province || user.tinh || "—";
  const roleLabel = canViewUnits
    ? scope?.scopeKind === "all"
      ? "Quản trị hệ thống"
      : "Cấp tỉnh"
    : "Cấp xã/phường";
  const acctName = scope?.self.name || user.name || user.username;
  const initials = (acctName || "?")
    .split(/\s+/)
    .slice(-2)
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  const VIEW_META: Record<View, { title: string; sub: string }> = {
    tq: { title: "Tổng quan", sub: "Bức tranh tổng thể số hồ sơ tiếp nhận qua Trợ lý trong kỳ." },
    dv: { title: "Theo đơn vị", sub: "So sánh số liệu giữa các phường/xã trong phạm vi." },
    tt: { title: "Theo thủ tục", sub: "Danh mục thủ tục phát sinh hồ sơ và tỷ trọng." },
    nk: { title: "Nhật ký hồ sơ", sub: "Từng hồ sơ đã chạy qua Trợ lý (tạm chưa gồm thời lượng xử lý)." },
  };

  const NAV: { id: View | string; label: string; icon: string; group: string; soon?: boolean; lock?: boolean }[] = [
    { id: "tq", label: "Tổng quan", icon: "grid", group: "Báo cáo" },
    { id: "dv", label: "Theo đơn vị", icon: "bank", group: "Báo cáo" },
    { id: "tt", label: "Theo thủ tục", icon: "list", group: "Báo cáo" },
    { id: "nk", label: "Nhật ký hồ sơ", icon: "book", group: "Báo cáo" },
    { id: "ac", label: "Đơn vị & tài khoản", icon: "users", group: "Quản trị", soon: true },
    { id: "dm", label: "Danh mục thủ tục", icon: "doc", group: "Quản trị", soon: true },
  ];
  const navCount: Record<string, number | undefined> = {
    dv: scope?.unitCount,
    tt: kpis?.procedureTypes,
    nk: logs?.total,
  };
  const NAVC: Record<string, string> = { tq: "#1256C7", dv: "#0E8A45", tt: "#C07C00", nk: "#6D3AA8" };

  function goto(id: View | string, soon?: boolean, lock?: boolean) {
    if (soon || lock) return;
    setView(id as View);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ── Trạng thái đặc biệt ─────────────────────────────────────────────────────
  if (notAssigned) {
    return (
      <div className="app">
        <main className="mn">
          <div className="ct">
            <div className="lockbox" style={{ maxWidth: 720, margin: "40px auto" }}>
              <div className="ic">
                <Ic n="lock" />
              </div>
              <div>
                <h3>Tài khoản chưa có phạm vi số liệu</h3>
                <p>
                  Tài khoản này chưa được gán tỉnh/phường-xã nên chưa có dữ liệu để hiển thị. Vui lòng liên hệ quản trị
                  để cập nhật.
                </p>
                <button className="btn" style={{ marginTop: 14 }} onClick={onLogout}>
                  <Ic n="logout" /> Đăng xuất
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className={`app ${collapsed ? "narrow" : ""}`}>
      {/* ── Thanh điều hướng trái ── */}
      <aside className="sb">
        <div className="sb-brand">
          <div className="em" style={emblemStyle}>
            <Ic n="shield" />
          </div>
          <div className="tx">
            <div className="t1">TRỢ LÝ NGƯỜI DÂN</div>
            <div className="t2">Thống kê hồ sơ hành chính công</div>
          </div>
          <button className="sb-collapse" onClick={() => setCollapsed((c) => !c)} title="Thu gọn">
            <Ic n="grid" />
          </button>
        </div>

        <nav className="sb-nav">
          {["Báo cáo", "Quản trị"].map((g) => (
            <div key={g}>
              <div className="ng">{g}</div>
              {NAV.filter((n) => n.group === g).map((n) => (
                <button
                  key={n.id}
                  className={`ni ${n.id === view ? "on" : ""} ${n.soon ? "lockrow" : ""}`}
                  disabled={n.soon}
                  style={NAVC[n.id] ? ({ ["--nc" as string]: NAVC[n.id] } as CSSProperties) : undefined}
                  onClick={() => goto(n.id, n.soon, n.lock)}
                >
                  <Ic n={n.icon} />
                  <span className="lb">{n.label}</span>
                  {n.lock && (
                    <span className="lk">
                      <Ic n="lock" />
                    </span>
                  )}
                  {navCount[n.id] != null && <span className="cb num">{fmt(navCount[n.id]!)}</span>}
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="sb-foot">
          <div className={`scopecard ${canViewUnits ? "" : "lock"}`}>
            <div className="hd">
              <Ic n={canViewUnits ? "shield" : "lock"} />
              <span>Phạm vi dữ liệu</span>
            </div>
            <div className="nm">{canViewUnits ? `Toàn tỉnh ${provinceName}` : acctName}</div>
            <div className="ds">
              {canViewUnits ? "Xem số liệu toàn bộ đơn vị trực thuộc" : "Chỉ xem số liệu của đơn vị mình"}
            </div>
            <div className="st">
              <div>
                <b className="num">{fmt(canViewUnits ? scope?.unitCount ?? 0 : 1)}</b>
                <span>Đơn vị</span>
              </div>
              <div>
                <b className="num">{fmt(scopeTotal)}</b>
                <span>Hồ sơ</span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Cột phải ── */}
      <div className="mn">
        <div className="tb">
          <button className="icb" onClick={() => setCollapsed((c) => !c)} title="Ẩn/hiện điều hướng">
            <Ic n="grid" />
          </button>
          <div className="sp" />
          {updatedAt && (
            <span className="stamp" style={stampStyle}>
              {loading ? "Đang cập nhật số liệu…" : `Số liệu tính đến ${updatedAt}`}
            </span>
          )}
          <button
            className={`icb ${loading ? "spinning" : ""}`}
            onClick={() => setReloadKey((k) => k + 1)}
            disabled={loading}
            title="Làm mới"
          >
            <Ic n="refresh" />
          </button>
          <div className="me">
            <div className="av">{initials}</div>
            <div>
              <div className="nm">{acctName}</div>
              <div className="rl">
                <b>{roleLabel}</b> · {provinceName}
              </div>
            </div>
            <button className="icb" style={{ marginLeft: 4 }} onClick={onLogout} title="Đăng xuất">
              <Ic n="logout" />
            </button>
          </div>
        </div>

        <div className="ct">
          <div className="ph">
            <div>
              <h1>{VIEW_META[view].title}</h1>
              <div className="sub">{VIEW_META[view].sub}</div>
            </div>
            <div className="rt">
              <button className="btn btn-pri" onClick={() => setShowExport(true)} disabled={loading}>
                <Ic n="download" /> Xuất Excel
              </button>
            </div>
          </div>

          {/* Bộ lọc */}
          <div className="filters">
            <div className="fl">
              <label>Khoảng thời gian</label>
              <select className="ctl" value={preset} onChange={(e) => setPreset(e.target.value as Preset)}>
                {PRESETS.map((p) => (
                  <option key={p.key} value={p.key}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            {preset === "custom" && (
              <>
                <div className="fl">
                  <label>Từ ngày</label>
                  <input className="ctl" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
                </div>
                <div className="fl">
                  <label>Đến ngày</label>
                  <input className="ctl" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
                </div>
              </>
            )}
            <div className="fl">
              <label>Đơn vị</label>
              <select
                className="ctl"
                value={selectedUnit}
                disabled={!canViewUnits}
                onChange={(e) => setSelectedUnit(e.target.value)}
              >
                <option value="all">
                  {canViewUnits ? `Tất cả đơn vị trong tỉnh (${scope?.unitCount ?? 0})` : acctName}
                </option>
                {canViewUnits &&
                  scope?.units.map((u) => (
                    <option key={u.unitId} value={u.unitId}>
                      {u.xa || u.name}
                    </option>
                  ))}
              </select>
              {!canViewUnits && (
                <span className="hint">
                  <Ic n="lock" /> Chỉ đơn vị của bạn
                </span>
              )}
            </div>
            <div className="sp" />
            <div className="acts">
              <button
                className={`btn ${loading ? "spinning" : ""}`}
                onClick={() => setReloadKey((k) => k + 1)}
                disabled={loading}
              >
                <Ic n="refresh" /> {loading ? "Đang tải…" : "Làm mới"}
              </button>
            </div>
          </div>

          {handfreeMissing && (
            <div className="hf-note">
              <Ic n="lock" />
              <span>
                Đang hiển thị số liệu <b>Auto Fill</b>. Chưa cộng được số liệu Handfree (dịch vụ chưa cấu hình
                hoặc tạm gián đoạn) — bấm Làm mới để thử lại.
              </span>
            </div>
          )}

          {error ? (
            <div className="none" style={{ background: "#fff", borderRadius: 16, border: "1px solid var(--line)" }}>
              {error}{" "}
              <button className="btn" style={{ marginLeft: 8 }} onClick={() => setReloadKey((k) => k + 1)}>
                Thử lại
              </button>
            </div>
          ) : loading && !summary ? (
            <div className="none" style={{ background: "#fff", borderRadius: 16, border: "1px solid var(--line)" }}>
              Đang tải số liệu…
            </div>
          ) : (
            <>
              {view === "tq" && renderTQ()}
              {view === "dv" && renderDV()}
              {view === "tt" && renderTT()}
              {view === "nk" && renderNK()}
            </>
          )}
        </div>
      </div>
      {renderExportModal()}
    </div>
  );

  // ── MÀN 1 · TỔNG QUAN ───────────────────────────────────────────────────────
  function renderTQ() {
    const total = kpis?.dossiers ?? 0;
    const top = kpis?.topProcedure;
    const selectedName = summary?.selected?.xa || summary?.selected?.name;
    const kpiSpecs: KpiSpec[] = [
      {
        icon: "doc",
        color: "var(--pri)",
        bg: "var(--pri-bg)",
        label: "Tổng hồ sơ tiếp nhận",
        value: fmt(total),
        foot: (
          <>
            Qua Trợ lý trong kỳ · phạm vi{" "}
            <b>{selectedName ? selectedName : canViewUnits ? "toàn tỉnh" : acctName}</b>
          </>
        ),
      },
      {
        icon: "list",
        color: "var(--amb)",
        bg: "var(--amb-bg)",
        label: "Loại thủ tục phát sinh",
        value: fmt(kpis?.procedureTypes ?? 0),
        foot: <>Số thủ tục có ít nhất một hồ sơ trong kỳ</>,
      },
      {
        icon: "cup",
        color: "var(--grn)",
        bg: "var(--grn-bg)",
        label: "Thủ tục nhiều hồ sơ nhất",
        value: top ? fmt(top.count) : "—",
        foot: top ? <b title={top.label}>{trim(top.label, 58)}</b> : <>Chưa có hồ sơ</>,
      },
      canViewUnits && !summary?.selected
        ? {
            icon: "bank",
            color: "var(--vio)",
            bg: "var(--vio-bg)",
            label: "Đơn vị có phát sinh",
            value: fmt(unitsWithData),
            vs: `/${scope?.unitCount ?? 0}`,
            foot: (
              <>
                Bình quân <b>{fmt(unitsWithData ? Math.round(scopeTotal / unitsWithData) : 0)}</b> hồ sơ mỗi đơn vị
              </>
            ),
          }
        : {
            icon: "cal",
            color: "var(--tea)",
            bg: "var(--tea-bg)",
            label: "Số ngày có hồ sơ",
            value: fmt(byDay.filter((d) => d.count > 0).length),
            vs: "ngày",
            foot: <>Trong khoảng thời gian đang chọn</>,
          },
    ];

    const rankRows = byProc.slice(0, 7);
    const mx = Math.max(...rankRows.map((p) => p.count), 1);

    return (
      <>
        <div className="kpis">
          {kpiSpecs.map((s, i) => (
            <Kpi key={i} spec={s} />
          ))}
        </div>
        <div className="bento">
          <div className="stack">
            <Card
              title="Diễn biến hồ sơ tiếp nhận theo ngày"
              sub="Số hồ sơ phát sinh mỗi ngày · cột xám là cuối tuần"
              right={
                byDay.length ? (
                  <span className="tagp b">Cao nhất {fmt(Math.max(...byDay.map((d) => d.count)))} hồ sơ/ngày</span>
                ) : undefined
              }
            >
              {byDay.length ? <BarDays data={byDay} /> : <div className="none">Chưa đủ dữ liệu theo ngày.</div>}
            </Card>

            <Card
              title="Thủ tục phát sinh nhiều hồ sơ nhất"
              sub={`Top ${rankRows.length} trên tổng ${byProc.length} thủ tục trong phạm vi`}
              right={
                <button className="btn" style={{ height: 34, fontSize: 12.5 }} onClick={() => setView("tt")}>
                  Xem tất cả
                </button>
              }
            >
              <div className="rank">
                {rankRows.length ? (
                  rankRows.map((p, i) => (
                    <div
                      className="rk"
                      key={p.key}
                      style={{ ["--nc" as string]: PAL[i % PAL.length], ["--nb" as string]: PALBG[i % PALBG.length] } as CSSProperties}
                    >
                      <span className="no">{i + 1}</span>
                      <span className="tx">
                        <span className="t1" title={p.label}>
                          {p.label}
                        </span>
                        <span className="t2">{pct(p.count, total)}% tổng hồ sơ trong kỳ</span>
                      </span>
                      <span className="bar">
                        <i style={{ width: `${(p.count / mx) * 100}%`, background: PAL[i % PAL.length] }} />
                      </span>
                      <span className="mt">
                        <div className="mv num" style={{ color: PAL[i % PAL.length] }}>
                          {fmt(p.count)}
                        </div>
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="none">Chưa có hồ sơ nào trong kỳ.</div>
                )}
              </div>
            </Card>
          </div>

          <div className="stack">
            <Card title="Ngày cao điểm trong tuần" sub="Tổng hồ sơ cộng dồn theo thứ">
              {byDay.length ? <WeekColumns data={byDay} /> : <div className="none">Chưa đủ dữ liệu.</div>}
            </Card>
            <Card title="Cơ cấu theo thủ tục" sub="Tỷ trọng hồ sơ của các thủ tục cao nhất">
              {slices.length ? (
                <DonutMini slices={slices} total={total} procTypes={kpis?.procedureTypes ?? 0} />
              ) : (
                <div className="none">Chưa có hồ sơ.</div>
              )}
            </Card>
          </div>
        </div>
      </>
    );
  }

  // ── MÀN 2 · THEO ĐƠN VỊ ─────────────────────────────────────────────────────
  function renderDV() {
    if (!canViewUnits) {
      // HCC xã/tỉnh: "Theo đơn vị" chính là 1 đơn vị — của mình.
      const total = kpis?.dossiers ?? 0;
      const top = kpis?.topProcedure;
      const selfKpis: KpiSpec[] = [
        {
          icon: "doc",
          color: "var(--pri)",
          bg: "var(--pri-bg)",
          label: "Hồ sơ của đơn vị",
          value: fmt(total),
          foot: (
            <>
              Trong kỳ · <b>{acctName}</b>
            </>
          ),
        },
        {
          icon: "list",
          color: "var(--amb)",
          bg: "var(--amb-bg)",
          label: "Loại thủ tục phát sinh",
          value: fmt(kpis?.procedureTypes ?? 0),
          foot: <>Số thủ tục có hồ sơ trong kỳ</>,
        },
        {
          icon: "cup",
          color: "var(--grn)",
          bg: "var(--grn-bg)",
          label: "Thủ tục nhiều hồ sơ nhất",
          value: top ? fmt(top.count) : "—",
          foot: top ? <b title={top.label}>{trim(top.label, 56)}</b> : <>Chưa có hồ sơ</>,
        },
        {
          icon: "cal",
          color: "var(--tea)",
          bg: "var(--tea-bg)",
          label: "Số ngày có hồ sơ",
          value: fmt(byDay.filter((d) => d.count > 0).length),
          vs: "ngày",
          foot: <>Trong khoảng thời gian đang chọn</>,
        },
      ];
      return (
        <>
          <div className="kpis">
            {selfKpis.map((s, i) => (
              <Kpi key={i} spec={s} />
            ))}
          </div>
          <Card title="Số liệu đơn vị của bạn" sub={`${unitLevel(scope?.self.xa).label} · ${provinceName}`}>
            {dvTable()}
          </Card>
        </>
      );
    }

    const ranked = [...units].sort((a, b) => b.dossiers - a.dossiers);
    const best = ranked[0];
    const mx = best?.dossiers || 1;
    const avg = scope?.unitCount ? Math.round(scopeTotal / scope.unitCount) : 0;

    const kpiSpecs: KpiSpec[] = [
      {
        icon: "bank",
        color: "var(--pri)",
        bg: "var(--pri-bg)",
        label: "Đơn vị trong phạm vi",
        value: fmt(scope?.unitCount ?? 0),
        foot: (
          <>
            <b>{fmt(unitsWithData)}</b> đơn vị có phát sinh hồ sơ trong kỳ
          </>
        ),
      },
      {
        icon: "cup",
        color: "var(--grn)",
        bg: "var(--grn-bg)",
        label: "Đơn vị dẫn đầu",
        value: best ? fmt(best.dossiers) : "—",
        foot: best ? <b>{best.xa || best.name}</b> : <>Chưa có dữ liệu</>,
      },
      {
        icon: "doc",
        color: "var(--amb)",
        bg: "var(--amb-bg)",
        label: "Bình quân mỗi đơn vị",
        value: fmt(avg),
        foot: <>Trên tổng {fmt(scope?.unitCount ?? 0)} đơn vị trong phạm vi</>,
      },
      {
        icon: "grid",
        color: "var(--vio)",
        bg: "var(--vio-bg)",
        label: "Tổng hồ sơ toàn tỉnh",
        value: fmt(scopeTotal),
        foot: <>Cộng dồn tất cả đơn vị trong kỳ</>,
      },
    ];

    return (
      <>
        <div className="kpis">
          {kpiSpecs.map((s, i) => (
            <Kpi key={i} spec={s} />
          ))}
        </div>
        <Card
          title="Xếp hạng đơn vị theo số hồ sơ"
          sub={`${scope?.unitCount ?? 0} đơn vị · tổng ${fmt(scopeTotal)} hồ sơ trong kỳ`}
        >
          <div className="rank">
            {ranked.filter((u) => u.dossiers > 0).length ? (
              ranked
                .filter((u) => u.dossiers > 0)
                .map((u, i) => {
                  const c = i < 3 ? PAL[i] : `hsl(214 ${58 - i * 3}% ${44 + i * 3}%)`;
                  const isMe = u.unitId === scope?.self.unitId;
                  return (
                    <div
                      className="rk"
                      key={u.unitId}
                      style={{ ["--nc" as string]: c, ["--nb" as string]: i < 3 ? PALBG[i] : "var(--pri-bg)" } as CSSProperties}
                    >
                      <span className="no">{i + 1}</span>
                      <span className="tx">
                        <span className="t1">
                          {u.xa || u.name}
                          {isMe && <em> · đơn vị của bạn</em>}
                        </span>
                        <span className="t2">{unitLevel(u.xa).label} · {fmt(u.procedureTypes)} loại thủ tục</span>
                      </span>
                      <span className="bar" style={{ width: 190 }}>
                        <i style={{ width: `${(u.dossiers / mx) * 100}%`, background: c }} />
                      </span>
                      <span className="mt">
                        <div className="mv num" style={{ color: c }}>
                          {fmt(u.dossiers)}
                        </div>
                      </span>
                    </div>
                  );
                })
            ) : (
              <div className="none">Chưa có đơn vị nào phát sinh hồ sơ trong kỳ.</div>
            )}
          </div>
        </Card>
        <div style={{ height: 16 }} />
        <Card
          title="Bảng số liệu chi tiết theo đơn vị"
          sub="Bấm tiêu đề cột để sắp xếp"
          right={
            <input
              className="ctl"
              placeholder="Tìm đơn vị…"
              style={{ height: 34, fontSize: 12.5, minWidth: 190, fontWeight: 500 }}
              value={qUnit}
              onChange={(e) => setQUnit(e.target.value)}
            />
          }
        >
          {dvTable()}
        </Card>
      </>
    );
  }

  function dvSort(k: "name" | "dossiers" | "procedureTypes") {
    setSortDv((s) => (s.k === k ? { k, d: (s.d * -1) as 1 | -1 } : { k, d: -1 }));
  }

  function dvTable() {
    const meId = scope?.self.unitId;
    let rows = units.map((u) => ({ ...u, name: u.xa || u.name || "" }));
    const all = rows.length;
    const q = qUnit.trim().toLowerCase();
    if (q) rows = rows.filter((r) => (r.name || "").toLowerCase().includes(q));
    rows = [...rows].sort((a, b) => {
      const k = sortDv.k;
      const av = k === "name" ? (a.name || "") : (a as any)[k];
      const bv = k === "name" ? (b.name || "") : (b as any)[k];
      const cmp = typeof av === "string" ? av.localeCompare(bv as string, "vi") : (av as number) - (bv as number);
      return cmp * sortDv.d;
    });
    const arrow = (k: string) => (sortDv.k === k ? (sortDv.d < 0 ? "↓" : "↑") : "↕");
    const th = (k: "name" | "dossiers" | "procedureTypes", label: string, cls?: string) => (
      <th className={`${cls || ""} s ${sortDv.k === k ? "on" : ""}`} onClick={() => dvSort(k)}>
        {label}
        <span className="ar">{arrow(k)}</span>
      </th>
    );
    return (
      <>
        <div className="tw">
          <table>
            <thead>
              <tr>
                <th className="c" style={{ width: 46 }}>TT</th>
                {th("name", "Đơn vị")}
                <th className="c">Cấp</th>
                {th("dossiers", "Hồ sơ", "r")}
                {th("procedureTypes", "Loại thủ tục", "r")}
                <th>Thủ tục nhiều nhất</th>
              </tr>
            </thead>
            <tbody>
              {rows.length ? (
                rows.map((u, i) => {
                  const lv = unitLevel(u.xa);
                  return (
                    <tr key={u.unitId} className={u.unitId === meId ? "mine" : ""}>
                      <td className="c">
                        <span className="rkn">{i + 1}</span>
                      </td>
                      <td>
                        <div className="uname">
                          <span>{u.name}</span>
                          {u.unitId === meId && <em>Đơn vị của bạn</em>}
                        </div>
                      </td>
                      <td className="c">
                        <span className={`kind ${lv.cls}`}>{lv.label}</span>
                      </td>
                      <td className="r n num">{fmt(u.dossiers)}</td>
                      <td className="r num">{fmt(u.procedureTypes)}</td>
                      <td>
                        <span className="tnm" title={u.topProcedure?.label || ""}>
                          {u.topProcedure ? `${trim(u.topProcedure.label, 46)} · ${fmt(u.topProcedure.count)}` : "—"}
                        </span>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={6} className="none">
                    Không có đơn vị nào khớp với từ khoá “{qUnit}”.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="tfoot">
          Hiển thị <b>{rows.length}</b>/{all} đơn vị · tổng <b>{fmt(scopeTotal)}</b> hồ sơ
        </div>
      </>
    );
  }

  // ── MÀN 3 · THEO THỦ TỤC ────────────────────────────────────────────────────
  function ttSort(k: "label" | "count" | "units") {
    setSortTt((s) => (s.k === k ? { k, d: (s.d * -1) as 1 | -1 } : { k, d: -1 }));
  }

  function renderTT() {
    const total = kpis?.dossiers ?? 0;
    const top = byProc[0];
    const conc = total ? Math.round((byProc.slice(0, 3).reduce((a, b) => a + b.count, 0) / total) * 100) : 0;
    const kpiSpecs: KpiSpec[] = [
      {
        icon: "list",
        color: "var(--pri)",
        bg: "var(--pri-bg)",
        label: "Thủ tục phát sinh hồ sơ",
        value: fmt(byProc.length),
        foot: <>Số loại thủ tục có hồ sơ trong kỳ</>,
      },
      {
        icon: "cup",
        color: "var(--grn)",
        bg: "var(--grn-bg)",
        label: "Thủ tục nhiều hồ sơ nhất",
        value: top ? fmt(top.count) : "—",
        foot: top ? <b title={top.label}>{trim(top.label, 56)}</b> : <>Chưa có hồ sơ</>,
      },
      {
        icon: "gauge",
        color: "var(--amb)",
        bg: "var(--amb-bg)",
        label: "Mức độ tập trung",
        value: String(conc),
        vs: "%",
        foot: <>3 thủ tục hàng đầu chiếm phần khối lượng này</>,
      },
      {
        icon: "doc",
        color: "var(--vio)",
        bg: "var(--vio-bg)",
        label: "Tổng hồ sơ trong kỳ",
        value: fmt(total),
        foot: <>Cộng dồn mọi thủ tục trong phạm vi đang xem</>,
      },
    ];

    let rows = [...byProc];
    const all = rows.length;
    const q = qProc.trim().toLowerCase();
    if (q) rows = rows.filter((r) => r.label.toLowerCase().includes(q));
    const cidx = new Map(byProc.map((p, i) => [p.key, i]));
    rows.sort((a, b) => {
      const k = sortTt.k;
      const av = k === "label" ? a.label : k === "units" ? a.units ?? 0 : a.count;
      const bv = k === "label" ? b.label : k === "units" ? b.units ?? 0 : b.count;
      const cmp = typeof av === "string" ? av.localeCompare(bv as string, "vi") : (av as number) - (bv as number);
      return cmp * sortTt.d;
    });
    const mx = Math.max(...rows.map((r) => r.count), 1);
    const arrow = (k: string) => (sortTt.k === k ? (sortTt.d < 0 ? "↓" : "↑") : "↕");
    const th = (k: "label" | "count" | "units", label: string, cls?: string) => (
      <th className={`${cls || ""} s ${sortTt.k === k ? "on" : ""}`} onClick={() => ttSort(k)}>
        {label}
        <span className="ar">{arrow(k)}</span>
      </th>
    );
    const showUnitsCol = canViewUnits && !summary?.selected;

    return (
      <>
        <div className="kpis">
          {kpiSpecs.map((s, i) => (
            <Kpi key={i} spec={s} />
          ))}
        </div>
        <Card
          title="Danh mục thủ tục phát sinh hồ sơ"
          sub={`${all} thủ tục · tổng ${fmt(total)} hồ sơ · ${
            summary?.selected ? summary.selected.xa || summary.selected.name : canViewUnits ? `toàn tỉnh (${scope?.unitCount ?? 0} đơn vị)` : acctName
          }`}
          right={
            <input
              className="ctl"
              placeholder="Tìm tên thủ tục…"
              style={{ height: 34, fontSize: 12.5, minWidth: 240, fontWeight: 500 }}
              value={qProc}
              onChange={(e) => setQProc(e.target.value)}
            />
          }
        >
          <div className="tw">
            <table>
              <thead>
                <tr>
                  <th className="c" style={{ width: 56 }}>Hạng</th>
                  {th("label", "Tên thủ tục")}
                  {th("count", "Hồ sơ", "r")}
                  {showUnitsCol && th("units", "Đơn vị phát sinh", "r")}
                  <th style={{ width: 170 }}>Tỷ trọng</th>
                </tr>
              </thead>
              <tbody>
                {rows.length ? (
                  rows.map((r, i) => {
                    const ci = (cidx.get(r.key) ?? i) % PAL.length;
                    return (
                      <tr key={r.key}>
                        <td className="c">
                          <span className="rkn" style={{ background: PALBG[ci], color: PAL[ci] }}>
                            {i + 1}
                          </span>
                        </td>
                        <td>
                          <span className="tnm" title={r.label}>
                            {r.label}
                          </span>
                        </td>
                        <td className="r n num">{fmt(r.count)}</td>
                        {showUnitsCol && (
                          <td className="r num">
                            {fmt(r.units ?? 0)}
                            <span style={{ color: "var(--ink3)" }}>/{scope?.unitCount ?? 0}</span>
                          </td>
                        )}
                        <td>
                          <div className="mbar">
                            <i style={{ width: `${(r.count / mx) * 100}%`, background: PAL[ci] }} />
                          </div>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={showUnitsCol ? 5 : 4} className="none">
                      Không có thủ tục nào khớp với từ khoá “{qProc}”.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="tfoot">
            {q ? (
              <>
                Hiển thị <b>{rows.length}</b>/{all} thủ tục khớp từ khoá
              </>
            ) : (
              <>
                Tổng cộng <b>{all}</b> thủ tục · <b>{fmt(total)}</b> hồ sơ
              </>
            )}
          </div>
        </Card>
      </>
    );
  }

  // ── MÀN 4 · NHẬT KÝ HỒ SƠ ───────────────────────────────────────────────────
  function renderNK() {
    const items = logs?.items ?? [];
    const total = logs?.total ?? 0;
    const pageSize = logs?.pageSize ?? 15;
    const pages = Math.max(1, Math.ceil(total / pageSize));
    return (
      <Card
        title="Nhật ký hồ sơ"
        sub={`${fmt(total)} lượt · mỗi dòng là một lần hồ sơ chạy qua Trợ lý · chỉ hồ sơ Auto Fill`}
      >
        <div className="tw">
          <table>
            <thead>
              <tr>
                <th style={{ width: 150 }}>Mã hồ sơ</th>
                <th style={{ width: 168 }}>Thời gian tiếp nhận</th>
                <th>Đơn vị tiếp nhận</th>
                <th>Thủ tục</th>
                <th className="c" style={{ width: 128 }}>Bước</th>
              </tr>
            </thead>
            <tbody>
              {items.length ? (
                items.map((it, i) => (
                  <tr key={`${it.requestId || "row"}-${i}`}>
                    <td>
                      <span className="sid">{it.requestId || "—"}</span>
                    </td>
                    <td className="num">{fmtDateTime(it.receivedAt)}</td>
                    <td>
                      <span className="tnm" title={it.unitName}>
                        {it.unitName}
                      </span>
                    </td>
                    <td>
                      <span className="tnm" title={it.procedureLabel || ""}>
                        {it.procedureLabel || "—"}
                      </span>
                    </td>
                    <td className="c">
                      <span className={`chip ${it.kind === "attach" ? "help" : "ok"}`}>
                        {it.kind === "attach" ? "Đính kèm" : "Điền form"}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="none">
                    {logsLoading ? "Đang tải nhật ký…" : "Chưa có hồ sơ nào trong kỳ."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="tfoot">
          <span>
            Trang <b>{nkPage}</b>/{pages} · tổng <b>{fmt(total)}</b> lượt
          </span>
          <div className="pager">
            <button disabled={nkPage <= 1} onClick={() => setNkPage((p) => Math.max(1, p - 1))}>
              ‹ Trước
            </button>
            <button className="on">{nkPage}</button>
            <button disabled={nkPage >= pages} onClick={() => setNkPage((p) => p + 1)}>
              Sau ›
            </button>
          </div>
        </div>
      </Card>
    );
  }

  // ── Hộp thoại xác nhận xuất Excel ────────────────────────────────────────────
  function renderExportModal() {
    if (!showExport) return null;
    const selUnit = summary?.selected;
    const rangeLabel =
      preset === "custom"
        ? dateFrom && dateTo
          ? `Từ ${dateFrom} đến ${dateTo}`
          : dateFrom
            ? `Từ ${dateFrom}`
            : dateTo
              ? `Đến ${dateTo}`
              : "Tùy chọn khoảng…"
        : PRESETS.find((p) => p.key === preset)?.label ?? "—";
    const donViXuat = canViewUnits
      ? selUnit
        ? selUnit.xa || selUnit.name || "1 đơn vị"
        : `Tất cả ${scope?.unitCount ?? 0} đơn vị`
      : acctName;
    const phamVi = canViewUnits ? `Toàn tỉnh ${provinceName} — ${scope?.unitCount ?? 0} đơn vị` : acctName;
    const soDong = selUnit ? kpis?.dossiers ?? 0 : scopeTotal;
    const soDonVi = selUnit ? 1 : scope?.unitCount ?? 1;
    const cauTruc = canViewUnits
      ? "4 sheet: Tổng hợp · Theo đơn vị · Theo thủ tục · Nhật ký hồ sơ"
      : "3 sheet: Tổng hợp · Theo thủ tục · Nhật ký hồ sơ";
    return (
      <div
        className="mask on"
        onClick={(e) => {
          if (e.target === e.currentTarget && !exporting) setShowExport(false);
        }}
      >
        <div className="modal" role="dialog" aria-modal="true" aria-label="Xác nhận xuất báo cáo Excel">
          <div className="mh">
            <div className="ic">
              <Ic n="download" />
            </div>
            <div>
              <h3>Xác nhận xuất báo cáo Excel</h3>
              <p>Kiểm tra phạm vi dữ liệu trước khi tải về</p>
            </div>
          </div>
          <div className="mb">
            <dl className="kvlist">
              <dt>Tài khoản</dt>
              <dd>{acctName}</dd>
              <dt>Cấp tài khoản</dt>
              <dd style={{ color: canViewUnits ? "var(--pri)" : "var(--amb)", fontWeight: 700 }}>{roleLabel}</dd>
              <dt>Phạm vi được phép</dt>
              <dd>{phamVi}</dd>
              <dt>Đơn vị xuất</dt>
              <dd>{donViXuat}</dd>
              <dt>Nội dung xuất</dt>
              <dd>Màn hình “{VIEW_META[view].title}”</dd>
              <dt>Kỳ báo cáo</dt>
              <dd>{rangeLabel}</dd>
              <dt>Số dòng dữ liệu</dt>
              <dd>
                {fmt(soDong)} hồ sơ · {fmt(soDonVi)} đơn vị
              </dd>
              <dt>Cấu trúc file</dt>
              <dd>{cauTruc}</dd>
            </dl>
            <div className="mnote">
              <Ic n="info" />
              <span>
                {canViewUnits ? (
                  <>
                    File chỉ chứa dữ liệu của các đơn vị thuộc <b>tỉnh {provinceName}</b>. Hệ thống ghi nhật ký mỗi
                    lượt xuất báo cáo.
                  </>
                ) : (
                  <>
                    File chỉ chứa dữ liệu của <b>đơn vị bạn quản lý</b>. Tài khoản cấp xã/phường không xuất được dữ
                    liệu đơn vị khác.
                  </>
                )}
              </span>
            </div>
          </div>
          <div className="mf">
            <button className="btn" onClick={() => setShowExport(false)} disabled={exporting}>
              Hủy
            </button>
            <button className={`btn btn-pri ${exporting ? "spinning" : ""}`} onClick={handleExport} disabled={exporting}>
              <Ic n="download" /> {exporting ? "Đang tải…" : "Tải file .xlsx"}
            </button>
          </div>
        </div>
      </div>
    );
  }
}

// ── Tiện ích ──────────────────────────────────────────────────────────────────
function trim(s: string, n: number): string {
  return s.length > n ? s.slice(0, n).trimEnd() + "…" : s;
}
function fmtDateTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}
function pct(part: number, whole: number): string {
  if (!whole) return "0";
  return (Math.round((part / whole) * 1000) / 10).toLocaleString("vi-VN");
}

const emblemStyle: CSSProperties = {
  width: 36,
  height: 36,
  borderRadius: 10,
  display: "grid",
  placeItems: "center",
  background: "linear-gradient(140deg,#1256C7,#3B82E8)",
  color: "#fff",
};
const stampStyle: CSSProperties = {
  fontSize: 12,
  color: "var(--ink3)",
  fontWeight: 600,
  whiteSpace: "nowrap",
};
