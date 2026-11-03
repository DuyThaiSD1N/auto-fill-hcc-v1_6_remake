const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const crypto = require("node:crypto");
const { Blob } = require("node:buffer");

const endpointSource = fs.readFileSync(path.join(__dirname, "..", "api", "endpoints.js"), "utf8");

class TestFormData {
  constructor() { this.items = []; }
  append(name, value, filename) { this.items.push({ name, value, filename }); }
  get(name) { return this.items.find((item) => item.name === name)?.value ?? null; }
  getAll(name) { return this.items.filter((item) => item.name === name).map((item) => item.value); }
}

const calls = [];
let reply = () => ({ fileRefs: true });
const sandbox = {
  Blob, FormData: TestFormData, Uint8Array, Array, JSON, console, decodeURIComponent,
  crypto: globalThis.crypto,
  atob: (value) => Buffer.from(value, "base64").toString("binary"),
  chrome: { runtime: { getManifest: () => ({ version: "9.9.9" }) } },
  apiJson: async (requestPath, options) => {
    calls.push(options.body);
    return reply(options.body);
  },
};
vm.runInNewContext(`${endpointSource}\nglobalThis.testApi = api;`, sandbox);

const toFile = (name, text) => ({
  name, type: "application/pdf", role: "doc",
  dataUrl: `data:application/pdf;base64,${Buffer.from(text).toString("base64")}`,
});
const meta = (form) => JSON.parse(form.get("fileMetadata"));

(async () => {
  const big = toFile("to-khai.pdf", "noi-dung-lon");
  const sha = crypto.createHash("sha256").update("noi-dung-lon").digest("hex");

  // Lượt điền: gửi đủ tệp; BE báo fileRefs → nhớ sha256.
  await sandbox.testApi.process({ procedure: "khai-tu", options: {}, files: [big] });
  assert.equal(calls[0].getAll("files").length, 1);
  assert.equal("stored" in meta(calls[0])[0], false);

  // Lượt đính: tệp cũ chỉ gửi mã, tệp mới gửi nội dung, thứ tự metadata giữ nguyên.
  await sandbox.testApi.attachmentPlan({ procedure: "khai-tu", options: {}, files: [big, toFile("moi.pdf", "moi")] });
  assert.deepEqual(meta(calls[1]).map((m) => m.stored || ""), [sha, ""]);
  assert.equal(calls[1].getAll("files").length, 1);

  // Máy chủ đã xoá tệp → 409 → gửi lại đầy đủ ngay trong cùng lần gọi.
  reply = (form) => {
    if (meta(form).some((m) => m.stored)) {
      const err = new Error("thiếu tệp");
      err.status = 409;
      err.data = { error: "STORED_FILE_MISSING" };
      throw err;
    }
    return { requestId: "req_ok" };
  };
  const res = await sandbox.testApi.attachmentPlan({ procedure: "khai-tu", options: {}, files: [big] });
  assert.equal(res.requestId, "req_ok");
  assert.equal(calls[3].getAll("files").length, 1);
  assert.equal("stored" in meta(calls[3])[0], false);

  // BE không báo fileRefs (bản cũ) → không bao giờ gửi mã.
  await sandbox.testApi.attachmentPlan({ procedure: "khai-tu", options: {}, files: [big] });
  assert.equal("stored" in meta(calls[4])[0], false);

  console.log("api v2 file refs: tệp đã gửi chỉ gửi mã, thiếu thì gửi lại đầy đủ");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
