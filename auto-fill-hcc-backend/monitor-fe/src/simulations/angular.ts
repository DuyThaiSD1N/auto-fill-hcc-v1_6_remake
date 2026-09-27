// Mô phỏng điền form ANGULAR (cổng liên thông lienthong.dichvucong.gov.vn…) bằng mẫu chụp từ trang thật
// (scripts/capture-angular-form.js → mau-angular/<tên>.json).
//
// Quy tắc chép từ engine Angular của extension (auto-fill-hcc-extension/content/fill-angular.js):
// - tìm ô theo formcontrolname (đúng tên → không phân biệt hoa thường), aliases; `raw` còn tìm ô "Số lượng";
// - dropdown (ng-select / mat-select): khớp đúng chữ → nếu không, lấy option ĐẦU TIÊN "chứa nhau" hai chiều
//   (ngOptMatch) — KHÔNG kiểm ranh giới từ, không đòi duy nhất → nhiều option cùng khớp là nguy cơ chọn sai;
// - địa chỉ (diachi): Tỉnh → Xã (chỉ khi chọn được tỉnh) → Chi tiết; tỉnh/xã khớp như autocomplete (đúng chữ
//   hoặc option chứa chuỗi cần tìm);
// - radio: đúng value → đúng nhãn → nhãn chứa; checkbox: tích/bỏ tích, ô khoá thì không đổi được;
// - comp quanhe-auto / sdt-nguoiyeucau: extension tự quyết theo người đăng nhập → mô phỏng chỉ ghi chú;
// - màu cuối: có giá trị → xanh; BẮT BUỘC mà trống → đỏ (markAngularMarks); ô không bắt buộc trống để trắng;
// - ChaHoTen ↔ ChaHo/ChaChuDem/ChaTen là hai cách biểu diễn thay thế: một bên vào được thì bên kia không tính lỗi.
import { isEmpty, type UiField } from "./fill";
import { GLOBAL_ALIASES, norm, normalizeAreaValue, type Cell, type Opt, type SimStats, type Unmatched } from "./eform";

export type NgKind = "text" | "number" | "textarea" | "date" | "ngaysinh" | "ng-select" | "mat-select" | "radio" | "checkbox" | "diachi";

export interface NgPart {
  label: string;
  kind: string;
  required?: boolean;
  readonly?: boolean;
  options?: string[];
}

export interface NgField {
  key: string;
  kind: NgKind;
  label: string;
  required?: boolean;
  readonly?: boolean;
  hasValue?: boolean;
  portalType?: string;
  options?: (string | { value: string; label: string })[];
  parts?: NgPart[];
  skipped?: string;
}

export interface NgForm {
  source: string;
  title: string;
  step?: string;
  capturedAt: string;
  live?: boolean;
  note?: string;
  sections: { title: string; fields: NgField[] }[];
}

/** Danh mục tỉnh + xã theo tỉnh dùng chung với mẫu hộ tịch (mau-eform/_dia-gioi.json). */
export interface AreaCatalog {
  provinces: Opt[];
  wards: (provinceValue: string) => Opt[];
}

export interface NgResult {
  cells: Map<string, Cell>;
  unmatched: Unmatched[];
  stats: SimStats;
}

const ALT_NAME_GROUPS = [{ combined: "ChaHoTen", split: ["ChaHo", "ChaChuDem", "ChaTen"] }];
const DATE_RE = /^\d{1,2}\/\d{1,2}\/\d{4}$/;
const NGAY_SINH_RE = [/^\d{1,2}\/\d{1,2}\/\d{4}(?:[\s,]+\d{1,2}:\d{1,2})?$/, /^\d{1,2}\/\d{4}$/, /^\d{4}$/];

const optMatch = (text: string, want: string) => {
  const t = norm(text);
  return !!t && (t === want || t.includes(want) || want.includes(t));
};

/** fillNgSelect/fillMatSelect: đúng chữ, không thì option đầu tiên chứa nhau. */
function pickSelect(options: Opt[], value: unknown) {
  const want = norm(value);
  const exact = options.find(([, l]) => norm(l) === want);
  if (exact) return { opt: exact, how: "exact" as const, hits: 1 };
  const hits = options.filter(([, l]) => optMatch(l, want));
  return { opt: hits[0] ?? null, how: "loose" as const, hits: hits.length, sample: hits.slice(0, 4).map((o) => o[1]) };
}

/** ngPickAutocomplete: đúng chữ, không thì option đầu tiên CHỨA chuỗi cần tìm (một chiều). */
function pickAutocomplete(options: Opt[], value: unknown) {
  const want = norm(value);
  const exact = options.find(([, l]) => norm(l) === want);
  if (exact) return { opt: exact, how: "exact" as const, hits: 1 };
  const hits = options.filter(([, l]) => norm(l).includes(want));
  return { opt: hits[0] ?? null, how: "loose" as const, hits: hits.length, sample: hits.slice(0, 4).map((o) => o[1]) };
}

const asOpts = (list: NgField["options"] | NgPart["options"]): Opt[] | undefined =>
  list?.map((o) => (typeof o === "string" ? [o, o] : [o.value, o.label]) as Opt);

export function simulateAngular(form: NgForm, fields: UiField[], area: AreaCatalog | null): NgResult {
  const all = form.sections.flatMap((s) => s.fields);
  const byKey = new Map(all.map((f) => [f.key, f]));
  const byLower = new Map(all.map((f) => [f.key.toLowerCase(), f]));
  const find = (names: string[]) => {
    for (const n of names) if (byKey.has(n)) return byKey.get(n);
    for (const n of names) if (byLower.has(n.toLowerCase())) return byLower.get(n.toLowerCase());
    return undefined;
  };

  const cells = new Map<string, Cell>();
  const unmatched: Unmatched[] = [];
  const typeOf = (k: NgKind) =>
    k === "ng-select" || k === "mat-select" ? "x-select" : k === "radio" ? "x-radio" : k === "date" || k === "ngaysinh" ? "x-date" : k === "checkbox" ? "checkbox" : "x-input";

  // Ô trên mẫu → ô mô phỏng (trạng thái trước khi điền: cổng tự điền / trống).
  for (const f of all) {
    const opts = asOpts(f.options);
    if (f.kind === "diachi") {
      (f.parts ?? []).forEach((p, i) => {
        const role = i === 0 ? "tinh" : i === 1 ? "xa" : "diaChi";
        const key = `${f.key}/${role}`;
        cells.set(key, {
          key, name: f.key, type: role === "diaChi" ? "x-input" : "x-select", label: p.label, required: !!p.required,
          readonly: !!p.readonly, status: p.readonly ? "prefilled" : "empty", reasons: [],
          options: role === "tinh" ? area?.provinces ?? asOpts(p.options) : undefined,
        });
      });
      continue;
    }
    cells.set(f.key, {
      key: f.key, name: f.key, type: typeOf(f.kind), label: f.label, required: !!f.required, readonly: !!f.readonly,
      // Ô khoá = cổng tự điền (theo tài khoản đăng nhập, hoặc tự sinh như "Ghi bằng chữ"); HTML đã lưu
      // không giữ giá trị của input nên không dựa được vào hasValue cho các ô này.
      status: f.hasValue || f.readonly ? "prefilled" : "empty", reasons: [], options: opts,
      picked: f.kind === "radio" || f.kind === "checkbox" ? null : undefined,
    });
  }

  const setText = (c: Cell, value: unknown, field: UiField) => {
    c.field = field;
    if (c.readonly) {
      c.status = "miss";
      c.want = value;
      c.reasons.push("ô chỉ đọc (cổng khoá) — giá trị gõ vào không được Angular nhận");
      return;
    }
    c.status = field.default ? "default" : "filled";
    c.text = typeof value === "object" ? JSON.stringify(value) : String(value);
  };

  const setSelect = (c: Cell, value: unknown, field: UiField, pick = pickSelect) => {
    c.field = field;
    if (!c.options?.length && !c.readonly) {
      c.status = "unchecked";
      c.want = value;
      c.text = String(value);
      c.reasons.push("chưa có danh sách option của cổng — chưa kiểm được");
      return;
    }
    if (c.readonly) {
      // Ô khoá do cổng tự điền: extension chỉ giữ xanh khi giá trị cổng trùng, không mở được để đổi.
      c.status = "prefilled";
      c.want = value;
      c.reasons.push("ô chỉ đọc — cổng tự điền; extension chỉ xác nhận nếu trùng, không đổi được");
      return;
    }
    const p = pick(c.options ?? [], value);
    c.picked = p.opt;
    if (!p.opt) {
      c.status = "miss";
      c.want = value;
      c.reasons.push(`không có trong ${c.options?.length ?? 0} option`);
      return;
    }
    c.status = field.default ? "default" : "filled";
    c.text = p.opt[1];
    c.how = p.how;
    if (p.how === "loose") {
      c.want = value;
      if (p.hits > 1) c.reasons.push(`khớp lỏng ${p.hits} option (${(p as { sample?: string[] }).sample?.join(", ")}…) — extension lấy option ĐẦU TIÊN`);
    }
  };

  for (const f of fields) {
    const names = [f.name, ...(f.aliases ?? []), ...(GLOBAL_ALIASES[f.name] ?? [])];
    if (f.comp === "radio-bylabel") {
      const want = norm(f.value);
      const hit = all.filter((x) => x.kind === "radio").flatMap((x) => (asOpts(x.options) ?? []).map((o) => [x, o] as const))
        .find(([, o]) => norm(o[1]) === want || norm(o[1]).includes(want));
      if (hit) {
        const c = cells.get(hit[0].key)!;
        c.field = f; c.picked = hit[1]; c.text = hit[1][1]; c.status = f.default ? "default" : "filled";
      } else unmatched.push({ field: f, reason: "không thấy lựa chọn radio nào có nhãn này" });
      continue;
    }
    const target = find(names) ?? (f.comp === "raw" ? all.find((x) => norm(x.label).includes("số lượng")) : undefined);
    if (!target) {
      unmatched.push({ field: f, reason: "mẫu không có ô formcontrolname này → extension báo không thấy" });
      continue;
    }
    if (f.comp === "quanhe-auto" || f.comp === "sdt-nguoiyeucau") {
      const c = cells.get(target.key)!;
      c.field = f;
      c.status = "auto";
      c.want = f.value;
      c.reasons.push(f.comp === "quanhe-auto"
        ? "extension tự chọn Cha/Mẹ/Người giám hộ lúc chạy, bằng cách so người đăng nhập với cha/mẹ trên giấy tờ"
        : "extension chỉ điền khi người đăng nhập đúng là người ký tờ khai");
      continue;
    }
    if (isEmpty(f.value)) continue;

    if (target.kind === "diachi") {
      const data = normalizeAreaValue(f.value);
      const tinh = cells.get(`${target.key}/tinh`);
      const xa = cells.get(`${target.key}/xa`);
      const chiTiet = cells.get(`${target.key}/diaChi`);
      let tinhOk = !data.tinh;
      if (tinh && !isEmpty(data.tinh)) {
        setSelect(tinh, data.tinh, f, pickAutocomplete);
        tinhOk = tinh.status === "filled" || tinh.status === "default";
        if (tinh.status === "unchecked") tinhOk = true;
      }
      if (xa && !isEmpty(data.xa)) {
        if (!tinhOk) {
          xa.field = f; xa.status = "miss"; xa.want = data.xa;
          xa.reasons.push("chưa chọn được Tỉnh nên extension bỏ qua Phường/Xã");
        } else {
          xa.options = tinh?.picked && area ? area.wards(tinh.picked[0]) : undefined;
          setSelect(xa, data.xa, f, pickAutocomplete);
          if (xa.status === "miss" && tinh?.picked) xa.reasons[xa.reasons.length - 1] += ` xã của ${tinh.picked[1]}`;
        }
      }
      if (chiTiet && !isEmpty(data.diaChi)) setText(chiTiet, data.diaChi, f);
      continue;
    }

    const c = cells.get(target.key)!;
    if (target.key !== f.name) c.via = `khớp qua tên ${target.key}`;
    const value = f.value as unknown;
    if (value && typeof value === "object" && "tu" in (value as Record<string, unknown>)) {
      c.field = f; c.status = "auto"; c.want = value;
      c.reasons.push(`extension chép từ ô ${(value as { tu: string }).tu} đang có trên trang`);
      continue;
    }
    const kind = f.comp === "radio" || target.kind === "radio" ? "radio" : f.comp === "checkbox" ? "checkbox" : target.kind;
    if (kind === "radio") {
      const opts = c.options ?? [];
      const want = norm(value);
      const hit = opts.find(([v]) => v === String(value)) ?? opts.find(([, l]) => norm(l) === want) ?? opts.find(([, l]) => norm(l).includes(want));
      c.field = f; c.picked = hit ?? null;
      if (hit) { c.status = f.default ? "default" : "filled"; c.text = hit[1]; }
      else { c.status = "miss"; c.want = value; c.reasons.push(`không khớp lựa chọn nào (${opts.map((o) => `${o[0]}=${o[1]}`).join(", ")})`); }
    } else if (kind === "checkbox") {
      const on = !(value === false || value === "false" || value === 0 || value === "0");
      c.field = f;
      if (c.readonly && on !== (c.status === "prefilled")) { c.status = "miss"; c.want = value; c.reasons.push("ô tích đang bị khoá — không đổi được"); }
      else { c.status = f.default ? "default" : "filled"; c.text = on ? "✓" : "không tích"; c.picked = on ? ["1", "✓"] : null; }
    } else if (kind === "ng-select" || kind === "mat-select" || f.comp === "select") {
      setSelect(c, value, f);
    } else if (kind === "ngaysinh" || f.comp === "ngaysinh") {
      setText(c, value, f);
      if (!NGAY_SINH_RE.some((re) => re.test(String(value).trim()))) {
        c.status = "miss"; c.want = value; c.reasons.push("không đúng dd/mm/yyyy, mm/yyyy hoặc yyyy");
      }
    } else if (kind === "date" || f.comp === "date") {
      setText(c, value, f);
      if (c.status !== "miss" && !DATE_RE.test(String(value).trim())) {
        c.status = "miss"; c.want = value; c.reasons.push("không đúng dd/mm/yyyy — ô ngày của cổng không nhận");
      }
    } else {
      setText(c, value, f);
    }
  }

  // Hai cách biểu diễn họ tên cha: bên nào không có ô thì không tính lỗi khi bên kia đã vào.
  for (const g of ALT_NAME_GROUPS) {
    const splitIn = g.split.some((n) => cells.get(n)?.field);
    const combinedIn = !!cells.get(g.combined)?.field;
    for (let i = unmatched.length - 1; i >= 0; i--) {
      const n = unmatched[i].field.name;
      if ((n === g.combined && splitIn) || (g.split.includes(n) && combinedIn)) unmatched.splice(i, 1);
    }
  }

  // Màu cuối như markAngularMarks: trống mà không bắt buộc → không tô (không tính đỏ).
  const shown = [...cells.values()];
  for (const c of shown) if (c.status === "empty" && !c.required) c.status = "blank";
  const miss = shown.filter((c) => c.status === "miss").length;
  const empty = shown.filter((c) => c.status === "empty" && c.required).length;
  return {
    cells, unmatched,
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
