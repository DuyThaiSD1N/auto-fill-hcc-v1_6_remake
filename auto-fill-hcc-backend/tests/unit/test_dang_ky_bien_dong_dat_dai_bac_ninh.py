"""Unit test "[Bắc Ninh] Đăng ký biến động QSDĐ" (1.115468).

Theo spec (ánh xạ hồ sơ): đơn Mẫu 18 khớp CLASS eform-element-<Key>, GỘP 2 vợ chồng vào ô Tên/Giấy tờ.
Khối "được ủy quyền" (doiTuongKhac*) = NGƯỜI ỦY QUYỀN = CHỦ HỒ SƠ (KHÔNG phải người được ủy quyền).
Đính kèm 16 mã TP-H05 + File đính kèm khác. Phân loại LLM-first.
"""

from app.pipelines.dang_ky_bien_dong_dat_dai_bac_ninh.attach import catalog, planner
from app.pipelines.dang_ky_bien_dong_dat_dai_bac_ninh.process import mapper, schema
from app.procedures.registry import get_attach_pipeline, get_procedure

_KEY = "dang-ky-bien-dong-dat-dai-bac-ninh"

# Hồ sơ mẫu Nguyễn Văn Dũng + Nguyễn Thị Yến (vợ chồng nhận tặng cho), nộp qua ủy quyền Phan Mỹ Dung.
_SAMPLE = {
    "ChuHoSo_HoTen": "Nguyễn Văn Dũng",
    "ChuHoSo_GioiTinh": "Nam",
    "ChuHoSo_SoDinhDanh": "027087017758",
    "ChuHoSo_NgaySinh": "28/08/1987",
    "ChuHoSo_NgayCap": "26/09/2024",
    "ChuHoSo_NoiCap": "Bộ Công an",
    # Địa chỉ ưu tiên Đơn M18/tờ khai (Nam Sơn) — theo chốt của user, KHÔNG lấy CCCD (Văn Dương).
    "ChuHoSo_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Nam Sơn", "diaChi": ""},
    "ChuHoSo_DienThoai": "0983696787",
    "ChuHoSo_MaSoThue": "027087017758",
    "DongSuDung_HoTen": "Nguyễn Thị Yến",
    "DongSuDung_SoDinhDanh": "024189005605",
    "DongSuDung_NgaySinh": "04/03/1989",
    "Don_KinhGui": "Chi nhánh Văn phòng đăng ký đất đai liên phường Bắc Ninh",
    "Don_LoaiGiaoDich": "tặng cho",
    "Don_TenHopDong": "Hợp đồng tặng cho quyền sử dụng đất, số công chứng 2224/2026/CCGD",
    "Don_GiayToKem": "CCCD (bản sao chứng thực); Giấy chứng nhận kết hôn; Trích lục khai sinh; Giấy ủy quyền; Biên bản bàn giao đất",
    "Don_TranhChap": "Không có tranh chấp",
    "Don_RanhGioi": "Không thay đổi so với ranh giới được cấp Giấy chứng nhận",
}


def _fields(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _map(d: dict, options: dict | None = None) -> dict:
    mapped, _ = mapper.enrich(_fields(d), options)
    return {f["name"]: f["value"] for f in mapped}


def test_registration_don_gop_hai_vo_chong():
    got = _map(_SAMPLE)
    assert got[schema.K_KINHGUI] == "Chi nhánh Văn phòng đăng ký đất đai liên phường Bắc Ninh"
    # Tên(2) GỘP cả 2 người + sinh năm.
    assert got[schema.K_TEN] == "Nguyễn Văn Dũng, sinh năm 1987 và Nguyễn Thị Yến, sinh năm 1989"
    # Giấy tờ nhân thân GỘP 2 CCCD (kèm tên).
    assert got[schema.K_GIAYTO] == "027087017758 (Nguyễn Văn Dũng); 024189005605 (Nguyễn Thị Yến)"
    assert got[schema.K_DIACHI] == "Nam Sơn, Bắc Ninh"
    assert got[schema.K_MST] == "027087017758"
    assert got[schema.K_DIENTHOAI] == "0983696787"
    assert got[schema.K_NOIDUNG] == "Nhận tặng cho quyền sử dụng đất"
    # Mục IV(2) = hợp đồng; mục IV(3) = giấy tờ tùy thân/hộ tịch (KHÔNG gồm hợp đồng).
    assert "Hợp đồng tặng cho" in got[schema.K_GIAYTOKEM2]
    assert got[schema.K_GIAYTOKEM3].startswith("CCCD (bản sao")
    assert "Hợp đồng" not in got[schema.K_GIAYTOKEM3]
    assert got[schema.K_TRANHCHAP] == "Không có tranh chấp"
    assert got[schema.K_RANHGIOI].startswith("Không thay đổi")


def test_authorized_block_is_chu_ho_so_not_proxy():
    """doiTuongKhac* = CHỦ HỒ SƠ = người ủy quyền (Nguyễn Văn Dũng), KHÔNG phải người được ủy quyền."""
    got = _map(_SAMPLE, options={"purpose": "authorized_person"})
    assert got["doiTuongKhachoTen"] == "Nguyễn Văn Dũng"
    assert got["doiTuongKhacgioiTinhId"] == "Nam"
    assert got["doiTuongKhacsoDinhDanh"] == "027087017758"
    assert got["doiTuongKhacngayCap"] == "26/09/2024"
    assert got["doiTuongKhacnoiCap"] == "Bộ Công an"
    assert got["doiTuongKhacngaySinh"] == "28/08/1987"
    assert got["doiTuongKhacsoDienThoai"] == "0983696787"
    assert got["doiTuongKhactinhThanhId"] == "Bắc Ninh"
    assert got["doiTuongKhacphuongXaId"] == "Nam Sơn"
    assert got["doiTuongKhacdiaChiChiTiet"] == "Nam Sơn, Bắc Ninh"
    # KHÔNG lẫn field đơn.
    assert schema.K_TEN not in got


def test_optional_giayto_kem_khong_ep_mac_dinh():
    """"Có thì điền, không thì để trống": không có hợp đồng/giấy tờ kèm → ô (2)/(3) BỎ TRỐNG (không default)."""
    got = _map({"ChuHoSo_HoTen": "A", "ChuHoSo_SoDinhDanh": "1", "Don_LoaiGiaoDich": "tặng cho"})
    assert schema.K_GIAYTOKEM2 not in got  # không ép hd_default
    assert schema.K_GIAYTOKEM3 not in got
    assert schema.K_MIENGIAM not in got and schema.K_TRANHCHAP not in got
    # Ô bắt buộc "Nội dung biến động" vẫn suy ra được.
    assert got[schema.K_NOIDUNG] == "Nhận tặng cho quyền sử dụng đất"


def test_authorized_block_needs_chu_ho_so_identity():
    mapped, warnings = mapper.enrich(_fields({"Don_KinhGui": "X"}), {"purpose": "authorized_person"})
    assert mapped == [] and warnings and "chủ hồ sơ" in warnings[0].lower()


def test_registration_single_person_no_gop():
    got = _map({"ChuHoSo_HoTen": "Trần Thị B", "ChuHoSo_SoDinhDanh": "048301000999",
                "ChuHoSo_NgaySinh": "1990", "Don_LoaiGiaoDich": "chuyển nhượng"})
    assert got[schema.K_TEN] == "Trần Thị B, sinh năm 1990"
    assert got[schema.K_GIAYTO] == "048301000999 (Trần Thị B)"
    assert got[schema.K_NOIDUNG] == "Nhận chuyển nhượng quyền sử dụng đất"


def test_transaction_map_covers_new_types():
    for loai, noidung in [
        ("chuyển đổi", "Chuyển đổi quyền sử dụng đất nông nghiệp"),
        ("thừa kế", "Nhận thừa kế quyền sử dụng đất"),
        ("mua bán nhà ở có thời hạn", "Mua bán nhà ở có thời hạn"),
    ]:
        got = _map({"ChuHoSo_HoTen": "A", "Don_LoaiGiaoDich": loai})
        assert got[schema.K_NOIDUNG] == noidung, loai


def test_catalog_routes_tp_h05_and_supplementary():
    assert catalog.resolve("vb_tang_cho") == ("existing", "TP-H05.000080")
    assert catalog.resolve("hop_dong_chuyen_quyen") == ("existing", "TP-H05.000069")
    assert catalog.resolve("van_ban_dai_dien") == ("existing", "TP-H05.000079")
    assert catalog.resolve("gcn") == ("existing", "TP-H05.000040")
    assert catalog.resolve("don_bien_dong") == ("existing", "TP-H05.000026")
    for lbl in ("cccd", "ho_tich", "to_khai_thue", "bien_ban_ban_giao", "khac"):
        assert catalog.resolve(lbl) == ("supplementary", ""), lbl
    codes = [c for _, c, _ in catalog.CATALOG if c]
    assert len(codes) == 16 and len(set(codes)) == 16


def test_build_item_supplementary_and_existing():
    item = planner._build_item({"name": "ủy quyền.pdf"}, 0, "van_ban_dai_dien", "Giấy ủy quyền")
    assert item["target"] == "existing" and item["componentName"] == "TP-H05.000079"
    supp = planner._build_item({"name": "khai thue.pdf"}, 1, "to_khai_thue", "Tờ khai thuế")
    assert supp["target"] == "supplementary" and supp["componentName"] == ""


def test_schema_split_uyquyen_vs_don():
    """Ủy quyền chỉ nhân thân 1 người; Đơn thêm đồng sử dụng + nghiệp vụ; chung 6 trường _PERSON."""
    uq, don = schema.ALLOWED_UYQUYEN, schema.ALLOWED_DON
    # Ủy quyền có giới tính/ngày cấp/nơi cấp; Đơn KHÔNG cần (đơn không có ô riêng cho 3 cái này).
    assert {"ChuHoSo_GioiTinh", "ChuHoSo_NgayCap", "ChuHoSo_NoiCap"} <= uq
    assert not ({"ChuHoSo_GioiTinh", "ChuHoSo_NgayCap", "ChuHoSo_NoiCap"} & don)
    # Đơn có đồng sử dụng + MST + nghiệp vụ; ủy quyền KHÔNG.
    assert {"DongSuDung_HoTen", "ChuHoSo_MaSoThue", "Don_KinhGui", "Don_GiayToKem"} <= don
    assert not ({"DongSuDung_HoTen", "Don_KinhGui"} & uq)
    # Chung 6 trường nhân thân.
    assert {"ChuHoSo_HoTen", "ChuHoSo_SoDinhDanh", "ChuHoSo_NgaySinh", "ChuHoSo_ThuongTru",
            "ChuHoSo_DienThoai", "ChuHoSo_Email"} <= (uq & don)


def test_registry_entry():
    proc = get_procedure(_KEY)
    assert proc is not None and proc["mode"] == "agent" and proc["hasAttachmentStep"] is True
    assert "maThuTucHanhChinh=1.115468" in proc["detect"]["urlIncludes"]
    assert "dichvucong.bacninh.gov.vn" in proc["detect"]["urlScope"]
    assert get_attach_pipeline(_KEY) is not None


def test_thoa_thuan_1_115470_muc_rieng_dung_chung_pipeline():
    # 1.115470 (thỏa thuận hộ gia đình/vợ chồng…) cùng đơn Mẫu 18 → chạy chung pipeline 1.115468
    # nhưng là mục riêng để card hiện đúng tên.
    proc = get_procedure("dang-ky-bien-dong-thoa-thuan-bac-ninh")
    assert proc["detect"]["urlIncludes"] == ["maThuTucHanhChinh=1.115470"]
    assert proc["detect"]["urlScope"] == ["dichvucong.bacninh.gov.vn"]
    assert "thỏa thuận của các thành viên hộ gia đình" in proc["label"]
    assert "maThuTucHanhChinh=1.115470" not in get_procedure(_KEY)["detect"]["urlIncludes"]
    # Đính kèm KHÔNG dùng chung catalog: 18 thành phần 1.115470 khác 1.115468.
    from app.pipelines.dang_ky_bien_dong_dat_dai_bac_ninh.attach import plan_thoa_thuan
    assert get_attach_pipeline("dang-ky-bien-dong-thoa-thuan-bac-ninh") is plan_thoa_thuan


# 18 mã thành phần trên trang 1.115470 (crawl 20/10/2026).
_MA_TRANG_1115470 = {
    "TP-H05.000026", "TP-H05.000033", "TP-H05.000040", "TP-H05.000045", "TP-H05.000046",
    *(f"TP-H05.0000{n}" for n in range(85, 98)),
}


def test_catalog_thoa_thuan_chi_dung_ma_co_tren_trang_1_115470():
    ma = catalog.MA_THOA_THUAN
    codes = [c for _, c, _ in catalog.CATALOG_THOA_THUAN if c]
    assert len(codes) == len(set(codes)) == 18
    assert set(codes) == _MA_TRANG_1115470
    # Hai chỗ đính trượt ở bản dùng chung catalog 1.115468: thỏa thuận → 000069, ủy quyền → 000079.
    assert catalog.resolve("vb_thoa_thuan", ma) == ("existing", "TP-H05.000085")
    assert catalog.resolve("van_ban_dai_dien", ma) == ("existing", "TP-H05.000046")
    assert catalog.resolve("giay_to_hon_nhan", ma) == ("existing", "TP-H05.000086")
    for lbl in ("cccd", "ho_tich", "to_khai_thue", "khac"):
        assert catalog.resolve(lbl, ma) == ("supplementary", ""), lbl
    # Nhãn riêng của 1.115468 không hợp lệ ở 1.115470 (và ngược lại).
    assert not catalog.is_valid("hop_dong_chuyen_quyen", ma)
    assert not catalog.is_valid("vb_thoa_thuan")
    for lbl, _, _ in catalog.CATALOG_THOA_THUAN:
        assert catalog.display_name(lbl) != "Tài liệu kèm theo" or lbl == "khac", lbl
    # Mặc định vẫn là 1.115468.
    assert catalog.resolve("van_ban_dai_dien") == ("existing", "TP-H05.000079")


async def test_plan_thoa_thuan_dung_prompt_va_ma_rieng(monkeypatch):
    from app.pipelines.dang_ky_bien_dong_dat_dai_bac_ninh.attach import plan_thoa_thuan
    from app.process.schemas import FileItem
    from app.services import ocr

    texts = {
        "a.pdf": "VĂN BẢN THỎA THUẬN VỀ DIỆN TÍCH giữa những người cùng đứng tên",
        "b.pdf": "GIẤY ỦY QUYỀN",
        "c.pdf": "GIẤY KHAI SINH",
    }

    async def fake_ocr(files):
        return [{"name": f["name"], "text": texts[f["name"]]} for f in files]

    seen = {}

    async def fake_chat(messages, **_):
        seen["system"] = messages[0]["content"]
        return (
            '{"documents":[{"index":0,"label":"vb_thoa_thuan","documentName":"Văn bản thỏa thuận"},'
            '{"index":1,"label":"van_ban_dai_dien","documentName":"Giấy ủy quyền"},'
            '{"index":2,"label":"ho_tich","documentName":"Giấy khai sinh"}]}'
        )

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(planner.client, "chat", fake_chat)
    files = [FileItem(name=n, role="", type="application/pdf", dataUrl="data:application/pdf;base64,AA==") for n in texts]
    out = await plan_thoa_thuan(files)

    assert "vb_thoa_thuan" in seen["system"] and "TP-H05" not in seen["system"]
    got = [(a["detectedType"], a["target"], a["componentName"]) for a in out["attachments"]]
    assert got == [
        ("vb_thoa_thuan", "existing", "TP-H05.000085"),
        ("van_ban_dai_dien", "existing", "TP-H05.000046"),
        ("ho_tich", "supplementary", ""),
    ]


def test_dinh_chinh_gcn_da_cap_nhan_ma_moi_1_115436():
    # Cổng Bắc Ninh chuyển "Đính chính GCN đã cấp" sang 1.115436; mã 1.115476 vẫn dùng được nên có
    # entry riêng (trợ lý có thẻ tìm theo mã), cùng pipeline. Mỗi mã chỉ đúng một entry nhận.
    from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline

    for key, code in (("dinh-chinh-gcn-da-cap-bac-ninh", "1.115436"),
                      ("dinh-chinh-gcn-da-cap-1115476-bac-ninh", "1.115476")):
        proc = get_procedure(key)
        assert proc["detect"]["urlIncludes"] == [f"maThuTucHanhChinh={code}"]
        assert proc["detect"]["urlScope"] == ["dichvucong.bacninh.gov.vn"]
        trung = [p["key"] for p in PROCEDURES
                 if f"maThuTucHanhChinh={code}" in ((p.get("detect") or {}).get("urlIncludes") or [])]
        assert trung == [key]
    assert get_pipeline("dinh-chinh-gcn-da-cap-1115476-bac-ninh") is get_pipeline("dinh-chinh-gcn-da-cap-bac-ninh")
    assert (get_attach_pipeline("dinh-chinh-gcn-da-cap-1115476-bac-ninh")
            is get_attach_pipeline("dinh-chinh-gcn-da-cap-bac-ninh"))


def test_tro_ly_co_the_rieng_ma_1_115476():
    # Ô tìm "Tất cả thủ tục" của trợ lý lọc theo mã: thẻ 1.115476 phải mang đúng mã đó, mở link DVCQG
    # 1.115476 (chỉ chọn Tỉnh, không "chọn Sở"); thẻ cũ vẫn là 1.115436.
    from app.channels.handfree.procedure_registry import get_procedure as get_tl, procedure_code

    moi = get_tl("dinh-chinh-gcn-da-cap-1115476-bac-ninh")
    cu = get_tl("dinh-chinh-gcn-da-cap-bac-ninh")
    assert procedure_code(moi) == "1.115476" and procedure_code(cu) == "1.115436"
    assert moi["keKhaiUrl"].endswith("019f169e-c716-76a7-b47e-269721b1d9c2")
    assert moi["provinceOnly"] == ["bacninh"] and not moi.get("agencySoFirst")
    assert moi["label"] == cu["label"] == "Đính chính giấy chứng nhận đã cấp"


def test_dinh_chinh_gcn_da_cap_dinh_kem_theo_form_moi():
    # Crawl 13/10/2026 (eformId 2892): nhóm GCN đổi mã TP-H05.000040 → TP-H05.000165.S. Đơn đăng ký
    # đất đai Mẫu 13 có cụm "Giấy chứng nhận" + "quyền sử dụng đất" nhưng phải vào nhóm Đơn.
    from app.pipelines.dinh_chinh_gcn_da_cap_bac_ninh.attach import planner as dc_planner

    don_m13 = (
        "Mẫu số 13. Đơn đăng ký đất đai, tài sản gắn liền với đất\n"
        "ĐƠN ĐĂNG KÝ ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\nKính gửi: UBND phường Ví Dụ (1)\n"
        "Trường hợp đề nghị cấp Giấy chứng nhận ... Nhận quyền sử dụng đất của ông Nguyễn Văn B"
    )
    gcn = "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT, QUYỀN SỞ HỮU NHÀ Ở VÀ TÀI SẢN KHÁC GẮN LIỀN VỚI ĐẤT"
    assert dc_planner._detect_route_type(don_m13) == "application"
    assert dc_planner._detect_route_type(gcn) == "land_certificate"
    assert dc_planner._detect_route_by_filename("Đơn đk đất đai, ds người sd chung.pdf") == "application"

    gcn_item = dc_planner._build_item({"name": "so.pdf"}, 1, "land_certificate", "Giấy chứng nhận QSDĐ")
    assert gcn_item["componentName"] == "TP-H05.000165"
    # Tên dòng cổng hiện tại (crawl) phải chứa đúng componentName của từng nhóm.
    rows = [
        "TP-H05.000026 Mẫu số 18. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất",
        "TP-H05.000165.S Giấy chứng nhận đã cấp.",
        "TP-H05.000175.S Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận",
        "TP-H05.000115.S Văn bản về việc ủy quyền theo quy định của pháp luật về dân sự",
    ]
    for comp, _label in dc_planner._ROUTE.values():
        assert sum(comp in r for r in rows) == 1, comp

    # Link cũ 1.115476 (crawl 27/10/2026) vẫn mở eform cũ: nhóm GCN mang mã TP-H05.000040 → item GCN
    # gửi kèm mã cũ làm fallbackComponentName; nhóm khác không cần.
    assert gcn_item["fallbackComponentName"] == "TP-H05.000040"
    rows_cu = [
        "TP-H05.000026 Mẫu số 18. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất",
        "TP-H05.000040 Giấy chứng nhận đã cấp, trừ trường hợp thực hiện quyết định hoặc bản án",
        "TP-H05.000116.S Giấy tờ chứng minh sai sót thông tin ... so với thông tin trên Giấy chứng nhận đã cấp.",
        "TP-H05.000115.S Văn bản về việc ủy quyền theo quy định của pháp luật về dân sự",
    ]
    assert sum(gcn_item["fallbackComponentName"] in r for r in rows_cu) == 1
    don_item = dc_planner._build_item({"name": "don.pdf"}, 0, "application", "Đơn Mẫu 18")
    assert "fallbackComponentName" not in don_item


def test_dinh_chinh_gcn_da_cap_kinh_gui_va_hien_trang():
    from app.pipelines.dinh_chinh_gcn_da_cap_bac_ninh.process import fallback as dc_fallback
    from app.pipelines.dinh_chinh_gcn_da_cap_bac_ninh.process import mapper as dc_mapper
    from app.pipelines.dinh_chinh_gcn_da_cap_bac_ninh.process import schema as dc_schema

    got = dc_fallback.apply_ocr_fallback({}, [{"text": "Kính gửi: (1) UBND xã Ví Dụ\nHọ tên: A"}])
    assert got["Don_KinhGui"] == "UBND xã Ví Dụ"

    out = {f["name"]: f for f in dc_mapper.enrich([
        {"name": "Don_KinhGui", "value": "(1) Chi nhánh VP ĐKĐĐ Ví Dụ"},
        {"name": "Don_HienTrang", "value": "Sử dụng ổn định, không tranh chấp"},
    ])}
    assert out[dc_schema.K_KINHGUI]["value"] == "Chi nhánh VP ĐKĐĐ Ví Dụ"
    assert out["HienTrangSuDungDatSuDungOnDinh"] == {
        "name": "HienTrangSuDungDatSuDungOnDinh", "comp": "bn-textarea",
        "value": "Sử dụng ổn định, không tranh chấp",
    }
    assert "Don_HienTrang" in dc_schema.ALLOWED
