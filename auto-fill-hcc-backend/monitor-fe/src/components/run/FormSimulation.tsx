import { createElement, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { findSim, loadAngularForm, loadAreaCatalog, loadForm, type SimEntry } from "../../simulations/registry";
import { foldChoice, simulateEform, type Cell, type Eform, type EformResult, type SimStats, type Unmatched as UnmatchedRow } from "../../simulations/eform";
import { simulateAngular, type AreaCatalog, type NgField, type NgForm } from "../../simulations/angular";
import { toFields, type UiField } from "../../simulations/fill";
import { useAsync } from "../../hooks";
import { formatDateTime } from "../../format";
import type { RunDetail } from "../../types";
import { EmptyState, ErrorNotice, Spinner } from "../Status";
import { show } from "./model";

const STATUS_TEXT: Record<Cell["status"], string> = {
  filled: "đã điền (viền xanh)",
  default: "giá trị mặc định (viền vàng)",
  miss: "BE có giá trị nhưng không vào được ô (viền đỏ)",
  empty: "trống (cổng tô đỏ)",
  "hidden-value": "có giá trị nhưng khối đang ẩn",
  prefilled: "cổng tự điền (theo tài khoản / mặc định)",
  unchecked: "có giá trị, chưa có danh sách option để kiểm",
  auto: "extension tự quyết lúc chạy",
  blank: "trống, cổng không tô (không bắt buộc)",
};

// Thẻ HTML của mẫu được dựng lại; thẻ khác bỏ vỏ, giữ nội dung. Không giữ style của cổng ngoài căn lề.
const TAGS = new Set(["p", "strong", "b", "em", "i", "u", "br", "span", "div", "table", "thead", "tbody", "tr", "td", "th", "ul", "ol", "li", "sup", "sub", "h1", "h2", "h3", "h4", "h5", "h6"]);

interface Ctx {
  notFound: Set<string>;
}

interface HtmlCtx extends Ctx {
  form: Eform;
  sim: EformResult;
}

function OptionList({ cell, onClose }: { cell: Cell; onClose: () => void }) {
  const [q, setQ] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const away = (e: MouseEvent) => { if (ref.current && !ref.current.parentElement?.contains(e.target as Node)) onClose(); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("mousedown", away);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", away); document.removeEventListener("keydown", esc); };
  }, [onClose]);
  const opts = cell.options ?? [];
  const needle = foldChoice(q);
  const hits = needle ? opts.filter(([, l]) => foldChoice(l).includes(needle)) : opts;
  return (
    <div className="ef-pop" ref={ref} role="dialog" aria-label={`Danh sách option của ${cell.name}`}>
      <input autoFocus className="input" placeholder={`Tìm trong ${opts.length} option…`} value={q} onChange={(e) => setQ(e.target.value)} />
      <ul>
        {hits.slice(0, 300).map(([v, l]) => (
          <li key={v + l} className={cell.picked?.[0] === v ? "is-on" : undefined}>{l}</li>
        ))}
        {hits.length > 300 ? <li className="faint">… còn {hits.length - 300} option, gõ để lọc</li> : null}
        {!hits.length ? <li className="faint">Không có option nào khớp</li> : null}
      </ul>
    </div>
  );
}

function Notes({ cell, ctx }: { cell: Cell; ctx: Ctx }) {
  const notes: { text: string; bad?: boolean }[] = [];
  if (cell.status === "auto" || cell.status === "unchecked" || cell.status === "prefilled") {
    cell.reasons.forEach((r) => notes.push({ text: r }));
  } else if (cell.status === "miss" || cell.status === "hidden-value") {
    notes.push({ text: `"${show(cell.want)}" — ${cell.reasons.join("; ")}`, bad: true });
  } else {
    if (cell.how === "loose") notes.push({ text: `khớp lỏng từ "${show(cell.want)}"` });
    if (cell.how === "mirror") notes.push({ text: "extension chép từ số định danh" });
    cell.reasons.forEach((r) => notes.push({ text: r, bad: true }));
  }
  if (cell.via && !cell.key.includes("/")) notes.push({ text: cell.via });
  if (!cell.key.includes("/") && ctx.notFound.has(cell.name.toLowerCase())) notes.push({ text: "lượt thật: extension báo không thấy", bad: true });
  return <>{notes.map((n) => <small key={n.text} className={`ef-note${n.bad ? "" : " ef-note--info"}`}>{n.text}</small>)}</>;
}

function Widget({ cell, ctx }: { cell: Cell; ctx: Ctx }) {
  const [open, setOpen] = useState(false);
  const title = `${cell.name} (${cell.type})${cell.required ? " — bắt buộc" : ""}\n${STATUS_TEXT[cell.status]}`;
  let body: ReactNode;
  if (cell.type === "x-radio") {
    body = (
      <span className="ef-radios">
        {(cell.options ?? []).map(([v, l]) => (
          <span key={v} className={`ef-radio${cell.picked?.[0] === v ? " is-on" : ""}`}><i aria-hidden="true" />{l}</span>
        ))}
      </span>
    );
  } else if (cell.type === "checkbox") {
    body = <span className={`ef-radio${cell.picked ? " is-on" : ""}`}><i aria-hidden="true" />{cell.label}</span>;
  } else if (cell.type === "x-select") {
    const hasList = (cell.options?.length ?? 0) > 0;
    body = (
      <button type="button" className="ef-select" onClick={() => setOpen((o) => !o)} aria-expanded={open} disabled={!hasList && !cell.options}>
        <span className={cell.text ? undefined : "ef-muted"}>
          {cell.text ?? (cell.status === "miss" ? <s>{show(cell.want)}</s> : cell.status === "prefilled" ? "(cổng tự điền)" : "-- Chọn --")}
        </span>
        <b aria-hidden="true">▾</b>
      </button>
    );
  } else {
    const placeholder = cell.type === "x-date" ? "dd/mm/yyyy" : "";
    body = cell.text
      ? <span>{cell.text}</span>
      : cell.status === "miss" ? <s>{show(cell.want)}</s>
      : cell.status === "prefilled" ? <span className="ef-muted">(cổng tự điền)</span>
      : cell.status === "auto" ? <span className="ef-muted">{cell.want !== undefined ? show(cell.want) : "(extension tự quyết)"}</span>
      : <span className="ef-muted">{placeholder}</span>;
  }
  return (
    <span className="ef-slot">
      <span id={`ef-${cell.key}`} className={`ef-w ef-w--${cell.type.replace("x-", "")} is-${cell.status}`} title={title}>
        {cell.required ? <em className="ef-req" aria-label="bắt buộc">*</em> : null}
        {body}
        {open ? <OptionList cell={cell} onClose={() => setOpen(false)} /> : null}
      </span>
      <Notes cell={cell} ctx={ctx} />
    </span>
  );
}

function Area({ name, ctx }: { name: string; ctx: HtmlCtx }) {
  const f = ctx.form.fields[name];
  const cells = (f.parts ?? []).filter((p) => p.name).map((p) => ctx.sim.cells.get(`${name}/${p.name}`)).filter(Boolean) as Cell[];
  const visible = ctx.sim.visibleAreas.has(name);
  if (!visible && !cells.some((c) => c.status === "hidden-value")) return null;
  const via = cells.find((c) => c.via)?.via;
  return (
    <span className={`ef-area${visible ? "" : " ef-area--hidden"}`} title={name}>
      {!visible ? <small className="ef-note">Khối {name} đang ẩn — chỉ hiện khi {ctx.sim.hiddenBy.get(name)}</small> : null}
      {via ? <small className="ef-note ef-note--info">{via}</small> : null}
      {(f.parts ?? []).map((p, i) => {
        if (!p.name) return <span key={`br${i}`} className="ef-br" />;
        const cell = ctx.sim.cells.get(`${name}/${p.name}`);
        if (!cell) return null;
        return (
          <span key={p.name} className={`ef-part${p.br ? " ef-part--wide" : ""}`}>
            {p.label ? <span className="ef-part__label">{p.label}</span> : null}
            <Widget cell={cell} ctx={ctx} />
          </span>
        );
      })}
    </span>
  );
}

function renderNodes(nodes: NodeListOf<ChildNode>, ctx: HtmlCtx, prefix: string): ReactNode[] {
  const out: ReactNode[] = [];
  nodes.forEach((node, i) => {
    const key = `${prefix}.${i}`;
    if (node.nodeType === Node.TEXT_NODE) {
      if (node.textContent) out.push(node.textContent.replace(/\u00a0/g, " "));
      return;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    const el = node as Element;
    const tag = el.tagName.toLowerCase();
    const name = el.getAttribute("name");
    if (tag === "span" && el.classList.contains("mention") && name) {
      const f = ctx.form.fields[name];
      if (!f) return;
      if (f.type === "x-select-area") out.push(<Area key={key} name={name} ctx={ctx} />);
      else {
        const cell = ctx.sim.cells.get(name);
        if (cell) out.push(<Widget key={key} cell={cell} ctx={ctx} />);
      }
      return;
    }
    const children = renderNodes(el.childNodes, ctx, key);
    if (!TAGS.has(tag)) { out.push(...children); return; }
    if (tag === "br") { out.push(<br key={key} />); return; }
    const align = (el as HTMLElement).style?.textAlign;
    const props: Record<string, unknown> = { key };
    if (align) props.style = { textAlign: align };
    if (tag === "td" || tag === "th") {
      const cs = el.getAttribute("colspan"); const rs = el.getAttribute("rowspan");
      if (cs) props.colSpan = Number(cs);
      if (rs) props.rowSpan = Number(rs);
    }
    out.push(createElement(tag, props, ...children));
  });
  return out;
}

function jump(key: string) {
  const el = document.getElementById(`ef-${key}`);
  if (!el) return;
  el.scrollIntoView({ behavior: "smooth", block: "center" });
  el.classList.remove("is-flash");
  void el.offsetWidth;
  el.classList.add("is-flash");
}

function Summary({ stats, cells, source, children }: { stats: SimStats; cells: Cell[]; source: ReactNode; children?: ReactNode }) {
  const problems = cells.filter((c) => c.status === "miss" || c.status === "hidden-value" || (c.status === "filled" && c.how === "loose" && c.reasons.length));
  const unchecked = cells.filter((c) => c.status === "unchecked").length;
  return (
    <div className="panel panel__body ef-summary">
      <div className="sim-legend">
        <span><b className="num">{stats.filled}/{stats.cells}</b> ô có giá trị</span>
        {stats.defaults ? <span><i className="sim-dot sim-dot--default" />{stats.defaults} mặc định</span> : null}
        <span className={stats.red ? "ef-red" : undefined}><i className="sim-dot sim-dot--empty" /><b>{stats.red}</b> ô sẽ đỏ trên cổng</span>
        <span className="faint">({stats.miss} giá trị không vào được · {stats.requiredEmpty} bắt buộc còn trống)</span>
        {unchecked ? <span className="faint">{unchecked} ô chưa kiểm được option</span> : null}
      </div>
      <div className="faint ef-source">{source}</div>
      {children}
      {problems.length ? (
        <ul className="ef-problems">
          {problems.map((c) => (
            <li key={c.key}>
              <button type="button" className="linklike" onClick={() => jump(c.key)}>
                <span className="mono">{c.key}</span>
              </button>
              {" "}<b>"{show(c.want)}"</b> — {c.reasons.join("; ")}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function FormView({ form, sim, notFound }: { form: Eform; sim: EformResult; notFound: Set<string> }) {
  const doc = useMemo(() => new DOMParser().parseFromString(form.html, "text/html"), [form]);
  const ctx: HtmlCtx = { form, sim, notFound };
  return (
    <>
      <Summary stats={sim.stats} cells={[...sim.cells.values()]}
        source={<>Mẫu thật của cổng: {form.name} · <span className="mono">tokhaidientu.moj.gov.vn{form.path}</span> · chụp {formatDateTime(form.fetchedAt)}</>} />
      <div className="sim-form ef-doc">{renderNodes(doc.body.childNodes, ctx, "n")}</div>
    </>
  );
}

function Unmatched({ list, many }: { list: UnmatchedRow[]; many?: boolean }) {
  if (!list.length) return null;
  return (
    <div className="panel panel__body" style={{ marginTop: 12 }}>
      <div className="section-title">Field BE trả nhưng {many ? "không tờ khai nào" : "mẫu"} có ô ({list.length})</div>
      <table className="mini-table ef-unmatched">
        <thead><tr><th>Field</th><th>comp</th><th>Giá trị</th><th>Lý do</th></tr></thead>
        <tbody>
          {list.map(({ field, reason }) => (
            <tr key={field.name}><td className="mono">{field.name}</td><td className="mono">{field.comp ?? "—"}</td><td>{show(field.value)}</td><td>{reason}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Form Angular (cổng liên thông): dựng theo khối → ô từ mẫu chụp, không có HTML bố cục của cổng. */
function AngularSimulation({ form, area, run }: { form: NgForm; area: AreaCatalog; run: RunDetail }) {
  const response = run.steps?.outputs?.response;
  const sim = useMemo(() => simulateAngular(form, toFields(response), area), [form, area, response]);
  const notFound = new Set(((run.trace?.report?.notFound as string[] | undefined) ?? []).map((n) => n.toLowerCase()));
  const ctx: Ctx = { notFound };
  const cellsOf = (f: NgField) => (f.kind === "diachi" ? ["tinh", "xa", "diaChi"].map((r) => sim.cells.get(`${f.key}/${r}`)) : [sim.cells.get(f.key)]).filter(Boolean) as Cell[];
  return (
    <div className="sim-form-wrap">
      <Summary stats={sim.stats} cells={[...sim.cells.values()]}
        source={<>Mẫu chụp từ cổng: <span className="mono">{form.source}</span>{form.step ? ` · bước "${form.step}"` : ""} · chụp {formatDateTime(form.capturedAt)}{form.note ? ` · ${form.note}` : ""}</>} />
      <div className="sim-form ng-form">
        <h2 className="ng-form__title">{form.title}</h2>
        {form.sections.map((sec, si) => (
          <section key={`${si}-${sec.title}`} className="ng-sec">
            {sec.title ? <h3>{sec.title}</h3> : null}
            <div className="ng-grid">
              {sec.fields.map((f) => (
                <div key={f.key} className={`ng-field${f.kind === "diachi" || f.kind === "radio" ? " ng-field--wide" : ""}`}>
                  {f.kind !== "checkbox" ? (
                    <span className="ng-field__label">
                      {f.kind === "diachi" ? "Địa chỉ" : f.label || (f.kind === "radio" ? "" : f.key)}
                      {f.required && f.kind !== "diachi" ? <em className="ef-req"> *</em> : null}
                      <code>{f.key}</code>
                    </span>
                  ) : null}
                  {f.kind === "diachi" ? (
                    <span className="ng-parts">
                      {cellsOf(f).map((c) => (
                        <span key={c.key} className="ef-part">
                          <span className="ef-part__label">{c.label}{c.required ? " *" : ""}</span>
                          <Widget cell={c} ctx={ctx} />
                        </span>
                      ))}
                    </span>
                  ) : cellsOf(f).map((c) => <Widget key={c.key} cell={c} ctx={ctx} />)}
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
      <Unmatched list={sim.unmatched} />
    </div>
  );
}

function Simulation({ entry, forms, run }: { entry: SimEntry; forms: Eform[]; run: RunDetail }) {
  const response = run.steps?.outputs?.response;
  const fields = useMemo(() => toFields(response), [response]);
  const sims = useMemo(() => forms.map((form) => simulateEform(form, fields)), [forms, fields]);
  // Nhiều tờ khai: extension điền tờ khai đang mở, field thuộc tờ khai kia sẽ "không thấy" ở tờ này →
  // chỉ coi là field không có ô khi KHÔNG tờ khai nào nhận nó.
  const unmatched = useMemo(() => {
    const missing = (f: UiField) => sims.every((sim) => sim.unmatched.some((u) => u.field === f));
    return sims[0]?.unmatched.filter((u) => missing(u.field)) ?? [];
  }, [sims]);
  // Tờ khai mở sẵn = tờ nhận được nhiều field nhất của lượt này.
  const best = sims.reduce((bi, sim, i) => (fields.length - sim.unmatched.length > fields.length - sims[bi].unmatched.length ? i : bi), 0);
  const [picked, setPicked] = useState<number | null>(null);
  const active = picked ?? best;
  const notFound = new Set(((run.trace?.report?.notFound as string[] | undefined) ?? []).map((n) => n.toLowerCase()));

  return (
    <div className="sim-form-wrap">
      {entry.note ? <p className="faint ef-entry-note">{entry.note}</p> : null}
      {forms.length > 1 ? (
        <div className="seg ef-tabs" role="tablist" aria-label="Tờ khai">
          {forms.map((form, i) => (
            <button key={form.id} type="button" role="tab" aria-selected={i === active} onClick={() => setPicked(i)}>
              Tờ khai {i + 1}: {form.name}
              <span className={sims[i].stats.red ? "ef-red" : "faint"}> · {sims[i].stats.red} đỏ</span>
            </button>
          ))}
        </div>
      ) : null}
      <FormView key={forms[active].id} form={forms[active]} sim={sims[active]} notFound={notFound} />

      <Unmatched list={unmatched} many={forms.length > 1} />
    </div>
  );
}

/** Mô phỏng form: output trả FE (T5) điền vào mẫu e-form thật của cổng theo quy tắc của extension. */
export default function FormSimulation({ run }: { run: RunDetail }) {
  const procedure = run.trace?.procedure ?? (run.steps?.meta?.procedure as string | undefined);
  const entry = findSim(procedure);
  const { data, error, loading, reload } = useAsync(async () => {
    if (!entry) return null;
    if (entry.angular) {
      const [form, area] = await Promise.all([loadAngularForm(entry.angular), loadAreaCatalog()]);
      return { kind: "angular" as const, form, area };
    }
    return { kind: "eform" as const, forms: await Promise.all((entry.forms ?? []).map(loadForm)) };
  }, entry?.key ?? "none");
  if (!entry) {
    return <EmptyState title={`Chưa có mẫu mô phỏng cho thủ tục "${procedure ?? "?"}"`} hint="Tạo thư mục monitor-fe/src/simulations/thu-tuc/<key thủ tục>/index.ts khai mẫu (xem docs/web-monitor/mo-phong-form.md)." />;
  }
  if (!toFields(run.steps?.outputs?.response).length) {
    return <EmptyState title="Lượt này chưa có output trả FE (T5)" hint="Lượt ghi trước khi bật bộ ghi công đoạn không lưu output trả FE." />;
  }
  if (error) return <ErrorNotice message={error} onRetry={reload} />;
  if (loading || !data) return <Spinner label="Đang tải mẫu form" />;
  if (data.kind === "angular") return <AngularSimulation form={data.form} area={data.area} run={run} />;
  return <Simulation entry={entry} forms={data.forms} run={run} />;
}
