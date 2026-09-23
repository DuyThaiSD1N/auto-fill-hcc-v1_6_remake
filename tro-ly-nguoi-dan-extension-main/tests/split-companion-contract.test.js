// Khung "hồ sơ phụ" ở TAB TÁCH của chứng thực nhiều hồ sơ.
//
// Tab tách do background mở bằng tabs.create nên không có dấu phiên (tlnd_journey) → trước đây
// chỉ còn bong bóng, bấm vào ra màn bắt đầu như chưa làm gì. Khung phụ lấp chỗ đó, nhưng phải
// CHỈ ĐỌC: một phiên chỉ được một khung lái.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8");
const background = read("background.js");
const content = read("content.js");
const companion = read("companion.js");
const companionHtml = read("companion.html");
const manifest = JSON.parse(read("manifest.json"));

// Bình luận giải thích trong mã nguồn cũng chứa đúng mấy chữ đang tìm ("không gọi /chat"...),
// nên phải bóc bình luận trước khi khẳng định "không có đường gọi nào".
const stripComments = (src) => src
  .replace(/\/\*[\s\S]*?\*\//g, "")
  .split("\n").map((line) => line.replace(/\/\/.*$/, "")).join("\n");
const companionCode = stripComments(companion);

test("thẻ hồ sơ phụ đi KEY RIÊNG, không đụng bản đồ đếm mốc Nộp", () => {
  // tlnd_split_tab_origin là đường chuyển tiếp mốc "Nộp hồ sơ" của tab tách — vừa vá sau sự cố
  // 4 hồ sơ chỉ đếm 1. Đổi hình dạng giá trị của nó (số → object) là làm hỏng đúng chỗ đó.
  assert.match(background, /const SPLIT_TAB_INFO_KEY = "tlnd_split_tab_info"/);
  assert.match(background, /map\[splitTabId\] = originTabId;/,
    "bản đồ đếm mốc phải vẫn lưu số tab trần");
  // Ghi thẻ cùng lúc mở tab, trước khi điều hướng — content script của tab tách đọc ngay lúc boot.
  assert.match(background, /rememberSplitTabOrigin\(tab\.id[\s\S]{0,200}?rememberSplitTabInfo\(tab\.id[\s\S]{0,700}?chrome\.tabs\.update\(tab\.id/);
  // Đóng tab thì dọn CẢ HAI bản đồ.
  assert.match(background, /forgetSplitTabOrigin\(tabId\);\s*void forgetSplitTabInfo\(tabId\);/);
});

test("thẻ cũ quá hạn thì bỏ, không dựng nhầm khung cho tab công dân tự mở", () => {
  // Chrome dùng lại số tab. Tab đóng lúc service worker ngủ thì không ai dọn được mục của nó.
  assert.match(background, /SPLIT_TAB_INFO_TTL_MS/);
  assert.match(content, /Date\.now\(\) - \(the\.ts \|\| 0\) > 12 \* 60 \* 60 \* 1000/);
});

test("content.js dựng khung hồ sơ phụ cho tab tách, trước mọi nhánh khác", () => {
  // Phải nằm TRƯỚC nhánh hộ kinh doanh/trang chủ DVC/showInitial, nếu không tab tách rơi xuống
  // showInitial() và lại chỉ còn bong bóng như cũ.
  assert.match(content, /_theHoSoPhu = await docTheHoSoPhu\(\);\s*if \(_theHoSoPhu\) \{[\s\S]{0,500}?\}[\s\S]{0,200}?if \(IS_BUSINESS_HOST\)/);
  // Nộp hồ sơ xong cổng nạp lại trang → không được bật lại khung đã bị thu gọn.
  assert.match(content, /daThuGon\) showLauncher\(\); else ensurePanelOpen\(\)/);
  assert.match(content, /const trangKhung = _theHoSoPhu \? "companion\.html" : "sidebar\.html"/);
  assert.match(content, /getURL\(`\$\{trangKhung\}\?\$\{sidebarQuery\.toString\(\)\}`\)/);
});

test("khung hồ sơ phụ KHÔNG có đường lái phiên", () => {
  // Đây là điều khoản quan trọng nhất của cả tính năng: hai khung cùng lái một phiên thì mốc
  // "Nộp" đếm đôi, trạng thái trang của sai hồ sơ đi về backend, và mỗi khung giữ một nút
  // chuyển bước riêng.
  for (const cam of [
    /\bapi\.ask\(/,            // không gọi /chat
    /page_status/,             // không báo trạng thái trang
    /submit_clicked/,          // không chấm mốc Nộp — đường chuyển tiếp của background lo
    /submitClicked/,
    /runActions/,              // không thi hành lệnh của backend
    /saveJourney|mutateJourney|keep_open/, // không ghi dấu phiên cho tab mình
    /last_reply/,              // không dựng lại chips/cards còn bấm được
  ]) {
    assert.doesNotMatch(companionCode, cam, `khung phụ không được có ${cam}`);
  }
  // Thứ DUY NHẤT nó gọi lên backend là một lượt đọc.
  assert.match(companionCode, /api\.getConversation\(convId\)/);
  const goiApi = companionCode.match(/\bapi\.\w+\(/g) || [];
  assert.deepEqual([...new Set(goiApi)], ["api.getConversation("],
    "khung phụ chỉ được đọc hội thoại, không gọi gì khác");
});

test("mã phiên đọc nhờ từ tab gốc, không chép sang tab mình", () => {
  assert.match(companionCode, /st\?\.\[JOURNEY_KEY\]\?\.\[theHoSo\.originTabId\]\?\.conversation_id/);
  assert.doesNotMatch(companionCode, /storage\.local\.set/,
    "khung phụ chỉ đọc storage, ghi vào là bắt đầu có trạng thái riêng");
});

test("khung phụ dùng chung giao diện và được phép nạp", () => {
  assert.match(companionHtml, /href="sidebar\.css"/);
  const war = manifest.web_accessible_resources[0].resources;
  assert.ok(war.includes("companion.html") && war.includes("companion.js"),
    "thiếu trong web_accessible_resources thì iframe không nạp được");
});

test("tab phụ cũng bấm được nút chuyển bước / gửi hồ sơ của CHÍNH TRANG MÌNH", () => {
  // Nút cuối trang nằm dưới bảng thành phần hồ sơ dài — đúng cái khó mà luồng dẫn từng bước
  // sinh ra để gỡ; hồ sơ tách cũng cần. Lệnh đi thẳng tới content script của tab mình, không
  // qua backend nên không đụng hội thoại.
  assert.match(companionCode, /chrome\.tabs\.sendMessage\(id, payload/);
  assert.match(companionCode, /laGui \? "guidedSubmit" : "guidedClickNext"/);
  // Chọn nút theo thanh bước THẬT của trang, và không đọc được thì không dựng nút nào:
  // bấm nhầm "Gửi hồ sơ" lúc đang ở bước đính kèm là nộp hồ sơ công dân chưa kịp rà.
  assert.match(companionCode, /const laGui = step >= BUOC_NHAN_KET_QUA/);
  assert.match(companionCode, /function themNutBuoc\(step\) \{[\s\S]{0,300}?if \(!step\) return;/);
  // Bấm được ≠ trang chịu chuyển — phải đối chiếu lại thanh bước mới dám báo đã sang bước.
  assert.match(companionCode, /buocSau > step/);
  // Lời cổng đọc nguyên văn (toast tự tắt sau vài giây).
  assert.match(companionCode, /Trang báo: \*\$\{res\.message\}\*/);
});

test("nút quay về hồ sơ chính đi qua background", () => {
  // Khung chạy trong iframe của trang cổng; chrome.tabs không dùng được ở đó.
  assert.match(companionCode, /action: "focusDossierTab", tabId: theHoSo\.originTabId/);
  assert.match(background, /msg\?\.action !== "focusDossierTab"/);
  assert.match(background, /chrome\.tabs\.update\(tabId, \{ active: true \}\)/);
});

if (require.main === module) test.run?.();
