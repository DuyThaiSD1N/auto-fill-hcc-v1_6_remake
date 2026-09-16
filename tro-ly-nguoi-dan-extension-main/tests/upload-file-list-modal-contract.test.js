const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");

test("checklist mở modal danh sách theo từng loại giấy tờ", () => {
  assert.match(html, /id="file-list-scrim"/);
  assert.match(html, /role="dialog" aria-modal="true"/);
  assert.match(sidebar, /className = "doc-files-btn"/);
  assert.match(sidebar, /openUploadFileList\(\{/);
  assert.match(sidebar, /event\.key !== "Tab"/);
  assert.match(sidebar, /file\.doc_key === activeFileGroup\.docKey/);
  assert.match(sidebar, /activeFileGroup\.unknown\s*\? !file\.doc_key/);
  assert.match(css, /\.file-list-dialog \{/);
});

test("mở danh sách chỉ lấy metadata của upload session", () => {
  const start = sidebar.indexOf("async function loadUploadSessionFiles");
  const end = sidebar.indexOf("async function openUploadFileList", start);
  const metadataLoader = sidebar.slice(start, end);
  assert.ok(start >= 0 && end > start);
  assert.match(sidebar, /uploadSessionFetch\(`\$\{BASE_URL\}\/api\/v1\/upload-sessions\/\$\{encodeURIComponent\(sid\)\}`\)/);
  assert.match(sidebar, /uploadSessionFiles = Array\.isArray\(data\?\.files\)/);
  assert.doesNotMatch(metadataLoader, /\.blob\(\)/);
});

test("mọi REST upload-session từ extension đều đi qua Bearer auth", () => {
  assert.match(sidebar, /const uploadSessionFetch = \(url, init\) => window\.tlndAuth\.authFetch\(url, init\)/);
  const directFetches = sidebar.match(/fetch\(`\$\{BASE_URL\}\/api\/v1\/upload-sessions/g) || [];
  assert.equal(directFetches.length, 0);
  assert.match(sidebar, /uploadSessionFetch\(`\$\{BASE_URL\}\/api\/v1\/upload-sessions[\s\S]*method: "DELETE"/);
  assert.match(sidebar, /uploadSessionFetch\(`\$\{BASE_URL\}\/api\/v1\/upload-sessions[\s\S]*method: "POST", body: fd/);
});

test("xóa ngay theo fid, không có bước xác nhận", () => {
  assert.match(sidebar, /deleteUploadSessionFile\(file\)/);
  assert.match(sidebar, /files\/\$\{encodeURIComponent\(file\.fid\)\}`,[\s\S]*method: "DELETE"/);
  assert.match(sidebar, /uploadSessionFiles\.filter\(\(item\) => item\.fid !== file\.fid\)/);
  assert.doesNotMatch(sidebar, /confirm\s*\(/);
});

test("khi phiên đã chốt chỉ xem và không tạo nút xóa", () => {
  assert.match(sidebar, /const locked = !!uploadSessionProgress\?\.complete/);
  assert.match(sidebar, /if \(locked\)[\s\S]*lock\.textContent = "Đã chốt";[\s\S]*else \{/);
  assert.match(sidebar, /uploadSessionProgress\?\.complete \|\| deletingFileIds\.has/);
});

test("lượt điều chỉnh mở ngay cùng upload session và không tự bật hộp chọn tệp", () => {
  assert.match(sidebar, /a\.type === "resume_upload_session" && a\.session_id/);
  assert.match(sidebar, /const snapshotPromise = setUploadSession\(a\.session_id\);[\s\S]*subscribeUploadSession\(a\.session_id\);[\s\S]*await snapshotPromise/);
  assert.match(sidebar, /skipped: Number\(res\?\.skipped\) \|\| 0/);
});

test("sang Thành phần hồ sơ thì gỡ các action sửa Kê khai cũ", () => {
  assert.match(sidebar, /b\.dataset\.send = c\.send \|\| ""/);
  assert.match(sidebar, /b\.dataset\.renderState = lastState \|\| ""/);
  assert.match(sidebar, /function hideStaleDeclarationActions\(\)/);
  assert.match(sidebar, /attachmentTarget[\s\S]*attachmentComponentCount > 0[\s\S]*hideStaleDeclarationActions\(\)/);
  assert.match(sidebar, /data-send="__action:refill"/);
  assert.match(sidebar, /data-send="__action:add_documents"/);
  assert.match(sidebar, /button\.dataset\.renderState === "done"/);
});

test("xóa hết tệp khóa lại nút chốt giấy tờ", () => {
  assert.match(sidebar, /docsReceived = gotAny/);
  assert.match(sidebar, /\$docsDoneChip\.disabled = !gotAny/);
});

test("đổi hoặc kết thúc phiên đóng modal và xóa state cũ", () => {
  assert.match(sidebar, /function resetUploadFileListState\(\)/);
  assert.match(sidebar, /if \(uploadSid !== sid\) resetUploadFileListState\(\)/);
  assert.match(sidebar, /uploadSid = sid;[\s\S]*return loadUploadSessionFiles\(\)\.catch/);
  assert.match(sidebar, /resetUploadFileListState\(\);[\s\S]{0,600}?await api\.deleteConversation\(reason/);
});
