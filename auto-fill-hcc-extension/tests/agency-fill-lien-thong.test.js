// Nút "Chọn cơ quan thực hiện" — bước 01 liên thông khai sinh (bản no handfree).
//
// Handfree đã điền hộ khối này từ lâu qua action fill_agency_plan; bản no handfree thì cán bộ
// phải chọn tay 6 mục mỗi hồ sơ. Nút này dùng LẠI engine fillFormAngular có sẵn — không có
// logic điền mới.
//
// Ba ranh giới phải giữ:
//   1. Kế hoạch điền do BE cấp (procedures[].agencyFillPlan). Chốt cứng danh sách ô trong
//      extension là mỗi lần cổng đổi nhãn phải phát hành lại bản mới cho mọi máy quầy.
//   2. Chỉ chạy ở ĐÚNG bước 01. Bước kê khai cũng là Angular, bấm nhầm mà không chặn là điền
//      bậy vào biểu mẫu.
//   3. {province}/{ward} phải được thay TRƯỚC khi gửi, nếu không cán bộ nhận ô Tỉnh mang
//      nguyên chữ "{province}".
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const html = fs.readFileSync(path.join(root, "popup.html"), "utf8");
const angular = fs.readFileSync(path.join(root, "content", "fill-angular.js"), "utf8");

// ── 1. Kế hoạch đến từ BE ───────────────────────────────────────────────────────────────
assert.match(popup, /currentConfig\(\)\?\.agencyFillPlan/);
assert.match(popup, /agencyFillBtn\.hidden = !currentAgencyFillPlan\(\);/);
// Không được chốt cứng theo key thủ tục: thêm cổng khác chỉ nên phải sửa BE.
const btnBlock = popup.slice(popup.indexOf("if (agencyFillBtn) {"));
assert.ok(!/khai-sinh-dang-ky/.test(btnBlock.slice(0, 1200)),
  "gắn nút theo key thủ tục → thêm cổng phải phát hành lại extension");
// Tên ô của cổng cũng không được nằm trong extension.
for (const field of ["IsNuocNgoai", "DkksTruongHop", "IsCapTheCanCuoc"]) {
  assert.ok(!popup.includes(field), `popup.js chốt cứng ô "${field}" — phải lấy từ BE`);
}

// ── 2. Chỉ chạy đúng bước 01 ────────────────────────────────────────────────────────────
const handler = angular.slice(angular.indexOf('msg.action !== "fillAgencyByPlan"'));
assert.match(handler.slice(0, 400), /formcontrolname="IsNuocNgoai"/,
  "thiếu guard → bấm nhầm ở bước kê khai là điền bậy");
assert.match(handler.slice(0, 700), /fillFormAngular\(msg\.fields \|\| \[\]\)/,
  "phải dùng lại engine chung, không viết logic điền riêng");
// KHÔNG tự bấm "Chuyển bước tiếp theo" — cán bộ rà lại cơ quan rồi tự bấm (giống handfree).
assert.ok(!/Chuyển bước tiếp theo|buoc-tiep-theo/i.test(handler.slice(0, 900)));

// ── 3. Thay {province}/{ward} trước khi gửi ─────────────────────────────────────────────
const start = popup.indexOf("function resolveAgencyPlan");
assert.ok(start > 0, "thiếu resolveAgencyPlan");
const fnSrc = popup.slice(start, popup.indexOf("\nif (agencyFillBtn) {", start));
const resolve = (loc, plan) =>
  new Function("currentLocation", "plan", `${fnSrc}\nreturn resolveAgencyPlan(plan);`)(loc, plan);

const PLAN = [
  { name: "IsNuocNgoai", comp: "select", value: "Không có yếu tố nước ngoài" },
  { name: "CqdkksDiaChi", comp: "diachi", value: { tinh: "{province}", xa: "{ward}" } },
  { name: "IsCapTheCanCuoc", comp: "checkbox", value: true },
];
const out = resolve({ province: "Tỉnh Ninh Bình", ward: "Xã Nghĩa Hưng" }, PLAN);
// Chuỗi phải là tên ĐẦY ĐỦ theo danh mục — đúng chữ trên dropdown của cổng.
assert.deepEqual(out[1].value, { tinh: "Tỉnh Ninh Bình", xa: "Xã Nghĩa Hưng" });
assert.equal(out[0].value, "Không có yếu tố nước ngoài", "giá trị không phải placeholder thì giữ nguyên");
assert.equal(out[2].value, true, "boolean không được biến thành chuỗi");
assert.notEqual(PLAN[1].value.tinh, "Tỉnh Ninh Bình", "không được sửa vào plan gốc");

// Thiếu địa bàn: popup phải CHẶN trước khi gửi, không gửi ô Tỉnh rỗng rồi để lại chữ lọc rác.
assert.match(popup, /if \(!locationIsComplete\(\)\) \{/);
assert.match(popup, /Chọn Tỉnh\/Thành và Phường\/Xã ở mục Địa bàn trước đã\./);

// ── Nút hiện đúng chỗ, không khoá theo số tệp ───────────────────────────────────────────
assert.match(html, /id="agencyFillBtn"[^>]*hidden/);
// Bước 01 diễn ra TRƯỚC khi chọn giấy tờ → khoá theo files.length là nút vô dụng.
assert.ok(!/agencyFillBtn\.disabled = !files\.length/.test(popup));
// Phải cập nhật ở CẢ hai nhịp: đổi thủ tục (applyFormUI) và thêm/bớt tệp (refreshAttachStepUI).
assert.equal((popup.match(/agencyFillBtn\.hidden = !currentAgencyFillPlan\(\);/g) || []).length, 2);

// ── 4. So khớp nhãn option phải chuẩn hoá NFC ───────────────────────────────────────────
// Nhãn "Loại khai sinh" của cổng lưu ở dạng tổ hợp KHÁC NFC. So === với chuỗi NFC của backend
// là trượt, mà hai chuỗi hiện ra y hệt nhau — nhìn log không tài nào thấy ra. Bản handfree đã
// chuẩn hoá từ trước; thiếu ở đây thì cùng một kế hoạch chạy được bên kia lại hỏng bên này.
const content = fs.readFileSync(path.join(root, "content.js"), "utf8");
const normSrc = content.slice(content.indexOf("const norm = (s) =>"));
assert.match(normSrc.slice(0, 120), /normalize\("NFC"\)/, "norm() thiếu chuẩn hoá NFC");

// Chạy thật trên chữ LẤY TỪ TRANG (snapshot bước 01), không phải chuỗi gõ tay.
const snapshot = path.join(root, "..", "liên thông b1", "liên thông bước 1.html");
if (fs.existsSync(snapshot)) {
  const norm = new Function(`${normSrc.slice(0, normSrc.indexOf("\n"))}\nreturn norm;`)();
  const html = fs.readFileSync(snapshot, "utf8");
  const option = [...html.matchAll(/>([^<>]{5,80})</g)].map((m) => m[1].trim())
    .find((t) => t.normalize("NFC").includes("Không có yếu tố nước ngoài"));
  assert.ok(option, "không tìm thấy nhãn option trong snapshot");
  assert.equal(norm(option), norm("Không có yếu tố nước ngoài"),
    "nhãn trên trang không khớp giá trị backend — kiểm lại chuẩn hoá NFC");
}

// ── 5. Hai nút khác bước phải tách nhau ─────────────────────────────────────────────────
const css = fs.readFileSync(path.join(root, "popup.css"), "utf8");
assert.match(css, /#agencyFillBtn:not\(\[hidden\]\) \{ margin-bottom: \d+px; \}/,
  "nút bước 01 dính sát nút Quét và nhập dữ liệu → dễ bấm nhầm");

console.log("agency fill liên thông: plan từ BE, khoá đúng bước, thay địa bàn, khớp NFC passed");
