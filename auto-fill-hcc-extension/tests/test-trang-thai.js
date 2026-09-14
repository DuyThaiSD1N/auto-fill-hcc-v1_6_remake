// Test may trang thai cua lib/trangThai.js — nap FILE THAT vao mot DOM gia,
// dieu khien dong ho de kiem cac nguong thoi gian.
const fs = require("fs");
const vm = require("vm");
const path = require("path");
// Goc thu muc extension — suy tu vi tri file test, khong ghim duong dan tuyet
// doi (thu muc da tung bi chuyen cho va lam gay het bo test).
const GOC = path.resolve(__dirname, "..");
const SRC = path.join(GOC, "lib/trangThai.js");

let so = 0, hong = 0;
function ok(ten, dk) { so++; if (!dk) { hong++; console.error("  FAIL:", ten); } }
function chay(ten, fn) { try { fn(); } catch (e) { hong++; console.error("  LOI:", ten, e.message); } }

function dungMoiTruong() {
  let gio = 1_000_000;
  const listeners = { document: {}, window: {} };
  const doc = {
    visibilityState: "visible",
    activeElement: null,
    hasFocus: () => doc._focus,
    _focus: true,
    addEventListener(ev, cb) { (listeners.document[ev] ||= []).push(cb); },
  };
  const win = {
    addEventListener(ev, cb) { (listeners.window[ev] ||= []).push(cb); },
    fetch: null,
  };
  const FakeDate = { now: () => gio };
  const sandbox = {
    window: win, document: doc, Date: FakeDate, Promise, Math, Number, Set, Map,
    console: { warn() {}, info() {}, error() {} },
    setInterval: () => 0,
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(SRC, "utf8"), sandbox);
  const TT = win.HccTrangThai;
  return {
    TT, doc, win, listeners,
    tien: (ms) => { gio += ms; },
    gio: () => gio,
    banNgoai(f) { TT.batDau({ layCoBanNgoai: f }); },
  };
}

(() => {
  chay("mac dinh: vua nap -> dang lam viec", () => {
    const { TT } = dungMoiTruong();
    ok("dang-lam-viec", TT.hienTai() === "dang-lam-viec");
  });

  chay("im lang qua nguong -> mo nhung khong lam viec", () => {
    const e = dungMoiTruong();
    e.tien(e.TT.NGUONG_HOAT_DONG_MS + 1000);
    ok("mo-khong-lam-viec", e.TT.hienTai() === "mo-khong-lam-viec");
  });

  chay("tab bi an -> chay nen NGAY, khong doi nguong", () => {
    const e = dungMoiTruong();
    e.doc.visibilityState = "hidden";
    ok("chay-nen", e.TT.hienTai() === "chay-nen");
  });

  chay("mat focus CHUA du lau -> chua phai chay nen", () => {
    const e = dungMoiTruong();
    e.doc._focus = false;
    e.TT.hienTai();                 // luot nay ghi moc bat dau mat focus
    e.tien(e.TT.NGUONG_NEN_MS - 2000);
    ok("van chua chay-nen", e.TT.hienTai() !== "chay-nen");
  });

  chay("mat focus du lau -> chay nen", () => {
    const e = dungMoiTruong();
    e.doc._focus = false;
    e.TT.hienTai();
    e.tien(e.TT.NGUONG_NEN_MS + 1000);
    ok("chay-nen", e.TT.hienTai() === "chay-nen");
  });

  chay("con tro trong o nhap -> dang lam viec du im lang rat lau", () => {
    const e = dungMoiTruong();
    e.doc.activeElement = { tagName: "INPUT" };
    e.tien(10 * 60 * 1000);
    ok("dang-lam-viec", e.TT.hienTai() === "dang-lam-viec");
  });

  chay("co ban NGOAI (dang dinh kem) -> dang lam viec du im lang", () => {
    const e = dungMoiTruong();
    let ban = true;
    e.banNgoai(() => ban);
    e.tien(10 * 60 * 1000);
    ok("bi khoa boi co ngoai", e.TT.hienTai() === "dang-lam-viec");
    ban = false;
    ok("nha co ra thi ranh", e.TT.hienTai() === "mo-khong-lam-viec");
  });

  chay("layCoBanNgoai nem loi -> coi nhu BAN (an toan)", () => {
    const e = dungMoiTruong();
    e.banNgoai(() => { throw new Error("hong"); });
    e.tien(10 * 60 * 1000);
    ok("dang-lam-viec", e.TT.hienTai() === "dang-lam-viec");
  });

  chay("request dang chay -> dang lam viec, ke ca khi tab an", () => {
    const e = dungMoiTruong();
    e.TT.batDau({});
    e.TT.moViec();
    e.doc.visibilityState = "hidden";
    ok("request thang tab-an", e.TT.hienTai() === "dang-lam-viec");
    e.TT.dongViec();
    ok("xong request thi ve chay-nen", e.TT.hienTai() === "chay-nen");
  });

  chay("hoat dong tren TRANG GOC giu trang thai lam viec du panel mat focus", () => {
    const e = dungMoiTruong();
    e.TT.batDau({});
    e.doc._focus = false;   // focus dang o trang goc, khong phai trong iframe panel
    // Trang goc bao: cua so VAN co focus, va vua co thao tac
    e.TT.__nhanTinTrangGoc({ source: undefined, data: { type: "autofill-hcc-trang-thai-trang", focus: true, an: false } });
    e.tien(e.TT.NGUONG_NEN_MS + 5000);
    e.TT.__nhanTinTrangGoc({ source: undefined, data: { type: "autofill-hcc-hoat-dong" } });
    ok("khong bi coi la chay-nen", e.TT.hienTai() === "dang-lam-viec");
  });

  chay("trang goc bao mat focus du lau -> chay nen", () => {
    const e = dungMoiTruong();
    e.TT.batDau({});
    e.TT.__nhanTinTrangGoc({ source: undefined, data: { type: "autofill-hcc-trang-thai-trang", focus: false, an: false } });
    e.TT.hienTai();
    e.tien(e.TT.NGUONG_NEN_MS + 1000);
    ok("chay-nen", e.TT.hienTai() === "chay-nen");
  });

  chay("trang goc bao tab an -> chay nen ngay", () => {
    const e = dungMoiTruong();
    e.TT.batDau({});
    e.TT.__nhanTinTrangGoc({ source: undefined, data: { type: "autofill-hcc-trang-thai-trang", focus: true, an: true } });
    ok("chay-nen", e.TT.hienTai() === "chay-nen");
  });

  chay("boc fetch: dem dung so request dang chay", async () => {
    const e = dungMoiTruong();
    let giai;
    e.win.fetch = () => new Promise((r) => { giai = r; });
    e.TT.batDau({});
    const p = e.win.fetch("http://x");
    ok("dang co 1 request", e.TT.soRequestDangChay() === 1);
    ok("trang thai la dang-lam-viec", e.TT.hienTai() === "dang-lam-viec");
    giai("xong");
    await p;
    ok("ve 0 sau khi xong", e.TT.soRequestDangChay() === 0);
  });

  chay("boc fetch: khong boc hai lan", () => {
    const e = dungMoiTruong();
    e.win.fetch = () => Promise.resolve("a");
    e.TT.batDau({});
    const sauLan1 = e.win.fetch;
    e.TT.__daBatDau = false;
    e.TT.batDau({});
    ok("van la ban boc cu", e.win.fetch === sauLan1);
  });

  setTimeout(() => {
    console.log(`\n${so} phep kiem, ${hong} hong`);
    process.exit(hong ? 1 : 0);
  }, 50);
})();
