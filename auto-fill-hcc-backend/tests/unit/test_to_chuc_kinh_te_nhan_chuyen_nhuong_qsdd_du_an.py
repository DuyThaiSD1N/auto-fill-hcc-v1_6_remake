"""[Lào Cai] Tổ chức kinh tế nhận chuyển nhượng QSDĐ thực hiện dự án — mã 1.115681.

Khoá sáu điều dễ vỡ, đều lấy từ `Mapping_1.115681_Minh_Phuong.xlsx`, ảnh ánh xạ đính kèm và bộ hồ sơ
mẫu Công ty TNHH Dịch vụ Minh Phượng:
  1. Nhận diện phải bám cụm căn cứ pháp lý "điểm a, b khoản 1 Điều 127 Luật Đất đai".
  2. Chủ hồ sơ là PHÁP NHÂN → "Đối tượng nộp hồ sơ" = DN, 7 ô nhân thân cá nhân bị ẩn, không phát.
  3. Ô "Tên cơ quan/tổ chức" của khối NGƯỜI NỘP là ĐƠN VỊ ĐƯỢC ỦY QUYỀN, không phải chủ hồ sơ.
  4. Hai ô readonly `CongDan_tenCongDan` / `CongDan_soCmnd` KHÔNG BAO GIỜ được phát; khối người nộp
     chỉ được điền khi hồ sơ có giấy tờ của chính tài khoản đang đăng nhập.
  5. Số điện thoại trên Giấy chứng nhận ĐKDN là của CHỦ HỒ SƠ — nộp thay theo ủy quyền không mượn.
  6. Đính kèm: mọi tệp xuống "Giấy tờ khác" (target=new); hai dòng đầu giữ nguyên văn tên thành phần
     theo ảnh hướng dẫn, phần còn lại là đính kèm chung, không bỏ sót tệp nào.
"""

from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an.attach import planner
from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an.process import mapper
from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an.process.schema import (
    INDIVIDUAL_ONLY_FIELDS,
    ORG_ONLY_FIELDS,
    UI_COMP_BY_NAME,
)
from app.procedures.registry import public_list

_KEY = "to-chuc-kinh-te-nhan-chuyen-nhuong-qsdd-du-an"

# Hồ sơ mẫu: Công ty TNHH Dịch vụ Minh Phượng đứng đơn, đại diện bà Thân Thị Thanh, ủy quyền cho
# Công ty CP đo đạc bản đồ Quân Tiến (bà Nguyễn Thị Hằng) đi nộp.
_HS_UY_QUYEN = [
    {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY TNHH DỊCH VỤ MINH PHƯỢNG"},
    {"name": "ChuHoSo_MaSoThue", "value": "5200921208"},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Doanh nghiệp"},
    {"name": "ChuHoSo_DienThoai", "value": "0912282787"},
    # Đơn đề nghị đã in địa giới MỚI sau 01/7/2025.
    {"name": "ChuHoSo_TruSoChinh", "value": {"tinh": "Lào Cai", "xa": "Phường Âu Lâu", "diaChi": "Tổ dân phố Nước Mát"}},
    {"name": "NguoiDaiDien_HoTen", "value": "THÂN THỊ THANH"},
    {"name": "NguoiDaiDien_ChucDanh", "value": "Giám đốc"},
    {"name": "NguoiDaiDien_NgaySinh", "value": "27/05/1988"},
    {"name": "NguoiDaiDien_DanToc", "value": "Kinh"},
    {"name": "NguoiDaiDien_SoDinhDanh", "value": "024188002186"},
    {"name": "NguoiDaiDien_NgayCap", "value": "17/05/2021"},
    {"name": "NguoiDaiDien_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "NguoiNop_HoTen", "value": "NGUYỄN THỊ HẰNG"},
    {"name": "NguoiNop_TenToChuc", "value": "Công ty cổ phần đo đạc bản đồ Quân Tiến"},
    {"name": "NguoiNop_SoDinhDanh", "value": "026192004454"},
    {"name": "NguoiNop_NgayCap", "value": "07/04/2021"},
    {"name": "NguoiNop_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    # Giấy ủy quyền in địa giới TRƯỚC 01/7/2025 → phải được quy đổi.
    {"name": "NguoiNop_NoiCuTru", "value": {"tinh": "Yên Bái", "xa": "Phường Đồng Tâm", "diaChi": "Tổ 12"}},
    {"name": "UyQuyen_NgayLap", "value": "25/11/2025"},
]

# Biến thể: chính người đại diện theo pháp luật đăng nhập đi nộp, hồ sơ không có giấy ủy quyền.
_HS_TU_NOP = [
    {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY TNHH DỊCH VỤ MINH PHƯỢNG"},
    {"name": "ChuHoSo_MaSoThue", "value": "5200921208"},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Doanh nghiệp"},
    {"name": "ChuHoSo_DienThoai", "value": "0912282787"},
    {"name": "ChuHoSo_TruSoChinh", "value": {"tinh": "Lào Cai", "xa": "Phường Âu Lâu", "diaChi": "Tổ dân phố Nước Mát"}},
    {"name": "NguoiDaiDien_HoTen", "value": "THÂN THỊ THANH"},
    {"name": "NguoiDaiDien_NgaySinh", "value": "27/05/1988"},
    {"name": "NguoiDaiDien_DanToc", "value": "Kinh"},
    {"name": "NguoiDaiDien_SoDinhDanh", "value": "024188002186"},
    {"name": "NguoiDaiDien_NgayCap", "value": "17/05/2021"},
    {"name": "NguoiDaiDien_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "NguoiDaiDien_NoiThuongTru", "value": {"tinh": "Bắc Ninh", "xa": "Phường Bắc Giang", "diaChi": "Số nhà 08 đường Đào Sư Tích"}},
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
    "1.115681 - Tổ chức kinh tế nhận chuyển nhượng, thuê quyền sử dụng đất, nhận góp vốn bằng quyền "
    "sử dụng đất để thực hiện dự án đầu tư theo quy định tại điểm a, b khoản 1 Điều 127 Luật Đất đai."
)


def test_trang_1_115681_nhan_dung_thu_tuc_nay():
    assert _detect(_URL_LAO_CAI, _TIEU_DE) == _KEY


def test_cum_nhan_dien_giu_nguyen_can_cu_phap_ly():
    """Cụm "điểm a, b khoản 1 Điều 127" là thứ duy nhất tách thủ tục này khỏi các thủ tục đất đai khác."""
    phrases = _entry()["detect"]["textIncludes"]
    assert any("điểm a, b khoản 1 Điều 127" in p for p in phrases)


def test_thu_tuc_dat_dai_khac_cung_cong_khong_bi_cuop_trang():
    """Trang chỉ có cụm chung ("nhận chuyển nhượng…") mà thiếu căn cứ pháp lý thì không được khớp."""
    body = _TIEU_DE.replace("theo quy định tại điểm a, b khoản 1 Điều 127 Luật Đất đai.", "")
    assert _detect(_URL_LAO_CAI, body) != _KEY


# ------------------------------------------------ hai ô readonly: không bao giờ được phát
def test_khong_bao_gio_phat_hai_o_readonly_cua_tai_khoan():
    """Ghi vào 2 ô này là script cổng xoá trắng "Di động" + "Số Căn cước" vừa điền xong."""
    assert "CongDan_tenCongDan" not in UI_COMP_BY_NAME
    assert "CongDan_soCmnd" not in UI_COMP_BY_NAME

    for ho_so, options in (
        (_HS_UY_QUYEN, _ctx("Nguyễn Thị Hằng", "026192004454")),
        (_HS_TU_NOP, _ctx("Thân Thị Thanh", "024188002186")),
    ):
        fields, _ = mapper.enrich(list(ho_so), options)
        names = _names(fields)
        assert "CongDan_tenCongDan" not in names
        assert "CongDan_soCmnd" not in names


def test_khong_phat_checkbox_va_truong_an_cua_cong():
    for name in ("chkbox_nguoinoplachuhs", "code-dkdn", "local_file", "local_file_xuly",
                 "AN_FORM_CHS", "tokenCsrf", "CongDan_maDMDiaChi"):
        assert name not in UI_COMP_BY_NAME


# ------------------------------------------------------- chủ hồ sơ là PHÁP NHÂN
def test_chu_ho_so_la_to_chuc_chon_dung_option_dn():
    fields, _ = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Thị Hằng", "026192004454"))
    names = _names(fields)
    # Option value thật của cổng, không phải nhãn tiếng Việt.
    assert names["ChuHoSo_maDoiTuongNopHS"] == "DN"
    assert names["ChuHoSo_tenCoQuanToChucCHS"] == "CÔNG TY TNHH DỊCH VỤ MINH PHƯỢNG"
    assert names["ChuHoSo_maSoThueChuHoSo"] == "5200921208"
    assert names["ChuHoSo_diDongLienLacCHS"] == "0912282787"


def test_ho_so_to_chuc_khong_phat_7_o_nhan_than_dang_bi_an():
    """Chọn Doanh nghiệp/Tổ chức là cổng display:none cả nhóm — phát vào đó chỉ báo lỗi vô cớ."""
    fields, _ = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Thị Hằng", "026192004454"))
    names = _names(fields)
    for name in INDIVIDUAL_ONLY_FIELDS:
        assert name not in names, name


def test_dia_chi_tru_so_phat_du_ba_o_khoi_chu_ho_so():
    """Checkbox "Người nộp là chủ hồ sơ" của cổng KHÔNG copy địa chỉ → mapper phải tự phát."""
    fields, _ = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Thị Hằng", "026192004454"))
    names = _names(fields)
    assert names["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    assert names["ChuHoSo_maPhuongXaCHS"] == "Phường Âu Lâu"
    assert names["ChuHoSo_diaChiChuHoSo"] == "Tổ dân phố Nước Mát"


def test_dia_gioi_cu_tren_gcn_dkdn_duoc_quy_doi_sang_danh_muc_hien_hanh():
    """"Xã Âu Lâu, Yên Bái" (địa giới trước 01/7/2025) phải ra "Phường Âu Lâu, Lào Cai"."""
    ho_so = [f for f in _HS_UY_QUYEN if f["name"] != "ChuHoSo_TruSoChinh"] + [
        {"name": "ChuHoSo_TruSoChinh", "value": {"tinh": "Yên Bái", "xa": "Xã Âu Lâu", "diaChi": "Thôn Nước Mát"}},
    ]
    fields, _ = mapper.enrich(ho_so, _ctx("Nguyễn Thị Hằng", "026192004454"))
    names = _names(fields)
    assert names["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    assert names["ChuHoSo_maPhuongXaCHS"] == "Phường Âu Lâu"


def test_ubnd_o_dong_kinh_gui_khong_thanh_to_chuc_chu_ho_so():
    fields, _ = mapper.enrich(
        list(_HS_UY_QUYEN) + [{"name": "DonDeNghi_NoiNhan", "value": "Ủy ban nhân dân phường Âu Lâu"}],
        _ctx("Nguyễn Thị Hằng", "026192004454"),
    )
    assert _names(fields)["ChuHoSo_tenCoQuanToChucCHS"] == "CÔNG TY TNHH DỊCH VỤ MINH PHƯỢNG"


def test_khong_co_to_chuc_nao_thi_nga_ve_ca_nhan_va_canh_bao():
    """Ngoài phạm vi thủ tục nhưng cổng vẫn render nhánh cá nhân — điền để cán bộ sửa, kèm cảnh báo."""
    ho_so = [f for f in _HS_TU_NOP if not f["name"].startswith("ChuHoSo_")]
    fields, errors = mapper.enrich(ho_so, _ctx("Thân Thị Thanh", "024188002186"))
    names = _names(fields)
    assert names["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert names["ChuHoSo_tenChuHoSo"] == "THÂN THỊ THANH"
    assert names["ChuHoSo_soCMNDChuHoSo"] == "024188002186"
    for name in ORG_ONLY_FIELDS:
        assert name not in names
    assert any("chỉ dành cho TỔ CHỨC KINH TẾ" in e for e in errors)


# ------------------------------- ô "Tên cơ quan/tổ chức" của khối người nộp = ĐƠN VỊ ĐI NỘP THAY
def test_nop_thay_thi_ten_co_quan_la_don_vi_duoc_uy_quyen():
    """Chỗ sai chết người: điền tên chủ hồ sơ vào đây là khai sai đơn vị đi nộp."""
    fields, _ = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Thị Hằng", "026192004454"))
    names = _names(fields)
    assert names["CongDan_tenCoQuanToChuc"] == "Công ty cổ phần đo đạc bản đồ Quân Tiến"
    assert names["CongDan_tenCoQuanToChuc"] != names["ChuHoSo_tenCoQuanToChucCHS"]
    # Hồ sơ không kèm ĐKDN của đơn vị được ủy quyền → MST để trống, không mượn của chủ hồ sơ.
    assert "CongDan_maSoThueNguoiNop" not in names


def test_dai_dien_tu_nop_thi_ten_co_quan_la_chinh_chu_ho_so():
    fields, _ = mapper.enrich(list(_HS_TU_NOP), _ctx("Thân Thị Thanh", "024188002186"))
    names = _names(fields)
    assert names["CongDan_tenCoQuanToChuc"] == "CÔNG TY TNHH DỊCH VỤ MINH PHƯỢNG"
    assert names["CongDan_maSoThueNguoiNop"] == "5200921208"


def test_canh_bao_khi_khong_doc_duoc_don_vi_duoc_uy_quyen():
    ho_so = [f for f in _HS_UY_QUYEN if f["name"] != "NguoiNop_TenToChuc"]
    _, errors = mapper.enrich(ho_so, _ctx("Nguyễn Thị Hằng", "026192004454"))
    canh_bao = next(e for e in errors if "Tên cơ quan/tổ chức" in e)
    assert "ĐƠN VỊ ĐI NỘP THAY" in canh_bao
    assert "đừng chép tên chủ hồ sơ sang" in canh_bao


# ----------------------------------------------------------------- hai mode người nộp
def test_uy_quyen_giu_nguyen_hai_nguoi_khac_nhau():
    fields, _ = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Thị Hằng", "026192004454"))
    names = _names(fields)
    # Ngày cấp căn cước của bà Hằng, không phải của bà Thanh.
    assert names["CongDan_ngayCapCmnd"] == "07/04/2021"
    # Địa chỉ đơn vị được ủy quyền (Đồng Tâm → Phường Yên Bái sau sắp xếp), khác trụ sở chủ hồ sơ.
    assert names["CongDan_maTinhThanh"] == "Tỉnh Lào Cai"
    assert names["CongDan_maPhuongXa"] == "Phường Yên Bái"
    assert names["CongDan_diaChi"] == "Tổ 12"
    assert names["CongDan_maPhuongXa"] != names["ChuHoSo_maPhuongXaCHS"]
    # Nhân thân người đại diện KHÔNG được rò sang khối người nộp.
    assert "CongDan_ngaySinhCongDan" not in names
    assert "CongDan_danTocCongDan" not in names


def test_uy_quyen_khong_muon_so_dien_thoai_cua_to_chuc():
    """SĐT trên Giấy chứng nhận ĐKDN là của CHỦ HỒ SƠ → ô Di động khối người nộp phải TRỐNG."""
    fields, errors = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Thị Hằng", "026192004454"))
    names = _names(fields)
    assert "CongDan_diDong" not in names
    assert names["ChuHoSo_diDongLienLacCHS"] == "0912282787"
    assert any("Di động" in e and "BẮT BUỘC" in e for e in errors)


def test_dai_dien_tu_nop_thi_duoc_dung_so_dien_thoai_cua_to_chuc():
    """Người đại diện đi nộp là đại diện cho chính tổ chức đó → số của tổ chức là hợp lệ."""
    fields, _ = mapper.enrich(list(_HS_TU_NOP), _ctx("Thân Thị Thanh", "024188002186"))
    names = _names(fields)
    assert names["CongDan_diDong"] == "0912282787"
    assert names["CongDan_ngaySinhCongDan"] == "27/05/1988"
    assert names["CongDan_ngayCapCmnd"] == "17/05/2021"


def test_uy_quyen_canh_bao_cam_tick_checkbox():
    _, errors = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Thị Hằng", "026192004454"))
    assert any("nộp thay theo ủy quyền" in e for e in errors)
    assert any("Người nộp là chủ hồ sơ" in e for e in errors)


def test_moc_tai_khoan_chot_mode_du_ho_so_co_uy_quyen():
    """Chính người đại diện đăng nhập thì lần nộp này không dùng ủy quyền — bỏ nhân thân bà Hằng."""
    fields, errors = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Thân Thị Thanh", "024188002186"))
    names = _names(fields)
    assert names["CongDan_ngayCapCmnd"] == "17/05/2021"        # của bà Thanh, không phải 07/04/2021
    assert names["CongDan_tenCoQuanToChuc"] == "CÔNG TY TNHH DỊCH VỤ MINH PHƯỢNG"
    assert names["CongDan_gioiTinhCongDan"] == "Nữ"            # 024188002186 → chữ số thứ 4 = 1
    assert any("KHÔNG dùng ủy quyền" in e for e in errors)


# ----------------------------------- khối người nộp: chỉ điền khi có giấy tờ của người đăng nhập
_O_NGUOI_NOP = (
    "CongDan_tenCoQuanToChuc",
    "CongDan_maSoThueNguoiNop",
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
    """Hai ô readonly hiện đúng tên tài khoản mà ngày sinh/địa chỉ là của người khác = sai lệch nhân thân."""
    fields, errors = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nhâm Đắc Đạt", "001088000999"))
    names = _names(fields)
    for name in _O_NGUOI_NOP:
        assert name not in names, name
    assert any("KHÔNG có giấy tờ tuỳ thân của người đang đăng nhập" in e for e in errors)
    # Khối chủ hồ sơ là của TỔ CHỨC, không phải của phiên đăng nhập → vẫn phải điền đủ.
    assert names["ChuHoSo_tenCoQuanToChucCHS"] == "CÔNG TY TNHH DỊCH VỤ MINH PHƯỢNG"
    assert names["ChuHoSo_maPhuongXaCHS"] == "Phường Âu Lâu"


def test_khong_doc_duoc_tai_khoan_thi_cung_bo_trong_khoi_nguoi_nop():
    fields, errors = mapper.enrich(list(_HS_UY_QUYEN), {})
    names = _names(fields)
    for name in _O_NGUOI_NOP:
        assert name not in names, name
    assert any("KHÔNG xác minh được" in e for e in errors)
    assert names["ChuHoSo_maSoThueChuHoSo"] == "5200921208"


def test_canh_bao_chan_khoi_nguoi_nop_chi_ro_cach_go():
    _, errors = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nhâm Đắc Đạt", "001088000999"))
    chan = next(e for e in errors if "KHÔNG có giấy tờ tuỳ thân" in e)
    assert "001088000999" in chan            # nói rõ đang thiếu giấy tờ của số căn cước nào
    assert "tải thêm CCCD" in chan           # cách gỡ 1
    assert "đăng nhập bằng tài khoản" in chan  # cách gỡ 2


# ------------------------------------------------------- ngày sinh / dân tộc / giới tính
def test_khong_bia_ngay_thang_khi_chi_co_nam():
    ho_so = [f for f in _HS_TU_NOP if f["name"] != "NguoiDaiDien_NgaySinh"] + [
        {"name": "NguoiDaiDien_NgaySinh", "value": "1988"},
    ]
    fields, errors = mapper.enrich(ho_so, _ctx("Thân Thị Thanh", "024188002186"))
    assert "CongDan_ngaySinhCongDan" not in _names(fields)
    assert any("NĂM SINH" in e for e in errors)


def test_khong_mac_dinh_dan_toc_kinh_cho_nguoi_duoc_uy_quyen():
    fields, _ = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Thị Hằng", "026192004454"))
    assert "CongDan_danTocCongDan" not in _names(fields)


def test_gioi_tinh_suy_tu_chu_so_thu_4_cua_can_cuoc():
    fields, _ = mapper.enrich(list(_HS_UY_QUYEN), _ctx("Nguyễn Thị Hằng", "026192004454"))
    assert _names(fields)["CongDan_gioiTinhCongDan"] == "Nữ"  # 026192004454 → chữ số thứ 4 = 1


def test_khong_co_can_cuoc_12_so_thi_bo_trong_gioi_tinh():
    ho_so = [f for f in _HS_UY_QUYEN if f["name"] != "NguoiNop_SoDinhDanh"] + [
        {"name": "NguoiNop_SoDinhDanh", "value": "060182225"},  # CMND cũ 9 số
    ]
    fields, _ = mapper.enrich(ho_so, _ctx("Nguyễn Thị Hằng", "060182225"))
    assert "CongDan_gioiTinhCongDan" not in _names(fields)


def test_canh_bao_ben_chuyen_nhuong_vi_buoc_2_khong_co_o():
    ho_so = list(_HS_UY_QUYEN) + [
        {"name": "KhuDat_TongDienTich", "value": "292,9"},
        {"name": "KhuDat_DanhSachThua", "value": "Thửa 132, 135 (tờ 9) — hộ ông Đoàn Văn Đức"},
    ]
    _, errors = mapper.enrich(ho_so, _ctx("Nguyễn Thị Hằng", "026192004454"))
    assert any("BÊN CHUYỂN NHƯỢNG" in e and "292,9" in e for e in errors)


def test_canh_bao_nguoi_dai_dien_cu_tren_quyet_dinh_chap_thuan():
    ho_so = list(_HS_UY_QUYEN) + [{"name": "QDChapThuan_So", "value": "2151/QĐ-UBND"}]
    _, errors = mapper.enrich(ho_so, _ctx("Nguyễn Thị Hằng", "026192004454"))
    assert any("NGƯỜI ĐẠI DIỆN CŨ" in e and "2151/QĐ-UBND" in e for e in errors)


def test_khong_doc_duoc_dia_chi_tru_so_thi_canh_bao_thay_vi_im_lang():
    ho_so = [f for f in _HS_UY_QUYEN if f["name"] != "ChuHoSo_TruSoChinh"]
    _, errors = mapper.enrich(ho_so, _ctx("Nguyễn Thị Hằng", "026192004454"))
    assert any("địa chỉ trụ sở chính" in e for e in errors)


# --------------------------------------------------------------------------- đính kèm
_BO_7_TEP = [
    "Don_DN_Minh_Phuong.pdf",
    "2So_do_khu_dat__GCN_3_ho_gia_dinh.pdf",
    "3QD_chap_thuan_chu_truong.pdf",
    "4DKKD.pdf",
    "5Giay_UY_quyen.pdf",
    "6QD_thhuee_datBD_thue_dat_gd_1.pdf",
    "7Tong_MB.pdf",
]
_LLM_7_TEP = {
    0: "don_de_nghi",
    1: "so_do_khu_dat",
    2: "qd_chap_thuan_chu_truong",
    3: "gcn_dkdn",
    4: "giay_uy_quyen",
    5: "qd_giao_thue_dat",
    6: "so_hoa_mat_bang",
}


def test_moi_tep_mot_dong_giay_to_khac_khong_dung_fixed_slot():
    """Màn hình này KHÔNG có bảng "Thành phần hồ sơ nộp" → không được phát target fixed-slot."""
    attachments, _, _ = planner.build_plan_items(_files(_BO_7_TEP), _LLM_7_TEP)
    assert len(attachments) == 7
    for item in attachments:
        assert item["target"] == "new"
        assert item["needsAddComponent"] is True
        # Cổng iGate VNPT: bấm "Chọn tệp tin" mở hộp thoại file của OS → phải gán thẳng.
        assert item["noChooserClick"] is True
        assert "slotIndex" not in item


def test_hai_dong_dau_giu_nguyen_van_ten_thanh_phan_theo_anh_huong_dan():
    attachments, _, _ = planner.build_plan_items(_files(_BO_7_TEP), _LLM_7_TEP)
    assert attachments[0]["documentName"] == "Trích lục vị trí khu đất mà nhà đầu tư đề xuất thực hiện dự án"
    assert attachments[0]["fileName"] == "2So_do_khu_dat__GCN_3_ho_gia_dinh.pdf"
    assert attachments[1]["documentName"] == (
        "Văn bản đề nghị chấp thuận cho tổ chức kinh tế nhận chuyển nhượng, thuê quyền sử dụng đất, "
        "nhận góp vốn bằng quyền sử dụng đất để thực hiện dự án đầu tư"
    )
    assert attachments[1]["fileName"] == "3QD_chap_thuan_chu_truong.pdf"
    # FE gõ componentName vào ô tên của dòng "Giấy tờ khác" → phải trùng tên giấy tờ.
    assert all(a["componentName"] == a["documentName"] for a in attachments)


def test_nam_tep_dinh_kem_chung_giu_dung_thu_tu_anh_anh_xa():
    attachments, _, _ = planner.build_plan_items(_files(_BO_7_TEP), _LLM_7_TEP)
    assert [a["fileName"] for a in attachments[2:]] == [
        "Don_DN_Minh_Phuong.pdf",
        "4DKKD.pdf",
        "5Giay_UY_quyen.pdf",
        "6QD_thhuee_datBD_thue_dat_gd_1.pdf",
        "7Tong_MB.pdf",
    ]


def test_giu_nguyen_fileindex_khi_sap_lai_thu_tu_dong():
    """Sắp lại thứ tự dòng không được làm lệch tệp — fileIndex phải trỏ đúng tệp gốc."""
    files = _files(_BO_7_TEP)
    attachments, _, _ = planner.build_plan_items(files, _LLM_7_TEP)
    for item in attachments:
        assert files[item["fileIndex"]]["name"] == item["fileName"]


def test_canh_bao_cho_doi_diem_anh_anh_xa_tu_ghi_nhan_la_chua_chac():
    """Dòng ② mang tên "Văn bản đề nghị…" nhưng gắn Quyết định chấp thuận — phải nói ra, không tự sửa."""
    _, warnings, _ = planner.build_plan_items(_files(_BO_7_TEP), _LLM_7_TEP)
    canh_bao = next(w for w in warnings if "đổi chỗ hai tệp" in w)
    assert "QUYẾT ĐỊNH CHẤP THUẬN CHỦ TRƯƠNG ĐẦU TƯ" in canh_bao
    assert "không tự đổi" in canh_bao


def test_hai_tep_cung_loai_van_co_ten_dong_khac_nhau():
    files = _files(["dkdn1.pdf", "dkdn2.pdf"])
    attachments, _, _ = planner.build_plan_items(files, {0: "gcn_dkdn", 1: "gcn_dkdn"})
    names = [a["documentName"] for a in attachments]
    assert names[0] != names[1]
    assert names[0] == "Giấy chứng nhận đăng ký doanh nghiệp"


def test_khong_bo_sot_file_nao_khi_llm_chet():
    attachments, warnings, _ = planner.build_plan_items(_files(_BO_7_TEP), {})
    assert len(attachments) == 7
    assert all(a["target"] == "new" for a in attachments)
    assert any("Chưa nhận ra loại giấy tờ" in w for w in warnings)


def test_canh_bao_khi_thieu_giay_to_chinh():
    _, warnings, _ = planner.build_plan_items(_files(["don.pdf"]), {0: "don_de_nghi"})
    assert any("Giấy chứng nhận đăng ký doanh nghiệp của tổ chức đứng đơn" in w for w in warnings)
    assert any("Quyết định chấp thuận chủ trương đầu tư" in w for w in warnings)


def test_du_giay_to_chinh_thi_khong_canh_bao_thieu():
    _, warnings, _ = planner.build_plan_items(_files(_BO_7_TEP), _LLM_7_TEP)
    assert not any("Chưa thấy trong bộ tệp" in w for w in warnings)


def test_cccd_van_duoc_dinh_kem_chu_khong_bi_bo():
    """Ảnh ánh xạ chốt "7/7 tệp trong hồ sơ đã được gắn" → không loại tệp nào."""
    files = _files(["don.pdf", "cccd.pdf"])
    attachments, warnings, _ = planner.build_plan_items(files, {0: "don_de_nghi", 1: "giay_to_tuy_than"})
    assert len(attachments) == 2
    assert attachments[1]["documentName"] == "Giấy tờ tùy thân"
    assert any("giấy tờ tùy thân" in w for w in warnings)


def test_luon_nhac_khong_tach_sang_thanh_phan_ho_so_va_giu_o_ve_viec():
    _, warnings, _ = planner.build_plan_items(_files(["don.pdf"]), {0: "don_de_nghi"})
    nhac = next(w for w in warnings if "Giấy tờ khác" in w and "Thành phần hồ sơ nộp" in w)
    assert "Về việc (*)" in nhac


def test_khong_co_tep_thi_khong_canh_bao_thua():
    attachments, warnings, _ = planner.build_plan_items([], {})
    assert attachments == []
    assert not any("Giấy tờ khác" in w and "Thành phần hồ sơ nộp" in w for w in warnings)


def test_tep_vuot_6mb_bi_loai_va_bao_ro():
    import base64

    big = "data:application/pdf;base64," + base64.b64encode(b"x" * (7 * 1024 * 1024)).decode()
    assert planner._data_url_size(big) > planner._MAX_FILE_BYTES


# --------------------------------------------------------------------------- prompt
def test_prompt_attach_co_bay_phan_biet_hai_loai_quyet_dinh():
    from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an.attach.prompt import SYSTEM_PROMPT

    assert "qd_chap_thuan_chu_truong" in SYSTEM_PROMPT
    assert "qd_giao_thue_dat" in SYSTEM_PROMPT
    assert "HAI LOẠI QUYẾT ĐỊNH" in SYSTEM_PROMPT
    # Không được phân loại theo tên file.
    assert "ĐỪNG DÙNG TÊN FILE" in SYSTEM_PROMPT


def test_prompt_process_tach_hai_phap_nhan_va_ben_chuyen_nhuong():
    from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an.process.prompt import EXTRA_RULES

    assert "HAI PHÁP NHÂN TRONG CÙNG MỘT HỒ SƠ" in EXTRA_RULES
    assert "BÊN CHUYỂN NHƯỢNG" in EXTRA_RULES
    assert "không bịa 01/01" in EXTRA_RULES
    assert "ông/bà" in EXTRA_RULES


def test_prompt_process_canh_bao_kinh_gui_ubnd_khong_phai_to_chuc():
    from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhung_sqdd_du_an.process.prompt import EXTRA_RULES

    assert "KÍNH GỬI" in EXTRA_RULES.upper()
    assert "NƠI NHẬN" in EXTRA_RULES.upper()
