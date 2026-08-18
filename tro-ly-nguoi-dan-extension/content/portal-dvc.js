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

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
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

  // Modal "Thông tin chung" của wizard hồ sơ (mở sau Nộp trực tuyến, đã điền sẵn đúng
  // cơ quan) → bấm "Xác nhận" hộ. data-e2e là hook test của cổng — ổn định hơn class.
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.action !== "confirmInfoModal") return;
    const btn = document.querySelector('button[data-e2e="confirm-button-information"]');
    if (!btn) return; // frame không có modal → để frame đúng trả lời
    clickLikeUser(btn);
    sendResponse({ ok: true });
  });
})();
