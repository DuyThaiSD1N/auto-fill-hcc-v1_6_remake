const TLND_DEFAULT_BASE_URL = "http://localhost:12005";  // Backend CHÍNH — ĐANG TRỎ LOCAL để thử FE (prod: https://trolyhoso-hcc.tiengnoi.vn)

const TLND_BASE_URL_KEY = "tlnd_base_url";
const TLND_LEGACY_BASE_URLS = new Set([
  "https://trolynguoidan-admin.vnekyc.vn",
]);

// Backend PHỤ (dự phòng) — điền domain server phụ để BẬT failover; để TRỐNG = tắt (chạy như cũ).
// ⚠ 2 backend PHẢI dùng chung JWT_ACCESS_SECRET/JWT_REFRESH_SECRET và có cùng tài khoản, nếu không
// khi chuyển sang phụ user sẽ bị đá ra đăng nhập lại.
const TLND_FALLBACK_BASE_URL = "";  // TẮT failover khi chạy local (prod: https://trolyhoso-hcc.vnekyc.vn)
const TLND_API_TIMEOUT_MS = 100000;        // đủ dài cho chat/OCR+LLM; chỉ cắt server TREO thật rồi mới failover
const TLND_FAILOVER_COOLDOWN_MS = 30000;   // chính vừa lỗi thì ưu tiên phụ trong khoảng này rồi thử lại chính

// Đọc base URL (ưu tiên override trong storage). Dùng: const base = await tlndBaseUrl();
function tlndBaseUrl() {
  return new Promise((resolve) => {
    try {
      chrome.storage.local.get([TLND_BASE_URL_KEY], (res) => {
        if (chrome.runtime.lastError) return resolve(TLND_DEFAULT_BASE_URL);
        const v = String(res?.[TLND_BASE_URL_KEY] || "").trim().replace(/\/+$/, "");
        if (!v || TLND_LEGACY_BASE_URLS.has(v)) {
          // Bản đã cài có thể còn lưu domain Handfree cũ trong storage. Chỉ migrate
          // đúng giá trị legacy; URL dev/tùy chỉnh khác của đội triển khai vẫn giữ nguyên.
          if (v) {
            chrome.storage.local.set({ [TLND_BASE_URL_KEY]: TLND_DEFAULT_BASE_URL });
          }
          return resolve(TLND_DEFAULT_BASE_URL);
        }
        resolve(v);
      });
    } catch (_) {
      resolve(TLND_DEFAULT_BASE_URL);
    }
  });
}

//   https://host → wss://host   ·   http://host:8010 → ws://host:8010
function tlndWsBase(httpBase) {
  const base = String(httpBase || "").replace(/\/+$/, "");
  if (base.startsWith("https://")) return "wss://" + base.slice("https://".length);
  if (base.startsWith("http://")) return "ws://" + base.slice("http://".length);
  return base;
}

// ===== Failover backend CHÍNH ↔ PHỤ =====
// Chỉ chuyển backend khi lỗi HẠ TẦNG (mạng/timeout/502/503/504). 401/4xx giữ nguyên (authFetch lo refresh).
const _TLND_INFRA_STATUS = new Set([502, 503, 504]);
const _tlndDownAt = Object.create(null); // base → timestamp lần lỗi gần nhất (cho cooldown)

// Danh sách base theo thứ tự thử: CHÍNH (đã tính override storage) trước, PHỤ sau; nếu chính vừa lỗi
// trong cooldown thì đảo PHỤ lên trước (vẫn giữ chính làm chốt cuối để tự phục hồi).
async function tlndBases() {
  const primary = await tlndBaseUrl();
  const fb = (typeof TLND_FALLBACK_BASE_URL === "string" ? TLND_FALLBACK_BASE_URL : "")
    .trim().replace(/\/+$/, "");
  if (!fb || fb === primary) return [primary];
  const downTs = _tlndDownAt[primary];
  if (downTs && Date.now() - downTs < TLND_FAILOVER_COOLDOWN_MS) return [fb, primary];
  return [primary, fb];
}

// fetch có timeout — cắt request treo để failover kịp.
function tlndFetch(url, init = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TLND_API_TIMEOUT_MS);
  return fetch(url, { ...init, signal: ctrl.signal }).finally(() => clearTimeout(timer));
}

// Chạy 1 request qua nhiều base. doReq(base) tự dựng URL = base + path rồi fetch (kèm Bearer/refresh
// nếu gọi qua authFetch). Lỗi hạ tầng → thử base kế; app-level status trả về ngay.
async function tlndOverBases(doReq) {
  const bases = await tlndBases();
  let lastErr;
  for (let i = 0; i < bases.length; i++) {
    const base = bases[i];
    const isLast = i === bases.length - 1;
    try {
      const res = await doReq(base);
      if (!isLast && res && _TLND_INFRA_STATUS.has(res.status)) {
        _tlndDownAt[base] = Date.now();
        console.warn(`[TLND] Backend lỗi HTTP ${res.status} tại ${base} → chuyển sang backend phụ`);
        continue;
      }
      delete _tlndDownAt[base];
      if (i > 0) console.warn(`[TLND] Đang chạy trên BACKEND PHỤ: ${base} (backend chính đang lỗi)`);
      return res;
    } catch (e) {
      lastErr = e;
      _tlndDownAt[base] = Date.now();
      if (!isLast) {
        console.warn(`[TLND] Không gọi được backend ${base} (mạng/timeout) → chuyển sang backend phụ`);
        continue;
      }
      throw e;
    }
  }
  throw lastErr || new Error("Không có backend nào khả dụng");
}

window.tlndBaseUrl = tlndBaseUrl;
window.tlndWsBase = tlndWsBase;
window.tlndBases = tlndBases;
window.tlndFetch = tlndFetch;
window.tlndOverBases = tlndOverBases;
window.TLND_DEFAULT_BASE_URL = TLND_DEFAULT_BASE_URL;
window.TLND_FALLBACK_BASE_URL = TLND_FALLBACK_BASE_URL;
