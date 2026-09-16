// Contract luồng "Đăng ký thay đổi nội dung hộ kinh doanh" (HkdOnline, workflow change):
// adapter nhận workflow/businessFlow từ BE (không hardcode create/8 trang), engine change
// có stage home + stopAtStage (dừng ở màn tra cứu nhận giấy tờ) + delay trước khi điền.
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const adapter = read("content/business-registration-adapter.js");
const engine = read("content/procedures/business-registration.js");
const sidebar = read("sidebar.js");
const content = read("content.js");

test("adapter: workflow/businessFlow từ action BE, order động, không hardcode create", () => {
  assert.ok(adapter.includes("function workflowOf(msg)"));
  assert.ok(adapter.includes("stopAtStage: String(msg?.stop_at"));
  assert.ok(/businessFlow\.pageOrder\.length\s*\?\s*\[\.\.\.businessFlow\.pageOrder\]/.test(adapter),
    "order phải lấy từ businessFlow.pageOrder khi có (trang động của luồng change)");
  assert.ok(adapter.includes("businessSearch: businessFlow?.search || null"),
    "thiếu businessSearch thì stepChangeBootstrap không tra cứu được hộ KD");
  // Regex phase phải nhận 2 màn wizard riêng của luồng change.
  assert.ok(adapter.includes("search-business|select-change"));
  // Không còn `workflow: "create"` hardcode trong startPrepare/startFullRun.
  assert.ok(!/workflow:\s*"create",/.test(adapter));
});

test("engine change: nhận stage home, stopAtStage, delay ~5s khi vào Khối dữ liệu", () => {
  // Handfree đáp xuống TRANG CHỦ HkdOnline → luồng change phải tự bấm menu như create.
  assert.match(engine, /function detectBusinessChangeStage\(\) \{[\s\S]{0,900}stage: "home"/);
  assert.ok(engine.includes("st.stopAtStage && detected.stage === st.stopAtStage"));
  // Câu bắt đầu + nghỉ ~5 giây trước khi điền các khối (yêu cầu nghiệp vụ 09/09).
  assert.match(engine, /Em bắt đầu điền các khối cần sửa[\s\S]{0,200}await sleep\(5000\)/);
  // Owner-probe + chốt lại địa chỉ thuế đã được đồng bộ từ auto-fill.
  assert.ok(engine.includes("function handleOwnerProbe"));
  assert.ok(engine.includes("function taxWantsSameAsHeadOffice"));
  assert.ok(engine.includes("const OWNER_CHANGE_TYPE_FIELDS"));
  // Guard handfree phải SỐNG SÓT qua đồng bộ engine.
  assert.match(engine, /async function stepFillAll\(\) \{[\s\S]{0,300}isBusinessRunCancelled/);
  assert.match(engine, /async function advanceFillAll\([\s\S]{0,120}isBusinessRunCancelled/);
  assert.ok(engine.includes("stepCreateBootstrap(st)"), "dispatch bootstrap thành lập mới phải còn");
  assert.ok(engine.includes("detectBusinessAnyStage"));
});

test("page_status dùng stage GỘP (create + change) để BE thấy search-business/select-change", () => {
  assert.ok(content.includes("detectBusinessAnyStage"));
  assert.ok(adapter.includes("detectBusinessAnyStage"));
});

test("sidebar chuyển tiếp ĐỦ tham số change ở CẢ prepare lẫn start (bug 09/09: sót start → đơ)", () => {
  assert.ok(sidebar.includes('stop_at: a.stop_at || ""'));
  assert.ok(sidebar.includes("Đang mở luồng Đăng ký thay đổi hộ kinh doanh"));
  // start_business_registration PHẢI mang workflow + businessFlow xuống adapter —
  // thiếu là adapter default create, bootstrap sai màn rồi đứng im.
  const start = sidebar.indexOf('action: "startBusinessRegistration"');
  assert.ok(start > 0);
  const block = sidebar.slice(start, start + 700);
  assert.ok(block.includes('workflow: a.workflow || ""'));
  assert.ok(block.includes("businessFlow: a.businessFlow || null"));
  // prepare cũng mang workflow (khối riêng phía trên).
  const prepare = sidebar.indexOf('action: "prepareBusinessRegistration"');
  assert.ok(sidebar.slice(prepare, prepare + 300).includes('workflow: a.workflow || ""'));
});
