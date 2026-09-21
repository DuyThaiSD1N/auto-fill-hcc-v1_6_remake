"""[Lào Cai] Đăng ký đất đai, tài sản gắn liền với đất, cấp GCN lần đầu 1.115688 — eForm iGate
(CongDan_*/ChuHoSo_*) + đính kèm fixed-slot bảng phẳng khớp theo từ khóa dòng.

Khoá năm điều dễ vỡ:
  1. Hồ sơ TỔ CHỨC (HS01, HS02) phải ra nhánh ô tổ chức; hồ sơ CÁ NHÂN (HS03) ra nhánh ô cá nhân — chọn sai
     ô "Đối tượng nộp hồ sơ" là cổng hiện nhầm nhóm trường bắt buộc.
  2. Hồ sơ NỘP THAY (HS02: Giáo xứ Sa Pa uỷ quyền cho ông Phan Duy Khánh): khối người nộp là người được uỷ
     quyền, khối chủ hồ sơ là tổ chức — lẫn hai bên là hồ sơ sai chủ thể mà nhìn vào vẫn thấy "đủ dữ liệu".
  3. Không phát ô readonly (Họ tên/Số Căn cước) và không tích "Người nộp là chủ hồ sơ".
  4. Di động/Email trên Đơn là của người sử dụng đất → chỉ chép sang khối người nộp khi tự nộp.
  5. Từ khóa từng dòng thành phần hồ sơ phải khớp ĐÚNG dòng của nó trên DOM thật (cổng render số dòng khác
     nhau giữa biến thể tổ chức và cá nhân).
"""

import re
import unicodedata

from app.pipelines.dk_dat_dai_gan_tai_san_lao_cai.attach import catalog, planner
from app.pipelines.dk_dat_dai_gan_tai_san_lao_cai.process import mapper
from app.pipelines.dk_dat_dai_gan_tai_san_lao_cai.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import public_list

_KEY = "dang-ky-dat-dai-cap-gcn-lan-dau-to-chuc"
_URL_LAO_CAI = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"

# HS03 của "Mapping_1.115688_DangKyDatDai_LanDau_LaoCai.xlsx": ông Lý Quốc Luân tự nộp, đồng sử dụng với bà
# Vũ Thị Tơ (chỉ kê ở Mẫu 15a — form chỉ nhận một chủ hồ sơ).
_LY_QUOC_LUAN = {
    "HoTen": "Lý Quốc Luân",
    "SoDinhDanh": "010089001379",
    "NgaySinh": "27/11/1989",
    "GioiTinh": "Nam",
    "NgayCap": "25/04/2021",
    "NoiCap": "Cục cảnh sát QLHC về TTXH",
    "NoiCuTru": {"tinh": "Lào Cai", "xa": "Sa Pa", "diaChi": "Tổ dân phố Sa Pả 1"},
}
_VU_THI_TO = {
    "HoTen": "Vũ Thị Tơ",
    "SoDinhDanh": "010164001085",
    "NgaySinh": "1961",
    "GioiTinh": "Nữ",
    "NoiCuTru": {"tinh": "Lào Cai", "xa": "Sa Pa", "diaChi": "Tổ dân phố Sa Pả 1"},
}
_CTX_HS03 = {"formContext": {"applicantIdentityNumber": "010089001379", "applicantFullname": "LÝ QUỐC LUÂN"}}


def _ho_so_ca_nhan():
    return [
        {"name": "NguoiTrongGiayTo", "value": [_LY_QUOC_LUAN, _VU_THI_TO]},
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
        {"name": "ChuHoSo_HoTen", "value": "Lý Quốc Luân"},
        {"name": "ChuHoSo_XungHo", "value": "Ông"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "0100 8900 1379"},
        {"name": "ChuHoSo_NgaySinh", "value": "27/11/1989"},
        {"name": "ChuHoSo_NgayCap", "value": "25/04/2021"},
        {"name": "ChuHoSo_NoiCap", "value": "Cục cảnh sát QLHC về TTXH"},
        {"name": "ChuHoSo_DiaChiDon",
         "value": {"tinh": "Lào Cai", "xa": "Sa Pa", "diaChi": "Tổ dân phố Sa Pả 1"}},
        {"name": "Don_DienThoai", "value": "0983938459"},
    ]


# HS01: Ban Quản lý rừng phòng hộ khu vực Bát Xát (đơn vị sự nghiệp công lập) — ông Nguyễn Bá Hà ký Đơn M15.
def _ho_so_to_chuc():
    return [
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cơ quan nhà nước"},
        {"name": "ChuHoSo_TenToChuc", "value": "Ban Quản lý rừng phòng hộ khu vực Bát Xát"},
        {"name": "ChuHoSo_DiaChiDon",
         "value": {"tinh": "Lào Cai", "xa": "Lào Cai", "diaChi": "Số 336, Nhạc Sơn Cốc Lếu"}},
        {"name": "Don_DienThoai", "value": "0983938459"},
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
    """Bản rút gọn luật nhận diện của popup.js (urlScope → textIncludes, chọn cụm dài nhất)."""
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


# Tên thủ tục THẬT in trên trang nộp hồ sơ của cổng Lào Cai.
_TIEU_DE_TRANG = (
    "Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản "
    "gắn liền với đất lần đầu đối với tổ chức đang sử dụng đất"
)


# ---------------------------------------------------------------- registry & nhận diện


def test_co_trong_registry_va_khoa_dung_cong_lao_cai():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["detect"]["urlScope"] == ["laocai.gov.vn"]
    assert entry["label"].startswith("[Lào Cai]")


def test_key_trung_muc_ke_khai_links_1_115688():
    """Key phải khớp danh mục link để popup chọn link cũng chọn luôn pipeline điền."""
    from app.procedures.ke_khai_links import KE_KHAI_LINKS

    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.115688"
    # Thủ tục nộp ở Phường/Xã: bật selectSo là popup tick radio "Sở" rồi bỏ hẳn ô Phường/Xã.
    assert not link.get("selectSo")
    assert link.get("needsAgencySelect") is True


def test_trang_1_115688_lao_cai_nhan_dung_thu_tuc():
    assert _detect(_URL_LAO_CAI, _TIEU_DE_TRANG) == _KEY


def test_khong_cuop_trang_cac_thu_tuc_dat_dai_khac_cung_cong_lao_cai():
    khac = {
        "thu-hoi-gcn-cap-lan-dau-khong-dung-quy-dinh-cap-lai": (
            "Thu hồi Giấy chứng nhận đã cấp lần đầu không đúng quy định của pháp luật đất đai do người sử "
            "dụng đất, chủ sở hữu tài sản gắn liền với đất phát hiện và cấp lại Giấy chứng nhận sau khi thu hồi"
        ),
        "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai": (
            "Đăng ký, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất cho người "
            "nhận chuyển nhượng quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng trong dự án bất "
            "động sản"
        ),
        "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep": "Xác nhận tiếp tục sử dụng đất nông nghiệp",
    }
    for key, body in khac.items():
        assert _detect(_URL_LAO_CAI, body) == key, key


def test_cong_tinh_khac_khong_dinh_vao_pipeline_lao_cai():
    """1.115688 là mã QUỐC GIA, cổng iGate tỉnh khác dùng đúng tên đó → urlScope phải chặn."""
    assert _detect("https://dichvucong.bacninh.gov.vn/x", _TIEU_DE_TRANG) != _KEY
    assert _detect("https://dichvucong.laichau.gov.vn/x", _TIEU_DE_TRANG) != _KEY


# ---------------------------------------------------------------- bước 2: điền thông tin


def test_ho_so_ca_nhan_tu_nop_dien_du_hai_khoi():
    values = _names(mapper.enrich(_ho_so_ca_nhan(), _CTX_HS03))
    assert values["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert values["ChuHoSo_tenChuHoSo"] == "LÝ QUỐC LUÂN"
    # Đơn ghi cách nhóm 4 số "0100 8900 1379" → phải về liền 12 chữ số.
    assert values["ChuHoSo_soCMNDChuHoSo"] == "010089001379"
    assert values["ChuHoSo_gioiTinhChuHoSo"] == "Nam"
    assert values["ChuHoSo_ngaySinhChuHoSo"] == "27/11/1989"
    assert values["ChuHoSo_ngayCapCMNDCHS"] == "25/04/2021"
    assert values["ChuHoSo_diaChiChuHoSo"] == "Tổ dân phố Sa Pả 1"
    # Người nộp chính là chủ hồ sơ → khối người nộp lấy nhân thân của chính người đó.
    assert values["CongDan_ngaySinhCongDan"] == "27/11/1989"
    assert values["CongDan_diaChi"] == "Tổ dân phố Sa Pả 1"


def test_nguoi_dong_su_dung_dat_khong_bi_ghep_vao_chu_ho_so():
    """Form chỉ nhận MỘT chủ hồ sơ; bà Vũ Thị Tơ chỉ được kê ở Mẫu 15a."""
    values = _names(mapper.enrich(_ho_so_ca_nhan(), _CTX_HS03))
    assert values["ChuHoSo_tenChuHoSo"] == "LÝ QUỐC LUÂN"
    assert values["ChuHoSo_soCMNDChuHoSo"] != "010164001085"


def test_o_bat_buoc_ma_cong_de_trong_duoc_dien():
    """"Số nhà/Đường/Tổ/Thôn" và "Di động" của khối người nộp là (*) mà cổng để trống."""
    values = _names(mapper.enrich(_ho_so_ca_nhan(), _CTX_HS03))
    assert values["CongDan_diaChi"] == "Tổ dân phố Sa Pả 1"
    assert values["CongDan_diDong"] == "0983938459"


def test_nop_thay_khong_chep_so_dien_thoai_cua_chu_ho_so_sang_nguoi_nop():
    """Số trên Đơn là của người sử dụng đất; nộp thay mà chép sang là cổng báo tin về sai người."""
    values = _names(mapper.enrich(
        _ho_so_ca_nhan(),
        {"formContext": {"applicantIdentityNumber": "001091000123", "applicantFullname": "NGUYỄN VĂN A"}},
    ))
    assert "CongDan_diDong" not in values
    assert "CongDan_email" not in values
    # Khối chủ hồ sơ vẫn giữ số đó.
    assert values["ChuHoSo_diDongLienLacCHS"] == "0983938459"


def test_khong_phat_lai_o_readonly_va_khong_tich_nguoi_nop_la_chu_ho_so():
    values = _names(mapper.enrich(_ho_so_ca_nhan(), _CTX_HS03))
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    # Tích ô này là cổng ÉP Đối tượng = Cá nhân rồi chép đè khối chủ hồ sơ.
    assert "chkbox_nguoinoplachuhs" not in values


def test_nguoi_nop_khong_lay_nham_nhan_than_khi_khong_biet_tai_khoan():
    """Không đọc được tài khoản đang đăng nhập thì thà bỏ trống còn hơn gán bừa một người trong hồ sơ."""
    values = _names(mapper.enrich(_ho_so_ca_nhan(), {}))
    for name in ("CongDan_ngaySinhCongDan", "CongDan_ngayCapCmnd", "CongDan_maTinhThanh", "CongDan_diaChi"):
        assert name not in values


def test_tinh_phat_truoc_xa_o_ca_hai_khoi():
    """Danh sách Phường/Xã chỉ nạp AJAX sau khi chọn tỉnh; phát ngược là ô xã rỗng."""
    order = _order(mapper.enrich(_ho_so_ca_nhan(), _CTX_HS03))
    assert order.index("CongDan_maTinhThanh") < order.index("CongDan_maPhuongXa")
    assert order.index("ChuHoSo_maTinhThanhCHS") < order.index("ChuHoSo_maPhuongXaCHS")


def test_ho_so_to_chuc_chon_dung_nhom_o_va_khong_bia_ca_nhan():
    values = _names(mapper.enrich(_ho_so_to_chuc(), {}))
    assert values["ChuHoSo_maDoiTuongNopHS"] == "CQ"
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == "Ban Quản lý rừng phòng hộ khu vực Bát Xát"
    assert values["ChuHoSo_diaChiChuHoSo"] == "Số 336, Nhạc Sơn Cốc Lếu"
    # Người nộp đứng ra đại diện cho chính tổ chức chủ hồ sơ.
    assert values["CongDan_tenCoQuanToChuc"] == "Ban Quản lý rừng phòng hộ khu vực Bát Xát"
    assert "ChuHoSo_tenChuHoSo" not in values
    assert "ChuHoSo_soCMNDChuHoSo" not in values


def test_ho_so_to_chuc_ton_giao_nop_thay_khong_lan_hai_chu_the():
    """HS02: chủ hồ sơ là Giáo xứ Sa Pa, ông Phan Duy Khánh chỉ là người được uỷ quyền đi nộp."""
    khanh = {
        "HoTen": "Phan Duy Khánh",
        "SoDinhDanh": "001091000123",
        "NgayCap": "12/05/2021",
        "NoiCap": "Cục cảnh sát QLHC về TTXH",
        "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 2 Xuân Tăng"},
    }
    values = _names(mapper.enrich(
        [
            {"name": "NguoiTrongGiayTo", "value": [khanh]},
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức khác"},
            {"name": "ChuHoSo_TenToChuc", "value": "Giáo xứ Sa Pa"},
            {"name": "ChuHoSo_DiaChiUyQuyen",
             "value": {"tinh": "Lào Cai", "xa": "Sa Pa", "diaChi": "Giáo xứ Sa Pa, Tổ dân phố Sa Pa 07"}},
        ],
        {"formContext": {"applicantIdentityNumber": "001091000123", "applicantFullname": "PHAN DUY KHÁNH"}},
    ))
    assert values["ChuHoSo_maDoiTuongNopHS"] == "TC"
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == "Giáo xứ Sa Pa"
    # Địa chỉ chủ hồ sơ theo Giấy uỷ quyền (trụ sở giáo xứ), KHÔNG phải nơi ở của người đi nộp.
    assert values["ChuHoSo_diaChiChuHoSo"] == "Giáo xứ Sa Pa, Tổ dân phố Sa Pa 07"
    # Khối người nộp là của ông Khánh.
    assert values["CongDan_diaChi"] == "Tổ 2 Xuân Tăng"
    assert values["CongDan_ngayCapCmnd"] == "12/05/2021"


def test_khong_bia_ngay_thang_khi_chi_co_nam():
    """Mẫu 15a chỉ có cột "Năm sinh" → ô DD/MM/YYYY phải bỏ trống, không tự thêm 01/01."""
    values = _names(mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
            {"name": "ChuHoSo_HoTen", "value": "Vũ Thị Tơ"},
            {"name": "ChuHoSo_SoDinhDanh", "value": "010164001085"},
            {"name": "ChuHoSo_NgaySinh", "value": "1961"},
        ],
        {},
    ))
    assert "ChuHoSo_ngaySinhChuHoSo" not in values


def test_khong_nham_so_quyet_dinh_voi_so_dinh_danh():
    """"2733/QĐ-UBND", "64/BC-BQL" lọt vào ô Số Căn cước là hồ sơ sai người mà không ai soát ra."""
    values = _names(mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
            {"name": "ChuHoSo_HoTen", "value": "Lý Quốc Luân"},
            {"name": "ChuHoSo_SoDinhDanh", "value": "2733/QĐ-UBND"},
        ],
        {},
    ))
    assert "ChuHoSo_soCMNDChuHoSo" not in values
    # Thiếu số định danh thì chưa đủ để khẳng định chủ hồ sơ → không phát cả khối, tránh điền nửa vời.
    assert "ChuHoSo_tenChuHoSo" not in values


def test_doan_lai_doi_tuong_khi_llm_tra_nhan_chung_chung():
    assert mapper.org_option("Tổ chức", "Ban Quản lý rừng phòng hộ khu vực Bát Xát") == "CQ"
    assert mapper.org_option("", "Giáo xứ Sa Pa") == "TC"
    assert mapper.org_option("", "Công ty TNHH Một thành viên X") == "DN"


def test_ui_comp_chi_khai_o_cua_buoc_2():
    for name in UI_COMP_BY_NAME:
        assert name.startswith(("CongDan_", "ChuHoSo_")), name


# ---------------------------------------------------------------- bước 3: đính kèm


def test_cac_dong_co_dinh_nhan_dung_tep():
    items, _, classified = planner.build_plan_items(
        _files(["don_m15.pdf", "trich_luc.pdf", "bao_cao_15d.pdf", "bien_lai.pdf"]),
        _llm(["don_dang_ky", "trich_luc", "bao_cao_ra_soat", "chung_tu_tai_chinh"]),
    )
    by_file = {it["fileName"]: it for it in items}
    assert by_file["don_m15.pdf"]["slotKey"] == "lc_115688_1"
    assert by_file["trich_luc.pdf"]["slotKey"] == "lc_115688_4"
    assert by_file["bao_cao_15d.pdf"]["slotKey"] == "lc_115688_5"
    assert by_file["bien_lai.pdf"]["slotKey"] == "lc_115688_7"
    assert all(it["target"] == "fixed-slot" and it["tickRow"] is True for it in items)
    # Bảng không có tiêu đề nhóm → phải neo vào tiêu đề cột thì FE mới dùng slotKeywords của BE.
    assert all(it["sectionHeader"] == catalog.SECTION_HEADER for it in items)
    assert [c["target"] for c in classified] == ["fixed-slot"] * 4


def test_danh_sach_15a_15b_gom_chung_dong_don():
    """Mẫu 15a/15b là phụ lục của Đơn → cùng slotKey để FE gom một lần bơm tệp."""
    items, _, _ = planner.build_plan_items(
        _files(["don_m15.pdf", "ds_15b.pdf"]), _llm(["don_dang_ky", "danh_sach_kem_don"])
    )
    assert {it["slotKey"] for it in items} == {"lc_115688_1"}
    # Mỗi tệp vẫn phải có documentName riêng để cán bộ đọc được nhật ký đính kèm.
    assert len({it["documentName"] for it in items}) == 2


def test_giay_to_khong_co_dong_rieng_xuong_giay_to_khac():
    """Quyết định thành lập/phê duyệt phương án, giấy uỷ quyền, đơn đề nghị xác nhận đều là "Giấy tờ khác"
    — đúng như ảnh cổng thật của hồ sơ HS01."""
    items, _, _ = planner.build_plan_items(
        _files(["qd_2733.pdf", "qd_1830.pdf", "uy_quyen.pdf", "don_de_nghi_xn.pdf"]),
        _llm(["qd_thanh_lap_to_chuc", "qd_phuong_an_su_dung_dat", "van_ban_dai_dien", "don_de_nghi_xac_nhan"]),
    )
    assert all(it["target"] == "new" and it["needsAddComponent"] is True for it in items)
    # Cổng iGate VNPT: bấm "Chọn tệp tin" mở hộp thoại file của hệ điều hành → FE phải gán thẳng.
    assert all(it["noChooserClick"] is True for it in items)
    assert all("slotKey" not in it for it in items)


def test_cccd_khong_dinh_kem_nhung_phai_canh_bao():
    items, warnings, classified = planner.build_plan_items(
        _files(["don_m15.pdf", "cccd.jpg"]), _llm(["don_dang_ky", "cccd"])
    )
    assert [it["fileName"] for it in items] == ["don_m15.pdf"]
    assert any("cccd.jpg" in w for w in warnings)
    assert [c["target"] for c in classified if c["fileName"] == "cccd.jpg"] == ["skip"]


def test_canh_bao_khi_thieu_don_dang_ky():
    _, warnings, _ = planner.build_plan_items(_files(["trich_luc.pdf"]), _llm(["trich_luc"]))
    assert any("Đơn đăng ký đất đai" in w for w in warnings)


def test_canh_bao_tep_quet_gop_de_can_bo_biet_dong_trong_la_co_chu_y():
    """HS01/HS03 đều gộp cả bộ vào một PDF; mỗi tệp chỉ vào một dòng nên phải nói rõ dòng nào còn trống."""
    _, warnings, _ = planner.build_plan_items(_files(["ca_bo_ho_so.pdf"]), _llm(["don_dang_ky"]))
    assert any("Trích lục" in w for w in warnings)
    assert any("Báo cáo kết quả rà soát" in w for w in warnings)
    # Có tệp riêng rồi thì không cảnh báo thừa.
    _, warnings2, _ = planner.build_plan_items(
        _files(["don.pdf", "trich_luc.pdf", "bao_cao.pdf", "ds.pdf"]),
        _llm(["don_dang_ky", "trich_luc", "bao_cao_ra_soat", "danh_sach_kem_don"]),
    )
    assert not any("thường quét gộp" in w for w in warnings2)


def test_khong_bo_sot_file_nao_khi_llm_chet():
    items, warnings, _ = planner.build_plan_items(_files(["a.pdf", "b.pdf", "c.pdf"]), {})
    assert len(items) == 3
    assert all(it["target"] == "new" for it in items)
    assert any("Chưa nhận ra loại giấy tờ" in w for w in warnings)


# ---------------------------------------------------------------- hợp đồng slot với extension

# Text THẬT của bảng "Thành phần hồ sơ" trên cổng — gộp cả hai biến thể đã chụp được (ảnh hướng dẫn hồ sơ cá
# nhân HS03 và ảnh cổng thật hồ sơ tổ chức HS01). Đây là hợp đồng duy nhất giữa từ khóa của BE và DOM của
# cổng — cổng đổi câu chữ là test này đỏ ngay, thay vì FE lặng lẽ tích nhầm dòng.
_DONG_THAT = {
    catalog.ROW_DON: "Đơn đăng ký đất đai, tài sản gắn liền với đất theo Mẫu số 21 ban hành kèm theo Quyết "
                     "định số 47/2026/QĐ-UBND",
    catalog.ROW_GIAY_TO_QSDD: "Một trong các loại giấy tờ quy định tại Điều 137, khoản 4, khoản 5 Điều 148, "
                              "khoản 4, khoản 5 Điều 149 Luật Đất đai (nếu có); Trường hợp chủ đầu tư xây "
                              "dựng nhà ở để kinh doanh quy định tại khoản 4 Điều 148 của Luật Đất đai hoặc "
                              "chủ đầu tư xây dựng công trình xây dựng quy định tại khoản 4 Điều 149 của "
                              "Luật Đất đai đề nghị chứng nhận quyền sở hữu nhà ở, quyền sở hữu công trình "
                              "xây dựng thì phải có quyết định phê duyệt dự án; sơ đồ tài sản đề nghị chứng "
                              "nhận quyền sở hữu",
    catalog.ROW_THUA_KE: "Giấy tờ về việc nhận thừa kế quyền sử dụng đất theo quy định của pháp luật về dân "
                         "sự đối với người gốc Việt Nam định cư ở nước ngoài",
    catalog.ROW_TRICH_LUC: "Sơ đồ hoặc bản trích lục bản đồ địa chính hoặc mảnh trích đo bản đồ địa chính "
                           "thửa đất (nếu có); mảnh trích đo bản đồ địa chính thửa đất (nếu có) đối với "
                           "người gốc Việt Nam định cư ở nước ngoài",
    catalog.ROW_BAO_CAO_RA_SOAT: "Báo cáo kết quả rà soát hiện trạng sử dụng đất theo Mẫu số 21d ban hành "
                                 "kèm theo Quyết định số 47/2026/QĐ-UBND đối với trường hợp tổ chức trong "
                                 "nước, tổ chức tôn giáo, tổ chức tôn giáo trực thuộc đang sử dụng đất",
    catalog.ROW_THIET_KE: "Hồ sơ thiết kế xây dựng công trình đã được cơ quan chuyên môn về xây dựng thẩm "
                          "định hoặc đã có văn bản chấp thuận kết quả nghiệm thu hoàn thành hạng mục công "
                          "trình, công trình xây dựng theo quy định của pháp luật về xây dựng đối với "
                          "trường hợp chứng nhận quyền sở hữu công trình xây dựng trên đất nông nghiệp mà "
                          "chủ sở hữu công trình không có một trong các loại giấy tờ quy định tại Điều 149 "
                          "Luật Đất đai hoặc công trình được miễn giấy phép xây dựng theo quy định của "
                          "pháp luật về xây dựng",
    catalog.ROW_NGHIA_VU_TAI_CHINH: "Chứng từ thực hiện nghĩa vụ tài chính, giấy tờ liên quan đến việc "
                                    "miễn, giảm nghĩa vụ tài chính về đất đai, tài sản gắn liền với đất "
                                    "(nếu có)",
    catalog.ROW_QUOC_PHONG: "Quyết định vị trí đóng quân hoặc văn bản giao cơ sở nhà đất hoặc địa điểm công "
                            "trình quốc phòng, an ninh được cấp có thẩm quyền phê duyệt cho đơn vị quân "
                            "đội, đơn vị công an, đơn vị sự nghiệp công lập thuộc Quân đội nhân dân, Công "
                            "an nhân dân; doanh nghiệp nhà nước do Bộ Quốc phòng, Bộ Công an được giao "
                            "quản lý, sử dụng đất, công trình gắn liền với đất",
}
# Hai biến thể tiêu đề cột đã chụp được (bản có cột "Mẫu đơn" và bản có cột "Loại").
_TIEU_DE_COT = [
    "# Tên giấy tờ Số bản (*) Tệp tin Mẫu đơn Ký số tệp tin",
    "# Tên giấy tờ Số bản (*) Loại Tệp tin Ký số tệp tin",
]


def test_tu_khoa_khop_dung_mot_dong_that():
    folded = {pos: _norm(text) for pos, text in _DONG_THAT.items()}
    for position, (keywords, _) in catalog.ROWS.items():
        hits = [pos for pos, text in folded.items() if any(kw in text for kw in keywords)]
        assert hits == [position], (position, keywords, hits)


def test_section_header_la_tieu_de_cot_va_khong_khop_dong_nao():
    """FE lấy các dòng NẰM SAU dòng khớp sectionHeader; header mà khớp cả dòng dữ liệu là khoanh vùng hụt."""
    for header in _TIEU_DE_COT:
        assert catalog.SECTION_HEADER in _norm(header)
        for keywords, _ in catalog.ROWS.values():
            for keyword in keywords:
                assert keyword not in _norm(header), keyword
    for text in _DONG_THAT.values():
        assert catalog.SECTION_HEADER not in _norm(text)


def test_moi_tuyen_deu_tro_vao_dong_co_that_va_slot_key_rieng():
    for label, position in catalog.ROUTES.items():
        assert position in catalog.ROWS, (label, position)
    keys = {catalog.slot(position)["slotKey"] for position in catalog.ROWS}
    assert len(keys) == len(catalog.ROWS)
    assert all(k.startswith("lc_115688_") for k in keys)


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


def test_merged_hints_tro_vao_nhan_va_dong_co_that():
    for label, (host_label, _) in catalog.MERGED_HINTS.items():
        assert label in catalog.ROUTES, label
        assert catalog.is_valid(host_label), host_label
