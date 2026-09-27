#!/usr/bin/env node
// Chụp mẫu e-form hộ tịch của tokhaidientu.moj.gov.vn thành JSON cho tab "Mô phỏng form" của Monitor.
//
//   node scripts/snapshot-eform.mjs <id | url-e-form> [...]
//   node scripts/snapshot-eform.mjs "https://tokhaidientu.moj.gov.vn/e-form/a03040a3-...?..." 2057
//
// Ghi src/simulations/mau-eform/<id>.json — mẫu là của CỔNG, nhiều thủ tục dùng chung một mẫu (vd khai sinh
// dùng ở cả khai sinh thường lẫn khai sinh kết hợp nhận cha mẹ con); thủ tục nào dùng mẫu nào khai trong
// thư mục riêng src/simulations/thu-tuc/<key-thủ-tục>/index.ts. Chạy lại khi cổng đổi mẫu (xem diff).
// Danh sách option (xã của 34 tỉnh, dân tộc, quốc tịch…) giống nhau giữa các mẫu → gom vào MỘT file chung
// mau-eform/_danh-muc.json theo mã băm nội dung; mẫu chỉ giữ mã. Sau mỗi lần chụp, file chung được dựng lại
// từ đúng các mã còn được mẫu nào đó dùng. Danh mục tỉnh + xã theo tỉnh còn được trỏ riêng ở
// mau-eform/_dia-gioi.json để engine của cổng KHÁC (form Angular liên thông) dùng chung.
//
// Cổng dựng form trên trình duyệt từ 2 API công khai (không cần đăng nhập):
//   - eform/find-by-id/<id>: HTML bố cục (ô = <span class="mention" type="x-…" name="…">) + metadata
//     từng ô (loại, bắt buộc, nguồn option, ô con của x-select-area, điều kiện hiện khối);
//   - api/call-api {eformId, apiId, dependency}: danh sách option của một ô (proxy sang danh mục).
// Metadata của cổng kèm URL + header đăng nhập của API nội bộ → CHỈ giữ các khoá mô phỏng cần,
// không chép controlApiDTO/apiGetData/apiSubmitData/valueForm ra file.
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const BASE = "https://tokhaidientu.moj.gov.vn";
// Tường lửa của cổng trả 500 cho user-agent headless/không phải trình duyệt.
const UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36";
const OUT_DIR = join(dirname(fileURLToPath(import.meta.url)), "..", "src", "simulations", "mau-eform");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function api(path, body) {
  for (let attempt = 1; ; attempt++) {
    try {
      const res = await fetch(BASE + path, {
        method: body ? "POST" : "GET",
        headers: { "User-Agent": UA, "Content-Type": "application/json", Accept: "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      if (json.code !== 200) throw new Error(`code ${json.code}: ${json.message}`);
      await sleep(150); // gọi tuần tự, giãn nhịp: đây là cổng của cơ quan nhà nước
      return json.result;
    } catch (e) {
      if (attempt >= 3) throw new Error(`${path} ${JSON.stringify(body ?? "")}: ${e.message}`);
      await sleep(1000 * attempt);
    }
  }
}

async function resolveId(arg) {
  if (/^\d+$/.test(arg)) return Number(arg);
  const url = new URL(arg, BASE);
  const found = await api("/api/eform-service/eform/getDataEform", { Uri: `${BASE}${url.pathname}` });
  if (!found?.id) throw new Error(`Không tra được mẫu của ${arg}`);
  return found.id;
}

const LISTS_FILE = () => join(OUT_DIR, "_danh-muc.json");

function saveLists(fresh) {
  const old = existsSync(LISTS_FILE()) ? JSON.parse(readFileSync(LISTS_FILE(), "utf8")) : {};
  const all = { ...old, ...fresh };
  const used = new Set();
  for (const name of readdirSync(OUT_DIR)) {
    if (!/^\d+\.json$/.test(name)) continue;
    const form = JSON.parse(readFileSync(join(OUT_DIR, name), "utf8"));
    for (const f of Object.values(form.fields)) {
      if (f.list) used.add(f.list);
      for (const key of Object.values(f.byParent ?? {})) used.add(key);
    }
  }
  const kept = Object.fromEntries([...used].sort().filter((k) => all[k]).map((k) => [k, all[k]]));
  writeFileSync(LISTS_FILE(), JSON.stringify(kept));
}

const text = (v) => (v == null ? "" : String(v).replace(/\s+/g, " ").trim());

async function snapshot(id) {
  const tpl = await api(`/api/eform-service/eform/find-by-id/${id}`);
  const meta = tpl.metadata || [];
  const byName = new Map(meta.filter((m) => m.fieldName).map((m) => [m.fieldName, m]));

  // Danh sách option gộp theo nội dung: nhiều ô dùng chung một danh mục (quốc tịch, xã theo tỉnh…).
  const pool = {};
  const put = (rows) => {
    const key = createHash("sha1").update(JSON.stringify(rows)).digest("hex").slice(0, 10);
    pool[key] = rows;
    return key;
  };
  // Cùng URL danh mục + cùng tham số → cùng kết quả, dù apiId của mỗi ô khác nhau.
  const fetched = new Map();
  const loadList = async (m, dependency) => {
    const c = m.controlApiDTO || {};
    const cacheKey = `${c.url}|${JSON.stringify(dependency ?? {})}`;
    if (!fetched.has(cacheKey)) {
      const body = { eformId: id, apiId: c.id, ...(dependency ? { dependency } : {}) };
      const rows = (await api("/api/eform-service/api/call-api", body)) || [];
      fetched.set(cacheKey, put(rows.map((r) => [text(r[m.keyValue]), text(r[m.keyLabel])]).filter(([, l]) => l)));
    }
    return fetched.get(cacheKey);
  };

  const fields = {};
  const dependents = [];
  for (const m of meta) {
    if (!m.fieldName || m.active === false) continue;
    const f = { type: m.typeControl, required: !!m.require };
    if (m.disabled) f.disabled = true;
    if (m.typeControl === "x-radio") {
      f.options = (m.fields || []).filter((o) => o.fieldName).map((o) => [text(o.fieldName), text(o.description)]);
    }
    if (m.typeControl === "x-select-area") {
      f.parts = (m.fields || []).map((p) => (p.fieldName
        ? { name: p.fieldName, label: text(p.description), required: !!p.require, br: !!p.downLine }
        : { br: true }));
    }
    const dep = m.dependency && Object.entries(m.dependency);
    if (m.controlApiDTO?.id) {
      if (dep && dep.length) dependents.push([m, f, dep]);
      else f.list = await loadList(m);
    }
    const show = (m.configShowSelectArea || [])
      .map((c) => ({ values: (c.values || []).map(String), areas: (c.configs || []).map((x) => x.selectArea).filter(Boolean) }))
      .filter((c) => c.values.length && c.areas.length);
    if (show.length) f.show = show;
    fields[m.fieldName] = f;
  }

  // Danh sách phụ thuộc (xã theo tỉnh…): tải theo TỪNG giá trị của ô cha.
  for (const [m, f, dep] of dependents) {
    if (dep.length !== 1) { f.list = null; f.note = "danh sách phụ thuộc nhiều ô — chưa hỗ trợ"; continue; }
    const [parentName, param] = dep[0];
    const parent = fields[parentName];
    const parentRows = parent?.list ? pool[parent.list] : null;
    if (!parentRows) { f.note = `phụ thuộc ${parentName} nhưng ô cha không có danh sách`; continue; }
    f.dependsOn = parentName;
    f.byParent = {};
    for (const [value] of parentRows) f.byParent[value] = await loadList(m, { [param]: value });
    process.stdout.write(".");
  }

  const out = {
    id: tpl.id,
    name: text(tpl.name),
    path: tpl.url,
    fetchedAt: new Date().toISOString(),
    html: tpl.html,
    fields,
  };
  mkdirSync(OUT_DIR, { recursive: true });
  const file = join(OUT_DIR, `${tpl.id}.json`);
  writeFileSync(file, JSON.stringify(out));
  saveLists(pool);
  const ward = Object.values(fields).find((f) => f.dependsOn && f.byParent && fields[f.dependsOn]?.list);
  if (ward) {
    writeFileSync(join(OUT_DIR, "_dia-gioi.json"), JSON.stringify({
      provinces: fields[ward.dependsOn].list, wards: ward.byParent, from: `${tpl.id}:${ward.dependsOn}`,
    }));
  }
  const unused = [...byName.keys()].filter((n) => !tpl.html.includes(`name="${n}"`));
  console.log(`\n${tpl.id} "${out.name}": ${Object.keys(fields).length} ô, ${Object.keys(pool).length} danh sách → ${file}`);
  if (unused.length) console.log(`  ô không có trong HTML (ô con của khối): ${unused.length}`);
}

const args = process.argv.slice(2);
if (!args.length) {
  console.error("Cách dùng: node scripts/snapshot-eform.mjs <id | url-e-form> [...]");
  process.exit(1);
}
for (const arg of args) await snapshot(await resolveId(arg));
