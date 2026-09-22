"""[Lào Cai] Tặng cho quyền sử dụng đất mở rộng đường giao thông — mã 1.115690 (hiến đất làm đường).

Khoá năm điều dễ vỡ, đều lấy từ `Mapping_tang_cho_quyen_su_dung_dat.xlsx` và bộ hồ sơ mẫu Lương Thị
Linh / Nguyễn Tiến Quân:
  1. Nhận diện phải bám cụm "thửa đất CHƯA được cấp Giấy chứng nhận" — cổng có thủ tục song sinh.
  2. Hai ô readonly `CongDan_tenCongDan` / `CongDan_soCmnd` KHÔNG BAO GIỜ được phát.
  3. Hai mode người nộp: nộp thay theo ủy quyền thì TUYỆT ĐỐI không chép nhân thân chéo hai khối.
  4. Giấy tờ chỉ ghi NĂM SINH và không ghi dân tộc → bỏ trống, không bịa 01/01, không mặc định Kinh;
     giới tính chỉ suy từ chữ số thứ 4 của CCCD 12 số, không suy từ họ tên hay "ông/bà".
  5. Đính kèm: KHÔNG có bảng "Thành phần hồ sơ" → mọi tệp xuống "Giấy tờ khác" (target=new), mỗi tệp
     một dòng, tên mô tả đúng nguyên văn ảnh ánh xạ, không bỏ sót tệp nào.
"""

from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn.attach import planner
from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn.process import mapper
from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn.process.schema import (
    INDIVIDUAL_ONLY_FIELDS,
    ORG_ONLY_FIELDS,
    UI_COMP_BY_NAME,
)
from app.procedures.registry import public_list

_KEY = "tang-cho-qsdd-nha-nuoc-chua-cap-gcn"

# Hồ sơ mẫu: bà Lương Thị Linh tặng cho đất làm đường, ông Nguyễn Tiến Quân nộp thay theo Giấy uỷ quyền.
_HS_UY_QUYEN = [
    {"name": "ChuHoSo_HoTen", "value": "Lương Thị Linh"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "010164003196"},
    {"name": "ChuHoSo_NgayCap", "value": "27/03/2024"},
    {"name": "ChuHoSo_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "ChuHoSo_DienThoai", "value": "0383513017"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Phường Cam Đường", "diaChi": "Tổ 42"}},
    {"name": "NguoiNop_HoTen", "value": "Nguyễn Tiến Quân"},
    {"name": "NguoiNop_SoDinhDanh", "value": "010066000177"},
    {"name": "NguoiNop_NgayCap", "value": "07/04/2021"},
    {"name": "NguoiNop_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "NguoiNop_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Phường Bình Minh", "diaChi": "Tổ 17"}},
    {"name": "DongSuDung_HoTen", "value": "Nông Văn Tường"},
    {"name": "DongSuDung_SoDinhDanh", "value": "010052002571"},
]

# Biến thể tự nộp: chính bà Linh đi nộp, hồ sơ chỉ khai một lần ở khối chủ hồ sơ.
_HS_TU_NOP = [
    {"name": "ChuHoSo_HoTen", "value": "Lương Thị Linh"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "010164003196"},
    {"name": "ChuHoSo_NgayCap", "value": "27/03/2024"},
    {"name": "ChuHoSo_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "ChuHoSo_DienThoai", "value": "0383513017"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Phường Cam Đường", "diaChi": "Tổ 42"}},
]


def _entry(key=_KEY):
    return next(p for p in public_list() if p["key"] == key)


def _names(fields):
    return {f["name"]: f["value"] for f in fields}


def _ctx(fullname: str, identity: str) -> dict:
    return {"formContext": {"applicantFullname": fullname, "applicantIdentityNumber": identity}}


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


# --------------------------------------------------------------------------- registry & nhận diện
def test_co_trong_registry_va_khoa_dung_cong_lao_cai():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["detect"]["urlScope"] == ["dichvucong.laocai.gov.vn"]
    # Cổng SPA, sid đổi mỗi phiên → không được khóa bằng urlIncludes.
    assert "urlIncludes" not in entry["detect"]


def test_co_pipeline_process_va_attach():
    from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE

    assert _KEY in _PIPELINE
    assert _KEY in _ATTACH_PIPELINE


def _detect(url: str, body: str) -> str:
    """Bản rút gọn nhánh textPriority + textIncludes của popup.js detectProcedureKeyFromSignals."""
    import re
    import unicodedata

    def norm(value):
        text = unicodedata.normalize("NFD", str(value or ""))
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()

    url, body = url.lower(), norm(body)
    items = [p for p in public_list() if p.get("detect") and not p.get("detectDisabled")]

    def scope_ok(detect):
        scope = detect.get("urlScope")
        return True if not scope else any(u and u.lower() in url for u in scope)

    for only_priority in (True, False):
        best, best_score = "", 0
        for p in items:
            detect = p["detect"]
            if only_priority and not detect.get("textPriority"):
                continue
            if not scope_ok(detect):
                continue
            phrases = [norm(x) for x in (detect.get("textIncludes") or []) if x]
            if not phrases or not all(x in body for x in phrases):
                continue
            score = sum(len(x) for x in phrases)
            if score > best_score:
                best, best_score = p["key"], score
        if best:
            return best
    return ""


_URL_LAO_CAI = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"
_TIEU_DE = (
    "1.115690 - Tặng cho quyền sử dụng đất cho Nhà nước hoặc cộng đồng dân cư hoặc mở rộng đường "
    "giao thông đối với trường hợp thửa đất chưa được cấp Giấy chứng nhận"
)


def test_trang_1_115690_nhan_dung_thu_tuc_nay():
    assert _detect(_URL_LAO_CAI, _TIEU_DE) == _KEY


def test_ban_song_sinh_da_duoc_cap_gcn_khong_bi_cuop_trang():
    """Thủ tục song sinh chỉ khác chữ "đã"/"chưa" — entry này tuyệt đối không được khớp trang đó."""
    body = _TIEU_DE.replace("chưa được cấp", "đã được cấp")
    assert _detect(_URL_LAO_CAI, body) != _KEY


def test_cum_nhan_dien_giu_nguyen_chu_chua_duoc_cap():
    phrases = _entry()["detect"]["textIncludes"]
    assert any("chưa được cấp Giấy chứng nhận" in p for p in phrases)


# ------------------------------------------------ hai ô readonly: không bao giờ được phát
def test_khong_bao_gio_phat_hai_o_readonly_cua_tai_khoan():
    """Ghi vào 2 ô này là script cổng xoá trắng "Di động" + "Số Căn cước" vừa điền xong."""
    assert "CongDan_tenCongDan" not in UI_COMP_BY_NAME
    assert "CongDan_soCmnd" not in UI_COMP_BY_NAME

    for ho_so, options in ((_HS_UY_QUYEN, _ctx("Nguyễn Tiến Quân", "010066000177")), (_HS_TU_NOP, {})):
        fields, _ = mapper.enrich(list(ho_so), options)
        names = _names(fields)
        assert "CongDan_tenCongDan" not in names
        assert "CongDan_soCmnd" not in names


# ----------------------------------------------------------------- hai mode người nộp
def test_uy_quyen_giu_nguyen_hai_nguoi_khac_nhau():
    fields, _ = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Tiến Quân", "010066000177"))
    names = _names(fields)
    # Khối chủ hồ sơ là người tặng cho, không bị nhân thân người nộp đè lên.
    assert names["ChuHoSo_tenChuHoSo"] == "Lương Thị Linh"
    assert names["ChuHoSo_soCMNDChuHoSo"] == "010164003196"
    assert names["ChuHoSo_ngayCapCMNDCHS"] == "27/03/2024"
    # Hai khối hai địa chỉ khác nhau — không được chép chéo.
    assert names["ChuHoSo_maPhuongXaCHS"] != names["CongDan_maPhuongXa"]
    assert names["CongDan_ngayCapCmnd"] == "07/04/2021"


def test_uy_quyen_khong_muon_so_dien_thoai_cua_chu_ho_so():
    """Giấy uỷ quyền không ghi số của người được uỷ quyền → ô Di động khối người nộp phải TRỐNG."""
    fields, errors = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Tiến Quân", "010066000177"))
    names = _names(fields)
    assert "CongDan_diDong" not in names
    assert names["ChuHoSo_diDongLienLacCHS"] == "0383513017"
    assert any("Di động" in e for e in errors)


def test_uy_quyen_canh_bao_o_readonly_va_cam_tick_checkbox():
    _, errors = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Tiến Quân", "010066000177"))
    assert any("nộp thay" in e.lower() for e in errors)
    assert any("Người nộp là chủ hồ sơ" in e for e in errors)


def test_moc_tai_khoan_chot_mode_tu_nop_du_ho_so_co_uy_quyen():
    """Chính chủ hồ sơ đăng nhập thì đó là mode tự nộp, bất kể giấy tờ có người được uỷ quyền.

    Giấy uỷ quyền trong hồ sơ KHÔNG được dùng cho lần nộp này, nên nhân thân của người được uỷ quyền
    phải bị bỏ hẳn — điền địa chỉ/ngày cấp của ông Quân cho bà Linh là sai người.
    """
    fields, errors = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Lương Thị Linh", "010164003196"))
    names = _names(fields)
    assert names["CongDan_diDong"] == "0383513017"
    assert names["CongDan_maPhuongXa"] == "Phường Cam Đường"
    assert names["CongDan_diaChi"] == "Tổ 42"
    assert names["CongDan_ngayCapCmnd"] == "27/03/2024"       # của bà Linh, không phải 07/04/2021
    assert names["CongDan_gioiTinhCongDan"] == "Nữ"           # suy từ CCCD bà Linh
    assert any("KHÔNG dùng uỷ quyền" in e for e in errors)


# ----------------------------------- khối người nộp: chỉ điền khi có giấy tờ của người đăng nhập
_O_NGUOI_NOP = (
    "CongDan_ngaySinhCongDan",
    "CongDan_gioiTinhCongDan",
    "CongDan_danTocCongDan",
    "CongDan_ngayCapCmnd",
    "CongDan_noiCapCmnd",
    "CongDan_maTinhThanh",
    "CongDan_maPhuongXa",
    "CongDan_diaChi",
    "CongDan_diDong",
    "CongDan_email",
    "CongDan_fax",
)


def test_tai_khoan_la_nguoi_la_thi_bo_trong_ca_khoi_nguoi_nop():
    """Người đăng nhập không có giấy tờ nào trong hồ sơ → TUYỆT ĐỐI không mượn nhân thân người khác.

    Đây là lỗi thật đã gặp trên cổng: hai ô readonly hiện đúng tên tài khoản, còn ngày sinh/giới
    tính/địa chỉ lại là của người trong CCCD đã tải lên — hồ sơ sai lệch nhân thân mà nhìn màn hình
    rất khó thấy.
    """
    fields, errors = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nhâm Đắc Đạt", "001088000999"))
    names = _names(fields)
    for name in _O_NGUOI_NOP:
        assert name not in names, name
    assert any("KHÔNG có giấy tờ tuỳ thân của người đang đăng nhập" in e for e in errors)
    # Khối chủ hồ sơ là của HỒ SƠ, không phải của phiên đăng nhập → vẫn phải điền đủ.
    assert names["ChuHoSo_tenChuHoSo"] == "Lương Thị Linh"
    assert names["ChuHoSo_maPhuongXaCHS"] == "Phường Cam Đường"


def test_khong_doc_duoc_tai_khoan_thi_cung_bo_trong_khoi_nguoi_nop():
    fields, errors = mapper.enrich(list(_HS_UY_QUYEN), {})
    names = _names(fields)
    for name in _O_NGUOI_NOP:
        assert name not in names, name
    assert any("KHÔNG xác minh được" in e for e in errors)
    assert names["ChuHoSo_tenChuHoSo"] == "Lương Thị Linh"


def test_canh_bao_chan_khoi_nguoi_nop_chi_ro_cach_go():
    _, errors = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nhâm Đắc Đạt", "001088000999"))
    chan = next(e for e in errors if "KHÔNG có giấy tờ tuỳ thân" in e)
    assert "001088000999" in chan          # nói rõ đang thiếu giấy tờ của số căn cước nào
    assert "tải thêm CCCD" in chan         # cách gỡ 1
    assert "đăng nhập bằng tài khoản" in chan  # cách gỡ 2


def test_tu_nop_bo_khuyet_khoi_nguoi_nop_tu_chu_ho_so():
    """Chủ hồ sơ tự đăng nhập và hồ sơ có CCCD của chính họ → được phép điền khối người nộp."""
    fields, _ = mapper.enrich(list(_HS_TU_NOP), _ctx("Lương Thị Linh", "010164003196"))
    names = _names(fields)
    assert names["CongDan_ngayCapCmnd"] == "27/03/2024"
    assert names["CongDan_diDong"] == "0383513017"
    assert names["CongDan_maTinhThanh"] == "Tỉnh Lào Cai"
    assert names["CongDan_diaChi"] == "Tổ 42"


def test_uy_quyen_dung_tai_khoan_thi_van_dien_khoi_nguoi_nop():
    fields, _ = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Tiến Quân", "010066000177"))
    names = _names(fields)
    assert names["CongDan_ngayCapCmnd"] == "07/04/2021"
    assert names["CongDan_maPhuongXa"] == "Phường Bình Minh"


def test_tu_nop_van_phat_du_ba_o_dia_chi_khoi_chu_ho_so():
    """Checkbox "Người nộp là chủ hồ sơ" của cổng KHÔNG copy địa chỉ → mapper phải tự phát."""
    fields, _ = mapper.enrich(list(_HS_TU_NOP), _ctx("Lương Thị Linh", "010164003196"))
    names = _names(fields)
    assert names["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    assert names["ChuHoSo_maPhuongXaCHS"] == "Phường Cam Đường"
    assert names["ChuHoSo_diaChiChuHoSo"] == "Tổ 42"


def test_khong_phat_checkbox_nguoi_nop_la_chu_ho_so():
    assert "chkbox_nguoinoplachuhs" not in UI_COMP_BY_NAME


def test_khong_phat_truong_an_cua_cong():
    for name in ("code-dkdn", "local_file", "local_file_xuly", "AN_FORM_CHS", "tokenCsrf",
                 "CongDan_maDMDiaChi"):
        assert name not in UI_COMP_BY_NAME


# ------------------------------------------------------------- cá nhân / tổ chức
def test_ho_so_ca_nhan_khong_phat_o_bi_an_cua_khoi_to_chuc():
    fields, _ = mapper.enrich(list(_HS_TU_NOP), {})
    names = _names(fields)
    assert names["ChuHoSo_maDoiTuongNopHS"] == "Cá nhân"
    for name in ORG_ONLY_FIELDS:
        assert name not in names


def test_ho_so_to_chuc_khong_phat_o_nhan_than_ca_nhan_dang_bi_an():
    ho_so = list(_HS_TU_NOP) + [
        {"name": "ChuHoSo_LaToChuc", "value": True},
        {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY TNHH MTV ABC"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300123456-001"},
    ]
    fields, _ = mapper.enrich(ho_so, {})
    names = _names(fields)
    assert names["ChuHoSo_maDoiTuongNopHS"] == "Tổ chức"
    assert names["ChuHoSo_tenCoQuanToChucCHS"] == "CÔNG TY TNHH MTV ABC"
    assert names["ChuHoSo_maSoThueChuHoSo"] == "5300123456-001"
    for name in INDIVIDUAL_ONLY_FIELDS:
        assert name not in names


def test_ubnd_o_dong_kinh_gui_khong_bien_ho_so_thanh_to_chuc():
    """"Kính gửi: UBND phường…" là nơi nhận — chỉ nằm ở field trace, không được kéo sang tổ chức."""
    ho_so = list(_HS_TU_NOP) + [
        {"name": "TangCho_NoiNhan", "value": "ỦY BAN NHÂN DÂN PHƯỜNG CAM ĐƯỜNG"},
    ]
    fields, _ = mapper.enrich(ho_so, {})
    names = _names(fields)
    assert names["ChuHoSo_maDoiTuongNopHS"] == "Cá nhân"
    assert "ChuHoSo_tenCoQuanToChucCHS" not in names


# ------------------------------------------------------- ngày sinh / dân tộc / giới tính
def test_khong_bia_ngay_thang_khi_chi_co_nam():
    ho_so = list(_HS_TU_NOP) + [{"name": "ChuHoSo_NgaySinh", "value": "1964"}]
    fields, errors = mapper.enrich(ho_so, {})
    assert "ChuHoSo_ngaySinhChuHoSo" not in _names(fields)
    assert any("NĂM SINH" in e for e in errors)


def test_khong_mac_dinh_dan_toc_kinh():
    fields, _ = mapper.enrich(list(_HS_TU_NOP), {})
    names = _names(fields)
    assert "ChuHoSo_danTocChuHoSo" not in names
    assert "CongDan_danTocCongDan" not in names


def test_gioi_tinh_suy_tu_chu_so_thu_4_cua_cccd():
    """File mapping cấm suy từ họ tên và từ "ông/bà" → CCCD 12 số là căn cứ duy nhất."""
    fields, _ = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Tiến Quân", "010066000177"))
    names = _names(fields)
    assert names["ChuHoSo_gioiTinhChuHoSo"] == "Nữ"   # 010164003196 → chữ số thứ 4 = 1
    assert names["CongDan_gioiTinhCongDan"] == "Nam"  # 010066000177 → chữ số thứ 4 = 0


def test_khong_co_cccd_12_so_thi_bo_trong_gioi_tinh():
    ho_so = [
        {"name": "ChuHoSo_HoTen", "value": "Lương Thị Linh"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "063078311"},  # CMND cũ 9 số
    ]
    fields, _ = mapper.enrich(ho_so, {})
    assert "ChuHoSo_gioiTinhChuHoSo" not in _names(fields)


def test_canh_bao_nguoi_dong_su_dung_vi_buoc_2_khong_co_o():
    _, errors = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Tiến Quân", "010066000177"))
    assert any("Nông Văn Tường" in e for e in errors)


def test_khong_doc_duoc_dia_chi_thi_canh_bao_thay_vi_im_lang():
    ho_so = [{"name": "ChuHoSo_HoTen", "value": "Lương Thị Linh"}]
    _, errors = mapper.enrich(ho_so, {})
    assert any("địa chỉ chủ hồ sơ" in e for e in errors)


# --------------------------------------------------------------------------- đính kèm
def test_moi_tep_mot_dong_giay_to_khac_khong_dung_fixed_slot():
    """Thủ tục này KHÔNG có bảng "Thành phần hồ sơ" → không được phát target fixed-slot."""
    files = _files(["vbhiendat.pdf", "GIAY_UQ.pdf", "GCNQSD_DAT.pdf"])
    llm = {0: "van_ban_tang_cho", 1: "giay_uy_quyen", 2: "gcn_qsdd"}
    attachments, _, _ = planner.build_plan_items(files, llm)
    assert len(attachments) == 3
    for item in attachments:
        assert item["target"] == "new"
        assert item["needsAddComponent"] is True
        # Cổng iGate VNPT: bấm "Chọn tệp tin" mở hộp thoại file của OS → phải gán thẳng.
        assert item["noChooserClick"] is True
        assert "slotIndex" not in item


def test_ten_mo_ta_dung_nguyen_van_anh_anh_xa():
    files = _files(["a.pdf", "b.pdf", "c.pdf"])
    llm = {0: "van_ban_tang_cho", 1: "giay_uy_quyen", 2: "gcn_qsdd"}
    attachments, _, _ = planner.build_plan_items(files, llm)
    assert [a["documentName"] for a in attachments] == [
        "Văn bản tặng cho quyền sử dụng đất",
        "Giấy ủy quyền",
        "Giấy chứng nhận quyền sử dụng đất",
    ]
    # FE gõ componentName vào ô tên của dòng "Giấy tờ khác" → phải trùng tên giấy tờ.
    assert all(a["componentName"] == a["documentName"] for a in attachments)


def test_hai_tep_cung_loai_van_co_ten_dong_khac_nhau():
    files = _files(["gcn1.pdf", "gcn2.pdf"])
    attachments, _, _ = planner.build_plan_items(files, {0: "gcn_qsdd", 1: "gcn_qsdd"})
    names = [a["documentName"] for a in attachments]
    assert names[0] != names[1]
    assert names[0] == "Giấy chứng nhận quyền sử dụng đất"


def test_khong_bo_sot_file_nao_khi_llm_chet():
    files = _files(["a.pdf", "b.pdf", "c.pdf"])
    attachments, warnings, _ = planner.build_plan_items(files, {})
    assert len(attachments) == 3
    assert all(a["target"] == "new" for a in attachments)
    assert any("Chưa nhận ra loại giấy tờ" in w for w in warnings)


def test_canh_bao_khi_thieu_giay_to_chinh():
    files = _files(["vbhiendat.pdf"])
    _, warnings, _ = planner.build_plan_items(files, {0: "van_ban_tang_cho"})
    assert any("Giấy ủy quyền có công chứng" in w for w in warnings)
    assert any("Giấy chứng nhận quyền sử dụng đất" in w for w in warnings)


def test_du_ba_giay_to_chinh_thi_khong_canh_bao_thieu():
    files = _files(["a.pdf", "b.pdf", "c.pdf"])
    llm = {0: "van_ban_tang_cho", 1: "giay_uy_quyen", 2: "gcn_qsdd"}
    _, warnings, _ = planner.build_plan_items(files, llm)
    assert not any("Chưa thấy trong bộ tệp" in w for w in warnings)


def test_cccd_van_duoc_dinh_kem_chu_khong_bi_bo():
    """Ảnh ánh xạ ghi rõ "Không được bỏ sót file đính kèm chung" → không loại tệp nào."""
    files = _files(["a.pdf", "cccd.pdf"])
    attachments, warnings, _ = planner.build_plan_items(files, {0: "van_ban_tang_cho", 1: "giay_to_tuy_than"})
    assert len(attachments) == 2
    assert attachments[1]["documentName"] == "Giấy tờ tùy thân"
    assert any("giấy tờ tùy thân" in w for w in warnings)


def test_luon_nhac_khong_tach_sang_thanh_phan_ho_so():
    files = _files(["a.pdf"])
    _, warnings, _ = planner.build_plan_items(files, {0: "van_ban_tang_cho"})
    assert any("Giấy tờ khác" in w and "Thành phần hồ sơ" in w for w in warnings)


def test_khong_co_tep_thi_khong_canh_bao_thua():
    attachments, warnings, _ = planner.build_plan_items([], {})
    assert attachments == []
    assert not any("Giấy tờ khác" in w and "Thành phần hồ sơ" in w for w in warnings)


def test_tep_vuot_6mb_bi_loai_va_bao_ro():
    import base64

    big = "data:application/pdf;base64," + base64.b64encode(b"x" * (7 * 1024 * 1024)).decode()
    assert planner._data_url_size(big) > planner._MAX_FILE_BYTES


# --------------------------------------------------------------------------- prompt
def test_prompt_attach_co_bay_phan_biet_uy_quyen_voi_gcn():
    from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn.attach.prompt import SYSTEM_PROMPT

    assert "giay_uy_quyen" in SYSTEM_PROMPT
    assert "Căn cứ uỷ quyền" in SYSTEM_PROMPT
    # Không được phân loại theo tên file.
    assert "ĐỪNG DÙNG TÊN FILE" in SYSTEM_PROMPT


def test_prompt_process_cam_suy_gioi_tinh_tu_ten_va_ong_ba():
    from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn.process.prompt import EXTRA_RULES

    assert "không suy từ họ tên" in EXTRA_RULES.lower() or "KHÔNG suy từ họ tên" in EXTRA_RULES
    assert "ông/bà" in EXTRA_RULES
    assert "không bịa 01/01" in EXTRA_RULES.lower() or "TUYỆT ĐỐI không bịa 01/01" in EXTRA_RULES


def test_prompt_process_canh_bao_kinh_gui_ubnd_khong_phai_to_chuc():
    from app.pipelines.tang_cho_qsdd_nha_nuoc_chua_cap_gcn.process.prompt import EXTRA_RULES

    assert "KÍNH GỬI" in EXTRA_RULES.upper()
    assert "NƠI NHẬN" in EXTRA_RULES.upper()
