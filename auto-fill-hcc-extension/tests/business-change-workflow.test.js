const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function node(text, visible = true) {
  return {
    textContent: text,
    value: "",
    getBoundingClientRect: () => visible ? ({ width: 100, height: 20 }) : ({ width: 0, height: 0 }),
    querySelectorAll: () => [],
  };
}

const ids = new Map();
const selectors = new Map();
const sandbox = {
  console,
  Event,
  MouseEvent: class {},
  setTimeout,
  clearTimeout,
  getComputedStyle: () => ({ display: "block", visibility: "visible" }),
  chrome: { storage: { local: { get() {}, set() {}, remove() {} } }, runtime: {} },
  document: {
    getElementById: (id) => ids.get(id) || null,
    querySelector: (selector) => selectors.get(selector) || null,
    querySelectorAll: () => [],
    forms: { namedItem: () => null },
  },
};
sandbox.window = {
  location: { pathname: "/HkdOnline/Forms/APP/Registration.aspx" },
  __HCC__: {
    sleep: async () => {},
    norm: (value) => String(value || "").trim().toLowerCase().replace(/\s+/g, " "),
    fieldCandidates: () => [],
    setNativeValue: () => {},
    waitFor: async () => false,
    readAcctContact: () => "",
    fillFormStandard: async () => {},
    findStandardInput: () => null,
    findStandardSelect: () => null,
    isPostbackAddressField: () => false,
  },
  addEventListener() {},
};

const source = fs.readFileSync(
  path.join(__dirname, "..", "content", "procedures", "business-registration.js"),
  "utf8",
);
const contentSource = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");
vm.runInNewContext(source, sandbox, { filename: "business-registration.js" });
const detect = sandbox.window.__HCC__.detectBusinessChangeStage;
const detectHint = sandbox.window.__HCC__.detectBusinessProcedureHint;
const parseDeletePostback = sandbox.window.__HCC__.parseBusinessDeletePostback;
const isBusinessRowMarkedDeleted = sandbox.window.__HCC__.isBusinessRowMarkedDeleted;

const cases = [
  ["ctl00_C_myWizard_LblQuestion1", "Chọn loại đăng ký trực tuyến", "select-registration"],
  ["ctl00_C_myWizard_Label2", "Tìm kiếm Hộ kinh doanh để tiến hành đăng ký thay đổi", "search-business"],
  ["ctl00_C_myWizard_Label11", "Chọn loại đăng ký thay đổi", "select-change"],
  ["ctl00_C_myWizard_Label12", "Xác nhận thông tin đăng ký", "confirm"],
];

for (const [id, text, expected] of cases) {
  ids.clear();
  ids.set(id, node(text));
  assert.equal(detect().stage, expected);
  const expectedHint = expected === "select-registration" ? "choice"
    : expected === "search-business" ? "shared-business-search" : "change";
  assert.equal(detectHint(), expectedHint);
}

// Heading có thể có rect=0 trên cổng thật; control ASP.NET vẫn phải nhận diện đúng WizardStep.
ids.clear();
ids.set("ctl00_C_myWizard_CtlType_1", node("", false));
assert.equal(detect().stage, "select-registration");
ids.clear();
ids.set("ctl00_C_myWizard_GDT_CODEFld", node("", false));
assert.equal(detect().stage, "search-business");
ids.clear();
ids.set("ctl00_C_myWizard_CtlAmendmentType_0", node("", false));
assert.equal(detect().stage, "select-change");
ids.clear();
ids.set("ctl00_C_myWizard_FinishNavigationTemplateContainerID_FinishButton", node("", false));
assert.equal(detect().stage, "confirm");
ids.clear();
ids.set("ctl00_C_REI_REASONTxt", node("", false));
ids.set("ctl00_C_REI_TYPE_IDChBox_0", node("", false));
assert.deepEqual(JSON.parse(JSON.stringify(detect())), {
  stage: "main", pageKey: "thong-tin-de-nghi-cap-lai", label: "",
});

ids.clear();
ids.set("ctl00_C_myWizard_Label12", node("Xác nhận thông tin đăng ký"));
ids.set("ctl00_C_myWizard_InfoChnType", node("Đăng ký cấp lại Giấy chứng nhận hộ kinh doanh"));
assert.equal(detect().stage, "confirm");
assert.equal(detectHint(), "reissue");

ids.set("ctl00_C_myWizard_InfoChnType", node("Thành lập mới hộ kinh doanh"));
assert.equal(detectHint(), "create");

ids.clear();
assert.equal(detect().stage, "unknown");
assert.equal(detectHint(), "");

const sitemap = node("");
sitemap.querySelectorAll = () => [node("Ngành nghề kinh doanh")];
selectors.set("#ctl00_LV4_SiteMapPath1", sitemap);
ids.set("ctl00_C_INFOCtl_DOCUMENT_TYPE_IDFld", node("Thành lập mới hộ kinh doanh"));
assert.equal(detect().stage, "unknown");
assert.equal(detectHint(), "create");
ids.set("ctl00_C_INFOCtl_DOCUMENT_TYPE_IDFld", node("Đăng ký thay đổi nội dung hộ kinh doanh"));
assert.deepEqual(JSON.parse(JSON.stringify(detect())), {
  stage: "main", pageKey: "nganh-nghe-kinh-doanh", label: "ngành nghề kinh doanh",
});
assert.equal(detectHint(), "change-exact");

sitemap.querySelectorAll = () => [node("Thông báo quyết định giải thể")];
assert.deepEqual(JSON.parse(JSON.stringify(detect())), {
  stage: "main", pageKey: "cham-dut-hoat-dong", label: "thông báo quyết định giải thể",
});
assert.equal(detectHint(), "dissolution");

sitemap.querySelectorAll = () => [node("Thông tin cấp lại GCN/GXN")];
ids.set("ctl00_C_INFOCtl_DOCUMENT_TYPE_IDFld", node("Đăng ký cấp lại Giấy chứng nhận hộ kinh doanh"));
assert.deepEqual(JSON.parse(JSON.stringify(detect())), {
  stage: "main", pageKey: "thong-tin-de-nghi-cap-lai", label: "thông tin cấp lại gcn/gxn",
});
assert.equal(detectHint(), "reissue");

sitemap.querySelectorAll = () => [node("Người nộp hồ sơ")];
assert.deepEqual(JSON.parse(JSON.stringify(detect())), {
  stage: "main", pageKey: "nguoi-nop-ho-so", label: "người nộp hồ sơ",
});
assert.equal(detectHint(), "reissue");

sitemap.querySelectorAll = () => [node("Khối dữ liệu")];
ids.set("ctl00_C_BLCtl_LblFilterExpand_DB", node("Khối dữ liệu"));
ids.set("ctl00_C_BLCtl_CtlList", node("Hình thức đăng ký Địa chỉ Ngành nghề kinh doanh"));
sandbox.window.location.pathname = "/HkdOnline/Forms/APP/DW_DOCUMENTEdit.aspx";
assert.deepEqual(JSON.parse(JSON.stringify(detect())), {
  stage: "main-root", pageKey: null, label: "khối dữ liệu",
});
assert.equal(detectHint(), "reissue");

// Trang tổng quan hồ sơ thành lập mới không có pageKey; metadata phải thắng session workflow cũ.
ids.set("ctl00_C_INFOCtl_DOCUMENT_TYPE_IDFld", node("Thành lập mới hộ kinh doanh"));
assert.equal(detect().stage, "unknown");
assert.equal(detectHint(), "create");

sandbox.window.location.pathname = "/HkdOnline/Forms/APP/ATTACHMENTS.aspx";
assert.equal(detect().stage, "unknown");

const directDelete = {
  getAttribute(name) {
    if (name === "href") {
      return "javascript:__doPostBack('ctl00$C$BActCtl$CtlList$ctl02$LnkDelete','')";
    }
    if (name === "onclick") return "return confirm('Bạn có muốn xóa bản ghi này không?');";
    return "";
  },
};
assert.deepEqual(JSON.parse(JSON.stringify(parseDeletePostback(directDelete))), {
  target: "ctl00$C$BActCtl$CtlList$ctl02$LnkDelete",
  arg: "",
});

const optionsDelete = {
  getAttribute(name) {
    if (name === "href") return "";
    if (name === "onclick") {
      return "return confirm('Xóa?') && WebForm_DoPostBackWithOptions(new WebForm_PostBackOptions(\"ctl00$C$BActCtl$CtlList$ctl03$LnkDelete\", \"Delete$3\", true, \"\", \"\", false, false));";
    }
    return "";
  },
};
assert.deepEqual(JSON.parse(JSON.stringify(parseDeletePostback(optionsDelete))), {
  target: "ctl00$C$BActCtl$CtlList$ctl03$LnkDelete",
  arg: "Delete$3",
});

const restoredRow = {
  querySelector: () => null,
  querySelectorAll: () => [{
    value: "",
    textContent: "Khôi phục",
    getAttribute: () => "",
  }],
};
assert.equal(isBusinessRowMarkedDeleted(restoredRow), true);
assert.equal(isBusinessRowMarkedDeleted({
  querySelector: () => null,
  querySelectorAll: () => [{ value: "", textContent: "Xóa", getAttribute: () => "" }],
}), false);

const sourceText = source;
assert.match(sourceText, /findBusinessRowByCode\(pendingRemove\)/);
assert.ok(sourceText.includes('a[id$="LnkDelete"]'));
assert.match(sourceText, /submitBusinessDeleteWithoutNativeConfirm\(control\)/);
assert.doesNotMatch(sourceText, /clickSaveDetectReload\(control\)/);
assert.match(sourceText, /st\.phase = "deleting-industry"/);
assert.match(sourceText, /reconcile xóa ngành/);
assert.match(sourceText, /rowStillExists=\$\{!!remainingRow\}/);
assert.match(sourceText, /markedDeleted=\$\{markedDeleted\}/);
assert.match(sourceText, /đã xóa mềm mã ngành, tiếp tục state machine/);
assert.match(sourceText, /row && !isBusinessRowMarkedDeleted\(row\)/);
assert.doesNotMatch(sourceText, /failChangeWorkflow\("Không bổ sung được mã ngành sau nhiều lần thử\."\)/);
assert.match(sourceText, /bỏ qua mã ngành bổ sung sau 4 lần thử, tiếp tục luồng/);
assert.match(sourceText, /không thấy ô\/nút lưu ngành không mã, bỏ qua và tiếp tục luồng/);
assert.match(sourceText, /fillBusinessLineDescriptions\(\{ items: availableCoded \}\)/);
assert.match(sourceText, /storage\.set timeout — tiếp tục state machine/);
assert.match(sourceText, /FILLALL_SESSION_MIRROR_KEY/);
assert.match(sourceText, /newestFillAllState/);
assert.match(contentSource, /window\.addEventListener\("pageshow", resume\)/);
assert.match(contentSource, /\[FillAll\] auto-resume/);
assert.match(contentSource, /\[FillAll\] auto-resume lỗi/);
assert.match(contentSource, /window\.top !== window && \[/);
assert.match(contentSource, /"detectBusinessChangeStage",/);
assert.match(contentSource, /"startChangeBusiness",/);
assert.match(contentSource, /businessSearch: \(msg && msg\.businessSearch\) \|\| flow\.search \|\| null/);
assert.match(sourceText, /nameChange \? "Y" : "N"/);
assert.match(sourceText, /amendmentValue === "DISSOLU"/);
assert.match(sourceText, /const search = st\.businessSearch \|\| flow\.search \|\| \{\}/);
assert.doesNotMatch(sourceText, /window\.Confirm=function/);
assert.match(sourceText, /value="\$\{amendmentValue\}"/);
assert.match(sourceText, /TAX_TERMINATION_NOTICE/);
assert.match(sourceText, /BUSINESS_REG_CERT_ORIGINAL/);
assert.match(sourceText, /matchCopiedApplicant/);
assert.match(sourceText, /detected\.stage === "main" \|\| detected\.stage === "main-root"/);
assert.match(sourceText, /value="\$\{registrationOption\}"/);
assert.match(sourceText, /flow\.wizardType === "reissue"/);
assert.match(sourceText, /Cổng đang ở nhánh Đăng ký thay đổi \(CHN\), không phải nhánh Cấp lại GCN \(REI\)/);
assert.match(sourceText, /Bước xác nhận không hiển thị loại Cấp lại Giấy chứng nhận/);
assert.match(sourceText, /async function handleReissuePage\(st\)/);
assert.match(sourceText, /kind === "cap_doi" \? label\.includes\("cap doi"\)/);
assert.match(sourceText, /Cổng không có lựa chọn \$\{wanted\} tương ứng với hồ sơ; không chọn loại khác thay thế/);
assert.match(sourceText, /BUSREISSUEFRM/);

console.log("business change workflow: stage selectors, delete confirmation and safety guards passed");
