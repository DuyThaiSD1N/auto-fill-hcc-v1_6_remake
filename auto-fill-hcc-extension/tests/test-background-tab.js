// Test coTabNaoDangLamViec cua background.js — cho quyet dinh "co duoc nap lai
// khong". Trich THANG ham that tu background.js.
const fs = require("fs");
const vm = require("vm");
const path = require("path");
// Goc thu muc extension — suy tu vi tri file test, khong ghim duong dan tuyet
// doi (thu muc da tung bi chuyen cho va lam gay het bo test).
const GOC = path.resolve(__dirname, "..");
const SRC = path.join(GOC, "background.js");
const src = fs.readFileSync(SRC, "utf8");

function trichHam(ten) {
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
  throw new Error("khong dong ngoac cho " + ten);
}
function trichHang(ten) {
  const m = new RegExp("^const " + ten + " = .*$", "m").exec(src);
  if (!m) throw new Error("khong tim thay hang " + ten);
  return m[0];
}

let so = 0, hong = 0;
function ok(ten, dk) { so++; if (!dk) { hong++; console.error("  FAIL:", ten); } }
async function chay(ten, fn) { try { await fn(); } catch (e) { hong++; console.error("  LOI:", ten, e.message); } }

function dungMoiTruong({ tabs = [], traLoi = () => ({}) } = {}) {
  const sandbox = {
    console: { warn() {}, info() {}, error() {} },
    Promise, Number, Array, Math, Date,
    chrome: {
      tabs: {
        // async => tra Promise => trinh duyet MOI
        query: async () => tabs,
        sendMessage: async (id, msg) => traLoi(id, msg),
      },
    },
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext([trichHang("NGUONG_ROI_DI_MS"), trichHam("hoTroPromise"),
                   trichHam("coTabNaoDangLamViec")].join("\n\n"), sandbox);
  return sandbox;
}

(async () => {
  await chay("tab co panel, dang focus, vua thao tac -> DANG LAM VIEC", async () => {
    const s = dungMoiTruong({ tabs: [{ id: 1 }],
      traLoi: () => ({ coPanel: true, focus: true, an: false, imLangMs: 1000 }) });
    ok("co", (await s.coTabNaoDangLamViec()) === true);
  });

  await chay("tab co panel nhung bi an -> khong tinh", async () => {
    const s = dungMoiTruong({ tabs: [{ id: 1 }],
      traLoi: () => ({ coPanel: true, focus: true, an: true, imLangMs: 0 }) });
    ok("khong", (await s.coTabNaoDangLamViec()) === false);
  });

  await chay("mat focus va im lang du lau -> da roi di, khong tinh", async () => {
    const s = dungMoiTruong({ tabs: [{ id: 1 }],
      traLoi: () => ({ coPanel: true, focus: false, an: false, imLangMs: 999999 }) });
    ok("khong", (await s.coTabNaoDangLamViec()) === false);
  });

  await chay("mat focus nhung vua thao tac -> VAN tinh la dang lam viec", async () => {
    const s = dungMoiTruong({ tabs: [{ id: 1 }],
      traLoi: () => ({ coPanel: true, focus: false, an: false, imLangMs: 1000 }) });
    ok("co", (await s.coTabNaoDangLamViec()) === true);
  });

  await chay("tab khong co panel -> khong co gi de mat", async () => {
    const s = dungMoiTruong({ tabs: [{ id: 1 }], traLoi: () => ({ coPanel: false }) });
    ok("khong", (await s.coTabNaoDangLamViec()) === false);
  });

  await chay("tab khong co content script (nem loi) -> khong tinh", async () => {
    const s = dungMoiTruong({ tabs: [{ id: 1 }],
      traLoi: () => { throw new Error("Could not establish connection"); } });
    ok("khong", (await s.coTabNaoDangLamViec()) === false);
  });

  // ---- trinh duyet CU: day la cho de hong theo huong nguy hiem ----
  await chay("TRINH DUYET CU (khong tra Promise) + undefined -> coi nhu DANG LAM VIEC", async () => {
    const s = dungMoiTruong({ tabs: [{ id: 1 }], traLoi: () => undefined });
    s.chrome.tabs.query = () => undefined;           // ban cu: khong tra Promise
    ok("coi la ban", (await s.coTabNaoDangLamViec()) === true);
  });

  await chay("TRINH DUYET MOI + undefined (trang extension mo dang tab) -> RANH", async () => {
    // Mot trang extension mo thanh tab co nguoi nhan message nhung khong ai tra
    // loi -> undefined. Do KHONG phai panel tren trang cong, khong co gi de mat.
    // Gop chung voi ca "trinh duyet cu" la chan vinh vien.
    const s = dungMoiTruong({ tabs: [{ id: 1 }], traLoi: () => undefined });
    ok("coi la ranh", (await s.coTabNaoDangLamViec()) === false);
  });

  await chay("TRINH DUYET CU: tabs.query tra undefined -> coi nhu DANG LAM VIEC", async () => {
    const s = dungMoiTruong({});
    s.chrome.tabs.query = async () => undefined;
    ok("coi la ban", (await s.coTabNaoDangLamViec()) === true);
  });

  await chay("khong co tab nao -> ranh", async () => {
    const s = dungMoiTruong({ tabs: [] });
    ok("ranh", (await s.coTabNaoDangLamViec()) === false);
  });

  await chay("mot tab ban trong nhieu tab -> ket luan la BAN", async () => {
    const s = dungMoiTruong({ tabs: [{ id: 1 }, { id: 2 }, { id: 3 }],
      traLoi: (id) => id === 2
        ? { coPanel: true, focus: true, an: false, imLangMs: 0 }
        : { coPanel: false } });
    ok("co", (await s.coTabNaoDangLamViec()) === true);
  });

  console.log(`\n${so} phep kiem, ${hong} hong`);
  process.exit(hong ? 1 : 0);
})();
