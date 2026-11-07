// Mô phỏng điền e-form hộ tịch (tokhaidientu.moj.gov.vn) bằng MẪU THẬT của cổng: bố cục HTML, loại ô,
// danh sách option (dân tộc, quốc tịch, tỉnh, xã theo tỉnh…) chụp bằng scripts/snapshot-eform.mjs.
//
// Quy tắc đặt output BE (T5) vào ô chép từ engine legacy của extension
// (auto-fill-hcc-extension/content/fill-legacy.js):
// - tìm ô theo thẻ = `comp` và `name` (đúng tên → không phân biệt hoa thường), rồi aliases;
//   `raw` = input trần theo name (kể cả ô con nằm trong x-select-area);
// - đường vòng: khối ly hôn tìm qua ô con Ben(Nam|Nu)_SoBanAn; ô ghi tay "Khác" tìm theo `otherOf`;
// - dropdown (pickInWidget): khớp chính xác (bỏ dấu) trước, rồi khớp lỏng theo RANH GIỚI TỪ và chỉ
//   nhận khi đúng MỘT option khớp — không khớp thì ô đỏ;
// - khối địa chỉ: xã chọn trong danh sách xã của tỉnh VỪA chọn được;
// - ô gương (số giấy tờ = số định danh) chép sau cùng; ô trống còn lại cổng tô đỏ, default → vàng.
// Chỗ lệch có chủ ý: extension gõ ô tìm kiếm của dropdown rồi mới khớp lỏng trên danh sách đã lọc;
// ở đây khớp lỏng trên danh sách đầy đủ (bộ lọc của cổng không chụp được) — kết quả chỉ khác khi
// danh sách đầy đủ có nhiều option cùng khớp lỏng.
import { isEmpty, type UiField } from "./fill";

export type Opt = [value: string, label: string];

export interface EfPart {
  name?: string;
  label?: string;
  required?: boolean;
  br?: boolean;
}

export interface EfField {
  type: string;
  required?: boolean;
  disabled?: boolean;
  options?: Opt[];
  list?: string | null;
  dependsOn?: string;
  byParent?: Record<string, string>;
  parts?: EfPart[];
  show?: { values: string[]; areas: string[] }[];
  note?: string;
}

export interface Eform {
  id: number;
  name: string;
  path: string;
  fetchedAt: string;
  html: string;
  fields: Record<string, EfField>;
  lists: Record<string, Opt[]>;
}

// ---- khớp chữ, chép từ fill-legacy.js ----------------------------------------------------------

export const norm = (s: unknown) => String(s ?? "").normalize("NFC").trim().toLowerCase().replace(/\s+/g, " ");

export function foldChoice(value: unknown): string {
  return String(value ?? "")
    .replace(/Đ/g, "D").replace(/đ/g, "d")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/\s*[-–—‐‑]+\s*/g, " ")
    .replace(/['’‘`´ʼ]/g, "")
    .replace(/\s*(?:…|\.{2,})\s*/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function hasWord(haystack: string, needle: string): boolean {
  if (!haystack || !needle) return false;
  const escaped = needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(^|[^\\p{L}\\p{N}])${escaped}([^\\p{L}\\p{N}]|$)`, "u").test(haystack);
}

const isPlaceholder = (label: string) => {
  const t = norm(label);
  return !t || t.includes("không tìm thấy") || t === "-- chọn --" || t === "-- chon --";
};

export interface OptPick {
  opt: Opt | null;
  how?: "exact" | "loose";
  /** Số option cùng khớp lỏng khi không chốt được (extension bỏ trống). */
  ambiguous?: Opt[];
}

export function pickOption(options: Opt[], value: unknown): OptPick {
  const want = norm(value);
  const folded = foldChoice(value);
  const real = options.filter(([, label]) => !isPlaceholder(label));
  const exact = real.find(([, l]) => norm(l) === want) ?? real.find(([, l]) => foldChoice(l) === folded);
  if (exact) return { opt: exact, how: "exact" };
  let ambiguous: Opt[] | undefined;
  const single = (pred: (o: Opt) => boolean) => {
    const hits = real.filter(pred);
    if (hits.length === 1) return hits[0];
    if (hits.length > 1 && !ambiguous) ambiguous = hits;
    return null;
  };
  const loose = single(([, l]) => hasWord(norm(l), want))
    ?? single(([, l]) => hasWord(foldChoice(l), folded) || hasWord(folded, foldChoice(l)));
  return loose ? { opt: loose, how: "loose" } : { opt: null, ambiguous };
}

// Tên thay thế + ô gương extension áp cho MỌI thủ tục (content.js FIELD_NAME_ALIASES, LEGACY_MIRROR_FIELDS).
export const GLOBAL_ALIASES: Record<string, string[]> = {
  LoaiDangKy: ["loaiDangKy"], loaiDangKy: ["LoaiDangKy"],
  SoGiayToDinhDanhC1: ["SoGiayToTuyThanC1", "SoDinhDanhC1"], SoGiayToTuyThanC1: ["SoGiayToDinhDanhC1", "SoDinhDanhC1"],
};
const MIRRORS: [string, string][] = [
  ["SoDinhDanhC", "SoGiayToDinhDanhC"], ["SoDinhDanhC", "SoGiayToTuyThanC"], ["SoDinhDanhC", "NYC_SoGiayToTuyThan"],
  ["NYC_SoDinhDanh", "NYC_SoGiayToTuyThan"], ["NYC_SoDinhDanh", "SoGiayToDinhDanhC"],
  ["SoDinhDanhC1", "SoGiayToDinhDanhC1"], ["SoDinhDanhC1", "SoGiayToTuyThanC1"],
  ["SoDinhDanhCha", "SoGiayToDinhDanhCha"], ["SoDinhDanhMe", "SoGiayToDinhDanhMe"],
  ["SoDinhDanh_BenNam", "SoGiayToDinhDanh_BenNam"], ["SoDinhDanh_BenNu", "SoGiayToDinhDanh_BenNu"],
  ["SoDinhDanh", "SoGiayToDinhDanh"],
];

const candidates = (f: UiField) =>
  [f.name, ...(f.aliases ?? []), ...(GLOBAL_ALIASES[f.name] ?? [])].filter((n, i, a) => n && a.indexOf(n) === i);

// ---- kết quả ------------------------------------------------------------------------------------

// prefilled = cổng tự điền (theo tài khoản / mặc định của cổng); unchecked = có giá trị nhưng chưa có danh sách
// option để kiểm; auto = extension tự quyết lúc chạy (theo người đăng nhập…), mô phỏng không biết trước;
// blank = trống nhưng cổng không tô đỏ (form Angular chỉ tô đỏ ô bắt buộc).
export type CellStatus = "filled" | "default" | "miss" | "empty" | "hidden-value" | "prefilled" | "unchecked" | "auto" | "blank";

export interface Cell {
  /** Khoá ô: name với ô ngoài cùng, "<khối>/<ô con>" với ô con của x-select-area. */
  key: string;
  name: string;
  type: string;
  label?: string;
  required: boolean;
  status: CellStatus;
  /** Chữ nằm trong ô sau khi điền (option đã chọn / giá trị gõ vào). */
  text?: string;
  /** Giá trị BE muốn điền (khi khác `text`, vd không khớp option). */
  want?: unknown;
  options?: Opt[];
  picked?: Opt | null;
  how?: "exact" | "loose" | "mirror";
  field?: UiField;
  via?: string;
  reasons: string[];
  /** Ô chỉ đọc (khoá) trên cổng. */
  readonly?: boolean;
}

export interface Unmatched {
  field: UiField;
  reason: string;
}

export interface SimStats {
  cells: number; filled: number; defaults: number; red: number; miss: number; empty: number; requiredEmpty: number;
}

export interface EformResult {
  cells: Map<string, Cell>;
  /** Khối x-select-area đang hiện trên cổng (không bị điều kiện ẩn, hoặc điều kiện đã thoả). */
  visibleAreas: Set<string>;
  /** Khối bị ẩn → điều kiện hiện của nó (để ghi chú). */
  hiddenBy: Map<string, string>;
  unmatched: Unmatched[];
  tops: string[];
  stats: SimStats;
}

type Target = { kind: "top"; name: string; via?: string };

const DIVORCE_KEYS = ["soBanAnQuyetDinhLyHon", "ngayCapBanAnQuyetDinhLyHon", "coQuanCapBanAnQuyetDinhLyHon"];

function isDivorceLike(v: unknown): v is Record<string, unknown> {
  return !!v && typeof v === "object" &&
    [...DIVORCE_KEYS, "voChongHoTen", "thoiDiemBatDau", "thoiDiemKetThuc"].some((k) => (v as Record<string, unknown>)[k]);
}

export function normalizeAreaValue(v: unknown): Record<string, unknown> {
  if (!v || typeof v !== "object") return {};
  const o = v as Record<string, unknown>;
  if (!Array.isArray(o.selects)) return o;
  const out: Record<string, unknown> = { diaChi: o.diaChi };
  for (const s of o.selects) {
    const n = norm(s);
    if (!n) continue;
    if (n === "việt nam" || n.includes("quốc gia") || n.includes("country")) out.quocGia = s;
    else if (n.includes("tỉnh") || n.includes("thành phố") || /\btp\b/.test(n)) out.tinh = s;
    else if (n.includes("xã") || n.includes("phường") || n.includes("thị trấn")) out.xa = s;
  }
  return out;
}

const DATE_RE = /^\d{1,2}\/\d{1,2}\/\d{4}$/;
const text = (v: unknown) => (v === null || v === undefined ? "" : typeof v === "object" ? JSON.stringify(v) : String(v).trim());

export function topFieldNames(html: string): string[] {
  const doc = new DOMParser().parseFromString(html, "text/html");
  return Array.from(doc.querySelectorAll("span.mention[name]")).map((el) => el.getAttribute("name")!).filter(Boolean);
}

export function simulateEform(form: Eform, fields: UiField[]): EformResult {
  const F = form.fields;
  const tops = topFieldNames(form.html).filter((n, i, a) => a.indexOf(n) === i && F[n]);
  const listOf = (f: EfField | undefined): Opt[] => (f?.list ? form.lists[f.list] ?? [] : f?.options ?? []);

  // ---- 1. BE field → ô trên mẫu ----
  const areasOfPart = new Map<string, string[]>();
  for (const name of tops) {
    for (const p of F[name].parts ?? []) {
      if (!p.name) continue;
      areasOfPart.set(p.name, [...(areasOfPart.get(p.name) ?? []), name]);
    }
  }
  const findTop = (names: string[], comp?: string) => {
    for (const n of names) if (F[n] && tops.includes(n) && (!comp || F[n].type === comp)) return n;
    const lower = new Set(names.map((n) => n.toLowerCase()));
    return tops.find((t) => lower.has(t.toLowerCase()) && (!comp || F[t].type === comp));
  };

  const assigned = new Map<string, UiField>(); // key ô → field BE
  const vias = new Map<string, string>();
  const unmatched: Unmatched[] = [];
  const put = (key: string, f: UiField, via?: string) => {
    assigned.set(key, f);
    if (via) vias.set(key, via);
  };

  for (const f of fields) {
    const names = candidates(f);
    let target: Target | null = null;
    if (f.comp === "raw") {
      const top = findTop(names);
      if (top && ["x-input", "x-input-number"].includes(F[top].type)) target = { kind: "top", name: top };
      else {
        const part = names.find((n) => areasOfPart.has(n)) ?? [...areasOfPart.keys()].find((p) => names.some((n) => n.toLowerCase() === p.toLowerCase()));
        if (part) {
          for (const area of areasOfPart.get(part)!) put(`${area}/${part}`, f);
          continue;
        }
      }
    } else {
      const top = findTop(names, f.comp);
      if (top) target = { kind: "top", name: top, via: top !== f.name ? `khớp qua tên ${top}` : undefined };
    }
    if (!target && f.comp === "x-select-area" && isDivorceLike(f.value)) {
      const side = /Ben(Nam|Nu)$/.exec(f.name)?.[1];
      const area = side && areasOfPart.get(`Ben${side}_SoBanAn`)?.[0];
      if (area) target = { kind: "top", name: area, via: `tên khối trên cổng là ${area} — extension tìm qua ô con Ben${side}_SoBanAn` };
    }
    if (!target && f.otherOf) {
      const driver = f.otherOf.toLowerCase().replace(/[_-]/g, "");
      const other = tops.find((t) => {
        const n = t.toLowerCase().replace(/[_-]/g, "");
        return n.includes("khac") && n.replace("khac", "") === driver;
      });
      if (other) target = { kind: "top", name: other, via: `tìm theo ô gốc ${f.otherOf} (otherOf)` };
    }
    if (target?.kind === "top") { put(target.name, f, target.via); continue; }

    const sameName = findTop(names) ?? [...areasOfPart.keys()].find((p) => names.some((n) => n.toLowerCase() === p.toLowerCase()));
    unmatched.push({
      field: f,
      reason: sameName
        ? `BE gửi comp=${f.comp ?? "?"} nhưng ô "${sameName}" trên cổng là ${F[sameName]?.type ?? "ô con của khối"} → extension không tìm thấy`
        : "mẫu không có ô tên này → extension báo không thấy",
    });
  }

  // ---- 2. tính từng ô ----
  const cells = new Map<string, Cell>();
  const base = (key: string, name: string, f: EfField | undefined, label?: string, required?: boolean): Cell => ({
    key, name, type: f?.type ?? "x-input", label, required: !!(required ?? f?.required), status: "empty", reasons: [],
  });
  const finish = (cell: Cell, field: UiField | undefined) => {
    cell.field = field;
    if (field?.default && (cell.status === "filled")) cell.status = "default";
    return cell;
  };

  const evalScalar = (cell: Cell, f: EfField | undefined, value: unknown, parentPick?: Opt | null) => {
    if (isEmpty(value)) return;
    const type = f?.type ?? "x-input";
    if (type === "x-select") {
      let opts = listOf(f);
      if (f?.dependsOn) {
        const key = parentPick?.[0];
        opts = key && f.byParent?.[key] ? form.lists[f.byParent[key]] ?? [] : [];
        if (!parentPick) {
          cell.status = "miss";
          cell.want = value;
          cell.options = [];
          cell.reasons.push(`chưa chọn được ô cha nên danh sách trống`);
          return;
        }
      }
      cell.options = opts;
      const p = pickOption(opts, value);
      cell.picked = p.opt;
      if (p.opt) {
        cell.status = "filled";
        cell.text = p.opt[1];
        cell.how = p.how;
        if (p.how === "loose" || norm(p.opt[1]) !== norm(value)) cell.want = value;
      } else {
        cell.status = "miss";
        cell.want = value;
        cell.reasons.push(p.ambiguous
          ? `khớp lỏng ${p.ambiguous.length} option (${p.ambiguous.slice(0, 3).map((o) => o[1]).join(", ")}…) → extension bỏ trống`
          : `không có trong ${opts.length} option của danh sách`);
      }
      return;
    }
    if (type === "x-radio") {
      const opts = f?.options ?? [];
      cell.options = opts;
      const v = String(value);
      const hit = opts.find(([val]) => val.toLowerCase() === v.toLowerCase()) ?? opts.find(([, l]) => foldChoice(l) === foldChoice(v));
      cell.picked = hit ?? null;
      if (hit) { cell.status = "filled"; cell.text = hit[1]; }
      else { cell.status = "miss"; cell.want = value; cell.reasons.push(`không khớp lựa chọn nào (${opts.map((o) => `${o[0]}=${o[1]}`).join(", ")})`); }
      return;
    }
    if (type === "x-date") {
      if (DATE_RE.test(String(value).trim())) { cell.status = "filled"; cell.text = String(value).trim(); }
      else { cell.status = "miss"; cell.want = value; cell.reasons.push("không đúng dd/mm/yyyy — extension không tách được ngày/tháng/năm"); }
      return;
    }
    cell.status = "filled";
    cell.text = text(value);
  };

  const evalArea = (area: string, f: EfField, field: UiField | undefined) => {
    const parts = (f.parts ?? []).filter((p): p is EfPart & { name: string } => !!p.name);
    const partCells = new Map<string, Cell>();
    for (const p of parts) {
      const key = `${area}/${p.name}`;
      const pf = F[p.name];
      const cell = base(key, p.name, pf, p.label, p.required);
      if (pf?.type === "x-select" && !pf.dependsOn) cell.options = listOf(pf);
      partCells.set(p.name, cell);
      cells.set(key, cell);
    }
    const value = field?.value;
    const inputs = parts.filter((p) => (F[p.name]?.type ?? "x-input") === "x-input");
    const dates = parts.filter((p) => F[p.name]?.type === "x-date");

    if (field && !isEmpty(value)) {
      if (typeof value === "string" || typeof value === "number") {
        const first = inputs[0];
        if (first) evalScalar(partCells.get(first.name)!, F[first.name], value);
        else partCells.forEach((c) => c.reasons.push("khối không có ô chữ để ghi giá trị"));
      } else if (isDivorceLike(value)) {
        const v = value as Record<string, unknown>;
        const byName = (n: string) => parts.find((p) => p.name === n);
        const plan: [(EfPart & { name: string }) | undefined, unknown][] = [
          [byName("voChongHoTen"), v.voChongHoTen],
          [inputs.find((p) => /SoBanAn|soGiayTo/i.test(p.name)) ?? inputs[0], v.soBanAnQuyetDinhLyHon],
          [dates[0], v.ngayCapBanAnQuyetDinhLyHon ?? v.thoiDiemBatDau],
          [dates[1], v.thoiDiemKetThuc],
          [inputs.find((p) => /CoQuanCap|coQuanCapGiayTo/i.test(p.name)) ?? inputs[inputs.length - 1], v.coQuanCapBanAnQuyetDinhLyHon],
        ];
        for (const [p, val] of plan) if (p && !isEmpty(val)) evalScalar(partCells.get(p.name)!, F[p.name], val);
      } else {
        const data = normalizeAreaValue(value);
        const selects = parts.filter((p) => F[p.name]?.type === "x-select");
        const xa = selects.find((p) => F[p.name].dependsOn);
        const tinh = xa ? selects.find((p) => p.name === F[xa.name].dependsOn) : undefined;
        const quocGia = selects.find((p) => p !== xa && p !== tinh);
        if (quocGia && !isEmpty(data.quocGia)) evalScalar(partCells.get(quocGia.name)!, F[quocGia.name], data.quocGia);
        let tinhPick: Opt | null | undefined = null;
        if (tinh && !isEmpty(data.tinh)) {
          const c = partCells.get(tinh.name)!;
          evalScalar(c, F[tinh.name], data.tinh);
          tinhPick = c.picked;
        }
        if (xa && !isEmpty(data.xa)) {
          const c = partCells.get(xa.name)!;
          evalScalar(c, F[xa.name], data.xa, tinhPick);
          if (c.status === "miss" && tinhPick) c.reasons[c.reasons.length - 1] += ` xã của ${tinhPick[1]}`;
        }
        if (inputs[0] && !isEmpty(data.diaChi)) evalScalar(partCells.get(inputs[0].name)!, F[inputs[0].name], data.diaChi);
        const known = new Set(["quocGia", "tinh", "xa", "diaChi", "selects"]);
        const extra = Object.keys(data).filter((k) => !known.has(k) && !isEmpty(data[k]));
        if (extra.length) partCells.values().next().value?.reasons.push(`khoá lạ extension không dùng: ${extra.join(", ")}`);
      }
    }
    // Ô con BE gửi riêng theo name (comp raw, vd SoLuong trong khối "Thông tin bản sao").
    for (const [pname, cell] of partCells) {
      const direct = assigned.get(`${area}/${pname}`);
      if (direct && !isEmpty(direct.value)) evalScalar(cell, F[pname], direct.value);
      finish(cell, direct ?? field);
    }
  };

  for (const name of tops) {
    const f = F[name];
    const field = assigned.get(name);
    if (f.type === "x-select-area") {
      evalArea(name, f, field);
      continue;
    }
    const cell = base(name, name, f);
    if (f.type === "x-select" && !f.dependsOn) cell.options = listOf(f);
    if (f.type === "x-radio") cell.options = f.options ?? [];
    if (field) evalScalar(cell, f, field.value, f.dependsOn ? cells.get(f.dependsOn)?.picked : undefined);
    if (vias.has(name)) cell.via = vias.get(name);
    cells.set(name, finish(cell, field));
  }
  for (const [key, via] of vias) {
    for (const c of cells.values()) if (c.key.startsWith(`${key}/`)) c.via = via;
  }

  // ---- 3. ô gương ----
  for (const [src, dst] of MIRRORS) {
    const s = cells.get(src);
    const d = cells.get(dst);
    if (!s?.text || !d || !["x-input", "x-input-number"].includes(d.type)) continue;
    if (d.text !== s.text) {
      d.want = d.text ? d.text : undefined;
      d.text = s.text;
    }
    d.status = "filled";
    d.how = "mirror";
    d.reasons = [];
  }

  // ---- 4. khối ẩn/hiện theo ô điều khiển ----
  const controlled = new Map<string, string[]>();
  const active = new Set<string>();
  for (const name of tops) {
    const f = F[name];
    for (const rule of f.show ?? []) {
      const labels = rule.values.map((v) => (f.options ?? listOf(f)).find((o) => o[0] === v)?.[1] ?? v);
      for (const area of rule.areas) controlled.set(area, [...(controlled.get(area) ?? []), `${name} = ${labels.join(" / ")}`]);
      const picked = cells.get(name)?.picked?.[0];
      if (picked && rule.values.includes(picked)) rule.areas.forEach((a) => active.add(a));
    }
  }
  const visibleAreas = new Set<string>();
  const hiddenBy = new Map<string, string>();
  for (const name of tops) {
    if (F[name].type !== "x-select-area") continue;
    if (!controlled.has(name) || active.has(name)) visibleAreas.add(name);
    else hiddenBy.set(name, controlled.get(name)!.join(" hoặc "));
  }
  const visible = (c: Cell) => {
    const area = c.key.includes("/") ? c.key.split("/")[0] : F[c.name]?.type === "x-select-area" ? c.name : null;
    return !area || visibleAreas.has(area);
  };
  for (const c of cells.values()) {
    if (visible(c)) continue;
    const area = c.key.split("/")[0];
    if (c.status !== "empty") {
      c.status = "hidden-value";
      c.reasons.push(`khối chỉ hiện khi ${hiddenBy.get(area)} — trên cổng extension không thấy ô để điền`);
    }
  }

  const shown = [...cells.values()].filter(visible);
  const miss = shown.filter((c) => c.status === "miss").length;
  const empty = shown.filter((c) => c.status === "empty").length;
  return {
    cells, visibleAreas, hiddenBy, unmatched, tops,
    stats: {
      cells: shown.length,
      filled: shown.filter((c) => c.status === "filled" || c.status === "default").length,
      defaults: shown.filter((c) => c.status === "default").length,
      red: miss + empty,
      miss,
      empty,
      requiredEmpty: shown.filter((c) => c.status === "empty" && c.required).length,
    },
  };
}
