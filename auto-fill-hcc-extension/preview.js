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

// Ảnh → blob URL của PDF 1 trang A4; "" khi thiếu thư viện / định dạng chưa chuyển được (webp, gif…).
// Trang A4 (ảnh ngang thì trang ngang), ảnh co vừa trong lề và căn giữa, vẫn nhúng nguyên ảnh gốc nên in ra vẫn nét.
// Không dùng trang to bằng số điểm ảnh như bước đính kèm: ảnh điện thoại ~3000×4000 thành trang khổ hơn 1 m, Chrome in
// mặc định theo kích thước thật nên tờ A4 chỉ lấy được góc trên bên trái.
const A4_LE = 24; // pt
async function anhSangPdf(dataUrl, name, loai) {
  if (typeof PdfConvert === "undefined" || !window.PDFLib || !PdfConvert.isImage(loai, name)) return "";
  try {
    const { PDFDocument, PageSizes } = window.PDFLib;
    const pdf = await PDFDocument.create({ updateMetadata: false });
    const img = await PdfConvert._embedImage(pdf, PdfConvert._dataUrlToBytes(dataUrl), dataUrl, name, loai);
    const [rong, cao] = img.width > img.height ? [PageSizes.A4[1], PageSizes.A4[0]] : PageSizes.A4;
    // Không phóng ảnh nhỏ (ảnh quét cỡ thẻ) lên kín trang — phóng là mờ.
    const tiLe = Math.min((rong - 2 * A4_LE) / img.width, (cao - 2 * A4_LE) / img.height, 1);
    const w = img.width * tiLe;
    const h = img.height * tiLe;
    pdf.addPage([rong, cao]).drawImage(img, { x: (rong - w) / 2, y: (cao - h) / 2, width: w, height: h });
    return URL.createObjectURL(new Blob([await pdf.save()], { type: "application/pdf" }));
  } catch (e) {
    console.warn("[Preview] Không chuyển được ảnh sang PDF, hiện ảnh gốc:", e);
    return "";
  }
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
    // Ảnh (chụp điện thoại, quét) → PDF ngay lúc xem, giữ nguyên chất lượng: trình xem PDF của Chrome có nút tải
    // xuống nên cán bộ tải được bản PDF. Tệp gốc trong danh sách vẫn là ảnh (đọc thông tin dùng ảnh gốc).
    baoLoi("Đang mở…");
    const pdfUrl = await anhSangPdf(dataUrl, name, loai);
    if (vanTayHienTai !== vanTay) {            // đã chuyển sang xem tệp khác trong lúc chuyển
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      return;
    }
    noiDungEl.textContent = "";
    if (pdfUrl) {
      URL.revokeObjectURL(blobUrlHienTai);
      blobUrlHienTai = pdfUrl;
      const f = document.createElement("iframe");
      f.src = pdfUrl + "#navpanes=0";
      noiDungEl.appendChild(f);
    } else {
      const img = document.createElement("img"); // chuyển lỗi (ảnh lạ) → hiện ảnh như cũ
      img.src = blobUrlHienTai;
      img.alt = name || "";
      noiDungEl.appendChild(img);
    }
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
