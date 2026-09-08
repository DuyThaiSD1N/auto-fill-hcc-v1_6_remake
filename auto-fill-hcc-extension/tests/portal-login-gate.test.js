// Chặng "check đăng nhập" nối "Nộp trực tuyến" với bước kê khai.
//
// Hai phần: (1) bộ nhận diện trong content/portal-login.js chạy trên DOM giả;
// (2) máy trạng thái trong content/agency-select.js có đúng chặng login và không bỏ rơi cờ.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const loginSource = fs.readFileSync(
  path.join(__dirname, "..", "content", "portal-login.js"), "utf8",
);
const agencySource = fs.readFileSync(
  path.join(__dirname, "..", "content", "agency-select.js"), "utf8",
);

// ---------- DOM giả: đủ cho querySelector/querySelectorAll/closest mà bộ nhận diện dùng ----------
function node(tag, { text = "", attrs = {}, children = [], shown = true } = {}) {
  const el = {
    tagName: tag.toUpperCase(),
    attrs,
    children,
    shown,
    parentElement: null,
    get textContent() {
      return text + children.map((child) => child.textContent).join(" ");
    },
    matches(selector) { return matchesSelector(el, selector); },
    querySelector(selector) { return el.querySelectorAll(selector)[0] || null; },
    querySelectorAll(selector) {
      const out = [];
      for (const child of descendants(el)) {
        if (selector.split(",").some((part) => matchesSelector(child, part.trim()))) out.push(child);
      }
      return out;
    },
    closest(selector) {
      let cur = el;
      while (cur) {
        if (selector.split(",").some((part) => matchesSelector(cur, part.trim()))) return cur;
        cur = cur.parentElement;
      }
      return null;
    },
    getClientRects() { return el.shown ? [{ width: 10, height: 10 }] : []; },
    ownerDocument: null,
  };
  for (const child of children) child.parentElement = el;
  return el;
}

function descendants(root) {
  const out = [];
  for (const child of root.children) { out.push(child, ...descendants(child)); }
  return out;
}

/** Chỉ hỗ trợ đúng các dạng selector mà portal-login.js dùng: tag, .class, #id, [attr="v"]. */
function matchesSelector(el, selector) {
  const parts = selector.match(/^([a-zA-Z0-9]+)?((?:[.#][\w-]+|\[[^\]]+\])*)$/);
  if (!parts) return false;
  if (parts[1] && el.tagName !== parts[1].toUpperCase()) return false;
  for (const token of parts[2].match(/[.#][\w-]+|\[[^\]]+\]/g) || []) {
    if (token[0] === ".") {
      if (!String(el.attrs.class || "").split(/\s+/).includes(token.slice(1))) return false;
    } else if (token[0] === "#") {
      if (el.attrs.id !== token.slice(1)) return false;
    } else {
      const [, name, value] = token.match(/\[([\w-]+)(?:=["']?([^"'\]]*)["']?)?\]/) || [];
      if (!(name in el.attrs)) return false;
      if (value !== undefined && String(el.attrs[name]) !== value) return false;
    }
  }
  return true;
}

function makeDoc(children) {
  const root = node("body", { children });
  root.ownerDocument = { defaultView: { getComputedStyle: () => ({}) } };
  for (const child of descendants(root)) child.ownerDocument = root.ownerDocument;
  return root;
}

function loadDetector(hostname) {
  const sandbox = { location: { hostname }, window: {} };
  sandbox.window = sandbox;
  vm.runInNewContext(loginSource, sandbox);
  return sandbox.__HCC_LOGIN__;
}

// ---------- 1. Nhận diện trạng thái đăng nhập ----------
const detector = loadDetector("dichvucong.gov.vn");

// Đã đăng nhập: cổng React hiện tên tài khoản.
const loggedInDoc = makeDoc([
  node("div", { attrs: { class: "user-dropdown" }, text: "Nguyễn Văn A" }),
  node("span", { text: "Chọn cơ quan thực hiện" }),
]);
let state = detector.detectLoginState(loggedInDoc, { maxAgeMs: 0 });
assert.equal(state.loggedIn, true);
assert.equal(state.loginRequired, false, "Đã đăng nhập thì không được coi là đang bị chặn");

// Nút "Đăng nhập" ở header trang chủ KHÔNG đủ để kết luận đang ở màn đăng nhập — nếu đủ thì mọi
// trang chưa đăng nhập đều bị hiểu là màn QR và luồng đứng lại vô cớ.
const headerOnlyDoc = makeDoc([
  node("button", { text: "Đăng nhập" }),
  node("span", { text: "Danh sách dịch vụ công" }),
]);
state = detector.detectLoginState(headerOnlyDoc, { maxAgeMs: 0 });
assert.equal(state.loginRequired, false, 'Chỉ có chữ "Đăng nhập" thì chưa phải màn đăng nhập');

// Màn QR thật: có đủ "Đăng nhập" + "Quét mã QR".
const qrDoc = makeDoc([
  node("h2", { text: "Đăng nhập" }),
  node("p", { text: "Quét mã QR bằng ứng dụng VNeID" }),
]);
state = detector.detectLoginState(qrDoc, { maxAgeMs: 0 });
assert.equal(state.loginRequired, true);
assert.match(detector.loginHint(state), /VNeID/);

// Modal passcode thắng cả trạng thái đã đăng nhập: cổng hiện tên tài khoản nhưng vẫn đang chặn.
const passcodeDoc = makeDoc([
  node("div", { attrs: { class: "user-dropdown" }, text: "Nguyễn Văn A" }),
  node("div", {
    attrs: { class: "ant-modal-content" },
    children: [
      node("div", { text: "Nhập passcode" }),
      node("input", { attrs: { type: "number", inputmode: "numeric", autocomplete: "off" } }),
      node("button", { text: "Xác nhận" }),
    ],
  }),
]);
state = detector.detectLoginState(passcodeDoc, { maxAgeMs: 0 });
assert.equal(state.loggedIn, true);
assert.equal(state.vneidPasscodePrompt, true);
assert.equal(state.loginRequired, true, "Modal passcode vẫn chặn dù đã hiện tên tài khoản");
assert.match(detector.loginHint(state), /passcode/i);

// Modal chia sẻ dữ liệu phải ra hint riêng, không bị modal passcode nuốt.
const sharingDoc = makeDoc([
  node("div", {
    attrs: { class: "ant-modal-content" },
    children: [
      node("span", {
        text: "Tôi đã đọc và hiểu rõ nội dung mục đích và quyền, nghĩa vụ của chủ thể dữ liệu",
      }),
      node("input", { attrs: { type: "checkbox" } }),
      node("button", { text: "Xác nhận chia sẻ" }),
    ],
  }),
]);
state = detector.detectLoginState(sharingDoc, { maxAgeMs: 0 });
assert.equal(state.vneidDataSharingPrompt, true);
assert.equal(state.vneidPasscodePrompt, false);
assert.match(detector.loginHint(state), /chia sẻ/);

// Node bị ẩn không được tính: cổng giữ lại component đăng nhập cũ trong DOM sau khi đã vào hồ sơ.
const hiddenQrDoc = makeDoc([
  node("h2", { text: "Đăng nhập", shown: false }),
  node("p", { text: "Quét mã QR bằng ứng dụng VNeID", shown: false }),
  node("span", { text: "Kê khai thông tin" }),
]);
state = detector.detectLoginState(hiddenQrDoc, { maxAgeMs: 0 });
assert.equal(state.loginRequired, false, "Marker đăng nhập đang ẩn thì không được chặn luồng");

// Cổng TỈNH chặn bằng dialog chỉ có nút "Đăng nhập bằng VNeID" (không có chữ "quét mã QR").
const provinceLoginDoc = makeDoc([
  node("div", {
    attrs: { role: "dialog" },
    children: [node("button", { text: "Đăng nhập bằng VNeID" })],
  }),
]);
state = detector.detectLoginState(provinceLoginDoc, { maxAgeMs: 0 });
assert.equal(state.vneidLoginButton, true);
assert.equal(state.loginRequired, true, "Dialog đăng nhập của cổng tỉnh phải chặn luồng");
assert.match(detector.loginHint(state), /Đăng nhập bằng VNeID/);

// NHƯNG cùng cái nút đó nằm ngoài dialog (khu vực tài khoản của trang) thì KHÔNG được coi là chặn
// — nhận nhầm là trợ lý đứng chờ đăng nhập vĩnh viễn trên trang vốn đã vào được.
const inlineLoginDoc = makeDoc([
  node("div", {
    attrs: { class: "header" },
    children: [node("button", { text: "Đăng nhập bằng VNeID" })],
  }),
  node("span", { text: "Danh sách thủ tục hành chính" }),
]);
state = detector.detectLoginState(inlineLoginDoc, { maxAgeMs: 0 });
assert.equal(
  state.loginRequired, false,
  'Nút "Đăng nhập bằng VNeID" ngoài dialog không được chặn luồng',
);

// Host xác thực thì chặn ngay, không cần marker chữ.
state = loadDetector("sso.dancuquocgia.gov.vn")
  .detectLoginState(makeDoc([node("div", { text: "Đang tải" })]), { maxAgeMs: 0 });
assert.equal(state.loginRequired, true);

// ---------- 2. Máy trạng thái trong agency-select.js ----------
assert.match(
  agencySource,
  /if \(arm\.stage === "login"\) return void await loginStage\(arm\);/,
  "run() phải điều phối được chặng login",
);
assert.match(
  agencySource,
  /const ttl = arm\.stage === "login" \? LOGIN_TTL_MS : ARM_TTL_MS;/,
  "Chặng login phải dùng hạn dùng riêng, dài hơn các chặng bấm nút",
);
assert.ok(
  /const LOGIN_TTL_MS = 30 \* 60 \* 1000;/.test(agencySource),
  "Hạn chặng login phải đủ dài cho một lượt quét QR + passcode",
);
assert.match(
  agencySource,
  /if \(seen === "login"\) return void await parkForLogin\(arm\);/,
  "Thấy màn đăng nhập giữa lúc chờ modal thì phải đỗ lại, không bỏ cuộc",
);
assert.match(
  agencySource,
  /if \(loginBlocked\(true\)\) return void await parkForLogin\(arm\);/,
  'Không thấy nút "Nộp trực tuyến" vì chưa đăng nhập thì phải đỗ lại thay vì xoá cờ',
);
assert.match(
  agencySource,
  /atPortalHome: !\(onProcedurePage \|\| infoModal \|\| ownerInfo \|\| ready \|\| login\.loginRequired\),/,
  "Đang ở màn đăng nhập thì panel không được coi là đang ở trang chủ cổng",
);
assert.match(
  agencySource,
  /if \(wasBlocked && !state\.loginRequired\) return void start\(\);/,
  "Đăng nhập xong phải tự chạy tiếp, không đợi cổng đổi URL",
);

// parkForLogin gọi lại lần hai (mỗi nhịp watcher) chỉ được gia hạn, không bắn toast lần nữa.
const parkBody = agencySource.slice(
  agencySource.indexOf("async function parkForLogin(arm)"),
  agencySource.indexOf("async function loginStage(arm)"),
);
assert.match(parkBody, /if \(arm\.stage === "login"\)/, "parkForLogin phải nhận ra cờ đã đỗ sẵn");
assert.ok(
  parkBody.indexOf('if (arm.stage === "login")') < parkBody.indexOf("toast("),
  "Nhánh đã-đỗ-sẵn phải chặn trước toast để không spam mỗi nhịp watcher",
);

// loginStage phải xét cả ba khả năng cổng trả về sau khi đăng nhập.
const loginBody = agencySource.slice(
  agencySource.indexOf("async function loginStage(arm)"),
  agencySource.indexOf("async function run()"),
);
for (const branch of ["formReady() || findInfoModal()", "pickSubmitButton(", "findAgencyCard()"]) {
  assert.ok(loginBody.includes(branch), `loginStage thiếu nhánh: ${branch}`);
}
assert.match(
  loginBody,
  /if \(loginBlocked\(true\)\) \{\s*await setArm\(\{ \.\.\.arm, at: Date\.now\(\) \}\);/,
  "Còn đang xác thực thì phải gia hạn cờ, không để nó hết hạn giữa chừng",
);

// portal-login.js phải nạp TRƯỚC agency-select.js, nếu không cầu nối là undefined ở nhịp đầu.
const manifest = JSON.parse(
  fs.readFileSync(path.join(__dirname, "..", "manifest.json"), "utf8"),
);
const js = manifest.content_scripts[0].js;
assert.ok(
  js.indexOf("content/portal-login.js") >= 0
  && js.indexOf("content/portal-login.js") < js.indexOf("content/agency-select.js"),
  "manifest phải nạp portal-login.js trước agency-select.js",
);

console.log("portal login gate: login stage bridges 'Nộp trực tuyến' and the declaration form");
