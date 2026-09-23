"""[Lào Cai] Sử dụng đất kết hợp đa mục đích (cấp xã) — mã 1.115682.

Khoá sáu điều dễ vỡ:
  1. Nhận diện phải khóa host Lào Cai và KHÔNG cướp trang của các thủ tục đất đai khác cùng cổng.
  2. Đính kèm KHÔNG có bảng thành phần hồ sơ → tuyệt đối không được sinh fixed-slot/slotIndex.
  3. Hai ô readonly CongDan_tenCongDan/CongDan_soCmnd KHÔNG BAO GIỜ được phát.
  4. Cán bộ nộp thay (mode A) là ca thường gặp — không được chép nhân thân chéo hai khối.
  5. Lệch diện tích kết hợp giữa Đơn Mẫu 13 và Thuyết minh phải được nói ra, KHÔNG sửa lén.
  6. Lệch TỈNH giữa thửa đất và nơi thường trú là BÌNH THƯỜNG ở thủ tục này (ngược 1.115685).
"""

from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_cap_xa.attach import planner
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_cap_xa.process import mapper
from app.pipelines.su_dung_dat_ket_hop_da_muc_dich_cap_xa.process.schema import (
    INDIVIDUAL_ONLY_FIELDS,
    ORG_ONLY_FIELDS,
    UI_COMP_BY_NAME,
)
from app.procedures.registry import public_list

_KEY = "su-dung-dat-ket-hop-da-muc-dich-cap-xa"

# Hồ sơ mẫu của file mapping: ông NGUYỄN ĐỨC NHÂN (thường trú Nghệ An) xin dùng kết hợp 258,5 m² của
# thửa 428 tờ bản đồ 264 tại TDP Cầu Mây 1, phường Sa Pa, tỉnh Lào Cai vào mục đích thương mại dịch
# vụ. Người đi nộp là cán bộ NHÂM ĐẮC ĐẠT (thường trú Hưng Yên) — BA TỈNH khác nhau.
_HS_CHU_HO_SO = [
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Đức Nhân"},
    {"name": "ChuHoSo_NgaySinh", "value": "15/11/1980"},
    {"name": "ChuHoSo_GioiTinh", "value": "Nam"},
    {"name": "ChuHoSo_SoDinhDanh", "value": "040080009633"},
    {"name": "ChuHoSo_NgayCap", "value": "20/12/2021"},
    {"name": "ChuHoSo_NoiCap", "value": "Cục Cảnh sát QLHC về TTXH"},
    {"name": "ChuHoSo_NoiCuTru",
     "value": {"tinh": "Nghệ An", "xa": "Xã Vân Du", "diaChi": "Xóm Tiên Sơn"}},
    {"name": "Don_KinhGui", "value": "UBND phường Sa Pa"},
    {"name": "Don_MauSo", "value": "Mẫu số 13"},
    {"name": "Don_NgayKy", "value": "25/6/2026"},
    {"name": "ThuaDat_DiaChi",
     "value": {"tinh": "Lào Cai", "xa": "Phường Sa Pa", "diaChi": "Tổ dân phố Cầu Mây 1"}},
    {"name": "ThuaDat_SoThua", "value": "428"},
    {"name": "ThuaDat_SoToBanDo", "value": "264"},
    {"name": "ThuaDat_TongDienTich", "value": "538,0"},
    {"name": "ThuaDat_MucDichSuDung", "value": "Đất trồng cây hàng năm khác"},
    {"name": "ThuaDat_ThoiHanSuDung", "value": "Đến ngày 20/10/2075"},
    {"name": "KetHop_MucDich", "value": "Thương mại dịch vụ"},
    {"name": "KetHop_DienTich", "value": "258,5"},
    {"name": "Gcn_SoPhatHanh", "value": "AA 01695788"},
    {"name": "Gcn_SoVaoSo", "value": "CN 653"},
    {"name": "Gcn_NgayCap", "value": "06/11/2025"},
    {"name": "Gcn_DonViCap", "value": "Chi nhánh Văn phòng Đăng ký đất đai khu vực Sa Pa"},
]

# Biến thể nộp thay: hồ sơ có thêm CCCD + giấy ủy quyền của người đi nộp.
_HS_NOP_THAY = _HS_CHU_HO_SO + [
    {"name": "NguoiNop_HoTen", "value": "Nhâm Đắc Đạt"},
    {"name": "NguoiNop_SoDinhDanh", "value": "034203010212"},
    {"name": "NguoiNop_NgaySinh", "value": "01/01/1990"},
    {"name": "NguoiNop_NoiCuTru",
     "value": {"tinh": "Hưng Yên", "xa": "Xã Đông Quan", "diaChi": "Thôn Trưng Trắc B"}},
    {"name": "NguoiNop_DienThoai", "value": "0912345678"},
    {"name": "UyQuyen_SoGiay", "value": "0456"},
]


def _entry(key=_KEY):
    return next(p for p in public_list() if p["key"] == key)


def _names(fields):
    return {f["name"]: f["value"] for f in fields}


def _ctx(fullname: str, identity: str) -> dict:
    """options như popup gửi lên: nhân thân tài khoản định danh đang đăng nhập."""
    return {"formContext": {"applicantFullname": fullname, "applicantIdentityNumber": identity}}


def _ctx_chu_ho_so():
    return _ctx("Nguyễn Đức Nhân", "040080009633")


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


def test_key_trung_voi_muc_ke_khai_links_1_115682():
    """Key phải trùng mục ke_khai_links thì chọn link kê khai mới ra đúng pipeline điền."""
    from app.procedures.ke_khai_links import _load

    muc = next(i for i in _load() if i["key"] == _KEY)
    assert muc["code"] == "1.115682"


def test_khong_an_theo_chu_hoa():
    """Hàm chuẩn hoá của popup.js đã hạ chữ thường — cụm khai phải là bản thường."""
    phrases = _entry()["detect"]["textIncludes"]
    assert all(p == p.lower() for p in phrases)


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
_TIEU_DE = "1.115682 - Sử dụng đất kết hợp đa mục đích (cấp xã)."


def test_trang_lao_cai_nhan_dung_thu_tuc_nay():
    assert _detect(_URL_LAO_CAI, _TIEU_DE) == _KEY


def test_ngoai_cong_lao_cai_thi_khong_nhan():
    """urlScope là thứ duy nhất chặn cụm text này quét sang cổng tỉnh khác."""
    assert _detect("https://dichvucong.quangngai.gov.vn/vi/padsvc/apply-online/1", _TIEU_DE) != _KEY


def test_khong_cuop_trang_cua_thu_tuc_dat_dai_khac_cung_cong():
    """Cụm "sử dụng đất kết hợp đa mục đích" không được khớp trang của thủ tục khác ở Lào Cai."""
    khac = (
        "Xác định lại diện tích đất ở của hộ gia đình, cá nhân đã được cấp Giấy chứng nhận trước "
        "ngày 01 tháng 7 năm 2004"
    )
    assert _detect(_URL_LAO_CAI, khac) != _KEY


# ------------------------------------------------ hai ô readonly: không bao giờ được phát
def test_khong_bao_gio_phat_hai_o_readonly_cua_tai_khoan():
    """Ghi vào 2 ô này là script cổng XOÁ TRẮNG "Di động" + "Số Căn cước" vừa điền xong."""
    assert "CongDan_tenCongDan" not in UI_COMP_BY_NAME
    assert "CongDan_soCmnd" not in UI_COMP_BY_NAME

    for payload, ctx in (
        (_HS_CHU_HO_SO, _ctx_chu_ho_so()),
        (_HS_NOP_THAY, _ctx("Nhâm Đắc Đạt", "034203010212")),
    ):
        by_name = _names(mapper.enrich(payload, ctx)[0])
        assert "CongDan_tenCongDan" not in by_name
        assert "CongDan_soCmnd" not in by_name


def test_khong_phat_o_bi_cong_an_theo_doi_tuong():
    """Hồ sơ cá nhân thì 2 ô tổ chức display:none — phát vào đó chỉ làm engine báo lỗi vô cớ."""
    by_name = _names(mapper.enrich(_HS_CHU_HO_SO, _ctx_chu_ho_so())[0])
    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "Cá nhân"
    assert not (ORG_ONLY_FIELDS & set(by_name))

    to_chuc = [
        {"name": "ChuHoSo_LaToChuc", "value": True},
        {"name": "ChuHoSo_TenToChuc", "value": "CÔNG TY TNHH ABC"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300123456"},
        {"name": "ChuHoSo_HoTen", "value": "Nguyễn Đức Nhân"},
    ]
    by_name = _names(mapper.enrich(to_chuc)[0])
    assert by_name["ChuHoSo_maDoiTuongNopHS"] == "Tổ chức"
    assert not (INDIVIDUAL_ONLY_FIELDS & set(by_name))


# --------------------------------------------------------- mode B: người sử dụng đất tự đi nộp
def test_tu_nop_dien_du_ca_hai_khoi():
    fields, warnings = mapper.enrich(_HS_CHU_HO_SO, _ctx_chu_ho_so())
    by_name = _names(fields)

    assert by_name["ChuHoSo_tenChuHoSo"] == "Nguyễn Đức Nhân"
    assert by_name["ChuHoSo_soCMNDChuHoSo"] == "040080009633"
    assert by_name["ChuHoSo_ngaySinhChuHoSo"] == "15/11/1980"
    assert by_name["ChuHoSo_ngayCapCMNDCHS"] == "20/12/2021"
    assert "Cục Cảnh sát quản lý hành chính" in by_name["ChuHoSo_noiCapCMNDCHS"]
    # Nơi thường trú là NGHỆ AN, không phải Lào Cai nơi có thửa đất.
    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Nghệ An"
    assert by_name["ChuHoSo_diaChiChuHoSo"] == "Xóm Tiên Sơn"
    # Khối người nộp là chính người đó → điền đủ, kể cả 3 ô địa chỉ checkbox không copy.
    assert by_name["CongDan_ngaySinhCongDan"] == "15/11/1980"
    assert by_name["CongDan_maTinhThanh"] == "Tỉnh Nghệ An"
    assert any("trùng chủ hồ sơ" in w for w in warnings)


def test_khong_phat_khoi_nguoi_nop_khi_khong_doc_duoc_tai_khoan():
    """Không có mốc tài khoản → để trống khối người nộp, không mượn nhân thân chủ hồ sơ."""
    fields, warnings = mapper.enrich(_HS_CHU_HO_SO)
    by_name = _names(fields)

    assert not [n for n in by_name if n.startswith("CongDan_")]
    assert by_name["ChuHoSo_tenChuHoSo"] == "Nguyễn Đức Nhân"
    assert any("Chưa đọc được tài khoản định danh" in w for w in warnings)


def test_can_bo_nop_thay_ma_ho_so_khong_co_giay_to_cua_ho_thi_bo_trong_khoi_nguoi_nop():
    """Ca thường gặp nhất của thủ tục này — phải nói rõ lý do, không im lặng."""
    fields, warnings = mapper.enrich(_HS_CHU_HO_SO, _ctx("Nhâm Đắc Đạt", "034203010212"))
    by_name = _names(fields)

    assert not [n for n in by_name if n.startswith("CongDan_")]
    assert by_name["ChuHoSo_tenChuHoSo"] == "Nguyễn Đức Nhân"
    assert any("KHÔNG có giấy tờ tuỳ thân của người đang đăng nhập" in w for w in warnings)


# ------------------------------------------------------------------ mode A: nộp thay có giấy tờ
def test_nop_thay_giu_nguyen_hai_nguoi_khac_nhau():
    fields, warnings = mapper.enrich(_HS_NOP_THAY, _ctx("Nhâm Đắc Đạt", "034203010212"))
    by_name = _names(fields)

    assert by_name["ChuHoSo_tenChuHoSo"] == "Nguyễn Đức Nhân"
    assert by_name["ChuHoSo_soCMNDChuHoSo"] == "040080009633"
    assert by_name["ChuHoSo_maTinhThanhCHS"] == "Tỉnh Nghệ An"
    # Ba tỉnh phải giữ nguyên ba nơi, không được lẫn vào nhau.
    assert by_name["CongDan_maTinhThanh"] == "Tỉnh Hưng Yên"
    assert by_name["CongDan_ngaySinhCongDan"] == "01/01/1990"
    assert by_name["CongDan_diDong"] == "0912345678"
    assert any("nộp thay" in w for w in warnings)
    assert any("READONLY" in w for w in warnings)


def test_nop_thay_khong_muon_dien_thoai_cua_chu_ho_so():
    payload = [f for f in _HS_NOP_THAY if f["name"] != "NguoiNop_DienThoai"]
    payload = payload + [{"name": "ChuHoSo_DienThoai", "value": "0987654321"}]
    fields, warnings = mapper.enrich(payload, _ctx("Nhâm Đắc Đạt", "034203010212"))
    by_name = _names(fields)

    assert "CongDan_diDong" not in by_name
    assert by_name["ChuHoSo_diDongLienLacCHS"] == "0987654321"
    assert any("KHÔNG lấy số của chủ hồ sơ" in w for w in warnings)


# --------------------------------------------------------- điều kiện riêng của 1.115682
def test_canh_bao_lech_dien_tich_giua_don_va_thuyet_minh():
    """Hồ sơ mẫu lệch thật: Đơn mục 5.2 ghi 258,5 m² còn Thuyết minh mục IV.2 ghi 267,8 m²."""
    payload = _HS_CHU_HO_SO + [{"name": "KetHop_DienTichTheoThuyetMinh", "value": "267,8"}]
    fields, warnings = mapper.enrich(payload, _ctx_chu_ho_so())

    canh_bao = [w for w in warnings if "LỆCH DIỆN TÍCH" in w]
    assert canh_bao, warnings
    assert "258,5" in canh_bao[0] and "267,8" in canh_bao[0]
    # Không tự chọn hộ, không sửa số: bước 2 vốn không có ô diện tích nào để phát.
    assert not [n for n in _names(fields) if "DienTich" in n]


def test_hai_nguon_dien_tich_khop_thi_khong_canh_bao():
    payload = _HS_CHU_HO_SO + [{"name": "KetHop_DienTichTheoThuyetMinh", "value": "258,5"}]
    _, warnings = mapper.enrich(payload, _ctx_chu_ho_so())
    assert not any("LỆCH DIỆN TÍCH" in w for w in warnings)


def test_ho_so_mau_48_phan_tram_khong_bi_canh_bao_vuot_tran():
    """258,5 / 538,0 = 48% — dưới trần 50% của Điều 99 NĐ 102/2024, không được báo động giả."""
    _, warnings = mapper.enrich(_HS_CHU_HO_SO, _ctx_chu_ho_so())
    assert not any("vượt mức 50%" in w for w in warnings)


def test_canh_bao_khi_dien_tich_ket_hop_vuot_50_phan_tram():
    payload = [f for f in _HS_CHU_HO_SO if f["name"] != "KetHop_DienTich"]
    payload = payload + [{"name": "KetHop_DienTich", "value": "400,0"}]
    _, warnings = mapper.enrich(payload, _ctx_chu_ho_so())
    assert any("vượt mức 50%" in w and "102/2024" in w for w in warnings)


def test_canh_bao_khi_dien_tich_ket_hop_lon_hon_ca_thua():
    payload = [f for f in _HS_CHU_HO_SO if f["name"] != "KetHop_DienTich"]
    payload = payload + [{"name": "KetHop_DienTich", "value": "1.258,5"}]
    _, warnings = mapper.enrich(payload, _ctx_chu_ho_so())
    assert any("LỚN HƠN tổng diện tích thửa" in w for w in warnings)


def test_canh_bao_don_khong_dung_mau_so_13():
    payload = [f for f in _HS_CHU_HO_SO if f["name"] != "Don_MauSo"]
    payload = payload + [{"name": "Don_MauSo", "value": "Mẫu số 11/ĐK"}]
    _, warnings = mapper.enrich(payload, _ctx_chu_ho_so())
    assert any("Mẫu số 13" in w for w in warnings)


def test_dung_mau_so_13_thi_khong_canh_bao():
    _, warnings = mapper.enrich(_HS_CHU_HO_SO, _ctx_chu_ho_so())
    assert not any("Mẫu số 13" in w for w in warnings)


def test_thua_dat_khac_tinh_noi_cu_tru_la_binh_thuong():
    """Ngược 1.115685: ở đây thường trú Nghệ An mà thửa đất Lào Cai là chuyện bình thường."""
    _, warnings = mapper.enrich(_HS_CHU_HO_SO, _ctx_chu_ho_so())
    assert not any("khác tỉnh" in w for w in warnings)


def test_canh_bao_khi_noi_cu_tru_trung_khit_dia_chi_thua_dat():
    """Giấy chứng nhận KHÔNG ghi nơi thường trú — trùng khít là dấu hiệu chép nhầm mục 2.e."""
    payload = [f for f in _HS_CHU_HO_SO if f["name"] != "ChuHoSo_NoiCuTru"]
    payload = payload + [
        {"name": "ChuHoSo_NoiCuTru",
         "value": {"tinh": "Lào Cai", "xa": "Phường Sa Pa", "diaChi": "Tổ dân phố Cầu Mây 1"}},
    ]
    _, warnings = mapper.enrich(payload, _ctx_chu_ho_so())
    assert any("TRÙNG KHÍT địa chỉ thửa đất" in w for w in warnings)


def test_so_dinh_danh_sai_do_dai_van_phat_kem_canh_bao():
    payload = [f for f in _HS_CHU_HO_SO if f["name"] != "ChuHoSo_SoDinhDanh"]
    payload = payload + [{"name": "ChuHoSo_SoDinhDanh", "value": "01695788"}]
    fields, warnings = mapper.enrich(payload, _ctx("Nguyễn Đức Nhân", ""))

    assert _names(fields)["ChuHoSo_soCMNDChuHoSo"] == "01695788"
    assert any("8 chữ số" in w for w in warnings)


# ------------------------------------------------------------------------------------ đính kèm
def test_khong_sinh_fixed_slot_vi_man_hinh_khong_co_bang_thanh_phan_ho_so():
    """Khối "Biểu mẫu giấy tờ" chỉ ghi "(Hồ sơ không yêu cầu giấy tờ kèm theo)"."""
    files = _files(["don.pdf", "phuongan.pdf", "gcn.pdf"])
    llm = {0: "don_de_nghi", 1: "phuong_an", 2: "gcn"}
    attachments, _, _ = planner.build_plan_items(files, llm)

    for item in attachments:
        assert item["target"] == "new"
        assert item["needsAddComponent"] is True
        assert "slotIndex" not in item
        assert "slotKey" not in item
        assert "tickRow" not in item
        # Cổng iGate: bấm "Chọn tệp tin" mở hộp thoại hệ điều hành → FE phải gán thẳng.
        assert item["noChooserClick"] is True
        # componentName là thứ FE gõ vào ô tên dòng "Giấy tờ khác" → phải bằng documentName.
        assert item["componentName"] == item["documentName"]


def test_ten_dong_theo_danh_muc_thanh_phan_ho_so_chu_khong_theo_ten_tep():
    files = _files(["NGUYEN_DUC_NHAN__01695788__CN.pdf", "Don_Nguyen_Duc_Nhan_dmd.pdf",
                    "0602_Thuyet_minh__Anh_Phu.pdf"])
    llm = {0: "gcn", 1: "don_de_nghi", 2: "phuong_an"}
    attachments, _, _ = planner.build_plan_items(files, llm)
    ten = {a["fileName"]: a["documentName"] for a in attachments}

    assert ten["NGUYEN_DUC_NHAN__01695788__CN.pdf"].startswith("Giấy chứng nhận đã cấp")
    assert ten["Don_Nguyen_Duc_Nhan_dmd.pdf"] == (
        "Văn bản đề nghị sử dụng đất kết hợp đa mục đích theo Mẫu số 13"
    )
    assert ten["0602_Thuyet_minh__Anh_Phu.pdf"] == "Phương án sử dụng đất kết hợp"


def test_hai_ban_cung_loai_ra_hai_dong_khac_ten():
    """Mỗi dòng "Giấy tờ khác" chỉ giữ được MỘT tệp — trùng tên là đè nhau."""
    files = _files(["don.pdf", "don_signed.pdf"])
    attachments, _, _ = planner.build_plan_items(files, {0: "don_de_nghi", 1: "don_de_nghi"})

    ten = [a["documentName"] for a in attachments]
    assert len(set(ten)) == 2
    assert ten[1].endswith("(2)")


def test_giay_to_khong_ro_loai_giu_ten_tep_va_canh_bao():
    files = _files(["don.pdf", "la.pdf"])
    attachments, warnings, _ = planner.build_plan_items(files, {0: "don_de_nghi"})

    by_file = {a["fileName"]: a for a in attachments}
    assert by_file["la.pdf"]["detectedType"] == "khac"
    assert by_file["la.pdf"]["target"] == "new"
    assert any("Chưa nhận ra loại giấy tờ" in w for w in warnings)


def test_thieu_giay_to_cot_loi_thi_canh_bao():
    _, warnings, _ = planner.build_plan_items(_files(["don.pdf"]), {0: "don_de_nghi"})
    thieu = [w for w in warnings if "Thiếu giấy tờ cốt lõi" in w]
    assert thieu, warnings
    assert "Phương án sử dụng đất kết hợp" in thieu[0]
    assert "Giấy chứng nhận đã cấp" in thieu[0]


def test_du_ba_giay_to_cot_loi_thi_khong_canh_bao_thieu():
    _, warnings, _ = planner.build_plan_items(
        _files(["don.pdf", "pa.pdf", "gcn.pdf"]),
        {0: "don_de_nghi", 1: "phuong_an", 2: "gcn"},
    )
    assert not any("Thiếu giấy tờ cốt lõi" in w for w in warnings)


def test_nhac_bo_sung_cccd_chu_ho_theo_muc_6_cua_don():
    """Ảnh ánh xạ đánh dấu đỏ ô ⑧: Đơn mục 6 kê bản sao CCCD nhưng hồ sơ mẫu chưa có tệp."""
    _, warnings, _ = planner.build_plan_items(
        _files(["don.pdf", "pa.pdf", "gcn.pdf"]),
        {0: "don_de_nghi", 1: "phuong_an", 2: "gcn"},
    )
    assert any("Bản sao Căn cước công dân của chủ hộ" in w for w in warnings)

    _, warnings, _ = planner.build_plan_items(
        _files(["don.pdf", "pa.pdf", "gcn.pdf", "cccd.pdf"]),
        {0: "don_de_nghi", 1: "phuong_an", 2: "gcn", 3: "giay_to_nhan_than"},
    )
    assert not any("chưa có tệp CCCD nào" in w for w in warnings)


def test_luon_nhac_giu_nguyen_o_ve_viec_va_khong_co_bang_thanh_phan_ho_so():
    _, warnings, _ = planner.build_plan_items(_files(["don.pdf"]), {0: "don_de_nghi"})
    assert any("Về việc" in w and "KHÔNG ghi đè" in w for w in warnings)
    assert any("KHÔNG có bảng \"Thành phần hồ sơ\"" in w for w in warnings)


def test_khong_bo_sot_tep_nao():
    files = _files(["a.pdf", "b.pdf", "c.pdf", "d.pdf", "e.pdf"])
    attachments, _, classified = planner.build_plan_items(
        files, {0: "don_de_nghi", 1: "phuong_an", 2: "gcn", 3: "giay_to_nhan_than"}
    )

    assert len(attachments) == len(files)
    assert len(classified) == len(files)
    assert {a["fileIndex"] for a in attachments} == set(range(len(files)))
