import { useCallback, useEffect, useRef, useState, type ClipboardEvent, type DragEvent, type FormEvent } from "react";
import Icon from "../../components/Icon";
import { Spinner } from "../../components/Status";
import { devApi, errorText, type DevProcedure, type InputGroup, type LinkCheck } from "./api";

const GROUPS: { key: InputGroup; title: string; hint: string; exts: string[] }[] = [
  { key: "mapping", title: "Excel mapping điền", hint: "File .xlsx mô tả từng ô trên cổng lấy dữ liệu từ đâu", exts: [".xlsx", ".xlsm", ".csv"] },
  { key: "attach", title: "Ảnh ánh xạ đính kèm", hint: "Ảnh chụp phần thành phần hồ sơ trên cổng, ghi giấy tờ nào vào dòng nào", exts: [".png", ".jpg", ".jpeg", ".webp", ".gif"] },
  { key: "samples", title: "File mẫu", hint: "Giấy tờ mẫu để chạy thử: PDF, ảnh hoặc Word", exts: [".pdf", ".png", ".jpg", ".jpeg", ".webp", ".docx"] },
];
const ACCEPT = Array.from(new Set(GROUPS.flatMap((g) => g.exts))).join(",");
const MAX_FILE_MB = 40;

interface Picked {
  id: number;
  group: InputGroup;
  file: File;
}

const extOf = (name: string) => (/\.[^.]+$/.exec(name.toLowerCase())?.[0] ?? "");

/** Thả chung một chỗ thì tự xếp nhóm: Excel là mapping, PDF/Word là file mẫu, ảnh là ánh xạ đính kèm (ảnh mẫu thì chuyển tay). */
function guessGroup(name: string): InputGroup | null {
  const ext = extOf(name);
  if ([".xlsx", ".xlsm", ".csv"].includes(ext)) return "mapping";
  if ([".pdf", ".docx"].includes(ext)) return "samples";
  if ([".png", ".jpg", ".jpeg", ".webp", ".gif"].includes(ext)) return "attach";
  return null;
}

/** Key gợi ý từ tên thủ tục: bỏ dấu, chữ thường, nối bằng gạch ngang, cắt ở ranh giới từ. Người dùng sửa lại cho gọn. */
export function suggestKey(label: string): string {
  const plain = label.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();
  const words = plain.replace(/[^a-z0-9]+/g, " ").trim().split(/\s+/).filter(Boolean);
  let key = "";
  for (const word of words) {
    const next = key ? `${key}-${word}` : word;
    if (next.length > 60) break;
    key = next;
  }
  return key;
}

function sizeText(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

const EMPTY: DevProcedure = {
  key: "", code: "", label: "", url: "", newLink: true,
  needsAgencySelect: true, provinceOnlyAgency: false, selectSo: false, autoConfirm: true, linkNotes: "",
};

export default function NewProcedure({ onCreated }: { onCreated: (id: string) => void }) {
  const [proc, setProc] = useState<DevProcedure>(EMPTY);
  const [keyTouched, setKeyTouched] = useState(false);
  const [check, setCheck] = useState<LinkCheck | null>(null);
  const [checking, setChecking] = useState(false);
  const [files, setFiles] = useState<Picked[]>([]);
  const [rejected, setRejected] = useState<string[]>([]);
  const [hover, setHover] = useState(false);
  const [notes, setNotes] = useState("");
  const [troLy, setTroLy] = useState(true);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const nextId = useRef(1);
  const picker = useRef<HTMLInputElement>(null);

  const set = <K extends keyof DevProcedure>(name: K, value: DevProcedure[K]) => setProc((p) => ({ ...p, [name]: value }));

  // Key bám theo tên cho tới khi người dùng tự sửa key.
  useEffect(() => {
    if (!keyTouched && proc.newLink) setProc((p) => ({ ...p, key: suggestKey(p.label) }));
  }, [proc.label, proc.newLink, keyTouched]);

  useEffect(() => {
    const key = proc.key.trim();
    const code = proc.code.trim();
    if (!key && !code) {
      setCheck(null);
      return;
    }
    let alive = true;
    setChecking(true);
    const timer = window.setTimeout(() => {
      devApi.check(key, code)
        .then((found) => { if (alive) setCheck(found); })
        .catch(() => { if (alive) setCheck(null); })
        .finally(() => { if (alive) setChecking(false); });
    }, 400);
    return () => { alive = false; window.clearTimeout(timer); };
  }, [proc.key, proc.code]);

  // "Dùng link có sẵn": gõ đúng key là hiện luôn tên, mã, URL của link đó để biết đang làm thủ tục nào.
  useEffect(() => {
    const entry = check?.entry;
    if (proc.newLink || !entry || entry.key !== proc.key) return;
    setProc((p) => ({
      ...p, label: entry.label, code: String(entry.code ?? ""), url: entry.url, needsAgencySelect: !!entry.needsAgencySelect,
      autoConfirm: !!entry.autoConfirm, selectSo: !!entry.selectSo, provinceOnlyAgency: !!entry.provinceOnlyAgency,
    }));
  }, [check, proc.newLink, proc.key]);

  const add = useCallback((list: File[], group?: InputGroup) => {
    const bad: string[] = [];
    const ok: Picked[] = [];
    for (const file of list) {
      const target = group ?? guessGroup(file.name);
      const allowed = target && GROUPS.find((g) => g.key === target)!.exts.includes(extOf(file.name));
      if (!target || !allowed) bad.push(`${file.name}: không nhận loại tệp này${extOf(file.name) === ".xls" ? " (lưu lại dạng .xlsx)" : ""}`);
      else if (file.size > MAX_FILE_MB * 1024 * 1024) bad.push(`${file.name}: quá ${MAX_FILE_MB} MB`);
      else if (!file.size) bad.push(`${file.name}: tệp rỗng`);
      else ok.push({ id: nextId.current++, group: target, file });
    }
    setRejected(bad);
    if (ok.length) setFiles((current) => [...current, ...ok]);
  }, []);

  function onDrop(event: DragEvent<HTMLElement>, group?: InputGroup) {
    event.preventDefault();
    event.stopPropagation();
    setHover(false);
    add(Array.from(event.dataTransfer.files), group);
  }

  // Dán ảnh chụp màn hình (Snipping Tool, Ctrl+V) thẳng vào form: ảnh từ clipboard không có tên nên tự đặt.
  function onPaste(event: ClipboardEvent<HTMLElement>) {
    const images = Array.from(event.clipboardData.items)
      .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
      .map((item) => item.getAsFile())
      .filter((file): file is File => !!file);
    if (!images.length) return;
    event.preventDefault();
    const stamp = new Date().toTimeString().slice(0, 8).replace(/:/g, "");
    add(images.map((file, i) => new File([file], `anh-dan-${stamp}${images.length > 1 ? `-${i + 1}` : ""}.png`, { type: file.type })), "attach");
  }

  function useExisting() {
    if (!check?.entry) return;
    const entry = check.entry;
    setProc((p) => ({
      ...p, newLink: false, key: entry.key, label: entry.label, code: String(entry.code ?? ""), url: entry.url,
      needsAgencySelect: !!entry.needsAgencySelect, autoConfirm: !!entry.autoConfirm, selectSo: !!entry.selectSo,
      provinceOnlyAgency: !!entry.provinceOnlyAgency,
    }));
    setKeyTouched(true);
  }

  const counts = Object.fromEntries(GROUPS.map((g) => [g.key, files.filter((f) => f.group === g.key).length])) as Record<InputGroup, number>;
  const keyProblem = !proc.key ? "" : check && !check.keyValid ? "Key chỉ gồm chữ thường không dấu, số và dấu gạch ngang."
    : proc.newLink && check?.keyExists ? "Key này đã có trong ke_khai_links.json." : !proc.newLink && check && !check.keyExists ? "Không có key này để dùng lại." : "";
  const linkReady = proc.newLink
    ? proc.label.trim().length >= 5 && /^https:\/\/[^/\s]+\.gov\.vn/.test(proc.url.trim()) && (!proc.code || /^\d{1,2}\.\d{6}$/.test(proc.code.trim()))
    : !!check?.keyExists;
  const ready = !!proc.key && !keyProblem && linkReady && files.length > 0 && !!username.trim() && !!password && !sending && !checking;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ready) return;
    setSending(true);
    setError("");
    try {
      const job = await devApi.create(
        { procedure: { ...proc, key: proc.key.trim() }, notes: notes.trim(), troLy, replayUsername: username.trim(), replayPassword: password },
        files.map(({ group, file }) => ({ group, file })),
      );
      setPassword("");
      onCreated(job.id);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setSending(false);
    }
  }

  return (
    <form className="panel at-start dv-form" onSubmit={submit} onPaste={onPaste}>
      <div className="at-start__head">
        <h1>Thêm thủ tục mới</h1>
        <p className="muted">
          Nhập link kê khai rồi thả Excel mapping, ảnh ánh xạ đính kèm và file mẫu. Agent làm pipeline điền và đính kèm theo CLAUDE.md, hệ thống
          tự chạy test, build và chạy thử trên file mẫu. Kết quả nằm trong thư mục làm việc, chưa commit.
        </p>
      </div>

      <fieldset className="dv-section">
        <legend>1. Link kê khai <span className="faint">(app/procedures/data/ke_khai_links.json)</span></legend>
        <div className="dv-switch" role="radiogroup" aria-label="Link kê khai">
          <label className={proc.newLink ? "is-on" : undefined}>
            <input type="radio" name="newLink" checked={proc.newLink} onChange={() => { set("newLink", true); setKeyTouched(false); }} /> Thêm link mới
          </label>
          <label className={!proc.newLink ? "is-on" : undefined}>
            <input type="radio" name="newLink" checked={!proc.newLink} onChange={() => { set("newLink", false); setKeyTouched(true); }} /> Dùng link có sẵn
          </label>
        </div>
        <div className="dv-grid">
          <label className="field dv-wide">
            <span>Tên thủ tục</span>
            <input className="input" value={proc.label} disabled={!proc.newLink} onChange={(e) => set("label", e.target.value)}
                   placeholder="Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất" />
          </label>
          <label className="field">
            <span>Mã thủ tục</span>
            <input className="input mono" value={proc.code} disabled={!proc.newLink} onChange={(e) => set("code", e.target.value.trim())} placeholder="1.013831" inputMode="decimal" />
          </label>
          <label className="field">
            <span>Key {proc.newLink ? "(gợi ý từ tên, sửa cho gọn)" : ""}</span>
            <input className="input mono" value={proc.key} spellCheck={false} autoComplete="off"
                   onChange={(e) => { set("key", e.target.value.trim().toLowerCase()); setKeyTouched(true); }} placeholder="dang-ky-bien-dong-khanh-hoa" />
          </label>
          <label className="field dv-wide">
            <span>URL trang thủ tục trên Cổng DVC</span>
            <input className="input mono" value={proc.url} disabled={!proc.newLink} onChange={(e) => set("url", e.target.value.trim())}
                   placeholder="https://dichvucong.gov.vn/thu-tuc-hanh-chinh/…" />
          </label>
        </div>
        <div className="dv-check" aria-live="polite">
          {checking ? <Spinner label="Đang kiểm key" /> : null}
          {keyProblem ? <span className="form-error">{keyProblem}</span> : null}
          {check?.keyExists && proc.newLink ? (
            <button type="button" className="btn btn--sm" onClick={useExisting}>Dùng link có sẵn: {check.entry?.label}</button>
          ) : null}
          {proc.key && check?.keyValid ? <span className="faint">Thư mục pipeline: <span className="mono">app/pipelines/{check.folder}/</span>{check.pipelineExists ? " (đã có, agent sẽ sửa trên đó)" : ""}</span> : null}
          {check?.sameCode.length ? (
            <span className="at-warn"><Icon name="alert" size={14} /> Mã này đã có ở: {check.sameCode.map((s) => `${s.key} (${s.label})`).join(", ")}</span>
          ) : null}
        </div>
        <div className="dv-flags">
          <label className="lab-check"><input type="checkbox" checked={proc.needsAgencySelect} disabled={!proc.newLink} onChange={(e) => set("needsAgencySelect", e.target.checked)} /> Chọn cơ quan thực hiện trên DVCQG</label>
          <label className="lab-check"><input type="checkbox" checked={proc.selectSo} disabled={!proc.newLink} onChange={(e) => set("selectSo", e.target.checked)} /> Tích Sở (nộp cấp Sở)</label>
          <label className="lab-check"><input type="checkbox" checked={proc.provinceOnlyAgency} disabled={!proc.newLink} onChange={(e) => set("provinceOnlyAgency", e.target.checked)} /> Chỉ chọn Tỉnh, không chọn xã</label>
          <label className="lab-check"><input type="checkbox" checked={proc.autoConfirm} disabled={!proc.newLink} onChange={(e) => set("autoConfirm", e.target.checked)} /> Tự bấm Xác nhận</label>
        </div>
        <label className="field">
          <span>Điều kiện đặc biệt của link (nếu có)</span>
          <textarea className="input at-textarea" rows={2} value={proc.linkNotes} onChange={(e) => set("linkNotes", e.target.value)}
                    placeholder="Ví dụ: chỉ tích Sở với tài khoản Khánh Hòa; Đà Nẵng tích Sở xong chọn Chi cục An toàn thực phẩm" />
        </label>
      </fieldset>

      <fieldset className="dv-section">
        <legend>2. Tài liệu</legend>
        <div
          className={`dv-drop${hover ? " is-hover" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setHover(true); }}
          onDragLeave={() => setHover(false)}
          onDrop={(e) => onDrop(e)}
          onClick={() => picker.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); picker.current?.click(); } }}
        >
          <Icon name="folder" size={22} />
          <strong>Kéo thả tất cả tệp vào đây, hoặc bấm để chọn</strong>
          <span className="faint">Excel tự vào mapping, PDF và Word vào file mẫu, ảnh vào ánh xạ đính kèm. Dán ảnh chụp màn hình bằng Ctrl+V.</span>
          <input ref={picker} type="file" multiple accept={ACCEPT} hidden onChange={(e) => { add(Array.from(e.target.files ?? [])); e.target.value = ""; }} />
        </div>
        {rejected.length ? <ul className="form-error dv-rejected">{rejected.map((r) => <li key={r}>{r}</li>)}</ul> : null}
        <div className="dv-groups">
          {GROUPS.map((group) => (
            <section
              key={group.key}
              className="dv-group"
              onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
              onDrop={(e) => onDrop(e, group.key)}
              aria-label={group.title}
            >
              <header>
                <b>{group.title}</b> <span className="at-tag at-tag--plain">{counts[group.key]}</span>
                <p className="faint">{group.hint}</p>
              </header>
              {files.filter((f) => f.group === group.key).map((item) => (
                <div key={item.id} className="dv-file">
                  <Icon name="file" size={14} />
                  <span className="dv-file__name" title={item.file.name}>{item.file.name}</span>
                  <span className="faint num">{sizeText(item.file.size)}</span>
                  <select
                    className="input dv-file__move"
                    aria-label={`Chuyển nhóm cho ${item.file.name}`}
                    value={item.group}
                    onChange={(e) => {
                      const target = e.target.value as InputGroup;
                      if (!GROUPS.find((g) => g.key === target)!.exts.includes(extOf(item.file.name))) {
                        setRejected([`${item.file.name}: nhóm ${GROUPS.find((g) => g.key === target)!.title} không nhận loại tệp này`]);
                        return;
                      }
                      setFiles((all) => all.map((f) => (f.id === item.id ? { ...f, group: target } : f)));
                    }}
                  >
                    {GROUPS.map((g) => <option key={g.key} value={g.key}>{g.title}</option>)}
                  </select>
                  <button type="button" className="btn btn--icon btn--ghost" aria-label={`Bỏ ${item.file.name}`}
                          onClick={() => setFiles((all) => all.filter((f) => f.id !== item.id))}>
                    <Icon name="x" size={14} />
                  </button>
                </div>
              ))}
              {!counts[group.key] ? <p className="faint dv-empty">Thả tệp vào đây nếu muốn xếp thẳng vào nhóm này</p> : null}
            </section>
          ))}
        </div>
        <label className="field">
          <span>Yêu cầu thêm, điều kiện ngoài</span>
          <textarea className="input at-textarea" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)}
                    placeholder="Ví dụ: chủ hồ sơ là bên nhận chuyển nhượng; ở trợ lý có phần lựa chọn trường hợp giống các thủ tục Bắc Ninh" />
        </label>
        <label className="lab-check">
          <input type="checkbox" checked={troLy} onChange={(e) => setTroLy(e.target.checked)} />
          Đưa luôn lên trợ lý nhân dân (procedure_registry, chọn thủ tục, tiếng Mông, test handfree) theo CLAUDE.md
        </label>
      </fieldset>

      <fieldset className="dv-section">
        <legend>3. Tài khoản chạy thử</legend>
        <div className="at-start__grid at-start__grid--account">
          <label className="field">
            <span>Tài khoản backend</span>
            <input className="input" autoComplete="off" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="tài khoản đúng tỉnh của thủ tục" />
          </label>
          <label className="field">
            <span>Mật khẩu</span>
            <span className="field__pw">
              <input className="input" type={showPassword ? "text" : "password"} autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
              <button className="btn btn--icon btn--ghost" type="button" onClick={() => setShowPassword((v) => !v)} aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}>
                <Icon name={showPassword ? "eye-off" : "eye"} size={16} />
              </button>
            </span>
          </label>
        </div>
        <p className="faint at-note">Dùng để chạy thử pipeline mới trên file mẫu qua backend local; các ô theo xã/tỉnh ra theo đơn vị của tài khoản này. Mật khẩu chỉ giữ trong bộ nhớ của dịch vụ khi job chạy.</p>
      </fieldset>

      {error ? <div className="form-error" role="alert">{error}</div> : null}
      <div className="at-start__actions">
        <span className="faint">{files.length ? `${files.length} tệp · ${counts.mapping} mapping, ${counts.attach} ảnh ánh xạ, ${counts.samples} file mẫu` : "Chưa có tệp nào"}</span>
        <button className="btn btn--primary" type="submit" disabled={!ready}>
          {sending ? <Spinner label="Đang gửi" /> : "Bắt đầu làm thủ tục"}
        </button>
      </div>
    </form>
  );
}
