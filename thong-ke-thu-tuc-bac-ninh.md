# Thủ tục dùng được cho tài khoản Bắc Ninh — hiện trạng trên Trợ lý nhân dân

Lấy từ code ở commit `5cb6871` ngày 21/10/2026:

- registry lõi: `auto-fill-hcc-backend/app/procedures/registry.py`, 222 thủ tục;
- registry trợ lý: `auto-fill-hcc-backend/app/channels/handfree/procedure_registry.py`, 69 thủ tục.

Cách lọc: lấy 222 thủ tục lõi, bỏ các thủ tục chỉ dùng ở tỉnh khác (Lào Cai, Đà Nẵng, Quảng Ninh, Ninh Bình,
Quảng Ngãi, Lâm Đồng, Lai Châu). Tỉnh của một thủ tục xác định theo `urlScope` hoặc theo tiền tố tỉnh trên nhãn lõi
và nhãn trong `ke_khai_links.json`. Thủ tục nộp trên cổng bộ ngành (`dvc.moc.gov.vn`, `dichvucong-tthc.moit.gov.vn`…)
vẫn giữ lại. Kết quả là **133 thủ tục**: 116 dùng chung toàn quốc và 17 riêng Bắc Ninh.

Cột "Trợ lý":
- ✅: đã có trên trợ lý và tài khoản Bắc Ninh thấy được.
- ⚠️ chỉ Đà Nẵng: đã có trên trợ lý nhưng đặt `provinceOnly: ["danang"]`, nên tài khoản Bắc Ninh không thấy.
- ❌: chưa thêm.

## Tổng hợp

| Lĩnh vực | Lõi | ✅ | ⚠️ | ❌ |
|---|---:|---:|---:|---:|
| Tư pháp | 34 | 34 | 0 | 0 |
| Đất đai Bắc Ninh (cổng riêng) | 10 | 10 | 0 | 0 |
| Thủ tục riêng Bắc Ninh khác | 5 | 0 | 0 | 5 |
| Nông nghiệp & Môi trường khác | 9 | 0 | 1 | 8 |
| Tài chính | 7 | 5 | 0 | 2 |
| Xây dựng / giao thông | 21 | 6 | 1 | 14 |
| Y tế | 17 | 5 | 0 | 12 |
| Nội vụ | 20 | 5 | 0 | 15 |
| Văn hóa, TT&DL | 4 | 0 | 0 | 4 |
| Công Thương | 4 | 0 | 0 | 4 |
| Giáo dục & ĐT | 2 | 1 | 0 | 1 |
| **Tổng** | **133** | **66** | **2** | **65** |

Trong 65 thủ tục chưa thêm có 11 thủ tục không dành cho người dân, đánh dấu *(không phải người dân)* ở các bảng dưới:
công ty 2, hội 3, tuyển công chức / viên chức 4, nội quy lao động 1, điền thông tin tài khoản 1. Bỏ nhóm này thì phần
nên thêm cho người dân Bắc Ninh còn **54**.

## Tư pháp — 34

| # | Key | Thủ tục | Trợ lý |
|---|---|---|---|
| 1 | `chung-thuc-ban-sao` | Chứng thực bản sao từ bản chính | ✅ |
| 2 | `chung-thuc-chu-ky` | Chứng thực chữ ký | ✅ |
| 3 | `chung-thuc-chu-ky-nguoi-dich-ctv` | Chứng thực chữ ký người dịch là cộng tác viên | ✅ |
| 4 | `chung-thuc-chu-ky-nguoi-dich-khong-ctv` | Chứng thực chữ ký người dịch không phải cộng tác viên | ✅ |
| 5 | `chung-thuc-giao-dich-tai-san` | Chứng thực giao dịch liên quan đến động sản, QSDĐ, nhà ở | ✅ |
| 6 | `chung-thuc-phan-chia-di-san` | Chứng thực văn bản thỏa thuận phân chia di sản | ✅ |
| 7 | `chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich` | Chứng thực việc sửa đổi, bổ sung, hủy bỏ giao dịch | ✅ |
| 8 | `chung-thuc-tu-choi-nhan-di-san` | Chứng thực văn bản từ chối nhận di sản | ✅ |
| 9 | `chung-thuc-di-chuc` | Chứng thực di chúc | ✅ |
| 10 | `cap-ban-sao-so-goc` | Cấp bản sao từ sổ gốc | ✅ |
| 11 | `bau-to-truong-to-hoa-giai` | Bầu tổ trưởng tổ hòa giải | ✅ |
| 12 | `khai-sinh-dang-ky` | Liên thông khai sinh, thường trú, BHYT trẻ dưới 6 tuổi | ✅ |
| 13 | `khai-sinh-dang-ky-thuong` | Đăng ký khai sinh (Cổng DVC quốc gia mới) | ✅ |
| 14 | `khai-sinh-dang-ky-lai` | Đăng ký lại khai sinh | ✅ |
| 15 | `khai-sinh-da-co-ho-so` | Khai sinh cho người đã có hồ sơ, giấy tờ cá nhân | ✅ |
| 16 | `khai-sinh-ket-hop-nhan-cha-me-con` | Khai sinh kết hợp nhận cha, mẹ, con | ✅ |
| 17 | `ket-hon` | Đăng ký kết hôn | ✅ |
| 18 | `ket-hon-nuoc-ngoai` | Đăng ký kết hôn có yếu tố nước ngoài | ✅ |
| 19 | `dang-ky-lai-ket-hon` | Đăng ký lại kết hôn | ✅ |
| 20 | `dang-ky-giam-ho` | Đăng ký giám hộ | ✅ |
| 21 | `dang-ky-cham-dut-giam-ho` | Đăng ký chấm dứt giám hộ | ✅ |
| 22 | `dang-ky-nhan-cha-me-con` | Đăng ký nhận cha, mẹ, con | ✅ |
| 23 | `dang-ky-nuoi-con-nuoi-trong-nuoc` | Đăng ký nuôi con nuôi trong nước | ✅ |
| 24 | `trich-luc-ks` | Cấp bản sao trích lục hộ tịch, bản sao giấy khai sinh | ✅ |
| 25 | `thay-doi-cai-chinh-ho-tich` | Thay đổi, cải chính, bổ sung thông tin hộ tịch | ✅ |
| 26 | `xac-nhan-thong-tin-ho-tich` | Xác nhận thông tin hộ tịch | ✅ |
| 27 | `khai-tu` | Đăng ký khai tử | ✅ |
| 28 | `khai-tu-dang-ky-lai` | Đăng ký lại khai tử | ✅ |
| 29 | `khai-tu-lien-thong` | Liên thông khai tử, xóa thường trú, trợ cấp mai táng | ✅ |
| 30 | `xac-nhan-tinh-trang-hon-nhan` | Cấp giấy xác nhận tình trạng hôn nhân | ✅ |
| 31 | `yeu-cau-tro-giup-phap-ly` | Yêu cầu trợ giúp pháp lý | ✅ |
| 32 | `cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su` | CCHN luật sư (miễn đào tạo, miễn tập sự) | ✅ |
| 33 | `dang-ky-bien-phap-bao-dam-bac-ninh` | [Bắc Ninh] Đăng ký biện pháp bảo đảm bằng QSDĐ | ✅ |
| 34 | `xoa-dang-ky-bien-phap-bao-dam-bac-ninh` | [Bắc Ninh] Xóa đăng ký biện pháp bảo đảm bằng QSDĐ | ✅ |

## Đất đai Bắc Ninh (cổng `dichvucong.bacninh.gov.vn`) — 10

Chi tiết mã trên URL xem [danh-sach-thu-tuc-dat-dai-bac-ninh.md](danh-sach-thu-tuc-dat-dai-bac-ninh.md).

| # | Key | Thủ tục | Trợ lý |
|---|---|---|---|
| 1 | `dinh-chinh-gcn-da-cap-bac-ninh` | Đính chính giấy chứng nhận đã cấp | ✅ |
| 2 | `dinh-chinh-sai-sot-bac-ninh` | Đính chính GCN đã cấp lần đầu có sai sót | ✅ |
| 3 | `cap-doi-gcn-bac-ninh` | Cấp đổi GCN | ✅ |
| 4 | `tach-hop-thua-dat-bac-ninh` | Tách thửa hoặc hợp thửa đất | ✅ |
| 5 | `dang-ky-dat-dai-lan-dau-bac-ninh` | Đăng ký đất đai, cấp GCN lần đầu | ✅ |
| 6 | `thu-hoi-gcn-cap-sai-bac-ninh` | Thu hồi GCN cấp lần đầu không đúng quy định | ✅ |
| 7 | `giao-thue-chuyen-muc-dich-dat-bac-ninh` | Giao đất, cho thuê đất, chuyển mục đích sử dụng đất | ✅ |
| 8 | `dang-ky-bien-dong-chuyen-nhuong-bac-ninh` | Đăng ký biến động chuyển nhượng, thừa kế, tặng cho (1.013831) | ✅ |
| 9 | `dang-ky-bien-dong-dat-dai-bac-ninh` | Đăng ký biến động (1.115468) | ✅ |
| 10 | `dang-ky-bien-dong-thoa-thuan-bac-ninh` | Đăng ký biến động theo thỏa thuận, bản án, xử lý tài sản thế chấp | ✅ |

## Thủ tục riêng Bắc Ninh khác — 5

Năm thủ tục này cùng chạy trên cổng `dichvucong.bacninh.gov.vn`, cổng mà trợ lý đã chạy được, nên dễ thêm nhất.

| # | Key | Thủ tục | Trợ lý |
|---|---|---|---|
| 1 | `ho-tro-nguoi-cao-tuoi-bac-ninh` | Hỗ trợ người cao tuổi từ đủ 70 đến dưới 75 tuổi… | ❌ |
| 2 | `ho-tro-chi-phi-hoa-tang-bac-ninh` | Hỗ trợ chi phí hỏa táng (cả điện táng) | ❌ |
| 3 | `dang-ky-nha-o-xa-hoi-bac-ninh` | Đăng ký mua, thuê mua, thuê nhà ở xã hội | ❌ |
| 4 | `cap-hoc-tap-bac-ninh` | Hỗ trợ chi phí học tập cho học sinh, sinh viên | ❌ |
| 5 | `dien-thong-tin-tai-khoan-bac-ninh` | Điền thông tin tài khoản *(không phải TTHC)* | ❌ |

## Nông nghiệp & Môi trường khác — 9

| # | Key | Thủ tục | Trợ lý |
|---|---|---|---|
| 1 | `cap-giay-phep-khai-thac-thuy-san` | Cấp, cấp lại giấy phép khai thác thủy sản | ⚠️ chỉ Đà Nẵng |
| 2 | `dieu-chinh-dat-dai` | Điều chỉnh quyết định giao đất, cho thuê đất, chuyển mục đích | ❌ |
| 3 | `cap-van-ban-chap-thuan-tau-ca` | Chấp thuận đóng mới, cải hoán, thuê, mua tàu cá | ❌ |
| 4 | `cap-gcn-dang-ky-tau-ca` | Cấp GCN đăng ký tàu cá | ❌ |
| 5 | `xoa-dang-ky-tau-ca` | Xóa đăng ký tàu cá | ❌ |
| 6 | `gia-han-chung-chi-hanh-nghe-thu-y` | Gia hạn CCHN thú y | ❌ |
| 7 | `cap-lai-chung-chi-hanh-nghe-thu-y` | Cấp lại CCHN thú y | ❌ |
| 8 | `cap-gcn-attp-nong-lam-thuy-san` | GCN ATTP cơ sở nông, lâm, thủy sản | ❌ |
| 9 | `ho-tro-co-so-san-xuat-thiet-hai-dich-benh-dong-vat` | Hỗ trợ cơ sở bị thiệt hại do dịch bệnh động vật | ❌ |

## Tài chính — 7

| # | Key | Thủ tục | Trợ lý |
|---|---|---|---|
| 1 | `dang-ky-kinh-doanh` | Đăng ký thành lập hộ kinh doanh | ✅ |
| 2 | `dang-ky-thay-doi-noi-dung-ho-kinh-doanh` | Thay đổi nội dung đăng ký hộ kinh doanh | ✅ |
| 3 | `tam-ngung-kinh-doanh` | Tạm ngừng kinh doanh hộ kinh doanh | ✅ |
| 4 | `cham-dut-hoat-dong-ho-kinh-doanh` | Chấm dứt hoạt động hộ kinh doanh | ✅ |
| 5 | `cap-lai-cap-doi-gcn-ho-kinh-doanh` | Cấp lại, cấp đổi GCN đăng ký hộ kinh doanh | ✅ |
| 6 | `thanh-lap-cong-ty-co-phan` | Thành lập công ty cổ phần *(không phải người dân)* | ❌ |
| 7 | `thanh-lap-cong-ty-tnhh-hai-thanh-vien` | Thành lập công ty TNHH hai thành viên trở lên *(không phải người dân)* | ❌ |

## Xây dựng / giao thông — 21

| # | Key | Thủ tục | Trợ lý |
|---|---|---|---|
| 1 | `cung-cap-thong-tin-quy-hoach` | Cung cấp thông tin quy hoạch | ✅ |
| 2 | `cap-giay-phep-xay-dung-moi-nha-o-rieng-le` | GPXD mới công trình cấp III, IV và nhà ở riêng lẻ | ✅ |
| 3 | `dieu-chinh-giay-phep-xay-dung` | Điều chỉnh GPXD (cổng Bộ Xây dựng) | ✅ |
| 4 | `sua-chua-cai-tao-gpxd-nha-o-rieng-le` | GPXD sửa chữa, cải tạo nhà ở riêng lẻ | ✅ |
| 5 | `cap-phep-long-duong-via-he` | Sử dụng tạm thời lòng đường, vỉa hè (cổng Bộ Xây dựng) | ✅ |
| 6 | `cap-giay-phep-lien-van-viet-lao` | Cấp, cấp lại giấy phép liên vận Việt Nam – Lào | ✅ |
| 7 | `cho-thue-thue-mua-nha-o-xa-hoi` | Cho thuê, thuê mua nhà ở xã hội vốn đầu tư công (cổng Bộ Xây dựng) | ⚠️ chỉ Đà Nẵng |
| 8 | `gia-han-giay-phep-xay-dung` | Gia hạn GPXD | ❌ |
| 9 | `sua-chua-cai-tao-gpxd-cong-trinh` | GPXD sửa chữa, cải tạo công trình | ❌ |
| 10 | `dang-ky-lap-dat-su-dung-nuoc-sach` | Đăng ký lắp đặt sử dụng nước sạch | ❌ |
| 11 | `chuyen-doi-ten-hop-dong-nuoc-sach` | Chuyển đổi tên hợp đồng nước sạch | ❌ |
| 12 | `cap-giay-phep-chat-ha-cay-xanh` | Chặt hạ, dịch chuyển cây xanh (cổng Bộ Xây dựng) | ❌ |
| 13 | `chap-thuan-dau-noi-tam` | Chấp thuận đấu nối tạm vào đường bộ (cổng Bộ Xây dựng) | ❌ |
| 14 | `cap-bo-sung-xe-tap-lai-cap-lai-giay-phep-xe-tap-lai` | Cấp bổ sung xe tập lái, cấp lại giấy phép xe tập lái | ❌ |
| 15 | `cap-cap-lai-phu-hieu-xe-kinh-doanh-van-tai` | Cấp, cấp lại phù hiệu xe kinh doanh vận tải | ❌ |
| 16 | `gia-han-luu-hanh-phuong-tien-lao` | Gia hạn lưu hành phương tiện của Lào (cổng Bộ Xây dựng) | ❌ |
| 17 | `cap-gcnkncm-cccm` | GCN khả năng chuyên môn, chứng chỉ chuyên môn (cổng Bộ Xây dựng) | ❌ |
| 18 | `xoa-dang-ky-phuong-tien-thuy` | Xóa đăng ký phương tiện thủy nội địa | ❌ |
| 19 | `dang-ky-lai-phuong-tien-chuyen-quyen-so-huu-khong-doi-co-quan` | Đăng ký lại phương tiện khi chuyển quyền sở hữu | ❌ |
| 20 | `xac-nhan-dieu-kien-dien-tich-nha-o-dang-ky-thuong-tru` | Xác nhận diện tích nhà ở để đăng ký thường trú | ❌ |
| 21 | `cap-moi-chung-chi-hanh-nghe-moi-gioi-bat-dong-san` | Cấp mới CCHN môi giới bất động sản | ❌ |

## Y tế — 17

| # | Key | Thủ tục | Trợ lý |
|---|---|---|---|
| 1 | `cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham` | GCN ATTP dịch vụ ăn uống | ✅ |
| 2 | `xac-dinh-muc-do-khuyet-tat` | Xác định mức độ khuyết tật | ✅ |
| 3 | `doi-cap-lai-giay-xac-nhan-khuyet-tat` | Đổi, cấp lại giấy xác nhận khuyết tật | ✅ |
| 4 | `tro-cap-xa-hoi-hang-thang` | Thực hiện, điều chỉnh, thôi hưởng trợ cấp xã hội hằng tháng | ✅ |
| 5 | `thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang` | Trợ cấp xã hội và nhận chăm sóc, nuôi dưỡng hằng tháng | ✅ |
| 6 | `cap-lai-giay-chung-nhan-du-dieu-kien-an-toan-thuc-pham` | Cấp lại GCN ATTP | ❌ |
| 7 | `ho-tro-mai-tang` | Hỗ trợ mai táng đối tượng bảo trợ xã hội (1.001731) | ❌ |
| 8 | `ho-tro-chi-phi-van-chuyen-nguoi-tu-vong-den-co-so-hoa-tang` | Hỗ trợ vận chuyển người tử vong đến cơ sở hỏa táng | ❌ |
| 9 | `cap-moi-giay-phep-hanh-nghe-chuyen-tiep` | Cấp mới GPHN giai đoạn chuyển tiếp | ❌ |
| 10 | `dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep` | Điều chỉnh GPHN giai đoạn chuyển tiếp | ❌ |
| 11 | `cap-lai-giay-phep-hanh-nghe-truoc-2024` | Cấp lại GPHN cấp trước 01/01/2024 | ❌ |
| 12 | `cap-moi-giay-phep-hoat-dong-kham-benh-chua-benh` | Cấp mới GPHĐ khám bệnh, chữa bệnh | ❌ |
| 13 | `dieu-chinh-giay-phep-hoat-dong-kcb` | Điều chỉnh GPHĐ khám bệnh, chữa bệnh | ❌ |
| 14 | `cap-chung-chi-hanh-nghe-duoc` | Cấp CCHN dược | ❌ |
| 15 | `cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te` | Cấp lại, điều chỉnh GCN đủ điều kiện kinh doanh dược | ❌ |
| 16 | `dang-ky-hanh-nghe` | Đăng ký hành nghề | ❌ |
| 17 | `cong-bo-co-so-du-dieu-kien-tiem-chung` | Công bố cơ sở đủ điều kiện tiêm chủng | ❌ |

## Nội vụ — 20

| # | Key | Thủ tục | Trợ lý |
|---|---|---|---|
| 1 | `dieu-chinh-huu-tri-xa-hoi` | Thực hiện trợ cấp hưu trí xã hội | ✅ |
| 2 | `ho-tro-mai-tang-huu-tri-xa-hoi` | Hỗ trợ mai táng đối tượng hưởng hưu trí xã hội | ✅ |
| 3 | `tro-cap-tho-cung-liet-si` | Trợ cấp thờ cúng liệt sĩ | ✅ |
| 4 | `uu-dai-ncc-tu-tran` | Trợ cấp khi người có công từ trần | ✅ |
| 5 | `di-chuyen-ho-so-nguoi-huong-tro-cap` | Di chuyển hồ sơ người hưởng trợ cấp ưu đãi | ✅ |
| 6 | `mai-tang-dan-cong-hoa-tuyen` | Mai táng phí dân công hỏa tuyến | ❌ |
| 7 | `cap-lai-to-quoc-ghi-cong` | Cấp lại Bằng "Tổ quốc ghi công" | ❌ |
| 8 | `cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong` | Cấp bổ sung, cấp lại GCN người có công | ❌ |
| 9 | `bo-sung-than-nhan-liet-si` | Bổ sung thân nhân trong hồ sơ liệt sĩ | ❌ |
| 10 | `tham-vieng-mo-liet-si` | Thăm viếng mộ liệt sĩ | ❌ |
| 11 | `giai-quyet-che-do-khang-chien` | Chế độ người hoạt động kháng chiến | ❌ |
| 12 | `sua-doi-thong-tin-ho-so-nguoi-co-cong` | Sửa đổi thông tin hồ sơ người có công | ❌ |
| 13 | `xet-tuyen-vien-chuc` | Xét tuyển viên chức *(không phải người dân)* | ❌ |
| 14 | `xet-tuyen-cong-chuc` | Xét tuyển công chức *(không phải người dân)* | ❌ |
| 15 | `thi-tuyen-cong-chuc` | Thi tuyển công chức *(không phải người dân)* | ❌ |
| 16 | `thi-tuyen-cong-chuc-mot-cua-moha` | Thi tuyển công chức, cổng Một cửa Bộ Nội vụ *(không phải người dân)* | ❌ |
| 17 | `chia-tach-sap-nhap-hop-nhat-hoi-cap-tinh` | Chia, tách, sáp nhập, hợp nhất hội *(không phải người dân)* | ❌ |
| 18 | `bao-cao-to-chuc-dai-hoi-hoi-cap-tinh` | Báo cáo tổ chức đại hội hội *(không phải người dân)* | ❌ |
| 19 | `thong-bao-ket-qua-dai-hoi-phe-duyet-dieu-le-hoi-cap-tinh` | Thông báo kết quả đại hội, phê duyệt điều lệ hội *(không phải người dân)* | ❌ |
| 20 | `dang-ky-noi-quy-lao-dong` | Đăng ký nội quy lao động *(không phải người dân)* | ❌ |

## Văn hóa, TT&DL — 4

| # | Key | Thủ tục | Trợ lý |
|---|---|---|---|
| 1 | `cap-gcn-diem-tro-choi-dien-tu-cong-cong` | Điểm cung cấp trò chơi điện tử công cộng | ❌ |
| 2 | `thong-bao-san-pham-quang-cao-bang-ron` | Thông báo quảng cáo băng-rôn (cổng Bộ VHTTDL, cần `fill-liz.js`) | ❌ |
| 3 | `cap-giay-phep-xuat-ban-tai-lieu-khong-kinh-doanh` | Xuất bản tài liệu không kinh doanh | ❌ |
| 4 | `cap-the-huong-dan-vien-du-lich-noi-dia` | Thẻ hướng dẫn viên du lịch nội địa | ❌ |

## Công Thương — 4

| # | Key | Thủ tục | Trợ lý |
|---|---|---|---|
| 1 | `cap-gcn-attp-cong-thuong` | GCN ATTP ngành công thương | ❌ |
| 2 | `dang-ky-khuyen-mai-may-rui-mot-tinh` | Đăng ký khuyến mại may rủi (cổng Bộ Công Thương) | ❌ |
| 3 | `thong-bao-sua-doi-bo-sung-noi-dung-chuong-trinh-khuyen-mai` | Sửa đổi nội dung chương trình khuyến mại (cổng Bộ Công Thương) | ❌ |
| 4 | `thong-bao-phat-trien-nguon-dien-mat-troi-mai-nha` | Thông báo điện mặt trời mái nhà | ❌ |

## Giáo dục & ĐT — 2

| # | Key | Thủ tục | Trợ lý |
|---|---|---|---|
| 1 | `cap-ban-sao-van-bang-so-goc` | Bản sao văn bằng, chứng chỉ từ sổ gốc (cổng Bộ GD&ĐT) | ✅ |
| 2 | `mien-giam-hoc-phi-gdnn-dai-hoc-tu-thuc` | Miễn, giảm học phí GDNN, đại học tư thục | ❌ |

## Ghi chú

- Trợ lý có 69 entry. Entry duy nhất nằm ngoài 133 thủ tục ở trên là `ho-tro-mai-tang-1116910`, vì nhãn lõi ghi
  "[Tỉnh Ninh Bình]". Entry này không đặt `provinceOnly`, nên tài khoản Bắc Ninh vẫn thấy.
- Hiện trạng tính theo code. Chưa đối chiếu với container 12005 hay stack toàn trình 12015.
