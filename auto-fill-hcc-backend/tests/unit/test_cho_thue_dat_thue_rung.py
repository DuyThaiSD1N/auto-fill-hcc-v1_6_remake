"""[Lào Cai] Giao đất/cho thuê đất, giao rừng/cho thuê rừng — mã 1.115678 (Điều 3 QĐ 40/2026).

Khoá bốn điều dễ vỡ, đều là chỗ đã sai hoặc suýt sai khi dựng pipeline này:
  1. Nhận diện KHÔNG được cướp trang của thủ tục 1.115650 và ngược lại — hai tiêu đề lồng nhau.
  2. Thứ tự dòng đính kèm KHÁC 1.115650 (Điều 133 lên slot 3, miễn giảm xuống slot 9).
  3. Cả bộ giấy tờ trúng đấu giá phải gộp vào dòng Đơn (slot 0), không rơi xuống "giấy tờ khác".
  4. Hai mode người nộp: nộp thay theo ủy quyền thì TUYỆT ĐỐI không chép nhân thân chéo hai khối.
"""

from app.pipelines.cho_thue_dat_thue_rung.attach import planner
from app.pipelines.cho_thue_dat_thue_rung.process import mapper
from app.pipelines.cho_thue_dat_thue_rung.process.schema import (
    INDIVIDUAL_ONLY_FIELDS,
    ORG_ONLY_FIELDS,
    UI_COMP_BY_NAME,
)
from app.pipelines.giao_thue_dat_lao_cai.attach import planner as planner_1_115650
from app.procedures.registry import public_list

_KEY = "cho-thue-dat-thue-rung"
_KEY_KHONG_DAU_GIA = "giao-thue-dat-lao-cai"

# HS1 của file mapping: ông Nguyễn Quốc Tuấn trúng đấu giá, bà Bùi Thị Như Hoa nộp thay theo ủy quyền.
_HS1_UY_QUYEN = [
    {"name": "ChuHoSo_HoTen", "value": "NGUYỄN QUỐC TUẤN"},
    {"name": "ChuHoSo_NgaySinh", "value": "21/07/1996"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "010096000466"},
    {"name": "ChuHoSo_NgayCap", "value": "13/04/2021"},
    {"name": "ChuHoSo_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "ChuHoSo_DienThoai", "value": "0898911996"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Xã Bảo Nhai", "diaChi": "Thôn Nậm Khắp Ngoài"}},
    {"name": "NguoiNop_HoTen", "value": "BÙI THỊ NHƯ HOA"},
    {"name": "NguoiNop_NgaySinh", "value": "20/08/1972"},
    {"name": "NguoiNop_SoDinhDanh", "value": "015172006500"},
    {"name": "NguoiNop_NgayCap", "value": "13/01/2025"},
    {"name": "NguoiNop_NoiCap", "value": "Bộ Công an"},
    {"name": "NguoiNop_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Phường Trung Tâm", "diaChi": "Tổ dân phố Nghĩa Lợi"}},
]

# HS2 của file mapping: bà Nguyễn Thị Bích Liên tự nộp, hồ sơ chỉ khai một lần ở khối chủ hồ sơ.
_HS2_TU_NOP = [
    {"name": "ChuHoSo_HoTen", "value": "NGUYỄN THỊ BÍCH LIÊN"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "010174000311"},
    {"name": "ChuHoSo_NgayCap", "value": "10/04/2021"},
    {"name": "ChuHoSo_NoiCap", "value": "Cục Cảnh sát quản lý hành chính về trật tự xã hội"},
    {"name": "ChuHoSo_DienThoai", "value": "0866622867"},
    {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Phường Lào Cai", "diaChi": "Tổ 14 Cốc Lếu"}},
]


def _entry(key=_KEY):
    return next(p for p in public_list() if p["key"] == key)


def _names(fields):
    return {f["name"]: f["value"] for f in fields}


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

_TIEU_DE_CHUNG = (
    "Giao đất, cho thuê đất đối với trường hợp giao đất, cho thuê đất không đấu giá quyền sử dụng "
    "đất, không đấu thầu lựa chọn nhà đầu tư thực hiện dự án có sử dụng đất và trường hợp giao đất, "
    "cho thuê đất thông qua đấu thầu lựa chọn nhà đầu tư thực hiện dự án có sử dụng đất; giao đất và "
    "giao rừng; cho thuê đất và cho thuê rừng"
)


def test_trang_1_115678_nhan_dung_thu_tuc_nay():
    body = (
        f"{_TIEU_DE_CHUNG} (đối với các trường hợp quy định tại Điều 3 Quyết định số 40/2026/QĐ-UBND "
        "ngày 31/5/2026 của UBND tỉnh Lào Cai)."
    )
    assert _detect(_URL_LAO_CAI, body) == _KEY


def test_trang_1_115650_khong_bi_thu_tuc_moi_cuop_mat():
    """Tiêu đề 1.115650 là CHUỖI CON của tiêu đề thủ tục này — chiều ngược lại phải vẫn đúng."""
    assert _detect(_URL_LAO_CAI, _TIEU_DE_CHUNG) == _KEY_KHONG_DAU_GIA


def test_cum_rieng_khong_dinh_toi_phan_qd_ubnd_de_vo():
    """Cổng có chỗ in "QĐ- UBND" (thừa dấu cách) — khai tới đó là tự làm hỏng nhận diện."""
    phrases = _entry()["detect"]["textIncludes"]
    rieng = [p for p in phrases if "40/2026" in p]
    assert rieng and all("UBND" not in p for p in rieng)


def test_diem_nhan_dien_phai_cao_hon_thu_tuc_1_115650():
    """textPriority chọn entry có TỔNG ĐỘ DÀI CỤM lớn nhất → phải khai lại cả cụm dùng chung."""
    def score(key):
        return sum(len(p) for p in _entry(key)["detect"]["textIncludes"])

    assert score(_KEY) > score(_KEY_KHONG_DAU_GIA)


# ------------------------------------------------ hai ô readonly: không bao giờ được phát
def test_khong_bao_gio_phat_hai_o_readonly_cua_tai_khoan():
    """Ghi vào 2 ô này là script cổng XOÁ TRẮNG "Di động" + "Số Căn cước" vừa điền xong."""
    assert "CongDan_tenCongDan" not in UI_COMP_BY_NAME
    assert "CongDan_soCmnd" not in UI_COMP_BY_NAME

    for payload in (_HS1_UY_QUYEN, _HS2_TU_NOP):
        by_name = _names(mapper.enrich(payload)[0])
        assert "CongDan_tenCongDan" not in by_name
        assert "CongDan_soCmnd" not in by_name


def _ctx(fullname: str, identity: str) -> dict:
    """options như popup gửi lên: nhân thân tài khoản định danh đang đăng nhập."""
    return {"formContext": {"applicantFullname": fullname, "applicantIdentityNumber": identity}}


# ------------------------------------------------------------------- mode A: nộp thay theo ủy quyền
def test_uy_quyen_giu_nguyen_hai_nguoi_khac_nhau():
    """Tài khoản đăng nhập là bà Hoa (người được ủy quyền) → hai khối phải tách bạch."""
    fields, _ = mapper.enrich(_HS1_UY_QUYEN, _ctx("BÙI THỊ NHƯ HOA", "015172006500"))
    by_name = _names(fields)

    assert by_name["ChuHoSo_tenChuHoSo"] == "NGUYỄN QUỐC TUẤN"
    assert by_name["ChuHoSo_soCMNDChuHoSo"] == "010096000466"
    # Địa chỉ hai khối là hai nơi khác nhau, không được lẫn.
    assert by_name["CongDan_maPhuongXa"] == "Phường Trung Tâm"
    assert by_name["ChuHoSo_maPhuongXaCHS"] == "Xã Bảo Nhai"


def test_uy_quyen_khong_muon_so_dien_thoai_cua_chu_ho_so():
    """Hợp đồng ủy quyền không ghi SĐT bên B — mượn số của chủ hồ sơ là gán sai liên hệ."""
    fields, warnings = mapper.enrich(_HS1_UY_QUYEN, _ctx("BÙI THỊ NHƯ HOA", "015172006500"))
    by_name = _names(fields)

    assert "CongDan_diDong" not in by_name
    assert by_name["ChuHoSo_diDongLienLacCHS"] == "0898911996"
    assert any("hỏi trực tiếp người nộp" in w for w in warnings)


def test_uy_quyen_canh_bao_o_readonly_va_cam_tick_checkbox():
    _, warnings = mapper.enrich(_HS1_UY_QUYEN, _ctx("BÙI THỊ NHƯ HOA", "015172006500"))
    assert any("READONLY" in w for w in warnings)
    assert any("không tick" in w.lower() for w in warnings)


# --------------------------------------------------- mốc tài khoản quyết định mode, không phải giấy tờ
def test_moc_tai_khoan_chot_mode_tu_nop_du_ho_so_co_uy_quyen():
    """Chính người trúng đấu giá đăng nhập → là người đi nộp thật, dù hồ sơ có kèm ủy quyền."""
    fields, warnings = mapper.enrich(_HS1_UY_QUYEN, _ctx("NGUYỄN QUỐC TUẤN", "010096000466"))
    by_name = _names(fields)

    # Cùng một người nên được bổ khuyết chéo: SĐT của ông Tuấn dùng cho cả khối người nộp.
    assert by_name["CongDan_diDong"] == "0898911996"
    assert any("trùng chủ hồ sơ" in w for w in warnings)


def test_canh_bao_khi_tai_khoan_dang_nhap_khong_phai_nguoi_duoc_uy_quyen():
    """Ca thật hay gặp: người thứ ba đăng nhập tài khoản của mình rồi nộp hộ."""
    _, warnings = mapper.enrich(_HS1_UY_QUYEN, _ctx("TRẦN VĂN C", "011122233344"))

    assert any("KHÔNG phải người được ủy quyền" in w for w in warnings)


def test_khong_co_moc_tai_khoan_thi_noi_ro_la_suy_doan():
    _, warnings = mapper.enrich(_HS1_UY_QUYEN)
    assert any("chỉ là suy đoán từ giấy tờ" in w for w in warnings)


def test_co_moc_tai_khoan_thi_khong_con_canh_bao_suy_doan():
    _, warnings = mapper.enrich(_HS2_TU_NOP, _ctx("NGUYỄN THỊ BÍCH LIÊN", "010174000311"))
    assert not any("suy đoán từ giấy tờ" in w for w in warnings)


# ------------------------------------------------------------------------------ mode B: tự nộp
def test_tu_nop_bo_khuyet_khoi_nguoi_nop_tu_chu_ho_so():
    """Hồ sơ chỉ khai một lần; cùng một người nên chép sang khối người nộp là an toàn."""
    fields, _ = mapper.enrich(_HS2_TU_NOP)
    by_name = _names(fields)

    assert by_name["CongDan_diDong"] == "0866622867"
    assert by_name["CongDan_ngayCapCmnd"] == "10/04/2021"
    assert by_name["CongDan_maTinhThanh"] == "Tỉnh Lào Cai"
    assert by_name["CongDan_maPhuongXa"] == "Phường Lào Cai"
    assert by_name["CongDan_diaChi"] == "Tổ 14 Cốc Lếu"


def test_tu_nop_van_phat_du_ba_o_dia_chi_khoi_chu_ho_so():
    """Checkbox "Người nộp là chủ hồ sơ" của cổng KHÔNG copy địa chỉ → phải tự phát."""
    fields, _ = mapper.enrich(_HS2_TU_NOP)
    by_name = _names(fields)

    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    assert by_name["ChuHoSo_maPhuongXaCHS"] == "Phường Lào Cai"
    assert by_name["ChuHoSo_diaChiChuHoSo"] == "Tổ 14 Cốc Lếu"


def test_khong_doi_chieu_duoc_thi_ngac_ve_hai_nguoi_khac_nhau():
    """Người nộp có tên riêng nhưng thiếu vế kia để so → KHÔNG được chép nhân thân chủ hồ sơ sang.

    Ngả về "khác" là phía an toàn: cùng lắm bỏ trống vài ô cho cán bộ nhập tay, còn ngả nhầm sang
    "trùng" là gán nhân thân người này cho người kia.
    """
    fields, _ = mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN QUỐC TUẤN"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "010096000466"},
        {"name": "ChuHoSo_DienThoai", "value": "0898911996"},
        {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Xã Bảo Nhai", "diaChi": "Thôn Nậm Khắp Ngoài"}},
        {"name": "NguoiNop_HoTen", "value": "BÙI THỊ NHƯ HOA"},
    ])
    by_name = _names(fields)

    # Không chép SĐT lẫn địa chỉ của chủ hồ sơ sang khối người nộp.
    assert "CongDan_diDong" not in by_name
    assert "CongDan_maPhuongXa" not in by_name
    assert by_name["ChuHoSo_diDongLienLacCHS"] == "0898911996"


def test_khong_phat_checkbox_nguoi_nop_la_chu_ho_so():
    assert "chkbox_nguoinoplachuhs" not in UI_COMP_BY_NAME
    fields, _ = mapper.enrich(_HS2_TU_NOP)
    assert "chkbox_nguoinoplachuhs" not in _names(fields)


def test_khong_phat_truong_an_cua_cong():
    for hidden in ("CongDan_maDMDiaChi", "local_file", "local_file_xuly", "AN_FORM_CHS", "tokenCsrf"):
        assert hidden not in UI_COMP_BY_NAME, hidden


# ---------------------------------------------------------------------------- cá nhân vs tổ chức
def test_ho_so_ca_nhan_khong_phat_o_bi_an_cua_khoi_to_chuc():
    fields, _ = mapper.enrich(_HS2_TU_NOP)
    by_name = _names(fields)

    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "Cá nhân"
    for name in ORG_ONLY_FIELDS:
        assert name not in by_name, name


def test_ho_so_to_chuc_khong_phat_o_nhan_than_ca_nhan_dang_bi_an():
    fields, _ = mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_LaToChuc", "value": True},
        {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY TNHH MỘT THÀNH VIÊN X"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300123456-001"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "012345678901"},
        {"name": "ChuHoSo_NoiCuTru", "value": {"tinh": "Lào Cai", "xa": "Phường Cam Đường", "diaChi": "Số 1 đường A"}},
    ])
    by_name = _names(fields)

    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "Tổ chức"
    assert by_name["ChuHoSo_tenCoQuanToChucCHS"] == "CÔNG TY TNHH MỘT THÀNH VIÊN X"
    # Mã số thuế giữ đuôi đơn vị phụ thuộc.
    assert by_name["ChuHoSo_maSoThueChuHoSo"] == "5300123456-001"
    for name in INDIVIDUAL_ONLY_FIELDS:
        assert name not in by_name, name


def test_to_chuc_nop_thay_thi_khoi_nguoi_nop_khong_mang_ten_cong_ty():
    """Bên được ủy quyền là CÁ NHÂN — điền tên/MST công ty vào khối người nộp là sai người."""
    fields, _ = mapper.enrich([
        {"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"},
        {"name": "ChuHoSo_LaToChuc", "value": True},
        {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY TNHH MỘT THÀNH VIÊN X"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300123456"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "012345678901"},
        {"name": "NguoiNop_HoTen", "value": "TRẦN THỊ B"},
        {"name": "NguoiNop_SoDinhDanh", "value": "098765432109"},
    ])
    by_name = _names(fields)

    assert "CongDan_tenCoQuanToChuc" not in by_name
    assert "CongDan_maSoThueNguoiNop" not in by_name


def test_ho_so_ca_nhan_khong_bia_to_chuc():
    fields, _ = mapper.enrich(_HS2_TU_NOP)
    assert "ChuHoSo_tenCoQuanToChucCHS" not in _names(fields)


def test_khong_bia_ngay_thang_khi_chi_co_nam():
    """HS2 chỉ có "Sinh năm 1974" — ghép 01/01 là bịa nhân thân."""
    fields, _ = mapper.enrich(_HS2_TU_NOP + [{"name": "ChuHoSo_NgaySinh", "value": "1974"}])
    assert "ChuHoSo_ngaySinhChuHoSo" not in _names(fields)


def test_khong_doc_duoc_dia_chi_thi_canh_bao_thay_vi_im_lang():
    fields, warnings = mapper.enrich([{"name": "ChuHoSo_HoTen", "value": "NGUYỄN VĂN A"}])

    assert "ChuHoSo_maTinhThanhCHS" not in _names(fields)
    assert any("KHÔNG sao chép" in w for w in warnings)


# ------------------------------------------------------------------------------------ đính kèm
def test_thu_tu_10_dong_dung_theo_danh_muc_cua_thu_tuc_nay():
    """10 dòng đầu = 10 dòng thành phần hồ sơ; 4 ô "giấy tờ khác" nối ngay sau."""
    assert planner._ROUTES["don_mau_01"]["slotIndex"] == 0
    assert planner._ROUTES["van_ban_chu_truong_dau_tu"]["slotIndex"] == 1
    assert planner._ROUTES["van_ban_dau_gia_khong_thanh"]["slotIndex"] == 2
    assert planner._ROUTES["van_ban_dieu_133"]["slotIndex"] == 3
    assert planner._ROUTES["phuong_an_sdd_dieu_180"]["slotIndex"] == 4
    assert planner._ROUTES["phuong_an_sdd_nong_lam_181"]["slotIndex"] == 5
    assert planner._ROUTES["phuong_an_sdd_dat_thu_hoi"]["slotIndex"] == 6
    assert planner._ROUTES["giay_phep_khoang_san"]["slotIndex"] == 7
    assert planner._ROUTES["ho_so_rung"]["slotIndex"] == 8
    assert planner._ROUTES["giay_to_mien_giam"]["slotIndex"] == 9
    assert planner._OTHER_SLOT_INDEX == 10
    assert planner._OTHER_SLOT_INDEX + planner._OTHER_SLOT_COUNT == 14


def test_thu_tu_dong_KHAC_thu_tuc_1_115650():
    """Chốt bằng test để không ai "dọn trùng lặp" bằng cách dùng chung bảng của 1.115650."""
    cu = planner_1_115650._ROUTES
    assert cu["van_ban_dieu_133"]["slotIndex"] == 9
    assert planner._ROUTES["van_ban_dieu_133"]["slotIndex"] == 3
    assert cu["giay_to_mien_giam"]["slotIndex"] == 8
    assert planner._ROUTES["giay_to_mien_giam"]["slotIndex"] == 9


def test_bo_giay_to_trung_dau_gia_gop_vao_dong_don():
    names = ["don.pdf", "qd301.pdf", "bb_dau_gia.pdf", "gnt.pdf", "tb_thue.pdf", "hd_uy_quyen.pdf", "cccd.pdf"]
    items, warnings, _ = planner.build_plan_items(
        _files(names),
        {
            0: "don_mau_01",
            1: "quyet_dinh_trung_dau_gia",
            2: "bien_ban_dau_gia",
            3: "chung_tu_nop_tien",
            4: "thong_bao_thue",
            5: "hop_dong_uy_quyen",
            6: "giay_to_tuy_than",
        },
    )

    # TẤT CẢ vào dòng Đơn — danh mục cổng không có dòng riêng cho bộ giấy tờ trúng đấu giá.
    assert {i["slotIndex"] for i in items} == {0}
    assert all(i["target"] == "fixed-slot" for i in items)
    # Nhưng mỗi tệp vẫn giữ TÊN LOẠI riêng để cán bộ đối chiếu, không bị gộp nhãn thành "Đơn".
    by_file = {i["fileName"]: i["documentName"] for i in items}
    assert "trúng đấu giá" in by_file["qd301.pdf"]
    assert "ủy quyền" in by_file["hd_uy_quyen.pdf"]
    assert any("gộp chung vào dòng" in w for w in warnings)


def test_giay_to_du_an_van_di_dung_dong_rieng():
    items, _, _ = planner.build_plan_items(
        _files(["cttdt.pdf", "pa180.pdf", "rung.pdf", "mien_giam.pdf"]),
        {
            0: "van_ban_chu_truong_dau_tu",
            1: "phuong_an_sdd_dieu_180",
            2: "ho_so_rung",
            3: "giay_to_mien_giam",
        },
    )
    assert [i["slotIndex"] for i in items] == [1, 4, 8, 9]


def test_nhieu_tai_lieu_la_trai_deu_qua_cac_o_giay_to_khac():
    items, _, _ = planner.build_plan_items(_files([f"la{i}.pdf" for i in range(6)]), {})

    # 4 ô "giấy tờ khác" (10..13), file thứ 5 trở đi dồn vào ô cuối.
    assert [i["slotIndex"] for i in items] == [10, 11, 12, 13, 13, 13]
    # Giữ TÊN THẬT theo tệp để cán bộ biết là giấy gì.
    assert items[0]["documentName"].startswith("la0")


def test_khong_bo_sot_file_nao_khi_llm_chet():
    items, warnings, classified = planner.build_plan_items(_files(["a.pdf", "b.pdf"]), {})

    assert [i["fileIndex"] for i in items] == [0, 1]
    assert warnings
    assert all(c["source"] == "default" for c in classified)


def test_canh_bao_khi_mot_dong_vuot_tran_6mb_cua_cong():
    """Cổng chỉ báo lỗi lúc bấm nộp; cả bộ trúng đấu giá dồn vào dòng Đơn nên rất hay vượt."""
    import base64

    big = "data:application/pdf;base64," + base64.b64encode(b"x" * (4 * 1024 * 1024)).decode()
    files = [
        {"name": "don.pdf", "type": "application/pdf", "dataUrl": big},
        {"name": "qd301.pdf", "type": "application/pdf", "dataUrl": big},
    ]
    _, warnings, _ = planner.build_plan_items(files, {0: "don_mau_01", 1: "quyet_dinh_trung_dau_gia"})

    assert any("vượt giới hạn 6 MB" in w for w in warnings)


def test_khong_canh_bao_dung_luong_khi_con_duoi_tran():
    import base64

    small = "data:application/pdf;base64," + base64.b64encode(b"x" * 1024).decode()
    files = [{"name": "don.pdf", "type": "application/pdf", "dataUrl": small}]
    _, warnings, _ = planner.build_plan_items(files, {0: "don_mau_01"})

    assert not any("6 MB" in w for w in warnings)


def test_slot_key_khong_trung_keyword_cua_extension():
    """slotKey cố ý KHÔNG có trong FIXED_SLOT_KEYWORDS → FE dùng thẳng slotIndex."""
    from pathlib import Path

    content = (
        Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "content.js"
    )
    if not content.exists():
        return
    block = content.read_text(encoding="utf-8").split("FIXED_SLOT_KEYWORDS = {", 1)[1].split("};", 1)[0]
    for doc_type in planner._ROUTES:
        assert f"laocai_ctdtr_{doc_type}:" not in block, doc_type


def test_prompt_co_bay_phan_biet_phai_nop_va_da_nop():
    from app.pipelines.cho_thue_dat_thue_rung.attach.prompt import SYSTEM_PROMPT

    assert "PHÂN BIỆT \"PHẢI NỘP\" VỚI \"ĐÃ NỘP\"" in SYSTEM_PROMPT
    assert "ĐẤU GIÁ THÀNH ≠ ĐẤU GIÁ KHÔNG THÀNH" in SYSTEM_PROMPT
    assert "DANH SÁCH KÈM THEO ĂN THEO VĂN BẢN CHÍNH" in SYSTEM_PROMPT
    assert "TUYỆT ĐỐI KHÔNG BỎ SÓT" in SYSTEM_PROMPT


def test_prompt_process_canh_bao_ma_so_thue_ca_nhan_la_so_dinh_danh():
    from app.pipelines.cho_thue_dat_thue_rung.process.prompt import EXTRA_RULES

    assert "CHÍNH LÀ số định danh cá nhân" in EXTRA_RULES
    assert "ĐỪNG LẪN ĐỊA CHỈ THỬA ĐẤT VỚI NƠI CƯ TRÚ" in EXTRA_RULES
