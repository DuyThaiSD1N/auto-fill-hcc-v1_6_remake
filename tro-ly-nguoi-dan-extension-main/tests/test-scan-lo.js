// Test lib/scanLo.js — CUNG cac kich ban voi tests/test-batch-import.js ben autofill 1.17, de hai
// ban khong bao gio quyet dinh khac nhau tren cung mot thu muc quet.
// Chay: node tests/test-scan-lo.js
const fs = require("fs");
const vm = require("vm");
const path = require("path");
const GOC = path.resolve(__dirname, "..");
const SRC = path.join(GOC, "lib/scanLo.js");

const PHUT = 60 * 1000;
let so = 0, hong = 0;
function ok(ten, dk, chiTiet) {
  so++;
  if (!dk) { hong++; console.error("  FAIL:", ten, chiTiet !== undefined ? JSON.stringify(chiTiet) : ""); }
}
function chay(ten, fn) { try { fn(); } catch (e) { hong++; console.error("  LOI:", ten, e.message); } }

function moi() {
  const sandbox = { console: { info() {}, warn() {} } };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(SRC, "utf8"), sandbox);
  return sandbox.TLNDScanLo;
}
const NOW = Date.UTC(2026, 8, 13, 3, 0, 0);
function dsPhut(dsPhutTruoc) {
  return { folder: "/scan", files: dsPhutTruoc.map((p, i) => ({
    rel: `f${i}.pdf`, name: `f${i}.pdf`, mtime: new Date(NOW - p * PHUT).toISOString(),
  })) };
}
const L = moi();
const qd = (o) => L.quyetDinh({ now: NOW, ...o });

chay("lo vua quet -> TU TAI", () => {
  const kq = qd({ trenDia: dsPhut([1, 2, 3]) });
  ok("hanh dong tu-them", kq.hanhDong === "tu-them", kq.hanhDong);
  ok("du 3 tep", kq.tuThem.length === 3);
});

chay("lo cu 3 NGAY -> KHONG tu tai, cung KHONG hien danh sach (qua 2 gio)", () => {
  const ngay = 3 * 24 * 60;
  const kq = qd({ trenDia: dsPhut([ngay, ngay + 1, ngay + 2]) });
  ok("khong lam gi", kq.hanhDong === "khong", kq.hanhDong);
  ok("khong tu tai", kq.tuThem.length === 0);
  ok("khong danh sach", kq.chonTay.length === 0);
});

chay("lo cu 45 phut -> khong tu tai nhung HIEN danh sach chon tay", () => {
  const kq = qd({ trenDia: dsPhut([45, 46]) });
  ok("chon-tay", kq.hanhDong === "chon-tay", kq.hanhDong);
  ok("2 dong", kq.chonTay.length === 2);
  ok("moi nhat len dau", kq.chonTay[0].rel === "f0.pdf");
});

chay("watermark chan tep cua cong dan truoc", () => {
  const kq = qd({ trenDia: dsPhut([10, 11]), watermarkMs: NOW - 5 * PHUT });
  ok("khong lam gi", kq.hanhDong === "khong");
  ok("nhat ky dem dung", kq.nhatKy.bi_watermark_chan === 2, kq.nhatKy);
});

chay("tep da co tren phien thi khong tai lai", () => {
  const kq = qd({ trenDia: dsPhut([1, 2]), daCo: new Set(["f0.pdf"]) });
  ok("chi tai tep con lai", kq.tuThem.length === 1 && kq.tuThem[0].rel === "f1.pdf", kq.tuThem);
});

chay("ranh gioi RO giua hai cong dan -> chi lay lo moi nhat", () => {
  const kq = qd({ trenDia: dsPhut([1, 2, 3, 60, 61]) });
  ok("tu-them", kq.hanhDong === "tu-them");
  ok("dung 3 tep moi", kq.tuThem.map((f) => f.rel).join() === "f0.pdf,f1.pdf,f2.pdf", kq.tuThem.map((f) => f.rel));
});

chay("tep dung mot minh: tep ke cach < 5 phut thi gop, >= 5 phut thi tach", () => {
  ok("[1,3] gop 2", qd({ trenDia: dsPhut([1, 3]) }).tuThem.length === 2);
  ok("[1,10] chi 1", qd({ trenDia: dsPhut([1, 10]) }).tuThem.length === 1);
});

chay("quet lien tuc qua 30 tep ma khong thay ranh gioi -> KHONG doan, cho chon tay", () => {
  const ds = Array.from({ length: 35 }, (_, i) => 1 + i * (10 / 60));  // cach nhau 10 giay
  const kq = qd({ trenDia: dsPhut(ds) });
  ok("chon-tay", kq.hanhDong === "chon-tay", kq.hanhDong);
  ok("cat con toi da", kq.chonTay.length === L.RECENT_LIST_MAX, kq.chonTay.length);
});

chay("thu muc rong / du lieu hong", () => {
  ok("rong", qd({ trenDia: { folder: "/scan", files: [] } }).hanhDong === "khong");
  ok("undefined", qd({ trenDia: undefined }).hanhDong === "khong");
  const kq = qd({ trenDia: { files: [{ rel: "x.pdf", mtime: "khong-phai-ngay" }, { name: "khong-rel" }] } });
  ok("mtime hong bi bo", kq.nhatKy.tren_dia === 0, kq.nhatKy);
});

console.log(`scanLo: ${so - hong}/${so} dat`);
process.exit(hong ? 1 : 0);
