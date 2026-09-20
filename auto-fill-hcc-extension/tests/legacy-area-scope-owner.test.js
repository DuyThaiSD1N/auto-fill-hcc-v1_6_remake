// req_dd367e1e8712 — "TP Hồ Chí Minh của tôi đâu?"
//
// Mẫu khai tử có BA khối địa chỉ, mỗi khối một ô tích "Trong nước/Khác" riêng. Kịch bản thật:
//   1. Mục (4) Nơi cư trú điền XONG: Hồ Chí Minh / Phường Bình Tân / 79 Đường số 6.
//   2. Mục (12) Nơi chết điền lượt 1 THIẾU Phường/Xã (agent đọc "Vinh Lộc", khớp lỏng 2 option
//      "Xã Vĩnh Lộc" + "Xã Tân Vĩnh Lộc" nên extension bỏ qua, không đoán bừa).
//   3. Thiếu Phường/Xã → fillSelectArea gọi resetLegacyAreaScope để cổng dựng lại khối rồi điền lượt 2.
//   4. LỖI: bước 3 đi tìm ô phạm vi bằng querySelectorAll("x-radio") trần → vớ phải ô ĐẦU TIÊN theo
//      thứ tự tài liệu, tức ô của mục (4). Tick vào đó, cổng dựng lại khối mục (4) và xóa sạch dữ
//      liệu đã điền đúng ở đấy — mục (12) thì vẫn nguyên si vì chưa hề được dựng lại.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const FILE = path.join(__dirname, "..", "content", "fill-legacy.js");

// ---- DOM tối giản: đủ contains / querySelectorAll theo tag / compareDocumentPosition ----
function buildForm() {
  let seq = 0;
  class El {
    constructor(tag) {
      this.tag = tag; this.children = []; this.parentElement = null;
      this.seq = seq++; this.checked = false; this.label = "";
    }
    add(...kids) { for (const k of kids) { k.parentElement = this; this.children.push(k); } return this; }
    get descendants() { return this.children.flatMap((c) => [c, ...c.descendants]); }
    querySelectorAll(sel) {
      return this.descendants.filter((n) => n.tag === sel || (sel === 'input[type="checkbox"]' && n.tag === "input"));
    }
    contains(other) { return other === this || this.descendants.includes(other); }
    // Thứ tự tài liệu = thứ tự dựng cây (dựng đúng thứ tự xuất hiện trên biểu mẫu).
    compareDocumentPosition(other) { return other.seq < this.seq ? 2 /* PRECEDING */ : 4 /* FOLLOWING */; }
    click() {
      if (this.tag !== "input") return;
      for (const sib of this.parentElement.children) sib.checked = false;
      this.checked = true;
      // Cổng dựng LẠI khối địa chỉ của chính ô tích này mỗi lần đổi option → sạch trơn.
      for (const area of this.parentElement.parentElement.querySelectorAll("x-select-area")) area.filled = null;
    }
  }
  const el = (tag) => new El(tag);

  const block = (ten) => {
    const radio = el("x-radio");
    const trongNuoc = el("input"); trongNuoc.label = "Trong nước"; trongNuoc.checked = true;
    const khac = el("input"); khac.label = "Khác";
    radio.add(trongNuoc, khac);
    const area = el("x-select-area");
    area.ten = ten;
    return { ten, radio, trongNuoc, khac, area, wrap: el("div").add(radio, area) };
  };

  const nyc = block("(4) Nơi cư trú người yêu cầu");
  const nkt = block("(10) Nơi cư trú cuối cùng");
  const chet = block("(12) Nơi chết");
  el("form").add(nyc.wrap, nkt.wrap, chet.wrap);
  return { nyc, nkt, chet };
}

function loadRetry() {
  const source = fs.readFileSync(FILE, "utf8");
  const start = source.indexOf("function legacyAreaScopeGroup(container)");
  const end = source.indexOf("// Mỗi khối địa chỉ chỉ được điền TỐI ĐA hai lượt", start);
  assert.ok(start >= 0 && end > start, "Không tách được nhóm hàm retry ô phạm vi");
  const sandbox = {
    Node: { DOCUMENT_POSITION_PRECEDING: 2 },
    console: { warn() {} },
    sleep: () => Promise.resolve(),
    foldLegacyChoice: (v) => String(v || "").normalize("NFD")
      .replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d").toLowerCase(),
    legacyRadioOptionLabel: (_group, box) => box.label || "",
    legacyRadioOptionWrap: (_group, box) => box,
  };
  vm.runInNewContext(
    `${source.slice(start, end)}
     globalThis.scopeOf = legacyAreaScopeGroup;
     globalThis.resetScope = resetLegacyAreaScope;`,
    sandbox,
  );
  return sandbox;
}

(async () => {
  const api = loadRetry();

  // --- Mỗi khối phải nhận ra ô phạm vi CỦA CHÍNH NÓ ---
  const form = buildForm();
  for (const block of [form.nyc, form.nkt, form.chet]) {
    const found = api.scopeOf(block.area);
    assert.ok(found, `${block.ten}: phải tìm được ô phạm vi`);
    assert.equal(found.group, block.radio, `${block.ten}: lấy nhầm ô phạm vi của khối khác`);
    assert.equal(found.current, block.trongNuoc, `${block.ten}: option đang tick phải là "Trong nước"`);
    assert.equal(found.other, block.khac, `${block.ten}: phải nhảy sang "Khác" rồi mới quay lại`);
  }

  // --- Kịch bản thật: (4) điền xong, (12) thiếu Phường/Xã nên retry ---
  const run = buildForm();
  run.nyc.area.filled = { tinh: "Hồ Chí Minh", xa: "Phường Bình Tân", diaChi: "79 Đường số 6" };
  run.nkt.area.filled = { tinh: "Lâm Đồng", xa: "Phường Xuân Hương", diaChi: "23/1 Hùng Vương" };
  run.chet.area.filled = { tinh: "Hồ Chí Minh", xa: null, diaChi: "tại nhà không số ấp 53" };

  assert.equal(await api.resetScope(run.chet.area), true, "Phải tick lại được ô phạm vi của (12)");

  assert.deepEqual(
    run.nyc.area.filled,
    { tinh: "Hồ Chí Minh", xa: "Phường Bình Tân", diaChi: "79 Đường số 6" },
    "Retry của mục (12) KHÔNG được làm cổng dựng lại mục (4) — đó là chỗ mất 'TP Hồ Chí Minh'",
  );
  assert.deepEqual(
    run.nkt.area.filled,
    { tinh: "Lâm Đồng", xa: "Phường Xuân Hương", diaChi: "23/1 Hùng Vương" },
    "Retry của mục (12) cũng không được đụng mục (10)",
  );
  assert.equal(run.chet.area.filled, null, "Đúng khối (12) mới là khối được dựng lại để điền lượt 2");
  assert.equal(run.chet.trongNuoc.checked, true, 'Tick xong phải quay lại "Trong nước"');

  // --- Ô phạm vi đứng SAU khối thì không phải của khối đó ---
  assert.notEqual(api.scopeOf(run.nyc.area)?.group, run.chet.radio, "Không được lấy ô phạm vi đứng sau khối");

  console.log("legacy area scope owner passed");
})();
