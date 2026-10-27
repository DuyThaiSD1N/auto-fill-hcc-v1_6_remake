// Cổng Bộ Xây dựng (dvc.moc.gov.vn): luồng 4 bước do BE điều phối (chat/bxd, cờ supportsBxdFlow) — bấm Tiếp tục,
// bổ sung ô trên tờ khai Form.io, chọn hình thức nhận kết quả, bấm Nộp hồ sơ sau khi soát cam đoan + mã xác nhận;
// bảng 29 dòng tick sẵn → bỏ tích dòng không đính.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8").replace(/^\s*\/\/.*$/gm, "");
const sidebar = read("sidebar.js");
const content = read("content.js");
const portal = read("content/bxd/portal.js");
const review = read("content/bxd/field-review-formio.js");
const attach = read("content/attach-core.js");

test("manifest nạp phần Bộ Xây dựng (thư mục content/bxd) sau engine điền và trước content.js", () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));
  const js = manifest.content_scripts.find((c) => c.js.includes("content/fill-core.js")).js;
  for (const file of ["content/bxd/portal.js", "content/bxd/field-review-formio.js"]) {
    assert.ok(js.indexOf(file) > js.indexOf("content/fill-core.js"), file);
    assert.ok(js.indexOf(file) > js.indexOf("content/field-review.js"), file);
    assert.ok(js.indexOf(file) < js.indexOf("content.js"), file);
  }
});

test("nhận ra bước 3 \"Hình thức nhận kết quả\" (dvc.moc, Bộ Y tế) / \"Thông tin bổ sung\" (Bộ Nội vụ) như bước thứ 3 của wizard MAE", () => {
  assert.match(content, /\["thong tin phi", "hinh thuc nhan ket qua", "thong tin bo sung"\]/);
});

test("sidebar khai cờ, chạy lệnh bxd ngoài lượt ask() và đối chiếu wizardStep sau khi bấm Tiếp tục", () => {
  assert.match(sidebar, /supportsBxdFlow: true,/);
  assert.match(sidebar, /a\.type === "bxd_next"\) \{\s*setTimeout\(\(\) => \{ void runBxdMove\(a\); \}, 0\);/);
  assert.match(sidebar, /a\.type === "bxd_result_scan" \|\| a\.type === "bxd_result_set"\) \{\s*setTimeout/);
  assert.match(sidebar, /a\.type === "bxd_submit"\) \{\s*setTimeout\(\(\) => \{ void runBxdSubmit\(\); \}, 0\);/);
  assert.match(sidebar, /step = Number\(ctx\?\.wizardStep\) \|\| 0;\s*moved = !!expect && step === expect;/);
  assert.match(sidebar, /: lastReplyData\?\.bxd \? Number\(ctx\.wizardStep\) \|\| 0 : 0;/);
});

test("bấm Tiếp tục của bước đang mở; nộp chỉ sau khi tích cam đoan + nhập mã, tin bước 4 thật chứ không tin chữ", () => {
  assert.match(portal, /const openPanel = \(\) => document\.querySelector\('\[id\^="cdk-step-content"\]\[aria-expanded="true"\]'\)/);
  assert.match(portal, /buttonIn\(openPanel\(\), \["tiep tuc"\]\)/);
  assert.match(portal, /if \(agree && !ticked\) missing\.push\("camDoan"\);/);
  assert.match(portal, /if \(captcha && !String\(captcha\.value \|\| ""\)\.trim\(\)\) missing\.push\("captcha"\);/);
  assert.match(portal, /button\[form="captchaForm"\]/);
  assert.match(portal, /message: selectedStep\(\) > step \? "" : message/);
});

test("bộ đọc ô Form.io: chỉ trang cổng iGate Bộ Xây dựng / Bộ Y tế, ô đang hiện, ô trùng tên phân biệt bằng occurrence, điền bằng engine Form.io", () => {
  assert.match(review, /const ourPage = \(\) => HOSTS\.includes\(location\.hostname\)/);
  assert.match(review, /comp\.closest\("\.formio-hidden"\)/);
  assert.match(review, /marker: comp\.classList\.contains\("required"\) \|\| [^\n]*\n\s*\|\| hasError\(comp\)/);
  assert.match(review, /if \(slot\.duplicate\) field\.occurrence = slot\.occurrence;/);
  assert.match(review, /await H\.fillFormStandard\(\[field\]\);/);
  assert.match(review, /formio-component-\(checkbox\|selectboxes\|button/);
});

test("đính kèm ô cố định: bỏ tích hết trước khi đính, dòng đính được thì tích lại", () => {
  assert.match(attach, /const untick = attachments\.some\(\(item\) => item\.untickUnplannedRows\);\s*if \(untick\) await uncheckAllAttpRows\(\);/);
  assert.match(attach, /if \(untick && trigger\.closest\("tr"\)\) await tickAttpRowCheckbox\(trigger\.closest\("tr"\)\);/);
});

test("ô chọn Choices.js đang hiện chữ gợi ý là ô TRỐNG (không đọc option ẩn mang chữ gợi ý)", () => {
  assert.match(review, /const single = comp\.querySelector\("\.choices__list--single"\);/);
  assert.match(review, /single\.querySelector\("\.choices__item:not\(\.choices__placeholder\)"\)/);
  // Mục đã chọn có khi bọc chữ trong thẻ con → lấy cả cây chữ, chỉ bỏ nút xoá.
  assert.match(review, /copy\.querySelectorAll\("button"\)\.forEach\(\(b\) => b\.remove\(\)\);/);
});

test("con trỏ chỉ ô: chờ trang cuộn xong rồi mới chỉ, trang cuộn tiếp thì con trỏ bám theo ô", () => {
  const pointer = read("content/field-review.js");
  assert.match(pointer, /if \(top === lastTop\) break;/);
  assert.match(pointer, /if \(cur\?\.classList\.contains\("follow"\)\) pointAt\(cur, hintTarget\);/);
});

test("con trỏ chỉ ô: chờ trang cuộn xong rồi mới chỉ, trang cuộn tiếp thì con trỏ bám theo ô", () => {
  const pointer = read("content/field-review.js");
  assert.match(pointer, /if \(top === lastTop\) break;/);
  assert.match(pointer, /if \(cur\?\.classList\.contains\("follow"\)\) pointAt\(cur, hintTarget\);/);
});

test("đổi hình thức nhận kết quả: chọn lựa chọn khớp NGUYÊN VĂN (\"Nhận trực tiếp\" ≠ \"Nhận trực tiếp tại nhà qua bưu điện\")", () => {
  for (const file of ["content/bxd/portal.js", "content/lien-thong.js"]) {
    const src = read(file);
    assert.match(src, /async function pickMatOption\(name, value\)/, file);
    assert.match(src, /overlayOptions\(\)\.find\(\(o\) => sameText\(textOf\(o\), value\)\)/, file);
    assert.match(src, /ok = await pickMatOption\(msg\.name, msg\.value\);/, file);
    // Cổng vẽ lại ô chọn sau khi đổi → kiểm trên ô tìm lại theo tên, không trên phần tử cũ.
    assert.match(src, /sameText\(valueOf\(selectOf\(name\)\), value\)/, file);
    assert.doesNotMatch(src, /fillFormAngular\(\[\{ name: msg\.name, comp: "select"/, file);
  }
});

test("cổng Bộ Y tế, Bộ Nội vụ, Bộ GD&ĐT cùng nền iGate: chạy cùng luồng, ô bắt buộc đánh dấu trên nhãn label.field-required", () => {
  for (const src of [portal, review]) {
    assert.match(src, /const HOSTS = \["dvc\.moc\.gov\.vn", "dichvucongbyt\.moh\.gov\.vn", "dichvucongbnv\.moha\.gov\.vn", "dvc\.moet\.gov\.vn"\];/);
  }
  assert.match(portal, /!HOSTS\.includes\(location\.hostname\)/);
  assert.match(review, /comp\.querySelector\(":scope > label\.field-required"\)/);
});

test("ô chọn chưa có lựa chọn (xã chờ tỉnh): không lấy dòng \"No choices to choose from\" làm lựa chọn, chưa hỏi ô đó", () => {
  assert.match(review, /\["choices__placeholder", "has-no-results", "has-no-choices"\]/);
  assert.match(review, /if \(s\.kind !== "select" \|\| s\.options\(\)\.length\) return true;\s*await loadLazyOptions\(s\);\s*return s\.options\(\)\.length > 0;/);
  assert.match(review, /\|\| await firstAskable\(false\);/);
});

test("ô số Form.io: nhãn bỏ chữ ẩn \", numeric only,\", nối đơn vị cạnh ô, báo loại \"number\" để BE chỉ nhận con số", () => {
  assert.match(review, /if \(\/formio-component-number\\b\/\.test\(cls\)\) return "number";/);
  assert.match(review, /copy\?\.querySelectorAll\("\.sr-only"\)\.forEach\(\(el\) => el\.remove\(\)\);/);
  assert.match(review, /comp\.querySelector\("\.input-group-append, \.input-group-prepend"\)/);
  assert.match(review, /number: "dom-input"/);
});

test("ô chọn lazyLoad (Phường/Xã cổng Bộ GD&ĐT): mở dropdown một nhịp cho cổng tải danh sách; bỏ chữ gợi ý của <select> ẩn", () => {
  assert.match(review, /async function loadLazyOptions\(slot\)/);
  assert.match(review, /trigger\.dispatchEvent\(new MouseEvent\("mousedown", \{ bubbles: true \}\)\);/);
  assert.match(review, /\.filter\(\(label\) => label && !hints\.has\(label\)\)/);
  assert.match(review, /\.replace\(\/<\[\^>\]\*>\/g, ""\)/);
});
