const assert = require("node:assert/strict");
const { webcrypto } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.join(__dirname, "..");
const credentialSource = fs.readFileSync(path.join(root, "api", "credentials.js"), "utf8");
const popupSource = fs.readFileSync(path.join(root, "popup.js"), "utf8");
const htmlSource = fs.readFileSync(path.join(root, "popup.html"), "utf8");

// Chỉ nạp factory crypto; không khởi tạo IndexedDB thật trong Node.
const browserStoreMarker = credentialSource.indexOf("\nconst RememberedLoginStore =");
assert.ok(browserStoreMarker > 0, "Không tách được factory kho thông tin đăng nhập");
const sandbox = {
  crypto: webcrypto,
  TextEncoder,
  TextDecoder,
  Date,
};
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

(async () => {
  const repository = createMemoryRepository();
  const vault = sandbox.createVault(repository, webcrypto);
  const username = "test1";
  const password = "Mat-khau-rieng-123!";

  await vault.save(username, password);

  const keyRecord = repository.records.get(sandbox.keyId);
  const dataRecord = repository.records.get(sandbox.dataId);
  assert.ok(keyRecord?.value, "Phải tạo khóa AES");
  assert.equal(keyRecord.value.extractable, false, "Khóa AES không được phép export raw");
  assert.equal(keyRecord.value.algorithm.name, "AES-GCM");
  assert.equal(keyRecord.value.algorithm.length, 256);
  assert.equal(new Uint8Array(dataRecord.iv).byteLength, 12, "AES-GCM dùng IV 96-bit");

  const persisted = JSON.stringify(dataRecord);
  assert.doesNotMatch(persisted, /test1|Mat-khau-rieng-123/,
    "Bản ghi IndexedDB không được chứa tài khoản/mật khẩu dạng rõ");

  const restored = await vault.get();
  assert.equal(restored.username, username);
  assert.equal(restored.password, password);

  // Cùng credential nhưng mã hóa lại phải có ciphertext/IV khác.
  const firstIv = Buffer.from(dataRecord.iv).toString("hex");
  const firstCiphertext = Buffer.from(dataRecord.ciphertext).toString("hex");
  await vault.save(username, password);
  const second = repository.records.get(sandbox.dataId);
  assert.notEqual(Buffer.from(second.iv).toString("hex"), firstIv);
  assert.notEqual(Buffer.from(second.ciphertext).toString("hex"), firstCiphertext);

  // Ciphertext bị sửa phải fail closed và dọn cả khóa lẫn dữ liệu.
  const tampered = structuredClone(second);
  const bytes = new Uint8Array(tampered.ciphertext);
  bytes[0] ^= 0xff;
  await repository.put(tampered);
  assert.equal(await vault.get(), null);
  assert.equal(repository.records.size, 0);

  await assert.rejects(() => vault.save("", password), /Thiếu thông tin đăng nhập/);
  await assert.rejects(() => vault.save(username, ""), /Thiếu thông tin đăng nhập/);

  // Contract UI: file crypto nạp trước popup; chỉ save sau khi API login thành công.
  assert.match(htmlSource, /id="rememberLogin"[\s\S]*id="forgetLoginBtn"/);
  assert.ok(
    htmlSource.indexOf('src="api/credentials.js"') < htmlSource.indexOf('src="popup.js"'),
    "Kho credential phải nạp trước popup",
  );
  assert.ok(
    popupSource.indexOf("const data = await api.login(username, password)")
      < popupSource.indexOf("await RememberedLoginStore.save(username, password)"),
    "Chỉ lưu credential sau khi backend xác thực thành công",
  );
  assert.match(popupSource, /chrome\.extension\?\.inIncognitoContext !== true/);
  assert.match(popupSource, /rememberLogin\.addEventListener\("change"[\s\S]*clearRememberedLogin/);
  assert.match(popupSource, /forgetLoginBtn\.addEventListener\("click"[\s\S]*clearFields: true/);
  assert.doesNotMatch(popupSource, /CredStore/);

  console.log("remembered login: AES-GCM vault + popup contract passed");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
