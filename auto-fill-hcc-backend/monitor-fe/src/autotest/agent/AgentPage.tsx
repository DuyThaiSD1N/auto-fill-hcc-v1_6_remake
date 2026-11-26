import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { ApiError } from "../../api";
import Icon from "../../components/Icon";
import { Spinner } from "../../components/Status";
import { formatDateTime } from "../../format";
import { navigate } from "../../router";
import { agentApi, errorText, serviceDown, type FixTarget, type JobSummary, type RequestInfo } from "./api";
import JobDetail, { OutcomeTag, StatusTag } from "./JobDetail";

const LIST_POLL_MS = 4000;

type Filter = "all" | "running" | "approve" | "fixed" | "attention";

const FILTERS: { key: Filter; label: string; match: (job: JobSummary) => boolean }[] = [
  { key: "all", label: "Tất cả", match: () => true },
  { key: "running", label: "Đang chạy", match: (j) => j.status === "running" || j.status === "queued" },
  { key: "approve", label: "Chờ duyệt", match: (j) => j.status === "running" && (j.stage === "approve" || j.stage === "plan") },
  { key: "fixed", label: "Đã sửa", match: (j) => j.outcome === "fixed" },
  { key: "attention", label: "Cần xem", match: (j) => j.outcome === "need_human" || j.status === "failed" },
];

const TARGETS: { value: FixTarget; label: string; hint: string }[] = [
  { value: "autofill", label: "Auto Fill", hint: "Sửa backend hoặc extension Auto Fill." },
  { value: "troly", label: "Trợ lý hồ sơ", hint: "Sửa backend, gồm kênh trợ lý; chạy thêm tests/handfree." },
];

function ServiceNotice({ message }: { message: string }) {
  return (
    <div className="notice notice--error" role="alert">
      <Icon name="alert" />
      <div>
        <strong>Chưa dùng được phần Agent tự sửa</strong>
        <span>{message}</span>
      </div>
    </div>
  );
}

function Choice<T extends string>({ label, value, options, onChange, disabled }: {
  label: string;
  value: T;
  options: { value: T; label: string; hint: string }[];
  onChange: (value: T) => void;
  disabled?: (value: T) => boolean;
}) {
  const current = options.find((o) => o.value === value);
  return (
    <div className="at-choice">
      {label ? <span className="at-choice__label">{label}</span> : null}
      <div className="seg at-seg" role="radiogroup" aria-label={label || options.map((o) => o.label).join(" / ")}>
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            role="radio"
            aria-checked={o.value === value}
            aria-pressed={o.value === value}
            disabled={disabled?.(o.value)}
            onClick={() => onChange(o.value)}
          >
            {o.label}
          </button>
        ))}
      </div>
      {current ? <p className="at-choice__hint faint">{current.hint}</p> : null}
    </div>
  );
}

function LookupCard({ info, looking, error, onPick }: {
  info: RequestInfo | null; looking: boolean; error: string; onPick: (requestId: string) => void;
}) {
  if (looking) return <div className="at-lookup"><Spinner label="Đang tra req" /></div>;
  if (error) return <div className="at-lookup at-lookup--bad" role="alert">{error}</div>;
  if (!info) return <div className="at-lookup at-lookup--empty faint">Nhập mã req của lượt điền hoặc lượt đính kèm rồi rời ô để tra.</div>;
  const unit = [info.account.xa, info.account.tinh].filter(Boolean).join(", ");
  const attach = info.kind === "attach";
  const others = info.attachRuns || [];
  return (
    <div className="at-lookup" aria-live="polite">
      <div className="at-lookup__title">
        <strong>{info.label}</strong>
        <span className={`at-tag at-tag--${attach ? "warn" : "plain"}`}>{attach ? "Lượt đính kèm" : "Lượt điền"}</span>
        {info.thanhTra?.has ? (
          <span className="at-tag at-tag--plain" title="Sau lần điền đầu, một AI khác đọc lại giấy tờ và sửa ô khi có bằng chứng. Hội đồng sẽ xét cả bước này.">
            Có thanh tra{info.thanhTra.ran === "done" ? ` · đã sửa ${info.thanhTra.patched ?? 0} ô` : info.thanhTra.ran ? "" : " · lượt này không chạy"}
          </span>
        ) : null}
        <span className={`at-tag at-tag--${info.source === "archive" ? "plain" : "ok"}`}>
          {info.source === "archive" ? "Kho lưu trữ" : "Còn trên production"}
        </span>
      </div>
      <p className="at-lookup__meta faint">
        <span>{info.account.username}{unit ? ` · ${unit}` : ""}</span>
        <span>{info.files.length} tệp</span>
        {attach ? (
          <>
            <span>{info.fieldsCount ?? 0} mục đính kèm</span>
            <span>Tách giấy tờ: {info.splitDocuments === true ? "bật" : "tắt"}</span>
          </>
        ) : <span>{info.fieldsCount ?? 0} field</span>}
        {info.createdAt ? <span>{formatDateTime(info.createdAt)}</span> : null}
      </p>
      {!attach && others.length ? (
        <p className="at-lookup__related faint">
          Lỗi ở bước đính kèm thì test bằng mã đính kèm cùng hồ sơ:{" "}
          {others.map((run) => (
            <button key={run.requestId} type="button" className="at-linkbtn mono" onClick={() => onPick(run.requestId)}>
              {run.requestId}
            </button>
          ))}
        </p>
      ) : null}
      {info.missingFiles.length ? <p className="form-error">Thiếu {info.missingFiles.length} tệp gốc, không chạy lại được.</p> : null}
    </div>
  );
}

function StartForm({ onCreated, onCancel, initialRequest }: {
  onCreated: (id: string) => void; onCancel?: () => void; initialRequest?: string;
}) {
  const [requestId, setRequestId] = useState(initialRequest ?? "");
  const [description, setDescription] = useState("");
  const [info, setInfo] = useState<RequestInfo | null>(null);
  const [lookupError, setLookupError] = useState("");
  const [looking, setLooking] = useState(false);
  const [runs, setRuns] = useState(5);
  const [maxRounds, setMaxRounds] = useState(3);
  const [reproduce, setReproduce] = useState(true);
  const [target, setTarget] = useState<FixTarget>("autofill");
  const [applicantName, setApplicantName] = useState("");
  const [applicantId, setApplicantId] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const looked = useRef("");

  const lookup = useCallback(async (raw: string) => {
    const id = raw.trim();
    if (!id || id === looked.current) return;
    looked.current = id;
    setLooking(true);
    setLookupError("");
    setInfo(null);
    try {
      const found = await agentApi.lookup(id);
      setInfo(found);
      // Lượt điền bằng trợ lý thì mặc định sửa cho trợ lý; trợ lý hiện chỉ chạy được ở chế độ Chỉ gọi backend.
      const troly = found.experience === "handfree";
      setTarget(troly ? "troly" : "autofill");
    } catch (reason) {
      setLookupError(errorText(reason));
    } finally {
      setLooking(false);
    }
  }, []);

  // Mở từ Monitor (Tái hiện lượt › Gửi Agent tự sửa): mã req có sẵn trên URL → tra luôn.
  useEffect(() => {
    if (initialRequest) void lookup(initialRequest);
  }, [initialRequest, lookup]);

  const pickTarget = (value: FixTarget) => {
    setTarget(value);
  };

  const ready = !!info && !info.missingFiles.length && description.trim().length >= 5 && !sending;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ready || !info) return;
    setSending(true);
    setError("");
    try {
      const job = await agentApi.create({
        requestId: info.requestId,
        description: description.trim(),
        runs,
        maxRounds,
        reproduce,
        applicant: { applicantFullname: applicantName, applicantIdentityNumber: applicantId, applicantBirthday: "" },
        mode: "api",
        target,
      });
      onCreated(job.id);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setSending(false);
    }
  }

  return (
    <form className="panel at-new" onSubmit={submit}>
      <div className="at-new__head">
        <h2>Tạo ca mới</h2>
        <p className="faint">Hội đồng agent đọc lượt điền, tìm nguyên nhân; lỗi code thì sửa, chờ bạn duyệt rồi chạy lại để kiểm.</p>
      </div>
      <div className="at-new__req">
        <label className="field">
          <span>Mã req</span>
          <input
            className="input mono"
            placeholder="req_…"
            autoComplete="off"
            spellCheck={false}
            value={requestId}
            onChange={(e) => { setRequestId(e.target.value); looked.current = ""; setInfo(null); setLookupError(""); }}
            onBlur={(e) => void lookup(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); void lookup(requestId); } }}
          />
        </label>
        <LookupCard
          info={info}
          looking={looking}
          error={lookupError}
          onPick={(id) => { setRequestId(id); looked.current = ""; void lookup(id); }}
        />
      </div>
      <label className="field">
        <span>Lỗi người dùng báo</span>
        <textarea
          className="input at-textarea"
          rows={3}
          placeholder={info?.kind === "attach"
            ? "Giấy nào vào sai dòng và đúng ra phải vào dòng nào. Ví dụ: CCCD hai mặt bị tách làm hai mục, phải chung một mục ở dòng Giấy tờ tùy thân."
            : "Ô nào sai và đúng ra phải thế nào. Ví dụ: ô giới tính bị trống trong khi giấy khai sinh ghi Nữ."}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>
      <div className="at-new__choices">
        <Choice label="Sửa cho" value={target} options={TARGETS} onChange={pickTarget} />
      </div>
      <p className="faint at-mode-note">
        Chạy lại bằng cách gọi backend thử với giấy tờ của req (OCR mới mỗi lần), không mở cổng, không cần VNeID. Kết quả xem ở tab
        Kết quả điền: trường nào nhận giá trị gì, mô phỏng trên form của thủ tục như web trace.
      </p>
      {info?.needsApplicant ? (
        <fieldset className="at-applicant">
          <legend>Mốc người nộp</legend>
          <p className="faint">Ngữ cảnh của lượt trợ lý đã hết hạn. Thiếu mốc người nộp thì nhiều thủ tục không phân được vai.</p>
          <div className="at-applicant__grid">
            <label className="field">
              <span>Họ tên người nộp</span>
              <input className="input" autoComplete="off" value={applicantName} onChange={(e) => setApplicantName(e.target.value)} />
            </label>
            <label className="field">
              <span>Số định danh</span>
              <input className="input mono" autoComplete="off" inputMode="numeric" value={applicantId} onChange={(e) => setApplicantId(e.target.value)} />
            </label>
          </div>
        </fieldset>
      ) : null}
      <details className="at-new__more">
        <summary>Tuỳ chọn <span className="faint">· chạy {runs} lần · tối đa {maxRounds} vòng sửa{reproduce ? " · chạy lại trước khi họp" : ""}</span></summary>
        <div className="at-new__opts">
          <label className="field">
            <span>Số lần chạy</span>
            <select className="input" value={runs} onChange={(e) => setRuns(Number(e.target.value))}>
              {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Số vòng sửa tối đa</span>
            <select className="input" value={maxRounds} onChange={(e) => setMaxRounds(Number(e.target.value))}>
              {[1, 2, 3].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <label className="lab-check">
            <input type="checkbox" checked={reproduce} onChange={(e) => setReproduce(e.target.checked)} />
            Chạy lại {runs} lần trước khi họp, để biết lỗi có lặp lại không
          </label>
        </div>
      </details>
      {error ? <div className="form-error" role="alert">{error}</div> : null}
      <div className="at-new__foot">
        <p className="faint">Chạy lại bằng tài khoản test cùng xã, tỉnh với req, dịch vụ tự dựng.</p>
        {onCancel ? <button className="btn" type="button" onClick={onCancel}>Đóng</button> : null}
        <button className="btn btn--primary" type="submit" disabled={!ready}>
          {sending ? <Spinner label="Đang tạo" /> : <><Icon name="play" size={14} /> Bắt đầu</>}
        </button>
      </div>
    </form>
  );
}

function JobList({ jobs, onOpen }: { jobs: JobSummary[]; onOpen: (id: string) => void }) {
  if (!jobs.length) return <p className="faint at-empty">Không có ca nào ở mục này.</p>;
  return (
    <div className="table-wrap panel">
      <table className="mini-table at-jobs">
        <thead>
          <tr>
            <th>Thủ tục</th>
            <th className="at-col-desc">Lỗi người dùng báo</th>
            <th>Kết quả</th>
            <th className="at-num at-col-rounds">Vòng</th>
            <th className="at-col-time">Lúc</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} className="at-jobs__row" onClick={() => onOpen(job.id)}>
              <td className="at-jobs__main">
                <button className="at-link" type="button" onClick={(e) => { e.stopPropagation(); onOpen(job.id); }}>{job.label}</button>
                <span className="mono faint">{job.requestId}<span className="at-jobs__time"> · {formatDateTime(job.createdAt)}</span></span>
              </td>
              <td className="at-clip at-col-desc" title={job.description}>{job.description}</td>
              <td>
                <span className="at-jobs__state">
                  {job.outcome ? <OutcomeTag outcome={job.outcome} /> : <StatusTag status={job.status} stage={job.stage} />}
                  {job.status === "running" && (job.stage === "plan" || job.stage === "approve") ? (
                    <button className="btn btn--sm btn--primary" type="button" onClick={(e) => { e.stopPropagation(); onOpen(job.id); }}>Duyệt</button>
                  ) : null}
                </span>
              </td>
              <td className="at-num num at-col-rounds">{job.rounds || "–"}</td>
              <td className="num faint at-nowrap at-col-time">{formatDateTime(job.createdAt)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const AGENT_HOME = "/autotest/agent";
const openJob = (id: string) => navigate(`${AGENT_HOME}/${encodeURIComponent(id)}`);

/** Monitor › Auto test › Agent tự sửa. Ca đang mở nằm trên URL (/autotest/agent/<mã ca>) để gửi link cho người duyệt;
 * ?req=<mã req> mở sẵn form tạo ca với mã req đó. */
export default function AgentPage({ jobId = null, initialRequest }: { jobId?: string | null; initialRequest?: string }) {
  const open = jobId;
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [listError, setListError] = useState("");
  const [blocked, setBlocked] = useState(false);
  const [showForm, setShowForm] = useState<boolean | null>(initialRequest ? true : null);
  const [filter, setFilter] = useState<Filter>("all");

  const refresh = useCallback(() => {
    agentApi.list().then((data) => {
      setJobs(data.items);
      setListError("");
      setBlocked(false);
      // Lần đầu: chưa có ca nào thì mở sẵn form.
      setShowForm((current) => current ?? !data.items.length);
    }).catch((reason) => {
      // Dịch vụ tắt hoặc tài khoản không đủ quyền: có form cũng không gửi được. Lỗi thoáng qua thì giữ form, kẻo mất chữ đang gõ.
      setBlocked(serviceDown(reason) || (reason instanceof ApiError && reason.status === 403));
      setListError(errorText(reason));
    });
  }, []);

  useEffect(() => {
    if (open) return;
    refresh();
    const timer = window.setInterval(refresh, LIST_POLL_MS);
    return () => window.clearInterval(timer);
  }, [open, refresh]);

  const counts = useMemo(() => {
    const all = jobs ?? [];
    return Object.fromEntries(FILTERS.map((f) => [f.key, all.filter(f.match).length])) as Record<Filter, number>;
  }, [jobs]);
  const shown = useMemo(() => (jobs ?? []).filter(FILTERS.find((f) => f.key === filter)!.match), [jobs, filter]);

  if (open) {
    return <section className="at" aria-label="Agent tự sửa"><JobDetail id={open} onBack={() => navigate(AGENT_HOME)} /></section>;
  }

  return (
    <section className="at" aria-label="Agent tự sửa">
      <header className="at-head">
        <div className="at-head__title">
          <h1>Ca kiểm thử</h1>
          <div className="at-stats">
            <span><b className="num">{counts.running}</b> đang chạy</span>
            <span className={counts.approve ? "is-warn" : undefined}><b className="num">{counts.approve}</b> chờ duyệt</span>
            <span><b className="num">{counts.fixed}</b> đã sửa</span>
          </div>
        </div>
        {blocked || showForm ? null : (
          <button className="btn btn--primary" type="button" onClick={() => setShowForm(true)}>
            <Icon name="plus" size={14} /> Tạo ca mới
          </button>
        )}
      </header>
      {listError ? <ServiceNotice message={listError} /> : null}
      {!blocked && showForm ? (
        <StartForm onCreated={openJob} initialRequest={initialRequest}
                   onCancel={jobs?.length ? () => { setShowForm(false); if (initialRequest) navigate(AGENT_HOME, { replace: true }); } : undefined} />
      ) : null}
      {jobs ? (
        <div className="at-list">
          <div className="seg at-filter" role="tablist" aria-label="Lọc ca">
            {FILTERS.map((f) => (
              <button key={f.key} type="button" role="tab" aria-selected={filter === f.key} onClick={() => setFilter(f.key)}>
                {f.label} <span className="at-filter__n num">{counts[f.key]}</span>
              </button>
            ))}
          </div>
          <JobList jobs={shown} onOpen={openJob} />
        </div>
      ) : null}
    </section>
  );
}
