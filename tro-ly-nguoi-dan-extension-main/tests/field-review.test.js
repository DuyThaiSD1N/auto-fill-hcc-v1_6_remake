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
  // Lệnh của BE (required, skip, apply, focus, noAsk…) chuyển nguyên sang content script.
  assert.match(sidebar, /a\.type === "field_review_next"[\s\S]*?sendToContent\(\{ \.\.\.a, action: "fieldReviewNext" \}\);[\s\S]*?ask\(`__event:field_review_focus:/);
  assert.match(sidebar, /a\.type === "field_review_stop"[\s\S]*?action: "fieldReviewStop"/);
});

test("sidebar: câu hỏi ô đọc xong tự mở mic một lượt", () => {
  assert.match(sidebar, /const listenAfter = !opts\?\.noTts && \(d\.actions \|\| \[\]\)\.some\(\(a\) => a\.type === "listen_after_tts"\)/);
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
  assert.match(review, /let slot = \(msg\.focus && list\.find\(\(s\) => s\.key === msg\.focus\)\)\s*\|\| \(msg\.requiredFirst && list\.find/);
  assert.match(sidebar, /sendToContent\(\{ \.\.\.a, action: "fieldReviewNext" \}\)/);
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
  assert.match(guided, /text\.includes\("xem to khai"\)/);
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
  assert.match(guided, /\.find\(\(el\) => shown\(el\) && isPreviewTitle\(fold\(el\.textContent\)\)\);/);
});

test("bản xem trước mở (công dân tự bấm Xem trước, hoặc mở muộn) → trang báo sidebar, sidebar báo BE đã mở", () => {
  const guided = strip(fs.readFileSync(path.join(root, "content", "guided-steps.js"), "utf8"));
  // Cổng dựng PDF có lúc quá 10s: chưa thấy toast chặn thì chờ ~20s.
  assert.match(guided, /const limit = watched\.message \? 12 : 80;/);
  // Chỉ báo lúc chuyển đóng → mở.
  assert.match(guided, /if \(open && !previewWasOpen\) \{[\s\S]*?action: "declarationPreviewSeen"/);
  // Sidebar: đúng tab, trợ lý đang tự bấm thì không báo trùng, chỉ ở bước tờ khai.
  const nghe = sidebar.slice(sidebar.indexOf('message?.action !== "declarationPreviewSeen"'));
  assert.match(nghe, /Number\(sender\?\.tab\?\.id\) !== Number\(TAB_ID\)/);
  assert.match(nghe, /if \(previewByAssistant\) \{ previewSeenWhileAssistant = true; return; \}/);
  assert.match(nghe, /\["reviewing", "attaching"\]\.includes\(lastState\)/);
  assert.match(sidebar, /__action:field_review_preview_report:\$\{JSON\.stringify\(\{ opened: true, source: "page" \}\)\}/);
  assert.match(sidebar, /if \(!res\?\.opened && previewSeenWhileAssistant\) reportPreviewSeen\(\);/);
});

test("ô ghi chữ cạnh lựa chọn Khác: tích xong điền luôn apply.extra bằng engine, khai cờ cho BE", () => {
  assert.match(review, /async function applyExtra\(fields\) \{[\s\S]*?await H\.fillForm\(fields\);[\s\S]*?notFound/);
  assert.match(review, /await applyValue\(target, slots\(\), String\(msg\.apply\.value \?\? ""\)\)\) && \(await applyExtra\(msg\.apply\.extra\)\)/);
  assert.match(sidebar, /supportsFieldReviewOtherText: true/);
});

test("engine fill-legacy tìm ô ghi chữ của Khác theo cấu trúc (quan hệ xác nhận thông tin hộ tịch)", () => {
  const legacy = strip(fs.readFileSync(path.join(root, "content", "fill-legacy.js"), "utf8"));
  assert.match(legacy, /nycquanhekhac: "nycQuanHe"/);
  assert.match(legacy, /function findLegacyRawInput\(field\) \{\s*return findNamedElement\("input", fieldCandidates\(field\)\)\.el \|\| findLegacyOtherTextInput\(field\);/);
  assert.match(legacy, /let el = findLegacyRawInput\(f\);\s*if \(!el && hasLegacyOtherTextDriver\(f\)\)/);
});

test("khối lồng (mẹ / cha nuôi): tách từng ô con, dropdown không tên điền theo khối + nhãn, ô năm sinh hỏi như ô ngày", () => {
  assert.match(review, /function nestedSlots\(area, areaName\)/);
  assert.match(review, /nestedAreas\.has\(name\) \? nestedSlots\(c, name\) : areaSlots\(c, name\)/);
  assert.match(review, /fill: \{ containers: \[areaName\], label: cleanLabel\(label\) \}/);
  assert.match(review, /\{ name: slot\.name, comp: slot\.comp, value, \.\.\.\(slot\.fill \|\| \{\}\) \}/);
  assert.match(review, /if \(Array\.isArray\(msg\?\.nested\)\) nestedAreas = new Set\(msg\.nested\);/);
  assert.match(review, /textDateNames\.has\(slot\.name\)\) \{ slot\.kind = "date"; slot\.partialDate = true; \}/);
  assert.match(sidebar, /supportsFieldReviewNested: true/);
});

// Cổng bọc ô Số định danh trong <span> riêng, nhãn nằm ngoài span: nhãn đọc rỗng thì slots() ghép nhãn ô liền trước
// ("Quốc tịch") → trợ lý hỏi "Ô Quốc tịch" ở ô Số định danh và LLM hiểu câu trả lời thành tên nước.
test("ô bọc trong <span> riêng: đọc nhãn trước thẻ bọc, không mượn nhãn ô trước", () => {
  const pick = (re) => { const m = review.match(re); assert.ok(m, String(re)); return m[0]; };
  const src = pick(/function labelBefore\(node\) \{[\s\S]*?\n  \}\n/)
    + pick(/const INLINE_WRAPPER = [\s\S]*?function slotLabel\(node\) \{[\s\S]*?\n  \}\n/);
  const Node = { ELEMENT_NODE: 1 };
  const text = (t) => ({ nodeType: 3, textContent: t });
  const el = (tagName, attrs, children = []) => {
    const node = { nodeType: 1, tagName, attrs, children, classList: { contains: () => false } };
    const all = () => children.filter((c) => c.nodeType === 1).flatMap((c) => [c, ...c.all()]);
    Object.assign(node, {
      all,
      get textContent() { return children.map((c) => c.textContent).join(""); },
      querySelector: (sel) => (sel === "[name]" ? all().find((c) => c.attrs.name) || null : null),
      querySelectorAll: () => all().filter((c) => /^X-/.test(c.tagName) && c.attrs.name),
    });
    children.forEach((c, i) => { c.parentElement = node; c.previousSibling = children[i - 1] || null; });
    return node;
  };
  const quocTich = el("X-SELECT", { name: "QuocTichBenNu" });
  const soDinhDanh = el("X-INPUT", { name: "SoDinhDanh_BenNu" });
  const hoTen = el("X-INPUT", { name: "HoTenBenNu" });
  el("P", {}, [text("(5) Quốc tịch "), quocTich, text(" (6) Số định danh cá nhân: "), el("SPAN", {}, [soDinhDanh])]);
  el("P", {}, [text("(2) Họ, chữ đệm, tên: "), el("SPAN", {}, [hoTen, el("X-INPUT", { name: "Khac" })])]);
  const slotLabel = new Function("Node", "SLOT_SELECTOR", `${src}; return slotLabel;`)(Node, "x-*");
  assert.equal(slotLabel(soDinhDanh), "(6) Số định danh cá nhân:");
  assert.equal(slotLabel(quocTich), "(5) Quốc tịch");
  assert.equal(slotLabel(hoTen), "", "thẻ bọc chứa nhiều ô: không leo ra, tránh lấy nhầm chữ của ô khác");
  assert.match(review, /label: slotLabel\(c\)/);
});

// Vòng bổ sung bản 2 (BE): agent điều phối cần cả danh sách ô để hiểu "sửa tên bên nam", "sửa nhiều ô" — extension chỉ
// gửi khi BE xin (msg.catalog), BE cũ không xin thì phản hồi giữ nguyên.
test("BE xin catalog thì trả kèm danh sách ô (cả khi hết ô trống), không xin thì không", () => {
  const pick = (re) => { const m = review.match(re); assert.ok(m, String(re)); return m[0]; };
  const src = pick(/function catalogOf\(msg, list\) \{[\s\S]*?\n  \}\n/);
  const slots = [
    { key: "HoTenBenNam", kind: "text", box: "a", value: () => "NGUYEN VAN A" },
    { key: "DanTocBenNam", kind: "radio", options: ["Kinh", "Khác"], box: "b", value: () => "" },
  ];
  const publicField = (s, options, section) => ({ key: s.key, options, section, value: s.value() });
  const catalogOf = new Function("headings", "sectionOf", "publicField", `${src}; return catalogOf;`)(
    () => [], () => "II. Bên nam", publicField);
  assert.deepEqual(catalogOf({}, slots), {});
  const out = catalogOf({ catalog: true }, slots).catalog;
  assert.equal(out.length, 2);
  assert.deepEqual(out[1].options, ["Kinh", "Khác"]);
  assert.equal(out[0].value, "NGUYEN VAN A");
  assert.match(review, /field: publicField\(slot, options, sectionOf\(slot\.box, headings\(\)\), province\), stats,\s*\.\.\.catalogOf\(msg, list\)/);
  assert.match(review, /field: null, stats, \.\.\.catalogOf\(msg, list\)/);
});

test("cả 6 bộ đọc ô (eForm, SurveyJS, Angular, BXD, Bắc Ninh, liz) trả catalog khi BE xin", () => {
  const files = ["content/field-review.js", "content/field-review-surveyjs.js", "content/field-review-angular.js",
    "content/bxd/field-review-formio.js", "content/bacninh/field-review.js", "content/liz/field-review.js"];
  for (const file of files) {
    const src = fs.readFileSync(path.join(__dirname, "..", file), "utf8");
    assert.match(src, /function catalogOf\(msg, list\) \{\s*if \(!msg\?\.catalog\) return \{\};/, file);
    assert.match(src, /field: null, stats, \.\.\.catalogOf\(msg, list\) \}/, `${file}: hết ô trống vẫn gửi catalog`);
    assert.equal((src.match(/\.\.\.catalogOf\(msg, list\)/g) || []).length, 2, file);
  }
});

// Tích "Trong nước" xong cổng dựng khối địa chỉ, có lúc để trống / dựng hỏng ô Quốc gia: chọn luôn Việt Nam, danh sách
// rỗng thì tick lại ô phạm vi rồi chọn lại; ô Tỉnh / Quốc gia rỗng lúc hỏi cũng dựng lại khối.
test("điền \"Trong nước\" thì chọn Quốc gia Việt Nam, danh sách rỗng thì tick lại ô phạm vi", () => {
  assert.match(review, /if \(ok\) await afterScope\(target, msg\.apply\.value\);/);
  assert.match(review, /function afterScope\(slot, value\) \{\s*if \(slot\.kind !== "radio" \|\| !fold\(String\(value \|\| ""\)\)\.includes\("trong nuoc"\)\) return;/);
  assert.match(review, /const HOME_COUNTRY = "Việt Nam";/);
  const home = review.match(/async function homeCountry\(group\) \{[\s\S]*?\n  \}\n/)[0];
  assert.match(home, /fillArea\(name, \{ \.\.\.areaData\(name\), quocGia: HOME_COUNTRY \}\)/);
  assert.match(home, /toggleScope\(area\)/);
  assert.match(review, /slot\.role === "tinh" \|\| slot\.role === "quocGia"\) && slot\.area\) \{\s*options = await rebuiltOptions\(slot\);/);
});

// Dropdown Xã rỗng hiện "Không tìm thấy kết quả": phải coi là rỗng để chạy bước chọn tỉnh khác rồi chọn lại.
test("dòng \"Không tìm thấy kết quả\" không phải lựa chọn", () => {
  assert.match(review, /t\.startsWith\("khong tim thay"\)/);
  const src = review.match(/const fold = [\s\S]*?const isPlaceholder = \(text\) => \{[\s\S]*?\n  \};/)[0];
  const isPlaceholder = new Function(`${src}; return isPlaceholder;`)();
  assert.equal(isPlaceholder("Không tìm thấy kết quả"), true);
  assert.equal(isPlaceholder("Xã Tam Hợp"), false);
});

// Mẫu eForm mới: tiêu đề phần là <span class="sec-title">Thông tin bên nữ</span> (huy hiệu "I" tách riêng) — không nhận
// thì mọi ô mất tên phần, BE hiện "Tờ khai".
test("nhận tiêu đề phần cả mẫu cũ (<b>I. …</b>) lẫn mẫu mới (.sec-title)", () => {
  assert.match(review, /document\.querySelectorAll\("strong, b, \.sec-title"\)/);
  assert.match(review, /el\.classList\.contains\("sec-title"\) \|\| \/\^\[IVXLC\]\+/);
});
