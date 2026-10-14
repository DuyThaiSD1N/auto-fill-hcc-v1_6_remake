const assert = require("node:assert/strict");
const { webcrypto } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const credentialSource = fs.readFileSync(path.join(root, "api", "credentials.js"), "utf8");
const sidebarSource = fs.readFileSync(path.join(root, "sidebar.js"), "utf8");
const authSource = fs.readFileSync(path.join(root, "api", "auth.js"), "utf8");
const htmlSource = fs.readFileSync(path.join(root, "sidebar.html"), "utf8");
const cssSource = fs.readFileSync(path.join(root, "sidebar.css"), "utf8");

const browserStoreMarker = credentialSource.indexOf("\nconst RememberedLoginStore =");
assert.ok(browserStoreMarker > 0, "Không tách được factory kho thông tin đăng nhập");
const sandbox = { crypto: webcrypto, TextEncoder, TextDecoder, Date };
vm.runInNewContext(`${credentialSource.slice(0, browserStoreMarker)}
  globalThis.createVault = createRememberedLoginVault;
  globalThis.keyId = REMEMBERED_LOGIN_KEY_ID;
  globalThis.dataId = REMEMBERED_LOGIN_DATA_ID;
`, sandbox);

function createMemoryRepository() {
  const records = new Map();
  return {
    records,
    async getMany(ids) {
      return ids.map((id) => records.get(id) || null);
    },
    async put(record) {
      records.set(record.id, structuredClone(record));
    },
    async clear() {
      records.clear();
    },
  };
}

test("thông tin ghi nhớ được mã hóa AES-GCM và fail closed khi dữ liệu hỏng", async () => {
  const repository = createMemoryRepository();
  const vault = sandbox.createVault(repository, webcrypto);
  const username = "canbo-test";
  const password = "Mat-khau-rieng-123!";

  await vault.save(username, password);

  const keyRecord = repository.records.get(sandbox.keyId);
  const dataRecord = repository.records.get(sandbox.dataId);
  assert.equal(keyRecord.value.extractable, false);
  assert.equal(keyRecord.value.algorithm.name, "AES-GCM");
  assert.equal(keyRecord.value.algorithm.length, 256);
  assert.equal(new Uint8Array(dataRecord.iv).byteLength, 12);
  assert.doesNotMatch(JSON.stringify(dataRecord), /canbo-test|Mat-khau-rieng-123/);
  const restored = await vault.get();
  assert.equal(restored.username, username);
  assert.equal(restored.password, password);

  const tampered = structuredClone(dataRecord);
  new Uint8Array(tampered.ciphertext)[0] ^= 0xff;
  await repository.put(tampered);
  assert.equal(await vault.get(), null);
  assert.equal(repository.records.size, 0);
});

test("màn đăng nhập dùng logo HCC và contract ghi nhớ giống Auto Fill", () => {
  const credentialsScript = htmlSource.indexOf('<script src="api/credentials.js"></script>');
  const sidebarScript = htmlSource.indexOf('<script src="sidebar.js"></script>');

  assert.ok(credentialsScript > 0 && credentialsScript < sidebarScript);
  assert.match(htmlSource, /id="remember-login"[\s\S]*id="forget-login-btn"/);
  assert.match(sidebarSource, /BRAND_ICON\(46, "brand-icon-login"\)/);
  assert.doesNotMatch(sidebarSource, /getElementById\("login-avatar"\)\.innerHTML = ROBOT/);
  assert.match(cssSource, /\.brand-icon-login/);
  assert.match(sidebarSource, /CAN_REMEMBER_LOGIN = chrome\.extension\?\.inIncognitoContext !== true/);
  assert.match(sidebarSource, /prefillLogin\(\)[\s\S]*RememberedLoginStore\.get\(\)/);
  assert.match(sidebarSource, /remember-login/);
  assert.match(sidebarSource, /forget-login-btn/);
  assert.match(sidebarSource, /RememberedLoginStore\.clear\(\)/);
  assert.match(sidebarSource, /invalidRememberedLogin[\s\S]*Thông tin đã nhớ đã được xóa/);
  assert.match(authSource, /error\.status = res\.status/);

  const loginAt = sidebarSource.indexOf("await window.tlndAuth.login(u, p)");
  const saveAt = sidebarSource.indexOf("await window.RememberedLoginStore.save(u, p)");
  assert.ok(loginAt > 0 && saveAt > loginAt, "Chỉ lưu mật khẩu sau khi API đăng nhập thành công");
});
