// Cổng DVC quốc gia mới: chọn "Bản thân" thì cổng chép giấy tờ tùy thân / nơi cư trú của tài khoản vào khối người được
// cấp rồi KHOÁ các ô đó. BE gửi khối này với onlyIfEmpty → ô đã có giá trị phải "giữ nguyên" (kept) TRƯỚC khi xét ô chỉ
// đọc; xét chỉ đọc trước thì ô đúng giá trị bị báo "không điền được" và tô đỏ.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const src = fs.readFileSync(path.join(__dirname, "..", "content", "surveyjs-main.js"), "utf8")
  .replace(/\/\/[^\n]*/g, "");

test("setOne: ô onlyIfEmpty đã có giá trị được giữ nguyên trước khi chặn ô chỉ đọc", () => {
  const start = src.indexOf("async function setOne(");
  assert.ok(start >= 0, "không thấy setOne");
  const body = src.slice(start, src.indexOf("\n  }\n", start));
  const keep = body.indexOf("field.onlyIfEmpty && !q.isEmpty?.()");
  const readonly = body.indexOf("q.isReadOnly");
  assert.ok(keep > 0 && readonly > 0, "thiếu nhánh giữ nguyên hoặc nhánh chỉ đọc");
  assert.ok(keep < readonly, "nhánh giữ nguyên phải đứng trước nhánh chỉ đọc");
  assert.match(body, /if \(q\.isReadOnly\) return \{ ok: false, reason: "readonly" \};/,
    "ô chỉ đọc mà còn trống vẫn phải báo không điền được");
});

// Bảng ngành nghề (matrixdynamic) của đăng ký thành lập hộ kinh doanh trên Cổng DVC quốc gia: BE gửi mảng dòng
// {ma, ten, chiTiet, chinh}; engine thêm đủ dòng, chọn mã trước, tên chỉ ghi khi ô còn trống, tích ngành chính.
function loadSetMatrix(extra = {}) {
  const start = src.indexOf("async function setMatrix(");
  assert.ok(start >= 0, "không thấy setMatrix");
  const fnSrc = src.slice(start, src.indexOf("async function setOne(", start));
  const fold = (s) => String(s ?? "").replace(/Đ/g, "D").replace(/đ/g, "d").normalize("NFD")
    .replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  const choicesOf = (q) => q.choices || [];
  const bestChoice = (q, want) => choicesOf(q).find((c) => fold(c.text) === fold(want)) || null;
  const document = { getElementById: () => null, activeElement: null, ...extra.document };
  // Đồng hồ giả: sleep chỉ đẩy giờ, vòng chờ theo Date.now() không quay bận thật.
  const clock = { t: 0 };
  const sleep = async (ms) => { clock.t += ms; };
  const FakeDate = { now: () => clock.t };
  return new Function("fold", "sleep", "choicesOf", "bestChoice", "document", "MouseEvent", "KeyboardEvent", "Event",
    "Date", `${fnSrc}; return setMatrix;`)(fold, sleep, choicesOf, bestChoice, document, class {}, class {}, class {},
    FakeDate);
}

function cell(type, extra = {}) {
  return {
    type, value: undefined, isReadOnly: false, choices: [], ...extra,
    getType() { return this.type; }, isEmpty() { return this.value === undefined || this.value === ""; },
  };
}

const TEN_5610 = "Nhà hàng và các dịch vụ ăn uống phục vụ lưu động";

function matrix(makeCells) {
  const rows = [];
  const makeRow = () => {
    const cells = makeCells();
    return { cells, getQuestionByColumnName: (n) => cells[n] };
  };
  rows.push(makeRow());
  return {
    rows,
    q: {
      columns: [{ name: "c1", title: "Tên ngành nghề" }, { name: "c2", title: "Chi Tiết Ngành nghề" },
        { name: "c3", title: "Mã ngành" }, { name: "c4", title: "Ngành chính" }],
      get rowCount() { return rows.length; },
      set rowCount(n) { while (rows.length < n) rows.push(makeRow()); },
      get visibleRows() { return rows; },
    },
  };
}

test("setMatrix: thêm dòng, chọn mã, giữ tên cổng tự đổ, tích ngành chính, dòng thiếu mã báo trượt", async () => {
  const { q, rows } = matrix(() => {
    const ten = cell("dropdown", { choices: [{ value: "T5610", text: TEN_5610 }, { value: "TX", text: "Bán nước mía" }] });
    const ma = cell("dropdown", { choices: [{ value: "5610", text: "5610" }] });
    let maValue;
    // Cổng tự đổ tên ngành theo mã → engine không ghi đè tên.
    Object.defineProperty(ma, "value", {
      get: () => maValue,
      set: (v) => { maValue = v; if (v) ten.value = "TU_DO"; },
    });
    return { c1: ten, c2: cell("text"), c3: ma, c4: cell("checkbox", { choices: [{ value: "Nganhchinh", text: "" }] }) };
  });
  const res = await loadSetMatrix()(q, [
    { ma: "5610", ten: TEN_5610, chiTiet: "", chinh: true },
    { ma: "", ten: "Bán nước mía", chiTiet: "Bán nước mía", chinh: false },
  ]);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].cells.c3.value, "5610");
  assert.equal(rows[0].cells.c1.value, "TU_DO");
  assert.deepEqual(rows[0].cells.c4.value, ["Nganhchinh"]);
  assert.equal(rows[0].cells.c2.value, undefined);
  assert.equal(rows[1].cells.c1.value, "TX");
  assert.equal(rows[1].cells.c2.value, "Bán nước mía");
  assert.equal(rows[1].cells.c4.value, undefined);
  assert.deepEqual(res, { ok: false, reason: "matrix-rows:2(ma:missing)" });
});

test("setMatrix: mã chỉ có danh mục sau khi chọn tên, danh mục tên nạp khi gõ tìm", async () => {
  const { q, rows } = matrix(() => {
    const ma = cell("dropdown");
    const ten = cell("dropdown");
    // Danh mục tên nạp theo chữ gõ (lazy load); chọn tên xong cổng mới nạp danh mục mã.
    ten.dropdownListModel = {
      popupModel: { isVisible: false },
      set filterString(text) { if (String(text).includes("Nhà hàng")) ten.choices = [{ value: "T5610", text: TEN_5610 }]; },
      get filterString() { return ""; },
    };
    let tenValue;
    Object.defineProperty(ten, "value", {
      get: () => tenValue,
      set: (v) => { tenValue = v; if (v) ma.choices = [{ value: "id-1", text: "5610" }]; },
    });
    return { c1: ten, c2: cell("text"), c3: ma, c4: cell("checkbox", { choices: [{ value: "Nganhchinh", text: "" }] }) };
  });
  const res = await loadSetMatrix()(q, [{ ma: "5610", ten: TEN_5610, chiTiet: "", chinh: true }]);
  assert.deepEqual(res, { ok: true });
  assert.equal(rows[0].cells.c1.value, "T5610");
  assert.equal(rows[0].cells.c3.value, "id-1");
});

test("setMatrix: mã không có trong danh mục thì không đoán theo chữ, báo lý do theo ô", async () => {
  const { q, rows } = matrix(() => ({
    c1: cell("dropdown", { choices: [{ value: "T", text: TEN_5610 }] }),
    c2: cell("text"),
    c3: cell("dropdown", { choices: [{ value: "5630", text: "5630" }] }),
    c4: cell("checkbox", { choices: [{ value: "Nganhchinh", text: "" }] }),
  }));
  const res = await loadSetMatrix()(q, [{ ma: "5610", ten: TEN_5610, chiTiet: "", chinh: true }]);
  assert.equal(rows[0].cells.c3.value, undefined);
  assert.equal(res.ok, false);
  assert.match(res.reason, /^matrix-rows:1\(ma:no-match\/1/);
});
