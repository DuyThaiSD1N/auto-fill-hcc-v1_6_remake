// DANH SÁCH MẪU MÔ PHỎNG FORM (tab "Mô phỏng form" của web Monitor) — tự gom, không sửa file này khi thêm thủ tục.
//
// CHUNG:
//   - mau-eform/<id>.json   : mẫu e-form của CỔNG (một mẫu có thể dùng cho nhiều thủ tục);
//   - mau-eform/_danh-muc.json : danh sách option dùng chung mọi mẫu (xã theo tỉnh, dân tộc, quốc tịch…);
//   - eform.ts (engine khớp), scripts/snapshot-eform.mjs (chụp mẫu), FormSimulation.tsx (hiển thị).
//   - mau-angular/<tên>.json : mẫu form Angular (cổng liên thông) chụp bằng scripts/capture-angular-form.js;
//   - mau-eform/_dia-gioi.json : trỏ danh mục tỉnh + xã theo tỉnh trong _danh-muc (dùng cho cả form Angular);
//   - angular.ts (engine khớp của form Angular).
//   - mau-surveyjs/<tên>.json : mẫu biểu mẫu SurveyJS (Cổng DVC quốc gia mới) dựng lại theo trang thật, kèm bảng
//     thành phần hồ sơ cho mô phỏng đính kèm; surveyjs.ts (engine khớp).
// RIÊNG mỗi thủ tục: thư mục thu-tuc/<key-thủ-tục>/ (key theo app/procedures/registry.py), index.ts khai các
//   mẫu thủ tục dùng (thứ tự = thứ tự tờ khai trên cổng) + ghi chú; luật riêng của thủ tục cũng đặt ở đây.
// Chi tiết: docs/web-monitor/mo-phong-form.md
import type { AreaCatalog, NgForm } from "./angular";
import type { Eform, Opt } from "./eform";
import type { SjsForm } from "./surveyjs";

export interface ProcedureSim {
  /** id mẫu e-form hộ tịch trong mau-eform/, theo thứ tự tờ khai trên cổng. */
  forms?: number[];
  /** Hoặc: tên mẫu form Angular trong mau-angular/ (cổng liên thông). */
  angular?: string;
  /** Tên mẫu biểu mẫu SurveyJS trong mau-surveyjs/ (Cổng DVC quốc gia mới). Khai cùng `forms` khi thủ tục đã
   *  chuyển cổng: lượt có output "sjs-*" dựng bằng mẫu này, lượt cũ vẫn dựng bằng `forms`. */
  surveyjs?: string;
  note?: string;
}

export interface SimEntry extends ProcedureSim {
  key: string;
}

const procedures = import.meta.glob<{ default: ProcedureSim }>("./thu-tuc/*/index.ts", { eager: true });
const forms = import.meta.glob<{ default: Omit<Eform, "lists"> }>(["./mau-eform/*.json", "!./mau-eform/_danh-muc.json"]);
const lists = import.meta.glob<{ default: Record<string, Opt[]> }>("./mau-eform/_danh-muc.json");
const loadLists = () => lists["./mau-eform/_danh-muc.json"]().then((m) => m.default);

export const SIMS: SimEntry[] = Object.entries(procedures).map(([file, mod]) => ({ ...mod.default, key: file.split("/")[2] }));

export function findSim(procedure: string | null | undefined): SimEntry | undefined {
  if (!procedure) return undefined;
  return SIMS.find((s) => s.key === procedure);
}

export async function loadForm(id: number): Promise<Eform> {
  const load = forms[`./mau-eform/${id}.json`];
  if (!load) throw new Error(`Chưa chụp mẫu e-form ${id} (node scripts/snapshot-eform.mjs ${id})`);
  const [form, lists] = await Promise.all([load(), loadLists()]);
  return { ...form.default, lists };
}

const angularForms = import.meta.glob<{ default: NgForm }>("./mau-angular/*.json");
const areaIndex = import.meta.glob<{ default: { provinces: string; wards: Record<string, string> } }>("./mau-eform/_dia-gioi.json");

export async function loadAngularForm(name: string): Promise<NgForm> {
  const load = angularForms[`./mau-angular/${name}.json`];
  if (!load) throw new Error(`Chưa có mẫu form ${name} trong mau-angular/`);
  return (await load()).default;
}

export async function loadAreaCatalog(): Promise<AreaCatalog> {
  const [index, all] = await Promise.all([areaIndex["./mau-eform/_dia-gioi.json"](), loadLists()]);
  const { provinces, wards } = index.default;
  return { provinces: all[provinces] ?? [], wards: (value) => all[wards[value]] ?? [] };
}

const surveyForms = import.meta.glob<{ default: SjsForm }>("./mau-surveyjs/*.json");

export async function loadSurveyForm(name: string): Promise<SjsForm> {
  const load = surveyForms[`./mau-surveyjs/${name}.json`];
  if (!load) throw new Error(`Chưa có mẫu biểu mẫu ${name} trong mau-surveyjs/`);
  return (await load()).default;
}
