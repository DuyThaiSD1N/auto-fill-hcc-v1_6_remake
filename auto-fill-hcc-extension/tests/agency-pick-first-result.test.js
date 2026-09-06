// Tìm một thủ tục trên cổng DVC quốc gia thường ra NHIỀU thẻ "Nộp trực tuyến": cùng dịch vụ nhưng
// do Sở và do phường/xã tiếp nhận. Bản cũ gặp cảnh này là trả null rồi nhường người dùng bấm tay.
// Quy ước nghiệp vụ: LUÔN lấy thẻ ĐẦU TIÊN (cấp Sở đứng đầu danh sách).
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "agency-select.js"), "utf8")
  .split(String.fromCharCode(13)).join("");

function slice(start, end) {
  const a = source.indexOf(start);
  const b = source.indexOf(end, a);
  assert.ok(a >= 0 && b > a, `không tách được ${start}`);
  return source.slice(a, b);
}

/** Trang giả: mỗi thẻ là một "card" có tiêu đề + đúng một nút Nộp trực tuyến. */
function makePage(cards) {
  const buttons = [];
  cards.forEach((title, i) => {
    const button = { _card: title, textContent: "Nộp trực tuyến", tagName: "BUTTON" };
    // Thẻ phải có querySelectorAll: submitButtons(scope) đếm số nút NỘP trong đúng thẻ đó.
    const card = {
      textContent: `${title} Nộp trực tuyến`,
      parentElement: null,
      querySelectorAll: () => [button],
    };
    button.parentElement = card;
    buttons.push(button);
  });
  return {
    buttons,
    doc: {
      querySelectorAll: () => buttons,
    },
  };
}

function load(page) {
  const box = {
    document: page.doc,
    console: { log() {} },
    visible: () => true,
    fold: (s) => String(s || "").replace(/đ/g, "d").replace(/Đ/g, "D")
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim(),
    SUBMIT_LABEL: "nop truc tuyen",
  };
  vm.runInNewContext(`
    ${slice("  function submitButtons(", "  /** Tên cơ quan/thủ tục")}
    ${slice("  function submitButtonContext(", "  /**\n   * Chọn nút")}
    ${slice("  function pickSubmitButton(", "\n  /**\n   * Giai đoạn 2")}
    globalThis.pick = pickSubmitButton;
  `, box);
  // submitButtons(scope) lọc trong scope -> giả lập cho nhánh đếm nút trong 1 thẻ.
  return box;
}

const LABEL = "Thủ tục đăng ký kết hôn";

// ---------------------------------------------------------------- 1. Sở + phường -> lấy thẻ Sở
{
  const page = makePage([
    "Sở Tư pháp - Thủ tục đăng ký kết hôn",
    "UBND Phường Hạc Thành - Thủ tục đăng ký kết hôn",
  ]);
  const box = load(page);
  const chosen = box.pick(LABEL);
  assert.ok(chosen, "hai thẻ cùng tên thủ tục thì KHÔNG được bỏ cuộc");
  assert.strictEqual(chosen._card, "Sở Tư pháp - Thủ tục đăng ký kết hôn",
    `phải lấy thẻ đầu (cấp Sở), thực tế lấy: ${chosen._card}`);
  console.log("ok - ra cả Sở lẫn phường thì chọn thẻ đầu (Sở)");
}

// ---------------------------------------------------------------- 2. Nhãn cổng viết gọn hơn danh mục
// "Thủ tục đăng ký kết hôn" (danh mục) vs "Đăng ký kết hôn" (cổng) -> không thẻ nào khớp tên.
// Vẫn phải lấy thẻ đầu chứ không dừng lại bắt người dùng bấm.
{
  const page = makePage([
    "Sở Tư pháp - Đăng ký kết hôn",
    "UBND Phường Hạc Thành - Đăng ký kết hôn",
  ]);
  const box = load(page);
  const chosen = box.pick(LABEL);
  assert.ok(chosen, "khớp tên hụt thì vẫn phải chọn thẻ đầu, không bỏ cuộc");
  assert.strictEqual(chosen._card, "Sở Tư pháp - Đăng ký kết hôn",
    `phải lấy thẻ đầu, thực tế: ${chosen._card}`);
  console.log("ok - nhãn cổng viết gọn hơn danh mục thì vẫn chọn thẻ đầu");
}

// ---------------------------------------------------------------- 3. Một thẻ duy nhất
{
  const page = makePage(["Sở Tư pháp - Thủ tục đăng ký kết hôn"]);
  const box = load(page);
  assert.strictEqual(box.pick(LABEL)._card, "Sở Tư pháp - Thủ tục đăng ký kết hôn");
  console.log("ok - một thẻ thì chọn luôn thẻ đó");
}

// ---------------------------------------------------------------- 4. Không có thẻ nào
{
  const box = load(makePage([]));
  assert.strictEqual(box.pick(LABEL), null, "không có nút nào thì phải trả null để nhường người dùng");
  console.log("ok - không có kết quả thì trả null, không bịa");
}
