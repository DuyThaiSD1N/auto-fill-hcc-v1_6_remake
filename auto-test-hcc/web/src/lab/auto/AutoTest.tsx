import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError } from "../../api";
import Icon from "../../components/Icon";
import { Spinner } from "../../components/Status";
import { formatDateTime } from "../../format";
import { agentApi, errorText, serviceDown, type JobKind, type JobSummary, type RequestInfo, type RunMode } from "./api";
import DevJobDetail from "./DevJobDetail";
import JobDetail, { OutcomeTag, StatusTag } from "./JobDetail";
import NewProcedure from "./NewProcedure";

const LIST_POLL_MS = 4000;

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

function StartForm({ onCreated, initialRequestId = "" }: { onCreated: (id: string) => void; initialRequestId?: string }) {
  const [requestId, setRequestId] = useState(initialRequestId);
  const [description, setDescription] = useState(initialRequestId ? "Kiểm thử thủ tục vừa làm trên cổng thật: các ô có điền đúng như kết quả chạy thử không" : "");
  const [info, setInfo] = useState<RequestInfo | null>(null);
  const [lookupError, setLookupError] = useState("");
  const [looking, setLooking] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [runs, setRuns] = useState(5);
  const [maxRounds, setMaxRounds] = useState(3);
  const [reproduce, setReproduce] = useState(true);
  const [mode, setMode] = useState<RunMode>("portal");
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
      setUsername(found.account.username);
    } catch (reason) {
      setLookupError(errorText(reason));
    } finally {
      setLooking(false);
    }
  }, []);

  // Mở từ nút "Kiểm thử trên cổng thật" của job thêm thủ tục: tra luôn req chạy thử.
  useEffect(() => {
    if (initialRequestId) void lookup(initialRequestId);
  }, [initialRequestId, lookup]);

  const ready = !!info && !info.missingFiles.length && description.trim().length >= 5 && !!username.trim() && !!password && !sending;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ready || !info) return;
    setSending(true);
    setError("");
    try {
      const job = await agentApi.create({
        requestId: info.requestId,
        description: description.trim(),
        replayUsername: username.trim(),
        replayPassword: password,
        runs,
        maxRounds,
        reproduce,
        applicant: { applicantFullname: applicantName, applicantIdentityNumber: applicantId, applicantBirthday: "" },
        mode,
      });
      setPassword("");
      onCreated(job.id);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setSending(false);
    }
  }

  return (
    <form className="panel at-start" onSubmit={submit}>
      <div className="at-start__head">
        <h1>Đưa một ca lỗi cho hội đồng agent</h1>
        <p className="muted">Hội đồng đọc lượt điền của req, họp bàn, rồi trọng tài quyết định. Lỗi OCR thì bỏ qua và báo cáo; lỗi ở backend hoặc extension thì sửa rồi chạy lại để kiểm tra.</p>
      </div>
      <div className="at-start__grid">
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
          />
        </label>
        <div className="at-found" aria-live="polite">
          {looking ? <Spinner label="Đang tra req" /> : null}
          {lookupError ? <span className="form-error">{lookupError}</span> : null}
          {info ? (
            <>
              <strong>{info.label}</strong>
              <span className="faint">
                {info.account.username}{info.account.xa ? ` · ${info.account.xa}` : ""}{info.account.tinh ? `, ${info.account.tinh}` : ""}
                {" · "}{info.files.length} tệp · {info.fieldsCount ?? 0} field{info.createdAt ? ` · ${formatDateTime(info.createdAt)}` : ""}
              </span>
              {info.missingFiles.length ? <span className="form-error">Tệp gốc không còn trên đĩa, không chạy lại được.</span> : null}
            </>
          ) : null}
        </div>
      </div>
      <label className="field">
        <span>Lỗi do đâu</span>
        <textarea
          className="input at-textarea"
          rows={3}
          placeholder="Mô tả ô nào sai và đúng ra phải thế nào, ví dụ: ô giới tính bị trống trong khi giấy khai sinh ghi rõ là Nữ"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>
      <fieldset className="at-modes">
        <legend>Chạy kiểm thử ở đâu</legend>
        <label className={mode === "portal" ? "is-on" : undefined}>
          <input type="radio" name="mode" checked={mode === "portal"} onChange={() => setMode("portal")} />
          <span><b>Trên cổng thật</b><small>Bot mở trang chủ Cổng DVC quốc gia trên máy chạy dịch vụ, bạn chỉ cần đăng nhập VNeID. Bot tự vào thủ tục, điền bằng extension, đọc lại form rồi tải lại trang để điền lần sau. Bot không nộp hồ sơ.</small></span>
        </label>
        <label className={mode === "api" ? "is-on" : undefined}>
          <input type="radio" name="mode" checked={mode === "api"} onChange={() => setMode("api")} />
          <span><b>Chỉ gọi backend</b><small>Không cần VNeID, nhanh hơn, nhưng chỉ biết backend trả gì, không biết form nhận được gì, và không sửa được extension.</small></span>
        </label>
      </fieldset>
      <div className="at-start__grid at-start__grid--account">
        <label className="field">
          <span>Tài khoản chạy lại</span>
          <input className="input" autoComplete="off" value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label className="field">
          <span>Mật khẩu tài khoản này</span>
          <span className="field__pw">
            <input className="input" type={showPassword ? "text" : "password"} autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            <button className="btn btn--icon btn--ghost" type="button" onClick={() => setShowPassword((v) => !v)} aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}>
              <Icon name={showPassword ? "eye-off" : "eye"} size={16} />
            </button>
          </span>
        </label>
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
      </div>
      {info?.needsApplicant && mode === "api" ? (
        <fieldset className="at-applicant">
          <legend>Mốc người nộp</legend>
          <p className="at-note">Req này chạy từ trợ lý và ngữ cảnh đã hết hạn sau 24 giờ. Thiếu mốc người nộp thì nhiều thủ tục không phân được vai, chạy lại sẽ ra ít field hơn lượt gốc.</p>
          <div className="at-start__grid at-start__grid--applicant">
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
      <p className="faint at-note">Chạy lại bằng tài khoản này nên các ô theo xã/tỉnh điền theo đơn vị của nó. Mật khẩu chỉ giữ trong bộ nhớ của dịch vụ khi job chạy, không ghi xuống đĩa.</p>
      <label className="lab-check">
        <input type="checkbox" checked={reproduce} onChange={(e) => setReproduce(e.target.checked)} />
        Chạy {runs} lần trước khi họp, để biết lỗi có lặp lại không và OCR có dao động không
      </label>
      {error ? <div className="form-error" role="alert">{error}</div> : null}
      <div className="at-start__actions">
        <button className="btn btn--primary" type="submit" disabled={!ready}>
          {sending ? <Spinner label="Đang tạo" /> : "Bắt đầu"}
        </button>
      </div>
    </form>
  );
}

function JobList({ jobs, onOpen }: { jobs: JobSummary[]; onOpen: (id: string, kind: JobKind) => void }) {
  if (!jobs.length) return <p className="faint at-empty">Chưa có ca nào.</p>;
  return (
    <div className="table-wrap panel">
      <table className="mini-table at-jobs">
        <thead>
          <tr>
            <th>Mã req / key</th>
            <th>Thủ tục</th>
            <th>Mô tả</th>
            <th>Kết quả</th>
            <th className="at-num">Vòng</th>
            <th className="at-num">Chi phí</th>
            <th>Lúc</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id}>
              <td>
                <button className="at-link mono" type="button" onClick={() => onOpen(job.id, job.kind ?? "fix")}>{job.requestId}</button>
                {job.kind === "dev" ? <span className="at-tag at-tag--plain dv-kind">Thêm thủ tục</span> : null}
              </td>
              <td className="at-clip" title={job.label}>{job.label}</td>
              <td className="at-clip" title={job.description}>{job.description}</td>
              <td>{job.outcome ? <OutcomeTag outcome={job.outcome} /> : <StatusTag status={job.status} stage={job.stage} kind={job.kind} />}</td>
              <td className="at-num num">{job.rounds}</td>
              <td className="at-num num">${job.cost.usd.toFixed(2)}</td>
              <td className="num faint">{formatDateTime(job.createdAt)}</td>
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
  const [open, setOpen] = useState<{ id: string; kind: JobKind } | null>(null);
  const [mode, setMode] = useState<JobKind>("fix");
  const [prefill, setPrefill] = useState("");

  const refresh = useCallback(() => {
    agentApi.list().then((data) => {
      setJobs(data.items);
      setListError("");
      setBlocked(false);
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

  if (open) {
    return (
      <section className="at" aria-label="Agent tự sửa">
        {open.kind === "dev" ? (
          <DevJobDetail
            id={open.id}
            onBack={() => setOpen(null)}
            onTestPortal={(requestId) => { setPrefill(requestId); setMode("fix"); setOpen(null); }}
          />
        ) : <JobDetail id={open.id} onBack={() => setOpen(null)} />}
      </section>
    );
  }

  return (
    <section className="at" aria-label="Agent tự sửa">
      {listError ? <ServiceNotice message={listError} /> : null}
      {blocked ? null : (
        <>
          <div className="tabs dv-modes" role="tablist" aria-label="Loại việc">
            <button type="button" role="tab" aria-selected={mode === "fix"} onClick={() => setMode("fix")}>Sửa lỗi một ca</button>
            <button type="button" role="tab" aria-selected={mode === "dev"} onClick={() => setMode("dev")}>Thêm thủ tục mới</button>
          </div>
          {mode === "fix"
            ? <StartForm key={prefill} initialRequestId={prefill} onCreated={(id) => setOpen({ id, kind: "fix" })} />
            : <NewProcedure onCreated={(id) => setOpen({ id, kind: "dev" })} />}
        </>
      )}
      {jobs ? (
        <div className="at-list">
          <h2 className="section-title">Các việc đã giao</h2>
          <JobList jobs={jobs} onOpen={(id, kind) => setOpen({ id, kind })} />
        </div>
      ) : null}
    </section>
  );
}
