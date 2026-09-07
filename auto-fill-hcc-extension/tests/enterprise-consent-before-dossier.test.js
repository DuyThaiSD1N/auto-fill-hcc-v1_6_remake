// Cổng ĐKKD qua mạng có HAI chặng: bấm nút lần đầu = mở hồ sơ (wizard 3 bước), trang tải lại rồi
// panel TỰ bấm lại để quét. Nếu chốt đồng ý điều khoản đứng SAU bước mở hồ sơ thì màn điều khoản
// chỉ hiện ở lượt tự bấm — cán bộ đã bị đưa vào hồ sơ rồi mới được hỏi.
// Hợp đồng: đồng ý điều khoản TRƯỚC, rồi mới vào hồ sơ, rồi mới quét.
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8")
  .split(String.fromCharCode(13)).join("");

/** Thứ tự xuất hiện của các mốc trong thân một handler. */
function orderIn(handlerStart, marks) {
  const a = source.indexOf(handlerStart);
  assert.ok(a >= 0, `không tìm được handler: ${handlerStart}`);
  const b = source.indexOf("__AUTOFILL_HCC_POPUP_BUSY__ = true", a);
  assert.ok(b > a, "không tìm được mốc kết thúc phần gác cổng");
  const body = source.slice(a, b);
  return marks.map((m) => {
    const i = body.indexOf(m);
    assert.ok(i >= 0, `handler thiếu mốc: ${m}`);
    return { mark: m, at: i };
  });
}

// ---------------------------------------------------------------- 1. Nút "Quét và nhập dữ liệu"
{
  const o = orderIn('ocrBtn.addEventListener("click"', [
    "requireConsent(ocrBtn)",
    "startEnterpriseDossierIfNeeded()",
  ]);
  assert.ok(o[0].at < o[1].at,
    "Phải hỏi đồng ý điều khoản TRƯỚC khi mở hồ sơ doanh nghiệp (ocrBtn)");
  console.log("ok - ocrBtn: đồng ý điều khoản đứng trước bước mở hồ sơ");
}

// ---------------------------------------------------------------- 2. Nút "Quét nhập + đính kèm"
{
  const o = orderIn('fillAllBtn.addEventListener("click"', [
    "requireConsent(fillAllBtn)",
    "startEnterpriseDossierIfNeeded()",
  ]);
  assert.ok(o[0].at < o[1].at,
    "Phải hỏi đồng ý điều khoản TRƯỚC khi mở hồ sơ doanh nghiệp (fillAllBtn)");
  console.log("ok - fillAllBtn: đồng ý điều khoản đứng trước bước mở hồ sơ");
}

// ---------------------------------------------------------------- 3. Không mất khả năng mở hồ sơ
// khi chưa đính file: phép kiểm "Chưa có file nào" phải đứng SAU bước mở hồ sơ ở ocrBtn.
{
  const o = orderIn('ocrBtn.addEventListener("click"', [
    "startEnterpriseDossierIfNeeded()",
    'setStatus("Chưa có file nào.", "err")',
  ]);
  assert.ok(o[0].at < o[1].at,
    "Chưa đính file vẫn phải bấm nút để MỞ HỒ SƠ được — phép kiểm file không được chặn trước");
  console.log("ok - chưa có file vẫn mở được hồ sơ (kiểm file đứng sau)");
}

// ---------------------------------------------------------------- 4. Khoá đồng ý phải sống qua
// reload, nếu không lượt tự bấm sau khi vào hồ sơ sẽ hỏi lại lần hai.
{
  assert.ok(/restoreConsent\(\)/.test(source),
    "popup phải khôi phục trạng thái đồng ý qua reload (restoreConsent)");
  const ctx = source.indexOf("async function resolveConsentContext()");
  assert.ok(ctx >= 0, "không tìm được resolveConsentContext");
  const body = source.slice(ctx, ctx + 700);
  assert.ok(body.includes('base + "|" + proc'),
    "khoá đồng ý phải gồm thủ tục — cùng thủ tục thì hai chặng dùng chung một khoá");
  console.log("ok - khoá đồng ý (phiên|thủ tục) giữ qua reload → không hỏi lại lần hai");
}
