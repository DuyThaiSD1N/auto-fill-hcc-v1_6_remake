const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");

test("Trợ lý nhân dân dùng backend chung và được cấp quyền HTTPS/WSS", () => {
  const config = fs.readFileSync(path.join(root, "api/config.js"), "utf8");
  const manifest = JSON.parse(fs.readFileSync(path.join(root, "manifest.json"), "utf8"));

  // Hai chế độ hợp lệ:
  //   PHÁT HÀNH — chính tiengnoi + phụ vnekyc (failover bật).
  //   DEV       — localhost:12005 (docker app), failover TẮT.
  // Test chấp nhận cả hai nhưng vẫn KHÓA chặt từng chế độ, để đổi nhầm nửa vời (vd trỏ localhost
  // mà quên tắt failover → request rơi sang server thật) vẫn bị bắt.
  const devBase = /const TLND_DEFAULT_BASE_URL = "http:\/\/localhost:12005";/.test(config);
  if (devBase) {
    assert.match(
      config,
      /const TLND_FALLBACK_BASE_URL = "";/,
      "trỏ localhost thì PHẢI tắt failover, nếu không request rớt sang server thật",
    );
    for (const perm of ["http://localhost:12005/*", "ws://localhost:12005/*"]) {
      assert.ok(manifest.host_permissions.includes(perm), `thiếu quyền ${perm}`);
    }
    // Base URL cũ còn nằm trong storage của bản đang cài sẽ ĐÈ hằng số ở trên → phải nằm trong
    // danh sách migrate, nếu không extension vẫn gọi production và tưởng code mới không chạy.
    for (const host of ["trolyhoso-hcc.tiengnoi.vn", "trolyhoso-hcc.vnekyc.vn"]) {
      assert.ok(
        config.includes(`"https://${host}"`),
        `TLND_LEGACY_BASE_URLS thiếu ${host} → storage cũ vẫn trỏ production`,
      );
    }
  } else {
    assert.match(
      config,
      /const TLND_DEFAULT_BASE_URL = "https:\/\/trolyhoso-hcc\.tiengnoi\.vn";/,
    );
    assert.match(
      config,
      /const TLND_FALLBACK_BASE_URL = "https:\/\/trolyhoso-hcc\.vnekyc\.vn";/,
    );
  }
  assert.match(config, /TLND_LEGACY_BASE_URLS\.has\(v\)/);

  // Dù đang ở chế độ nào, quyền HTTPS/WSS của hai backend production KHÔNG được xóa khỏi manifest
  // — nếu không, lúc trả về production sẽ mất quyền gọi API/WebSocket.
  for (const host of ["trolyhoso-hcc.tiengnoi.vn", "trolyhoso-hcc.vnekyc.vn"]) {
    assert.ok(manifest.host_permissions.includes(`https://${host}/*`), `thiếu https ${host}`);
    assert.ok(manifest.host_permissions.includes(`wss://${host}/*`), `thiếu wss ${host}`);
  }
});
