"""Prompt rules đặc thù cho "Cấp Giấy chứng nhận đủ điều kiện ATTP" (cổng Bộ Công Thương — Form.io)."""

EXTRA_RULES = """<critical_rules>
1. Chỉ trả field nguồn trong schema. KHÔNG trả field UI dạng data[...].
2. Đây là thủ tục CẤP LẦN ĐẦU GCN đủ điều kiện ATTP cho cơ sở sản xuất, kinh doanh thực phẩm (Bộ Công
   Thương). Đầu vào: CCCD người nộp, GCN đăng ký hộ kinh doanh/doanh nghiệp (GCN ĐKKD), Đơn đề nghị Mẫu
   01a, Bản thuyết minh CSVC Mẫu 02a/02b, Danh sách tập huấn ATTP, Giấy khám sức khỏe, Giấy ủy quyền (nếu
   nộp thay).
3. KHÔNG bịa. Không chắc field nào thì bỏ field đó.
</critical_rules>

<vai_tro>
- NGƯỜI NỘP (Applicant_*) = chủ tài khoản đăng nhập/đi nộp. Nhân thân lấy ở CCCD. Nếu nộp thay thì là bên
  ĐƯỢC ủy quyền.
- CƠ SỞ (CoSo_*) = đối tượng thụ hưởng: cơ sở sản xuất, kinh doanh thực phẩm (thường là HỘ KINH DOANH →
  CoSo_LoaiChuThe="Tổ chức"). Tên/mã số/địa chỉ/ngành nghề lấy ở GCN ĐKKD / Đơn 01a / TM 02a.
- ⚠ PHÂN BIỆT: Applicant_HoTen = tên NGƯỜI (CCCD); CoSo_Ten = tên PHÁP NHÂN (hộ kinh doanh). ĐỪNG lẫn.
  CoSo_NguoiDaiDien/CoSo_SoDinhDanhChuCoSo = chủ hộ (người), lấy ở GCN ĐKKD mục 6.
</vai_tro>

<dia_chi>
1. Applicant_NoiCuTru = NƠI THƯỜNG TRÚ cá nhân người nộp (CCCD). object {quocGia,tinh,xa,diaChi}.
2. CoSo_DiaChi = ĐỊA CHỈ TRỤ SỞ/địa điểm CƠ SỞ SXKD (GCN ĐKKD 'Trụ sở hộ kinh doanh' / Đơn 01a 'Địa điểm
   tại'). object {quocGia,tinh,xa,diaChi}. THƯỜNG KHÁC nơi thường trú cá nhân — vd thường trú "Tổ 88, Hòa
   Xuân" nhưng trụ sở cơ sở "86 Lê Đình Dương, Hải Châu". ĐỪNG lẫn 2 địa chỉ.
3. tinh='Tỉnh/Thành phố …', xa=phường/xã, diaChi=số nhà/đường (KHÔNG lặp phường/xã/tỉnh). Nếu địa chỉ ghi
   đơn vị hành chính CŨ (còn cấp huyện) thì vẫn tách tinh/xa như đọc được, không tự sáp nhập.
</dia_chi>

<loai_hinh>
Don_LoaiHinh: đọc ô vuông ĐÃ ĐÁNH DẤU (×) trên Đơn 01a — đúng MỘT trong: "san_xuat" (Cơ sở sản xuất) /
"kinh_doanh" (Cơ sở kinh doanh) / "vua_sx_vua_kd" (Cơ sở vừa sản xuất vừa kinh doanh) / "chuoi" (Chuỗi cơ
sở kinh doanh thực phẩm). Nếu GCN ĐKKD có cả ngành sản xuất lẫn bán lẻ và đơn tích "vừa sản xuất vừa kinh
doanh" → "vua_sx_vua_kd". Don_TenChuoi chỉ khi loại hình = "chuoi".
</loai_hinh>

<nganh_nghe>
CoSo_NganhNghe = TÊN SẢN PHẨM/mặt hàng (vd "Sản xuất các loại bánh mặn, ngọt"), KHÔNG chép mã ngành (1071,
4721). Ưu tiên Đơn 01a; GCN ĐKKD/TM 02a fallback.
</nganh_nghe>

<ngay_thang>
Ngày trả dd/mm/yyyy. Applicant_NgaySinh, Applicant_NgayCap, Don_NgayLap (ngày lập Đơn 01a). Đọc đúng từ
giấy tờ, KHÔNG bịa.
</ngay_thang>

<uy_quyen>
Chỉ khi có Giấy ủy quyền: UyQuyen_BenUyQuyen_* = chủ cơ sở (I. BÊN ỦY QUYỀN); UyQuyen_BenDuocUyQuyen_* =
người nộp thay (II. BÊN ĐƯỢC ỦY QUYỀN). Ngày/nơi cấp lấy trong cùng mục với người đó, không trộn 2 bên.
</uy_quyen>

<reminder>Chỉ trả JSON field nguồn hợp lệ. Phân biệt rõ tên người (Applicant) với tên cơ sở (CoSo), và
địa chỉ cá nhân với địa chỉ trụ sở cơ sở.</reminder>"""
