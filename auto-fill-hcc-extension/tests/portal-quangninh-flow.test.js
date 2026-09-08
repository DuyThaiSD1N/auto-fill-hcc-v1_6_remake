// Chặng cổng tỉnh: bấm "Nộp hồ sơ" ĐÚNG DÒNG rồi chọn ĐÚNG chi nhánh tiếp nhận.
//
// Hai chỗ này sai là hồ sơ đi lạc cơ quan mà không ai kê khai điều đó, nên test chạy thẳng logic
// chọn thay vì chỉ soát chuỗi nguồn.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const source = fs.readFileSync(path.join(root, "content", "portal-quangninh.js"), "utf8");

/** Cắt một hàm khai báo ở mức 2 dấu cách thụt đầu dòng ra khỏi IIFE để chạy riêng. */
function sliceFn(name) {
  const start = source.indexOf(`function ${name}(`);
  assert.ok(start >= 0, `Không tìm thấy hàm ${name}`);
  const end = source.indexOf("\n  }\n", start);
  assert.ok(end > start, `Không tách được thân hàm ${name}`);
  return source.slice(start, end + 4);
}

const sandbox = { console: { log() {}, warn() {} }, submitButtons: () => [] };
vm.runInNewContext(`
  ${sliceFn("fold")}
  ${sliceFn("rowOf")}
  ${sliceFn("matchOption")}
  ${sliceFn("rowIndexOf")}
  ${sliceFn("pickSubmitButton")}
  const log = () => {};
  globalThis.fold = fold;
  globalThis.matchOption = matchOption;
  globalThis.pickSubmitButton = pickSubmitButton;
`, sandbox);

function fakeRow(text) {
  const row = { textContent: text };
  const button = {
    textContent: "Nộp hồ sơ",
    closest: (selector) => (selector === "tr" ? row : null),
    parentElement: row,
    row,
  };
  return button;
}

const DONG_BANG = "Đăng ký biến động quyền sử dụng đất ... - Đối với cá nhân, cộng đồng dân cư";
const MIEN_NUI = "[Đặc thù] Đăng ký biến động quyền sử dụng đất ... - Miền núi, hải đảo";

// 1. Khớp theo CHỮ trong dòng — đúng biến thể "Miền núi, hải đảo" dù nó không đứng đầu bảng.
let buttons = [fakeRow(DONG_BANG), fakeRow(MIEN_NUI), fakeRow("Thủ tục khác")];
sandbox.submitButtons = () => buttons;
assert.equal(
  sandbox.pickSubmitButton({ rowIncludes: "Miền núi, hải đảo", rowIndex: 2 }).row.textContent,
  MIEN_NUI,
);

// 2. Chữ khớp thì THẮNG vị trí: bảng đổi thứ tự thì vẫn ra đúng dòng, không bám số thứ tự cũ.
buttons = [fakeRow(MIEN_NUI), fakeRow(DONG_BANG)];
assert.equal(
  sandbox.pickSubmitButton({ rowIncludes: "Miền núi, hải đảo", rowIndex: 2 }).row.textContent,
  MIEN_NUI,
  "Khớp chữ phải thắng rowIndex, nếu không bảng đảo thứ tự là bấm nhầm dòng",
);

// 3. Cổng đổi cách viết nhãn -> rơi về vị trí đã cấu hình.
buttons = [fakeRow(DONG_BANG), fakeRow("Biến thể hai"), fakeRow("Biến thể ba")];
assert.equal(
  sandbox.pickSubmitButton({ rowIncludes: "Miền núi, hải đảo", rowIndex: 2 }).row.textContent,
  "Biến thể hai",
);

// 4. Không cấu hình gì -> lấy dòng ĐẦU (cùng quy ước "mục đầu như default" của agency-select.js).
assert.equal(sandbox.pickSubmitButton({}).row.textContent, DONG_BANG);

// 5. rowIndex vượt số dòng -> KHÔNG bấm gì. Rơi về dòng đầu là mở nhầm biến thể thủ tục (đồng
// bằng thay vì miền núi, "không phải nộp" thay vì "phải nộp nghĩa vụ tài chính").
assert.equal(
  sandbox.pickSubmitButton({ rowIndex: 99 }), null,
  "Bảng thiếu dòng thì phải nhường cán bộ bấm tay, tuyệt đối không rơi về dòng đầu",
);

// 5b. Dòng thứ 6 (1.115840) — chốt theo vị trí, không dùng chữ.
buttons = Array.from({ length: 8 }, (_, i) => fakeRow(`Biến thể ${i + 1} - Miền núi, hải đảo`));
sandbox.submitButtons = () => buttons;
assert.equal(sandbox.pickSubmitButton({ rowIndex: 6 }).row.textContent, "Biến thể 6 - Miền núi, hải đảo");
assert.equal(sandbox.pickSubmitButton({ rowIndex: 4 }).row.textContent, "Biến thể 4 - Miền núi, hải đảo");
// Và đây là lý do 1.115840 KHÔNG được khai rowIncludes: nhiều dòng cùng chứa cụm đó, khớp chữ sẽ
// nuốt mất vị trí và bấm trúng dòng 1.
assert.equal(
  sandbox.pickSubmitButton({ rowIncludes: "Miền núi, hải đảo", rowIndex: 6 }).row.textContent,
  "Biến thể 1 - Miền núi, hải đảo",
);

// 6. Bảng chưa dựng -> null để nhịp watcher sau thử lại, KHÔNG bấm bừa.
sandbox.submitButtons = () => [];
assert.equal(sandbox.pickSubmitButton({ rowIncludes: "Miền núi, hải đảo" }), null);

// ---------- chọn chi nhánh trong modal "Thông tin chung" ----------
const options = [
  "Chi nhánh Văn phòng đăng ký đất đai số 7 Tiên Yên",
  "Chi nhánh Văn phòng đăng ký đất đai số 8 Ba Chẽ",
  "Chi nhánh Văn phòng đăng ký đất đai số 1 Hạ Long",
  "Chi nhánh Văn phòng đăng ký đất đai số 12 Cô Tô",
  "Chi nhánh Văn phòng đăng ký đất đai số 11 Hải Hà",
].map((text) => ({ textContent: text }));

const picked = sandbox.matchOption(options, "Chi nhánh Văn phòng đăng ký đất đai số 12 Cô Tô");
assert.equal(picked.textContent, "Chi nhánh Văn phòng đăng ký đất đai số 12 Cô Tô");

// "số 12" KHÔNG được dính vào "số 1": khớp theo cả chuỗi nên tiền tố không nuốt nhau.
assert.equal(
  sandbox.matchOption(options, "Chi nhánh Văn phòng đăng ký đất đai số 1 Hạ Long").textContent,
  "Chi nhánh Văn phòng đăng ký đất đai số 1 Hạ Long",
);

// Cổng thêm khoảng trắng/xuống dòng trong option -> fold vẫn khớp.
assert.equal(
  sandbox.matchOption(
    [{ textContent: "  Chi nhánh Văn phòng đăng ký\n đất đai số 12 Cô Tô " }],
    "Chi nhánh Văn phòng đăng ký đất đai số 12 Cô Tô",
  ) !== null,
  true,
);

// Không có chi nhánh cần tìm -> null, để engine dừng và nhường cán bộ chọn tay.
assert.equal(sandbox.matchOption(options, "Chi nhánh Văn phòng đăng ký đất đai số 99 Không Có"), null);

// ---------- bất biến an toàn ----------
// Bỏ chú thích rồi mới soát: tên địa bàn được phép xuất hiện để giải thích, chỉ không được nằm
// trong CODE — nằm trong code là engine chỉ chạy đúng cho một huyện.
// Dùng regex theo dòng cho gọn: bỏ dòng chú thích // rồi bỏ khối /* */.
const code = source.replace(/^\s*\/\/.*$/gm, "").replace(/\/\*[\s\S]*?\*\//g, "");
assert.ok(
  !/Cô Tô|Miền núi/.test(code),
  "Engine không được hard-code địa bàn — cấu hình phải nằm ở ke_khai_links.json",
);

const agencyStage = source.slice(
  source.indexOf("async function agencyStage("),
  source.indexOf("// ---------- điều phối ----------"),
);
assert.ok(
  agencyStage.indexOf("await stop();") < agencyStage.indexOf("confirmButton(modal)"),
  "Không chọn được cơ quan thì phải DỪNG trước khi tới nhánh bấm Xác nhận",
);
assert.match(
  agencyStage,
  /if \(wanted && !await pickAgency\(modal, wanted\)\)/,
  "Phải chọn được cơ quan rồi mới được bấm Xác nhận",
);
// Thủ tục cấp xã khai flow KHÔNG có `agency` (modal không phải chọn chi nhánh). `wanted` rỗng thì
// bỏ qua pickAgency và đi thẳng tới điền ô còn trống — bỏ mất chữ `wanted &&` là engine coi chuỗi
// rỗng như một cơ quan cần tìm, không thấy rồi dừng hẳn.
assert.match(
  agencyStage,
  /const wanted = String\(flow\.agency \|\| ""\)\.trim\(\);/,
  "flow thiếu agency phải coi là KHÔNG cần chọn chi nhánh, không phải lỗi",
);
assert.ok(
  agencyStage.includes("const picked = [wanted, ...chosen].filter(Boolean);"),
  "Toast tổng kết phải bỏ được phần cơ quan rỗng",
);

// Chuỗi select PHỤ THUỘC: chọn Cơ quan thực hiện xong cổng mới nạp "Đơn vị tiếp nhận".
assert.ok(
  agencyStage.indexOf("await fillDependentCombos(modal)") < agencyStage.indexOf("confirmButton(modal)"),
  'Phải điền các ô phụ thuộc TRƯỚC khi bấm Xác nhận, nếu không hồ sơ thiếu "Đơn vị tiếp nhận"',
);
assert.ok(
  agencyStage.indexOf("if (failed)") < agencyStage.indexOf("realClick(confirm)"),
  "Ô đặt không được thì phải dừng trước nhánh bấm Xác nhận",
);

const dependent = source.slice(
  source.indexOf("async function fillDependentCombos("),
  source.indexOf("function confirmButton("),
);
assert.match(
  dependent,
  /if \(!control\(\) \|\| !isPlaceholder\(control\(\)\)\) continue;/,
  "Ô đã có giá trị thì không được ghi đè — cổng tự điền sẵn theo mã trên URL",
);
assert.match(
  dependent,
  /await waitFor\(\(\) => optionNodes\(dropdownPanel\(\) \|\| panel\)\[0\], 4000, 200\);/,
  "Danh sách phụ thuộc nạp bằng API -> phải CHỜ có lựa chọn, không đọc lúc còn rỗng",
);
// Ô rỗng hẳn = tuỳ chọn, không được tính là hỏng (nếu không mọi hồ sơ đều bị chặn bắt bấm tay);
// ô có lựa chọn mà đặt không được mới là hỏng.
const emptyBranch = dependent.indexOf("không có lựa chọn nào");
const failBranch = dependent.indexOf("if (ok) chosen.push(label); else failed += 1;");
assert.ok(emptyBranch > 0 && failBranch > emptyBranch);
assert.ok(
  !/không có lựa chọn nào[\s\S]{0,200}failed \+= 1;/.test(dependent),
  "Ô không có lựa chọn nào KHÔNG được tính là hỏng",
);

// Nghỉ giữa các bước: bấm liền tay là đọc trúng danh sách cũ/rỗng.
assert.match(source, /const STEP_PAUSE_MS = 500;/, "Thiếu nhịp nghỉ giữa các bước chọn");
assert.match(
  source,
  /if \(loginBlocked\(\)\) return void await park\(arm\);/,
  "Cổng tỉnh chặn đăng nhập thì phải đỗ lại như chặng login của cổng quốc gia",
);
assert.ok(
  source.includes("if (index > count) {") && source.includes("await stop();"),
  "Bảng vẽ xong mà thiếu dòng thì phải dừng và báo, đừng lặng lẽ thử lại mãi",
);
assert.match(
  source,
  /if \(Date\.now\(\) - lastSubmitClickAt < CLICK_COOLDOWN_MS\) return;/,
  'Phải có khoảng nghỉ sau khi bấm "Nộp hồ sơ", nếu không nhịp watcher kế bấm lần hai',
);
assert.ok(
  source.includes('if (String(flow.host || "") !== location.hostname) {'),
  "Chỉ được chạy khi cờ đúng host cổng tỉnh — cổng khác phải đứng ngoài hoàn toàn",
);
// Đứng ngoài phải NÓI LÝ DO: im lặng thì lúc trợ lý không bấm gì, không ai biết vì sao.
for (const reason of ['chưa có cờ', 'không khai provincePortalFlow', 'cờ dành cho host', 'quá hạn']) {
  assert.ok(source.includes(reason), `Thiếu log lý do đứng ngoài: ${reason}`);
}
assert.match(
  source,
  /if \(ctx === undefined\) return;/,
  "Đọc cờ hụt MỘT nhịp không được làm watcher tự tắt vĩnh viễn",
);

// ---------- nạp đúng thứ tự + cấu hình có thật ----------
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));
const js = manifest.content_scripts[0].js;
assert.ok(
  js.indexOf("content/portal-login.js") < js.indexOf("content/portal-quangninh.js"),
  "portal-quangninh.js dùng __HCC_LOGIN__ nên phải nạp sau portal-login.js",
);
assert.ok(
  manifest.content_scripts[0].matches.includes("https://dichvucong.quangninh.gov.vn/*"),
  "Thiếu host cổng tỉnh thì content script không chạy ở đó",
);

const links = JSON.parse(fs.readFileSync(
  path.join(root, "..", "auto-fill-hcc-backend", "app", "procedures", "data", "ke_khai_links.json"),
  "utf8",
)).links;
// Họ thủ tục đặc thù Quảng Ninh: chung engine cổng tỉnh, khác nhau ở DÒNG phải bấm.
const CO_TO = "Chi nhánh Văn phòng đăng ký đất đai số 12 Cô Tô";
const CARD_VP = "Cơ quan thực hiện: Văn phòng Đăng ký đất đai";
// Mặc định của họ này: cấp tỉnh (chỉ chọn Tỉnh) + vào thẻ Văn phòng Đăng ký đất đai + chọn chi
// nhánh Cô Tô. Thủ tục nào lệch thì khai `ward: true` (chọn cả Phường/Xã) hoặc `card: null`
// (lấy thẻ đầu như đa số thủ tục khác).
const QUANG_NINH = [
  {
    key: "dang-ky-bien-dong-dat-dai-quang-ninh",
    code: "1.115835",
    uuid: "019f6567-3744-7003-ab4b-e4fb4ee54bf8",
    flow: { host: "dichvucong.quangninh.gov.vn", rowIncludes: "Miền núi, hải đảo", rowIndex: 2, agency: CO_TO },
  },
  {
    key: "dang-ky-bien-dong-doi-ten-nguoi-su-dung-dat-quang-ninh",
    code: "1.115837",
    uuid: "019f656f-5ba4-739d-a55d-8dd0fe6d167a",
    flow: { host: "dichvucong.quangninh.gov.vn", rowIncludes: "Miền núi, hải đảo", rowIndex: 2, agency: CO_TO },
  },
  {
    // Biện pháp bảo đảm: bảng cổng tỉnh chỉ cần DÒNG ĐẦU, không có biến thể miền núi/hải đảo.
    key: "dang-ky-bien-phap-bao-dam-quang-ninh",
    code: "1.011441",
    uuid: "019d2bfd-7e5d-7318-a451-84198f210213",
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 1, agency: CO_TO },
  },
  {
    key: "xoa-dang-ky-bien-phap-bao-dam-quang-ninh",
    code: "1.011443",
    uuid: "019d2bfd-7e53-77ba-aa3f-086a9b9717ba",
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 1, agency: CO_TO },
  },
  {
    // Thủ tục này có nhiều biến thể CÙNG chứa "Miền núi, hải đảo" (phải/không phải nộp nghĩa vụ
    // tài chính, cá nhân/tổ chức) nên KHÔNG được khớp theo chữ đó — chỉ chốt theo vị trí dòng 6.
    key: "dang-ky-tai-san-gan-lien-thua-dat-da-cap-gcn-quang-ninh",
    code: "1.115840",
    uuid: "019f657a-a27d-76b8-95e8-cb32f91f6fd2",
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 6, agency: CO_TO },
  },
  {
    // Cũng nhiều biến thể cùng chứa "Miền núi, hải đảo" -> chốt theo vị trí, không khớp chữ.
    key: "tach-thua-hop-thua-dat-quang-ninh",
    code: "1.115832",
    uuid: "019f653e-1a95-7398-92e6-0ded98532d7d",
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 4, agency: CO_TO },
  },
  {
    key: "dang-ky-bien-dong-thoa-thuan-thanh-vien-ho-gia-dinh-quang-ninh",
    code: "1.115839",
    uuid: "019f6577-9b7b-72f6-b29d-a51ecb05373a",
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 2, agency: CO_TO },
  },
  {
    key: "thu-hoi-gcn-cap-khong-dung-quy-dinh-quang-ninh",
    code: "1.115855",
    uuid: "019f6935-0ba6-725e-a3fd-22da413b9f86",
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 4, agency: CO_TO },
  },
  {
    key: "dinh-chinh-gcn-da-cap-quang-ninh",
    code: "1.115854",
    uuid: "019f6930-9ba4-76f7-923a-7740c26ced69",
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 4, agency: CO_TO },
  },
  {
    key: "cap-lai-gcn-do-bi-mat-quang-ninh",
    code: "1.115849",
    uuid: "019f68fb-daa9-7444-94c2-987cdd53c1c5",
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 6, agency: CO_TO },
  },
  {
    // Thủ tục này DỪNG ở cổng quốc gia: chọn đúng thẻ Văn phòng Đăng ký đất đai là xong, không bị
    // ném sang cổng tỉnh. Gắn provincePortalFlow cho nó là để engine cổng tỉnh chờ một trang không
    // bao giờ tới.
    key: "cap-doi-gcn-quyen-su-dung-dat-quang-ninh",
    code: "1.115848",
    uuid: "019f68f5-4176-748a-b391-7be76a4a653f",
    flow: null,
  },
  {
    key: "dang-ky-cap-gcn-da-chuyen-quyen-truoc-01-8-2024-quang-ninh",
    code: "1.115852",
    uuid: "019f6925-187c-754c-8308-457a21e513c9",
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 2, agency: CO_TO },
  },
  {
    // Thủ tục cấp XÃ: chọn cả Phường/Xã theo địa chỉ tài khoản rồi bấm "Nộp trực tuyến" của chính
    // phường/xã đó (thẻ đầu, như đa số thủ tục). Modal cổng tỉnh KHÔNG phải chọn chi nhánh VPĐK
    // nên flow cố ý không có `agency`.
    key: "dang-ky-dat-dai-tai-san-gan-lien-lan-dau-quang-ninh",
    code: "1.115820",
    uuid: "019f650b-3d23-7368-83ca-2f9acdc7e4ab",
    ward: true,
    card: null,
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 2 },
  },
  {
    key: "chuyen-muc-dich-su-dung-dat-cap-xa-quang-ninh",
    code: "1.115860",
    uuid: "019f69dd-996e-75b1-a839-07629a53ce98",
    ward: true,
    card: null,
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 2 },
  },
  {
    key: "dang-ky-cap-gcn-toan-bo-dien-tich-dang-su-dung-quang-ninh",
    code: "1.115841",
    uuid: "019f685c-cd7f-7499-b2be-38cd916bcc7e",
    ward: true,
    card: null,
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 2 },
  },
  {
    key: "thu-hoi-gcn-cap-lan-dau-khong-dung-quy-dinh-quang-ninh",
    code: "1.115831",
    uuid: "019f653d-b31e-77ea-b60f-36154676763a",
    ward: true,
    card: null,
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 2 },
  },
  {
    key: "dang-ky-cap-gcn-da-chuyen-quyen-chua-lam-thu-tuc-quang-ninh",
    code: "1.115825",
    uuid: "019f652a-3c7f-71d2-95f8-8358d8e62912",
    ward: true,
    card: null,
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 2 },
  },
  {
    key: "giai-quyet-tranh-chap-dat-dai-cap-xa-quang-ninh",
    code: "1.013967",
    uuid: "019d2bfa-8671-7318-8ef7-15304f36d400",
    ward: true,
    card: null,
    flow: { host: "dichvucong.quangninh.gov.vn", rowIndex: 2 },
  },
];
for (const { key, code, uuid, flow, ward, card } of QUANG_NINH) {
  const entry = links.find((item) => item.key === key);
  assert.ok(entry, `Thiếu thủ tục Quảng Ninh ${code} trong danh mục link`);
  assert.equal(entry.code, code);
  assert.equal(entry.url, `https://dichvucong.gov.vn/thu-tuc-hanh-chinh/${uuid}`);
  // Thủ tục cấp xã phải để trống provinceOnlyAgency — khai true là trợ lý bỏ luôn bước chọn
  // Phường/Xã rồi nộp vào cơ quan cấp tỉnh.
  assert.equal(
    entry.provinceOnlyAgency, ward ? undefined : true,
    `provinceOnlyAgency của ${code} sai — thủ tục cấp xã phải chọn cả Phường/Xã`,
  );
  assert.equal(entry.needsAgencySelect, true);
  // PHẢI autoConfirm: false là submitStage xoá cờ ngay sau khi bấm "Nộp trực tuyến" -> chặng cổng
  // tỉnh không bao giờ chạy.
  assert.equal(entry.autoConfirm, true);
  assert.ok(entry.label.startsWith("Quảng Ninh - "), `Nhãn ${code} phải mở đầu bằng tỉnh`);
  // Nhãn dài (có thủ tục >1000 ký tự) là bình thường, nhưng rỗng/cụt thì popup hiện dòng vô nghĩa.
  assert.ok(entry.label.length > 30, `Nhãn ${code} bị cụt`);
  if (flow) {
    assert.deepEqual(entry.provincePortalFlow, flow, `Cấu hình cổng tỉnh của ${code} sai`);
  } else {
    assert.equal(
      entry.provincePortalFlow, undefined,
      `Thủ tục ${code} dừng ở cổng quốc gia — không được khai provincePortalFlow`,
    );
  }
  // Trang kết quả cổng QG ra nhiều thẻ khác nhau ở cơ quan thực hiện; thiếu chuỗi này là trợ lý
  // lấy thẻ đầu và nộp vào nhầm cơ quan ngay từ bước đầu.
  assert.equal(
    entry.submitCardIncludes, card === null ? undefined : CARD_VP,
    `submitCardIncludes của ${code} sai — thủ tục cấp xã lấy thẻ đầu của chính phường/xã đó`,
  );
}

// Thêm thủ tục Quảng Ninh mà quên khai vào đây là mất luôn lớp kiểm tra cấu hình.
const flows = links.filter((item) => item.provincePortalFlow);
const withFlow = QUANG_NINH.filter((item) => item.flow);
assert.equal(
  flows.length, withFlow.length,
  `Danh mục có ${flows.length} thủ tục đi cổng tỉnh nhưng test chỉ soát ${withFlow.length}: `
  + flows.map((item) => item.key).filter((k) => !withFlow.some((q) => q.key === k)).join(", "),
);

// Cờ này chỉ dành cho họ thủ tục đất đai Quảng Ninh — gắn nhầm sang thủ tục khác là đổi cơ quan
// tiếp nhận của hồ sơ người khác.
for (const item of links.filter((l) => l.submitCardIncludes)) {
  assert.ok(
    QUANG_NINH.some(({ key }) => key === item.key),
    `Thủ tục ${item.key} không thuộc họ Quảng Ninh mà lại khai submitCardIncludes`,
  );
}

// Biện pháp bảo đảm (1.011441) và xoá biện pháp bảo đảm (1.011443) mỗi mã có BA bản dùng chung
// mã + URL. Rất dễ vá nhầm sang bản tỉnh khác nên chốt: chỉ bản Quảng Ninh được mang cấu hình.
for (const code of ["1.011441", "1.011443"]) {
  const family = links.filter((item) => item.code === code);
  assert.equal(family.length, 3, `Mã ${code} phải đủ ba bản Bắc Ninh / Đà Nẵng / Quảng Ninh`);
  for (const item of family) {
    if (item.key.endsWith("-quang-ninh")) continue;
    assert.equal(
      item.provincePortalFlow, undefined,
      `Bản ${item.key} không đi cổng tỉnh Quảng Ninh — không được gắn provincePortalFlow`,
    );
    assert.equal(item.provinceOnlyAgency, undefined, `Bản ${item.key} phải giữ nguyên như cũ`);
  }
}

// `key` là thứ popup dùng để chọn đúng pipeline nên phải DUY NHẤT toàn danh mục. Ngược lại `code`
// và `url` được phép trùng: cùng một mã TTHC quốc gia có nhiều bản theo tỉnh (1.011441 có ba bản).
const keys = links.map((item) => item.key);
assert.equal(new Set(keys).size, keys.length, "Danh mục link có key trùng nhau");

const popup = fs.readFileSync(path.join(root, "popup.js"), "utf8");

assert.match(
  popup,
  /provincePortalFlow: link\.provincePortalFlow \|\| null,/,
  "popup phải gắn cấu hình cổng tỉnh vào cờ, nếu không content script không biết làm gì",
);

console.log("portal quang ninh flow: picks the right row and the right land-registry branch");
