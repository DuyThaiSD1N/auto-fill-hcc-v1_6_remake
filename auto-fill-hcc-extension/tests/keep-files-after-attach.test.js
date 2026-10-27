// Đính kèm xong KHÔNG được tự xoá danh sách giấy tờ trong popup: cán bộ còn cần tệp để rà soát,
// đính lại hoặc dùng tiếp. Danh sách chỉ xoá khi đăng xuất, "Tạo phiên mới" hoặc đổi thủ tục.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const popup = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8").replace(/\/\/[^\n]*/g, "");
assert.doesNotMatch(popup, /clearFilesAfterAttach/, "không được dọn danh sách giấy tờ sau khi đính kèm");

console.log("keep files after attach passed");
