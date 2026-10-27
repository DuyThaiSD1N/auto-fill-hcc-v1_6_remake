// Tab mới của chế độ "mỗi tài liệu một hồ sơ": lấy bundle theo tabId, tự đi từ Chủ hồ sơ
// tới Thành phần hồ sơ rồi gọi đúng attach-core. Chạy riêng để content.js không phình thêm.
(function initSplitAttachWorker() {
  "use strict";
  if (window.top !== window || window.__TLND_SPLIT_ATTACH_WORKER__) return;
  window.__TLND_SPLIT_ATTACH_WORKER__ = true;

  const H = window.__TLND__ || {};
  const RELOADABLE_CODES = new Set([
    "wallet-stale-modal",
    "wallet-modal-not-opened",
    "wallet-device-upload-not-opened",
  ]);
  const MAX_RELOADS_PER_CODE = 3;

  const fold = (value) => String(value || "")
    .replace(/Đ/g, "D").replace(/đ/g, "d")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/\s+/g, " ").trim().toLowerCase();
  const visible = (el) => {
    if (!el) return false;
    try {
      const style = getComputedStyle(el);
      return style.display !== "none" && style.visibility !== "hidden" && style.opacity !== "0"
        && el.getClientRects().length > 0;
    } catch (_) { return false; }
  };
  const waitFor = async (fn, timeout = 4000, interval = 120) => {
    const end = Date.now() + timeout;
    while (Date.now() < end) {
      const value = fn();
      if (value) return value;
      await new Promise((resolve) => setTimeout(resolve, interval));
    }
    return null;
  };
  const sendRuntime = (payload) => new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage(payload, (response) => {
        void chrome.runtime.lastError;
        resolve(response || null);
      });
    } catch (_) { resolve(null); }
  });

  sendRuntime({ action: "getPendingAttach" }).then((response) => {
    const pending = response?.pending;
    const files = Array.isArray(pending?.files) ? pending.files.filter(Boolean) : [];
    const attachments = Array.isArray(pending?.attachments) ? pending.attachments.filter(Boolean) : [];
    if (!files.length || !attachments.length) return;

    let deadline = Date.now() + 5 * 60 * 1000;
    let hiddenSince = null;
    let busy = false;
    let terminal = false;
    let nextFailures = 0;
    const recoveryBase = `__tlnd_split_reload_${pending.ts || "legacy"}`;
    const recoveryTotalKey = `${recoveryBase}_total`;
    const recoveryKey = (code) => `${recoveryBase}_${String(code || "unknown").replace(/[^a-z0-9_-]+/gi, "_")}`;
    const readCount = (key) => {
      try { return Number.parseInt(sessionStorage.getItem(key) || "0", 10) || 0; }
      catch (_) { return 0; }
    };
    const reloadCount = (code) => readCount(recoveryKey(code));
    const reloadTotal = () => readCount(recoveryTotalKey);
    const markReload = (code) => {
      try {
        sessionStorage.setItem(recoveryKey(code), String(reloadCount(code) + 1));
        sessionStorage.setItem(recoveryTotalKey, String(reloadTotal() + 1));
        return true;
      } catch (_) { return false; }
    };
    const seedInitialReload = () => {
      const code = String(pending.recoveryCode || "");
      const count = Number(pending.recoveryCount) || 0;
      if (!RELOADABLE_CODES.has(code) || count <= 0) return;
      try {
        if (reloadCount(code) < count) sessionStorage.setItem(recoveryKey(code), String(count));
        if (reloadTotal() < count) sessionStorage.setItem(recoveryTotalKey, String(count));
      } catch (_) { /* guard best-effort */ }
    };
    const clearReloadGuards = () => {
      try {
        sessionStorage.removeItem(recoveryTotalKey);
        for (const code of RELOADABLE_CODES) sessionStorage.removeItem(recoveryKey(code));
      } catch (_) { /* bỏ qua */ }
    };
    const ownerStepPresent = () => Array.from(document.querySelectorAll("h1,h2,h3")).some((el) =>
      visible(el) && fold(el.textContent).includes("thong tin chu ho so")
    );
    const findOwnerNext = () => {
      if (!ownerStepPresent()) return null;
      return Array.from(document.querySelectorAll(
        'button[id^="kt_buoc-tiep-theo"],button[data-e2e="btn-next"]'
      )).find((button) => visible(button) && !button.disabled
        && button.getAttribute("aria-disabled") !== "true") || null;
    };
    const clickNextAndVerify = async () => {
      const button = findOwnerNext();
      if (!button) return { attempted: false, advanced: false };
      const beforeUrl = location.href;
      button.scrollIntoView({ block: "center", inline: "center" });
      button.focus?.();
      button.click();
      const advanced = await waitFor(() => location.href !== beforeUrl || !ownerStepPresent()
        || H.hasAttachmentTarget?.(), 4000, 120);
      return { attempted: true, advanced: !!advanced };
    };
    const finish = (ok, details = {}) => {
      if (terminal) return;
      terminal = true;
      sendRuntime({
        action: ok ? "clearPendingAttach" : "failPendingAttach",
        code: details.code || null,
        error: details.error || null,
      });
    };

    seedInitialReload();
    const tick = async () => {
      if (terminal) return;
      if (document.hidden) {
        if (!hiddenSince) hiddenSince = Date.now();
        setTimeout(tick, 500);
        return;
      }
      if (hiddenSince) {
        deadline += Date.now() - hiddenSince;
        hiddenSince = null;
      }
      if (Date.now() > deadline) {
        finish(false, { code: "split-timeout", error: "Hết thời gian chờ trang đính kèm sẵn sàng." });
        return;
      }

      if (!busy && H.hasAttachmentTarget?.()) {
        busy = true;
        try {
          const result = await H.attachFilesByPlan(files, attachments, pending.procedure || "", { mode: "split" });
          if (result?.ok && !result?.error) {
            clearReloadGuards();
            finish(true);
            return;
          }
          const code = String(result?.code || "");
          if (RELOADABLE_CODES.has(code)) {
            const maxTotal = RELOADABLE_CODES.size * MAX_RELOADS_PER_CODE;
            if (reloadCount(code) < MAX_RELOADS_PER_CODE && reloadTotal() < maxTotal && markReload(code)) {
              location.reload();
              return;
            }
            finish(false, { code, error: result?.error || "Ví tài liệu vẫn lỗi sau khi tải lại." });
            return;
          }
          if (result?.error) {
            finish(false, { code: code || "attach-failed", error: result.error });
            return;
          }
        } catch (_) { /* lỗi DOM tạm thời: vòng sau thử lại */ }
        busy = false;
      } else if (!busy && nextFailures < 5 && ownerStepPresent()) {
        busy = true;
        const step = await clickNextAndVerify();
        busy = false;
        if (step.attempted && !step.advanced) nextFailures += 1;
        if (step.advanced) {
          setTimeout(tick, 500);
          return;
        }
        if (nextFailures >= 5) {
          finish(false, { code: "owner-next-not-advanced",
            error: "Nút Bước tiếp theo không chuyển sang trang đính kèm." });
          return;
        }
      }
      setTimeout(tick, 1200);
    };
    tick();
  });
})();
