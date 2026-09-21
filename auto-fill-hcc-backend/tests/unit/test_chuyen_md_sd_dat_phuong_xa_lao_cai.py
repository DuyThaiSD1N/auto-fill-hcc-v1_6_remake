"""[Lào Cai] Chuyển mục đích sử dụng đất… nộp tại PHƯỜNG/XÃ (1.115679) — eForm iGate (CongDan_*/ChuHoSo_*)
+ đính kèm fixed-slot theo bảng bước 3 in một lần cả bốn nhóm "a) b) c) d)".

Khoá sáu điều dễ vỡ:
  1. Thủ tục này TRÙNG TÊN với 1.115651 (bản nộp ở Sở) — nhận nhầm là chạy sai pipeline đính kèm và sai cơ
     quan tiếp nhận. Tách nhau bằng MÃ THỦ TỤC: nhãn mang mã 1.115679 để cán bộ tìm ra, còn nhận diện đọc mã
     trong banner <h4> "thủ tục đã chọn" của cổng (có ở mọi bước, kể cả bước 3).
  2. Hồ sơ NỘP THAY (HS1: ông Đào Văn Tuấn nộp thay hộ ông Hoàng Trung Thành - bà Trần Thị Thương theo Giấy
     uỷ quyền 488/2026/CCGD): khối người nộp là bên ĐƯỢC uỷ quyền, khối chủ hồ sơ là bên UỶ quyền.
  3. Hai vợ chồng cùng đứng tên mà form chỉ có MỘT ô họ tên → không được ghép hai người.
  4. Khối người nộp có 6 ô (*) cổng để trống; ô Giới tính không có lựa chọn trống nên luôn hiện "Nữ".
  5. Từ khóa từng dòng thành phần hồ sơ phải khớp ĐÚNG dòng của nó trên bảng thật — bảng lặp lại dòng "giấy
     chứng nhận" và dòng "quyết định giao đất…" ở cả bốn nhóm.
  6. Giấy chứng nhận và Quyết định đi vào HAI DÒNG CUỐI BẢNG (nhóm d) theo ảnh hướng dẫn của bộ phận một cửa.
"""

import re
import unicodedata

from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.attach import catalog, planner
from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.process import mapper
from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import public_list

_KEY = "chuyen-muc-dich-su-dung-dat-khoan-1-dieu-175"
_KEY_SO = "chuyen-muc-dich-su-dung-dat-lao-cai"  # bản cùng tên nộp ở Sở (1.115651)
_URL_LAO_CAI = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"

# HS1 của "Mapping_CMDSDD_1.115679_LaoCai_CaNhan_ToChuc.xlsx": ông Hoàng Trung Thành và vợ Trần Thị Thương
# uỷ quyền cho ông Đào Văn Tuấn đi nộp. Hồ sơ KHÔNG có bản scan CCCD — mọi nhân thân đọc từ Đơn Mẫu số 02 và
# Giấy uỷ quyền, nên tất cả đều nằm ở NguoiTrongGiayTo.
_HOANG_TRUNG_THANH = {
    "HoTen": "Hoàng Trung Thành",
    "SoDinhDanh": "015085007662",
    "NgaySinh": "1985",
    "NgayCap": "10/06/2025",
    "NoiCap": "Bộ Công an",
    "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ dân phố số 9 Xuân Tăng"},
}
_TRAN_THI_THUONG = {
    "HoTen": "Trần Thị Thương",
    "SoDinhDanh": "010189007136",
    "NgaySinh": "1989",
    "NgayCap": "24/06/2021",
    "NoiCap": "Cục cảnh sát và QLHC về TTXH",
    "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ dân phố số 9 Xuân Tăng"},
}
_DAO_VAN_TUAN = {
    "HoTen": "Đào Văn Tuấn",
    "SoDinhDanh": "001063041682",
    "NgaySinh": "1963",
    "NgayCap": "27/10/2023",
    "NoiCap": "Cục cảnh sát quản lý hành chính về trật tự xã hội",
    "NoiCuTru": {"tinh": "Lào Cai", "xa": "Lào Cai", "diaChi": "Tổ dân phố số 20"},
}
# Ông Tuấn đăng nhập bằng tài khoản của chính mình để nộp thay.
_CTX_NOP_THAY = {"formContext": {"applicantIdentityNumber": "001063041682", "applicantFullname": "ĐÀO VĂN TUẤN"}}
# Ông Thành tự nộp.
_CTX_TU_NOP = {"formContext": {"applicantIdentityNumber": "015085007662", "applicantFullname": "HOÀNG TRUNG THÀNH"}}


def _ho_so_hs1():
    return [
        {"name": "NguoiTrongGiayTo", "value": [_HOANG_TRUNG_THANH, _TRAN_THI_THUONG, _DAO_VAN_TUAN]},
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
        {"name": "ChuHoSo_HoTen", "value": "Hoàng Trung Thành"},
        {"name": "ChuHoSo_XungHo", "value": "Ông"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "0150 8500 7662"},
        {"name": "ChuHoSo_NgaySinh", "value": "1985"},
        {"name": "ChuHoSo_NgayCap", "value": "10/06/2025"},
        {"name": "ChuHoSo_NoiCap", "value": "Bộ công an"},
        # Đơn Mẫu 02 mục 2 ghi "Tổ 39 Phường Cam Đường, tỉnh Lào Cai".
        {"name": "ChuHoSo_DiaChiDon",
         "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 39"}},
        {"name": "ChuHoSo_DiaChiUyQuyen",
         "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ dân phố số 9 Xuân Tăng"}},
        # GCN 2018 còn địa danh trước sáp nhập.
        {"name": "ChuHoSo_DiaChiGcn",
         "value": {"tinh": "Lào Cai", "xa": "Bình Minh", "huyen": "Lào Cai", "diaChi": "Tổ 24"}},
        {"name": "Don_DienThoai", "value": "0342788569"},
        {"name": "PhieuChuyen_DienThoai", "value": "0977689446"},
    ]


def _entry():
    return next(p for p in public_list() if p["key"] == _KEY)


def _names(fields):
    return {f["name"]: f["value"] for f in fields}


def _order(fields):
    return [f["name"] for f in fields]


def _files(names):
    return [{"name": n, "_index": i} for i, n in enumerate(names)]


def _llm(labels):
    return {i: {"label": label, "documentName": ""} for i, label in enumerate(labels)}


def _norm(value):
    text = unicodedata.normalize("NFD", str(value or "").replace("Đ", "D").replace("đ", "d"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text).strip().lower()


def _detect(url, body):
    """Bản rút gọn luật nhận diện của popup.js (urlScope → textPriority → textIncludes dài nhất)."""
    url, body = url.lower(), _norm(body)
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
            phrases = [_norm(x) for x in (detect.get("textIncludes") or []) if x]
            if not phrases or not all(x in body for x in phrases):
                continue
            score = sum(len(x) for x in phrases)
            if score > best_score:
                best, best_score = p["key"], score
        if best:
            return best
    return ""


# Tên thủ tục in trên trang nộp hồ sơ — DÙNG CHUNG cho 1.115651 và 1.115679, một mình nó KHÔNG tách được.
_TIEU_DE_TRANG = (
    "Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia hạn sử dụng đất khi hết thời hạn sử "
    "dụng đất; điều chỉnh thời hạn sử dụng đất của dự án đầu tư đối với trường hợp quy định tại Khoản 1 "
    "Điều 175 Luật Đất đai năm 2024"
)


def _banner(ma: str) -> str:
    """Chữ HIỂN THỊ của banner "thủ tục đã chọn" trên cổng, chép theo DOM thật:

    <section id="thu-tuc-da-chon-wrapper">
      <h4><span class="label label-warning label-fill-out">Một phần</span> 1.115679 - Lào Cai - Chuyển … </h4>

    Banner này có ở MỌI bước của luồng nộp hồ sơ và là chỗ DUY NHẤT in mã thủ tục.
    """
    return f"Một phần {ma} - Lào Cai - {_TIEU_DE_TRANG}"


# Text nhìn thấy ở bước 2 (nhập thông tin người nộp) và bước 3 (thành phần hồ sơ) của 1.115679.
_TRANG_BUOC_2 = (
    "QUY TRÌNH THỰC HIỆN DỊCH VỤ CÔNG TRỰC TUYẾN Thông tin người nộp hồ sơ "
    + _banner("1.115679")
    + " Nơi tiếp nhận hồ sơ Thời gian giải quyết Thông tin người nộp Họ và tên Tên cơ quan/tổ chức"
)
_TRANG_BUOC_3 = (
    _banner("1.115679")
    + " Thành phần hồ sơ a) Hồ sơ đề nghị chuyển mục đích sử dụng đất gồm: "
    "Đơn theo Mẫu số 02 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND"
)


# ---------------------------------------------------------------- registry & nhận diện


def test_co_trong_registry_va_khoa_dung_cong_lao_cai():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["detect"]["urlScope"] == ["laocai.gov.vn"]
    assert entry["label"].startswith("[Lào Cai]")


def test_nhan_mang_ma_1_115679_de_tach_khoi_ban_cung_ten_nop_o_so():
    """Popup tìm thủ tục theo `label + key`; hai bản cùng tên chỉ phân biệt được nhờ mã in trong nhãn.

    Mã đặt ở CUỐI nhãn để đọc hết tên thủ tục rồi mới tới phần phân biệt — tên thủ tục giữ nguyên như cổng in.
    """
    entry = _entry()
    assert entry["label"].endswith("(1.115679 - cho Phường/Xã)")
    o_so = next(p for p in public_list() if p["key"] == _KEY_SO)
    assert entry["label"] != o_so["label"]


def test_key_trung_muc_ke_khai_links_1_115679():
    """Key phải khớp danh mục link để popup chọn link cũng chọn luôn pipeline điền."""
    from app.procedures.ke_khai_links import KE_KHAI_LINKS

    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.115679"
    # Nộp ở Phường/Xã: bật selectSo là popup tick radio "Sở" rồi bỏ hẳn ô Phường/Xã.
    assert not link.get("selectSo")
    assert link.get("needsAgencySelect") is True
    assert link["label"].startswith("Lào Cai -")
    assert link["label"].endswith("(1.115679 - cho Phường/Xã)")


def test_nhan_dung_thu_tuc_o_ca_buoc_2_va_buoc_3():
    """Banner <h4> in mã thủ tục ở MỌI bước → nhận diện không phụ thuộc bước nào đang mở."""
    assert _detect(_URL_LAO_CAI, _TRANG_BUOC_2) == _KEY
    assert _detect(_URL_LAO_CAI, _TRANG_BUOC_3) == _KEY


def test_ma_thu_tuc_la_dau_hieu_bat_buoc_chu_khong_phai_ten():
    """Tên thủ tục trùng y hệt 1.115651 → thiếu mã trong banner thì KHÔNG được nhận bừa sang 1.115679."""
    assert "1.115679" in _TRANG_BUOC_3
    khong_co_ma = _TRANG_BUOC_3.replace("1.115679", "")
    assert _detect(_URL_LAO_CAI, khong_co_ma) != _KEY


def test_khong_cuop_trang_cua_ban_nop_o_so_va_cac_thu_tuc_dat_dai_khac():
    # Banner của bản nộp ở Sở in mã 1.115651 → rule theo mã của bản phường/xã không dính.
    body_so = _banner("1.115651") + " (1) Hồ sơ đề nghị chuyển mục đích sử dụng đất"
    assert _detect(_URL_LAO_CAI, body_so) == _KEY_SO
    khac = {
        "thu-hoi-gcn-cap-lan-dau-khong-dung-quy-dinh-cap-lai": (
            "Thu hồi Giấy chứng nhận đã cấp lần đầu không đúng quy định của pháp luật đất đai do người sử "
            "dụng đất, chủ sở hữu tài sản gắn liền với đất phát hiện và cấp lại Giấy chứng nhận sau khi thu hồi"
        ),
        "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep": "Xác nhận tiếp tục sử dụng đất nông nghiệp",
    }
    for key, body in khac.items():
        assert _detect(_URL_LAO_CAI, body) == key, key


def test_cong_tinh_khac_khong_dinh_vao_pipeline_lao_cai():
    """1.115679 là mã QUỐC GIA, cổng iGate tỉnh khác in đúng mã đó → urlScope phải chặn."""
    assert _detect("https://dichvucong.bacninh.gov.vn/x", _TRANG_BUOC_2) != _KEY
    assert _detect("https://dichvucong.lamdong.gov.vn/x", _TRANG_BUOC_2) != _KEY


# ---------------------------------------------------------------- bước 2: điền thông tin


def test_ho_so_nop_thay_khong_lan_hai_chu_the():
    """Khối chủ hồ sơ là bên UỶ QUYỀN, khối người nộp là bên ĐƯỢC UỶ QUYỀN."""
    values = _names(mapper.enrich(_ho_so_hs1(), _CTX_NOP_THAY))
    assert values["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert values["ChuHoSo_tenChuHoSo"] == "HOÀNG TRUNG THÀNH"
    # Đơn ghi cách nhóm 4 số "0150 8500 7662" → phải về liền 12 chữ số.
    assert values["ChuHoSo_soCMNDChuHoSo"] == "015085007662"
    assert values["ChuHoSo_ngayCapCMNDCHS"] == "10/06/2025"
    # Khối người nộp là của ông Đào Văn Tuấn.
    assert values["CongDan_ngayCapCmnd"] == "27/10/2023"
    assert values["CongDan_diaChi"] == "Tổ dân phố số 20"
    # remap_area trả tên ĐẦY ĐỦ đúng như option trên cổng, không phải tên ngắn.
    assert values["CongDan_maPhuongXa"] == "Phường Lào Cai"


def test_nop_thay_khong_chep_so_dien_thoai_cua_chu_ho_so_sang_nguoi_nop():
    """Số trên Đơn là của người sử dụng đất; nộp thay mà chép sang là cổng báo tin về sai người."""
    values = _names(mapper.enrich(_ho_so_hs1(), _CTX_NOP_THAY))
    assert "CongDan_diDong" not in values
    assert values["ChuHoSo_diDongLienLacCHS"] == "0342788569"


def test_tu_nop_thi_o_di_dong_bat_buoc_cua_khoi_nguoi_nop_duoc_dien():
    values = _names(mapper.enrich(_ho_so_hs1(), _CTX_TU_NOP))
    assert values["CongDan_diDong"] == "0342788569"
    assert values["CongDan_diaChi"] == "Tổ dân phố số 9 Xuân Tăng"


def test_gioi_tinh_suy_duoc_tu_xung_ho_vi_o_select_khong_co_lua_chon_trong():
    """Cổng luôn hiện sẵn "Nữ" → hồ sơ của nam giới mà bỏ trống ô này là nộp sai mà nhìn vẫn thấy đã chọn."""
    values = _names(mapper.enrich(_ho_so_hs1(), _CTX_NOP_THAY))
    assert values["ChuHoSo_gioiTinhChuHoSo"] == "Nam"


def test_vo_chong_cung_dung_ten_khong_bi_ghep_vao_mot_o():
    """Form chỉ có MỘT ô họ tên; bà Trần Thị Thương nằm trong Đơn và GCN đính kèm."""
    values = _names(mapper.enrich(_ho_so_hs1(), _CTX_NOP_THAY))
    assert values["ChuHoSo_tenChuHoSo"] == "HOÀNG TRUNG THÀNH"
    assert values["ChuHoSo_soCMNDChuHoSo"] != "010189007136"


def test_dia_chi_chu_ho_so_lay_theo_don_khi_khong_co_anh_cccd():
    """Ma trận đa nguồn: CCCD → Đơn → Giấy uỷ quyền → GCN. Không có ảnh thẻ thì Đơn đứng đầu."""
    values = _names(mapper.enrich(_ho_so_hs1(), _CTX_NOP_THAY))
    assert values["ChuHoSo_diaChiChuHoSo"] == "Tổ 39"
    assert values["ChuHoSo_maPhuongXaCHS"] == "Phường Cam Đường"


def test_co_anh_cccd_thi_cccd_thang_don():
    card = {**_HOANG_TRUNG_THANH,
            "GioiTinh": "Nam",
            "DanToc": "Kinh",
            "NgaySinh": "12/03/1985",
            "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ dân phố số 39"}}
    values = _names(mapper.enrich(
        _ho_so_hs1() + [{"name": "DanhSachCccd", "value": [card]}], _CTX_NOP_THAY
    ))
    assert values["ChuHoSo_diaChiChuHoSo"] == "Tổ dân phố số 39"
    assert values["ChuHoSo_ngaySinhChuHoSo"] == "12/03/1985"
    assert values["ChuHoSo_danTocChuHoSo"] == "Kinh"


def test_khong_bia_ngay_thang_khi_giay_to_chi_ghi_nam_sinh():
    """Đơn và Giấy uỷ quyền chỉ ghi "Sinh: 1985" → ô DD/MM/YYYY phải bỏ trống."""
    values = _names(mapper.enrich(_ho_so_hs1(), _CTX_NOP_THAY))
    assert "ChuHoSo_ngaySinhChuHoSo" not in values


def test_khong_phat_lai_o_readonly_va_khong_tich_nguoi_nop_la_chu_ho_so():
    values = _names(mapper.enrich(_ho_so_hs1(), _CTX_NOP_THAY))
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    # Tích ô này là cổng ÉP Đối tượng = Cá nhân rồi chép đè khối chủ hồ sơ.
    assert "chkbox_nguoinoplachuhs" not in values


def test_nguoi_nop_khong_lay_nham_nhan_than_khi_khong_biet_tai_khoan():
    """Không đọc được tài khoản đang đăng nhập thì thà bỏ trống còn hơn gán bừa một người trong hồ sơ."""
    values = _names(mapper.enrich(_ho_so_hs1(), {}))
    for name in ("CongDan_ngayCapCmnd", "CongDan_maTinhThanh", "CongDan_diaChi", "CongDan_diDong"):
        assert name not in values


def test_tinh_phat_truoc_xa_o_ca_hai_khoi():
    """Danh sách Phường/Xã chỉ nạp AJAX sau khi chọn tỉnh; cổng còn nạp sẵn xã của tỉnh theo tài khoản."""
    order = _order(mapper.enrich(_ho_so_hs1(), _CTX_NOP_THAY))
    assert order.index("CongDan_maTinhThanh") < order.index("CongDan_maPhuongXa")
    assert order.index("ChuHoSo_maTinhThanhCHS") < order.index("ChuHoSo_maPhuongXaCHS")


def test_doi_tuong_phat_truoc_cac_o_cua_nhanh_tuong_ung():
    order = _order(mapper.enrich(_ho_so_hs1(), _CTX_NOP_THAY))
    assert order.index("ChuHoSo_maDoiTuongNopHS") < order.index("ChuHoSo_tenChuHoSo")


def test_ho_so_to_chuc_chon_dung_nhom_o_va_khong_bia_ca_nhan():
    values = _names(mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Doanh nghiệp"},
            {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Một thành viên Hoàng Long"},
            {"name": "ChuHoSo_MaSoThue", "value": "5300461970"},
            {"name": "ChuHoSo_DiaChiDon",
             "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 12 đường Hợp Thành"}},
        ],
        {},
    ))
    assert values["ChuHoSo_maDoiTuongNopHS"] == "DN"
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == "Công ty TNHH Một thành viên Hoàng Long"
    assert values["ChuHoSo_maSoThueChuHoSo"] == "5300461970"
    # Người nộp đứng ra đại diện cho chính tổ chức chủ hồ sơ.
    assert values["CongDan_tenCoQuanToChuc"] == "Công ty TNHH Một thành viên Hoàng Long"
    assert "ChuHoSo_tenChuHoSo" not in values


def test_doan_lai_doi_tuong_khi_llm_tra_nhan_chung_chung():
    assert mapper.org_option("Tổ chức", "Ban Quản lý rừng phòng hộ khu vực Bát Xát") == "CQ"
    assert mapper.org_option("", "Giáo xứ Sa Pa") == "TC"
    assert mapper.org_option("", "Công ty TNHH Một thành viên X") == "DN"


def test_khong_nham_so_quyet_dinh_hay_so_cong_chung_voi_so_dinh_danh():
    """"5334/QĐ-UBND", "488/2026/CCGD" lọt vào ô Số Căn cước là hồ sơ sai người mà không ai soát ra."""
    values = _names(mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
            {"name": "ChuHoSo_HoTen", "value": "Hoàng Trung Thành"},
            {"name": "ChuHoSo_SoDinhDanh", "value": "5334/QĐ-UBND"},
        ],
        {},
    ))
    assert "ChuHoSo_soCMNDChuHoSo" not in values
    # Thiếu số định danh thì chưa đủ để khẳng định chủ hồ sơ → không phát cả khối, tránh điền nửa vời.
    assert "ChuHoSo_tenChuHoSo" not in values


def test_ui_comp_chi_khai_o_cua_buoc_2():
    for name in UI_COMP_BY_NAME:
        assert name.startswith(("CongDan_", "ChuHoSo_")), name


# ---------------------------------------------------------------- bước 3: đính kèm


def test_bo_ho_so_mau_hs1_di_dung_dong():
    """Đúng ảnh ánh xạ đính kèm: Đơn ở nhóm a), GCN và Quyết định ở hai dòng CUỐI BẢNG, còn lại Giấy tờ khác."""
    items, _, classified = planner.build_plan_items(
        _files([
            "Don_HOang_Trung_Thanh.pdf",
            "GCN_Hoang_Trung_Thanh.pdf",
            "QD_Chuyen_muc_dich__QD_dieu_chinh.pdf",
            "Giay_uy_quyen.pdf",
            "HS_do_dac__TB_Thue__giay_nop_tien.pdf",
        ]),
        _llm(["don_mau_02", "gcn", "quyet_dinh_giao_dat", "vb_uy_quyen", "ho_so_nghia_vu_tai_chinh"]),
    )
    by_file = {it["fileName"]: it for it in items}
    assert by_file["Don_HOang_Trung_Thanh.pdf"]["slotKey"] == "lc_115679_1"
    assert by_file["GCN_Hoang_Trung_Thanh.pdf"]["slotKey"] == "lc_115679_6"
    assert by_file["QD_Chuyen_muc_dich__QD_dieu_chinh.pdf"]["slotKey"] == "lc_115679_7"
    assert by_file["Giay_uy_quyen.pdf"]["target"] == "new"
    assert by_file["HS_do_dac__TB_Thue__giay_nop_tien.pdf"]["target"] == "new"
    assert [c["target"] for c in classified] == ["fixed-slot"] * 3 + ["new"] * 2


def test_dong_co_dinh_deu_tich_checkbox_va_gui_kem_tu_khoa():
    items, _, _ = planner.build_plan_items(_files(["don.pdf"]), _llm(["don_mau_02"]))
    item = items[0]
    assert item["target"] == "fixed-slot" and item["tickRow"] is True
    # FE chỉ dùng slotKeywords của BE khi item CÓ sectionHeader.
    assert item["sectionHeader"] and item["slotKeywords"]


def test_gcn_va_quyet_dinh_neo_vao_nhom_d_con_don_neo_vao_tieu_de_cot():
    assert catalog.slot(catalog.ROW_DON_02)["sectionHeader"] == catalog.HEADER_BANG
    for position in (catalog.ROW_GCN, catalog.ROW_QUYET_DINH, catalog.ROW_VB_THAY_DOI):
        assert catalog.slot(position)["sectionHeader"] == catalog.HEADER_NHOM_D


def test_giay_to_khong_co_dong_rieng_xuong_giay_to_khac():
    items, _, _ = planner.build_plan_items(
        _files(["uy_quyen.pdf", "thue.pdf", "do_dac.pdf", "dkdn.pdf", "tb_tra_hs.pdf"]),
        _llm(["vb_uy_quyen", "ho_so_nghia_vu_tai_chinh", "ho_so_do_dac", "gcn_dkdn", "tb_ket_qua_tthc"]),
    )
    assert all(it["target"] == "new" and it["needsAddComponent"] is True for it in items)
    # Cổng iGate VNPT: bấm "Chọn tệp tin" mở hộp thoại file của hệ điều hành → FE phải gán thẳng.
    assert all(it["noChooserClick"] is True for it in items)
    assert all("slotKey" not in it for it in items)
    # Mỗi tệp vẫn phải có documentName riêng để cán bộ đọc được nhật ký đính kèm.
    assert len({it["documentName"] for it in items}) == 5


def test_cccd_khong_dinh_kem_nhung_phai_canh_bao():
    items, warnings, classified = planner.build_plan_items(
        _files(["don.pdf", "cccd.jpg"]), _llm(["don_mau_02", "cccd"])
    )
    assert [it["fileName"] for it in items] == ["don.pdf"]
    assert any("cccd.jpg" in w for w in warnings)
    assert [c["target"] for c in classified if c["fileName"] == "cccd.jpg"] == ["skip"]


def test_canh_bao_khi_thieu_don_de_nghi():
    _, warnings, _ = planner.build_plan_items(_files(["gcn.pdf"]), _llm(["gcn"]))
    assert any("Đơn đề nghị" in w for w in warnings)
    # Có đơn rồi thì không cảnh báo thừa.
    _, warnings2, _ = planner.build_plan_items(
        _files(["don.pdf", "gcn.pdf"]), _llm(["don_mau_17", "gcn"])
    )
    assert not any("Đơn đề nghị" in w for w in warnings2)


def test_canh_bao_khi_ho_so_chuyen_muc_dich_thieu_giay_chung_nhan():
    _, warnings, _ = planner.build_plan_items(_files(["don.pdf"]), _llm(["don_mau_02"]))
    assert any("Giấy chứng nhận quyền sử dụng đất" in w for w in warnings)


def test_khong_bo_sot_file_nao_khi_llm_chet():
    items, warnings, _ = planner.build_plan_items(_files(["a.pdf", "b.pdf", "c.pdf"]), {})
    assert len(items) == 3
    assert all(it["target"] == "new" for it in items)
    assert any("Chưa nhận ra loại giấy tờ" in w for w in warnings)


def test_moi_nhan_llm_deu_duoc_xu_ly():
    """Nhãn có trong danh mục gửi LLM mà planner không biết đường đi là tệp rơi vào hư không."""
    labels = [label for label, _, _ in catalog.LABELS]
    assert all(catalog.is_valid(label) for label in labels)
    items, _, classified = planner.build_plan_items(
        _files([f"{label}.pdf" for label in labels]), _llm(labels)
    )
    assert len(classified) == len(labels)
    assert {c["target"] for c in classified} == {"fixed-slot", "new", "skip"}
    assert len(items) == len(labels) - len(catalog.SKIPPED_LABELS)
    fixed = {c["label"] for c in classified if c["target"] == "fixed-slot"}
    assert fixed == set(catalog.ROUTES)
    assert {c["label"] for c in classified if c["target"] == "skip"} == catalog.SKIPPED_LABELS


def test_moi_tuyen_deu_tro_vao_dong_co_that_va_slot_key_rieng():
    for label, position in catalog.ROUTES.items():
        assert position in catalog.ROWS, (label, position)
    keys = {catalog.slot(position)["slotKey"] for position in catalog.ROWS}
    assert len(keys) == len(catalog.ROWS)
    assert all(k.startswith("lc_115679_") for k in keys)


def test_don_labels_deu_co_dong_rieng():
    for label in catalog.DON_LABELS:
        assert catalog.is_valid(label) and label in catalog.ROUTES, label


# ---------------------------------------------------------------- hợp đồng slot với extension

# Text THẬT của bảng "Thành phần hồ sơ" bước 3, chép nguyên văn từ ảnh chụp cổng (ảnh ánh xạ đính kèm hồ sơ
# HS1). Đây là hợp đồng duy nhất giữa từ khóa của BE và DOM của cổng — cổng đổi câu chữ là test này đỏ ngay,
# thay vì FE lặng lẽ tích nhầm dòng.
_HDR_A = "a) Hồ sơ đề nghị chuyển mục đích sử dụng đất gồm:"
_HDR_B = "b) Hồ sơ đề nghị chuyển hình thức sử dụng đất gồm:"
_HDR_C = "c) Hồ sơ đề nghị gia hạn sử dụng đất khi hết thời hạn sử dụng đất gồm:"
_HDR_D = "d) Hồ sơ đề nghị điều chỉnh thời hạn sử dụng đất của dự án đầu tư gồm:"

_KHOAN_21 = (
    "Một trong các giấy chứng nhận quy định tại khoản 21 Điều 3, khoản 3 Điều 256 Luật Đất Đai hoặc một "
    "trong các giấy tờ quy định tại Điều 137 Luật Đất đai"
)
_QD_QUA_CAC_THOI_KY = (
    "Quyết định giao đất, quyết định cho thuê đất, quyết định cho phép chuyển mục đích sử dụng đất của cơ "
    "quan nhà nước có thẩm quyền theo quy định của pháp luật về đất đai qua các thời kỳ"
)

# Bảng theo ĐÚNG thứ tự dòng trên cổng: (có phải dòng tiêu đề nhóm không, text dòng).
_BANG_THAT: list[tuple[bool, str]] = [
    (True, _HDR_A),
    (False, "Đơn theo Mẫu số 02 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND"),
    (False, _KHOAN_21 + " hoặc quyết định giao đất, quyết định cho thuê đất, quyết định cho phép chuyển mục "
            "đích sử dụng đất của cơ quan nhà nước có thẩm quyền theo quy định của pháp luật về đất đai qua "
            "các thời kỳ; các tài liệu liên quan đến việc đáp ứng tiêu chí, điều kiện chuyển mục đích sử "
            "dụng đất trồng lúa, đất rừng phòng hộ, đất rừng đặc dụng, đất rừng sản xuất sang mục đích khác "
            "quy định tại khoản 1 Điều 46 Nghị định số 102/2024/NĐ-CP (nếu có)"),
    (True, _HDR_B),
    (False, "Đơn theo Mẫu số 03 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND"),
    (False, _KHOAN_21),
    (False, _QD_QUA_CAC_THOI_KY),
    (True, _HDR_C),
    (False, "Đơn theo Mẫu số 17 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND"),
    (False, _KHOAN_21),
    (False, "Quyết định giao đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất của cơ quan nhà nước "
            "có thẩm quyền theo quy định của pháp luật về đất đai qua các thời kỳ"),
    (False, "Văn bản của cơ quan có thẩm quyền cho phép gia hạn thời hạn hoạt động của dự án đầu tư hoặc "
            "thời hạn hoạt động của dự án đầu tư theo quy định của pháp luật về đầu tư đối với trường hợp "
            "sử dụng đất để thực hiện dự án đầu tư"),
    (True, _HDR_D),
    (False, "Văn bản của cơ quan có thẩm quyền cho phép thay đổi thời hạn hoạt động của dự án đầu tư theo "
            "quy định của pháp luật về đầu tư"),
    (False, "Một trong các giấy chứng nhận: Giấy chứng nhận quyền sử dụng đất, Giấy chứng nhận quyền sở hữu "
            "nhà ở và quyền sử dụng đất ở, Giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở và tài sản "
            "khác gắn liền với đất, Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất"),
    (False, "Quyết định giao đất, cho thuê đất, quyết định cho phép chuyển mục đích sử dụng đất của cơ quan "
            "nhà nước có thẩm quyền theo quy định của pháp luật về đất đai qua các thời kỳ"),
]

_TIEU_DE_COT = "# Tên giấy tờ Số bản (*) Tệp tin Mẫu đơn Ký số tệp tin"

# Vị trí (0-based) trong _BANG_THAT mà mỗi dòng của catalog phải trỏ tới.
_DONG_MONG_DOI = {
    catalog.ROW_DON_02: 1,
    catalog.ROW_DON_03: 4,
    catalog.ROW_DON_17: 8,
    catalog.ROW_VB_GIA_HAN: 11,
    catalog.ROW_VB_THAY_DOI: 13,
    catalog.ROW_GCN: 14,
    catalog.ROW_QUYET_DINH: 15,
}


def _vung_quet(header: str) -> list[int]:
    """Bản rút gọn fixedSlotSectionInputs() của content.js: lấy các dòng NẰM SAU dòng khớp header.

    FIXED_SLOT_SECTION_RE của extension chỉ nhận tiêu đề dạng "a) Đối với trường hợp…" / "(n) …" nên tiêu đề
    chữ cái "a) Hồ sơ đề nghị…" KHÔNG cắt vùng — vùng quét chạy tới cuối bảng. Nhóm d) là nhóm CUỐI nên vẫn
    đúng ba dòng cuối.
    """
    folded = _norm(header)
    rows = [_norm(text) for _, text in _BANG_THAT]
    if folded in _norm(_TIEU_DE_COT):
        return list(range(len(rows)))
    start = next(i for i, text in enumerate(rows) if folded in text)
    return list(range(start + 1, len(rows)))


def test_tu_khoa_khop_dung_mot_dong_that_trong_vung_quet_cua_no():
    for position, (keywords, header, _) in catalog.ROWS.items():
        vung = _vung_quet(header)
        hits = [i for i in vung if any(kw in _norm(_BANG_THAT[i][1]) for kw in keywords)]
        assert hits == [_DONG_MONG_DOI[position]], (position, keywords, hits)


def test_tu_khoa_khong_dinh_vao_dong_tieu_de_nhom():
    """Tích nhầm dòng tiêu đề nhóm là cổng nhận một thành phần hồ sơ không có thật."""
    headers = [_norm(text) for is_header, text in _BANG_THAT if is_header]
    for keywords, _, _ in catalog.ROWS.values():
        for keyword in keywords:
            assert not any(keyword in h for h in headers), keyword


def test_tieu_de_neo_vung_co_that_tren_bang_va_khong_khop_dong_du_lieu():
    """FE lấy các dòng NẰM SAU dòng khớp sectionHeader; header mà khớp cả dòng dữ liệu là khoanh vùng hụt."""
    assert catalog.HEADER_BANG in _norm(_TIEU_DE_COT)
    assert any(catalog.HEADER_NHOM_D in _norm(text) for _, text in _BANG_THAT)
    for _, text in _BANG_THAT:
        assert catalog.HEADER_BANG not in _norm(text)
    # Nhóm d) phải là nhóm CUỐI, nếu không vùng quét sẽ tràn sang nhóm khác.
    d_index = next(i for i, (_, text) in enumerate(_BANG_THAT) if catalog.HEADER_NHOM_D in _norm(text))
    assert not any(is_header for is_header, _ in _BANG_THAT[d_index + 1:])
