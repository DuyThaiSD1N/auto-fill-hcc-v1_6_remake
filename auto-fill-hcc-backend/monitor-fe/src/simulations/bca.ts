// Mô phỏng điền trang căn cước của Cổng DVC Bộ Công an (dichvucong.bocongan.gov.vn/portal/p/home/dvc-CCCD-*.html:
// jQuery + bootstrap-select + bootstrap-datepicker, ô id = name) bằng mẫu trong mau-bca/<tên>.json.
//
// Quy tắc chép từ extension (auto-fill-hcc-extension/content.js, fillFormStandard trên host bocongan):
// - bca-declarant (radio radIsNCC): so Phần I (tài khoản VNeID, cổng khoá) với người cần cấp trên giấy — cùng số định
//   danh, một bên thiếu số thì so họ tên → "self"; khác → "other" mở khối Phần II (otherBlock). Không đọc được Phần I →
//   không chọn. Ô bcaOtherOnly chỉ điền khi "other", bcaSelfOnly chỉ khi "self" (fillBcaDeclarantField);
// - bcaAccountIs {name,id}: chỉ ghi khi Phần I đúng là người đó (bcaAccountIs);
// - keepPortalValue: cổng đổ sẵn SĐT/email tài khoản thì giữ nguyên (standardKeepsPortalValue);
// - bca-relation: tài khoản trùng số → trùng tên (khác số thì không tính) với cha/mẹ/người đại diện trên giấy; không trùng
//   ai → fallback (fillBcaRelationField);
// - bca-agency: Tỉnh (cityId) → Xã (wardId, chỉ khi có ward) khớp trọn tên, không thì bỏ "Công an" + tiền tố đơn vị hành
//   chính và phải ra ĐÚNG MỘT dòng; readySelect nạp sau, một dòng thật thì chọn luôn (readyPick) (fillBcaAgencyField);
// - dom-select: bootstrap-select — khớp đủ chữ (bỏ dấu) trước, bỏ tiền tố Phường/Xã/Tỉnh chỉ khi ra đúng một mục
//   (pickBootstrapSelectItem);
// - dom-radio: radio ĐẦU TIÊN có nhãn trùng / chứa / nằm trong giá trị (radioValueMatches), không khớp thì không tick;
// - dom-date: dd/mm/yyyy (bcaSetPickerDates gán qua datepicker).
// Tài khoản đăng nhập không có trong output → người xem chọn ở thanh "Tài khoản đăng nhập" (mặc định suy từ giấy).
import { isEmpty, type UiField } from "./fill";
import { foldChoice, type Cell, type Opt, type SimStats, type Unmatched } from "./eform";
import type { AreaCatalog } from "./angular";

export type BcaKind = "text" | "date" | "select" | "radio";

export interface BcaField {
  /** id = name của ô trên trang. */
  id: string;
  kind: BcaKind;
  label: string;
  required?: boolean;
  /** Ô cổng đổ theo tài khoản VNeID và khoá (Phần I). */
  readonly?: boolean;
  /** Danh sách option; "@provinces" = 34 tỉnh, "@wards:<id ô tỉnh>" = xã theo tỉnh đang chọn ở ô đó. */
  options?: string[] | string;
  /** Tiền tố cổng gắn trước tên đơn vị trong option (vd "Công an " ở ô cơ quan thực hiện). */
  optionPrefix?: string;
  /** Chỉ hiện khi ô `field` đang chọn một trong các nhãn `is`. */
  showWhen?: { field: string; is: string[] };
  /** Ô mở của chủ tài khoản (SĐT/email Phần I) cổng thường đổ sẵn từ VNeID → còn trống thì không tính đỏ. */
  portalMayFill?: boolean;
  /** Lựa chọn cổng chọn sẵn khi mở trang (BE không gửi thì ô giữ lựa chọn này). */
  portalDefault?: string;
  /** Cổng tự điền rồi khoá ô khi ô `field` đang chọn một trong các nhãn `is` (vd khối chủ hộ khi lập hộ mới). */
  lockedWhen?: { field: string; is: string[]; note: string };
  /** Ô ngày theo ô "Định dạng": nhận dd/mm/yyyy, mm/yyyy hoặc yyyy. */
  partialDate?: boolean;
  /** Id từng radio, cùng thứ tự `options` — BE gửi selfId/otherId mà không kèm nhãn thì khớp theo id. */
  radioIds?: string[];
  wide?: boolean;
  note?: string;
}

export interface BcaSection {
  title: string;
  /** id khối trên trang (vd divCheck_NDN). */
  id?: string;
  /** "other": chỉ hiện khi người kê khai là cha/mẹ/người đại diện (radio radIsNCC → khác người). */
  showWhenDeclarant?: "other";
  /** Cổng ẩn/hiện khối theo điều kiện mô phỏng không biết trước → ô trống không tính đỏ. */
  portalDecides?: string;
  note?: string;
  fields: BcaField[];
  /** Bảng dòng lặp (comp "bca-rows"): ô dòng n có id <prefix><n>, dòng thêm bằng nút "thêm" của cổng. */
  table?: { id: string; columns: { prefix: string; label: string; kind: BcaKind; options?: string[] }[] };
}

export interface BcaForm {
  source: string;
  title: string;
  capturedAt: string;
  note?: string;
  /** Mẫu dựng theo mapping + mã extension, chưa chụp trên trang thật. */
  inferred?: boolean;
  /** Mã thủ tục theo lựa chọn của một radio (vd dưới 14 tuổi: Cấp Tỉnh 1.012549 / Cấp Xã 1.014062). */
  code?: string | { field: string; map: Record<string, string> };
  sections: BcaSection[];
}

export interface BcaPerson {
  name?: string;
  id?: string;
}

export interface BcaPersona {
  key: string;
  label: string;
  person: BcaPerson | null;
}

export interface BcaResult {
  cells: Map<string, Cell>;
  /** Ô đang hiện trên trang (khối + điều kiện). */
  visible: Set<string>;
  hiddenSections: Set<number>;
  /** Ô có giá trị nhưng extension cố ý không ghi (theo tài khoản / khối ẩn). */
  held: { field: UiField; reason: string }[];
  declarant: "self" | "other" | null;
  /** Dòng của bảng bca-rows theo id bảng. */
  rows: Map<string, Cell[][]>;
  code: string | null;
  unmatched: Unmatched[];
  stats: SimStats;
}

const fold = (s: unknown) => foldChoice(s);
const digits = (s: unknown) => String(s ?? "").replace(/\D/g, "");
const DATE_RE = /^\d{2}\/\d{2}\/\d{4}$/;
const PARTIAL_DATE_RE = /^(?:\d{2}\/)?(?:\d{2}\/)?\d{4}$/;
const UNIT_PREFIX = /^(phuong|xa|thi tran|dac khu|tinh|thanh pho)\s+/;
const bootstrapKey = (s: string) => fold(s).replace(UNIT_PREFIX, "").trim();
const agencyBare = (s: string) => fold(s).replace(/^cong an\s+/, "").replace(UNIT_PREFIX, "");

/** Người có trên giấy (theo output) để chọn làm tài khoản đăng nhập. */
export function bcaPersonas(fields: UiField[]): BcaPersona[] {
  const out: BcaPersona[] = [];
  const add = (label: string, p: BcaPerson | undefined | null) => {
    if (!p || !(p.name || p.id)) return;
    const key = `${fold(p.name)}|${digits(p.id)}`;
    if (out.some((x) => x.key === key)) return;
    out.push({ key, label: `${label}: ${p.name ?? ""}${p.id ? ` (${p.id})` : ""}`.trim(), person: { name: p.name, id: p.id } });
  };
  for (const f of fields) {
    const v = f.value as Record<string, unknown> | null;
    if (f.comp === "bca-declarant" && v) add("Người cần cấp", v.subject as BcaPerson);
    if (f.comp === "bca-relation" && v && Array.isArray(v.people)) {
      for (const p of v.people as (BcaPerson & { relation?: string })[]) add(p.relation ?? "Người trên giấy", p);
    }
    const owner = (f as UiField & { bcaAccountIs?: BcaPerson }).bcaAccountIs;
    if (owner) add("Người ký trên giấy", owner);
  }
  out.push({ key: "other", label: "Người khác (không trùng ai trên giấy)", person: { name: "__khac__", id: "000000000000" } });
  return out;
}

/** Tài khoản mặc định: người chủ SĐT/email Phần I trên giấy (bcaAccountIs) — không có thì người cần cấp, rồi người đầu. */
export function defaultPersona(personas: BcaPersona[], fields: UiField[]): string {
  const owner = fields.map((f) => (f as UiField & { bcaAccountIs?: BcaPerson }).bcaAccountIs).find(Boolean);
  if (owner) {
    const hit = personas.find((p) => p.person && samePerson(p.person, owner));
    if (hit) return hit.key;
  }
  return personas[0]?.key ?? "other";
}

/** Cùng số định danh; một bên thiếu số thì so họ tên (bcaAccountIs / fillBcaDeclarantField). */
function samePerson(account: BcaPerson, want: BcaPerson): boolean {
  const a = digits(account.id), w = digits(want.id);
  if (a && w) return a === w;
  return !!fold(account.name) && fold(account.name) === fold(want.name);
}

const optionsOf = (f: BcaField, area: AreaCatalog | null, pickedCity: Map<string, Opt | null>): Opt[] | undefined => {
  const prefix = f.optionPrefix ?? "";
  if (Array.isArray(f.options)) return f.options.map((l) => [l, l] as Opt);
  if (f.options === "@provinces") return area?.provinces.map(([v, l]) => [v, prefix + l] as Opt);
  const ward = /^@wards:(.+)$/.exec(String(f.options ?? ""));
  if (ward) {
    const city = pickedCity.get(ward[1]);
    return city && area ? area.wards(city[0]).map(([v, l]) => [v, prefix + l] as Opt) : [];
  }
  return undefined;
};

export function simulateBca(form: BcaForm, fields: UiField[], area: AreaCatalog | null, account: BcaPerson | null): BcaResult {
  const all = form.sections.flatMap((s, si) => s.fields.map((f) => ({ f, si })));
  const byId = new Map(all.map((x) => [x.f.id, x]));
  const cells = new Map<string, Cell>();
  const unmatched: Unmatched[] = [];
  const held: BcaResult["held"] = [];
  const pickedCity = new Map<string, Opt | null>();
  const typeOf = (k: BcaKind) => (k === "select" ? "x-select" : k === "radio" ? "x-radio" : k === "date" ? "x-date" : "x-input");

  for (const { f } of all) {
    cells.set(f.id, {
      key: f.id, name: f.id, type: typeOf(f.kind), label: f.label, required: !!f.required, readonly: !!f.readonly,
      status: f.readonly ? "prefilled" : "empty", reasons: [], via: f.note,
      options: f.kind === "radio" || Array.isArray(f.options) || f.options === "@provinces" ? optionsOf(f, area, pickedCity) : undefined,
      picked: f.kind === "radio" ? null : undefined,
    });
  }
  for (const { f } of all) {
    if (!f.portalDefault) continue;
    const c = cells.get(f.id)!;
    const opt = (c.options ?? []).find(([, l]) => fold(l) === fold(f.portalDefault)) ?? null;
    c.status = "prefilled"; c.text = f.portalDefault; c.picked = opt ?? [f.portalDefault, f.portalDefault];
    c.reasons.push("cổng chọn sẵn khi mở trang");
  }
  const rows = new Map<string, Cell[][]>();
  // Phần I: cổng đổ theo tài khoản — hiện người đang chọn làm tài khoản.
  const accountName = cells.get("txtFULLNAME_NDN");
  const accountId = cells.get("txtIDENTIFY_NUMBER_NDN");
  const realAccount = account && account.name !== "__khac__" ? account : null;
  if (accountName) accountName.text = realAccount?.name ?? (account ? "(người khác)" : undefined);
  if (accountId) accountId.text = realAccount?.id ?? undefined;

  const mark = (c: Cell, f: UiField, text: string, opt?: Opt | null) => {
    c.field = f;
    c.status = f.default ? "default" : "filled";
    c.text = text;
    if (opt !== undefined) c.picked = opt;
  };
  const miss = (c: Cell, f: UiField, want: unknown, reason: string) => {
    c.field = f; c.status = "miss"; c.want = want; c.reasons.push(reason);
  };

  // Ghi chú thông tin (không phải lỗi): Notes của FormSimulation hiện `via` màu thường, `reasons` của ô đã điền màu đỏ.
  const info = (c: Cell, text: string) => { c.via = c.via ? `${c.via} · ${text}` : text; };
  const pickSelect = (opts: Opt[], value: unknown) => {
    const full = fold(value);
    const exact = opts.find(([, l]) => fold(l) === full);
    if (exact) return { opt: exact, how: "exact" as const };
    const key = bootstrapKey(String(value ?? ""));
    const byKey = key ? opts.filter(([, l]) => bootstrapKey(l) === key) : [];
    if (byKey.length === 1) return { opt: byKey[0], how: "loose" as const };
    return { opt: null, hits: byKey.length };
  };

  let declarant: BcaResult["declarant"] = null;
  const ordered = [...fields].sort((a, b) => Number(b.comp === "bca-declarant") - Number(a.comp === "bca-declarant"));

  for (const f of ordered) {
    const extra = f as UiField & { bcaOtherOnly?: boolean; bcaSelfOnly?: boolean; bcaAccountIs?: BcaPerson; keepPortalValue?: boolean };
    const v = f.value as Record<string, unknown>;

    if (f.comp === "bca-declarant") {
      const c = cells.get(f.name);
      if (!c) { unmatched.push({ field: f, reason: `mẫu không có radio ${f.name}` }); continue; }
      const subject = (v?.subject ?? {}) as BcaPerson;
      if (!account) { c.field = f; c.status = "auto"; c.reasons.push("chưa đọc được tài khoản ở Phần I → extension không chọn"); continue; }
      declarant = samePerson(account, subject) ? "self" : "other";
      // Extension tìm radio theo id (selfId / otherId) trước, không thấy mới dò theo nhãn.
      const wantId = String((declarant === "self" ? v.selfId : v.otherId) ?? "");
      const want = declarant === "self" ? String(v.selfLabel ?? "") : String(v.otherLabel ?? "");
      const ids = byId.get(f.name)?.f.radioIds ?? [];
      const opt = (ids.includes(wantId) ? (c.options ?? [])[ids.indexOf(wantId)] : undefined)
        ?? (want ? (c.options ?? []).find(([, l]) => fold(l) === fold(want)) : undefined) ?? null;
      if (opt) mark(c, f, opt[1], opt);
      else miss(c, f, want || wantId, "không thấy radio có id / nhãn này (extension dò theo id rồi theo nhãn)");
      info(c, declarant === "self" ? "tài khoản trùng người cần cấp → tự kê khai" : "tài khoản khác người cần cấp → kê khai thay, mở Phần II");
      continue;
    }

    if ((extra.bcaOtherOnly && declarant !== "other") || (extra.bcaSelfOnly && declarant !== "self")) {
      held.push({ field: f, reason: extra.bcaOtherOnly ? "chỉ điền khi người kê khai là cha/mẹ/người đại diện" : "chỉ điền khi người kê khai là người cần cấp" });
      const c = cells.get(f.name);
      if (c && !c.readonly && !extra.bcaOtherOnly) { c.status = "auto"; c.field = f; c.want = f.value; c.reasons.push("tài khoản không tự kê khai → extension không ghi; ô giữ giá trị cổng đổ (nếu có)"); }
      continue;
    }
    if (extra.bcaAccountIs && !(account && samePerson(account, extra.bcaAccountIs))) {
      held.push({ field: f, reason: `tài khoản không phải ${extra.bcaAccountIs.name ?? extra.bcaAccountIs.id} → extension không ghi` });
      const c = cells.get(f.name);
      if (c) { c.status = "auto"; c.field = f; c.want = f.value; c.reasons.push(`chỉ ghi khi tài khoản là ${extra.bcaAccountIs.name ?? extra.bcaAccountIs.id}; ô giữ giá trị cổng đổ (nếu có)`); }
      continue;
    }

    if (f.comp === "bca-agency") {
      const cityId = String(v?.cityId ?? "cboORGTinh"), wardId = String(v?.wardId ?? "cboORGXa");
      const city = cells.get(cityId), ward = cells.get(wardId);
      const province = String(v?.province ?? ""), wardName = String(v?.ward ?? "");
      if (!city || (!ward && wardName)) { unmatched.push({ field: f, reason: `mẫu không có ô ${!city ? cityId : wardId}` }); continue; }
      const agencyPick = (opts: Opt[], name: string) => {
        const full = opts.filter(([, l]) => fold(l) === fold(name));
        if (full.length === 1) return full[0];
        const loose = opts.filter(([, l]) => agencyBare(l) === agencyBare(name));
        return loose.length === 1 ? loose[0] : null;
      };
      const cityOpts = city.options ?? [];
      const co = cityOpts.length ? agencyPick(cityOpts, province) : null;
      if (!cityOpts.length) { city.field = f; city.status = "unchecked"; city.text = province; city.reasons.push("chưa có danh sách cơ quan tỉnh"); }
      else if (!co) { miss(city, f, province, `không khớp đúng một trong ${cityOpts.length} cơ quan tỉnh`); continue; }
      else mark(city, f, co[1], co);
      pickedCity.set(cityId, co);
      if (wardName && ward) {
        const wf = byId.get(wardId)!.f;
        ward.options = optionsOf(wf, area, pickedCity);
        const wo = ward.options?.length ? agencyPick(ward.options, wardName) : null;
        if (!ward.options?.length) { ward.field = f; ward.status = "unchecked"; ward.text = wardName; ward.reasons.push("chưa có danh sách cơ quan xã của tỉnh này"); }
        else if (!wo) miss(ward, f, wardName, `không khớp đúng một trong ${ward.options.length} cơ quan xã của ${co?.[1] ?? province}`);
        else mark(ward, f, wo[1], wo);
      }
      if (f.onlyIfEmpty) info(city, "Tỉnh/Xã đã chọn sẵn trên trang thì extension giữ nguyên");
      const ready = v?.readySelect ? cells.get(String(v.readySelect)) : undefined;
      if (ready && v.readyPick) {
        ready.field = f; ready.status = "auto";
        ready.reasons.push("cổng nạp theo cơ quan; chỉ một địa chỉ thì extension chọn luôn, nhiều thì để cán bộ chọn");
      } else if (ready) info(ready, "cổng nạp danh sách sau khi chọn cơ quan — extension chờ có option rồi mới điền tiếp");
      continue;
    }

    if (f.comp === "bca-rows") {
      const table = form.sections.map((s) => s.table).find((t) => t?.id === f.name);
      if (!table) { unmatched.push({ field: f, reason: `mẫu không có bảng ${f.name}` }); continue; }
      const out: Cell[][] = [];
      ((v?.rows ?? []) as { id: string; comp?: string; value: unknown }[][]).forEach((row, ri) => {
        const line: Cell[] = table.columns.map((col) => ({
          key: `${col.prefix}${ri}`, name: `${col.prefix}${ri}`, type: typeOf(col.kind), label: col.label, required: false,
          status: "blank", reasons: [], options: col.options?.map((l) => [l, l] as Opt),
        }));
        for (const sub of Array.isArray(row) ? row : []) {
          const ci = table.columns.findIndex((col) => sub.id.startsWith(col.prefix) && /^\d+$/.test(sub.id.slice(col.prefix.length)));
          const sf: UiField = { name: sub.id, comp: sub.comp, value: sub.value, default: f.default };
          if (ci < 0) { unmatched.push({ field: sf, reason: `bảng ${f.name} không có cột cho ô này` }); continue; }
          const cell = line[ci];
          if (isEmpty(sub.value)) continue;
          if (sub.comp === "dom-select" && cell.options?.length) {
            const p = pickSelect(cell.options, sub.value);
            if (p.opt) { mark(cell, sf, p.opt[1], p.opt); cell.how = p.how; } else miss(cell, sf, sub.value, `không có trong ${cell.options.length} option`);
          } else if (sub.comp === "dom-select") {
            cell.field = sf; cell.status = "unchecked"; cell.text = String(sub.value); cell.reasons.push("chưa có danh sách option của cột này");
          } else mark(cell, sf, String(sub.value));
        }
        line.forEach((cell) => cells.set(cell.key, cell));
        out.push(line);
      });
      rows.set(f.name, out);
      continue;
    }

    const c = cells.get(f.name);
    if (!c) { unmatched.push({ field: f, reason: "mẫu không có ô id này → extension báo không thấy" }); continue; }

    if (f.comp === "bca-relation") {
      const people = (Array.isArray(v?.people) ? v.people : []) as (BcaPerson & { relation?: string })[];
      if (!account) { c.field = f; c.status = "auto"; c.reasons.push("chưa đọc được tài khoản ở Phần I → không chọn"); continue; }
      const aid = digits(account.id);
      const hit = people.find((p) => aid && digits(p.id) === aid)
        ?? people.find((p) => fold(p.name) && fold(p.name) === fold(account.name) && !(aid && digits(p.id) && digits(p.id) !== aid));
      const relation = hit?.relation ?? String(v?.fallback ?? "");
      const opt = (c.options ?? []).find(([, l]) => fold(l) === fold(relation)) ?? null;
      if (opt) mark(c, f, opt[1], opt);
      else miss(c, f, relation, "không có option quan hệ này");
      info(c, hit ? `tài khoản trùng ${hit.relation} trên giấy` : "tài khoản không trùng ai trên giấy → option dự phòng");
      continue;
    }
    if (isEmpty(f.value)) continue;
    if (c.readonly) { miss(c, f, f.value, "ô cổng khoá theo tài khoản — extension không ghi được"); continue; }

    const tf = byId.get(f.name)!.f;
    if (f.comp === "dom-radio" || tf.kind === "radio") {
      const want = fold(f.value);
      const opt = (c.options ?? []).find(([, l]) => { const lf = fold(l); return !!lf && (lf === want || lf.includes(want) || want.includes(lf)); }) ?? null;
      if (opt) mark(c, f, opt[1], opt);
      else miss(c, f, f.value, `không khớp lựa chọn nào (${(c.options ?? []).map((o) => o[1]).join(" / ")}) → không tick`);
      continue;
    }
    if (f.comp === "dom-select" || tf.kind === "select") {
      const sel = f as UiField & { firstOption?: boolean; waitMs?: number };
      if (sel.waitMs) info(c, `danh sách nạp chậm qua API — extension thử lại tới ${Math.min(sel.waitMs, 10000) / 1000} s`);
      if (sel.firstOption) {
        // pickFirstSelectOption: không khớp chữ, chọn mục thật đầu tiên (ô chỉ có cơ quan đã chọn ở bước chọn trường hợp).
        c.field = f; c.status = "auto"; c.want = f.value;
        c.reasons.push("extension chọn mục thật đầu tiên của danh sách, không khớp theo chữ");
        continue;
      }
      const opts = optionsOf(tf, area, pickedCity) ?? [];
      c.options = opts;
      if (!opts.length) {
        c.field = f; c.status = "unchecked"; c.text = String(f.value);
        c.reasons.push(String(tf.options ?? "").startsWith("@wards") ? "chưa có danh sách option (ô nạp theo ô khác chưa chọn được)" : "chưa có danh sách option của cổng cho ô này — chưa kiểm được");
        continue;
      }
      const p = pickSelect(opts, f.value);
      if (!p.opt) { miss(c, f, f.value, p.hits && p.hits > 1 ? `bỏ tiền tố thì khớp ${p.hits} mục → không chọn` : `không có trong ${opts.length} option`); continue; }
      mark(c, f, p.opt[1], p.opt);
      c.how = p.how;
      if (p.how === "loose") c.want = f.value;
      if (/^@provinces$/.test(String(tf.options))) pickedCity.set(tf.id, p.opt);
      continue;
    }
    if (f.comp === "dom-date" || tf.kind === "date") {
      const ok = (tf.partialDate ? PARTIAL_DATE_RE : DATE_RE).test(String(f.value).trim());
      if (!ok) { miss(c, f, f.value, tf.partialDate ? "không đúng dd/mm/yyyy, mm/yyyy hay yyyy" : "không đúng dd/mm/yyyy — datepicker không nhận"); continue; }
      mark(c, f, String(f.value));
      continue;
    }
    mark(c, f, typeof f.value === "object" ? JSON.stringify(f.value) : String(f.value));
    if (extra.keepPortalValue) info(c, "cổng đã đổ sẵn giá trị của tài khoản thì extension giữ nguyên");
  }

  // Ô / khối đang hiện.
  const visible = new Set<string>();
  const hiddenSections = new Set<number>();
  form.sections.forEach((s, si) => {
    if (s.showWhenDeclarant === "other" && declarant !== "other") { hiddenSections.add(si); return; }
    if (s.table) for (const line of rows.get(s.table.id) ?? []) line.forEach((c) => visible.add(c.key));
    for (const f of s.fields) {
      if (f.showWhen) {
        const on = cells.get(f.showWhen.field)?.picked?.[1];
        if (!on || !f.showWhen.is.some((x) => fold(x) === fold(on))) continue;
      }
      visible.add(f.id);
    }
  });
  for (const [id, c] of cells) {
    if (visible.has(id)) continue;
    if (c.field && ["filled", "default", "miss"].includes(c.status)) {
      held.push({ field: c.field, reason: `ô ${id} đang ẩn trên cổng` });
    }
  }

  // Ô cổng tự điền + khoá theo lựa chọn khác (vd khối chủ hộ khi lập hộ mới).
  for (const { f } of all) {
    if (!f.lockedWhen) continue;
    const c = cells.get(f.id)!;
    const on = cells.get(f.lockedWhen.field)?.picked?.[1];
    if (!on || !f.lockedWhen.is.some((x) => fold(x) === fold(on))) continue;
    if (c.status === "empty") { c.status = "prefilled"; c.reasons.push(f.lockedWhen.note); }
    else if (c.field) { c.status = "miss"; c.want = c.field.value; c.reasons.push(`${f.lockedWhen.note} — giá trị BE không ghi được`); }
  }

  // Ô trống: bắt buộc mà khối không do cổng tự ẩn/hiện → đỏ; còn lại để trắng.
  const sectionOf = new Map(all.map((x) => [x.f.id, form.sections[x.si]]));
  const fieldOf = new Map(all.map((x) => [x.f.id, x.f]));
  for (const c of cells.values()) {
    if (c.status !== "empty") continue;
    if (fieldOf.get(c.key)?.portalMayFill) {
      c.status = "auto";
      c.reasons.push("BE không ghi ô này — cổng đổ sẵn từ tài khoản VNeID nếu tài khoản có");
    } else if (!c.required || sectionOf.get(c.key)?.portalDecides) c.status = "blank";
  }

  const shown = [...cells.values()].filter((c) => visible.has(c.key));
  const missN = shown.filter((c) => c.status === "miss").length;
  const emptyN = shown.filter((c) => c.status === "empty").length;
  let code: string | null = null;
  if (typeof form.code === "string") code = form.code;
  else if (form.code) {
    const on = cells.get(form.code.field)?.picked?.[1];
    code = on ? form.code.map[on] ?? null : null;
  }
  return {
    cells, visible, hiddenSections, held, declarant, rows, code, unmatched,
    stats: {
      cells: shown.length,
      filled: shown.filter((c) => ["filled", "default", "prefilled", "unchecked", "auto"].includes(c.status)).length,
      defaults: shown.filter((c) => c.status === "default").length,
      red: missN + emptyN,
      miss: missN,
      empty: emptyN,
      requiredEmpty: emptyN,
    },
  };
}
