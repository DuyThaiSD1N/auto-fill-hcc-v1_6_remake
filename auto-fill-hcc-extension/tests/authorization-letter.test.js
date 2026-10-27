// Giấy ủy quyền soạn tại quầy: mục vàng trên màn chọn thủ tục → tab riêng authorization-letter.html.
// Không phải thủ tục DVC — BE chỉ gửi mục này khi extension khai supportsAuthorizationLetter.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8");
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const sidebar = strip(read("sidebar.js"));
const page = strip(read("authorization-letter.js"));
const html = read("authorization-letter.html");

test("sidebar khai capability để BE gửi mục Giấy tờ soạn tại quầy", () => {
  assert.match(sidebar, /supportsAuthorizationLetter:\s*true/);
});

test("mục vàng chỉ vẽ công cụ extension biết mở, bấm là mở TAB riêng", () => {
  assert.match(sidebar, /const COUNTER_TOOL_PAGES = \{ "giay-uy-quyen": "authorization-letter\.html" \}/);
  assert.match(sidebar, /filter\(\(it\) => COUNTER_TOOL_PAGES\[it\.key\]\)/);
  assert.match(sidebar, /chrome\.tabs\.create\(\{ url \}/);
  const render = sidebar.slice(sidebar.indexOf("function renderServiceList(card)"));
  assert.match(render.slice(0, 4000), /renderCounterTools\(card\.counterTools\)/);
});

test("trang nạp đủ config → auth → máy quét trước script của trang", () => {
  const order = ["api/config.js", "api/auth.js", "lib/scanAgent.js", "authorization-letter.js"]
    .map((f) => html.indexOf(`<script src="${f}"></script>`));
  assert.ok(order.every((i) => i > 0), "thiếu script");
  assert.deepEqual([...order].sort((a, b) => a - b), order, "sai thứ tự nạp");
});

test("ba nguồn ảnh cùng đổ vào MỘT phiên tải ảnh", () => {
  assert.match(page, /apiJson\("\/api\/v1\/upload-sessions", \{ method: "POST" \}\)/);
  assert.match(page, /qr_png_base64/, "QR điện thoại");
  assert.match(page, /window\.ScanAgent\.connect\(/, "máy quét tại quầy");
  assert.match(page, /form\.append\("files", f, f\.name\)/, "chọn tệp / kéo thả");
});

test("đọc ảnh, dựng docx/pdf qua endpoint giấy ủy quyền", () => {
  assert.match(page, /\$\{API\}\/extract`, jsonInit\("POST", \{ session_id: sid \}\)/);
  assert.match(page, /const sid = state\.sid;/, "chốt phiên lúc bắt đầu đọc");
  assert.match(page, /renderFile\("docx"\)/);
  assert.match(page, /renderFile\("pdf"\)/);
});

test("bản xem trước là CHÍNH file PDF BE dựng — không chép mẫu giấy sang extension", () => {
  assert.match(page, /\$\("preview"\)\.src = `\$\{state\.previewUrl\}#toolbar=0/);
  assert.doesNotMatch(page, /BÊN ĐƯỢC ỦY QUYỀN|THỜI GIAN ỦY QUYỀN/, "câu chữ mẫu giấy chỉ nằm ở BE");
});

test("đóng tab xoá ảnh căn cước ngay (keepalive), không chờ phiên hết hạn", () => {
  assert.match(page, /addEventListener\("pagehide", \(\) => \{ void deleteSession\(state\.sid, \{ keepalive: true \}\)/);
  assert.match(page, /keepalive: true, headers: \{ Authorization: `Bearer \$\{token\}` \}/);
});

test("đang soạn dở thì báo bận để extension không tự nạp lại (nạp lại là đóng tab)", () => {
  assert.match(page, /msg\?\.action !== "hccTabDangLamViec"/);
  assert.match(page, /coPanel: busy, focus: busy, an: false/);
});

test("câu bảo mật đúng thực tế: ảnh CÓ gửi lên hệ thống để đọc", () => {
  assert.match(html, /Ảnh được gửi lên hệ thống để đọc và tự xoá khi đóng cửa sổ này\./);
  assert.doesNotMatch(html, /không gửi đi đâu/);
});

test("Bỏ hết, chọn lại → dọn kết quả đọc (câu hỏi vai, bước 2) và quay về đầu bước 1", () => {
  const clear = page.slice(page.indexOf('$("clearFiles").addEventListener'), page.indexOf('$("extractBtn").addEventListener'));
  assert.match(clear, /resetReadResult\(\);\s*void replaceSession\(\);/);
  const reset = page.slice(page.indexOf("function resetReadResult()"), page.indexOf("async function replaceSession()"));
  for (const must of [/state\.people = \[\]/, /state\.assign = \[\]/, /state\.sides = \{ A: \[\], B: \[\] \}/,
    /state\.reached = 1/, /\$\("rolePick"\)\.hidden = true/, /\$\("uploadActions"\)\.hidden = false/, /goStep\(1\)/]) {
    assert.match(reset, must);
  }
  assert.doesNotMatch(reset, /\$\("content"\)\.value = ""/, "nội dung bước 3 cán bộ tự gõ — giữ lại");
});

test("bộ ảnh đổi sau khi đã đọc → phải đọc lại", () => {
  const refresh = page.slice(page.indexOf("async function refreshFiles()"), page.indexOf("async function uploadFiles("));
  assert.match(refresh, /if \(hasReadResult\(\)\) \{\s*resetReadResult\(\);/);
});

test("kết quả đọc về muộn của bộ ảnh cũ bị bỏ, không bật lại câu hỏi vai", () => {
  const ex = page.slice(page.indexOf("async function extract()"), page.indexOf("async function askRole("));
  assert.match(ex, /if \(sid !== state\.sid \|\| seq !== state\.readSeq\) return;/);
  assert.match(page.slice(page.indexOf("function resetReadResult()")), /state\.readSeq\+\+/);
});

// ── Chọn bên: mỗi bên MỘT hoặc NHIỀU người ──

test("mỗi người chọn Bên ủy quyền / Bên được ủy quyền, chạm lại để bỏ chọn", () => {
  assert.match(page, /const SIDE_LABEL = \{ A: "Bên ủy quyền", B: "Bên được ủy quyền" \}/);
  assert.match(page, /state\.assign\[i\] = state\.assign\[i\] === side \? "" : side;/);
  assert.doesNotMatch(read("authorization-letter.html"), /người NHỜ/, "bỏ cách hỏi 'người nhờ' khó hiểu");
});

test("hai người: chọn bên cho một người thì người kia tự sang bên còn lại", () => {
  const pick = page.slice(page.indexOf("function pickSide("), page.indexOf("function renderRolePick("));
  assert.match(pick, /state\.people\.length === 2/);
  assert.match(pick, /state\.assign\[i\] === "A" \? "B" : "A"/);
});

test("gửi BE danh sách người của từng bên", () => {
  assert.match(page, /benUyQuyen: state\.sides\.A\.map\(\(e\) => partyOf\(e\.data\)\)/);
  assert.match(page, /benDuocUyQuyen: state\.sides\.B\.map\(\(e\) => partyOf\(e\.data\)\)/);
});

test("bước 2 thêm / bỏ người; quay lại bước 1 rồi Tiếp tục không mất chỗ đã sửa", () => {
  assert.match(page, /state\.sides\[add\.dataset\.add\]\.push\(/);
  assert.match(page, /state\.sides\[side\]\.splice\(/);
  const apply = page.slice(page.indexOf("function applyAssign()"), page.indexOf("function startManual()"));
  assert.match(apply, /old\.find\(\(e\) => e\.src === i\) \|\| entryFromPerson\(i\)/);
});


// ── Kiểm tra dữ liệu bước 2 (chạy THẬT bộ kiểm tra trong vm) ──
const vm = require("node:vm");
function loadValidators() {
  const src = read("authorization-letter.js");
  const start = src.indexOf("  // ── Kiểm tra dữ liệu bước 2 ──");
  const endMarker = "const fieldError = ";
  const end = src.indexOf("\n", src.indexOf(endMarker));
  const ctx = vm.createContext({ Date, String, Number, RegExp });
  vm.runInContext(src.slice(start, end) + "\n;this.api = { fieldError, normalizeField };", ctx);
  return ctx.api;
}
const V = loadValidators();
const person = (o) => ({ hoTen: "Nguyễn Thị Minh", ngaySinh: "", soDinhDanh: "", ngayCap: "", noiCap: "", noiThuongTru: "", ...o });

test("giá trị rác trong ảnh báo lỗi đều bị chặn", () => {
  const d = person({ ngaySinh: "222222222", soDinhDanh: "0362222222222222222222222222",
    ngayCap: "2222222222222222222", noiThuongTru: "ttttttttttttttttttttttttt" });
  for (const key of ["ngaySinh", "soDinhDanh", "ngayCap", "noiThuongTru"]) {
    assert.ok(V.fieldError(key, d), `${key} phải báo lỗi`);
  }
});

test("giá trị đúng thì không báo lỗi; ô trống (viết tay) hợp lệ trừ họ tên", () => {
  const d = person({ hoTen: "NGUYỄN THỊ BÍCH NHUNG", ngaySinh: "26/10/1993", soDinhDanh: "036193005241",
    ngayCap: "10/08/2021", noiCap: "Cục Cảnh sát quản lý hành chính về trật tự xã hội", noiThuongTru: "KĐT Văn Phú, Hà Đông, Hà Nội" });
  for (const key of Object.keys(d)) assert.equal(V.fieldError(key, d), "", key);
  assert.equal(V.fieldError("ngayCap", person({})), "");
  assert.ok(V.fieldError("hoTen", person({ hoTen: "" })));
});

test("ngày: sai lịch, tương lai, ngày cấp trước ngày sinh", () => {
  assert.ok(V.fieldError("ngaySinh", person({ ngaySinh: "31/02/1990" })));
  assert.ok(V.fieldError("ngaySinh", person({ ngaySinh: "01/01/2999" })));
  assert.match(V.fieldError("ngayCap", person({ ngaySinh: "01/01/2000", ngayCap: "01/01/1999" })), /sau ngày sinh/);
});

test("số định danh: CCCD 12 số, CMND 9 số, hộ chiếu chữ + số", () => {
  for (const ok of ["036193005241", "123456789", "C1234567"]) assert.equal(V.fieldError("soDinhDanh", person({ soDinhDanh: ok })), "", ok);
  for (const bad of ["03619300524", "0361930052411", "abc"]) assert.ok(V.fieldError("soDinhDanh", person({ soDinhDanh: bad })), bad);
});

test("họ tên không có số", () => {
  assert.ok(V.fieldError("hoTen", person({ hoTen: "Nguyen 123" })));
});

test("rời ô thì chuẩn hoá ngày và số định danh", () => {
  assert.equal(V.normalizeField("ngaySinh", "5/9/1990"), "05/09/1990");
  assert.equal(V.normalizeField("ngayCap", "05-09-2021"), "05/09/2021");
  assert.equal(V.normalizeField("soDinhDanh", " 036 193 005 241 "), "036193005241");
});

test("sang bước 3 / tải Word / in đều phải qua kiểm tra", () => {
  assert.match(page, /if \(n === 3 && state\.step === 2 && !validateSides\(\)\) return;/);
  const ready = page.slice(page.indexOf("function namesReady()"), page.indexOf("async function downloadWord()"));
  assert.match(ready, /if \(!validateSides\(\)\) return false;/);
  assert.match(ready, /copies < 1 \|\| copies > 20/);
});
