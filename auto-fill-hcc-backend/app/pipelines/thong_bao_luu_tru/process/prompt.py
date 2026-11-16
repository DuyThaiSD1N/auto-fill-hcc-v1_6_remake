"""Luật riêng của thủ tục Thông báo lưu trú cho compact agent."""

EXTRA_RULES = """Đầu vào thường gồm:
1. Phiếu thông báo lưu trú (Mẫu CT14): phần THÔNG TIN NGƯỜI THÔNG BÁO và bảng NỘI DUNG THÔNG BÁO LƯU TRÚ (mỗi dòng
   một người lưu trú: họ tên, ngày sinh, giới tính, số định danh cá nhân/số hộ chiếu, địa chỉ lưu trú, thời gian lưu
   trú, lý do lưu trú).
2. Có thể có bìa hồ sơ / phiếu kiểm soát ghi tóm tắt (người thông báo, địa chỉ lưu trú, danh mục giấy tờ).
3. Thẻ căn cước / CCCD / hộ chiếu của từng người lưu trú.

<critical_rules>
- NguoiLuuTru CHỈ gồm những người có tên trong bảng người lưu trú của Phiếu CT14 (không có Phiếu thì những người có
  thẻ căn cước/hộ chiếu nộp kèm làm người lưu trú). Người thông báo KHÔNG phải người lưu trú, trừ khi chính người đó
  cũng có một dòng trong bảng người lưu trú.
- Mỗi item NguoiLuuTru là MỘT người: chỉ bổ sung từ thẻ căn cước / hộ chiếu của CHÍNH người đó (cùng số định danh;
  giấy không có số thì cùng họ tên và ngày sinh). Tuyệt đối không lấy ngày sinh, giới tính, nơi cư trú của người này
  điền cho người khác.
- Không bịa thông tin còn thiếu. Ô để trống, chấm chấm ("……") hoặc gạch ngang là KHÔNG có dữ liệu.
</critical_rules>

<guest_rules>
- hoTen: họ, chữ đệm và tên như trên thẻ / Phiếu CT14.
- ngaySinh: dd/mm/yyyy; giấy chỉ ghi tháng năm thì mm/yyyy, chỉ ghi năm thì yyyy.
- gioiTinh: "Nam" hoặc "Nữ".
- soDinhDanh: số định danh cá nhân / CCCD 12 chữ số hoặc CMND 9 chữ số (ghép liền, bỏ khoảng trắng). Cột "Số định danh
  cá nhân/số hộ chiếu" ghi số hộ chiếu (có chữ cái) → đưa vào soHoChieu, không vào soDinhDanh.
- quocTich: quốc tịch ghi trên thẻ / hộ chiếu (thẻ căn cước Việt Nam → "Việt Nam").
- danToc: chỉ khi giấy tờ có ghi dân tộc của người đó.
- noiCuTru: object địa chỉ — nơi thường trú / nơi cư trú ghi trên thẻ căn cước của chính người đó (hoặc ghi trong
  Phiếu CT14 cho người đó). KHÔNG lấy địa chỉ lưu trú (địa chỉ cơ sở nơi người đó đến ở) làm noiCuTru.
- loaiCuTru: "thường trú" khi nhãn trên giấy là nơi thường trú, "tạm trú" khi nhãn là nơi tạm trú; nhãn chỉ ghi
  "Nơi cư trú" hoặc không rõ → bỏ trống.
- lyDo: lý do lưu trú của người đó trên Phiếu CT14, chép nguyên văn.
- tuNgay / denNgay: thời gian lưu trú "từ ngày … đến ngày …" của người đó, dd/mm/yyyy. Phiếu ghi một thời gian chung
  cho nhiều người (vd "1 và 2: từ … đến …") thì mỗi người đều nhận thời gian đó.
- soDienThoai, noiLamViec, soPhong: chỉ khi giấy tờ ghi cho người đó.
</guest_rules>

<accommodation_rules>
- CoSo_DiaChi: địa chỉ lưu trú (nơi người lưu trú đến ở) trên Phiếu CT14, không có thì địa chỉ lưu trú trên bìa hồ sơ.
- CoSo_LoaiHinh: chỉ khi giấy tờ ghi rõ loại cơ sở (khách sạn, nhà nghỉ, homestay → "Cơ sở lưu trú du lịch"; ký túc
  xá → "Ký túc xá sinh viên"; phòng trọ → "Nhà ngăn phòng cho thuê"; bệnh viện, cơ sở khám chữa bệnh → "Cơ sở chữa
  bệnh"), hoặc người thông báo ghi là chủ hộ / thành viên hộ gia đình nơi lưu trú → "Hộ gia đình". Không có căn cứ
  trên giấy → bỏ trống.
- CoSo_Ten: tên cơ sở lưu trú nếu giấy tờ ghi; lưu trú tại nhà hộ gia đình thường không có tên → bỏ trống.
</accommodation_rules>"""
