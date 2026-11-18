"""Prompt đặc thù cho "Đăng ký hành nghề luật sư với tư cách cá nhân" (1.002153)."""

EXTRA_RULES = """Thủ tục: Đăng ký hành nghề luật sư với tư cách cá nhân (Bộ Tư pháp, nộp tại Sở Tư pháp). Tờ khai trên
cổng là "Đơn đề nghị đăng ký hành nghề luật sư với tư cách cá nhân" Mẫu TP-LS-05-sđ: Kính gửi; 1. luật sư (họ tên,
giới tính, ngày sinh, điện thoại, fax, email, giấy tờ tùy thân số/ngày cấp/nơi cấp, nơi thường trú, nơi ở hiện tại, thẻ
luật sư số/ngày cấp, Đoàn Luật sư); 2. tên, địa chỉ, điện thoại, fax, email, website của cơ quan, tổ chức ký hợp đồng
lao động; địa danh, ngày lập đơn, họ tên luật sư ký.

Hồ sơ thường gồm:
- ĐƠN ĐỀ NGHỊ ĐĂNG KÝ HÀNH NGHỀ LUẬT SƯ VỚI TƯ CÁCH CÁ NHÂN bản giấy (nguồn chính của Kính gửi, điện thoại, email, nơi
  ở hiện tại, mục 2, ngày ký).
- BẢN SAO HỢP ĐỒNG LAO ĐỘNG (Bên A = cơ quan, tổ chức; Bên B = luật sư), trang cuối có thể là LỜI CHỨNG chứng thực
  bản sao của UBND xã/phường — người ký lời chứng KHÔNG phải luật sư.
- THẺ LUẬT SƯ do Liên đoàn Luật sư Việt Nam cấp (số thẻ dạng '…/LS', Đoàn Luật sư, dòng 'Hà Nội, ngày … tháng … năm
  …' là ngày cấp thẻ); có thể có Chứng chỉ hành nghề luật sư (số dạng '…/TP/LS-CCHN') — số chứng chỉ KHÔNG phải số thẻ.
- CCCD của luật sư (2 mặt).

NGUỒN VÀ ƯU TIÊN:
- Nhân thân, số/ngày cấp/nơi cấp giấy tờ tùy thân: CCCD > Đơn > HĐLĐ Bên B > Thẻ luật sư.
- Nơi thường trú: Ls_ThuongTru theo ĐƠN (địa giới mới sau sắp xếp 01/7/2025) > HĐLĐ Bên B > CCCD; đồng thời trả
  CCCD_ThuongTru đúng như in trên thẻ CCCD để hệ thống đối chiếu. CCCD cũ có cấp quận/huyện: bỏ quận/huyện, giữ tên
  phường/xã cũ.
- Thẻ luật sư số, ngày cấp, Đoàn Luật sư: Thẻ luật sư > Đơn > HĐLĐ.
- Cơ quan, tổ chức: ToChuc_HDLD theo Bên A của HĐLĐ, ToChuc_Don theo mục 2 của Đơn — trả cả hai khi có.
- Điện thoại / email của luật sư và của công ty là HAI bộ khác nhau, không lẫn.
- Địa chỉ "Số 12, phố A, phường B, thành phố C" → {quocGia:"Việt Nam", tinh:"Thành phố C", xa:"Phường B",
  chiTietDuoiXa:"Số 12, phố A"}; "P." là "Phường", "TP." là "Thành phố". Không có cấp huyện.
- Ô Đơn ghi "Không" / "Không có" (fax…) → bỏ, không trả chữ "Không".
- Mọi ngày dd/mm/yyyy. Không bịa điện thoại, email hay dữ liệu giấy tờ không ghi.

KHÔNG trả field UI của eForm (HoVaTenC, TT_TinhThanhC, CoQuan_HopDongC…). Chỉ trả field compact trong schema."""
