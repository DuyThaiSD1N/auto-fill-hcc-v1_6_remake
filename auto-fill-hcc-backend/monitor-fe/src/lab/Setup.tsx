import { useRef, useState, type DragEvent } from "react";
import Icon from "../components/Icon";
import { formatBytes } from "../format";
import { MAX_RUNS, MAX_SETS, type DocSet } from "./engine";
import { GROUPS, LAB_PROCEDURES, type LabProcedure } from "./procedures";

export interface SetupState {
  procedure: string;
  setCount: number;
  runCount: number;
  attach: boolean;
  split: boolean;
  variant: string;
}

const COUNTS = [1, 2, 3, 4, 5];

function Counter({ label, value, max, onChange, disabled }: { label: string; value: number; max: number; onChange: (n: number) => void; disabled: boolean }) {
  return (
    <div className="lab-counter">
      <span className="lab-label">{label}</span>
      <div className="seg" role="radiogroup" aria-label={label}>
        {COUNTS.filter((n) => n <= max).map((n) => (
          <button key={n} type="button" role="radio" aria-checked={value === n} aria-pressed={value === n} disabled={disabled} onClick={() => onChange(n)}>
            {n}
          </button>
        ))}
      </div>
    </div>
  );
}

function SetCard({ index, set, onChange, disabled }: {
  index: number;
  set: DocSet;
  onChange: (patch: Partial<DocSet>) => void;
  disabled: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const add = (list: FileList | null) => {
    if (!list?.length) return;
    onChange({ files: [...set.files, ...Array.from(list)] });
  };
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    if (!disabled) add(e.dataTransfer.files);
  };
  const size = set.files.reduce((sum, f) => sum + f.size, 0);
  const applicantSet = !!(set.applicant.name || set.applicant.id);

  return (
    <div className={`lab-set${set.files.length ? "" : " lab-set--empty"}`}>
      <div className="lab-set__head">
        <span className="lab-set__no num">{index + 1}</span>
        <input className="input lab-set__name" aria-label={`Tên bộ tài liệu ${index + 1}`} value={set.name} disabled={disabled}
               onChange={(e) => onChange({ name: e.target.value })} />
        {set.files.length ? (
          <button className="btn btn--sm btn--ghost" type="button" disabled={disabled} onClick={() => onChange({ files: [] })}>Xoá tệp</button>
        ) : null}
      </div>
      <label className={`lab-drop${over ? " is-over" : ""}${disabled ? " is-disabled" : ""}`}
             onDragOver={(e) => { e.preventDefault(); if (!disabled) setOver(true); }}
             onDragLeave={() => setOver(false)} onDrop={onDrop}>
        <Icon name="file" size={18} />
        <span><b>Chọn tệp</b> hoặc kéo thả vào đây<small>Ảnh hoặc PDF, nhiều tệp — gửi đúng thứ tự trong danh sách</small></span>
        <input ref={input} type="file" multiple accept="image/*,.pdf,application/pdf" disabled={disabled} className="sr-only"
               onChange={(e) => { add(e.target.files); e.target.value = ""; }} />
      </label>
      {set.files.length ? (
        <ol className="lab-files">
          {set.files.map((f, i) => (
            <li key={`${f.name}-${i}`}>
              <span className="lab-files__name" title={f.name}>{f.name}</span>
              <span className="faint num">{formatBytes(f.size)}</span>
              <button className="btn btn--icon btn--ghost btn--sm" type="button" disabled={disabled} aria-label={`Bỏ ${f.name}`}
                      onClick={() => onChange({ files: set.files.filter((_, k) => k !== i) })}>
                <Icon name="x" size={14} />
              </button>
            </li>
          ))}
        </ol>
      ) : null}
      <div className="lab-set__foot faint">{set.files.length ? `${set.files.length} tệp · ${formatBytes(size)}` : "Chưa có tệp"}</div>
      <details className="lab-applicant">
        <summary>Mốc tài khoản người nộp {applicantSet ? <span className="tag">đã nhập</span> : <span className="faint">(tuỳ chọn)</span>}</summary>
        <p className="faint">Cổng đổ sẵn từ VNeID, extension gửi kèm để BE biết người nộp là ai (tính quan hệ, khối người yêu cầu). Bỏ trống = như tài khoản cổng không có dữ liệu.</p>
        <div className="lab-applicant__grid">
          <label className="field"><span>Họ tên</span>
            <input className="input" disabled={disabled} value={set.applicant.name} onChange={(e) => onChange({ applicant: { ...set.applicant, name: e.target.value } })} />
          </label>
          <label className="field"><span>Số định danh</span>
            <input className="input mono" inputMode="numeric" disabled={disabled} value={set.applicant.id} onChange={(e) => onChange({ applicant: { ...set.applicant, id: e.target.value } })} />
          </label>
          <label className="field"><span>Ngày sinh</span>
            <input className="input" placeholder="dd/mm/yyyy" disabled={disabled} value={set.applicant.birthday} onChange={(e) => onChange({ applicant: { ...set.applicant, birthday: e.target.value } })} />
          </label>
        </div>
      </details>
    </div>
  );
}

export default function Setup({ state, onState, sets, onSet, procedure, hint, beLabel, running, ready, onStart, onStop, onImport, importError }: {
  state: SetupState;
  onState: (patch: Partial<SetupState>) => void;
  sets: DocSet[];
  onSet: (index: number, patch: Partial<DocSet>) => void;
  procedure: LabProcedure;
  hint?: string;
  beLabel: (key: string) => string | undefined;
  running: boolean;
  ready: boolean;
  onStart: () => void;
  onStop: () => void;
  onImport: (file: File) => void;
  importError: string;
}) {
  const attach = procedure.attach && state.attach;
  const calls = state.setCount * state.runCount * (attach ? 2 : 1);
  const group = GROUPS.find((g) => g.key === procedure.group);

  return (
    <section className="panel lab-setup" aria-label="Thiết lập đợt kiểm thử">
      <div className="lab-setup__grid">
        <label className="field lab-proc">
          <span className="lab-label">Thủ tục</span>
          <select className="select" value={state.procedure} disabled={running} onChange={(e) => onState({ procedure: e.target.value, variant: "" })}>
            {GROUPS.map((g) => (
              <optgroup key={g.key} label={`${g.label} — ${g.hint}`}>
                {LAB_PROCEDURES.filter((p) => p.group === g.key).map((p) => (
                  <option key={p.key} value={p.key}>{beLabel(p.key) || p.label}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
        <Counter label="Số bộ tài liệu" value={state.setCount} max={MAX_SETS} disabled={running} onChange={(n) => onState({ setCount: n })} />
        <Counter label="Số lần chạy mỗi bộ" value={state.runCount} max={MAX_RUNS} disabled={running} onChange={(n) => onState({ runCount: n })} />
      </div>

      <div className="lab-opts">
        <span className="tag">{group?.label}</span>
        <span className="mono faint">{procedure.key}</span>
        {procedure.attach ? (
          <>
            <label className="lab-check">
              <input type="checkbox" checked={state.attach} disabled={running} onChange={(e) => onState({ attach: e.target.checked })} />
              Chạy cả đính kèm
            </label>
            <label className={`lab-check${state.attach ? "" : " is-off"}`}>
              <input type="checkbox" checked={state.split} disabled={running || !state.attach} onChange={(e) => onState({ split: e.target.checked })} />
              Tách giấy tờ <small className="faint">(cài đặt “Tách giấy tờ” của extension)</small>
            </label>
          </>
        ) : <span className="faint">Chỉ chạy điền</span>}
        {procedure.variants ? (
          <div className="lab-variant">
            <span className="lab-label">Tờ khai đang mở</span>
            <div className="seg" role="radiogroup" aria-label="Tờ khai đang mở">
              {procedure.variants.map((v, i) => {
                const on = state.variant ? state.variant === v.value : i === 0;
                return (
                  <button key={v.value} type="button" role="radio" aria-checked={on} aria-pressed={on} disabled={running} onClick={() => onState({ variant: v.value })}>{v.label}</button>
                );
              })}
            </div>
          </div>
        ) : null}
      </div>

      {hint ? (
        <details className="lab-hint">
          <summary>Giấy tờ cần tải lên cho thủ tục này</summary>
          <p>{hint}</p>
        </details>
      ) : null}

      <div className="lab-sets">
        {sets.slice(0, state.setCount).map((set, i) => (
          <SetCard key={i} index={i} set={set} disabled={running} onChange={(patch) => onSet(i, patch)} />
        ))}
      </div>

      <div className="lab-actions">
        {running ? (
          <button className="btn" type="button" onClick={onStop}><Icon name="x" size={14} /> Dừng</button>
        ) : (
          <button className="btn btn--primary" type="button" disabled={!ready} onClick={onStart}>
            Chạy {state.setCount * state.runCount} lượt
          </button>
        )}
        <span className="muted">
          {state.setCount} bộ × {state.runCount} lần{attach ? " × (điền + đính kèm)" : ""} = <b className="num">{calls}</b> lần gọi máy chủ
          {!ready && !running ? <span className="ef-red"> · bộ nào cũng cần ít nhất một tệp</span> : null}
        </span>
        <label className="btn btn--ghost lab-import">
          <Icon name="folder" size={14} /> Mở kết quả đã xuất
          <input type="file" accept="application/json,.json" className="sr-only" disabled={running}
                 onChange={(e) => { const f = e.target.files?.[0]; if (f) onImport(f); e.target.value = ""; }} />
        </label>
        {importError ? <span className="ef-red">{importError}</span> : null}
      </div>
    </section>
  );
}
