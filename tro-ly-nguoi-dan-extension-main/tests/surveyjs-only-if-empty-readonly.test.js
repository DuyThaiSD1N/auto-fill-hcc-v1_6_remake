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

// Ô dropdown nạp danh mục theo chữ gõ (lazy load): ghi lại mọi chữ gõ vào ô lọc, chữ nào nạp ra mục nào do test quyết.
function lazyDropdown(load) {
  const q = cell("dropdown");
  q.typed = [];
  let filter = "";
  q.dropdownListModel = {
    popupModel: { isVisible: false },
    get filterString() { return filter; },
    set filterString(text) {
      filter = String(text);
      q.typed.push(filter);
      if (filter) q.choices = load(filter) || [];
    },
  };
  return q;
}

const TEN_4719 = "Bán lẻ tổng hợp khác";

test("setMatrix: cột tên không gõ mã vào ô lọc; mã cổng không có thì báo missingCodes, không để tên lẻ", async () => {
  // Danh mục ngành của cổng ít hơn danh mục cấp 4 của BE: không có 4719. Ô lọc của cột tên gõ "4719" thì API trả mục
  // chữ "4719" — engine cũ gõ mã vào đó nên ô tên hiện "4719".
  const ten = lazyDropdown((text) => (text === "4719" ? [{ value: "4719", text: "4719" }]
    : text.startsWith("Bán lẻ") ? [{ value: "T4711", text: "Bán lẻ lương thực" }] : []));
  const ma = lazyDropdown(() => []);
  const { q, rows } = matrix(() => ({
    c1: ten, c2: cell("text"), c3: ma, c4: cell("checkbox", { choices: [{ value: "Nganhchinh", text: "" }] }),
  }));
  const res = await loadSetMatrix()(q, [{ ma: "4719", ten: TEN_4719, chiTiet: "Bán tạp hóa", chinh: false }]);
  assert.ok(!ten.typed.includes("4719"), `cột tên đã gõ: ${ten.typed.join(" | ")}`);
  assert.deepEqual(ten.typed.filter(Boolean), [TEN_4719, "Bán lẻ"], "chỉ gõ chữ tên (cả tên rồi hai chữ đầu)");
  assert.equal(ten.dropdownListModel.filterString, "", "xoá chữ đã gõ khỏi ô lọc");
  assert.equal(rows[0].cells.c1.value, undefined, "không để tên lẻ khi cổng không có mã");
  assert.equal(rows[0].cells.c3.value, undefined);
  assert.equal(rows[0].cells.c2.value, "Bán tạp hóa", "giữ chi tiết để người dùng biết dòng kinh doanh gì");
  assert.equal(res.ok, false);
  assert.deepEqual(res.missingCodes, ["4719"]);
});

test("setMatrix: ô tên chỉ hiện mã (cổng tự đổ mà không nạp được chữ tên) thì xoá, giữ mã", async () => {
  const { q, rows } = matrix(() => {
    const ten = cell("dropdown");
    const ma = cell("dropdown", { choices: [{ value: "5610", text: "5610" }] });
    let maValue;
    Object.defineProperty(ma, "value", {
      get: () => maValue,
      set: (v) => { maValue = v; if (v) ten.value = "5610"; },
    });
    return { c1: ten, c2: cell("text"), c3: ma, c4: cell("checkbox", { choices: [{ value: "Nganhchinh", text: "" }] }) };
  });
  const res = await loadSetMatrix()(q, [{ ma: "5610", ten: TEN_5610, chiTiet: "", chinh: true }]);
  assert.equal(rows[0].cells.c3.value, "5610");
  assert.equal(rows[0].cells.c1.value, undefined);
  assert.match(res.reason, /ten:code-shown/);
  assert.equal(res.missingCodes, undefined, "mã có trong danh mục thì không báo thiếu");
});

test("setMatrix: điền lại theo danh sách mới — bỏ dòng thừa, dòng đổi mã thì ghi lại tên, chi tiết bị xoá thì ghi lại",
  async () => {
    const make = (ma, ten) => {
      const tenCell = cell("dropdown", { value: ten, choices: [{ value: "T5610", text: TEN_5610 }] });
      const maCell = cell("dropdown", { value: ma, choices: [{ value: "5610", text: "5610" }] });
      // Cổng xoá ô chi tiết ở lần ghi đầu (dựng lại dòng sau khi đổi tên) → engine phải ghi lại.
      const chiTiet = cell("text");
      let sets = 0;
      let detail;
      Object.defineProperty(chiTiet, "value", {
        get: () => detail,
        set: (v) => { sets += 1; detail = sets === 1 ? undefined : v; },
      });
      const cells = { c1: tenCell, c2: chiTiet, c3: maCell, c4: cell("checkbox", { choices: [{ value: "N", text: "" }] }) };
      return { cells, getQuestionByColumnName: (n) => cells[n] };
    };
    const rows = [make("4711", "T4711"), make("4719", "T4719")];
    const q = {
      columns: [{ name: "c1", title: "Tên ngành nghề" }, { name: "c2", title: "Chi Tiết Ngành nghề" },
        { name: "c3", title: "Mã ngành" }, { name: "c4", title: "Ngành chính" }],
      get rowCount() { return rows.length; },
      set rowCount(n) { rows.length = Math.min(rows.length, n); },
      get visibleRows() { return rows; },
    };
    const res = await loadSetMatrix()(q, [{ ma: "5610", ten: TEN_5610, chiTiet: "Mở quán ăn", chinh: true }]);
    assert.deepEqual(res, { ok: true });
    assert.equal(rows.length, 1, "bảng theo đúng danh sách mới");
    assert.equal(rows[0].cells.c3.value, "5610");
    assert.equal(rows[0].cells.c1.value, "T5610", "tên cũ của mã 4711 được thay bằng tên mã mới");
    assert.equal(rows[0].cells.c2.value, "Mở quán ăn");
  });

// Bảng "Thành viên hộ gia đình" (đăng ký thành lập hộ kinh doanh, Cổng DVC quốc gia): tên câu hỏi trên cổng chưa biết →
// engine tìm bảng theo tiêu đề cột; dòng chuHo lấy theo phần chủ hộ trên biểu mẫu, ô đó trống mới dùng giá trị BE gửi.
function loadMembers(questions = {}) {
  const start = src.indexOf("async function setMatrix(");
  const fnSrc = src.slice(start, src.indexOf("async function setOne(", start));
  const fold = (s) => String(s ?? "").replace(/Đ/g, "D").replace(/đ/g, "d").normalize("NFD")
    .replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  const choicesOf = (q) => q.choices || [];
  const bestChoice = (q, want) => choicesOf(q).find((c) => fold(c.text) === fold(want)) || null;
  const findQuestion = (_survey, name) => questions[name] || null;
  const toIsoDate = (value) => {
    const m = String(value || "").trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    return m ? `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}` : String(value || "");
  };
  const clock = { t: 0 };
  const sleep = async (ms) => { clock.t += ms; };
  return new Function("fold", "sleep", "choicesOf", "bestChoice", "document", "MouseEvent", "KeyboardEvent", "Event",
    "Date", "findQuestion", "toIsoDate",
    `${fnSrc}; return { setMemberMatrix, findMemberMatrix, isMemberMatrix };`)(
    fold, sleep, choicesOf, bestChoice, { getElementById: () => null, activeElement: null }, class {}, class {},
    class {}, { now: () => clock.t }, findQuestion, toIsoDate);
}

const MEMBER_COLS = [{ name: "m1", title: "Họ và tên" }, { name: "m2", title: "Ngày sinh" },
  { name: "m3", title: "Số định danh cá nhân" }, { name: "m4", title: "Giới tính" }, { name: "m5", title: "Quốc tịch" },
  { name: "m6", title: "Nơi thường trú" }];

function memberMatrix(makeCells, start = 2) {
  const rows = [];
  const makeRow = () => {
    const cells = makeCells();
    return { cells, getQuestionByColumnName: (n) => cells[n] };
  };
  while (rows.length < start) rows.push(makeRow()); // cổng để sẵn hai dòng trống
  return {
    rows,
    q: {
      name: "bang7__1", isVisible: true, columns: MEMBER_COLS, getType: () => "matrixdynamic",
      get rowCount() { return rows.length; },
      set rowCount(n) { while (rows.length < n) rows.push(makeRow()); rows.length = n; },
      get visibleRows() { return rows; },
    },
  };
}

const formQ = (value, extra = {}) => ({ value, getType: () => extra.type || "text", isEmpty: () => !value, ...extra });

test("bảng thành viên: tìm theo tiêu đề cột, dòng chủ hộ lấy theo phần chủ hộ trên biểu mẫu", async () => {
  // Dữ liệu giả.
  const questions = {
    citizenName: formQ("LÊ THỊ HOA"),
    citizenDateOfBirth: formQ("1990-06-05"),
    citizengioiTinh: formQ("2", { type: "dropdown", selectedItem: { text: "Nữ" } }),
    citizenIdentity: formQ("001190000011"),
    citizenDiachi: formQ("Xóm A"),
    citizenxa: formQ("x-1", { type: "dropdown", selectedItem: null, displayValue: "Phường Hoa Lư" }),
    // Danh mục tỉnh chưa nạp: chỉ có mã → bỏ, không ghi mã vào ô chữ.
    citizenTinh: formQ("019d-tinh", { type: "dropdown", selectedItem: null, displayValue: "019d-tinh" }),
  };
  const { setMemberMatrix, findMemberMatrix, isMemberMatrix } = loadMembers(questions);
  const { q, rows } = memberMatrix(() => {
    const quocTich = lazyDropdown((text) => (text === "Việt Nam" ? [{ value: "VN", text: "Việt Nam" }] : []));
    return {
      m1: cell("text"), m2: cell("text", { inputType: "date" }), m3: cell("text"),
      m4: cell("dropdown", { choices: [{ value: "NAM", text: "Nam" }, { value: "NU", text: "Nữ" }] }),
      m5: quocTich, m6: cell("text"),
    };
  });
  const nganh = { isVisible: true, getType: () => "matrixdynamic",
    columns: [{ name: "c1", title: "Tên ngành nghề" }, { name: "c3", title: "Mã ngành" }] };
  assert.equal(isMemberMatrix(nganh), false, "bảng ngành không phải bảng thành viên");
  assert.equal(await findMemberMatrix({ getAllQuestions: () => [nganh, q] }), q);
  const from = {
    hoTen: ["citizenName"], ngaySinh: ["citizenDateOfBirth"], gioiTinh: ["citizengioiTinh"],
    soDinhDanh: ["citizenIdentity"], noiThuongTru: ["citizenDiachi", "citizenxa", "citizenTinh"],
  };
  const res = await setMemberMatrix({}, q, [
    { chuHo: true, hoTen: "TÊN BE GỬI", noiOHienTai: "Số 2 ngõ B" },
    { hoTen: "TRẦN VĂN BÌNH", ngaySinh: "02/03/1988", soDinhDanh: "001088000033", gioiTinh: "Nam", quocTich: "Việt Nam" },
  ], from);
  assert.deepEqual(res, { ok: true });
  const [head, member] = rows.map((r) => r.cells);
  assert.equal(head.m1.value, "LÊ THỊ HOA", "chữ trên phần chủ hộ của biểu mẫu thắng giá trị BE");
  assert.equal(head.m2.value, "1990-06-05");
  assert.equal(head.m3.value, "001190000011");
  assert.equal(head.m4.value, "NU");
  assert.equal(head.m6.value, "Xóm A, Phường Hoa Lư");
  assert.equal(member.m1.value, "TRẦN VĂN BÌNH");
  assert.equal(member.m2.value, "1988-03-02", "ô ngày (flatpickr) lưu ISO");
  assert.equal(member.m4.value, "NAM");
  assert.equal(member.m5.value, "VN");
  assert.deepEqual(member.m5.typed, ["Việt Nam", ""], "gõ tìm theo chữ rồi xoá chữ đã gõ");
});

test("bảng thành viên: ô ngày chữ thường ghi dd/mm/yyyy, bỏ dòng thừa, thiếu ô bắt buộc thì báo theo dòng", async () => {
  const { setMemberMatrix } = loadMembers({});
  const { q, rows } = memberMatrix(() => ({
    m1: cell("text"), m2: cell("text"), m3: cell("text"), m4: cell("dropdown", { choices: [] }), m5: cell("text"),
    m6: cell("text"),
  }), 3);
  const res = await setMemberMatrix({}, q, [
    { chuHo: true, hoTen: "LÊ THỊ HOA", ngaySinh: "05/06/1990", soDinhDanh: "001190000011" },
    { hoTen: "TRẦN VĂN BÌNH", soDinhDanh: "001088000033" },
  ], { hoTen: ["citizenName"] });
  assert.equal(rows.length, 2, "điền lại ít dòng hơn thì bỏ dòng thừa");
  assert.equal(rows[0].cells.m1.value, "LÊ THỊ HOA", "phần chủ hộ trên biểu mẫu trống → dùng giá trị BE");
  assert.equal(rows[0].cells.m2.value, "05/06/1990");
  assert.deepEqual(res, { ok: false, reason: "matrix-rows:2(ngaySinh:missing)" });
});

test("setOne: bảng thành viên không thấy theo tên thì tìm theo tiêu đề cột, trả tên câu hỏi thật", () => {
  const start = src.indexOf("async function setOne(");
  const body = src.slice(start, src.indexOf("async function setArea(", start));
  assert.match(body, /findQuestion\(survey, field\.name\) \|\|\s*\(field\.matrix === "members" \? await findMemberMatrix\(survey\) : null\)/);
  assert.match(body, /setMemberMatrix\(survey, q, field\.value, field\.chuHoFrom\)\), qName: q\.name/);
  assert.ok(body.indexOf('field.matrix === "members") {') < body.indexOf("return setMatrix(q, field.value)"),
    "bảng thành viên rẽ trước bảng ngành");
});
