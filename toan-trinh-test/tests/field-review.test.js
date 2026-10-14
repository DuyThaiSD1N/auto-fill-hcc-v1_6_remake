// Bổ sung ô còn trống trên tờ khai eForm sau khi điền: tô TỪNG ô 3 màu (xanh / cam / đỏ), dẫn công dân
// qua từng ô trống từ trên xuống, điền đúng một ô bằng engine fill-legacy. Điều phối ở BE (field_review).
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const review = strip(fs.readFileSync(path.join(root, "content", "field-review.js"), "utf8"));
const sidebar = strip(fs.readFileSync(path.join(root, "sidebar.js"), "utf8"));
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

test("nạp trong iframe tờ khai, SAU engine fill-legacy (dùng H.fillForm)", () => {
  const block = manifest.content_scripts.find((c) => c.matches.some((m) => m.includes("tokhaidientu")));
  assert.ok(block && block.all_frames);
  const at = block.js.indexOf("content/field-review.js");
  assert.ok(at > block.js.indexOf("content/fill-legacy.js") && at > block.js.indexOf("content/fill-core.js"));
});

test("chỉ frame chứa tờ khai eForm trả lời", () => {
  assert.match(review, /H\.detectFormKind\?\.\(\) !== "legacy"/);
  assert.match(review, /action\.startsWith\("fieldReview"\)/);
});

test("tô từng ô: có giá trị xanh, trống bắt buộc đỏ, trống không bắt buộc cam", () => {
  assert.match(review, /if \(slot\.value\(\)\) \{ slot\.box\.classList\.add\("autofill-filled"\)/);
  assert.match(review, /else if \(slot\.required\) \{ slot\.box\.classList\.add\("autofill-not-filled"\)/);
  assert.match(review, /else \{ slot\.box\.classList\.add\("tlnd-fr-optional"\)/);
  // Bắt buộc = tên BE khai HOẶC chấm đỏ của cổng ngay cạnh ô.
  assert.match(review, /slot\.required = need\.has\(slot\.name\) \|\| slot\.marker;/);
  assert.match(review, /classList\?\.contains\("validate-hiden"\)/);
});

test("khối địa chỉ tô theo từng ô con, không tô cả khối x-select-area", () => {
  assert.match(review, /key: `\$\{name\}#\$\{role\}`[\s\S]*box: header \|\| widget/);
  assert.match(review, /key: `\$\{name\}#diaChi`/);
  // Gỡ mọi viền cũ (kể cả viền cả khối của lượt điền) trước khi tô lại.
  assert.match(review, /function clearMarks\(\)[\s\S]*classList\.remove\(\.\.\.MARKS\)/);
});

test("điền một ô bằng engine cũ; đổi Tỉnh thì bỏ Xã cũ", () => {
  assert.match(review, /await H\.fillForm\(\[field\]\);/);
  assert.match(review, /if \(slot\.role === "tinh"\) delete data\.xa;/);
  // Điền hỏng thì không hỏi lại ngay ô đó.
  assert.match(review, /if \(!ok\) skip\.add\(msg\.apply\.key\);/);
});

test("ô trống kế tiếp: từ trên xuống, bỏ ô đã bỏ qua, đưa con trỏ tới rồi mới báo", () => {
  assert.match(review, /\|\| list\.find\(\(s\) => !s\.value\(\) && !skip\.has\(s\.key\)\);/);
  assert.match(review, /let options = await readOptions\(slot\);[\s\S]*?await focusSlot\(slot\);\s*return \{/);
});

test("sidebar: khai cờ, tô màu sau khi điền và gửi số ô kèm báo cáo điền", () => {
  assert.match(sidebar, /supportsFieldReview: true,/);
  assert.match(sidebar, /if \(a\.fieldReview\) \{[\s\S]*?action: "fieldReviewMark"[\s\S]*?report\.review = marked\.stats;/);
});

test("sidebar: tìm ô kế tiếp rồi báo BE, gỡ con trỏ khi dừng", () => {
  assert.match(sidebar, /a\.type === "field_review_next"[\s\S]*?action: "fieldReviewNext", required: a\.required \|\| \[\], skip: a\.skip \|\| \[\], apply: a\.apply \|\| null,[\s\S]*?ask\(`__event:field_review_focus:/);
  assert.match(sidebar, /a\.type === "field_review_stop"[\s\S]*?action: "fieldReviewStop"/);
});

test("sidebar: câu hỏi ô đọc xong tự mở mic một lượt", () => {
  assert.match(sidebar, /const listenAfter = !opts\?\.noTts && \(d\.actions \|\| \[\]\)\.some\(\(a\) => a\.type === "listen_after_tts"\);/);
  assert.match(sidebar, /if \(\(handsfree \|\| listenAfter\) && !completionReturnTimer && replyTtsInFlight === 0\) listenWhenQuiet\(\);/);
  assert.match(sidebar, /\} else if \(handsfree \|\| listenAfter\) \{\s*listenWhenQuiet\(\);/);
});

test("ô năm sinh (x-date-text): chỉ có năm là đã điền; danh sách lựa chọn không cắt ở 200", () => {
  assert.match(review, /const yearOnly = tag === "x-date-text";/);
  assert.match(review, /return yearOnly \? read\(parts\[2\]\) : "";/);
  assert.match(review, /yearOnly: !!slot\.yearOnly/);
  assert.match(review, /\.slice\(0, 400\)/);
});

test("khối x-select-area không có dropdown (vd Số lượng bản sao) là ô chữ riêng, không phải ô Địa chỉ", () => {
  assert.match(review, /if \(!widgets\.length\) \{[\s\S]*?key: name, name, comp: "x-select-area", role: "", kind: "text", plain: true,/);
  assert.match(review, /value: slot\.plain \? value : areaValue\(slot, list, value\)/);
});

test("sửa ô vừa điền: về đúng ô đó dù đã có giá trị", () => {
  assert.match(review, /let slot = \(msg\.focus && list\.find\(\(s\) => s\.key === msg\.focus\)\)\s*\|\| list\.find/);
  assert.match(sidebar, /focus: a\.focus \|\| "",/);
});

test("bong bóng kết quả ô trước hiện riêng, phía trên câu hỏi", () => {
  assert.match(sidebar, /filter\(\(a\) => a\.type === "lead_message" && a\.md\)\.forEach\(\(a\) => addBotMd\(String\(a\.md\)\)\);\s*\}\s*const \$botBubble =/);
});

test("bong bóng phụ đứng sau câu chính, trước nút (báo điền xong tách nhiều bong bóng)", () => {
  assert.match(sidebar, /const \$botBubble = [^\n]*\n[\s\S]{0,200}?a\.type === "trail_message" && a\.md\)\.forEach\(\(a\) => addBotMd\(String\(a\.md\)\)\);/);
});

test("bước chủ hồ sơ đã đủ: bấm sang Kê khai xong đẩy trạng thái trang lên ngay", () => {
  assert.match(sidebar, /if \(moved && \(phase === "owner" \|\| phase === "field_review_owner"\)\) await verifyPortalState\(\);/);
});

test("ô Xã rỗng mà Tỉnh đã có: chọn tỉnh liền kề rồi chọn lại tỉnh cũ (2 lần), rồi tick lại ô phạm vi", () => {
  assert.match(review, /if \(!options\.length && slot\.role === "xa" && areaData\(slot\.name\)\.tinh\) \{\s*options = await wardOptions\(slot\.name\);/);
  // Chọn lại ĐÚNG tỉnh cũ không làm cổng nạp lại → phải đổi sang tỉnh khác trước.
  assert.match(review, /await fillArea\(name, \{ \.\.\.keep, tinh: other \}\);[\s\S]*?await fillArea\(name, keep\);/);
  assert.match(review, /attempt < 3[\s\S]*?if \(attempt < 2\) \{[\s\S]*?\} else if \(!\(await toggleScope\(tinh\.area\)\)\) \{/);
  // Không chữa được vẫn trả khối về đúng tỉnh đang có.
  assert.match(review, /if \(fold\(find\("tinh"\)\?\.value\(\)\) !== fold\(keep\.tinh\)\) await fillArea\(name, keep\);/);
  // Khối Xã bị thay sau khi chọn lại → tô lại, lấy lại ô; vẫn rỗng thì báo BE.
  assert.match(review, /\(\{ list, stats \} = markAll\(msg\.required\)\);\s*slot = list\.find/);
  assert.match(review, /\.\.\.\(province \? \{ optionsFailed: true, province \} : \{\}\)/);
});

test("nút của vòng bổ sung có màu theo nghĩa (tone do BE gắn), tên lạ bỏ qua", () => {
  assert.match(sidebar, /const CHIP_TONES = new Set\(\["skip", "back", "stop", "reload"\]\);/);
  assert.match(sidebar, /\+ \(CHIP_TONES\.has\(c\.tone\) \? ` tone-\$\{c\.tone\}` : ""\);/);
  const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");
  for (const tone of ["skip", "back", "stop", "reload"]) assert.match(css, new RegExp(`\\.chip\\.tone-${tone} \\{`));
  // Nút bị khoá không trắng bệch khi rê chuột (luật .chip:disabled:hover chung).
  assert.match(css, /\.chip\[class\*=" tone-"\]:disabled:hover \{ background: var\(--chip-bg\); \}/);
});

test("Kê khai: bấm Xem trước (kiểm chữ, id #xem-truoc-to-khai) rồi Xác nhận trong hộp thoại 'Xem tờ khai điện tử'", () => {
  const guided = strip(fs.readFileSync(path.join(root, "content", "guided-steps.js"), "utf8"));
  assert.match(guided, /const PREVIEW_SELECTORS = \["#xem-truoc-to-khai", 'button\[data-e2e="btn-next"\]'\];/);
  assert.match(guided, /fold\(el\.textContent\)\.includes\("xem to khai"\)/);
  assert.match(guided, /fold\(el\.textContent\) === "xac nhan"/);
  // Frame không có trang Kê khai thì im.
  assert.match(guided, /if \(!previewButton && !dialog\) return;/);
  // Sidebar: không mở được → tô lại để đếm ô đỏ; Xác nhận → đối chiếu thanh bước rồi mới báo.
  assert.match(sidebar, /if \(!res\?\.opened\) \{[\s\S]*?action: "fieldReviewMark", required \}/);
  assert.match(sidebar, /__action:field_review_confirm_report:[\s\S]*?if \(moved\) await verifyPortalState\(\);/);
  assert.match(sidebar, /a\.type === "declaration_preview"[\s\S]*?setTimeout\(\(\) => \{ void runDeclarationPreview\(required\); \}, 0\);/);
});

test("bước chủ hồ sơ: chờ cổng đổ xong dữ liệu tài khoản vào ô rồi mới báo BE (không quyết lúc ô còn trống)", () => {
  assert.match(sidebar, /if \(c\.wizardStep === 1 && c\.ownerForm\) c = await settleOwnerForm\(c\);\s*const pageStatus = \{/);
  assert.match(sidebar, /async function settleOwnerForm\(c\) \{[\s\S]*?for \(let i = 0; i < 8 && !ready\(c\.ownerForm\); i\+\+\)[\s\S]*?if \(still >= 2\) break;/);
});

test("bản xem trước là hộp thoại position:fixed → nhận theo khung hiển thị, không theo offsetParent", () => {
  const guided = strip(fs.readFileSync(path.join(root, "content", "guided-steps.js"), "utf8"));
  assert.match(guided, /const shown = \(el\) => !!el && el\.getClientRects\(\)\.length > 0;/);
  assert.match(guided, /\.find\(\(el\) => shown\(el\) && fold\(el\.textContent\)\.includes\("xem to khai"\)\);/);
});
