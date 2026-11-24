// Bộ ca test: mỗi ca là một lượt thật đã ghi (ẩn danh), phát lại OCR + câu trả lời mô hình đã ghi trên bản backend cần thử
// rồi so với tờ khai người dân đã nộp. Thêm ca bằng nút "Tạo ca test" ở màn tái hiện, hoặc nhập mã req ở đây.
import { useState, type FormEvent } from "react";
import Icon from "../components/Icon";
import { EmptyState, ErrorNotice, PageLoading, Spinner } from "../components/Status";
import { SourceTag } from "../components/Tags";
import { formatWhen } from "../format";
import { useAsync, useFacets } from "../hooks";
import { navigate, onLinkClick, useLocation } from "../router";
import { labApi, useLabAvailable, type Suite, type Target } from "./api";
import { CaTestTabs, LabCrumbs, LabNotice, Section, StatusBadge, Unavailable } from "./parts";
import "./autotest.css";

export default function SuitesPage() {
  const lab = useLabAvailable();
  const loc = useLocation();
  const { data, error, loading, reload } = useAsync(() => labApi.suites(), "suites");
  const { procLabel } = useFacets();
  const suites = data?.suites ?? [];
  const asked = loc.query.get("suite");
  const selected = suites.find((s) => s.key === asked) ?? suites[0] ?? null;
  const select = (key: string) => navigate(`/autotest/suites?suite=${encodeURIComponent(key)}`, { replace: true });

  if (lab === false) return <><LabNotice /><LabCrumbs items={[{ label: "Ca test", href: "/autotest/suites" }, { label: "Bộ ca test" }]} /><Unavailable /></>;
  if (loading && !data) return <><LabNotice /><PageLoading label="Đang tải bộ ca…" /></>;
  return (
    <>
      <LabNotice />
      <LabCrumbs items={[{ label: "Ca test", href: "/autotest/suites" }, { label: "Bộ ca test" }]} />
      <div className="page-head">
        <h1>Ca test</h1>
        <span className="page-head__meta">
          Mỗi ca test là một lượt thật đã ghi. Hệ thống phát lại đúng giấy tờ (OCR đã ghi) và câu trả lời mô hình đã ghi trên bản
          backend cần thử, rồi so kết quả với tờ khai người dân đã nộp.
        </span>
      </div>
      <CaTestTabs active="suites" />
      {error ? <ErrorNotice message={error} onRetry={reload} /> : null}
      <AddCase onDone={(key) => { reload(); if (key) select(key); }} />

      {!suites.length ? (
        <EmptyState title="Chưa có ca test nào" hint="Mở một lượt (Xem lượt) rồi bấm “Tạo ca test từ lượt này”, hoặc nhập mã req ở ô trên." />
      ) : (
        <div className="lab-suites">
          <div className="lab-suites__list" role="list">
            {suites.map((s) => (
              <button key={s.key} type="button" role="listitem" className={`lab-suite${selected?.key === s.key ? " is-on" : ""}`} onClick={() => select(s.key)}>
                <span className="lab-suite__name">{s.kind === "agent" ? s.label : `${procLabel(s.procedure, s.label)} — từ lượt thật`}</span>
                <span className="lab-suite__count num">{s.cases.length} ca</span>
                <span className="lab-suite__meta">
                  {s.running ? "Đang chạy…" : s.lastRun ? `Lần chạy #${s.lastRun.no} · ${formatWhen(s.lastRun.finishedAt).main} ${formatWhen(s.lastRun.finishedAt).sub}` : "Chưa chạy lần nào"}
                </span>
                {s.lastRun?.counts ? (
                  <span className="lab-suite__counts">
                    <span className="lab-c lab-c--ok">{s.lastRun.counts.pass} đạt</span>
                    {s.lastRun.counts.fail ? <span className="lab-c lab-c--bad">{s.lastRun.counts.fail} lỗi</span> : null}
                    {s.lastRun.counts.review ? <span className="lab-c lab-c--warn">{s.lastRun.counts.review} cần duyệt</span> : null}
                    {s.lastRun.counts.error ? <span className="lab-c lab-c--bad">{s.lastRun.counts.error} không chạy được</span> : null}
                  </span>
                ) : null}
              </button>
            ))}
          </div>
          {selected ? <SuiteDetail suite={selected} targets={data?.targets ?? []} onChanged={reload} highlight={loc.query.get("case")} /> : null}
        </div>
      )}
    </>
  );
}

function AddCase({ onDone }: { onDone: (suiteKey?: string) => void }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "ok" | "bad"; text: string } | null>(null);
  async function submit(event: FormEvent) {
    event.preventDefault();
    const id = text.trim();
    if (!/^req_[a-z0-9]+$/i.test(id)) return;
    setBusy(true);
    setMessage(null);
    try {
      const res = await labApi.createCase(id);
      setMessage({ tone: "ok", text: res.existing ? `Lượt này đã có ca ${res.caseId}.` : `Đã tạo ca ${res.caseId} (dữ liệu cá nhân đã thay bằng dữ liệu giả).` });
      setText("");
      const run = await labApi.run(id).catch(() => null);
      onDone(run ? `lab:${(run.procedure ?? "khac").replace(/[^\w.-]/g, "_")}` : undefined);
    } catch (reason) {
      setMessage({ tone: "bad", text: reason instanceof Error ? reason.message : String(reason) });
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <form className="lab-pick" onSubmit={submit}>
        <input className="input" placeholder="Thêm ca từ một lượt: mã req_… (lượt điền)" value={text} onChange={(e) => setText(e.target.value)} />
        <button className="btn" type="submit" disabled={busy || !/^req_[a-z0-9]+$/i.test(text.trim())}>
          {busy ? <Spinner label="Đang dựng ca…" /> : <><Icon name="flask" size={14} /> Tạo ca test</>}
        </button>
        <a className="btn btn--ghost" href="/autotest/replay" onClick={(e) => onLinkClick(e, "/autotest/replay")}>Chọn trong lượt người dân sửa</a>
      </form>
      {message ? <div className={`lab-msg lab-msg--${message.tone}`}>{message.text}</div> : null}
    </>
  );
}

function SuiteDetail({ suite, targets, onChanged, highlight }: { suite: Suite; targets: Target[]; onChanged: () => void; highlight: string | null }) {
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const { procLabel } = useFacets();
  const history = suite.cases[0]?.history ?? [];
  const runNos = Array.from(new Set(suite.cases.flatMap((c) => c.history.map((h) => h.no)))).sort((a, b) => a - b).slice(-2);

  async function start(target: "dev" | "release") {
    setBusy(target);
    setMessage("");
    try {
      const run = await labApi.startRun(suite.key, target);
      navigate(`/autotest/runs/${run.no}`);
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : String(reason));
      setBusy("");
    }
  }

  async function remove(id: string) {
    if (!window.confirm(`Xoá ca ${id}? Tệp ca trong runs/_lab bị xoá, lượt gốc không bị đụng.`)) return;
    try {
      await labApi.deleteCase(id);
      onChanged();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : String(reason));
    }
  }

  return (
    <div className="lab-suite-detail">
      <Section title={suite.kind === "agent" ? suite.label ?? "Ca hồi quy" : `${procLabel(suite.procedure, suite.label)} — từ lượt thật`}
               sub={`${suite.cases.length} ca · ${suite.edited} ca có ô người dân sửa${history.length ? "" : " · chưa chạy lần nào"}`}
               actions={<>
                 {targets.map((t) => (
                   <button key={t.key} className={`btn btn--sm${t.key === "dev" ? " btn--primary" : ""}`} type="button" disabled={!t.ok || !!busy || suite.running}
                           title={`${t.label}${t.commit ? ` · ${t.tag ?? t.commit}${t.dirty ? " + sửa chưa commit" : ""}` : ""}`} onClick={() => start(t.key)}>
                     {busy === t.key ? <Spinner label="Đang bắt đầu…" /> : <><Icon name="play" size={14} /> Chạy trên {t.key === "dev" ? "bản đang phát triển" : "bản production"}</>}
                   </button>
                 ))}
               </>}>
        {message ? <div className="lab-msg lab-msg--bad">{message}</div> : null}
        {suite.kind === "agent" ? (
          <p className="lab-hint">Ca hồi quy do Agent tự sửa sinh khi một bản sửa đạt (regression/cases). Các ca này phải luôn đạt; chạy trong CI.</p>
        ) : null}
        <div className="table-wrap">
          <table className="grid">
            <thead>
              <tr>
                <th>Mã ca</th><th>Lượt gốc</th><th>Đơn vị · kênh</th><th>Đầu vào phát lại</th><th>Đáp án</th>
                {runNos.map((no) => <th key={no}><a href={`/autotest/runs/${no}`} onClick={(e) => onLinkClick(e, `/autotest/runs/${no}`)}>#{no}</a></th>)}
                {suite.kind === "lab" ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {suite.cases.map((c) => (
                <tr key={c.id} className={highlight === c.id ? "is-current" : undefined}>
                  <td className="mono nowrap">{c.id}{c.createdAt && Date.now() - new Date(c.createdAt).getTime() < 86_400_000 ? <span className="lab-badge lab-badge--new">Mới thêm</span> : null}</td>
                  <td>{c.requestId ? (
                    <a className="mono" href={`/autotest/replay/${encodeURIComponent(c.requestId)}`} onClick={(e) => onLinkClick(e, `/autotest/replay/${encodeURIComponent(c.requestId!)}`)}>{c.requestId}</a>
                  ) : <span className="faint">ẩn danh</span>}</td>
                  <td><span className="cell-main">{c.xa || c.unit || "—"}</span><span className="cell-sub"><SourceTag source={c.experience} /></span></td>
                  <td>{c.files} tệp · {c.llm} lần gọi mô hình</td>
                  <td>{c.checks} ô{c.edited ? <> · <b className="lab-bad">{c.edited} ô người dân sửa</b></> : " · 0 ô sửa"}
                    {c.answer === "backend" ? <span className="cell-sub">đáp án = kết quả lúc ghi</span> : null}</td>
                  {runNos.map((no) => {
                    const h = c.history.find((x) => x.no === no);
                    return <td key={no}><StatusBadge status={h?.status} failed={h?.failed} /></td>;
                  })}
                  {suite.kind === "lab" ? (
                    <td><button className="btn btn--icon btn--ghost btn--sm" type="button" aria-label={`Xoá ca ${c.id}`} onClick={() => remove(c.id)}><Icon name="x" size={14} /></button></td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Một ca test chạy thế nào">
        <ol className="lab-how">
          <li><b>Phát lại đầu vào.</b> Văn bản OCR đã ghi của từng giấy tờ, đúng thứ tự tệp; câu trả lời mô hình đã ghi theo từng lần gọi;
            options của lượt (mốc người nộp, cài đặt). Đi qua đúng endpoint <code>/api/v1/process</code> của bản backend cần thử, không gọi mạng,
            không ghi Mongo, không chạm cổng thật.</li>
          <li><b>Không phát lại.</b> Những lần người dân tự sửa ô: đó chính là đáp án. Bản mới gọi mô hình nhiều hơn lúc ghi thì ca báo
            “Không chạy được” và cần ghi lại ca (đổi prompt / thêm lượt gọi mô hình phải chạy thật qua Agent tự sửa).</li>
          <li><b>So với đáp án.</b> Từng ô so với giá trị người dân để lại khi nộp (ảnh chụp form cuối), chuẩn hoá khoảng trắng. Ô giữ nguyên
            lấy giá trị backend đã trả; ô bị xoá phải trống. Bản mới điền thêm ô không có trong đáp án thì ca “Cần duyệt”.</li>
        </ol>
        <p className="lab-hint">Ca để trong <code>auto-test-hcc/runs/_lab</code> (gitignore): họ tên, số giấy tờ, số nhà / thôn đã thay bằng dữ
          liệu giả nhất quán giữa OCR, câu trả lời mô hình và đáp án; giữ đơn vị hành chính và ngày tháng vì mapper cần.</p>
      </Section>
    </div>
  );
}
