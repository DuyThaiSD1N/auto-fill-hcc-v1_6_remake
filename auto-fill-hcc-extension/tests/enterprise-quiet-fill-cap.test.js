// Trang "Tên doanh nghiệp" (EnterpriseName.aspx) LUÔN chạm trần số lượt điền vì ô tiền tố loại hình
// là dropdown AutoPostBack: đặt giá trị là cổng tải lại trang ngay, lệnh đánh dấu "đã xong" chết
// theo trang. Kết quả vẫn đúng, nên toast đỏ "điền mãi không xong" ở trang này là CẢNH BÁO SAI.
// Hợp đồng: trang bật quietFillCap thì KHÔNG toast; trang khác vẫn phải toast như cũ.
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "..", "content", "procedures", "enterprise-registration.js"), "utf8")
  .split(String.fromCharCode(13)).join("");

// ---------------------------------------------------------------- spec khai đúng cờ
{
  const a = source.indexOf('"ten-doanh-nghiep": {');
  const b = source.indexOf("},", a);
  assert.ok(a >= 0 && b > a, "không tách được spec trang Tên doanh nghiệp");
  assert.ok(source.slice(a, b).includes("quietFillCap: true"),
    "trang Tên doanh nghiệp phải bật quietFillCap");
  console.log("ok - trang Tên doanh nghiệp có khai quietFillCap");
}

// ---------------------------------------------------------------- chạy thật nhánh chạm trần
function runCapBranch(spec) {
  // Tách đúng khối xử lý "vượt trần" rồi chạy nó với spec giả.
  const a = source.indexOf("      if (fillTries > MAX_FILL_TRIES) {");
  const b = source.indexOf("      if (fields.length) {", a);
  assert.ok(a >= 0 && b > a, "không tách được nhánh vượt trần");
  const box = {
    fillTries: 99, MAX_FILL_TRIES: 3, spec,
    console: { warn(...args) { box.warns.push(args.join(" ")); } },
    warns: [], toasts: [],
    toast: (msg) => box.toasts.push(msg),
    state: { done: [] },
    onPage: "x",
    setFillState: async () => {},
    scheduleStepFill() {},
  };
  const body = source.slice(a, b)
    .replace("state.done = [...state.done, onPage];", "state.done = [...state.done, onPage];");
  vm.runInNewContext(`(async () => { ${body} })();`, box);
  return box;
}

// a) Trang bật cờ -> KHÔNG toast đỏ, nhưng vẫn log để còn lần được.
{
  const box = runCapBranch({ label: "Tên doanh nghiệp", quietFillCap: true });
  assert.deepStrictEqual(box.toasts, [],
    `Trang bật quietFillCap KHÔNG được bắn toast, thực tế: ${JSON.stringify(box.toasts)}`);
  assert.ok(box.warns.some((w) => w.includes("Tên doanh nghiệp")),
    "vẫn phải console.warn để chẩn đoán được khi cần");
  console.log("ok - trang bật cờ: không toast đỏ, vẫn ghi log");
}

// b) Trang KHÔNG bật cờ -> vẫn toast như cũ (không được làm mất lưới an toàn của trang khác).
{
  const box = runCapBranch({ label: "Thông tin về vốn" });
  assert.strictEqual(box.toasts.length, 1,
    "Trang không bật cờ vẫn phải cảnh báo khi điền mãi không xong");
  assert.ok(box.toasts[0].includes("Thông tin về vốn"), "toast phải nêu đúng tên trang");
  console.log("ok - trang khác vẫn giữ cảnh báo đỏ như cũ");
}

// c) Dù im lặng hay không, trang vẫn phải được đánh dấu xong để luồng đi tiếp.
{
  for (const spec of [{ label: "A", quietFillCap: true }, { label: "B" }]) {
    const box = runCapBranch(spec);
    assert.ok(box.state.done.includes("x"),
      `trang ${spec.label} phải được đánh dấu xong để không kẹt luồng`);
  }
  console.log("ok - cả hai nhánh đều đánh dấu xong, không kẹt luồng");
}
