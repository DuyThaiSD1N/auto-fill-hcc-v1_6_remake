// portal-dvc.js — engine cho CỔNG REACT MỚI dichvucong.gov.vn (trang chi tiết thủ tục).
// Nhiệm vụ Bước nâng cấp kết hôn: khối "Chọn cơ quan thực hiện" — chọn Tỉnh/Xã theo
// phiên hội thoại rồi bấm "Đồng ý" để vào kê khai.
//
// DOM của khối (cổng React, class Tailwind đổi theo build nên KHÔNG dùng làm selector):
//   - combobox = button[aria-haspopup="listbox"], giá trị hiện ở span đầu tiên (class truncate)
//   - dropdown mở bằng click (markup options render động — quét rộng [role=option]/li sau khi mở)
//   - radio sr-only (searchType=PROVINCE/commune=WARD) mặc định ĐÚNG → không đụng
//   - submit: button[type=submit] chữ "Đồng ý"
// Selector khớp TEXT fold dấu — không dùng class Tailwind (đổi theo build).
(() => {
  if (window.__TLND_PORTAL_DVC__) return;
  window.__TLND_PORTAL_DVC__ = true;
  const H = window.__TLND__ || (window.__TLND__ = {});

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  // fill-core export helper qua namespace H; giữ fallback cục bộ để portal engine không
  // phụ thuộc một biến global không tồn tại trong isolated content-script scope.
  const nodeText = typeof H.nodeText === "function"
    ? H.nodeText
    : (el) => String(el?.textContent || "").replace(/\s+/g, " ").trim();
  const ownerLog = (stage, detail = {}) => {
    console.log("[TLND-OwnerFill]", stage, {
      href: location.href,
      ...detail,
    });
  };
  const ownerWarn = (stage, detail = {}) => {
    console.warn("[TLND-OwnerFill]", stage, {
      href: location.href,
      ...detail,
    });
  };
  const infoLog = (stage, detail = {}) => {
    console.log("[TLND-InfoModal]", stage, { href: location.href, ...detail });
  };
  const infoWarn = (stage, detail = {}) => {
    console.warn("[TLND-InfoModal]", stage, { href: location.href, ...detail });
  };
  const fold = (s) => String(s || "")
    .replace(/Đ/g, "D").replace(/đ/g, "d")
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/\s+/g, " ").trim().toLowerCase();

  async function waitFor(fn, timeout = 4000, interval = 120) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const v = fn();
      if (v) return v;
      await sleep(interval);
    }
    return null;
  }

  function isVisible(el) {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  function leafByText(text, scope = document) {
    const wanted = fold(text).replace(/:$/, "");
    const exact = Array.from(scope.querySelectorAll("h1,h2,h3,h4,p,label,span,div")).filter((el) =>
      !el.children.length && fold(el.textContent).replace(/:$/, "") === wanted);
    // Ưu tiên node hiện; nếu cổng dùng display/measurement lạ thì vẫn lấy node exact trong
    // khối định danh thay vì trả null hoàn toàn.
    return exact.find(isVisible) || exact[0] || null;
  }

  function valueBesideLabel(label, scope = document) {
    const node = leafByText(label, scope);
    if (!node) return "";
    const row = node.parentElement;
    const siblings = Array.from(row?.children || []);
    const index = siblings.indexOf(node);
    for (const candidate of siblings.slice(index + 1)) {
      const value = nodeText(candidate);
      if (value && fold(value) !== fold(label)) return value;
    }
    return "";
  }

  function ownerIdentityScope() {
    const heading = leafByText("Thông tin định danh");
    if (!heading) return null;
    let scope = heading.parentElement;
    for (let i = 0; i < 6 && scope; i++, scope = scope.parentElement) {
      if (leafByText("Họ và tên", scope) && leafByText("Số giấy tờ", scope)) return scope;
    }
    return null;
  }

  function extractOwnerContext() {
    const scope = ownerIdentityScope();
    if (!scope) return null;
    const context = {
      fullName: valueBesideLabel("Họ và tên", scope),
      identityNumber: valueBesideLabel("Số giấy tờ", scope).replace(/\D/g, ""),
      dateOfBirth: valueBesideLabel("Ngày tháng năm sinh", scope),
      gender: valueBesideLabel("Giới tính", scope),
      nationality: valueBesideLabel("Quốc tịch", scope),
      documentType: valueBesideLabel("Loại giấy tờ", scope),
      currentAddress: valueBesideLabel("Địa chỉ chi tiết", scope),
    };
    return (context.fullName || context.identityNumber) ? context : null;
  }

  function ownerFieldSection(field) {
    const sectionLabel = String(field.sectionLabel || "").trim();
    if (!sectionLabel) return { root: document, anchor: null };
    const anchor = leafByText(sectionLabel);
    if (!anchor) return null;
    return { root: anchor.closest("form") || anchor.parentElement || document, anchor };
  }

  function isAfterSectionAnchor(element, anchor) {
    if (!anchor) return true;
    return !!(anchor.compareDocumentPosition(element) & Node.DOCUMENT_POSITION_FOLLOWING);
  }

  function ownerFieldCandidate(section, selector) {
    return Array.from(section.root.querySelectorAll(selector))
      .find((element) => isVisible(element) && isAfterSectionAnchor(element, section.anchor)) || null;
  }

  function normalizedOwnerFieldLabel(value) {
    // Cổng bọc dấu bắt buộc trong <span>*</span>. Bỏ marker ở cuối để label có
    // phần tử con vẫn khớp, nhưng không làm lỏng việc so tên trường.
    return fold(value).replace(/\s*\*+\s*$/, "").replace(/:$/, "").trim();
  }

  function matchesOwnerFieldLabel(element, wanted, section, allowChildren = false) {
    if ((!allowChildren && element.children.length) || !isVisible(element) ||
        !isAfterSectionAnchor(element, section.anchor)) return false;
    const text = normalizedOwnerFieldLabel(element.textContent);
    return text === wanted || text.startsWith(`${wanted} (`);
  }

  function ownerFieldLabel(field, section) {
    const wanted = normalizedOwnerFieldLabel(field.label || "");
    if (!wanted) return null;

    // Ưu tiên <label> thật và cho phép label chứa <span>*</span>. Các node generic
    // vẫn phải là leaf để không bắt nhầm wrapper chứa cả cụm form.
    const label = Array.from(section.root.querySelectorAll("label"))
      .find((element) => matchesOwnerFieldLabel(element, wanted, section, true));
    if (label) return label;
    return Array.from(section.root.querySelectorAll("p,span,div"))
      .find((element) => matchesOwnerFieldLabel(element, wanted, section)) || null;
  }

  function fieldControl(field) {
    const section = ownerFieldSection(field);
    // Field có sectionLabel mà section chưa xuất hiện thì không được fallback ra toàn trang:
    // đặc biệt tránh điền nhầm "Ngày tháng năm sinh" của khối định danh.
    if (!section) return { control: null, scope: null };
    if (field.dataE2e) {
      const byE2e = ownerFieldCandidate(
        section, `[data-e2e="${CSS.escape(String(field.dataE2e))}"]`
      );
      if (byE2e) return { control: byE2e, scope: byE2e.parentElement };
    }
    if (field.name) {
      const named = ownerFieldCandidate(
        section, `[name="${CSS.escape(String(field.name))}"]`
      );
      if (named) return { control: named, scope: named.parentElement };
    }
    const label = ownerFieldLabel(field, section);
    if (!label) return { control: null, scope: null };
    let scope = label.parentElement;
    for (let i = 0; i < 6 && scope; i++, scope = scope.parentElement) {
      const selector = field.comp === "owner-combobox"
        ? 'input[role="combobox"]'
        : "input:not([type=hidden]),textarea";
      const control = Array.from(scope.querySelectorAll(selector)).find((element) =>
        isVisible(element) && isAfterSectionAnchor(element, section.anchor));
      if (control) return { control, scope };
      if (scope === section.root) break;
    }
    return { control: null, scope: null };
  }

  function setReactValue(input, value, blur = true) {
    const text = ownerScalarValue(value);
    if (typeof H.setNativeValue === "function") {
      H.setNativeValue(input, text, { typing: true, commit: blur });
      return;
    }
    const proto = input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
    if (setter) setter.call(input, text);
    else input.value = text;
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    if (blur) input.dispatchEvent(new Event("blur", { bubbles: true }));
  }

  function comboDisplayedValue(scope) {
    const displayed = scope?.querySelector('[class*="singleValue"]');
    return nodeText(displayed);
  }

  function ownerScalarValue(value) {
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return String(value.diaChi || value.dia_chi || value.diachi || "").trim();
    }
    return String(value ?? "").trim();
  }

  function usableOwnerValue(value) {
    const text = ownerScalarValue(value);
    const normalized = fold(text);
    return !!text && normalized !== "[object object]" && normalized !== "dd/mm/yyyy";
  }

  function ownerMarkTarget(control, scope, comp) {
    // scope là wrapper của đúng field (chứa cả label + control) và ổn định qua
    // vòng render React. Parent trực tiếp của input ngày/select có thể bị thay node.
    if (scope?.classList && scope.isConnected) return scope;
    if (comp === "owner-combobox") {
      return control.closest('[class$="-control"]') || control.parentElement?.parentElement || scope || control;
    }
    return control.parentElement || scope || control;
  }

  function markOwner(control, scope, comp, ok) {
    const target = ownerMarkTarget(control, scope, comp);
    const marker = ok ? H.markFilled : H.markUnfilled;
    if (typeof marker === "function") marker(target);
  }

  function markCurrentOwnerField(field, fallbackControl, fallbackScope, ok) {
    // React có thể thay input/wrapper ngay sau input/change/blur. Tìm lại field
    // hiện hành để class màu không bị gắn vào node cũ đã rời DOM.
    const current = fieldControl(field);
    markOwner(
      current.control || fallbackControl,
      current.scope || fallbackScope,
      field.comp,
      ok,
    );
  }

  function reactSelectOptions() {
    const explicit = Array.from(document.querySelectorAll(
      '[role="option"], [id^="react-select-"][id*="-option-"], [class*="-option"]'
    )).filter((el) => isVisible(el));
    const leaves = Array.from(document.querySelectorAll("div,li,button,span"))
      .filter((el) => !el.children.length && isVisible(el) && fold(el.textContent));
    return [...new Set([...explicit, ...leaves])];
  }

  function matchReactSelectOption(target, roots = []) {
    const wanted = fold(target);
    if (roots.length) {
      const leaf = optionCandidates(roots).find((el) => fold(el.textContent) === wanted);
      if (leaf) {
        return leaf.closest(
          '[role="option"], [id^="react-select-"][id*="-option-"], [class*="-option"], li, button'
        ) || leaf;
      }
    }
    const leaf = reactSelectOptions().find((el) => fold(el.textContent) === wanted);
    return leaf?.closest?.(
      '[role="option"], [id^="react-select-"][id*="-option-"], [class*="-option"], li, button'
    ) || leaf || null;
  }

  function visibleReactSelectValues() {
    return reactSelectOptions()
      .map((el) => nodeText(el))
      .filter(Boolean)
      .filter((text, index, all) => all.indexOf(text) === index)
      .slice(0, 8);
  }

  async function openOwnerReactSelect(input, control) {
    const roots = [];
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType === 1) roots.push(node);
        }
      }
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });

    // React Select mở menu ở onMouseDown. Chỉ phát đúng thao tác mở, tránh chuỗi click
    // nhiều event làm component toggle mở rồi đóng lại.
    const opener = control.querySelector('[class*="indicatorContainer"]') || control;
    ownerLog("react-select:open", {
      inputId: input.id || "",
      expandedBefore: input.getAttribute("aria-expanded"),
      openerClass: opener.className || "",
    });
    opener.dispatchEvent(new MouseEvent("mousedown", {
      bubbles: true, cancelable: true, view: window, button: 0,
    }));
    await waitFor(() => input.getAttribute("aria-expanded") === "true" || roots.length, 1800, 80);
    await sleep(250);
    observer.disconnect();
    const connected = roots.filter((node) => node.isConnected);
    ownerLog("react-select:opened", {
      inputId: input.id || "",
      expandedAfter: input.getAttribute("aria-expanded"),
      mutationRoots: connected.length,
      visibleValues: visibleReactSelectValues(),
    });
    return connected;
  }

  async function fillOwnerCombobox(input, scope, value) {
    const current = comboDisplayedValue(scope);
    if (usableOwnerValue(current)) {
      ownerLog("react-select:kept", { current });
      return { kept: true };
    }
    const wanted = ownerScalarValue(value);
    if (!wanted) {
      ownerWarn("react-select:missing-value");
      return { missing: true };
    }
    const control = input.closest('[class$="-control"]') || input;
    ownerLog("react-select:start", { wanted, inputId: input.id || "" });

    // React Select không nhận việc gán input.value như một giá trị đã chọn. Phải mở menu,
    // tìm option thật rồi click; menu thường được portal vào cuối body nên không giới hạn scope.
    const roots = await openOwnerReactSelect(input, control);
    const option = await waitFor(() => matchReactSelectOption(wanted, roots), 3000, 100);

    if (!option) {
      const seen = visibleReactSelectValues();
      ownerWarn("react-select:option-not-found", {
        wanted,
        expanded: input.getAttribute("aria-expanded"),
        seen,
      });
      document.body.click();
      return {
        error: `Không thấy lựa chọn "${wanted}"` +
          (seen.length ? `. Danh sách đang có: ${seen.join(" | ")}` : ""),
      };
    }

    try { option.scrollIntoView({ block: "nearest" }); } catch (_) {}
    ownerLog("react-select:option-click", {
      wanted,
      optionText: nodeText(option),
      optionId: option.id || "",
      optionClass: option.className || "",
    });
    option.click();
    const selected = await waitFor(() => {
      const displayed = comboDisplayedValue(scope);
      return usableOwnerValue(displayed) &&
        fold(displayed) === fold(wanted)
        ? displayed : null;
    }, 2500, 100);
    if (selected) {
      ownerLog("react-select:selected", { wanted, selected });
      return { filled: true };
    }
    ownerWarn("react-select:not-committed", {
      wanted,
      displayed: comboDisplayedValue(scope),
      expanded: input.getAttribute("aria-expanded"),
    });
    return { error: `Đã click nhưng React Select chưa nhận "${wanted}"` };
  }

  async function fillOwnerFields(fields) {
    if (typeof H.injectAutofillStyles === "function") H.injectAutofillStyles();
    if (typeof H.clearAutofillMarks === "function") H.clearAutofillMarks();
    let filled = 0;
    let kept = 0;
    const filledLabels = [];
    const keptLabels = [];
    const notFound = [];
    const errors = [];
    ownerLog("fill:start", {
      fields: (fields || []).map((field) => ({
        key: field.key || field.name || field.label || "?",
        comp: field.comp || "",
        hasValue: usableOwnerValue(field.value),
      })),
    });
    for (const field of fields || []) {
      const { control, scope } = fieldControl(field);
      const label = field.label || field.key || field.name || "?";
      if (!control) {
        notFound.push(label);
        ownerWarn("field:control-not-found", {
          label, name: field.name || "", comp: field.comp || "",
        });
        continue;
      }
      ownerLog("field:control-found", {
        label,
        name: field.name || "",
        sectionLabel: field.sectionLabel || "",
        comp: field.comp || "",
        tag: control.tagName,
        id: control.id || "",
      });
      try {
        if (field.comp === "owner-combobox") {
          const result = await fillOwnerCombobox(control, scope, field.value);
          if (result.kept) { kept += 1; keptLabels.push(label); markCurrentOwnerField(field, control, scope, true); }
          else if (result.filled) { filled += 1; filledLabels.push(label); markCurrentOwnerField(field, control, scope, true); }
          else if (result.missing) { notFound.push(label); markCurrentOwnerField(field, control, scope, false); }
          else { errors.push(`${label}: ${result.error}`); markCurrentOwnerField(field, control, scope, false); }
        } else if (usableOwnerValue(control.value) && field.overwrite !== true) {
          kept += 1;
          keptLabels.push(label);
          markCurrentOwnerField(field, control, scope, true);
        } else if (!usableOwnerValue(field.value)) {
          notFound.push(label);
          markCurrentOwnerField(field, control, scope, false);
        } else {
          setReactValue(control, field.value);
          if (usableOwnerValue(control.value)) {
            filled += 1;
            filledLabels.push(label);
            // Date component cập nhật state sau blur; chờ render xong rồi đánh
            // dấu wrapper mới thay vì parent cũ của input.
            await sleep(80);
            markCurrentOwnerField(field, control, scope, true);
          } else {
            errors.push(`${label}: trang không nhận giá trị`);
            markCurrentOwnerField(field, control, scope, false);
          }
        }
      } catch (error) {
        errors.push(`${label}: ${String(error?.message || error)}`);
        ownerWarn("field:error", { label, error: String(error?.message || error) });
        markCurrentOwnerField(field, control, scope, false);
      }
    }
    const result = { ok: errors.length === 0, filled, kept, filledLabels, keptLabels, notFound, errors };
    ownerLog("fill:done", result);
    return result;
  }

  Object.assign(H, { extractOwnerContext, fillOwnerFields });

  // Khối "Chọn cơ quan thực hiện" — tìm theo heading fold text (id/class React đổi theo build).
  function agencyBlock() {
    const heads = Array.from(document.querySelectorAll("div, h3, h4"))
      .filter((el) => fold(el.textContent).startsWith("chon co quan thuc hien") && el.children.length === 0);
    for (const h of heads) {
      let cur = h;
      for (let i = 0; i < 4 && cur; i++) {
        cur = cur.parentElement;
        if (cur && cur.querySelector('button[aria-haspopup="listbox"]')) return cur;
      }
    }
    return null;
  }

  function comboValue(btn) {
    const span = btn.querySelector("span");
    return span ? span.textContent.trim() : "";
  }

  // Click "như người thật" — React/lib dropdown có thể mở ở mousedown thay vì click.
  function clickLikeUser(el) {
    for (const type of ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {
      try {
        el.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, view: window }));
      } catch (_) { el.click(); return; }
    }
  }

  // MARKUP-AGNOSTIC: không đoán cấu trúc dropdown —
  // MutationObserver bắt các node ĐƯỢC THÊM vào DOM sau khi click combobox; option nằm
  // trong đó dù render kiểu gì (portal, sibling, ul/li hay div trần).
  async function openAndCollect(btn, timeout = 3000) {
    const roots = [];
    const obs = new MutationObserver((muts) => {
      for (const m of muts) {
        for (const n of m.addedNodes) if (n.nodeType === 1) roots.push(n);
      }
    });
    obs.observe(document.documentElement, { childList: true, subtree: true });
    clickLikeUser(btn);
    const t0 = Date.now();
    while (Date.now() - t0 < timeout && roots.length === 0) await sleep(120);
    await sleep(300); // cho danh sách render đủ
    obs.disconnect();
    return roots.filter((n) => n.isConnected);
  }

  // Lá có text trong các root vừa xuất hiện = ứng viên option (query TƯƠI mỗi lần gọi —
  // gõ search xong danh sách re-render trong cùng root).
  function optionCandidates(roots) {
    const out = [];
    for (const root of roots) {
      if (!root.isConnected) continue;
      const nodes = [root, ...root.querySelectorAll("*")];
      for (const el of nodes) {
        if (el.children.length === 0 && isVisible(el)) {
          const t = fold(el.textContent);
          if (t.length >= 2 && t.length <= 120) out.push(el);
        }
      }
    }
    return out;
  }

  function matchOption(roots, target) {
    const wanted = fold(target);
    const cands = optionCandidates(roots);
    // CHÍNH XÁC → option chứa target → target chứa option ("UBND Phường Song Liễu" / "Song Liễu").
    let hit = cands.find((el) => fold(el.textContent) === wanted);
    if (!hit) hit = cands.find((el) => fold(el.textContent).includes(wanted));
    if (!hit) hit = cands.find((el) => {
      const t = fold(el.textContent);
      return t.length >= 4 && wanted.includes(t);
    });
    if (!hit) return null;
    // Click vào phần tử "bấm được" gần nhất (option thường là cha của span text).
    return hit.closest('[role="option"], li, button') || hit;
  }

  function typeIntoSearch(roots, target) {
    for (const root of roots) {
      if (!root.isConnected) continue;
      const inp = [root, ...root.querySelectorAll("input")].find(
        (el) => el.tagName === "INPUT" && isVisible(el));
      if (inp) {
        const desc = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
        desc.set.call(inp, target);
        inp.dispatchEvent(new Event("input", { bubbles: true }));
        return true;
      }
    }
    return false;
  }

  // force=true: LUÔN mở dropdown chọn lại dù giá trị hiển thị có vẻ đúng — text trên nút
  // có thể chỉ là giá trị nhớ từ phiên trước, React state chưa init → danh sách xã không nạp.
  async function pickCombo(btn, target, { force = false, timeout = 4000 } = {}) {
    if (!target) return { ok: true, skipped: true };
    if (!force && fold(comboValue(btn)) === fold(target)) return { ok: true, kept: true };

    const roots = await openAndCollect(btn);
    let opt = null;
    const t0 = Date.now();
    while (Date.now() - t0 < timeout && !opt) {
      opt = matchOption(roots, target);
      if (!opt) await sleep(200);
    }
    if (!opt && typeIntoSearch(roots, target)) {
      const t1 = Date.now();
      while (Date.now() - t1 < 3000 && !opt) {
        await sleep(250);
        opt = matchOption(roots, target);
      }
    }
    if (!opt) {
      // Chẩn đoán: liệt kê những gì THẤY trong dropdown để sửa selector từ xa.
      const seen = optionCandidates(roots).slice(0, 10).map((el) => el.textContent.trim()).filter(Boolean);
      document.body.click(); // đóng dropdown cho sạch
      return {
        ok: false,
        error: `Không thấy "${target}". Dropdown hiện ${roots.length} khối, thấy: ` +
               (seen.length ? seen.join(" | ").slice(0, 200) : "(trống)"),
      };
    }
    try { opt.scrollIntoView({ block: "nearest" }); } catch (_) {}
    clickLikeUser(opt);
    // Chờ giá trị combobox đổi (React re-render).
    await waitFor(() => fold(comboValue(btn)).includes(fold(target)), 2000);
    return { ok: true };
  }

  // Sau "Đồng ý" trang hiện danh sách cơ quan/dịch vụ → tự bấm luôn "Nộp trực tuyến",
  // không dừng giữa chừng bắt người dân bấm.
  async function clickNopTrucTuyen() {
    const btn = await waitFor(() => {
      const cands = Array.from(document.querySelectorAll("button, a"))
        .filter((b) => isVisible(b) && fold(b.textContent).includes("nop truc tuyen"));
      return cands[0] || null;
    }, 7000);
    if (!btn) return false;
    try { btn.scrollIntoView({ block: "center" }); } catch (_) {}
    clickLikeUser(btn);
    return true;
  }

  async function selectAgency({ province, ward }) {
    const block = await waitFor(agencyBlock, 6000);
    if (!block) return { error: 'Không thấy khối "Chọn cơ quan thực hiện" trên trang.' };

    const combos = Array.from(block.querySelectorAll('button[aria-haspopup="listbox"]'));
    if (combos.length < 2) return { error: `Chỉ thấy ${combos.length}/2 ô chọn tỉnh/xã.` };

    // TỈNH chọn chủ động TRƯỚC (force) → React nạp danh sách xã theo tỉnh.
    const provRes = await pickCombo(combos[0], province, { force: true });
    if (!provRes.ok) return { error: `Tỉnh: ${provRes.error}` };
    await sleep(800); // chờ danh sách xã nạp theo tỉnh vừa chọn

    // XÃ: danh sách nạp async → chờ dài hơn.
    const wardRes = await pickCombo(combos[1], ward, { force: true, timeout: 8000 });
    if (!wardRes.ok) return { error: `Xã: ${wardRes.error}` };

    // Nút chốt trong block: "Đồng ý" (chưa đăng nhập) HOẶC "Nộp hồ sơ" (đã đăng nhập).
    // Khớp text fold, không tin class.
    const SUBMIT_LABELS = ["dong y", "nop ho so", "nop truc tuyen"];
    const submit = Array.from(block.querySelectorAll('button[type="submit"], button'))
      .find((b) => SUBMIT_LABELS.some((k) => fold(b.textContent).includes(k)));
    if (!submit) {
      const seen = Array.from(block.querySelectorAll("button"))
        .map((b) => b.textContent.trim()).filter(Boolean).slice(0, 6);
      return { error: `Không thấy nút nộp (Đồng ý / Nộp hồ sơ). Nút trong khối: ${seen.join(" | ") || "(trống)"}` };
    }
    const submitLabel = submit.textContent.trim();
    clickLikeUser(submit);
    await sleep(500);

    // Trình tự trên cổng: "Nộp hồ sơ"/"Đồng ý" trong khối → danh sách cơ quan
    // hiện ra kèm nút "Nộp trực tuyến" RIÊNG → phải bấm nốt. Chỉ bỏ qua khi nút vừa bấm
    // đã chính là "Nộp trực tuyến".
    const submitted = fold(submitLabel).includes("nop truc tuyen") ? true : await clickNopTrucTuyen();
    return { ok: true, province: comboValue(combos[0]), ward: comboValue(combos[1]),
             submit: submitLabel, nop_truc_tuyen: submitted };
  }

  // Message riêng — chỉ frame có khối cơ quan mới trả lời (all_frames: im lặng nếu không match).
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.action !== "selectAgency") return;
    if (!agencyBlock()) return; // frame không chứa khối → để frame đúng trả lời
    selectAgency({ province: msg.province || "", ward: msg.ward || "" })
      .then(sendResponse)
      .catch((e) => sendResponse({ error: String(e?.message || e) }));
    return true; // async
  });

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.action !== "getOwnerContext") return;
    const ownerContext = extractOwnerContext();
    if (!ownerContext) return; // frame không có khối định danh → để frame đúng trả lời
    sendResponse({ ok: true, ownerContext });
  });

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.action !== "fillOwnerFields") return;
    const fields = Array.isArray(msg.fields) ? msg.fields : [];
    // Không phụ thuộc ownerIdentityScope: context có thể fallback từ principal VNeID.
    // Chỉ frame có ít nhất một control thật mới giành quyền phản hồi.
    const matchingFields = fields.filter((field) => fieldControl(field).control);
    if (!matchingFields.length) {
      ownerLog("message:skip-frame", {
        traceId: msg.traceId || "",
        fieldCount: fields.length,
      });
      return;
    }
    ownerLog("message:accepted", {
      traceId: msg.traceId || "",
      fieldCount: fields.length,
      matchingCount: matchingFields.length,
    });
    fillOwnerFields(fields)
      .then((result) => {
        ownerLog("message:response", { traceId: msg.traceId || "", result });
        sendResponse(result);
      })
      .catch((e) => {
        const error = String(e?.message || e);
        ownerWarn("message:error", { traceId: msg.traceId || "", error });
        sendResponse({ error });
      });
    return true;
  });

  function infoSubjectCombobox(dialog) {
    const label = leafByText("Đối tượng thực hiện", dialog);
    if (!label) return null;
    let scope = label.parentElement;
    for (let depth = 0; depth < 5 && scope && scope !== dialog; depth += 1, scope = scope.parentElement) {
      const control = Array.from(scope.querySelectorAll('button[role="combobox"]')).find(isVisible);
      if (control) return control;
    }
    return null;
  }

  function infoSubjectOption(target, portalValue, roots = []) {
    const candidates = [
      ...optionCandidates(roots),
      ...Array.from(document.querySelectorAll(
        '[role="option"], [data-radix-collection-item], [data-value]'
      )).filter(isVisible),
    ];
    const wanted = fold(target);
    const exact = [...new Set(candidates)].find((element) => {
      const value = String(element.getAttribute?.("data-value") || "");
      return (portalValue && value === String(portalValue)) || fold(nodeText(element)) === wanted;
    });
    return exact?.closest?.('[role="option"], [data-radix-collection-item], button, li')
      || exact || null;
  }

  async function selectInfoSubject(dialog, requested) {
    if (!requested?.label) return { kept: true, selected: "" };
    const combobox = infoSubjectCombobox(dialog);
    if (!combobox) throw new Error("Không tìm thấy ô Đối tượng thực hiện");

    const target = String(requested.label || "").trim();
    const current = nodeText(combobox);
    infoLog("subject:start", {
      current,
      target,
      portalValue: requested.portalValue ?? "",
    });
    if (fold(current) === fold(target)) {
      infoLog("subject:kept", { current });
      return { kept: true, selected: current };
    }

    const roots = await openAndCollect(combobox);
    const option = await waitFor(
      () => infoSubjectOption(target, requested.portalValue, roots),
      3000,
      100,
    );
    if (!option) {
      const seen = Array.from(document.querySelectorAll('[role="option"]'))
        .filter(isVisible).map(nodeText).filter(Boolean).slice(0, 8);
      throw new Error(`Không thấy lựa chọn ${target}; danh sách đang có: ${seen.join(" | ") || "(trống)"}`);
    }

    option.scrollIntoView?.({ block: "nearest" });
    clickLikeUser(option);
    const selected = await waitFor(() => {
      const value = nodeText(combobox);
      return fold(value) === fold(target) ? value : "";
    }, 2500, 100);
    if (!selected) throw new Error(`Trang chưa nhận lựa chọn ${target}`);
    infoLog("subject:selected", { selected });
    return { kept: false, selected };
  }

  async function confirmInfoModal(executionSubject) {
    const btn = Array.from(document.querySelectorAll(
      'button[data-e2e="confirm-button-information"]'
    )).find(isVisible);
    if (!btn) return null; // frame không có modal → để frame đúng trả lời
    const dialog = btn.closest('[role="dialog"]');
    if (!dialog || !isVisible(dialog)) throw new Error("Không tìm thấy modal Thông tin chung");
    const subjectResult = await selectInfoSubject(dialog, executionSubject);
    infoLog("confirm:click", { executionSubject: executionSubject || null, subjectResult });
    clickLikeUser(btn);
    return { ok: true, ...subjectResult };
  }

  // Modal "Thông tin chung" của wizard hồ sơ: chọn Đối tượng thực hiện theo contract
  // backend rồi mới bấm "Xác nhận". data-e2e là hook ổn định hơn class Tailwind động.
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.action !== "confirmInfoModal") return;
    confirmInfoModal(msg.executionSubject || null)
      .then((result) => {
        if (result) sendResponse(result);
      })
      .catch((error) => {
        const message = String(error?.message || error);
        infoWarn("confirm:error", {
          executionSubject: msg.executionSubject || null,
          error: message,
        });
        sendResponse({ ok: false, error: message });
      });
    return true;
  });
})();
