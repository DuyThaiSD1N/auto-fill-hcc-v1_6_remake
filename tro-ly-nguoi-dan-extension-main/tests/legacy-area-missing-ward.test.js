// "OCR ra thành phố mà không ra phường/xã thì sao?" — legacyAreaRolesFilled là chỗ QUYẾT ĐỊNH có
// tick lại ô phạm vi (làm cổng dựng lại khối, xóa sạch cái vừa điền) hay không. Nó chỉ soi những
// vai CÓ dữ liệu, nên hai kịch bản rẽ hai hướng khác nhau:
//   (a) data KHÔNG có xã  -> điền xong Tỉnh là coi như đạt -> KHÔNG retry, Tỉnh giữ nguyên.
//   (b) data CÓ xã nhưng dropdown không khớp -> chưa đạt -> retry: khối bị dựng lại rồi điền lượt 2.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");
const start = source.indexOf("function legacyAreaWidgetsByRole(container)");
const end = source.indexOf("// Ô tích phạm vi địa chỉ", start);
assert.ok(start >= 0 && end > start, "Không tách được legacyAreaRolesFilled");

const norm = (v) => String(v || "").replace(/\s+/g, " ").trim().toLowerCase();
const sandbox = {
  norm,
  // Bản rút gọn của legacyChoiceMatches: khớp khi một bên chứa trọn bên kia.
  legacyChoiceMatches: (a, b) => {
    const x = norm(a); const y = norm(b);
    return !!x && !!y && (x === y || x.includes(y) || y.includes(x));
  },
  areaRoleOf: (widget) => widget.role,
};
vm.runInNewContext(`${source.slice(start, end)}\nglobalThis.rolesFilled = legacyAreaRolesFilled;`, sandbox);

// Khối có 3 dropdown; "picked" là nhãn đang hiện trên mỗi ô.
const block = (picked) => ({
  querySelectorAll: () => ["quocGia", "tinh", "xa"].map((role) => ({
    role,
    querySelector: () => ({ textContent: picked[role] || "" }),
  })),
});

// --- (a) OCR chỉ ra thành phố, KHÔNG ra phường/xã ---
const chiCoTinh = { quocGia: "Việt Nam", tinh: "Hồ Chí Minh", xa: "", diaChi: "79 Đường số 6" };
assert.equal(
  sandbox.rolesFilled(block({ quocGia: "Việt Nam", tinh: "Thành phố Hồ Chí Minh", xa: "-- Chọn --" }), chiCoTinh),
  true,
  "Không có xã trong dữ liệu thì điền được Tỉnh là ĐẠT — không được tick lại ô phạm vi",
);
// Ngay cả khi ô Phường/Xã còn trống trơn: đó là ô không có gì để điền, không phải lỗi.
assert.equal(
  sandbox.rolesFilled(block({ quocGia: "Việt Nam", tinh: "Thành phố Hồ Chí Minh", xa: "" }), chiCoTinh),
  true,
  "Ô Phường/Xã trống không làm khối bị coi là hỏng khi dữ liệu vốn không có xã",
);

// --- (b) Có xã nhưng dropdown không khớp (ca "Vĩnh Lộc"/"Vinh Lộc") ---
const coXa = { quocGia: "Việt Nam", tinh: "Hồ Chí Minh", xa: "Vĩnh Lộc", diaChi: "ấp 53" };
assert.equal(
  sandbox.rolesFilled(block({ quocGia: "Việt Nam", tinh: "Thành phố Hồ Chí Minh", xa: "-- Chọn --" }), coXa),
  false,
  "Có xã mà chưa chọn được thì phải coi là chưa đạt để còn chạy lượt 2",
);
// Chọn được cả hai thì thôi, không đụng vào nữa.
assert.equal(
  sandbox.rolesFilled(block({ quocGia: "Việt Nam", tinh: "Thành phố Hồ Chí Minh", xa: "Xã Vĩnh Lộc" }), coXa),
  true,
  "Đủ Tỉnh + Xã thì chốt, không tick lại ô phạm vi",
);
// Tỉnh trượt cũng là chưa đạt (ca "TP Hồ Chí Minh" cũ).
assert.equal(
  sandbox.rolesFilled(block({ quocGia: "Việt Nam", tinh: "-- Chọn --", xa: "-- Chọn --" }), coXa),
  false,
  "Tỉnh chưa chọn được thì phải chạy lượt 2",
);

console.log("legacy area missing ward passed");
