const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");

function readBase(config, name) {
  const m = config.match(new RegExp(`const ${name} = "([^"]*)"`));
  assert.ok(m, `không tìm thấy ${name} trong api/config.js`);
  return m[1].replace(/\/+$/, "");
}

test("Backend CHÍNH/PHỤ của Trợ lý người dân đều được cấp quyền HTTP/WS trong manifest", () => {
  const config = fs.readFileSync(path.join(root, "api/config.js"), "utf8");
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

  // Base có thể là prod (https://…) hoặc local khi thử FE (http://localhost:12005); backend PHỤ
  // để trống = tắt failover. Bất kể trỏ đâu, manifest phải cấp quyền cả HTTP lẫn WS cho origin đó,
  // nếu không extension không gọi được API/WebSocket.
  const bases = [
    readBase(config, "TLND_DEFAULT_BASE_URL"),
    readBase(config, "TLND_FALLBACK_BASE_URL"),
  ].filter(Boolean);
  assert.ok(bases.length >= 1, "phải có backend CHÍNH");

  for (const base of bases) {
    const u = new URL(base);
    const wsScheme = u.protocol === "https:" ? "wss" : "ws";
    assert.ok(
      manifest.host_permissions.includes(`${u.protocol}//${u.host}/*`),
      `thiếu quyền ${u.protocol}//${u.host}/*`,
    );
    assert.ok(
      manifest.host_permissions.includes(`${wsScheme}://${u.host}/*`),
      `thiếu quyền ${wsScheme}://${u.host}/*`,
    );
  }

  assert.match(config, /TLND_LEGACY_BASE_URLS\.has\(v\)/);
});
