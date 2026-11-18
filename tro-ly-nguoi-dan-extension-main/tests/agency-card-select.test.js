// Trang kết quả DVCQG ra NHIỀU thẻ "Nộp trực tuyến", thẻ đầu là cấp Sở. Thủ tục khai
// agencyCardIncludes (ATTP Bộ Y tế: "Cơ quan thực hiện: UBND") phải bấm ĐÚNG thẻ đó, và khi không
// thấy thì DỪNG — không lùi về thẻ đầu (thẻ đầu chính là thẻ sai).
// Chạy THẬT các hàm của portal-dvc.js trong vm với cây DOM giả.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const strip = (s) => s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const dvc = fs.readFileSync(path.join(root, "content/portal-dvc.js"), "utf8");

const fold = (s) => String(s || "")
  .replace(/Đ/g, "D").replace(/đ/g, "d")
  .normalize("NFD").replace(/[̀-ͯ]/g, "")
  .replace(/\s+/g, " ").trim().toLowerCase();

// ── Cây DOM giả: đủ parentElement / textContent / querySelectorAll("button, a") ──
class Node {
  constructor(text = "", children = [], isButton = false) {
    this.ownText = text;
    this.children = children;
    this.isButton = isButton;
    this.parentElement = null;
    this.clicked = false;
    children.forEach((c) => { c.parentElement = this; });
  }
  get textContent() {
    return [this.ownText, ...this.children.map((c) => c.textContent)].join(" ");
  }
  querySelectorAll() {
    const out = [];
    const walk = (n) => n.children.forEach((c) => { if (c.isButton) out.push(c); walk(c); });
    walk(this);
    return out;
  }
  scrollIntoView() {}
}
const btn = () => new Node("Nộp trực tuyến", [], true);
// Một thẻ kết quả: tiêu đề thủ tục + dòng cơ quan + nút, bọc thêm một lớp div như React.
const card = (agency) => {
  const b = btn();
  return { node: new Node("", [new Node("", [
    new Node("Cấp giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm"),
    new Node(`Cơ quan thực hiện: ${agency}`),
    b,
  ])]), button: b };
};

function load(documentRoot) {
  const start = dvc.indexOf("const nopTrucTuyenButtons");
  const end = dvc.indexOf("async function selectAgency", start);
  assert.ok(start >= 0 && end > start, "không cắt được hàm chọn thẻ");
  const ctx = {
    fold,
    isVisible: () => true,
    sleep: async () => {},
    waitFor: async (fn) => fn(),
    clickLikeUser: (el) => { el.clicked = true; },
    document: documentRoot,
  };
  vm.createContext(ctx);
  vm.runInContext(
    dvc.slice(start, end) + "\nthis.clickNopTrucTuyenByCard = clickNopTrucTuyenByCard;"
      + "\nthis.resultCard = resultCard;",
    ctx,
  );
  return ctx;
}

test("thẻ Sở đứng đầu, thẻ UBND phía sau → bấm thẻ UBND", async () => {
  const so = card("Sở Y tế tỉnh Lai Châu");
  const ubnd = card("UBND Phường Tân Phong");
  const { clickNopTrucTuyenByCard } = load(new Node("", [so.node, ubnd.node]));
  const res = await clickNopTrucTuyenByCard("Cơ quan thực hiện: UBND");
  assert.equal(res.ok, true);
  assert.equal(ubnd.button.clicked, true);
  assert.equal(so.button.clicked, false, "thẻ đầu là cấp Sở — bấm là nộp nhầm cơ quan");
});

test("không thẻ nào khớp → dừng, KHÔNG lùi về thẻ đầu", async () => {
  const so = card("Sở Y tế tỉnh Lai Châu");
  const so2 = card("Chi cục An toàn vệ sinh thực phẩm");
  const { clickNopTrucTuyenByCard } = load(new Node("", [so.node, so2.node]));
  const res = await clickNopTrucTuyenByCard("Cơ quan thực hiện: UBND");
  assert.equal(res.code, "card_not_found");
  assert.equal(so.button.clicked, false);
  assert.equal(so2.button.clicked, false);
});

test("dò thẻ không leo sang thẻ bên cạnh", () => {
  const so = card("Sở Y tế");
  const ubnd = card("UBND Phường Tân Phong");
  const list = new Node("", [so.node, ubnd.node]);
  const { resultCard } = load(list);
  // Leo quá thẻ là ôm cả danh sách → text của thẻ Sở sẽ chứa chữ UBND của thẻ bên cạnh.
  assert.equal(resultCard(so.button), so.node);
  assert.ok(!fold(resultCard(so.button).textContent).includes("ubnd"));
});

test("listener + sidebar chuyển tiếp cardIncludes và báo riêng khi không thấy thẻ", () => {
  const code = strip(dvc);
  assert.match(code, /cardIncludes:\s*msg\.cardIncludes\s*\|\|\s*""/);
  const sidebar = strip(fs.readFileSync(path.join(root, "sidebar.js"), "utf8"));
  assert.match(sidebar, /supportsAgencyCard:\s*true/);
  const block = sidebar.slice(sidebar.indexOf('action: "selectAgency"'));
  assert.match(block.slice(0, 900), /cardIncludes:\s*a\.cardIncludes\s*\|\|\s*""/);
  assert.match(block.slice(0, 900), /code === "card_not_found"[\s\S]*__event:agency_card_missing/);
});

test("ô Phường/Xã ra hai dòng cùng tên: Bắc Nha Trang (Khánh Hòa) bấm dòng trên rồi dòng dưới, xã khác vẫn dòng đầu", () => {
  const start = dvc.indexOf("const PORTAL_AGENCY_WARD_PICKS");
  const end = dvc.indexOf("function typeIntoSearch", start);
  assert.ok(start >= 0 && end > start, "không cắt được bảng dòng trùng tên + matchOption");
  const ctx = { fold, isVisible: () => true };
  vm.createContext(ctx);
  vm.runInContext(
    dvc.slice(start, end)
      + "\nthis.matchOption = matchOption;\nthis.portalAgencyWardPicks = portalAgencyWardPicks;",
    ctx,
  );
  const option = (text) => {
    const node = { textContent: text, children: [], isConnected: true };
    node.closest = () => node;
    return node;
  };
  const panel = (options) => ({
    textContent: options.map((o) => o.textContent).join(" "),
    children: options,
    isConnected: true,
    querySelectorAll: () => options,
  });

  // Mảng tạo trong vm khác realm → so qua JSON.
  const picks = (p, w) => JSON.stringify(ctx.portalAgencyWardPicks(p, w));
  assert.equal(picks("Tỉnh Khánh Hòa", "Phường Bắc Nha Trang"), "[1,2]", "cổng lỗi: dòng trên trước, dòng dưới sau");
  assert.equal(picks("Khánh Hòa", "Bắc Nha Trang"), "[1,2]");
  assert.equal(picks("Tỉnh Khánh Hòa", "Phường Nha Trang"), "[1]");
  assert.equal(picks("Tỉnh Bắc Ninh", "Phường Bắc Nha Trang"), "[1]");

  const tren = option("Phường Bắc Nha Trang");
  const duoi = option("Phường Bắc Nha Trang");
  const roots = [panel([tren, duoi, option("Phường Nha Trang"), option("Phường Tây Nha Trang")])];
  assert.equal(ctx.matchOption(roots, "Phường Bắc Nha Trang", 1), tren);
  assert.equal(ctx.matchOption(roots, "Phường Bắc Nha Trang", 2), duoi);
  assert.equal(ctx.matchOption(roots, "Phường Bắc Nha Trang"), tren, "không khai thì giữ dòng đầu như cũ");
  // Cổng gộp còn một dòng → lấy dòng duy nhất, không báo không thấy.
  const mot = option("Phường Bắc Nha Trang");
  assert.equal(ctx.matchOption([panel([mot, option("Phường Nha Trang")])], "Phường Bắc Nha Trang", 2), mot);
});

test("thủ tục không khai thẻ giữ nguyên đường bấm thẻ đầu", () => {
  const code = strip(dvc);
  const sel = code.slice(code.indexOf("async function selectAgency"));
  // Chỉ rẽ sang dò thẻ khi có cardIncludes; còn lại vẫn là clickNopTrucTuyen cũ.
  assert.match(sel, /if \(cardIncludes && !fold\(submitLabel\)\.includes\("nop truc tuyen"\)\)/);
  assert.match(sel, /await clickNopTrucTuyen\(\)/);
});

// ── Thủ tục nộp thẳng (BE agencyDirectSubmit, 1.001194): như Auto Fill directSubmit + bcaSubmit ──
function loadDirect(documentRoot, search = "") {
  const start = dvc.indexOf("async function clickNopTrucTuyen()");
  const end = dvc.indexOf("async function selectAgency", start);
  const bStart = dvc.indexOf("function bcaTthcSubmitButton");
  const bEnd = dvc.indexOf("chrome.runtime.onMessage.addListener", bStart);
  assert.ok(start >= 0 && end > start && bStart > 0 && bEnd > bStart, "không cắt được hàm nộp thẳng");
  const ctx = {
    fold,
    isVisible: () => true,
    sleep: async () => {},
    waitFor: async (fn) => fn(),
    clickLikeUser: (el) => { el.clicked = true; },
    document: documentRoot,
    location: { search },
    URLSearchParams,
  };
  vm.createContext(ctx);
  vm.runInContext(
    dvc.slice(start, end) + dvc.slice(bStart, bEnd)
      + "\nthis.directSubmit = directSubmit;\nthis.bcaTthcSubmit = bcaTthcSubmit;",
    ctx,
  );
  return ctx;
}

test("nộp thẳng: không đụng ô Tỉnh/Xã, bấm Nộp hồ sơ của khối rồi Nộp trực tuyến", async () => {
  const nopHoSo = new Node("Nộp hồ sơ", [], true);
  const block = new Node("Chọn cơ quan thực hiện", [new Node("-- Chọn Tỉnh/ Thành phố --"), nopHoSo]);
  const ketQua = btn();
  const { directSubmit } = loadDirect(new Node("", [block, ketQua]));
  const res = await directSubmit(block);
  assert.equal(res.ok, true);
  assert.equal(nopHoSo.clicked, true);
  assert.equal(ketQua.clicked, true);
  // Không thấy nút "Nộp hồ sơ" trong khối → báo lỗi, không bấm gì.
  const empty = new Node("Chọn cơ quan thực hiện", [new Node("-- Chọn Tỉnh/ Thành phố --")]);
  assert.ok((await loadDirect(new Node("", [empty])).directSubmit(empty)).error);
});

test("trang thủ tục cổng Bộ Công an: chỉ bấm Nộp hồ sơ khi MaTTHC trùng mã", async () => {
  const page = () => {
    const nop = new Node("Nộp hồ sơ", [], true);
    nop.closest = () => null;
    const menu = new Node("Nộp hồ sơ trực tuyến", [], true);
    menu.closest = () => null;
    return { root: new Node("", [menu, nop]), nop, menu };
  };
  let p = page();
  let res = await loadDirect(p.root, "?matt=1&MaTTHC=1.001194").bcaTthcSubmit({ code: "1.001194" });
  assert.equal(res.ok, true);
  assert.equal(p.nop.clicked, true);
  assert.equal(p.menu.clicked, false, "menu đầu trang \"Nộp hồ sơ trực tuyến\" không được bấm");
  p = page();
  res = await loadDirect(p.root, "?MaTTHC=1.001456").bcaTthcSubmit({ code: "1.001194" });
  assert.equal(res.ok, false);
  assert.equal(p.nop.clicked, false);
});

test("nộp thẳng: listener, sidebar và page_status chuyển đủ cờ", () => {
  const code = strip(dvc);
  assert.match(code, /direct:\s*msg\.direct\s*===\s*true/);
  assert.match(code, /if \(direct\) return directSubmit\(block\)/);
  const sidebar = strip(fs.readFileSync(path.join(root, "sidebar.js"), "utf8"));
  const block = sidebar.slice(sidebar.indexOf('action: "selectAgency"'));
  assert.match(block.slice(0, 1200), /direct:\s*a\.direct\s*===\s*true/);
  assert.match(sidebar, /a\.type === "bca_tthc_submit"[\s\S]{0,400}action: "bcaTthcSubmit"/);
  assert.match(sidebar, /bcaTthcPage:\s*!!c\.bcaTthcPage/);
  assert.match(sidebar, /supportsBcaThiThuc:\s*true/);
  const content = strip(fs.readFileSync(path.join(root, "content.js"), "utf8"));
  assert.match(content, /bcaTthcPage,\s*bcaTthcCode,/);
});

// ── eForm Nth Bộ Công an, trang "xác nhận thông tin nộp" (thị thực 1.001194, ảnh 18/11): công dân tự nhập Mã xác nhận +
// tích ô chịu trách nhiệm; nút Nộp hồ sơ của trợ lý soát hai ô đó rồi mới bấm nút nộp của cổng ──
function loadNth({ captcha, boxes, buttons, alerts }) {
  const bStart = dvc.indexOf("function bcaTthcSubmitButton");
  const bEnd = dvc.indexOf("chrome.runtime.onMessage.addListener", bStart);
  const ctx = {
    fold,
    isVisible: () => true,
    sleep: async () => {},
    waitFor: async (fn) => fn(),
    clickLikeUser: (el) => { el.clicked = true; },
    location: { search: "", hostname: "dichvucong.bocongan.gov.vn" },
    URLSearchParams,
    document: {
      querySelectorAll: (sel) => {
        if (sel.includes("captcha")) return captcha ? [captcha] : [];
        if (sel === 'input[type="checkbox"]') return boxes;
        if (sel === "a.bca-search-btn, button.bca-search-btn") return [];
        if (sel === "a, button") return buttons;
        if (sel.startsWith(".modal")) return alerts();
        return [];
      },
    },
  };
  vm.createContext(ctx);
  vm.runInContext(dvc.slice(bStart, bEnd) + "\nthis.bcaNthSubmit = bcaNthSubmit;", ctx);
  return ctx;
}

function nthPage() {
  const captcha = { value: "", scrollIntoView() {}, focus() {} };
  // Ô "Nhận trực tiếp" cùng trang: khung to bao cả câu cam kết không được nhận nhầm là ô cam kết.
  const bigText = `Nơi nhận thị thực Nhận trực tiếp ${"x".repeat(300)} Tôi xin chịu trách nhiệm trước pháp luật về lời khai trên`;
  const delivery = { checked: true, labels: [{ textContent: "Nhận trực tiếp" }], textContent: "",
    parentElement: { textContent: "Nhận trực tiếp", classList: { contains: () => false },
      parentElement: { textContent: bigText, parentElement: null } } };
  const commit = { checked: false, labels: [], textContent: "", scrollIntoView() {},
    parentElement: { textContent: "Tôi xin chịu trách nhiệm trước pháp luật về lời khai trên",
      classList: { contains: () => false }, parentElement: null } };
  let shownAlerts = [];
  const menu = { textContent: "Nộp hồ sơ trực tuyến", closest: () => null, click() { this.clicked = true; } };
  const nop = { textContent: "Nộp hồ sơ", closest: () => null, scrollIntoView() {}, click() { this.clicked = true; } };
  const page = { captcha, commit, delivery, menu, nop, setAlertOnClick: null };
  nop.click = function click() {
    this.clicked = true;
    if (page.setAlertOnClick) shownAlerts = [page.setAlertOnClick];
  };
  page.ctx = () => loadNth({ captcha, boxes: [delivery, commit], buttons: [menu, nop], alerts: () => shownAlerts });
  return page;
}

function alertEl(text, buttons) {
  return {
    textContent: text,
    querySelector: () => null,
    querySelectorAll: () => buttons.map((b) => ({ textContent: b })),
  };
}

test("trang xác nhận Bộ Công an: chưa nhập mã / chưa tích ô thì KHÔNG bấm Nộp hồ sơ", async () => {
  const page = nthPage();
  let res = await page.ctx().bcaNthSubmit();
  assert.equal(JSON.stringify(res), JSON.stringify({ clicked: false, missing: ["captcha"] }));
  page.captcha.value = "tohlw";
  res = await page.ctx().bcaNthSubmit();
  assert.equal(JSON.stringify(res), JSON.stringify({ clicked: false, missing: ["commit"] }));
  assert.equal(page.nop.clicked, undefined, "thiếu mã / chưa tích ô thì không được nộp");
});

test("trang xác nhận Bộ Công an: đủ mã + đã tích ô → bấm đúng nút Nộp hồ sơ, cổng hỏi lại thì để công dân bấm", async () => {
  const page = nthPage();
  page.captcha.value = "tohlw";
  page.commit.checked = true;
  let res = await page.ctx().bcaNthSubmit();
  assert.equal(res.clicked, true);
  assert.equal(res.message, "");
  assert.equal(page.nop.clicked, true);
  assert.equal(page.menu.clicked, undefined, "menu \"Nộp hồ sơ trực tuyến\" đầu trang không được bấm");
  // Cổng hỏi "chắc chắn nộp?" → báo confirm, trợ lý không bấm thay.
  const confirmPage = nthPage();
  confirmPage.captcha.value = "tohlw";
  confirmPage.commit.checked = true;
  confirmPage.setAlertOnClick = alertEl("Bạn có chắc chắn nộp hồ sơ?", ["Đồng ý", "Hủy"]);
  res = await confirmPage.ctx().bcaNthSubmit();
  assert.equal(res.confirm, true);
  // Cổng báo sai mã → trả lời của cổng về BE.
  const wrong = nthPage();
  wrong.captcha.value = "abcde";
  wrong.commit.checked = true;
  wrong.setAlertOnClick = alertEl("Mã xác nhận không đúng", ["Đóng"]);
  res = await wrong.ctx().bcaNthSubmit();
  assert.equal(res.clicked, true);
  assert.equal(res.message, "Mã xác nhận không đúng");
});

test("trang xác nhận Bộ Công an: page_status, sidebar và capability nối đủ", () => {
  const sidebar = strip(fs.readFileSync(path.join(root, "sidebar.js"), "utf8"));
  assert.match(sidebar, /supportsBcaNthSubmit:\s*true/);
  assert.match(sidebar, /bcaConfirmPage:\s*!!c\.bcaConfirmPage/);
  assert.match(sidebar, /a\.type === "bca_nth_submit"[\s\S]{0,600}action: "bcaNthSubmit"/);
  assert.match(sidebar, /__action:bca_nth_submit_report:/);
  const content = strip(fs.readFileSync(path.join(root, "content.js"), "utf8"));
  assert.match(content, /bcaKeKhaiForm,\s*bcaConfirmPage,/);
  assert.match(content, /\/xac-nhan-thong-tin-nop\//);
});
