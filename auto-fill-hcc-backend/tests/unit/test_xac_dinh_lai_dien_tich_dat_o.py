"""[Lào Cai] Xác định lại diện tích đất ở (GCN cấp trước 01/7/2004) — mã 1.115685.

Khoá sáu điều dễ vỡ:
  1. Nhận diện KHÔNG được cướp trang của bản Quảng Ngãi (tên thủ tục TRÙNG KHÍT) và ngược lại.
  2. Đính kèm là bảng PHẲNG 3 dòng; dòng Đơn phải nhận ĐƯỢC NHIỀU TỆP (bản ký số + bản chưa ký).
  3. Hai ô readonly CongDan_tenCongDan/CongDan_soCmnd KHÔNG BAO GIỜ được phát.
  4. Hai mode người nộp: nộp thay thì TUYỆT ĐỐI không chép nhân thân chéo hai khối.
  5. Giấy chứng nhận cấp TỪ 01/7/2004 trở đi phải bị cảnh báo (sai điều kiện áp dụng của thủ tục).
  6. Đơn dùng mẫu khác Mẫu số 24 cổng đang treo phải được nói ra, KHÔNG sửa lén.
"""

from app.pipelines.xac_dinh_lai_dien_tich_dat_o.attach import planner
from app.pipelines.xac_dinh_lai_dien_tich_dat_o.process import mapper
from app.pipelines.xac_dinh_lai_dien_tich_dat_o.process.schema import (
    INDIVIDUAL_ONLY_FIELDS,
    ORG_ONLY_FIELDS,
    UI_COMP_BY_NAME,
)
from app.procedures.registry import public_list

_KEY = "xac-dinh-lai-dien-tich-dat-o-truoc-01-7-2004"
_KEY_QUANG_NGAI = "xac-dinh-lai-dien-tich-dat-o-quang-ngai"

# Hồ sơ mẫu 2 của file mapping: ông Mai Xuân Hải TỰ ĐỨNG ĐƠN, tổ dân phố Sa Pa 4, phường Sa Pa.
_HS_TU_NOP = [
    {"name": "ChuHoSo_HoTen", "value": "MAI XUÂN HẢI"},
    {"name": "ChuHoSo_NgaySinh", "value": "10/9/1975"},
    {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "010075000950"},
    {"name": "ChuHoSo_NgayCap", "value": "25/4/2021"},
    {"name": "ChuHoSo_NoiCap", "value": "cục CSQLHCTTXH"},
    {"name": "ChuHoSo_DienThoai", "value": "0915352955"},
    {"name": "ChuHoSo_NoiCuTru",
     "value": {"tinh": "Lào Cai", "xa": "Phường Sa Pa", "diaChi": "Tổ dân phố Sa Pa 4"}},
    {"name": "Don_KinhGui", "value": "Ủy ban nhân dân phường Sa Pa"},
    {"name": "Don_MauSo", "value": "Mẫu số 18"},
    {"name": "Don_NgayKy", "value": "11/11/2025"},
    {"name": "Don_NoiDungBienDong",
     "value": "Xác định lại diện tích đất ở của hộ gia đình, cá nhân đã được cấp Giấy chứng nhận "
              "trước ngày 01 tháng 7 năm 2004"},
]

# Hồ sơ mẫu 1: ông Đỗ Trọng Thanh, có Giấy chứng nhận A 131603 và Bản án 36/2024/HC-ST, nộp thay
# theo văn bản đại diện (biến thể dựng để khoá mode A).
_HS_UY_QUYEN = [
    {"name": "ChuHoSo_HoTen", "value": "ĐỖ TRỌNG THANH"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "010082001171"},
    {"name": "ChuHoSo_NoiCuTru",
     "value": {"tinh": "Lào Cai", "xa": "Phường Sa Pa", "diaChi": "Số nhà 547, đường Điện Biên Phủ"}},
    {"name": "ChuHoSo_DienThoai", "value": "0975778866"},
    {"name": "NguoiNop_HoTen", "value": "Nguyễn Thị Lan"},
    {"name": "NguoiNop_SoDinhDanh", "value": "010180004321"},
    {"name": "NguoiNop_NoiCuTru",
     "value": {"tinh": "Lào Cai", "xa": "Phường Cam Đường", "diaChi": "Tổ 12"}},
    {"name": "UyQuyen_SoGiay", "value": "0123"},
    {"name": "Gcn_SoPhatHanh", "value": "A 131603"},
    {"name": "Gcn_SoVaoSo", "value": "00003 QSDĐ"},
    {"name": "BanAn_SoHieu", "value": "36/2024/HC-ST"},
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
    # Cổng iGate, sid đổi mỗi phiên → không được khóa bằng urlIncludes.
    assert "urlIncludes" not in entry["detect"]


def test_co_pipeline_process_va_attach():
    from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE

    assert _KEY in _PIPELINE
    assert _KEY in _ATTACH_PIPELINE


def test_key_trung_voi_muc_ke_khai_links_1_115685():
    """Key phải trùng mục ke_khai_links thì chọn link kê khai mới ra đúng pipeline điền."""
    from app.procedures.ke_khai_links import _load

    muc = next(i for i in _load() if i["key"] == _KEY)
    assert muc["code"] == "1.115685"


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
_URL_QUANG_NGAI = "https://dichvucong.quangngai.gov.vn/vi/padsvc/apply-online/653f1a"

_TIEU_DE = (
    "Xác định lại diện tích đất ở của hộ gia đình, cá nhân đã được cấp Giấy chứng nhận trước ngày "
    "01 tháng 7 năm 2004"
)


def test_trang_lao_cai_nhan_dung_thu_tuc_nay():
    assert _detect(_URL_LAO_CAI, _TIEU_DE) == _KEY


def test_trang_quang_ngai_khong_bi_thu_tuc_moi_cuop_mat():
    """Tên thủ tục TRÙNG KHÍT hai tỉnh — urlScope là thứ duy nhất tách được, phải kiểm cả hai chiều."""
    assert _detect(_URL_QUANG_NGAI, _TIEU_DE) == _KEY_QUANG_NGAI


def test_khong_khai_text_priority_de_khong_dam_nhanh_uu_tien_cua_quang_ngai():
    assert not _entry()["detect"].get("textPriority")
    assert _entry(_KEY_QUANG_NGAI)["detect"].get("textPriority")


def test_khong_an_theo_chu_hoa():
    """Hàm chuẩn hoá của popup.js đã hạ chữ thường — cụm khai phải là bản thường."""
    phrases = _entry()["detect"]["textIncludes"]
    assert all(p == p.lower() for p in phrases)


# ------------------------------------------------ hai ô readonly: không bao giờ được phát
def test_khong_bao_gio_phat_hai_o_readonly_cua_tai_khoan():
    """Ghi vào 2 ô này là script cổng XOÁ TRẮNG "Di động" + "Số Căn cước" vừa điền xong."""
    assert "CongDan_tenCongDan" not in UI_COMP_BY_NAME
    assert "CongDan_soCmnd" not in UI_COMP_BY_NAME

    for payload, ctx in (
        (_HS_TU_NOP, _ctx("MAI XUÂN HẢI", "010075000950")),
        (_HS_UY_QUYEN, _ctx("Nguyễn Thị Lan", "010180004321")),
    ):
        by_name = _names(mapper.enrich(payload, ctx)[0])
        assert "CongDan_tenCongDan" not in by_name
        assert "CongDan_soCmnd" not in by_name


def test_khong_phat_o_bi_cong_an_theo_doi_tuong():
    """Hồ sơ cá nhân thì 2 ô tổ chức display:none — phát vào đó chỉ làm engine báo lỗi vô cớ."""
    by_name = _names(mapper.enrich(_HS_TU_NOP, _ctx("MAI XUÂN HẢI", "010075000950"))[0])
    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "Cá nhân"
    assert not (ORG_ONLY_FIELDS & set(by_name))

    to_chuc = [
        {"name": "ChuHoSo_LaToChuc", "value": True},
        {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY TNHH ABC"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300123456"},
        {"name": "ChuHoSo_HoTen", "value": "Mai Xuân Hải"},
    ]
    fields, warnings = mapper.enrich(to_chuc)
    by_name = _names(fields)
    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "Tổ chức"
    assert not (INDIVIDUAL_ONLY_FIELDS & set(by_name))
    # Thủ tục chỉ dành cho hộ gia đình/cá nhân → hồ sơ tổ chức phải được nhắc.
    assert any("HỘ GIA ĐÌNH, CÁ NHÂN" in w for w in warnings)


# ------------------------------------------------------------------- mode B: tự nộp (mặc định)
def test_tu_nop_dien_du_ca_hai_khoi():
    fields, warnings = mapper.enrich(_HS_TU_NOP, _ctx("MAI XUÂN HẢI", "010075000950"))
    by_name = _names(fields)

    assert by_name["ChuHoSo_tenChuHoSo"] == "MAI XUÂN HẢI"
    assert by_name["ChuHoSo_soCMNDChuHoSo"] == "010075000950"
    assert by_name["ChuHoSo_ngaySinhChuHoSo"] == "10/09/1975"
    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Lào Cai"
    assert by_name["ChuHoSo_maPhuongXaCHS"] == "Phường Sa Pa"
    assert by_name["ChuHoSo_diaChiChuHoSo"] == "Tổ dân phố Sa Pa 4"
    # Khối người nộp là chính người đó → phải được điền đủ, kể cả 3 ô địa chỉ checkbox không copy.
    assert by_name["CongDan_ngaySinhCongDan"] == "10/09/1975"
    assert by_name["CongDan_diDong"] == "0915352955"
    assert by_name["CongDan_maTinhThanh"] == "Tỉnh Lào Cai"
    assert by_name["CongDan_maPhuongXa"] == "Phường Sa Pa"
    assert any("trùng chủ hồ sơ" in w for w in warnings)


def test_tu_nop_chuan_hoa_noi_cap_can_cuoc():
    by_name = _names(mapper.enrich(_HS_TU_NOP, _ctx("MAI XUÂN HẢI", "010075000950"))[0])
    assert "Cục Cảnh sát quản lý hành chính" in by_name["ChuHoSo_noiCapCMNDCHS"]


def test_khong_phat_khoi_nguoi_nop_khi_khong_doc_duoc_tai_khoan():
    """Không có mốc tài khoản → để trống khối người nộp, không mượn nhân thân chủ hồ sơ."""
    fields, warnings = mapper.enrich(_HS_TU_NOP)
    by_name = _names(fields)

    assert not [n for n in by_name if n.startswith("CongDan_")]
    assert by_name["ChuHoSo_tenChuHoSo"] == "MAI XUÂN HẢI"
    assert any("Chưa đọc được tài khoản định danh" in w for w in warnings)


def test_tai_khoan_khong_khop_ho_so_thi_bo_trong_khoi_nguoi_nop():
    fields, warnings = mapper.enrich(_HS_TU_NOP, _ctx("Trần Văn B", "010099009900"))
    by_name = _names(fields)

    assert not [n for n in by_name if n.startswith("CongDan_")]
    assert any("KHÔNG có giấy tờ tuỳ thân của người đang đăng nhập" in w for w in warnings)


# ------------------------------------------------------------------- mode A: nộp thay theo ủy quyền
def test_uy_quyen_giu_nguyen_hai_nguoi_khac_nhau():
    fields, warnings = mapper.enrich(_HS_UY_QUYEN, _ctx("Nguyễn Thị Lan", "010180004321"))
    by_name = _names(fields)

    assert by_name["ChuHoSo_tenChuHoSo"] == "ĐỖ TRỌNG THANH"
    assert by_name["ChuHoSo_soCMNDChuHoSo"] == "010082001171"
    # Hai khối cùng tỉnh nhưng KHÁC phường — không được lẫn.
    assert by_name["CongDan_maPhuongXa"] == "Phường Cam Đường"
    assert by_name["ChuHoSo_maPhuongXaCHS"] == "Phường Sa Pa"
    assert any("nộp thay" in w for w in warnings)
    assert any("READONLY" in w for w in warnings)
    assert any("không tick" in w.lower() for w in warnings)


def test_uy_quyen_khong_muon_so_dien_thoai_cua_chu_ho_so():
    fields, warnings = mapper.enrich(_HS_UY_QUYEN, _ctx("Nguyễn Thị Lan", "010180004321"))
    by_name = _names(fields)

    assert "CongDan_diDong" not in by_name
    assert by_name["ChuHoSo_diDongLienLacCHS"] == "0975778866"
    assert any("hỏi trực tiếp người nộp" in w for w in warnings)


# --------------------------------------------------------------- điều kiện riêng của 1.115685
def test_canh_bao_gcn_cap_tu_01_7_2004_tro_di():
    payload = _HS_TU_NOP + [{"name": "Gcn_NgayCap", "value": "15/8/2019"}]
    _, warnings = mapper.enrich(payload, _ctx("MAI XUÂN HẢI", "010075000950"))
    assert any("TRƯỚC ngày 01/7/2004" in w for w in warnings)


def test_gcn_cap_truoc_moc_thi_khong_canh_bao():
    payload = _HS_TU_NOP + [{"name": "Gcn_NgayCap", "value": "20/3/1999"}]
    _, warnings = mapper.enrich(payload, _ctx("MAI XUÂN HẢI", "010075000950"))
    assert not any("TRƯỚC ngày 01/7/2004" in w for w in warnings)


def test_canh_bao_don_khong_dung_mau_so_24():
    """Hồ sơ mẫu dùng Mẫu số 18 trong khi cổng treo Mẫu số 24 — nói ra, KHÔNG sửa lén."""
    _, warnings = mapper.enrich(_HS_TU_NOP, _ctx("MAI XUÂN HẢI", "010075000950"))
    assert any("Mẫu số 24" in w for w in warnings)

    dung_mau = [f for f in _HS_TU_NOP if f["name"] != "Don_MauSo"]
    dung_mau = dung_mau + [{"name": "Don_MauSo", "value": "Mẫu số 24"}]
    _, warnings = mapper.enrich(dung_mau, _ctx("MAI XUÂN HẢI", "010075000950"))
    assert not any("Mẫu số 24" in w for w in warnings)


def test_khong_canh_bao_trung_dia_chi_thua_dat():
    """Ngược 1.115693: ở đây người dân ở ngay trên thửa đất nên trùng địa chỉ là BÌNH THƯỜNG."""
    payload = _HS_TU_NOP + [
        {"name": "ThuaDat_DiaChi",
         "value": {"tinh": "Lào Cai", "xa": "Phường Sa Pa", "diaChi": "Tổ dân phố Sa Pa 4"}},
    ]
    _, warnings = mapper.enrich(payload, _ctx("MAI XUÂN HẢI", "010075000950"))
    assert not any("trùng" in w.lower() and "thửa đất" in w.lower() for w in warnings)


def test_canh_bao_khi_thua_dat_khac_tinh_noi_cu_tru():
    # ⚠ Không dùng "Yên Bái" làm tỉnh đối chứng: area_remap gộp nó về "Lào Cai" theo sắp xếp ĐVHC,
    # nên hai địa chỉ sẽ hóa cùng tỉnh và cảnh báo (đúng) không phát.
    payload = _HS_TU_NOP + [
        {"name": "ThuaDat_DiaChi",
         "value": {"tinh": "Bắc Ninh", "xa": "Phường Kinh Bắc", "diaChi": "Khu Niềm Xá"}},
    ]
    _, warnings = mapper.enrich(payload, _ctx("MAI XUÂN HẢI", "010075000950"))
    assert any("khác tỉnh với nơi thường trú" in w for w in warnings)


def test_so_dinh_danh_sai_do_dai_van_phat_kem_canh_bao():
    payload = [f for f in _HS_TU_NOP if f["name"] != "ChuHoSo_SoDinhDanh"]
    payload = payload + [{"name": "ChuHoSo_SoDinhDanh", "value": "0100 75 00 09 5"}]
    fields, warnings = mapper.enrich(payload, _ctx("MAI XUÂN HẢI", "010075000950"))

    assert _names(fields)["ChuHoSo_soCMNDChuHoSo"] == "01007500095"
    assert any("11 chữ số" in w for w in warnings)


# ------------------------------------------------------------------------------------ đính kèm
def test_bang_dung_3_dong_va_khong_route_ra_ngoai():
    assert set(planner._ROWS) == {0, 1, 2}
    assert {slot for slot, _ in planner._ROUTES.values()} <= {0, 1, 2}


def test_route_dung_dong_va_tick_checkbox():
    files = _files(["don.pdf", "gcn.pdf", "uyquyen.pdf"])
    llm = {0: "don_bien_dong", 1: "gcn", 2: "van_ban_dai_dien"}
    attachments, _, _ = planner.build_plan_items(files, llm)

    by_file = {a["fileName"]: a for a in attachments}
    assert by_file["don.pdf"]["slotIndex"] == 0
    assert by_file["gcn.pdf"]["slotIndex"] == 1
    assert by_file["uyquyen.pdf"]["slotIndex"] == 2
    for item in attachments:
        assert item["target"] == "fixed-slot"
        assert item["tickRow"] is True
        assert item["needsAddComponent"] is False
        assert item["componentName"] == planner._ROWS[item["slotIndex"]]


def test_hai_ban_don_ky_so_va_chua_ky_cung_vao_mot_dong():
    """Ảnh ánh xạ: "Số bản: 1 · Gắn cả 2 tệp vào dòng này" — engine gom theo slotKey."""
    files = _files(["donmaixuanhai0001_signed_95.pdf", "don_mai_xuan_hai0001.pdf"])
    attachments, warnings, _ = planner.build_plan_items(
        files, {0: "don_bien_dong", 1: "don_bien_dong"}
    )

    assert {a["slotIndex"] for a in attachments} == {0}
    assert len({a["slotKey"] for a in attachments}) == 1
    # Mỗi tệp đúng một dòng — không nhân bản lượt đính.
    assert len(attachments) == len(files)
    assert any("đang gắn 2 tệp" in w for w in warnings)


def test_giay_to_khong_co_dong_rieng_xuong_giay_to_khac():
    files = _files(["cccd.pdf", "banan.pdf", "la.pdf"])
    attachments, warnings, _ = planner.build_plan_items(
        files, {0: "giay_to_nhan_than", 1: "ban_an"}
    )

    by_file = {a["fileName"]: a for a in attachments}
    for name in ("cccd.pdf", "banan.pdf", "la.pdf"):
        assert by_file[name]["target"] == "new"
        assert by_file[name]["needsAddComponent"] is True
        # Cổng iGate: bấm "Chọn tệp tin" mở hộp thoại hệ điều hành → FE phải gán thẳng.
        assert by_file[name]["noChooserClick"] is True
        # componentName là thứ FE gõ vào ô tên của dòng → phải bằng documentName.
        assert by_file[name]["componentName"] == by_file[name]["documentName"]
    assert "Bản án" in by_file["banan.pdf"]["documentName"]
    assert any("Chưa nhận ra loại giấy tờ" in w for w in warnings)


def test_thieu_don_hoac_gcn_thi_canh_bao():
    attachments, warnings, _ = planner.build_plan_items(
        _files(["don.pdf"]), {0: "don_bien_dong"}
    )
    assert len(attachments) == 1
    assert any("Giấy chứng nhận đã cấp" in w and "bắt buộc" in w for w in warnings)
    # Văn bản đại diện KHÔNG bắt buộc — tự đứng đơn là trường hợp thường gặp.
    assert not any("Văn bản về việc đại diện" in w and "bắt buộc" in w for w in warnings)


def test_co_van_ban_dai_dien_thi_nhac_kiem_tra_khoi_nguoi_nop():
    _, warnings, _ = planner.build_plan_items(
        _files(["don.pdf", "uyquyen.pdf"]), {0: "don_bien_dong", 1: "van_ban_dai_dien"}
    )
    assert any("NỘP THAY" in w for w in warnings)


def test_luon_nhac_giu_nguyen_o_ve_viec():
    _, warnings, _ = planner.build_plan_items(_files(["don.pdf"]), {0: "don_bien_dong"})
    assert any("Về việc" in w and "KHÔNG ghi đè" in w for w in warnings)


def test_khong_bo_sot_tep_nao():
    files = _files(["a.pdf", "b.pdf", "c.pdf", "d.pdf"])
    attachments, _, classified = planner.build_plan_items(files, {0: "don_bien_dong", 1: "gcn"})

    assert len(attachments) == len(files)
    assert len(classified) == len(files)
    assert {a["fileIndex"] for a in attachments} == set(range(len(files)))
