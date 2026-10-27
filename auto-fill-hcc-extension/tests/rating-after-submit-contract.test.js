// Đánh giá trải nghiệm sau khi bấm nộp (no-handfree).
// Ba thứ dễ vỡ nhất, khoá lại ở đây:
//  1. Mức chọn ở BƯỚC 1 phải gửi NGAY — bước 2 là bước hay bị bỏ dở nhất.
//  2. Cờ "cần hỏi" phải nằm ở storage, không phải RAM — bấm nộp xong trang điều hướng/postback
//     làm panel nạp lại là mất sạch biến trong bộ nhớ.
//  3. Hỏi theo dossierId, KHÔNG theo tab — chứng thực tách nhiều tab dùng chung một khóa.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const background = fs.readFileSync(path.join(root, "background.js"), "utf8");
const html = fs.readFileSync(path.join(root, "popup.html"), "utf8");
const css = fs.readFileSync(path.join(root, "popup.css"), "utf8");
const endpoints = fs.readFileSync(path.join(root, "api", "endpoints.js"), "utf8");

test("chọn mức ở bước 1 là gửi NGAY, không chờ nút Gửi đánh giá", () => {
  const start = popup.indexOf('box.querySelectorAll(".rt-opt")');
  const body = popup.slice(start, popup.indexOf('box.querySelector(".rt-skip")', start));
  assert.match(body, /st\.level = Number\(b\.dataset\.lv\)/);
  assert.match(body, /postRating\(st\.dossierId, \{ level: st\.level \}\)/);
  // Không được đợi: gửi xong mới render là chặn UI sau một vòng mạng.
  assert.match(body, /void postRating/);
});

test("bỏ qua ở bước 2 KHÔNG được xoá mức đã chọn ở bước 1", () => {
  // Gửi skipped=true ở đây sẽ ghi đè phiếu bước 1 thành "bỏ qua" và mất con số đã có.
  const step2 = popup.slice(popup.indexOf('// "Bỏ qua" ở bước 2'));
  const handler = step2.slice(0, step2.indexOf("\n}"));
  assert.match(handler, /\.rt-skip[\s\S]{0,140}?close\(false\)/);
  assert.doesNotMatch(handler, /skipped: true/);
});

test("cờ cần-hỏi nằm ở storage và khoá theo dossierId, không theo tab", () => {
  assert.match(background, /const RATING_PENDING_KEY = "autofill_rating_pending"/);
  assert.match(background, /chrome\.storage\.local\.set\(\{\s*\[RATING_PENDING_KEY\]/);
  // Đã hỏi rồi thì thôi, kể cả khi tab khác của cùng hồ sơ lại bấm nộp.
  assert.match(background, /if \(done\.includes\(dossierId\)\) return false/);
  assert.match(popup, /if \(done\.includes\(dossierId\)\) return;/);
  assert.match(popup, /const RATING_DONE_KEY = "autofill_rating_done"/);
});

test("panel dựng lại sau điều hướng vẫn mở được màn đánh giá", () => {
  // Message runtime bắn lúc panel chưa tồn tại → chỉ storage mới sống sót.
  assert.match(popup, /async function resumePendingRating\(\)/);
  const calls = popup.match(/await resumePendingRating\(\);/g) || [];
  assert.ok(calls.length >= 2, "phải gọi ở CẢ hai đường vào panel (đã đăng nhập sẵn + vừa đăng nhập)");
  assert.match(popup, /action === "dossierSubmitted"[\s\S]{0,400}?resumePendingRating\(\)/);
});

test("cờ quá cũ thì bỏ, không hỏi muộn", () => {
  assert.match(popup, /Date\.now\(\) - Number\(pending\.at\) > 30 \* 60 \* 1000/);
});

test("câu chữ lấy từ BE, không chép cứng vào extension", () => {
  assert.match(popup, /if \(res\.ratingCard && Array\.isArray\(res\.ratingCard\.scale\)\) RATING_CARD = res\.ratingCard/);
  // BE bản cũ không trả ratingCard → tắt lặng lẽ chứ không nổ.
  assert.match(popup, /if \(!dossierId \|\| !RATING_CARD \|\| ratingState\) return/);
  // Dữ liệu (mức + danh sách lý do) tuyệt đối không được nằm trong extension: thêm/bớt lý do
  // phải là việc sửa BE rồi deploy, không phải phát hành lại extension.
  for (const label of ["Rất hài lòng", "Bình thường", "Không phải tự điền", "Máy đọc sai thông tin"]) {
    assert.ok(!popup.includes(label) && !html.includes(label), `"${label}" phải do BE cấp`);
  }
  // Nhãn nút được phép có bản dự phòng, nhưng CHỈ sau dấu || — tức BE luôn thắng.
  // Chỉ soi trong KHỐI đánh giá và bỏ comment: "Bỏ qua" là cụm tiếng Việt thường, chỗ khác
  // trong popup.js dùng nó cho việc khác, và nhắc tên nút trong lời giải thích không phải chép cứng.
  const block = popup.slice(popup.indexOf("let RATING_CARD = null;"), popup.indexOf("async function resumePendingRating"));
  const code = block.replace(/^\s*\/\/.*$/gm, "");
  for (const label of ["Gửi đánh giá", "Bỏ qua"]) {
    const hits = code.split(label).length - 1;
    const fallbacks = (code.match(new RegExp(`\\|\\| "${label}`, "g")) || []).length;
    assert.equal(hits, fallbacks, `"${label}" chỉ được xuất hiện làm bản dự phòng sau ||`);
  }
});

test("lỗi mạng lúc gửi đánh giá không được chặn cán bộ làm việc tiếp", () => {
  const fn = popup.slice(popup.indexOf("async function postRating"));
  assert.match(fn.slice(0, fn.indexOf("\n}")), /catch \(e\)[\s\S]{0,180}?return false/);
});

test("view đánh giá dựng đúng khuôn cs-view đang có", () => {
  assert.match(html, /<div id="view-rating" class="cs-view" hidden>/);
  assert.match(html, /id="ratingInner"/);
  assert.match(popup, /rating: document\.getElementById\("view-rating"\)/);
});

test("5 mức xếp DỌC cho panel hẹp 360px", () => {
  assert.match(css, /\.rt-scale\{[^}]*display:grid/);
  assert.doesNotMatch(css, /\.rt-scale\{[^}]*grid-template-columns:\s*repeat\(5/);
});

test("nút Gửi đánh giá không được nằm ngoài tầm nhìn", () => {
  // .cs-scroll cắt ở max-height:340px; kế thừa nó là màn đánh giá tự đẻ thanh cuộn và đẩy hai
  // nút xuống dưới — cán bộ không thấy nút mà bấm. Khung panel vốn tự cao theo nội dung.
  assert.match(css, /\.rt-scroll\{[^}]*max-height:none/);
  assert.match(css, /\.rt-scroll\{[^}]*overflow:visible/);
  // Lưới chắn cho cửa sổ quá thấp (iframe bị content.js kẹp ở innerHeight-120).
  assert.match(css, /\.rt-actions\{[^}]*position:sticky[^}]*bottom:0/s);
});

test("mọi nút của màn đánh giá phải tự đặt nền khi hover", () => {
  // popup.css có button:hover{background:#0d47a1} dùng chung cho cả panel. Nút nào không tự
  // đặt nền khi hover sẽ bị tô XANH ĐẬM, cộng với chữ màu tối ở trạng thái thường là không
  // đọc được chữ gì — đã gặp thật ở chip lý do.
  // Bỏ comment trước khi khớp: lời giải thích có nhắc "button{width:100%}", dấu } trong đó
  // cắt ngang phép khớp khối.
  const bare = css.replace(/\/\*[\s\S]*?\*\//g, "");
  assert.match(bare, /button:hover\s*\{\s*background:\s*#0d47a1/, "quy tắc nền chung vẫn còn → vẫn phải đè");
  for (const name of ["rt-opt", "rt-skip", "rt-send", "rt-change", "rt-chip", "rt-chip\\.sel"]) {
    const hover = new RegExp(`\\.${name}:hover\\s*\\{([^}]*)\\}`).exec(bare);
    assert.ok(hover, `.${name}:hover phải được khai báo`);
    assert.match(hover[1], /background\s*:/, `.${name}:hover phải tự đặt nền, nếu không sẽ bị xanh đậm`);
  }
  // Hover phải SÁNG chứ không tối: chip dùng nền xanh rất nhạt, chữ đậm lên cho nổi.
  assert.match(bare, /\.rt-chip:hover\{[^}]*background:#eaf3ff[^}]*color:#12356f/);
});

test("chip lý do và nút Chọn lại không được ăn hết bề ngang", () => {
  // button{width:100%} của panel biến chip thành thanh dài, và nút "Chọn lại" bóp nhãn mức
  // ("Rất hài lòng") xuống 3 dòng.
  const bare = css.replace(/\/\*[\s\S]*?\*\//g, "");
  assert.match(bare, /\.rt-chip\{[^}]*width:auto/);
  assert.match(bare, /\.rt-change\{[^}]*width:auto/);
  assert.match(bare, /\.rt-change\{[^}]*flex:0 0 auto/);
});

test("có endpoint gửi phiếu", () => {
  assert.match(endpoints, /dossierRating\(body\)[\s\S]{0,220}?\/api\/v1\/dossiers\/rating/);
});
