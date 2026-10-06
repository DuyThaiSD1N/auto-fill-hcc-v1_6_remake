const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");

test("Trợ lý nhân dân dùng backend chung và được cấp quyền HTTPS/WSS", () => {
  const config = fs.readFileSync(path.join(root, "api/config.js"), "utf8");
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

  // Backend CHÍNH (tiengnoi) + backend PHỤ failover (vnekyc) là domain API của backend: cả hai
  // đều phải được cấp quyền HTTPS/WSS trong manifest, nếu không extension không gọi được API/WS.
  assert.match(
    config,
    /const TLND_DEFAULT_BASE_URL = "https:\/\/trolyhoso-hcc-admin\.tiengnoi\.vn";/,
  );
  // Server phụ đang TẮT (khác database → refresh token không tồn tại, dữ liệu ghi lệch).
  assert.match(config, /const TLND_FALLBACK_BASE_URL = "";/);
  assert.match(config, /TLND_LEGACY_BASE_URLS\.has\(v\)/);
  // Máy đã cài còn lưu domain FE cũ trong storage → phải được chuyển sang backend chính.
  for (const legacy of ["trolyhoso-hcc.tiengnoi.vn", "trolyhoso-hcc.vnekyc.vn"]) {
    assert.ok(config.includes(`"https://${legacy}",`), `thiếu legacy ${legacy}`);
  }
  for (const host of ["trolyhoso-hcc-admin.tiengnoi.vn", "trolyhoso-hcc-admin.vnekyc.vn"]) {
    assert.ok(manifest.host_permissions.includes(`https://${host}/*`), `thiếu https ${host}`);
    assert.ok(manifest.host_permissions.includes(`wss://${host}/*`), `thiếu wss ${host}`);
  }
});
