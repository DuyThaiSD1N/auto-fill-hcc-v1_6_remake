// Thủ tục ĐĂNG KÝ KẾT HÔN CÓ YẾU TỐ NƯỚC NGOÀI: khối "Số bản án/Quyết định ly hôn" đặt tên input
// KHÁC bản kết hôn trong nước (soGiayTo / ngayCapGiayTo-* / coQuanCapGiayTo và BenNu_SoBanAn đều
// không có), nên tầng khớp-theo-tên trượt sạch và trước đây cả 3 ô bị bỏ trống — trợ lý báo
// "1 ô chưa khớp được: TTHN_LyHonBenNu". Tầng khớp-theo-NHÃN phải cứu được cả ba.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

function functionSource(name, nextName) {
  const start = source.indexOf(`function ${name}`);
  let end = source.indexOf(`\nfunction ${nextName}`, start);
  if (end < 0) end = source.indexOf(`\nasync function ${nextName}`, start);
  assert.ok(start >= 0 && end > start, `Không tách được helper ${name}`);
  return source.slice(start, end);
}

const sandbox = {
  norm: (s) => (s || "").trim().toLowerCase().replace(/\s+/g, " "),
};

vm.runInNewContext(`
  ${functionSource("nearbyLabelText", "closestCommonAncestor")}
  ${functionSource("divorceControlsByLabel", "fillSelectArea")}
  globalThis.labelText = nearbyLabelText;
  globalThis.controlsByLabel = divorceControlsByLabel;
`, sandbox);

// DOM giả lập tối thiểu: mỗi ô nhập nằm trong một dòng có nhãn riêng, đúng như biểu mẫu trên cổng.
function makeInput(name, labelText, { tag = "input", type = "text", dateWrapper = null } = {}) {
  const row = { textContent: labelText, parentElement: null };
  const node = {
    tagName: tag.toUpperCase(),
    getAttribute: (attr) => (attr === "name" ? name : attr === "type" ? type : null),
    parentElement: dateWrapper || row,
    closest: (sel) => (sel === "x-date" ? dateWrapper : null),
  };
  if (dateWrapper) dateWrapper.parentElement = row;
  return node;
}

const dateWrapper = { tagName: "X-DATE", textContent: "", parentElement: null };
const soInput = makeInput("tthn_so_x1", "Số bản án/Quyết định ly hôn");
const dayInput = makeInput("dq-day", "", { dateWrapper });
const cqInput = makeInput("tthn_cq_x1", "Cơ quan cấp bản án/Quyết định ly hôn:");
// Ô của phần khác trong biểu mẫu, KHÔNG được nhận nhầm.
const otherInput = makeInput("SoLanKetHon_BenNam", "(19) Kết hôn lần thứ mấy:");
dateWrapper.parentElement = { textContent: "Ngày cấp bản án/Quyết định ly hôn:", parentElement: null };

const container = {
  querySelectorAll: () => [soInput, dayInput, cqInput, otherInput],
};

const found = sandbox.controlsByLabel(container);

assert.equal(found.number, soInput, "Ô số bản án phải khớp theo nhãn 'Số bản án'");
assert.equal(found.agency, cqInput, "Ô cơ quan cấp phải khớp theo nhãn 'Cơ quan cấp bản án'");
assert.equal(found.date, dateWrapper, "Ô ngày phải trả về x-date bọc ngoài, không phải input con");

// Nhãn không nhắc "bản án" thì tuyệt đối không được nhận — nếu không sẽ điền đè sang ô khác.
assert.ok(
  found.number !== otherInput && found.agency !== otherInput && found.date !== otherInput,
  "Ô ngoài khối bản án không được khớp",
);

console.log("divorce decision (foreign marriage): 3 ô khớp theo nhãn khi tên input lạ");
