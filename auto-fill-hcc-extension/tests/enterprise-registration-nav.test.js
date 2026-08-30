// Kiểm tra luồng "tự tiến tới thủ tục" của content/procedures/enterprise-registration.js trên
// dangkyquamang.dkkd.gov.vn, đúng ba bước đã chụp màn hình cổng thật:
//   B1 Registration.aspx  chọn NEW (Thành lập mới doanh nghiệp/đơn vị trực thuộc) -> Tiếp theo
//   B2 Registration.aspx  chọn SC  (Công ty cổ phần, KHÔNG lấy dòng TNHH mặc định) -> Tiếp theo
//   B3 Registration.aspx  bấm "Bắt đầu"
//   => DW_DOCUMENTEdit.aspx (Khối dữ liệu): xóa cờ, không chạy nữa.
// Mỗi bước là một postback tải lại trang nên chạy trong một sandbox riêng, giống thực tế.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const SOURCE = fs.readFileSync(
  path.join(__dirname, "..", "content", "procedures", "enterprise-registration.js"),
  "utf8",
);

// ---- DOM giả tối thiểu: đủ cho các selector mà script dùng ----
function parseSelector(part) {
  const tag = (part.match(/^[a-z]+/i) || [""])[0].toLowerCase();
  const attrs = [...part.matchAll(/\[([a-z-]+)(\$?=)"([^"]*)"\]/gi)]
    .map(([, name, op, value]) => ({ name, op, value }));
  return { tag, attrs };
}

function matches(node, part) {
  const { tag, attrs } = parseSelector(part);
  if (tag && node.tagName.toLowerCase() !== tag) return false;
  return attrs.every(({ name, op, value }) => {
    const actual = String(node[name === "for" ? "htmlFor" : name] ?? "");
    return op === "$=" ? actual.endsWith(value) : actual === value;
  });
}

function makeNode(spec) {
  const node = {
    tagName: (spec.tag || "input").toUpperCase(),
    type: spec.type || "",
    name: spec.name || "",
    value: spec.value || "",
    id: spec.id || "",
    htmlFor: spec.htmlFor || "",
    textContent: spec.textContent || "",
    disabled: !!spec.disabled,
    isConnected: true,
    clicks: 0,
    events: [],
    getBoundingClientRect: () => ({ width: 120, height: 20 }),
    closest: () => null,
    click() { this.clicks += 1; },
    dispatchEvent(event) { this.events.push(event?.type || String(event)); return true; },
  };
  // Trình duyệt thật tự BỎ TICK các radio cùng name khi gán checked = true; script dựa vào hành vi
  // này (chỉ set trên radio đích) nên DOM giả phải mô phỏng, nếu không test sẽ dễ dãi hơn thực tế.
  let checked = !!spec.checked;
  Object.defineProperty(node, "checked", {
    get: () => checked,
    set(value) {
      checked = !!value;
      if (!checked || !node.group) return;
      for (const sibling of node.group) if (sibling !== node) sibling.checked = false;
    },
  });
  return node;
}

const REGISTRATION_RADIOS = [
  ["NEW", "Thành lập mới doanh nghiệp/đơn vị trực thuộc"],
  ["REI", "Đăng ký cấp lại Giấy chứng nhận/Giấy xác nhận"],
  ["CHN", "Đăng ký thay đổi nội dung đăng ký doanh nghiệp/đơn vị trực thuộc"],
];
// Nhãn + value đọc từ DOM cổng thật (ảnh chụp): Công ty cổ phần = C_myWizard_CtlEntType_2, value "SC".
const ENTITY_RADIOS = [
  ["LLC1", "Công ty trách nhiệm hữu hạn một thành viên"],
  ["LLC2", "Công ty trách nhiệm hữu hạn hai thành viên trở lên"],
  ["SC", "Công ty cổ phần"],
  ["PRI", "Doanh nghiệp tư nhân"],
  ["PAR", "Công ty hợp danh"],
];

/** Dựng "trang" theo từng bước wizard; trả { nodes, pathname, bodyText }. */
function buildPage(stage) {
  const nodes = [];
  if (stage === "dossier") {
    // innerText của bảng "Thông tin về hồ sơ": mỗi dòng là "nhãn<TAB>giá trị" (theo ảnh cổng thật).
    return {
      nodes,
      pathname: "/online/Forms/APP/DW_DOCUMENTEdit.aspx",
      bodyText: [
        "Trang chủ > Khối dữ liệu",
        "KHỐI DỮ LIỆU",
        "Hình thức đăng ký",
        "Địa chỉ",
        "Ngành nghề kinh doanh",
        "Thông tin về hồ sơ",
        "Hình thức đăng ký:\tThành lập mới doanh nghiệp/đơn vị trực thuộc",
        "Loại hình doanh nghiệp:\tCông ty cổ phần",
        "Trạng thái hồ sơ:\tĐã lưu",
      ].join("\n"),
    };
  }
  if (stage === "confirm") {
    nodes.push(makeNode({ tag: "input", type: "submit", value: "Trở về" }));
    nodes.push(makeNode({ tag: "input", type: "submit", value: "Bắt đầu" }));
    return { nodes, pathname: "/online/Forms/APP/Registration.aspx", bodyText: "Xác nhận thông tin đăng ký" };
  }

  const entity = stage === "entity";
  const field = entity ? "CtlEntType" : "CtlType";
  (entity ? ENTITY_RADIOS : REGISTRATION_RADIOS).forEach(([value, label], index) => {
    // Cổng render id NGẮN (không có tiền tố ctl00_) — chốt luôn trong test để khỏi lặp lỗi cũ.
    const id = `C_myWizard_${field}_${index}`;
    nodes.push(makeNode({
      tag: "input", type: "radio", name: `ctl00$C$myWizard$${field}`, value, id,
      checked: index === 0,   // cổng tick sẵn dòng đầu ở cả hai bước
    }));
    nodes.push(makeNode({ tag: "label", htmlFor: id, textContent: label }));
  });
  const group = nodes.filter((node) => node.type === "radio");
  for (const radio of group) radio.group = group;
  if (entity) nodes.push(makeNode({ tag: "input", type: "submit", value: "Trở về" }));
  nodes.push(makeNode({ tag: "input", type: "submit", value: "Tiếp theo" }));
  return { nodes, pathname: "/online/Forms/APP/Registration.aspx", bodyText: "Chọn loại đăng ký trực tuyến" };
}

function radioOf(page, value) {
  return page.nodes.find((node) => node.type === "radio" && node.value === value);
}
function buttonOf(page, label) {
  return page.nodes.find((node) => node.value === label);
}

/** Chạy script một lần trên "trang" đã dựng; trả về danh sách toast để soi thông báo. */
async function runOnce(page, store, session = {}) {
  const toasts = [];
  const nodes = page.nodes;
  const sandbox = {
    console: { log() {}, warn() {}, error() {} },
    Event: class { constructor(type) { this.type = type; } },
    CSS: { escape: (value) => value },
    setTimeout,
    clearTimeout,
    setInterval: () => 0,           // vòng rà nền không cần cho test
    clearInterval: () => {},
    getComputedStyle: () => ({ display: "block", visibility: "visible" }),
    chrome: {
      storage: {
        local: {
          async get(key) { return key in store ? { [key]: store[key] } : {}; },
          async set(patch) { Object.assign(store, patch); },
          async remove(key) { delete store[key]; },
        },
      },
    },
    document: {
      readyState: "complete",
      body: { innerText: page.bodyText || "" },
      addEventListener() {},
      querySelector: (selector) => nodes.find((node) => matches(node, selector.trim())) || null,
      querySelectorAll: (selector) => selector.split(",")
        .map((part) => part.trim())
        .flatMap((part) => nodes.filter((node) => matches(node, part))),
    },
  };
  sandbox.window = sandbox;
  // sessionStorage sống theo TAB: mỗi lượt runOnce là một lần tải trang trong CÙNG tab nên phải
  // dùng chung store (tham số `session`), không tạo mới mỗi lượt.
  sandbox.sessionStorage = {
    getItem: (k) => (k in session ? session[k] : null),
    setItem: (k, v) => { session[k] = String(v); },
    removeItem: (k) => { delete session[k]; },
  };
  sandbox.location = { hostname: "dangkyquamang.dkkd.gov.vn", pathname: page.pathname };
  sandbox.top = sandbox;
  sandbox.__HCC__ = { showPageToast: (message, kind) => toasts.push({ message, kind }) };
  vm.runInNewContext(SOURCE, sandbox, { filename: "enterprise-registration.js" });
  // run() là async (có sleep 1200ms khi phải tick radio) -> chờ dài hơn một nhịp.
  await new Promise((resolve) => setTimeout(resolve, 1600));
  return {
    toasts,
    hint: sandbox.__HCC__.detectEnterpriseProcedureHint(),
    entityLabel: sandbox.__HCC__.detectEnterpriseEntityLabel(),
  };
}

const ARM_KEY = "autofill_enterprise_autostart";
const ARM = {
  registrationType: "NEW",
  registrationLabel: "Thành lập mới doanh nghiệp",
  entityValue: "SC",
  entityLabel: "Công ty cổ phần",
  procedureKey: "thanh-lap-cong-ty-co-phan",
  procedureLabel: "Đăng ký thành lập công ty cổ phần",
};

(async () => {
  const store = { [ARM_KEY]: { ...ARM, at: Date.now() } };

  // ---- B1: loại đăng ký ----
  const step1 = buildPage("registration");
  const run1 = await runOnce(step1, store);
  assert.equal(run1.hint, "select-registration-type");
  assert.equal(radioOf(step1, "NEW").checked, true, "B1 phải giữ lựa chọn Thành lập mới");
  assert.equal(buttonOf(step1, "Tiếp theo").clicks, 1, "B1 phải bấm Tiếp theo đúng một lần");
  assert.ok(store[ARM_KEY], "Chưa xong wizard thì cờ phải còn để lượt tải trang sau chạy tiếp");

  // ---- B2: loại hình (postback -> sandbox mới, cờ mang sang) ----
  const step2 = buildPage("entity");
  const run2 = await runOnce(step2, store);
  assert.equal(run2.hint, "select-entity-type");
  assert.equal(
    run2.entityLabel, "",
    "Ở bước chọn loại hình, cổng tick sẵn dòng đầu (TNHH) nên TUYỆT ĐỐI không được báo loại hình",
  );
  assert.equal(radioOf(step2, "SC").checked, true, "Phải tick đúng dòng Công ty cổ phần");
  assert.equal(radioOf(step2, "LLC1").checked, false, "Không được giữ dòng TNHH một thành viên mặc định");
  assert.equal(buttonOf(step2, "Tiếp theo").clicks, 1, "B2 phải bấm Tiếp theo đúng một lần");
  assert.ok(store[ARM_KEY], "Còn bước Bắt đầu nên cờ phải còn");

  // ---- B3: màn xác nhận -> Bắt đầu ----
  const step3 = buildPage("confirm");
  const run3 = await runOnce(step3, store);
  assert.equal(run3.hint, "confirm");
  assert.equal(buttonOf(step3, "Bắt đầu").clicks, 1, "B3 phải bấm Bắt đầu đúng một lần");
  assert.equal(buttonOf(step3, "Trở về").clicks, 0, "Không được bấm nhầm Trở về");
  assert.ok(store[ARM_KEY], "Chỉ xóa cờ khi đã vào tới khối dữ liệu, không xóa ngay khi bấm Bắt đầu");

  // ---- Vào tới khối dữ liệu: xóa cờ + báo xong ----
  const dossierSession = {};
  const dossier = buildPage("dossier");
  const run4 = await runOnce(dossier, store, dossierSession);
  assert.equal(run4.hint, "dossier");
  assert.equal(
    run4.entityLabel, "Công ty cổ phần",
    'Trang hồ sơ phải đọc được dòng "Loại hình doanh nghiệp" để popup nhận diện đúng thủ tục',
  );
  assert.equal(store[ARM_KEY], undefined, "Vào tới hồ sơ phải xóa cờ để không chạy lặp");
  // Hai chặng đã nối liền (panel tự quét tiếp) nên KHÔNG được toast ở đây — thông báo giữa luồng
  // chỉ là nhiễu, và cán bộ đã yêu cầu bỏ.
  assert.deepEqual(run4.toasts, [], "Vào tới hồ sơ thì không toast gì cả");

  // ---- Cờ được đặt lại ở trang hồ sơ: vẫn phải dọn sạch và vẫn im lặng ----
  store[ARM_KEY] = { ...ARM, at: Date.now() };
  const run5 = await runOnce(buildPage("dossier"), store, dossierSession);
  assert.equal(store[ARM_KEY], undefined, "Cờ đặt lại ở trang hồ sơ vẫn phải được dọn");
  assert.deepEqual(run5.toasts, [], "Đã báo mở xong rồi thì không được toast lại");

  // ---- Cán bộ tự chọn loại đăng ký KHÁC: trợ lý phải đứng im ----
  // Luồng giờ tự chạy, không cần bấm nút, nên đây là lưới an toàn quan trọng nhất: cán bộ đang định
  // làm "Đăng ký thay đổi nội dung" thì không được kéo họ sang nhánh thành lập mới.
  const manual = buildPage("registration");
  radioOf(manual, "CHN").checked = true;
  const manualStore = { [ARM_KEY]: { ...ARM, at: Date.now() } };
  const runManual = await runOnce(manual, manualStore);
  assert.equal(radioOf(manual, "CHN").checked, true, "Không được ghi đè lựa chọn tay của cán bộ");
  assert.equal(radioOf(manual, "NEW").checked, false, "Không được tự tick lại Thành lập mới");
  assert.equal(buttonOf(manual, "Tiếp theo").clicks, 0, "Không được tự bấm Tiếp theo khi cán bộ đã chọn khác");
  assert.equal(manualStore[ARM_KEY], undefined, "Dừng có kiểm soát thì phải dọn cờ");
  assert.ok(
    runManual.toasts.some((t) => t.kind === "warn"),
    "Phải báo cho cán bộ biết vì sao trợ lý không đi tiếp",
  );

  // ---- Không có cờ thì tuyệt đối không đụng vào wizard của cán bộ ----
  const untouched = buildPage("entity");
  await runOnce(untouched, {});
  assert.equal(buttonOf(untouched, "Tiếp theo").clicks, 0, "Không có cờ thì không được bấm Tiếp theo");
  assert.equal(radioOf(untouched, "SC").checked, false, "Không có cờ thì không được đổi lựa chọn");

  // ---- Cờ quá hạn: bỏ qua và dọn cờ ----
  const stale = buildPage("registration");
  const staleStore = { [ARM_KEY]: { ...ARM, at: Date.now() - 20 * 60 * 1000 } };
  await runOnce(stale, staleStore);
  assert.equal(buttonOf(stale, "Tiếp theo").clicks, 0, "Cờ quá hạn thì không được bấm Tiếp theo");
  assert.equal(staleStore[ARM_KEY], undefined, "Cờ quá hạn phải được dọn");

  // ---- Nhãn cổng đổi chữ: vẫn chọn đúng nhờ value "SC" ----
  const renamed = buildPage("entity");
  renamed.nodes
    .filter((node) => node.tagName === "LABEL" && node.htmlFor === "C_myWizard_CtlEntType_2")
    .forEach((node) => { node.textContent = "Cty cổ phần (CTCP)"; });
  const renamedStore = { [ARM_KEY]: { ...ARM, at: Date.now() } };
  await runOnce(renamed, renamedStore);
  assert.equal(radioOf(renamed, "SC").checked, true, "Nhãn đổi chữ thì value SC phải đỡ được");

  console.log("enterprise-registration: điều hướng 3 bước tới hồ sơ Công ty cổ phần passed");
})();
