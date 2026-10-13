// Mô phỏng điền biểu mẫu SURVEYJS của Cổng DVC quốc gia mới (dichvucong.gov.vn/nop-ho-so) bằng mẫu dựng lại
// theo trang thật (mau-surveyjs/<tên>.json: bố cục hàng/cột, nhãn, ô khoá, điều kiện hiện, bảng thành phần hồ sơ).
//
// Quy tắc chép từ engine SurveyJS của extension (auto-fill-hcc-extension/content/surveyjs-main.js):
// - tìm câu hỏi theo tên BE gửi, hoặc tên có hậu tố "__<mã mẫu>"; ô khoá (cổng đổ từ tài khoản) → bỏ qua;
// - dropdown / radio: khớp MÃ option (field.code) trước, rồi điểm khớp nhãn (đúng chữ 100, bỏ tiền tố hành chính
//   95, chứa nhau ~80, trùng từ ≤70) — lấy option điểm cao nhất, dưới 50 thì không chọn;
// - xã theo tỉnh: danh mục xã chỉ có khi ô tỉnh đã chọn được;
// - ô ngày: giá trị = code (yyyy-mm-dd) hoặc đổi dd/mm/yyyy → ISO;
// - sjs-area: dò ô theo NHÃN trong cùng khối, nằm sau radio `field.radio` và trước radio kế tiếp:
//   "quốc gia" / "tỉnh thành phố" (dropdown) / "xã phường|phường xã" (dropdown) / "chi tiết|địa chỉ" (text);
// - "Kính gửi" / "Tại": extension tự điền theo tài khoản trợ lý (chỉ khi ô còn trống);
// - màu cuối như emptyRequired: ô hiện, không khoá, trống mà bắt buộc (isRequired hoặc nhãn có "*") → đỏ.
// Chỗ không mô phỏng được: cổng tra CSDL dân cư sau ba ô `lookup` rồi tự đổ + khoá các ô bên dưới (extension
// không ghi đè ô cổng vừa đổ) — chỉ ghi chú, vì kết quả tra phụ thuộc dữ liệu dân cư lúc chạy.
import { isEmpty, type UiField } from "./fill";
import type { AreaCatalog } from "./angular";
import type { Cell, Opt, SimStats, Unmatched } from "./eform";

export type SjsKind = "text" | "date" | "dropdown" | "radio";

export interface SjsField {
  /** Tên câu hỏi (phần trước "__"). Ô BE không gửi tới mà formJson chưa chụp được tên → tên tạm bắt đầu "~". */
  name: string;
  kind: SjsKind;
  label: string;
  required?: boolean;
  /** Cổng đổ từ tài khoản định danh và khoá. */
  readonly?: boolean;
  /** Cổng đổ sẵn giá trị nhưng vẫn sửa được. */
  prefilled?: boolean;
  /** Extension tự quyết lúc chạy (Kính gửi / Tại theo tài khoản trợ lý) — ghi chú hiển thị. */
  auto?: string;
  /** Số cột chiếm trong hàng (mặc định 1). */
  span?: number;
  /** Nhãn đứng bên trái ô thay vì nổi trên viền. */
  inlineLabel?: boolean;
  options?: Opt[];
  /** Danh mục dùng chung: tỉnh, hoặc xã theo ô tỉnh `parent`. */
  catalog?: "provinces" | "wards";
  parent?: string;
  /** Regex định dạng của cổng (validator) + lời nhắc khi sai. */
  pattern?: string;
  patternHint?: string;
  /** Chỉ hiện khi MỌI ô điều kiện mang một trong các mã đã liệt kê. */
  visibleIf?: Record<string, string[]>;
  /** Cổng tự chép giá trị vào ô khi điều kiện thoả (vd Quan hệ = "Bản thân" → chép khối người nộp). */
  copiedIf?: Record<string, string[]>;
}

export interface SjsRow {
  /** Số cột của hàng; mặc định = tổng span các ô. */
  cols?: number;
  fields?: SjsField[];
  /** Dòng chữ của cổng (không phải ô). */
  text?: string;
}

export interface SjsSection {
  title: string;
  /** "box": khung riêng (Kính gửi, Hình thức nhận kết quả); mặc định: khối con có vạch tiêu đề trong khung chính. */
  frame?: "box";
  rows: SjsRow[];
}

export interface SjsComponent {
  name: string;
  banChinh?: number;
  banSao?: number;
}

export interface SjsForm {
  source: string;
  title: string;
  capturedAt: string;
  note?: string;
  sections: SjsSection[];
  /** Bảng THÀNH PHẦN HỒ SƠ (dòng cố định, nút "Tải lên file" theo dòng). */
  components?: SjsComponent[];
}

export interface SjsResult {
  cells: Map<string, Cell>;
  /** Ô đang hiện trên cổng sau khi điền xong. */
  visible: Set<string>;
  /** Ô đang ẩn → điều kiện hiện (để ghi chú). */
  hiddenBy: Map<string, string>;
  unmatched: Unmatched[];
  stats: SimStats;
}

// ---- khớp chữ, chép từ surveyjs-main.js -------------------------------------------------------------------

export const sjsFold = (s: unknown) => String(s ?? "")
  .replace(/Đ/g, "D").replace(/đ/g, "d")
  .normalize("NFD").replace(/[̀-ͯ]/g, "")
  .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
const stripAdmin = (s: unknown) => sjsFold(s).replace(/^(tinh|thanh pho|tp|xa|phuong|thi tran|dac khu)\s+/, "");

function matchScore(want: unknown, text: string, value: string): number {
  const w = sjsFold(want);
  if (!w) return 0;
  const t = sjsFold(text);
  if (t === w || sjsFold(value) === w) return 100;
  if (stripAdmin(t) === stripAdmin(w)) return 95;
  if (t && (t.includes(w) || w.includes(t))) return 80 - Math.min(20, Math.abs(t.length - w.length) / 4);
  const wt = new Set(w.split(" ")), tt = new Set(t.split(" "));
  const common = [...wt].filter((x) => tt.has(x)).length;
  return common ? Math.round((common / Math.max(wt.size, tt.size)) * 70) : 0;
}

function bestChoice(options: Opt[], want: unknown): { opt: Opt | null; score: number } {
  let opt: Opt | null = null;
  let score = 0;
  for (const o of options) {
    const s = matchScore(want, o[1], o[0]);
    if (s > score) { opt = o; score = s; }
  }
  return score >= 50 ? { opt, score } : { opt: null, score };
}

const ISO_RE = /^(\d{4})-(\d{2})-(\d{2})$/;
const DMY_RE = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;

export function sjsFields(form: SjsForm): SjsField[] {
  return form.sections.flatMap((s) => s.rows.flatMap((r) => r.fields ?? []));
}

export function simulateSurveyJs(form: SjsForm, fields: UiField[], area: AreaCatalog | null): SjsResult {
  const all = sjsFields(form);
  const defs = new Map(all.map((f) => [f.name, f]));
  const cells = new Map<string, Cell>();
  const unmatched: Unmatched[] = [];
  const typeOf = (k: SjsKind) => (k === "dropdown" ? "x-select" : k === "radio" ? "x-radio" : k === "date" ? "x-date" : "x-input");

  for (const f of all) {
    const status: Cell["status"] = f.auto ? "auto" : f.readonly || f.prefilled ? "prefilled" : "empty";
    cells.set(f.name, {
      key: f.name, name: f.name, type: typeOf(f.kind), label: f.label, required: !!f.required, readonly: !!f.readonly,
      status, reasons: f.auto ? [f.auto] : [],
      options: f.catalog === "provinces" ? area?.provinces : f.options,
      picked: f.kind === "radio" ? null : undefined,
    });
  }

  const value = (name: string) => cells.get(name)?.picked?.[0];
  const holds = (cond: Record<string, string[]>) => Object.entries(cond)
    .every(([name, codes]) => codes.includes(String(value(name) ?? "")));
  const isVisible = (f: SjsField) => !f.visibleIf || holds(f.visibleIf);
  const conditionText = (f: SjsField, cond = f.visibleIf) => Object.entries(cond ?? {}).map(([name, codes]) => {
    const def = defs.get(name);
    const labels = codes.map((c) => def?.options?.find((o) => o[0] === c)?.[1] ?? c);
    return `"${(def?.label || name).replace(/\s*:\s*$/, "")}" = ${labels.join(" / ")}`;
  }).join(" và ");

  // Danh mục xã nạp theo tỉnh đã chọn; chưa chọn tỉnh thì cổng chưa có danh sách.
  const optionsOf = (f: SjsField, c: Cell): Opt[] | undefined => {
    if (f.catalog !== "wards") return c.options;
    const province = f.parent ? cells.get(f.parent)?.picked : null;
    return province && area ? area.wards(province[0]) : [];
  };

  const setChoice = (f: SjsField, c: Cell, want: unknown, field: UiField, code?: string) => {
    c.field = field;
    const opts = optionsOf(f, c);
    c.options = opts;
    if (opts === undefined) {
      c.status = "unchecked";
      c.want = want;
      c.text = String(want);
      c.reasons.push("chưa có danh sách option của cổng (danh mục nạp từ API) — chưa kiểm được");
      return;
    }
    if (!opts.length) {
      c.status = "miss";
      c.want = want;
      c.reasons.push(f.catalog === "wards" ? "chưa chọn được Tỉnh nên cổng chưa nạp danh sách xã" : "danh mục trống");
      return;
    }
    const byCode = code !== undefined && code !== null && code !== "" ? opts.find((o) => o[0] === String(code)) : undefined;
    const hit = byCode ? { opt: byCode, score: 100 } : bestChoice(opts, want);
    c.picked = hit.opt;
    if (!hit.opt) {
      c.status = "miss";
      c.want = want;
      c.reasons.push(`không option nào khớp đủ (điểm cao nhất ${Math.round(hit.score)}/100, cần ≥ 50)`);
      return;
    }
    c.status = field.default ? "default" : "filled";
    c.text = hit.opt[1];
    if (!byCode && hit.score < 100) {
      c.how = "loose";
      c.want = want;
      if (hit.score < 95) c.reasons.push(`khớp gần đúng (${Math.round(hit.score)}/100) — kiểm lại option đã chọn`);
    }
  };

  const setText = (f: SjsField, c: Cell, raw: unknown, field: UiField) => {
    c.field = field;
    let text = typeof raw === "object" ? JSON.stringify(raw) : String(raw);
    if (f.kind === "date") {
      const iso = field.code && ISO_RE.test(field.code) ? field.code : text.replace(DMY_RE, (_, d, m, y) => `${y}-${m.padStart(2, "0")}-${d.padStart(2, "0")}`);
      const m = iso.match(ISO_RE);
      if (!m) {
        c.status = "miss";
        c.want = raw;
        c.reasons.push("không đổi được sang ngày yyyy-mm-dd — ô ngày của cổng không nhận");
        return;
      }
      text = `${m[3]}/${m[2]}/${m[1]}`;
    }
    c.text = text;
    c.status = field.default ? "default" : "filled";
    if (f.pattern && !new RegExp(f.pattern).test(text)) {
      c.status = "miss";
      c.want = raw;
      c.reasons.push(`cổng báo sai định dạng${f.patternHint ? ` (${f.patternHint})` : ""}`);
    }
  };

  const fill = (f: SjsField, c: Cell, want: unknown, field: UiField, code?: string) => {
    if (f.kind === "dropdown" || f.kind === "radio") setChoice(f, c, want, field, code);
    else setText(f, c, want, field);
  };

  // sjs-area: ô sau radio của cụm, trước radio kế tiếp, trong cùng khối; dò theo nhãn.
  const fillArea = (field: UiField) => {
    const data = (field.value ?? {}) as Record<string, unknown>;
    const section = form.sections.find((s) => s.rows.some((r) => r.fields?.some((x) => x.name === field.radio)));
    const ordered = section ? section.rows.flatMap((r) => r.fields ?? []) : all;
    const start = field.radio ? ordered.findIndex((x) => x.name === field.radio) : -1;
    const candidates: SjsField[] = [];
    for (const x of ordered.slice(start + 1)) {
      if (field.radio && x.kind === "radio") break;
      if (!x.readonly && isVisible(x)) candidates.push(x);
    }
    const pick = (re: RegExp, kind: SjsKind) => candidates.find((x) => x.kind === kind && re.test(sjsFold(x.label)));
    const steps: [SjsField | undefined, unknown][] = [
      [pick(/quoc gia/, "dropdown"), data.quocGia || "Việt Nam"],
      [pick(/tinh thanh pho/, "dropdown"), data.tinh],
      [pick(/xa phuong|phuong xa/, "dropdown"), data.xa],
      [pick(/chi tiet|dia chi/, "text"), data.diaChi],
    ];
    let any = false;
    for (const [x, want] of steps) {
      if (!x || isEmpty(want)) continue;
      any = true;
      const c = cells.get(x.name)!;
      fill(x, c, want, field);
      c.via = `cụm địa chỉ ${field.name} (dò ô theo nhãn sau radio ${field.radio ?? "—"})`;
    }
    if (!any) {
      unmatched.push({
        field,
        reason: candidates.length
          ? "không ô nào sau radio khớp nhãn quốc gia / tỉnh / xã / địa chỉ"
          : `không có ô nào đang hiện sau radio ${field.radio ?? "(không khai radio)"} — chọn radio chưa đúng`,
      });
    }
  };

  for (const field of fields) {
    if (isEmpty(field.value)) continue;
    if (field.comp === "sjs-area") { fillArea(field); continue; }
    const f = defs.get(field.name) ?? all.find((x) => x.name.startsWith(`${field.name}__`));
    if (!f) {
      unmatched.push({ field, reason: "mẫu không có câu hỏi tên này → extension báo không thấy" });
      continue;
    }
    const c = cells.get(f.name)!;
    if (f.readonly) {
      c.field = field;
      c.want = field.value;
      c.reasons.push(`BE gửi "${String(field.value)}" nhưng ô khoá theo tài khoản — extension bỏ qua`);
      continue;
    }
    if (field.onlyIfEmpty && c.status === "prefilled") {
      c.field = field;
      c.reasons.push(`BE gửi "${String(field.value)}" chỉ để điền khi ô trống — cổng đã đổ sẵn nên extension giữ nguyên`);
      continue;
    }
    fill(f, c, field.value, field, field.code);
    if (field.lookup) c.via = "ô tra cứu CSDL dân cư: cổng tra được thì tự đổ + khoá giới tính, dân tộc, giấy tờ, nơi cư trú — extension không ghi đè ô cổng đã đổ";
  }

  // Cổng tự chép (trigger copyvalue): ô BE không gửi mà điều kiện chép thoả → cổng tự điền.
  for (const f of all) {
    const c = cells.get(f.name)!;
    if (f.copiedIf && holds(f.copiedIf) && c.status === "empty") {
      c.status = "prefilled";
      c.reasons.push(`cổng tự chép từ khối người nộp khi ${conditionText(f, f.copiedIf)}`);
    }
  }

  // Hiện/ẩn theo giá trị cuối cùng: ô có giá trị nhưng khối ẩn → cổng xoá khi nộp.
  const visible = new Set<string>();
  const hiddenBy = new Map<string, string>();
  for (const f of all) {
    if (isVisible(f)) { visible.add(f.name); continue; }
    hiddenBy.set(f.name, conditionText(f));
    const c = cells.get(f.name)!;
    if (c.status === "filled" || c.status === "default" || c.status === "miss") {
      c.status = "hidden-value";
      c.want = c.want ?? c.text;
      c.reasons.push(`khối đang ẩn — chỉ hiện khi ${conditionText(f)}`);
    }
  }

  const shown = [...cells.values()].filter((c) => visible.has(c.key) || c.status === "hidden-value");
  for (const c of shown) if (c.status === "empty" && !c.required) c.status = "blank";
  const miss = shown.filter((c) => c.status === "miss" || c.status === "hidden-value").length;
  const empty = shown.filter((c) => c.status === "empty").length;
  return {
    cells, visible, hiddenBy, unmatched,
    stats: {
      cells: shown.length,
      filled: shown.filter((c) => ["filled", "default", "prefilled", "unchecked", "auto"].includes(c.status)).length,
      defaults: shown.filter((c) => c.status === "default").length,
      red: miss + empty,
      miss,
      empty,
      requiredEmpty: empty,
    },
  };
}

// ---- Đính kèm: dòng của bảng thành phần hồ sơ, chép findUploadRow của content/fill-surveyjs.js -----------

export interface SjsPlanItem {
  fileIndex?: number;
  fileName?: string;
  documentName?: string;
  componentName?: string;
  slotName?: string;
  slotIndex?: number;
  sourceFileIndexes?: number[];
  sourceSegments?: { fileIndex: number; pages?: number[]; pageIndexes?: number[] }[];
}

/** Dòng nhận tệp: có tên dòng thì so CHỨA (40 ký tự đầu, đã bỏ dấu), không khớp → null (extension báo lỗi). */
export function findComponentRow(components: SjsComponent[], item: SjsPlanItem): number | null {
  const want = sjsFold(item.slotName || item.componentName).slice(0, 40);
  if (want) {
    const i = components.findIndex((c) => sjsFold(c.name).includes(want));
    return i >= 0 ? i : null;
  }
  const i = item.slotIndex ?? 0;
  return i < components.length ? i : null;
}
