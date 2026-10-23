# Checklist T6 23/10/2026 — ưu tiên Bắc Ninh (72 → 77)

Danh sách đầy đủ thủ tục đã lên trợ lý: mục 7 của [ke-hoach-100-thu-tuc-tro-ly.md](ke-hoach-100-thu-tuc-tro-ly.md).
Mốc Đợt 2 là **79 vào T2 26/10**.

## Hiện trạng lúc 11:00

- Trợ lý có **75** thủ tục (đầu giờ 72). Registry đếm 75, container `app` build 10:23 23/10 cũng đếm 75,
  `/healthz` ok. Phần sửa chưa commit, nằm trên `aedb955`.
- Đã thêm 3 thủ tục Bắc Ninh: `ho-tro-nguoi-cao-tuoi-bac-ninh`, `ho-tro-chi-phi-hoa-tang-bac-ninh`,
  `dang-ky-nha-o-xa-hoi-bac-ninh`.
- **Bỏ qua `cap-hoc-tap-bac-ninh` (1.014581).** Không làm hôm nay, cũng không dời sang T2.
- Còn 2 thủ tục để chạm 77: `cap-moi-giay-phep-hanh-nghe-chuyen-tiep` và `cap-giay-phep-chat-ha-cay-xanh`. Kế
  hoạch ở mục 11:00 và 13:30 bên dưới.
- Đã làm thêm 2 việc ngoài kế hoạch, cả hai đều có cờ extension, extension cũ thì giữ hành vi cũ:
  - **Nối khối "người được ủy quyền" Bắc Ninh** (phương án (b) của mục học tập cũ). BE chạy song song một lượt
    pipeline `purpose: "authorized_person"`, ghép thêm ô đánh dấu `comp: "bn-doi-tuong-khac"` (chọn "Cá nhân khác
    là Công dân Việt Nam") vào lệnh điền. Extension `fill-bacninh.js` điền đơn trước, sau đó tick ô bổ sung, chọn
    loại đối tượng rồi điền `doiTuongKhac*`. Lượt này chỉ chạy khi công dân chọn đối tượng `authorized_person` /
    `enterprise_authorized` và extension có cờ `supportsBacNinhAuthorizedPerson`. Áp cho **6** thủ tục: đăng ký
    và xóa biện pháp bảo đảm, `dang-ky-bien-dong-thoa-thuan-bac-ninh`, `dang-ky-bien-dong-dat-dai-bac-ninh`, hỏa táng,
    nhà ở xã hội. `dang-ky-bien-dong-chuyen-nhuong-bac-ninh` chưa có.
  - **Bước "Hình thức nhận kết quả" của cổng Bộ Y tế** (stepper iGate). Đính kèm xong thì trợ lý bấm "Tiếp tục" và
    chọn ô `receivingKind` theo thẻ (Nhận trực tuyến / trực tiếp / bưu điện). Sau đó trợ lý nhắc công dân **tự**
    tích ô cam đoan, nhập Mã xác nhận rồi bấm nộp. Cờ `supportsIgateResultStep`. Cấu hình tự gắn cho mọi entry có
    `urlScope` `dichvucongbyt.moh.gov.vn`: **11** thủ tục. Ở chế độ tiếng Mông luồng này tắt, vẫn giữ câu "tự bấm
    nộp".
- Extension trợ lý lên **1.13.3** (ngày 23/10). Test extension: 3/91 đỏ, bằng baseline.
- BE `ke_khai_links.json`: đổi key link 1.014589 thành `ho-tro-nguoi-cao-tuoi-bac-ninh`, thêm link
  `dang-ky-dat-dai-lan-dau-ninh-binh` (1.013978).

### BE mới `aedb955` (08:25 23/10)

- Chỉ **thêm**, không ghi đè phần sửa của `bb277b9` / `53ea8cd`.
- Nội dung mới:
  - `chat/lien_thong.py`: dẫn đủ 6 bước cổng liên thông cho `khai-sinh-dang-ky` (cờ `lienThongFlow`, chọn cách nhận
    kết quả từng giấy tờ, nói "nộp" có hỏi xác nhận).
  - `field_review` (vòng bổ sung ô) cho giám hộ, khai sinh đã có hồ sơ, khai sinh liên thông, nhận cha mẹ con, trợ
    giúp pháp lý. Thêm sửa mapper giám hộ và nhận cha mẹ con.
- Luồng liên thông chỉ bật khi extension gửi `supportsLienThongFlow`. Extension trợ lý 1.13.3 **vẫn chưa có cờ
  này**, nên khai sinh liên thông vẫn chạy luồng cũ cho tới khi có extension mới.

## 08:45–09:15 · Đưa BE mới lên Docker

- [x] Test các phần BE vừa đổi (chạy lại 11:00): `test_nhan_cha_me_con_mapper.py`, `test_dang_ky_giam_ho_compact_agent.py`,
      `test_cap_moi_gphn_chuyen_tiep_attach.py`, cùng 3 file `tests/handfree` (`test_flow_profiles.py`,
      `test_tu_phap_buoc_nhan_ket_qua.py`, `test_bien_phap_bao_dam_bac_ninh_flow.py`). Kết quả **122 passed**. Chạy
      riêng từng file thì `tests/handfree` collect được.
- [x] Test toàn bộ `tests/unit` + `tests/integration` (11:00): `11 failed, 2980 passed, 39 skipped, 3 errors`, bằng
      baseline. 3 errors vẫn là do thiếu `mongomock`.
- [x] `docker compose -f compose.prod.yml up -d --build --remove-orphans app`: container `Up` (build 10:23),
      healthz `{"ok":true}`.
- [ ] Nếu anh dán extension trợ lý mới: kiểm có `supportsLienThongFlow`, chạy lại test extension (baseline 3/91 đỏ),
      thử khai sinh liên thông đi hết 6 bước tới **trước nút Hoàn thành**.
- [x] Sau mỗi lần dán BE, đếm lại registry trợ lý. Lần đếm gần nhất ra 75.

## 09:15–10:30 · Bắc Ninh, phần dễ (72 → 74) — xong entry

Khung chung chép từ `dang-ky-bien-phap-bao-dam-bac-ninh`: `provinceOnly: ["bacninh"]`, `detect` khoá host
`dichvucong.bacninh.gov.vn` + `maThuTucHanhChinh=<mã>`, `agencyProvince: "Bắc Ninh"`, `samePageAttach`.
Cả 3 thủ tục đều có gợi ý chọn thủ tục (`procedure_picker/prompt.py`) và tên tiếng Mông (`script_mong.py`, BẢN NHÁP
chờ anh Dư soát).

**#1 `ho-tro-nguoi-cao-tuoi-bac-ninh`** (1.014589): chỉ đính kèm, cổng tự điền nhân thân từ VNeID.

- [x] uuid DVCQG `019d7c4f-0f4f-756f-a7db-e8f96edb8171`, đã đặt làm `keKhaiUrl`. Link vốn có trong `ke_khai_links.json`
      dưới key `ho-tro-nguoi-cao-tuoi-dang-vien-40-nam-tuoi-dang`, nay đổi thành `ho-tro-nguoi-cao-tuoi-bac-ninh`.
- [ ] Mở trang xem cơ quan tiếp nhận là UBND xã hay Sở. Link không có `selectSo` nên entry đang chọn cấp xã.
- [x] `requiredDocs`: Tờ khai Mẫu 01 có xác nhận của UBND xã (bắt buộc); CCCD, kết quả tra cứu dân cư (tuỳ chọn).
- [x] Gợi ý chọn thủ tục tách với `tro-cap-xa-hoi-hang-thang` và `dieu-chinh-huu-tri-xa-hoi`: chỉ nhận cụm có mốc
      70–75 tuổi, huy hiệu 40 năm tuổi đảng hoặc Bắc Ninh.

**#2 `ho-tro-chi-phi-hoa-tang-bac-ninh`** (1.014582): điền đơn, đính 2 thành phần bắt buộc, điền khối ủy quyền.

- [x] Mapper phát `bn-input` theo `element_757xx`, `fillFormBacNinh` của trợ lý nhận được.
- [x] Khối "người được ủy quyền": **đã nối** (`bacNinhAuthorizedPerson`). `uploadHint` dặn chọn đối tượng "Người
      khác ủy quyền" để trợ lý điền phần này.
- [x] Gợi ý chọn thủ tục tách "hỏa táng / điện táng" với `ho-tro-mai-tang-1116910`, `ho-tro-mai-tang-huu-tri-xa-hoi`.
- [x] Test lõi: `tests/unit/test_ho_tro_chi_phi_hoa_tang_bac_ninh.py`.

## 10:30–11:00 · Bắc Ninh: nhà ở xã hội (74 → 75) — xong entry

**#3 `dang-ky-nha-o-xa-hoi-bac-ninh`** (1.014632): khung giống hỏa táng (eForm 2836).

- [x] `detect` khoá host `dichvucong.bacninh.gov.vn` + `maThuTucHanhChinh=1.014632`. Bản Bộ Xây dựng
      `cho-thue-thue-mua-nha-o-xa-hoi` nằm ở `dvc.moc.gov.vn`.
- [ ] Mở trang thật để kiểm chéo hai bản.
- [x] Gợi ý chọn thủ tục: bản Bắc Ninh `provinceOnly: ["bacninh"]`, bản Bộ Xây dựng `provinceOnly: ["danang"]`. Không
      tài khoản nào thấy cả hai.
- [x] `requiredDocs`: Mẫu 02 (thường 2 bản, vợ và chồng), CCCD, giấy chứng nhận kết hôn, ủy quyền hoặc giấy xác nhận
      nơi làm việc (tuỳ chọn). Đính vào KQ005445.
- [x] Khối ủy quyền: **đã nối** như #2.
- [x] Không có file test lõi riêng. `tests/handfree/unit/test_flow_profiles.py` pass.

## ~~13:30–14:30 · Bắc Ninh: hỗ trợ chi phí học tập~~ — bỏ qua

`cap-hoc-tap-bac-ninh` (1.014581) bỏ qua theo quyết định 23/10. Ghi lại để lần sau khỏi tra lại:

- Link DVCQG của mã này **chưa có** trong `ke_khai_links.json`.
- Phần điền của thủ tục chỉ có khối ủy quyền (HSSV nộp qua cha mẹ). Khối này nay đã nối được
  (`bacNinhAuthorizedPerson`), nên nếu làm lại thì không cần chọn giữa (a) và (b) nữa.

## 11:00–12:00 · Y tế: cấp mới GPHN chuyển tiếp (75 → 76)

**`cap-moi-giay-phep-hanh-nghe-chuyen-tiep`** (1.012289). Lõi đã có pipeline process + attach, key trùng lõi nên tự nối.
Chép entry `dieu-chinh-giay-phep-hanh-nghe-chuyen-tiep` (`procedure_registry.py`, nhóm Y tế) và đặt ngay sau entry đó.

- [x] `detect`: `urlScope` `["dichvucongbyt.moh.gov.vn", "dichvucong.gov.vn"]`; `urlIncludes` `maThuTuc=1.012289`,
      `MaTTHC=1.012289`, `019d2bff-1db7-73d4-8e28-7b1fd65945b7`; `textIncludes` lấy y lõi ("cấp mới giấy phép hành
      nghề trong giai đoạn chuyển tiếp" + "kiểm tra đánh giá năng lực hành nghề"). `textIncludes` đòi đủ mọi cụm, nên
      cụm đầu đủ tách với bản "điều chỉnh".
- [ ] **Chọn cơ quan** (entry đã viết theo nhánh Sở Y tế như bản điều chỉnh, **chưa mở trang kiểm**; `selectSo`
      trong `ke_khai_links.json` chưa thêm): `ke_khai_links` của mã này **không có** `selectSo`, còn bản điều chỉnh thì có. Mở link DVCQG
      trước khi viết entry:
  - Hộp chọn cơ quan có Sở Y tế: đặt `agencyProvinceOnly` + `agencySoFirst` + `agencyDeptLabel: "Sở Y tế"`. Báo anh
    để thêm `selectSo: true` vào `ke_khai_links.json` cho khớp (file này Auto Fill cũng dùng).
  - Không có Sở: bỏ cả ba cờ, chọn đủ Tỉnh + Xã.
- [x] `requiredDocs` theo `uploadHint` lõi: Đơn Mẫu 08 PL I NĐ 96/2023, văn bằng chuyên môn, giấy khám sức khỏe, sơ
      yếu lý lịch Mẫu 09, giấy xác nhận thực hành Mẫu 07, 02 ảnh 4x6, CCCD người hành nghề (thêm CCCD người nộp nếu
      nộp thay). Bảng đính kèm có dòng cố định, nên để `hideRepeatableHint: False` như bản điều chỉnh.
- [x] Bước "Hình thức nhận kết quả" tự gắn vì `urlScope` có host Bộ Y tế. Đếm lại: entry có
      `guidedSteps.capability == "supportsIgateResultStep"` phải lên **12**.
- [x] Gợi ý chọn thủ tục: "xin cấp giấy phép hành nghề lần đầu", "bác sĩ / điều dưỡng mới ra trường xin giấy phép
      hành nghề", "cấp mới giấy phép hành nghề khám bệnh, chữa bệnh". Phải tách được với `dieu-chinh-…` (đã có GPHN,
      đổi phạm vi) và `dang-ky-hanh-nghe` (cơ sở đăng ký danh sách người hành nghề).
- [x] Tên tiếng Mông, ghép từ "Kho ntawv tso cai ua haujlwm kho mob" của bản điều chỉnh, ghi BẢN NHÁP chờ anh Dư soát.
- [x] Test: `tests/unit/test_cap_moi_gphn_chuyen_tiep_attach.py`, `tests/handfree/unit/test_flow_profiles.py`
      (cập nhật số đếm 76), `tests/handfree/unit/test_tu_phap_buoc_nhan_ket_qua.py`.
- [ ] Thử chéo trên trang: mở trang "điều chỉnh" thì không được nhận thành "cấp mới", và ngược lại.

## 13:30–14:45 · Xây dựng: chặt hạ, dịch chuyển cây xanh (76 → 77)

**`cap-giay-phep-chat-ha-cay-xanh`** (1.002693). Cổng Bộ Xây dựng `dvc.moc.gov.vn`, lõi có process + attach, key trùng.
Chép khung `cho-thue-thue-mua-nha-o-xa-hoi` (cùng cổng, `flowProfile: "xay-dung"`).

- [x] `detect`: `urlScope: ["dvc.moc.gov.vn"]`; `urlIncludes` `maThuTuc=1.002693`, `019d2bfe-230c-75d8-8979-11b8bdc68e6c`;
      `textIncludes: ["cấp giấy phép chặt hạ, dịch chuyển cây xanh"]` như lõi. `keKhaiUrl` = link DVCQG uuid trên.
- [x] **Chọn cơ quan:** làm theo đề xuất (chỉ Đà Nẵng, chọn Sở Xây dựng). `autoConfirm` chưa kiểm trên trang. `ke_khai_links` ghi `selectSoProvinces: ["danang"]` (chỉ Đà Nẵng chọn Sở, tỉnh
      khác chọn cấp xã) và `autoConfirm: false`. Registry trợ lý chưa có cờ chọn Sở theo từng tỉnh: `agencySoFirst`
      áp cho mọi tỉnh.
  - Đề xuất: `provinceOnly: ["danang"]` + `agencyProvinceOnly` + `agencySoFirst` + `agencyDeptLabel: "Sở Xây dựng"`.
    Cách này khớp phần lõi đã cấu hình và giống bản nhà ở xã hội của Bộ Xây dựng. Thử bằng `lienchieutest` hoặc
    `haichauhkd`.
  - Muốn mở cho tỉnh khác (cấp xã, thử bằng `hiephoabn`) thì phải thêm cờ chọn cơ quan theo tỉnh. Đó là việc riêng,
    không làm hôm nay.
  - `autoConfirm: false`: xem luồng chọn cơ quan của trợ lý dừng ở đâu, có phải công dân tự bấm "Đồng ý" không.
- [ ] Bảng kê cây: mapper phát `data[panel][tbantest][i][...]`. `fill-core.js` của trợ lý đã có nhánh datagrid
      (khoảng dòng 1307–1374, ví dụ trong comment chính là bảng này), nên không phải sửa extension. Chạy thử với đơn có
      **≥ 2 cây** để kiểm nút "Thêm dòng".
- [x] `requiredDocs`: Đơn Mẫu 01 có bảng kê cây xanh (bắt buộc), CCCD chủ hồ sơ, ảnh hiện trạng cây, GCN QSDĐ (nếu có),
      CCCD người nộp thay (nếu có). `uploadHint` chép từ lõi, bỏ chữ "extension".
- [x] Gợi ý chọn thủ tục: "xin phép chặt cây xanh", "chặt hạ cây trước nhà", "di dời / dịch chuyển cây xanh". Phải
      tách với cấp phép xây dựng và `cap-phep-long-duong-via-he`.
- [x] Tên tiếng Mông (BẢN NHÁP): "Ntawv tso cai txiav los yog tsiv ntoo".
- [x] Lõi không có file test riêng. Chạy `tests/handfree/unit/test_flow_profiles.py` (số đếm 77) và test toàn bộ.

## 14:45–15:45 · Nợ chạy thử (dữ liệu bịa, dừng trước nút Nộp)

- [ ] Bắc Ninh bằng `hiephoabn`: 3 card mới hiện, mở trang nhận đúng mã. Hỏa táng + nhà ở xã hội chọn đối tượng "Người
      khác ủy quyền": khối ủy quyền mở ra và điền đủ `doiTuongKhac*`. Mở trang xem cơ quan tiếp nhận của cả 3.
- [ ] Bộ Y tế: chạy một thủ tục có sẵn (vd `tro-cap-xa-hoi-hang-thang`) tới bước "Hình thức nhận kết quả". Trợ lý bấm
      "Tiếp tục", chọn đúng ô; chọn "bưu điện" thì hiện câu dặn tự tích ô nhận tại nhà. **Không** tích ô cam đoan,
      **không** nhập mã.

## 15:45–16:30 · Test + deploy một lần cho cả ngày

- [ ] Import registry không lỗi, đếm đúng **77**.
- [ ] Test pipeline đã nêu, sau đó test toàn bộ `tests/unit` + `tests/integration` (plugin `win_socketpair` +
      `PYTHONUTF8=1`). Không vượt baseline `11 failed, 3 errors`.
- [ ] `docker compose -f compose.prod.yml up -d --build --remove-orphans app`. Container `Up`, healthz `{"ok":true}`.
- [ ] Cập nhật mục 7 của kế hoạch 100 thủ tục (hiện ghi 75).

## Dồn sang T2 26/10 (cần +2 để chạm 79)

- Chọn 2 trong: `chap-thuan-dau-noi-tam`, `cap-gcnkncm-cccm`, `cap-bo-sung-cap-lai-giay-chung-nhan-nguoi-co-cong`,
  `giai-quyet-che-do-khang-chien` (kiểm URL thật trên cổng Bộ Nội vụ trước khi viết `detect`).
- Bắc Ninh hết thủ tục trong lõi (trừ `cap-hoc-tap-bac-ninh` đã bỏ). Muốn thêm thủ tục Bắc Ninh thì phải viết pipeline
  mới ở lõi trước.

## Kết quả cuối ngày

| Bộ | Thủ tục | Entry | Nhận trang | Chạy thử | Ghi chú |
|---|---|---|---|---|---|
| Bắc Ninh | ho-tro-nguoi-cao-tuoi-bac-ninh | ☑ | ☐ | ☐ | attach-only; cơ quan đang để cấp xã, chưa mở trang kiểm |
| Bắc Ninh | ho-tro-chi-phi-hoa-tang-bac-ninh | ☑ | ☐ | ☐ | agent: điền đơn + đính kèm + khối ủy quyền (đã nối); cơ quan cấp xã, chưa mở trang kiểm |
| Bắc Ninh | dang-ky-nha-o-xa-hoi-bac-ninh | ☑ | ☐ | ☐ | agent: điền đơn Mẫu 02 + đính kèm KQ005445 + khối ủy quyền (đã nối); cơ quan cấp xã, chưa mở trang kiểm |
| Bắc Ninh | ~~cap-hoc-tap-bac-ninh~~ | — | — | — | bỏ qua |
| Y tế | cap-moi-giay-phep-hanh-nghe-chuyen-tiep | ☑ | ☐ | ☐ | cơ quan theo nhánh Sở Y tế, chưa mở trang kiểm; ke_khai_links chưa có selectSo |
| Xây dựng | cap-giay-phep-chat-ha-cay-xanh | ☑ | ☐ | ☐ | chỉ Đà Nẵng, chọn Sở Xây dựng; bảng kê ≥ 2 cây chưa chạy thử |

**Tổng hôm nay: 5 / 5 → lũy kế 77 / 100** (đích cuối ngày 77)

> Dùng dữ liệu bịa khi chạy thử. Không nộp hồ sơ thật.
