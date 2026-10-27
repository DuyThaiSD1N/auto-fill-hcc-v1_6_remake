const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const watchSource = fs.readFileSync(path.join(root, "content/moj-upload-watch-main.js"), "utf8");
const contentSource = fs.readFileSync(path.join(root, "content.js"), "utf8");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

const EVENT = "__HCC_MOJ_FILE_API__";

// Trang giả: XHR tự bắn "loadend" khi test gọi finish(status); fetch trả status cấu hình sẵn.
function setupPage({ hostname = "dichvucongnganhtuphap.moj.gov.vn", fetchStatus = 200, fetchReject = false } = {}) {
  const events = [];
  class FakeXHR {
    constructor() { this.listeners = {}; this.status = 0; this.responseText = ""; }
    open(method, url) { this.url = url; }
    send() { FakeXHR.sent.push(this); }
    addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
    finish(status, body = "") {
      this.status = status;
      this.responseText = body;
      for (const fn of this.listeners.loadend || []) fn();
    }
  }
  FakeXHR.sent = [];
  const window = {
    XMLHttpRequest: FakeXHR,
    fetch: () => (fetchReject
      ? Promise.reject(new Error("Failed to fetch"))
      : Promise.resolve({ status: fetchStatus, clone: () => ({ text: () => Promise.resolve("Bad Gateway") }) })),
  };
  const context = {
    window,
    location: { hostname, href: `https://${hostname}/nop-ho-so/1` },
    document: { dispatchEvent: (event) => { events.push(JSON.parse(event.detail)); return true; } },
    CustomEvent: class { constructor(type, init) { this.type = type; this.detail = init.detail; } },
    URL,
  };
  vm.runInNewContext(watchSource, context);
  return { window, FakeXHR, events };
}

test("manifest nạp script theo dõi API ở MAIN world, chỉ trên cổng moj", () => {
  const entry = manifest.content_scripts.find((item) => (item.js || []).includes("content/moj-upload-watch-main.js"));
  assert.ok(entry);
  assert.equal(entry.world, "MAIN");
  assert.equal(entry.run_at, "document_start");
  assert.deepEqual(entry.matches, ["https://dichvucongnganhtuphap.moj.gov.vn/*"]);
});

test("XHR tới API tải tệp: báo mã HTTP lỗi kèm nội dung, báo cả 200", () => {
  const { window, FakeXHR, events } = setupPage();
  const upload = new window.XMLHttpRequest();
  upload.open("POST", "https://apidvc.moj.gov.vn/api/File/upload");
  upload.send();
  const update = new window.XMLHttpRequest();
  update.open("POST", "https://apidvc.moj.gov.vn/api/File/cap-nhat-tai-lieu-ca-nhan");
  update.send();
  FakeXHR.sent[0].finish(500, "Internal Server Error");
  FakeXHR.sent[1].finish(200, '{"statusCode":"00"}');

  const ends = events.filter((event) => event.phase === "end");
  assert.deepEqual(ends.map((event) => [event.path, event.status]), [
    ["/api/File/upload", 500],
    ["/api/File/cap-nhat-tai-lieu-ca-nhan", 200],
  ]);
  assert.equal(ends[0].message, "Internal Server Error");
  assert.equal(ends[1].message, "", "2xx không cần đọc nội dung");
});

test("XHR không phải API tải tệp thì bỏ qua; không đọc header", () => {
  const { window, FakeXHR, events } = setupPage();
  const other = new window.XMLHttpRequest();
  other.open("GET", "https://apidvc.moj.gov.vn/api/HoSo/chi-tiet");
  other.send();
  FakeXHR.sent[0].finish(500);
  assert.equal(events.length, 0);
  assert.doesNotMatch(watchSource, /getResponseHeader|getAllResponseHeaders|authorization/i);
});

test("lỗi mạng (status 0) và fetch lỗi cũng được báo", async () => {
  const xhrPage = setupPage();
  const xhr = new xhrPage.window.XMLHttpRequest();
  xhr.open("POST", "/api/File/upload");
  xhr.send();
  xhrPage.FakeXHR.sent[0].finish(0);
  assert.equal(xhrPage.events.at(-1).status, 0);

  const fetchPage = setupPage({ fetchStatus: 502 });
  await fetchPage.window.fetch("https://apidvc.moj.gov.vn/api/File/upload", { method: "POST" });
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual([fetchPage.events.at(-1).status, fetchPage.events.at(-1).message], [502, "Bad Gateway"]);

  const rejectPage = setupPage({ fetchReject: true });
  await assert.rejects(rejectPage.window.fetch("https://apidvc.moj.gov.vn/api/File/upload"));
  assert.equal(rejectPage.events.at(-1).status, 0);
});

test("ngoài cổng moj thì không bọc XHR/fetch", () => {
  const { window, FakeXHR, events } = setupPage({ hostname: "dichvucong.gov.vn" });
  const xhr = new window.XMLHttpRequest();
  xhr.open("POST", "/api/File/upload");
  xhr.send();
  FakeXHR.sent[0].finish(500);
  assert.equal(events.length, 0);
});

// Khối nhận sự kiện trong content.js: chạy thật trong vm để kiểm mốc + chỉ xét mã HTTP.
function loadEngineBlock() {
  const start = contentSource.indexOf("const MOJ_FILE_API_EVENT");
  const endMarker = "function newMojFileApiFailure";
  const fnStart = contentSource.indexOf(endMarker, start);
  const fnEnd = contentSource.indexOf("\n  }\n", fnStart) + 4;
  assert.ok(start > 0 && fnStart > start && fnEnd > fnStart);
  const listeners = [];
  const context = {
    document: { addEventListener: (type, fn) => listeners.push([type, fn]) },
  };
  vm.runInNewContext(
    `${contentSource.slice(start, fnEnd)}\nthis.api = { mojFileApiMark, newMojFileApiFailure };`,
    context,
  );
  const fire = (detail) => listeners.forEach(([type, fn]) => type === EVENT && fn({ detail: JSON.stringify(detail) }));
  return { api: context.api, fire };
}

test("engine chỉ nhận lỗi HTTP xảy ra SAU mốc của tệp đang đính", () => {
  const { api, fire } = loadEngineBlock();
  fire({ phase: "end", path: "/api/File/upload", status: 500, message: "cũ" });
  const mark = api.mojFileApiMark();
  assert.equal(api.newMojFileApiFailure(mark), "", "lỗi của tệp trước không tính cho tệp này");

  fire({ phase: "start", path: "/api/File/upload" });
  fire({ phase: "end", path: "/api/File/upload", status: 200 });
  assert.equal(api.newMojFileApiFailure(mark), "", "2xx là bình thường");

  fire({ phase: "end", path: "/api/File/cap-nhat-tai-lieu-ca-nhan", status: 504, message: "Gateway Timeout" });
  assert.equal(
    api.newMojFileApiFailure(mark),
    "API /api/File/cap-nhat-tai-lieu-ca-nhan trả HTTP 504: Gateway Timeout",
  );

  const mark2 = api.mojFileApiMark();
  fire({ phase: "end", path: "/api/File/upload", status: 0 });
  assert.equal(api.newMojFileApiFailure(mark2), "API /api/File/upload trả lỗi mạng");
});

test("vòng đính qua ví dùng lỗi API làm lưới thứ hai cạnh toast", () => {
  assert.match(contentSource, /const apiMark = mojFileApiMark\(\);\n\s*const uploadFailed = \(\) => newPortalUploadFailure\(failuresBefore\) \|\| newMojFileApiFailure\(apiMark\);/);
  assert.match(contentSource, /const portalError = readPortalUploadError\(\) \|\| newMojFileApiFailure\(apiMark\);/);
});
