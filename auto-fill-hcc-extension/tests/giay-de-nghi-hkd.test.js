// Tờ khai đăng ký hộ kinh doanh: nút trong panel chỉ của thủ tục dang-ky-kinh-doanh → tab riêng giay-de-nghi-hkd.html.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const read = (f) => fs.readFileSync(path.join(root, f), "utf8").replace(/\r\n/g, "\n");
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const popup = strip(read("popup.js"));
const popupHtml = read("popup.html");
const page = strip(read("giay-de-nghi-hkd.js"));
const html = read("giay-de-nghi-hkd.html");
const lib = require("../lib/giayDeNghiHkd.js");

test("nút tạo tờ khai mặc định ẩn, chỉ hiện ở đăng ký thành lập hộ kinh doanh (HkdOnline + bản DVC quốc gia)", () => {
  assert.match(popupHtml, /<button id="giayDeNghiHkdBtn"[^>]*\bhidden\b/);
  assert.match(popup, /const GIAY_DE_NGHI_HKD_KEY = "dang-ky-kinh-doanh";/);
  assert.match(popup, /const TO_KHAI_HKD_DVCQG_KEY = "dang-ky-thanh-lap-ho-kinh-doanh";/);
  assert.match(popup, /const TO_KHAI_HKD_KEYS = new Set\(\[GIAY_DE_NGHI_HKD_KEY, TO_KHAI_HKD_DVCQG_KEY\]\);/);

  const start = popup.indexOf("function applyFormUI()");
  const line = popup.slice(start).match(/giayDeNghiHkdBtn\.hidden = (.+);/);
  assert.ok(line, "applyFormUI phải bật/tắt nút theo thủ tục");

  const keys = new Set(["dang-ky-kinh-doanh", "dang-ky-thanh-lap-ho-kinh-doanh"]);
  const hiddenFor = (key) => vm.runInNewContext(line[1], { cfg: { key }, TO_KHAI_HKD_KEYS: keys });
  assert.equal(hiddenFor("dang-ky-kinh-doanh"), false);
  assert.equal(hiddenFor("dang-ky-thanh-lap-ho-kinh-doanh"), false);
  for (const key of ["dang-ky-thay-doi-noi-dung-ho-kinh-doanh", "cham-dut-hoat-dong-ho-kinh-doanh", "tam-ngung-kinh-doanh",
    "cap-lai-cap-doi-gcn-ho-kinh-doanh", "khai-sinh", undefined]) {
    assert.equal(hiddenFor(key), true, `không được hiện ở ${key}`);
  }
});

test("bấm nút mở tab riêng của extension, kèm thủ tục đang chọn", () => {
  const click = popup.slice(popup.indexOf("giayDeNghiHkdBtn?.addEventListener(\"click\""), popup.indexOf("const toKhaiHkdNote"));
  assert.match(click, /TO_KHAI_HKD_KEYS\.has\(currentConfig\(\)\?\.key\) \? currentConfig\(\)\.key : GIAY_DE_NGHI_HKD_KEY/);
  assert.match(click, /chrome\.tabs\.create\(\{ url: chrome\.runtime\.getURL\(`giay-de-nghi-hkd\.html\?thuTuc=\$\{encodeURIComponent\(key\)\}`\) \}\)/);
});

test("trang nạp đủ config → auth → client → lib trước script của trang", () => {
  const order = ["api/config.js", "api/auth.js", "api/client.js", "lib/giayDeNghiHkd.js", "giay-de-nghi-hkd.js"]
    .map((f) => html.indexOf(`<script src="${f}"></script>`));
  assert.ok(order.every((i) => i > 0), "thiếu script");
  assert.deepEqual([...order].sort((a, b) => a - b), order, "sai thứ tự nạp");
});

test("trang extension không có script nội tuyến (CSP của MV3 chặn)", () => {
  assert.doesNotMatch(html, /<script(?![^>]*\bsrc=)[^>]*>/);
  assert.doesNotMatch(html, /\son[a-z]+="/);
});

test("file nhị phân không đi qua backendFetch (nó đọc res.text() làm hỏng Word/PDF)", () => {
  const fn = page.slice(page.indexOf("async function renderFile"), page.indexOf("function handleError"));
  assert.match(fn, /fetch\(`\$\{activeBackendBase\(\)\}\$\{API\}\/render`/);
  assert.match(fn, /await res\.blob\(\)/);
  assert.doesNotMatch(fn, /apiCall|backendFetch/);
  assert.match(fn, /res\.status === 401[\s\S]*apiJson\("\/auth\/me"\)[\s\S]*res = await send\(\)/, "token hết hạn thì làm mới rồi gửi lại");
});

test("không ghi dữ liệu người dân vào storage", () => {
  assert.doesNotMatch(page, /localStorage|sessionStorage|storage\.local|indexedDB/);
});

test("trả lời đang bận để tự cập nhật không đóng mất tab đang soạn", () => {
  assert.match(page, /msg\?\.action !== "hccTabDangLamViec"/);
  assert.match(page, /sendResponse\(\{ coPanel: busy/);
});

test("tải mẫu trống gửi rỗng, không gửi dữ liệu đang gõ", () => {
  const fn = page.slice(page.indexOf("async function downloadBlank"), page.indexOf("async function printForm"));
  assert.match(fn, /renderFile\("docx", \{\}\)/);
  assert.doesNotMatch(fn, /validateAll|readForm/);
});

test("in và tải đều kiểm tra ô nhập trước; bảng đang ẩn không chặn", () => {
  for (const name of ["async function download(", "async function printForm("]) {
    const fn = page.slice(page.indexOf(name));
    assert.match(fn.slice(0, 120), /if \(!validateAll\(\)\) return;/, name);
  }
  assert.match(page.slice(page.indexOf("function validateAll")), /input\.closest\("\[hidden\]"\)\) return;/);
});

// Hai ca dưới so với file BE: chỉ chạy được trong monorepo; repo extension riêng (CI thai_dev) không có thư mục BE.
const BACKEND_FILL = path.join(root, "../auto-fill-hcc-backend/app/pipelines/dang_ky_kinh_doanh/giay_de_nghi/fill.py");
const noBackend = !fs.existsSync(BACKEND_FILL) && "không có thư mục auto-fill-hcc-backend cạnh extension";

test("mỗi ô dữ liệu của form khớp một trường BE", { skip: noBackend }, () => {
  const fields = [...html.matchAll(/data-f="([^"]+)"/g)].map((m) => m[1]);
  const backend = fs.readFileSync(BACKEND_FILL, "utf8");
  const form = backend.slice(backend.indexOf("class GiayDeNghi"));
  for (const field of fields) {
    assert.match(form, new RegExp(`^    ${field.split(".")[0]}:`, "m"), field);
  }
  assert.ok(fields.length >= 30);
});

test("giới hạn độ dài ô không vượt giới hạn BE (vượt là 422 khi xem trước)", { skip: noBackend }, () => {
  const backend = fs.readFileSync(BACKEND_FILL, "utf8");
  const form = backend.slice(backend.indexOf("class GiayDeNghi"));
  const limit = (name) => Number(new RegExp(`^    ${name}: str = Field\\(default="", max_length=(\\d+)\\)`, "m").exec(form)?.[1]);
  let checked = 0;
  for (const m of html.matchAll(/data-f="([A-Za-z]+)"[^>]*maxlength="(\d+)"/g)) {
    if (/^ngay/.test(m[1])) continue; // ô ngày BE chặn bằng pattern dd/mm/yyyy, không bằng độ dài
    assert.ok(Number(m[2]) <= limit(m[1]), `${m[1]}: ${m[2]} > ${limit(m[1])}`);
    checked += 1;
  }
  assert.ok(checked >= 15);
});

// ── Phần thuần ──

test("chuẩn hoá ngày", () => {
  assert.equal(lib.chuanHoaNgay("5/9/1990"), "05/09/1990");
  assert.equal(lib.chuanHoaNgay("05-09-1990"), "05/09/1990");
  assert.equal(lib.chuanHoaNgay(" 5.9.1990 "), "05/09/1990");
  assert.equal(lib.chuanHoaNgay("abc"), "abc");
});

test("kiểm tra ngày", () => {
  assert.equal(lib.loiNgay(""), "");
  assert.equal(lib.loiNgay("29/02/2024"), "");
  assert.match(lib.loiNgay("29/02/2023"), /ngày\/tháng\/năm/);
  assert.match(lib.loiNgay("31/04/2020"), /ngày\/tháng\/năm/);
  assert.match(lib.loiNgay("01/01/1800"), /Năm/);
  assert.equal(lib.loiNgay("01/01/2099"), "", "ngày bắt đầu hoạt động được ở tương lai");
  assert.match(lib.loiNgay("01/01/2099", { quaKhu: true }), /tương lai/);
});

test("số định danh đúng 12 số, bỏ cách và chấm", () => {
  assert.equal(lib.chuanHoaSoDinhDanh("027 185.001-234"), "027185001234");
  assert.equal(lib.loiSoDinhDanh("027185001234"), "");
  assert.equal(lib.loiSoDinhDanh(""), "");
  assert.ok(lib.loiSoDinhDanh("123456789"));
  assert.ok(lib.loiSoDinhDanh("02718500123A"));
});

test("điện thoại, thư điện tử, mã ngành, lao động", () => {
  assert.equal(lib.loiDienThoai("0912 345 678"), "");
  assert.equal(lib.loiDienThoai("+84912345678"), "");
  assert.equal(lib.loiDienThoai("(0222) 123.456"), "");
  assert.ok(lib.loiDienThoai("abc"));
  assert.ok(lib.loiDienThoai("123"));
  assert.equal(lib.loiEmail("a.b@example.vn"), "");
  assert.ok(lib.loiEmail("a@b"));
  assert.equal(lib.loiMaNganh("4721"), "");
  assert.equal(lib.loiMaNganh(""), "", "ngành khác không cần mã");
  assert.ok(lib.loiMaNganh("47211"));
  assert.equal(lib.loiLaoDong("12"), "");
  assert.ok(lib.loiLaoDong("ba"));
});

test("định dạng tiền", () => {
  assert.equal(lib.dinhDangTien("150000000"), "150.000.000");
  assert.equal(lib.dinhDangTien("150.000.000 đồng"), "150.000.000");
  assert.equal(lib.dinhDangTien("007"), "7");
  assert.equal(lib.dinhDangTien(""), "");
});

test("đọc số tiền bằng chữ", () => {
  const cases = {
    0: "Không đồng",
    5: "Năm đồng",
    10: "Mười đồng",
    11: "Mười một đồng",
    15: "Mười lăm đồng",
    20: "Hai mươi đồng",
    21: "Hai mươi mốt đồng",
    24: "Hai mươi bốn đồng",
    25: "Hai mươi lăm đồng",
    100: "Một trăm đồng",
    101: "Một trăm linh một đồng",
    105: "Một trăm linh năm đồng",
    110: "Một trăm mười đồng",
    115: "Một trăm mười lăm đồng",
    121: "Một trăm hai mươi mốt đồng",
    1000: "Một nghìn đồng",
    1005: "Một nghìn không trăm linh năm đồng",
    1010: "Một nghìn không trăm mười đồng",
    1100: "Một nghìn một trăm đồng",
    10500: "Mười nghìn năm trăm đồng",
    1000000: "Một triệu đồng",
    1000005: "Một triệu không trăm linh năm đồng",
    1005000: "Một triệu không trăm linh năm nghìn đồng",
    1500000: "Một triệu năm trăm nghìn đồng",
    50000000: "Năm mươi triệu đồng",
    150000000: "Một trăm năm mươi triệu đồng",
    1000000000: "Một tỷ đồng",
    1000000005: "Một tỷ không trăm linh năm đồng",
    1500000000: "Một tỷ năm trăm triệu đồng",
    2005000000: "Hai tỷ không trăm linh năm triệu đồng",
    1000000000000: "Một nghìn tỷ đồng",
  };
  for (const [number, words] of Object.entries(cases)) {
    assert.equal(lib.docTienBangChu(number), words, number);
  }
  assert.equal(lib.docTienBangChu("150.000.000"), "Một trăm năm mươi triệu đồng");
  assert.equal(lib.docTienBangChu(""), "");
  assert.equal(lib.docTienBangChu("9".repeat(16)), "", "quá dài thì để cán bộ tự ghi, không đọc sai");
});

test("dòng vốn trên giấy", () => {
  assert.equal(lib.dongVon("150000000", "Một trăm năm mươi triệu đồng"), "150.000.000 đồng (Một trăm năm mươi triệu đồng)");
  assert.equal(lib.dongVon("150000000", ""), "150.000.000 đồng");
  assert.equal(lib.dongVon("", "Theo thỏa thuận"), "Theo thỏa thuận");
  assert.equal(lib.dongVon("", ""), "");
});

test("tìm ngành theo mã: chỉ mã bắt đầu bằng số đã gõ, xếp theo mã; không tìm theo tên", () => {
  const dm = [
    { ma: "5610", ten: "Nhà hàng và các dịch vụ ăn uống phục vụ lưu động" },
    { ma: "4722", ten: "Bán lẻ thực phẩm trong các cửa hàng chuyên doanh" },
    { ma: "4721", ten: "Bán lẻ lương thực trong các cửa hàng chuyên doanh" },
    { ma: "1047", ten: "Sản xuất có 47 trong tên" },
  ];
  assert.deepEqual(lib.timTheoMa(dm, "47").map((x) => x.ma), ["4721", "4722"]);
  assert.deepEqual(lib.timTheoMa(dm, " 4721 ").map((x) => x.ma), ["4721"]);
  assert.deepEqual(lib.timTheoMa(dm, "4").map((x) => x.ma), ["4721", "4722"]);
  assert.deepEqual(lib.timTheoMa(dm, ""), []);
  assert.deepEqual(lib.timTheoMa(dm, "ban le"), []);
  assert.deepEqual(lib.timTheoMa(dm, "47211"), []);
  assert.equal(lib.timTheoMa(Array.from({ length: 50 }, (_, i) => ({ ma: `47${String(i).padStart(2, "0")}`, ten: "x" })), "47").length, 30);
});

test("ô Mã ngành là ô tìm, đứng trước ô Tên ngành; bỏ gợi ý theo tên", () => {
  const row = page.slice(page.indexOf("function renderNganhRow("), page.indexOf("function addNganh("));
  assert.ok(row.indexOf('data-col="ma"') < row.indexOf('data-col="ten"'));
  assert.match(row, /role="combobox"/);
  assert.doesNotMatch(row, /list="nganhGoiY"/);
  assert.doesNotMatch(html, /nganhGoiY/);
  assert.match(page, /lib\.timTheoMa\(state\.config\.nganh, input\.value\)/);
});

// ── Auto Fill điền cổng thẳng từ tờ khai đã nhập, không OCR ──

test("chỉ chuyển cho Auto Fill khi tờ khai có nội dung thật", () => {
  assert.equal(lib.coNoiDung(null), false);
  assert.equal(lib.coNoiDung({ diaDanh: "Vũ Ninh", ngayLap: "10/11/2026", kinhGui: "UBND phường Vũ Ninh", nganh: [{ ten: "", ma: "" }] }), false);
  assert.equal(lib.coNoiDung({ hoTen: "TRẦN VĂN AN" }), true);
  assert.equal(lib.coNoiDung({ truSo: { chiTiet: "", xa: "Phường Vũ Ninh", tinh: "" } }), true);
  assert.equal(lib.coNoiDung({ nganh: [{ ten: "", ma: "4721" }] }), true);
});

test("tên tờ khai hiện trên panel", () => {
  assert.equal(lib.tenToKhai({ tenViet: "TẠP HÓA AN", hoTen: "TRẦN VĂN AN" }), "TẠP HÓA AN (chủ hộ TRẦN VĂN AN)");
  assert.equal(lib.tenToKhai({ hoTen: "TRẦN VĂN AN" }), "chủ hộ TRẦN VĂN AN");
  assert.equal(lib.tenToKhai({}), "chưa có tên");
  // Bản DVC quốc gia: kèm người nộp đã chọn để cán bộ thấy trước khi điền.
  assert.equal(lib.tenToKhai({ tenViet: "TẠP HÓA AN", hoTen: "TRẦN VĂN AN", nguoiNop: { loai: "uy_quyen" } }),
    "TẠP HÓA AN (chủ hộ TRẦN VĂN AN) · người nộp: Người được ủy quyền");
  assert.equal(lib.tenToKhai({ hoTen: "TRẦN VĂN AN", nguoiNop: { loai: "chu_ho" } }),
    "chủ hộ TRẦN VĂN AN · người nộp: Người có thẩm quyền ký giấy đề nghị");
  assert.equal(lib.tenToKhai({ hoTen: "TRẦN VĂN AN", nguoiNop: { loai: "" } }), "chủ hộ TRẦN VĂN AN");
});

// ── Bản Cổng DVC quốc gia (dang-ky-thanh-lap-ho-kinh-doanh): hỏi người nộp trước khi kê khai ──

test("tab biết đang soạn cho thủ tục nào qua ?thuTuc; thiếu / lạ là bản HkdOnline", () => {
  assert.equal(lib.thuTucTuTrang("?thuTuc=dang-ky-thanh-lap-ho-kinh-doanh"), "dang-ky-thanh-lap-ho-kinh-doanh");
  assert.equal(lib.thuTucTuTrang("?thuTuc=dang-ky-kinh-doanh"), "dang-ky-kinh-doanh");
  assert.equal(lib.thuTucTuTrang(""), "dang-ky-kinh-doanh");
  assert.equal(lib.thuTucTuTrang("?thuTuc=khai-sinh"), "dang-ky-kinh-doanh");
  // Mỗi thủ tục một khoá storage, khoá HkdOnline giữ tên cũ.
  assert.equal(lib.khoaAutoFill("dang-ky-kinh-doanh"), "hccToKhaiHkd");
  assert.equal(lib.khoaAutoFill("dang-ky-thanh-lap-ho-kinh-doanh"), "hccToKhaiHkdDvcqg");
});

test("tờ khai chỉ dùng cho đúng thủ tục; bản DVC quốc gia phải đã chọn người nộp", () => {
  const dvcqg = "dang-ky-thanh-lap-ho-kinh-doanh";
  const cu = { data: { hoTen: "TRẦN VĂN AN" }, tabId: 1 };                       // bản ghi trước khi có bản DVCQG
  assert.equal(lib.dungChoThuTuc(cu, "dang-ky-kinh-doanh"), true);
  assert.equal(lib.dungChoThuTuc(cu, dvcqg), false);
  const moi = { data: { hoTen: "TRẦN VĂN AN", nguoiNop: { loai: "chu_ho" } }, thuTuc: dvcqg };
  assert.equal(lib.dungChoThuTuc(moi, dvcqg), true);
  assert.equal(lib.dungChoThuTuc(moi, "dang-ky-kinh-doanh"), false);
  assert.equal(lib.dungChoThuTuc({ ...moi, data: { hoTen: "TRẦN VĂN AN", nguoiNop: { loai: "" } } }, dvcqg), false);
  assert.equal(lib.dungChoThuTuc({ thuTuc: dvcqg }, dvcqg), false);
});

test("tab bản DVC quốc gia: câu hỏi người nộp đứng ĐẦU form, chưa chọn thì ẩn phần kê khai", () => {
  const box = html.indexOf('id="nguoiNopBox"');
  assert.ok(box > 0 && box < html.indexOf("Đầu giấy"), "câu hỏi người nộp phải đứng trước phần kê khai");
  assert.match(html, /<section class="panel panel-ask" id="nguoiNopBox" hidden>/);
  assert.match(html, /name="nguoiNop" value="chu_ho"> <b>Người có thẩm quyền ký giấy đề nghị<\/b>/);
  assert.match(html, /name="nguoiNop" value="uy_quyen"> <b>Người được ủy quyền<\/b>/);
  assert.match(html, /<div id="uyQuyenBox" hidden>/);
  for (const nn of ["hoTen", "soDinhDanh", "dienThoai", "email", "noiO.chiTiet", "noiO.xa", "noiO.tinh"]) {
    assert.match(html, new RegExp(`data-nn="${nn.replace(".", "\\.")}"`), nn);
  }
  const css = read("giay-de-nghi-hkd.css");
  assert.match(css, /\.ws-form\[data-hoi-nguoi-nop="true"\] > :not\(#nguoiNopBox\)/);
  const sync = page.slice(page.indexOf("function syncNguoiNop()"), page.indexOf("function readNguoiNop()"));
  assert.match(sync, /if \(!DVCQG\) return;/);
  assert.match(sync, /\$\("uyQuyenBox"\)\.hidden = loai !== "uy_quyen";/);
  assert.match(sync, /\$\("form"\)\.dataset\.hoiNguoiNop = loai \? "false" : "true";/);
  const apply = page.slice(page.indexOf("function applyThuTuc()"), page.indexOf("async function init()"));
  assert.match(apply, /if \(!DVCQG\) return;/);
  assert.match(apply, /\$\("nguoiNopBox"\)\.hidden = false;/);
});

test("tab bản DVC quốc gia: chưa chọn người nộp thì không lưu; người nộp gửi Auto Fill, không in lên giấy", () => {
  const validate = page.slice(page.indexOf("function validateAll()"), page.indexOf("// ── Bảng ngành nghề ──"));
  assert.ok(validate.indexOf("if (DVCQG && !nguoiNopLoai())") < validate.indexOf("let first = null;"));
  assert.match(page.slice(page.indexOf("function readForm()")), /if \(DVCQG\) data\.nguoiNop = readNguoiNop\(\);/);
  const read_ = page.slice(page.indexOf("function readNguoiNop()"), page.indexOf("function validateAll()"));
  assert.match(read_, /if \(loai !== "uy_quyen"\) return out;/);
  const render = page.slice(page.indexOf("async function renderFile"), page.indexOf("function handleError"));
  assert.match(render, /const \{ nguoiNop: _nguoiNop, \.\.\.giay \} = data \|\| \{\};/);
  assert.match(render, /JSON\.stringify\(\{ format, \.\.\.giay \}\)/);
  const save = page.slice(page.indexOf("async function saveForAutoFill(data)"), page.indexOf("function forgetForAutoFill()"));
  assert.match(save, /sessionStore\.set\(\{ \[KHOA\]:/);
  assert.match(save, /thuTuc: THU_TUC/);
  assert.match(page, /const KHOA = lib\.khoaAutoFill\(THU_TUC\);/);
});

test("popup bản DVC quốc gia: nút Quét và nhập dữ liệu gửi tờ khai thay tệp, không tệp thì bỏ đính kèm", () => {
  const start = popup.indexOf("ocrBtn.addEventListener(\"click\"");
  const body = popup.slice(start, popup.indexOf("const fillOutcome = await dispatchFill", start));
  assert.match(body, /if \(!files\.length && !\(await toKhaiHkdForFill\(currentConfig\(\)\)\)\)/);
  assert.match(body, /const toKhai = cfg\.key === TO_KHAI_HKD_DVCQG_KEY \? await toKhaiHkdForFill\(cfg\) : null;/);
  assert.match(body, /if \(toKhai\) options\.giayDeNghi = toKhai\.data;/);
  assert.match(body, /const payloadFiles = toKhai \? \[\] : buildPayloadFiles\(\);/);
  assert.match(body, /api\.process\(\{ procedure: cfg\.key, options, files: payloadFiles \}\)/);
  const attach = popup.slice(popup.indexOf("async function attachAfterFill("), popup.indexOf("const SECOND_PASS_WAIT_MS"));
  assert.match(attach, /if \(!files\.length\) return;/);
  const ui = popup.slice(popup.indexOf("function refreshAttachStepUI()"), popup.indexOf("let pageFormKind"));
  assert.match(ui, /fillAttachBtn\.disabled = \(!files\.length && !toKhaiHkdReady\(cfg\)\)/);
});

test("tab tờ khai chỉ ghi vào storage.session, xoá khi đóng tab hoặc làm lại", () => {
  assert.match(page, /const sessionStore = chrome\.storage\?\.session \|\| null;/);
  assert.doesNotMatch(page, /chrome\.storage\.local/);
  assert.match(page, /window\.addEventListener\("pagehide", forgetForAutoFill\)/);
  const reset = page.slice(page.indexOf("function resetAll()"), page.indexOf("function syncThanhVienBox()"));
  assert.match(reset, /forgetForAutoFill\(\)/);
  const save = page.slice(page.indexOf("async function saveForAutoFill(data)"), page.indexOf("function forgetForAutoFill()"));
  assert.match(save, /tabId: state\.tabId/);
  assert.match(html, /<p class="autofill-state" id="autoFillState"/);
});

test("popup nạp lib tờ khai trước popup.js và có dòng báo điền theo tờ khai", () => {
  const lib_ = popupHtml.indexOf('<script src="lib/giayDeNghiHkd.js"></script>');
  assert.ok(lib_ > 0 && lib_ < popupHtml.indexOf('<script src="popup.js"></script>'));
  assert.match(popupHtml, /<div id="toKhaiHkdNote"[^>]*\bhidden\b/);
  assert.match(popupHtml, /<input id="toKhaiHkdUse" type="checkbox" checked>/);
});

test("điền 8 trang: có tờ khai thì gửi options.giayDeNghi, không gửi tệp, tệp chỉ để đính kèm", () => {
  const start = popup.indexOf("fillAllBtn.addEventListener(\"click\"");
  const body = popup.slice(start, popup.indexOf("const startRes = await sendToContent", start));
  assert.match(body, /const toKhai = await toKhaiHkdForFill\(cfg\);/);
  assert.match(body, /if \(!payloadFiles\.length && !toKhai\)/);
  assert.match(body, /if \(toKhai\) options\.giayDeNghi = toKhai\.data;/);
  assert.match(body, /api\.process\(\{ procedure: cfg\.key, options, files: toKhai \? \[\] : payloadFiles \}\)/);
  assert.match(body, /if \(payloadFiles\.length\) try \{\s*setStatus\("Đang phân tích & phân loại tài liệu đính kèm/);
});

test("chỉ luồng thành lập mới (HkdOnline + bản DVC quốc gia) dùng tờ khai, đúng thủ tục đã soạn; tab đã đóng thì bỏ", () => {
  const fn = popup.slice(popup.indexOf("async function toKhaiHkdForFill(cfg)"), popup.indexOf("toKhaiHkdOpen?.addEventListener"));
  assert.match(fn, /!TO_KHAI_HKD_KEYS\.has\(cfg\?\.key\) \|\| cfg\.businessWorkflow \|\| cfg\.enterprisePortal/);
  assert.match(fn, /toKhaiHkdUse && !toKhaiHkdUse\.checked/);
  assert.match(fn, /await readToKhaiHkd\(cfg\.key\)/);
  const read_ = popup.slice(popup.indexOf("async function readToKhaiHkd("), popup.indexOf("async function renderToKhaiHkdNote()"));
  assert.match(read_, /const storeKey = toKhaiHkdStoreKey\(procedure\);/);
  assert.match(read_, /!toKhaiHkdLib\.dungChoThuTuc\(rec, procedure\)/);
  assert.match(read_, /await chrome\.tabs\.get\(Number\(rec\.tabId\)\)/);
  assert.match(read_, /store\.remove\(storeKey\)/);
  assert.match(popup, /changes\[TO_KHAI_HKD_KEY\] \|\| changes\[TO_KHAI_HKD_DVCQG_STORE_KEY\]/);
});

// ── Nút Lưu: gõ không cập nhật gì, bấm Lưu mới dựng bản xem trước + chuyển cho Auto Fill ──

test("nút Lưu nằm trên đầu trang, trước các nút khác", () => {
  const top = html.slice(html.indexOf('<div class="ws-top-actions">'), html.indexOf("</header>"));
  assert.ok(top.indexOf('id="saveBtn"') > 0 && top.indexOf('id="saveBtn"') < top.indexOf('id="blankWord"'));
});

test("sửa form chỉ đánh dấu chưa lưu, không gọi máy chủ", () => {
  const wire = page.slice(page.indexOf("function wire()"), page.indexOf("async function init()"));
  const events = wire.slice(0, wire.indexOf('$("saveBtn").addEventListener'));
  assert.doesNotMatch(events, /refreshPreview|saveForAutoFill|renderFile/);
  assert.ok((events.match(/markUnsaved\(\)/g) || []).length >= 6, "mọi kiểu sửa phải đánh dấu chưa lưu");
  const mark = page.slice(page.indexOf("function markUnsaved()"), page.indexOf("async function saveAll("));
  assert.doesNotMatch(mark, /refreshPreview|saveForAutoFill|renderFile/);
});

test("Lưu: kiểm ô, ghi cho Auto Fill rồi dựng bản xem trước; Ctrl+S cũng lưu", () => {
  const save = page.slice(page.indexOf("async function saveAll("), page.indexOf("function saveBlob("));
  assert.match(save, /if \(!validateAll\(\)\) return false;/);
  assert.ok(save.indexOf("saveForAutoFill(data)") < save.indexOf("refreshPreview(data)"));
  assert.match(page, /\$\("saveBtn"\)\.addEventListener\("click", \(e\) => void saveAll\(e\.currentTarget\)\)/);
  assert.match(page, /e\.key\.toLowerCase\(\) === "s"/);
});

test("in / tải khi còn thay đổi thì lưu trước", () => {
  for (const fn of ["async function download(", "async function printForm("]) {
    const body = page.slice(page.indexOf(fn), page.indexOf(fn) + 300);
    assert.match(body, /if \(state\.unsaved && !\(await saveAll\(\$\("saveBtn"\), \{ quiet: true \}\)\)\) return;/, fn);
  }
});

test("giờ lưu dạng HH:MM", () => {
  assert.equal(lib.gioPhut(new Date(2026, 10, 10, 9, 5).getTime()), "09:05");
});
