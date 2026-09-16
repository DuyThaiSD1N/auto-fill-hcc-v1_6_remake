// Test moPanelTheoIcon() + khopMauUrl() trong background.js — bấm icon trên tab có content script
// MỒ CÔI (mở từ trước lần nạp lại extension) phải gỡ panel/launcher mồ côi, tiêm lại đủ bộ content
// script theo manifest rồi mở panel; trang không khớp content_scripts.matches thì KHÔNG tiêm.
const fs = require("fs");
const vm = require("vm");
const path = require("path");
const GOC = path.resolve(__dirname, "..");
const src = fs.readFileSync(path.join(GOC, "background.js"), "utf8");
const manifest = JSON.parse(fs.readFileSync(path.join(GOC, "manifest.json"), "utf8"));
const CS = manifest.content_scripts[0];

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
  throw new Error("khong dong ngoac " + ten);
}

let so = 0, hong = 0;
function ok(ten, dk) { so++; if (!dk) { hong++; console.error("  FAIL:", ten); } }

// guiLoi[i] = thông báo lỗi cho lần sendMessage thứ i (undefined = gửi được).
function taoSandbox({ guiLoi = [], tiemLoi = null } = {}) {
  const goi = [];
  const daGo = [];
  let lan = 0;
  const sandbox = {
    URL,
    console: { warn() {}, info() {}, log() {} },
    document: { getElementById: (id) => ({ remove: () => daGo.push(id) }) },
    chrome: {
      runtime: { getManifest: () => manifest },
      tabs: {
        sendMessage: async (tabId, msg) => {
          goi.push({ ham: "sendMessage", tabId, action: msg && msg.action });
          const loi = guiLoi[lan++];
          if (loi) throw new Error(loi);
        },
      },
      scripting: {
        insertCSS: async (o) => { goi.push({ ham: "insertCSS", target: o.target, files: o.files }); },
        executeScript: async (o) => {
          goi.push({ ham: "executeScript", target: o.target, files: o.files, func: o.func });
          if (o.func) o.func();
          if (tiemLoi && o.files) throw new Error(tiemLoi);
          return [];
        },
      },
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(
    trichHam("khopMauUrl") + "\n" + trichHam("moPanelTheoIcon") +
      "\nglobalThis.khopMauUrl = khopMauUrl; globalThis.moPanelTheoIcon = moPanelTheoIcon;",
    sandbox
  );
  return { sandbox, goi, daGo };
}

const MO_COI = "Could not establish connection. Receiving end does not exist.";

(async () => {
  ok("manifest co quyen scripting", (manifest.permissions || []).includes("scripting"));

  const { sandbox: s0 } = taoSandbox();
  const k = s0.khopMauUrl;
  ok("khop subdomain gov.vn", k("https://thu.dichvucong.gov.vn/ho-so?x=1", "https://*.gov.vn/*") === true);
  ok("*.gov.vn khop ca gov.vn", k("https://gov.vn/", "https://*.gov.vn/*") === true);
  ok("khong khop evilgov.vn", k("https://evilgov.vn/", "https://*.gov.vn/*") === false);
  ok("khong khop gov.vn.evil.com", k("https://x.gov.vn.evil.com/", "https://*.gov.vn/*") === false);
  ok("khong khop sai scheme", k("http://thu.gov.vn/", "https://*.gov.vn/*") === false);
  ok("khop host chinh xac", k("https://dichvucong.gov.vn/abc", "https://dichvucong.gov.vn/*") === true);
  ok("khong khop host khac", k("https://dvc.moet.gov.vn/", "https://dichvucong.gov.vn/*") === false);
  ok("khong khop chrome://", k("chrome://extensions/", "https://*.gov.vn/*") === false);
  ok("url rong khong khop", k(undefined, "https://*.gov.vn/*") === false);
  ok("mau hong khong khop", k("https://thu.gov.vn/", "khong-phai-mau") === false);
  ok("moi mau trong manifest deu doc duoc", CS.matches.every((mau) => k(mau.replace("*.", "a.").replace(/\*$/, "x"), mau)));

  // Content script còn sống: chỉ gửi togglePanel, không tiêm, không gỡ gì.
  const a = taoSandbox();
  const kqA = await a.sandbox.moPanelTheoIcon({ id: 7, url: "https://thu.dichvucong.gov.vn/" });
  ok("song: tra da-gui", kqA === "da-gui");
  ok("song: khong tiem", !a.goi.some((g) => g.ham !== "sendMessage"));
  ok("song: khong go panel", a.daGo.length === 0);

  // Tab mồ côi trên trang khớp: gỡ xác panel/launcher → CSS → đủ JS đúng thứ tự manifest → gửi lại.
  const b = taoSandbox({ guiLoi: [MO_COI] });
  const kqB = await b.sandbox.moPanelTheoIcon({ id: 9, url: "https://thu.dichvucong.gov.vn/ho-so" });
  ok("mo coi: tra tiem-lai", kqB === "tiem-lai");
  ok("mo coi: thu tu goi", b.goi.map((g) => g.ham).join(",") === "sendMessage,executeScript,insertCSS,executeScript,sendMessage");
  const don = b.goi[1];
  ok("mo coi: buoc don chay o khung tren cung", don && typeof don.func === "function" && !don.files && don.target.tabId === 9 && !don.target.allFrames);
  ok("mo coi: go dung panel + launcher mo coi", JSON.stringify(b.daGo) === JSON.stringify(["tro-ly-nguoi-dan-panel", "tro-ly-nguoi-dan-bubble"]));
  const tiem = b.goi[3];
  ok("mo coi: tiem dung danh sach + thu tu manifest", JSON.stringify(tiem && tiem.files) === JSON.stringify(CS.js));
  ok("mo coi: tiem moi frame theo all_frames", tiem && tiem.target.tabId === 9 && tiem.target.allFrames === !!CS.all_frames);
  const css = b.goi[2];
  ok("mo coi: chen css theo manifest", JSON.stringify(css && css.files) === JSON.stringify(CS.css || []));
  ok("mo coi: gui lai togglePanel", b.goi[4] && b.goi[4].action === "togglePanel" && b.goi[4].tabId === 9);

  // Trang không khớp matches: không gỡ, không tiêm gì.
  const c = taoSandbox({ guiLoi: [MO_COI] });
  const kqC = await c.sandbox.moPanelTheoIcon({ id: 3, url: "https://example.com/" });
  ok("khong khop: tra khong-ho-tro", kqC === "khong-ho-tro");
  ok("khong khop: khong tiem", !c.goi.some((g) => g.ham === "executeScript" || g.ham === "insertCSS"));

  // Không có tab.
  const d = taoSandbox();
  ok("khong tab: tra khong-tab", (await d.sandbox.moPanelTheoIcon(undefined)) === "khong-tab" && d.goi.length === 0);

  // Tiêm hỏng: ném ra cho listener ghi log, không gửi lại.
  const e = taoSandbox({ guiLoi: [MO_COI], tiemLoi: "Cannot access contents of the page" });
  let nem = null;
  try { await e.sandbox.moPanelTheoIcon({ id: 4, url: "https://thu.gov.vn/" }); } catch (err) { nem = err; }
  ok("tiem hong: nem loi", nem && /Cannot access/.test(nem.message));
  ok("tiem hong: khong gui lai", e.goi.filter((g) => g.ham === "sendMessage").length === 1);

  // Listener gắn vào chrome.action.onClicked gọi đúng hàm này.
  ok("onClicked goi moPanelTheoIcon", /chrome\.action\.onClicked\.addListener\(\(tab\) => \{\s*moPanelTheoIcon\(tab\)/.test(src));

  console.log(`test-mo-panel: ${so - hong}/${so} dat`);
  process.exit(hong ? 1 : 0);
})();
