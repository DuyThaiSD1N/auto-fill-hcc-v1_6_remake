// Vùng động =5 của "Xác nhận tình trạng hôn nhân" có BA ô ngày:
//   "Ngày cấp giấy chứng nhận kết hôn"  (do field raw ngayCapGiayTo-* điền ở tầng trên)
//   "Thời điểm bắt đầu của khoảng thời gian mong muốn xác nhận chưa đăng ký kết hôn với ai"
//   "Thời điểm kết thúc ..."
// Đếm thứ tự là lệch: ô ngày cấp nuốt mốc bắt đầu, raw ghi đè lên nó, mốc kết thúc nhảy vào ô bắt
// đầu và ô kết thúc trống (đúng lỗi gặp trên cổng thật). Phải định vị theo NHÃN.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content", "fill-legacy.js"), "utf8");

function slice(from, to) {
  const start = source.indexOf(from);
  const end = source.indexOf(to, start);
  assert.ok(start >= 0 && end > start, `Không cắt được đoạn "${from}"`);
  return source.slice(start, end);
}

const sandbox = {
  console: { warn() {}, log() {} },
  waitFor: async () => true,
  setNativeValue: (el, value) => { el.value = value; },
  markFilled: () => {},
  norm: (s) => (s || "").trim().toLowerCase().replace(/\s+/g, " "),
};
vm.runInNewContext(
  slice("function selectAreaTextControls", "function isPlainSelectAreaValue")
  + slice("function fillDivorceDecisionAreaByKnownNames", "async function fillSelectArea")
  + slice("function hasDivorceDecisionAreaValue", "function selectAreaTextControls")
  + "globalThis.fillDivorceDecisionArea = fillDivorceDecisionArea;"
  + "globalThis.hasDivorceDecisionAreaValue = hasDivorceDecisionAreaValue;",
  sandbox,
);

function input(name, { type = "text", useId = false } = {}) {
  const self = {
    tagName: "INPUT", value: "", owner: null, parentElement: null,
    id: useId ? name : "",
    getAttribute: (a) => (a === "type" ? type : a === "name" ? (useId ? null : name) : null),
    matches: (sel) => sel.includes("input"),
    querySelector: () => null,
    contains: (node) => node === self,
    closest: () => self.owner,
    get textContent() { return ""; },
    _name: name, _useId: useId,
  };
  return self;
}

/** x-date + hàng nhãn bọc ngoài, giống <span class="span_show">Nhãn: <input…></span> của eForm. */
function dateRow(prefix, label, { useId = false } = {}) {
  const parts = ["day", "month", "year", "name-date-input"]
    .map((suffix) => input(`${prefix}-${suffix}`, { useId }));
  const control = {
    tagName: "X-DATE", parts, parentElement: null,
    contains: (node) => parts.includes(node),
    querySelector: (sel) => {
      const prefixSel = sel.match(/(?:name|id)\^="([^"]+)"/);
      if (prefixSel) {
        // DOM thật: [name^=…] chỉ khớp khi ô có name; ô chỉ có id thì phải dùng [id^=…].
        const wantsId = sel.includes(`id^="${prefixSel[1]}"`);
        const wantsName = sel.includes(`name^="${prefixSel[1]}"`);
        return parts.find((p) => p._name.startsWith(prefixSel[1])
          && ((p._useId && wantsId) || (!p._useId && wantsName))) || null;
      }
      if (sel.includes('-day"')) return parts[0];
      if (sel.includes('-month"')) return parts[1];
      if (sel.includes('-year"')) return parts[2];
      if (sel.includes("date-input")) return parts[3];
      return null;
    },
  };
  for (const p of parts) p.owner = control;
  const row = { tagName: "SPAN", textContent: label, parentElement: null };
  control.parentElement = row;
  return { control, row, parts };
}

function makeArea5({ marriageDateUsesId = false } = {}) {
  const spouse = input("voChongHoTen");
  const number = input("soGiayTo");
  const agency = input("coQuanCapGiayTo");
  const capGCN = dateRow("ngayCapGiayTo", "Ngày cấp giấy chứng nhận kết hôn",
    { useId: marriageDateUsesId });
  const batDau = dateRow("x1", "Thời điểm bắt đầu của khoảng thời gian mong muốn xác nhận chưa đăng ký kết hôn với ai:");
  const ketThuc = dateRow("x2", "Thời điểm kết thúc của khoảng thời gian mong muốn xác nhận chưa đăng ký kết hôn với ai:");
  const texts = [spouse, agency, number];
  const dates = [capGCN, batDau, ketThuc];
  // Khối bọc cả vùng: textContent gộp mọi nhãn -> vòng leo phải dừng ở đây, không khớp nhầm.
  const wrapper = { tagName: "DIV", parentElement: null,
    textContent: dates.map((d) => d.row.textContent).join(" ") };
  for (const d of dates) d.row.parentElement = wrapper;

  return {
    spouse, number, agency,
    capGCN: capGCN.parts, batDau: batDau.parts, ketThuc: ketThuc.parts,
    querySelector: (sel) => {
      for (const el of texts) if (sel.includes(`"${el._name}"`)) return el;
      for (const suffix of ["day", "month", "year", "name-date-input"]) {
        if (sel.includes(`"ngayCapGiayTo-${suffix}"`)) {
          return marriageDateUsesId ? null : capGCN.parts[["day", "month", "year", "name-date-input"].indexOf(suffix)];
        }
      }
      return null;
    },
    querySelectorAll: (sel) => {
      if (sel.includes("x-date")) return dates.map((d) => d.control);
      return texts.concat(dates.flatMap((d) => d.parts));
    },
  };
}

const VALUES = {
  voChongHoTen: "Nguyễn Phạm Thu Huyền",
  thoiDiemBatDau: "01/01/2025",
  thoiDiemKetThuc: "13/12/2025",
};
const ymd = (parts) => [parts[0].value, parts[1].value, parts[2].value];

(async () => {
  assert.equal(sandbox.hasDivorceDecisionAreaValue({ thoiDiemBatDau: "01/01/2025" }), true,
    "Giá trị vùng =5 phải được định tuyến vào filler khối động");

  // 1. Ô ngày cấp GCN có name -> loại được cả bằng tên lẫn bằng nhãn.
  const a = makeArea5();
  await sandbox.fillDivorceDecisionArea(a, { ...VALUES });
  assert.equal(a.spouse.value, "Nguyễn Phạm Thu Huyền");
  assert.deepEqual(ymd(a.batDau), ["01", "01", "2025"], "Mốc BẮT ĐẦU phải vào đúng ô có nhãn bắt đầu");
  assert.deepEqual(ymd(a.ketThuc), ["13", "12", "2025"], "Mốc KẾT THÚC phải vào đúng ô có nhãn kết thúc");
  assert.deepEqual(ymd(a.capGCN), ["", "", ""], "Ô ngày cấp GCN để cho field raw điền, không được đụng");

  // 2. CA THẬT: ô ngày cấp GCN chỉ có id (không có name) -> lọc theo name trượt.
  //    Nhãn vẫn phải cứu được, nếu không mốc bắt đầu lại bị nuốt như trên cổng.
  const b = makeArea5({ marriageDateUsesId: true });
  await sandbox.fillDivorceDecisionArea(b, { ...VALUES });
  assert.deepEqual(ymd(b.batDau), ["01", "01", "2025"],
    "Ô ngày cấp GCN đặt tên bằng id vẫn KHÔNG được nuốt mốc bắt đầu");
  assert.deepEqual(ymd(b.ketThuc), ["13", "12", "2025"]);
  assert.deepEqual(ymd(b.capGCN), ["", "", ""]);

  console.log("legacy tthn period area: period dates targeted by label passed");
})();
