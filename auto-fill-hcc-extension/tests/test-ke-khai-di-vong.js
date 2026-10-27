// Test "đi vòng" cho thủ tục cổng tỉnh chưa liên thông DVC quốc gia:
//   - popup-ke-khai-di-vong.js: link ĐÍCH (1.014632) mượn trang DVC + cờ chọn cơ quan của thủ tục CẦU
//     (1.014589, đã liên thông) và mang theo chỉ dẫn đổi mã;
//   - content/portal-doi-ma-tthc.js: tới eform cổng Bắc Ninh với mã cầu thì đổi sang mã đích, CHỈ khi
//     cờ "Đi đến thủ tục" yêu cầu (người thật sự làm thủ tục cầu không bị đổi nhầm).
const assert = require("node:assert/strict");
const fs = require("fs");
const vm = require("vm");
const path = require("path");
const GOC = path.resolve(__dirname, "..");

let so = 0, hong = 0;
function ok(ten, fn) {
  so++;
  try { fn(); } catch (e) { hong++; console.error("  FAIL:", ten, "-", e.message); }
}

function trichHam(src, ten) {
  const re = new RegExp("(?:async\\s+)?function\\s+" + ten + "\\s*\\(");
  const m = re.exec(src);
  if (!m) throw new Error("khong tim thay " + ten);
  let j = src.indexOf("(", m.index), ngoac = 0;
  for (; j < src.length; j++) {
    if (src[j] === "(") ngoac++;
    else if (src[j] === ")") { ngoac--; if (ngoac === 0) break; }
  }
  let i = src.indexOf("{", j), sau = 0;
  for (let k = i; k < src.length; k++) {
    if (src[k] === "{") sau++;
    else if (src[k] === "}") { sau--; if (sau === 0) return src.slice(m.index, k + 1); }
  }
  throw new Error("khong dong ngoac " + ten);
}

const THAM_SO = "_org_bn_hoso_noptructuyen_maThuTucHanhChinh";
const HOST = "dichvucong.bacninh.gov.vn";
const CAU = {
  key: "ho-tro-nguoi-cao-tuoi-dang-vien-40-nam-tuoi-dang",
  code: "1.014589",
  label: "[Bắc Ninh] Thủ tục Hỗ trợ cho Người cao tuổi",
  url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d7c4f-0f4f-756f-a7db-e8f96edb8171",
  needsAgencySelect: true,
  autoConfirm: true,
};
const DICH = {
  key: "dang-ky-nha-o-xa-hoi-bac-ninh",
  code: "1.014632",
  label: "[Tỉnh Bắc Ninh] Đăng ký mua, thuê mua, thuê nhà ở xã hội",
  url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfe-985c-732b-822b-460f2199467e",
  needsAgencySelect: false,
  autoConfirm: false,
};
const KHAC = { key: "khai-sinh-dang-ky", code: "2.000987", label: "Khai sinh", url: "https://lienthong.dichvucong.gov.vn/#/ke-khai/2.000987" };

// ---------- popup-ke-khai-di-vong.js ----------
let DiVong = null;
ok("nap duoc popup-ke-khai-di-vong.js", () => {
  DiVong = require(path.join(GOC, "popup-ke-khai-di-vong.js"));
  assert.equal(typeof DiVong.apDungDiVong, "function");
});

ok("quy tac mac dinh: 1.014589 -> 1.014632 tren cong Bac Ninh", () => {
  const q = DiVong.QUY_TAC.find((x) => x.dich === "1.014632");
  assert.ok(q, "thieu quy tac cho 1.014632");
  assert.equal(q.cau, "1.014589");
  assert.equal(q.host, HOST);
  assert.equal(q.thamSo, THAM_SO);
});

ok("link dich muon trang DVC + co chon co quan cua thu tuc cau, giu ten/ma/key cua minh", () => {
  const vao = [KHAC, CAU, DICH];
  const banSao = JSON.parse(JSON.stringify(vao));
  const ra = DiVong.apDungDiVong(vao);
  const dich = ra.find((l) => l.code === "1.014632");
  assert.equal(dich.key, DICH.key);
  assert.equal(dich.label, DICH.label);
  assert.equal(dich.url, CAU.url);
  assert.equal(dich.cauLabel, CAU.label);
  assert.equal(dich.needsAgencySelect, true);
  assert.equal(dich.autoConfirm, true);
  assert.deepEqual(dich.doiMaThuTuc, { host: HOST, thamSo: THAM_SO, tu: "1.014589", sang: "1.014632" });
  assert.deepEqual(ra.find((l) => l.code === "1.014589"), CAU, "thu tuc cau phai giu nguyen");
  assert.deepEqual(ra.find((l) => l.code === "2.000987"), KHAC, "link khac phai giu nguyen");
  assert.deepEqual(vao, banSao, "khong duoc sua mang dau vao");
});

ok("danh muc thieu thu tuc cau: link dich giu nguyen, khong gan doiMaThuTuc", () => {
  const ra = DiVong.apDungDiVong([KHAC, DICH]);
  assert.deepEqual(ra.find((l) => l.code === "1.014632"), DICH);
});

ok("dau vao khong phai mang -> mang rong", () => {
  assert.deepEqual(DiVong.apDungDiVong(undefined), []);
  assert.deepEqual(DiVong.apDungDiVong(null), []);
});

// ---------- content/portal-doi-ma-tthc.js ----------
const ENGINE = path.join(GOC, "content", "portal-doi-ma-tthc.js");
let urlSauDoiMa = null, viecCanLam = null;
ok("trich duoc ham tu engine", () => {
  const src = fs.readFileSync(ENGINE, "utf8");
  const sandbox = { URL };
  vm.createContext(sandbox);
  vm.runInContext(trichHam(src, "urlSauDoiMa") + "\n" + trichHam(src, "viecCanLam") +
    "\nglobalThis.urlSauDoiMa = urlSauDoiMa; globalThis.viecCanLam = viecCanLam;", sandbox);
  urlSauDoiMa = sandbox.urlSauDoiMa;
  viecCanLam = sandbox.viecCanLam;
});

const FLOW = { host: HOST, thamSo: THAM_SO, tu: "1.014589", sang: "1.014632" };
const eform = (ma) => `https://${HOST}/web/guest/eform?p_p_id=org_bn_hoso_noptructuyen&p_p_lifecycle=0&p_p_state=normal`
  + `&_org_bn_hoso_noptructuyen_mvcRenderCommandName=nopHoSonopTrucTuyen&${THAM_SO}=${ma}`;

ok("urlSauDoiMa: ma cau -> ma dich, giu nguyen tham so khac", () => {
  const moi = new URL(urlSauDoiMa(eform("1.014589"), FLOW));
  assert.equal(moi.searchParams.get(THAM_SO), "1.014632");
  assert.equal(moi.searchParams.get("p_p_id"), "org_bn_hoso_noptructuyen");
  assert.equal(moi.searchParams.get("_org_bn_hoso_noptructuyen_mvcRenderCommandName"), "nopHoSonopTrucTuyen");
  assert.equal(moi.hostname, HOST);
  assert.equal(moi.pathname, "/web/guest/eform");
});
ok("urlSauDoiMa: da o ma dich -> null", () => assert.equal(urlSauDoiMa(eform("1.014632"), FLOW), null));
ok("urlSauDoiMa: ma khac -> null", () => assert.equal(urlSauDoiMa(eform("1.014582"), FLOW), null));
ok("urlSauDoiMa: host khac -> null", () => {
  assert.equal(urlSauDoiMa(eform("1.014589").replace(HOST, "dichvucong.lamdong.gov.vn"), FLOW), null);
});
ok("urlSauDoiMa: url hong / flow thieu -> null", () => {
  assert.equal(urlSauDoiMa("khong-phai-url", FLOW), null);
  assert.equal(urlSauDoiMa(eform("1.014589"), null), null);
});

const TTL = 30 * 60 * 1000;
const BAY_GIO = 1_000_000_000_000;
const coDiVong = (them = {}) => ({ procedureKey: DICH.key, doiMaThuTuc: FLOW, at: BAY_GIO - 60_000, ...them });

ok("viecCanLam: khong co co -> null", () => assert.equal(viecCanLam(null, eform("1.014589"), BAY_GIO, TTL), null));
ok("viecCanLam: co cua thu tuc khac (khong doiMaThuTuc) -> null", () => {
  assert.equal(viecCanLam({ procedureKey: CAU.key, at: BAY_GIO }, eform("1.014589"), BAY_GIO, TTL), null);
});
ok("viecCanLam: host khac -> null", () => {
  assert.equal(viecCanLam(coDiVong(), "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/x", BAY_GIO, TTL), null);
});
ok("viecCanLam: dang o ma cau -> doi sang url ma dich", () => {
  const v = viecCanLam(coDiVong(), eform("1.014589"), BAY_GIO, TTL);
  assert.equal(v.viec, "doi");
  assert.equal(new URL(v.url).searchParams.get(THAM_SO), "1.014632");
});
ok("viecCanLam: da o ma dich -> xong (don co)", () => {
  assert.deepEqual(JSON.parse(JSON.stringify(viecCanLam(coDiVong(), eform("1.014632"), BAY_GIO, TTL))), { viec: "xong" });
});
ok("viecCanLam: co qua han -> het-han", () => {
  assert.equal(viecCanLam(coDiVong({ at: BAY_GIO - TTL - 1 }), eform("1.014589"), BAY_GIO, TTL).viec, "het-han");
});
ok("viecCanLam: da doi 2 lan ma cong van ve ma cau -> bo-cuoc (khong lap vo han)", () => {
  assert.equal(viecCanLam(coDiVong({ doiMaLanThu: 2 }), eform("1.014589"), BAY_GIO, TTL).viec, "bo-cuoc");
  assert.equal(viecCanLam(coDiVong({ doiMaLanThu: 1 }), eform("1.014589"), BAY_GIO, TTL).viec, "doi");
});
ok("viecCanLam: trang khac tren dung host (chua toi eform ma cau) -> null", () => {
  assert.equal(viecCanLam(coDiVong(), `https://${HOST}/web/guest/trang-chu`, BAY_GIO, TTL), null);
});

// ---------- noi day ----------
ok("popup.html nap popup-ke-khai-di-vong.js TRUOC popup.js", () => {
  const html = fs.readFileSync(path.join(GOC, "popup.html"), "utf8");
  const a = html.indexOf('<script src="popup-ke-khai-di-vong.js"></script>');
  const b = html.indexOf('<script src="popup.js"></script>');
  assert.ok(a >= 0, "chua nap popup-ke-khai-di-vong.js");
  assert.ok(a < b, "phai nap truoc popup.js");
});
ok("popup.js ap quy tac khi nap danh muc + dua doiMaThuTuc vao co", () => {
  const js = fs.readFileSync(path.join(GOC, "popup.js"), "utf8");
  // assert.ok thay vì assert.match: match in cả file popup.js (hàng trăm KB) ra khi hỏng.
  assert.ok(/KeKhaiDiVong\.apDungDiVong\(/.test(js), "chua ap KeKhaiDiVong.apDungDiVong khi nap danh muc");
  assert.ok(/doiMaThuTuc: link\.doiMaThuTuc \|\| null/.test(js), "co Di den thu tuc chua mang doiMaThuTuc");
  assert.ok(/procedureLabel: link\.cauLabel \|\| link\.label/.test(js), "chua do the theo ten thu tuc cau");
});
ok("manifest: engine doi ma chay tren cong Bac Ninh, sau portal-quangninh.js", () => {
  const m = JSON.parse(fs.readFileSync(path.join(GOC, "manifest.json"), "utf8"));
  const cs = m.content_scripts.find((c) => (c.js || []).includes("content/portal-doi-ma-tthc.js"));
  assert.ok(cs, "chua khai content/portal-doi-ma-tthc.js");
  assert.ok(cs.matches.includes("https://dichvucong.bacninh.gov.vn/*"));
  assert.ok(cs.js.indexOf("content/portal-doi-ma-tthc.js") > cs.js.indexOf("content/portal-quangninh.js"));
});

console.log(`test-ke-khai-di-vong: ${so - hong}/${so} dat`);
process.exit(hong ? 1 : 0);
