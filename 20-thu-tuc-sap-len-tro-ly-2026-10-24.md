# 20 thủ tục sắp lên Trợ lý người dân (81 → 101)

Lập ngày 24/10/2026, hạn 100 thủ tục là 31/10 (xem [ke-hoach-100-thu-tuc-tro-ly.md](ke-hoach-100-thu-tuc-tro-ly.md)).

## Hiện trạng

Cập nhật 24/10/2026 (tối): **xong nhóm A (7), nhóm B Y tế (4), 3/5 Xây dựng (#12, #14, #15) và #17 tàu cá**
(đã deploy Docker local, `/healthz` ok).

- Registry trợ lý `app/channels/handfree/procedure_registry.py` có **96** thủ tục (81 + 7 nhóm A + 4 nhóm B + 3 nhóm C
  + 1 nhóm D).
- Registry lõi `app/procedures/registry.py` có **222** thủ tục, tức **126** thủ tục đã có pipeline mà trợ lý chưa mở.
- Còn **5** thủ tục trong danh sách chính (#13, #16, #18, #19, #20), trong đó **2** thủ tục chưa có link (#13, #16), xem mục
  [Còn thiếu link](#còn-thiếu-link--cần-tìm-uuid-dvcqg).
- Cả 20 thủ tục dưới đây **đã có pipeline process + attach ở lõi**. Mỗi thủ tục chỉ cần thêm:
  - entry trong `procedure_registry.py`;
  - gợi ý chọn thủ tục trong `procedure_picker/prompt.py`;
  - tên tiếng Mông trong `script_mong.py` (BẢN NHÁP, chờ anh Dư soát).

  Không tạo file mới.

## Cách chọn

Chỉ lấy thủ tục đạt đủ 3 điều kiện:

1. Thủ tục nằm trên cổng mà trợ lý đã chạy được: Bộ Nội vụ, Bộ Y tế, Bộ Xây dựng, Bộ NN&MT, Bộ GD&ĐT, DVCQG.
2. Pipeline không đòi engine mà extension trợ lý (1.13.5) chưa có: `add-document-dialog`, `sectionHeader`,
   `dom-click`, `dom-editgrid`, `fill-liz.js`. Đã kiểm bằng grep trên pipeline lõi và trên extension.
3. Đối tượng nộp là người dân hoặc hộ kinh doanh nhỏ, không phải doanh nghiệp hay cơ quan.

Mỗi nhóm có một **entry mẫu** đã chạy trên cùng cổng. Khi thêm thủ tục thì chép khung từ entry mẫu đó.

## Danh sách 20 thủ tục

### A. Người có công — Sở Nội vụ (7) — ✅ XONG 24/10

Cổng `dichvucongbnv.moha.gov.vn`. Entry mẫu: `tro-cap-tho-cung-liet-si`, có bảng đính kèm với mục "Thêm giấy tờ"
(`target: "new"`); extension đã hỗ trợ mục này.

| # | Key | Mã TTHC | Tên ngắn | Giấy tờ chính | Cấp cơ quan | Trạng thái |
|---|---|---|---|---|---|---|
| 1 | `cap-lai-to-quoc-ghi-cong` | 1.010778 | Cấp lại Bằng "Tổ quốc ghi công" | Đơn Mẫu 16, CCCD | Xã | ✅ code + deploy, chờ chạy thử |
| 2 | `cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong` | 1.010814 | Cấp bổ sung, cấp lại giấy chứng nhận người có công | Đơn Mẫu 25 NĐ 131/2021, CCCD | Xã | ✅ code + deploy, chờ chạy thử |
| 3 | `bo-sung-than-nhan-liet-si` | 1.010825 | Bổ sung tình hình thân nhân trong hồ sơ liệt sĩ | Đơn Mẫu 26/06, CCCD, giấy tờ chứng minh quan hệ | Xã | ✅ code + deploy, chờ chạy thử |
| 4 | `tham-vieng-mo-liet-si` | 1.013750 | Thăm viếng mộ liệt sĩ | Giấy giới thiệu / đơn Mẫu 31/42, CCCD | Xã | ✅ code + deploy, chờ chạy thử |
| 5 | `giai-quyet-che-do-khang-chien` | 1.010819 | Chế độ người hoạt động kháng chiến | Bản khai Mẫu 11, CCCD, Huân/Huy chương | Xã | ✅ code + deploy, chờ chạy thử |
| 6 | `sua-doi-thong-tin-ho-so-nguoi-co-cong` | 1.010826 | Sửa đổi thông tin cá nhân trong hồ sơ người có công | Đơn Mẫu 26, CCCD | **Sở** | ✅ code + deploy, chờ chạy thử |
| 7 | `mai-tang-dan-cong-hoa-tuyen` | 1.014359 | Mai táng phí cho dân công hỏa tuyến | Bản khai Mẫu 02-MTP, QĐ trợ cấp, trích lục khai tử, biên bản Mẫu 80A | Xã | ✅ code + deploy, chờ chạy thử |

Đã làm cho cả 7 thủ tục: entry trong `procedure_registry.py` (khuôn `tro-cap-tho-cung-liet-si`, `maePortal`, `bxdFlow`
4 bước), gợi ý chọn thủ tục, tên tiếng Mông (BẢN NHÁP; từ mới "ntxa" = mộ, "tsov rog" = chiến tranh, "tub rog" = bộ
đội), test ở `test_mae_agency_cap_xa.py` và `test_flow_profiles.py`. Thử chéo bằng chữ trên toàn registry: 10 thủ
tục Bộ Nội vụ đều tự nhận đúng trang của mình.

Lưu ý:

- **Cấp cơ quan là suy luận, CHƯA thấy trên cổng thật.** `ke_khai_links` không phân biệt được xã hay Sở (`di-chuyen-ho-so`
  ở cấp Sở mà cũng không có `selectSo`). Căn cứ: NĐ 131/2021 và giấy tờ của từng pipeline (công văn UBND xã, bản khai
  có xác nhận xã). #6 đặt cấp Sở vì đơn gửi Sở nơi quản lý hồ sơ gốc. Khi chạy thử phải xem hộp thoại chọn cơ quan
  là "Phường/Xã" hay "Sở". Nếu sai thì sửa cờ `maeAgencyLevel` / `agencyProvinceOnly` + `agencySoFirst` + `agencyDeptLabel`.
- **#5, #6, #7 không có nút "Thêm giấy tờ"** trên cổng. Giấy tờ ngoài ô cố định (CCCD, sổ BHXH, biên bản 80A…) chỉ dùng
  để đọc và điền, không đính lên cổng. #7 dồn mọi tệp vào ô 1, riêng trích lục khai tử vào ô 2.
- **#7** đã có link, nhưng nằm dưới key khác trong `ke_khai_links.json` (`giai-quyet-che-do-mai-tang-dan-cong-hoa-tuyen`,
  mã 1.014359), nên uuid + mã được khai tay trong `detect`.
- Trang kê khai (`apply-online/<id>`) chưa có id SPA, trừ #5 (lấy từ lõi). Hiện nhận bằng cụm tên. Khi chạy thử nên ghi
  lại id để thêm vào `urlIncludes`.
- **#3 và #6** cùng đơn Mẫu 26: #3 nhận theo "bổ sung tình hình thân nhân trong hồ sơ liệt sĩ", #6 theo "bổ sung thông
  tin cá nhân" + "hồ sơ người có công".
- **#1 và #2**: #1 nhận theo "cấp lại bằng" + "tổ quốc ghi công", #2 theo "cấp bổ sung hoặc cấp lại giấy chứng nhận
  người có công".
- **#5 và #7**: #7 ghi "kháng chiến chống Pháp, chống Mỹ … nhiệm vụ quốc tế", không trùng cụm của #5.
- Chưa tạo `handfree/field_review.py` cho 7 thủ tục (không thêm file mới), nên chưa có vòng "Bổ sung các thông tin
  còn thiếu". Luồng 4 bước vẫn chạy.

### B. Y tế — Sở Y tế (4) — ✅ XONG 24/10

Cổng `dichvucongbyt.moh.gov.vn`. Bước "Hình thức nhận kết quả" (`supportsIgateResultStep`) tự gắn vào entry nào có
`urlScope` là host này.

| # | Key | Mã TTHC | Tên ngắn | Entry mẫu | Trạng thái |
|---|---|---|---|---|---|
| 8 | `cap-lai-giay-phep-hanh-nghe-truoc-2024` | 1.012290 | Cấp lại giấy phép hành nghề (cấp trước 01/01/2024) | `cap-moi-giay-phep-hanh-nghe-chuyen-tiep` (field-key trùng khít) | ✅ code + deploy, chờ chạy thử |
| 9 | `dieu-chinh-giay-phep-hoat-dong-kcb` | 1.012280 | Điều chỉnh giấy phép hoạt động khám bệnh, chữa bệnh | `cap-moi-giay-phep-hoat-dong-kham-benh-chua-benh` | ✅ code + deploy, chờ chạy thử |
| 10 | `cap-chung-chi-hanh-nghe-duoc` | 1.014092 | Cấp chứng chỉ hành nghề dược | `cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te` | ✅ code + deploy, chờ chạy thử |
| 11 | `cong-bo-co-so-du-dieu-kien-tiem-chung` | 2.000655 | Công bố cơ sở đủ điều kiện tiêm chủng | `dang-ky-hanh-nghe` | ✅ code + deploy, chờ chạy thử |

Đã làm cho cả 4: `flowProfile: "xay-dung"`, cấp Sở Y tế (`agencyProvinceOnly` + `agencySoFirst` + `agencyDeptLabel`),
`hideRepeatableHint: False`, `detect` có urlScope `dichvucongbyt.moh.gov.vn` + `dichvucong.gov.vn` (nên bước "Hình
thức nhận kết quả" tự gắn), gợi ý chọn thủ tục, tên tiếng Mông (BẢN NHÁP; từ mới "txhaj tshuaj" = tiêm, "tshaj tawm" =
công bố), test ở `test_flow_profiles.py`. Thử chéo bằng chữ trên cổng Bộ Y tế: 4 thủ tục nhận đúng trang của mình.

Lưu ý:

- **#8, #9** không có `selectSo` trong `ke_khai_links` nhưng vẫn đặt cấp Sở, theo hai bản "cấp mới" cùng form (cũng
  thiếu `selectSo` mà trợ lý chọn Sở). Khi chạy thử phải xem DVCQG có toggle "Sở" không.
- **#11** để urlScope cả `dichvucongbyt.moh.gov.vn` và `dichvucong.gov.vn`: pipeline ghi "hệ thống TTHC Bộ Y tế" nhưng
  doc cũ ghi DVCQG. Khi chạy thử xem trang kê khai nằm ở host nào; nếu là host khác thì phải thêm vào `urlScope`.
- **#9, #11** có chủ hồ sơ là CƠ SỞ (phòng khám, cơ sở tiêm chủng), không phải cá nhân.

- **#8** phải tách với cấp mới và điều chỉnh GPHN chuyển tiếp. Cả ba có chung cụm "kiểm tra đánh giá năng lực hành
  nghề", nên `textIncludes` phải dùng cụm đầu "cấp lại giấy phép hành nghề đối với trường hợp được cấp trước ngày 01
  tháng 01 năm 2024". Mở trang này rồi thử chéo: trang không được nhận thành thủ tục kia, và ngược lại.
- **#9** phải tách với cấp mới GPHĐ.
- **#8 và #9** có link, nhưng trong `ke_khai_links.json` nằm dưới key khác (xem mục
  [Link nằm dưới key khác](#link-nằm-dưới-key-khác-trong-ke_khai_linksjson)), nên phải khai tay uuid + mã vào `detect`.
- **#10 và #11** có `selectSo` trong `ke_khai_links`, nên đặt `agencyProvinceOnly` + `agencySoFirst` +
  `agencyDeptLabel: "Sở Y tế"`.
- Pipeline **#11** ghi cổng DVCQG chứ không ghi `dichvucongbyt`. Mở link xem trang chuyển sang cổng nào trước khi đặt
  `urlScope`.

### C. Xây dựng, giao thông — Sở Xây dựng (5) — ✅ XONG 3/5 ngày 24/10 (#13, #16 chờ link)

Cổng `dvc.moc.gov.vn`, `flowProfile: "xay-dung"`. Entry mẫu: `cap-giay-phep-lien-van-viet-lao`.

| # | Key | Mã TTHC | Tên ngắn | Giấy tờ chính | Cấp cơ quan | Trạng thái |
|---|---|---|---|---|---|---|
| 12 | `chap-thuan-dau-noi-tam` | 1.000314 | Chấp thuận vị trí đấu nối tạm vào đường bộ | Văn bản đề nghị, hợp đồng thi công / chủ trương đầu tư, bản vẽ nút giao | Tỉnh + Xã | ✅ code + deploy, chờ chạy thử |
| 13 | `cap-gcnkncm-cccm` | — | Cấp, cấp lại, chuyển đổi GCN khả năng chuyên môn, chứng chỉ chuyên môn (thuyền viên) | Đơn, GCNKNCM cũ, giấy khám sức khỏe, ảnh 2x3, CCCD | | ⏸ chờ link |
| 14 | `gia-han-luu-hanh-phuong-tien-lao` | 1.002063 | Gia hạn thời gian lưu hành cho phương tiện của Lào | Giấy đề nghị Mẫu 07, giấy phép liên vận, CCCD | Sở | ✅ code + deploy, chờ chạy thử |
| 15 | `dang-ky-lai-phuong-tien-chuyen-quyen-so-huu-khong-doi-co-quan` | 1.004002 | Đăng ký lại phương tiện thủy khi chuyển quyền sở hữu | Biên lai trước bạ, GCN an toàn kỹ thuật, hợp đồng + hóa đơn + GCN cũ, Đơn 07 + Đơn xóa 10 | Sở | ✅ code + deploy, chờ chạy thử |
| 16 | `xoa-dang-ky-phuong-tien-thuy` | — | Xóa đăng ký phương tiện thủy nội địa | Theo `uploadHint` lõi | | ⏸ chờ link |

Đã làm cho #12, #14, #15: entry trong `procedure_registry.py` (`flowProfile: "xay-dung"`, `detect` có urlScope
`dvc.moc.gov.vn` + `dichvucong.gov.vn`, mã + uuid, cụm tên), `hideRepeatableHint: False` (bảng thành phần hồ sơ dòng
cố định), gợi ý chọn thủ tục, tên tiếng Mông (BẢN NHÁP, chỉ ghép từ chữ đã có), test ở `test_flow_profiles.py`.
Thử chéo bằng chữ trên `dvc.moc.gov.vn`: 3 thủ tục nhận đúng trang của mình, không đè lên liên vận hay lòng đường.

Lưu ý:

- **Cấp cơ quan:** #14, #15 có `selectSo` trong `ke_khai_links` → chọn Sở Xây dựng. #12 không có → chọn đủ Tỉnh + Xã
  như `cap-phep-long-duong-via-he`. Nhưng `ke_khai` không đáng tin tuyệt đối (liên vận cũng không có `selectSo` mà
  trợ lý chọn Sở), nên khi chạy thử #12 phải xem DVCQG đưa sang đúng cơ quan không. Hộp thoại "Chọn trường hợp giải
  quyết" của cổng vẫn đọc lựa chọn thật và hỏi người dân (`maeDialogChoice`).
- **#12** có đối tượng là "đơn vị đề nghị" (nhà thầu / chủ đầu tư), gần với tổ chức hơn người dân. Đã làm vì nằm trong
  danh sách, nhưng ít người dân dùng.
- **#14 và #15** dùng engine tách/gộp trang PDF (`sourceSegments`). Extension trợ lý đã có engine này, BE chỉ phát khi
  extension báo `supportsSourceSegments`. #14 KHÔNG có nút "Thêm giấy tờ": giấy tờ khác đính chung dòng 1.
  #15: căn cước chỉ dùng để điền, không đính.
- **#14** tách với `cap-giay-phep-lien-van-viet-lao`: #14 nhận theo cả cụm "gia hạn thời gian lưu hành tại Việt Nam cho
  phương tiện của Lào". Link của #14 nằm dưới key khác (`gia-han-luu-hanh-phuong-tien-lao-tai-viet-nam`) nên uuid +
  mã khai tay trong `detect`.
- **#15 và #16** cùng nhóm phương tiện thủy, nên khi làm #16 phải tách "đăng ký lại" với "xóa đăng ký" trong gợi ý chọn
  thủ tục. #15 cũng phải tách với đăng ký tàu cá (Bộ NN&MT).
- **#13 và #16** chưa có link trong `ke_khai_links.json`.

### D. Nông nghiệp, thủy sản, thú y — Sở NN&MT (3)

Entry mẫu: `cap-gcn-dang-ky-tau-ca`, có `urlScope` `dichvucongnnmt.mae.gov.vn` + `dichvucong.gov.vn`.

| # | Key | Mã TTHC | Tên ngắn | Giấy tờ chính | Trạng thái |
|---|---|---|---|---|---|
| 17 | `cap-van-ban-chap-thuan-tau-ca` | 1.004344 | Văn bản chấp thuận đóng mới, cải hoán, thuê, mua tàu cá | Tờ khai Mẫu 12.TC, CCCD | ✅ code + deploy 24/10, chờ chạy thử |
| 18 | `cap-lai-chung-chi-hanh-nghe-thu-y` | 1.005319 | Cấp lại chứng chỉ hành nghề thú y | Đơn Mẫu 03.HNTY, CCCD, CCHN cũ | Chưa làm |
| 19 | `ho-tro-co-so-san-xuat-thiet-hai-dich-benh-dong-vat` | 1.013997 | Hỗ trợ cơ sở bị thiệt hại do dịch bệnh động vật | Đơn Mẫu 2a/2b NĐ 116/2025, biên bản tiêu hủy, CCCD | Chưa làm |

Lưu ý:

- **#17** đã làm theo khuôn `cap-gcn-dang-ky-tau-ca`: DVCQG chỉ chọn Tỉnh → trang MAE chọn Sở NN&MT (`maePortal`). Nhưng
  `ke_khai_links` không khai `provinceOnlyAgency` như bản đăng ký tàu, nên cấp Sở là suy ra theo thẩm quyền (cơ quan
  thủy sản cấp tỉnh). Khi chạy thử phải kiểm. Cụm nhận diện "cấp văn bản chấp thuận đóng mới, cải hoán, thuê, mua tàu
  cá" không đụng đăng ký tàu cá. Xóa đăng ký tàu cá vẫn chưa làm, vì cần `add-document-dialog`.
- **#18** có `selectSo`. Thủ tục này phải tách với gia hạn CCHN thú y, cũng chưa làm vì cần `add-document-dialog`.
- **#19** có cổng ghi là "Cổng ngành Nông nghiệp và Môi trường". Mở link xem host thật.

### E. Giáo dục — Sở GD&ĐT (1)

Cổng `dvc.moet.gov.vn`. Entry mẫu: `cap-ban-sao-van-bang-so-goc`.

| # | Key | Mã TTHC | Tên ngắn | Giấy tờ chính |
|---|---|---|---|---|
| 20 | `mien-giam-hoc-phi-gdnn-dai-hoc-tu-thuc` | 1.014335 | Miễn, giảm học phí (giáo dục nghề nghiệp, đại học tư thục) | Đơn Phụ lục IV NĐ 238/2025, giấy xác nhận của trường, CCCD |

Lưu ý: mapper phát `dom-expect`. `fill-core.js` của trợ lý đã có nhánh này.

## Lịch đề xuất (5 thủ tục mỗi ngày)

Lũy kế tính theo registry thật. Lúc lập kế hoạch đếm 81 nhưng chưa cộng `cap-gcn-dang-ky-tau-ca`; nhóm A xong sớm
ngày 24/10, nên lịch dời lên một ngày.

| Ngày | Thủ tục | Lũy kế |
|---|---|---|
| T7 24/10 | ✅ #1–#7 (người có công), ✅ #12, #14, #15 (Xây dựng), ✅ #8–#11 (Y tế), ✅ #17 (NN&MT) | 96 |
| T2 26/10 | #18–#19 (NN&MT), #20 (GD&ĐT) | 99 |
| T3 27/10 | Chạy thử nhóm A, B, C, #17 trên cổng thật, sửa cấp cơ quan nếu sai | 99 |
| T4 28/10 | Dự phòng sửa lỗi chạy thử | 99 |
| T5 29/10 | #13, #16 nếu đã tìm được link; nếu chưa thì lấy 2 thủ tục từ dự bị | 101 |
| T6 30/10 | Hồi quy toàn bộ + deploy bản chốt | 101 |

Mỗi ngày deploy Docker một lần, gom cả nhóm vào lần đó. Sau mỗi lần dán BE mới thì đếm lại registry trợ lý.

## Link nằm dưới key khác trong `ke_khai_links.json`

Có link, nhưng key trong `ke_khai_links.json` khác key ở lõi, nên `with_ke_khai_detect_urls` không tự gộp URL. Khi viết
entry trợ lý phải khai tay uuid + mã TTHC vào `detect.urlIncludes` (như #7).

| # | Key lõi | Key trong `ke_khai_links` | Mã |
|---|---|---|---|
| 7 | `mai-tang-dan-cong-hoa-tuyen` | `giai-quyet-che-do-mai-tang-dan-cong-hoa-tuyen` | 1.014359 |
| 8 | `cap-lai-giay-phep-hanh-nghe-truoc-2024` | `cap-lai-giay-phep-hanh-nghe-cap-truoc-2024` | 1.012290 |
| 9 | `dieu-chinh-giay-phep-hoat-dong-kcb` | `dieu-chinh-giay-phep-hoat-dong-kham-benh-chua-benh` | 1.012280 |
| 14 | `gia-han-luu-hanh-phuong-tien-lao` | `gia-han-luu-hanh-phuong-tien-lao-tai-viet-nam` | 1.002063 |

## Còn thiếu link — cần tìm uuid DVCQG

Không có trong `ke_khai_links.json`, kể cả khi dò theo tên thủ tục. Tìm link "Nộp trực tuyến" trên DVCQG
(`dichvucong.gov.vn/thu-tuc-hanh-chinh/<uuid>`) và mã TTHC, rồi thêm vào `ke_khai_links.json` và `keKhaiUrl`.

| # | Key | Nhóm | Ghi chú |
|---|---|---|---|
| 13 | `cap-gcnkncm-cccm` | Xây dựng | Thuyền viên |
| 16 | `xoa-dang-ky-phuong-tien-thuy` | Xây dựng | Phải tách với đăng ký lại phương tiện thủy (#15) |

## Danh sách dự bị

Dùng khi một thủ tục trong danh sách chính bị kẹt.

| Key | Mã | Vì sao chưa vào danh sách chính |
|---|---|---|
| `dang-ky-lap-dat-su-dung-nuoc-sach` | 3.000598 | Mã địa phương, chưa rõ cổng nào |
| `chuyen-doi-ten-hop-dong-nuoc-sach` | 3.000600 | Như trên |
| `xac-nhan-dieu-kien-dien-tich-nha-o-dang-ky-thuong-tru` | 1.013314 | Pipeline viết cho cổng Quảng Ngãi, trợ lý chưa chạy cổng này |
| `xet-tuyen-vien-chuc` | 3.000601 | Mã địa phương, chưa rõ cổng |
| `thi-tuyen-cong-chuc` | 1.014111 | Có link + pipeline điền; chưa rõ cổng (thêm 24/10) |
| `xet-tuyen-cong-chuc` | 1.014113 | Có link + pipeline điền; chưa rõ cổng (thêm 24/10) |
| `cap-moi-chung-chi-hanh-nghe-moi-gioi-bat-dong-san` | 1.012906 | Chưa rõ cổng; có `selectSo` |
| `cap-doi-gcn-da-nang` | — | Cổng Đà Nẵng chưa mở đường trên trợ lý |

## Không đưa vào đợt này

| Nhóm | Lý do |
|---|---|
| Lào Cai (đất đai, đầu tư), ~32 thủ tục | Nhiều bảng đính kèm chia nhánh (`sectionHeader`), extension trợ lý chưa có engine này. Chưa mở cổng. |
| Gia hạn GPXD, xóa tàu cá, gia hạn CCHN thú y, nội quy lao động, điện mặt trời mái nhà, tính tiền SDĐ Quảng Ngãi | Cần `add-document-dialog` |
| Phù hiệu xe kinh doanh vận tải | Cần `dom-click` |
| Thẻ hướng dẫn viên du lịch (4), trò chơi điện tử, xuất bản, băng-rôn quảng cáo | Cổng Bộ VHTTDL cần `fill-liz.js`, extension trợ lý chưa có |
| Đất đai Quảng Ninh, Quảng Ngãi, Ninh Bình, Lâm Đồng, Lai Châu | Trợ lý chưa chạy các cổng này, cổng nào cũng phải mở đường riêng |
| Đất đai Đà Nẵng (16) | Cổng Đà Nẵng chưa mở đường. Nên làm `cap-doi-gcn-da-nang` trước. |
| Thành lập công ty, chủ trương đầu tư, khuyến mại, hội cấp tỉnh, ATTP Công Thương | Đối tượng là doanh nghiệp hoặc tổ chức, không phải người dân |
| `cap-hoc-tap-bac-ninh` | Đã quyết định bỏ qua ngày 23/10 |
| `ho-tro-mai-tang` (1.001731) | Trùng nghiệp vụ với `ho-tro-mai-tang-1116910`, thủ tục này đã có trên trợ lý |
| `dien-thong-tin-tai-khoan-bac-ninh` | Đây là bước đăng nhập VNeID, không phải thủ tục |

## Thế nào là "xong" cho một thủ tục

1. Có entry trong `procedure_registry.py`, gợi ý chọn thủ tục và tên tiếng Mông.
2. Card hiện ra trên trợ lý và trợ lý nhận đúng trang. Thử chéo với các thủ tục dễ nhầm đã nêu ở từng nhóm.
3. Chạy thử một hồ sơ bằng **dữ liệu bịa**: chọn cơ quan → điền form → đính kèm → **dừng trước nút Nộp**.
4. Chạy pytest. `tests/handfree/unit/test_flow_profiles.py` phải cập nhật số đếm (hiện là 96). Test toàn bộ không
   được vượt baseline `11 failed, 4 errors`. Lỗi collect thứ 4 là `test_archive_worker.py` (thiếu `mongomock`), đến
   cùng bản BE 2676438. `tests/handfree/unit` hiện chỉ còn 2 đỏ môi trường Windows: `test_consent_pdf` (dấu `\` trong
   đường dẫn) và `test_asr_khong_lo_dia_chi` (thiếu `protobuf` mới). Test đỏ sẵn vì `cap-gcn-dang-ky-tau-ca` đã sửa
   ngày 24/10.
5. Deploy Docker: container `Up`, `/healthz` trả `{"ok":true}`.
