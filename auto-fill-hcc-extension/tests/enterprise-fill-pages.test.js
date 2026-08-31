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
      // append được: engine có lúc dựng banner thật bằng createElement + appendChild.
      body: {
        innerText: "Khối dữ liệu Hình thức đăng ký",
        appendChild: (el) => { nodes.push(el); return el; },
      },
      documentElement: { appendChild: (el) => { nodes.push(el); return el; } },
      createElement: (tag) => {
        const el = {
          tagName: String(tag).toUpperCase(), style: {}, id: "", type: "", name: "", value: "",
          textContent: "", className: "", children: [], handlers: {},
          append(...kids) { el.children.push(...kids); },
          appendChild(kid) { el.children.push(kid); return kid; },
          addEventListener(type, fn) { el.handlers[type] = fn; },
          remove() { const i = nodes.indexOf(el); if (i >= 0) nodes.splice(i, 1); },
          getBoundingClientRect: () => ({ width: 100, height: 20 }),
          matchesSelector: () => false,   // banner của trợ lý không được coi là control của cổng
        };
        return el;
      },
      addEventListener() {},
      getElementById: (id) => nodes.find((n) => n.id === id) || null,
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
    toasts: [],
    showPageToast: (message, kind) => { sandbox.__HCC__.toasts.push({ message, kind }); },
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
    className: spec.className || "",
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
      // Selector theo class: thiếu nhánh này thì MỌI node đều khớp và test đậu giả.
      const cls = sel.match(/^\.([\w-]+)/);
      if (cls && !String(self.className || "").split(/\s+/).includes(cls[1])) return false;
      // Selector theo id — cũng phải chặt, nếu không mọi node đều khớp và test đậu giả.
      const byId = sel.match(/^#([\w-]+)/);
      if (byId && self.id !== byId[1]) return false;
      const exact = sel.match(/\[name="([^"]+)"\]/);
      if (exact && self.name !== exact[1]) return false;
      const prefix = sel.match(/\[name\^="([^"]+)"\]/);
      if (prefix && !self.name.startsWith(prefix[1])) return false;
      // Hậu tố: engine dùng [name$="$REPCtl$..."] để phân biệt hai form cùng khối PERSCtl.
      // Thiếu nhánh này thì node NÀO cũng khớp và test đậu giả.
      const suffix = sel.match(/\[name\$="([^"]+)"\]/);
      if (suffix && !self.name.endsWith(suffix[1])) return false;
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
// PAGE_SPEC dùng CHUNG cho mọi loại hình doanh nghiệp trên cổng (công ty cổ phần có trang "Thông tin
// về cổ phần", TNHH hai thành viên có "Thông tin về thành viên" + "Người đại diện theo pháp luật"),
// nên nó là HỢP của các bộ trang. Ràng buộc phải giữ: mọi key của từng pipeline đều có trong
// PAGE_SPEC và giữ ĐÚNG THỨ TỰ TƯƠNG ĐỐI — thứ tự PAGE_SPEC chính là thứ tự điền.
function backendPageKeys(pipeline) {
  const source = fs.readFileSync(
    path.join(root, "..", "auto-fill-hcc-backend", "app", "pipelines", pipeline,
      "process", "schema.py"),
    "utf8",
  );
  const block = source.slice(source.indexOf("PAGES: list[dict] = ["), source.indexOf("DEFAULT_PAGE"));
  return [...block.matchAll(/\{"key":\s*"([^"]+)"/g)].map((m) => m[1]);
}

const sandbox = makeSandbox([], {});
const feKeys = Object.keys(sandbox.__HCC__.enterpriseFillPageSpec);

for (const pipeline of ["thanh_lap_ctcp", "thanh_lap_ctythnn_2_nguoi"]) {
  const backendKeys = backendPageKeys(pipeline);
  assert.ok(backendKeys.length >= 8, `${pipeline}: schema.py phải khai đủ các trang khối dữ liệu`);
  assert.equal(backendKeys[0], "hinh-thuc-dang-ky", `${pipeline}: Hình thức đăng ký phải là trang ĐẦU TIÊN`);
  for (const key of backendKeys) {
    assert.ok(feKeys.includes(key), `${pipeline}: PAGE_SPEC thiếu key "${key}" -> trang này sẽ im lặng không được điền`);
  }
  // Lọc PAGE_SPEC theo đúng bộ trang của pipeline này phải ra ĐÚNG thứ tự backend khai —
  // engine dựng state.order y hệt phép lọc này.
  assert.deepEqual(
    feKeys.filter((key) => backendKeys.includes(key)), backendKeys,
    `${pipeline}: thứ tự trang trong PAGE_SPEC phải khớp thứ tự mục menu backend khai`,
  );
}

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
  async function runSubmitterPage({ accountName, accountDocNo, candidates, legalRep }) {
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
          ...(legalRep ? [{ name: "__legalRep", comp: "raw", value: legalRep }] : []),
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

  // ---- 11b. Chốt vai trò theo NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT (đúng luật của thủ tục hộ kinh doanh
  // đối chiếu tài khoản với CHỦ HỘ). Mốc này phải chạy được KHI HỒ SƠ KHÔNG KÈM ẢNH CCCD — đó là
  // trường hợp lối đối chiếu theo CCCD bị bỏ qua im lặng.
  const repThuong = { fullName: "Trần Thị Hoài Thương", docNo: "049197013201" };

  const asRepById = await runSubmitterPage({
    accountName: "Trần Thị Hoài Thương", accountDocNo: "049197013201",
    candidates: [], legalRep: repThuong,
  });
  assert.equal(asRepById.radioSelf.checked, true,
    "Tài khoản TRÙNG số định danh người đại diện -> người có thẩm quyền ký, dù hồ sơ không có CCCD");
  assert.equal(asRepById.radioAuth.checked, false);

  // OCR hay rơi dấu nên chỉ cần trùng MỘT trong hai (số hoặc tên) là chính chủ — y như HKD.
  const asRepByName = await runSubmitterPage({
    accountName: "Trần Thị Hoài Thương", accountDocNo: "",
    candidates: [], legalRep: { fullName: "Trần Thị Hoài Thương", docNo: "" },
  });
  assert.equal(asRepByName.radioSelf.checked, true, "Trùng HỌ TÊN người đại diện cũng là chính chủ");

  const asOtherPerson = await runSubmitterPage({
    accountName: "Lê Thị Hiền Chi", accountDocNo: "052176015320",
    candidates: [], legalRep: repThuong,
  });
  assert.equal(asOtherPerson.radioAuth.checked, true,
    "Tài khoản KHÁC người đại diện -> phải chuyển sang người được ủy quyền, không cần ảnh CCCD");
  assert.equal(asOtherPerson.radioSelf.checked, false);
  assert.deepEqual(asOtherPerson.filled.flat().map((f) => f.name), [],
    "Không phải người trong hồ sơ thì vẫn KHÔNG được ghi đè nhân thân của tài khoản");

  // Người đại diện là mốc CHÍNH: có cả CCCD trong hồ sơ thì vẫn chốt theo người đại diện.
  const repWins = await runSubmitterPage({
    accountName: "Lê Thị Hiền Chi", accountDocNo: "052176015320",
    candidates: [{ fullName: "Lê Thị Hiền Chi", docNo: "052176015320", address: {} }],
    legalRep: repThuong,
  });
  assert.equal(repWins.radioAuth.checked, true,
    "Có CCCD của chính người đăng nhập nhưng họ KHÔNG phải người đại diện -> vẫn là được ủy quyền");

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

  // ======================================================================================
  // TNHH HAI THÀNH VIÊN TRỞ LÊN: trang danh sách thành viên + chống lặp vô hạn
  // ======================================================================================
  const FILL_KEY = "autofill_enterprise_fillall";

  // ---- 13. Nhận diện ba trang mới, KHÔNG nhầm hai form dùng chung khối REPCtl$PERSCtl ----
  const onMemberList = makeSandbox([], {}, "/online/Forms/APP/DW_MEMBER_VWListing.aspx");
  assert.equal(onMemberList.__HCC__.currentEnterpriseFillPage(), "thong-tin-thanh-vien",
    "DW_MEMBER_VWListing.aspx là trang danh sách thành viên");

  // Đường dẫn thật của cổng — không có control nào, chỉ dựa vào tên file.
  const onLegalRepPath = makeSandbox([], {},
    "/online/Forms/APP/Information_of_Legal_representative.aspx");
  assert.equal(onLegalRepPath.__HCC__.currentEnterpriseFillPage(), "nguoi-dai-dien-phap-luat",
    "Information_of_Legal_representative.aspx là trang người đại diện theo pháp luật");
  assert.equal(onLegalRepPath.__HCC__.isInEnterpriseDossier(), true);

  // Lưới đỡ khi cổng đổi tên file: vẫn nhận được theo control.
  const onLegalRep = makeSandbox([node({ name: "ctl00$C$REPCtl$PERSCtl$FULL_NAMEFld" })], {},
    "/online/Forms/APP/DW_DOCUMENTEdit.aspx");
  assert.equal(onLegalRep.__HCC__.currentEnterpriseFillPage(), "nguoi-dai-dien-phap-luat",
    "Đổi tên file thì khối REPCtl$PERSCtl phải đỡ được");

  // Cùng khối control, chỉ khác ô "Tên thành viên là tổ chức" -> notProbe phải loại đúng.
  const onOrgRep = makeSandbox([
    node({ name: "ctl00$C$REPCtl$PERSCtl$FULL_NAMEFld" }),
    node({ tag: "select", name: "ctl00$C$REPCtl$NameMemberdrFld" }),
  ], {}, "/online/Forms/APP/DW_DOCUMENTEdit.aspx");
  assert.equal(onOrgRep.__HCC__.currentEnterpriseFillPage(), "nguoi-dai-dien-to-chuc",
    "Form người đại diện của TỔ CHỨC không được nhận nhầm thành người đại diện theo pháp luật");

  // ---- 14. Mỗi thành viên MỘT lượt: danh sách bấm "Tạo mới" -> form chi tiết -> Lưu ----
  const memberPages = {
    "thong-tin-thanh-vien": [
      {
        name: "__members",
        comp: "raw",
        value: [
          { fullName: "LÊ TỰ SANG", fields: [{ name: "ctl00$C$MEM_PCtl$PERSCtl$FULL_NAMEFld", comp: "dom-input", value: "LÊ TỰ SANG" }] },
          { fullName: "TRẦN THỊ HOÀI THƯƠNG", fields: [{ name: "ctl00$C$MEM_PCtl$PERSCtl$FULL_NAMEFld", comp: "dom-input", value: "TRẦN THỊ HOÀI THƯƠNG" }] },
        ],
      },
    ],
  };
  const memberState = (memberIndex) => ({
    order: ["thong-tin-thanh-vien"], pages: memberPages, done: [], navTries: {}, memberIndex, steps: 1,
  });

  // 14a. Trang danh sách, còn người chưa nhập -> mở form.
  const listStore = {};
  const addButton = node({ tag: "input", type: "submit", value: "Tạo mới" });
  const onList = makeSandbox([addButton], listStore, "/online/Forms/APP/DW_MEMBER_VWListing.aspx");
  await onList.__HCC__.startEnterpriseFillAll({ pages: memberPages });
  await new Promise((resolve) => setTimeout(resolve, 400));
  assert.equal(addButton.clicks, 1, "Còn thành viên chưa nhập thì phải bấm Tạo mới");
  assert.equal(Number(listStore[FILL_KEY].memberIndex || 0), 0,
    "Chưa điền xong người nào thì chỉ số thành viên phải giữ nguyên");
  assert.deepEqual([...listStore[FILL_KEY].done], [],
    "Còn thành viên chưa nhập thì KHÔNG được đánh dấu xong trang");
  delete listStore[FILL_KEY];   // dừng state machine của sandbox này

  // 14b + 14c. Form chi tiết: điền đúng người theo chỉ số, lưu xong mới nhích sang người kế.
  for (const [index, expected] of [[0, "LÊ TỰ SANG"], [1, "TRẦN THỊ HOÀI THƯƠNG"]]) {
    const detailStore = { [FILL_KEY]: memberState(index) };
    const detailSave = node({ tag: "input", type: "submit", name: "ctl00$C$btnSave", value: "Lưu" });
    const onDetail = makeSandbox(
      [node({ name: "ctl00$C$MEM_PCtl$PERSCtl$FULL_NAMEFld" }), detailSave],
      detailStore, "/online/Forms/APP/InformationOfMembers.aspx",
    );
    await new Promise((resolve) => setTimeout(resolve, 2000));
    assert.equal(onDetail.__HCC__.filled.length, 1, `Thành viên ${index + 1}: phải điền đúng một lượt`);
    assert.equal([...onDetail.__HCC__.filled[0]][0].value, expected,
      `Phải điền ĐÚNG thành viên thứ ${index + 1}, không lấy nhầm người khác`);
    assert.equal(detailSave.clicks, 1, "Điền xong một thành viên phải bấm Lưu");
    assert.equal(detailStore[FILL_KEY].memberIndex, index + 1,
      "Chỉ nhích sang người kế khi đã chắc chắn bấm Lưu");
    delete detailStore[FILL_KEY];
  }

  // 14d. Hết thành viên -> đóng trang, không bấm Tạo mới nữa (nếu không sẽ đẻ dòng rỗng).
  // Thêm một trang nữa vào order để luồng CHƯA kết thúc — có vậy mới soi được state sau khi
  // trang thành viên bị đánh dấu xong (xong hết thì finishFill dọn sạch state).
  const doneState = memberState(2);
  doneState.order = ["thong-tin-thanh-vien", "thong-tin-ve-thue"];
  doneState.pages = { ...memberPages, "thong-tin-ve-thue": [{ name: "x", comp: "dom-input", value: "y" }] };
  const doneStore = { [FILL_KEY]: doneState };
  const addAgain = node({ tag: "input", type: "submit", value: "Tạo mới" });
  makeSandbox([addAgain], doneStore, "/online/Forms/APP/DW_MEMBER_VWListing.aspx");
  await new Promise((resolve) => setTimeout(resolve, 1200));
  assert.equal(addAgain.clicks, 0, "Nhập đủ thành viên rồi thì KHÔNG được bấm Tạo mới nữa");
  assert.deepEqual([...doneStore[FILL_KEY].done], ["thong-tin-thanh-vien"],
    "Nhập đủ thành viên thì trang phải được đánh dấu xong để đi tiếp");
  delete doneStore[FILL_KEY];

  // ---- 14e. Nhập xong người CUỐI mà cổng vẫn đứng ở form chi tiết → phải sang MỤC KẾ ----
  // Nhánh xử lý form chi tiết chạy TRƯỚC nhánh chung và trước đây không xét state.done: hết người
  // thì nó đánh dấu xong rồi hẹn nhịp, nhịp sau lại nhận đúng trang đó → quay vòng mãi ở mục thành
  // viên, không bao giờ mở mục kế ("đã lưu thông tin nhưng không chịu chuyển qua mục khác").
  const stallState = memberState(2);
  stallState.order = ["thong-tin-thanh-vien", "thong-tin-ve-thue"];
  stallState.pages = {
    ...memberPages,
    "thong-tin-ve-thue": [{ name: "x", comp: "dom-input", value: "y" }],
  };
  const stallStore = { [FILL_KEY]: stallState };
  const taxMenuLink = node({ tag: "a", textContent: "Thông tin về thuế" });
  const onStall = makeSandbox(
    [node({ name: "ctl00$C$MEM_PCtl$PERSCtl$FULL_NAMEFld" }), taxMenuLink],
    stallStore, "/online/Forms/APP/InformationOfMembers.aspx",
  );
  await new Promise((resolve) => setTimeout(resolve, 1500));
  assert.equal(onStall.__HCC__.filled.length, 0, "Hết thành viên thì không được điền đè lên form");
  assert.ok(stallStore[FILL_KEY].done.includes("thong-tin-thanh-vien"),
    "Hết thành viên thì mục thành viên phải được đánh dấu xong");
  assert.ok(Number(stallStore[FILL_KEY].navTries["thong-tin-ve-thue"] || 0) >= 1,
    "Phải chuyển sang MỤC KẾ, không được quay vòng ở mục thành viên");
  delete stallStore[FILL_KEY];

  // ---- 15. Mục "Người đại diện theo pháp luật" trỏ tới trang DANH SÁCH ----
  // Bấm mục menu xong là ra trang danh sách, phải bấm "Tạo mới" mới có form nhập. Tên file trang
  // danh sách chưa biết nên engine nhận theo NGỮ CẢNH: mục vừa mở + trang lạ + có nút "Tạo mới".
  const repListStore = {
    [FILL_KEY]: {
      order: ["nguoi-dai-dien-phap-luat"],
      pages: {
        "nguoi-dai-dien-phap-luat": [
          { name: "ctl00$C$REPCtl$PERSCtl$FULL_NAMEFld", comp: "dom-input", value: "TRẦN THỊ HOÀI THƯƠNG" },
        ],
      },
      done: [], navTries: {}, fillTries: {}, navTarget: "nguoi-dai-dien-phap-luat",
      memberIndex: 0, steps: 1,
    },
  };
  const repAddButton = node({ tag: "input", type: "submit", value: "Tạo mới" });
  // Trang danh sách: KHÔNG có control nào của form nhập, đường dẫn cũng lạ với engine.
  const onRepList = makeSandbox([repAddButton], repListStore,
    "/online/Forms/APP/DW_LEGAL_REP_VWListing.aspx");
  await new Promise((resolve) => setTimeout(resolve, 800));
  assert.equal(repAddButton.clicks, 1,
    "Trang danh sách người đại diện: phải bấm Tạo mới để mở form, không được bỏ qua mục");
  assert.equal(onRepList.__HCC__.filled.length, 0, "Trang danh sách thì chưa có gì để điền");
  delete repListStore[FILL_KEY];

  // Nút phải khớp theo NAME thật của cổng (ctl00$C$btnNew) chứ không chỉ theo chữ — và phải chạy
  // được KỂ CẢ khi state.navTarget rỗng (lệnh ghi state thua cuộc với lúc cổng chuyển trang).
  const repListStore2 = {
    [FILL_KEY]: {
      order: ["nguoi-dai-dien-phap-luat"],
      pages: {
        "nguoi-dai-dien-phap-luat": [
          { name: "ctl00$C$REPCtl$PERSCtl$FULL_NAMEFld", comp: "dom-input", value: "A" },
        ],
      },
      done: [], navTries: {}, fillTries: {}, navTarget: "", memberIndex: 0, steps: 1,
    },
  };
  // Chữ trên nút cố tình KHÁC "Tạo mới" để chứng minh việc khớp là nhờ NAME.
  const repAddByName = node({
    tag: "input", type: "submit", name: "ctl00$C$btnNew", value: "Khai báo người đại diện",
  });
  await makeSandbox([repAddByName], repListStore2, "/online/Forms/APP/DW_LEGAL_REP_VWListing.aspx");
  await new Promise((resolve) => setTimeout(resolve, 800));
  assert.equal(repAddByName.clicks, 1,
    "Phải nhận ra nút Tạo mới theo name ctl00$C$btnNew, không phụ thuộc chữ trên nút hay navTarget");
  delete repListStore2[FILL_KEY];

  // Trường hợp khó nhất: DANH SÁCH và FORM dùng CHUNG một .aspx. Đường dẫn khớp nên engine nhận ra
  // đúng mục, nhưng control của form chưa render — không xử lý thì engine điền vào hư không rồi
  // đánh dấu xong, bỏ luôn cả mục.
  const sharedStore = {
    [FILL_KEY]: {
      order: ["nguoi-dai-dien-phap-luat"],
      pages: {
        "nguoi-dai-dien-phap-luat": [
          { name: "ctl00$C$REPCtl$PERSCtl$FULL_NAMEFld", comp: "dom-input", value: "A" },
        ],
      },
      done: [], navTries: {}, fillTries: {}, navTarget: "", memberIndex: 0, steps: 1,
    },
  };
  const sharedAdd = node({ tag: "input", type: "submit", name: "ctl00$C$btnNew", value: "Tạo mới" });
  const onShared = makeSandbox([sharedAdd], sharedStore,
    "/online/Forms/APP/Information_of_Legal_representative.aspx");
  await new Promise((resolve) => setTimeout(resolve, 900));
  assert.equal(sharedAdd.clicks, 1,
    "Cùng .aspx nhưng chưa có control form → phải bấm Tạo mới, không được điền vào hư không");
  assert.equal(onShared.__HCC__.filled.length, 0, "Chưa có form thì chưa được điền");
  assert.ok(!sharedStore[FILL_KEY].done.includes("nguoi-dai-dien-phap-luat"),
    "Chưa điền được thì KHÔNG được đánh dấu xong (đánh dấu là bỏ luôn cả mục)");
  delete sharedStore[FILL_KEY];

  // Bấm Tạo mới xong ra form thật → điền và Lưu như mọi trang khác.
  const repFormStore = {
    [FILL_KEY]: {
      order: ["nguoi-dai-dien-phap-luat"],
      pages: {
        "nguoi-dai-dien-phap-luat": [
          { name: "ctl00$C$REPCtl$PERSCtl$FULL_NAMEFld", comp: "dom-input", value: "TRẦN THỊ HOÀI THƯƠNG" },
        ],
      },
      done: [], navTries: {}, fillTries: {}, navTarget: "nguoi-dai-dien-phap-luat",
      memberIndex: 0, steps: 1,
    },
  };
  const repSave = node({ tag: "input", type: "submit", name: "ctl00$C$btnSave", value: "Lưu" });
  const onRepForm = makeSandbox(
    [node({ name: "ctl00$C$REPCtl$PERSCtl$FULL_NAMEFld" }), repSave], repFormStore,
    "/online/Forms/APP/Information_of_Legal_representative.aspx",
  );
  await new Promise((resolve) => setTimeout(resolve, 1500));
  assert.equal(onRepForm.__HCC__.filled.length, 1, "Vào được form thì phải điền");
  assert.equal(repSave.clicks, 1, "Điền xong phải bấm Lưu");
  assert.ok(repFormStore[FILL_KEY].done.includes("nguoi-dai-dien-phap-luat"));
  delete repFormStore[FILL_KEY];

  // ---- 16. Chống LẶP VÔ HẠN khi control có AutoPostBack (EnterpriseName.aspx) ----
  // Dropdown tiền tố loại hình ở trang Tên doanh nghiệp có AutoPostBack: vừa đổi giá trị là cổng
  // tải lại trang NGAY. Nếu state chỉ được ghi SAU khi điền thì lệnh ghi chết theo trang, trang
  // không bao giờ được đánh dấu, lượt sau lại điền → lặp vô hạn.
  const loopStore = {};
  const loopSave = node({ tag: "input", type: "submit", name: "ctl00$C$BtnSave", value: "Lưu" });
  const onName = makeSandbox([node({ name: "ctl00$C$NAMEFld" }), loopSave], loopStore,
    "/online/Forms/APP/EnterpriseName.aspx");
  await onName.__HCC__.startEnterpriseFillAll({
    pages: {
      "ten-doanh-nghiep": [
        { name: "ctl00$C$DROP_NAME_TYPE", comp: "dom-select", value: "CÔNG TY TNHH" },
        { name: "ctl00$C$NAMEFld", comp: "dom-input", value: "DỊCH VỤ VẬN TẢI" },
      ],
    },
  });
  await new Promise((resolve) => setTimeout(resolve, 300));
  assert.equal(loopStore[FILL_KEY].fillTries["ten-doanh-nghiep"], 1,
    "Số lần thử phải được GHI TRƯỚC khi điền, nếu không postback giữa chừng sẽ nuốt mất state");
  await new Promise((resolve) => setTimeout(resolve, 1200));
  delete loopStore[FILL_KEY];

  // Đã thử quá trần: bỏ qua trang để cả luồng còn chạy tiếp, không quay vòng mãi.
  const cappedStore = {
    [FILL_KEY]: {
      order: ["ten-doanh-nghiep", "thong-tin-ve-thue"],
      pages: {
        "ten-doanh-nghiep": [{ name: "ctl00$C$NAMEFld", comp: "dom-input", value: "ABC" }],
        "thong-tin-ve-thue": [{ name: "x", comp: "dom-input", value: "y" }],
      },
      done: [], navTries: {}, fillTries: { "ten-doanh-nghiep": 3 }, memberIndex: 0, steps: 1,
    },
  };
  const cappedSave = node({ tag: "input", type: "submit", name: "ctl00$C$BtnSave", value: "Lưu" });
  const onCapped = makeSandbox([node({ name: "ctl00$C$NAMEFld" }), cappedSave], cappedStore,
    "/online/Forms/APP/EnterpriseName.aspx");
  await new Promise((resolve) => setTimeout(resolve, 1200));
  assert.equal(onCapped.__HCC__.filled.length, 0, "Quá trần thì KHÔNG được điền lại nữa");
  assert.equal(cappedSave.clicks, 0, "Quá trần thì cũng không bấm Lưu");
  assert.ok(cappedStore[FILL_KEY].done.includes("ten-doanh-nghiep"),
    "Quá trần thì phải đánh dấu xong để đi tiếp trang khác, không kẹt cả luồng");
  assert.ok(onCapped.__HCC__.toasts.some((t) => t.kind === "warn"),
    "Bỏ qua trang thì phải báo cho cán bộ biết mà điền tay");
  delete cappedStore[FILL_KEY];

  console.log("enterprise-fill-pages: bàn giao đính kèm + vai trò người nộp + URL thật + chờ nút Lưu"
    + " + vòng lặp thành viên + trang danh sách người đại diện + chống lặp vô hạn passed");
})();
