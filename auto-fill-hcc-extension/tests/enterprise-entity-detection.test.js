/**
 * Nhận diện LOẠI HÌNH doanh nghiệp trên cổng ĐKKD qua mạng (dangkyquamang.dkkd.gov.vn).
 *
 * Cổng dùng CHUNG domain + chung Registration.aspx/DW_DOCUMENTEdit.aspx cho mọi loại hình, nên thứ
 * duy nhất phân biệt hồ sơ công ty cổ phần với hồ sơ TNHH hai thành viên là dòng "Loại hình doanh
 * nghiệp" in trên chính hồ sơ. Test giữ hai mắt xích:
 *   1. content/procedures/enterprise-registration.js đọc ĐÚNG dòng đó (bảng hai cột lẫn innerText);
 *   2. popup.js quy nhãn về mã loại hình rồi chọn thủ tục, và KHÔNG đoán theo domain khi chưa biết.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { el } = require("./mini-dom");

// ===================== 1. popup.js: nhãn loại hình -> thủ tục =====================
const popupSource = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");
const start = popupSource.indexOf("function enterpriseEntityCode(label)");
const end = popupSource.indexOf("\nfunction setProcedureDetected", start);
assert.ok(start >= 0 && end > start, "Không tách được engine detect thủ tục");

const sandbox = { selectedKey: "" };
vm.runInNewContext(`
  const PROCEDURES = [
    {key:"dang-ky-kinh-doanh", label:"Đăng ký thành lập hộ kinh doanh",
     detect:{urlIncludes:["hokinhdoanh.dkkd.gov.vn"], headingDisabled:true}},
    {key:"thanh-lap-cong-ty-co-phan", label:"Đăng ký thành lập công ty cổ phần",
     enterprisePortal:true, enterpriseEntityLabel:"Công ty cổ phần", enterpriseEntityValue:"SC",
     detect:{urlIncludes:["dangkyquamang.dkkd.gov.vn"], headingDisabled:true}},
    {key:"thanh-lap-cong-ty-tnhh-hai-thanh-vien",
     label:"Đăng ký thành lập công ty trách nhiệm hữu hạn hai thành viên trở lên",
     enterprisePortal:true,
     enterpriseEntityLabel:"Công ty trách nhiệm hữu hạn hai thành viên trở lên",
     enterpriseEntityValue:"LLC2",
     detect:{urlIncludes:["dangkyquamang.dkkd.gov.vn"], headingDisabled:true}},
  ];
  function normalizeProcedureSearch(value) {
    return String(value || "").normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").replace(/đ/g, "d").toLowerCase();
  }
  function normDetect(value) { return normalizeProcedureSearch(value).replace(/\\s+/g, " ").trim(); }
  function selectedProcedureConfig() { return PROCEDURES.find((item) => item.key === selectedKey) || null; }
  function detectUrlScopeOk(detect, url) {
    const scope = detect.urlScope || [];
    if (!scope.length) return true;
    return scope.some((u) => u && url.includes(String(u).toLowerCase()));
  }
  ${popupSource.slice(start, end)}
  globalThis.detect = detectProcedureKeyFromSignals;
  globalThis.entityCode = enterpriseEntityCode;
`, sandbox);

const DOSSIER = "https://dangkyquamang.dkkd.gov.vn/online/Forms/APP/DW_DOCUMENTEdit.aspx?h=89c0";
const WIZARD = "https://dangkyquamang.dkkd.gov.vn/online/Forms/APP/Registration.aspx";
const detect = (signals) => sandbox.detect({ bodyText: "", headings: [], ...signals });

// --- Quy nhãn về mã loại hình (value radio $CtlEntType của cổng) ---
assert.equal(sandbox.entityCode("Công ty cổ phần"), "SC");
assert.equal(sandbox.entityCode("CÔNG TY CỔ PHẦN"), "SC");
assert.equal(sandbox.entityCode("Công ty trách nhiệm hữu hạn hai thành viên trở lên"), "LLC2");
assert.equal(sandbox.entityCode("Công ty TNHH hai thành viên trở lên"), "LLC2");
assert.equal(sandbox.entityCode("Công ty TNHH 2 thành viên trở lên"), "LLC2");
assert.equal(sandbox.entityCode("Công ty trách nhiệm hữu hạn một thành viên"), "LLC1");
assert.equal(sandbox.entityCode("Công ty TNHH MTV"), "LLC1");
assert.equal(sandbox.entityCode("Doanh nghiệp tư nhân"), "PRI");
assert.equal(sandbox.entityCode("Công ty hợp danh"), "PARTNER");
// TNHH mà không nói rõ một hay hai thành viên: KHÔNG được đoán.
assert.equal(sandbox.entityCode("Công ty trách nhiệm hữu hạn"), "");
assert.equal(sandbox.entityCode(""), "");

// --- Hồ sơ đã tạo: chốt thủ tục theo loại hình in trên hồ sơ ---
sandbox.selectedKey = "";
assert.equal(
  detect({ url: DOSSIER, enterpriseProcedureHint: "dossier", enterpriseEntityLabel: "Công ty cổ phần" }),
  "thanh-lap-cong-ty-co-phan",
);
for (const label of [
  "Công ty trách nhiệm hữu hạn hai thành viên trở lên",
  "Công ty TNHH hai thành viên trở lên",
  "Công ty TNHH 2 thành viên trở lên",
]) {
  assert.equal(
    detect({ url: DOSSIER, enterpriseProcedureHint: "dossier", enterpriseEntityLabel: label }),
    "thanh-lap-cong-ty-tnhh-hai-thanh-vien",
    `Nhãn "${label}" phải ra thủ tục TNHH hai thành viên`,
  );
}

// Hồ sơ CTCP nhưng panel còn giữ thủ tục TNHH của lần trước → phải đổi theo hồ sơ đang mở.
sandbox.selectedKey = "thanh-lap-cong-ty-tnhh-hai-thanh-vien";
assert.equal(
  detect({ url: DOSSIER, enterpriseProcedureHint: "dossier", enterpriseEntityLabel: "Công ty cổ phần" }),
  "thanh-lap-cong-ty-co-phan",
);

// Loại hình CHƯA có thủ tục (TNHH một thành viên): giữ lựa chọn doanh nghiệp đang có, không nhận bừa.
assert.equal(
  detect({ url: DOSSIER, enterpriseProcedureHint: "dossier", enterpriseEntityLabel: "Công ty TNHH một thành viên" }),
  "thanh-lap-cong-ty-tnhh-hai-thanh-vien",
);
sandbox.selectedKey = "";
assert.equal(
  detect({ url: DOSSIER, enterpriseProcedureHint: "dossier", enterpriseEntityLabel: "Công ty TNHH một thành viên" }),
  "",
);
sandbox.selectedKey = "dang-ky-kinh-doanh";
assert.equal(
  detect({ url: DOSSIER, enterpriseProcedureHint: "dossier", enterpriseEntityLabel: "Công ty TNHH một thành viên" }),
  "",
  "Thủ tục hộ kinh doanh không bao giờ đúng ở cổng doanh nghiệp",
);

// --- Wizard/trang chưa chốt loại hình: giữ lựa chọn, tuyệt đối không đoán về CTCP ---
sandbox.selectedKey = "";
assert.equal(detect({ url: WIZARD, enterpriseProcedureHint: "select-entity-type" }), "");
sandbox.selectedKey = "thanh-lap-cong-ty-tnhh-hai-thanh-vien";
assert.equal(
  detect({ url: WIZARD, enterpriseProcedureHint: "select-entity-type" }),
  "thanh-lap-cong-ty-tnhh-hai-thanh-vien",
);

// Lượt postback mà content script của cổng chưa gắn kịp → hint RỖNG. Trước đây rơi xuống rule
// urlIncludes (CTCP và TNHH khai trùng domain, CTCP đứng trước) nên hồ sơ TNHH đang điền dở bị kéo
// sang công ty cổ phần. Nay gate theo domain nên lựa chọn được giữ nguyên.
assert.equal(
  detect({ url: DOSSIER, enterpriseProcedureHint: "" }),
  "thanh-lap-cong-ty-tnhh-hai-thanh-vien",
);
sandbox.selectedKey = "";
assert.equal(detect({ url: DOSSIER, enterpriseProcedureHint: "" }), "");

// Cổng hộ kinh doanh không bị ảnh hưởng.
sandbox.selectedKey = "";
assert.equal(detect({ url: "https://hokinhdoanh.dkkd.gov.vn/Registration.aspx" }), "dang-ky-kinh-doanh");

// ===================== 2. đọc dòng "Loại hình doanh nghiệp" trên hồ sơ =====================
const entSource = fs.readFileSync(
  path.join(__dirname, "..", "content", "procedures", "enterprise-registration.js"), "utf8",
);
const foldStart = entSource.indexOf("  function fold(value) {");
const foldEnd = entSource.indexOf("\n  }", foldStart) + "\n  }".length;
const readerStart = entSource.indexOf("  const ENTITY_LABEL_MARKER");
const readerEnd = entSource.indexOf("  if (window.top !== window) return;", readerStart);
assert.ok(foldStart >= 0 && readerStart >= 0 && readerEnd > readerStart, "Không tách được hàm đọc loại hình");

const readerCtx = vm.createContext({
  H: {},
  location: { hostname: "dangkyquamang.dkkd.gov.vn" },
  detectStage: () => "dossier",
  document: null,
});
vm.runInContext(
  `${entSource.slice(foldStart, foldEnd)}\n${entSource.slice(readerStart, readerEnd)}`,
  readerCtx,
);
const readEntityLabel = (doc) => { readerCtx.document = doc; return readerCtx.H.detectEnterpriseEntityLabel(); };

// Bảng hai cột "nhãn | giá trị" — hình dạng thật của khối "Thông tin về hồ sơ".
function twoColumnDoc(label, value) {
  const body = el("body");
  const row = el("tr");
  row.add(el("td", { text: label }), el("td", { text: value }));
  const table = el("table");
  table.add(row);
  body.add(table);
  body.innerText = "";     // ép đi đường ô bảng
  return { body, querySelectorAll: (sel) => body.querySelectorAll(sel) };
}

assert.equal(
  readEntityLabel(twoColumnDoc("Loại hình doanh nghiệp", "Công ty trách nhiệm hữu hạn hai thành viên trở lên")),
  "Công ty trách nhiệm hữu hạn hai thành viên trở lên",
);
assert.equal(
  readEntityLabel(twoColumnDoc("Loại hình doanh nghiệp:", "Công ty cổ phần")),
  "Công ty cổ phần",
);
// Nhãn và giá trị chung một ô.
const oneCell = (() => {
  const body = el("body");
  const row = el("tr");
  row.add(el("td", { text: "Loại hình doanh nghiệp: Công ty cổ phần" }));
  const table = el("table");
  table.add(row);
  body.add(table);
  body.innerText = "";
  return { body, querySelectorAll: (sel) => body.querySelectorAll(sel) };
})();
assert.equal(readEntityLabel(oneCell), "Công ty cổ phần");

// Không có bảng: rơi về innerText. Dòng nối bằng TAB là chỗ bản cũ trả rỗng rồi vớ nhầm dòng kế tiếp.
const textDoc = (innerText) => {
  const body = el("body");
  body.innerText = innerText;
  return { body, querySelectorAll: () => [] };
};
assert.equal(
  readEntityLabel(textDoc(
    "Thông tin về hồ sơ\nLoại hình doanh nghiệp\tCông ty TNHH hai thành viên trở lên\nTình trạng\tĐang soạn",
  )),
  "Công ty TNHH hai thành viên trở lên",
);
assert.equal(
  readEntityLabel(textDoc("Loại hình doanh nghiệp: Công ty cổ phần\nTình trạng: Đang soạn")),
  "Công ty cổ phần",
);
assert.equal(
  readEntityLabel(textDoc("Loại hình doanh nghiệp\nCông ty cổ phần\nTình trạng")),
  "Công ty cổ phần",
);
assert.equal(readEntityLabel(textDoc("Không có dòng loại hình")), "");

// Ngoài trang hồ sơ (wizard) thì KHÔNG đọc: bước 2 tick sẵn dòng đầu nên đọc ở đó là nhận nhầm.
readerCtx.detectStage = () => "select-entity-type";
assert.equal(
  readEntityLabel(textDoc("Loại hình doanh nghiệp: Công ty cổ phần")),
  "",
);
readerCtx.detectStage = () => "dossier";

console.log("enterprise entity detection: CTCP / TNHH hai thành viên passed");
