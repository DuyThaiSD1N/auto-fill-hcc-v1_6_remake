"""Quy tắc trích riêng của thủ tục cấp Phiếu lý lịch tư pháp (3.000333, Cổng DVC quốc gia mới)."""

EXTRA_RULES = """<ho_so>
Hồ sơ cấp Phiếu lý lịch tư pháp: tờ khai yêu cầu cấp Phiếu (mẫu cá nhân tự yêu cầu, hoặc mẫu dùng cho trường hợp ủy
quyền / cha, mẹ của người chưa thành niên), thẻ căn cước / CCCD / hộ chiếu của người yêu cầu, văn bản ủy quyền, phiếu
tiếp nhận hồ sơ, biên lai / giấy nộp phí, giấy tờ chứng minh miễn giảm phí. Khối người nộp trên cổng khóa theo tài
khoản → KHÔNG trích tài khoản.
</ho_so>

<vai>
1. NGƯỜI YÊU CẦU CẤP PHIẾU (NYC_*) là người ĐƯỢC CẤP phiếu:
   - Tờ khai mẫu ủy quyền: người ở "PHẦN KHAI VỀ NGƯỜI ỦY QUYỀN HOẶC NGƯỜI CHƯA THÀNH NIÊN" (= tên sau "Được sự ủy
     quyền"). Người sau "Tên tôi là" ở đầu tờ khai mẫu này là NGƯỜI KHAI (NguoiKhai_*), KHÔNG phải người yêu cầu.
   - Tờ khai cá nhân: người sau "Tên tôi là".
   - Phiếu tiếp nhận: "Tiếp nhận hồ sơ yêu cầu cấp Phiếu Lý lịch tư pháp của Ông/Bà". "Người được ủy quyền nộp hồ sơ"
     và "Người nộp" trên biên lai là người đi nộp, KHÔNG phải người yêu cầu.
2. Thẻ căn cước / CCCD của người yêu cầu (trùng họ tên / số với người yêu cầu ở trên) là nguồn ƯU TIÊN cho họ tên, số,
   ngày sinh, giới tính, quốc tịch, ngày cấp, nơi cấp ("BỘ CÔNG AN" ở mặt sau), nơi đăng ký khai sinh; tờ khai bổ sung
   phần thẻ không có (dân tộc, tạm trú, cha, mẹ, vợ/chồng, điện thoại). Ngày sinh lệch thì đối chiếu MRZ (6 số đầu
   dòng 2 = yymmdd). Không lấy giấy tờ của người khai / người nộp cho người yêu cầu.
3. Bảng "CHA / MẸ / VỢ CHỒNG" là cha, mẹ, vợ/chồng CỦA NGƯỜI YÊU CẦU (tờ khai mẫu ủy quyền ghi "của người ủy quyền
   hoặc ... người chưa thành niên"). Ô trống → bỏ.
4. Ô ghi "Không" (tên gọi khác...) → bỏ. Điện thoại và email cùng một dòng thì tách: dãy số → SoDienThoai, chuỗi có
   "@" → Email.
5. Địa chỉ tách {quocGia,tinh,xa,chiTietDuoiXa}: cuối là tỉnh, áp cuối là xã/phường; cấp huyện cũ (nếu có) trả riêng ở
   khóa "huyen"; phần trước xã là chiTietDuoiXa. Thẻ căn cước ghi gọn "<xã>, <tỉnh>" (hai cụm) → tinh = cụm
   cuối, xa = cụm đầu.
</vai>"""
