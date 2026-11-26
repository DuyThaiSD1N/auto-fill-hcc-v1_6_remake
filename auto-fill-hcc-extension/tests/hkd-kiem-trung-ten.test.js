// Thành lập hộ kinh doanh: điền xong trang Tên hộ thì kiểm trùng cả 3 tên trên cổng, chỉ cảnh báo (không chặn Lưu).
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const engine = fs.readFileSync(path.join(__dirname, "..", "content", "procedures", "business-registration.js"), "utf8")
  .replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

function extract(name) {
  const start = engine.search(new RegExp(`function ${name}\\(`));
  assert.ok(start >= 0, `thiếu ${name}`);
  let depth = 0;
  for (let i = engine.indexOf("{", start); i < engine.length; i++) {
    if (engine[i] === "{") depth++;
    else if (engine[i] === "}" && --depth === 0) return engine.slice(start, i + 1);
  }
  throw new Error(`không tách được ${name}`);
}

test("kiểm đủ 3 tên; tên viết tắt dùng API tên tiếng Việt", () => {
  assert.match(engine, /\{ field: "ctl00\$C\$NAMEFld", label: "Tên hộ kinh doanh", api: "GetExistName", key: "name" \}/);
  assert.match(engine, /\{ field: "ctl00\$C\$NAME_FFld", label: "Tên tiếng nước ngoài", api: "GetExistNameF", key: "name_f" \}/);
  assert.match(engine, /\{ field: "ctl00\$C\$SHORT_NAMEFld", label: "Tên viết tắt", api: "GetExistName", key: "name" \}/);
  assert.match(extract("checkBusinessName"), /body: JSON\.stringify\(\{ \[check\.key\]: `\$\{name\}::\$\{type\}` \}\)/);
});

test("có tên trong bảng là trùng dù không đọc được câu đếm", () => {
  assert.match(extract("checkBusinessName"), /count: Math\.max\(counted \? Number\(counted\[1\]\) : 0, names\.length\)/);
});

test("kiểm sau khi điền trang Tên hộ, trước khi Lưu, một lần; cảnh báo vào câu kết thúc", () => {
  const body = extract("stepFillAll");
  const check = body.indexOf('if (targetKey === "ten-ho-kinh-doanh" && !st.nameChecked)');
  assert.ok(check > body.indexOf("await ensureBusinessFieldsFilled(pageFields") && check < body.indexOf("const saveBtn = findBusinessSaveButton();"));
  assert.match(extract("finishFillAllThenAttach"), /const warn = unverifiedPagesText\(st && st\.unverifiedPages\) \+ nameWarningText\(st\);/);
});

test("panel tô đỏ đậm riêng dòng cảnh báo trùng tên sau câu báo xong", () => {
  const vm = require("node:vm");
  const popup = fs.readFileSync(path.join(__dirname, "..", "popup.js"), "utf8");
  const start = popup.indexOf("async function restoreFillAllResult(");
  let depth = 0, end = -1;
  for (let i = popup.indexOf("{", start); i < popup.length; i++) {
    if (popup[i] === "{") depth++;
    else if (popup[i] === "}" && --depth === 0) { end = i + 1; break; }
  }
  const text = "✓ Đã điền xong 8 trang. Vui lòng rà soát rồi bấm Nộp.\n⚠ Kiểm trùng tên — Tên hộ kinh doanh \"HO A\": cổng có 2 hộ trùng hoặc tương tự. Xem lại trước khi nộp.";
  const children = [];
  const statusEl = { textContent: "", appendChild: (c) => children.push(c) };
  const ctx = {
    statusEl, FILLALL_RESULT_KEY: "k", FILLALL_RESULT_TTL_MS: 60000, Date,
    chrome: { storage: { local: { get: async () => ({ k: { text, type: "ok", at: Date.now() } }), remove: async () => {} } } },
    setStatus: (t) => { statusEl.textContent = t; },
    document: { createElement: (tag) => ({ tag, className: "", textContent: "" }) },
  };
  vm.runInNewContext(`${popup.slice(start, end)}; this.run = restoreFillAllResult;`, ctx);
  return ctx.run().then(() => {
    assert.equal(statusEl.textContent, "✓ Đã điền xong 8 trang. Vui lòng rà soát rồi bấm Nộp.");
    assert.equal(children.length, 1);
    assert.equal(children[0].className, "status-danger");
    assert.ok(children[0].textContent.startsWith("\n⚠ Kiểm trùng tên"));
    assert.match(fs.readFileSync(path.join(__dirname, "..", "popup.css"), "utf8"), /\.status \.status-danger \{ color: #b71c1c; font-weight: 700; \}/);
  });
});
