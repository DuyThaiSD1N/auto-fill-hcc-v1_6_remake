// Xuất JSON [{id: <request_id>, tinh: <tinh gốc>}] cho mọi trace thuộc các tỉnh mục tiêu.
// Cách xác định tỉnh: trace.user_id -> users.tinh (fold dấu, khớp danh sách TINH_LIST).
// Chạy trong container mongo (mongosh). Sửa TINH_LIST nếu cần đổi/thêm tỉnh.
const TINH_LIST = ["Lai Châu", "Bắc Ninh", "Lâm Đồng"];
const DB_NAME = "autofill_hcc";

function fold(s) {
  return (s == null ? "" : s.toString())
    .toLowerCase()
    .normalize("NFD")
    .replace(/đ/g, "d")
    .replace(/[̀-ͯ]/g, "")
    .trim();
}

const targets = new Set(TINH_LIST.map(fold));
const adb = db.getSiblingDB(DB_NAME);

// 1) user_id (string) -> tinh gốc, cho các user thuộc bất kỳ tỉnh mục tiêu nào.
const tinhByUid = {};
adb.users.find({}, { tinh: 1 }).forEach(function (u) {
  if (targets.has(fold(u.tinh))) tinhByUid[u._id.toString()] = u.tinh;
});
const uids = Object.keys(tinhByUid);

// 2) traces của các user đó, gộp trùng theo request_id.
const seen = {};
let traceCount = 0;
adb.traces
  .find({ user_id: { $in: uids } }, { request_id: 1, user_id: 1 })
  .forEach(function (t) {
    traceCount++;
    if (t.request_id && !(t.request_id in seen)) {
      seen[t.request_id] = { id: t.request_id, tinh: tinhByUid[t.user_id] };
    }
  });

const result = Object.keys(seen).map(function (k) { return seen[k]; });

// Chẩn đoán ra stderr để không lẫn vào JSON stdout: tổng + breakdown theo tỉnh (đã fold).
const byTinh = {};
result.forEach(function (r) {
  const k = fold(r.tinh);
  byTinh[k] = (byTinh[k] || 0) + 1;
});
console.error(
  "[i] users tỉnh khớp=" + uids.length +
  " | trace docs=" + traceCount +
  " | request_id duy nhất=" + result.length
);
console.error("[i] theo tỉnh: " + JSON.stringify(byTinh));
print(JSON.stringify(result, null, 2));
