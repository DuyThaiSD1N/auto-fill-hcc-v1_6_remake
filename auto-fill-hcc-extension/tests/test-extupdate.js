// Test logic tu-nap-lai cua popup.js. Trich THANG tu file that (khong chep lai)
// de test khong bao gio lech voi code dang chay.
const fs = require("fs");
const vm = require("vm");
const path = require("path");
// Goc thu muc extension — suy tu vi tri file test, khong ghim duong dan tuyet
// doi (thu muc da tung bi chuyen cho va lam gay het bo test).
const GOC = path.resolve(__dirname, "..");
const SRC = path.join(GOC, "popup.js");

const src = fs.readFileSync(SRC, "utf8");
const dau = src.indexOf("// ---- Tự nạp lại khi agent đã đặt bản extension mới lên đĩa");
const cuoi = src.indexOf("function ensureScanAgentConnected() {");
if (dau < 0 || cuoi < 0 || cuoi < dau) throw new Error("khong trich duoc khoi ext-update tu popup.js");
const khoi = src.slice(dau, cuoi);

let so = 0, hong = 0;
function ok(ten, dk) {
  so++;
  if (dk) return;
  hong++;
  console.error("  FAIL:", ten);
}
async function chay(ten, fn) {
  try { await fn(); } catch (e) { hong++; console.error("  LOI:", ten, e.message); }
}

// --- moi truong gia ---
function dungMoiTruong({ versionDangChay = "1.0.0", trangThai = "mo-khong-lam-viec", queue = null, thu = null,
                        tabKhacDangLamViec = false, sendMessageHong = false, thieuModule = false } = {}) {
  const luu = {};
  if (thu) luu["autofill_ext_update_thu"] = thu;
  if (queue) luu["autofill_split_attach_queue"] = queue;
  const vet = { reload: 0, saveSession: 0, removed: [], set: [] };
  const sandbox = {
    console: { info() {}, warn() {}, error() {} },
    setInterval: (fn, ms) => { vet.interval = { fn, ms }; return 1; },
    clearInterval: () => { vet.interval = null; },
    Date,
    Number,
    window: thieuModule ? {} : {
      HccTrangThai: {
        batDau() { vet.daBatDauTheoDoi = true; },
        hienTai: () => trangThai,
      },
    },
    document: {},
    async saveSession() { vet.saveSession++; },
    chrome: {
      runtime: {
        getManifest: () => ({ version: versionDangChay }),
        reload: () => { vet.reload++; },
        async sendMessage(msg) {
          vet.daGui = (vet.daGui || []);
          vet.daGui.push(msg?.action);
          if (sendMessageHong) throw new Error("khong co background");
          if (msg?.action === "hccCoTabNaoDangLamViec") return { co: tabKhacDangLamViec };
          return { ok: true };
        },
      },
      storage: {
        local: {
          async get(k) { return k in luu ? { [k]: luu[k] } : {}; },
          async set(o) { Object.assign(luu, o); vet.set.push(o); },
          remove(k) { delete luu[k]; vet.removed.push(k); return Promise.resolve(); },
        },
      },
    },
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(khoi, sandbox);
  return { sandbox, vet, luu };
}
const doiMotNhip = () => new Promise((r) => setImmediate(() => setImmediate(r)));

(async () => {
  await chay("nap lai ngay khi dia co ban moi va dang ranh", async () => {
    const { sandbox, vet } = dungMoiTruong({ versionDangChay: "1.17.0.1" });
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("da goi reload", vet.reload === 1);
    ok("da ghi phien truoc khi reload", vet.saveSession === 1);
  });

  await chay("KHONG nap lai khi dia dung bang ban dang chay", async () => {
    const { sandbox, vet } = dungMoiTruong({ versionDangChay: "1.17.0.2" });
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("khong reload", vet.reload === 0);
    ok("xoa bo dem thu", vet.removed.includes("autofill_ext_update_thu"));
  });

  await chay("HA CAP cung phai nap lai (CMS lui ban de chua chay)", async () => {
    const { sandbox, vet } = dungMoiTruong({ versionDangChay: "1.17.0.9" });
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("da reload khi ha cap", vet.reload === 1);
  });

  await chay("agent ban cu khong khai ext_version -> khong lam gi", async () => {
    const { sandbox, vet } = dungMoiTruong({ versionDangChay: "1.17.0.1" });
    sandbox.extUpdateGhiNhan("");
    await doiMotNhip();
    ok("khong reload", vet.reload === 0);
  });

  await chay("panel DANG LAM VIEC -> hoan lai, hen gio thu lai", async () => {
    let tt = "dang-lam-viec";
    const { sandbox, vet } = dungMoiTruong({ versionDangChay: "1.17.0.1" });
    sandbox.window.HccTrangThai.hienTai = () => tt;
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("chua reload", vet.reload === 0);
    ok("da dat hen gio", !!vet.interval);
    tt = "mo-khong-lam-viec";
    vet.interval.fn();
    await doiMotNhip();
    ok("reload khi da ranh", vet.reload === 1);
  });

  await chay("THIEU module trang thai -> khong bao gio tu nap lai", async () => {
    const { sandbox, vet } = dungMoiTruong({ versionDangChay: "1.17.0.1", thieuModule: true });
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("khong reload", vet.reload === 0);
  });

  await chay("chay nen (can bo da di) -> duoc nap lai", async () => {
    const { sandbox, vet } = dungMoiTruong({ versionDangChay: "1.17.0.1", trangThai: "chay-nen" });
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("da reload", vet.reload === 1);
  });

  await chay("hang doi tach ho so dang chay -> hoan lai", async () => {
    const { sandbox, vet } = dungMoiTruong({
      versionDangChay: "1.17.0.1", queue: { items: [1] },
    });
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("chua reload khi dang tach ho so", vet.reload === 0);
  });

  await chay("van an toan: khong thu qua tran cho CUNG mot version", async () => {
    const { sandbox, vet } = dungMoiTruong({
      versionDangChay: "1.17.0.1",
      thu: { version: "1.17.0.2", so: 3, luc: Date.now() },
    });
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("khong reload nua", vet.reload === 0);
  });

  await chay("bo dem thu tang dan qua tung lan", async () => {
    const { sandbox, vet, luu } = dungMoiTruong({
      versionDangChay: "1.17.0.1",
      thu: { version: "1.17.0.2", so: 1, luc: Date.now() },
    });
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("van reload (chua qua tran)", vet.reload === 1);
    ok("bo dem len 2", luu["autofill_ext_update_thu"].so === 2);
  });

  await chay("bo dem cua version KHAC khong tinh vao version nay", async () => {
    const { sandbox, vet } = dungMoiTruong({
      versionDangChay: "1.17.0.1",
      thu: { version: "1.16.0.9", so: 9, luc: Date.now() },
    });
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("reload binh thuong", vet.reload === 1);
  });

  await chay("tab KHAC dang lam viec -> KHONG nap lai", async () => {
    const { sandbox, vet } = dungMoiTruong({ versionDangChay: "1.17.0.1", tabKhacDangLamViec: true });
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("khong reload", vet.reload === 0);
    ok("co hoi background", (vet.daGui || []).includes("hccCoTabNaoDangLamViec"));
  });

  await chay("GO panel moi tab TRUOC khi nap lai", async () => {
    const { sandbox, vet } = dungMoiTruong({ versionDangChay: "1.17.0.1" });
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    const gui = vet.daGui || [];
    ok("da reload", vet.reload === 1);
    ok("da yeu cau go panel", gui.includes("hccGoPanelMoiTab"));
    ok("go TRUOC khi reload", gui.indexOf("hccGoPanelMoiTab") < gui.length);
  });

  await chay("trinh duyet CU: sendMessage tra undefined -> coi nhu BAN", async () => {
    // Tren trinh duyet chua tra Promise cho sendMessage, `res` la undefined ma
    // KHONG nem loi. Coi falsy la "ranh" nghia la o dung nhung may do extension
    // se nap lai bat ke can bo dang lam gi.
    const { sandbox, vet } = dungMoiTruong({ versionDangChay: "1.17.0.1" });
    sandbox.chrome.runtime.sendMessage = async () => undefined;
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("khong reload", vet.reload === 0);
  });

  await chay("tra loi khong ro rang (thieu truong co) -> coi nhu BAN", async () => {
    const { sandbox, vet } = dungMoiTruong({ versionDangChay: "1.17.0.1" });
    sandbox.chrome.runtime.sendMessage = async () => ({});
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("khong reload", vet.reload === 0);
  });

  await chay("khong hoi duoc background -> coi nhu BAN (an toan)", async () => {
    const { sandbox, vet } = dungMoiTruong({ versionDangChay: "1.17.0.1", sendMessageHong: true });
    sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("khong reload khi khong biet chac", vet.reload === 0);
  });

  await chay("tab khac vua ranh -> nap lai o luot kiem sau", async () => {
    const env = dungMoiTruong({ versionDangChay: "1.17.0.1", tabKhacDangLamViec: true });
    env.sandbox.extUpdateGhiNhan("1.17.0.2");
    await doiMotNhip();
    ok("chua reload", env.vet.reload === 0);
    ok("da dat hen gio", !!env.vet.interval);
    env.sandbox.chrome.runtime.sendMessage = async () => ({ co: false });
    env.vet.interval.fn();
    await doiMotNhip();
    ok("reload sau khi tab kia ranh", env.vet.reload === 1);
  });

  console.log(`\n${so} phep kiem, ${hong} hong`);
  process.exit(hong ? 1 : 0);
})();
