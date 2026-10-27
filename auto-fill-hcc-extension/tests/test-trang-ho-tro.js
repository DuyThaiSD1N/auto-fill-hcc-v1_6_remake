// Test bo so khop match-pattern trong content.js — thu quyet dinh "trang nay co
// mo duoc panel khong". Trich THANG tu content.js, va doi chieu voi manifest THAT.
const fs = require("fs");
const vm = require("vm");
const path = require("path");
// Goc thu muc extension — suy tu vi tri file test, khong ghim duong dan tuyet
// doi (thu muc da tung bi chuyen cho va lam gay het bo test).
const GOC = path.resolve(__dirname, "..");
const BASE = GOC;
const src = fs.readFileSync(BASE + "/content.js", "utf8");
const manifest = JSON.parse(fs.readFileSync(BASE + "/manifest.json", "utf8"));

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

const sandbox = {
  console: { warn() {}, info() {} }, URL, RegExp, Array, String,
  chrome: { runtime: { getManifest: () => manifest } },
  location: { href: "https://dichvucong.gov.vn/" },
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext([trichHam("khopMauMatch"), trichHam("trangDuocHoTro")].join("\n\n"), sandbox);
const { khopMauMatch, trangDuocHoTro } = sandbox;

// ---- so khop mau ----
ok("khop ten mien dung", khopMauMatch("https://dichvucong.gov.vn/*", "https://dichvucong.gov.vn/abc?x=1"));
ok("khac ten mien -> khong khop", !khopMauMatch("https://dichvucong.gov.vn/*", "https://khac.gov.vn/abc"));
ok("khac giao thuc -> khong khop", !khopMauMatch("https://dichvucong.gov.vn/*", "http://dichvucong.gov.vn/abc"));
ok("*.tenmien khop ten mien con", khopMauMatch("https://*.laichau.gov.vn/*", "https://dichvucong.laichau.gov.vn/x"));
ok("*.tenmien KHONG khop ten mien la", !khopMauMatch("https://*.laichau.gov.vn/*", "https://laichau.gov.vn.ke-gian.com/x"));
ok("file:// khong khop mau https", !khopMauMatch("https://dichvucong.gov.vn/*", "file:///Users/a/dvc-trang-chu.html"));
ok("<all_urls> khop tat ca", khopMauMatch("<all_urls>", "file:///bat/ky/dau.html"));
ok("mau rac -> khong khop, khong nem", !khopMauMatch("khong-phai-mau", "https://dichvucong.gov.vn/"));
ok("url rac -> khong khop, khong nem", !khopMauMatch("https://dichvucong.gov.vn/*", "khong-phai-url"));

// ---- doi chieu voi manifest THAT ----
const mauThat = manifest.web_accessible_resources.flatMap((b) => b.matches);
ok("manifest that co it nhat 20 mau", mauThat.length >= 20);
ok("cong dvc that -> DUOC ho tro", trangDuocHoTro("https://dichvucong.gov.vn/trang-chu"));
ok("cong bac ninh -> DUOC ho tro", trangDuocHoTro("https://dichvucong.bacninh.gov.vn/x/y"));

// Chinh ca anh Truong gap: trang luu ve may / server cuc bo
ok("file:// cuc bo -> KHONG ho tro", !trangDuocHoTro("file:///Users/truong/Downloads/dvc-trang-chu.html"));
ok("localhost -> KHONG ho tro", !trangDuocHoTro("http://localhost:29300/dvc-trang-chu.html"));
ok("about:blank -> KHONG ho tro", !trangDuocHoTro("about:blank"));
ok("trang la -> KHONG ho tro", !trangDuocHoTro("https://google.com/"));

// Doc manifest hong -> KHONG duoc tu chan
sandbox.chrome.runtime.getManifest = () => { throw new Error("hong"); };
ok("manifest hong -> van cho mo (khong tu chan)", trangDuocHoTro("https://bat-ky-dau.com/"));

console.log(`\n${so} phep kiem, ${hong} hong`);
process.exit(hong ? 1 : 0);
