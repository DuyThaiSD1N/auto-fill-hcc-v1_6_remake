// Dùng lại giấy tờ trong Ví cá nhân của cổng Bộ Tư pháp (BE chat/wallet_reuse.py).
// Khoá: cờ supportsWalletReuse; cài đặt theo tài khoản reuseWalletDocuments (công tắc khoá tới khi đọc BE); extension KHÔNG đọc token của
// cổng — danh sách lấy từ phần dữ liệu mà chính trang gọi (MAIN world), tệp tải bằng đường không cần token, gửi vào
// phiên TẠM của BE; runActions không await ask (khoá sidebar).
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const stripComments = (src) => src.replace(/\/\/[^\n]*/g, "");
const read = (file) => stripComments(fs.readFileSync(path.join(root, file), "utf8"));
const sidebar = read("sidebar.js");
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
const watcher = read("content/moj-upload-watch-main.js");
const attachCore = read("content/attach-core.js");
const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");

function slice(src, startMarker, endMarker) {
  const start = src.indexOf(startMarker);
  const end = src.indexOf(endMarker, start + startMarker.length);
  assert.ok(start >= 0 && end > start, `Không tìm thấy khối ${startMarker}`);
  return src.slice(start, end);
}

// Cờ + cài đặt tài khoản.
assert.match(sidebar, /supportsWalletReuse: true,/);
assert.match(html, /id="wallet-reuse-switch"[^>]*aria-checked="false"[^>]*disabled/, "mặc định tắt, khoá tới khi đọc BE");
assert.match(html, /id="wallet-reuse-status"/);
assert.match(sidebar, /let reuseWalletDocuments = false;/);
assert.match(slice(sidebar, "function storeAccountSettings", "\n  }\n"),
  /reuseWalletDocuments = settings\?\.reuseWalletDocuments === true;/, "BE cũ thiếu khoá → tắt");
assert.match(slice(sidebar, "function forgetAccountSettings", "\n  }\n"), /reuseWalletDocuments = false;/);
assert.match(sidebar, /saveAccountSetting\(\{ reuseWalletDocuments: !reuseWalletDocuments \}, "wallet-reuse-status"\)/);
assert.match(sidebar, /"wallet-reuse-status"/);

// runActions: chạy nền, không await ask trong runActions.
assert.match(sidebar, /a\.type === "wallet_list"\) \{\s*setTimeout\(\(\) => \{ void runWalletList\(a\); \}, 0\);/);
assert.match(sidebar, /a\.type === "wallet_read"\) \{\s*setTimeout\(\(\) => \{ void runWalletRead\(a\); \}, 0\);/);
assert.match(sidebar, /card\.kind === "wallet_docs"\) return renderWalletDocs\(card\);/);

// Đọc danh sách qua content, báo BE kèm origin.
const list = slice(sidebar, "async function runWalletList", "\n  }\n");
assert.match(list, /sendToContent\(\{ action: "listWalletDocuments", limit: a\.limit, tabs: a\.tabs \}\)/);
assert.match(list, /__event:wallet_list:/);
assert.match(list, /origin: String\(res\?\.origin \|\| ""\)/);

// Tải tệp: chỉ origin https *.gov.vn, không gửi cookie, gửi vào ĐÚNG phiên tạm BE chỉ định.
const readFn = slice(sidebar, "async function runWalletRead", "\n  }\n");
assert.match(readFn, /\\\.gov\\\.vn\$\/i\.test\(origin\)/);
assert.match(readFn, /credentials: "omit"/);
assert.match(readFn, /upload-sessions\/\$\{encodeURIComponent\(sid\)\}\/files/);
assert.match(readFn, /const sid = String\(a\.session_id \|\| ""\)/);
assert.match(readFn, /__event:wallet_uploaded:/);
assert.doesNotMatch(readFn, /uploadFilesToSession\(/, "không đẩy tệp ví vào phiên giấy tờ hồ sơ");

// Thẻ: dựng DOM bằng textContent (tên giấy là dữ liệu công dân), gửi đúng action chọn.
const card = slice(sidebar, "function renderWalletDocs", "\n  }\n\n");
assert.match(card, /name\.textContent = String\(entry\.name \|\| ""\)/);
assert.doesNotMatch(card, /innerHTML\s*=/);
assert.match(card, /card\.pickSend \|\| "__action:wallet_pick"/);
assert.match(card, /JSON\.stringify\(\{ picked:/);

// Xem tệp: khung xem trước TRÊN TRANG (cùng khung với tệp đã nhận), không mở tab mới; nội dung tải thẳng từ cổng (origin
// https *.gov.vn, không cookie); nút chọn ở thanh dưới khung đổi lựa chọn trên thẻ.
const viPreview = slice(sidebar, "function taiDuLieuPreviewVi", "\n  }\n");
assert.match(viPreview, /WALLET_ORIGIN_RE\.test\(origin\)/);
assert.match(viPreview, /credentials: "omit"/);
assert.doesNotMatch(sidebar, /function previewWalletRemote/, "không mở tệp trong ví ở tab mới");
assert.match(slice(sidebar, "async function openWalletPreview", "\n  }\n"), /action: "tlndPreviewOpen"/);
assert.match(card, /if \(remote\) openPreview\(entry\);/);
assert.match(card, /fid: `vi:\$\{e\.uri\}`/);
assert.match(sidebar, /\(wallet \? taiDuLieuPreviewVi\(fid\) : taiDuLieuPreview\(fid\)\)/);
assert.match(sidebar, /msg\?\.action === "tlndPreviewChon" && walletPreview/);
const contentJs = read("content.js");
assert.match(contentJs, /d\?\.type === "tlnd-preview-chon"[\s\S]*action: "tlndPreviewChon"/);
const previewJs = read("preview.js");
assert.match(previewJs, /chanEl\.hidden = typeof tep\?\.chon !== "boolean";/);
assert.match(previewJs, /type: "tlnd-preview-chon", fid: tep\.fid/);
assert.match(previewJs, /cungNhom && d\.giuViTri === true \? chiSo/, "bấm chọn trên thẻ không làm khung nhảy tệp");

// Hai mục bấm để đổi (Tài liệu tải lên / Tài liệu được cấp), số liền qua hai mục; chọn tất cả theo mục đang mở.
assert.match(card, /const tabbed = entries\.some\(\(e\) => e\.tab\);/);
assert.match(card, /e\.tab === "issued" \? "issued" : "uploaded"/);
assert.match(card, /` số \$\{Math\.min\(\.\.\.nos\)\}–\$\{Math\.max\(\.\.\.nos\)\}`/);
assert.match(card, /const tabEntries = inTab\(activeTab\);\s*const allOn = tabEntries\.every/);
assert.match(card, /`Đã chọn \$\{picked\.size\}\/\$\{entries\.length\}`/);
assert.match(css, /\.wallet-item\[hidden\]\{display:none\}|\.wallet-item\[hidden\][^{]*\{display:none\}/);
assert.match(card, /walletSizeText\(entry\.size\)/);

// MAIN world: nghe phần dữ liệu danh sách ví, KHÔNG đọc header (token).
assert.match(watcher, /__HCC_MOJ_WALLET_LIST__/);
assert.match(watcher, /\\\/api\\\/CongDan\\\/TaiLieuCaNhan/);
assert.match(watcher, /const uploaded = filter === "uploaded";/);
assert.match(watcher, /if \(uploaded \? u\.searchParams\.get\("uploadBy"\) !== "MY" : filter !== "issued"\) return;/);
assert.match(watcher, /tab: uploaded \? "uploaded" : "issued",/);
assert.match(watcher, /keyword: String\(u\.searchParams\.get\("keyword"\) \|\| ""\),/);
assert.doesNotMatch(watcher, /getResponseHeader|getAllResponseHeaders|setRequestHeader|[Aa]uthorization/);

// Content: mở ví của dòng hồ sơ, gom theo trang, luôn đóng hộp thoại.
const listFn = slice(attachCore, "async function listWalletDocuments", "\n}\n");
assert.match(listFn, /openDocumentWalletForRow\(row, \{\}\)/);
assert.match(listFn, /foldedNodeText\(b\) === "sau"/);
assert.match(listFn, /finally \{[\s\S]*closeWalletListDialog\(\)/);
assert.match(attachCore, /msg\?\.action === "listWalletDocuments"/);
assert.match(attachCore, /listWalletDocuments\(msg\.limit, msg\.tabs\)/);
// Tab được cấp chỉ đọc khi BE xin; danh sách kết quả tìm kiếm (keyword) không lẫn vào danh sách ví.
assert.match(listFn, /const withIssued = Array\.isArray\(tabs\) && tabs\.includes\("issued"\);/);
assert.match(listFn, /\|\| data\.keyword\) return;/);
assert.match(listFn, /\.map\(\(item\) => \(\{ \.\.\.item, tab \}\)\)/);

// Bản supportsWalletPick: giấy lấy từ ví đính bằng nút "Chọn" của đúng dòng trong ví (cổng chỉ tính dùng lại giấy tờ
// khi chọn từ ví), khớp đúng id qua danh sách API; không thấy thì vẫn tải lên để không sót giấy.
assert.match(sidebar, /supportsWalletPick: true,/);
const pick = slice(attachCore, "async function pickExistingWalletDocument", "\n}\n");
assert.match(pick, /String\(item\?\.id \|\| ""\) === wantId/);
assert.match(pick, /input\[name="keyword"\]/);
assert.match(pick, /let row = latest \? findRow\(\) : null;/, "chưa có danh sách mang id thì chưa khớp theo tên");
assert.match(pick, /button\.click\(\);\s*return \{ ok: true \};/, "bấm một lần (clickLikeUser bắn hai click)");
const one = slice(attachCore, "async function attachOneFileViaDocumentWallet", "\n}\n");
assert.match(one, /if \(planItem\.walletPick\) \{[\s\S]*pickExistingWalletDocument\(dialog, planItem\.walletPick\)[\s\S]*waitForPersistedAttachment\(row, planItem, existingName, 8000\)/);
assert.ok(one.indexOf("pickExistingWalletDocument") < one.indexOf('findButtonByText(dialog, ["Tải lên từ thiết bị"])'),
  "chọn từ ví trước, tải lên chỉ là đường dự phòng");
assert.match(attachCore, /if \(planItem\.walletPick\?\.name\) ownNames\.push\(planItem\.walletPick\.name\);/);

// Khung chat là cột flex cao cố định: thẻ phải flex:none, không thì bị co còn mỗi viền.
assert.match(css, /\.wallet-card\{[^}]*flex:none/);

// Auto Fill cài cùng file watcher với cờ chung __HCC_MOJ_FILE_API_WATCH__: nó nạp trước thì bản này vẫn phải nghe được
// danh sách ví (lỗi thật: máy cài cả hai extension báo "chưa đọc được Ví cá nhân").
{
  const vm = require("node:vm");
  const src = fs.readFileSync(path.join(root, "content/moj-upload-watch-main.js"), "utf8");
  const events = [];
  function FakeXhr() { this.listeners = {}; }
  FakeXhr.prototype.open = function () {};
  FakeXhr.prototype.send = function () {};
  FakeXhr.prototype.addEventListener = function (type, fn) { this.listeners[type] = fn; };
  const window = { __HCC_MOJ_FILE_API_WATCH__: true, XMLHttpRequest: FakeXhr };
  const sandbox = {
    window, URL, JSON, Number, String, Array,
    location: { hostname: "dichvucongnganhtuphap.moj.gov.vn", href: "https://dichvucongnganhtuphap.moj.gov.vn/nop-ho-so/1" },
    document: { dispatchEvent: (ev) => events.push(ev) },
    CustomEvent: function (type, init) { this.type = type; this.detail = init.detail; },
  };
  vm.runInNewContext(src, sandbox);
  const xhr = new FakeXhr();
  xhr.open("GET", "https://apidvc.moj.gov.vn/api/CongDan/TaiLieuCaNhan?page=1&pageSize=10&filter=uploaded&uploadBy=MY");
  xhr.send();
  Object.assign(xhr, { status: 200, responseType: "", responseText: JSON.stringify({ data: { totalItems: 1, items: [
    { id: "1", name: "a.pdf", uri: "u-1", size: 5, createdAt: "2026-11-20T10:00:00" }] } }) });
  xhr.listeners.loadend();
  assert.equal(events.length, 1, "cờ chung đã đặt (Auto Fill nạp trước) mà vẫn phải phát danh sách ví");
  assert.equal(events[0].type, "__HCC_MOJ_WALLET_LIST__");
  const detail = JSON.parse(events[0].detail);
  assert.equal(detail.origin, "https://apidvc.moj.gov.vn");
  assert.deepEqual(detail.items.map((i) => i.uri), ["u-1"]);
  assert.equal(detail.tab, "uploaded");
  const issued = new FakeXhr();
  issued.open("GET", "https://apidvc.moj.gov.vn/api/CongDan/TaiLieuCaNhan?page=1&pageSize=10&filter=issued&status=5&uploadBy=OTHER&keyword=KQ");
  issued.send();
  Object.assign(issued, { status: 200, responseType: "", responseText: JSON.stringify({ data: { totalItems: 1, items: [
    { id: "2", name: "KQ_1.pdf", uri: "u-2", size: 5, isSigned: true }] } }) });
  issued.listeners.loadend();
  const second = JSON.parse(events[1].detail);
  assert.equal(second.tab, "issued");
  assert.equal(second.keyword, "KQ");
  assert.equal(second.items[0].signed, true);
}

console.log("wallet reuse (handfree) passed");
