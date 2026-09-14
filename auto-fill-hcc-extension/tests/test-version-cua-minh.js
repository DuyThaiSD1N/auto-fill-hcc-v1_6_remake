// Test versionCuaChinhMinh() trong lib/scanAgent.js — luat quyet dinh "ban moi
// tren dia co phai cua MINH khong". Sai o day la extension nap lai vo ich.
const fs = require("fs");
const vm = require("vm");
const path = require("path");
// Goc thu muc extension — suy tu vi tri file test, khong ghim duong dan tuyet
// doi (thu muc da tung bi chuyen cho va lam gay het bo test).
const GOC = path.resolve(__dirname, "..");
const SRC = path.join(GOC, "lib/scanAgent.js");
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
  throw new Error("khong dong ngoac " + ten);
}
const hangID = /^\s*const ID_AUTOFILL = .*$/m.exec(src)[0];

let so = 0, hong = 0;
function ok(ten, dk) { so++; if (!dk) { hong++; console.error("  FAIL:", ten); } }

function dung(id) {
  const sandbox = { chrome: { runtime: { id } } };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext([hangID, trichHam("idCuaMinh"), trichHam("versionCuaChinhMinh")].join("\n"), sandbox);
  return sandbox;
}
const AF = "jggkfcelfkeljnfnelmfmglcjanhmiem";
const HF = "klkgpeagdccbcomfnaaghjngohfomphl";

// --- agent BAN MOI: co ext_versions theo ID ---
let s = dung(AF);
ok("autofill tra dung version cua minh",
   s.versionCuaChinhMinh({ ext_versions: { [AF]: "1.17.0.9", [HF]: "1.2" } }) === "1.17.0.9");
s = dung(HF);
ok("handfree tra dung version cua minh",
   s.versionCuaChinhMinh({ ext_versions: { [AF]: "1.17.0.9", [HF]: "1.2" } }) === "1.2");

ok("co ext_versions nhung KHONG co ID cua minh -> rong (khong lay cua con khac)",
   dung("mot-id-la").versionCuaChinhMinh({ ext_versions: { [AF]: "1.17.0.9" }, ext_version: "1.17.0.9" }) === "");

// --- agent BAN CU: chi co ext_version so it ---
ok("agent cu + autofill -> dung ext_version",
   dung(AF).versionCuaChinhMinh({ ext_version: "1.17.0.9" }) === "1.17.0.9");
ok("agent cu + handfree -> RONG (ext_version la cua autofill, khong phai cua minh)",
   dung(HF).versionCuaChinhMinh({ ext_version: "1.17.0.9" }) === "");

// --- bien dang ---
ok("khong co gi ca -> rong", dung(AF).versionCuaChinhMinh({}) === "");
ok("ext_versions rong -> rong", dung(AF).versionCuaChinhMinh({ ext_versions: {} }) === "");
ok("ext_version khong phai chuoi -> rong", dung(AF).versionCuaChinhMinh({ ext_version: 123 }) === "");

console.log(`\n${so} phep kiem, ${hong} hong`);
process.exit(hong ? 1 : 0);
