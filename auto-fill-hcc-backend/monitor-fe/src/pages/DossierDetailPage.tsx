import { useEffect } from "react";
import { getDossier } from "../api";
import CopyButton from "../components/CopyButton";
import StageRibbon from "../components/StageRibbon";
import { ErrorNotice, PageLoading } from "../components/Status";
import { KindTag, OutcomeBadge, SourceTag } from "../components/Tags";
import { formatClock, formatDateTime, formatMs } from "../format";
import { useAsync, useFacets } from "../hooks";
import { navigate, onLinkClick } from "../router";
import type { DossierDetail, Timing } from "../types";
import { DossierStatus } from "./DossiersPage";
import { runHref } from "./RunsPage";

interface Event {
  at: string;
  type: "start" | "run" | "report" | "submit" | "rating" | "close";
  title: string;
  kind?: string;
  outcome?: string;
  timing?: Timing | null;
  legacyMs?: number | null;
  href?: string;
  detail?: string;
}

function buildEvents(data: DossierDetail): Event[] {
  const d = data.dossier;
  const ev: Event[] = [];
  if (d?.startedAt) ev.push({ at: d.startedAt, type: "start", title: "Bắt đầu hồ sơ" });
  for (const t of data.traces) {
    ev.push({
      at: t.created_at, type: "run", title: "", kind: t.kind, outcome: t.outcome ?? (t.status === "error" ? "error" : "ok"),
      timing: t.timing, legacyMs: t.timing ? null : t.stats?.total_latency_ms, href: runHref(t as { request_id: string; kind?: string }),
      detail: t.error_code ?? undefined,
    });
    const received = t.report?.received_at;
    if (received) {
      const r = t.report as Record<string, unknown>;
      const count = t.kind === "attach" ? r.attached ?? r.uploadedAttachments : r.filled;
      const errs = Array.isArray(r.errors) ? r.errors.length : 0;
      const missing = Array.isArray(r.notFound) ? r.notFound.length : 0;
      const summary = [
        count !== undefined ? `${t.kind === "attach" ? "đính" : "điền"} ${count} ${t.kind === "attach" ? "tệp" : "ô"}` : "",
        missing ? `${missing} ô không thấy` : "",
        errs ? `${errs} lỗi` : "",
      ].filter(Boolean).join(", ");
      ev.push({ at: String(received), type: "report", title: `Extension báo kết quả ${t.kind === "attach" ? "đính kèm" : "điền"}`, detail: summary });
    }
  }
  for (const s of data.stepsOnly) {
    ev.push({ at: String(s.created_at), type: "run", title: "", kind: s.kind, outcome: s.outcome, timing: s.timing, href: runHref(s) });
  }
  for (const e of d?.submitEvents ?? []) ev.push({ at: e.at, type: "submit", title: "Bấm nộp trên cổng", detail: e.host });
  if (d?.closedAt) ev.push({ at: d.closedAt, type: "close", title: "Đóng hồ sơ", detail: d.closeReason });
  return ev.filter((e) => e.at).sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());
}

export default function DossierDetailPage({ id }: { id: string }) {
  const { data, error, loading, reload } = useAsync(() => getDossier(id), id);
  const { unitName, procLabel } = useFacets();
  const procTitle = data?.dossier ? procLabel(data.dossier.procedure, data.dossier.procedureLabel) : "";
  useEffect(() => {
    document.title = procTitle && procTitle !== "—" ? `Hồ sơ · ${procTitle} — Monitor` : "Hồ sơ — Monitor";
    return () => { document.title = "Monitor — Trợ lý nhân dân"; };
  }, [procTitle]);

  if (loading && !data) return <PageLoading label="Đang tải hồ sơ…" />;
  if (error && !data) return <ErrorNotice message={error} onRetry={reload} />;
  if (!data) return null;
  const d = data.dossier;
  const events = buildEvents(data);

  return (
    <>
      <nav className="crumbs" aria-label="Vị trí">
        <a href="/dossiers" onClick={(e) => onLinkClick(e, "/dossiers")}>Hồ sơ</a><span>/</span><span className="mono">{id}</span>
      </nav>
      <section className="run-head">
        <div className="run-head__title">
          <h1>{d?.applicantName || procLabel(d?.procedure, d?.procedureLabel)}</h1>
          <div className="run-head__meta">
            {d ? <DossierStatus d={d} /> : null}
            <SourceTag source={d?.experience} />
            <span>{procLabel(d?.procedure, d?.procedureLabel)}</span><span>·</span>
            <span>{unitName(d?.userId, d?.name)}</span><span>·</span>
            <span className="num">bắt đầu {formatDateTime(d?.startedAt)}</span>
          </div>
        </div>
        <div className="run-head__actions"><CopyButton text={id} label="Sao chép mã hồ sơ" /></div>
        <div className="facts">
          <span><b>{data.traces.length + data.stepsOnly.length}</b> lượt xử lý</span>
          <span>Tới lúc nộp <b>{formatMs(d?.durationMs)}</b></span>
          {d?.rating?.label ? <span>Đánh giá <b>{d.rating.label}</b>{d.rating.reasons?.length ? ` — ${d.rating.reasons.join(", ")}` : ""}</span> : null}
        </div>
      </section>

      <div className="panel panel__body">
        <ol className="timeline">
          {events.map((e, i) => (
            <li key={i}>
              <time dateTime={e.at}>{formatClock(e.at)}</time>
              <span className={`timeline__dot${e.type === "run" ? (e.outcome === "error" ? " timeline__dot--error" : " timeline__dot--run") : e.type === "submit" ? " timeline__dot--submit" : ""}`} />
              <div className="timeline__body">
                {e.type === "run" ? (
                  <>
                    <div className="timeline__line">
                      <KindTag kind={e.kind} />
                      <OutcomeBadge outcome={e.outcome} />
                      <span className="mono">{formatMs(e.timing?.wait ?? e.legacyMs)}</span>
                      {e.href ? <a href={e.href} onClick={(ev) => { ev.preventDefault(); navigate(e.href!); }}>Chi tiết</a> : null}
                    </div>
                    <StageRibbon timing={e.timing} legacyMs={e.legacyMs} />
                    {e.detail ? <span className="dropped">{e.detail}</span> : null}
                  </>
                ) : (
                  <div className="timeline__line"><b>{e.title}</b>{e.detail ? <span className="muted">{e.detail}</span> : null}</div>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </>
  );
}
