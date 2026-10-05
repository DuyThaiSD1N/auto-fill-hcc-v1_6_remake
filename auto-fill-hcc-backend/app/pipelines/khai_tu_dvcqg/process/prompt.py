"""Quy tắc trích riêng của thủ tục đăng ký khai tử (Cổng DVC quốc gia mới)."""

EXTRA_RULES = """<ho_so>
Hồ sơ đăng ký khai tử: tờ khai đăng ký khai tử (nếu có), GIẤY BÁO TỬ hoặc giấy tờ thay thế (trích lục khai tử,
biên bản xác minh, văn bản xác nhận việc chết), CCCD/CMND của người mất và người yêu cầu, giấy ủy quyền, giấy tờ
chứng minh nơi chết, công văn xác minh người chết lâu năm. Khối người nộp trên cổng khóa theo tài khoản → KHÔNG
trích người nộp.
</ho_so>

<phan_vai>
- Có khối <phan_vai_da_xac_dinh> phía dưới → người mất theo đúng khối đó.
- Không có (dự phòng): người SAU câu "Đề nghị cơ quan đăng ký khai tử..." của tờ khai; không có tờ khai thì người
  được ghi là người chết trên giấy báo tử / trích lục / công văn.
</phan_vai>

<nguoi_mat>
1. Nguồn họ tên, ngày sinh, giới tính, quốc tịch, số định danh: tờ khai → giấy báo tử / giấy tờ thay thế → CCCD
   của chính người mất → công văn ghi rõ. Số CCCD trên tờ khai khớp số in trên thẻ của người mất (thừa/thiếu 1–2
   chữ số do OCR) → họ tên, số, ngày cấp, nơi cấp lấy theo THẺ (bản in đáng tin hơn chữ viết tay).
2. Ngày sinh / ngày chết: giấy chỉ ghi năm (hoặc tháng/năm) → trả đúng độ chính xác đó (yyyy, mm/yyyy); không
   bịa "01/01".
3. Giấy tờ tùy thân của người mất: dòng "Giấy tờ tùy thân" trong khối NGƯỜI MẤT (tờ khai, trích lục khai tử) hoặc
   thẻ của chính họ; KHÔNG lấy giấy tờ của người đi khai tử / người yêu cầu. Nơi cấp chép đúng chữ; CMND do
   "Công an tỉnh ..." cấp giữ nguyên; "Cục CS QLHC về TTXH" → "Cục Cảnh sát quản lý hành chính về trật tự xã hội";
   căn cước mới "BỘ CÔNG AN" → "Bộ Công an".
4. NguoiMat_NoiCuTru = NƠI CƯ TRÚ CUỐI CÙNG: tờ khai → giấy báo tử → văn bản xác nhận cư trú gần thời điểm chết →
   nơi thường trú trên CCCD người mất (cuối cùng). Không dùng địa chỉ người yêu cầu / vợ chồng / chủ hộ.
5. Ngày chết, giờ chết, nơi chết, nguyên nhân: giấy báo tử / giấy tờ thay thế → tờ khai. Nơi chết chỉ từ nhãn
   "Nơi chết"/"Nơi tử vong"; cơ quan cấp giấy báo tử không mặc nhiên là nơi chết; nơi an táng không phải nơi chết.
6. Dân tộc chỉ khi giấy ghi rõ; CCCD thường không in dân tộc → không suy.
</nguoi_mat>

<giay_bao_tu>
7. Gbt_* lấy từ chính GIẤY BÁO TỬ hoặc dòng dẫn chiếu "Số Giấy báo tử/Giấy tờ thay thế..." trên tờ khai. Không có
   giấy báo tử mà có TRÍCH LỤC KHAI TỬ → Gbt_Loai = "Giấy tờ thay thế", Gbt_So = số trích lục ở dòng "Đã được đăng
   ký khai tử tại ... Số: ...", Gbt_CoQuanCap / Gbt_NgayCap theo trích lục. Công văn xác minh không phải Gbt_*.
8. Gbt_So giữ nguyên số hiệu đầy đủ in trên giấy (số + ký hiệu). Nhãn để trống / toàn dấu chấm → bỏ.
</giay_bao_tu>

<to_khai>
9. NguoiYeuCau_* chép khối người yêu cầu của tờ khai (họ tên, số giấy tờ, dòng quan hệ) — chỉ để đối chiếu với tài
   khoản; tờ khai ghi người yêu cầu khác tài khoản vẫn chép đúng tờ khai.
10. SoLuongBanSao: dấu chọn thật (☑, ☒, [x], X) ở "Có" + số lượng dương → số đó; chọn "Không" → 0. "Có ☐, Không ☐"
    và số lượng để chấm = CHƯA KHAI → bỏ field.
</to_khai>

<dia_chi>
11. Địa chỉ tách {quocGia,tinh,xa,diaChi}: "[chi tiết], [xã], [huyện], [tỉnh]" đếm từ cuối — cuối là tỉnh, áp cuối
    là cấp huyện (bỏ khỏi xa/diaChi, trả riêng ở khóa "huyen"), cụm trước huyện là xã, còn lại là diaChi. Chọn đúng
    nguồn trước rồi mới tách; không ghép chi tiết nguồn này với xã/tỉnh nguồn khác.
</dia_chi>

<khong_bia>
12. Giấy tờ không ghi → bỏ field. Không suy diễn.
</khong_bia>"""
