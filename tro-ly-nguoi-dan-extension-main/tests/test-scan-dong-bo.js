// Test lib/scanDongBo.js — nap FILE THAT vao sandbox, dung lai dung cac chuoi event agent ban ra
// khi can bo chuyen/doi ten/ghi de file trong thu muc quet.
// Chay: node tests/test-scan-dong-bo.js
const fs = require("fs");
const vm = require("vm");
const path = require("path");
const GOC = path.resolve(__dirname, "..");
const SRC = path.join(GOC, "lib/scanDongBo.js");

let so = 0, hong = 0;
function ok(ten, dk, chiTiet) {
  so++;
  if (!dk) { hong++; console.error("  FAIL:", ten, chiTiet !== undefined ? JSON.stringify(chiTiet) : ""); }
}
function chay(ten, fn) { try { fn(); } catch (e) { hong++; console.error("  LOI:", ten, e.message); } }

function moi() {
  const sandbox = {};
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(SRC, "utf8"), sandbox);
  return sandbox.TLNDScanDongBo.tao();
}

// Mo phong mot luot tai: vé chot TRUOC, fid co SAU.
function taiXongNgay(d, rel, fid, hash) { return d.taiXong(d.batDauTai(rel), fid, hash); }

chay("them roi xoa: xoa dung fid", () => {
  const d = moi();
  ok("tai xong khong phai xoa gi", taiXongNgay(d, "a.pdf", "f1").length === 0);
  ok("xoa a.pdf tra f1", d.daXoa("a.pdf") === "f1");
  ok("so tep ve 0", d.soTep() === 0);
});

chay("chuyen vao thu muc con, CUNG luot quet (added truoc, removed sau)", () => {
  const d = moi();
  taiXongNgay(d, "a.pdf", "f1");
  const ve = d.batDauTai("con/a.pdf");            // added(con/a.pdf) bat dau tai
  const xoa = d.daXoa("a.pdf");                   // removed(a.pdf) toi trong luc dang tai
  ok("removed a.pdf xoa f1", xoa === "f1", xoa);
  const phaiXoa = d.taiXong(ve, "f2");            // con/a.pdf tai xong
  ok("ban moi KHONG bi xoa (khac rel)", phaiXoa.length === 0, phaiXoa);
  ok("con dung 1 tep", d.soTep() === 1);
  ok("removed con/a.pdf ve sau tra f2", d.daXoa("con/a.pdf") === "f2");
});

chay("chuyen vao thu muc con, KHAC luot (removed truoc, added sau)", () => {
  const d = moi();
  taiXongNgay(d, "a.pdf", "f1");
  ok("removed truoc xoa f1", d.daXoa("a.pdf") === "f1");
  ok("added sau khong phai xoa gi", taiXongNgay(d, "con/a.pdf", "f2").length === 0);
  ok("con dung 1 tep", d.soTep() === 1);
});

chay("xoa khoi dia GIUA luc dang tai cung rel -> xoa luon ban vua tai", () => {
  const d = moi();
  const ve = d.batDauTai("a.pdf");
  ok("chua co fid nao de xoa", d.daXoa("a.pdf") === null);
  const phaiXoa = d.taiXong(ve, "f1");
  ok("phai xoa ngay f1", phaiXoa.length === 1 && phaiXoa[0] === "f1", phaiXoa);
  ok("khong nho a.pdf", d.soTep() === 0);
});

chay("may quet GHI DE cung rel -> xoa ban cu, giu ban moi", () => {
  const d = moi();
  taiXongNgay(d, "a.pdf", "f1", "H1");
  const phaiXoa = taiXongNgay(d, "a.pdf", "f2", "H2");
  ok("xoa f1", phaiXoa.length === 1 && phaiXoa[0] === "f1", phaiXoa);
  ok("hash cap nhat sang H2", d.hashCua("a.pdf") === "H2");
  ok("a.pdf -> f2", d.daXoa("a.pdf") === "f2");
});

chay("rel la KHONG doan theo ten (tep trung ten cua cong dan)", () => {
  const d = moi();
  taiXongNgay(d, "con/giay.pdf", "f1");
  ok("removed giay.pdf (rel khac) khong xoa gi", d.daXoa("giay.pdf") === null);
  ok("con/giay.pdf van con", d.soTep() === 1);
});

chay("xoa roi dat LAI dung cho cu", () => {
  const d = moi();
  taiXongNgay(d, "a.pdf", "f1");
  d.daXoa("a.pdf");
  const phaiXoa = taiXongNgay(d, "a.pdf", "f2");   // ve chot SAU event xoa
  ok("ban dat lai khong bi xoa oan", phaiXoa.length === 0, phaiXoa);
  ok("a.pdf -> f2", d.daXoa("a.pdf") === "f2");
});

chay("bam X -> quenFid", () => {
  const d = moi();
  taiXongNgay(d, "a.pdf", "f1");
  d.quenFid("f1");
  ok("event xoa ve sau khong co gi de xoa", d.daXoa("a.pdf") === null);
});

chay("dat lai phien: luot tai cu con bay khong bi so sai", () => {
  const d = moi();
  d.daXoa("x.pdf");                  // seq = 1
  const ve = d.batDauTai("a.pdf");   // ve.seq = 1
  d.datLai();                        // sang cong dan moi
  ok("tai xong sau dat lai: khong xoa oan", d.taiXong(ve, "f9").length === 0);
});

chay("dau vao rong", () => {
  const d = moi();
  ok("taiXong khong ve", d.taiXong(null, "f1").length === 0);
  ok("taiXong khong fid", d.taiXong(d.batDauTai("a.pdf"), "").length === 0);
});

// ---- song qua lan dung lai iframe (luu/nap) ----
chay("xuat -> nap vao sidebar MOI: file.removed van tim ra fid", () => {
  const cu = moi();
  taiXongNgay(cu, "a.pdf", "f1", "H1");
  taiXongNgay(cu, "con/b.pdf", "f2", "H2");
  const banLuu = JSON.parse(JSON.stringify(cu.xuat()));   // qua chrome.storage la JSON
  const moiDung = moi();                                  // iframe dung lai sau dieu huong
  moiDung.nap(banLuu);
  ok("nap du 2 tep", moiDung.soTep() === 2);
  ok("hash giu nguyen", moiDung.hashCua("con/b.pdf") === "H2");
  ok("removed a.pdf sau dieu huong xoa dung f1", moiDung.daXoa("a.pdf") === "f1");
});

chay("nap la GOP: muc moi hon trong bo nho khong bi ban luu cu de len", () => {
  const d = moi();
  taiXongNgay(d, "a.pdf", "f-moi", "H-MOI");               // event toi truoc khi nap xong
  d.nap({ "a.pdf": { fid: "f-cu", hash: "H-CU" }, "b.pdf": { fid: "f-b", hash: "" } });
  ok("a.pdf van la ban moi", d.daXoa("a.pdf") === "f-moi");
  ok("b.pdf duoc nap them", d.daXoa("b.pdf") === "f-b");
});

chay("nap KHONG hoi sinh tep vua bi xoa", () => {
  const d = moi();
  d.daXoa("a.pdf");                                        // removed toi trong luc cho storage
  d.nap({ "a.pdf": { fid: "f1", hash: "H" } });
  ok("a.pdf khong quay lai", d.soTep() === 0);
});

chay("nap bo qua du lieu hong", () => {
  const d = moi();
  d.nap(null);
  d.nap("rac");
  d.nap({ "": { fid: "x" }, "a.pdf": null, "b.pdf": { fid: 5 }, "c.pdf": { hash: "H" } });
  ok("khong nap gi", d.soTep() === 0);
});

chay("doi ten do chinh minh: doiRel + timTheoFid", () => {
  const d = moi();
  taiXongNgay(d, "con/a.pdf", "f1", "H1");
  ok("tim theo fid ra rel + hash", JSON.stringify(d.timTheoFid("f1")) === JSON.stringify({ rel: "con/a.pdf", hash: "H1" }));
  ok("doi rel thanh cong", d.doiRel("con/a.pdf", "con/moi.pdf") === true);
  ok("rel cu khong con", d.daXoa("con/a.pdf") === null);
  ok("rel moi mang dung fid", d.daXoa("con/moi.pdf") === "f1");
  ok("doi rel khong ton tai tra false", d.doiRel("khong-co.pdf", "x.pdf") === false);
});

console.log(`scanDongBo: ${so - hong}/${so} dat`);
process.exit(hong ? 1 : 0);
