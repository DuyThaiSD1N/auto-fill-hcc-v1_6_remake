// Tái hiện lượt + Nội dung trợ lý điền + Tệp + Gói ghi thô của MỘT lượt (dữ liệu từ dịch vụ agent, agents/lab.py).
import { useEffect, useMemo, useState } from "react";
import CopyButton from "../components/CopyButton";
import Icon from "../components/Icon";
import FormSimulation from "../components/run/FormSimulation";
import Json from "../components/run/Json";
import { EmptyState, ErrorNotice, PageLoading, Spinner } from "../components/Status";
import { KindTag, SourceTag } from "../components/Tags";
import { formatBytes, formatDateTime, formatMs, pct } from "../format";
import { useAsync } from "../hooks";
import { navigate, onLinkClick, useLocation } from "../router";
import { findSim } from "../simulations/registry";
import { stepLabel } from "../stages";
import type { RunDetail, StepsDoc, TraceDoc } from "../types";
import { labApi, rerunRequest, useLabAvailable, type LabEvent, type LabRow, type LabRunView } from "./api";
import {
  clockAt, DATA_SOURCE, downloadJson, humanDuration, LabCrumbs, LabNotice, Masked, offset, RevealContext,
  Section, SOURCE_LABEL, SOURCE_TEXT, Unavailable, useMask, VERDICTS, VerdictBadge,
} from "./parts";
import "./autotest.css";

export type LabView = "flow" | "fill" | "files" | "raw";

export default function LabRunPage({ requestId, view }: { requestId: string; view: LabView }) {
  const lab = useLabAvailable();
  const { data, error, loading, reload } = useAsync(() => labApi.run(requestId), requestId);
  const [reveal, setReveal] = useState(false);
  useEffect(() => {
    document.title = `${view === "fill" ? "Nội dung trợ lý điền" : "Tái hiện lượt"} ${requestId} — Monitor`;
    return () => { document.title = "Monitor — Trợ lý nhân dân"; };
  }, [requestId, view]);

  const crumbs = [{ label: "Xem lượt", href: "/autotest/replay" }, { label: requestId, mono: true }];
  if (lab === false) return <><LabNotice /><LabCrumbs items={crumbs} /><Unavailable /></>;
  if (loading && !data) return <><LabNotice /><PageLoading label="Đang dựng lại lượt (đọc Mongo nguồn / kho lưu trữ)…" /></>;
  if (error && !data) return <><LabNotice /><LabCrumbs items={crumbs} /><ErrorNotice message={error} onRetry={reload} /></>;
  if (!data) return null;
  return (
    <RevealContext.Provider value={reveal}>
      <LabNotice />
      <RunHeader run={data} view={view} reveal={reveal} onReveal={() => setReveal((v) => !v)} onChanged={reload} />
      {view === "flow" ? <FlowView run={data} /> : null}
      {view === "fill" ? <FillView run={data} onChanged={reload} /> : null}
      {view === "files" ? <FilesView run={data} /> : null}
      {view === "raw" ? <RawView requestId={requestId} /> : null}
    </RevealContext.Provider>
  );
}

// ---- đầu trang ----------------------------------------------------------------------------------------------------

function suiteKey(procedure?: string | null) {
  return `lab:${(procedure ?? "khac").replace(/[^\w.-]/g, "_")}`;
}

function RunHeader({ run, view, reveal, onReveal, onChanged }: {
  run: LabRunView; view: LabView; reveal: boolean; onReveal: () => void; onChanged: () => void;
}) {
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState<{ tone: "ok" | "bad"; text: string } | null>(null);
  const id = run.requestId;
  const end = run.startAt ? clockAt(run.startAt, run.durationMs) : "—";
  const day = run.startAt ? new Date(run.startAt).toLocaleDateString("vi-VN") : "";
  const unit = run.unit.name || run.unit.username || "—";
  const tabs: { key: LabView; label: string; count?: string; href: string }[] = [
    { key: "flow", label: "Luồng và hội thoại", count: `${run.events.length}`, href: `/autotest/replay/${encodeURIComponent(id)}` },
    { key: "fill", label: "Nội dung trợ lý điền", count: `${run.rows.length} ô`, href: `/autotest/fill/${encodeURIComponent(id)}` },
    { key: "files", label: "Tệp", count: `${run.files.length}`, href: `/autotest/replay/${encodeURIComponent(id)}?tab=files` },
    { key: "raw", label: "Gói ghi thô", href: `/autotest/replay/${encodeURIComponent(id)}?tab=raw` },
  ];

  async function act(name: string, work: () => Promise<void>) {
    setBusy(name);
    setMessage(null);
    try {
      await work();
    } catch (reason) {
      setMessage({ tone: "bad", text: reason instanceof Error ? reason.message : String(reason) });
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <LabCrumbs items={[{ label: "Xem lượt", href: "/autotest/replay" }, { label: id, mono: true },
                         { label: view === "fill" ? "Nội dung trợ lý điền" : view === "files" ? "Tệp" : view === "raw" ? "Gói ghi thô" : "Tái hiện" }]} />
      <section className="lab-head">
        <div className="lab-head__title">
          <h1>{view === "fill" ? "Nội dung trợ lý điền" : "Tái hiện lượt"} <span className="mono">{id}</span></h1>
          <div className="lab-head__meta">
            <KindTag kind={run.kind} />
            {run.summary.edited ? <span className="lab-badge lab-badge--bad">Sửa {run.summary.edited} ô</span> : null}
            <SourceTag source={run.experience} />
            <span>{unit}</span><span>·</span>
            <span>{run.label || run.procedure || "—"}</span><span>·</span>
            <span className="num">{clockAt(run.startAt, 0)} → {end} {day} ({humanDuration(run.durationMs)})</span>
            {run.extVersion ? <><span>·</span><span>Extension v{run.extVersion}</span></> : null}
            <span>·</span><span>{run.files.length} tệp</span>
            <span>·</span><span title="Nơi dịch vụ agent đọc được lượt này">{DATA_SOURCE[run.source] ?? run.source}</span>
          </div>
        </div>
        <div className="lab-head__actions">
          {run.caseId ? (
            <a className="btn btn--sm" href={`/autotest/suites?suite=${encodeURIComponent(suiteKey(run.procedure))}&case=${run.caseId}`}
               onClick={(e) => onLinkClick(e, `/autotest/suites?suite=${encodeURIComponent(suiteKey(run.procedure))}&case=${run.caseId}`)}>
              <Icon name="flask" size={14} /> Ca {run.caseId}
            </a>
          ) : run.kind === "autofill" ? (
            <button className="btn btn--sm" type="button" disabled={!!busy}
                    onClick={() => act("case", async () => {
                      const res = await labApi.createCase(id);
                      setMessage({ tone: "ok", text: `Đã tạo ca test ${res.caseId} (dữ liệu cá nhân đã thay bằng dữ liệu giả).` });
                      onChanged();
                    })}>
              {busy === "case" ? <Spinner label="Đang tạo ca…" /> : <><Icon name="flask" size={14} /> Tạo ca test từ lượt này</>}
            </button>
          ) : null}
          {run.kind === "autofill" ? (
            <button className="btn btn--sm btn--primary" type="button" disabled={!!busy}
                    onClick={() => act("rerun", async () => navigate(`/autotest/runs/${await rerunRequest(id, run.caseId, run.procedure)}`))}>
              {busy === "rerun" ? <Spinner label="Đang chạy…" /> : <><Icon name="play" size={14} /> Chạy lại với bản mới</>}
            </button>
          ) : null}
          <a className="btn btn--sm" href={`/autotest/agent?req=${encodeURIComponent(id)}`}
             onClick={(e) => onLinkClick(e, `/autotest/agent?req=${encodeURIComponent(id)}`)}
             title="Tạo ca Agent tự sửa với mã req này: hội đồng agent tìm nguyên nhân, sửa code, chờ duyệt rồi chạy lại để chấm">
            <Icon name="wrench" size={14} /> Gửi Agent tự sửa
          </a>
          <button className="btn btn--sm" type="button" disabled={!!busy}
                  onClick={() => act("raw", async () => downloadJson(`${id}.json`, await labApi.raw(id)))}>
            {busy === "raw" ? <Spinner label="Đang tải…" /> : <><Icon name="download" size={14} /> Tải gói ghi (.json)</>}
          </button>
          <button className="btn btn--sm btn--ghost" type="button" onClick={onReveal} aria-pressed={reveal}
                  title="Số giấy tờ ≥ 9 chữ số mặc định hiện dạng 024199•••147">
            <Icon name={reveal ? "eye-off" : "eye"} size={14} /> {reveal ? "Che số giấy tờ" : "Hiện đủ số"}
          </button>
          <CopyButton text={id} label="Sao chép mã" />
        </div>
      </section>
      {message ? <div className={`lab-msg lab-msg--${message.tone}`}>{message.text}</div> : null}
      <div className="tabs" role="tablist" aria-label="Phần của lượt">
        {tabs.map((t) => (
          <button key={t.key} role="tab" type="button" aria-selected={view === t.key} onClick={() => navigate(t.href, { replace: true })}>
            {t.label}{t.count ? <span className="count">{t.count}</span> : null}
          </button>
        ))}
      </div>
    </>
  );
}

// ---- luồng và hội thoại ---------------------------------------------------------------------------------------------

const SPEEDS = [1, 2, 4, 8, 16];

function lastAt(events: LabEvent[], t: number): number {
  let found = -1;
  for (let i = 0; i < events.length; i += 1) {
    if (events[i].t <= t) found = i;
    else break;
  }
  return found;
}

type Stage = "before" | "backend" | "fill" | "final";

function stageAt(run: LabRunView, t: number): Stage {
  const response = run.events.find((e) => e.type === "response")?.t ?? 0;
  const fill = run.snapshots.find((s) => s.kind === "fill")?.t ?? null;
  const last = run.snapshots.length ? run.snapshots[run.snapshots.length - 1].t : null;
  if (t < response) return "before";
  if (fill === null || t < fill) return "backend";
  if (last !== null && t >= last && run.snapshots.length > 1) return "final";
  return "fill";
}

function rowValue(row: LabRow, stage: Stage): string {
  if (stage === "before") return "";
  if (stage === "backend") return row.inBe ? row.be : "";
  if (stage === "fill") return row.fill ?? (row.inBe ? row.be : "");
  return row.final ?? row.fill ?? row.be;
}

function rowTag(row: LabRow, stage: Stage, value: string): { cls: string; text: string } {
  if (stage === "final" && ["llm", "ocr", "other", "cleared"].includes(row.verdict)) return { cls: "edit", text: "Người dân sửa" };
  if (stage === "final" && row.verdict === "missing" && value) return { cls: "self", text: "Người dân tự điền" };
  if (!value) return stage !== "before" && row.verdict === "nodata" && row.be ? { cls: "warn", text: "Form không nhận" } : { cls: "empty", text: "Chưa điền" };
  if (row.source === "llm") return { cls: "ocr", text: "Đọc từ giấy tờ" };
  if (row.source === "rule") return { cls: "rule", text: "Luật suy ra" };
  if (row.source === "be") return { cls: "rule", text: "Backend điền" };
  return { cls: "empty", text: "" };
}

function FlowView({ run }: { run: LabRunView }) {
  const loc = useLocation();
  const events = run.events;
  const total = Math.max(run.durationMs, 1);
  const [t, setT] = useState<number>(() => {
    const snap = run.snapshots.find((s) => s.id === loc.query.get("snap"));
    return snap?.t ?? 0;
  });
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(4);
  const idx = lastAt(events, t);
  const cur = idx >= 0 ? events[idx] : null;
  const step = cur?.step ?? 0;

  useEffect(() => {
    if (!playing) return undefined;
    const handle = window.setInterval(() => {
      setT((v) => {
        const next = v + 200 * speed;
        if (next >= total) {
          setPlaying(false);
          return total;
        }
        return next;
      });
    }, 200);
    return () => window.clearInterval(handle);
  }, [playing, speed, total]);

  const jump = (to: number) => { setPlaying(false); setT(Math.max(0, Math.min(total, to))); };
  const warns = events.filter((e) => e.warn).length;

  return (
    <div className="lab-flow">
      <div className="lab-cards">
        <Card title="Nhật ký luồng" value={`${events.length} sự kiện`} sub={`${run.steps.filter((s) => s.from !== null).length}/5 bước · ${warns} cảnh báo`} />
        <Card title="Hội thoại người dân – trợ lý" value={run.chat.length ? `${run.chat.length} tin nhắn` : "Không có"}
              sub={run.chat.length ? `${run.chat.filter((m) => m.role === "user").length} lượt người dân nói · ${DATA_SOURCE[run.chatSource ?? ""] ?? ""}`
                : run.experience === "handfree" ? "Mongo chỉ giữ 24 giờ, kho chưa có bản lưu" : "Kênh Auto Fill không có hội thoại"} />
        <Card title="Ảnh chụp form" value={run.snapshots.length ? `${run.snapshots.length} bản` : "Không có"}
              sub={run.snapshots.length ? `S1–S${run.snapshots.length} · sau điền, mỗi lần sửa, rời bước` : "Kho chưa nhận ảnh chụp form của lượt"} />
        <Card title="Nội dung trợ lý điền" value={`${run.rows.length} ô`}
              sub={<>{run.summary.edited} ô người dân sửa · <a href={`/autotest/fill/${encodeURIComponent(run.requestId)}`}
                    onClick={(e) => onLinkClick(e, `/autotest/fill/${encodeURIComponent(run.requestId)}`)}>xem từng ô</a></>} />
      </div>

      <section className="panel lab-player" aria-label="Trình tua lượt">
        <div className="lab-player__bar">
          <button className="btn btn--primary btn--sm" type="button" onClick={() => {
            if (t >= total) setT(0);
            setPlaying((v) => !v);
          }}>
            <Icon name={playing ? "pause" : "play"} size={14} /> {playing ? "Tạm dừng" : t > 0 && t < total ? "Phát tiếp" : "Phát lại"}
          </button>
          <span className="num lab-player__time">{offset(t)} / {offset(total)}</span>
          <span className="lab-player__where">
            Sự kiện {idx + 1}/{events.length} · Bước {step + 1}/5 {run.steps[step]?.name} · {clockAt(run.startAt, t)}
          </span>
          <div className="filter" role="group" aria-label="Tốc độ">
            <span>Tốc độ</span>
            <div className="seg">
              {SPEEDS.map((s) => <button key={s} type="button" aria-pressed={speed === s} onClick={() => setSpeed(s)}>{s}×</button>)}
            </div>
          </div>
        </div>
        <div className="lab-player__steps">
          {run.steps.map((s, i) => (
            <button key={s.no} type="button" className={`lab-step${i === step ? " is-on" : ""}`} disabled={s.from === null}
                    onClick={() => s.from !== null && jump(s.from)}>
              <b>{s.no}</b> {s.name}
            </button>
          ))}
          <span className="lab-player__snaps">
            {run.snapshots.map((s) => (
              <button key={s.id} type="button" className={`lab-snapchip${cur?.snap === s.id ? " is-on" : ""}`}
                      title={`${s.label} · ${offset(s.t)}`} onClick={() => s.t !== null && jump(s.t)}>{s.id}</button>
            ))}
          </span>
        </div>
        <Track run={run} t={t} total={total} onJump={jump} />
        <div className="lab-track__axis num"><span>00:00 · {clockAt(run.startAt, 0)}</span><span>{offset(total)} · {clockAt(run.startAt, total)}</span></div>
        <p className="lab-hint">
          Vạch cao: sự kiện có cảnh báo · màu: <i className="lab-dot lab-dot--backend" /> backend <i className="lab-dot lab-dot--form" /> form
          {" "}<i className="lab-dot lab-dot--chat" /> hội thoại <i className="lab-dot lab-dot--extension" /> extension · S1–S{run.snapshots.length || "n"}: ảnh chụp form · bấm vào thanh để tua tới
          {run.backendEstimated ? " · giờ công đoạn backend là ước lượng (bản ghi backend được ghi lại sau, vd điền đợt 2)" : ""}
        </p>
      </section>

      <div className="lab-split">
        <ChatPanel run={run} t={t} step={step} />
        <FormPanel run={run} t={t} cur={cur} />
      </div>

      <EventLog run={run} idx={idx} onPick={(e) => jump(e.t)} />
      {cur ? <EventDetail run={run} event={cur} /> : null}
    </div>
  );
}

function Card({ title, value, sub }: { title: string; value: string; sub?: React.ReactNode }) {
  return <div className="kpi lab-card"><span>{title}</span><b>{value}</b>{sub ? <small>{sub}</small> : null}</div>;
}

function Track({ run, t, total, onJump }: { run: LabRunView; t: number; total: number; onJump: (t: number) => void }) {
  const left = (ms: number) => `${Math.min(100, (ms / total) * 100)}%`;
  return (
    <div className="lab-track" role="slider" aria-label="Dòng thời gian của lượt" aria-valuemin={0} aria-valuemax={total} aria-valuenow={t}
         tabIndex={0}
         onKeyDown={(e) => {
           if (e.key === "ArrowRight") onJump(t + total / 100);
           if (e.key === "ArrowLeft") onJump(t - total / 100);
         }}
         onClick={(e) => {
           const box = e.currentTarget.getBoundingClientRect();
           onJump(((e.clientX - box.left) / box.width) * total);
         }}>
      {run.steps.map((s, i) => (s.from !== null && s.to !== null ? (
        <span key={s.no} className={`lab-band lab-band--${i}`} style={{ left: left(s.from), width: `max(4px, ${((s.to - s.from) / total) * 100}%)` }} />
      ) : null))}
      {run.events.map((e) => (
        <span key={e.no} className={`lab-tick lab-tick--${e.src}${e.warn ? " lab-tick--warn" : ""}`} style={{ left: left(e.t) }}
              title={`#${e.no} ${offset(e.t)} · ${e.label}`} />
      ))}
      {run.snapshots.map((s) => (s.t !== null ? <span key={s.id} className="lab-snapmark" style={{ left: left(s.t) }}>{s.id}</span> : null))}
      <span className="lab-cursor" style={{ left: left(t) }} />
    </div>
  );
}

function ChatPanel({ run, t, step }: { run: LabRunView; t: number; step: number }) {
  const [all, setAll] = useState(false);
  const mask = useMask();
  const shown = run.chat.filter((m) => m.t <= t);
  const visible = all ? shown : shown.slice(-8);
  const feed = run.events.filter((e) => e.t <= t && (e.src === "form" || e.src === "extension" || e.type === "response")).slice(-6);
  return (
    <section className="panel lab-phone" aria-label="Extension lúc đang xem">
      <div className="panel__head">
        <div className="lab-section__title">
          <h2>{run.experience === "handfree" ? "Trợ lý nhân dân" : "Auto Fill"} · Bước {step + 1}/5 · {run.steps[step]?.name}</h2>
          <span>Người dân thấy gì lúc {clockAt(run.startAt, t)}</span>
        </div>
      </div>
      <div className="lab-phone__body">
        {run.chat.length ? (
          <>
            {shown.length > visible.length ? (
              <button className="linklike lab-more" type="button" onClick={() => setAll(true)}>Hiện {shown.length - visible.length} tin trước đó</button>
            ) : all && shown.length > 8 ? <button className="linklike lab-more" type="button" onClick={() => setAll(false)}>Chỉ hiện 8 tin gần nhất</button> : null}
            {visible.map((m, i) => (
              <div key={i} className={`lab-bubble lab-bubble--${m.role}`}>
                <p>{mask(m.text)}</p>
                <small className="num">{offset(m.t)}{m.source ? ` · ${m.source}` : ""}{m.state ? ` · ${m.state}` : ""}</small>
              </div>
            ))}
            {!visible.length ? <p className="faint">Chưa có tin nhắn ở thời điểm này.</p> : null}
          </>
        ) : (
          <p className="faint">{run.experience === "handfree" ? "Không còn hội thoại của lượt này (Mongo chỉ giữ 24 giờ, kho chưa có bản lưu)." : "Kênh Auto Fill: cán bộ thao tác trên extension, không có hội thoại."}</p>
        )}
        {feed.length ? (
          <ul className="lab-feed">
            {feed.map((e) => <li key={e.no}><span className="num">{offset(e.t)}</span> {e.label}{e.text ? ` · ${e.text}` : ""}</li>)}
          </ul>
        ) : null}
      </div>
    </section>
  );
}

function FormPanel({ run, t, cur }: { run: LabRunView; t: number; cur: LabEvent | null }) {
  const stage = stageAt(run, t);
  const sim = findSim(run.procedure);
  const [mode, setMode] = useState<"rows" | "sim">("rows");
  const mask = useMask();
  const changedNow = cur && (cur.type === "response" || cur.type.startsWith("snapshot"));
  const previous: Stage | null = stage === "backend" ? "before" : stage === "fill" ? "backend" : stage === "final" ? "fill" : null;
  const rows = run.rows;
  const stageText: Record<Stage, string> = {
    before: "Backend chưa trả kết quả",
    backend: "Backend đã trả, extension chưa điền",
    fill: "Sau khi extension điền (bản S1)",
    final: `Bản cuối trước khi nộp (S${run.snapshots.length})`,
  };
  const simRun = useMemo<RunDetail>(() => {
    const byKey = new Map(rows.map((r) => [r.key, r]));
    const fields = run.beFields.map((f) => {
      const key = f.occurrence ? `${f.name}#${f.occurrence}` : f.name;
      const row = byKey.get(key) ?? rows.find((r) => r.beKey === key);
      const value = row ? rowValue(row, stage) : stage === "before" ? "" : f.value;
      return { ...f, value: typeof value === "string" ? mask(value) : value };
    });
    return {
      trace: { id: "", request_id: run.requestId, procedure: run.procedure ?? undefined, procedure_label: run.label, created_at: run.startAt ?? "" } as TraceDoc,
      steps: { outputs: { response: { fields } }, meta: { procedure: run.procedure } } as unknown as StepsDoc,
    };
  }, [rows, run, stage, mask]);

  return (
    <section className="panel lab-form" aria-label="Tờ khai lúc đang xem">
      <div className="panel__head">
        <div className="lab-section__title">
          <h2>Tờ khai · dựng lại từ giá trị ô</h2>
          <span>{stageText[stage]}</span>
        </div>
        {sim ? (
          <div className="seg lab-section__actions">
            <button type="button" aria-pressed={mode === "rows"} onClick={() => setMode("rows")}>Bảng ô</button>
            <button type="button" aria-pressed={mode === "sim"} onClick={() => setMode("sim")}>Mô phỏng tờ khai</button>
          </div>
        ) : null}
      </div>
      <div className="lab-legend">
        <span><i className="lab-tag lab-tag--ocr" />Đọc từ giấy tờ</span>
        <span><i className="lab-tag lab-tag--rule" />Luật suy ra / backend điền</span>
        <span><i className="lab-tag lab-tag--edit" />Người dân sửa</span>
        <span><i className="lab-tag lab-tag--self" />Người dân tự điền</span>
        <span><i className="lab-tag lab-tag--empty" />Chưa điền</span>
        <span><i className="lab-changed" />Vừa thay đổi ở sự kiện đang xem</span>
      </div>
      {mode === "sim" && sim ? (
        <div className="lab-form__sim">
          <p className="lab-hint">Mô phỏng trên mẫu form đã khai của thủ tục (như web trace), giá trị ô theo thời điểm đang xem. Chưa có HTML eform đã lưu (đợt 2).</p>
          {run.beFields.length ? <FormSimulation run={simRun} /> : <EmptyState title="Backend không trả trường nào" />}
        </div>
      ) : rows.length ? (
        <div className="lab-form__rows">
          {rows.map((row) => {
            const value = rowValue(row, stage);
            const before = previous ? rowValue(row, previous) : value;
            const tag = rowTag(row, stage, value);
            return (
              <div key={row.key} className={`lab-field${changedNow && before !== value ? " is-changed" : ""}`}>
                <span className="lab-field__label" title={row.name}>{row.label}</span>
                <span className="lab-field__value">{value ? mask(value) : <span className="faint">—</span>}</span>
                {tag.text ? <span className={`lab-tag lab-tag--${tag.cls}`}>{tag.text}</span> : <span />}
              </div>
            );
          })}
          {run.hasReview ? <p className="lab-hint">Kho giữ giá trị ô lúc extension điền (S1) và lúc nộp (bản cuối); ô đổi ở lần sửa nào giữa chừng thì chưa biết (cần HTML eform từng bản — đợt 2).</p>
            : <p className="lab-hint">Chưa có ảnh chụp form của lượt này: chỉ hiện giá trị backend trả.</p>}
        </div>
      ) : <EmptyState title={run.kind === "attach" ? "Lượt đính kèm không có ô tờ khai" : "Lượt không có ô nào"} />}
    </section>
  );
}

function EventLog({ run, idx, onPick }: { run: LabRunView; idx: number; onPick: (e: LabEvent) => void }) {
  const mask = useMask();
  const warns = run.events.filter((e) => e.warn).length;
  return (
    <Section title="Nhật ký luồng" sub={`${run.events.length} sự kiện · ${warns} cảnh báo · bấm một dòng để tua tới`}>
      <div className="table-wrap lab-log">
        <table className="grid">
          <thead><tr><th>#</th><th>Mốc</th><th>Nguồn</th><th>Sự kiện</th><th>Nội dung</th><th className="right">Độ trễ</th></tr></thead>
          <tbody>
            {run.events.map((e, i) => (
              <tr key={e.no} className={`${i === idx ? "is-current" : ""}${i > idx ? " is-future" : ""}`} onClick={() => onPick(e)}>
                <td className="num">{e.no}</td>
                <td className="num nowrap">{offset(e.t)}</td>
                <td><span className={`lab-src lab-src--${e.src}`}>{SOURCE_LABEL[e.src] ?? e.src}</span></td>
                <td>{e.src === "backend" && /^[a-z]+\./.test(e.label) ? stepLabel(e.label) : e.label}{e.snap ? <span className="lab-snapchip is-static">{e.snap}</span> : null}</td>
                <td className="lab-log__text">{e.warn ? <span className="lab-badge lab-badge--bad">Cảnh báo</span> : null} {mask(e.text)}</td>
                <td className="num right">{e.ms !== null && e.ms !== undefined ? formatMs(e.ms) : ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

function EventDetail({ run, event }: { run: LabRunView; event: LabEvent }) {
  const mask = useMask();
  return (
    <Section title={`Chi tiết sự kiện #${event.no}`}>
      <dl className="kv lab-kv">
        <dt>Thời điểm</dt><dd className="num">{clockAt(run.startAt, event.t)} (+{offset(event.t)})</dd>
        <dt>Nguồn</dt><dd>{SOURCE_LABEL[event.src] ?? event.src}</dd>
        <dt>Loại</dt><dd className="mono">{event.type}</dd>
        <dt>Bước</dt><dd>{event.step + 1}. {run.steps[event.step]?.name}</dd>
        <dt>Nội dung</dt><dd>{mask(event.text) || "—"}</dd>
      </dl>
      {event.data ? <pre className="code">{mask(JSON.stringify(event.data, null, 2))}</pre> : null}
    </Section>
  );
}

// ---- nội dung trợ lý điền ----------------------------------------------------------------------------------------------

type FillFilter = "all" | "edited" | "missing" | "same" | "nodata";

function FillView({ run, onChanged }: { run: LabRunView; onChanged: () => void }) {
  const [filter, setFilter] = useState<FillFilter>("all");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const s = run.summary;
  const edited = (r: LabRow) => ["llm", "ocr", "other", "cleared"].includes(r.verdict);
  const filters: { key: FillFilter; label: string; test: (r: LabRow) => boolean }[] = [
    { key: "all", label: "Tất cả", test: () => true },
    { key: "edited", label: "Người dân sửa", test: edited },
    { key: "missing", label: "Trợ lý bỏ trống", test: (r) => r.verdict === "missing" && !!r.final },
    { key: "same", label: "Giữ nguyên", test: (r) => r.verdict === "same" && !!r.be },
    { key: "nodata", label: "Form không nhận", test: (r) => r.verdict === "nodata" },
  ];
  const test = filters.find((f) => f.key === filter)!.test;
  const rows = run.rows.filter(test);
  const edits = run.snapshots.filter((x) => x.kind === "edit");
  const editSpan = edits.length ? (edits[edits.length - 1].t ?? 0) - (edits[0].t ?? 0) : 0;
  const groups = ["ocr", "llm", "other", "cleared", "missing", "nodata"]
    .map((v) => ({ v, rows: run.rows.filter((r) => r.verdict === v && (v !== "missing" || (!!r.final && r.onDocs > 0))) }))
    .filter((g) => g.rows.length);

  if (!run.rows.length) {
    return <EmptyState title={run.kind === "attach" ? "Lượt đính kèm không có ô tờ khai" : "Lượt không có ô nào"} hint="Backend không trả trường nào và kho chưa có ảnh chụp form của lượt." />;
  }
  return (
    <div className="lab-fill">
      <div className="kpis">
        <div className="kpi"><span>Ô trên tờ khai</span><b>{s.total}</b><small>{s.beFilled} trợ lý điền · {s.missing} người dân tự điền</small></div>
        <div className="kpi"><span>Trợ lý điền đúng</span><b>{s.beFilled ? `${s.same}/${s.beFilled}` : "—"}</b><small>{pct(s.same, s.beFilled)} · người dân giữ nguyên khi nộp</small></div>
        <div className="kpi"><span>Người dân sửa</span><b className={s.edited ? "lab-bad" : undefined}>{s.edited}</b>
          <small>{["ocr", "llm", "other", "cleared"].filter((v) => s.byVerdict[v]).map((v) => `${s.byVerdict[v]} ${VERDICTS[v].cause?.toLowerCase()}`).join(" · ") || "không ô nào"}</small></div>
        <div className="kpi"><span>Trợ lý bỏ trống</span><b>{s.missing}</b><small>{s.missingOnDocs} ô có trên giấy tờ · {s.nodata} ô form không nhận</small></div>
        <div className="kpi"><span>Người dân tự sửa mất</span><b>{edits.length ? humanDuration(editSpan) : "—"}</b>
          <small>{edits.length ? `${edits.length} lần sửa, từ ${offset(edits[0].t)} đến ${offset(edits[edits.length - 1].t)}` : "không có lần sửa nào"}</small></div>
      </div>

      <Section title="Từng ô: trợ lý điền gì, lấy từ đâu, người dân nộp gì" actions={
        run.kind === "autofill" && !run.caseId ? (
          <button className="btn btn--sm" type="button" disabled={busy} onClick={async () => {
            setBusy(true);
            try {
              const res = await labApi.createCase(run.requestId);
              setMessage(`Đã tạo ca ${res.caseId}: ${s.edited + s.missingOnDocs} ô bị sửa / bỏ sót nằm trong đáp án.`);
              onChanged();
            } catch (reason) {
              setMessage(reason instanceof Error ? reason.message : String(reason));
            } finally {
              setBusy(false);
            }
          }}>{busy ? <Spinner label="Đang tạo…" /> : <><Icon name="flask" size={14} /> Đưa {s.edited + s.missingOnDocs} ô bị sửa vào ca test</>}</button>
        ) : run.caseId ? <span className="lab-badge lab-badge--ok">Đã có ca {run.caseId}</span> : null
      }>
        {message ? <div className="lab-msg lab-msg--ok">{message}</div> : null}
        <div className="chips lab-chips">
          {filters.map((f) => (
            <button key={f.key} type="button" className="lab-chip" aria-pressed={filter === f.key} onClick={() => setFilter(f.key)}>
              {f.label} <span className="count">{run.rows.filter(f.test).length}</span>
            </button>
          ))}
        </div>
        <div className="table-wrap">
          <table className="grid lab-fill__table">
            <thead><tr><th>Ô trên tờ khai</th><th>Trợ lý điền · nguồn</th><th>Form nhận</th><th>Giá trị khi nộp</th><th>Kết quả</th><th>Ghi chú</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key} className={edited(r) ? "is-bad" : r.verdict === "missing" || r.verdict === "nodata" ? "is-warn" : undefined}>
                  <td><span className="cell-main">{r.label}</span><span className="cell-sub mono">{r.key}{r.section ? ` · ${r.section}` : ""}</span></td>
                  <td><span className="cell-main"><Masked value={r.inBe ? r.be : ""} /></span><span className="cell-sub">{SOURCE_TEXT[r.source]}</span></td>
                  <td><Masked value={r.fill} /></td>
                  <td><b><Masked value={r.final} /></b></td>
                  <td><VerdictBadge verdict={r.verdict} /></td>
                  <td className="lab-note">{r.verdict === "same" ? "" : r.verdictText}{r.onDocs ? `${r.verdict === "same" ? "" : " · "}có trên ${r.onDocs} giấy tờ` : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="lab-hint">Đang hiện {rows.length}/{run.rows.length} ô. “Giá trị khi nộp” lấy từ ảnh chụp form cuối (trước khi nộp) và là đáp án khi dùng lượt này làm ca test.
          {run.hasReview ? "" : " Lượt này chưa có ảnh chụp form nên chỉ có giá trị backend trả."}</p>
      </Section>

      {groups.length ? (
        <Section title="Vì sao các ô bị sửa" sub="gom theo nguyên nhân để so giữa các lượt">
          <div className="lab-causes">
            {groups.map((g) => (
              <div key={g.v} className={`lab-cause lab-cause--${VERDICTS[g.v].tone}`}>
                <h3>{VERDICTS[g.v].cause} <span className="count">{g.rows.length} ô</span></h3>
                <p className="lab-cause__fields">{g.rows.map((r) => r.label).join(", ")}</p>
                <p>{VERDICTS[g.v].fix}</p>
                {g.rows.slice(0, 4).map((r) => (
                  <p key={r.key} className="lab-cause__diff"><b>{r.label}</b>: <Masked value={r.inBe ? r.be : ""} empty="(trống)" /> → <Masked value={r.final} empty="(trống)" /></p>
                ))}
              </div>
            ))}
          </div>
        </Section>
      ) : null}

      <Section title={`Ảnh chụp form · ${run.snapshots.length} bản`} sub="Extension tự chụp giá trị ô sau khi điền, mỗi lần sửa (gộp 3 giây) và khi rời bước kê khai">
        {run.snapshots.length ? (
          <div className="table-wrap">
            <table className="grid">
              <thead><tr><th>Bản</th><th>Mốc</th><th>Lý do tự lưu</th><th className="right">Số ô</th><th>Extension</th><th>Trang</th><th /></tr></thead>
              <tbody>
                {run.snapshots.map((x, i) => (
                  <tr key={x.id}>
                    <td><span className="lab-snapchip is-static">{x.id}</span></td>
                    <td className="num">{offset(x.t)} · {x.t !== null ? clockAt(run.startAt, x.t) : formatDateTime(x.at)}</td>
                    <td>{x.label}{i === run.snapshots.length - 1 && run.snapshots.length > 1 ? <span className="lab-badge lab-badge--ok">dùng làm đáp án</span> : null}{x.empty ? <span className="lab-badge lab-badge--warn">form trống</span> : null}</td>
                    <td className="num right">{x.fields ?? "—"}</td>
                    <td className="num">{x.extVersion ?? "—"}</td>
                    <td className="mono lab-note">{x.host ?? ""}</td>
                    <td><a href={`/autotest/replay/${encodeURIComponent(run.requestId)}?snap=${x.id}`}
                           onClick={(e) => onLinkClick(e, `/autotest/replay/${encodeURIComponent(run.requestId)}?snap=${x.id}`)}>Xem trong tái hiện</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <EmptyState title="Kho chưa có ảnh chụp form của lượt này" hint="Extension gửi ảnh chụp form sang kho; lượt chạy trên máy dev không bật kho thì không có." />}
        <p className="lab-hint">Mỗi bản hiện chỉ lưu giá trị từng ô (kho dựng bảng be → fill → final). Lưu thêm HTML vùng tờ khai để dựng lại đúng giao diện lúc đó là đợt 2 (xem Cấu hình ghi).</p>
      </Section>
    </div>
  );
}

// ---- tệp ------------------------------------------------------------------------------------------------------------

function FilesView({ run }: { run: LabRunView }) {
  const [open, setOpen] = useState<number | null>(null);
  const mask = useMask();
  if (!run.files.length) return <EmptyState title="Lượt không có tệp" />;
  return (
    <Section title={`Tệp của lượt · ${run.files.length}`} sub="Tệp gốc không tải về từ đây; xem văn bản OCR đã ghi">
      <div className="table-wrap">
        <table className="grid">
          <thead><tr><th>#</th><th>Tên tệp</th><th>Loại</th><th className="right">Kích thước</th><th className="right">Trang</th><th className="right">Ký tự OCR</th><th>Cache</th><th>Lỗi</th><th /></tr></thead>
          <tbody>
            {run.files.map((f) => (
              <tr key={f.idx}>
                <td className="num">{f.idx + 1}</td>
                <td className="mono">{f.name}</td>
                <td>{f.type ?? "—"}{f.role ? ` · ${f.role}` : ""}</td>
                <td className="num right">{formatBytes(f.size)}</td>
                <td className="num right">{f.pages ?? "—"}</td>
                <td className="num right">{f.chars ?? (f.ocr ? f.ocr.length : "—")}</td>
                <td>{f.cache ?? "—"}</td>
                <td>{f.error ? <span className="lab-badge lab-badge--bad">{f.error}</span> : ""}</td>
                <td>{f.ocr ? <button className="linklike" type="button" onClick={() => setOpen(open === f.idx ? null : f.idx)}>{open === f.idx ? "Ẩn OCR" : "Xem OCR"}</button> : null}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {open !== null ? <pre className="code code--tall lab-ocr">{mask(run.files[open]?.ocr ?? "")}</pre> : null}
    </Section>
  );
}

// ---- gói ghi thô ------------------------------------------------------------------------------------------------------

function RawView({ requestId }: { requestId: string }) {
  const { data, error, loading, reload } = useAsync(() => labApi.raw(requestId), `raw:${requestId}`);
  if (loading && !data) return <PageLoading label="Đang tải gói ghi thô…" />;
  if (error && !data) return <ErrorNotice message={error} onRetry={reload} />;
  return (
    <Section title="Gói ghi thô" sub="process_requests · traces · trace_steps · formReview · OCR · hội thoại, đúng như đang lưu"
             actions={<button className="btn btn--sm" type="button" onClick={() => downloadJson(`${requestId}.json`, data)}><Icon name="download" size={14} /> Tải .json</button>}>
      <Json value={data} tall />
    </Section>
  );
}

