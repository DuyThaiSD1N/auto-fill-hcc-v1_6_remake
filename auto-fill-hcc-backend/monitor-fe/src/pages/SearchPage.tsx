import { useEffect, useMemo, useState, type FormEvent } from "react";
import { listTraces } from "../api";
import {
  formatDateTime,
  traceActionLabel,
  traceSourceLabel,
  traceUnit,
} from "../format";
import type { MonitorUser, TraceListResponse } from "../types";
import AppHeader from "../components/AppHeader";
import Icon from "../components/Icon";
import { ErrorNotice, Spinner } from "../components/Status";

interface Props {
  user: MonitorUser;
  onLogout: () => void;
  onOpenTrace: (traceId: string, returnPath: string) => void;
}

function readQuery(): { q: string; page: number } {
  const params = new URLSearchParams(window.location.search);
  const page = Number(params.get("page") || "1");
  return { q: params.get("q")?.trim() || "", page: Number.isFinite(page) && page > 0 ? page : 1 };
}

export default function SearchPage({ user, onLogout, onOpenTrace }: Props) {
  const initial = useMemo(readQuery, []);
  const [input, setInput] = useState(initial.q);
  const [query, setQuery] = useState(initial.q);
  const [page, setPage] = useState(initial.page);
  const [result, setResult] = useState<TraceListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!query) return;
    let active = true;
    setLoading(true);
    setError("");
    listTraces(query, page)
      .then((data) => {
        if (active) setResult(data);
      })
      .catch((reason) => {
        if (active) setError(reason instanceof Error ? reason.message : "Không tra cứu được mã hỗ trợ.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [query, page, reloadKey]);

  function syncUrl(nextQuery: string, nextPage: number) {
    const params = new URLSearchParams();
    if (nextQuery) params.set("q", nextQuery);
    if (nextPage > 1) params.set("page", String(nextPage));
    const queryString = params.toString();
    const next = queryString ? `/?${queryString}` : "/";
    window.history.replaceState({}, "", next);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const nextQuery = input.trim();
    if (!nextQuery) return;
    setResult(null);
    setQuery(nextQuery);
    setPage(1);
    syncUrl(nextQuery, 1);
  }

  function changePage(nextPage: number) {
    setPage(nextPage);
    syncUrl(query, nextPage);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const pages = result ? Math.max(1, Math.ceil(result.total / result.pageSize)) : 1;
  const currentPath = `${window.location.pathname}${window.location.search}`;

  return (
    <div className="monitor-app">
      <AppHeader user={user} onLogout={onLogout} />
      <main id="main-content" className="shell search-page">
        <section className="search-intro">
          <div>
            <span className="eyebrow">Trace lookup</span>
            <h1>Tra mã hỗ trợ</h1>
            <p>Tìm đúng lượt xử lý trước khi mở giấy tờ và nội dung phân tích chi tiết.</p>
          </div>
          <span className="security-label"><Icon name="shield" /> Chỉ super admin</span>
        </section>

        <form className="trace-search" onSubmit={submit} role="search">
          <label htmlFor="support-code">Mã hỗ trợ hoặc một phần mã</label>
          <div className="trace-search__row">
            <span className="trace-search__input">
              <Icon name="search" size={20} />
              <input
                id="support-code"
                onChange={(event) => setInput(event.target.value)}
                placeholder="Ví dụ: req_b261436d2638"
                spellCheck={false}
                value={input}
              />
            </span>
            <button className="button button--primary" disabled={loading || !input.trim()} type="submit">
              {loading ? <Spinner label="Đang tra" /> : <><Icon name="search" /> Tra cứu</>}
            </button>
          </div>
          <p>Có thể dán toàn bộ mã hoặc nhập một đoạn mã đã nhận từ cán bộ.</p>
        </form>

        {!query ? (
          <section className="empty-state empty-state--initial">
            <span className="empty-state__icon"><Icon name="document" size={28} /></span>
            <h2>Bắt đầu từ mã hỗ trợ</h2>
            <p>Monitor không tự tải danh sách hồ sơ. Chỉ hồ sơ được tra cứu mới xuất hiện.</p>
          </section>
        ) : null}

        {error ? <ErrorNotice message={error} onRetry={() => setReloadKey((value) => value + 1)} /> : null}

        {query && !error ? (
          <section className="results-section" aria-busy={loading}>
            <header className="section-heading">
              <div>
                <span className="section-index">01</span>
                <div>
                  <h2>Kết quả tra cứu</h2>
                  <p>
                    {result ? `${result.total.toLocaleString("vi-VN")} lượt khớp với “${query}”` : "Đang đối chiếu mã hỗ trợ…"}
                  </p>
                </div>
              </div>
            </header>

            {loading && !result ? (
              <div className="result-skeleton" aria-label="Đang tải kết quả">
                <span /><span /><span />
              </div>
            ) : null}

            {result && result.items.length === 0 ? (
              <div className="empty-state">
                <span className="empty-state__icon"><Icon name="search" size={26} /></span>
                <h3>Không tìm thấy lượt xử lý</h3>
                <p>Kiểm tra lại mã hỗ trợ hoặc thử nhập một đoạn ngắn hơn.</p>
              </div>
            ) : null}

            {result && result.items.length > 0 ? (
              <div className="table-frame">
                <table className="trace-table">
                  <thead>
                    <tr>
                      <th>Thời gian</th>
                      <th>Mã hỗ trợ</th>
                      <th>Đơn vị</th>
                      <th>Thủ tục</th>
                      <th>Nguồn</th>
                      <th>Thao tác</th>
                      <th><span className="sr-only">Mở</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.items.map((trace) => (
                      <tr key={trace.id}>
                        <td className="nowrap">{formatDateTime(trace.created_at)}</td>
                        <td>
                          <button
                            className="request-link"
                            onClick={() => onOpenTrace(trace.id, currentPath)}
                            type="button"
                          >
                            {trace.request_id}
                          </button>
                        </td>
                        <td>{traceUnit(trace.name, trace.username)}</td>
                        <td>{trace.procedure_label || trace.procedure || "—"}</td>
                        <td><span className={`badge badge--${trace.experience === "handfree" ? "voice" : "quiet"}`}>{traceSourceLabel(trace.experience)}</span></td>
                        <td><span className="badge badge--outline">{traceActionLabel(trace.kind)}</span></td>
                        <td>
                          <button
                            aria-label={`Mở trace ${trace.request_id}`}
                            className="row-open"
                            onClick={() => onOpenTrace(trace.id, currentPath)}
                            type="button"
                          >
                            <Icon name="chevron-right" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}

            {result && pages > 1 ? (
              <nav className="pagination" aria-label="Phân trang kết quả">
                <button className="button button--secondary" disabled={page <= 1 || loading} onClick={() => changePage(page - 1)} type="button">
                  <Icon name="chevron-left" /> Trang trước
                </button>
                <span>Trang <strong>{page}</strong> / {pages}</span>
                <button className="button button--secondary" disabled={page >= pages || loading} onClick={() => changePage(page + 1)} type="button">
                  Trang sau <Icon name="chevron-right" />
                </button>
              </nav>
            ) : null}
          </section>
        ) : null}
      </main>
    </div>
  );
}
