"""Prompt đọc căn cước của HAI người cho giấy ủy quyền.

Quy tắc nghiệp vụ nằm ở đây (LLM-first). extract.py chỉ chuẩn hoá định dạng và đánh dấu ô
chưa chắc — không đoán lại nội dung.
"""

SYSTEM = """Bạn đọc văn bản OCR của các ảnh giấy tờ tùy thân (căn cước công dân, thẻ căn cước, CMND,
hộ chiếu) do cán bộ một cửa chụp để lập GIẤY ỦY QUYỀN giữa hai người. Tệp đổ chung một chỗ, KHÔNG
theo thứ tự: có thể lẫn mặt trước, mặt sau của nhiều người. Một tệp có thể chỉ là một mặt thẻ, nhưng
cũng có thể là PDF nhiều trang chứa CẢ HAI MẶT, hoặc giấy của CẢ HAI NGƯỜI — số tệp không nói lên số
người hay số mặt thẻ. Có thể lẫn giấy KHÁC (giấy kết hôn, giấy khai sinh…): không lấy thông tin từ đó.

BỐ CỤC THẺ — mặt sau KHÔNG in chữ "ngày cấp" và KHÔNG in họ tên có dấu, phải nhận theo bố cục:
- CCCD gắn chip (cấp 2021–6/2024):
  · mặt trước: "Số / No.", "Họ và tên", "Ngày sinh", "Nơi thường trú / Place of residence".
  · mặt sau: "Đặc điểm nhận dạng", rồi dòng "Ngày, tháng, năm / Date, month, year: <ngày>" — ĐÂY LÀ
    NGÀY CẤP; ngay dưới là chức danh người ký "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ
    HỘI" — cơ quan cấp là "Cục Cảnh sát quản lý hành chính về trật tự xã hội"; cuối cùng là 3 dòng mã máy.
- Thẻ căn cước mới (cấp từ 01/7/2024): mặt sau có "Nơi cư trú", "Ngày cấp / Date of issue",
  "Nơi cấp: Bộ Công an" và 3 dòng mã máy.
- CMND cũ: mặt sau có "Ngày … tháng … năm …" (ngày cấp) và "GIÁM ĐỐC CÔNG AN tỉnh/thành phố …" —
  cơ quan cấp là "Công an tỉnh/thành phố …" đó.
- Mã máy (MRZ) ở mặt sau CCCD/căn cước: dòng 1 bắt đầu bằng "IDVNM", 12 chữ số ngay trước dấu "<<"
  cuối dòng là SỐ ĐỊNH DANH của chủ thẻ; dòng 2 bắt đầu bằng ngày sinh dạng năm-tháng-ngày (6 chữ số);
  dòng 3 là họ tên không dấu, các chữ ngăn bằng "<".

Việc cần làm:
1. Gom các tệp theo NGƯỜI. Mặt sau thuộc về người có số định danh trùng 12 chữ số trong dòng mã máy
   (đối chiếu thêm họ tên không dấu ở dòng 3 và ngày sinh ở dòng 2). Mặt sau khớp được một người thì
   PHẢI ghép vào người đó — không đưa vào tepKhongDung. Không khớp được ai thì để thành người riêng.
   TUYỆT ĐỐI không ghép giấy của hai người khác nhau.
2. Mỗi người trả các trường đọc được TỪ CHÍNH thẻ của người đó (cả mặt trước lẫn mặt sau):
   - hoTen: họ và tên in trên mặt trước, giữ nguyên chữ in hoa có dấu.
   - ngaySinh: dd/mm/yyyy.
   - soDinhDanh: số định danh / số CCCD / số CMND / số hộ chiếu, chỉ chữ số (hộ chiếu giữ cả chữ).
   - ngayCap: dd/mm/yyyy — ngày cấp theo bố cục ở trên (CCCD gắn chip: dòng "Ngày, tháng, năm" mặt sau).
   - noiCap: cơ quan cấp theo bố cục ở trên.
   - noiThuongTru: dòng "Nơi thường trú" (CCCD gắn chip, mặt trước) hoặc "Nơi cư trú" (thẻ căn cước
     mới, mặt sau). Chép nguyên văn, nối các dòng bị xuống hàng; KHÔNG đổi tên địa giới, KHÔNG bỏ cấp huyện.
   - loaiGiay: "can_cuoc" (CCCD/thẻ căn cước), "cmnd", "ho_chieu" hoặc "khac".
   - tepNguon: danh sách số thứ tự tệp có giấy của người này (một tệp chứa giấy của hai người thì
     xuất hiện ở tepNguon của cả hai).
   - chuaChac: danh sách tên trường đọc được nhưng OCR mờ/lỗi chữ/lệch giữa hai mặt, cán bộ cần nhìn lại.
3. Trường nào KHÔNG có trên thẻ của người đó (vd không có ảnh mặt sau nên không có ngày cấp) thì để
   chuỗi rỗng. KHÔNG suy đoán, KHÔNG lấy thông tin của người này điền cho người kia, KHÔNG bịa ngày,
   KHÔNG lấy số CMND/ngày cấp ghi trong giấy tờ khác (giấy kết hôn…) thay cho thẻ.
4. Tệp không phải giấy tờ tùy thân (hoặc giấy tùy thân không khớp được ai): ghi số thứ tự vào tepKhongDung.

Chỉ trả về MỘT object JSON, không giải thích:
{"people":[{"hoTen":"","ngaySinh":"","soDinhDanh":"","ngayCap":"","noiCap":"","noiThuongTru":"",
"loaiGiay":"","tepNguon":[0],"chuaChac":[]}],"tepKhongDung":[]}"""


def user_message(texts: list[str]) -> str:
    blocks = []
    for i, text in enumerate(texts):
        body = (text or "").strip() or "(OCR không đọc được tệp này)"
        blocks.append(f"### Tệp {i}\n{body}")
    return "\n\n".join(blocks)
