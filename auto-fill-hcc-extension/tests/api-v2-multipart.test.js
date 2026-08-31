const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { Blob } = require("node:buffer");

const root = path.join(__dirname, "..");
const endpointSource = fs.readFileSync(path.join(root, "api", "endpoints.js"), "utf8");
const clientSource = fs.readFileSync(path.join(root, "api", "client.js"), "utf8");

class TestFormData {
  constructor() { this.items = []; }
  append(name, value, filename) { this.items.push({ name, value, filename }); }
  get(name) { return this.items.find((item) => item.name === name)?.value ?? null; }
  getAll(name) { return this.items.filter((item) => item.name === name).map((item) => item.value); }
}

const calls = [];
const sandbox = {
  Blob,
  FormData: TestFormData,
  Uint8Array,
  JSON,
  console,
  atob: (value) => Buffer.from(value, "base64").toString("binary"),
  decodeURIComponent,
  apiJson: async (requestPath, options) => {
    calls.push({ requestPath, options });
    return { ok: true };
  },
  backendFetch: async () => ({ ok: true, status: 200, json: async () => ({}) }),
  BACKEND_URL: "https://backend.test",
};

vm.runInNewContext(`${endpointSource}
globalThis.testApi = api;
globalThis.testBuildV2ProcessForm = buildV2ProcessForm;
`, sandbox);

(async () => {
  const binary = Buffer.from("noi-dung-pdf");
  const file = {
    name: "ho-so.pdf",
    type: "application/pdf",
    role: "doc",
    dataUrl: `data:application/pdf;base64,${binary.toString("base64")}`,
  };

  await sandbox.testApi.process({ procedure: "khai-tu", options: { requestMode: "full" }, files: [file] });
  await sandbox.testApi.attachmentPlan({
    procedure: "khai-tu",
    options: { sessionId: "req_previous", attachmentContext: { components: [] } },
    files: [file],
  });
  await sandbox.testApi.clientAttachmentTrace({
    procedure: "chung-thuc-chu-ky-nguoi-dich-ctv",
    options: { splitMode: true },
    files: [{ name: "Ban_dich.pdf", type: "application/pdf", size: 12 }],
    attachments: [{ fileIndex: 0, documentName: "Ban_dich" }],
  });

  assert.equal(calls.length, 3);
  assert.equal(calls[0].requestPath, "/api/v2/process");
  assert.equal(calls[1].requestPath, "/api/v2/process");
  assert.equal(calls[2].requestPath, "/api/v1/attachments/client-trace");
  assert.equal(calls[0].options.body.get("action"), "fill");
  assert.equal(calls[1].options.body.get("action"), "attach");
  assert.equal(calls[0].options.body.get("procedure"), "khai-tu");
  assert.deepEqual(JSON.parse(calls[1].options.body.get("options")), {
    sessionId: "req_previous",
    attachmentContext: { components: [] },
    // attachmentPlan báo NĂNG LỰC đính kèm của extension cho BE (tương thích ngược).
    extVersion: "",
    attachSupports: ["attp-row", "fixed-slot", "add-document-dialog", "fixed-slot+add-document-dialog"],
  });

  const metadata = JSON.parse(calls[0].options.body.get("fileMetadata"));
  assert.equal(metadata[0].name, "ho-so.pdf");
  assert.equal(metadata[0].role, "doc");
  const blob = calls[0].options.body.getAll("files")[0];
  assert.equal(blob.type, "application/pdf");
  assert.deepEqual(Buffer.from(await blob.arrayBuffer()), binary);

  const clientTraceBody = JSON.parse(calls[2].options.body);
  assert.equal(clientTraceBody.files[0].name, "Ban_dich.pdf");
  assert.equal(clientTraceBody.files[0].size, 12);
  assert.equal("dataUrl" in clientTraceBody.files[0], false);
  assert.equal(calls[2].options.body.includes(binary.toString("base64")), false);

  // HTTP client phải giữ nguyên FormData và không tự gắn Content-Type JSON/boundary sai.
  let fetchInit = null;
  const clientSandbox = {
    FormData: TestFormData,
    BACKEND_URL: "https://backend.test",
    AuthStore: { getTokens: async () => ({ accessToken: "token" }) },
    fetch: async (_url, init) => {
      fetchInit = init;
      return { ok: true, status: 200, text: async () => "{}" };
    },
    chrome: { runtime: { sendMessage() {}, lastError: null } },
    JSON,
  };
  vm.runInNewContext(`${clientSource}
globalThis.testApiCall = apiCall;
`, clientSandbox);
  const form = new TestFormData();
  form.append("action", "fill");
  await clientSandbox.testApiCall("/api/v2/process", { method: "POST", body: form });
  assert.equal(fetchInit.body, form);
  assert.equal(fetchInit.headers.Authorization, "Bearer token");
  assert.equal(fetchInit.headers["Content-Type"], undefined);

  console.log("api v2 multipart: fill/attach share endpoint and binary body is preserved");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
