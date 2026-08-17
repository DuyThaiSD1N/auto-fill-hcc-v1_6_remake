import { useCallback, useEffect, useState } from "react";
import { fetchConsentPdf, listConsents } from "../api";
import type { ConsentListItem, User } from "../types";
import { fmtDateTime } from "../format";
import TopBar, { type View } from "../components/TopBar";

interface Props {
  user: User;
  onLogout: () => void;
  view: View;
  onNavigate: (v: View) => void;
}

const PAGE_SIZE = 20;

export default function Consents({ user, onLogout, view, onNavigate }: Props) {
  const [items, setItems] = useState<ConsentListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [accepted, setAccepted] = useState<"" | "true" | "false">("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pdfBusy, setPdfBusy] = useState(""); // id đang tải PDF — khoá nút, tránh double-click

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await listConsents(page, PAGE_SIZE, accepted);
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi tải danh sách");
    } finally {
      setLoading(false);
    }
  }, [page, accepted]);

  useEffect(() => {
    load();
  }, [load]);

  // PDF nằm sau Authorization — tải blob rồi mở object URL ở tab mới (link trần sẽ 401).
  async function openPdf(it: ConsentListItem) {
    if (pdfBusy) return;
    setPdfBusy(it.id);
    setError("");
    try {
      const blob = await fetchConsentPdf(it.id);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được PDF");
    } finally {
      setPdfBusy("");
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="app">
      <TopBar user={user} view={view} onNavigate={onNavigate} onLogout={onLogout} />

      <div className="stats-head">
        <div>
          <h1 className="page-title">Nhật ký chấp thuận</h1>
          <p className="muted page-sub">
            Chấp thuận xử lý dữ liệu cá nhân (Luật 91/2025/QH15) — lượt đồng ý có PDF biên bản
          </p>
        </div>
        <select
          value={accepted}
          onChange={(e) => {
            setPage(1);
            setAccepted(e.target.value as "" | "true" | "false");
          }}
        >
          <option value="">Tất cả kết quả</option>
          <option value="true">Đồng ý</option>
          <option value="false">Từ chối</option>
        </select>
      </div>

      {error && <div className="error bar">{error}</div>}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Thời điểm</th>
              <th>Mã nhật ký</th>
              <th>Chủ thể (VNeID)</th>
              <th>Thủ tục</th>
              <th>Nơi làm thủ tục</th>
              <th>Tài khoản quầy</th>
              <th className="center">Kết quả</th>
              <th className="center">Biên bản</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={8} className="center muted">
                  Đang tải…
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={8} className="center muted">
                  Chưa có bản ghi chấp thuận nào
                </td>
              </tr>
            )}
            {!loading &&
              items.map((it) => {
                const place = [it.location?.ward, it.location?.province]
                  .filter(Boolean)
                  .join(", ");
                // Ưu tiên CCCD; chỉ tên khi cổng không lộ số; không có → theo mã phiên.
                const principal = it.principal_cccd
                  ? `${it.principal_cccd}${it.principal_name ? ` — ${it.principal_name}` : ""}`
                  : it.principal_name || "";
                return (
                  <tr key={it.id}>
                    <td className="muted">
                      {it.at_display || (it.at ? fmtDateTime(it.at) : "—")}
                    </td>
                    <td className="mono">{it.id}</td>
                    <td title={principal ? "" : "Không xác định được từ cổng — ghi nhận theo mã phiên"}>
                      {principal || <span className="muted">theo mã phiên</span>}
                    </td>
                    <td>{it.procedure_label || <span className="muted">—</span>}</td>
                    <td>{place || <span className="muted">—</span>}</td>
                    <td>{it.auth_username || <span className="muted">—</span>}</td>
                    <td className="center">
                      <span
                        className={`badge ${it.accepted ? "ok" : "warn"}`}
                        title={`Phiên bản nội dung ${it.version || "?"} · ${
                          it.method === "verbal" ? "nói/gõ đồng ý" : "bấm nút trên thẻ"
                        }`}
                      >
                        {it.accepted ? "Đồng ý" : "Từ chối"}
                      </span>
                    </td>
                    <td className="center">
                      {it.has_pdf ? (
                        <button
                          className="ghost sm"
                          disabled={pdfBusy === it.id}
                          onClick={() => openPdf(it)}
                        >
                          {pdfBusy === it.id ? "Đang mở…" : "Xem PDF"}
                        </button>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
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
    </div>
  );
}
