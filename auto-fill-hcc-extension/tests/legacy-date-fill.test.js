// Ô ngày là thứ TRƯỢT MỘT LẦN LÀ MẤT HẲN: repairLostLegacyFields chỉ retry field đã từng điền
// được (eligibleNames), nên fillDate trả false một lần là field bị loại khỏi mọi lượt sửa sau đó
// và đỏ vĩnh viễn. Đó là gốc của triệu chứng "ngày cấp CCCD lúc điền được, lúc không".
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

// ---------------------------------------------------------------- splitLegacyDate
const start = source.indexOf("function splitLegacyDate");
const end = source.indexOf("\nfunction fillDate", start);
assert.ok(start >= 0 && end > start, "Không tách được splitLegacyDate");

const sandbox = {};
vm.runInNewContext(
  `${source.slice(start, end)}\nglobalThis.split = splitLegacyDate;`,
  sandbox
);

// vm trả mảng của realm khác nên deepStrictEqual so cả prototype sẽ trượt; so bằng chuỗi cho gọn.
const split = (value) => {
  const parts = sandbox.split(value);
  return parts ? Array.from(parts).join("/") : parts;
};

// Dạng chuẩn và các biến thể agent hay trả tùy giấy tờ.
assert.equal(split("16/12/2024"), "16/12/2024");
assert.equal(split("5/3/2024"), "05/03/2024", "Phải pad 2 chữ số");
assert.equal(split("16-12-2024"), "16/12/2024", "Gạch ngang vẫn phải nhận");
assert.equal(split("22.11.2024"), "22/11/2024", "Dấu chấm vẫn phải nhận");
assert.equal(split("2024-12-16"), "16/12/2024", "ISO phải đảo về dd/mm/yyyy");
// Không nhận dạng được thì trả null để filler báo false — KHÔNG đoán bừa.
assert.equal(split("1968"), null, "Chỉ có năm thì không phải ngày đầy đủ");
assert.equal(split(""), null);
assert.equal(split(null), null);
assert.equal(split("khong ro"), null);

// ---------------------------------------------------------------- hợp đồng nguồn
// Widget ngày của cổng chỉ ghi vào model nội bộ khi nhận blur. Thiếu typing/commit thì giá trị
// nằm trong DOM nhưng component không biết, và lần render lại bất kỳ sẽ xóa sạch.
const fillDateBody = source.slice(
  source.indexOf("function fillDate(container, f)"),
  source.indexOf("function fillDateText(container, f)")
);
assert.match(
  fillDateBody,
  /setNativeValue\(el, value, \{ typing: true, commit: true \}\)/,
  "fillDate phải phát đủ event như fillInput/fillDateText"
);
assert.doesNotMatch(
  fillDateBody,
  /f\.value\.split\("\/"\)/,
  "Không được tách ngày bằng split('/') cứng nữa"
);
assert.match(
  fillDateBody,
  /container\.querySelector\(`input\[name\$="\$\{suffix\}"\]`\)/,
  "Phải có fallback dò ô con theo hậu tố cho vùng động"
);

// Lượt chờ ô con render muộn phải phủ CẢ x-date, không riêng x-date-text.
assert.match(source, /async function retryLateDateFields\(fields, result, filledNames\)/);
assert.match(
  source,
  /f\.comp === "x-date-text" \|\| f\.comp === "x-date"/,
  "Lượt retry phải nhận cả hai loại ô ngày"
);
assert.match(
  source,
  /const attr = f\.comp === "x-date" \? "name" : "id"/,
  "x-date đánh tên ô con bằng name, x-date-text bằng id"
);
assert.match(source, /await retryLateDateFields\(fields, result, filledNames\)/, "Phải được gọi ở pass 3");
assert.doesNotMatch(source, /retryLateDateTextFields/, "Không còn tên hàm cũ nào sót lại");

console.log("legacy date fill: split bien the + typing/commit + retry cho x-date passed");
