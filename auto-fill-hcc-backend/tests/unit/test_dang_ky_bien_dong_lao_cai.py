"""[Lào Cai] Đăng ký biến động 1.115671 — eForm iGate (CongDan_*/ChuHoSo_*) + đính kèm fixed-slot 5 nhóm.

Khoá ba điều dễ vỡ:
  1. Ô "Đối tượng nộp hồ sơ" có 4 lựa chọn (CN/DN/CQ/TC) — hồ sơ điển hình là tổ chức chính trị - xã hội hoặc
     cơ quan nhà nước, chọn nhầm "Doanh nghiệp" là cổng đòi mã số thuế mà hồ sơ không có.
  2. Nhóm thành phần hồ sơ chỉ được chọn theo VĂN BẢN CĂN CỨ (Đơn/GCN/bản vẽ có ở cả 5 nhóm).
  3. Từ khóa dòng phải khoanh đúng trong nhóm và KHÔNG khớp chính dòng tiêu đề nhóm.
"""

import re
import unicodedata
from pathlib import Path

from app.pipelines.dang_ky_bien_dong_lao_cai.attach import catalog, planner
from app.pipelines.dang_ky_bien_dong_lao_cai.process import mapper
from app.pipelines.dang_ky_bien_dong_lao_cai.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import public_list

_KEY = "dang-ky-bien-dong-thoa-thuan-thanh-vien-ho-gia-dinh-theo-ban-an"
_URL_LAO_CAI = "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1"

# Hồ sơ thật dùng để dựng pipeline: Cơ quan UB MTTQ VN tỉnh Lào Cai tiếp nhận trụ sở của Hội Nông dân tỉnh
# Yên Bái (điều chuyển tài sản công) — xem "mapping_dang-ky-bien-dong_1.115671_LaoCai_MTTQ.xlsx".
_TEN_CO_QUAN = "Cơ quan Ủy ban Mặt trận Tổ quốc Việt Nam tỉnh Lào Cai"
_NGUOI_DAI_DIEN = {
    "HoTen": "Nguyễn Ngọc Linh",
    "SoDinhDanh": "010087000653",
    "NgayCap": "13/04/2021",
    "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
}
_CTX = {"formContext": {"applicantIdentityNumber": "010087000653", "applicantFullname": "NGUYỄN NGỌC LINH"}}


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


# ---------------------------------------------------------------- registry & nhận diện


def test_co_trong_registry_va_khoa_dung_cong_lao_cai():
    entry = _entry()
    assert entry["mode"] == "agent"
    assert entry["hasAttachmentStep"] is True
    assert entry["detect"]["urlScope"] == ["laocai.gov.vn"]
    assert entry["label"].startswith("[Lào Cai]")


def test_key_trung_muc_ke_khai_links_1_115671():
    """Key phải khớp danh mục link để popup chọn link cũng chọn luôn pipeline điền."""
    from app.procedures.ke_khai_links import KE_KHAI_LINKS

    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.115671"


def test_trang_1_115671_lao_cai_nhan_dung_thu_tuc():
    body = (
        "Đăng ký biến động đối với trường hợp thay đổi quyền sử dụng đất, quyền sở hữu tài sản gắn liền với "
        "đất theo thỏa thuận của các thành viên hộ gia đình hoặc của vợ và chồng; bán tài sản, điều chuyển, "
        "chuyển nhượng quyền sử dụng đất là tài sản công theo quy định của pháp luật về quản lý, sử dụng tài "
        "sản công"
    )
    assert _detect(_URL_LAO_CAI, body) == _KEY


def test_khong_cuop_trang_1_115668_cung_cong_lao_cai():
    body = (
        "Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất trong các trường hợp "
        "chuyển đổi quyền sử dụng đất nông nghiệp mà không theo phương án dồn điền, đổi thửa; chuyển nhượng, "
        "thừa kế, tặng cho quyền sử dụng đất"
    )
    assert _detect(_URL_LAO_CAI, body) == "dang-ky-bien-dong-dat-dai-lao-cai"


def test_cong_tinh_khac_khong_dinh_vao_pipeline_lao_cai():
    """Cùng mã QG 1.115671 nhưng Quảng Ninh/Lâm Đồng là form khác → urlScope phải chặn."""
    body = "thay đổi quyền sử dụng đất theo thỏa thuận của các thành viên hộ gia đình hoặc của vợ và chồng"
    assert _detect("https://dichvucong.quangninh.gov.vn/x", body) != _KEY


# ---------------------------------------------------------------- bước 2: điền thông tin


def test_ho_so_to_chuc_chinh_tri_xa_hoi_chon_to_chuc_khac():
    fields = mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức khác"},
            {"name": "ChuHoSo_TenToChuc", "value": _TEN_CO_QUAN},
            {"name": "NguoiTrongGiayTo", "value": [_NGUOI_DAI_DIEN]},
            {
                "name": "ChuHoSo_DiaChiDon",
                "value": {
                    "tinh": "Lào Cai",
                    "xa": "Yên Bái",
                    "diaChi": "Đường Trần Huy Liệu, Tổ dân phố Đồng Tâm 2",
                },
            },
        ],
        _CTX,
    )
    values = _names(fields)
    assert values["ChuHoSo_maDoiTuongNopHS"] == "TC"
    # Tên cơ quan phải vào CẢ hai khối: người nộp đứng ra đại diện cho chính tổ chức chủ hồ sơ.
    assert values["ChuHoSo_tenCoQuanToChucCHS"] == _TEN_CO_QUAN
    assert values["CongDan_tenCoQuanToChuc"] == _TEN_CO_QUAN
    assert "Lào Cai" in values["ChuHoSo_maTinhThanhCHS"]
    assert "Yên Bái" in values["ChuHoSo_maPhuongXaCHS"]
    assert values["ChuHoSo_diaChiChuHoSo"] == "Đường Trần Huy Liệu, Tổ dân phố Đồng Tâm 2"


def test_khong_phat_lai_o_readonly_cua_khoi_nguoi_nop():
    """Sửa "Họ và tên"/"Số Căn cước" là cổng xoá trắng Di động + CCCD → tuyệt đối không phát."""
    fields = mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức khác"},
            {"name": "ChuHoSo_TenToChuc", "value": _TEN_CO_QUAN},
            {"name": "NguoiTrongGiayTo", "value": [_NGUOI_DAI_DIEN]},
        ],
        _CTX,
    )
    values = _names(fields)
    assert "CongDan_tenCongDan" not in values
    assert "CongDan_soCmnd" not in values
    assert "CongDan_diDong" not in values


def test_ngay_noi_cap_nguoi_nop_lay_duoc_tu_muc_1d_cua_don():
    """Hồ sơ hay THIẾU bản sao CCCD; mục 1.d của Đơn vẫn ghi đủ số + ngày cấp + nơi cấp của người đại diện."""
    fields = mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức khác"},
            {"name": "ChuHoSo_TenToChuc", "value": _TEN_CO_QUAN},
            {"name": "NguoiTrongGiayTo", "value": [_NGUOI_DAI_DIEN]},
        ],
        _CTX,
    )
    values = _names(fields)
    assert values["CongDan_ngayCapCmnd"] == "13/04/2021"
    assert values["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Không có CCCD thật → không được bịa ngày sinh/giới tính/dân tộc từ số định danh.
    assert "CongDan_ngaySinhCongDan" not in values
    assert "CongDan_gioiTinhCongDan" not in values


def test_doi_tuong_phat_truoc_o_cua_nhom_va_tinh_phat_truoc_xa():
    """Đối tượng là driver hiện nhóm ô; danh sách Phường/Xã chỉ nạp sau khi chọn tỉnh."""
    fields = mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức khác"},
            {"name": "ChuHoSo_TenToChuc", "value": _TEN_CO_QUAN},
            {"name": "ChuHoSo_DiaChiDon",
             "value": {"tinh": "Lào Cai", "xa": "Yên Bái", "diaChi": "Đường Trần Huy Liệu"}},
        ],
        _CTX,
    )
    order = _order(fields)
    assert order.index("ChuHoSo_maDoiTuongNopHS") < order.index("ChuHoSo_tenCoQuanToChucCHS")
    assert order.index("ChuHoSo_maTinhThanhCHS") < order.index("ChuHoSo_maPhuongXaCHS")


def test_ho_so_ca_nhan_khong_bia_to_chuc():
    fields = mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
            {"name": "ChuHoSo_HoTen", "value": "Trần Thị B"},
            {"name": "ChuHoSo_SoDinhDanh", "value": "012345678901"},
            {"name": "ChuHoSo_XungHo", "value": "Bà"},
        ],
        {},
    )
    values = _names(fields)
    assert values["ChuHoSo_maDoiTuongNopHS"] == "CN"
    assert values["ChuHoSo_tenChuHoSo"] == "TRẦN THỊ B"
    assert values["ChuHoSo_gioiTinhChuHoSo"] == "Nữ"
    assert "ChuHoSo_tenCoQuanToChucCHS" not in values
    assert "CongDan_tenCoQuanToChuc" not in values


def test_khong_bia_ngay_thang_khi_chi_co_nam():
    fields = mapper.enrich(
        [
            {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
            {"name": "ChuHoSo_HoTen", "value": "Trần Thị B"},
            {"name": "ChuHoSo_SoDinhDanh", "value": "012345678901"},
            {"name": "ChuHoSo_NgaySinh", "value": "1970"},
        ],
        {},
    )
    assert "ChuHoSo_ngaySinhChuHoSo" not in _names(fields)


def test_doan_lai_doi_tuong_khi_llm_tra_nhan_chung_chung():
    """LLM hay trả "Tổ chức" như các thủ tục anh em → phải đoán lại theo chính tên tổ chức."""
    assert mapper.org_option("Tổ chức", _TEN_CO_QUAN) == "TC"
    assert mapper.org_option("", "Ủy ban nhân dân phường Yên Bái") == "CQ"
    assert mapper.org_option("", "Công ty TNHH Một thành viên X") == "DN"
    # "Cơ quan Ủy ban Mặt trận…" có cả chữ "cơ quan" lẫn "ủy ban" → nhánh tổ chức chính trị - xã hội
    # phải thắng, nếu không hồ sơ MTTQ bị đẩy sang "Cơ quan nhà nước".
    assert mapper.org_option("", _TEN_CO_QUAN) == "TC"


def test_ui_comp_chi_khai_o_cua_buoc_2():
    for name in UI_COMP_BY_NAME:
        assert name.startswith(("CongDan_", "ChuHoSo_")), name


# ---------------------------------------------------------------- bước 3: đính kèm


def test_chon_nhom_theo_van_ban_can_cu_chu_khong_theo_don():
    """Đơn/GCN có ở cả 5 nhóm nên không nói lên gì; căn cứ mới quyết định nhóm."""
    _, _, _, group, source = planner.build_plan_items(
        _files(["don.pdf", "gcn.pdf"]), _llm(["don_dang_ky", "gcn"]), ""
    )
    assert (group, source) == (catalog.GROUP_1, "default")

    _, _, _, group, source = planner.build_plan_items(
        _files(["don.pdf", "ban_an.pdf"]), _llm(["don_dang_ky", "vb_giai_quyet_tranh_chap"]), ""
    )
    assert (group, source) == (catalog.GROUP_4, "can_cu")


def test_llm_doan_nhom_chi_duoc_dung_khi_khong_co_can_cu():
    _, _, _, group, source = planner.build_plan_items(
        _files(["don.pdf"]), _llm(["don_dang_ky"]), "5"
    )
    assert (group, source) == (catalog.GROUP_5, "llm")
    # Có căn cứ thật thì căn cứ thắng, không nghe LLM đoán nhóm khác.
    _, _, _, group, source = planner.build_plan_items(
        _files(["the_chap.pdf"]), _llm(["hop_dong_xu_ly_the_chap"]), "1"
    )
    assert (group, source) == (catalog.GROUP_5, "can_cu")


def test_bo_ho_so_dieu_chuyen_tai_san_cong_vao_dung_dong_nhom_3():
    """Hồ sơ thật của Cơ quan UB MTTQ: 8 file → nhóm (3), 4 file căn cứ gom chung một dòng."""
    names = ["don.pdf", "qd1255.pdf", "gcn_bia.pdf", "gcn_trang.pdf", "tb83.pdf", "bb_bangiao.pdf",
             "qd09.pdf", "qd2743.pdf"]
    labels = ["don_dang_ky", "qd_giao_dat_cap_gcn", "gcn", "gcn",
              "vb_cho_phep_tai_san_cong", "vb_cho_phep_tai_san_cong",
              "vb_cho_phep_tai_san_cong", "vb_cho_phep_tai_san_cong"]
    items, warnings, _, group, _ = planner.build_plan_items(_files(names), _llm(labels), "")

    assert group == catalog.GROUP_3
    assert not warnings
    by_file = {it["fileName"]: it for it in items}
    assert by_file["don.pdf"]["slotKey"] == "lc_115671_3_1"
    # Quyết định giao đất/cấp GCN đi CÙNG dòng "Giấy chứng nhận đã cấp" (Đơn mục 3 ghi chung một gạch đầu dòng).
    assert {by_file[n]["slotKey"] for n in ("qd1255.pdf", "gcn_bia.pdf", "gcn_trang.pdf")} == {"lc_115671_3_2"}
    assert {by_file[n]["slotKey"] for n in ("tb83.pdf", "bb_bangiao.pdf", "qd09.pdf", "qd2743.pdf")} == {
        "lc_115671_3_3"
    }
    assert all(it["target"] == "fixed-slot" and it["tickRow"] is True for it in items)
    # Mỗi tệp phải tự có documentName riêng để cán bộ đọc được nhật ký đính kèm.
    assert len({it["documentName"] for it in items}) == len(items)


def test_giay_to_khong_co_dong_trong_nhom_xuong_giay_to_khac():
    """Nhóm (3) KHÔNG có dòng "Mảnh trích đo" → phải xuống "Giấy tờ khác", không tích bừa dòng khác."""
    items, _, _, group, _ = planner.build_plan_items(
        _files(["bb_bangiao.pdf", "trich_do.pdf"]),
        _llm(["vb_cho_phep_tai_san_cong", "manh_trich_do"]),
        "",
    )
    assert group == catalog.GROUP_3
    by_file = {it["fileName"]: it for it in items}
    assert by_file["trich_do.pdf"]["target"] == "new"
    assert by_file["trich_do.pdf"]["needsAddComponent"] is True
    # Cùng tệp đó ở nhóm (1) thì có dòng riêng.
    items, _, _, group, _ = planner.build_plan_items(
        _files(["thoa_thuan.pdf", "trich_do.pdf"]),
        _llm(["vb_thoa_thuan_ho_gia_dinh", "manh_trich_do"]),
        "",
    )
    assert group == catalog.GROUP_1
    assert {it["fileName"]: it["slotKey"] for it in items}["trich_do.pdf"] == "lc_115671_1_5"


def test_cccd_khong_dinh_kem_nhung_phai_canh_bao():
    items, warnings, classified, _, _ = planner.build_plan_items(
        _files(["don.pdf", "cccd.jpg"]), _llm(["don_dang_ky", "cccd"]), ""
    )
    assert [it["fileName"] for it in items] == ["don.pdf"]
    assert any("cccd.jpg" in w for w in warnings)
    assert [c["target"] for c in classified if c["fileName"] == "cccd.jpg"] == ["skip"]


def test_khong_bo_sot_file_nao_khi_llm_chet():
    items, _, _, group, source = planner.build_plan_items(_files(["a.pdf", "b.pdf", "c.pdf"]), {}, "")
    assert len(items) == 3
    assert (group, source) == (catalog.GROUP_1, "default")
    assert all(it["target"] == "new" for it in items)


def test_uy_quyen_va_tu_cach_phap_nhan_chung_dong_van_ban_dai_dien():
    items, _, _, _, _ = planner.build_plan_items(
        _files(["thoa_thuan.pdf", "uy_quyen.pdf", "dkkd.pdf"]),
        _llm(["vb_thoa_thuan_ho_gia_dinh", "vb_dai_dien", "vb_tu_cach_phap_nhan"]),
        "",
    )
    by_file = {it["fileName"]: it for it in items}
    assert by_file["uy_quyen.pdf"]["slotKey"] == by_file["dkkd.pdf"]["slotKey"] == "lc_115671_1_6"


# ---------------------------------------------------------------- hợp đồng slot với extension


def test_moi_nhom_deu_co_du_dong_va_khong_trung_vi_tri():
    for group in catalog.GROUPS:
        positions = [pos for (g, pos) in catalog.ROWS if g == group]
        assert sorted(positions) == list(range(1, 7)), group
    # Mọi tuyến đều trỏ vào một dòng có thật.
    for label, routes in catalog.ROUTES.items():
        for group, position in routes.items():
            assert (group, position) in catalog.ROWS, (label, group, position)


def test_tu_khoa_dong_khong_khop_chinh_tieu_de_nhom():
    """FE quét từ dòng SAU tiêu đề, nhưng từ khóa trùng tiêu đề vẫn là bẫy khi cổng đổi bố cục."""
    for (group, position), (keywords, _) in catalog.ROWS.items():
        header = catalog.SECTION_HEADERS[group]
        for keyword in keywords:
            assert keyword not in header, (group, position, keyword)


def test_tu_khoa_trong_cung_nhom_khong_khop_lan_nhau():
    for group in catalog.GROUPS:
        rows = [(pos, catalog.ROWS[(group, pos)]) for pos in range(1, 7)]
        for pos, (keywords, _) in rows:
            for other_pos, (_, other_name) in rows:
                if other_pos == pos:
                    continue
                for keyword in keywords:
                    assert keyword not in _norm(other_name), (group, pos, other_pos, keyword)


def test_extension_nhan_dien_duoc_tieu_de_nhom_danh_so():
    """Tiêu đề "(2) Đối với trường hợp…" phải nằm trong FIXED_SLOT_SECTION_RE của content.js."""
    content = Path(__file__).resolve().parents[2].parent / "auto-fill-hcc-extension" / "content.js"
    if not content.exists():
        return
    line = next(
        ln for ln in content.read_text(encoding="utf-8").splitlines()
        if "FIXED_SLOT_SECTION_RE" in ln and "=" in ln
    )
    assert "doi voi truong hop" in line
    assert r"\(\d+\)" in line


# Text THẬT của bảng "Thành phần hồ sơ" trên cổng, chép từ ảnh chụp hồ sơ Cơ quan UB MTTQ VN tỉnh Lào Cai
# (ảnh 1/7 → 4/7). Đây là hợp đồng duy nhất giữa từ khóa của BE và DOM của cổng — cổng đổi câu chữ là test này
# đỏ ngay, thay vì FE lặng lẽ tích nhầm dòng.
_DON_MAU_24 = (
    "Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 24 ban hành kèm theo Quyết định "
    "số 47/2026/QĐ-UBND"
)
_GCN_DA_CAP = "Giấy chứng nhận đã cấp"
_BAN_VE = (
    "Bản vẽ tách thửa đất, hợp thửa đất theo Mẫu số 28 ban hành kèm theo Quyết định số 47/2026/QĐ-UBND đối "
    "với trường hợp đăng ký biến động đất đai mà phải tách thửa đất, hợp thửa đất"
)
_TRICH_DO = (
    "Mảnh trích đo bản đồ địa chính thửa đất đối với trường hợp người sử dụng đất có nhu cầu đo đạc để xác "
    "định lại kích thước các cạnh, diện tích của thửa đất"
)
_DAI_DIEN = (
    "Văn bản về việc đại diện theo quy định của pháp luật về dân sự đối với trường hợp thực hiện thủ tục "
    "đăng ký đất đai, tài sản gắn liền với đất thông qua người đại diện"
)

_DONG_THAT = {
    catalog.GROUP_1: [
        _DON_MAU_24,
        _GCN_DA_CAP,
        "Văn bản thỏa thuận về việc thay đổi quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất theo "
        "thỏa thuận của các thành viên hộ gia đình hoặc của vợ và chồng. + Trường hợp thay đổi quyền sử dụng "
        "đất của các thành viên có chung quyền sử dụng đất của hộ gia đình thì văn bản thỏa thuận phải thể "
        "hiện thông tin thành viên của hộ gia đình có chung quyền sử dụng đất tại thời điểm được Nhà nước "
        "giao đất, cho thuê đất, công nhận quyền sử dụng đất, nhận chuyển quyền sử dụng đất.",
        _BAN_VE,
        _TRICH_DO,
        _DAI_DIEN,
    ],
    catalog.GROUP_2: [
        _DON_MAU_24,
        _GCN_DA_CAP,
        "Văn bản về việc cho phép thay đổi quyền sử dụng đất xây dựng công trình trên mặt đất phục vụ cho "
        "việc vận hành, khai thác sử dụng công trình ngầm, quyền sở hữu công trình ngầm của cơ quan, người "
        "có thẩm quyền",
        _BAN_VE,
        _TRICH_DO,
        _DAI_DIEN,
    ],
    catalog.GROUP_3: [
        _DON_MAU_24,
        _GCN_DA_CAP,
        "Văn bản cho phép bán tài sản, điều chuyển, chuyển nhượng quyền sử dụng đất, tài sản gắn liền với "
        "đất của cơ quan có thẩm quyền",
        "Hợp đồng mua bán tài sản công là quyền sử dụng đất, tài sản gắn liền với đất theo quy định của pháp "
        "luật đối với trường hợp bán tài sản, chuyển nhượng quyền sử dụng đất là tài sản công",
        _BAN_VE,
        _DAI_DIEN + ".",
    ],
    catalog.GROUP_4: [
        _DON_MAU_24,
        _GCN_DA_CAP,
        "Một trong các văn bản sau: + Biên bản hòa giải thành hoặc văn bản công nhận kết quả hòa giải thành "
        "được cơ quan có thẩm quyền công nhận. + Quyết định của cơ quan có thẩm quyền về giải quyết tranh "
        "chấp, khiếu nại, tố cáo về đất đai đã có hiệu lực thi hành theo quy định của pháp luật. + Quyết "
        "định hoặc bản án của Tòa án nhân dân, quyết định về thi hành án của cơ quan thi hành án đã được thi "
        "hành. + Quyết định hoặc phán quyết của Trọng tài thương mại Việt Nam về giải quyết tranh chấp giữa "
        "các bên phát sinh từ hoạt động thương mại liên quan đến đất đai.",
        _BAN_VE,
        _TRICH_DO,
        _DAI_DIEN,
    ],
    catalog.GROUP_5: [
        _DON_MAU_24,
        _GCN_DA_CAP,
        "Một trong các văn bản sau: + Hợp đồng chuyển nhượng quyền sử dụng đất, tài sản gắn liền với đất "
        "giữa người sử dụng đất, chủ sở hữu tài sản gắn liền với đất với người nhận chuyển nhượng. + Hợp "
        "đồng chuyển nhượng hoặc hợp đồng chuyển giao khác về quyền sử dụng đất, quyền sở hữu tài sản gắn "
        "liền với đất giữa người có quyền chuyển nhượng, bán tài sản thế chấp là quyền sử dụng đất, tài sản "
        "gắn liền với đất với người nhận chuyển nhượng. + Hợp đồng mua bán tài sản đấu giá quyền sử dụng "
        "đất, tài sản gắn liền với đất hoặc văn bản xác nhận kết quả thi hành án của Cơ quan thi hành án "
        "dân sự. + Hợp đồng thế chấp quyền sử dụng đất, tài sản gắn liền với đất hoặc văn bản khác có thỏa "
        "thuận về việc bên nhận thế chấp có quyền được nhận chính tài sản bảo đảm theo quy định của pháp luật",
        _BAN_VE,
        _TRICH_DO,
        _DAI_DIEN,
    ],
}

# Tiêu đề nhóm THẬT (dòng có checkbox trên cổng). Nhóm (1) không có tiêu đề riêng — xem catalog.
_TIEU_DE_THAT = {
    catalog.GROUP_2: "(2) Đối với trường hợp thay đổi quyền sử dụng đất xây dựng công trình trên mặt đất phục "
                     "vụ cho việc vận hành, khai thác sử dụng công trình ngầm, quyền sở hữu công trình ngầm:",
    catalog.GROUP_3: "(3) Đối với trường hợp bán tài sản, điều chuyển, chuyển nhượng quyền sử dụng đất là tài "
                     "sản công theo quy định của pháp luật về quản lý, sử dụng tài sản công:",
    catalog.GROUP_4: "(4) Đối với trường hợp nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất "
                     "theo kết quả giải quyết tranh chấp, khiếu nại, tố cáo về đất đai hoặc bản án, quyết "
                     "định của Tòa án, quyết định thi hành án của cơ quan thi hành án đã được thi hành; "
                     "quyết định hoặc phán quyết của Trọng tài thương mại Việt Nam về giải quyết tranh chấp "
                     "giữa các bên phát sinh từ hoạt động thương mại liên quan đến đất đai:",
    catalog.GROUP_5: "(5) Đối với trường hợp nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất do "
                     "xử lý tài sản thế chấp là quyền sử dụng đất, tài sản gắn liền với đất đã được đăng ký, "
                     "bao gồm cả xử lý khoản nợ có nguồn gốc từ khoản nợ xấu của tổ chức tín dụng, chi nhánh "
                     "ngân hàng nước ngoài:",
}


def test_tu_khoa_khop_dung_mot_dong_that_trong_nhom():
    """Hợp đồng giữa slotKeywords của BE và text DOM của cổng: mỗi từ khóa khớp ĐÚNG dòng của nó."""
    for group, rows in _DONG_THAT.items():
        folded = [_norm(text) for text in rows]
        for position in range(1, 7):
            keywords, _ = catalog.ROWS[(group, position)]
            hits = [i for i, text in enumerate(folded) if any(kw in text for kw in keywords)]
            assert hits == [position - 1], (group, position, keywords, hits)


def test_tieu_de_nhom_that_khop_section_header_va_khong_chua_tu_khoa_dong():
    """sectionHeader phải là chuỗi con của tiêu đề thật; tiêu đề KHÔNG được khớp từ khóa dòng nào."""
    for group, header in _TIEU_DE_THAT.items():
        folded = _norm(header)
        assert catalog.SECTION_HEADERS[group] in folded, group
        for position in range(1, 7):
            keywords, _ = catalog.ROWS[(group, position)]
            for keyword in keywords:
                assert keyword not in folded, (group, position, keyword)


def test_slot_key_rieng_cho_thu_tuc_nay():
    keys = {catalog.slot(row)["slotKey"] for row in catalog.ROWS}
    assert len(keys) == len(catalog.ROWS)
    assert all(k.startswith("lc_115671_") for k in keys)
