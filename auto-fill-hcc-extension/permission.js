// permission.js — Trang xin quyền micro cho extension (voice push-to-talk).
//
// Vì sao cần: popup chạy trong iframe nhúng vào trang web (origin chrome-extension://…);
// Chrome thường KHÔNG hiện prompt micro trong iframe nhúng. Mở trang này như TAB top-level
// của extension → prompt hiện bình thường → quyền lưu cho origin extension → iframe dùng lại được.
const $btn = document.getElementById("grant");
const $msg = document.getElementById("msg");


$btn.addEventListener("click", async () => {
  $msg.textContent = "Đang xin quyền micro…";
  $msg.className = "";
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((t) => t.stop()); // chỉ cần kích hoạt quyền, không giữ mic
    $msg.textContent = "✅ Đã cấp quyền micro! Bạn đóng tab này và bấm 🎤 trong trợ lý là nói được ạ.";
    $msg.className = "ok";
    $btn.hidden = true;
    setTimeout(() => { try { window.close(); } catch (_) {} }, 1800);
  } catch (e) {
    const name = e && e.name;
    if (name === "NotAllowedError" || name === "SecurityError") {
      $msg.innerHTML =
        "❌ Quyền micro đang bị chặn. Bấm biểu tượng <b>🔒 / 🎤</b> ở thanh địa chỉ → " +
        "đặt Micro thành <b>“Cho phép”</b> → bấm lại nút trên.";
    } else if (name === "NotFoundError") {
      $msg.textContent = "❌ Không tìm thấy thiết bị micro. Bạn kiểm tra micro đã cắm/bật chưa ạ.";
    } else {
      $msg.textContent = "Lỗi: " + ((e && e.message) || e);
    }
    $msg.className = "err";
  }
});
