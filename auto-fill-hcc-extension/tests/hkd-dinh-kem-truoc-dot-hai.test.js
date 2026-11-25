// Hộ kinh doanh (HkdOnline 8 trang) có điền đợt 2: đính kèm TRƯỚC trong lúc BE soát, đính xong lấy các trang đã soát rồi
// mới điền. Dữ liệu giả.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const strip = (src) => src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const read = (name) => strip(fs.readFileSync(path.join(__dirname, "..", name), "utf8"));
const popup = read("popup.js");
const content = read("content.js");
const engine = read("content/procedures/business-registration.js");
const background = read("background.js");

function extract(src, name) {
  const start = src.search(new RegExp(`function ${name}\\(`));
  assert.ok(start >= 0, `thiếu ${name}`);
  let depth = 0;
  for (let i = src.indexOf("{", start); i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}" && --depth === 0) return src.slice(start, i + 1);
  }
  throw new Error(`không tách được ${name}`);
}

test("popup chỉ khai secondPassHkd cho hồ sơ thành lập mới đọc từ tệp, gửi mã lượt điền cho engine", () => {
  assert.match(popup, /const hkdSecondPass = cfg\.secondPass === "hkd" && !isAmendmentWorkflow && !cfg\.enterprisePortal && !toKhai;/);
  assert.match(popup, /if \(hkdSecondPass\) options\.fillSupports = \["secondPassHkd"\];/);
  const at = popup.indexOf('if (hkdSecondPass) options.fillSupports');
  assert.ok(at > 0 && at < popup.indexOf("const res = await api.process({ procedure: cfg.key, options, files: toKhai ? [] : payloadFiles });"));
  // BE không soát (đợt 2 tắt / ngoài diện thí điểm / quá tải) → giữ thứ tự cũ: chỉ bật khi BE báo đang soát.
  assert.match(popup, /const sp = await api\.secondPass\(businessFillSupportCode\)\.catch\(\(\) => null\);\s*secondPassOn = sp\?\.status === "pending" \|\| sp\?\.status === "done";/);
  assert.match(popup, /secondPass: secondPassOn \? \{ requestId: businessFillSupportCode, at: secondPassAt \} : null,/);
});

test("đính kèm trước: nhánh máy đính kèm đứng chờ cán bộ thì báo lỗi để máy điền chạy tiếp", () => {
  const upload = extract(engine, "handleUploadPhase");
  assert.match(upload, /if \(st\.thenFill\) return void failAttachAll\("Chưa thấy ô tải tệp trên trang đính kèm\."\);/);
  const step = extract(engine, "stepAttachAll");
  assert.equal((step.match(/if \(st\.thenFill\) return void failAttachAll\(/g) || []).length, 2);
});

test("dừng tiến trình xoá cả bản sao state trong sessionStorage", () => {
  assert.match(extract(content, "cancelFillAll"), /sessionStorage\.removeItem\("__af_fillall_state_mirror"\)/);
  assert.match(engine, /const FILLALL_SESSION_MIRROR_KEY = "__af_fillall_state_mirror";/);
});

test("content chỉ bật đính kèm trước khi có cả mã lượt soát lẫn kế hoạch đính kèm", () => {
  const start = content.indexOf('if (msg?.action === "startFillAllBusiness")');
  const block = content.slice(start, content.indexOf('if (msg?.action === "startChangeBusiness")', start));
  assert.match(block, /secondPass: \(msg && msg\.secondPass && msg\.secondPass\.requestId\) \? msg\.secondPass : null,/);
  assert.match(block, /attachFirst: !!\(msg && msg\.secondPass && msg\.secondPass\.requestId && msg\.attachPayload\),/);
  assert.match(content, /H\.withFinalTaxPass = withFinalTaxPass;/);
});

test("máy điền: mở hồ sơ → đính kèm trước → chờ soát → mới điền; đang đính thì nhường máy đính kèm", () => {
  const body = extract(engine, "stepFillAll");
  const boot = body.indexOf("return void stepCreateBootstrap(st);");
  const parked = body.indexOf('if (st.phase === "attaching-first") return;');
  const attach = body.indexOf("if (st.attachFirst && !st.attachFirstDone) return void startAttachFirst(st);");
  const wait = body.indexOf("if (st.secondPass && !st.secondPassDone) return void awaitSecondPass(st);");
  assert.ok(boot > 0 && parked > boot && attach > parked && wait > attach);
  assert.ok(wait < body.indexOf('if (st.phase === "probing-owner")'));
});

test("đính kèm trước xong / lỗi quay về máy điền; lỗi thì giữ kế hoạch để đính lại sau khi điền", () => {
  assert.match(extract(engine, "finishAttachAll"), /if \(st && st\.thenFill\) return void resumeFillAfterAttach\(true, ""\);/);
  assert.match(extract(engine, "failAttachAll"), /if \(st && st\.thenFill\) return void resumeFillAfterAttach\(false, msg\);/);
  const resume = extract(engine, "resumeFillAfterAttach");
  assert.match(resume, /if \(ok\) st\.attachPayload = null;/);
  assert.match(resume, /st\.attachFirstDone = true;/);
  assert.match(extract(engine, "startAttachFirst"), /H\.startAttachAllBusiness\(payload\.files, payload\.attachments, st\.businessDefaults, \{ thenFill: true \}\)/);
});

test("ghép kết quả soát: thay nguyên trang có trong state, bỏ khoá page/from/by, tính lại lượt chốt thuế", () => {
  const H = { withFinalTaxPass: (order, pages) => (pages.tax?.[0]?.value === "1" ? [...order, "tax"] : order) };
  const ctx = { H };
  vm.runInNewContext(`${extract(engine, "mergeSecondPassPages")}; this.merge = mergeSecondPassPages;`, ctx);
  const st = {
    order: ["dia-chi", "tax", "nguoi-nop"],
    pages: { "dia-chi": [{ name: "ward", value: "Xa Cu" }, { name: "street", value: "Thon A" }], tax: [{ name: "r", value: "0" }],
      "nguoi-nop": [{ name: "n", value: "x" }] },
  };
  const keys = ctx.merge(st, [
    { page: "dia-chi", name: "ward", comp: "dom-select", value: "Xa Moi", from: "Xa Cu", by: "dia_chi" },
    { page: "dia-chi", name: "street", comp: "dom-input", value: "Thon A" },
    { page: "tax", name: "r", value: "1" },
    { page: "khong-co", name: "z", value: "1" },
    { name: "khong-trang", value: "1" },
  ]);
  assert.deepEqual(keys, ["dia-chi", "tax"]);
  assert.deepEqual(st.pages["dia-chi"], [{ name: "ward", comp: "dom-select", value: "Xa Moi" }, { name: "street", comp: "dom-input", value: "Thon A" }]);
  assert.deepEqual(st.pages["nguoi-nop"], [{ name: "n", value: "x" }]);
  assert.deepEqual(st.order, ["dia-chi", "tax", "nguoi-nop", "tax"]);
  assert.equal(st.pages["khong-co"], undefined);
});

test("chờ soát có hạn tính từ lúc BE trả lượt điền; hết hạn / không có thì điền theo lượt đầu", () => {
  const wait = extract(engine, "awaitSecondPass");
  assert.match(engine, /const SECOND_PASS_WAIT_MS = 30000;/);
  assert.match(wait, /const deadline = Number\(sp\.at \|\| Date\.now\(\)\) \+ SECOND_PASS_WAIT_MS;/);
  assert.match(wait, /if \(res\?\.status !== "pending" \|\| Date\.now\(\) \+ SECOND_PASS_POLL_MS > deadline\) break;/);
  assert.match(wait, /const fresh = await getFillAllState\(\);\s*if \(!fresh\) return;/);
  assert.match(wait, /fresh\.secondPassDone = true;/);
});

test("background hỏi kết quả soát bằng token của tài khoản, lỗi → none", () => {
  assert.match(background, /if \(msg\?\.action === "hkdSecondPass"\) \{\s*fetchSecondPass\(String\(msg\.requestId \|\| ""\)\)\.then\(sendResponse, \(\) => sendResponse\(\{ status: "none" \}\)\);\s*return true;/);
  const fetchFn = extract(background, "fetchSecondPass");
  assert.match(fetchFn, /\/api\/v1\/process\/\$\{encodeURIComponent\(requestId\)\}\/second-pass/);
  assert.match(fetchFn, /refreshSubmitTokens\(base, tokens\)/);
  assert.match(fetchFn, /return \{ status: "none" \};\s*\}$/);
});
