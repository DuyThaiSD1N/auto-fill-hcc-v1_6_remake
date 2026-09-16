const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const css = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");

test("extension khai capability supportsRating (BE mới cắm bước đánh giá; bản cũ không khai → luồng cũ)", () => {
  assert.match(sidebar, /CLIENT_CAPABILITIES[\s\S]*supportsRating:\s*true/);
});

test("renderCard nhận card kind 'rating' và có renderRatingCard", () => {
  assert.match(sidebar, /card\.kind === "rating"[\s\S]*renderRatingCard\(card\)/);
  assert.match(sidebar, /function renderRatingCard\(card\)/);
});

test("card đánh giá gửi đúng action rate / rate_skip", () => {
  assert.match(sidebar, /__action:rate:\$\{JSON\.stringify\(\{ level, reasons: \[\.\.\.reasons\], note: note\.trim\(\) \}\)\}/);
  assert.match(sidebar, /__action:rate_skip/);
});

test("đánh giá là MỘT khối tự đổi: có state 'thanked' hiện cảm ơn trong card, KHÔNG đẻ bong bóng echo", () => {
  // finish() không addUserText (không bong bóng "Đánh giá: ..."); morph sang thanked trong card.
  assert.match(sidebar, /const finish = \(action, label\) => \{[\s\S]*thanked = true;[\s\S]*draw\(\);[\s\S]*ask\(action/);
  assert.doesNotMatch(sidebar, /const finish = \(action, label\) => \{[\s\S]*addUserText\(label\)/);
  assert.match(sidebar, /if \(thanked\) \{[\s\S]*rating-thanks[\s\S]*card\.thanks/);
});

test("chọn mức xong thì thang mức BIẾN MẤT, chỉ còn tóm tắt (Chọn lại) + bước lý do", () => {
  // Bước 1 chỉ render khi chưa chọn (level == null); bước 2 render 'rating-picked' + nút Chọn lại.
  assert.match(sidebar, /if \(level == null\)[\s\S]*rating-scale/);
  assert.match(sidebar, /rating-picked[\s\S]*data-change="1"/);
  // Xử lý Chọn lại → về bước 1.
  assert.match(sidebar, /data-change[\s\S]*level = null/);
});

test("chọn mức (bước 1) LƯU LOG ngay qua rate_level (chạy nền), dù bỏ dở bước 2", () => {
  assert.match(sidebar, /data-lv[\s\S]*api\.ask\(`__action:rate_level:\$\{JSON\.stringify\(\{ level \}\)\}`/);
  // Bỏ qua ở bước 2 (đã chọn mức) → chốt GIỮ mức, không phải rate_skip.
  assert.match(sidebar, /data-skip[\s\S]*if \(level == null\) finish\("__action:rate_skip"[\s\S]*else submitRating\(\)/);
});

test("mỗi lần card đổi nội dung thì cuộn xuống đáy khung chat", () => {
  assert.match(sidebar, /const scrollDown = \(\) => requestAnimationFrame\([\s\S]*\$messages\.scrollTop = \$messages\.scrollHeight/);
  assert.match(sidebar, /scrollDown\(\);/);
});

test("ghi âm ý kiến: ASR đổ vào ô ý kiến (ratingNoteSink) thay vì gửi chat", () => {
  assert.match(sidebar, /let ratingNoteSink = null/);
  // Guard đặt TRƯỚC nhánh xử lý câu hội thoại (partial → $input, final → ask).
  assert.match(sidebar, /if \(ratingNoteSink\) \{[\s\S]*ratingNoteSink\(msg\.text[\s\S]*return;\s*\}/);
});

test("CSS có style card đánh giá (thang mức + chip + nút gửi)", () => {
  assert.match(css, /\.rating-card\b/);
  assert.match(css, /\.rating-opt\b/);
  assert.match(css, /\.rating-chip\b/);
  assert.match(css, /\.rating-submit\b/);
});

test("chip lý do ĐÃ TICK phải nổi hơn chưa tick, không mờ đi", () => {
  // Bản cũ chỉ đổi viền + nền xanh nhạt, giữ nguyên màu chữ và độ đậm → nền tint kéo tương
  // phản TỤT (10,4:1 so với 11,4:1), cán bộ nhìn tưởng chọn xong thì chữ bị mờ.
  const sel = /\.rating-chip\.sel \{([^}]*)\}/.exec(css);
  assert.ok(sel, ".rating-chip.sel phải được khai báo");
  assert.match(sel[1], /color:\s*#08301f/, "chữ phải tối hơn lúc chưa tick");
  assert.match(sel[1], /font-weight:\s*800/, "và đậm hơn một nấc (chưa tick là 700)");
  assert.match(css, /\.rating-chip\.sel:hover \{[^}]*background/, "hover khi đã tick vẫn phải giữ nền riêng");
});
