import { useCallback, useEffect, useState } from "react";
import { getFacets, listTraces } from "../api";
import type { Facets, TraceListItem, User } from "../types";
import { fmtDateTime } from "../format";
import TraceDetailPanel from "../components/TraceDetailPanel";
import TopBar, { type View } from "../components/TopBar";
import Combobox from "../components/Combobox";

const PAGE_SIZE = 20;

interface Filters {
  source: "all" | "autofill" | "handfree";
  userId: string;
  procedure: string;
  dateFrom: string;
  dateTo: string;
  requestId: string;
}

const EMPTY: Filters = {
  source: "all",
  userId: "",
  procedure: "",
  dateFrom: "",
  dateTo: "",
  requestId: "",
};

// Giữ bộ lọc + trang trong sessionStorage để khi xem chi tiết trace rồi bấm Back, danh sách
// không bị reset (state-preservation). sessionStorage: chỉ trong tab, xóa khi đóng tab.
const STORE_KEY = "hcc_traces_view";
function loadPersisted(): { filters?: Filters; page?: number } {
  try {
    return JSON.parse(sessionStorage.getItem(STORE_KEY) || "{}");
  } catch {
    return {};
  }
}

export default function Traces({
  user,
  onLogout,
  view,
  onNavigate,
}: {
  user: User;
  onLogout: () => void;
  view: View;
  onNavigate: (v: View) => void;
}) {
  const [facets, setFacets] = useState<Facets>({ users: [], procedures: [] });
  // Merge với EMPTY: bộ lọc lưu ở phiên bản cũ (chưa có requestId) không làm thiếu khóa → tránh .trim() undefined.
  const [filters, setFilters] = useState<Filters>(() => ({ ...EMPTY, ...(loadPersisted().filters ?? {}) }));
  const [items, setItems] = useState<TraceListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(() => loadPersisted().page ?? 1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    getFacets(filters.source)
      .then(setFacets)
      .catch(() => {});
  }, [filters.source]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await listTraces({
        source: filters.source,
        userId: filters.userId || undefined,
        procedure: filters.procedure || undefined,
        // input type=date trả YYYY-MM-DD; thêm giờ để bao trọn ngày.
        dateFrom: filters.dateFrom ? `${filters.dateFrom}T00:00:00` : undefined,
        dateTo: filters.dateTo ? `${filters.dateTo}T23:59:59` : undefined,
        requestId: filters.requestId?.trim() || undefined,
        page,
        pageSize: PAGE_SIZE,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi tải dữ liệu");
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    sessionStorage.setItem(STORE_KEY, JSON.stringify({ filters, page }));
  }, [filters, page]);

  function update<K extends keyof Filters>(key: K, value: Filters[K]) {
    setPage(1);
    setFilters((f) => ({ ...f, [key]: value }));
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="app">
      <TopBar user={user} view={view} onNavigate={onNavigate} onLogout={onLogout} />

      <section className="filters">
        <label>
          Nguồn
          <select
            value={filters.source}
            onChange={(e) => update("source", e.target.value as Filters["source"])}
          >
            <option value="all">Tất cả</option>
            <option value="autofill">No handfree</option>
            <option value="handfree">Handfree</option>
          </select>
        </label>
        <label className="filter-reqid">
          Mã hỗ trợ
          <input
            type="text"
            value={filters.requestId}
            onChange={(e) => update("requestId", e.target.value)}
            placeholder="Dán mã hỗ trợ để tra nhanh"
            spellCheck={false}
            autoComplete="off"
          />
        </label>
        <Combobox
          label="Phường"
          value={filters.userId}
          onChange={(v) => update("userId", v)}
          options={facets.users.map((u) => ({
            value: u.userId,
            label: u.name || u.username || u.userId,
          }))}
          placeholder="Tìm phường…"
        />
        <Combobox
          label="Thủ tục"
          value={filters.procedure}
          onChange={(v) => update("procedure", v)}
          options={facets.procedures.map((p) => ({ value: p.key, label: p.label || p.key }))}
          placeholder="Tìm thủ tục…"
        />
        <label>
          Từ ngày
          <input
            type="date"
            value={filters.dateFrom}
            onChange={(e) => update("dateFrom", e.target.value)}
          />
        </label>
        <label>
          Đến ngày
          <input
            type="date"
            value={filters.dateTo}
            onChange={(e) => update("dateTo", e.target.value)}
          />
        </label>
        <button className="ghost" onClick={() => { setFilters(EMPTY); setPage(1); }}>
          Xóa lọc
        </button>
      </section>

      {error && <div className="error bar">{error}</div>}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th className="col-time">Thời gian</th>
              <th>Mã hỗ trợ</th>
              <th>Phường</th>
              <th>Thủ tục</th>
              <th>Loại</th>
              <th>Thao tác</th>
              <th>Người làm thủ tục</th>
              <th className="num">Số file</th>
            </tr>
          </thead>
          <tbody>
            {items.map((t) => (
              <tr key={t.id} className="row" onClick={() => setSelected(t.id)}>
                <td className="col-time">{fmtDateTime(t.created_at)}</td>
                <td className="col-reqid" title={t.request_id}>{t.request_id || "—"}</td>
                <td>{t.name || "—"}</td>
                <td>{t.procedure_label || t.procedure}</td>
                <td>
                  <span className={`badge source-${t.experience || "autofill"}`}>
                    {t.experience === "handfree" ? "Handfree" : "No handfree"}
                  </span>
                </td>
                <td>
                  <span className={`badge ${t.kind === "attach" ? "warn" : "ok"}`}>
                    {t.kind === "attach" ? "Đính kèm" : "Auto-fill"}
                  </span>
                </td>
                <td>{t.applicant_name || "—"}</td>
                <td className="num">{t.attachments?.length ?? 0}</td>
              </tr>
            ))}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={8} className="muted center">
                  Không có dữ liệu
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="pager">
        <span className="muted">
          {total} bản ghi · trang {page}/{totalPages}
        </span>
        <div>
          <button className="ghost" disabled={page <= 1 || loading} onClick={() => setPage((p) => p - 1)}>
            ‹ Trước
          </button>
          <button
            className="ghost"
            disabled={page >= totalPages || loading}
            onClick={() => setPage((p) => p + 1)}
          >
            Sau ›
          </button>
        </div>
      </div>

      {selected && <TraceDetailPanel id={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
