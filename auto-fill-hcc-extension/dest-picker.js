// Khung "Chuyển thủ tục khác" (dest-picker.html) — content.js nhúng BÊN CẠNH panel.
//
// Chỉ là lớp nhìn: popup.js giữ nguồn dữ liệu (các <select> tỉnh/xã/thủ tục ẩn trong panel), gửi
// sang đây một bản chụp trạng thái; chọn gì ở đây thì báo ngược về để popup.js áp vào <select> gốc
// và chạy đúng code sẵn có (lưu địa chỉ, gợi ý, lên đạn chọn cơ quan, mở trang).
//
// Kênh là BroadcastChannel tên riêng do panel sinh và truyền qua #hash: hai iframe cùng origin
// extension nên nói thẳng được với nhau, tên ngẫu nhiên thì panel ở tab khác không nghe nhầm.
(() => {
  const tenKenh = decodeURIComponent(location.hash.slice(1));
  if (!tenKenh) return;
  const kenh = new BroadcastChannel(tenKenh);
  const gui = (msg) => kenh.postMessage(msg);

  const $ = (id) => document.getElementById(id);
  const locationStatus = $("locationStatus");
  const keKhaiStatus = $("keKhaiStatus");
  const nutDi = $("di");

  // Bỏ dấu để gõ "lam vien" vẫn ra "Lâm Viên".
  function chuanHoa(s) {
    return String(s || "")
      .normalize("NFD").replace(/\p{M}/gu, "")
      .replace(/đ/g, "d").replace(/Đ/g, "D")
      .toLowerCase().replace(/\s+/g, " ").trim();
  }

  const combos = [];

  /** Combobox có ô tìm — cùng class .combo-* với panel để nhìn y hệt. */
  function taoCombo(chua, { field, searchPlaceholder }) {
    const combo = document.createElement("div");
    combo.className = "combo";
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "combo-trigger";
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    const label = document.createElement("span");
    label.className = "combo-label";
    const caret = document.createElement("span");
    caret.className = "combo-caret";
    caret.setAttribute("aria-hidden", "true");
    caret.textContent = "▾";
    trigger.append(label, caret);
    const dropdown = document.createElement("div");
    dropdown.className = "combo-dropdown";
    dropdown.hidden = true;
    const search = document.createElement("input");
    search.type = "text";
    search.autocomplete = "off";
    search.className = "combo-search";
    search.placeholder = searchPlaceholder;
    const list = document.createElement("div");
    list.className = "combo-list";
    list.setAttribute("role", "listbox");
    dropdown.append(search, list);
    combo.append(trigger, dropdown);
    chua.appendChild(combo);

    let data = { options: [], value: "", placeholder: "", disabled: false };

    function renderList(query) {
      const needle = chuanHoa(query);
      // Mã TTHC gõ tay hay thiếu/thừa dấu chấm -> so theo phần số, cần ≥4 chữ số mới coi là tra mã.
      const digits = needle.replace(/\D+/g, "");
      const codeNeedle = digits.length >= 4 ? digits : "";
      list.innerHTML = "";
      const matched = data.options.filter((opt) => {
        if (!needle) return true;
        if (chuanHoa(opt.text).includes(needle)) return true;
        return !!codeNeedle && String(opt.code || "").replace(/\D+/g, "").includes(codeNeedle);
      });
      if (!matched.length) {
        const empty = document.createElement("div");
        empty.className = "combo-empty";
        empty.textContent = "Không tìm thấy";
        list.appendChild(empty);
        return;
      }
      for (const opt of matched) {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "combo-option" + (opt.value === data.value ? " active" : "");
        item.setAttribute("role", "option");
        item.textContent = opt.text;
        if (opt.code) item.title = `${opt.code} — ${opt.text}`;
        item.addEventListener("click", () => {
          close();
          if (opt.value === data.value) return;
          data.value = opt.value;
          syncTrigger();
          gui({ type: "pick", field, value: opt.value });
        });
        list.appendChild(item);
      }
    }

    function syncTrigger() {
      const picked = data.options.find((opt) => opt.value === data.value);
      label.textContent = picked ? picked.text : data.placeholder;
      label.classList.toggle("placeholder", !picked);
      trigger.disabled = !!data.disabled;
      if (data.disabled) close();
    }

    function open() {
      if (data.disabled) return;
      for (const c of combos) if (c !== api) c.close();
      dropdown.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
      search.value = "";
      renderList("");
      search.focus();
    }

    function close() {
      if (dropdown.hidden) return;
      dropdown.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
    }

    trigger.addEventListener("click", () => (dropdown.hidden ? open() : close()));
    search.addEventListener("input", () => renderList(search.value));
    document.addEventListener("click", (e) => {
      if (!dropdown.hidden && !combo.contains(e.target)) close();
    });

    const api = {
      close,
      isOpen: () => !dropdown.hidden,
      set(next) {
        data = { ...data, ...next };
        syncTrigger();
        if (!dropdown.hidden) renderList(search.value);
      },
    };
    combos.push(api);
    return api;
  }

  const comboProvince = taoCombo($("comboProvince"), { field: "province", searchPlaceholder: "Tìm tỉnh/thành phố..." });
  const comboWard = taoCombo($("comboWard"), { field: "ward", searchPlaceholder: "Tìm phường/xã..." });
  const comboProcedure = taoCombo($("comboProcedure"), {
    field: "procedure", searchPlaceholder: "Tìm theo tên hoặc mã (vd 2.000815)...",
  });

  function datStatus(el, s) {
    el.textContent = s?.text || "";
    el.className = "status" + (s?.cls ? " " + s.cls : "");
  }

  kenh.onmessage = (e) => {
    const d = e.data;
    if (d?.type !== "state") return;
    comboProvince.set(d.province);
    comboWard.set(d.ward);
    comboProcedure.set(d.procedure);
    datStatus(locationStatus, d.locationStatus);
    datStatus(keKhaiStatus, d.keKhaiStatus);
    nutDi.disabled = !!d.busy;
  };

  const huy = () => gui({ type: "cancel" });
  $("dong").addEventListener("click", huy);
  $("huy").addEventListener("click", huy);
  nutDi.addEventListener("click", () => gui({ type: "go" }));
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const dangMo = combos.find((c) => c.isOpen());
    if (dangMo) dangMo.close();
    else huy();
  });

  // Cao theo nội dung: báo content.js để co/giãn khung (mở dropdown thì khung dài ra).
  const baoCao = () => parent.postMessage(
    { type: "autofill-hcc-dest-resize", height: Math.ceil(document.body.scrollHeight) },
    "*",
  );
  if (typeof ResizeObserver !== "undefined") new ResizeObserver(baoCao).observe(document.body);
  baoCao();

  gui({ type: "ready" });
})();
