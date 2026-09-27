// Dòng tên "Văn bản ủy quyền" trong BẢNG THÀNH PHẦN HỒ SƠ là thành phần thật phải đính, KHÔNG phải
// bảng ủy quyền ở bước chủ hồ sơ của cổng tư pháp. Nhận nhầm → hasAttachmentTarget() = false →
// listener attachFilesByPlan im lặng → sidebar báo "0 tệp, 0 lỗi" (thờ cúng liệt sĩ, Bộ Nội vụ:
// dòng 1 là "- Văn bản ủy quyền.").
//
// Chạy THẬT các hàm của attach-core.js trong vm với DOM giả dựng theo đúng tiêu đề bảng đọc từ
// snapshot: "thong tin handfree/thờ cúng ls" (iGate, tiêu đề ở <th>, không <thead>) và
// "mẫu toàn trình/chứng thực bs/trường hợp uỷ quyền.html" + "đính kèm.html" (tư pháp, có <thead>).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const src = fs.readFileSync(path.join(root, "content/attach-core.js"), "utf8");

function slice(from, to) {
  const start = src.indexOf(from);
  const end = src.indexOf(to, start + 1);
  assert.ok(start >= 0 && end > start, `không cắt được đoạn ${from} → ${to}`);
  return src.slice(start, end);
}

const fold = (s) => String(s || "")
  .replace(/Đ/g, "D").replace(/đ/g, "d")
  .normalize("NFD").replace(/[̀-ͯ]/g, "")
  .replace(/\s+/g, " ").trim().toLowerCase();

// ── DOM giả tối thiểu ──
function table({ thead = null, th = [] } = {}) {
  return {
    querySelector: (sel) => (sel === "thead" && thead ? { textContent: thead } : null),
    querySelectorAll: (sel) => (sel === "th" ? th.map((t) => ({ textContent: t })) : []),
  };
}
function row(text, tbl) {
  return { textContent: text, closest: (sel) => (sel === "table" ? tbl : null) };
}
function button(text, tr) {
  return { textContent: text, closest: (sel) => (sel === "tr" ? tr : null) };
}

// Tiêu đề thật từ snapshot.
const MOHA = table({ th: ["STT", "Tên giấy tờ", "Loại bản", "Mẫu giấy tờ", "Đính kèm giấy tờ"] });
const TU_PHAP_AUTH = table({ thead: "Tên hồ sơ Đính kèm Hành động" });
const TU_PHAP_COMPONENT = table({
  thead: "STT Tên thành phần hồ sơ Đính kèm tệp tin Loại chứng thực Thao Tác",
});

function loadContext(extra = {}) {
  const ctx = {
    foldChoiceText: fold,
    foldedNodeText: (el) => fold(el?.textContent),
    isVisible: () => true,
    findCopyCertificationAttachmentRow: () => null,
    document: { querySelector: () => null, querySelectorAll: () => [] },
    ...extra,
  };
  vm.createContext(ctx);
  const code = [
    // Nạp kèm helper thật để test chạy được trên CẢ bản cũ (chỉ xét nút đầu, dùng
    // findButtonByText) — thiếu nó thì bản cũ đỏ vì ReferenceError chứ không vì hành vi.
    slice("function findButtonByText", "\nfunction findButtonsByText"),
    slice("const AUTHORIZATION_ROW_MARKERS", "function findAuthorizationAttachmentRow"),
    slice("function hasAttachmentTarget", "\nconst COPY_CERT_ATTACHMENT_SNIPPETS"),
    "this.isAuthorizationAttachmentRow = isAuthorizationAttachmentRow;",
    "this.hasAttachmentTarget = hasAttachmentTarget;",
  ].join("\n");
  vm.runInContext(code, ctx);
  return ctx;
}

test("iGate Bộ Nội vụ: dòng 'Văn bản ủy quyền' trong bảng thành phần KHÔNG bị loại", () => {
  const { isAuthorizationAttachmentRow } = loadContext();
  const r = row("1 - Văn bản ủy quyền. 1 Bản chính 1 Bản sao Chọn tệp tin", MOHA);
  assert.equal(isAuthorizationAttachmentRow(r), false);
});

test("tư pháp: bảng ủy quyền ở bước chủ hồ sơ VẪN bị loại như cũ", () => {
  const { isAuthorizationAttachmentRow } = loadContext();
  assert.equal(
    isAuthorizationAttachmentRow(row("Đính kèm tài liệu ủy quyền Chọn tệp đính kèm", TU_PHAP_AUTH)),
    true,
  );
  // Nhận bằng tiêu đề kể cả khi tên dòng đổi, không còn chữ ủy quyền.
  assert.equal(isAuthorizationAttachmentRow(row("Tệp đính kèm", TU_PHAP_AUTH)), true);
});

test("tư pháp: bảng thành phần hồ sơ không bị loại", () => {
  const { isAuthorizationAttachmentRow } = loadContext();
  const r = row("1 Bản chính giấy tờ làm cơ sở để chứng thực bản sao", TU_PHAP_COMPONENT);
  assert.equal(isAuthorizationAttachmentRow(r), false);
});

test("dòng lẻ không nằm trong bảng mà mang chữ ủy quyền: giữ hành vi cũ (loại)", () => {
  const { isAuthorizationAttachmentRow } = loadContext();
  assert.equal(isAuthorizationAttachmentRow(row("Giấy ủy quyền", null)), true);
});

test("thờ cúng liệt sĩ: trang có đích đính kèm (lỗi gốc)", () => {
  const r1 = row("1 - Văn bản ủy quyền. 1 Bản chính Chọn tệp tin", MOHA);
  const r2 = row("2 - Đơn đề nghị Mẫu số 18 Phụ lục I Chọn tệp tin", MOHA);
  const buttons = [button("attachment Chọn tệp tin", r1), button("attachment Chọn tệp tin", r2)];
  const { hasAttachmentTarget } = loadContext({
    document: { querySelector: () => null, querySelectorAll: (s) => (s === "button" ? buttons : []) },
  });
  assert.equal(hasAttachmentTarget(), true);
});

test("nút ĐẦU nằm ở bảng ủy quyền nhưng còn nút hợp lệ phía sau → vẫn có đích", () => {
  // Khoá riêng sửa thứ hai: không được chỉ xét nút đầu tiên.
  const auth = row("Đính kèm tài liệu ủy quyền", TU_PHAP_AUTH);
  const comp = row("1 Bản chính giấy tờ", TU_PHAP_COMPONENT);
  const buttons = [button("Chọn tệp đính kèm", auth), button("Chọn tệp đính kèm", comp)];
  const { hasAttachmentTarget } = loadContext({
    document: { querySelector: () => null, querySelectorAll: (s) => (s === "button" ? buttons : []) },
  });
  assert.equal(hasAttachmentTarget(), true);
});

test("trang chủ hồ sơ tư pháp chỉ có bảng ủy quyền → KHÔNG phải trang đính kèm", () => {
  const auth = row("Đính kèm tài liệu ủy quyền", TU_PHAP_AUTH);
  const buttons = [button("Chọn tệp đính kèm", auth)];
  const { hasAttachmentTarget } = loadContext({
    document: { querySelector: () => null, querySelectorAll: (s) => (s === "button" ? buttons : []) },
  });
  assert.equal(hasAttachmentTarget(), false,
    "nhận nhầm là bot bỏ qua bước chủ hồ sơ và đính giấy chứng thực vào ô ủy quyền");
});

test("sidebar: trang không trả lời lệnh đính kèm thì báo lỗi, không báo '0 tệp, 0 lỗi'", () => {
  const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
  const block = sidebar.slice(sidebar.indexOf('action: "attachFilesByPlan",\n        files,\n        attachments: sendAttachments'));
  const report = block.slice(0, 1200);
  assert.match(report, /errors:\s*!res\s*\?/, "res null phải sinh lỗi riêng");
  assert.match(report, /Trang không nhận lệnh đính kèm/);
});
