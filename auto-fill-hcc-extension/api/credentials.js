// Kho thông tin đăng nhập được người dùng chủ động chọn ghi nhớ.
//
// TẠI SAO không dùng chrome.storage.local:
// - content script có thể đọc storage.local theo mặc định;
// - mật khẩu là bí mật dài hạn, không được để dạng rõ hoặc đồng bộ qua Chrome Sync.
//
// Username + mật khẩu được mã hóa chung bằng AES-GCM 256-bit. Khóa CryptoKey đặt
// extractable=false và cả khóa/ciphertext chỉ được lưu trong IndexedDB thuộc origin
// chrome-extension://...; trang DVC và content script không dùng chung origin này.

const REMEMBERED_LOGIN_DB = "autofill_hcc_credentials";
const REMEMBERED_LOGIN_DB_VERSION = 1;
const REMEMBERED_LOGIN_STORE = "secrets";
const REMEMBERED_LOGIN_KEY_ID = "aes-key";
const REMEMBERED_LOGIN_DATA_ID = "login-data";
const REMEMBERED_LOGIN_PAYLOAD_VERSION = 1;
const LEGACY_LOGIN_PREFILL_KEY = "login_prefill";

function createIndexedDbCredentialRepository(indexedDbApi) {
  function openDb() {
    return new Promise((resolve, reject) => {
      const request = indexedDbApi.open(REMEMBERED_LOGIN_DB, REMEMBERED_LOGIN_DB_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(REMEMBERED_LOGIN_STORE)) {
          db.createObjectStore(REMEMBERED_LOGIN_STORE, { keyPath: "id" });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("Không mở được kho đăng nhập."));
      request.onblocked = () => reject(new Error("Kho đăng nhập đang được sử dụng."));
    });
  }

  async function getMany(ids) {
    const db = await openDb();
    try {
      return await new Promise((resolve, reject) => {
        const tx = db.transaction(REMEMBERED_LOGIN_STORE, "readonly");
        const store = tx.objectStore(REMEMBERED_LOGIN_STORE);
        const values = new Map();
        for (const id of ids) {
          const request = store.get(id);
          request.onsuccess = () => values.set(id, request.result || null);
        }
        tx.oncomplete = () => resolve(ids.map((id) => values.get(id) || null));
        tx.onerror = () => reject(tx.error || new Error("Không đọc được kho đăng nhập."));
        tx.onabort = () => reject(tx.error || new Error("Đọc kho đăng nhập bị hủy."));
      });
    } finally {
      db.close();
    }
  }

  async function put(record) {
    const db = await openDb();
    try {
      await new Promise((resolve, reject) => {
        const tx = db.transaction(REMEMBERED_LOGIN_STORE, "readwrite");
        tx.objectStore(REMEMBERED_LOGIN_STORE).put(record);
        tx.oncomplete = resolve;
        tx.onerror = () => reject(tx.error || new Error("Không lưu được thông tin đăng nhập."));
        tx.onabort = () => reject(tx.error || new Error("Lưu thông tin đăng nhập bị hủy."));
      });
    } finally {
      db.close();
    }
  }

  async function clear() {
    const db = await openDb();
    try {
      await new Promise((resolve, reject) => {
        const tx = db.transaction(REMEMBERED_LOGIN_STORE, "readwrite");
        tx.objectStore(REMEMBERED_LOGIN_STORE).clear();
        tx.oncomplete = resolve;
        tx.onerror = () => reject(tx.error || new Error("Không xóa được thông tin đăng nhập."));
        tx.onabort = () => reject(tx.error || new Error("Xóa thông tin đăng nhập bị hủy."));
      });
    } finally {
      db.close();
    }
  }

  return { getMany, put, clear };
}

function createRememberedLoginVault(repository, cryptoApi) {
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  async function getOrCreateKey() {
    const [saved] = await repository.getMany([REMEMBERED_LOGIN_KEY_ID]);
    if (saved?.value) return saved.value;

    const key = await cryptoApi.subtle.generateKey(
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt", "decrypt"],
    );
    await repository.put({ id: REMEMBERED_LOGIN_KEY_ID, value: key });
    return key;
  }

  async function save(username, password) {
    const cleanUsername = String(username || "").trim();
    const cleanPassword = String(password || "");
    if (!cleanUsername || !cleanPassword) throw new Error("Thiếu thông tin đăng nhập để ghi nhớ.");

    const key = await getOrCreateKey();
    const iv = cryptoApi.getRandomValues(new Uint8Array(12));
    const plaintext = encoder.encode(JSON.stringify({
      version: REMEMBERED_LOGIN_PAYLOAD_VERSION,
      username: cleanUsername,
      password: cleanPassword,
    }));
    try {
      const ciphertext = await cryptoApi.subtle.encrypt({ name: "AES-GCM", iv }, key, plaintext);
      await repository.put({
        id: REMEMBERED_LOGIN_DATA_ID,
        version: REMEMBERED_LOGIN_PAYLOAD_VERSION,
        iv: iv.buffer,
        ciphertext,
        savedAt: Date.now(),
      });
    } finally {
      // Giảm thời gian byte plaintext còn nằm trong vùng nhớ mutable. Chuỗi JS gốc do
      // runtime quản lý nên không thể xóa tuyệt đối; popup vẫn xóa ô mật khẩu sau login.
      plaintext.fill(0);
    }
  }

  async function get() {
    const [keyRecord, dataRecord] = await repository.getMany([
      REMEMBERED_LOGIN_KEY_ID,
      REMEMBERED_LOGIN_DATA_ID,
    ]);
    if (!keyRecord?.value || !dataRecord?.ciphertext || !dataRecord?.iv) return null;
    if (dataRecord.version !== REMEMBERED_LOGIN_PAYLOAD_VERSION) return null;

    try {
      const plaintext = await cryptoApi.subtle.decrypt(
        { name: "AES-GCM", iv: new Uint8Array(dataRecord.iv) },
        keyRecord.value,
        dataRecord.ciphertext,
      );
      const decoded = JSON.parse(decoder.decode(plaintext));
      if (decoded?.version !== REMEMBERED_LOGIN_PAYLOAD_VERSION) return null;
      if (typeof decoded.username !== "string" || typeof decoded.password !== "string") return null;
      if (!decoded.username.trim() || !decoded.password) return null;
      return { username: decoded.username, password: decoded.password };
    } catch (_) {
      // Ciphertext hỏng/bị sửa hoặc khóa không còn đúng: fail closed và xóa dữ liệu
      // không thể sử dụng, tuyệt đối không trả một phần thông tin đăng nhập.
      await repository.clear();
      return null;
    }
  }

  return { save, get, clear: repository.clear };
}

const RememberedLoginStore = createRememberedLoginVault(
  createIndexedDbCredentialRepository(indexedDB),
  crypto,
);

// Bản cũ chỉ lưu username trong storage.local. Xóa dấu vết này để từ phiên bản
// mới chỉ lưu khi người dùng chủ động chọn "Ghi nhớ đăng nhập".
RememberedLoginStore.clearLegacyPrefill = async function clearLegacyPrefill() {
  try {
    await chrome.storage.local.remove(LEGACY_LOGIN_PREFILL_KEY);
  } catch (_) {
  }
};

if (typeof window !== "undefined") {
  window.RememberedLoginStore = RememberedLoginStore;
}
