/**
 * Khối nhân thân CẤM GHI: "Thông tin người nộp hồ sơ" là nhân thân TÀI KHOẢN đang đăng nhập do cổng tự
 * đổ, BE không phát ô nào của khối đó. Mọi giá trị của ta xuất hiện ở đây đều là ghi đè ngoài ý muốn —
 * vùng dò trượt sang khối cấm, vòng điền lại, hoặc chính cổng tự sao chép sau khi ta điền khối chủ hồ sơ.
 *
 * Chốt chặn cuối: chụp giá trị khối cấm trước khi điền, xong xuôi ô nào đổi thành ĐÚNG dữ liệu ta vừa
 * ghi thì hoàn nguyên. Giá trị lạ (cổng tự đổi) phải để yên.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "..", "content.js"), "utf8");

function slice(startMarker, endMarker) {
  const start = source.indexOf(startMarker);
  assert.ok(start >= 0, `Không tìm thấy ${startMarker}`);
  const end = source.indexOf(endMarker, start);
  assert.ok(end > start, `Không tìm thấy ${endMarker}`);
  return source.slice(start, end);
}

const helpers = slice("  function standardScopeRoot(field) {", "  function orderStandardFields(fields) {");

// ------------------------------------------------------- DOM tối giản
function matches(node, selector) {
  return selector.split(",").some((part) => {
    const sel = part.trim();
    if (!sel) return false;
    const m = sel.match(/^([a-zA-Z]*)((?:\.[\w-]+)*)(?:\[name(?:="([^"]*)")?\])?$/);
    if (!m) return false;
    const [, tag, classes, name] = m;
    if (tag && node.tagName.toLowerCase() !== tag.toLowerCase()) return false;
    for (const cls of (classes.match(/\.[\w-]+/g) || []).map((c) => c.slice(1))) {
      if (!node.classes.includes(cls)) return false;
    }
    if (sel.includes("[name")) {
      if (!node.name) return false;
      if (name !== undefined && node.name !== name) return false;
    }
    return true;
  });
}

function baseNode(tag, props, children) {
  const node = {
    tagName: tag.toUpperCase(),
    name: props.name || "",
    id: props.id || "",
    classes: props.classes || [],
    owner: props.owner || "",
    children,
    parentElement: null,
    events: [],
    dispatchEvent(evt) {
      this.events.push(evt && evt.type);
      return true;
    },
    descendants() {
      return this.children.flatMap((child) => [child, ...child.descendants()]);
    },
    querySelectorAll(selector) {
      return this.descendants().filter((n) => matches(n, selector));
    },
    querySelector(selector) {
      return this.querySelectorAll(selector)[0] || null;
    },
  };
  children.forEach((child) => {
    child.parentElement = node;
  });
  return node;
}

function makeNode(tag, props = {}, children = []) {
  const node = baseNode(tag, props, children);
  node.value = props.value || "";
  return node;
}

// Select thật: gán .value là đổi luôn option đang chọn → text đọc ra đổi theo.
function makeSelect(props, optionTexts) {
  const node = baseNode("select", props, []);
  node.options = optionTexts.map((text, index) => ({ text, value: String(index) }));
  let current = String(props.selectedIndex ?? 0);
  Object.defineProperty(node, "value", {
    get: () => current,
    set: (next) => {
      current = String(next);
    },
  });
  Object.defineProperty(node, "selectedIndex", { get: () => Number(current) });
  return node;
}

const MARKERS = ["data[chonDoiTuong]", "data[isOwnerDossierCheck]", "data[ownerFullname]"];
const DON = ".formio-component-phuLuc1";

function buildPage() {
  const nopHoTen = makeNode("input", { name: "data[fullname]", owner: "nguoi-nop", value: "NGUYỄN DUY THÁI" });
  const nopNgaySinh = makeNode("input", { name: "data[birthday]", owner: "nguoi-nop", value: "11/08/2004" });
  const nopTinh = makeSelect({ name: "data[province]", owner: "nguoi-nop" }, ["Thành phố Hà Nội", "Tỉnh Lai Châu"]);
  const nopFax = makeNode("input", { name: "data[fax]", owner: "nguoi-nop", value: "" });
  const phanI = baseNode("div", {}, [
    makeNode("select", { name: "data[chonDoiTuong]", value: "Cá nhân" }),
    nopHoTen,
    nopNgaySinh,
    nopTinh,
    nopFax,
    makeNode("input", { name: "data[isOwnerDossierCheck]" }),
  ]);

  const phanII = baseNode("div", {}, [
    makeNode("input", { name: "data[ownerFullname]", owner: "chu-ho-so" }),
    makeNode("input", { name: "data[ownerBirthday]", owner: "chu-ho-so" }),
  ]);

  const toKhaiHoTen = makeNode("input", { name: "data[fullname]", owner: "to-khai" });
  const donBlock = baseNode("div", { classes: ["formio-component", "formio-component-phuLuc1"] }, [
    toKhaiHoTen,
    makeNode("input", { name: "data[bangCapChuyenMon]", owner: "to-khai" }),
  ]);

  const body = baseNode("body", {}, [phanI, phanII, donBlock]);
  const document = {
    body,
    documentElement: body,
    getElementById: () => null,
    querySelector: (selector) => body.querySelector(selector),
    querySelectorAll: (selector) => body.querySelectorAll(selector),
  };
  return { document, body, phanI, phanII, donBlock, nopHoTen, nopNgaySinh, nopTinh, nopFax, toKhaiHoTen };
}

function load(page) {
  const sandbox = {
    console: { warn() {} },
    document: page.document,
    CSS: { escape: (v) => String(v) },
    Event: class {
      constructor(type) {
        this.type = type;
      }
    },
    fieldCandidates: (f) => [String(f?.name || "")],
    foldChoiceText: (v) =>
      String(v || "")
        .normalize("NFD")
        .replace(/[̀-ͯ]/g, "")
        .replace(/Đ/g, "D")
        .replace(/đ/g, "d")
        .toLowerCase()
        .trim(),
    standardMarkTarget: () => null,
    sleep: () => Promise.resolve(),
    waitFor: async (fn, timeout = 3000, interval = 100) => {
      for (let elapsed = 0; elapsed < timeout; elapsed += interval) {
        const v = fn();
        if (v) return v;
      }
      return null;
    },
    // Bản thật: BE gửi khoá Form.io "data[x]", khối Angular ở đầu trang lại đặt name trần "x".
    standardNameVariants: (names) =>
      names.flatMap((raw) => {
        const name = String(raw || "").trim();
        const key = name.match(/^data\[([^\]]+)\]$/);
        return key ? [name, key[1]] : [name];
      }),
    standardControlVisible: () => true,
    findStandardDatagridFallbackInput: () => null,
    standardOccurrence: () => null,
    pickStandardControl: (elements) => elements[0] || null,
  };
  vm.runInNewContext(
    `${helpers}
     globalThis.scopeRoot = standardScopeRoot;
     globalThis.scopeRootWaiting = standardScopeRootWaiting;
     globalThis.forbiddenRoots = standardForbiddenRoots;
     globalThis.snapshot = snapshotStandardControls;
     globalThis.writtenKeys = standardWrittenValueKeys;
     globalThis.restore = restoreStandardForbidden;`,
    sandbox,
  );
  return sandbox;
}

// Payload thật của "Cấp lại Chứng chỉ hành nghề thú y": ô tờ đơn khai scope, ô chủ hồ sơ thì không.
const FIELDS = [
  { name: "data[isOwnerDossierCheck]", comp: "dom-checkbox", value: false },
  { name: "data[ownerFullname]", comp: "dom-input", value: "TRẦN THỊ BÍCH THUỶ" },
  { name: "data[ownerBirthday]", comp: "dom-date", value: "19/05/1989" },
  {
    name: "data[fullname]",
    comp: "dom-input",
    value: "TRẦN THỊ BÍCH THUỶ",
    scope: DON,
    scopeNear: "data[bangCapChuyenMon]",
    scopeAway: MARKERS,
  },
  {
    name: "data[province]",
    comp: "dom-select",
    value: "Tỉnh Lai Châu",
    scope: DON,
    scopeNear: "data[bangCapChuyenMon]",
    scopeAway: MARKERS,
  },
  { name: "data[bangCapChuyenMon]", comp: "dom-input", value: "Bác sĩ thú y" },
];

// Khối cấm = đúng thẻ bọc "Thông tin người nộp hồ sơ", KHÔNG trùm sang chủ hồ sơ hay tờ đơn.
{
  const page = buildPage();
  const api = load(page);
  const roots = api.forbiddenRoots(FIELDS);
  assert.equal(roots.length, 1, "Chỉ có một khối cấm");
  assert.ok(roots[0] === page.phanI, "Khối cấm phải là khối người nộp hồ sơ");
}

// Ô tờ đơn trượt sang khối người nộp (hoặc cổng tự copy) → hoàn nguyên nhân thân tài khoản.
{
  const page = buildPage();
  const api = load(page);
  const snap = api.snapshot(api.forbiddenRoots(FIELDS));

  page.nopHoTen.value = "TRẦN THỊ BÍCH THUỶ";
  page.nopNgaySinh.value = "19/05/1989";
  page.nopTinh.value = "1"; // đổi sang "Tỉnh Lai Châu"

  const reverted = api.restore(snap, api.writtenKeys(FIELDS));

  assert.equal(page.nopHoTen.value, "NGUYỄN DUY THÁI", "Họ tên người nộp phải giữ nguyên tài khoản");
  assert.equal(page.nopNgaySinh.value, "11/08/2004", "Ngày sinh người nộp phải giữ nguyên tài khoản");
  assert.equal(page.nopTinh.value, "0", "Tỉnh của người nộp phải quay về option ban đầu");
  assert.equal(reverted.length, 3);
  assert.ok(page.nopHoTen.events.includes("change"), "Hoàn nguyên phải bắn change cho form biết");
}

// Giá trị KHÔNG phải của ta (cổng tự đổi) thì để yên, không được đụng vào.
{
  const page = buildPage();
  const api = load(page);
  const snap = api.snapshot(api.forbiddenRoots(FIELDS));

  page.nopFax.value = "02133888999";
  const reverted = api.restore(snap, api.writtenKeys(FIELDS));

  assert.equal(page.nopFax.value, "02133888999", "Dữ liệu của cổng không được hoàn nguyên");
  assert.equal(reverted.length, 0);
}

// Ô của tờ đơn nằm ngoài khối cấm → điền xong giữ nguyên, không bị hoàn nguyên lây.
{
  const page = buildPage();
  const api = load(page);
  const snap = api.snapshot(api.forbiddenRoots(FIELDS));

  page.toKhaiHoTen.value = "TRẦN THỊ BÍCH THUỶ";
  page.phanII.querySelector('input[name="data[ownerFullname]"]').value = "TRẦN THỊ BÍCH THUỶ";
  api.restore(snap, api.writtenKeys(FIELDS));

  assert.equal(page.toKhaiHoTen.value, "TRẦN THỊ BÍCH THUỶ", "Ô tờ đơn phải giữ dữ liệu vừa điền");
  assert.equal(
    page.phanII.querySelector('input[name="data[ownerFullname]"]').value,
    "TRẦN THỊ BÍCH THUỶ",
    "Khối chủ hồ sơ vẫn được điền như thiết kế",
  );
}

// Khối người nộp do Angular dựng: ô mang name TRẦN ("fullname"), không phải khoá Form.io
// ("data[fullname]"). Mốc khối cấm phải nhận ra qua biến thể tên, nếu không vùng dò tưởng đã hẹp và ô
// của tờ đơn ghi thẳng lên khối người nộp — đúng lỗi gặp trên trang Cấp lại CCHN thú y.
{
  const nopHoTen = makeNode("input", { name: "fullname", owner: "nguoi-nop", value: "NGUYỄN DUY THÁI" });
  const phanI = baseNode("div", {}, [
    makeNode("select", { name: "chonDoiTuong", value: "Cá nhân" }),
    nopHoTen,
    makeNode("input", { name: "isOwnerDossierCheck" }),
  ]);
  const toKhaiHoTen = makeNode("input", { name: "data[fullname]", owner: "to-khai" });
  const donBlock = baseNode("div", {}, [
    toKhaiHoTen,
    makeNode("input", { name: "data[bangCapChuyenMon]", owner: "to-khai" }),
  ]);
  const body = baseNode("div", {}, [phanI, donBlock]);
  const root = baseNode("body", {}, [body]);
  const page = {
    document: {
      body: root,
      documentElement: root,
      getElementById: () => null,
      // Panel khai trong scope KHÔNG có trên trang này (form đổi tên panel) → vùng dò rơi về cả trang.
      querySelector: (selector) => (selector.startsWith(".") ? null : root.querySelector(selector)),
      querySelectorAll: (selector) => root.querySelectorAll(selector),
    },
  };
  const api = load(page);
  const scopeRoot = api.scopeRoot({
    name: "data[fullname]",
    scope: DON,
    scopeNear: "data[bangCapChuyenMon]",
    scopeAway: MARKERS,
  });
  assert.ok(scopeRoot === donBlock, "Vùng dò phải thu về khối tờ đơn dù khối cấm đặt name trần");
  assert.ok(
    !scopeRoot.querySelectorAll("input").includes(nopHoTen),
    "Ô họ tên của khối người nộp không được nằm trong vùng dò",
  );
}

// Trang thật có HAI panel CÙNG khoá "thongTinChung": một của khối người nộp, một của tờ đơn, và cả hai
// cùng chứa data[fullname]. Selector trần trúng cái đầu tiên (khối người nộp) nên BE phải tách bằng
// :has(ô chỉ có ở tờ đơn).
{
  const nopHoTen = makeNode("input", { name: "data[fullname]", owner: "nguoi-nop", value: "NGUYỄN DUY THÁI" });
  const panelNop = baseNode("div", { classes: ["formio-component-panel", "formio-component-thongTinChung"] }, [
    makeNode("select", { name: "data[chonDoiTuong]" }),
    nopHoTen,
    makeNode("input", { name: "data[isOwnerDossierCheck]" }),
  ]);
  const donHoTen = makeNode("input", { name: "data[fullname]", owner: "to-khai" });
  const panelDon = baseNode("div", { classes: ["formio-component-panel", "formio-component-thongTinChung"] }, [
    donHoTen,
    baseNode("div", { classes: ["formio-component", "formio-component-bangCapChuyenMon"] }, [
      makeNode("input", { name: "data[bangCapChuyenMon]", owner: "to-khai" }),
    ]),
  ]);
  const root = baseNode("body", {}, [panelNop, panelDon]);

  // querySelector hiểu "A:has(B)" như trình duyệt: lấy phần tử A đầu tiên có chứa B.
  const pick = (selector) => {
    const has = /^(.*?):has\((.*)\)$/.exec(selector.trim());
    if (!has) return root.querySelector(selector);
    return root.querySelectorAll(has[1]).find((node) => node.querySelector(has[2])) || null;
  };
  const page = {
    document: {
      body: root,
      documentElement: root,
      getElementById: () => null,
      querySelector: pick,
      querySelectorAll: (selector) => root.querySelectorAll(selector),
    },
  };
  const api = load(page);
  const field = {
    name: "data[fullname]",
    scope: ".formio-component-thongTinChung:has(.formio-component-bangCapChuyenMon)",
    scopeNear: "data[bangCapChuyenMon]",
    scopeAway: MARKERS,
  };

  assert.ok(
    page.document.querySelector(".formio-component-thongTinChung") === panelNop,
    "Selector trần trúng panel ĐẦU TIÊN, tức khối người nộp — lý do phải dùng :has",
  );
  const scoped = api.scopeRoot(field);
  assert.ok(scoped === panelDon, ":has phải trỏ đúng panel của tờ đơn");
  assert.ok(scoped.querySelectorAll("input").includes(donHoTen), "Vùng dò phải chứa ô họ tên của tờ đơn");
  assert.ok(!scoped.querySelectorAll("input").includes(nopHoTen), "Vùng dò không được chạm ô của khối người nộp");
}

// Panel tờ đơn do Form.io dựng TRỄ: lúc vòng điền chạm ô đầu tiên thì khối chưa có trong DOM. Không chờ
// thì ô của tờ đơn bị bỏ trắng oan, trong khi ô không khai scope vẫn điền được — đúng cảnh "Bằng cấp
// chuyên môn" có chữ mà Họ tên ngay trên nó thì trống.
{
  const donHoTen = makeNode("input", { name: "data[fullname]", owner: "to-khai" });
  const panel = baseNode("div", { classes: ["formio-component", "formio-component-panel", "formio-component-thongTinChung"] }, [
    donHoTen,
    makeNode("input", { name: "data[bangCapChuyenMon]", owner: "to-khai" }),
  ]);
  const nguoiNop = baseNode("div", {}, [makeNode("input", { name: "fullname", owner: "nguoi-nop" })]);
  const root = baseNode("body", {}, [nguoiNop]);

  let polls = 0;
  const page = {
    document: {
      body: root,
      documentElement: root,
      getElementById: () => null,
      querySelector: (selector) => {
        if (selector === ".formio-component-thongTinChung") {
          // Panel chỉ xuất hiện từ lần dò thứ ba trở đi.
          if (polls++ < 2) return null;
          if (!root.children.includes(panel)) {
            panel.parentElement = root;
            root.children.push(panel);
          }
          return panel;
        }
        return root.querySelector(selector);
      },
      querySelectorAll: (selector) => root.querySelectorAll(selector),
    },
  };
  const api = load(page);
  const field = {
    name: "data[fullname]",
    scope: ".formio-component-thongTinChung",
    scopeNear: "data[bangCapChuyenMon]",
    scopeAway: MARKERS,
  };

  assert.equal(api.scopeRoot(field), null, "Ngay lúc đầu khối chưa render nên chưa tra được");
  return Promise.resolve(api.scopeRootWaiting(field)).then((waited) => {
    assert.ok(waited === panel, "Chờ xong phải ra đúng panel tờ đơn");
    assert.ok(
      waited.querySelectorAll("input").includes(donHoTen),
      "Ô họ tên của tờ đơn phải nằm trong vùng dò sau khi chờ",
    );
    console.log("forbidden-block-no-overwrite: OK");
  });
}


