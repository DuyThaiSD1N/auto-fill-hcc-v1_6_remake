import { useCallback, useEffect, useState } from "react";
import { getFacets, listDossiers } from "../api";
import type { DossierListItem, Facets, User } from "../types";
import { fmtDateTime, fmtDuration } from "../format";
import DossierDetailPanel from "../components/DossierDetailPanel";
import TopBar, { type View } from "../components/TopBar";
import Combobox from "../components/Combobox";
import { RatingCell } from "../rating";

const PAGE_SIZE = 20;

interface Filters {
  source: "all" | "autofill" | "handfree";
  status: "all" | "submitted" | "unsubmitted";
  userId: string;
  procedure: string;
  dateFrom: string;
  dateTo: string;
}

const EMPTY: Filters = {
  source: "all",
  status: "all",
  userId: "",
  procedure: "",
  dateFrom: "",
  dateTo: "",
};

// Giữ bộ lọc + trang trong sessionStorage như trang Nhật ký: mở chi tiết rồi quay lại không
// bị reset. sessionStorage → chỉ trong tab, đóng tab là hết.
const STORE_KEY = "hcc_dossiers_view";
function loadPersisted(): { filters?: Filters; page?: number } {
  try {
    return JSON.parse(sessionStorage.getItem(STORE_KEY) || "{}");
  } catch {
    return {};
  }
}

export default function Dossiers({
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
  const [filters, setFilters] = useState<Filters>(() => ({ ...EMPTY, ...(loadPersisted().filters ?? {}) }));
  const [items, setItems] = useState<DossierListItem[]>([]);
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
      const res = await listDossiers({
        source: filters.source,
        status: filters.status,
        userId: filters.userId || undefined,
        procedure: filters.procedure || undefined,
        dateFrom: filters.dateFrom || undefined,
        dateTo: filters.dateTo || undefined,
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
  // Số hồ sơ trên cổng ≠ số dòng: chứng thực tách nhiều tab là một dòng nhưng nhiều lần nộp.
  const submittedOnPage = items.reduce((s, d) => s + (d.submitCount || 0), 0);

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
        <label>
          Trạng thái
          <select
            value={filters.status}
            onChange={(e) => update("status", e.target.value as Filters["status"])}
          >
            <option value="all">Tất cả</option>
            {/* "Đã hoàn thành" = đã bấm nộp, đúng tập mà Thống kê đếm từ 14/9/2026 — gọi
                đúng một tên ở cả hai màn để cán bộ đối chiếu được con số. */}
            <option value="submitted">Đã hoàn thành (đã nộp)</option>
            <option value="unsubmitted">Làm dở (chưa nộp)</option>
          </select>
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
          <input type="date" value={filters.dateFrom} onChange={(e) => update("dateFrom", e.target.value)} />
        </label>
        <label>
          Đến ngày
          <input type="date" value={filters.dateTo} onChange={(e) => update("dateTo", e.target.value)} />
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
              <th className="col-time">Bắt đầu</th>
              <th className="col-time">Nộp lần cuối</th>
              <th>Thời gian làm</th>
              <th>Phường</th>
              <th>Thủ tục</th>
              <th>Người làm thủ tục</th>
              <th>Loại</th>
              <th className="num">Lần nộp</th>
              <th>Đánh giá</th>
            </tr>
          </thead>
          <tbody>
            {items.map((d) => (
              <tr key={d.id} className="row" onClick={() => setSelected(d.id)}>
                <td className="col-time">{fmtDateTime(d.startedAt)}</td>
                <td className="col-time">
                  {d.submittedAt ? fmtDateTime(d.submittedAt) : <span className="muted">chưa nộp</span>}
                </td>
                <td>{fmtDuration(d.durationMs)}</td>
                <td>{d.name || "—"}</td>
                <td>{d.procedureLabel || d.procedure || "—"}</td>
                <td>{d.applicantName || "—"}</td>
                <td>
                  <span className={`badge source-${d.experience || "autofill"}`}>
                    {d.experience === "handfree" ? "Handfree" : "No handfree"}
                  </span>
                </td>
                <td className="num">
                  {d.submitCount ? d.submitCount : <span className="muted">0</span>}
                </td>
                <td><RatingCell rating={d.rating} /></td>
              </tr>
            ))}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={9} className="muted center">
                  Không có dữ liệu
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="pager">
        <span className="muted">
          {total} hồ sơ · {submittedOnPage} lần nộp trong trang · trang {page}/{totalPages}
        </span>
        <div>
          <button className="ghost" disabled={page <= 1 || loading} onClick={() => setPage((p) => p - 1)}>
            ‹ Trước
          </button>
          <button className="ghost" disabled={page >= totalPages || loading} onClick={() => setPage((p) => p + 1)}>
            Sau ›
          </button>
        </div>
      </div>

      {selected && <DossierDetailPanel id={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
