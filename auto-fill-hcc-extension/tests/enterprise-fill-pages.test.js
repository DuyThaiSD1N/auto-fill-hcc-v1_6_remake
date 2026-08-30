// Engine điền 7 trang khối dữ liệu của cổng ĐKKD qua mạng.
//
// Điểm chốt quan trọng nhất: KEY TRANG giữa backend (schema.py) và extension (PAGE_SPEC) phải TRÙNG
// TUYỆT ĐỐI. Backend trả field theo key, engine tra field theo key — lệch một ký tự thì mọi trang đều
// "không có field để điền" mà KHÔNG có lỗi nào hiện ra, cực khó lần.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const SOURCE = fs.readFileSync(
  path.join(root, "content", "procedures", "enterprise-registration.js"),
  "utf8",
);

function makeSandbox(nodes, store, pathname = "/online/Forms/APP/DW_DOCUMENTEdit.aspx") {
  const sandbox = {
    console: { log() {}, warn() {}, error() {} },
    Event: class { constructor(type) { this.type = type; } },
    CSS: { escape: (v) => v },
    setTimeout,
    clearTimeout,
    setInterval: () => 0,
    clearInterval: () => {},
    getComputedStyle: () => ({ display: "block", visibility: "visible" }),
    chrome: {
      storage: {
        local: {
          async get(key) { return key in store ? { [key]: store[key] } : {}; },
          async set(patch) { Object.assign(store, patch); },
          async remove(key) {
            for (const k of Array.isArray(key) ? key : [key]) delete store[k];
          },
        },
      },
    },
    document: {
      readyState: "complete",
      body: { innerText: "Khối dữ liệu Hình thức đăng ký" },
      addEventListener() {},
      querySelector: (sel) => nodes.find((n) => n.matchesSelector(sel)) || null,
      querySelectorAll: (sel) => sel.split(",").map((s) => s.trim())
        .flatMap((s) => nodes.filter((n) => n.matchesSelector(s))),
    },
  };
  sandbox.window = sandbox;
  // clickSaveDetectReload gắn beforeunload/pagehide lên window để biết cổng có postback hay không.
  sandbox.addEventListener = () => {};
  sandbox.removeEventListener = () => {};
  sandbox.sessionStorage = { getItem: () => null, setItem() {}, removeItem() {} };
  sandbox.location = { hostname: "dangkyquamang.dkkd.gov.vn", pathname };
  sandbox.top = sandbox;
  // Ghi lại lời gọi để test kiểm chứng engine có thật sự điền/khởi động UI tiến độ hay không.
  sandbox.__HCC__ = {
    filled: [],
    progressTexts: [],
    beganFillUI: false,
    fillFormStandard: async (fields) => { sandbox.__HCC__.filled.push(fields); },
    beginFillAllUI: () => { sandbox.__HCC__.beganFillUI = true; },
    endFillAllUI: (text) => { sandbox.__HCC__.progressTexts.push(text); },
    setRunProgressText: (text) => { sandbox.__HCC__.progressTexts.push(text); },
    showPageToast: () => {},
  };
  vm.runInNewContext(SOURCE, sandbox, { filename: "enterprise-registration.js" });
  return sandbox;
}

/** Node giả khớp được các dạng selector mà engine dùng: [name="x"], [name^="x"], tag, input[type=x]. */
function node(spec) {
  const self = {
    tagName: (spec.tag || "input").toUpperCase(),
    type: spec.type || "",
    name: spec.name || "",
    value: spec.value || "",
    textContent: spec.textContent || "",
    id: spec.id || "",
    htmlFor: spec.htmlFor || "",
    disabled: !!spec.disabled,
    isConnected: true,
    clicks: 0,
    getBoundingClientRect: () => ({ width: 100, height: 20 }),
    scrollIntoView() {},
    closest: () => null,
    dispatchEvent: () => true,
    click() { self.clicks += 1; },
    matchesSelector(sel) {
      const tag = (sel.match(/^[a-z]+/i) || [""])[0].toLowerCase();
      if (tag && self.tagName.toLowerCase() !== tag) return false;
      const exact = sel.match(/\[name="([^"]+)"\]/);
      if (exact && self.name !== exact[1]) return false;
      const prefix = sel.match(/\[name\^="([^"]+)"\]/);
      if (prefix && !self.name.startsWith(prefix[1])) return false;
      const type = sel.match(/\[type="?([a-z]+)"?\]/i);
      if (type && self.type !== type[1]) return false;
      // Radio vai trò được chọn bằng [value="..."] — thiếu nhánh này thì mọi radio cùng name đều
      // khớp và test đậu giả (luôn trúng radio đầu tiên).
      const value = sel.match(/\[value="([^"]+)"\]/);
      if (value && self.value !== value[1]) return false;
      return true;
    },
  };
  // Trình duyệt thật tự BỎ TICK các radio cùng name khi gán checked = true. Không mô phỏng thì test
  // không thấy được lỗi "tick đè ngược" — cả hai radio cùng bật một lúc mà vẫn đậu.
  let checked = !!spec.checked;
  Object.defineProperty(self, "checked", {
    get: () => checked,
    set(value) {
      checked = !!value;
      if (!checked || !self.group) return;
      for (const sibling of self.group) if (sibling !== self) sibling.checked = false;
    },
  });
  return self;
}

/** Gắn quan hệ nhóm cho các radio cùng name (phải gọi sau khi tạo đủ node). */
function groupRadios(nodes) {
  const radios = nodes.filter((n) => n.type === "radio");
  for (const radio of radios) radio.group = radios;
  return nodes;
}

// ---- 1. Key trang backend == key trang extension ----
const schemaSource = fs.readFileSync(
  path.join(root, "..", "auto-fill-hcc-backend", "app", "pipelines", "thanh_lap_ctcp",
    "process", "schema.py"),
  "utf8",
);
const pagesBlock = schemaSource.slice(
  schemaSource.indexOf("PAGES: list[dict] = ["),
  schemaSource.indexOf("DEFAULT_PAGE"),
);
const backendKeys = [...pagesBlock.matchAll(/\{"key":\s*"([^"]+)"/g)].map((m) => m[1]);

const sandbox = makeSandbox([], {});
const feKeys = Object.keys(sandbox.__HCC__.enterpriseFillPageSpec);

assert.deepEqual(
  feKeys, backendKeys,
  "PAGE_SPEC của extension phải trùng ĐÚNG THỨ TỰ và ĐÚNG TÊN với PAGES trong schema.py của backend",
);
// 7 trang có đặc tả field + trang "Hình thức đăng ký" đứng đầu (chỉ cần bấm Lưu để mở luồng).
assert.equal(backendKeys.length, 8, "Khối dữ liệu chạy 8 trang");
assert.equal(backendKeys[0], "hinh-thuc-dang-ky", "Hình thức đăng ký phải là trang ĐẦU TIÊN");

// ---- 2. Nút Lưu KHÔNG đồng nhất giữa các trang — chốt theo bảng đặc tả ----
const spec = sandbox.__HCC__.enterpriseFillPageSpec;
assert.equal(spec["dia-chi"].save, "ctl00$C$btnSave");
assert.equal(spec["ten-doanh-nghiep"].save, "ctl00$C$BtnSave", "Trang Tên doanh nghiệp dùng BtnSave (B hoa)");
assert.equal(spec["nganh-nghe-kinh-doanh"].save, "ctl00$C$BtnSaveNotVSIC", "Trang Ngành nghề có nút Lưu riêng");

// ---- 3. Nhận diện trang theo control đặc trưng, không theo breadcrumb ----
const onNamePage = makeSandbox([node({ name: "ctl00$C$NAMEFld" })], {});
assert.equal(onNamePage.__HCC__.currentEnterpriseFillPage(), "ten-doanh-nghiep");

const onCapitalPage = makeSandbox(
  [node({ name: "ctl00$C$UC_DW_CAPITALEditCtl$CPT_CHARTER_AMOUNTFld" })], {},
);
assert.equal(onCapitalPage.__HCC__.currentEnterpriseFillPage(), "thong-tin-ve-von",
  "Trang vốn nhận theo tiền tố UC_DW_CAPITALEditCtl");

const onWizard = makeSandbox([node({ name: "ctl00$C$myWizard$CtlType", type: "radio" })], {},
  "/online/Forms/APP/Registration.aspx");
assert.equal(onWizard.__HCC__.currentEnterpriseFillPage(), null,
  "Còn ở wizard thì KHÔNG được coi là trang khối dữ liệu");
assert.equal(onWizard.__HCC__.isInEnterpriseDossier(), false);

// Trang GỐC khối dữ liệu (khối "Thông tin về hồ sơ") KHÔNG có control của 7 trang con. Phải coi là
// ĐÃ vào hồ sơ, nếu không thì đứng ở đây sẽ bị hiểu nhầm là còn ở wizard và chạy lại wizard.
const onDossierRoot = makeSandbox([], {});
assert.equal(onDossierRoot.__HCC__.currentEnterpriseFillPage(), null);
assert.equal(onDossierRoot.__HCC__.isInEnterpriseDossier(), true,
  "Trang gốc khối dữ liệu phải tính là đã vào hồ sơ");

// ---- 4. Chưa vào hồ sơ thì từ chối chạy, không điền bừa ----
(async () => {
  const pagesPayload = {
    "dia-chi": [{ name: "ctl00$C$ADDRCtl$STREET_NUMBERFld", comp: "dom-input", value: "1 A" }],
  };
  const refused = await onWizard.__HCC__.startEnterpriseFillAll({ pages: pagesPayload });
  assert.ok(refused.error, "Không có dữ liệu wizard thì phải báo lỗi, không điền bừa lên trang wizard");

  // Còn ở wizard NHƯNG popup gửi kèm dữ liệu wizard → lượt bấm phải MỞ HỒ SƠ, không được báo lỗi
  // rồi bắt cán bộ bấm lại (đây chính là lỗi "bấm mãi không vào được" đã gặp trên cổng thật).
  const wizardStore = {};
  const onWizard2 = makeSandbox([node({ name: "ctl00$C$myWizard$CtlType", type: "radio" })],
    wizardStore, "/online/Forms/APP/Registration.aspx");
  const opening = await onWizard2.__HCC__.startEnterpriseFillAll({
    pages: pagesPayload,
    enterpriseFlow: { registrationType: "NEW", entityLabel: "Công ty cổ phần", entityValue: "SC" },
  });
  assert.ok(opening.openingDossier, "Có dữ liệu wizard thì phải tự mở hồ sơ");
  assert.ok(wizardStore.autofill_enterprise_autostart, "Phải đặt cờ chạy wizard");
  assert.equal(wizardStore.autofill_enterprise_autostart.entityValue, "SC");

  // ---- 5. Backend không trả trang nào → dừng có kiểm soát ----
  const onAddr = makeSandbox([node({ name: "ctl00$C$ADDRCtl$STREET_NUMBERFld" })], {});
  const empty = await onAddr.__HCC__.startEnterpriseFillAll({ pages: {} });
  assert.ok(empty.error, "Không có field thì không được bật state machine");

  // ---- 6. Chạy được thì chỉ nhận đúng các trang backend có field ----
  const store = {};
  const onAddr2 = makeSandbox([node({ name: "ctl00$C$ADDRCtl$STREET_NUMBERFld" })], store);
  const started = await onAddr2.__HCC__.startEnterpriseFillAll({
    pages: {
      "dia-chi": [{ name: "ctl00$C$ADDRCtl$STREET_NUMBERFld", comp: "dom-input", value: "189 Dũng Sĩ" }],
      "thong-tin-ve-thue": [{ name: "x", comp: "dom-input", value: "y" }],
    },
  });
  assert.equal(started.pages, 2, "Chỉ đưa vào order những trang backend thật sự có field");
  // Spread để so trong CÙNG realm: mảng sinh ra trong vm có Array.prototype khác, deepStrictEqual
  // sẽ báo lệch dù nội dung giống hệt.
  assert.deepEqual([...store.autofill_enterprise_fillall.order], ["dia-chi", "thong-tin-ve-thue"],
    "Order phải theo thứ tự PAGE_SPEC, không theo thứ tự key backend trả về");

  assert.deepEqual([...store.autofill_enterprise_fillall.done], [],
    "Mới bắt đầu thì chưa trang nào được đánh dấu xong");

  // ---- 7. Đứng sẵn ở một trang có dữ liệu → điền NGAY trang đó, không đòi khớp trang mục tiêu ----
  // Đây đúng tình huống trên cổng thật: cán bộ/cổng đang mở "Thông tin về vốn" trong khi thứ tự bắt
  // đầu từ "Địa chỉ". Bản cũ bỏ qua vì trang hiện tại khác trang mục tiêu.
  const capitalStore = {};
  const capitalNodes = [
    node({ name: "ctl00$C$UC_DW_CAPITALEditCtl$CPT_CHARTER_AMOUNTFld" }),
    node({ tag: "input", type: "submit", name: "ctl00$C$btnSave", value: "Lưu" }),
  ];
  const onCapital = makeSandbox(capitalNodes, capitalStore);
  await onCapital.__HCC__.startEnterpriseFillAll({
    pages: {
      "dia-chi": [{ name: "ctl00$C$ADDRCtl$STREET_NUMBERFld", comp: "dom-input", value: "189" }],
      "thong-tin-ve-von": [
        { name: "ctl00$C$UC_DW_CAPITALEditCtl$CPT_CHARTER_AMOUNTFld", comp: "dom-input", value: "5000000000" },
      ],
    },
  });
  // Engine chờ 500ms sau khi điền (cho cascade/postback lắng) rồi mới bấm Lưu → phải chờ dài hơn.
  await new Promise((resolve) => setTimeout(resolve, 1000));

  assert.equal(onCapital.__HCC__.beganFillUI, true, "Phải bật UI tiến độ khi bắt đầu điền");
  assert.equal(onCapital.__HCC__.filled.length, 1, "Phải điền đúng một lượt cho trang đang đứng");
  assert.equal([...onCapital.__HCC__.filled[0]][0].name,
    "ctl00$C$UC_DW_CAPITALEditCtl$CPT_CHARTER_AMOUNTFld",
    "Phải điền field của TRANG ĐANG ĐỨNG (vốn), không phải trang đầu danh sách (địa chỉ)");
  assert.equal(capitalNodes[1].clicks, 1, "Điền xong phải bấm Lưu");
  assert.deepEqual([...capitalStore.autofill_enterprise_fillall.done], ["thong-tin-ve-von"],
    "Trang vừa điền phải được đánh dấu xong để nhịp sau không điền lại");

  // ---- 8. Nút Lưu đang DISABLED: phải chờ nó bật rồi mới bấm ----
  // Cổng để Lưu mờ tới khi form có thay đổi hợp lệ; validator chạy sau sự kiện change nên ngay sau
  // khi điền nút vẫn disabled. Bản cũ kiểm một phát rồi bỏ qua -> mất luôn bước lưu.
  const lateStore = {};
  const lateSave = node({ tag: "input", type: "submit", name: "ctl00$C$btnSave", value: "Lưu", disabled: true });
  const lateNodes = [node({ name: "ctl00$C$NAMEFld" }), lateSave];
  const onLate = makeSandbox(lateNodes, lateStore);
  await onLate.__HCC__.startEnterpriseFillAll({
    pages: { "ten-doanh-nghiep": [{ name: "ctl00$C$NAMEFld", comp: "dom-input", value: "ABC" }] },
  });
  await new Promise((resolve) => setTimeout(resolve, 800));
  assert.equal(lateSave.clicks, 0, "Nút còn disabled thì chưa được bấm");
  lateSave.disabled = false;                       // cổng bật nút sau khi validator chạy
  await new Promise((resolve) => setTimeout(resolve, 900));
  assert.equal(lateSave.clicks, 1, "Nút vừa bật là phải bấm Lưu, không bỏ qua trang");

  // ---- 9. Trang con của khối dữ liệu là file .aspx RIÊNG, vẫn phải tính là đang ở trong hồ sơ ----
  const onSubPage = makeSandbox([node({ name: "ctl00$C$newBusinessLineCode" })], {},
    "/online/Forms/APP/DW_ENT_BUSINESS_LINE_VWListingInsUpd.aspx");
  assert.equal(onSubPage.__HCC__.isInEnterpriseDossier(), true,
    "DW_ENT_*.aspx (trang con) phải tính là đã vào hồ sơ");

  // ---- 10. Nhận diện trang theo ĐƯỜNG DẪN THẬT (tên file .aspx không theo quy tắc nào) ----
  // Địa chỉ = Address_of_head_office.aspx, Tên doanh nghiệp = EnterpriseName.aspx — không có tiền
  // tố DW_ như trang ngành nghề. Đoán theo tên file kiểu "DW_*" là sai hai trang này.
  const byPath = [
    ["/online/Forms/APP/Address_of_head_office.aspx", "dia-chi"],
    ["/online/Forms/APP/EnterpriseName.aspx", "ten-doanh-nghiep"],
    ["/online/Forms/APP/DW_ENT_BUSINESS_LINE_VWListingInsUpd.aspx", "nganh-nghe-kinh-doanh"],
  ];
  for (const [pathname, expected] of byPath) {
    const sb = makeSandbox([], {}, pathname);   // KHÔNG có control nào — chỉ dựa vào đường dẫn
    assert.equal(sb.__HCC__.currentEnterpriseFillPage(), expected, `Sai trang cho ${pathname}`);
    assert.equal(sb.__HCC__.isInEnterpriseDossier(), true, `${pathname} phải tính là trong hồ sơ`);
  }

  // Wizard KHÔNG bao giờ được coi là trang hồ sơ, kể cả khi text trang có chữ giống menu.
  const wizardAgain = makeSandbox([], {}, "/online/Forms/APP/Registration.aspx");
  assert.equal(wizardAgain.__HCC__.isInEnterpriseDossier(), false);

  // ---- 11. Trang "Người nộp hồ sơ": chốt vai trò theo TÀI KHOẢN ĐANG ĐĂNG NHẬP ----
  // Cơ chế port từ thủ tục hộ kinh doanh: nhờ cổng đổ nhân thân tài khoản xuống trước (nút "Sao chép
  // thông tin đăng ký tài khoản"), rồi đối chiếu với CCCD trong hồ sơ. Khớp -> người có thẩm quyền
  // ký; KHÔNG khớp -> người được ủy quyền.
  async function runSubmitterPage({ accountName, accountDocNo, candidates }) {
    const radioSelf = node({ type: "radio", name: "ctl00$C$PERS_SUBGroup", value: "IS_REPRESENTATIVE_BUTTON", checked: true });
    const radioAuth = node({ type: "radio", name: "ctl00$C$PERS_SUBGroup", value: "IS_AUTHORIZED_BUTTON" });
    const nodes = [
      radioSelf,
      radioAuth,
      node({ name: "ctl00$C$PERSCtl$FULL_NAMEFld", value: accountName }),
      node({ name: "ctl00$C$PERSCtl$PERS_DOC_NOFld", value: accountDocNo }),
      node({ tag: "input", type: "submit", name: "ctl00$C$btnSave", value: "Lưu" }),
    ];
    groupRadios(nodes);
    const sb = makeSandbox(nodes, {}, "/online/Forms/APP/ContactPerson.aspx");
    await sb.__HCC__.startEnterpriseFillAll({
      pages: {
        "nguoi-nop-ho-so": [
          // Mapper LUÔN phát sẵn vai trò mặc định; engine phải loại nó ra, nếu không nhánh điền
          // chung sẽ tick đè ngược lại ngay sau khi engine vừa chọn "được ủy quyền".
          { name: "ctl00$C$PERS_SUBGroup", comp: "dom-radio", value: "IS_REPRESENTATIVE_BUTTON" },
          { name: "ctl00$C$PERSCtl$PHONEFld", comp: "dom-input", value: "0987147714" },
          { name: "__identityCandidates", comp: "raw", value: candidates },
        ],
      },
    });
    await new Promise((resolve) => setTimeout(resolve, 1200));
    return { radioSelf, radioAuth, filled: sb.__HCC__.filled };
  }

  const cards = [{ fullName: "Bùi Thị Phương Hạnh", docNo: "049184011649", address: {} }];

  const asSelf = await runSubmitterPage({
    accountName: "Bùi Thị Phương Hạnh", accountDocNo: "049184011649", candidates: cards,
  });
  assert.equal(asSelf.radioSelf.checked, true, "Tài khoản trùng CCCD trong hồ sơ -> người có thẩm quyền ký");
  assert.equal(asSelf.radioAuth.checked, false);

  assert.ok(
    !asSelf.filled.flat().some((f) => String(f.name).includes("PERS_SUBGroup")),
    "Vai trò do engine quyết định — không được để lọt vào danh sách điền chung (gây tick đè ngược)",
  );

  const asAuthorized = await runSubmitterPage({
    accountName: "Nguyễn Duy Thái", accountDocNo: "036192014693", candidates: cards,
  });
  assert.equal(asAuthorized.radioAuth.checked, true,
    "Tài khoản KHÔNG có trong hồ sơ -> phải chuyển sang người được ủy quyền");
  assert.equal(asAuthorized.radioSelf.checked, false,
    "Chọn xong KHÔNG được tick đè ngược về người có thẩm quyền ký");
  // Khối nhân thân/địa chỉ ở trang này là của CHÍNH tài khoản đang đăng nhập; cổng ghi đè lại khi
  // lưu nên điền dữ liệu người khác vào là vô ích và làm sai hồ sơ.
  assert.deepEqual(asAuthorized.filled.flat().map((f) => f.name), [],
    "Tài khoản khác người trong hồ sơ -> KHÔNG được điền gì cả");

  // Hồ sơ không có CCCD nào để đối chiếu -> GIỮ mặc định của cổng, không đoán bừa vai trò.
  const noCards = await runSubmitterPage({
    accountName: "Nguyễn Duy Thái", accountDocNo: "036192014693", candidates: [],
  });
  assert.equal(noCards.radioSelf.checked, true, "Không có căn cứ thì không được đổi vai trò");
  assert.equal(noCards.radioAuth.checked, false);

  // ---- 12. Điền xong thì BÀN GIAO sang engine đính kèm dùng chung với hộ kinh doanh ----
  // Hai cổng dùng chung component đính kèm (icon ⚙ BLCtl_ImgAttachmentSettings, modal #attId/#tblAtt,
  // ô #FileUploadCtl) nên không viết lại state machine; chỉ khác tiền tố ClientID.
  const attachStore = {};
  const attachSave = node({ tag: "input", type: "submit", name: "ctl00$C$btnSave", value: "Lưu" });
  const attachSandbox = makeSandbox([node({ name: "ctl00$C$NAMEFld" }), attachSave], attachStore);
  const handoff = [];
  attachSandbox.__HCC__.startAttachAllBusiness = async (files, attachments) => {
    handoff.push({ files, attachments });
  };
  attachSandbox.__HCC__.stepAttachAll = () => {};
  await attachSandbox.__HCC__.startEnterpriseFillAll({
    pages: { "ten-doanh-nghiep": [{ name: "ctl00$C$NAMEFld", comp: "dom-input", value: "ABC" }] },
    attachPayload: {
      files: [{ name: "a.pdf", dataUrl: "data:application/pdf;base64,AA" }],
      attachments: [{ fileIndex: 0, fileName: "a.pdf", category: "ENTREGFRM",
                      componentName: "Giấy đề nghị đăng ký doanh nghiệp" }],
    },
  });
  // Điền (500ms) + clickSaveDetectReload chờ hết 2600ms vì DOM giả không "tải lại trang" -> phải
  // chờ dài hơn tổng đó mới tới được finishFill.
  await new Promise((resolve) => setTimeout(resolve, 4000));
  assert.equal(handoff.length, 1, "Điền xong phải bàn giao sang engine đính kèm");
  assert.equal([...handoff[0].attachments][0].category, "ENTREGFRM");
  assert.equal(attachStore.autofill_enterprise_fillall, undefined,
    "Bàn giao rồi phải dọn state điền, không để state machine chạy lại");

  console.log("enterprise-fill-pages: bàn giao đính kèm + vai trò người nộp + URL thật + chờ nút Lưu passed");
})();
