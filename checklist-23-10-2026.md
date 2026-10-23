# Checklist T6 23/10/2026 — ưu tiên Bắc Ninh (72 → 77)

Danh sách đầy đủ thủ tục đã lên trợ lý: mục 7 của [ke-hoach-100-thu-tuc-tro-ly.md](ke-hoach-100-thu-tuc-tro-ly.md).
Mốc Đợt 2 là **79 vào T2 26/10**.

## Hiện trạng đầu giờ

- Trợ lý có **72** thủ tục. Commit `53ea8cd` (17:36 22/10) thêm `dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep`.
  Chiều qua còn thiếu 2 thủ tục: `cap-moi-giay-phep-hanh-nghe-chuyen-tiep` và `cap-giay-phep-chat-ha-cay-xanh`.
- Lõi có 222 thủ tục, trợ lý chưa mở 150. **Bắc Ninh chỉ còn 4 thủ tục** (không tính
  `dien-thong-tin-tai-khoan-bac-ninh` vì đó không phải thủ tục):

| # | Key | Mã QG | Lõi | Link DVCQG trong `ke_khai_links` |
|---|---|---|---|---|
| 1 | `ho-tro-nguoi-cao-tuoi-bac-ninh` | 1.014589 | `attach`, chỉ 1 thành phần (KQ001012) | **chưa có** |
| 2 | `ho-tro-chi-phi-hoa-tang-bac-ninh` | 1.014582 | `agent`: đơn + khối ủy quyền + đính kèm | có |
| 3 | `dang-ky-nha-o-xa-hoi-bac-ninh` | 1.014632 | `agent`: đơn Mẫu 02 + khối ủy quyền + đính kèm | có |
| 4 | `cap-hoc-tap-bac-ninh` | 1.014581 | `attach`: chỉ điền khối ủy quyền (HSSV) + đính kèm | **chưa có** |

- Engine `fill-bacninh.js` của trợ lý đã chạy cho 12 thủ tục đất đai Bắc Ninh: điền đơn theo `element_*`, đính kèm
  theo mã KQ, `samePageAttach`. Hàm `fillAuthorizedPersonBacNinh` (khối "người được ủy quyền") **có trong file
  nhưng chưa nơi nào gọi**. BE trợ lý cũng chưa bao giờ gọi pipeline với `purpose: "authorized_person"`.
  Kết quả: #2, #3 điền được đơn và đính kèm, còn khối ủy quyền phải để người dùng tự điền. #4 thì phần điền **chỉ
  có** khối ủy quyền, nên nếu chưa nối thì trợ lý chỉ đính kèm được.
- Docker Desktop đang **tắt**: `docker compose ps` lỗi pipe, Mongo 12004 và backend 12005 không có. Container `app`
  gần nhất build lúc 15:09 22/10, có thể **chưa có** `53ea8cd`.

## 08:30–09:00 · Dựng lại môi trường

- [ ] Mở Docker Desktop. Nếu engine trả 500 hoặc panel trắng: kill Docker Desktop, chạy `wsl --shutdown`, mở lại.
- [ ] `docker compose -f compose.prod.yml up -d --build --remove-orphans app` để đưa `53ea8cd` lên. Kiểm tra
      `ps` thấy `Up`, `curl.exe -s http://localhost:12005/healthz` trả `{"ok":true}`.
- [ ] Đếm registry trợ lý đủ 72. Sau mỗi lần dán BE phải đếm lại.

## 09:00–10:30 · Bắc Ninh, phần dễ (72 → 74)

Mỗi thủ tục cần: entry trong `procedure_registry.py` (đặt cạnh nhóm Bắc Ninh), gợi ý chọn thủ tục
(`procedure_picker/prompt.py`), tên tiếng Mông (`script_mong.py`). Không tạo file mới.
Khung chung chép từ `dang-ky-bien-phap-bao-dam-bac-ninh`: `provinceOnly: ["bacninh"]`, `detect` khoá host
`dichvucong.bacninh.gov.vn` + `maThuTucHanhChinh=<mã>`, `agencyProvince: "Bắc Ninh"`, `samePageAttach`.
Đặt tên theo quy ước Bắc Ninh: `label` = label lõi bỏ `[Tỉnh Bắc Ninh] `; `shortLabel` chỉ cắt gọn chữ gốc, không
thêm "(Bắc Ninh)".

**#1 `ho-tro-nguoi-cao-tuoi-bac-ninh`**: chỉ đính kèm, cổng tự điền nhân thân từ VNeID.

- [ ] Tìm uuid DVCQG của mã 1.014589, thêm vào `ke_khai_links.json` và đặt làm `keKhaiUrl`.
- [ ] Mở trang xem cơ quan tiếp nhận là UBND xã hay Sở, để chọn đúng cờ chọn cơ quan. Không chép
      `agencySoFirst` của nhóm đất đai mà chưa kiểm.
- [ ] `requiredDocs`: Tờ khai Mẫu 01 có xác nhận của UBND xã (bắt buộc); CCCD, kết quả tra cứu dân cư (tuỳ chọn).
- [ ] Gợi ý chọn thủ tục tách được với `tro-cap-xa-hoi-hang-thang` và `dieu-chinh-huu-tri-xa-hoi`: đây là chế
      độ riêng của Bắc Ninh cho người từ đủ 70 đến dưới 75 tuổi, hoặc đảng viên có huy hiệu 40 năm tuổi đảng.

**#2 `ho-tro-chi-phi-hoa-tang-bac-ninh`**: điền đơn rồi đính 2 thành phần bắt buộc.

- [ ] Nhánh `registration_form` của mapper phát `bn-input` theo `element_7575x`. Kiểm `fillFormBacNinh` của trợ lý
      nhận `comp: "bn-input"` giống bên đất đai.
- [ ] `uploadHint` ghi rõ khối "người được ủy quyền" người dùng tự điền (chưa nối `fillAuthorizedPersonBacNinh`).
- [ ] Gợi ý chọn thủ tục tách "hỏa táng / điện táng" với 2 thủ tục mai táng đã có
      (`ho-tro-mai-tang-1116910`, `ho-tro-mai-tang-huu-tri-xa-hoi`).
- [ ] Test lõi: `tests/unit/test_ho_tro_chi_phi_hoa_tang_bac_ninh.py`.

## 10:30–11:45 · Bắc Ninh: nhà ở xã hội (74 → 75)

**#3 `dang-ky-nha-o-xa-hoi-bac-ninh`**: khung giống hỏa táng (eForm 2836).

- [ ] `detect` khoá host, vì trợ lý đã có `cho-thue-thue-mua-nha-o-xa-hoi` trên `dvc.moc.gov.vn` với tên gần giống.
      Mở trang bên Bộ Xây dựng, kiểm nó không bị nhận thành thủ tục Bắc Ninh, và ngược lại.
- [ ] Gợi ý chọn thủ tục: người dùng Bắc Ninh nói "nhà ở xã hội" thì hỏi lại hoặc ưu tiên bản Bắc Ninh. Kiểm
      `provinceOnly` đủ để tài khoản tỉnh khác không thấy bản Bắc Ninh.
- [ ] `requiredDocs`: Mẫu 02 (thường 2 bản, vợ và chồng), CCCD, giấy chứng nhận kết hôn, ủy quyền hoặc giấy xác
      nhận nơi làm việc (tuỳ chọn).
- [ ] Không có file test riêng cho pipeline này: chỉ chạy test registry và toàn bộ.

## 13:30–14:30 · Bắc Ninh: hỗ trợ chi phí học tập (75 → 76), có điểm cần quyết

**#4 `cap-hoc-tap-bac-ninh`**: HSSV chưa có VNeID, nên cha mẹ nộp thay và khối ủy quyền là phần điền duy nhất.

- [ ] Tìm uuid DVCQG của mã 1.014581, thêm vào `ke_khai_links.json`.
- [ ] **Quyết trước 13:30**, chọn một trong hai:
  - (a) Chỉ đính kèm: `mode: "attach"`, `supportsSplitDocuments`, `uploadHint` dặn người dùng tự điền khối HSSV.
    Khoảng 30 phút.
  - (b) Nối khối ủy quyền: sửa extension để gọi `fillAuthorizedPersonBacNinh(fields, "<loại đối tượng HSSV>")` khi
    pipeline trả `doiTuongKhac*`. Bên extension Auto Fill đã có sẵn trong `BAC_NINH_AUTHORIZED_PERSON_CONFIG`
    (`popup.js`). Khoảng 1,5 giờ. Làm xong thì #2, #3 cũng dùng được.
  - Đề xuất: làm (a) hôm nay cho kịp mốc, để (b) vào việc tuần sau.
- [ ] Test lõi: `tests/unit/test_cap_hoc_tap_bac_ninh_mapper.py`. Nếu sửa extension: chạy
      `node tests/bacninh-same-page-contract.test.js`.

## 14:30–15:30 · Nợ hôm qua: Y tế (76 → 77)

**`cap-moi-giay-phep-hanh-nghe-chuyen-tiep`** (1.012289): chép entry `dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep`
vừa thêm hôm qua.

- [ ] `ke_khai_links` của thủ tục này **không có** `selectSo`. Mở link DVCQG `019d2bff-1db7-73d4-8e28-7b1fd65945b7`
      xem có phải chọn Sở Y tế không, rồi mới đặt `agencyProvinceOnly` / `agencySoFirst`.
- [ ] Thử chéo: mở trang "điều chỉnh" thì không được nhận thành "cấp mới", và ngược lại.
- [ ] Test lõi: `test_cap_moi_gphn_chuyen_tiep_attach.py`.

## 15:30–16:15 · Dự phòng (77 → 78)

Chỉ làm khi các phần trên đã xong. Nếu không kịp thì dời sang T2 26/10.

- `cap-giay-phep-chat-ha-cay-xanh`: kiểm chọn cơ quan cấp xã bằng tài khoản `hiephoabn`.

## 16:15–17:00 · Test + deploy một lần cho cả ngày

- [ ] Import registry không lỗi, đếm đúng số thủ tục (77 hoặc 78).
- [ ] Test các pipeline đã nêu ở trên, sau đó test toàn bộ `tests/unit` + `tests/integration` (plugin `win_socketpair`
      + `PYTHONUTF8=1`). Không vượt baseline `11 failed, 3 errors`.
- [ ] `docker compose -f compose.prod.yml up -d --build --remove-orphans app`. Container `Up`, healthz `{"ok":true}`.
- [ ] Thử trên trợ lý bằng tài khoản `hiephoabn`: card Bắc Ninh hiện ra, mở trang thì nhận đúng thủ tục. Chạy thử một
      hồ sơ mẫu tới **trước nút Nộp**, dữ liệu bịa.
- [ ] Cập nhật mục 7 của kế hoạch 100 thủ tục.

## Dồn sang T2 26/10 (cần +2 để chạm 79)

- `chap-thuan-dau-noi-tam`, `cap-gcnkncm-cccm`, `cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong`,
  `giai-quyet-che-do-khang-chien` (kiểm URL thật trên cổng Bộ Nội vụ trước khi viết `detect`).
- Bắc Ninh hết thủ tục trong lõi sau hôm nay. Muốn thêm thủ tục Bắc Ninh thì phải viết pipeline mới ở lõi trước.

## Kết quả cuối ngày

| Bộ | Thủ tục | Entry | Nhận trang | Chạy thử | Ghi chú |
|---|---|---|---|---|---|
| Bắc Ninh | ho-tro-nguoi-cao-tuoi-bac-ninh | ☐ | ☐ | ☐ | |
| Bắc Ninh | ho-tro-chi-phi-hoa-tang-bac-ninh | ☐ | ☐ | ☐ | |
| Bắc Ninh | dang-ky-nha-o-xa-hoi-bac-ninh | ☐ | ☐ | ☐ | |
| Bắc Ninh | cap-hoc-tap-bac-ninh | ☐ | ☐ | ☐ | |
| Y tế | cap-moi-giay-phep-hanh-nghe-chuyen-tiep | ☐ | ☐ | ☐ | |
| Xây dựng | cap-giay-phep-chat-ha-cay-xanh (dự phòng) | ☐ | ☐ | ☐ | |

**Tổng hôm nay: ___ / 5 → lũy kế ___ / 100**

> Dùng dữ liệu bịa khi chạy thử. Không nộp hồ sơ thật.
