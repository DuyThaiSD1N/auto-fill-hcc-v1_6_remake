# Thủ tục đất đai Bắc Ninh — cổng riêng `dichvucong.bacninh.gov.vn`

Lấy từ `auto-fill-hcc-backend/app/procedures/registry.py` (bản BE `5792794`, 21/10/2026).
Mọi entry đều khóa host bằng `urlScope: ["dichvucong.bacninh.gov.vn"]` và dùng engine `fill-bacninh.js`
(Liferay eForm + select2). Nhận trang theo `maThuTucHanhChinh=<mã>` trên URL.

## Đất đai (Sở NN&MT) — 10 thủ tục

| # | Key | Mã trên URL | Thủ tục | Lượt / TK | Trợ lý |
|---|---|---|---|---|---|
| 1 | `dinh-chinh-gcn-da-cap-bac-ninh` | 1.115436, 1.115476 | Đính chính giấy chứng nhận đã cấp | 14 / 2 | Đang thêm (chưa commit) |
| 2 | `cap-doi-gcn-bac-ninh` | 1.115464 | Cấp đổi GCN quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất | 9 / 3 | Đang thêm (chưa commit) |
| 3 | `tach-hop-thua-dat-bac-ninh` | 1.115458 | Tách thửa đất hoặc hợp thửa đất | 9 / 1 | Đang thêm (chưa commit) |
| 4 | `dang-ky-dat-dai-lan-dau-bac-ninh` | 1.115443 | Đăng ký đất đai, tài sản gắn liền với đất, cấp GCN lần đầu | 6 / 1 | Đang thêm (chưa commit) |
| 5 | `thu-hoi-gcn-cap-sai-bac-ninh` | 1.115447 | Thu hồi GCN đã cấp lần đầu không đúng quy định do người sử dụng đất phát hiện và cấp lại GCN | 5 / 1 | Đang thêm (chưa commit) |
| 6 | `dinh-chinh-sai-sot-bac-ninh` | 1.115446 | Đính chính GCN đã cấp lần đầu có sai sót | — | Đang thêm (chưa commit) |
| 7 | `giao-thue-chuyen-muc-dich-dat-bac-ninh` | 1.115438 (cấp xã) | Giao đất, cho thuê đất, chuyển mục đích sử dụng đất; giao/cho thuê đất và rừng; gia hạn sử dụng đất | — | Đang thêm (chưa commit) |
| 8 | `dang-ky-bien-dong-chuyen-nhuong-bac-ninh` | 1.013831 | Đăng ký biến động: chuyển nhượng, thừa kế, tặng cho, góp vốn QSDĐ; cho thuê, cho thuê lại QSDĐ | — | Đang thêm (chưa commit) |
| 9 | `dang-ky-bien-dong-dat-dai-bac-ninh` | 1.115468 | Đăng ký biến động (phạm vi rộng hơn 1.013831: thêm chuyển đổi đất nông nghiệp, mua bán nhà ở có thời hạn, tài sản trên đất thuê trả tiền hằng năm…) | — | Đang thêm (chưa commit) |
| 10 | `dang-ky-bien-dong-thoa-thuan-bac-ninh` | 1.115470 | Đăng ký biến động theo thỏa thuận hộ gia đình / vợ chồng, theo bản án, kết quả giải quyết tranh chấp, xử lý tài sản thế chấp… | — | Đang thêm (chưa commit) |

Ghi chú:
- #1 và #6 cùng nền 2 tab cùng trang → `textPriority` có thể cướp trang của nhau, nhận trang phải theo mã.
- #9 và #10 chạy chung process (`dang_ky_bien_dong_dat_dai_bac_ninh_process`), đính kèm riêng.
- #8 vẫn dùng mã cũ 1.013831, chưa đổi sang mã 1.1154xx như các thủ tục còn lại.

## Tình trạng trợ lý đến 21/10/2026

- **Đã lên trợ lý (12/12):** #1 đính chính GCN, #2 cấp đổi GCN, #3 tách hợp thửa, #4 đăng ký lần đầu, #5 thu hồi GCN cấp sai,
  #6 đính chính sai sót lần đầu, #7 giao / thuê / chuyển mục đích, #8 biến động chuyển nhượng 1.013831, #9 biến động 1.115468, #10 biến động thỏa thuận, #11 và #12 biện pháp bảo đảm. Mười thủ tục đất đai #1–#10 mới nằm trong working tree (chưa commit),
  container 12005 đã chạy bản này. Stack toàn trình 12015 mới có #11 và #12.

## Biện pháp bảo đảm bằng QSDĐ (Tư pháp, nộp tại VP đăng ký đất đai) — 2 thủ tục

| # | Key | Mã trên URL | Thủ tục | Trợ lý |
|---|---|---|---|---|
| 11 | `dang-ky-bien-phap-bao-dam-bac-ninh` | 1.011441 | Đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất | ✅ |
| 12 | `xoa-dang-ky-bien-phap-bao-dam-bac-ninh` | 1.011443 | Xóa đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất | ✅ |

Lượt / TK lấy từ checklist 21/10 (`process_requests` Mongo local, phần lớn dữ liệu test); dấu "—" là chưa đếm.
