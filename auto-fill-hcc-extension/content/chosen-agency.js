// Cơ quan cán bộ / công dân CHỌN ở thẻ "Chọn cơ quan thực hiện" (trang thủ tục dichvucong.gov.vn) → dùng cho ô
// "Kính gửi" / "Tại" của form nộp hồ sơ, thay cho tỉnh/xã của tài khoản trợ lý (nộp hộ về xã khác vẫn đúng nơi nhận).
//
// Trang nộp hồ sơ không in tên cơ quan, chỉ có mã `departmentId` trên URL. Nên: đang ở trang chọn thì ghi lại tỉnh/xã
// đang chọn ("lựa chọn chờ"); vừa sang trang nộp thì gắn lựa chọn đó vào `departmentId`. Lần sau mở trang nộp cùng
// mã cơ quan → dùng lại; chọn lại thì ghi đè. Mã lạ (mở thẳng trang nộp, không qua bước chọn) → giữ tài khoản.
// File dùng chung y hệt cho Auto Fill (namespace window.__HCC__) và Handfree (window.__TLND__) — mỗi extension chạy
// thế giới riêng nên chỉ thấy namespace của mình; storage cũng riêng nên không đè nhau.
(() => {
  const H = window.__HCC__ || window.__TLND__;
  if (!H || H.chosenAgency) return;   // nạp lại script không gắn thêm vòng theo dõi
  const PENDING_KEY = "chosen_agency_pending";
  const BY_DEPARTMENT_KEY = "chosen_agency_by_department";
  // Chọn xong → đăng nhập VNeID → mới vào trang nộp; lựa chọn chờ quá lâu là của lượt đã bỏ dở.
  const PENDING_TTL_MS = 2 * 60 * 60 * 1000;
  const MAX_DEPARTMENTS = 50;
  const CARD_TITLE = "chon co quan thuc hien";
  const SUBMIT_LABEL = "nop truc tuyen";
  const COMBO_SELECTOR = 'button[aria-haspopup="listbox"], input:not([type="radio"]):not([type="checkbox"])';

  function fold(value) {
    return String(value || "")
      .replace(/đ/g, "d").replace(/Đ/g, "D")
      .normalize("NFD").replace(/[̀-ͯ]/g, "")
      .toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  }

  function departmentIdOf(url) {
    try {
      const parsed = new URL(url);
      if (!/^\/nop-ho-so\/?$/.test(parsed.pathname)) return "";
      return parsed.searchParams.get("departmentId") || "";
    } catch (_) {
      return "";
    }
  }

  /** Bảng mã cơ quan → nơi đã chọn sau khi gắn lựa chọn chờ; null khi không có gì để gắn. */
  function bindPending(map, pending, departmentId, now) {
    if (!departmentId || !pending || !pending.xa || now - (pending.at || 0) > PENDING_TTL_MS) return null;
    const next = { ...(map || {}), [departmentId]: { tinh: pending.tinh || "", xa: pending.xa, at: now } };
    const keys = Object.keys(next).sort((a, b) => (next[b].at || 0) - (next[a].at || 0));
    return Object.fromEntries(keys.slice(0, MAX_DEPARTMENTS).map((key) => [key, next[key]]));
  }

  /** Nơi điền Kính gửi / Tại: cơ quan đã chọn cho đúng mã trên URL, không có thì tài khoản. */
  function placeFor(map, departmentId, fallback) {
    const chosen = departmentId && map ? map[departmentId] : null;
    if (chosen && chosen.xa) return { tinh: chosen.tinh || "", xa: chosen.xa, source: "chosen" };
    return { tinh: fallback?.tinh || "", xa: fallback?.xa || "", source: "account" };
  }

  const storage = () => globalThis.chrome?.storage?.local;
  async function read(keys) {
    try { return (await storage()?.get(keys)) || {}; } catch (_) { return {}; }
  }
  async function write(items) {
    try { await storage()?.set(items); } catch (_) { /* extension vừa reload — bỏ qua */ }
  }

  async function bindCurrentPage(url) {
    const departmentId = departmentIdOf(url);
    if (!departmentId) return;
    const stored = await read([PENDING_KEY, BY_DEPARTMENT_KEY]);
    const next = bindPending(stored[BY_DEPARTMENT_KEY], stored[PENDING_KEY], departmentId, Date.now());
    if (!next) return;
    await write({ [BY_DEPARTMENT_KEY]: next });
    try { await storage()?.remove(PENDING_KEY); } catch (_) { /* bỏ qua */ }
  }

  async function placeForPage(url, fallback) {
    await bindCurrentPage(url);   // gọi điền ngay khi vừa sang trang nộp: gắn trước, khỏi chờ nhịp theo dõi
    const stored = await read([BY_DEPARTMENT_KEY]);
    return placeFor(stored[BY_DEPARTMENT_KEY], departmentIdOf(url), fallback);
  }

  H.chosenAgency = { departmentIdOf, bindPending, placeFor, placeForPage };

  if (window.top !== window || location.hostname !== "dichvucong.gov.vn") return;

  function visible(node) {
    if (!node || !node.getBoundingClientRect) return false;
    const rect = node.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return false;
    const style = getComputedStyle(node);
    return style.display !== "none" && style.visibility !== "hidden";
  }

  function agencyCard() {
    const heads = Array.from(document.querySelectorAll("div, h1, h2, h3, h4, span"))
      .filter((node) => fold(node.textContent) === CARD_TITLE && visible(node));
    for (const head of heads) {
      let node = head;
      for (let depth = 0; node && depth < 5; depth += 1) {
        if (node.querySelector('button[aria-haspopup="listbox"]')) return node;
        node = node.parentElement;
      }
    }
    return null;
  }

  function controlValue(control) {
    if (!control) return "";
    if (control.tagName === "INPUT") return String(control.value || "").trim();
    return (control.querySelector("span")?.textContent || control.textContent || "").trim();
  }

  /** Tỉnh + xã đang chọn ở thẻ chọn cơ quan; ô còn "-- Chọn … --" thì coi như chưa chọn. */
  function currentChoice() {
    const card = agencyCard();
    if (!card) return null;
    const [province, ward] = Array.from(card.querySelectorAll(COMBO_SELECTOR)).filter(visible).map(controlValue);
    const picked = (value) => value && !fold(value).startsWith("chon");
    return picked(ward) ? { tinh: picked(province) ? province : "", xa: ward } : null;
  }

  let lastKey = "";
  async function recordChoice() {
    const choice = currentChoice();
    if (!choice) return;
    const key = `${choice.tinh}|${choice.xa}`;
    if (key === lastKey) return;
    lastKey = key;
    await write({ [PENDING_KEY]: { ...choice, at: Date.now() } });
  }

  // Bấm "Nộp trực tuyến" (tay hay tự động) là chốt lựa chọn ngay, không đợi nhịp theo dõi kế tiếp.
  document.addEventListener("click", (event) => {
    const button = event.target?.closest?.("button, a");
    if (button && fold(button.textContent) === SUBMIT_LABEL) {
      lastKey = "";
      void recordChoice();
    }
  }, true);

  let lastBoundUrl = "";
  setInterval(() => {
    void recordChoice();
    if (location.href !== lastBoundUrl && departmentIdOf(location.href)) {
      lastBoundUrl = location.href;
      void bindCurrentPage(location.href);
    }
  }, 1000);
})();
