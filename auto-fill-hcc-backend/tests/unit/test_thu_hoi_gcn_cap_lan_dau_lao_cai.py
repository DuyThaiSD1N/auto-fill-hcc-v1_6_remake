"""[Lào Cai] Thu hồi GCN cấp lần đầu không đúng quy định, cấp lại 1.115687 — eForm iGate
(CongDan_*/ChuHoSo_*) + đính kèm fixed-slot bảng phẳng 2 dòng.

Khoá bốn điều dễ vỡ:
  1. Hồ sơ NỘP THAY: khối người nộp là Bên B của Giấy ủy quyền, khối chủ hồ sơ là Bên A — lẫn hai người là
     hồ sơ mang nhân thân sai mà nhìn vào vẫn thấy "đủ dữ liệu".
  2. Ba ô địa chỉ của khối NGƯỜI NỘP ở thủ tục này là bắt buộc (*) và cổng để trống (khác 1.115651/1.115671),
     phải điền theo nơi thường trú của chính người đi nộp.
  3. Không phát ô readonly (Họ tên/Số Căn cước) và không tích "Người nộp là chủ hồ sơ".
  4. Từ khóa hai dòng thành phần hồ sơ phải khớp ĐÚNG dòng của nó trên DOM thật.
"""

import re
import unicodedata

from app.pipelines.thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai.attach import catalog, planner
from app.pipelines.thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai.process import mapper
from app.pipelines.thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import public_list

_KEY = "thu-hoi-gcn-cap-lan-dau-khong-dung-quy-dinh-cap-lai"
_URL_LAO_CAI = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"

# Hồ sơ mẫu 1 của "mapping_thu_hoi_huy_GCN_laocai.xlsx": bà Trần Thị Tâm đứng đơn, ông Nguyễn Văn Hợi (Bên B
# của Giấy ủy quyền số công chứng 732/2026/CCGD) đi nộp thay.
_NGUOI_NOP = {
    "HoTen": "Nguyễn Văn Hợi",
    "SoDinhDanh": "015079007147",
    "NgaySinh": "09/04/1979",
    "GioiTinh": "Nam",
    "NgayCap": "06/09/2021",
    "NoiCap": "Cục cảnh sát Quản lý hành chính về trật tự xã hội",
    "NoiCuTru": {"tinh": "Lào Cai", "xa": "Yên Bình", "diaChi": "Thôn 4"},
}
_CHU_HO_SO = {
    "HoTen": "Trần Thị Tâm",
    "SoDinhDanh": "035150002037",
    "NgaySinh": "15/09/1950",
    "GioiTinh": "Nữ",
    "NgayCap": "27/03/2021",
    "NoiCap": "Cục cảnh sát Quản lý hành chính về trật tự xã hội",
    "NoiCuTru": {"tinh": "Lào Cai", "xa": "Yên Bình", "diaChi": "Thôn 4"},
}
_CTX = {"formContext": {"applicantIdentityNumber": "015079007147", "applicantFullname": "NGUYỄN VĂN HỢI"}}


def _ho_so_nop_thay():
    return [
        {"name": "NguoiTrongGiayTo", "value": [_NGUOI_NOP, _CHU_HO_SO]},
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
        {"name": "ChuHoSo_HoTen", "value": "Trần Thị Tâm"},
        {"name": "ChuHoSo_XungHo", "value": "Bà"},
        {"name": "ChuHoSo_SoDinhDanh", "value": "035150002037"},
        {"name": "ChuHoSo_NgaySinh", "value": "15/09/1950"},
        {"name": "ChuHoSo_NgayCap", "value": "27/03/2021"},
        {"name": "ChuHoSo_NoiCap", "value": "Cục cảnh sát Quản lý hành chính về trật tự xã hội"},
        {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Yên Bình", "diaChi": "Thôn 4"}},
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
    "Thu hồi Giấy chứng nhận đã cấp lần đầu không đúng quy định của pháp luật đất đai do người sử dụng đất, "
    "chủ sở hữu tài sản gắn liền với đất phát hiện và cấp lại Giấy chứng nhận sau khi thu hồi"
)


# ---------------------------------------------------------------- registry & nhận diện


def test_co_trong_registry_va_khoa_dung_cong_lao_cai():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["detect"]["urlScope"] == ["laocai.gov.vn"]
    assert entry["label"].startswith("[Lào Cai]")


def test_key_trung_muc_ke_khai_links_1_115687():
    """Key phải khớp danh mục link để popup chọn link cũng chọn luôn pipeline điền."""
    from app.procedures.ke_khai_links import KE_KHAI_LINKS

    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.115687"


def test_khong_tick_so_o_khoi_chon_co_quan():
    """1.115687 và 1.115688 nộp ở Phường/Xã, KHÔNG phải cấp Sở.

    `selectSo` bật là popup (selectSoFor → agencyProvinceOnly) tick radio "Sở" rồi lấy option đầu
    trong dropdown, BỎ HẲN ô Phường/Xã — hồ sơ đi lạc cấp tiếp nhận ngay từ bước chọn cơ quan mà
    trên màn hình vẫn trông như đã chọn xong. Các thủ tục đất đai Lào Cai khác đều là cấp Sở nên
    rất dễ chép nhầm cấu hình sang hai thủ tục này.
    """
    from app.procedures.ke_khai_links import KE_KHAI_LINKS

    for code in ("1.115687", "1.115688"):
        link = next(item for item in KE_KHAI_LINKS if item.get("code") == code)
        assert not link.get("selectSo"), code
        assert not link.get("selectSoProvinces"), code
        # Vẫn phải qua khối "Chọn cơ quan thực hiện" — chỉ khác là chọn Tỉnh + Phường/Xã.
        assert link.get("needsAgencySelect") is True, code


def test_trang_1_115687_lao_cai_nhan_dung_thu_tuc():
    assert _detect(_URL_LAO_CAI, _TIEU_DE_TRANG) == _KEY


def test_khong_cuop_trang_1_115671_cung_cong_lao_cai():
    body = (
        "Đăng ký biến động đối với trường hợp thay đổi quyền sử dụng đất, quyền sở hữu tài sản gắn liền với "
        "đất theo thỏa thuận của các thành viên hộ gia đình hoặc của vợ và chồng"
    )
    assert _detect(_URL_LAO_CAI, body) != _KEY


def test_cong_tinh_khac_khong_dinh_vao_pipeline_lao_cai():
    """1.115687 là mã QUỐC GIA; bản Bắc Ninh là DOM Liferay khác hẳn → urlScope phải chặn."""
    assert _detect("https://dichvucong.bacninh.gov.vn/x", _TIEU_DE_TRANG) != _KEY


def test_ban_bac_ninh_nhan_dien_bang_url_nen_khong_va_cham_text():
    """Bản Bắc Ninh của cùng thủ tục chốt theo maThuTucHanhChinh, không theo text → hai bên không giẫm nhau."""
    bac_ninh = next(p for p in public_list() if p["key"] == "thu-hoi-gcn-cap-sai-bac-ninh")
    assert not bac_ninh["detect"].get("textIncludes")
    assert bac_ninh["detect"]["urlScope"] == ["dichvucong.bacninh.gov.vn"]


# ---------------------------------------------------------------- bước 2: điền thông tin


def test_ho_so_nop_thay_khong_lan_nguoi_nop_voi_chu_ho_so():
    values = _names(mapper.enrich(_ho_so_nop_thay(), _CTX))
    # Khối người nộp = ông Hợi (Bên B của Giấy ủy quyền, cũng là tài khoản đang đăng nhập).
    assert values["CongDan_ngaySinhCongDan"] == "09/04/1979"
    assert values["CongDan_gioiTinhCongDan"] == "Nam"
    assert values["CongDan_ngayCapCmnd"] == "06/09/2021"
    # Khối chủ hồ sơ = bà Tâm (Bên A, người đứng đơn).
    assert values["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert values["ChuHoSo_tenChuHoSo"] == "TRẦN THỊ TÂM"
    assert values["ChuHoSo_soCMNDChuHoSo"] == "035150002037"
    assert values["ChuHoSo_gioiTinhChuHoSo"] == "Nữ"
    assert values["ChuHoSo_ngaySinhChuHoSo"] == "15/09/1950"
    assert values["ChuHoSo_ngayCapCMNDCHS"] == "27/03/2021"


def test_dia_chi_khoi_nguoi_nop_duoc_dien_vi_cong_de_trong_va_bat_buoc():
    """Khác 1.115651/1.115671: ba ô này (*) mà cổng không đổ sẵn → bỏ trống là cổng chặn Tiếp tục."""
    values = _names(mapper.enrich(_ho_so_nop_thay(), _CTX))
    assert values["CongDan_maTinhThanh"] == "Tỉnh Lào Cai"
    assert values["CongDan_maPhuongXa"] == "Xã Yên Bình"
    assert values["CongDan_diaChi"] == "Thôn 4"


def test_khong_phat_lai_o_readonly_va_khong_tich_nguoi_nop_la_chu_ho_so():
    """Sửa "Họ và tên"/"Số Căn cước" là cổng xoá trắng Di động + CCCD; tích checkbox là cổng chép đè chủ hồ sơ."""
    values = _names(mapper.enrich(_ho_so_nop_thay(), _CTX))
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    assert "chkbox_nguoinoplachuhs" not in values
    # Di động/Email của khối người nộp là "Tự nhập" trong mapping → không bịa từ số của chủ hồ sơ.
    assert "CongDan_diDong" not in values
    assert "CongDan_email" not in values


def test_nguoi_nop_khong_lay_nham_nhan_than_khi_khong_biet_tai_khoan():
    """Không đọc được tài khoản đang đăng nhập thì thà bỏ trống còn hơn gán bừa một người trong hồ sơ."""
    values = _names(mapper.enrich(_ho_so_nop_thay(), {}))
    for name in ("CongDan_ngaySinhCongDan", "CongDan_ngayCapCmnd", "CongDan_maTinhThanh", "CongDan_diaChi"):
        assert name not in values


def test_nhan_than_nguoi_nop_lay_duoc_tu_giay_uy_quyen_khi_thieu_anh_cccd():
    """Hồ sơ mẫu 1 không có ảnh CCCD; Giấy ủy quyền vẫn ghi đủ số + ngày cấp + nơi cấp + thường trú của Bên B."""
    values = _names(mapper.enrich(_ho_so_nop_thay(), _CTX))
    assert values["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Không có thẻ thật → không có dân tộc, và không được suy ra từ các chữ số của số định danh.
    assert "CongDan_danTocCongDan" not in values


def test_tinh_phat_truoc_xa_o_ca_hai_khoi():
    """Danh sách Phường/Xã chỉ nạp AJAX sau khi chọn tỉnh; phát ngược là ô xã rỗng."""
    order = _order(mapper.enrich(_ho_so_nop_thay(), _CTX))
    assert order.index("CongDan_maTinhThanh") < order.index("CongDan_maPhuongXa")
    assert order.index("ChuHoSo_maTinhThanhCHS") < order.index("ChuHoSo_maPhuongXaCHS")


def test_ho_so_tu_nop_van_dien_thang_khoi_chu_ho_so():
    """Hồ sơ mẫu 2 (bà Đinh Thị Thoa tự nộp, không có Giấy ủy quyền)."""
    thoa = {
        "HoTen": "Đinh Thị Thoa",
        "SoDinhDanh": "037146004756",
        "NgaySinh": "21/05/1946",
        "GioiTinh": "Nữ",
        "NgayCap": "07/09/2021",
        "NoiCap": "Cục cảnh sát Quản lý hành chính về trật tự xã hội",
        "NoiCuTru": {"tinh": "Lào Cai", "xa": "Yên Thành", "diaChi": "Thôn 02"},
    }
    values = _names(mapper.enrich(
        [
            {"name": "NguoiTrongGiayTo", "value": [thoa]},
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
            {"name": "ChuHoSo_HoTen", "value": "Đinh Thị Thoa"},
            {"name": "ChuHoSo_SoDinhDanh", "value": "037146004756"},
            {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Yên Thành", "diaChi": "Thôn 02"}},
        ],
        {"formContext": {"applicantIdentityNumber": "037146004756", "applicantFullname": "ĐINH THỊ THOA"}},
    ))
    assert values["ChuHoSo_tenChuHoSo"] == "ĐINH THỊ THOA"
    assert values["ChuHoSo_soCMNDChuHoSo"] == "037146004756"
    assert values["ChuHoSo_ngaySinhChuHoSo"] == "21/05/1946"
    assert values["CongDan_ngaySinhCongDan"] == "21/05/1946"
    assert values["CongDan_diaChi"] == "Thôn 02"


def test_khong_bia_ngay_thang_khi_chi_co_nam():
    """Giấy chứng nhận cũ chỉ ghi "Sinh năm 1952" → ô DD/MM/YYYY phải bỏ trống, không tự thêm 01/01."""
    fields = mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
            {"name": "ChuHoSo_HoTen", "value": "Đinh Thị Thoa"},
            {"name": "ChuHoSo_SoDinhDanh", "value": "037146004756"},
            {"name": "ChuHoSo_NgaySinh", "value": "1952"},
        ],
        {},
    )
    assert "ChuHoSo_ngaySinhChuHoSo" not in _names(fields)


def test_khong_nham_so_phat_hanh_gcn_voi_so_dinh_danh():
    """"BA 331193"/"CH 00077" lọt vào ô Số Căn cước là hồ sơ sai người mà không ai soát ra."""
    fields = mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
            {"name": "ChuHoSo_HoTen", "value": "Trần Thị Tâm"},
            {"name": "ChuHoSo_SoDinhDanh", "value": "BA 331193"},
        ],
        {},
    )
    values = _names(fields)
    assert "ChuHoSo_soCMNDChuHoSo" not in values
    # Thiếu số định danh thì chưa đủ để khẳng định chủ hồ sơ → không phát cả khối, tránh điền nửa vời.
    assert "ChuHoSo_tenChuHoSo" not in values


def test_ho_so_to_chuc_chon_dung_nhom_o_va_khong_bia_ca_nhan():
    values = _names(mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cơ quan nhà nước"},
            {"name": "ChuHoSo_TenToChuc", "value": "Ủy ban nhân dân xã Yên Bình"},
        ],
        _CTX,
    ))
    assert values["ChuHoSo_maDoiTuongNopHS"] == "CQ"
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == "Ủy ban nhân dân xã Yên Bình"
    # Người nộp đứng ra đại diện cho chính tổ chức chủ hồ sơ.
    assert values["CongDan_tenCoQuanToChuc"] == "Ủy ban nhân dân xã Yên Bình"
    assert "ChuHoSo_tenChuHoSo" not in values


def test_doan_lai_doi_tuong_khi_llm_tra_nhan_chung_chung():
    assert mapper.org_option("Tổ chức", "Ủy ban nhân dân xã Yên Bình") == "CQ"
    assert mapper.org_option("", "Công ty TNHH Một thành viên X") == "DN"
    assert mapper.org_option("", "Hội Nông dân tỉnh Lào Cai") == "TC"


def test_ui_comp_chi_khai_o_cua_buoc_2():
    for name in UI_COMP_BY_NAME:
        assert name.startswith(("CongDan_", "ChuHoSo_")), name


# ---------------------------------------------------------------- bước 3: đính kèm


def test_hai_dong_co_dinh_nhan_dung_tep():
    items, warnings, classified = planner.build_plan_items(
        _files(["don_tran_thi_tam.pdf", "so_tran_thi_tam.pdf"]), _llm(["don_kien_nghi", "gcn"])
    )
    assert not warnings
    by_file = {it["fileName"]: it for it in items}
    assert by_file["don_tran_thi_tam.pdf"]["slotKey"] == "lc_115687_1"
    assert by_file["so_tran_thi_tam.pdf"]["slotKey"] == "lc_115687_2"
    assert all(it["target"] == "fixed-slot" and it["tickRow"] is True for it in items)
    # Bảng không có tiêu đề nhóm → phải neo vào tiêu đề cột thì FE mới dùng slotKeywords của BE.
    assert all(it["sectionHeader"] == catalog.SECTION_HEADER for it in items)
    assert [c["target"] for c in classified] == ["fixed-slot", "fixed-slot"]


def test_nhieu_trang_so_do_gom_chung_mot_dong():
    items, _, _ = planner.build_plan_items(
        _files(["so_trang1.jpg", "so_trang2.jpg"]), _llm(["gcn", "gcn"])
    )
    assert {it["slotKey"] for it in items} == {"lc_115687_2"}
    # Mỗi tệp vẫn phải có documentName riêng để cán bộ đọc được nhật ký đính kèm.
    assert len({it["documentName"] for it in items}) == 2


def test_giay_uy_quyen_va_giay_to_bo_tro_xuong_giay_to_khac():
    """Bảng chỉ có 2 dòng — mọi thứ khác phải xuống "Giấy tờ khác", không tích bừa vào 2 dòng đó."""
    items, _, _ = planner.build_plan_items(
        _files(["uy_quyen.pdf", "ra_soat_vpdk.pdf", "bao_tu.pdf", "dkkd.pdf", "linh_tinh.pdf"]),
        _llm(["vb_dai_dien", "vb_ra_soat", "vb_dong_thuan", "vb_tu_cach_phap_nhan", "khac"]),
    )
    assert all(it["target"] == "new" and it["needsAddComponent"] is True for it in items)
    # Cổng iGate VNPT: bấm "Chọn tệp tin" mở hộp thoại file của hệ điều hành → FE phải gán thẳng.
    assert all(it["noChooserClick"] is True for it in items)
    assert all("slotKey" not in it for it in items)


def test_cccd_khong_dinh_kem_nhung_phai_canh_bao():
    items, warnings, classified = planner.build_plan_items(
        _files(["don.pdf", "cccd.jpg"]), _llm(["don_kien_nghi", "cccd"])
    )
    assert [it["fileName"] for it in items] == ["don.pdf"]
    assert any("cccd.jpg" in w for w in warnings)
    assert [c["target"] for c in classified if c["fileName"] == "cccd.jpg"] == ["skip"]


def test_khong_bo_sot_file_nao_khi_llm_chet():
    items, _, _ = planner.build_plan_items(_files(["a.pdf", "b.pdf", "c.pdf"]), {})
    assert len(items) == 3
    assert all(it["target"] == "new" for it in items)


# ---------------------------------------------------------------- hợp đồng slot với extension

# Text THẬT của bảng "Thành phần hồ sơ" trên cổng (ảnh hướng dẫn hồ sơ mẫu 2 — Đinh Thị Thoa). Đây là hợp đồng
# duy nhất giữa từ khóa của BE và DOM của cổng — cổng đổi câu chữ là test này đỏ ngay, thay vì FE lặng lẽ tích
# nhầm dòng.
_DONG_THAT = {
    catalog.ROW_KIEN_NGHI: "Văn bản kiến nghị việc cấp Giấy chứng nhận không đúng quy định của pháp luật đất "
                           "đai (bản chính)",
    catalog.ROW_GCN: "Giấy chứng nhận đã cấp (bản gốc)",
}
_TIEU_DE_COT = "# Tên giấy tờ Số bản (*) Tệp tin Mẫu đơn Ký số tệp tin"


def test_tu_khoa_khop_dung_mot_dong_that():
    folded = {pos: _norm(text) for pos, text in _DONG_THAT.items()}
    for position, (keywords, _) in catalog.ROWS.items():
        hits = [pos for pos, text in folded.items() if any(kw in text for kw in keywords)]
        assert hits == [position], (position, keywords, hits)


def test_section_header_la_tieu_de_cot_va_khong_khop_dong_nao():
    """FE lấy các dòng NẰM SAU dòng khớp sectionHeader; header mà khớp cả dòng dữ liệu là khoanh vùng hụt."""
    assert catalog.SECTION_HEADER in _norm(_TIEU_DE_COT)
    for text in _DONG_THAT.values():
        assert catalog.SECTION_HEADER not in _norm(text)
    for keywords, _ in catalog.ROWS.values():
        for keyword in keywords:
            assert keyword not in _norm(_TIEU_DE_COT), keyword


def test_moi_tuyen_deu_tro_vao_dong_co_that_va_slot_key_rieng():
    for label, position in catalog.ROUTES.items():
        assert position in catalog.ROWS, (label, position)
    keys = {catalog.slot(position)["slotKey"] for position in catalog.ROWS}
    assert len(keys) == len(catalog.ROWS)
    assert all(k.startswith("lc_115687_") for k in keys)


def test_moi_nhan_llm_deu_duoc_xu_ly():
    """Nhãn có trong danh mục gửi LLM mà planner không biết đường đi là tệp rơi vào hư không."""
    labels = [label for label, _, _ in catalog.LABELS]
    assert all(catalog.is_valid(label) for label in labels)
    items, warnings, classified = planner.build_plan_items(
        _files([f"{label}.pdf" for label in labels]), _llm(labels)
    )
    # Mỗi nhãn ra đúng một kết luận: tích dòng cố định, thêm "Giấy tờ khác", hoặc bỏ qua kèm cảnh báo.
    assert len(classified) == len(labels)
    assert {c["target"] for c in classified} == {"fixed-slot", "new", "skip"}
    assert len(items) + len(warnings) == len(labels)
    fixed = {c["label"] for c in classified if c["target"] == "fixed-slot"}
    assert fixed == set(catalog.ROUTES)
    assert {c["label"] for c in classified if c["target"] == "skip"} == catalog.SKIPPED_LABELS
