// Ảnh chụp form — khớp cú bấm "rời bước kê khai" theo luật BE cấp (app/form_snapshots/step_rules.py).
// Dùng chung nguyên văn cho hai extension.
(() => {
  "use strict";
  const NS = window.__HCC__ || window.__TLND__;
  if (!NS) return;
  const FS = NS.formSnapshot || (NS.formSnapshot = {});

  FS.CLICKABLE = 'button, a, input[type="submit"], input[type="button"]';

  FS.fold = (s) => String(s || "")
    .replace(/Đ/g, "D").replace(/đ/g, "d")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ").trim().toLowerCase();

  function urlMatches(rule, loc) {
    if (!rule.urlPattern) return true;
    try { return new RegExp(rule.urlPattern).test(loc.pathname + loc.hash); } catch (_) { return false; }
  }

  function buttonMatches(rule, el, label) {
    if ((rule.buttonIds || []).includes(String(el.id || ""))) return true;
    if ((rule.buttonText || []).includes(label)) return true;
    if (!rule.buttonSelector) return false;
    try { return el.matches(rule.buttonSelector); } catch (_) { return false; }
  }

  function inDialog(rule, el) {
    if (!rule.dialogText) return true;
    const dialog = el.closest('[role="dialog"], [role="alertdialog"]');
    return !!dialog && FS.fold(dialog.textContent).includes(rule.dialogText);
  }

  // Trả nhãn nút (làm `trigger`) khi khớp, null khi không.
  FS.matchStep = (rules, el, loc = location) => {
    const list = rules && rules[loc.hostname];
    if (!Array.isArray(list) || !el) return null;
    const raw = String((el.tagName === "INPUT" ? el.value : el.textContent) || "").replace(/\s+/g, " ").trim();
    const label = FS.fold(raw);
    for (const rule of list) {
      if (rule && urlMatches(rule, loc) && buttonMatches(rule, el, label) && inDialog(rule, el)) {
        return (raw || String(el.id || "") || "step").slice(0, 120);
      }
    }
    return null;
  };
})();
