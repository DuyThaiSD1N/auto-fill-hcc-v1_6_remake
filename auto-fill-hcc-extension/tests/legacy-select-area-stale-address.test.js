// Khối địa chỉ x-select-area: KHÔNG được để lại số nhà của người khác.
//
// Cổng điền sẵn ô "Địa chỉ" (số nhà/đường) theo TÀI KHOẢN VNeID đang đăng nhập. Giấy tờ trong hồ sơ
// thường chỉ đọc được tới cấp xã (CCCD ghi "Nơi thường trú: P. Hoàng Văn Thụ, TP. Bắc Giang"), nên
// nếu chỉ điền tỉnh/xã rồi bỏ qua ô số nhà thì mục I ra một địa chỉ LAI: tỉnh/xã của giấy ghép với
// số nhà của người đang đăng nhập (ca thật: "Tỉnh Bắc Ninh / Phường Bắc Giang / TDP Số 30 Mỹ Đình").
// Sai kiểu đó trông vẫn hợp lệ nên không ai soát ra và sẽ được nộp đi.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

/** Cắt đúng ba hàm cần thử, chạy trên DOM giả — không dựng cả content script. */
function slice(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start);
  assert.ok(start >= 0 && end > start, `Không cắt được đoạn "${from}"`);
  return source.slice(start, end);
}

const sandbox = {
  console: { warn() {}, log() {} },
  sleep: async () => {},
  waitFor: async () => true,
  // Bản sao NGUYÊN VĂN norm() của content.js: GIỮ dấu (areaRoleOf dò chữ "tỉnh"/"xã" CÓ dấu).
  norm: (s) => (s || "").trim().toLowerCase().replace(/\s+/g, " "),
  isPlainSelectAreaValue: () => false,
  hasDivorceDecisionAreaValue: () => false,
  setNativeValue: (el, value) => { el.value = value; },
  markFilled: (el) => { el.marks.push("filled"); },
  markUnfilled: (el) => { el.marks.push("unfilled"); },
  // Dropdown thật: chọn xong thì chữ trên header đổi theo. Trả false = không có option khớp.
  pickInWidget: async (widget, value) => {
    if (widget.options && !widget.options.includes(value)) return false;
    widget.header.textContent = value;
    return true;
  },
};
vm.runInNewContext(
  slice("function normalizeAreaValue", "function hasDivorceDecisionAreaValue")
  + slice("function areaRoleOf", "function hasDivorceDecisionAreaValue")
  + slice("async function fillSelectArea", "async function fillSelectDefault")
  + "globalThis.fillSelectArea = fillSelectArea;",
  sandbox,
);

/** Khối địa chỉ giả: ba dropdown (quốc gia/tỉnh/xã) + một ô số nhà. */
function makeArea({ tinh, xa, diaChi }) {
  const widget = (label, selected) => {
    const header = { textContent: selected, marks: [] };
    return {
      id: `custom-select-${label}`,
      header,
      parentElement: { textContent: label },
      querySelector: (sel) => (sel === ".input-field-select" ? header : null),
    };
  };
  const widgets = [
    widget("Quốc gia", "Việt Nam"),
    widget("Tỉnh/Thành phố", tinh),
    widget("Xã/Phường", xa),
  ];
  const addr = { value: diaChi, marks: [], parentElement: null };
  const container = {
    widgets,
    addr,
    querySelectorAll: (sel) => (sel === '[id^="custom-select-"]' ? widgets : []),
    querySelector: (sel) => {
      if (sel === '[id^="custom-select-"]') return widgets[0];
      if (sel === "input.input-field") return addr;
      return null;
    },
  };
  return container;
}

const BAC_NINH = { quocGia: "Việt Nam", tinh: "Tỉnh Bắc Ninh", xa: "Phường Bắc Giang" };

(async () => {
  // 1. Giấy tờ CÓ số nhà → điền đè như trước, không đổi gì.
  const co = makeArea({ tinh: "Thành phố Hà Nội", xa: "Phường Mỹ Đình", diaChi: "TDP Số 30 Mỹ Đình" });
  assert.equal(await sandbox.fillSelectArea(co, { value: { ...BAC_NINH, diaChi: "Tổ dân phố Hoàng Hoa Thám 2" } }), true);
  assert.equal(co.addr.value, "Tổ dân phố Hoàng Hoa Thám 2", "Có số nhà trên giấy thì phải ghi đè");
  assert.deepEqual(co.addr.marks, ["filled"]);

  // 2. CA THẬT: giấy tờ KHÔNG có số nhà và tỉnh/xã ĐỔI sang địa bàn khác → phải xóa số nhà cũ.
  const lai = makeArea({ tinh: "Thành phố Hà Nội", xa: "Phường Mỹ Đình", diaChi: "TDP Số 30 Mỹ Đình" });
  await sandbox.fillSelectArea(lai, { value: { ...BAC_NINH, diaChi: "" } });
  assert.equal(lai.addr.value, "",
    "Đổi tỉnh/xã mà không có số nhà: KHÔNG được giữ số nhà của tài khoản đăng nhập");
  assert.deepEqual(lai.addr.marks, ["unfilled"], "Ô bị xóa phải được tô để người dân gõ lại");

  // 3. Tỉnh/xã KHÔNG đổi (cổng điền sẵn đã đúng địa bàn) → số nhà cũ vẫn của đúng người, GIỮ nguyên.
  const giu = makeArea({ tinh: "Tỉnh Bắc Ninh", xa: "Phường Bắc Giang", diaChi: "Tổ dân phố Hoàng Hoa Thám 2" });
  await sandbox.fillSelectArea(giu, { value: { ...BAC_NINH, diaChi: "" } });
  assert.equal(giu.addr.value, "Tổ dân phố Hoàng Hoa Thám 2",
    "Cùng địa bàn thì số nhà cổng điền sẵn vẫn dùng được, không được xóa oan");
  assert.deepEqual(giu.addr.marks, []);

  // 4. Không chọn được option nào (tỉnh/xã không khớp danh mục) → không đụng vào số nhà.
  const hong = makeArea({ tinh: "Thành phố Hà Nội", xa: "Phường Mỹ Đình", diaChi: "TDP Số 30 Mỹ Đình" });
  for (const w of hong.widgets) w.options = ["Việt Nam"];
  await sandbox.fillSelectArea(hong, { value: { ...BAC_NINH, diaChi: "" } });
  assert.equal(hong.addr.value, "TDP Số 30 Mỹ Đình",
    "Chưa đổi được tỉnh/xã thì chưa có căn cứ nói số nhà là của người khác");

  console.log("legacy select-area: stale street address cleared on area change passed");
})();
