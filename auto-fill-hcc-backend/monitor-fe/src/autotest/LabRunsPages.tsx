// Lần chạy bộ ca test: danh sách, và kết quả một lần chạy so với lần trước của cùng bộ.
import { useEffect, useMemo, useState } from "react";
import Icon from "../components/Icon";
import { EmptyState, ErrorNotice, PageLoading, Spinner } from "../components/Status";
import { formatDateTime, formatMs, formatWhen, pct } from "../format";
import { useAsync, useFacets } from "../hooks";
import { navigate, onLinkClick } from "../router";
import { labApi, useLabAvailable, type CaseResult, type CaseStatus, type RunBrief, type RunDetailLab } from "./api";
import { CaTestTabs, downloadJson, humanDuration, LabCrumbs, LabNotice, Masked, Section, STATUS, StatusBadge, Unavailable, VerdictBadge } from "./parts";
import "./autotest.css";

function treeText(run: RunBrief) {
  const ref = run.tag ?? run.commit;
  return `${run.targetLabel ?? run.target}${ref ? ` · ${ref}` : ""}${run.dirty ? " + sửa chưa commit" : ""}`;
}

export function LabRunsPage() {
  const lab = useLabAvailable();
  const { data, error, loading, reload } = useAsync(() => labApi.runs(), "lab-runs");
  const { procLabel } = useFacets();
  useEffect(() => {
    if (!data?.current) return undefined;
    const handle = window.setTimeout(reload, 2000);
    return () => window.clearTimeout(handle);
  }, [data, reload]);

  if (lab === false) return <><LabNotice /><LabCrumbs items={[{ label: "Ca test", href: "/autotest/suites" }, { label: "Lần chạy" }]} /><Unavailable /></>;
  if (loading && !data) return <><LabNotice /><PageLoading label="Đang tải lần chạy…" /></>;
  const runs = data?.runs ?? [];
  return (
    <>
      <LabNotice />
      <LabCrumbs items={[{ label: "Ca test", href: "/autotest/suites" }, { label: "Lần chạy" }]} />
      <div className="page-head">
        <h1>Ca test</h1>
        <span className="page-head__meta">Mỗi lần chạy phát lại một bộ ca trên một bản backend. Bấm một dòng để xem từng ca, từng ô.</span>
      </div>
      <CaTestTabs active="runs" />
      {error ? <ErrorNotice message={error} onRetry={reload} /> : null}
      <div className="table-wrap">
        <table className="grid">
          <thead><tr><th>#</th><th>Bộ ca</th><th>Bản backend</th><th>Lúc</th><th className="right">Thời gian</th><th>Kết quả</th><th className="right">Ô điền đúng</th><th>Người chạy</th></tr></thead>
          <tbody>
            {runs.map((run) => {
              const when = formatWhen(run.finishedAt ?? run.startedAt);
              return (
                <tr key={run.no} onClick={() => navigate(`/autotest/runs/${run.no}`)}>
                  <td className="num">#{run.no}</td>
                  <td>{run.suite === "agent" ? run.suiteLabel : procLabel(run.suite.replace(/^lab:/, ""), run.suiteLabel)}</td>
                  <td className="lab-note">{treeText(run)}</td>
                  <td className="nowrap"><span className="cell-main num">{when.main}</span><span className="cell-sub">{when.sub}</span></td>
                  <td className="num right">{run.status === "running" ? <Spinner label="Đang chạy" /> : formatMs(run.durationMs)}</td>
                  <td><Counts run={run} /></td>
                  <td className="num right">{run.fields?.total ? pct(run.fields.ok, run.fields.total) : "—"}</td>
                  <td>{run.by ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!runs.length ? <EmptyState title="Chưa có lần chạy nào" hint="Vào tab Bộ ca, chọn một bộ rồi bấm Chạy." /> : null}
      </div>
    </>
  );
}

function Counts({ run }: { run: RunBrief }) {
  if (run.status === "error") return <span className="lab-badge lab-badge--bad" title={run.error}>Hỏng</span>;
  if (!run.counts) return <span className="faint">{run.total} ca</span>;
  const c = run.counts;
  return (
    <span className="lab-suite__counts">
      <span className="lab-c lab-c--ok">{c.pass} đạt</span>
      {c.fail ? <span className="lab-c lab-c--bad">{c.fail} lỗi</span> : null}
      {c.review ? <span className="lab-c lab-c--warn">{c.review} cần duyệt</span> : null}
      {c.error ? <span className="lab-c lab-c--bad">{c.error} không chạy được</span> : null}
    </span>
  );
}

type CaseFilter = "all" | "bad" | "changed";

export function LabRunResultPage({ no }: { no: number }) {
  const lab = useLabAvailable();
  const { data, error, loading, reload } = useAsync(() => labApi.runDetail(no), `lab-run:${no}`);
  const { procLabel } = useFacets();
  const [filter, setFilter] = useState<CaseFilter>("all");
  const [picked, setPicked] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const previous = useAsync(() => (data?.previous ? labApi.runDetail(data.previous) : Promise.resolve(null)), `lab-run-prev:${data?.previous ?? "none"}`);

  useEffect(() => {
    if (data?.status !== "running") return undefined;
    const handle = window.setTimeout(reload, 1500);
    return () => window.clearTimeout(handle);
  }, [data, reload]);

  const results = data?.results ?? [];
  const before = data?.previousResults ?? {};
  const changed = (r: CaseResult) => before[r.id] && before[r.id].status !== r.status;
  const shown = results.filter((r) => filter === "all" || (filter === "bad" ? r.status !== "pass" : changed(r)));
  const selected = useMemo(() => results.find((r) => r.id === picked) ?? results.find((r) => r.status !== "pass") ?? results[0] ?? null, [results, picked]);

  if (lab === false) return <><LabNotice /><LabCrumbs items={[{ label: "Ca test", href: "/autotest/suites" }, { label: "Lần chạy", href: "/autotest/runs" }, { label: `#${no}` }]} /><Unavailable /></>;
  if (loading && !data) return <><LabNotice /><PageLoading label="Đang tải lần chạy…" /></>;
  if (error && !data) return <><LabNotice /><LabCrumbs items={[{ label: "Ca test", href: "/autotest/suites" }, { label: "Lần chạy", href: "/autotest/runs" }, { label: `#${no}` }]} /><ErrorNotice message={error} onRetry={reload} /></>;
  if (!data) return null;

  const suiteName = data.suite === "agent" ? data.suiteLabel : procLabel(data.suite.replace(/^lab:/, ""), data.suiteLabel);
  const c = data.counts ?? { pass: 0, fail: 0, review: 0, error: 0 };
  const p = previous.data?.counts;
  const prevFields = previous.data?.fields;
  const rate = data.fields?.total ? (data.fields.ok / data.fields.total) * 100 : null;
  const prevRate = prevFields?.total ? (prevFields.ok / prevFields.total) * 100 : null;
  const newBad = results.filter((r) => r.status !== "pass" && before[r.id]?.status === "pass").length;
  const notPass = results.filter((r) => r.status !== "pass").map((r) => r.id);
  const slowest = results.reduce((m, r) => Math.max(m, r.ms ?? 0), 0);

  async function rerun() {
    setBusy(true);
    setMessage("");
    try {
      const run = await labApi.startRun(data!.suite, data!.target, notPass);
      navigate(`/autotest/runs/${run.no}`);
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <LabNotice />
      <LabCrumbs items={[{ label: "Bộ ca test", href: `/autotest/suites?suite=${encodeURIComponent(data.suite)}` }, { label: suiteName ?? data.suite },
                         { label: `Lần chạy #${data.no}` }]} />
      <section className="lab-head">
        <div className="lab-head__title">
          <h1>Lần chạy #{data.no} · {suiteName}</h1>
          <div className="lab-head__meta">
            <span>{treeText(data)}</span>
            {data.previous ? <><span>so với</span><a href={`/autotest/runs/${data.previous}`} onClick={(e) => onLinkClick(e, `/autotest/runs/${data.previous}`)}>lần chạy #{data.previous}</a>{previous.data ? <span>({treeText(previous.data)})</span> : null}</> : <span>lần chạy đầu của bộ này</span>}
            <span>·</span>
            {data.status === "running" ? <Spinner label={`Đang chạy ${data.total} ca…`} /> : <span>Xong {formatDateTime(data.finishedAt)} · {humanDuration(data.durationMs)}</span>}
            <span>·</span><span>Phát lại OCR + câu trả lời mô hình đã ghi, không gọi mạng, không nộp lên cổng</span>
          </div>
        </div>
        <div className="lab-head__actions">
          {notPass.length && data.status === "done" ? (
            <button className="btn btn--sm btn--primary" type="button" disabled={busy} onClick={rerun}>
              {busy ? <Spinner label="Đang bắt đầu…" /> : <><Icon name="refresh" size={14} /> Chạy lại {notPass.length} ca chưa đạt</>}
            </button>
          ) : null}
          <button className="btn btn--sm" type="button" onClick={() => downloadJson(`lan-chay-${data.no}.json`, data)}><Icon name="download" size={14} /> Xuất báo cáo</button>
        </div>
      </section>
      {message ? <div className="lab-msg lab-msg--bad">{message}</div> : null}
      {data.status === "error" ? <div className="notice notice--error"><Icon name="alert" /><div><strong>Lần chạy hỏng</strong><span>{data.error}</span></div></div> : null}

      {data.status === "done" ? (
        <>
          <div className="kpis kpis--6">
            <div className="kpi"><span>Ca đạt</span><b>{c.pass}/{data.total}</b><small>{p ? delta(c.pass - p.pass, `so với #${data.previous} (${p.pass}/${previous.data?.total})`) : "chưa có lần trước"}</small></div>
            <div className="kpi"><span>Lỗi</span><b className={c.fail ? "lab-bad" : undefined}>{c.fail}</b><small>{newBad ? `${newBad} ca mới lỗi so với #${data.previous}` : data.previous ? "không có ca mới lỗi" : ""}</small></div>
            <div className="kpi"><span>Cần duyệt</span><b className={c.review ? "lab-warn" : undefined}>{c.review}</b><small>bản này điền thêm ô không có đáp án</small></div>
            <div className="kpi"><span>Không chạy được</span><b className={c.error ? "lab-bad" : undefined}>{c.error}</b><small>gọi mô hình nhiều hơn lúc ghi / lỗi HTTP</small></div>
            <div className="kpi"><span>Ô điền đúng</span><b>{rate !== null ? `${rate.toLocaleString("vi-VN", { maximumFractionDigits: 1 })}%` : "—"}</b>
              <small>{data.fields ? `${data.fields.ok}/${data.fields.total} ô` : ""}{rate !== null && prevRate !== null ? ` · ${delta(Math.round((rate - prevRate) * 10) / 10, "điểm")}` : ""}</small></div>
            <div className="kpi"><span>Thời gian mỗi ca</span><b>{results.length ? formatMs((data.durationMs ?? 0) / results.length) : "—"}</b><small>chậm nhất {formatMs(slowest)}</small></div>
          </div>

          <Section title="Các ca" sub="Bấm một ca để xem chi tiết bên dưới" actions={
            <div className="seg">
              <button type="button" aria-pressed={filter === "all"} onClick={() => setFilter("all")}>Tất cả {results.length}</button>
              <button type="button" aria-pressed={filter === "bad"} onClick={() => setFilter("bad")}>Chưa đạt {notPass.length}</button>
              <button type="button" aria-pressed={filter === "changed"} onClick={() => setFilter("changed")}>Đổi kết quả {results.filter((r) => changed(r)).length}</button>
            </div>
          }>
            <div className="table-wrap">
              <table className="grid">
                <thead><tr><th>Mã ca</th><th>{data.previous ? `#${data.previous} → #${data.no}` : `#${data.no}`}</th><th>Điều khác biệt</th><th className="right">Ô đúng</th><th className="right">Chạy</th></tr></thead>
                <tbody>
                  {shown.map((r) => (
                    <tr key={r.id} className={selected?.id === r.id ? "is-current" : undefined} onClick={() => setPicked(r.id)}>
                      <td className="mono">{r.id}</td>
                      <td className="nowrap">{before[r.id] ? <><StatusBadge status={before[r.id].status} failed={before[r.id].failed} /> → </> : null}<StatusBadge status={r.status} failed={r.failedFields} /></td>
                      <td className="lab-note">{issue(r)}</td>
                      <td className="num right">{r.okFields}/{r.totalFields}</td>
                      <td className="num right">{formatMs(r.ms)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!shown.length ? <EmptyState title="Không có ca nào khớp bộ lọc" /> : null}
            </div>
          </Section>

          {selected ? <CaseDetail run={data} result={selected} before={before[selected.id]} /> : null}
        </>
      ) : null}
    </>
  );
}

function delta(value: number, suffix: string) {
  if (!value) return `không đổi ${suffix}`;
  return `${value > 0 ? "+" : "−"}${Math.abs(value).toLocaleString("vi-VN")} ${suffix}`;
}

function issue(r: CaseResult): string {
  if (r.status === "error") return r.error ?? "Không chạy được";
  const bad = r.rows.filter((x) => !x.ok).map((x) => x.label || x.field);
  if (r.status === "review") return `Điền thêm ô không có đáp án: ${r.extraFields.slice(0, 4).join(", ")}${r.extraFields.length > 4 ? "…" : ""}`;
  if (bad.length) return `${bad.length} ô khác đáp án: ${bad.slice(0, 3).join(", ")}${bad.length > 3 ? "…" : ""}`;
  return "Khớp đáp án";
}

function CaseDetail({ run, result, before }: { run: RunDetailLab; result: CaseResult; before?: { status: CaseStatus; failed?: number; rows: Record<string, string | null> } }) {
  const [all, setAll] = useState(false);
  const wrong = result.rows.filter((r) => !r.ok || (before && before.rows[r.field] !== undefined && before.rows[r.field] !== r.actual));
  const rows = all ? result.rows : wrong;
  return (
    <Section title={`${result.id} · ${STATUS[result.status].label}`} sub={`${result.okFields}/${result.totalFields} ô khớp đáp án`}
             actions={<a className="btn btn--sm" href={`/autotest/suites?suite=${encodeURIComponent(run.suite)}&case=${result.id}`}
                         onClick={(e) => onLinkClick(e, `/autotest/suites?suite=${encodeURIComponent(run.suite)}&case=${result.id}`)}>Mở trong bộ ca</a>}>
      {result.error && (result.status === "error" || !result.rows.length) ? <div className="lab-msg lab-msg--bad">{result.error}</div> : null}
      {result.extraFields.length ? <p className="lab-hint">Ô bản này điền mà ca không có đáp án (cần người kiểm tra quyết định): <span className="mono">{result.extraFields.join(", ")}</span></p> : null}
      {result.rows.length ? (
        <>
          <div className="table-wrap">
            <table className="grid">
              <thead><tr><th>Ô</th><th>Đáp án (người dân đã nộp)</th>{before ? <th>Lần trước</th> : null}<th>Lần này</th><th>Kết quả</th></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.field} className={r.ok ? undefined : "is-bad"}>
                    <td><span className="cell-main">{r.label}</span><span className="cell-sub mono">{r.field}</span>{r.verdict ? <VerdictBadge verdict={r.verdict} /> : null}</td>
                    <td>{r.op === "empty" ? <span className="faint">(phải trống)</span> : <Masked value={r.expected} />}</td>
                    {before ? <td><Masked value={before.rows[r.field]} empty="(trống)" /></td> : null}
                    <td><b><Masked value={r.actual} empty="(trống)" /></b></td>
                    <td>{r.ok ? <span className="lab-badge lab-badge--ok">Khớp</span> : <span className="lab-badge lab-badge--bad">Khác</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="lab-hint">
            {all ? null : `${result.rows.length - wrong.length} ô còn lại khớp đáp án${before ? " ở cả hai lần" : ""}. `}
            <button className="linklike" type="button" onClick={() => setAll((v) => !v)}>{all ? "Chỉ hiện ô khác" : "Hiện mọi ô"}</button>
          </p>
        </>
      ) : null}
    </Section>
  );
}
