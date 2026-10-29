"""[Lào Cai - cổng iGate mới] 1.115651 — mapper Form.io data[...] + kế hoạch đính kèm attp-row.

Dữ liệu trong file đều là ví dụ bịa.
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.attach import planner
from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process import mapper
from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import _ATTACH_PIPELINE, _PIPELINE, PROCEDURES

_KEY = "chuyen-muc-dich-su-dung-dat-igate-lao-cai"
_CHU_HO_SO = "001099000001"
_NGUOI_KHAC = "001088000002"

_FACTS = [
    {"name": "DanhSachCccd", "value": [
        {"HoTen": "NGUYỄN VĂN A", "SoDinhDanh": _CHU_HO_SO, "NgaySinh": "01/02/1980", "GioiTinh": "Nam",
         "NgayCap": "10/06/2021", "NoiCap": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 1"}},
        {"HoTen": "TRẦN THỊ B", "SoDinhDanh": _NGUOI_KHAC, "NgaySinh": "05/06/1988", "GioiTinh": "Nữ",
         "NgayCap": "15/01/2022", "NoiCap": "Bộ Công an",
         "NoiCuTru": {"tinh": "Lào Cai", "xa": "Yên Bái", "chiTietDuoiXa": "Tổ 5"}},
    ]},
    {"name": "ChuHoSo_LoaiDoiTuong", "value": "Cá nhân"},
    {"name": "ChuHoSo_HoTen", "value": "Nguyễn Văn A"},
    {"name": "ChuHoSo_XungHo", "value": "Ông"},
    {"name": "ChuHoSo_SoDinhDanh", "value": _CHU_HO_SO},
    {"name": "ChuHoSo_NgaySinh", "value": "1980"},
    {"name": "ChuHoSo_DiaChiDon", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Tổ 1"}},
    {"name": "Don_DienThoai", "value": "0912 345 678"},
]


def _values(fields):
    return {f["name"]: f["value"] for f in fields if f["comp"] != "dom-expect"}


def _expected(fields):
    return {f["name"] for f in fields if f["comp"] == "dom-expect"}


def _ctx(name, number):
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


def test_registry_tach_cong_chinh_thuc_va_cong_test():
    keys = [p["key"] for p in PROCEDURES]
    chinh = next(p for p in PROCEDURES if p["key"] == _KEY)
    test = next(p for p in PROCEDURES if p["key"] == _KEY + "-test")
    assert chinh["detect"]["urlScope"] == ["dichvucong.laocai.gov.vn/vi/"]
    assert test["detect"]["urlScope"] == ["dichvucongtest.laocai.gov.vn/vi/"]
    assert chinh["detect"]["urlIncludes"] == test["detect"]["urlIncludes"] == [
        "apply-online/6aa4c6e20ac3ff7a28894b2c", "matthc=1.115651", "madvc=1.115651."]
    assert test["label"] == chinh["label"] + " - test"
    assert test["uploadHint"] == chinh["uploadHint"]
    # Host chính thức không phải chuỗi con của host test (và ngược lại) → hai mục không lẫn nhau.
    url_test = "https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4c6e20ac3ff7a28894b2c?agency=x"
    assert not any(s in url_test for s in chinh["detect"]["urlScope"])
    assert any(s in url_test for s in test["detect"]["urlScope"])
    for key in (_KEY, _KEY + "-test"):
        assert _PIPELINE[key] is _PIPELINE[_KEY] and _ATTACH_PIPELINE[key] is _ATTACH_PIPELINE[_KEY]
        # Đứng trước mục cổng cũ: hai mục cùng khớp tên thủ tục thì mục đầu thắng khi điểm bằng nhau.
        assert keys.index(key) < keys.index("chuyen-muc-dich-su-dung-dat-lao-cai")


def test_khong_phat_o_bi_cong_khoa():
    fields = mapper.enrich(_FACTS, _ctx("TRẦN THỊ B", _NGUOI_KHAC))
    names = {f["name"] for f in fields}
    for locked in ("data[fullname]", "data[identityNumber]", "data[birthday]", "data[organization]",
                   "data[taxCode]", "data[chonDoiTuong]", "data[isOwnerDossier]"):
        assert locked not in names
        assert locked not in UI_COMP_BY_NAME


def test_nop_thay_lay_nhan_than_nguoi_dang_nhap_va_khong_lay_sdt_don():
    fields = mapper.enrich(_FACTS, _ctx("TRẦN THỊ B", _NGUOI_KHAC))
    values = _values(fields)

    assert values["data[gender]"] == "Nữ"
    assert values["data[identityDate]"] == "15/01/2022"
    assert values["data[idIssuePlace]"] == "Bộ Công An"
    assert values["data[province]"] == "Tỉnh Lào Cai"
    assert values["data[district]"] == "Phường Yên Bái"
    assert values["data[address]"] == "Tổ 5"
    # SĐT trên Đơn là của chủ hồ sơ → không điền cho người nộp thay, ô (*) tô đỏ.
    assert "data[phoneNumber]" not in values
    assert "data[phoneNumber]" in _expected(fields)
    # Chủ hồ sơ điền thẳng từ giấy tờ.
    assert values["data[ChuHS]"] == "Cá nhân"
    assert values["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert values["data[ownerIdentityNumber]"] == _CHU_HO_SO
    assert values["data[ownerBirthday]"] == "01/02/1980"
    assert values["data[ownerGender]"] == "Nam"
    assert values["data[ownerIdentityAgency22]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert values["data[ownerProvince]"] == "Tỉnh Lào Cai"
    assert values["data[ownerDistrict]"] == "Phường Cam Đường"
    assert values["data[ownerPhoneNumber]"] == "0912345678"


def test_tu_nop_dien_sdt_don_cho_ca_nguoi_nop():
    values = _values(mapper.enrich(_FACTS, _ctx("NGUYỄN VĂN A", _CHU_HO_SO)))

    assert values["data[gender]"] == "Nam"
    assert values["data[phoneNumber]"] == "0912345678"
    assert values["data[district]"] == "Phường Cam Đường"
    assert values["data[ownerPhoneNumber]"] == "0912345678"


def test_driver_va_tinh_dung_truoc_o_phu_thuoc():
    names = [f["name"] for f in mapper.enrich(_FACTS, _ctx("TRẦN THỊ B", _NGUOI_KHAC))]
    assert names.index("data[province]") < names.index("data[district]")
    assert names.index("data[ChuHS]") < names.index("data[ownerFullname]")
    assert names.index("data[ownerProvince]") < names.index("data[ownerDistrict]")


def test_chu_ho_so_cong_ty():
    facts = [
        {"name": "ChuHoSo_LoaiDoiTuong", "value": "Tổ chức"},
        {"name": "ChuHoSo_TenToChuc", "value": "Công ty TNHH Ví Dụ"},
        {"name": "ChuHoSo_MaSoThue", "value": "5300000001"},
        {"name": "ChuHoSo_DiaChiDkdn", "value": {"tinh": "Lào Cai", "xa": "Cam Đường", "diaChi": "Số 1"}},
    ]
    values = _values(mapper.enrich(facts, {}))

    assert values["data[ChuHS]"] == "Doanh nghiệp"
    assert values["data[ownerOrganizationFullname]"] == "CÔNG TY TNHH VÍ DỤ"
    assert values["data[ownerTaxCode]"] == "5300000001"
    assert "data[ownerFullname]" not in values


def test_noi_cap_ngoai_hai_option_thi_canh_bao():
    facts = [dict(f) for f in _FACTS]
    facts[0] = {"name": "DanhSachCccd", "value": [{**_FACTS[0]["value"][1], "NoiCap": "Công an tỉnh Yên Bái"}]}
    fields, warnings = mapper.enrich_with_warnings(facts, _ctx("TRẦN THỊ B", _NGUOI_KHAC))
    assert "data[idIssuePlace]" not in _values(fields)
    assert any("Nơi cấp" in w for w in warnings)


def test_theo_to_khai_canh_bao_khi_tai_khoan_khac():
    fields, warnings = mapper.enrich_with_warnings(
        _FACTS, {"submitterMode": "owner_as_submitter", **_ctx("TRẦN THỊ B", _NGUOI_KHAC)})
    values = _values(fields)
    assert values["data[gender]"] == "Nam"
    assert values["data[phoneNumber]"] == "0912345678"
    assert any("KHOÁ" in w for w in warnings)


# ---- Đính kèm ----

# Bảng thật crawl 29/10/2026 (13 dòng, 4 nhóm nối liền, không có tiêu đề nhóm).
_ROWS = [{"index": i + 1, "componentName": name} for i, name in enumerate(planner._DEFAULT_ROWS)]


def _files(n):
    return [{"name": f"tep-{i}.pdf", "_index": i} for i in range(n)]


def _plan(llm, rows=_ROWS, group=""):
    items, warnings, _, don = planner.build_plan_items(_files(len(llm) or 2), llm, group, rows)
    return {i["fileIndex"]: i for i in items}, warnings, don


def test_nhom_chuyen_muc_dich_dung_dong_1_2():
    by_file, warnings, don = _plan({
        0: {"label": "don_mau_02", "documentName": "Đơn đề nghị chuyển mục đích sử dụng đất"},
        1: {"label": "gcn", "documentName": "Giấy chứng nhận quyền sử dụng đất"},
        2: {"label": "vb_uy_quyen", "documentName": "Giấy ủy quyền"},
        3: {"label": "cccd", "documentName": "Căn cước công dân"},
    })
    assert don == "don_mau_02"
    assert by_file[0]["componentIndex"] == 1 and by_file[0]["target"] == "attp-row"
    # "khoản 21 Điều 3" có ở dòng 2/4/7 → phải là dòng 2 của nhóm (1), không phải dòng ngắn nhất cả bảng.
    assert by_file[1]["componentIndex"] == 2
    assert by_file[1]["componentName"] == _ROWS[1]["componentName"]
    assert by_file[2]["componentIndex"] == 1
    assert 3 not in by_file
    assert all(i["untickUnplannedRows"] is True for i in by_file.values())
    assert any("không có dòng riêng" in w for w in warnings)


def test_nhom_chuyen_hinh_thuc_dong_3_4_5():
    by_file, _, _ = _plan({
        0: {"label": "gcn", "documentName": "Giấy chứng nhận"},
        1: {"label": "don_mau_03", "documentName": "Đơn đề nghị chuyển hình thức sử dụng đất"},
        2: {"label": "quyet_dinh_giao_dat", "documentName": "Quyết định cho thuê đất"},
    })
    assert [by_file[i]["componentIndex"] for i in range(3)] == [4, 3, 5]


def test_nhom_gia_han_dong_6_den_9():
    by_file, _, _ = _plan({
        0: {"label": "don_mau_17", "documentName": "Đơn đề nghị gia hạn sử dụng đất"},
        1: {"label": "gcn", "documentName": "Giấy chứng nhận"},
        2: {"label": "quyet_dinh_giao_dat", "documentName": "Quyết định giao đất"},
        3: {"label": "vb_thoi_han_du_an", "documentName": "Quyết định chủ trương đầu tư"},
    })
    assert [by_file[i]["componentIndex"] for i in range(4)] == [6, 7, 8, 9]


def test_nhom_dieu_chinh_thoi_han_dong_10_den_13():
    by_file, _, _ = _plan({
        0: {"label": "don_mau_18", "documentName": "Đơn đề nghị điều chỉnh thời hạn"},
        1: {"label": "vb_thay_doi_thoi_han_du_an", "documentName": "Văn bản thay đổi thời hạn dự án"},
        2: {"label": "gcn", "documentName": "Giấy chứng nhận"},
        3: {"label": "quyet_dinh_giao_dat", "documentName": "Quyết định giao đất"},
    })
    # Dòng 13 trùng NGUYÊN VĂN dòng 8 → phải ra 13 nhờ khoanh nhóm.
    assert [by_file[i]["componentIndex"] for i in range(4)] == [10, 11, 12, 13]


def test_khong_co_attachment_context_dung_bang_mac_dinh():
    by_file, _, _ = _plan({
        0: {"label": "don_mau_18", "documentName": "Đơn"},
        1: {"label": "quyet_dinh_giao_dat", "documentName": "Quyết định giao đất"},
    }, rows=None)
    assert by_file[0]["componentIndex"] == 10
    assert by_file[1]["componentIndex"] == 13
    assert by_file[1]["componentName"] == planner._DEFAULT_ROWS[12]


def test_khong_ro_don_thi_theo_nhom_llm_hoac_mac_dinh_kem_canh_bao():
    by_file, _, _ = _plan({0: {"label": "gcn", "documentName": "Giấy chứng nhận"}}, group="(3)")
    assert by_file[0]["componentIndex"] == 7
    by_file, warnings, don = _plan({0: {"label": "gcn", "documentName": "Giấy chứng nhận"}})
    assert don == "don_mau_02" and by_file[0]["componentIndex"] == 2
    assert any("Không nhận ra Đơn" in w for w in warnings)


def test_khong_lam_roi_tep_khong_ro_loai():
    items, _, _, _ = planner.build_plan_items(_files(2), {}, "", _ROWS)
    assert sorted(i["fileIndex"] for i in items) == [0, 1]
    assert {i["componentIndex"] for i in items} == {1}
    assert len({i["documentName"] for i in items}) == 2


# ---- Nhận diện như popup (bước urlIncludes: mục khớp ĐẦU TIÊN thắng) trên đúng danh sách API trả ----

def _popup_url_match(url: str) -> str:
    from app.procedures.ke_khai_links import with_ke_khai_detect_urls
    from app.procedures.registry import public_list

    url = url.lower()
    for p in with_ke_khai_detect_urls(public_list()):
        detect = p.get("detect") or {}
        if detect.get("detectDisabled") or p.get("detectDisabled"):
            continue
        scope = detect.get("urlScope") or []
        if scope and not any(s.lower() in url for s in scope):
            continue
        if any(u and u.lower() in url for u in detect.get("urlIncludes") or []):
            return p["key"]
    return ""


def test_cong_test_man_chon_truong_hop_va_form_deu_ra_muc_test():
    chon = ("https://dichvucongtest.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115651&MaCoQuanThucHien=H38.44"
            "&MaDVC=1.115651.01&MaTTHCDP=1.115651&vneid=1")
    form = ("https://dichvucongtest.laocai.gov.vn/vi/padsvc/apply-online/6aa4c6e20ac3ff7a28894b2c"
            "?agency=6aa0b531ea2136132881f46e&process=6ac0db76de4a9904f459581e")
    assert _popup_url_match(chon) == _KEY + "-test"
    assert _popup_url_match(form) == _KEY + "-test"


def test_cong_chinh_thuc_nen_moi_ra_muc_igate_con_eform_cu_khong_dinh():
    assert _popup_url_match(
        "https://dichvucong.laocai.gov.vn/vi/nps/apply?MaTTHC=1.115651&MaDVC=1.115651.01") == _KEY
    assert _popup_url_match(
        "https://dichvucong.laocai.gov.vn/dich-vu-cong/tiep-nhan-online/nhap-thong-tin-ho-so?sid=1") != _KEY
