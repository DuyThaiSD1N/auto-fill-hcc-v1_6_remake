// Xem trước giấy tờ — chạy trong iframe chrome-extension:// do content.js dựng TRÊN TRANG GỐC.
// Nhận lệnh từ content.js (cha) qua postMessage; KHÔNG tự đọc gì từ trang gốc hay từ BE.
//
// Không nhận sẵn nội dung cả nhóm: một doc-row 5 tệp × 3MB là ~20MB base64 chạy qua message.
// Chỉ xin đúng tệp đang xem, qua cha → sidebar (bên có quyền gọi BE).
//
// Giao thức với cha:
//   cha → con  tlnd-preview-nhom     {tieuDe, bieuTuong, tep: [{fid, name}], chiSo, ghim}
//   cha → con  tlnd-preview-du-lieu  {fid, mime, dataUrl} | {fid, loi}
//   con → cha  tlnd-preview-san-sang
//   con → cha  tlnd-preview-can      {fid}
//   con → cha  tlnd-preview-dong
const $ = (id) => document.getElementById(id);
const tieuDeEl = $("tieuDe");
const bieuTuongEl = $("bieuTuong");
const demEl = $("dem");
const goiYEl = $("goiY");
const truocEl = $("truoc");
const sauEl = $("sau");
const daiEl = $("dai");
const noiDungEl = $("noiDung");

let nhom = { tieuDe: "", bieuTuong: "📄", tep: [] };
let chiSo = 0;
let ghim = true;
let blobUrl = "";
// fid ĐANG hiện. Dữ liệu về muộn của tệp khác (bấm "File tiếp theo" liên tục) phải bỏ, không vẽ đè.
let fidDangXem = "";
// Chỉ giữ tệp của NHÓM đang mở — đổi nhóm là dọn, không tích luỹ giấy của công dân trước.
const daCo = new Map(); // fid -> {mime, dataUrl}

function bao(chu) {
  noiDungEl.textContent = "";
  const d = document.createElement("div");
  d.id = "bao";
  d.textContent = chu;
  noiDungEl.appendChild(d);
}

function veDau() {
  const n = nhom.tep.length;
  const tep = nhom.tep[chiSo];
  const nhieu = n > 1;
  bieuTuongEl.textContent = nhom.bieuTuong || "📄";
  // Một tệp: tên tệp là thứ cần đọc. Nhiều tệp: tên mục ở đầu, tên từng tệp nằm ở dải bên dưới.
  tieuDeEl.textContent = nhieu ? nhom.tieuDe : (tep?.name || nhom.tieuDe);
  tieuDeEl.title = tep?.name || nhom.tieuDe || "";
  goiYEl.textContent = ghim ? "📌 đang giữ" : "nhấn để giữ";
  demEl.hidden = truocEl.hidden = sauEl.hidden = daiEl.hidden = !nhieu;
  if (!nhieu) return;
  demEl.textContent = `${chiSo + 1}/${n}`;
  daiEl.replaceChildren(...nhom.tep.map((t, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.setAttribute("role", "tab");
    b.textContent = t.name || `Tệp ${i + 1}`;
    b.title = t.name || "";
    b.setAttribute("aria-current", i === chiSo ? "true" : "false");
    b.addEventListener("click", () => chon(i));
    return b;
  }));
  daiEl.children[chiSo]?.scrollIntoView({ block: "nearest", inline: "nearest" });
}

function chon(i) {
  if (!nhom.tep.length || i < 0 || i >= nhom.tep.length) return;
  chiSo = i;
  veDau();
  const tep = nhom.tep[i];
  fidDangXem = tep.fid;
  const co = daCo.get(tep.fid);
  if (co) { void ve(tep, co); return; }
  bao("Đang tải tệp…");
  parent.postMessage({ type: "tlnd-preview-can", fid: tep.fid }, "*");
}

// BE không phải lúc nào cũng trả Content-Type đúng → đoán thêm theo đuôi tên tệp.
function loaiCua(tep, mime, blob) {
  const loai = String(mime || blob.type || "").toLowerCase();
  if (loai && loai !== "application/octet-stream") return loai;
  const duoi = String(tep.name || "").split(".").pop().toLowerCase();
  if (duoi === "pdf") return "application/pdf";
  if (["jpg", "jpeg", "png", "webp", "gif"].includes(duoi)) return `image/${duoi === "jpg" ? "jpeg" : duoi}`;
  return loai;
}

async function ve(tep, { mime, dataUrl }) {
  if (tep.fid !== fidDangXem) return;
  if (blobUrl) { URL.revokeObjectURL(blobUrl); blobUrl = ""; }
  if (!dataUrl) { bao("Không có nội dung để xem."); return; }
  let blob;
  try {
    blob = await (await fetch(dataUrl)).blob();
  } catch (e) {
    bao("Không đọc được nội dung tệp.");
    return;
  }
  if (tep.fid !== fidDangXem) return; // đã chuyển sang tệp khác trong lúc giải mã
  const loai = loaiCua(tep, mime, blob);
  blobUrl = URL.createObjectURL(blob);
  noiDungEl.textContent = "";
  if (loai === "application/pdf") {
    const f = document.createElement("iframe");
    // #navpanes=0: ẩn thanh thumbnail bên trái của trình xem PDF. Đo trên Chrome 152 với khung
    // 720px: mặc định thanh đó chiếm ~330px, trang chỉ còn zoom 52%; ẩn đi thì lên 90%.
    // KHÔNG dùng toolbar=0: nó ẩn luôn thanh công cụ, mất nút phóng to và số trang.
    f.src = blobUrl + "#navpanes=0";
    noiDungEl.appendChild(f);
  } else if (loai.startsWith("image/")) {
    const img = document.createElement("img");
    img.src = blobUrl;
    img.alt = tep.name || "";
    noiDungEl.appendChild(img);
  } else {
    // .docx và các loại khác: trình duyệt không xem được, nói thẳng thay vì hiện khung trắng.
    bao(`Không xem trước được định dạng này (${loai || "không rõ"}).`);
  }
}

// Đi VÒNG, không khoá ở hai đầu: tệp cuối bấm "File tiếp theo" thì về tệp đầu, tệp đầu bấm "File
// trước" thì về tệp cuối — lướt lại bộ giấy tờ không phải bấm ngược từng tệp (yêu cầu 2026-09-13).
function buoc(delta) {
  const n = nhom.tep.length;
  if (n < 2) return;
  chon((chiSo + delta + n) % n);
}

const xinDong = () => parent.postMessage({ type: "tlnd-preview-dong" }, "*");
$("dong").addEventListener("click", xinDong);
truocEl.addEventListener("click", () => buoc(-1));
sauEl.addEventListener("click", () => buoc(1));
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") xinDong();
  else if (e.key === "ArrowLeft") buoc(-1);
  else if (e.key === "ArrowRight") buoc(1);
});

window.addEventListener("message", (e) => {
  if (e.source !== window.parent) return;
  const d = e.data;
  if (d?.type === "tlnd-preview-nhom") {
    const tep = Array.isArray(d.tep) ? d.tep.filter((t) => t && t.fid) : [];
    const cungNhom = tep.length === nhom.tep.length && tep.every((t, i) => t.fid === nhom.tep[i].fid);
    const chiSoMoi = Math.max(0, Math.min(Number(d.chiSo) || 0, tep.length - 1));
    nhom = { tieuDe: String(d.tieuDe || ""), bieuTuong: d.bieuTuong || "📄", tep };
    ghim = d.ghim !== false;
    for (const fid of [...daCo.keys()]) if (!tep.some((t) => t.fid === fid)) daCo.delete(fid);
    if (!tep.length) {
      chiSo = 0;
      fidDangXem = "";
      veDau();
      bao("Chưa có tệp nào để xem.");
      return;
    }
    // Đúng tệp đang hiện (vd: đang xem tạm rồi NHẤN để ghim, hoặc tên tệp vừa được sửa) → chỉ vẽ lại
    // đầu khung. Dựng lại trình xem PDF là mất luôn trang đang đọc và mức phóng to.
    if (cungNhom && chiSoMoi === chiSo && fidDangXem === tep[chiSoMoi].fid && noiDungEl.querySelector("iframe, img")) {
      veDau();
      return;
    }
    chon(chiSoMoi);
  } else if (d?.type === "tlnd-preview-du-lieu") {
    if (d.loi) {
      if (d.fid === fidDangXem) bao(String(d.loi));
      return;
    }
    daCo.set(d.fid, { mime: d.mime, dataUrl: d.dataUrl });
    const tep = nhom.tep.find((t) => t.fid === d.fid);
    if (tep && d.fid === fidDangXem) void ve(tep, daCo.get(d.fid));
  }
});

// Báo cha đã sẵn sàng — content.js xếp hàng lệnh cho tới lúc nhận được tín hiệu này.
parent.postMessage({ type: "tlnd-preview-san-sang" }, "*");
