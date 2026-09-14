// Test quyet dinh TU PIN file quet: watermark, tran tuoi, va bo nho "da go thu cong".
// Trich THANG cac ham that tu popup.js — khong chep lai, de test khong bao gio lech.
const fs = require("fs");
const vm = require("vm");
const path = require("path");
// Goc thu muc extension — suy tu vi tri file test, khong ghim duong dan tuyet
// doi (thu muc da tung bi chuyen cho va lam gay het bo test).
const GOC = path.resolve(__dirname, "..");
const SRC = path.join(GOC, "popup.js");
const src = fs.readFileSync(SRC, "utf8");

function trichHam(ten) {
  const re = new RegExp("(?:async\\s+)?function\\s+" + ten + "\\s*\\(");
  const m = re.exec(src);
  if (!m) throw new Error("khong tim thay ham " + ten);
  // Tim "{" MO THAN HAM, khong phai "{" trong danh sach tham so
  // (importOneScanFile co tham so destructuring `{ tuDong = false } = {}`).
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
  throw new Error("khong dong ngoac cho " + ten);
}
function trichHang(ten) {
  const re = new RegExp("^const " + ten + " = .*$", "m");
  const m = re.exec(src);
  if (!m) throw new Error("khong tim thay hang " + ten);
  return m[0];
}

const PHUT = 60 * 1000;
let so = 0, hong = 0;
function ok(ten, dk) { so++; if (!dk) { hong++; console.error("  FAIL:", ten); } }
async function chay(ten, fn) { try { await fn(); } catch (e) { hong++; console.error("  LOI:", ten, e.message); } }

function dungMoiTruong({ watermark = 0, filesDangCo = [], luuTru = {} } = {}) {
  const vet = { themTuDong: [], danhSachChonTay: [], luu: [] };
  const sandbox = {
    console: { warn() {}, info() {}, error() {} },
    Date, Number, Set, Map, Array, JSON, Math, Promise, setTimeout,
    EMBEDDED_TAB_ID: null,
    files: filesDangCo,
    scanWatermarkMs: watermark,
    batchImportAttempted: false,
    scanRecentPending: [],
    RECENT_LIST_MAX: 8,
    renderFiles() {}, refreshAttachStepUI() {}, saveSession() {},
    renderScanRecentList() { vet.danhSachChonTay = sandbox.scanRecentPending.slice(); },
    scanAgentHelpers: null,
    // Phu thuoc cua importOneScanFile that (dung khi test chinh no):
    scanEventSeq: 0,
    scanRemovedAt: new Map(),
    scanNewestMs: 0,
    async readAsDataUrl() { return "data:application/pdf;base64,AAA"; },
    async sha256Hex(blob) { return (blob && blob.hash) || "HASH-MAC-DINH"; },
    defaultRoleFor() { return "doc"; },
    async importOneScanFileGia(evt, fetchBlob, opts) {
      vet.themTuDong.push({ rel: evt.rel, tuDong: !!(opts && opts.tuDong) });
      return true;
    },
    chrome: {
      storage: { local: {
        async get(k) { return k in luuTru ? { [k]: luuTru[k] } : {}; },
        async set(o) { Object.assign(luuTru, o); vet.luu.push(o); },
      } },
    },
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext([
    trichHang("BATCH_GAP_RATIO"), trichHang("BATCH_GAP_FLOOR_MS"),
    trichHang("BATCH_SINGLE_FLOOR_MS"), trichHang("BATCH_MAX_FILES"),
    trichHang("BATCH_MAX_SPAN_MS"), trichHang("RECENT_LIST_WINDOW_MS"),
    trichHang("BATCH_AUTO_MAX_AGE_MS"),
    trichHang("SCAN_DA_GO_KEY"), trichHang("SCAN_DA_GO_MAX"), trichHang("SCAN_DA_GO_TTL_MS"),
    "var scanDaGo = new Map();",  // var, khong phai let: can no nam tren global cua sandbox de test doc duoc
    trichHam("phanTichBatchGanNhat"), trichHam("attemptBatchImport"),
    trichHam("importOneScanFile"),
    trichHam("restoreScanDaGo"), trichHam("luuScanDaGo"), trichHam("ghiNhanDaGo"),
  ].join("\n\n"), sandbox);
  // Cac test ve attemptBatchImport dung ban GIA de chi do quyet dinh; cac test
  // ve chinh importOneScanFile thi goi ban THAT (da trich o tren).
  const that = sandbox.importOneScanFile;
  sandbox.importOneScanFileThat = that;
  sandbox.importOneScanFile = sandbox.importOneScanFileGia;
  return { sandbox, vet, luuTru, doc: (bieuThuc) => vm.runInContext(bieuThuc, sandbox) };
}

function dungFileList(dsPhutTruoc) {
  const now = Date.now();
  return { folder: "/scan", files: dsPhutTruoc.map((p, i) => ({
    rel: `f${i}.pdf`, name: `f${i}.pdf`, mtime: new Date(now - p * PHUT).toISOString(),
  })) };
}

(async () => {
  await chay("lo vua quet -> TU PIN", async () => {
    const { sandbox, vet } = dungMoiTruong();
    sandbox.scanAgentHelpers = { listFiles: async () => dungFileList([1, 2, 3]), fetchBlob: async () => null };
    await sandbox.attemptBatchImport();
    ok("da tu pin 3 file", vet.themTuDong.length === 3);
    ok("truyen co tuDong", vet.themTuDong.every((x) => x.tuDong === true));
  });

  await chay("lo cu 3 NGAY -> KHONG tu pin", async () => {
    const { sandbox, vet } = dungMoiTruong();
    const ngay = 3 * 24 * 60;
    sandbox.scanAgentHelpers = { listFiles: async () => dungFileList([ngay, ngay + 1, ngay + 2]), fetchBlob: async () => null };
    await sandbox.attemptBatchImport();
    ok("khong pin file nao", vet.themTuDong.length === 0);
    ok("cung khong hien danh sach (qua 2 gio)", vet.danhSachChonTay.length === 0);
  });

  await chay("lo cu 45 phut -> khong tu pin nhung HIEN danh sach chon tay", async () => {
    const { sandbox, vet } = dungMoiTruong();
    sandbox.scanAgentHelpers = { listFiles: async () => dungFileList([45, 46]), fetchBlob: async () => null };
    await sandbox.attemptBatchImport();
    ok("khong tu pin", vet.themTuDong.length === 0);
    ok("co hien de can bo chon", vet.danhSachChonTay.length === 2);
  });

  await chay("watermark van chan file cua cong dan truoc", async () => {
    const now = Date.now();
    const { sandbox, vet } = dungMoiTruong({ watermark: now - 5 * PHUT });
    sandbox.scanAgentHelpers = { listFiles: async () => dungFileList([10, 11]), fetchBlob: async () => null };
    await sandbox.attemptBatchImport();
    ok("khong pin gi", vet.themTuDong.length === 0);
  });

  await chay("file da co trong files[] thi khong pin lai", async () => {
    const { sandbox, vet } = dungMoiTruong({ filesDangCo: [{ fromScan: true, rel: "f0.pdf" }] });
    sandbox.scanAgentHelpers = { listFiles: async () => dungFileList([1, 2]), fetchBlob: async () => null };
    await sandbox.attemptBatchImport();
    ok("chi pin file con lai", vet.themTuDong.length === 1 && vet.themTuDong[0].rel === "f1.pdf");
  });

  // ---- bo nho "da go thu cong" ----
  await chay("ghiNhanDaGo luu theo hash va doc lai duoc", async () => {
    const { sandbox, luuTru } = dungMoiTruong();
    sandbox.ghiNhanDaGo({ fromScan: true, rel: "a.pdf", hash: "HASH1" });
    ok("da ghi vao storage", Object.keys(luuTru).length === 1);
    const moi = dungMoiTruong({ luuTru });
    await moi.sandbox.restoreScanDaGo();
    ok("doc lai thay hash", moi.doc('scanDaGo.has("HASH1")'));
  });

  await chay("file keo-tha (khong phai tu may quet) thi khong ghi nhan", async () => {
    const { sandbox, luuTru } = dungMoiTruong();
    sandbox.ghiNhanDaGo({ fromScan: false, hash: "HASH2" });
    sandbox.ghiNhanDaGo({ fromScan: true });           // thieu hash
    ok("khong ghi gi", Object.keys(luuTru).length === 0);
  });

  await chay("ban ghi qua han TTL bi bo khi doc lai", async () => {
    const cu = Date.now() - 25 * 60 * 60 * 1000;
    const luuTru = { "autofill_scan_da_go_popup": [
      { hash: "CU", rel: "x.pdf", luc: cu },
      { hash: "MOI", rel: "y.pdf", luc: Date.now() },
    ] };
    const { sandbox, doc } = dungMoiTruong({ luuTru });
    await sandbox.restoreScanDaGo();
    ok("bo ban ghi qua han", !doc('scanDaGo.has("CU")'));
    ok("giu ban ghi con han", doc('scanDaGo.has("MOI")'));
  });

  await chay("khong phinh vo han - cat con SCAN_DA_GO_MAX", async () => {
    const { sandbox, doc } = dungMoiTruong();
    for (let i = 0; i < 260; i++) sandbox.ghiNhanDaGo({ fromScan: true, rel: `f${i}`, hash: `H${i}` });
    ok("cat con dung tran", doc("scanDaGo.size") === doc("SCAN_DA_GO_MAX"));
  });

  // ---- chot chan that trong importOneScanFile ----
  await chay("da go thu cong -> duong TU DONG khong them lai", async () => {
    const { sandbox, doc } = dungMoiTruong();
    sandbox.ghiNhanDaGo({ fromScan: true, rel: "a.pdf", hash: "H-DA-GO" });
    const blob = { hash: "H-DA-GO", type: "application/pdf" };
    const kq = await sandbox.importOneScanFileThat(
      { rel: "a.pdf", mtimeMs: Date.now() }, async () => blob, { tuDong: true });
    ok("tra ve false", kq === false);
    ok("khong day vao files[]", sandbox.files.length === 0);
    ok("van con dau da go", doc('scanDaGo.has("H-DA-GO")'));
  });

  await chay("can bo CHU DONG them lai -> duoc, va dau bi go", async () => {
    const { sandbox, doc } = dungMoiTruong();
    sandbox.ghiNhanDaGo({ fromScan: true, rel: "a.pdf", hash: "H-DA-GO" });
    const blob = { hash: "H-DA-GO", type: "application/pdf" };
    const kq = await sandbox.importOneScanFileThat(
      { rel: "a.pdf", mtimeMs: Date.now() }, async () => blob); // khong co tuDong
    ok("them duoc", kq === true && sandbox.files.length === 1);
    ok("dau da go bi xoa", !doc('scanDaGo.has("H-DA-GO")'));
  });

  await chay("quet DE len dung ten cu ra NOI DUNG KHAC -> van duoc tu them", async () => {
    const { sandbox } = dungMoiTruong();
    sandbox.ghiNhanDaGo({ fromScan: true, rel: "a.pdf", hash: "H-CU" });
    const blob = { hash: "H-MOI", type: "application/pdf" };
    const kq = await sandbox.importOneScanFileThat(
      { rel: "a.pdf", mtimeMs: Date.now() }, async () => blob, { tuDong: true });
    ok("noi dung moi thi khong bi chan", kq === true && sandbox.files.length === 1);
  });

  // ---- chot chan TUOI nam trong importOneScanFile (khong o noi goi) ----
  await chay("tu dong + file qua cu -> tu choi, va KHONG tai blob", async () => {
    const { sandbox } = dungMoiTruong();
    let daTai = false;
    const cu = Date.now() - 3 * 24 * 60 * 60 * 1000;
    const kq = await sandbox.importOneScanFileThat(
      { rel: "cu.pdf", mtimeMs: cu },
      async () => { daTai = true; return { hash: "H", type: "application/pdf" }; },
      { tuDong: true });
    ok("tra ve false", kq === false);
    ok("khong day vao files[]", sandbox.files.length === 0);
    ok("khong ton bang thong tai file cu", daTai === false);
  });

  await chay("tu dong + file vua quet -> nhan binh thuong", async () => {
    const { sandbox } = dungMoiTruong();
    const kq = await sandbox.importOneScanFileThat(
      { rel: "moi.pdf", mtimeMs: Date.now() - 60 * 1000 },
      async () => ({ hash: "H", type: "application/pdf" }),
      { tuDong: true });
    ok("nhan", kq === true && sandbox.files.length === 1);
  });

  await chay("duong SSE (khong co mtimeMs) -> KHONG bi tran tuoi chan", async () => {
    // Event file.added nghia la "vua xuat hien NGAY BAY GIO" — chinh su kien la
    // bang chung moi. Siet no theo mtime se chan nham file cu duoc chep vao.
    const { sandbox } = dungMoiTruong();
    const kq = await sandbox.importOneScanFileThat(
      { rel: "sse.pdf", at: new Date().toISOString() },
      async () => ({ hash: "H", type: "application/pdf" }),
      { tuDong: true });
    ok("van nhan", kq === true && sandbox.files.length === 1);
  });

  await chay("can bo bam them TAY file cu -> van duoc", async () => {
    const { sandbox } = dungMoiTruong();
    const cu = Date.now() - 30 * 24 * 60 * 60 * 1000;
    const kq = await sandbox.importOneScanFileThat(
      { rel: "cu.pdf", mtimeMs: cu },
      async () => ({ hash: "H", type: "application/pdf" }));   // khong co tuDong
    ok("nhan vi la quyet dinh cua can bo", kq === true && sandbox.files.length === 1);
  });

  console.log(`\n${so} phep kiem, ${hong} hong`);
  process.exit(hong ? 1 : 0);
})();
