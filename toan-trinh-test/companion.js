// companion.js — khung "hồ sơ phụ" cho TAB TÁCH của chứng thực nhiều hồ sơ.
//
// Chứng thực tách mỗi tài liệu thành một hồ sơ riêng trên một tab mới (background.js, queue tách).
// Tab đó do máy mở nên không có dấu phiên → trước đây chỉ còn bong bóng, bấm vào ra màn bắt đầu
// như chưa làm gì. Trang này lấp đúng chỗ đó.
//
// NGUYÊN TẮC: MỘT phiên chỉ được MỘT khung lái. Khung này CHỈ ĐỌC — nó không giữ conversationId
// để gửi, không gọi /chat, không báo trạng thái trang, không thi hành action, không chấm mốc
// "Nộp hồ sơ". Hai khung cùng lái một phiên là:
//   · đếm nộp hai lần (mốc đi cả đường trực tiếp lẫn đường chuyển tiếp của background),
//   · báo trạng thái trang của SAI hồ sơ về backend → backend dẫn lệch bước,
//   · mỗi khung giữ một nút chuyển bước riêng, bấm nhầm nút cũ là đẩy cổng sai bước.
// Vì vậy mọi thứ ở đây chỉ có một chiều: đọc GET /conversations/{id} rồi vẽ lại.
(() => {
  "use strict";

  const params = new URLSearchParams(location.search);
  const TAB_ID = params.get("tabId") || "";
  const SPLIT_TAB_INFO_KEY = "tlnd_split_tab_info";
  const JOURNEY_KEY = "tlnd_journey";

  const $messages = document.getElementById("messages");
  const $nhan = document.getElementById("ho-so-nhan");

  const BRAND_ICON_URL = chrome.runtime.getURL("assets/icons/icon-128.png");
  document.getElementById("bot-avatar").innerHTML = `<img class="brand-icon-header"
    src="${BRAND_ICON_URL}" width="30" height="30" alt="" aria-hidden="true" draggable="false">`;

  // Bước "Thông tin nhận kết quả" của cổng tư pháp — từ bước này trở đi nút cuối trang là
  // "Gửi hồ sơ" chứ không còn là "Bước tiếp theo".
  const BUOC_NHAN_KET_QUA = 4;

  const api = new window.TlndApiClient();
  let theHoSo = null;          // thẻ hồ sơ của tab này (ordinal/total/label/originTabId/resultMethod)
  let dangTai = false;
  let choVeLai = false;        // có lượt vẽ tới trong lúc đang vẽ → vẽ lại ngay sau
  let loiVuaRoi = "";          // kết quả cú bấm vừa xong, vẽ kèm ở lượt vẽ lại
  let daGatKetQua = false;     // đã gạt sẵn cách nhận kết quả cho tab này (chỉ gạt MỘT lần)
  let ketQuaDangChon = "";     // key cách nhận kết quả đang bật trên trang (card đánh dấu)
  let dangDoiKetQua = false;   // đang gạt theo cú bấm trên card — chặn bấm dồn

  // ── Vẽ ──
  function botTone(md) {
    const s = String(md || "").replace(/^[\s*_#>]+/, "");
    if (/^(✅|🎉)/.test(s)) return " ok";
    if (/^(⚠️|⚠|❗|🚫)/.test(s)) return " warn";
    if (/^(ℹ️|ℹ|💡|📌)/.test(s)) return " info";
    return "";
  }
  function themBubble(role, html) {
    const el = document.createElement("div");
    el.className = `msg ${role}`;
    el.innerHTML = html;
    $messages.appendChild(el);
    return el;
  }
  const themBot = (md) => themBubble("bot" + botTone(md), window.renderMarkdown(md));
  const themNguoiDan = (text) => themBubble("user", window.escapeHtml(text));

  function themNutVeHoSoChinh() {
    if (!theHoSo?.originTabId) return;
    const wrap = document.createElement("div");
    wrap.className = "chips";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip solid";
    btn.textContent = "↩ Về hồ sơ chính";
    btn.addEventListener("click", () => {
      btn.disabled = true;
      const thatBai = () => {
        // Tab hồ sơ chính đã bị đóng. Nói thẳng thay vì để nút bấm mãi không thấy gì xảy ra.
        btn.remove();
        themBot("⚠️ Tab **hồ sơ chính** đã đóng rồi ạ. Công dân nộp nốt hồ sơ ở tab này, "
          + "rồi mở lại Trợ lý ở một tab mới để làm tiếp.");
        $messages.scrollTop = $messages.scrollHeight;
      };
      try {
        chrome.runtime.sendMessage({ action: "focusDossierTab", tabId: theHoSo.originTabId }, (res) => {
          if (chrome.runtime.lastError || res?.error) thatBai();
        });
      } catch (_) { thatBai(); }
    });
    wrap.appendChild(btn);
    $messages.appendChild(wrap);
  }

  // ── Bấm hộ nút của cổng NGAY TRÊN TRANG CỦA TAB NÀY ──
  // Đây KHÔNG phải lái phiên: lệnh đi thẳng tới content script của tab mình, không qua backend,
  // không đụng hội thoại. Nút cuối trang nằm dưới bảng thành phần hồ sơ dài — công dân lớn tuổi
  // cuộn không tới, mà đó đúng là lý do luồng dẫn từng bước tồn tại; hồ sơ tách cũng cần y vậy.
  // Cú bấm "Gửi hồ sơ" ở đây vẫn được content.js bắt và chuyển tiếp về tab gốc để chấm mốc nộp,
  // y như công dân tự tay bấm — không sinh thêm đường đếm nào.
  function guiToiTrang(payload) {
    return new Promise((resolve) => {
      const id = Number(TAB_ID);
      if (!id) return resolve(null);
      try {
        chrome.tabs.sendMessage(id, payload, (res) => {
          void chrome.runtime.lastError;
          resolve(res ?? null);
        });
      } catch (_) { resolve(null); }
    });
  }

  const ngu = (ms) => new Promise((r) => setTimeout(r, ms));

  // Gạt sẵn cách nhận kết quả mặc định (BE gửi kèm lúc tách hồ sơ) trên CHÍNH trang của tab này
  // — hồ sơ chính được sidebar gạt, các tab tách thì không ai gạt nếu khung phụ không làm.
  // onlyIfUnset: trang đã có công tắc bật (công dân tự chọn) thì engine không đụng.
  // Trả câu báo cho công dân, "" khi không có gì để nói.
  async function gatSanKetQua(step) {
    const lenh = theHoSo?.resultMethod;
    if (!lenh?.label || step < BUOC_NHAN_KET_QUA || daGatKetQua) return "";
    daGatKetQua = true;
    let res = null;
    // Vừa chuyển sang bước này thì React có thể chưa dựng xong công tắc: engine chỉ trả lời khi
    // thấy công tắc, nên chưa có trả lời = chờ chút rồi hỏi lại.
    for (let lan = 0; lan < 4 && !res; lan++) {
      if (lan) await ngu(700);
      res = await guiToiTrang({ action: "selectResultMethod", ...lenh, onlyIfUnset: true });
    }
    if (res?.ok && res.skipped) {
      // Công dân đã tự chọn trên trang: card đánh dấu đúng cái đang bật, không gạt gì thêm.
      ketQuaDangChon = keyTheoNhan(res.current);
      return "";
    }
    if (res?.ok) {
      ketQuaDangChon = String(lenh.method || "");
      const thieu = Array.isArray(res.missing) && res.missing.length
        ? ` Công dân điền giúp em: ${res.missing.map((m) => `**${m}**`).join(", ")}.` : "";
      const doiCach = (lenh.options || []).length
        ? "chọn ở danh sách bên dưới" : "gạt lại trên trang";
      return `✅ Em đã chọn sẵn **${lenh.label}** cho hồ sơ này.${thieu} Muốn nhận cách khác thì `
        + `công dân ${doiCach}, rồi bấm nút **Gửi hồ sơ** ạ.`;
    }
    daGatKetQua = false; // cho lượt vẽ sau thử lại
    return `⚠️ Em chưa chọn sẵn được cách nhận kết quả${res?.error ? `: *${res.error}*` : ""}. `
      + `Công dân gạt **${lenh.label}** trên trang giúp em, rồi bấm nút **Gửi hồ sơ** bên dưới ạ.`;
  }

  function keyTheoNhan(nhan) {
    const opt = (theHoSo?.resultMethod?.options || []).find((o) => o.label === nhan);
    return opt ? opt.key : "";
  }

  const NHAC_GUI = "\n\nCông dân kiểm tra thông tin, nếu đã ổn thì bấm **Gửi hồ sơ** để em nộp "
    + "hồ sơ ạ.";

  // Câu báo sau khi đổi cách — cùng lời với hồ sơ chính (GUIDED_RESULT_* ở BE) để hai nơi
  // không nói hai kiểu.
  function baoDoiKetQua(opt, res) {
    if (!res?.ok) {
      return `⚠️ Em chưa gạt được công tắc **${opt.label}** trên trang. Công dân gạt giúp em `
        + "ngay trên trang rồi bấm **Gửi hồ sơ** ạ.";
    }
    const daChon = `✅ Em đã chọn **${opt.label}** trên trang.`;
    const thieu = Array.isArray(res.missing) ? res.missing : [];
    if (thieu.length) {
      return `${daChon}\n\nTrang còn thiếu **${thieu.join(", ")}** — công dân điền nốt giúp em ạ.`;
    }
    if (opt.needsInput) {
      return `${daChon}\n\nCách này cần thêm thông tin người nhận — công dân điền trực tiếp `
        + "trên trang giúp em nhé, em không điền hộ địa chỉ hay tên người nhận đâu ạ." + NHAC_GUI;
    }
    return daChon + NHAC_GUI;
  }

  // Công dân đổi cách ngay trên card: gạt thẳng trên trang của tab này, KHÔNG hỏi BE (khung phụ
  // chỉ đọc hội thoại). Không có onlyIfUnset — đây là lựa chọn chủ động, phải tắt cái đang bật.
  async function chonKetQua(opt) {
    const lenh = theHoSo?.resultMethod;
    if (!lenh || dangDoiKetQua || opt.key === ketQuaDangChon) return;
    dangDoiKetQua = true;
    try {
      const res = await guiToiTrang({
        action: "selectResultMethod", label: opt.label, allLabels: lenh.allLabels || [],
        needsInput: !!opt.needsInput,
      });
      if (res?.ok) ketQuaDangChon = opt.key;
      daGatKetQua = true; // đã có lựa chọn chủ động — lượt vẽ sau không tự gạt đè
      loiVuaRoi = baoDoiKetQua(opt, res);
    } finally {
      dangDoiKetQua = false;
    }
    await ve();
  }

  // Card 3 lựa chọn như hồ sơ chính (cùng class .result-methods trong sidebar.css).
  function veCardKetQua(step) {
    const options = theHoSo?.resultMethod?.options || [];
    if (step < BUOC_NHAN_KET_QUA || !options.length) return;
    const wrap = document.createElement("div");
    wrap.className = "result-methods";
    options.forEach((opt) => {
      const el = document.createElement("div");
      el.className = "opt" + (opt.key === ketQuaDangChon ? " picked" : "");
      el.innerHTML = `<div class="oi">${window.escapeHtml(opt.icon || "")}</div><div>
        <div class="ot">${window.escapeHtml(opt.label || "")}</div>
        <div class="od">${window.escapeHtml(opt.desc || "")}</div></div>`;
      el.addEventListener("click", () => { void chonKetQua(opt); });
      wrap.appendChild(el);
    });
    $messages.appendChild(wrap);
  }

  async function docBuocHienTai() {
    const ctx = await guiToiTrang({ action: "getPageContext" });
    const step = Number(ctx?.wizardStep);
    return Number.isInteger(step) && step > 0 ? step : 0;
  }

  function themNutBuoc(step) {
    // Không đọc được thanh bước thì KHÔNG đoán: bấm nhầm "Gửi hồ sơ" lúc mới ở bước đính kèm
    // là nộp một hồ sơ công dân chưa kịp rà.
    if (!step) return;
    const laGui = step >= BUOC_NHAN_KET_QUA;
    // Tên nút THẬT trên trang cổng — dùng khi phải chỉ đường cho công dân tự bấm.
    const tenNutTrang = laGui ? "Gửi hồ sơ" : "Bước tiếp theo";
    const wrap = document.createElement("div");
    wrap.className = "chips";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip solid cta";
    btn.textContent = laGui ? "📨 Gửi hồ sơ" : "Xong, sang bước nhận kết quả →";
    btn.addEventListener("click", () => {
      btn.disabled = true;
      void (async () => {
        const res = await guiToiTrang({ action: laGui ? "guidedSubmit" : "guidedClickNext" });
        // Bấm được ≠ trang chịu chuyển. Đối chiếu lại thanh bước rồi mới dám báo đã sang bước,
        // không thì công dân tin lời em mà hồ sơ vẫn đứng nguyên chỗ cũ.
        const buocSau = laGui ? step : await docBuocHienTai();
        if (!res?.clicked) {
          loiVuaRoi = "⚠️ Em chưa bấm được nút trên trang. Công dân cuộn xuống cuối trang bấm "
            + `**${tenNutTrang}** giúp em ạ.`;
        } else if (res.message) {
          // Đọc NGUYÊN VĂN lời cổng: toast tự tắt sau vài giây, không đọc lại thì công dân chỉ
          // thấy "bấm mà không có gì xảy ra".
          loiVuaRoi = `⚠️ Trang báo: *${res.message}*`;
        } else if (laGui) {
          // Nói đúng việc đã làm là BẤM. Cổng báo nộp thành công bằng chính khung toast đó,
          // mà engine cố tình bỏ qua lời "thành công" nên ở đây không có căn cứ khẳng định hơn.
          loiVuaRoi = "✅ Em đã bấm **Gửi hồ sơ** cho hồ sơ ở tab này rồi ạ.";
        } else if (buocSau > step) {
          loiVuaRoi = theHoSo?.resultMethod?.label
            ? "✅ Đã sang bước **Thông tin nhận kết quả**."
            : "✅ Đã sang bước **Thông tin nhận kết quả**. Công dân chọn cách nhận kết "
              + "quả trên trang rồi bấm nút bên dưới để em gửi hồ sơ này ạ.";
        } else {
          loiVuaRoi = "⚠️ Em bấm rồi mà trang chưa chuyển bước và cũng không báo gì. Công dân "
            + "rà lại các ô còn thiếu trên trang giúp em, rồi bấm lại nút bên dưới ạ.";
        }
        await ve();
      })();
    });
    wrap.appendChild(btn);
    $messages.appendChild(wrap);
  }

  // ── Đọc storage ──
  function docStorage(keys) {
    return new Promise((resolve) => {
      try {
        chrome.storage.local.get(keys, (res) => {
          resolve(chrome.runtime.lastError ? null : res);
        });
      } catch (_) { resolve(null); }
    });
  }

  // Phiên nằm ở dấu hành trình của TAB GỐC. Đọc nhờ chứ không chép sang tab này: chép là tự
  // biến khung phụ thành khung lái thứ hai của cùng một phiên.
  async function layMaPhien() {
    if (!theHoSo?.originTabId) return "";
    const st = await docStorage([JOURNEY_KEY]);
    return String(st?.[JOURNEY_KEY]?.[theHoSo.originTabId]?.conversation_id || "");
  }

  function nhanHoSo() {
    if (!theHoSo) return "Hồ sơ phụ";
    const thuTu = theHoSo.ordinal && theHoSo.total ? `Hồ sơ ${theHoSo.ordinal}/${theHoSo.total}` : "Hồ sơ phụ";
    return theHoSo.label ? `${thuTu} · ${theHoSo.label}` : thuTu;
  }

  function loiNoiCuaTabNay(step) {
    // Khung có thể dựng lúc máy CÒN ĐANG đính kèm vào tab này. Không khẳng định "đã đính kèm
    // xong" — chưa đọc được trạng thái thật thì nói phần chắc chắn đúng ở cả hai lúc.
    const ten = theHoSo?.label ? `**${theHoSo.label}**` : "giấy tờ của hồ sơ này";
    // Không đọc được thanh bước thì không có nút để chỉ vào — chỉ đường thủ công cho chắc.
    const viec = step
      ? "công dân kiểm tra lại rồi bấm nút bên dưới, em làm tiếp cho hồ sơ này ạ."
      : "công dân kiểm tra lại rồi bấm **Bước tiếp theo / Gửi hồ sơ** ở cuối trang ạ.";
    return `✅ Tab này là **hồ sơ riêng** cho ${ten} — phần đính kèm em lo ở đây, ${viec}`;
  }

  async function ve() {
    // Lượt vẽ tới sau phải được XẾP HÀNG chứ không bỏ: cú bấm nút gọi ve() để báo kết quả, bỏ
    // lượt đó là nút kẹt ở trạng thái đã bấm và công dân không thấy trang báo gì.
    if (dangTai) { choVeLai = true; return; }
    dangTai = true;
    try {
      const convId = await layMaPhien();
      let conv = null;
      if (convId) {
        try { conv = await api.getConversation(convId); } catch (_) { conv = null; }
      }
      const step = await docBuocHienTai();
      const baoGatKetQua = await gatSanKetQua(step);
      $messages.replaceChildren();
      // Hội thoại của hồ sơ chính để công dân không thấy mình rơi vào một cuộc nói chuyện
      // trắng. KHÔNG vẽ chips/cards của last_reply: nút ở đây bấm sẽ không có ai thi hành.
      (conv?.history || []).forEach((h) => {
        if (h.role === "user") themNguoiDan(h.text);
        else themBot(h.text);
      });
      if (!conv) {
        themBot("ℹ️ Em chưa đọc lại được cuộc trò chuyện ở hồ sơ chính, nhưng tab này vẫn dùng "
          + "bình thường ạ.");
      }
      themBot(loiNoiCuaTabNay(step));
      themBot("💬 Công dân muốn hỏi gì thì quay về **hồ sơ chính** nhé — em trả lời ở bên đó ạ.");
      if (loiVuaRoi) { themBot(loiVuaRoi); loiVuaRoi = ""; }
      if (baoGatKetQua) themBot(baoGatKetQua);
      veCardKetQua(step);
      themNutVeHoSoChinh();
      themNutBuoc(step);
      $messages.scrollTop = $messages.scrollHeight;
    } finally {
      dangTai = false;
    }
    if (choVeLai) { choVeLai = false; await ve(); }
  }

  // ── Nút khung (giống sidebar: khung do content.js sở hữu) ──
  document.getElementById("min-btn").addEventListener("click",
    () => window.parent.postMessage({ __tlnd: "minimizePanel" }, "*"));
  document.getElementById("close-btn").addEventListener("click",
    () => window.parent.postMessage({ __tlnd: "closePanel" }, "*"));

  // Hết hạn đăng nhập quầy: khung phụ KHÔNG dựng màn đăng nhập (đăng nhập thuộc về khung chính,
  // hai màn đăng nhập cùng lúc là công dân gõ vào cái không ai chờ).
  window.addEventListener("tlnd-auth-required", () => {
    $messages.replaceChildren();
    themBot("⚠️ Phiên đăng nhập của quầy đã hết hạn. Cán bộ đăng nhập lại ở **hồ sơ chính** rồi "
      + "quay lại tab này ạ.");
    themNutVeHoSoChinh();
  });

  // Công dân quay lại nhìn tab này = lúc duy nhất cần dữ liệu mới. Rẻ hơn nhiều so với dựng một
  // đường phát tín hiệu từ khung chính sang, mà vẫn luôn hiện đúng chặng đang làm.
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) void ve();
  });

  void (async () => {
    const st = await docStorage([SPLIT_TAB_INFO_KEY]);
    theHoSo = st?.[SPLIT_TAB_INFO_KEY]?.[TAB_ID] || null;
    $nhan.textContent = nhanHoSo();
    await ve();
  })();
})();
