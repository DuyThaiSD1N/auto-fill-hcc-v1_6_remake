const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");

function declaredBase(config, name) {
  const m = new RegExp(`const ${name} = "([^"]*)";`).exec(config);
  assert.ok(m, `không tìm thấy khai báo ${name} trong api/config.js`);
  return m[1].replace(/\/+$/, "");
}

// Base nào khai trong api/config.js cũng PHẢI được cấp quyền trong manifest — thiếu là extension
// không gọi được API/WebSocket. Kiểm theo giá trị ĐANG khai (local hay production đều đúng) thay vì
// ghim cứng domain, để lúc trỏ về localhost hay đẩy lại prod đều không phải sửa test.
test("Base backend khai trong config đều được cấp quyền host trong manifest", () => {
  const config = fs.readFileSync(path.join(root, "api/config.js"), "utf8");
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

  const primary = declaredBase(config, "TLND_DEFAULT_BASE_URL");
  const fallback = declaredBase(config, "TLND_FALLBACK_BASE_URL"); // TRỐNG = tắt failover
  assert.ok(primary, "TLND_DEFAULT_BASE_URL không được để trống");

  for (const base of [primary, fallback].filter(Boolean)) {
    const { protocol, host } = new URL(base);
    const ws = protocol === "https:" ? "wss" : "ws";
    assert.ok(
      manifest.host_permissions.includes(`${protocol}//${host}/*`),
      `thiếu quyền ${protocol}//${host}/*`,
    );
    assert.ok(
      manifest.host_permissions.includes(`${ws}://${host}/*`),
      `thiếu quyền ${ws}://${host}/*`,
    );
  }

  // Storage của bản đã cài có thể còn domain Handfree cũ — phải giữ nhánh migrate.
  assert.match(config, /TLND_LEGACY_BASE_URLS\.has\(v\)/);
});
