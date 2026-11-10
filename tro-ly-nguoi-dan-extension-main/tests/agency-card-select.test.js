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
