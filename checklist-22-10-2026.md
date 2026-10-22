# Checklist T5 22/10/2026 — chiều: 3 thủ tục (71 → 74)

Danh sách đầy đủ thủ tục đã lên trợ lý: mục 7 của [ke-hoach-100-thu-tuc-tro-ly.md](ke-hoach-100-thu-tuc-tro-ly.md).

## Kết quả buổi sáng

Sáng nay đặt mục tiêu 69 → 78 (+9), thực tế chỉ thêm được **2** (69 → 71).

| Bộ | Thủ tục | Entry | Gợi ý + tiếng Mông | Ghi chú |
|---|---|---|---|---|
| Y tế | `cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te` | ☑ | ☑ | Mã 1.014104, `flowProfile: "xay-dung"` + `agencySoFirst` |
| Y tế | `dang-ky-hanh-nghe` | ☑ | ☑ | Mã 1.012275, cùng khung với dược |
| Y tế | `dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep` | ☐ | ☐ | → chiều nay |
| Y tế | `cap-moi-giay-phep-hanh-nghe-chuyen-tiep` | ☐ | ☐ | → chiều nay |
| Xây dựng | `cap-giay-phep-chat-ha-cay-xanh` | ☐ | ☐ | → chiều nay |
| Xây dựng | `chap-thuan-dau-noi-tam`, `cap-gcnkncm-cccm` | ☐ | ☐ | → T6 23/10 |
| Nội vụ | `cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong`, `giai-quyet-che-do-khang-chien` | ☐ | ☐ | → T6 23/10 |

- Commit `9534218` ("update BE mới", 11:47) dán đè BE và **xoá mất** 2 entry Y tế. Commit `bb277b9` (14:55) thêm lại.
  Sau mỗi lần dán BE, đếm lại registry trợ lý xem còn đủ 71 không.
- Container `app` 12005 build lúc 15:09, sau `bb277b9`, nên **đã có** cả 2 thủ tục. `/healthz` ok.
- Chưa chạy thử trên cổng 2 thủ tục này.
- Stack toàn trình 12015 vẫn chạy image `:dev-toan-trinh` từ 17/10.
- Đang có thay đổi chưa commit trong `ke_khai_links.json`: thêm 2 link Lào Cai (`dang-ky-dat-dai-lan-dau-ho-gia-dinh-lao-cai`,
  `dinh-chinh-gcn-da-cap-lao-cai`). Lần build tới sẽ đưa luôn thay đổi này lên.

## Chiều nay: 3 thủ tục

Mỗi thủ tục cần: entry trong `app/channels/handfree/procedure_registry.py`, gợi ý chọn thủ tục
(`procedure_picker/prompt.py`), tên tiếng Mông (`script_mong.py`). Không tạo file mới.

| # | Bộ | Key | Mã TTHC | Lượt / TK |
|---|---|---|---|---|
| 1 | Y tế | `dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep` | 1.012292 | 9 / 1 |
| 2 | Y tế | `cap-moi-giay-phep-hanh-nghe-chuyen-tiep` | 1.012289 | 7 / 2 |
| 3 | Xây dựng | `cap-giay-phep-chat-ha-cay-xanh` | 1.002693 | 6 / 2 |

### 16:00–16:50 · Y tế: giấy phép hành nghề chuyển tiếp (71 → 73)

Chép khung từ `dang-ky-hanh-nghe` vừa làm sáng nay (cổng `dichvucongbyt.moh.gov.vn`, `flowProfile: "xay-dung"`).

- [ ] `detect`: `urlScope` + `maThuTuc=` / `MaTTHC=` + uuid DVCQG trong `ke_khai_links.json`
      (`019d2bff-1db3-774c-81c5-200c7dcc25a1` cho #1, `019d2bff-1db7-73d4-8e28-7b1fd65945b7` cho #2).
- [ ] Hai thủ tục cùng cụm "kiểm tra đánh giá năng lực hành nghề". Bên Auto Fill, `textIncludes` đòi đủ **mọi** cụm
      (`popup.js:1469`), nên cụm đầu ("điều chỉnh…" / "cấp mới…") đã đủ phân biệt. Thử chéo trên trợ lý: mở trang #1
      thì không được nhận thành #2, và ngược lại.
- [ ] Chọn cơ quan: `ke_khai_links` của #1 có `selectSo`, còn #2 **không có**. Mở link DVCQG của #2 xem có phải chọn
      Sở Y tế không, rồi mới đặt `agencyProvinceOnly` / `agencySoFirst`.
- [ ] `requiredDocs` + `uploadHint` lấy từ entry lõi. Gợi ý chọn thủ tục phải tách được "cấp mới" với "điều chỉnh",
      và cả hai phải khác `cap-lai-giay-phep-hanh-nghe-truoc-2024`.
- [ ] Tên tiếng Mông (ghi BẢN NHÁP chờ anh Dư soát).
- [ ] Test lõi: `test_cap_moi_gphn_chuyen_tiep_attach.py`, `test_dang_ky_hanh_nghe.py`.

### 16:50–17:20 · Xây dựng: chặt hạ, dịch chuyển cây xanh (73 → 74)

Chép khung từ `cap-phep-long-duong-via-he` (`flowProfile: "xay-dung"`, key trùng lõi nên `detect` lấy từ lõi:
`urlScope dvc.moc.gov.vn` + cụm "cấp giấy phép chặt hạ, dịch chuyển cây xanh").

- [ ] `ke_khai_links` chỉ đặt `selectSoProvinces: ["danang"]` và `autoConfirm: false`. Kiểm chọn cơ quan ở một tỉnh
      khác (vd Bắc Ninh, tài khoản `hiephoabn`) có ra đúng cấp xã không.
- [ ] Entry + gợi ý chọn thủ tục + tên tiếng Mông. Card hiện, nhận đúng trang.

### 17:20–17:45 · Test + deploy một lần cho cả 3

- [ ] Import registry không lỗi, đủ **74** thủ tục.
- [ ] Test toàn bộ `tests/unit` + `tests/integration` (plugin `win_socketpair` + `PYTHONUTF8=1`):
      không vượt baseline `11 failed, 3 errors`.
- [ ] `docker compose -f compose.prod.yml up -d --build --remove-orphans app`.
- [ ] Container `Up`, `curl.exe -s http://localhost:12005/healthz` trả `{"ok":true}`.
- [ ] Stack toàn trình (12015) lên bản mới nếu trợ lý đang trỏ vào đó.

## Dồn sang T6 23/10

- 4 thủ tục còn lại của sáng nay: `chap-thuan-dau-noi-tam`, `cap-gcnkncm-cccm`,
  `cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong`, `giai-quyet-che-do-khang-chien` (kiểm URL thật trên cổng
  Bộ Nội vụ trước khi viết `detect`).
- Mốc Đợt 2 là **79 vào T2 26/10**. Chiều nay xong thì còn 74, cần thêm 5: 4 thủ tục trên + 1 trong dự phòng
  (`gia-han-luu-hanh-phuong-tien-lao`, `ho-tro-chi-phi-hoa-tang-bac-ninh`, `ho-tro-nguoi-cao-tuoi-bac-ninh`,
  `bo-sung-than-nhan-liet-si`).
- Nợ chạy thử trên cổng (dừng trước nút Nộp, dữ liệu bịa): 2 thủ tục Y tế sáng nay, 3 thủ tục chiều nay,
  10 thủ tục đất đai Bắc Ninh (21/10), `ho-tro-mai-tang-1116910`, 10 thủ tục có entry từ 19/10.
- Mở đường cổng Đà Nẵng bằng `cap-doi-gcn-da-nang` trước Đợt 3 (27/10).

## Kết quả cuối buổi chiều

| Bộ | Thủ tục | Entry | Nhận trang | Chạy thử | Ghi chú |
|---|---|---|---|---|---|
| Y tế | dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep | ☐ | ☐ | ☐ | |
| Y tế | cap-moi-giay-phep-hanh-nghe-chuyen-tiep | ☐ | ☐ | ☐ | |
| Xây dựng | cap-giay-phep-chat-ha-cay-xanh | ☐ | ☐ | ☐ | |

**Tổng chiều nay: ___ / 3 → lũy kế ___ / 100**

> Dùng dữ liệu bịa khi chạy thử. Không nộp hồ sơ thật.
