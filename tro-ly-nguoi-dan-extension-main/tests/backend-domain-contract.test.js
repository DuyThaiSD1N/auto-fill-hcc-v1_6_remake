const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");

test("Trợ lý người dân dùng backend chung và được cấp quyền HTTPS/WSS", () => {
  const config = fs.readFileSync(path.join(root, "api/config.js"), "utf8");
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

  // Backend CHÍNH (tiengnoi) + backend PHỤ failover (vnekyc): cả hai đều phải được cấp
  // quyền HTTPS/WSS trong manifest, nếu không extension không gọi được API/WebSocket.
  assert.match(
    config,
    /const TLND_DEFAULT_BASE_URL = "https:\/\/trolyhoso-hcc\.tiengnoi\.vn";/,
  );
  assert.match(
    config,
    /const TLND_FALLBACK_BASE_URL = "https:\/\/trolyhoso-hcc\.vnekyc\.vn";/,
  );
  assert.match(config, /TLND_LEGACY_BASE_URLS\.has\(v\)/);
  for (const host of ["trolyhoso-hcc.tiengnoi.vn", "trolyhoso-hcc.vnekyc.vn"]) {
    assert.ok(manifest.host_permissions.includes(`https://${host}/*`), `thiếu https ${host}`);
    assert.ok(manifest.host_permissions.includes(`wss://${host}/*`), `thiếu wss ${host}`);
  }
});
