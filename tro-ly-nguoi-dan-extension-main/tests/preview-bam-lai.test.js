// Nút "Xem trước" của cổng tư pháp lâu lâu phải bấm lần hai mới mở. Chạy thật openPreview (content/guided-steps.js)
// với cổng giả: ~3 giây không mở, không báo gì → bấm lại một lần; cổng báo chặn → không bấm lại; mở ngay → bấm một lần.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "guided-steps.js"), "utf8");
const fn = src.match(/const PREVIEW_RETRY_TICKS = \d+;\s*async function openPreview\(button\) \{[\s\S]*?\n  \}/)[0];

// cổng giả: openAfterPress = cú bấm thứ mấy thì bản xem trước mở (0 = không bao giờ); message = lời chặn mỗi cú bấm.
function run({ openAfterPress = 0, message = "" }) {
  let presses = 0;
  let open = false;
  const pressAndWatch = async () => {
    presses += 1;
    if (openAfterPress && presses >= openAfterPress) open = true;
    return { ok: true, clicked: true, message };
  };
  const previewDialog = () => (open ? {} : null);
  const sleep = async () => {};
  // eslint-disable-next-line no-new-func
  const openPreview = new Function("pressAndWatch", "previewDialog", "sleep", `${fn}; return openPreview;`)(
    pressAndWatch, previewDialog, sleep);
  return openPreview({ isConnected: true, disabled: false }).then((res) => ({ res, presses }));
}

test("lần đầu cổng lờ đi → bấm lại một lần, mở được", async () => {
  const { res, presses } = await run({ openAfterPress: 2 });
  assert.equal(presses, 2);
  assert.equal(res.opened, true);
});

test("mở ngay lần đầu → không bấm lại", async () => {
  const { res, presses } = await run({ openAfterPress: 1 });
  assert.equal(presses, 1);
  assert.equal(res.opened, true);
});

test("cổng báo chặn (còn ô bắt buộc trống) → không bấm lại, trả lời chặn", async () => {
  const { res, presses } = await run({ message: "Vui lòng nhập Họ tên" });
  assert.equal(presses, 1);
  assert.equal(res.opened, false);
  assert.equal(res.message, "Vui lòng nhập Họ tên");
});

test("bấm lại vẫn không mở → chỉ bấm tối đa hai lần", async () => {
  const { res, presses } = await run({});
  assert.equal(presses, 2);
  assert.equal(res.opened, false);
});
