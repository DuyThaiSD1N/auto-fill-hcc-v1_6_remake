const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const vneidSso = fs.readFileSync(path.join(root, "content/vneid-sso.js"), "utf8");

const SSO_HOST = "https://sso.dancuquocgia.gov.vn/*";

test("VNeID SSO được inject content scripts và được phép nhúng sidebar", () => {
  const contentMatches = (manifest.content_scripts || []).flatMap((entry) => entry.matches || []);
  const resourceMatches = (manifest.web_accessible_resources || [])
    .flatMap((entry) => entry.matches || []);

  assert.ok(contentMatches.includes(SSO_HOST));
  assert.ok(resourceMatches.includes(SSO_HOST));
});

test("trang SSO mở panel trong journey và chỉ thu gọn sau hướng dẫn", () => {
  assert.match(content, /const IS_LOGIN_PAGE = \/xacthuc\|vneid\|sso\//);
  assert.match(content, /j\?\.keep_open[\s\S]*createPanel\(tabId\)/);
  assert.match(sidebar, /collapseAfter && willSpeak[\s\S]*minimizePanel\(\)/);
  assert.match(sidebar, /collapseAfter && !willSpeak[\s\S]*7000/);
});

test("detector phân biệt mã đăng nhập, chia sẻ dữ liệu và passcode", () => {
  const context = { window: {} };
  vm.createContext(context);
  vm.runInContext(vneidSso, context);
  const H = context.window.__TLND__;

  const makeScope = ({ inputSelector, buttonText }) => ({
    textContent: "",
    children: [],
    getClientRects: () => [{}],
    querySelector: (selector) => selector.includes(inputSelector) ? {} : null,
    querySelectorAll: (selector) => selector === "button" ? [{
      textContent: buttonText, children: [], getClientRects: () => [{}],
    }] : [],
  });
  const makeMarker = (textContent, scope) => ({
    textContent, children: [], parentElement: scope,
    getClientRects: () => [{}], closest: () => scope,
  });
  const makeDoc = (marker) => ({ querySelectorAll: () => [marker] });
  const visible = (element) => element?.getClientRects?.().length > 0;

  const loginScope = makeScope({ inputSelector: 'input[inputmode="numeric"]', buttonText: "Xác nhận" });
  const loginDoc = makeDoc(makeMarker("Nhập mã xác nhận đăng nhập", loginScope));
  assert.equal(H.detectVneidLoginCodePrompt(loginDoc, visible), true);
  assert.equal(H.detectVneidDataSharingPrompt(loginDoc, visible), false);
  assert.equal(H.detectVneidPasscodePrompt(loginDoc, visible), false);

  const sharingScope = makeScope({ inputSelector: 'input[type="checkbox"]', buttonText: "Xác nhận chia sẻ" });
  const sharingDoc = makeDoc(makeMarker(
    "Tôi đã đọc và hiểu rõ nội dung mục đích; Quyền, nghĩa vụ của chủ thể dữ liệu và đồng ý với các nội dung này.",
    sharingScope,
  ));
  assert.equal(H.detectVneidLoginCodePrompt(sharingDoc, visible), false);
  assert.equal(H.detectVneidDataSharingPrompt(sharingDoc, visible), true);
  assert.equal(H.detectVneidPasscodePrompt(sharingDoc, visible), false);

  const passcodeScope = makeScope({ inputSelector: 'input[type="number"]', buttonText: "Xác nhận" });
  const passcodeDoc = makeDoc(makeMarker("Nhập passcode", passcodeScope));
  assert.equal(H.detectVneidLoginCodePrompt(passcodeDoc, visible), false);
  assert.equal(H.detectVneidDataSharingPrompt(passcodeDoc, visible), false);
  assert.equal(H.detectVneidPasscodePrompt(passcodeDoc, visible), true);

  const unrelated = {
    textContent: "Xác nhận chia sẻ thông tin để đăng nhập", children: [], parentElement: sharingScope,
    getClientRects: () => [{}], closest: () => sharingScope,
  };
  assert.equal(H.detectVneidDataSharingPrompt(makeDoc(unrelated), visible), false);
  assert.equal(H.detectVneidPasscodePrompt(makeDoc(unrelated), visible), false);
});

test("ba modal đổi chữ ký trang, mở lại panel và gửi context lên backend", () => {
  assert.match(content, /vneidLoginCodePrompt/);
  assert.match(content, /vneidDataSharingPrompt/);
  assert.match(content, /vneidPasscodePrompt/);
  assert.match(content, /t === "restorePanel"\) restorePanel\(\)/);
  assert.match(sidebar, /ctx\.vneidLoginCodePrompt \? 1 : 0/);
  assert.match(sidebar, /ctx\.vneidDataSharingPrompt \? 1 : 0/);
  assert.match(sidebar, /ctx\.vneidPasscodePrompt \? 1 : 0/);
  assert.match(sidebar, /ctx\.vneidLoginCodePrompt \|\| ctx\.vneidDataSharingPrompt \|\| ctx\.vneidPasscodePrompt/);
  assert.match(sidebar, /vneidLoginCodePrompt: !!c\.vneidLoginCodePrompt/);
  assert.match(sidebar, /vneidDataSharingPrompt: !!c\.vneidDataSharingPrompt/);
  assert.match(sidebar, /vneidPasscodePrompt: !!c\.vneidPasscodePrompt/);
});

test("modal VNeID trong iframe vẫn được gom vào page context", () => {
  assert.match(content, /action === "getVneidModalContext"/);
  assert.match(content, /if \(!Object\.values\(modalSignals\)\.some\(Boolean\)\) return/);
  assert.match(sidebar, /function readPageContext\(\)/);
  assert.match(sidebar, /action: "getVneidModalContext"/);
  assert.match(sidebar, /modal\?\.ok[\s\S]*\.\.\.modal, ok: true/);
});

test("có log xuyên suốt detector đến phản hồi backend mà không đọc giá trị passcode", () => {
  const auth = fs.readFileSync(path.join(root, "api/auth.js"), "utf8");
  assert.match(content, /\[TLND-VNeID\]\[content\] modal-state/);
  assert.match(content, /\[TLND-VNeID\]\[content\] send-modal-context/);
  assert.match(sidebar, /\[TLND-VNeID\]\[sidebar\] received-modal-context/);
  assert.match(sidebar, /\[TLND-VNeID\]\[sidebar\] send-page-status/);
  assert.match(sidebar, /\[TLND-VNeID\]\[sidebar\] backend-reply/);
  assert.match(auth, /\[TLND-Auth\] API trả 401/);
  assert.doesNotMatch(content + sidebar, /passcodeValue|otpValue/);
});
