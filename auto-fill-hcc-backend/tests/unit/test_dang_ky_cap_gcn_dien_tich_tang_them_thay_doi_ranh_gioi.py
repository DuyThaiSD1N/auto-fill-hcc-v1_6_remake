"""[Lào Cai] Thửa đất có diện tích tăng thêm do thay đổi ranh giới — mã 1.115693.

Khoá năm điều dễ vỡ, đều là chỗ thủ tục này khác hẳn thủ tục song sinh 1.115694:
  1. Nhận diện KHÔNG được cướp trang của 1.115694 và ngược lại — hai tiêu đề chỉ khác vế cuối.
  2. Đính kèm KHÔNG có bảng dòng cố định: mọi tệp phải đi vào mục "Giấy tờ khác" (target="new").
  3. Hai mode người nộp: nộp thay theo ủy quyền thì TUYỆT ĐỐI không chép nhân thân chéo hai khối.
  4. Nơi cư trú chủ hồ sơ hay ở TỈNH KHÁC với thửa đất — trùng nhau là dấu hiệu lấy nhầm địa chỉ.
  5. Số định danh sai độ dài (hồ sơ mẫu có bản 13 chữ số) phải được phát kèm cảnh báo, không sửa lén.
"""

from pathlib import Path

from app.pipelines.dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi.attach import planner
from app.pipelines.dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi.process import mapper
from app.pipelines.dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi.process.schema import (
    INDIVIDUAL_ONLY_FIELDS,
    ORG_ONLY_FIELDS,
    UI_COMP_BY_NAME,
)
from app.procedures.registry import public_list

_KEY = "dang-ky-cap-gcn-dien-tich-tang-them-thay-doi-ranh-gioi"
_KEY_CHUYEN_QUYEN = "dang-ky-cap-gcn-dien-tich-tang-them-nhan-chuyen-quyen-mot-phan-thua"

# Hồ sơ mẫu đi kèm file mapping: hộ ông Nguyễn Duy Tâm (thường trú Bắc Ninh) có thửa đất ở Lào Cai,
# ông Phùng Văn Thuyên nộp thay theo Giấy uỷ quyền số 0055 ngày 09/01/2026.
_HS_UY_QUYEN = [
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Duy Tâm"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "025 047 000 984"},
    {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
    {"name": "ChuHoSo_NoiCuTru",
     "value": {"tinh": "Bắc Ninh", "xa": "Phường Kinh Bắc", "diaChi": "Khu Niềm Xá"}},
    {"name": "NguoiNop_HoTen", "value": "Phùng Văn Thuyên"},
    # Giấy cam kết chỉ ghi NĂM sinh — mapper phải bỏ, không bịa 01/01.
    {"name": "NguoiNop_NgaySinh", "value": "1977"},
    # ⚠ Giấy cam kết ghi "025 077 0141 255" = 13 chữ số (CCCD chuẩn 12) → phải cảnh báo.
    {"name": "NguoiNop_SoDinhDanh", "value": "025 077 0141 255"},
    {"name": "NguoiNop_NoiCuTru",
     "value": {"tinh": "Phú Thọ", "xa": "Xã Cẩm Khê", "diaChi": "Khu Bình Phú"}},
    {"name": "UyQuyen_SoGiay", "value": "0055"},
    {"name": "ThuaDat_DiaChi",
     "value": {"tinh": "Lào Cai", "xa": "Phường Trung Tâm", "diaChi": "Tổ dân phố 5"}},
    {"name": "ThuaDat_SoThua", "value": "55"},
    {"name": "ThuaDat_SoToBanDo", "value": "24"},
    {"name": "DienTich_TangThem", "value": "10,0"},
]

# Biến thể tự nộp: chính chủ hộ đi nộp, hồ sơ chỉ khai một lần ở khối chủ hồ sơ.
_HS_TU_NOP = [
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Duy Tâm"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "025047000984"},
    {"name": "ChuHoSo_DienThoai", "value": "0912345678"},
    {"name": "ChuHoSo_NoiCuTru",
     "value": {"tinh": "Bắc Ninh", "xa": "Phường Kinh Bắc", "diaChi": "Khu Niềm Xá"}},
]


def _entry(key=_KEY):
    return next(p for p in public_list() if p["key"] == key)


def _names(fields):
    return {f["name"]: f["value"] for f in fields}


def _ctx(fullname: str, identity: str) -> dict:
    """options như popup gửi lên: nhân thân tài khoản định danh đang đăng nhập."""
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


def test_key_trung_voi_muc_ke_khai_links_1_115693():
    """Key phải trùng mục ke_khai_links thì chọn link kê khai mới ra đúng pipeline điền."""
    from app.procedures.ke_khai_links import _load

    muc = next(i for i in _load() if i["key"] == _KEY)
    assert muc["code"] == "1.115693"


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

# Phần dùng chung y nguyên của hai tiêu đề, dừng đúng trước vế phân biệt.
_TIEU_DE_CHUNG = (
    "Đăng ký, cấp Giấy chứng nhận đối với thửa đất có diện tích tăng thêm do thay đổi ranh giới so "
    "với Giấy chứng nhận đã cấp đối với trường hợp thửa đất gốc đã có Giấy chứng nhận,"
)


def test_trang_1_115693_nhan_dung_thu_tuc_nay():
    body = f"{_TIEU_DE_CHUNG} phần diện tích đất tăng thêm chưa được cấp Giấy chứng nhận"
    assert _detect(_URL_LAO_CAI, body) == _KEY


def test_trang_1_115694_khong_bi_thu_tuc_moi_cuop_mat():
    """Chiều ngược lại: trang của thủ tục song sinh phải vẫn về đúng 1.115694."""
    body = (
        f"{_TIEU_DE_CHUNG} phần diện tích đất tăng thêm do nhận chuyển quyền sử dụng một phần thửa "
        "đất đã được cấp Giấy chứng nhận"
    )
    assert _detect(_URL_LAO_CAI, body) == _KEY_CHUYEN_QUYEN


def test_hai_ve_cuoi_loai_tru_nhau_nen_khong_can_text_priority():
    """Cụm riêng của thủ tục này KHÔNG được là chuỗi con của tiêu đề 1.115694 (và ngược lại)."""
    import re
    import unicodedata

    def norm(value):
        text = unicodedata.normalize("NFD", str(value or ""))
        text = "".join(c for c in text if unicodedata.category(c) != "Mn")
        return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()

    rieng_1_115693 = "phần diện tích đất tăng thêm chưa được cấp giấy chứng nhận"
    assert rieng_1_115693 in _entry()["detect"]["textIncludes"]
    assert norm(rieng_1_115693) not in norm(_entry(_KEY_CHUYEN_QUYEN)["label"])
    # Không khai textPriority: hai vế loại trừ nhau nên nhánh textIncludes thường là đủ.
    assert not _entry()["detect"].get("textPriority")


def test_khong_an_theo_chu_hoa_giay_chung_nhan():
    """Tiêu đề 1.115693 viết hoa "Giấy chứng nhận" ở chỗ 1.115694 viết thường — đừng dựa vào đó."""
    phrases = _entry()["detect"]["textIncludes"]
    assert all(p == p.lower() for p in phrases)


# ------------------------------------------------ hai ô readonly: không bao giờ được phát
def test_khong_bao_gio_phat_hai_o_readonly_cua_tai_khoan():
    """Ghi vào 2 ô này là script cổng XOÁ TRẮNG "Di động" + "Số Căn cước" vừa điền xong."""
    assert "CongDan_tenCongDan" not in UI_COMP_BY_NAME
    assert "CongDan_soCmnd" not in UI_COMP_BY_NAME

    for payload in (_HS_UY_QUYEN, _HS_TU_NOP):
        by_name = _names(mapper.enrich(payload)[0])
        assert "CongDan_tenCongDan" not in by_name
        assert "CongDan_soCmnd" not in by_name


def test_khong_phat_o_bi_cong_an_theo_doi_tuong():
    """Hồ sơ cá nhân thì 2 ô tổ chức display:none — phát vào đó chỉ làm engine báo lỗi vô cớ."""
    by_name = _names(mapper.enrich(_HS_UY_QUYEN, _ctx("Phùng Văn Thuyên", "0250770141255"))[0])
    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "Cá nhân"
    assert not (ORG_ONLY_FIELDS & set(by_name))

    to_chuc = [
        {"name": "ChuHoSo_LaToChuc", "value": True},
        {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY TNHH ABC"},
        {"name": "ChuHoSo_MaSoThue", "value": "5200170752"},
        {"name": "ChuHoSo_HoTen", "value": "Nguyễn Duy Tâm"},
    ]
    by_name = _names(mapper.enrich(to_chuc)[0])
    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "Tổ chức"
    assert not (INDIVIDUAL_ONLY_FIELDS & set(by_name))


# ------------------------------------------------------------------- mode A: nộp thay theo ủy quyền
def test_uy_quyen_giu_nguyen_hai_nguoi_khac_nhau():
    """Tài khoản đăng nhập là ông Thuyên (người được ủy quyền) → hai khối phải tách bạch."""
    fields, _ = mapper.enrich(_HS_UY_QUYEN, _ctx("Phùng Văn Thuyên", "0250770141255"))
    by_name = _names(fields)

    assert by_name["ChuHoSo_tenChuHoSo"] == "Nguyễn Duy Tâm"
    assert by_name["ChuHoSo_soCMNDChuHoSo"] == "025047000984"
    # Địa chỉ hai khối là hai tỉnh khác nhau, không được lẫn.
    assert by_name["CongDan_maTinhThanh"] == "Tỉnh Phú Thọ"
    assert by_name["CongDan_maPhuongXa"] == "Xã Cẩm Khê"
    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Bắc Ninh"
    assert by_name["ChuHoSo_maPhuongXaCHS"] == "Phường Kinh Bắc"


def test_uy_quyen_khong_muon_so_dien_thoai_cua_chu_ho_so():
    """Giấy cam kết bỏ trống SĐT — mượn số của chủ hồ sơ là gán sai liên hệ."""
    payload = _HS_UY_QUYEN + [{"name": "ChuHoSo_DienThoai", "value": "0912345678"}]
    fields, warnings = mapper.enrich(payload, _ctx("Phùng Văn Thuyên", "0250770141255"))
    by_name = _names(fields)

    assert "CongDan_diDong" not in by_name
    assert by_name["ChuHoSo_diDongLienLacCHS"] == "0912345678"
    assert any("hỏi trực tiếp người nộp" in w for w in warnings)


def test_uy_quyen_canh_bao_o_readonly_va_cam_tick_checkbox():
    _, warnings = mapper.enrich(_HS_UY_QUYEN, _ctx("Phùng Văn Thuyên", "0250770141255"))
    assert any("READONLY" in w for w in warnings)
    assert any("không tick" in w.lower() for w in warnings)
    # Cảnh báo nêu đích danh số giấy ủy quyền để cán bộ đối chiếu.
    assert any("0055" in w for w in warnings)


def test_chi_co_nam_sinh_thi_bo_khong_biat_ngay_thang():
    """Giấy cam kết ghi "Ngày sinh: 1977" — ghép thành 01/01/1977 là bịa nhân thân."""
    by_name = _names(mapper.enrich(_HS_UY_QUYEN, _ctx("Phùng Văn Thuyên", "0250770141255"))[0])
    assert "CongDan_ngaySinhCongDan" not in by_name


# --------------------------------------------------- mốc tài khoản quyết định mode, không phải giấy tờ
# Các ô của khối "Thông tin người nộp" mà mình tự điền (2 ô readonly còn lại cổng tự đổ).
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


def test_moc_tai_khoan_la_chu_ho_so_thi_quay_ve_mode_tu_nop():
    """Giấy tờ ghi có người được ủy quyền, nhưng CHÍNH CHỦ HỘ đang đăng nhập đi nộp.

    ⚠ Khối người nộp phải mang địa chỉ của CHÍNH CHỦ HỘ (Bắc Ninh), TUYỆT ĐỐI không phải địa chỉ
    Phú Thọ của ông Thuyên — ông Thuyên không tham gia lần nộp này.
    """
    fields, warnings = mapper.enrich(_HS_UY_QUYEN, _ctx("Nguyễn Duy Tâm", "025047000984"))
    by_name = _names(fields)

    assert by_name["CongDan_maTinhThanh"] == "Tỉnh Bắc Ninh"
    assert by_name["CongDan_maPhuongXa"] == "Phường Kinh Bắc"
    assert by_name["CongDan_diaChi"] == "Khu Niềm Xá"
    assert any("trùng chủ hồ sơ" in w for w in warnings)


def test_tai_khoan_la_nguoi_la_thi_bo_trong_ca_khoi_nguoi_nop():
    """Người thân đăng nhập bằng tài khoản của mình rồi nộp hộ, hồ sơ không có CCCD của họ.

    Đây là lỗi thật đã thấy trên cổng: hai ô readonly hiện đúng tên tài khoản đăng nhập, còn ngày
    sinh / giới tính / Tỉnh / Phường-Xã lại là của người trong CCCD đã tải lên → hồ sơ sai lệch
    nhân thân mà nhìn màn hình rất khó phát hiện. Giờ phải để TRỐNG HẲN.
    """
    fields, warnings = mapper.enrich(_HS_UY_QUYEN, _ctx("Trần Văn Khác", "001199000111"))
    by_name = _names(fields)
    for name in _O_NGUOI_NOP:
        assert name not in by_name, name
    assert any("KHÔNG có giấy tờ tuỳ thân của người đang đăng nhập" in w for w in warnings)
    # Khối chủ hồ sơ là của HỒ SƠ, không phải của phiên đăng nhập → vẫn phải điền đủ.
    assert by_name["ChuHoSo_tenChuHoSo"] == "Nguyễn Duy Tâm"
    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Bắc Ninh"


def test_canh_bao_chan_khoi_nguoi_nop_chi_ro_cach_go():
    _, warnings = mapper.enrich(_HS_UY_QUYEN, _ctx("Trần Văn Khác", "001199000111"))
    chan = next(w for w in warnings if "KHÔNG có giấy tờ tuỳ thân" in w)
    assert "001199000111" in chan
    assert "tải thêm CCCD" in chan
    assert "đăng nhập bằng tài khoản" in chan


def test_thieu_moc_tai_khoan_thi_cung_bo_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_HS_UY_QUYEN)
    by_name = _names(fields)
    for name in _O_NGUOI_NOP:
        assert name not in by_name, name
    assert any("KHÔNG xác minh được" in w for w in warnings)
    assert by_name["ChuHoSo_tenChuHoSo"] == "Nguyễn Duy Tâm"


def test_uy_quyen_dung_tai_khoan_thi_van_dien_khoi_nguoi_nop():
    """Chính ông Thuyên đăng nhập → hồ sơ có Giấy cam kết của ông → được phép điền."""
    fields, _ = mapper.enrich(_HS_UY_QUYEN, _ctx("Phùng Văn Thuyên", "0250770141255"))
    by_name = _names(fields)
    assert by_name["CongDan_maTinhThanh"] == "Tỉnh Phú Thọ"
    assert by_name["CongDan_maPhuongXa"] == "Xã Cẩm Khê"


# ------------------------------------------------------------------- mode B: chủ hồ sơ tự đi nộp
def test_tu_nop_van_phat_du_ca_khoi_chu_ho_so():
    """Checkbox "Người nộp là chủ hồ sơ" KHÔNG copy Tỉnh/Phường-Xã/Địa chỉ → phải tự phát đủ."""
    fields, _ = mapper.enrich(_HS_TU_NOP, _ctx("Nguyễn Duy Tâm", "025047000984"))
    by_name = _names(fields)

    for name in ("ChuHoSo_maTinhThanhCHS", "ChuHoSo_maPhuongXaCHS", "ChuHoSo_diaChiChuHoSo"):
        assert name in by_name
    # Và khối người nộp cũng được bổ khuyết từ chủ hồ sơ vì đúng một người.
    assert by_name["CongDan_maTinhThanh"] == "Tỉnh Bắc Ninh"
    assert by_name["CongDan_diDong"] == "0912345678"


# ------------------------------------------------------------- bẫy riêng của thủ tục này
def test_so_dinh_danh_sai_do_dai_van_phat_nhung_phai_canh_bao():
    """Hồ sơ mẫu có CCCD 13 chữ số — sửa lén cho "đủ 12" là tự bịa nhân thân."""
    _, warnings = mapper.enrich(_HS_UY_QUYEN, _ctx("Phùng Văn Thuyên", "0250770141255"))
    canh_bao = [w for w in warnings if "13 chữ số" in w]
    assert canh_bao and "0250770141255" in canh_bao[0]


def test_khong_canh_bao_khi_so_dinh_danh_dung_do_dai():
    _, warnings = mapper.enrich(_HS_TU_NOP, _ctx("Nguyễn Duy Tâm", "025047000984"))
    assert not any("chữ số) — không đúng định dạng" in w for w in warnings)


def test_canh_bao_khi_dia_chi_chu_ho_so_trung_dia_chi_thua_dat():
    """Lấy nhầm địa chỉ lô đất làm nơi cư trú là bẫy số một của thủ tục này."""
    payload = [
        {"name": "ChuHoSo_HoTen", "value": "Nguyễn Duy Tâm"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "025047000984"},
        {"name": "ChuHoSo_NoiCuTru",
         "value": {"tinh": "Lào Cai", "xa": "Phường Trung Tâm", "diaChi": "Tổ dân phố 5"}},
        {"name": "ThuaDat_DiaChi",
         "value": {"tinh": "Lào Cai", "xa": "Phường Trung Tâm", "diaChi": "Tổ dân phố 5"}},
    ]
    _, warnings = mapper.enrich(payload, _ctx("Nguyễn Duy Tâm", "025047000984"))
    assert any("TRÙNG địa chỉ thửa đất" in w for w in warnings)


def test_khac_tinh_voi_thua_dat_la_binh_thuong_khong_canh_bao():
    """Chủ hộ ở Bắc Ninh, thửa đất ở Lào Cai — đúng hồ sơ mẫu, không được báo động giả."""
    _, warnings = mapper.enrich(_HS_UY_QUYEN, _ctx("Phùng Văn Thuyên", "0250770141255"))
    assert not any("TRÙNG địa chỉ thửa đất" in w for w in warnings)


def test_ma_so_thue_ca_nhan_khong_bien_ho_so_thanh_to_chuc():
    """MST 10 số trên 3 tờ khai thuế là MST CÁ NHÂN — prompt cấm đưa vào ChuHoSo_MaSoThue."""
    from app.pipelines.dang_ky_cap_gcn_dien_tich_tang_them_thay_doi_ranh_gioi.process.prompt import (
        EXTRA_RULES,
    )

    assert "MÃ SỐ THUẾ CÁ" in EXTRA_RULES.upper()
    assert "5200170752" in EXTRA_RULES


# ------------------------------------------------------------------------------- đính kèm
def test_moi_tep_deu_di_vao_giay_to_khac():
    """Bước Thành phần hồ sơ KHÔNG có dòng dựng sẵn → không được phát fixed-slot."""
    files = _files(["01_don.pdf", "02_do_dac.pdf", "03_bien_ban.pdf"])
    llm = {0: "don_bien_dong", 1: "phieu_do_dac", 2: "bien_ban_ranh_gioi"}
    attachments, _, _ = planner.build_plan_items(files, llm)

    assert len(attachments) == 3
    for item in attachments:
        assert item["target"] == "new"
        assert item["needsAddComponent"] is True
        # Cổng iGate VNPT: bấm "Chọn tệp tin" mở hộp thoại file của hệ điều hành → cấm bấm.
        assert item["noChooserClick"] is True
        assert "slotIndex" not in item
        # componentName là thứ FE gõ vào ô tên của dòng → phải bằng documentName.
        assert item["componentName"] == item["documentName"]


def test_ten_dong_lay_dung_theo_anh_anh_xa():
    files = _files(["a.pdf", "b.pdf", "c.pdf", "d.pdf", "e.pdf"])
    llm = {
        0: "don_bien_dong",
        1: "phieu_do_dac",
        2: "bien_ban_ranh_gioi",
        3: "giay_cam_ket_chu_ky",
        4: "to_khai_thue",
    }
    names = [i["documentName"] for i in planner.build_plan_items(files, llm)[0]]
    assert names == [
        "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất",
        "Phiếu đo đạc chỉnh lý thửa đất kèm Bản mô tả ranh giới, mốc giới thửa đất",
        "Biên bản làm việc xác nhận ranh giới, mốc giới và hiện trạng sử dụng đất",
        "Giấy cam kết xác nhận chữ ký",
        "Tờ khai lệ phí trước bạ, Tờ khai tiền sử dụng đất, Tờ khai thuế SDĐ phi nông nghiệp",
    ]


def test_hai_tep_cung_loai_khong_de_ten_dong_len_nhau():
    """documentName thành TÊN DÒNG → trùng tên là hai dòng ghi đè nhau trên cổng."""
    files = _files(["tk1.pdf", "tk2.pdf"])
    attachments, _, _ = planner.build_plan_items(files, {0: "to_khai_thue", 1: "to_khai_thue"})
    names = [i["documentName"] for i in attachments]
    assert len(set(names)) == 2
    assert names[1].endswith("(2)")


def test_tep_khong_ro_loai_van_duoc_them_dong_theo_ten_tep():
    attachments, warnings, _ = planner.build_plan_items(_files(["Bien_lai_nop_tien.pdf"]), {})
    assert len(attachments) == 1
    assert attachments[0]["detectedType"] == "khac"
    assert attachments[0]["documentName"]
    assert any("Chưa nhận ra loại giấy tờ" in w for w in warnings)


def test_nhac_thanh_phan_ho_so_chinh_con_thieu():
    """Ảnh ánh xạ ghi rõ GCN gốc chưa có trong file scan — phải nhắc, không im lặng."""
    files = _files(["01_don.pdf", "02_do_dac.pdf", "03_bien_ban.pdf"])
    llm = {0: "don_bien_dong", 1: "phieu_do_dac", 2: "bien_ban_ranh_gioi"}
    _, warnings, _ = planner.build_plan_items(files, llm)

    thieu = [w for w in warnings if "thành phần hồ sơ chính" in w]
    assert thieu and "TP 2" in thieu[0]
    assert "KHÔNG tự tạo tệp thay thế" in thieu[0]


def test_khong_nhac_khi_du_bon_thanh_phan_chinh():
    files = _files(["a.pdf", "b.pdf", "c.pdf", "d.pdf"])
    llm = {0: "don_bien_dong", 1: "gcn", 2: "phieu_do_dac", 3: "bien_ban_ranh_gioi"}
    _, warnings, _ = planner.build_plan_items(files, llm)
    assert not any("thành phần hồ sơ chính" in w for w in warnings)


def test_giay_cam_ket_khong_thay_duoc_giay_uy_quyen():
    """Đúng tình huống hồ sơ mẫu: có giấy cam kết nhưng bản uỷ quyền không được scan kèm."""
    files = _files(["04_cam_ket.pdf"])
    _, warnings, _ = planner.build_plan_items(files, {0: "giay_cam_ket_chu_ky"})
    assert any("không thay được văn bản về việc đại diện" in w for w in warnings)


def test_co_du_ca_hai_thi_khong_nhac_uy_quyen():
    files = _files(["04_cam_ket.pdf", "05_uy_quyen.pdf"])
    llm = {0: "giay_cam_ket_chu_ky", 1: "van_ban_dai_dien"}
    _, warnings, _ = planner.build_plan_items(files, llm)
    assert not any("không thay được văn bản về việc đại diện" in w for w in warnings)


def test_khong_co_tai_lieu_thi_bao_ro():
    attachments, warnings, _ = planner.build_plan_items([], {})
    assert not attachments
    assert any("Không có tài liệu nào để đính kèm" in w for w in warnings)


def test_tran_6mb_tinh_cho_tung_tep():
    """Mỗi tệp một dòng nên trần 6 MB của cổng là trần của từng tệp."""
    assert planner._MAX_FILE_BYTES == 6 * 1024 * 1024
    du_6mb = "data:application/pdf;base64," + "A" * (7 * 1024 * 1024 * 4 // 3)
    assert planner._data_url_size(du_6mb) > planner._MAX_FILE_BYTES


# --------------------------------------------------------------------------- extension
def test_popup_thu_thap_moc_tai_khoan_cho_thu_tuc_nay():
    """Thiếu formContext thì mapper phải đoán mode từ giấy tờ — mất chỗ dựa duy nhất."""
    popup = Path("../auto-fill-hcc-extension/popup.js").read_text(encoding="utf-8")
    assert f'cfg.key === "{_KEY}"' in popup
