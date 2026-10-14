// Test hoiAgent() trong background.js — lời ping mỗi phút tới agent phải kèm
// ext_id + ext_ver (version Chrome đang chạy) mà vẫn nhận agent y như cũ.
const fs = require("fs");
const vm = require("vm");
const path = require("path");
const GOC = path.resolve(__dirname, "..");
const src = fs.readFileSync(path.join(GOC, "background.js"), "utf8");

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
const hangCong = /^\s*const CONG_AGENT = .*$/m.exec(src)[0];

let so = 0, hong = 0;
function ok(ten, dk) { so++; if (!dk) { hong++; console.error("  FAIL:", ten); } }

async function chay(traLoi) {
  const daGoi = [];
  const sandbox = {
    chrome: { runtime: { id: "klkgpeagdccbcomfnaaghjngohfomphl", getManifest: () => ({ version: "1.3.1" }) } },
    AbortController, setTimeout, clearTimeout,
    fetch: async (url) => { daGoi.push(url); return traLoi(url); },
  };
  vm.createContext(sandbox);
  vm.runInContext(hangCong + "\n" + trichHam("hoiAgent") + "\nglobalThis.hoiAgent = hoiAgent;", sandbox);
  return { d: await sandbox.hoiAgent(), daGoi };
}

(async () => {
  const r1 = await chay(() => ({ ok: true, json: async () => ({ app: "scan-bridge-agent", version: "x" }) }));
  const u = new URL(r1.daGoi[0]);
  ok("goi dung cong dau tien", u.origin === "http://127.0.0.1:28147" && u.pathname === "/v1/ping");
  ok("kem ext_id", u.searchParams.get("ext_id") === "klkgpeagdccbcomfnaaghjngohfomphl");
  ok("kem ext_ver", u.searchParams.get("ext_ver") === "1.3.1");
  ok("chi hai tham so", [...u.searchParams.keys()].join(",") === "ext_id,ext_ver");
  ok("tra ping cua agent", r1.d && r1.d.version === "x");

  const r2 = await chay((url) => url.includes(":28147/")
    ? { ok: true, json: async () => ({ app: "khac" }) }
    : { ok: true, json: async () => ({ app: "scan-bridge-agent", version: "y" }) });
  ok("bo qua cong khong phai agent", r2.d && r2.d.version === "y" && r2.daGoi.length === 2);

  const r3 = await chay(() => { throw new Error("khong ket noi"); });
  ok("khong agent nao thi null", r3.d === null && r3.daGoi.length === 5);

  console.log(`test-hoi-agent: ${so - hong}/${so} dat`);
  process.exit(hong ? 1 : 0);
})();
