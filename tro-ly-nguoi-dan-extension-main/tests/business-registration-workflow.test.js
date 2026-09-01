const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const source = fs.readFileSync(
  path.join(root, "content", "procedures", "business-registration.js"), "utf8"
);
const adapter = fs.readFileSync(
  path.join(root, "content", "business-registration-adapter.js"), "utf8"
);
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

function domNode(text = "") {
  return {
    textContent: text,
    value: "",
    disabled: false,
    checked: false,
    getBoundingClientRect: () => ({ width: 100, height: 20 }),
    querySelectorAll: () => [],
    querySelector: () => null,
    getAttribute: () => "",
    click() {},
  };
}

function loadCore() {
  const ids = new Map();
  const selectors = new Map();
  const lists = new Map();
  const sandbox = {
    console,
    Event,
    setTimeout,
    clearTimeout,
    getComputedStyle: () => ({ display: "block", visibility: "visible" }),
    chrome: { storage: { local: { get() {}, set() {}, remove() {} } }, runtime: {} },
    document: {
      getElementById: (id) => ids.get(id) || null,
      querySelector: (selector) => selectors.get(selector) || null,
      querySelectorAll: (selector) => lists.get(selector) || [],
      forms: { namedItem: () => null },
    },
  };
  sandbox.window = {
    location: {
      hostname: "hokinhdoanh.dkkd.gov.vn",
      pathname: "/HkdOnline/Default.aspx",
    },
    __TLND__: {
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
    sessionStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  };
  vm.runInNewContext(source, sandbox, { filename: "business-registration.js" });
  return { sandbox, ids, selectors, lists, H: sandbox.window.__TLND__ };
}

test("nhận diện đủ ba màn bootstrap và trang Khối dữ liệu của hồ sơ NEW", () => {
  const { sandbox, ids, selectors, lists, H } = loadCore();
  const homeLink = domNode("Đăng ký Hộ kinh doanh");
  lists.set("a.AspNet-Menu-Link, .PrettyMenu a", [homeLink]);
  assert.equal(H.detectBusinessCreateStage().stage, "home");

  sandbox.window.location.pathname = "/HkdOnline/Forms/APP/Registration.aspx";
  lists.clear();
  ids.set("ctl00_C_myWizard_CtlType", domNode());
  assert.equal(H.detectBusinessCreateStage().stage, "select-registration");

  ids.clear();
  ids.set("ctl00_C_myWizard_FinishNavigationTemplateContainerID_FinishButton", domNode("Bắt đầu"));
  ids.set("ctl00_C_myWizard_InfoChnType", domNode("Thành lập mới hộ kinh doanh"));
  const confirmation = H.detectBusinessCreateStage();
  assert.equal(confirmation.stage, "confirm");
  assert.match(confirmation.confirmedType, /thanh lap moi/);

  ids.clear();
  const sitemap = domNode();
  sitemap.querySelectorAll = () => [domNode("Khối dữ liệu")];
  selectors.set("#ctl00_LV4_SiteMapPath1", sitemap);
  ids.set("ctl00_C_INFOCtl_DOCUMENT_TYPE_IDFld", domNode("Thành lập mới hộ kinh doanh"));
  ids.set("ctl00_C_BLCtl_LblFilterExpand_DB", domNode("Khối dữ liệu"));
  ids.set("ctl00_C_BLCtl_CtlList", domNode("Hình thức đăng ký Địa chỉ"));
  sandbox.window.location.pathname = "/HkdOnline/Forms/APP/DW_DOCUMENTEdit.aspx";
  assert.equal(H.detectBusinessCreateStage().stage, "main-root");
  assert.equal(H.detectBusinessProcedureHint(), "create");
});

test("bootstrap chỉ chọn NEW và kiểm tra xác nhận trước khi bấm Bắt đầu", () => {
  assert.match(source, /BUSINESS_CREATE_STEP_DELAY_MS = 2500/);
  assert.equal((source.match(/await waitCreateBootstrapStep\(/g) || []).length, 3);
  assert.match(source, /detected\.stage === "home"[\s\S]*?doAspPostback\(postback\[1\], postback\[2\]\)/);
  assert.match(source, /doAspPostback\("ctl00\$LV3\$mCon", "bĐăng ký Hộ kinh doanh"\)/);
  assert.match(source, /st\.homeTries > 3/);
  assert.match(source, /CtlType\"\]\[value=\"NEW\"\]/);
  assert.match(source, /detected\.confirmedType[\s\S]*?includes\("thanh lap moi"\)/);
  assert.match(source, /Bước xác nhận không hiển thị Thành lập mới hộ kinh doanh/);
  assert.match(source, /st\.workflow === "create" && !st\.bootstrapDone/);
  assert.match(source, /bootstrapOnly/);
});

test("đăng ký mới điền chủ hộ thẳng từ giấy đề nghị, không sao chép tài khoản", () => {
  const copyConfig = source.slice(
    source.indexOf("const COPY_PERSON_CFG"),
    source.indexOf("const OWNER_PAGE_CFG")
  );
  assert.match(copyConfig, /"nguoi-nop-ho-so"/);
  assert.doesNotMatch(copyConfig, /"chu-ho-kinh-doanh"/);

  const ownerHandler = source.slice(
    source.indexOf("async function handleOwnerPage"),
    source.indexOf("async function handleCopyPersonPage")
  );
  assert.doesNotMatch(ownerHandler, /btnIS_SIGNER/);
  assert.match(ownerHandler, /st\.workflow === "change"[\s\S]*?handleChangeOwnerPage/);
  assert.match(ownerHandler, /fillFormStandard\(structural\)/);
  assert.match(ownerHandler, /fillAddressCascade\(address\)/);
  assert.match(ownerHandler, /clickSaveDetectReload\(saveBtn\)/);
  assert.equal((ownerHandler.match(/applyOwnerFromDossier\(fields\)/g) || []).length, 2);
  assert.ok(
    ownerHandler.indexOf("applyOwnerFromDossier(fields)")
      < ownerHandler.indexOf("fillAddressCascade(address)")
  );
  assert.ok(
    ownerHandler.lastIndexOf("applyOwnerFromDossier(fields)")
      > ownerHandler.indexOf("fillAddressCascade(address)")
  );

  assert.match(source, /targetKey === "chu-ho-kinh-doanh"[\s\S]*?handleOwnerPage\(st\)/);
  assert.match(source, /targetKey === "nguoi-nop-ho-so"[\s\S]*?handleCopyPersonPage\(st, targetKey\)/);
  assert.match(source, /if \(el\.disabled\) el\.disabled = false/);
  assert.match(source, /if \(el\.readOnly\) el\.readOnly = false/);
});

test("default địa bàn được chèn hoặc ghi đè đúng ô người nộp hồ sơ", () => {
  const { H } = loadCore();
  const value = "Trung tâm Phục vụ hành chính công phường Hải Châu";

  const inserted = H.applyBusinessLocalDefaults(
    [], { postalServiceAddress: value }, "nguoi-nop-ho-so"
  );
  assert.deepEqual(JSON.parse(JSON.stringify(inserted)), [{
    name: "ctl00$C$POSTAL_SERVICEFld",
    comp: "dom-input",
    value,
  }]);

  const overwritten = H.applyBusinessLocalDefaults([{
    name: "ctl00$C$POSTAL_SERVICEFld",
    comp: "dom-input",
    value: "giá trị cũ",
  }], { postalServiceAddress: value }, "nguoi-nop-ho-so");
  assert.equal(overwritten.length, 1);
  assert.equal(overwritten[0].value, value);

  assert.deepEqual(
    JSON.parse(JSON.stringify(H.applyBusinessLocalDefaults([], {
      postalServiceAddress: value,
    }, "chu-ho-kinh-doanh"))),
    []
  );
});

test("HkdOnline giữ casing ngành nghề và không bỏ qua nút Lưu bị khóa", () => {
  assert.match(source, /function capitalizeBusinessLineName\(value\)/);
  assert.match(source, /const name = capitalizeBusinessLineName\(/);
  assert.match(source, /const current = String\(desc\.value \|\| ""\)\.trim\(\)/);
  assert.doesNotMatch(source, /const current = norm\(desc\.value\)/);

  const submitterHandler = source.slice(
    source.indexOf("async function handleCopyPersonPage"),
    source.indexOf("async function handleChangeOwnerPage")
  );
  assert.match(submitterHandler, /localDefaultFieldsFor\(st\.businessDefaults, targetKey\)/);
  assert.match(submitterHandler, /const hadChanges = fields\.length > 0 \|\| !!submitterOverride/);
  assert.match(submitterHandler, /saveBtn\.removeAttribute\("disabled"\)/);

  const genericHandler = source.slice(
    source.indexOf("const pageFields = applyBusinessLocalDefaults"),
    source.indexOf("ĐÍNH KÈM HỘ KINH DOANH")
  );
  assert.match(genericHandler, /if \(!pageFields\.length\) return void advanceFillAll\(st\)/);
  assert.match(genericHandler, /saveBtn\.removeAttribute\("disabled"\)/);
});

test("fallback vai trò người nộp và menu đính kèm theo nhãn hiển thị", () => {
  assert.match(source, /function findSubmitterRoleRadio\(authorized\)/);
  assert.match(source, /const authRadio = findSubmitterRoleRadio\(true\)/);
  assert.match(source, /const selfRadio = findSubmitterRoleRadio\(false\)/);
  assert.match(source, /nguoi duoc uy quyen/);
  assert.match(source, /nguoi co tham quyen ky/);

  const attachLinks = source.slice(
    source.indexOf("function attachTypeLinks"),
    source.indexOf("function clickAttachTypeLink")
  );
  assert.match(attachLinks, /Object\.values\(ATTACH_TYPE\)/);
  assert.match(attachLinks, /querySelectorAll\("\.left-menu a"\)/);
  assert.match(attachLinks, /labels\.includes\(foldBusinessPageText\(link\.textContent\)\)/);
});

test("manifest nạp adapter trước lõi HkdOnline và cấp quyền đúng host", () => {
  const scripts = manifest.content_scripts[0].js;
  const adapterIndex = scripts.indexOf("content/business-registration-adapter.js");
  const coreIndex = scripts.indexOf("content/procedures/business-registration.js");

  assert.ok(adapterIndex > scripts.indexOf("content/attach-core.js"));
  assert.ok(coreIndex > adapterIndex);
  assert.ok(manifest.host_permissions.includes("https://hokinhdoanh.dkkd.gov.vn/*"));
});

test("Handfree dùng một action cho 8 khối + attach và có recovery qua storage", () => {
  assert.match(adapter, /action === "startBusinessRegistration"/);
  assert.match(adapter, /attachPayload: files\.length && attachments\.length/);
  assert.match(adapter, /getBusinessRuntimeContext/);
  assert.match(adapter, /businessFlowFinished/);
  assert.match(adapter, /H\.getFillAllState/);
  assert.match(adapter, /H\.getAttachAllState/);
  assert.match(adapter, /clearBusinessRegistrationState/);
  assert.match(adapter, /H\.clearFillAllState/);
  assert.match(adapter, /H\.clearAttachAllState/);
  assert.match(adapter, /H\.cancelBusinessRegistrationRun/);
  assert.match(adapter, /businessRunFinalizing/);
  assert.match(source, /H\.isBusinessRunCancelled\?\.\(\)/);
  assert.match(sidebar, /a\.type === "start_business_registration"/);
  assert.match(sidebar, /__action:business_report/);
  assert.match(sidebar, /d\.type === "business_ready"/);
  assert.match(sidebar, /action: "clearBusinessRegistrationState"/);
});

test("Kết thúc hoặc dừng đều gửi snapshot tiến độ vào nội dung chat", () => {
  assert.match(adapter, /function progressReport\(run/);
  assert.match(adapter, /filledPages/);
  assert.match(adapter, /currentPage/);
  assert.match(adapter, /attachmentStarted/);
  assert.match(adapter, /attachmentCompleted/);
  assert.match(adapter, /uploadedAttachments/);
  assert.match(adapter, /clearBusinessRun\(\{ preserveResult: true \}\)/);
  assert.match(adapter, /notify\(\{ type: "businessFlowFinished", report \}\)/);
  assert.match(sidebar, /const isFullRun = report\.mode === "full"/);
  assert.doesNotMatch(sidebar, /if \(lastState === "filling"\) \{\s*ask\(`__action:business_report/);
});

test("Kết quả HkdOnline chờ khôi phục đúng conversation và giữ journey sống qua postback", () => {
  assert.match(content, /H\.persistPageActivity = persistPageActivity/);
  assert.match(adapter, /function touchBusinessActivity\(\)/);
  assert.match(adapter, /H\.persistPageActivity\?\.\(\)/);
  assert.match(adapter, /setTimeout\(async \(\) => \{\s*touchBusinessActivity\(\)/);
  assert.match(sidebar, /async function waitForChatBoot\(timeoutMs = 10000\)/);
  assert.match(sidebar, /const restored = await waitForChatBoot\(\)/);
  assert.match(sidebar, /if \(!restored\)[\s\S]*?return;[\s\S]*?__action:business_report/);
  assert.match(sidebar, /finally \{[\s\S]*?chatBootFinished = true/);
});

test("Handfree ẩn sidebar nặng qua postback và chỉ giữ thẻ tiến độ có nút dừng", () => {
  assert.match(content, /BUSINESS_PROGRESS_ID = "tro-ly-nguoi-dan-business-progress"/);
  assert.match(content, /BUSINESS_RUN_KEY = "tlnd_business_registration_run"/);
  assert.match(content, /position: "fixed"[\s\S]*?contain: "layout style"/);
  assert.match(content, /attachShadow\(\{ mode: "open" \}\)/);
  assert.match(content, /Dừng tiến trình/);
  assert.match(content, /min-height: 44px/);
  assert.match(content, /prefers-reduced-motion: reduce/);
  assert.match(content, /transform: scaleX/);
  assert.match(content, /panel\.style\.display = "none"/);
  assert.match(content, /releaseSidebarLayoutWithoutMotion/);
  assert.match(content, /chrome\.storage\.local\.get\(\[BUSINESS_RUN_KEY\]/);
  assert.match(content, /H\.finishBusinessRunUI = finishBusinessRunUI/);
});

test("Tiêu đề tiến độ phân biệt mở trang với kê khai và đính kèm", () => {
  assert.match(content, /phase === "bootstrap"[\s\S]*?Đang tự động mở trang kê khai/);
  assert.match(content, /Đang tự động kê khai thông tin và đính kèm/);
  assert.match(adapter, /businessProgressPhaseHint = "bootstrap"/);
  assert.match(adapter, /progressPhase: "bootstrap"/);
  assert.match(adapter, /progressPhase: businessProgressPhaseHint/);
  assert.doesNotMatch(content, /let title = "Đang tự động kê khai"/);
});

test("Handfree hủy banner xanh và state machine Auto-fill cũ khi bắt đầu", () => {
  assert.match(content, /LEGACY_AUTOFILL_PROGRESS_ID = "af-fillall-progress"/);
  assert.match(content, /LEGACY_AUTOFILL_CANCEL_ID = "af-fillall-progress-cancel"/);
  assert.match(content, /function cancelLegacyAutoFillBusinessRun\(\)/);
  assert.match(content, /cancel\.click\(\)/);
  assert.match(content, /legacy\.remove\(\)/);
  assert.match(content, /new MutationObserver\(\(\) => cancelLegacyAutoFillBusinessRun\(\)\)/);
  assert.match(content, /watchAndCancelLegacyAutoFillBusinessRun\(\);[\s\S]*?normalizeBusinessProgress/);
  assert.match(content, /stopLegacyAutoFillProgressWatcher\(\);[\s\S]*?clearBusinessProgressMirror/);
});

test("Đính kèm tự khai lại loại khi sidebar HkdOnline chưa dựng CtlAttList", () => {
  assert.match(source, /ATTACH_LIST_RELOAD_LIMIT = 2/);
  assert.match(source, /ATTACH_DECLARE_RECOVERY_LIMIT = 2/);
  assert.match(source, /waitForAttachModalData\(sel, st\)/);
  assert.match(source, /syncDeclaredFromModal\(st\)/);
  assert.match(source, /closeAttachModal\(\{ refreshList: true \}\)/);
  assert.match(source, /st\.forceDeclareRecovery = true/);
  assert.match(source, /st\.declared = \[\]/);
  assert.match(source, /Sidebar chưa hiển thị loại tài liệu\. Em đang kiểm tra và khai lại/);
  assert.doesNotMatch(source, /✓ Đã khai loại\. Hãy bấm 1 mục trong danh sách/);
});
