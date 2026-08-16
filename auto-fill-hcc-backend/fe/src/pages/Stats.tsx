import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getStats } from "../api";
import type { Role, StatsResp, StatsScope, StatsWard, User } from "../types";
import TopBar, { type View } from "../components/TopBar";

type Preset = "all" | "today" | "7" | "30" | "custom";
type AnalysisTab = "procedure" | "account";
type AccountRoleFilter = "all" | Role | "unknown";

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
const SCOPES: { key: StatsScope; label: string }[] = [
  { key: "official", label: "Hồ sơ thực tế" },
  { key: "all", label: "Tất cả hồ sơ" },
];
const ANALYSIS_TABS: { key: AnalysisTab; label: string }[] = [
  { key: "procedure", label: "Theo thủ tục" },
  { key: "account", label: "Theo tài khoản" },
];
const ROLE_META: Record<Role, { label: string; cls: string }> = {
  admin: { label: "Quản trị", cls: "role-admin" },
  user: { label: "Người dùng", cls: "role-user" },
  commune: { label: "HCC xã", cls: "role-commune" },
  province: { label: "HCC tỉnh", cls: "role-province" },
};
const ACCOUNT_ROLE_OPTIONS: Record<StatsScope, { key: AccountRoleFilter; label: string }[]> = {
  official: [
    { key: "all", label: "Tất cả vai trò HCC" },
    { key: "commune", label: "HCC xã" },
    { key: "province", label: "HCC tỉnh" },
  ],
  all: [
    { key: "all", label: "Tất cả vai trò" },
    { key: "admin", label: "Quản trị" },
    { key: "user", label: "Người dùng" },
    { key: "commune", label: "HCC xã" },
    { key: "province", label: "HCC tỉnh" },
    { key: "unknown", label: "Không xác định" },
  ],
};
const PROCEDURE_PAGE_SIZE = 20;

const vietnamDay = (d: Date): string => {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Ho_Chi_Minh",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(d);
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${value.year}-${value.month}-${value.day}`;
};

const shiftDay = (iso: string, days: number): string => {
  const [year, month, day] = iso.split("-").map(Number);
  const value = new Date(Date.UTC(year, month - 1, day));
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
};
const fmtNum = (n: number) => n.toLocaleString("vi-VN");

function paginationTokens(page: number, totalPages: number): Array<number | string> {
  if (totalPages <= 7) return Array.from({ length: totalPages }, (_, index) => index + 1);
  const pages = [...new Set([1, totalPages, page - 1, page, page + 1])]
    .filter((value) => value >= 1 && value <= totalPages)
    .sort((a, b) => a - b);
  const tokens: Array<number | string> = [];
  pages.forEach((value, index) => {
    if (index > 0 && value - pages[index - 1] > 1) tokens.push(`gap-${pages[index - 1]}-${value}`);
    tokens.push(value);
  });
  return tokens;
}

interface ProcedurePagerProps {
  page: number;
  totalPages: number;
  totalItems: number;
  from: number;
  to: number;
  onChange: (page: number) => void;
}

function ProcedurePager({ page, totalPages, totalItems, from, to, onChange }: ProcedurePagerProps) {
  return (
    <nav className="stats-pagination" aria-label="Phân trang thủ tục">
      <span className="pagination-summary">{from}–{to} / {fmtNum(totalItems)} thủ tục</span>
      <div className="pagination-buttons">
        <button
          type="button"
          className="stats-page-btn page-direction"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          aria-label="Trang thủ tục trước"
        >
          ‹ <span>Trước</span>
        </button>
        <span className="mobile-page-summary">Trang {page}/{totalPages}</span>
        <div className="page-numbers" aria-label={`Trang ${page} trên ${totalPages}`}>
          {paginationTokens(page, totalPages).map((token) =>
            typeof token === "number" ? (
              <button
                type="button"
                key={token}
                className={`stats-page-btn page-number ${token === page ? "active" : ""}`}
                aria-current={token === page ? "page" : undefined}
                aria-label={`Trang ${token}`}
                onClick={() => onChange(token)}
              >
                {token}
              </button>
            ) : (
              <span className="page-gap" key={token} aria-hidden="true">…</span>
            ),
          )}
        </div>
        <button
          type="button"
          className="stats-page-btn page-direction"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
          aria-label="Trang thủ tục sau"
        >
          <span>Sau</span> ›
        </button>
      </div>
    </nav>
  );
}

function presetRange(preset: Preset): { from?: string; to?: string } {
  if (preset === "all" || preset === "custom") return {};
  const today = vietnamDay(new Date());
  if (preset === "today") return { from: today, to: today };
  const back = preset === "7" ? 6 : 29;
  return { from: shiftDay(today, -back), to: today };
}

export default function Stats({ user, onLogout, view, onNavigate }: Props) {
  const [scope, setScope] = useState<StatsScope>("official");
  const [preset, setPreset] = useState<Preset>("all");
  const [analysisTab, setAnalysisTab] = useState<AnalysisTab>("procedure");
  const [procedurePage, setProcedurePage] = useState(1);
  const [accountRoleFilter, setAccountRoleFilter] = useState<AccountRoleFilter>("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [data, setData] = useState<StatsResp | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [openWards, setOpenWards] = useState<Set<string>>(new Set());
  const controllerRef = useRef<AbortController | null>(null);
  const requestSequenceRef = useRef(0);
  const analysisTabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const procedurePanelRef = useRef<HTMLElement | null>(null);

  const range = useMemo(() => {
    if (preset === "custom") return { from: dateFrom || undefined, to: dateTo || undefined };
    return presetRange(preset);
  }, [preset, dateFrom, dateTo]);

  const load = useCallback(async () => {
    if (range.from && range.to && range.from > range.to) {
      controllerRef.current?.abort();
      requestSequenceRef.current += 1;
      setLoading(false);
      setError("Từ ngày phải nhỏ hơn hoặc bằng đến ngày.");
      return;
    }
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    const sequence = ++requestSequenceRef.current;
    setLoading(true);
    setError("");
    setData(null);
    try {
      // Gửi ngày thuần; BE đổi sang [00:00 ngày đầu, 00:00 ngày kế tiếp) theo giờ Việt Nam.
      const res = await getStats(scope, range.from, range.to, controller.signal);
      if (sequence !== requestSequenceRef.current) return;
      setData(res);
    } catch (e) {
      if (controller.signal.aborted || sequence !== requestSequenceRef.current) return;
      setError(e instanceof Error ? e.message : "Lỗi tải dữ liệu");
    } finally {
      if (sequence === requestSequenceRef.current) setLoading(false);
    }
  }, [range, scope]);

  useEffect(() => {
    load();
    return () => controllerRef.current?.abort();
  }, [load]);

  useEffect(() => {
    setProcedurePage(1);
  }, [scope, preset, dateFrom, dateTo]);

  useEffect(() => {
    setAccountRoleFilter("all");
  }, [scope]);

  function toggleWard(id: string) {
    setOpenWards((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function moveAnalysisTab(event: React.KeyboardEvent<HTMLButtonElement>, index: number) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    let nextIndex = index;
    if (event.key === "ArrowLeft") nextIndex = (index - 1 + ANALYSIS_TABS.length) % ANALYSIS_TABS.length;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % ANALYSIS_TABS.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = ANALYSIS_TABS.length - 1;
    setAnalysisTab(ANALYSIS_TABS[nextIndex].key);
    analysisTabRefs.current[nextIndex]?.focus();
  }

  const procs = data?.procedures ?? [];
  const wards = data?.wards ?? [];
  const totalProcedurePages = Math.max(1, Math.ceil(procs.length / PROCEDURE_PAGE_SIZE));
  const procedurePageStart = procs.length ? (procedurePage - 1) * PROCEDURE_PAGE_SIZE + 1 : 0;
  const procedurePageEnd = Math.min(procedurePage * PROCEDURE_PAGE_SIZE, procs.length);
  const pagedProcs = procs.slice(procedurePageStart ? procedurePageStart - 1 : 0, procedurePageEnd);
  const filteredWards = useMemo(() => {
    if (accountRoleFilter === "all") return wards;
    if (accountRoleFilter === "unknown") return wards.filter((ward) => !ward.role);
    return wards.filter((ward) => ward.role === accountRoleFilter);
  }, [wards, accountRoleFilter]);
  const maxProc = procs[0]?.count ?? 0;
  const maxWard = filteredWards[0]?.total ?? 0;

  useEffect(() => {
    setProcedurePage((current) => Math.min(current, totalProcedurePages));
  }, [totalProcedurePages]);

  function changeProcedurePage(nextPage: number) {
    const safePage = Math.min(Math.max(nextPage, 1), totalProcedurePages);
    setProcedurePage(safePage);
    window.requestAnimationFrame(() => {
      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      procedurePanelRef.current?.scrollIntoView({
        behavior: reduceMotion ? "auto" : "smooth",
        block: "start",
      });
    });
  }

  return (
    <div className="app">
      <TopBar user={user} view={view} onNavigate={onNavigate} onLogout={onLogout} />

      <div className="stats-head">
        <div>
          <h1 className="page-title">Thống kê hồ sơ</h1>
          <p className="muted page-sub">Số hồ sơ riêng biệt theo tài khoản và thủ tục</p>
        </div>
      </div>

      <section className="stats-toolbar" aria-label="Bộ lọc thống kê">
        <div className="stats-filter-group">
          <span className="filter-label" id="stats-scope-label">Phạm vi số liệu</span>
          <div className="seg scope-seg" role="radiogroup" aria-labelledby="stats-scope-label">
            {SCOPES.map((item) => (
              <button
                key={item.key}
                type="button"
                role="radio"
                aria-checked={scope === item.key}
                className={`seg-btn ${scope === item.key ? "active" : ""}`}
                onClick={() => setScope(item.key)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <span className="scope-helper">
            {scope === "official"
              ? `Tài khoản HCC xã và tỉnh${data ? ` · ${fmtNum(data.accountCount)} tài khoản được tính` : ""}.`
              : "Bao gồm mọi loại tài khoản và dữ liệu lịch sử."}
          </span>
        </div>

        <div className="stats-filter-group time-filter">
          <span className="filter-label" id="stats-time-label">Thời gian</span>
          <div className="seg" role="radiogroup" aria-labelledby="stats-time-label">
            {PRESETS.map((p) => (
              <button
                key={p.key}
                type="button"
                role="radio"
                aria-checked={preset === p.key}
                className={`seg-btn ${preset === p.key ? "active" : ""}`}
                onClick={() => setPreset(p.key)}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </section>

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

      <section className="kpi-grid" aria-busy={loading}>
        <div className="kpi-card accent-primary">
          <span className="kpi-label">{scope === "official" ? "Hồ sơ thực tế" : "Tổng hồ sơ"}</span>
          <span className="kpi-num">{data ? fmtNum(data.totalDossiers) : "—"}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">
            {scope === "official" ? "Đơn vị có hồ sơ" : "Tài khoản có hồ sơ"}
          </span>
          <span className="kpi-num">{data ? fmtNum(wards.length) : "—"}</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-label">Loại thủ tục</span>
          <span className="kpi-num">{data ? fmtNum(procs.length) : "—"}</span>
        </div>
      </section>

      <div className="analysis-tabs" role="tablist" aria-label="Chiều phân tích">
        {ANALYSIS_TABS.map((tab, index) => (
          <button
            key={tab.key}
            ref={(element) => { analysisTabRefs.current[index] = element; }}
            id={`stats-tab-${tab.key}`}
            type="button"
            role="tab"
            tabIndex={analysisTab === tab.key ? 0 : -1}
            aria-selected={analysisTab === tab.key}
            aria-controls={`stats-panel-${tab.key}`}
            className={`analysis-tab ${analysisTab === tab.key ? "active" : ""}`}
            onClick={() => setAnalysisTab(tab.key)}
            onKeyDown={(event) => moveAnalysisTab(event, index)}
          >
            {tab.label}
            <span className="tab-count">{tab.key === "procedure" ? procs.length : wards.length}</span>
          </button>
        ))}
      </div>

      {analysisTab === "procedure" && (
        <section
          ref={procedurePanelRef}
          className="panel analysis-panel"
          role="tabpanel"
          id="stats-panel-procedure"
          aria-labelledby="stats-tab-procedure"
          aria-busy={loading}
        >
          <div className="panel-head">
            <div className="panel-title-group">
              <h2>Theo thủ tục</h2>
              <span className="muted">{procs.length} loại</span>
            </div>
            {procs.length > PROCEDURE_PAGE_SIZE && (
              <ProcedurePager
                page={procedurePage}
                totalPages={totalProcedurePages}
                totalItems={procs.length}
                from={procedurePageStart}
                to={procedurePageEnd}
                onChange={changeProcedurePage}
              />
            )}
          </div>
          <div className="metric-list-head procedure-metrics" aria-hidden="true">
            <span>Thủ tục</span><span></span><span>Hồ sơ</span>
          </div>
          <div className={`bar-list ${loading ? "is-loading" : ""}`}>
            {loading && Array.from({ length: 5 }, (_, index) => (
              <span className="stats-skeleton-row" key={`procedure-loading-${index}`} />
            ))}
            {pagedProcs.map((p) => (
              <div className="procedure-row procedure-metrics" key={p.key}>
                <span className="procedure-label" title={p.label}>
                  {p.label}
                </span>
                <span className="bar-track">
                  <span
                    className="bar-fill"
                    style={{ width: `${maxProc ? (p.count / maxProc) * 100 : 0}%` }}
                  />
                </span>
                <span className="bar-val metric-value">{fmtNum(p.count)}</span>
              </div>
            ))}
            {!loading && procs.length === 0 && <p className="empty">Chưa có hồ sơ nào</p>}
          </div>
          {procs.length > PROCEDURE_PAGE_SIZE && (
            <div className="panel-pagination-footer">
              <ProcedurePager
                page={procedurePage}
                totalPages={totalProcedurePages}
                totalItems={procs.length}
                from={procedurePageStart}
                to={procedurePageEnd}
                onChange={changeProcedurePage}
              />
            </div>
          )}
        </section>
      )}

      {analysisTab === "account" && (
        <section
          className="panel analysis-panel"
          role="tabpanel"
          id="stats-panel-account"
          aria-labelledby="stats-tab-account"
          aria-busy={loading}
        >
          <div className="panel-head">
            <div className="panel-title-group">
              <h2>{scope === "official" ? "Theo đơn vị HCC" : "Theo tài khoản"}</h2>
              <span className="muted">
                {filteredWards.length === wards.length
                  ? `${wards.length} tài khoản`
                  : `${filteredWards.length} / ${wards.length} tài khoản`}
              </span>
            </div>
            <label className="account-role-filter">
              <span>Vai trò tài khoản</span>
              <select
                value={accountRoleFilter}
                onChange={(event) => setAccountRoleFilter(event.target.value as AccountRoleFilter)}
              >
                {ACCOUNT_ROLE_OPTIONS[scope].map((option) => (
                  <option value={option.key} key={option.key}>{option.label}</option>
                ))}
              </select>
            </label>
          </div>
          <div className={`bar-list ${loading ? "is-loading" : ""}`}>
            {loading && Array.from({ length: 5 }, (_, index) => (
              <span className="stats-skeleton-row" key={`account-loading-${index}`} />
            ))}
            {filteredWards.map((w: StatsWard) => {
              const open = openWards.has(w.userId);
              const roleMeta = w.role ? ROLE_META[w.role] : null;
              return (
                <div className={`ward-item ${open ? "open" : ""}`} key={w.userId}>
                  <button className="ward-head" onClick={() => toggleWard(w.userId)} aria-expanded={open}>
                    <svg className="chev" viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">
                      <path d="M7 5l6 5-6 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span className="account-identity" title={w.name}>
                      <span className="account-name">{w.name}</span>
                      <span className={`badge compact ${roleMeta?.cls ?? "role-unknown"}`}>
                        {roleMeta?.label ?? "Không xác định"}
                      </span>
                    </span>
                    <span className="bar-track">
                      <span
                        className="bar-fill ward"
                        style={{ width: `${maxWard ? (w.total / maxWard) * 100 : 0}%` }}
                      />
                    </span>
                    <span className="bar-val" aria-label={`${fmtNum(w.total)} hồ sơ`}>
                      {fmtNum(w.total)} <span className="metric-unit">hồ sơ</span>
                    </span>
                  </button>
                  {open && (
                    <div className="ward-detail">
                      {w.procedures.map((p) => (
                        <div className="detail-row" key={p.key}>
                          <span className="detail-label" title={p.label}>
                            {p.label}
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
            {!loading && filteredWards.length === 0 && (
              <p className="empty">
                {wards.length === 0
                  ? "Chưa có hồ sơ nào"
                  : "Không có tài khoản thuộc vai trò này trong phạm vi đã chọn"}
              </p>
            )}
          </div>
        </section>
      )}

      <p className="stat-note muted">
        <strong>Cách tính:</strong> các bản ghi cùng tài khoản và thủ tục có bộ tài liệu trùng nhau,
        hoặc một bộ là tập con của bộ kia, được tính là cùng một hồ sơ. Mỗi tab được tách vẫn tính thành một hồ sơ riêng.
      </p>
    </div>
  );
}
