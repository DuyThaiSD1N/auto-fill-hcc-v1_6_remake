# Kế hoạch các thủ tục tiếp theo lên Trợ lý người dân (96 → …)

Lập ngày 25/10/2026, nối tiếp [20-thu-tuc-sap-len-tro-ly-2026-10-24.md](20-thu-tuc-sap-len-tro-ly-2026-10-24.md).

## Hiện trạng

Cập nhật 25/10/2026: **xong đợt 4** (deploy Docker local, `/healthz` ok) → trợ lý có **100** thủ tục. Đợt 5 **đang chặn**
vì chưa biết cổng thật (xem mục Đợt 5).

- Registry trợ lý (`app/channels/handfree/procedure_registry.py`) có **100** thủ tục (lúc lập kế hoạch: 96).
- Registry lõi (`app/procedures/registry.py`) có **222** thủ tục, tức **122** thủ tục đã có pipeline mà trợ lý chưa mở.
- Extension trợ lý 1.13.5 **chưa có** 5 engine: `add-document-dialog`, `sectionHeader`, `dom-click`, `dom-editgrid`,
  `fill-liz.js`. Đã có: `attp-row`, `sourceSegments` (tách trang PDF), `datagrid`, `dom-vehicle-add`, `dom-expect`.
- Cổng trợ lý đã chạy: Bộ Tư pháp / DVCQG, Bộ Nội vụ, Bộ Y tế, Bộ Xây dựng, Bộ NN&MT, Bộ GD&ĐT, Hộ kinh doanh,
  Bắc Ninh. **Chưa mở**: cổng tỉnh Đà Nẵng, Lào Cai, Ninh Bình, Lâm Đồng, Quảng Ngãi, Lai Châu, Quảng Ninh; Bộ Công
  Thương; Bộ VHTTDL.

## Tổng hợp 126 thủ tục chưa lên

| Đợt | Nội dung | Số thủ tục | Lũy kế nếu xong |
|---|---|---|---|
| 4 | Lên ngay: cổng đã chạy, có link, engine đủ | 4 | 100 |
| 5 | Có link, nhưng phải mở link xem cổng trước | 5 | 105 |
| 6 | Cổng đã chạy, **chờ link** | 5 | 110 |
| 7 | Mở cổng **Đà Nẵng** | 17 | 127 |
| 8 | Mở cổng **Lào Cai** | 21 | 148 |
| 9 | Mở cổng Ninh Bình, Lâm Đồng, Quảng Ngãi, Lai Châu, Quảng Ninh | 34 | 182 |
| 10 | Làm engine mới cho extension trợ lý | 21 | 203 |
| — | Không đưa lên (doanh nghiệp / tổ chức, trùng, không phải thủ tục) | 19 | — |
| | **Tổng** | **126** | |

Mỗi thủ tục, như đợt trước, cần: entry trong `procedure_registry.py`, gợi ý chọn thủ tục trong
`procedure_picker/prompt.py`, tên tiếng Mông trong `script_mong.py` (BẢN NHÁP chờ anh Dư soát), cập nhật test
`test_flow_profiles.py` (số đếm + khối kiểm cấp cơ quan). Không tạo file mới. "Xong" theo mục
[Thế nào là "xong"](20-thu-tuc-sap-len-tro-ly-2026-10-24.md#thế-nào-là-xong-cho-một-thủ-tục) của kế hoạch trước.

Bài học đợt trước, áp dụng cho mọi đợt:

- **Link có thể nằm dưới key khác** trong `ke_khai_links.json`. Dò theo tên thủ tục trước khi kết luận "chưa có link";
  nếu key lệch thì khai tay uuid + mã TTHC vào `detect.urlIncludes`.
- **`selectSo` trong `ke_khai_links` không đáng tin tuyệt đối** để suy cấp cơ quan (liên vận, di chuyển hồ sơ đều
  thiếu mà vẫn là cấp Sở). Ghi rõ cấp cơ quan là suy luận và kiểm khi chạy thử.
- **Đọc code planner, đừng tin chú thích đầu file**: tàu cá và CCHN dược ghi "bỏ qua căn cước" nhưng code thật đính
  căn cước. Chạy planner với hồ sơ bịa (script `kiem_e2e.py`) để thấy tệp nào vào dòng nào.

## Đợt 4 — lên ngay (4 thủ tục → 100) — ✅ XONG 25/10

| # | Key | Mã | Tên | Cổng | Cơ quan (đã đặt) | Entry mẫu | Trạng thái |
|---|---|---|---|---|---|---|---|
| 18 | `cap-lai-chung-chi-hanh-nghe-thu-y` | 1.005319 | Cấp lại chứng chỉ hành nghề thú y | Bộ NN&MT | Sở NN&MT (`provinceOnlyAgency` + `selectSo`) | `cap-gcn-dang-ky-tau-ca` | ✅ code + deploy, chờ chạy thử |
| 19 | `ho-tro-co-so-san-xuat-thiet-hai-dich-benh-dong-vat` | 1.013997 | Hỗ trợ cơ sở sản xuất bị thiệt hại do dịch bệnh động vật | Cổng ngành NN&MT | UBND cấp xã (lõi ghi) | `cap-gcn-attp-nong-lam-thuy-san` (cấp xã) | ✅ code + deploy, chờ chạy thử |
| 20 | `mien-giam-hoc-phi-gdnn-dai-hoc-tu-thuc` | 1.014335 | Miễn, giảm học phí (GDNN, đại học tư thục) | Bộ GD&ĐT | Tỉnh + Xã (mapper lõi: UBND cấp xã nơi thường trú) | `cap-ban-sao-van-bang-so-goc` | ✅ code + deploy, chờ chạy thử |
| 21 | `cap-moi-chung-chi-hanh-nghe-moi-gioi-bat-dong-san` | 1.012906 | Cấp mới chứng chỉ hành nghề môi giới bất động sản | Bộ Xây dựng (lõi ghi "Sở Xây dựng") | Sở Xây dựng (`selectSo`) | `gia-han-luu-hanh-phuong-tien-lao` | ✅ code + deploy, chờ chạy thử |

Kết quả kiểm 25/10:

- Đối chiếu lõi (link, mã duy nhất, pipeline, nhận diện, card, tiếng Mông, bước chọn cơ quan): 4/4 đạt. Riêng học phí,
  trang giả lập phải có đúng tiêu đề panel "Đơn đề nghị chi trả tiền miễn giảm học phí theo mẫu tại Phụ lục IV" (cụm của
  lõi) thì mới nhận ra.
- Agent chọn thủ tục (LLM thật): 12/12 câu đúng (8 câu cho thủ tục mới, 4 câu cho thủ tục cũ dễ nhầm).
- Chạy thật pipeline điền + đính kèm với hồ sơ bịa: điền 14–28 ô, đúng người. Đính kèm thật:
  - #18: Đơn + chứng chỉ cũ → dòng "Đơn đăng ký cấp lại"; **căn cước không đính**.
  - #19: Đơn + biên bản tiêu hủy gộp một tệp → dòng Đơn; **căn cước không đính**.
  - #20: dòng 1 gộp giấy xác nhận trường + **căn cước**; dòng 2 là Đơn PL IV.
  - #21: 6 dòng đúng; Đơn vào cả dòng 3 và dòng 6 (khi không có ảnh rời); cảnh báo căn cước chưa chứng thực.
- Test: `tests/handfree/unit` 907 pass (2 đỏ môi trường Windows như cũ); toàn bộ `11 failed, 3011 passed, 39 skipped,
  4 errors` = baseline.
- Tiếng Mông (BẢN NHÁP), từ mới: "tsiaj" (vật nuôi), "kab mob" (dịch bệnh), "kho tsiaj" (thú y), "nyiaj kawm ntawv"
  (học phí), "zam" (miễn), "neeg nruab nrab" (người môi giới).

Cần kiểm khi chạy thử: host trang kê khai của #19 (đặt `dichvucongnnmt.mae.gov.vn`) và #21 (đặt `dvc.moc.gov.vn`); #19
có hộp thoại "Phường/Xã" trên cổng ngành không; #20 DVCQG có chọn đủ Tỉnh + Xã không.

Lưu ý ban đầu:

- **#18** phải tách với `gia-han-chung-chi-hanh-nghe-thu-y` (đợt 10, cần `add-document-dialog`): "cấp lại" ≠ "gia hạn".
- **#19** lõi không khai `urlScope`. Mở link xem host thật (có thể là `dichvucongnnmt.mae.gov.vn`) trước khi đặt
  `urlScope`. Cụm tên rất dài, đủ tách.
- **#20** mapper phát `dom-expect`, `fill-core.js` của trợ lý đã có nhánh này. Đối tượng là sinh viên.
- **#21** planner tách trang (`sourceSegments`): Đơn trang 1 + CCCD trang 2 của cùng một PDF về 2 dòng. Phần I người nộp
  khóa theo tài khoản. Xác nhận host là `dvc.moc.gov.vn` khi mở link.

## Đợt 5 — có link, phải xem cổng trước (5 thủ tục → 105)

| Key | Mã | Tên | Vấn đề cần giải quyết |
|---|---|---|---|
| `thi-tuyen-cong-chuc` | 1.014111 | Thi tuyển công chức | Lõi không ghi cổng. Cụm nhận diện "Thi tuyển công chức" quá ngắn, trùng `thi-tuyen-cong-chuc-mot-cua-moha` (đợt 6) |
| `xet-tuyen-cong-chuc` | 1.014113 | Xét tuyển công chức | Như trên |
| `xet-tuyen-vien-chuc` | 3.000601 | Xét tuyển viên chức (NĐ 85/2023) | Mã địa phương. Phải tách với `xet-tuyen-vien-chuc-lai-chau` (đợt 9) |
| `dang-ky-lap-dat-su-dung-nuoc-sach` | 3.000598 | Đăng ký lắp đặt sử dụng nước sạch | Mã địa phương, chưa rõ cổng / tỉnh nào |
| `chuyen-doi-ten-hop-dong-nuoc-sach` | 3.000600 | Chuyển đổi tên trong hợp đồng nước sạch | Như trên |

Việc đầu tiên: mở 5 link DVCQG, ghi host thật và tỉnh áp dụng. Nếu là cổng tỉnh chưa mở thì chuyển sang đợt của tỉnh đó.

**⏸ Chặn ngày 25/10.** Đã thử xác định cổng mà không mở link:

- Code lõi: cả 5 pipeline phát field Form.io `data[...]` (nền iGate) nhưng **không ghi host** ở registry, pipeline, test
  hay git log. Nền iGate dùng chung cho cổng bộ và nhiều cổng tỉnh nên không đủ để biết cổng.
- Trang DVCQG là SPA, đọc tự động chỉ ra tiêu đề trang. Tra web theo mã 3.000598 / 3.000601 không ra trang nào nêu mã.
- Có một nguồn web (chưa kiểm chứng) nói Nghị định 259/2026/NĐ-CP bãi bỏ thủ tục thi tuyển, xét tuyển viên chức. Cần
  xác minh trước khi đưa `xet-tuyen-vien-chuc` lên.

Cần anh/chị mở 5 link dưới đây (đăng nhập VNeID), bấm "Nộp trực tuyến", rồi gửi lại **host + đường dẫn trang kê khai**
và **hộp thoại chọn cơ quan** (Tỉnh + Xã hay Sở, có trang "chọn nơi và loại" không):

| Key | Link DVCQG |
|---|---|
| `thi-tuyen-cong-chuc` | https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d90b5-0f50-773c-88d5-07d6ef77b613 |
| `xet-tuyen-cong-chuc` | https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-2326-7367-83e6-f242eef7cbc5 |
| `xet-tuyen-vien-chuc` | https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019f1834-0004-71bd-abd7-6c634065e005 |
| `dang-ky-lap-dat-su-dung-nuoc-sach` | https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019ef895-259b-72b1-ba55-179108f16bb1 |
| `chuyen-doi-ten-hop-dong-nuoc-sach` | https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019ef89f-fba4-7698-9dbb-f18e145be976 |

## Đợt 6 — cổng đã chạy, chờ link (5 thủ tục → 110)

| Key | Tên | Cổng | Ghi chú |
|---|---|---|---|
| `cap-gcnkncm-cccm` | Cấp, cấp lại, chuyển đổi GCN khả năng chuyên môn, chứng chỉ chuyên môn (thuyền viên) | Bộ Xây dựng | #13 kế hoạch trước |
| `xoa-dang-ky-phuong-tien-thuy` | Xóa đăng ký phương tiện thủy nội địa | Bộ Xây dựng | #16 kế hoạch trước; tách với đăng ký lại (đã lên) |
| `thi-tuyen-cong-chuc-mot-cua-moha` | [Một cửa Bộ Nội vụ] Thi tuyển công chức | Bộ Nội vụ (một cửa) | Làm cùng đợt 5 để tách nhận diện |
| `cap-lai-giay-chung-nhan-du-dieu-kien-an-toan-thuc-pham` | Cấp lại GCN đủ điều kiện ATTP (cơ sở sản xuất, kinh doanh) | Chưa rõ | Xem pipeline thuộc ngành nào (Y tế / Công Thương) |
| `cap-gcn-attp-cong-thuong` | Cấp GCN đủ điều kiện ATTP (Công Thương) | Bộ Công Thương — **chưa mở** | Có link xong vẫn phải mở cổng Bộ Công Thương |

Cần anh/chị tìm uuid DVCQG cho cả 5 thủ tục.

## Đợt 7 — mở cổng Đà Nẵng (17 thủ tục)

Việc mở đường: `urlScope` `dichvucong.danang.gov.vn`, cách chọn cơ quan trên cổng Đà Nẵng, `provinceOnly: ["danang"]`,
thử 1 thủ tục đầu đến bước dừng trước nút Nộp. Nên mở đường bằng `cap-doi-gcn-da-nang` (thủ tục hay dùng, đã đề xuất
từ 22/10), nhưng thủ tục này còn thiếu link → nếu chưa có link thì mở đường bằng `xoa-dang-ky-bien-phap-bao-dam-da-nang`.

**Có link (9):**

| Key | Mã | Tên | Cơ quan |
|---|---|---|---|
| `dang-ky-bien-dong-chia-tach-hop-nhat-sap-nhap-to-chuc-cap-gcn-tung-thua` | 1.013977 | Đăng ký biến động do chia, tách, hợp nhất, sáp nhập tổ chức | Sở |
| `dang-ky-bien-dong-dat-dai-da-nang` | 1.013831 | Đăng ký biến động (chuyển đổi, chuyển nhượng, thừa kế, tặng cho…) | |
| `dang-ky-bien-phap-bao-dam-qsdd` | 1.011441 | Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất | Sở |
| `dang-ky-dat-dai-lan-dau-nha-nuoc-giao-quan-ly` | 1.012756 | Đăng ký đất đai lần đầu (Nhà nước giao đất để quản lý) | Sở |
| `dang-ky-tai-san-gan-lien-thua-dat-da-cap-gcn` | 1.013995 | Đăng ký tài sản gắn liền với thửa đất đã cấp GCN | Sở |
| `dang-ky-thay-doi-bien-phap-bao-dam-qsdd` | 1.011442 | Đăng ký thay đổi biện pháp bảo đảm | Sở |
| `ho-tro-chi-phi-van-chuyen-nguoi-tu-vong-den-co-so-hoa-tang` | 3.000721 | Hỗ trợ chi phí vận chuyển người tử vong đến cơ sở hỏa táng | |
| `xac-dinh-lai-dien-tich-dat-o-gcn-truoc-2004` | 1.012817 | Xác định lại diện tích đất ở (GCN cấp trước 01/7/2004) | |
| `xoa-dang-ky-bien-phap-bao-dam-da-nang` | 1.011443 | Xóa đăng ký biện pháp bảo đảm | Sở |

**Chưa có link (8), cần tìm uuid DVCQG:** `cap-doi-gcn-da-nang` (cấp đổi GCN), `cap-gcn-so-nha-da-nang` (cấp mới/cấp lại
GCN số nhà), `chuyen-muc-dich-su-dung-dat-da-nang` (chuyển mục đích không phải xin phép), `dang-ky-dat-dai-lan-dau-da-nang`
(đăng ký đất đai lần đầu), `dinh-chinh-gcn-da-cap-da-nang` (đính chính GCN), `giao-thue-chuyen-muc-dich-dat-da-nang` (giao,
thuê, chuyển mục đích), `tach-hop-thua-dat-da-nang` (tách, hợp thửa), `xac-nhan-ho-so-so-nha-da-nang` (xác nhận hồ sơ số nhà).

Lưu ý: tên các thủ tục đất đai trùng với bản Bắc Ninh / Lào Cai / Ninh Bình → `urlScope` phải khóa đúng host Đà Nẵng,
không dựa vào cụm tên (xem cách Bắc Ninh làm).

## Đợt 8 — mở cổng Lào Cai (21 thủ tục)

Việc mở đường: `urlScope` `dichvucong.laocai.gov.vn`; nhiều thủ tục có 2 bản "Cấp Sở" và "Cấp phường/xã" (cùng mã) →
tách bằng cấp cơ quan, không bằng cụm tên. Còn 7 thủ tục Lào Cai cần `sectionHeader` → đợt 10.

**Có link (15):**

| Key | Mã | Tên | Cơ quan |
|---|---|---|---|
| `cho-thue-dat-thue-rung` | 1.115678 | Giao đất, cho thuê đất (không đấu giá…) | Xã |
| `dang-ky-bien-dong-chuyen-nhuong-thua-ke-tang-cho-dvcqg-lao-cai` | 1.013831 | Đăng ký biến động (chuyển nhượng, thừa kế, tặng cho) | Sở |
| `dang-ky-bien-dong-doi-ten-nguoi-su-dung-dat-lao-cai` | 1.013833 | Đăng ký biến động đổi tên / thay đổi thông tin người sử dụng đất | Sở |
| `dang-ky-cap-gcn-dien-tich-tang-them-nhan-chuyen-quyen-mot-phan-thua` | 1.115694 | Cấp GCN diện tích tăng thêm (nhận chuyển quyền một phần thửa) | Sở |
| `dang-ky-cap-gcn-dien-tich-tang-them-thay-doi-ranh-gioi` | 1.115693 | Cấp GCN diện tích tăng thêm do thay đổi ranh giới | Xã |
| `dang-ky-dat-dai-lan-dau-ho-gia-dinh-lao-cai` | 1.115689 | Đăng ký đất đai lần đầu (hộ gia đình, cá nhân) | Xã |
| `dieu-chinh-quyet-dinh-giao-dat-cap-xa-lao-cai` | 1.115680 | Điều chỉnh quyết định giao đất, cho thuê đất | Xã |
| `dinh-chinh-gcn-da-cap-dvcqg-lao-cai` | 1.012790 | Đính chính GCN đã cấp | Sở |
| `dinh-chinh-gcn-da-cap-lao-cai` | 1.115686 | Đính chính GCN đã cấp lần đầu có sai sót | Xã |
| `su-dung-dat-ket-hop-da-muc-dich-cap-xa` | 1.115682 | Sử dụng đất kết hợp đa mục đích | Xã |
| `tang-cho-qsdd-nha-nuoc-chua-cap-gcn` | 1.115690 | Tặng cho quyền sử dụng đất cho Nhà nước, cộng đồng | Xã |
| `xac-dinh-lai-dien-tich-dat-o-truoc-01-7-2004` | 1.115685 | Xác định lại diện tích đất ở (GCN trước 01/7/2004) | Xã |
| `xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep` | 1.115677 | Xác nhận tiếp tục sử dụng đất nông nghiệp | Sở |
| `xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep-lao-cai` | 1.013947 | Xác nhận tiếp tục sử dụng đất nông nghiệp (1.013947) | Sở |
| `xoa-dang-ky-bien-phap-bao-dam-lao-cai` | 1.011443 | Xóa đăng ký biện pháp bảo đảm | Sở |

**Chưa có link (6):** `dang-ky-bien-dong-chia-tach-to-chuc-lao-cai`, `dang-ky-bien-phap-bao-dam-lao-cai`,
`dang-ky-gcn-chuyen-quyen-truoc-2024-lao-cai`, `dang-ky-thay-doi-bien-phap-bao-dam-lao-cai`,
`dieu-chinh-quyet-dinh-giao-dat-lao-cai`, `giao-thue-dat-lao-cai`.

Lưu ý: hai bản "xác nhận tiếp tục sử dụng đất nông nghiệp" (1.115677 và 1.013947) phải xem có trùng nghiệp vụ không;
nếu trùng thì chỉ lên một bản.

## Đợt 9 — các tỉnh còn lại (34 thủ tục)

Mỗi tỉnh phải mở đường riêng như Đà Nẵng. Nên làm theo nhu cầu tài khoản đang dùng.

| Tỉnh | Có link | Chưa link | Ghi chú |
|---|---|---|---|
| Ninh Bình | `dang-ky-dat-dai-lan-dau-ninh-binh` (1.013978) | `cap-doi-gcn-ninh-binh`, `dang-ky-bien-dong-dat-dai-ninh-binh`, `dinh-chinh-da-cap-ninh-binh`, `dinh-chinh-gcn-da-cap-ninh-binh`, `giao-thue-chuyen-muc-dich-dat-ninh-binh` | 6 |
| Lâm Đồng | `chuyen-muc-dich-su-dung-dat-lam-dong` (1.116365), `dang-ky-dat-dai-lan-dau-lam-dong` (1.116360) | `dang-ky-dien-tich-tang-them-lam-dong`, `dinh-chinh-sai-sot-lam-dong` | 4 |
| Quảng Ngãi | `xac-nhan-dieu-kien-dien-tich-nha-o-dang-ky-thuong-tru` (1.013314) | `dang-ky-dat-dai-lan-dau-quang-ngai`, `dinh-chinh-sai-sot-quang-ngai`, `giao-thue-chuyen-muc-dich-dat-quang-ngai`, `ho-tro-chi-phi-hoa-tang-quang-ngai`, `xac-dinh-lai-dien-tich-dat-o-quang-ngai` | 6 (+1 cần `add-document-dialog` ở đợt 10) |
| Lai Châu | `dang-ky-dat-dai-tai-san-lan-dau-nguoi-o-nuoc-ngoai` (1.115583) | `dang-ky-dat-dai-lan-dau`, `dinh-chinh-sai-sot`, `xet-tuyen-vien-chuc-lai-chau` | 4 |
| Quảng Ninh | — | 14 thủ tục **chỉ có pipeline đính kèm** (không điền form) | 14 — lên dạng attach-only như chứng thực |

Quảng Ninh (14, đều đất đai, đa số "[Đặc thù] miền núi, hải đảo"): `cap-doi-gcn-do-do-dac-khong-nvtc-quang-ninh-mien-nui-hai-dao`,
`cap-doi-gcn-quang-ninh-mien-nui-hai-dao`, `cap-lai-gcn-do-bi-mat-quang-ninh` (1.115849), `chuyen-muc-dich-su-dung-dat-quang-ninh-mien-nui-hai-dao`,
`dang-ky-bien-dong-chuyen-muc-dich-sdd-khong-xin-phep-quang-ninh` (1.115846), `dang-ky-bien-dong-chuyen-nhuong-quang-ninh-mien-nui-hai-dao`,
`dang-ky-bien-dong-doi-ten-quang-ninh-mien-nui-hai-dao`, `dang-ky-bien-phap-bao-dam-quang-ninh` (1.011441),
`dang-ky-cap-gcn-toan-bo-dien-tich-dang-su-dung-quang-ninh` (1.115841), `dang-ky-dat-dai-lan-dau-quang-ninh-mien-nui-hai-dao`,
`dang-ky-tai-san-dat-quang-ninh-mien-nui-hai-dao`, `tach-hop-thua-dat-quang-ninh-mien-nui-hai-dao`,
`tinh-tien-su-dung-dat-nd-50-2026-quang-ninh` (1.115148), `xoa-dang-ky-bien-phap-bao-dam-quang-ninh` (1.011443).

## Đợt 10 — làm engine mới cho extension trợ lý (21 thủ tục)

Chép engine từ extension Auto Fill sang extension trợ lý (sửa extension, không đụng Docker), rồi mới thêm entry.

| Engine | Thủ tục cho người dân | Thủ tục tổ chức / doanh nghiệp | Ưu tiên |
|---|---|---|---|
| `add-document-dialog` | `gia-han-giay-phep-xay-dung` (1.013227), `xoa-dang-ky-tau-ca` (1.003681), `gia-han-chung-chi-hanh-nghe-thu-y` (2.001064), `tinh-tien-su-dung-dat-nd-50-2026-quang-ngai` (1.115148, cổng Quảng Ngãi) | `dang-ky-noi-quy-lao-dong` (2.001955), `thong-bao-phat-trien-nguon-dien-mat-troi-mai-nha` (1.115377) | **Cao** — 3 thủ tục bộ ngành dùng ngay được |
| `fill-liz.js` (Bộ VHTTDL) | `cap-the-huong-dan-vien-du-lich-noi-dia` (1.004623), `cap-doi-the-huong-dan-vien-du-lich-da-nang` (1.001432), `cap-lai-the-huong-dan-vien-du-lich-da-nang` (1.004614), `cap-the-huong-dan-vien-du-lich-tai-diem-da-nang` (1.001440) | `cap-gcn-diem-tro-choi-dien-tu-cong-cong` (1.013792), `cap-giay-phep-xuat-ban-tai-lieu-khong-kinh-doanh` (1.003868) | Trung bình — phải mở thêm cổng Bộ VHTTDL |
| `sectionHeader` | 6 thủ tục Lào Cai: `chuyen-muc-dich-su-dung-dat-khoan-1-dieu-175` (1.115679), `chuyen-muc-dich-su-dung-dat-lao-cai` (1.115651), `dang-ky-bien-dong-dat-dai-lao-cai` (1.115668), `dang-ky-bien-dong-thoa-thuan-thanh-vien-ho-gia-dinh-theo-ban-an` (1.115671), `dang-ky-dat-dai-cap-gcn-lan-dau-to-chuc` (1.115688), `thu-hoi-gcn-cap-lan-dau-khong-dung-quy-dinh-cap-lai` (1.115687) | `dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai` (1.115667), `thong-bao-san-pham-quang-cao-bang-ron` (1.004650, cần thêm `fill-liz`) | Sau đợt 8 (cần cổng Lào Cai) |
| `dom-click` | — | `cap-cap-lai-phu-hieu-xe-kinh-doanh-van-tai` (2.002288) | Thấp |

## Không đưa lên (19 thủ tục)

| Lý do | Thủ tục |
|---|---|
| Doanh nghiệp / tổ chức nộp | `thanh-lap-cong-ty-co-phan`, `thanh-lap-cong-ty-tnhh-hai-thanh-vien`, `thong-bao-sua-doi-bo-sung-noi-dung-chuong-trinh-khuyen-mai`, `dang-ky-khuyen-mai-may-rui-mot-tinh`, `bao-cao-to-chuc-dai-hoi-hoi-cap-tinh`, `chia-tach-sap-nhap-hop-nhat-hoi-cap-tinh`, `thong-bao-ket-qua-dai-hoi-phe-duyet-dieu-le-hoi-cap-tinh`, `cap-bo-sung-xe-tap-lai-cap-lai-giay-phep-xe-tap-lai`, `tham-dinh-bcnckt`, `to-chuc-kinh-te-nhan-chuyen-nhuong-qsdd-du-an`, `dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san`, `xoa-dang-ky-thue-cho-thue-lai-qsdd-du-an-ket-cau-ha-tang`, `chap-thuan-chu-truong-dau-tu-ubnd-tinh-lao-cai`, `chap-thuan-dieu-chinh-chu-truong-dau-tu-bql-lao-cai`, `dieu-chinh-du-an-dau-tu-ubnd-tinh-lao-cai` |
| Trùng nghiệp vụ thủ tục đã có | `ho-tro-mai-tang` (1.001731) — trùng `ho-tro-mai-tang-1116910` |
| Lõi đang tắt tự nhận diện, có bản Lào Cai thay | `dieu-chinh-dat-dai` (1.116531) |
| Không phải thủ tục | `dien-thong-tin-tai-khoan-bac-ninh` (bước đăng nhập VNeID) |
| Đã quyết bỏ qua 23/10 | `cap-hoc-tap-bac-ninh` |

## Lịch đề xuất

| Ngày | Việc | Lũy kế |
|---|---|---|
| CN 25/10 | ✅ Đợt 4 (#18–#21) + deploy | 100 |
| T3 27/10 | Chạy thử trên cổng thật 15 thủ tục đợt trước + đợt 4; sửa cấp cơ quan nếu sai | 100 |
| T4 28/10 | Đợt 5: mở 5 link xác định cổng, lên những thủ tục chạy trên cổng đã mở | ≤ 105 |
| T5 29/10 | Đợt 6 nếu đã có link; chép engine `add-document-dialog` sang extension trợ lý | ≤ 110 |
| T6 30/10 | 3 thủ tục `add-document-dialog` bộ ngành (gia hạn GPXD, xóa tàu cá, gia hạn CCHN thú y); hồi quy + deploy bản chốt | ≤ 113 |
| Từ 02/11 | Đợt 7 (Đà Nẵng) → đợt 8 (Lào Cai) → đợt 9 theo tỉnh đang có tài khoản dùng → phần còn lại của đợt 10 | |

Mốc 100 thủ tục (hạn 31/10) đạt được ngay khi xong đợt 4.

## Cần anh/chị cung cấp

1. uuid DVCQG cho: 5 thủ tục đợt 6, 8 thủ tục Đà Nẵng, 6 thủ tục Lào Cai, 16 thủ tục các tỉnh khác (đợt 9, trừ Quảng Ninh).
2. Quyết định có mở cổng tỉnh nào trước (Đà Nẵng đã đề xuất từ 22/10) và có mở cổng Bộ VHTTDL / Bộ Công Thương không.
3. Tài khoản test VNeID cho từng tỉnh khi mở cổng mới.
