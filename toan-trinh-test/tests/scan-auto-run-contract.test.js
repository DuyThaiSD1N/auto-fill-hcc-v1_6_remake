// Scan tại quầy tự chốt sau đợt chọn tệp: BE bật pick_files.auto_run → FE gửi docs_done
// (đúng lệnh nút "Đã đưa đủ", kèm page context để BE chọn đúng bước điền/đính kèm).
// QR và lượt Điều chỉnh giấy tờ giữ chốt tay như bản chợ.
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const sidebar = fs.readFileSync(path.resolve(__dirname, "..", "sidebar.js"), "utf8");
const css = fs.readFileSync(path.resolve(__dirname, "..", "sidebar.css"), "utf8");

test("FE khai capability supportsScanAutoRun — BE chỉ bật auto_run cho client khai cờ này", () => {
  assert.match(sidebar, /CLIENT_CAPABILITIES = Object\.freeze\(\{[\s\S]{0,700}supportsScanAutoRun: true/);
});

test("cờ auto-run chỉ bật từ action pick_files, QR/điều chỉnh reset về rỗng", () => {
  assert.ok(sidebar.includes("let uploadAutoRunSid"));
  assert.ok(sidebar.includes('uploadAutoRunSid = a.auto_run === true ? a.session_id : ""'));
  // show_qr và resume_upload_session (điều chỉnh) phải tắt auto-run.
  assert.match(sidebar, /a\.type === "show_qr"\) \{\s*\n\s*uploadAutoRunSid = ""/);
  assert.match(sidebar, /a\.type === "resume_upload_session"[\s\S]{0,300}uploadAutoRunSid = ""/);
});

test("sau đợt upload đã phân loại: tự gửi ĐÚNG lệnh của nút Đã đưa đủ, gate theo state", () => {
  // Logic auto-chốt nằm trong helper dùng chung uploadFilesToSession (chọn tệp tay + máy quét).
  const start = sidebar.indexOf("async function uploadFilesToSession");
  const block = sidebar.slice(start, start + 3500);
  assert.ok(block.includes("uploadSid === uploadAutoRunSid"));
  assert.ok(block.includes('lastState === "collecting_docs"'),
    "state khác (pipeline đang chạy) không được bắn trùng");
  assert.ok(block.includes('submitDocsComplete("__action:docs_done"'),
    "phải dùng docs_done (chốt phiên + page context) — không bịa lệnh khác");
  assert.ok(block.includes("files_count"), "chỉ tự chốt khi phiên đã có tệp thật");
  assert.ok(block.includes('source !== "scan"'),
    "máy quét (tệp về lẻ tẻ) KHÔNG tự chốt — để công dân bấm Đã đưa đủ");
});

test("máy quét: tệp về tự đổ vào CÙNG upload session, watermark chặn giấy người trước", () => {
  assert.match(sidebar, /window\.ScanAgent\.connect\(/);
  assert.match(sidebar, /uploadFilesToSession\(\[file\], \{ source: "scan" \}\)/);
  assert.match(sidebar, /scanWatermarkMs && mtime && mtime <= scanWatermarkMs/);
  // Ưu tiên máy quét: chỉ bật hộp chọn tệp khi KHÔNG có agent.
  assert.match(sidebar, /if \(!scanAgentConnected\) \$fileInput\?\.click\(\)/);
});

test("thẻ hướng dẫn (ảnh + lời) hiện Ở TRÊN khi chọn Scan; ảnh asset tồn tại", () => {
  assert.match(sidebar, /function renderScanGuideCard\(\)/);
  assert.match(sidebar, /assets\/scan-guide\.jpg/);
  assert.match(sidebar, /từng tờ một/);                    // lời hướng dẫn thao tác
  assert.match(sidebar, /theo hướng dẫn trong hình/);      // thẻ chỉ vào ảnh
  // Dựng NGAY khi chọn "Scan tại quầy" (renderDocOptions) → thẻ ở TRÊN checklist/nút.
  assert.match(sidebar, /if \(key === "scan"\) renderScanGuideCard\(\)/);
  const img = path.resolve(__dirname, "..", "assets", "scan-guide.jpg");
  assert.ok(fs.existsSync(img) && fs.statSync(img).size > 10000, "ảnh hướng dẫn scan phải có trong assets");
});

test("mỗi tệp về: thông báo TEXT trên danh sách + VOICE; nút Đã đưa đủ ở dưới cùng", () => {
  assert.match(sidebar, /function renderScanFeedback\(\)/);
  // Chữ giờ do BE cấp (/voice/config → scanFeedback) để có bản Mông; bản dưới đây chỉ là
  // dự phòng khi gặp server cũ, nên số tệp là {count} chứ không còn nội suy ${n}.
  assert.match(sidebar, /Em đã nhận \*\*\{count\} tệp\*\* giấy tờ từ máy quét/);  // text tổng số tệp
  assert.match(sidebar, /đặt tiếp tờ nữa/);                                       // còn thì đặt tiếp
  assert.match(sidebar, /Đã đưa đủ giấy tờ/);                                     // đủ thì bấm
  // Vẫn đọc thành tiếng, nhưng giọng đi theo ngôn ngữ CỦA CHỮ (xem scan-feedback-hmong).
  assert.match(sidebar, /window\.__hccTTS\?\.speak\?\.\(tts, hmPack \? "hmong" : "vi"\)/);
  // Chèn NGAY TRÊN danh sách giấy tờ (doc-progress-card) → danh sách + nút ở dưới cùng.
  assert.match(sidebar, /getElementById\("doc-progress-card"\)[\s\S]{0,120}insertBefore\(el, anchor\)/);
  assert.match(sidebar, /renderScanFeedback\(\); \/\/ text/);
});

test("không hiện dòng 'đang theo dõi' khi đã kết nối máy quét", () => {
  assert.doesNotMatch(sidebar, /Đang theo dõi máy quét/);   // đã bỏ theo yêu cầu
  assert.match(sidebar, /state === "chua_chon_thu_muc"/);   // chỉ còn nhắc chọn thư mục
});

test("cài đặt 'Ưu tiên Scan tại quầy': toggle lưu/nạp + tự chọn Scan (chỉ lượt LIVE)", () => {
  const html = fs.readFileSync(path.resolve(__dirname, "..", "sidebar.html"), "utf8");
  assert.match(html, /id="prefer-scan-switch"/);                        // toggle trong Cài đặt
  assert.match(sidebar, /PREFER_SCAN_KEY = "tlnd_prefer_scan"/);        // key lưu
  assert.match(sidebar, /res\?\.\[PREFER_SCAN_KEY\] === true/);          // nạp từ storage
  assert.match(sidebar, /function savePreferScan\(/);                    // lưu
  // renderDocOptions: preferScan + lượt LIVE + có scan → tự chọn Scan, KHÔNG render 2 nút.
  assert.match(sidebar, /if \(preferScan && renderingLiveReply && options\.includes\("scan"\)\)/);
  assert.match(sidebar, /renderingLiveReply = !opts\?\.noTts/);          // khôi phục phiên không tự bấm
  // Có link đổi sang QR khi tự chọn Scan.
  assert.match(sidebar, /Đổi sang chụp điện thoại \(QR\)/);
});

test("mỗi tệp máy quét về → toast; ảnh hướng dẫn bấm phóng to (lightbox)", () => {
  assert.match(sidebar, /function showToast\(/);
  assert.match(sidebar, /showToast\(`🖨️ Đã nhận: \$\{scanBaseName\(rel\)\}`\)/);
  assert.match(sidebar, /function openImageZoom\(/);
  // alt giờ lấy từ BE (bản Mông khi bật tiếng Mông) nên là biến `alt`, không còn hằng.
  assert.match(sidebar, /openImageZoom\(img, alt\)/);
  assert.match(css, /\.tlnd-toast\b/);
  assert.match(css, /\.img-zoom-scrim\b/);
});
