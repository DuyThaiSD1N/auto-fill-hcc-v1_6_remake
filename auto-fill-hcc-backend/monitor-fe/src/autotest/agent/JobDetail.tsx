import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import CopyButton from "../../components/CopyButton";
import Icon from "../../components/Icon";
import { ErrorNotice, PageLoading, Spinner } from "../../components/Status";
import { formatClock, formatDateTime } from "../../format";
import type { Batch } from "./engine";
import Results from "./Results";
import {
  agentApi, errorText, toBatch,
  type ApprovalResult, type Check, type Decision, type Evaluation, type ExtensionTests, type FullTests, type Job, type Opinion,
  type Outcome, type Round, type RunBrief, type Verdict,
} from "./api";

const POLL_MS = 2000;

const STAGES: { key: string; label: string; visited: (job: Job) => boolean }[] = [
  { key: "collect", label: "Thu thập", visited: () => true },
  { key: "reproduce", label: "Chạy lại", visited: (j) => !!j.reproduce },
  { key: "meeting", label: "Họp", visited: (j) => j.rounds.length > 0 },
  { key: "arbiter", label: "Trọng tài", visited: (j) => j.rounds.some((r) => r.decision) },
  { key: "plan", label: "Duyệt kế hoạch", visited: (j) => j.rounds.some((r) => r.planReviews?.length) },
  { key: "fix", label: "Sửa", visited: (j) => j.rounds.some((r) => r.fix) },
  { key: "test", label: "Test", visited: (j) => j.rounds.some((r) => r.tests) },
  { key: "approve", label: "Duyệt", visited: (j) => j.rounds.some((r) => r.approval) },
  { key: "deploy", label: "Build", visited: (j) => j.rounds.some((r) => r.deploy) },
  { key: "retest", label: "Chạy kiểm", visited: (j) => j.rounds.some((r) => r.retest) },
  { key: "report", label: "Kết luận", visited: (j) => !!j.report },
];

const CAUSES: Record<string, string> = {
  ocr: "Lỗi OCR",
  mapper: "Lỗi mapper",
  llm: "LLM trích sai",
  thanh_tra: "Thanh tra soát sai",
  catalog: "Danh mục, địa giới",
  extension: "Extension hoặc cổng",
  input: "Giấy tờ thiếu thông tin",
  not_a_bug: "Không phải lỗi",
  unknown: "Chưa rõ",
};

const DECISIONS: Record<Decision["decision"], string> = {
  skip_ocr: "Bỏ qua vì OCR đọc sai",
  fix_code: "Sửa code",
  report_only: "Không sửa, chỉ báo cáo",
};

const OUTCOMES: Record<Outcome, { label: string; tone: "ok" | "warn" | "bad" | "plain" }> = {
  fixed: { label: "Đã sửa", tone: "ok" },
  skipped_ocr: { label: "Bỏ qua: lỗi OCR", tone: "warn" },
  report_only: { label: "Chỉ báo cáo", tone: "plain" },
  not_reproduced: { label: "Không tái hiện", tone: "plain" },
  need_human: { label: "Cần người xem", tone: "bad" },
  not_approved: { label: "Không được duyệt", tone: "warn" },
};

const STANCES: Record<NonNullable<Opinion["stance"]>, string> = { agree: "Đồng ý", partly: "Đồng ý một phần", disagree: "Phản đối" };

const OPS: Record<string, string> = {
  equals: "phải bằng",
  contains: "phải chứa",
  not_contains: "không được chứa",
  empty: "phải trống",
  not_empty: "không được trống",
  regex: "khớp mẫu",
};

const STATUS_LABEL: Record<Job["status"], string> = {
  queued: "Đang xếp hàng",
  running: "Đang chạy",
  done: "Xong",
  failed: "Lỗi",
  stopped: "Đã dừng",
};

// ---- Lời giải thích cho tester không biết code -------------------------------------------------------------------

/** Các bước dữ liệu đi qua, nói bằng lời thường. `cause` = nguyên nhân hội đồng gán khi lỗi nằm ở bước đó. */
type Step = { key: string; label: string; hint: string; causes: string[] };

function dataPath(attach: boolean, thanhTra: boolean): Step[] {
  if (attach) {
    return [
      { key: "giay", label: "Giấy tờ", hint: "Ảnh / PDF người dân tải lên", causes: ["input"] },
      { key: "ocr", label: "Đọc chữ", hint: "Máy đọc chữ trên ảnh (OCR)", causes: ["ocr"] },
      { key: "ai", label: "AI nhận loại giấy", hint: "AI xem trang nào là giấy gì", causes: ["llm"] },
      { key: "xep", label: "Xếp vào dòng", hint: "Chọn dòng đính kèm cho từng giấy", causes: ["mapper", "catalog"] },
      { key: "cong", label: "Đính lên cổng", hint: "Extension tải tệp lên đúng dòng", causes: ["extension"] },
    ];
  }
  return [
    { key: "giay", label: "Giấy tờ", hint: "Ảnh / PDF người dân tải lên", causes: ["input"] },
    { key: "ocr", label: "Đọc chữ", hint: "Máy đọc chữ trên ảnh (OCR)", causes: ["ocr"] },
    { key: "ai", label: "AI trích thông tin", hint: "AI tìm họ tên, ngày sinh… trong chữ đã đọc", causes: ["llm"] },
    { key: "ghep", label: "Ghép vào ô", hint: "Đổi thông tin thành giá trị từng ô của form", causes: ["mapper", "catalog"] },
    ...(thanhTra ? [{ key: "thanhtra", label: "Thanh tra soát lại", hint: "AI thứ hai đọc lại giấy, chỉ sửa ô khi có bằng chứng", causes: ["thanh_tra"] }] : []),
    { key: "cong", label: "Điền lên cổng", hint: "Extension gõ giá trị vào form trên cổng", causes: ["extension"] },
  ];
}

const CAUSE_PLAIN: Record<string, string> = {
  ocr: "Máy đọc chữ đọc sai chữ trên giấy (ảnh mờ, nghiêng, chữ viết tay…). Code không biết được chữ đúng nên không sửa code.",
  llm: "Chữ đọc ra đúng nhưng AI lấy sai hoặc bỏ sót thông tin.",
  mapper: "AI lấy đúng thông tin nhưng bước ghép vào ô của form làm sai.",
  thanh_tra: "Lượt điền đầu ổn, nhưng bước thanh tra soát lại đã đổi ô thành sai, hoặc bắt trượt đúng loại lỗi nó phải bắt.",
  catalog: "Tên xã / phường, tỉnh hoặc mục chọn không khớp danh sách của cổng (thường do sáp nhập địa giới).",
  extension: "Hệ thống tính đúng nhưng khi điền lên cổng thì ô không nhận. Phần này người sửa extension phải làm.",
  input: "Giấy tờ tải lên không có thông tin này.",
  not_a_bug: "Hệ thống làm đúng; form của cổng vốn như vậy hoặc kỳ vọng chưa đúng.",
  unknown: "Chưa xác định được lỗi nằm ở bước nào.",
};

function stagePlain(stage: string, runs: number): string {
  const map: Record<string, string> = {
    collect: "Đang lấy giấy tờ và kết quả điền của lượt bị báo lỗi.",
    reproduce: `Đang cho hệ thống điền lại ${runs} lần với đúng giấy tờ đó để xem lỗi có lặp lại không.`,
    meeting: "Các AI phân tích đang đọc giấy tờ và code để tìm lỗi nằm ở bước nào.",
    arbiter: "AI trọng tài đang cân các ý kiến và quyết định có sửa hay không.",
    plan: "Đang chờ bạn duyệt kế hoạch sửa.",
    fix: "AI đang sửa code theo kế hoạch đã duyệt.",
    test: "Đang chạy test tự động để chắc bản sửa không làm hỏng chỗ khác.",
    approve: "Đang chờ bạn duyệt bản sửa.",
    deploy: "Đang dựng hệ thống thử với bản sửa.",
    retest: `Đang cho hệ thống điền lại ${runs} lần với bản sửa để chấm.`,
  };
  return map[stage] ?? "Đang chạy.";
}

function outcomePlain(outcome: Outcome, runs: number): string {
  const map: Record<Outcome, string> = {
    fixed: `Đã sửa: hệ thống thử điền lại ${runs} lần với bản sửa và lần nào cũng đúng. Bản sửa chờ người phát triển gộp vào bản chính.`,
    skipped_ocr: "Không sửa code: máy đọc chữ đọc sai chữ trên giấy. Nên chụp / scan lại giấy rõ hơn rồi điền lại.",
    report_only: "Không sửa code. Lý do ở phần kết luận; nếu cần sửa thì người phát triển làm tiếp.",
    not_reproduced: "Điền lại nhiều lần đều đúng nên không có gì để sửa. Lỗi có thể đã được sửa trước đó, hoặc chỉ thỉnh thoảng mới xảy ra.",
    need_human: "Đã thử sửa nhưng chưa đạt sau số vòng cho phép. Cần người phát triển xem tiếp.",
    not_approved: "Kế hoạch hoặc bản sửa không được duyệt nên đã dừng, code giữ nguyên.",
  };
  return map[outcome];
}

/** Nguyên nhân để tô trên sơ đồ: trọng tài đã quyết thì theo trọng tài, chưa thì theo số đông hội đồng. */
function currentCause(job: Job): { cause: string; final: boolean } | null {
  const rounds = [...job.rounds].reverse();
  const decided = rounds.find((r) => r.decision)?.decision;
  if (decided) return { cause: decided.cause, final: true };
  const opinions = rounds.find((r) => r.opinions.length)?.opinions.filter((o) => o.cause && !o.error) ?? [];
  if (!opinions.length) return null;
  const count: Record<string, number> = {};
  for (const o of opinions) count[o.cause!] = (count[o.cause!] ?? 0) + 1;
  const [cause] = Object.entries(count).sort((a, b) => b[1] - a[1])[0];
  return { cause, final: false };
}

function DataPath({ steps, cause }: { steps: Step[]; cause: string | null }) {
  return (
    <ol className="at-path" aria-label="Đường đi của dữ liệu">
      {steps.map((step) => {
        const hit = !!cause && step.causes.includes(cause);
        return (
          <li key={step.key} className={`at-path__step${hit ? " is-hit" : ""}${step.key === "thanhtra" ? " is-tt" : ""}`}>
            <b>{step.label}</b>
            <small>{step.hint}</small>
            {hit ? <span className="at-path__flag">Lỗi ở đây</span> : null}
          </li>
        );
      })}
    </ol>
  );
}

function thanhTraOriginal(job: Job): string | null {
  const info = job.case.thanhTra;
  if (!info?.has) return null;
  if (info.ran === "done") {
    const changed = info.patched ?? 0;
    return changed ? `Ở lượt bị báo lỗi, thanh tra đã sửa lại ${changed} ô sau khi điền lần đầu.` : "Ở lượt bị báo lỗi, thanh tra đã soát nhưng không sửa ô nào.";
  }
  if (info.ran) return "Ở lượt bị báo lỗi, thanh tra chạy không xong (quá giờ hoặc lỗi) nên form giữ kết quả điền lần đầu.";
  return "Ở lượt bị báo lỗi, thanh tra không chạy (extension cũ hoặc tài khoản chưa bật), nên khi chạy lại cũng tắt thanh tra cho giống.";
}

/** Khung đầu trang cho tester: lỗi ở bước nào, hệ thống đang / đã làm gì, bạn cần làm gì. Không thuật ngữ, không tên file. */
function PlainSummary({ job }: { job: Job }) {
  const attach = job.settings.kind === "attach";
  const thanhTra = !attach && !!job.case.thanhTra?.has;
  const picked = currentCause(job);
  const decision = [...job.rounds].reverse().find((r) => r.decision)?.decision ?? null;
  const running = job.status === "queued" || job.status === "running";
  const lastRound = job.rounds[job.rounds.length - 1];
  const before = job.rounds.find((r) => r.precheck)?.precheck;
  const after = [...job.rounds].reverse().find((r) => r.retest?.evaluation)?.retest?.evaluation;
  const conclusion = job.report?.plain ?? decision?.plain ?? null;
  let next = "";
  if (job.planApproval && running) next = "Bạn cần đọc kế hoạch sửa ở khung vàng bên dưới rồi chọn Đồng ý, Lập lại theo góp ý, hoặc Dừng.";
  else if (job.approval && running) next = "Bạn cần đọc bản sửa ở khung vàng bên dưới rồi chọn Đồng ý, Làm lại theo góp ý, hoặc Dừng.";
  else if (running) next = stagePlain(job.stage, job.settings.runs);
  else if (job.outcome) next = outcomePlain(job.outcome, job.settings.runs);
  else if (job.status === "failed") next = "Ca dừng vì lỗi hệ thống (xem dòng đỏ bên dưới). Báo người phát triển kèm mã ca.";
  else if (job.status === "stopped") next = "Ca đã dừng, mọi thay đổi đã hoàn tác.";
  return (
    <section className="at-plain" aria-label="Tóm tắt dễ hiểu">
      <h2 className="at-plain__title">Tóm tắt dễ hiểu</h2>
      <DataPath steps={dataPath(attach, thanhTra)} cause={picked?.cause ?? null} />
      <dl className="at-plain__list">
        <div>
          <dt>Lỗi nằm ở đâu</dt>
          <dd>
            {picked ? (
              <>
                {!picked.final ? <span className="faint">Hội đồng đang nghiêng về: </span> : null}
                {CAUSE_PLAIN[picked.cause] ?? CAUSES[picked.cause] ?? picked.cause}
              </>
            ) : <span className="faint">Chưa phân tích xong.</span>}
          </dd>
        </div>
        {conclusion ? (
          <div>
            <dt>Kết luận</dt>
            <dd>{conclusion}</dd>
          </div>
        ) : null}
        {thanhTra ? (
          <div>
            <dt>Thanh tra</dt>
            <dd>
              Thủ tục này có <b>thanh tra</b>: sau khi điền lần đầu, một AI khác đọc lại giấy tờ độc lập và chỉ sửa ô khi thấy bằng chứng
              trên giấy. {thanhTraOriginal(job)}
              {decision?.balance ? <span className="at-plain__balance">Vì sao sửa ở bước này: {decision.balance}</span> : null}
            </dd>
          </div>
        ) : null}
        {before || after ? (
          <div>
            <dt>Kết quả điền thử</dt>
            <dd>
              {before ? <span>Trước khi sửa: đúng <b>{before.passed}/{before.total}</b> lần. </span> : null}
              {after ? <span>Sau khi sửa: đúng <b className={after.allPass ? "lab-ok" : "ef-red"}>{after.passed}/{after.total}</b> lần.</span> : null}
            </dd>
          </div>
        ) : null}
        {next ? (
          <div>
            <dt>{running ? "Đang làm" : "Tiếp theo"}</dt>
            <dd>{next}</dd>
          </div>
        ) : null}
      </dl>
      {lastRound?.decision?.acceptance?.length && !after ? (
        <details className="at-more">
          <summary>Máy sẽ kiểm những gì sau khi sửa ({lastRound.decision.acceptance.length})</summary>
          <ul>{lastRound.decision.acceptance.map((c, i) => <li key={i}>{c.why || `${c.field} ${checkText(c)}`}</li>)}</ul>
        </details>
      ) : null}
      <details className="at-more">
        <summary>Giải thích từ ngữ</summary>
        <ul className="at-glossary">
          <li><b>Đọc chữ (OCR)</b>: máy đọc chữ trên ảnh giấy tờ thành văn bản.</li>
          <li><b>AI trích thông tin</b>: AI đọc văn bản đó và lấy ra họ tên, ngày sinh, địa chỉ…</li>
          <li><b>Ghép vào ô (mapper)</b>: code đổi thông tin thành đúng giá trị từng ô của form, ví dụ tách ngày, chọn đúng xã trong danh sách.</li>
          {thanhTra ? <li><b>Thanh tra</b>: sau lần điền đầu, AI khác đọc lại giấy mà không xem kết quả lần đầu. Chỗ hai bên lệch nhau, "toà án" xem bằng chứng trên giấy rồi mới quyết định có sửa ô hay không.</li> : null}
          <li><b>Hội đồng</b>: vài AI phân tích độc lập rồi phản biện nhau; <b>trọng tài</b> là AI ra quyết định cuối.</li>
          <li><b>Chạy lại {job.settings.runs} lần</b>: cho hệ thống điền lại bằng đúng giấy tờ đó, mỗi lần đọc chữ mới, để xem lỗi có lặp lại không.</li>
          <li><b>Tiêu chí</b>: điều máy tự kiểm trên kết quả điền, ví dụ "ô ngày sinh phải bằng 01/02/1990". Đạt đủ mọi lần mới tính là sửa được.</li>
        </ul>
      </details>
    </section>
  );
}

/** Chế độ dễ hiểu: phần kỹ thuật thu gọn vào một mục mở được; chế độ đầy đủ: hiện như cũ. */
function Tech({ simple, label, children }: { simple: boolean; label: string; children: ReactNode }) {
  if (!simple) return <>{children}</>;
  return (
    <details className="at-more at-tech">
      <summary>{label}</summary>
      <div className="at-tech__body">{children}</div>
    </details>
  );
}

type View = "simple" | "full";
const VIEW_KEY = "autotest.agent.view";

function useView(): [View, (view: View) => void] {
  const [view, setView] = useState<View>(() => {
    try {
      return window.localStorage.getItem(VIEW_KEY) === "full" ? "full" : "simple";
    } catch {
      return "simple";
    }
  });
  const change = useCallback((next: View) => {
    setView(next);
    try {
      window.localStorage.setItem(VIEW_KEY, next);
    } catch {
      /* trình duyệt chặn lưu: chỉ giữ trong phiên */
    }
  }, []);
  return [view, change];
}

export function OutcomeTag({ outcome }: { outcome: Outcome }) {
  const item = OUTCOMES[outcome];
  return <span className={`at-tag at-tag--${item.tone}`}>{item.label}</span>;
}

export function StatusTag({ status, stage }: { status: Job["status"]; stage: string }) {
  if (status === "running" && stage === "approve") return <span className="at-tag at-tag--warn">Chờ bạn duyệt bản sửa</span>;
  if (status === "running" && stage === "plan") return <span className="at-tag at-tag--warn">Chờ bạn duyệt kế hoạch</span>;
  const tone = status === "failed" ? "bad" : "plain";
  const name = STAGES.find((s) => s.key === stage)?.label;
  return <span className={`at-tag at-tag--${tone}`}>{STATUS_LABEL[status]}{status === "running" && name ? `: ${name}` : ""}</span>;
}

function StageRail({ job }: { job: Job }) {
  const live = job.status === "running" || job.status === "queued";
  const relevant = STAGES;
  // Ca đã xong: chỉ giữ các bước đã đi qua (ca Chỉ báo cáo không hiện Sửa / Test / Duyệt / Build rỗng).
  const stages = live ? relevant : relevant.filter((s) => s.visited(job) || s.key === job.stage);
  const index = stages.findIndex((s) => s.key === job.stage);
  return (
    <ol className="at-rail" aria-label="Tiến trình">
      {stages.map((stage, i) => {
        const now = live && i === index;
        const state = now ? "now" : stage.visited(job) && (i < index || !live) ? "done" : i < index ? "skip" : "todo";
        return (
          <li key={stage.key} className={`at-rail__item is-${state}`} aria-current={now ? "step" : undefined}>
            <span className="at-rail__dot">{state === "done" ? <Icon name="check" size={11} /> : null}</span>
            {stage.label}
          </li>
        );
      })}
    </ol>
  );
}

/** Trọng tài chọn sửa code: dừng lại để người dùng đọc kế hoạch, đồng ý thì agent mới sửa. */
function PlanBox({ job, busy, simple, onDecide }: { job: Job; busy: boolean; simple: boolean; onDecide: (decision: Verdict, note: string) => void }) {
  const [note, setNote] = useState("");
  const pending = job.planApproval;
  if (!pending || job.status !== "running") return null;
  const decision = job.rounds.find((r) => r.n === pending.round)?.decision;
  if (!decision) return null;
  const deadline = new Date(new Date(pending.since).getTime() + pending.timeoutMin * 60_000).toISOString();
  const text = note.trim();
  return (
    <section className="at-approve at-plan-box" role="alert" aria-label="Duyệt kế hoạch sửa">
      <div>
        <strong>Chờ bạn duyệt kế hoạch sửa vòng {pending.round}{pending.revision > 1 ? ` · bản lập lại lần ${pending.revision - 1}` : ""}</strong>
        <p>Trọng tài đề nghị sửa code theo kế hoạch dưới đây. Agent chỉ bắt đầu sửa khi bạn đồng ý; chưa có dòng code nào bị đổi.</p>
        <p className="faint">Quá {formatClock(deadline)} không ai duyệt thì ca tự dừng.</p>
      </div>
      <div className="at-plan-box__body">
        <p className="at-plan-box__cause">
          <span className="at-tag at-tag--plain">{CAUSES[decision.cause] ?? decision.cause}</span>
        </p>
        {decision.plain ? <p className="at-plain__lead">{decision.plain}</p> : null}
        {decision.balance ? <p className="muted"><b>Vì sao sửa ở bước này (thủ tục có thanh tra):</b> {decision.balance}</p> : null}
        {decision.acceptance?.length ? (
          <div>
            <b>Máy sẽ tự kiểm sau khi sửa</b>
            <ul className="at-plan-box__checks">
              {decision.acceptance.map((c, i) => (
                simple && c.why
                  ? <li key={i}>{c.why} <span className="faint mono">({c.field} {checkText(c)})</span></li>
                  : <li key={i}><span className="mono">{c.field}</span> {OPS[c.op] ?? c.op} {c.expected ? <b>{c.expected}</b> : null}{c.why ? <span className="faint"> · {c.why}</span> : null}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <Tech simple={simple} label="Chi tiết kỹ thuật của kế hoạch">
          <Clamp text={decision.reason} />
          {decision.plan ? (
            <div className="at-plan">
              <b>Kế hoạch:</b> {decision.plan.summary}
              <ol>{decision.plan.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
              {decision.plan.files.length ? <p className="mono at-refs">{decision.plan.files.join("  ")}</p> : null}
              {decision.plan.test ? <p className="muted"><b>Test:</b> {decision.plan.test}</p> : null}
            </div>
          ) : null}
          {decision.risk ? <p className="muted"><b>Rủi ro:</b> {decision.risk}</p> : null}
        </Tech>
      </div>
      <div className="at-decide-bar">
      <label className="field">
        <span>Góp ý cho trọng tài (bắt buộc khi yêu cầu lập lại)</span>
        <textarea
          className="input at-textarea"
          rows={2}
          maxLength={3000}
          placeholder="Ví dụ: chỉ sửa mapper của thủ tục này, không đụng engine điền chung"
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />
      </label>
      <div className="at-approve__actions">
        <button className="btn btn--primary" type="button" disabled={busy} onClick={() => onDecide("approve", text)}>
          <Icon name="check" size={14} /> Đồng ý kế hoạch vòng {pending.round}, cho sửa
        </button>
        <button
          className="btn"
          type="button"
          disabled={busy || !pending.canRevise || !text}
          title={!pending.canRevise ? "Đã hết lượt lập lại trong vòng này" : !text ? "Ghi góp ý trước" : undefined}
          onClick={() => onDecide("retry", text)}
        >
          <Icon name="refresh" size={14} /> Lập lại kế hoạch theo góp ý
        </button>
        <button
          className="btn"
          type="button"
          disabled={busy}
          onClick={() => { if (window.confirm("Không sửa theo kế hoạch này và dừng ca?")) onDecide("reject", text); }}
        >
          <Icon name="x" size={14} /> Không sửa, dừng
        </button>
      </div>
      </div>
    </section>
  );
}

/** Bản sửa đã qua test nhưng chưa build, chưa nạp extension: phải có người đọc patch và bấm một trong ba nút. */
function ApprovalBox({ job, busy, simple, onDecide }: { job: Job; busy: boolean; simple: boolean; onDecide: (decision: Verdict, note: string) => void }) {
  const [note, setNote] = useState("");
  const pending = job.approval;
  if (!pending || job.status !== "running") return null;
  const round = job.rounds.find((r) => r.n === pending.round);
  const deadline = new Date(new Date(pending.since).getTime() + pending.timeoutMin * 60_000).toISOString();
  const text = note.trim();
  return (
    <section className="at-approve" role="alert" aria-label="Duyệt bản sửa">
      <div>
        <strong>Chờ bạn duyệt bản sửa{job.rounds.length > 1 ? ` vòng ${pending.round}` : ""}</strong>
        <p>
          Agent đã sửa xong và test đã qua. Code đang nằm trong thư mục làm việc, chưa build Docker, chưa nạp vào extension. Bạn đồng ý
          thì hệ thống mới build rồi chạy lại {job.settings.runs} lần để chấm.
        </p>
        <p className="faint">Quá {formatClock(deadline)} không ai duyệt thì tự hoàn tác và kết thúc job.</p>
      </div>
      {round?.fix?.plain ? <p className="at-plain__lead">{round.fix.plain}</p> : null}
      {round ? <ChecksLine round={round} /> : null}
      <Tech simple={simple} label="Chi tiết kỹ thuật: file đã sửa, test, patch">
        {round?.fix?.summary ? <p className="at-approve__summary">{round.fix.summary}</p> : null}
        <p className="mono at-refs">{pending.files.join("  ")}</p>
        {round ? <Checks round={round} /> : null}
        {round?.fix?.patch ? <Patch patch={round.fix.patch} /> : null}
      </Tech>
      <div className="at-decide-bar">
      <label className="field">
        <span>Góp ý cho hội đồng (bắt buộc khi chọn làm lại)</span>
        <textarea
          className="input at-textarea"
          rows={3}
          maxLength={3000}
          placeholder="Ví dụ: đừng sửa engine điền chung, khoanh theo riêng thủ tục này"
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />
      </label>
      <div className="at-approve__actions">
        <button className="btn btn--primary" type="button" disabled={busy} onClick={() => onDecide("approve", text)}>
          <Icon name="check" size={14} /> Đồng ý, build và chạy kiểm
        </button>
        <button
          className="btn"
          type="button"
          disabled={busy || !pending.canRetry || !text}
          title={!pending.canRetry ? "Đây là vòng cuối" : !text ? "Ghi góp ý trước" : undefined}
          onClick={() => onDecide("retry", text)}
        >
          <Icon name="refresh" size={14} /> Không đồng ý, làm lại theo góp ý
        </button>
        <button
          className="btn"
          type="button"
          disabled={busy}
          onClick={() => { if (window.confirm("Hoàn tác bản sửa này và kết thúc job?")) onDecide("reject", text); }}
        >
          <Icon name="x" size={14} /> Không đồng ý, dừng
        </button>
      </div>
      </div>
      {!pending.canRetry ? <p className="faint">Đây là vòng cuối nên không còn lượt làm lại.</p> : null}
    </section>
  );
}

const VERDICT_LABEL: Record<Verdict, string> = {
  approve: "Người duyệt đồng ý",
  retry: "Người duyệt không đồng ý, cho làm lại",
  reject: "Người duyệt không đồng ý, dừng",
};

function ApprovalNote({ approval }: { approval: ApprovalResult }) {
  const label = approval.timeout ? "Hết giờ, không ai duyệt" : VERDICT_LABEL[approval.decision];
  return (
    <p className={`at-verdict is-${approval.decision}`}>
      <b>{label}</b>
      {approval.by ? <span className="faint"> · {approval.by}</span> : null}
      {approval.at ? <span className="faint num"> · {formatClock(approval.at)}</span> : null}
      {approval.note && !approval.timeout ? <span>: {approval.note}</span> : null}
    </p>
  );
}

function Banner({ job, simple }: { job: Job; simple: boolean }) {
  if (job.report) {
    const tone = OUTCOMES[job.report.outcome].tone;
    const plain = job.report.plain;
    return (
      <div className={`at-banner at-banner--${tone}`}>
        <strong>{job.report.headline}</strong>
        {plain ? <p>{plain}</p> : null}
        {plain && simple ? (
          <details className="at-more"><summary>Lý do kỹ thuật</summary><p>{job.report.reason}</p></details>
        ) : <p className={plain ? "muted" : undefined}>{job.report.reason}</p>}
      </div>
    );
  }
  if (job.status === "failed") {
    return <div className="at-banner at-banner--bad"><strong>Job dừng vì lỗi</strong><p>{job.error}</p></div>;
  }
  if (job.status === "stopped") {
    return <div className="at-banner at-banner--plain"><strong>Đã dừng</strong><p>Mọi thay đổi của job này đã được hoàn tác.</p></div>;
  }
  return null;
}

/** Đoạn chữ dài: thu gọn còn vài dòng, có nút xem thêm. */
function Clamp({ text, className }: { text: string; className?: string }) {
  const [open, setOpen] = useState(false);
  const long = text.length > 280;
  return (
    <div className={className}>
      <p className={long && !open ? "at-clamp" : undefined}>{text}</p>
      {long ? (
        <button className="at-more-btn" type="button" onClick={() => setOpen((v) => !v)}>{open ? "Thu gọn" : "Xem thêm"}</button>
      ) : null}
    </div>
  );
}

function OpinionCard({ item }: { item: Opinion }) {
  if (item.error) {
    return (
      <article className="at-card">
        <header className="at-card__head"><strong>{item.label}</strong><span className="at-tag at-tag--bad">Không trả lời được</span></header>
        <p className="faint">{item.error}</p>
      </article>
    );
  }
  return (
    <article className="at-card">
      <header className="at-card__head">
        <strong>{item.label}</strong>
        <span className="at-tag at-tag--plain">{CAUSES[item.cause ?? "unknown"] ?? item.cause}</span>
        {item.stance ? <span className={`at-tag at-tag--${item.stance === "agree" ? "ok" : item.stance === "disagree" ? "bad" : "warn"}`}>{STANCES[item.stance]}</span> : null}
        {typeof item.confidence === "number" ? (
          <span className="at-conf" title={`Độ tin cậy ${item.confidence}%`}>
            <span className="at-conf__bar"><span style={{ width: `${Math.max(0, Math.min(100, item.confidence))}%` }} /></span>
            <span className="num faint">{item.confidence}%</span>
          </span>
        ) : null}
      </header>
      {item.summary ? <Clamp text={item.summary} /> : null}
      {item.rebuttal ? <Clamp className="at-rebuttal" text={item.rebuttal} /> : null}
      {item.evidence?.length ? (
        <details className="at-more">
          <summary>Bằng chứng ({item.evidence.length})</summary>
          <ul>{item.evidence.map((e, i) => <li key={i}>{e}</li>)}</ul>
          {item.codeRefs?.length ? <p className="mono at-refs">{item.codeRefs.join("  ")}</p> : null}
        </details>
      ) : null}
      {item.proposal ? (
        <details className="at-more">
          <summary>Đề xuất</summary>
          <p className="muted at-proposal">{item.proposal}</p>
        </details>
      ) : null}
    </article>
  );
}

function checkText(check: Check): string {
  const needsValue = !["empty", "not_empty"].includes(check.op);
  return `${OPS[check.op] ?? check.op}${needsValue ? ` "${check.expected}"` : ""}`;
}

function CheckMatrix({ evaluation, caption, simple = false }: { evaluation: Evaluation; caption: string; simple?: boolean }) {
  const count = evaluation.total;
  return (
    <div className="table-wrap">
      <table className="mini-table at-matrix">
        <caption>{caption}: <b className={evaluation.allPass ? "lab-ok" : "ef-red"}>đạt {evaluation.passed}/{count} lần</b></caption>
        <thead>
          <tr>
            <th>Tiêu chí</th>
            {Array.from({ length: count }, (_, i) => <th key={i}>Lần {i + 1}</th>)}
          </tr>
        </thead>
        <tbody>
          {evaluation.rows.map((row, r) => (
            <tr key={r}>
              <td>
                {simple && row.check.why ? <>{row.check.why}<br /></> : null}
                <span className="mono">{row.check.field}</span> <small className="faint">{checkText(row.check)}</small>
              </td>
              {row.cells.map((cell, c) => (
                <td key={c} className={cell.ok ? "at-pass" : "at-fail"}>
                  {cell.value === null ? "lượt lỗi" : cell.value === "" ? <span className="faint">(trống)</span> : cell.value}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DecisionCard({ decision, shownAbove, simple = false }: { decision: Decision; shownAbove?: boolean; simple?: boolean }) {
  return (
    <article className="at-card at-card--arbiter">
      <header className="at-card__head">
        <strong>Trọng tài</strong>
        <span className="at-tag at-tag--plain">{CAUSES[decision.cause] ?? decision.cause}</span>
        <span className={`at-tag at-tag--${decision.decision === "fix_code" ? "ok" : decision.decision === "skip_ocr" ? "warn" : "plain"}`}>{DECISIONS[decision.decision]}</span>
      </header>
      {decision.plain ? <p className="at-plain__lead">{decision.plain}</p> : null}
      {decision.balance ? <p className="muted"><b>Vì sao sửa ở bước này (thủ tục có thanh tra):</b> {decision.balance}</p> : null}
      <Tech simple={simple && !!decision.plain} label="Lý do và kế hoạch chi tiết (kỹ thuật)">
        {shownAbove ? <p className="faint">Lý do: xem khung kết luận ở trên.</p> : <Clamp text={decision.reason} />}
        {decision.dissent ? <p className="muted"><b>Ý kiến bị bác:</b> {decision.dissent}</p> : null}
        {decision.plan ? (
          <div className="at-plan">
            <b>Kế hoạch sửa:</b> {decision.plan.summary}
            <ol>{decision.plan.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
            {decision.plan.files.length ? <p className="mono at-refs">{decision.plan.files.join("  ")}</p> : null}
            {decision.plan.test ? <p className="muted"><b>Test:</b> {decision.plan.test}</p> : null}
          </div>
        ) : null}
        {decision.risk ? <p className="muted"><b>Rủi ro:</b> {decision.risk}</p> : null}
      </Tech>
    </article>
  );
}

function Patch({ patch, open = true }: { patch: string; open?: boolean }) {
  return (
    <details className="at-more" open={open}>
      <summary>Patch</summary>
      <div className="at-patch__bar"><CopyButton text={patch} label="Chép patch" /></div>
      <pre className="at-patch">
        {patch.split("\n").map((line, i) => (
          <span key={i} className={line.startsWith("+") ? "is-add" : line.startsWith("-") ? "is-del" : line.startsWith("@@") ? "is-hunk" : undefined}>{line}{"\n"}</span>
        ))}
      </pre>
    </details>
  );
}

function RunDots({ runs, total }: { runs: RunBrief[]; total: number }) {
  return (
    <span className="at-dots" aria-label={`${runs.length}/${total} lần xong`}>
      {Array.from({ length: total }, (_, i) => {
        const run = runs.find((r) => r.n === i + 1);
        const tt = run?.secondPass;
        const note = tt ? (tt.status === "done" ? ` · thanh tra sửa ${tt.patched?.length ?? 0} ô` : tt.status === "none" ? "" : " · thanh tra không xong") : "";
        return <i key={i} className={run ? (run.status === "error" ? "is-bad" : "is-ok") : ""} title={run?.error ?? `Lần ${i + 1}${note}`} />;
      })}
    </span>
  );
}

function ExtensionCheck({ name, result }: { name: string; result: ExtensionTests }) {
  return (
    <li className={result.ok ? "" : "is-bad"}>
      <b>{name}</b> {result.failed}/{result.total} file đỏ
      <span className="faint"> (trước khi sửa: {result.failedBefore} đỏ)</span>
      {result.new.length ? <ul>{result.new.map((t) => <li key={t} className="mono">{t}</li>)}</ul> : <span className="faint"> · không có file mới đỏ</span>}
    </li>
  );
}

function SuiteCheck({ name, result }: { name: string; result: FullTests }) {
  return (
    <li className={result.ok ? "" : "is-bad"}>
      <b>{name}</b> {result.after.failed} failed, {result.after.passed} passed, {result.after.errors} errors
      <span className="faint"> (trước khi sửa: {result.before.failed} failed, {result.before.passed} passed)</span>
      {result.new.length ? <ul>{result.new.map((t) => <li key={t} className="mono">{t}</li>)}</ul> : <span className="faint"> · không có test mới đỏ</span>}
    </li>
  );
}

function Checks({ round }: { round: Pick<Round, "tests" | "deploy"> & { tests: (Round["tests"] & { troly?: ExtensionTests; handfree?: FullTests }) | null } }) {
  const { tests, deploy } = round;
  const full = tests?.full;
  const extension = tests?.extension;
  if (!tests && !deploy) return null;
  return (
    <ul className="at-checks">
      {extension ? <ExtensionCheck name="Test extension Auto Fill" result={extension} /> : null}
      {tests?.troly ? <ExtensionCheck name="Test extension trợ lý" result={tests.troly} /> : null}
      {tests?.pipeline ? (
        <li className={tests.pipeline.ok || tests.pipeline.skipped ? "" : "is-bad"}>
          <b>Test pipeline</b> {tests.pipeline.summary}
          {tests.pipeline.files?.length ? <span className="mono faint"> {tests.pipeline.files.join(" ")}</span> : null}
        </li>
      ) : null}
      {full ? <SuiteCheck name="Toàn bộ test" result={full} /> : null}
      {tests?.handfree ? <SuiteCheck name="Test trợ lý (tests/handfree)" result={tests.handfree} /> : null}
      {tests?.regression ? (
        <li className={tests.regression.ok ? "" : "is-bad"}>
          <b>Ca hồi quy</b> {tests.regression.broken ? "trình phát lại sập" : `${tests.regression.passed}/${tests.regression.total} đạt`}
          {tests.regression.new.length ? <span> · mới trượt: {tests.regression.new.join(", ")}</span> : null}
          {tests.regression.fixed.length ? <span className="faint"> · nay đạt: {tests.regression.fixed.join(", ")}</span> : null}
        </li>
      ) : null}
      {deploy ? (
        <li className={deploy.ok ? "" : "is-bad"}>
          <b>Docker</b> {deploy.ok ? (deploy.ps || "đã Up") : `lỗi ở bước ${deploy.step}`}
          {deploy.health ? <span className="mono faint"> {deploy.health}</span> : null}
        </li>
      ) : null}
    </ul>
  );
}

/** Một dòng cho tester: test tự động và dựng hệ thống thử có ổn không; chi tiết từng bộ test ở phần kỹ thuật. */
function ChecksLine({ round }: { round: Pick<Round, "tests" | "deploy"> }) {
  const tests = round.tests as (Round["tests"] & { troly?: ExtensionTests; handfree?: FullTests }) | null;
  if (!tests && !round.deploy) return null;
  const parts: { name: string; ok: boolean }[] = [];
  if (tests?.pipeline) parts.push({ name: "test của thủ tục", ok: tests.pipeline.ok || !!tests.pipeline.skipped });
  if (tests?.full) parts.push({ name: "toàn bộ test", ok: tests.full.ok });
  if (tests?.extension) parts.push({ name: "test extension", ok: tests.extension.ok });
  if (tests?.troly) parts.push({ name: "test extension trợ lý", ok: tests.troly.ok });
  if (tests?.handfree) parts.push({ name: "test trợ lý", ok: tests.handfree.ok });
  if (tests?.regression) parts.push({ name: "các ca lỗi cũ đã sửa", ok: tests.regression.ok });
  if (round.deploy) parts.push({ name: "dựng hệ thống thử", ok: round.deploy.ok });
  const bad = parts.filter((p) => !p.ok);
  return (
    <p className={`at-checkline ${bad.length ? "is-bad" : "is-ok"}`}>
      <Icon name={bad.length ? "alert" : "check"} size={14} />
      {bad.length
        ? <span>Kiểm tra tự động có chỗ chưa qua: {bad.map((p) => p.name).join(", ")}.</span>
        : <span>Kiểm tra tự động đều qua ({parts.map((p) => p.name).join(", ")}): bản sửa không làm hỏng chỗ khác mà test biết.</span>}
    </p>
  );
}

function RoundView({ job, round, single, simple }: { job: Job; round: Round; single: boolean; simple: boolean }) {
  const retest = round.retest;
  const council = round.opinions.length + round.reviews.length;
  return (
    <section className="at-round" aria-label={`Vòng ${round.n}`}>
      {single ? null : <h2 className="at-round__title">Vòng {round.n}</h2>}
      <Tech simple={simple} label={`Ý kiến chi tiết của hội đồng (${council})`}>
        {round.opinions.length ? (
          <div>
            <h3 className="section-title">Ý kiến độc lập</h3>
            <div className="at-cards">{round.opinions.map((o) => <OpinionCard key={o.role} item={o} />)}</div>
          </div>
        ) : null}
        {round.debate?.skipped ? <p className="faint">{round.debate.reason}</p> : null}
        {round.reviews.length ? (
          <div>
            <h3 className="section-title">Phản biện</h3>
            <div className="at-cards">{round.reviews.map((o) => <OpinionCard key={o.role} item={o} />)}</div>
          </div>
        ) : null}
      </Tech>
      {round.planHistory?.length ? (
        <details className="at-more">
          <summary>{round.planHistory.length} kế hoạch trước đã được yêu cầu lập lại</summary>
          {round.planHistory.map((d, i) => <DecisionCard key={i} decision={d} simple={simple} />)}
        </details>
      ) : null}
      {round.decision && job.planApproval?.round !== round.n ? (
        <DecisionCard decision={round.decision} simple={simple} shownAbove={!!job.report && job.report.reason === round.decision.reason} />
      ) : null}
      {round.planReviews?.map((r) => (
        <p key={r.revision} className={`at-verdict is-${r.decision}`}>
          <b>{r.timeout ? "Hết giờ, không ai duyệt kế hoạch" : r.decision === "approve" ? "Đồng ý kế hoạch" : r.decision === "retry" ? "Yêu cầu lập lại kế hoạch" : "Không đồng ý kế hoạch"}</b>
          {r.by ? <span className="faint"> · {r.by}</span> : null}
          {r.at ? <span className="faint num"> · {formatClock(r.at)}</span> : null}
          {r.note ? <span>: {r.note}</span> : null}
        </p>
      ))}
      {round.precheck ? <CheckMatrix evaluation={round.precheck} simple={simple} caption="Tiêu chí trên code trước khi sửa" /> : null}
      {round.fix ? (
        <article className="at-card">
          <header className="at-card__head">
            <strong>Sửa code</strong>
            {round.fix.repairs ? <span className="at-tag at-tag--warn">Vá lại {round.fix.repairs} lần</span> : null}
          </header>
          {round.fix.plain ? <p className="at-plain__lead">{round.fix.plain}</p> : null}
          <Tech simple={simple} label="Chi tiết kỹ thuật của bản sửa">
            <p>{round.fix.summary}</p>
            {round.fix.notes ? <p className="muted">{round.fix.notes}</p> : null}
            {round.fix.patch ? <Patch patch={round.fix.patch} open={!simple} /> : null}
          </Tech>
        </article>
      ) : null}
      {simple ? <ChecksLine round={round} /> : null}
      <Tech simple={simple} label="Chi tiết từng bộ test">
        <Checks round={round} />
      </Tech>
      {round.approval ? <ApprovalNote approval={round.approval} /> : null}
      {retest ? (
        <div className="at-retest">
          <h3 className="section-title">Chạy lại với bản sửa <RunDots runs={retest.runs} total={retest.total} /></h3>
          {retest.evaluation ? <CheckMatrix evaluation={retest.evaluation} simple={simple} caption="Tiêu chí sau khi sửa" /> : null}
          {retest.regressions?.length ? (
            <div className="at-regress">
              <b className="ef-red">Field đổi giá trị ngoài dự kiến</b>
              <ul>
                {retest.regressions.map((r) => (
                  <li key={r.field}><span className="mono">{r.field}</span>: {r.before.join(" / ") || "(trống)"} → {r.after.join(" / ") || "(trống)"}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
      {round.result && !round.result.ok ? (
        <p className="at-failed">
          <b>{round.result.kept ? "Vòng này không đạt. Code của vòng này được để lại cho người xem." : "Vòng này không đạt, đã hoàn tác."}</b>
          {" "}{round.result.reason}
        </p>
      ) : null}
    </section>
  );
}

function FieldsTab({ job }: { job: Job }) {
  const [batch, setBatch] = useState<Batch | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    setError("");
    agentApi.runs(job.id).then((data) => setBatch(data.phases.length ? toBatch(job, data.phases) : null)).catch((reason) => setError(errorText(reason)));
    // job đổi mỗi 2 giây khi đang chạy; chỉ tải lại khi có lượt mới.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job.id, job.rounds.length, job.reproduce?.runs.length, job.status]);
  useEffect(load, [load]);
  if (error) return <ErrorNotice message={error} onRetry={load} />;
  if (!batch) return <p className="faint">Chưa có lần chạy lại nào xong.</p>;
  return <Results key={batch.id} batch={batch} />;
}

function LogTab({ job }: { job: Job }) {
  return (
    <ol className="at-log">
      {[...job.events].reverse().map((event, i) => (
        <li key={i} className={`is-${event.level}`}>
          <time className="num faint">{formatClock(event.t)}</time>
          {event.who ? <b>{event.who}</b> : null}
          <span>{event.text}</span>
        </li>
      ))}
    </ol>
  );
}

type Tab = "flow" | "fields" | "log";

export default function JobDetail({ id, onBack }: { id: string; onBack: () => void }) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("flow");
  const [acting, setActing] = useState(false);
  const [view, setView] = useView();
  const simple = view === "simple";

  const refresh = useCallback(() => {
    agentApi.get(id).then((data) => { setJob(data); setError(""); }).catch((reason) => setError(errorText(reason)));
  }, [id]);

  useEffect(refresh, [refresh]);

  const live = !job || job.status === "queued" || job.status === "running" || !!job.fix?.reverting;
  useEffect(() => {
    if (!live) return;
    const timer = window.setInterval(refresh, POLL_MS);
    return () => window.clearInterval(timer);
  }, [live, refresh]);

  const lastEvent = useMemo(() => job?.events[job.events.length - 1], [job]);

  async function act(run: () => Promise<Job>) {
    setActing(true);
    try {
      setJob(await run());
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setActing(false);
    }
  }

  if (!job) return error ? <ErrorNotice message={error} onRetry={refresh} /> : <PageLoading label="Đang tải job…" />;

  const running = job.status === "queued" || job.status === "running";
  const account = job.case.account;
  const tabs: { key: Tab; label: string }[] = [
    { key: "flow", label: "Diễn biến" },
    { key: "fields", label: job.settings.kind === "attach" ? "Kết quả đính kèm" : "Kết quả điền" },
    { key: "log", label: "Nhật ký" },
  ];

  return (
    <div className="at-job">
      <div className="page-head">
        <button className="btn btn--sm" type="button" onClick={onBack}><Icon name="arrow-left" size={14} /> Trở lại</button>
        <h1>{job.case.label ?? job.requestId}</h1>
        {job.outcome ? <OutcomeTag outcome={job.outcome} /> : <StatusTag status={job.status} stage={job.stage} />}
        <span className="mono faint">{job.requestId}</span>
        <CopyButton text={job.requestId} label="Chép mã" />
        <div className="page-head__actions">
          {running ? (
            <button className="btn btn--sm" type="button" disabled={acting} onClick={() => void act(() => agentApi.stop(job.id))}>
              <Icon name="x" size={14} /> Dừng và hoàn tác
            </button>
          ) : null}
          {job.fix && !job.fix.reverted ? (
            <button
              className="btn btn--sm"
              type="button"
              disabled={acting || !!job.fix.reverting}
              onClick={() => { if (window.confirm("Hoàn tác bản sửa này và build lại backend?")) void act(() => agentApi.revert(job.id)); }}
            >
              {job.fix.reverting ? <Spinner label="Đang hoàn tác" /> : <><Icon name="refresh" size={14} /> Hoàn tác bản sửa</>}
            </button>
          ) : null}
        </div>
      </div>

      <div className="at-meta faint">
        {account ? <span>{account.username}{account.xa ? ` · ${account.xa}` : ""}{account.tinh ? `, ${account.tinh}` : ""}</span> : null}
        <span>Sửa cho {job.settings.target === "troly" ? "Trợ lý hồ sơ" : "Auto Fill"}</span>
        <span>{job.settings.kind === "attach" ? "Lượt đính kèm" : "Lượt điền"}</span>
        {job.case.thanhTra?.has ? <span>Có thanh tra soát lại</span> : null}
        {job.settings.mode === "portal" ? <span>Cổng thật (chế độ cũ)</span> : null}
        <span>Chạy lại bằng {job.settings.replayAccount}</span>
        {job.workspace?.["auto-fill-hcc-backend"] ? <span className="mono">BE {job.workspace["auto-fill-hcc-backend"].ref}</span> : null}
        <span>Bắt đầu {formatDateTime(job.createdAt)}</span>
        <span className="num">{job.cost.calls} lượt agent</span>
      </div>

      <blockquote className="at-quote">{job.description}</blockquote>
      <div className="at-viewbar">
        <span className="faint">Cách xem:</span>
        <div className="seg" role="group" aria-label="Cách xem">
          <button type="button" aria-pressed={simple} onClick={() => setView("simple")}>Dễ hiểu</button>
          <button type="button" aria-pressed={!simple} onClick={() => setView("full")}>Đầy đủ kỹ thuật</button>
        </div>
        <span className="faint at-viewbar__hint">{simple ? "Phần kỹ thuật được thu gọn, bấm vào để mở." : "Hiện toàn bộ ý kiến, file, test và patch."}</span>
      </div>
      <StageRail job={job} />
      {running ? (
        <p className="at-live" aria-live="polite">
          <Spinner label={job.status === "queued" ? "Đang chờ ca trước chạy xong" : lastEvent ? `${lastEvent.who ? `${lastEvent.who}: ` : ""}${lastEvent.text}` : "Đang chạy"} />
        </p>
      ) : null}
      <PlainSummary job={job} />
      <PlanBox
        key={`plan-${job.planApproval?.round ?? 0}-${job.planApproval?.revision ?? 0}`}
        job={job}
        busy={acting}
        simple={simple}
        onDecide={(decision, note) => void act(async () => ({
          ...(await agentApi.plan(job.id, { round: job.planApproval?.round ?? 0, revision: job.planApproval?.revision ?? 0, decision, note })),
          planApproval: null,
        }))}
      />
      <ApprovalBox
        key={job.approval?.round ?? 0}
        job={job}
        busy={acting}
        simple={simple}
        onDecide={(decision, note) => void act(async () => ({
          ...(await agentApi.approve(job.id, { round: job.approval?.round ?? 0, decision, note })),
          approval: null,
        }))}
      />
      <Banner job={job} simple={simple} />
      {job.fix?.reverted ? (
        <div className="at-banner at-banner--plain">
          <strong>Bản sửa đã được hoàn tác</strong>
          {job.fix.keptFiles?.length ? <p>Giữ nguyên vì đã bị sửa tiếp sau đó: {job.fix.keptFiles.join(", ")}</p> : null}
        </div>
      ) : null}
      {job.fix && !job.fix.reverted && !job.fix.reverting ? (
        job.fix.unverified ? (
          <p className="at-warn">
            <Icon name="alert" size={14} /> Code của vòng {job.fix.round} CHƯA ĐẠT khi kiểm, được để lại trong thư mục làm việc để bạn xem tiếp, chưa build
            lên Docker: {job.fix.files.map((f) => f.path).join(", ")}. Không dùng thì bấm Hoàn tác bản sửa.
          </p>
        ) : (
          job.fix.pushes?.length ? (
            <div className="at-deliver">
              <strong>Bàn giao</strong>
              <p className="faint">Bản sửa nằm trên nhánh riêng của ca, dựng trên tag đang chạy production; main không đổi.</p>
              <ul>
                {job.fix.pushes.map((p) => (
                  <li key={p.component}>
                    <b>{p.component}</b> {p.error ? <span className="is-bad">không đẩy được: {p.error}</span> : (
                      <>
                        nhánh <code>{p.branch}</code> trên {p.ref ?? "?"}{" "}
                        {p.compare ? <a href={p.compare} target="_blank" rel="noreferrer">Mở PR vào {p.base}</a> : <span className="mono faint">{p.remote}</span>}
                      </>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ) : job.fix.git ? (
            <p className="muted at-note">
              Bản sửa đã commit lên nhánh <code>{job.fix.git.branch}</code> ({job.fix.git.commit.slice(0, 10)}) trên GitHub, main không đổi. Mở PR từ
              nhánh này nếu muốn gộp: {job.fix.files.map((f) => f.path).join(", ")}.
            </p>
          ) : (
            <p className="muted at-note">Bản sửa đang nằm trong thư mục làm việc và chưa commit: {job.fix.files.map((f) => f.path).join(", ")}. Hãy xem lại rồi tự commit.</p>
          )
        )
      ) : null}
      {job.regression ? (
        job.regression.saved ? (
          <p className="muted at-note">
            Đã lưu ca hồi quy <code>{job.regression.path}</code>
            {job.regression.catchesOldBug ? ": trượt trên code production, đạt trên bản sửa." : ": chưa bắt được lỗi cũ (code production phát lại cũng đạt)."}
            {" "}Dữ liệu đã ẩn danh, soát lại rồi mới commit.
          </p>
        ) : <p className="muted at-note">Không lưu ca hồi quy: {job.regression.reason}</p>
      ) : null}
      {job.warnings.length > 2 ? (
        <details className="at-warns">
          <summary><Icon name="alert" size={14} /> {job.warnings.length} cảnh báo</summary>
          {job.warnings.map((w) => <p key={w} className="at-warn">{w}</p>)}
        </details>
      ) : job.warnings.map((w) => <p key={w} className="at-warn"><Icon name="alert" size={14} /> {w}</p>)}
      {error ? <p className="form-error" role="alert">{error}</p> : null}

      <div className="tabs" role="tablist" aria-label="Chi tiết job">
        {tabs.map((t) => <button key={t.key} type="button" role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)}>{t.label}</button>)}
      </div>
      {tab === "flow" ? (
        <div className="at-flow">
          {job.reproduce ? (
            <p className="muted">
              Chạy lại với code hiện tại <RunDots runs={job.reproduce.runs} total={job.reproduce.total} />
              {typeof job.reproduce.ocrFresh === "number" ? <span className="faint"> {job.reproduce.ocrFresh}/{job.reproduce.total} lần xác nhận OCR mới</span> : null}
              {job.reproduce.coverage ? <span className={job.reproduce.faithful === false ? "ef-red" : "faint"}> · ra {job.reproduce.coverage.matched}/{job.reproduce.coverage.original} {job.settings.kind === "attach" ? "ô đính kèm" : "field"} của lượt gốc</span> : null}
            </p>
          ) : null}
          {job.rounds.map((round) => <RoundView key={round.n} job={job} round={round} single={job.rounds.length === 1} simple={simple} />)}
        </div>
      ) : null}
      {tab === "fields" ? <FieldsTab job={job} /> : null}
      {tab === "log" ? <LogTab job={job} /> : null}
    </div>
  );
}
