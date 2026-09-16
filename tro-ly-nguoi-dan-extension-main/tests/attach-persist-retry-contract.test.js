// Đính kèm: KHÔNG được báo thành công khi cổng chưa ghi nhận file, và một tệp hỏng không
// được chặn các tệp còn lại. Bối cảnh: cổng moj trả 500 xen kẽ — 4 tệp chỉ vào được 2-3,
// phần hỏng vẫn bị tô xanh và báo ok.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const attach = fs.readFileSync(path.join(root, "content", "attach-core.js"), "utf8");
const sidebar = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");

test("verify đính bền với cổng ĐƠ: poll thật + check lần cuối + backoff retry", () => {
  // waitFor KHÔNG await callback → verify async chỉ chạy 1 lần; persist phải TỰ poll bằng vòng lặp.
  assert.match(attach, /async function waitForPersistedAttachment[\s\S]*?while \(Date\.now\(\) - start < timeout\)/);
  // Check LẦN CUỐI sau vòng lặp (cổng đơ >timeout thì Date.now vượt hạn ngay trong lúc đơ).
  assert.match(attach, /while \(Date\.now\(\) - start < timeout\)[\s\S]{0,420}?\n\s*return await probe\(\); \/\/ lần cuối/);
  // Hạn chờ: 12s → 25s (nới cho cổng đơ) → 8s. Rút mạnh được vì bỏ cuộc sớm giờ RẺ: hoãn lại
  // rồi lượt sau quay lại, mà lượt sau dedup sẽ nhận ra tệp đã lên trang nên không đính trùng.
  // Chờ 25s thì mỗi tệp hỏng bắt tất cả tệp còn lại xếp hàng.
  assert.match(attach, /waitForPersistedAttachment\(row, planItem = \{\}, previousName = "", timeout = 8000\)/);
  // Vòng chờ bằng chứng dương phải SẠCH tín hiệu toàn trang: toast không được cắt nó.
  assert.ok(!/PortalUploadError/.test(
    attach.slice(attach.indexOf("async function waitForPersistedAttachment")).split("\n}")[0]));
  // Tệp CUỐI/DUY NHẤT hỏng: round-robin không có tệp khác chen → backoff TĂNG DẦN trước khi thử lại.
  assert.match(attach, /const backoffMs = \(round - 1\) \* 3000 \+ \(queue\.length <= 1 \? 2500 : 0\)/);
  assert.match(attach, /const MAX_ROUNDS = 3/);
});

test("chỉ tô xanh khi TÊN FILE hiện thật trên dòng", () => {
  // Modal đóng chỉ chứng minh cú click đã chạy; cổng vẫn có thể trả 500 sau đó.
  assert.match(attach, /async function waitForPersistedAttachment[\s\S]{0,600}?rowAttachedFileName\(liveRow\)/);
  assert.match(attach, /const persisted = await waitForPersistedAttachment\(row, planItem, existingName\)/);
  assert.match(attach, /if \(!persisted\)[\s\S]{0,320}?markAttachmentResult\(liveRow \|\| dialog, false\)/);
  assert.match(attach, /code: "wallet-file-not-persisted"/);
  // Không còn đường tô xanh vô điều kiện sau khi modal đóng.
  assert.doesNotMatch(attach, /markAttachmentResult\(row \|\| dialog, true\)/);
});

test("tạo được DÒNG chưa phải là đính xong", () => {
  // addAttachmentComponent trước đây tô xanh ngay khi thêm được dòng trống → bước đính sau
  // hỏng thì dòng vẫn giữ màu xanh cũ.
  const fn = attach.slice(attach.indexOf("async function addAttachmentComponent"));
  const body = fn.slice(0, fn.indexOf("\n}\n"));
  assert.doesNotMatch(body, /markAttachmentResult\([^)]*true\)/);
});

test("hỏng một tệp KHÔNG chặn các tệp còn lại", () => {
  assert.match(attach, /const MAX_ROUNDS = 3/);
  assert.match(attach, /for \(let round = 1; round <= MAX_ROUNDS && queue\.length; round\+\+\)/);
  assert.match(attach, /deferred\.push\(\{ item, index: i \}\);\s*\n\s*continue;/);
  assert.match(attach, /queue = deferred;/);
  // Vòng retry TẠI CHỖ cũ phải biến mất: nó chờ chết 2s+4s rồi vẫn break bỏ các tệp sau.
  assert.doesNotMatch(attach, /MAX_ATTACH_ATTEMPTS/);
  assert.doesNotMatch(attach, /sleep\(2000 \* attempt\)/);
});

test("báo lỗi theo TỪNG tệp, không nuốt", () => {
  assert.match(attach, /for \(const \{ index \} of queue\)[\s\S]{0,200}?errors\.push\(message\)/);
  // Lý do thật từ toast của cổng (vd "Upload failed: 500") phải vào được lỗi trả về.
  // Đọc qua newPortalUploadError (so với mốc chụp trước lượt) chứ không đọc toast trần —
  // xem tests/attach-fast-fail-contract.test.js.
  assert.match(attach, /function portalUploadErrorNodes\(\)/);
  assert.match(attach, /portalError \? ` — cổng báo: \$\{portalError\}` : ""/);
});

test("scan/chọn tệp: bytes giữ tại chỗ, KHÔNG tải lại lần nào", () => {
  // Phải CHỜ xong trong luồng upload. Bắn-rồi-quên thì bấm "Đã đưa đủ" ngay là cache chưa
  // kịp ghi → vẫn phải tải.
  assert.match(sidebar, /await cacheUploadedBlobs\(uploadSid, files, data\?\.accepted\)/);
  // Giữ BLOB chứ không giữ dataUrl: Blob là tham chiếu → không phình heap, không cần trần.
  assert.match(sidebar, /blob: files\[i\]/);
  assert.doesNotMatch(sidebar, /FILE_CACHE_MAX_BYTES/);
});

test("không được ghép nhầm fid với tệp", () => {
  // Ghép nhầm = đính NHẦM giấy tờ, nặng hơn nhiều so với phải tải lại → thà bỏ cache.
  assert.match(sidebar, /accepted\.length !== files\.length[\s\S]{0,220}?return;/);
  assert.match(sidebar, /serverName !== files\[i\]\.name[\s\S]{0,200}?return;/);
});

test("QR: kéo sớm, một fid chỉ tải đúng một lần", () => {
  assert.match(sidebar, /void prefetchSessionFiles\(uploadSid\)/);
  // prefetch đang bay mà bước đính cũng hỏi → dùng CHUNG một promise, không tải đôi.
  assert.match(sidebar, /const flying = fileInFlight\.get\(fid\);\s*\n\s*if \(flying\) return flying;/);
  // prefetch (kéo nền) vẫn tải song song cho nhanh — KHÁC bước dựng payload đọc tuần tự.
  assert.match(sidebar, /await Promise\.all\(\(sess\.files/);
  // Đổi phiên phải xoá cache, không được lẫn giấy tờ người trước.
  assert.match(sidebar, /function resetFileCache\(sid\)[\s\S]{0,240}?fileCache = new Map\(\)/);
});

test("tải tệp có retry — một cú chớp mạng không được giết cả lượt đính", () => {
  assert.match(sidebar, /async function downloadSessionFile[\s\S]{0,600}?attempt <= 3/);
  // 4xx (tệp không còn / hết quyền) thì thử lại vô ích.
  assert.match(sidebar, /fr\.status >= 400 && fr\.status < 500/);
});

test("blobToDataUrl không nuốt lỗi thành [object ProgressEvent]", () => {
  // onerror PHẢI reject DOMException thật (r.error), KHÔNG reject cái ProgressEvent (event) —
  // String(event) = "[object ProgressEvent]" khiến trợ lý báo lỗi vô nghĩa.
  assert.match(sidebar, /r\.onerror = \(\) => reject\(r\.error \|\|/);
  assert.doesNotMatch(sidebar, /r\.onerror = reject\b/);
});

test("đọc tệp BỀN BỈ: blob cục bộ lỗi → tải lại từ server rồi đọc lại, thử vài vòng", () => {
  assert.match(sidebar, /async function readEntryToDataUrl/);
  // Vòng 1: blob đang cầm. Hỏng → tải lại từ phiên server (server luôn giữ bản hợp lệ) rồi đọc lại.
  assert.match(sidebar, /const fresh = await downloadSessionFile\(sid, f\.fid, f\.name\)[\s\S]{0,220}?blobToDataUrl\(fresh\.blob\)/);
  assert.match(sidebar, /for \(let attempt = 1; attempt <= 3; attempt\+\+\)/);
});

test("dựng payload đính kèm ĐỌC TUẦN TỰ, không Promise.all (tránh dồn RAM)", () => {
  const fn = sidebar.slice(sidebar.indexOf("async function fetchSessionFilesAsPayload"));
  const body = fn.slice(0, fn.indexOf("\n  }\n"));
  assert.match(body, /for \(let i = 0; i < list\.length; i\+\+\)/);
  assert.match(body, /await readEntryToDataUrl\(sid, f, entry\)/);
  assert.doesNotMatch(body, /await Promise\.all/);   // KHÔNG đọc song song (chỉ có chữ trong comment)
});

test("lỗi đính kèm ra TIẾNG VIỆT, không lọt [object …] hay lỗi tiếng Anh", () => {
  assert.match(sidebar, /function viAttachError\(e\)/);
  // Câu đã có dấu tiếng Việt (của mình) thì giữ nguyên; lỗi ASCII (tiếng Anh) mới dịch.
  assert.match(sidebar, /if \(\/\[\^\\x00-\\x7F\]\/\.test\(raw\)\) return raw;/);
  assert.match(sidebar, /notreadable\|could not be read/);
  // Cả 2 nhánh catch của đính kèm đều dùng viAttachError, không còn String\(e\)\.
  assert.doesNotMatch(sidebar, /errors: \[String\(e\?\.message \|\| e\)\]/);
  assert.ok((sidebar.match(/errors: \[viAttachError\(e\)\]/g) || []).length >= 2,
    "cả lượt đính thường lẫn ĐKKD phải dịch lỗi sang tiếng Việt");
});
