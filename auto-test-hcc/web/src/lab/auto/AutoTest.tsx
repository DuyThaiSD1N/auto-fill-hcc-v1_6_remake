import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { ApiError } from "../../api";
import Icon from "../../components/Icon";
import { Spinner } from "../../components/Status";
import { formatDateTime } from "../../format";
import { agentApi, errorText, serviceDown, type FixTarget, type JobSummary, type RequestInfo, type RunMode, type RunnerInfo } from "./api";
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
  { value: "troly", label: "Trợ lý hồ sơ", hint: "Sửa backend, gồm kênh trợ lý; chạy thêm tests/handfree. Chỉ chạy kiểu gọi backend." },
];

const MODES: { value: RunMode; label: string; hint: string }[] = [
  { value: "portal", label: "Cổng thật", hint: "Bot tự vào thủ tục và điền trên Cổng DVC, bạn chỉ đăng nhập VNeID. Bot không nộp hồ sơ." },
  { value: "api", label: "Chỉ gọi backend", hint: "Nhanh, không cần VNeID, nhưng không kiểm được extension." },
];

type BotHost = "mine" | "service";

const BOT_HOSTS: { value: BotHost; label: string; hint: string }[] = [
  { value: "mine", label: "Máy của tôi", hint: "Chromium của bot mở trên máy bạn đang dùng, bạn đăng nhập VNeID ngay ở đây." },
  { value: "service", label: "Máy chạy dịch vụ", hint: "Chromium mở trên máy chạy dịch vụ agent. Chỉ chọn khi bạn đang ngồi ở máy đó." },
];

const RUNNER_KEY = "autotest_runner";

function loadRunner(): { id: string; token: string } | null {
  try {
    const saved = JSON.parse(localStorage.getItem(RUNNER_KEY) || "null");
    return saved && typeof saved.id === "string" && typeof saved.token === "string" ? saved : null;
  } catch {
    return null;
  }
}

function storeRunner(value: { id: string; token: string } | null) {
  try {
    if (value) localStorage.setItem(RUNNER_KEY, JSON.stringify(value));
    else localStorage.removeItem(RUNNER_KEY);
  } catch {
    /* trình duyệt chặn lưu: lệnh vẫn hiện trên trang, chỉ mất khi tải lại */
  }
}

/** Nối máy người dùng làm nơi chạy Chromium của bot: cấp token, hiện lệnh chạy trình chạy, theo dõi trạng thái nối. */
function RunnerBox({ onReady }: { onReady: (runner: RunnerInfo | null) => void }) {
  const [saved, setSaved] = useState(loadRunner);
  const [info, setInfo] = useState<RunnerInfo | null>(null);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!saved) {
      setInfo(null);
      onReady(null);
      return undefined;
    }
    let alive = true;
    const tick = async () => {
      try {
        const found = await agentApi.runner(saved.id);
        if (!alive) return;
        setInfo(found);
        setError("");
        onReady(found.connected ? found : null);
      } catch (reason) {
        if (!alive) return;
        onReady(null);
        if (reason instanceof ApiError && reason.status === 404) {
          storeRunner(null);
          setSaved(null);
          setError("Token cũ đã hết hạn, bấm Nối máy này để lấy lệnh mới.");
        } else {
          setError(errorText(reason));
        }
      }
    };
    void tick();
    const timer = window.setInterval(() => void tick(), 3000);
    return () => { alive = false; window.clearInterval(timer); };
  }, [saved, onReady]);

  const create = async () => {
    setCreating(true);
    setError("");
    try {
      const made = await agentApi.createRunner();
      const value = { id: made.id, token: made.token ?? "" };
      storeRunner(value);
      setSaved(value);
      setInfo(made);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setCreating(false);
    }
  };

  const command = saved ? `python bot_runner.py --server ${window.location.origin} --token ${saved.token}` : "";
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setError("Trình duyệt không cho chép, hãy bôi đen lệnh rồi chép tay.");
    }
  };

  return (
    <div className="at-runner">
      {info?.connected ? (
        <p className="at-runner__state">
          <span className="at-tag at-tag--ok">Đã nối</span>
          <span>Máy <strong>{info.machine || "?"}</strong>{info.chromium ? ` · ${info.chromium}` : ""}. Giữ cửa sổ dòng lệnh trình chạy mở trong lúc chạy ca.</span>
        </p>
      ) : saved ? (
        <p className="at-runner__state">
          <span className="at-tag at-tag--warn">Chờ máy nối</span>
          <span className="faint">Chạy lệnh dưới đây trên máy này. Trang tự nhận khi trình chạy nối xong.</span>
        </p>
      ) : (
        <p className="at-runner__state faint">Máy này chưa nối làm nơi chạy Chromium của bot.</p>
      )}
      {saved && !info?.connected ? (
        <ol className="at-runner__steps">
          <li>
            Cài một lần (Python 3.10 trở lên): <code>pip install playwright websockets</code> rồi <code>python -m playwright install chromium</code>
          </li>
          <li>
            Tải <a href="/agent-api/runner/script" download="bot_runner.py">bot_runner.py</a> về máy.
          </li>
          <li>
            Mở dòng lệnh ở thư mục chứa tệp vừa tải, chạy:
            <span className="at-runner__cmd">
              <code className="mono">{command}</code>
              <button className="btn btn--sm" type="button" onClick={() => void copy()}>{copied ? "Đã chép" : "Chép"}</button>
            </span>
          </li>
        </ol>
      ) : null}
      <div className="at-runner__actions">
        {!saved ? (
          <button className="btn btn--sm btn--primary" type="button" disabled={creating} onClick={() => void create()}>
            {creating ? <Spinner label="Đang tạo" /> : "Nối máy này"}
          </button>
        ) : (
          <button className="btn btn--sm" type="button" onClick={() => { storeRunner(null); setSaved(null); setInfo(null); }}>
            Tạo lệnh mới
          </button>
        )}
      </div>
      {error ? <p className="form-error">{error}</p> : null}
    </div>
  );
}

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
            {info.portalRows ? <span>{info.portalRows} dòng trên cổng</span> : null}
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

function StartForm({ onCreated, onCancel }: { onCreated: (id: string) => void; onCancel?: () => void }) {
  const [requestId, setRequestId] = useState("");
  const [description, setDescription] = useState("");
  const [info, setInfo] = useState<RequestInfo | null>(null);
  const [lookupError, setLookupError] = useState("");
  const [looking, setLooking] = useState(false);
  const [runs, setRuns] = useState(5);
  const [maxRounds, setMaxRounds] = useState(3);
  const [reproduce, setReproduce] = useState(true);
  const [mode, setMode] = useState<RunMode>("portal");
  const [botHost, setBotHost] = useState<BotHost>("mine");
  const [runner, setRunner] = useState<RunnerInfo | null>(null);
  const onRunner = useCallback((value: RunnerInfo | null) => setRunner(value), []);
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
      if (troly) setMode("api");
    } catch (reason) {
      setLookupError(errorText(reason));
    } finally {
      setLooking(false);
    }
  }, []);

  const pickTarget = (value: FixTarget) => {
    setTarget(value);
    if (value === "troly") setMode("api");
  };

  const needsRunner = mode === "portal" && botHost === "mine";
  const ready = !!info && !info.missingFiles.length && description.trim().length >= 5 && !sending && (!needsRunner || !!runner);

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
        mode,
        target,
        runnerId: needsRunner && runner ? runner.id : undefined,
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
        <Choice label="Chạy kiểm" value={mode} options={MODES} onChange={setMode} disabled={(v) => v === "portal" && target === "troly"} />
      </div>
      {mode === "portal" ? (
        <fieldset className="at-runner-box">
          <legend>Chromium của bot chạy trên</legend>
          <Choice label="" value={botHost} options={BOT_HOSTS} onChange={setBotHost} />
          {botHost === "mine" ? <RunnerBox onReady={onRunner} /> : null}
        </fieldset>
      ) : null}
      {info?.needsApplicant && mode === "api" ? (
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

export default function AutoTest() {
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [listError, setListError] = useState("");
  const [blocked, setBlocked] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const [showForm, setShowForm] = useState<boolean | null>(null);
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
    return <section className="at" aria-label="Agent tự sửa"><JobDetail id={open} onBack={() => setOpen(null)} /></section>;
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
      {!blocked && showForm ? <StartForm onCreated={setOpen} onCancel={jobs?.length ? () => setShowForm(false) : undefined} /> : null}
      {jobs ? (
        <div className="at-list">
          <div className="seg at-filter" role="tablist" aria-label="Lọc ca">
            {FILTERS.map((f) => (
              <button key={f.key} type="button" role="tab" aria-selected={filter === f.key} onClick={() => setFilter(f.key)}>
                {f.label} <span className="at-filter__n num">{counts[f.key]}</span>
              </button>
            ))}
          </div>
          <JobList jobs={shown} onOpen={setOpen} />
        </div>
      ) : null}
    </section>
  );
}
