// Xem trước giấy tờ — chạy trong iframe chrome-extension:// do content.js dựng trên TRANG GỐC.
// Nhận dữ liệu từ content.js (cha) qua postMessage; KHÔNG tự đọc gì từ trang gốc.
//
// PDF hiện bằng trình xem PDF sẵn có của Chrome (iframe + blob URL) — không cần thư viện render
// nào: vendor/ chỉ có pdf-lib (tạo/sửa PDF, không render được), thêm pdf.js là thêm ~1MB và một
// worker script nữa phải lo CSP.
const tenEl = document.getElementById("ten");
const goiYEl = document.getElementById("goiY");
const noiDungEl = document.getElementById("noiDung");

// ✕ và Esc: xin content.js (cha) đóng hẳn. Cha mới là bên giữ trạng thái ghim, con chỉ báo.
const xinDong = () => parent.postMessage({ type: "autofill-hcc-preview-close" }, "*");
document.getElementById("dong").addEventListener("click", xinDong);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") xinDong(); });
let blobUrlHienTai = "";
// Vân tay nội dung ĐANG hiện. Không giữ nguyên chuỗi dataUrl (PDF 3MB ≈ 4MB base64, giữ thêm
// một bản là gấp đôi bộ nhớ) — độ dài + hai đầu chuỗi đủ để nhận ra "vẫn đúng file đó".
let vanTayHienTai = "";
const vanTayCua = (d) => (d ? d.length + ":" + d.slice(0, 128) + d.slice(-64) : "");

function baoLoi(chu) {
  noiDungEl.textContent = "";
  const d = document.createElement("div");
  d.id = "bao";
  d.textContent = chu;
  noiDungEl.appendChild(d);
}

async function ve({ name, mime, dataUrl, ghim }) {
  tenEl.textContent = name || "";
  tenEl.title = name || "";
  // Cập nhật TRƯỚC nhánh "đúng nội dung đang hiện" bên dưới: bấm ghim đúng file đang xem tạm
  // chỉ đổi trạng thái, không đổi nội dung — mà nhánh đó return sớm.
  goiYEl.textContent = ghim ? "📌 đang giữ" : "nhấn vào dòng để giữ";
  // ĐÚNG NỘI DUNG ĐANG HIỆN → chỉ đổi tiêu đề, KHÔNG dựng lại.
  // Dựng lại nghĩa là thu hồi blob, tạo blob mới, thay <iframe> → trình xem PDF nạp lại từ đầu,
  // mất luôn trang đang đọc và mức phóng to. Mà tình huống này xảy ra thường xuyên: đổi tên file
  // (nội dung y nguyên, chỉ khác cái tên), hay renderFiles() làm con trỏ vào lại đúng dòng cũ.
  const vanTay = vanTayCua(dataUrl);
  if (vanTay && vanTay === vanTayHienTai && noiDungEl.querySelector("iframe, img")) return;
  baoLoi("Đang mở…");
  // Thu hồi blob của lần xem trước: mỗi lần rê qua một file là một blob mới, không thu hồi thì
  // rê qua chục file là giữ luôn chục bản sao trong bộ nhớ.
  if (blobUrlHienTai) { URL.revokeObjectURL(blobUrlHienTai); blobUrlHienTai = ""; }
  vanTayHienTai = "";
  if (!dataUrl) { baoLoi("Không có nội dung để xem."); return; }
  let blob;
  try {
    blob = await (await fetch(dataUrl)).blob(); // fetch dataUrl: khoi phai tu giai base64
  } catch (e) {
    console.warn("[Preview] Không đọc được nội dung file:", e);
    baoLoi("Không đọc được nội dung file.");
    return;
  }
  const loai = String(mime || blob.type || "");
  blobUrlHienTai = URL.createObjectURL(blob);
  vanTayHienTai = vanTay;
  noiDungEl.textContent = "";
  if (loai === "application/pdf") {
    const f = document.createElement("iframe");
    // #navpanes=0: ẩn thanh thumbnail bên trái của trình xem PDF. Đo trên Chrome 152 với khung
    // 720px: mặc định thanh đó chiếm ~330px, trang chỉ còn zoom 52%; ẩn đi thì lên 90%.
    // KHÔNG dùng toolbar=0: nó ẩn luôn thanh công cụ, mất nút phóng to và số trang.
    f.src = blobUrlHienTai + "#navpanes=0";
    noiDungEl.appendChild(f);
  } else if (loai.startsWith("image/")) {
    const img = document.createElement("img");
    img.src = blobUrlHienTai;
    img.alt = name || "";
    noiDungEl.appendChild(img);
  } else {
    // .docx và các loại khác: trình duyệt không xem được, nói thẳng thay vì hiện khung trắng.
    baoLoi(`Không xem trước được định dạng này (${loai || "không rõ"}).`);
  }
}

window.addEventListener("message", (e) => {
  if (e.source !== window.parent) return;
  if (e.data?.type !== "autofill-hcc-preview-render") return;
  void ve(e.data);
});

// Báo cha biết đã sẵn sàng — content.js xếp hàng dữ liệu cho tới lúc nhận được tín hiệu này.
parent.postMessage({ type: "autofill-hcc-preview-ready" }, "*");
