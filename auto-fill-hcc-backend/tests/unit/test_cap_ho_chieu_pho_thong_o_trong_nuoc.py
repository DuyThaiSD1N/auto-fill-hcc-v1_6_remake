"""Cấp hộ chiếu phổ thông ở trong nước 1.001456 (Cổng DVC Bộ Công an): mapper ô form + đính kèm + nối registry / link
kê khai + trợ lý người dân."""
from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process import mapper
from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process.schema import (
    ALLOWED,
    COMPACT_COMP_BY_NAME,
    DE_NGHI_HET_HAN,
    DE_NGHI_KHAC,
    DE_NGHI_LAN_DAU,
    DE_NGHI_MAT,
)
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS, with_ke_khai_detect_urls

KEY = "cap-ho-chieu-pho-thong-o-trong-nuoc"
# Hồ sơ mẫu bịa cùng khuôn bộ mẫu: người thành niên tự nộp, hộ chiếu cũ cấp trước sáp nhập tỉnh (nơi sinh tỉnh cũ),
# tờ khai đề nghị khác "đổi từ CMND sang căn cước", cha mẹ chỉ ghi năm sinh.
HO_SO = {
    "ToKhai_Ho": "TRẦN", "ToKhai_ChuDemTen": "VĂN AN", "ToKhai_GioiTinh": "Nam", "ToKhai_NgaySinh": "02/03/1985",
    "ToKhai_NoiSinh": "Hưng Yên", "ToKhai_SoDinhDanh": "0340 8500 0001", "ToKhai_NgayCap": "10/06/2021",
    "ToKhai_DienThoai": "0912.345.678",
    "ToKhai_ThuongTru": {"tinh": "Tỉnh Lai Châu", "xa": "Phường Đoàn Kết", "chiTietDuoiXa": "Tổ dân phố số 2"},
    "ToKhai_TamTru": {"tinh": "Lạng Sơn", "xa": "Phường Kỳ Lừa", "chiTietDuoiXa": "Số 10 Tổ 1, Khối 2"},
    "ToKhai_NgheNghiep": "Tự do", "ToKhai_Cha_NgaySinh": "1950", "ToKhai_Me_NgaySinh": "năm 1952",
    "ToKhai_VoChong_HoTen": "NGUYỄN THỊ BÌNH", "ToKhai_VoChong_NgaySinh": "1990",
    "ToKhai_HoChieuCu_So": "C1234567", "ToKhai_HoChieuCu_NgayCap": "01/02/2019",
    "ToKhai_NoiDungDeNghi": "Đề nghị khác. . Thay đổi từ CMND sang Căn cước",
    "ToKhai_DiaChiNhanHoChieu": "Phòng Quản lý XNC-Công an tỉnh Lai Châu",
    "ToKhai_DonViTiepNhan": "Phòng Quản lý XNC-Công an tỉnh Lai Châu",
    "HoChieu_So": "C1234567", "HoChieu_HoTen": "TRẦN VĂN AN", "HoChieu_NoiSinh": "THÁI BÌNH",
    "HoChieu_NgayCap": "01/02/2019", "HoChieu_NgayHetHan": "01/02/2029", "HoChieu_NoiCap": "Cục Quản lý xuất nhập cảnh",
}


def _enrich(values: dict):
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], {})


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_dien_dung_mapping_bo_mau():
    out, warnings = _enrich(HO_SO)
    assert _by(out) == {
        # Cơ quan tiếp nhận: extension chọn mục thật đầu tiên (firstOption, user 19/11/2026).
        "CongDan__fs_BCANoiNopHS": "Cơ quan đã chọn ở bước chọn trường hợp hồ sơ",
        "CongDan__fsBCAHoCongDan": "TRẦN",
        "CongDan__fsBCAChuDemTen": "VĂN AN",
        "CongDan__fs_BCANoiKhaiSinhCD": "Hưng Yên",  # hộ chiếu ghi tỉnh cũ "THÁI BÌNH" → tỉnh sau sắp xếp
        "CongDan__fs_BCANgayCapCCCD": "10/06/2021",
        "CongDan__fs_BCANoiCapCCCD": "Cục CS QLHC về TTXH",  # CCCD 12 số cấp 2021 → suy theo ngày cấp
        "CongDan_diDong": "0912345678",
        "CongDan__fs_BCAQueQuanMaTinh": "Tỉnh Lai Châu",
        "CongDan__fs_BCAQueQuanMaQH": "Phường Đoàn Kết",
        "CongDan__fs_BCAQueQuanChiTiet": "Tổ dân phố số 2",
        "CongDan__fs_BCANoiOHienTaiMaTinh": "Tỉnh Lạng Sơn",
        "CongDan__fs_BCANoiOHienTaiMaQH": "Phường Kỳ Lừa",
        "CongDan__fs_BCADiaChiThuongTruCD": "Số 10 Tổ 1, Khối 2",
        "CongDan__fs_BCANgheNghiepCD": "Tự do",
        "CongDan__fs_BCANgaySinhChaCD": "1950",
        "CongDan__fs_BCANgaySinhMeCD": "1952",
        "CongDan__fsBCAHoVaTenVoChong": "NGUYỄN THỊ BÌNH",
        "CongDan__fs_BCANgaySinhVoChong": "1990",
        "CongDan__fs_BCAHoChieuPT": "C1234567",
        "CongDan__fs_BCANgayCapHoChieuPT": "01/02/2019",
        "CongDan__fs_BCANoiCapHCGanNhat": "Cục Quản lý xuất nhập cảnh",
        "CongDan__fs_BCANoiDungDeNghi": DE_NGHI_KHAC,
        "CongDan__fs_BCAChiTietDeNghi": "Thay đổi từ CMND sang Căn cước",
        "CongDan__fsBCAHoChieuGanChip": True,
        "CongDan__fs_BCANoiNhanHoChieu": True,
    }
    fields = {f["name"]: f for f in out}
    # Năm sinh cha/mẹ/vợ chồng: chọn định dạng "Năm" trước khi gõ; Phường/xã nạp theo tỉnh → chờ thêm.
    assert fields["CongDan__fs_BCANgaySinhChaCD"]["dateFormat"] == "Năm"
    assert fields["CongDan__fs_BCANgaySinhVoChong"]["dateFormat"] == "Năm"
    assert "dateFormat" not in fields["CongDan__fs_BCANgayCapCCCD"]
    assert fields["CongDan__fs_BCAQueQuanMaQH"]["waitMs"] == 8000 and fields["CongDan__fs_BCANoiOHienTaiMaQH"]["waitMs"]
    # Ô khoá do CSDLQG về dân cư đổ sẵn: không phát.
    for locked in ("CongDan_tenCongDan", "CongDan_soCmnd", "CongDan__fs_BCAGioiTinhCd", "CongDan__fs_BCANgaySinhCD",
                   "CongDan__fs_BCADanToc", "CongDan__fs_BCATonGiao", "CongDan__fs_BCAHoVaTenCha"):
        assert locked not in fields
    joined = " ".join(warnings)
    assert "Ảnh chân dung" in joined and "hoàn tiền" in joined and "Email" in joined
    assert "loại hộ chiếu" in joined  # tờ khai không thấy rõ ô đánh dấu → mặc định có chip, cảnh báo
    # Ô 17 theo cơ quan đã chọn ở bước chọn trường hợp → không phát, chỉ nhắc đơn vị trên tờ khai.
    assert "Công an tỉnh Lai Châu — kiểm tra ô 17" in joined


def test_noi_dung_de_nghi_va_loai_chip():
    by = _by(_enrich({**HO_SO, "ToKhai_NoiDungDeNghi": "Cấp lại hộ chiếu do bị mất",
                      "ToKhai_LoaiHoChieu": "khong_chip"})[0])
    assert by["CongDan__fs_BCANoiDungDeNghi"] == DE_NGHI_MAT and "CongDan__fs_BCAChiTietDeNghi" not in by
    assert by["CongDan__fsBCAHoKhongChieuGanChip"] is True and "CongDan__fsBCAHoChieuGanChip" not in by
    # Không có hộ chiếu cũ, mục 14 trống → cấp lần đầu, không phát ô mục 13.
    values = {k: v for k, v in HO_SO.items()
              if not k.startswith("HoChieu_") and k not in ("ToKhai_HoChieuCu_So", "ToKhai_HoChieuCu_NgayCap",
                                                             "ToKhai_NoiDungDeNghi")}
    by = _by(_enrich(values)[0])
    assert by["CongDan__fs_BCANoiDungDeNghi"] == DE_NGHI_LAN_DAU and "CongDan__fs_BCAHoChieuPT" not in by
    # Hộ chiếu cũ đã hết hạn, mục 14 trống → cấp lại do hết hạn.
    values = {**HO_SO, "HoChieu_NgayHetHan": "01/02/2020"}
    values.pop("ToKhai_NoiDungDeNghi")
    assert _by(_enrich(values)[0])["CongDan__fs_BCANoiDungDeNghi"] == DE_NGHI_HET_HAN


def test_giay_nguoi_khac_bi_bo_va_nhan_qua_buu_chinh_canh_bao():
    out, warnings = _enrich({**HO_SO, "HoChieu_HoTen": "TRẦN THỊ CÚC", "HoChieu_So": "C7654321",
                             "ToKhai_DiaChiNhanHoChieu": "Số 10 Tổ 1, Khối 2, Phường Kỳ Lừa, Tỉnh Lạng Sơn"})
    by = _by(out)
    # Hộ chiếu của người khác → lấy số + ngày cấp theo mục 13 tờ khai, nơi sinh theo tờ khai.
    assert by["CongDan__fs_BCAHoChieuPT"] == "C1234567" and by["CongDan__fs_BCANgayCapHoChieuPT"] == "01/02/2019"
    assert "CongDan__fs_BCANoiCapHCGanNhat" not in by and by["CongDan__fs_BCANoiKhaiSinhCD"] == "Hưng Yên"
    assert any("Hộ chiếu tải lên không phải của người đề nghị" in w for w in warnings)
    assert "CongDan__fs_BCANoiNhanHoChieu" not in by and any("Nhận qua bưu chính" in w for w in warnings)


def test_so_ho_chieu_ocr_doc_nham_va_mrz():
    # Chạy thật bộ mẫu 18/11: OCR đọc "5" thành "S" ở trang nhân thân và chen thêm "S" ở mục 13 tờ khai.
    out, warnings = _enrich({**HO_SO, "HoChieu_So": "CS234567", "ToKhai_HoChieuCu_So": "CS1234567"})
    assert _by(out)["CongDan__fs_BCAHoChieuPT"] == "C5234567"
    # Dòng MRZ đúng chữ số kiểm tra thắng số in trên trang; MRZ sai chữ số kiểm tra thì bỏ qua MRZ.
    mrz = "C1234567<0VNM8503029M2902014034085000001<<10"
    by = _by(_enrich({**HO_SO, "HoChieu_So": "CS234567", "HoChieu_MRZ": mrz})[0])
    assert by["CongDan__fs_BCAHoChieuPT"] == "C1234567"
    by = _by(_enrich({**HO_SO, "HoChieu_So": "C7654321", "HoChieu_MRZ": mrz.replace("<0VNM", "<3VNM")})[0])
    assert by["CongDan__fs_BCAHoChieuPT"] == "C7654321"
    # Tờ khai chen chữ thừa mà vẫn là cùng cuốn hộ chiếu → không cảnh báo lệch số.
    _, warnings = _enrich({**HO_SO, "HoChieu_MRZ": mrz, "ToKhai_HoChieuCu_So": "CS1234567"})
    assert not any("khác hộ chiếu tải lên" in w for w in warnings)


def test_fallback_ocr_khi_llm_bo_sot():
    to_khai = ("TỜ KHAI\n(Dùng cho công dân Việt Nam đề nghị cấp hộ chiếu phổ thông ở trong nước)\n"
               "13. Hộ chiếu phổ thông lần gần nhất (nếu có) số CS1234567 cấp ngày 01/02/2019\n"
               "14. Nội dung đề nghị(4) Đề nghị khác.. Thay đổi từ CMND sang Căn cước\n"
               "Cấp hộ chiếu không gắn chip điện tử ☐ Cấp hộ chiếu có gắn chip điện tử [X]")
    ho_chieu = "HỘ CHIẾU / PASSPORT\nP<VNMTRAN<<VAN<AN<<<<\nC1234567<0VNM8503029M2902014034085000001<<10"
    fields = mapper.ocr_fallback([{"name": "ToKhai_Ho", "value": "TRẦN"}],
                                 [{"name": "tk.pdf", "text": to_khai}, {"name": "hc.jpg", "text": ho_chieu}])
    assert fields["ToKhai_NoiDungDeNghi"] == "Đề nghị khác.. Thay đổi từ CMND sang Căn cước"
    assert fields["ToKhai_LoaiHoChieu"] == "co_chip" and fields["ToKhai_HoChieuCu_So"] == "CS1234567"
    assert fields["HoChieu_MRZ"].startswith("C1234567<0VNM")
    # LLM đã trả thì giữ nguyên; ô "không gắn chip" được đánh dấu → khong_chip.
    fields = mapper.ocr_fallback({"ToKhai_NoiDungDeNghi": "Cấp hộ chiếu lần đầu"},
                                 [{"text": to_khai.replace("điện tử ☐", "điện tử [X]").replace("tử [X]\n", "tử ☐\n")
                                   .replace("có gắn chip điện tử [X]", "có gắn chip điện tử ☐")}])
    assert fields["ToKhai_NoiDungDeNghi"] == "Cấp hộ chiếu lần đầu" and fields["ToKhai_LoaiHoChieu"] == "khong_chip"


def test_chan_khi_giay_to_cua_nguoi_khac_chu_tai_khoan():
    fields = [{"name": k, "value": v} for k, v in HO_SO.items()]

    def run(context):
        return mapper.enrich(fields, {"formContext": context})

    # Ô khoá Họ và tên / Số CCCD của tài khoản khác người trên tờ khai → không phát ô nào, chỉ một câu báo.
    out, warnings = run({"applicantFullname": "LÊ THỊ MAI", "applicantIdentityNumber": "001190000002"})
    assert out == [] and len(warnings) == 1
    assert warnings[0].startswith("Chưa điền: giấy tờ tải lên là của TRẦN VĂN AN, còn tài khoản VNeID đang đăng nhập "
                                  "là của LÊ THỊ MAI.")
    assert "Vui lòng tải giấy tờ đúng của LÊ THỊ MAI (chủ tài khoản VNeID)" in warnings[0]
    # Chỉ có tên (cổng chưa đổ số) mà tên khác → vẫn chặn; tên viết thường vẫn in hoa trong câu báo.
    assert run({"applicantFullname": "Lê Thị Mai"})[0] == []
    blocked = mapper.account_block(mapper._by_name(fields), {"formContext": {"applicantFullname": "Lê Thị Mai"}})
    assert blocked["code"] == "account_mismatch" and blocked["accountName"] == "LÊ THỊ MAI"
    assert blocked["documentName"] == "TRẦN VĂN AN"
    # Chỉ có số định danh tài khoản → câu báo gọi theo số.
    blocked = mapper.account_block(mapper._by_name(fields), {"formContext": {"applicantIdentityNumber": "001190000002"}})
    assert blocked["accountName"] == "người có số định danh 001190000002"
    # Đúng chủ tài khoản → điền như thường, không cảnh báo đối chiếu.
    out, warnings = run({"applicantFullname": "TRẦN VĂN AN", "applicantIdentityNumber": "034085000001"})
    assert _by(out)["CongDan__fsBCAHoCongDan"] == "TRẦN"
    assert not any("Chưa điền" in w or "Chưa đối chiếu" in w for w in warnings)
    # Trùng số định danh, OCR đọc lệch tên → số thắng, vẫn điền.
    assert run({"applicantFullname": "TRẦN VĂN ÂN", "applicantIdentityNumber": "034085000001"})[0]
    # Lệch số nhưng tên trùng (OCR đọc nhầm chữ số) → không chặn.
    assert run({"applicantFullname": "Trần Văn An", "applicantIdentityNumber": "034085000009"})[0]
    # Không có mốc tài khoản (extension cũ) → điền như cũ, kèm nhắc kiểm tra.
    out, warnings = _enrich(HO_SO)
    assert out and mapper.NO_ACCOUNT_WARNING in warnings


def test_runner_tra_blocked_va_tro_ly_noi_ro_ly_do(monkeypatch):
    """Auto Fill hiện nguyên blocked.message; trợ lý ghép tên vào vi.ACCOUNT_MISMATCH (không phải câu "chụp rõ hơn")."""
    from app.channels.handfree.chat import flow
    from app.channels.handfree.chat import script_vi as vi
    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process import runner as hc_runner

    async def fake_run(files_by_role, **kwargs):
        return {"fields": [{"name": k, "value": v} for k, v in HO_SO.items()], "errors": [], "extracted": {}}

    monkeypatch.setattr(hc_runner.runner, "run", fake_run)
    res = asyncio.run(hc_runner.run({}, {"formContext": {"applicantFullname": "LÊ THỊ MAI"}}))
    assert res["fields"] == [] and res["blocked"]["code"] == "account_mismatch"
    assert res["errors"] == [res["blocked"]["message"]]
    md, tts = flow._fmt(vi.ACCOUNT_MISMATCH, account=res["blocked"]["accountName"],
                        document=res["blocked"]["documentName"])
    assert "Giấy tờ công dân gửi là của **TRẦN VĂN AN**" in md and "gửi giấy tờ đúng của **LÊ THỊ MAI**" in md
    assert "LÊ THỊ MAI" in tts
    # Đúng chủ tài khoản → không có blocked, điền như thường.
    res = asyncio.run(hc_runner.run({}, {"formContext": {"applicantFullname": "Trần Văn An"}}))
    assert "blocked" not in res and res["fields"]


def test_noi_sinh_nuoc_ngoai_va_dia_chi_cccd_du_phong():
    values = {**HO_SO, "HoChieu_NoiSinh": "NHẬT BẢN", "Cccd_HoTen": "Trần Văn An", "Cccd_SoDinhDanh": "034085000001",
              "Cccd_NgayCap": "10/06/2021", "Cccd_NoiCap": "Cục trưởng Cục Cảnh sát quản lý hành chính về trật tự xã hội",
              "Cccd_NoiThuongTru": {"tinh": "Lai Châu", "xa": "Phường Đoàn Kết", "chiTietDuoiXa": "Tổ 2"}}
    values.pop("ToKhai_ThuongTru")
    by = _by(_enrich(values)[0])
    assert by["CongDan__fs_BCANoiKhaiSinhCD"] == "Nhật Bản"
    assert by["CongDan__fs_BCAQueQuanMaTinh"] == "Tỉnh Lai Châu" and by["CongDan__fs_BCAQueQuanChiTiet"] == "Tổ 2"
    assert by["CongDan__fs_BCANoiCapCCCD"] == "Cục CS QLHC về TTXH"


def test_schema_registry_link_va_detect():
    assert {"ToKhai_Ho", "ToKhai_Cha_NgaySinh", "HoChieu_So", "Cccd_NgayCap"} <= ALLOWED
    assert COMPACT_COMP_BY_NAME["ToKhai_ThuongTru"] == "x-select-area"
    assert COMPACT_COMP_BY_NAME["ToKhai_Cha_NgaySinh"] == "x-input"  # năm trần, không ép dd/mm/yyyy
    assert registry.get_pipeline(KEY) is not None and registry.get_attach_pipeline(KEY) is not None
    proc = registry.get_procedure(KEY)
    assert proc["hasAttachmentStep"] is True and proc["supportsSplitDocuments"] is True and proc["mode"] == "agent"
    assert proc["detect"]["urlScope"] == ["dichvucong.bocongan.gov.vn"]
    assert proc["detect"]["textIncludes"] == ["hộ chiếu phổ thông"]
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.001456" and link["label"] == proc["label"]
    assert link["needsAgencySelect"] is False and link["directSubmit"] is True and link["bcaSubmit"] is True
    public = next(p for p in with_ke_khai_detect_urls([proc]) if p["key"] == KEY)
    assert "matthc=1.001456" in public["detect"]["urlIncludes"]


# ── Trợ lý người dân (handfree) ──
from app.channels.handfree.chat import flow  # noqa: E402
from app.channels.handfree.chat.intents import Intent  # noqa: E402

CAPS = {"supportsBcaHoChieu": True}


def test_tro_ly_cung_key_detect_hien_moi_tinh_va_mo_thang_trang_chon_truong_hop():
    from app.channels.handfree import procedure_registry as hf
    from app.channels.handfree.chat.router import _clean_client_capabilities

    proc = hf.get_procedure(KEY)
    assert proc["detect"] == registry.get_procedure(KEY)["detect"] and proc["label"] == registry.get_procedure(KEY)["label"]
    assert proc["requiresCapability"] == "supportsBcaHoChieu" and proc["hasAttachmentStep"] is True
    assert proc["supportsSplitDocuments"] is True and hf.get_attach_pipeline(KEY) is registry.get_attach_pipeline(KEY)
    assert proc["keKhaiUrl"].endswith("chon-truong-hop-ho-so?ma-thu-tuc-public=29497")
    assert hf.get_pipeline(KEY) is registry.get_pipeline(KEY) and "provinceOnly" not in proc
    for slug in ("khanhhoa", "laichau", "bacninh", "quangninh", ""):
        assert KEY in {p["key"] for p in hf.public_list_for(slug)}, slug
    assert _clean_client_capabilities({"supportsBcaHoChieu": True})["supportsBcaHoChieu"] is True

    # Bản trợ lý chưa khai cờ: không dẫn vào cổng.
    conv = {"state": "greet", "procedure_key": None, "location": {}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert "chưa hỗ trợ" in r.display_md and not r.actions
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Phường Đoàn Kết"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._start_guide_login(conv)
    assert conv["state"] == "guide_login" and r.actions[0]["url"] == proc["keKhaiUrl"]
    flow._handle_guide_login(conv, Intent("event", "page_status", {"loggedIn": True, "formKind": "standard"}))
    assert conv["state"] in ("ask_doc_method", "consent")


def test_tro_ly_tu_chon_co_quan_theo_tinh_chi_hoi_truong_hop_giai_quyet():
    caps = {**CAPS, "supportsLaiChauFeeStep": True, "supportsBcaCaseStep": True}
    # Tỉnh của TÀI KHOẢN trợ lý thắng nơi làm thủ tục đã chọn (user 18/11).
    conv = {"_id": "c1", "state": "greet", "procedure_key": None, "client_capabilities": caps,
            "auth_user": {"tinh": "Khánh Hòa", "province_slug": "khanhhoa"},
            "location": {"province": "Tỉnh Lai Châu", "province_slug": "laichau", "ward": "Phường Đoàn Kết"}}
    flow._to_confirm_procedure(conv, KEY)
    flow._start_guide_login(conv)
    turn = lambda kind, value, payload=None: asyncio.run(flow._handle_turn_inner(conv, Intent(kind, value, payload or {})))  # noqa: E731
    r = turn("event", "page_status", {"loggedIn": True, "formKind": "", "lcStep": 1})
    # Tới trang: extension tự dò ô + chọn sẵn ô cơ quan theo tỉnh công dân chọn lúc đầu (ưu tiên mục "Công an …").
    assert r.actions == [{"type": "lc_result_scan", "groups": [{"name": "*"}],
                          "presets": [{"label": "Cơ quan giải quyết hồ sơ", "match": "khanh hoa", "prefer": "cong an"}]}]
    assert "**Trường hợp giải quyết**" in r.display_md
    # Extension đã chọn cơ quan, cổng hiện ô Trường hợp giải quyết (2 lựa chọn) → báo đã chọn + chỉ hỏi ô đó.
    agency = {"name": "maCoQuan", "present": True, "value": "Công an tỉnh Khánh Hòa", "options": ["Công an tỉnh Khánh Hòa"],
              "fixed": False, "label": "Cơ quan giải quyết hồ sơ", "required": True}
    case = {"name": "maQttt", "present": True, "value": "",
            "options": ["8 ngày làm việc - Cấp hộ chiếu phổ thông cho người đủ từ 14 tuổi",
                        "8 ngày làm việc - Cấp hộ chiếu phổ thông cho trẻ em dưới 14 tuổi"],
            "fixed": False, "label": "Trường hợp giải quyết", "required": True}
    r = turn("action", "lc_result_report", {"groups": [agency, case], "prepared": ["preset:maCoQuan"]})
    assert "Tôi đã chọn sẵn **Cơ quan giải quyết hồ sơ**: **Công an tỉnh Khánh Hòa**" in r.display_md
    trail = " ".join(a.get("md", "") for a in r.actions if a.get("type") == "trail_message")
    assert "**Trường hợp giải quyết**" in trail and "**Cơ quan giải quyết hồ sơ**" not in trail
    # Thẻ: dòng cơ quan chỉ hiện giá trị (không dãy nút tỉnh bị cắt 8 mục), dòng trường hợp có 2 nút.
    rows = {row["name"]: row for row in r.cards[0]["rows"]}
    assert rows["maCoQuan"]["fixed"] is True and rows["maCoQuan"]["options"] == []
    assert len(rows["maQttt"]["options"]) == 2
    # Cổng chặn / ô đổi → đọc lại vẫn kèm preset để chọn bù khi lượt đầu ô cơ quan chưa nạp kịp.
    r = turn("action", "lc_case_changed", {})
    assert r.actions[0]["prepare"] is False and r.actions[0]["presets"][0]["match"] == "khanh hoa"
    # Không biết tỉnh → không preset, công dân tự chọn cả hai ô trên thẻ.
    conv2 = {"_id": "c2", "state": "greet", "procedure_key": None, "client_capabilities": caps, "location": {}}
    flow._to_confirm_procedure(conv2, KEY)
    flow._start_guide_login(conv2)
    r = asyncio.run(flow._handle_turn_inner(conv2, Intent("event", "page_status",
                                                          {"loggedIn": True, "formKind": "", "lcStep": 1})))
    assert "presets" not in r.actions[0]


# ── Đính kèm: bảng Thành phần hồ sơ 2 dòng ──
import asyncio  # noqa: E402
import base64  # noqa: E402
import json  # noqa: E402

from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.attach import planner as attach_planner  # noqa: E402
from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.attach.dinh_kem_khong_tach import (  # noqa: E402
    planner as whole_planner,
)
from app.process.schemas import FileItem  # noqa: E402
from app.services import ocr as ocr_service  # noqa: E402
from app.services.llm import client as llm_client  # noqa: E402

TO_KHAI = ("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nTỜ KHAI\n(Dùng cho công dân Việt Nam đề nghị cấp hộ chiếu phổ thông ở "
           "trong nước)\n1. Họ TRẦN Chữ đệm và tên VĂN AN\n13. Hộ chiếu phổ thông lần gần nhất (nếu có) số C1234567")
HO_CHIEU = ("HỘ CHIẾU / PASSPORT\nSố hộ chiếu / Passport No C1234567\nHọ và tên / Full name TRẦN VĂN AN\n"
            "P<VNMTRAN<<VAN<AN<<<<<<<<<<<<<<<<<<<<<<<<<<<")
HO_CHIEU_2 = "CƠ QUAN CẤP HỘ CHIẾU\nISSUING AUTHORITY\nCỤC QUẢN LÝ XUẤT NHẬP CẢNH"
KHAI_SINH = "GIẤY KHAI SINH\nHọ, chữ đệm, tên: TRẦN MINH KHANG"
ROW2 = ["ho chieu pho thong cap lan gan nhat"]


def _file(name: str, size: int = 10) -> FileItem:
    data = base64.b64encode(b"x" * size).decode()
    return FileItem(name=name, type="application/pdf", dataUrl=f"data:application/pdf;base64,{data}", role="other")


def _pdf_text(*pages: str) -> str:
    return "\n".join(f"───── Trang {i}/{len(pages)} ─────\n{text}" for i, text in enumerate(pages, 1))


def _mock_io(monkeypatch, texts: dict[str, str], llm):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": texts.get(f["name"], "")} for f in files]

    async def fake_chat(messages, **_):
        return llm(messages) if callable(llm) else llm

    monkeypatch.setattr(ocr_service, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(llm_client, "chat", fake_chat)


def _slots(result) -> dict:
    return {a["slotIndex"]: a for a in result["attachments"] if a["target"] == "fixed-slot"}


def test_dinh_kem_khong_tach_ho_chieu_va_to_khai_chung_dong_2(monkeypatch):
    # Ảnh ánh xạ: tờ khai [F2] tải trước vẫn đứng SAU hộ chiếu [F1] trong dòng 2; dòng 1 không tick.
    files = [_file("to-khai.pdf"), _file("ho-chieu.jpg")]
    texts = {"to-khai.pdf": TO_KHAI, "ho-chieu.jpg": HO_CHIEU + "\n" + HO_CHIEU_2}
    llm = json.dumps({"documents": [{"index": 0, "docType": "to_khai", "documentName": ""},
                                    {"index": 1, "docType": "ho_chieu", "documentName": ""}]})
    _mock_io(monkeypatch, texts, llm)
    result = asyncio.run(attach_planner.plan(files, {}, {}))
    assert result["extracted"]["attachmentMode"] == "whole"
    slots = _slots(result)
    assert list(slots) == [1] and len(result["attachments"]) == 1
    row = slots[1]
    assert row["fileIndex"] == 1 and row["sourceFileIndexes"] == [1, 0] and row["tickRow"] is True
    assert row["slotKeywords"] == ROW2 and "sourceSegments" not in row
    assert any("đính kèm chung 2 giấy" in e for e in result["errors"])


def test_dinh_kem_luat_tieu_de_dai_dien_dong_1_va_cap_lan_dau(monkeypatch):
    files = [_file("ks.pdf"), _file("hc.pdf"), _file("tk.pdf")]
    texts = {"ks.pdf": KHAI_SINH, "hc.pdf": HO_CHIEU, "tk.pdf": TO_KHAI}
    _mock_io(monkeypatch, texts, "không phải JSON")  # LLM hỏng → luật theo tiêu đề
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": False}, {}))
    slots = _slots(result)
    assert slots[0]["fileIndex"] == 0 and slots[0]["slotKeywords"] == ["chung minh nguoi dai dien hop phap"]
    assert slots[1]["sourceFileIndexes"] == [1, 2]
    # Cấp lần đầu (không hộ chiếu cũ): dòng 2 trống, tờ khai không đính, cảnh báo; tệp > 6 MB bị loại.
    files = [_file("tk.pdf"), _file("to.pdf", 7 * 1024 * 1024)]
    result = asyncio.run(whole_planner.plan(files, {}, {}))
    assert result["attachments"] == []
    assert any("dòng \"Hộ chiếu phổ thông cấp lần gần nhất\" để trống" in e for e in result["errors"])
    assert any("Chưa đính kèm 'tk.pdf'" in e for e in result["errors"])
    assert any("vượt giới hạn 6 MB" in e for e in result["errors"])


def test_dinh_kem_tach_dung_dong_khong_sot_trang(monkeypatch):
    # Một PDF gộp: tờ khai (1 trang) + hộ chiếu (2 trang) + trang trắng.
    files = [_file("ho-so.pdf")]
    texts = {"ho-so.pdf": _pdf_text(TO_KHAI, HO_CHIEU, HO_CHIEU_2, "~ . ~")}
    llm = json.dumps({
        "tep": [{"fileIndex": 0, "tieuDeTrang": ["Tờ khai đề nghị cấp hộ chiếu", "Hộ chiếu phổ thông", "", ""]}],
        "documents": [
            {"fileIndex": 0, "pages": [1], "docType": "to_khai", "documentName": "Tờ khai"},
            {"fileIndex": 0, "pages": [2, 3], "docType": "ho_chieu", "documentName": "Hộ chiếu"},
            {"fileIndex": 0, "pages": [4], "docType": "blank_page", "documentName": ""},
        ],
    })
    _mock_io(monkeypatch, texts, llm)
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": True}, {}))
    assert result["extracted"]["attachmentMode"] == "split"
    slots = _slots(result)
    assert list(slots) == [1]
    # Hộ chiếu trước, tờ khai sau, cùng một tệp ghép.
    assert slots[1]["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1, 2]}, {"fileIndex": 0, "pageIndexes": [0]}]
    # Không sót trang có chữ; trang 4 không có chữ là trang trắng → bỏ (khung chia trang dùng chung).
    pages = sorted(p for a in result["attachments"] for s in a.get("sourceSegments") or [] for p in s["pageIndexes"])
    assert pages == [0, 1, 2]


def test_dinh_kem_tach_loi_quay_ve_khong_tach(monkeypatch):
    files = [_file("hc.pdf"), _file("tk.pdf")]
    texts = {"hc.pdf": HO_CHIEU, "tk.pdf": TO_KHAI}

    def broken(_messages):
        raise RuntimeError("LLM sập")

    _mock_io(monkeypatch, texts, broken)
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": True}, {}))
    assert result["errors"][0].startswith("attachment_agent (tách)")
    assert result["extracted"]["attachmentMode"] == "whole"
    assert _slots(result)[1]["sourceFileIndexes"] == [0, 1]
    assert not any(a.get("sourceSegments") for a in result["attachments"])


# ── Trợ lý: vòng bổ sung ô trên eForm Nth Bộ Công an (cờ supportsBcaNthReview, user 19/11/2026) ──
NTH_CAPS = {**CAPS, "supportsLaiChauFeeStep": True, "supportsBcaCaseStep": True, "supportsFieldReview": True,
            "supportsBcaNthReview": True}
SAME_PAGE = {"pageContextCaptured": True, "formKind": "standard", "attachmentTarget": True,
             "attachmentComponentCount": 2, "bcaKeKhaiForm": True}


def _nth_conv(caps: dict, **extra) -> dict:
    return {"_id": "t-nth-review", "state": "attaching", "history": [], "procedure_key": KEY, "upload_session_id": "s1",
            "docs_target": "declaration", "docs_page_context": flow._docs_page_context(SAME_PAGE),
            "client_capabilities": dict(caps), **extra}


def _attach_done(conv: dict, review: dict | None = None, errors: list | None = None):
    conv.update(attach_plan=[{"fileIndex": 0, "target": "fixed-slot", "slotIndex": 1}],
                attach_action_in_progress=True, attach_action_dispatch_id="d1", fill_report={"filled": 30})
    payload = {"attached": 1, "skipped": 0, "errors": errors or [], "dispatch_id": "d1"}
    if review is not None:
        payload["review"] = review
    return asyncio.run(flow._handle_attaching(conv, Intent("action", "attach_report", payload)))


def test_tro_ly_bca_nth_an_dong_y_va_tiep_tuc_khi_con_o_bat_buoc_trong():
    from app.channels.handfree.chat import field_review, lai_chau
    from app.channels.handfree.chat import script_vi as vi
    from app.channels.handfree.chat.router import _clean_client_capabilities
    from app.channels.handfree import procedure_registry as hf

    proc = hf.get_procedure(KEY)
    assert _clean_client_capabilities({"supportsBcaNthReview": True})["supportsBcaNthReview"] is True
    assert field_review.bca_nth(proc) and not field_review.bca(proc)
    assert field_review.active(_nth_conv(NTH_CAPS), proc)
    assert not field_review.active(_nth_conv({**NTH_CAPS, "supportsBcaNthReview": False}), proc)
    # Lệnh điền mang bộ quy tắc ô → extension tô 3 màu và đếm trên host bocongan.
    assert field_review.fill_action_extra(_nth_conv(NTH_CAPS), proc) is not None

    # Đính xong cùng trang mà form còn 2 ô bắt buộc trống → KHÔNG có "Đồng ý và tiếp tục", có Bổ sung + Điền lại tờ khai.
    conv = _nth_conv(NTH_CAPS)
    r = _attach_done(conv, review={"filled": 20, "optional": 3, "required": 2})
    sends = [c["send"] for c in r.chips]
    assert lai_chau.NEXT_SEND not in sends and not [c for c in r.chips if c.get("cta")]
    assert sends[0] == "__action:field_review_start" and "__action:refill" in sends
    assert any(c["label"] == vi.BCA_NTH_REFILL_CHIP for c in r.chips)
    trail = " ".join(a.get("md", "") for a in r.actions if a.get("type") == "trail_message")
    assert "**2 ô bắt buộc**" in trail
    # Công dân tự gõ đủ trên trang → hiện "Đồng ý và tiếp tục" (cta) kèm câu đủ ô.
    r = asyncio.run(flow._handle_turn_inner(conv, Intent("event", "field_review_status",
                                                         {"stats": {"filled": 22, "optional": 3, "required": 0}})))
    assert [c for c in r.chips if c.get("cta")] == [lai_chau.next_chip()]
    assert "Đồng ý và tiếp tục" in r.display_md

    # Đủ ô ngay khi đính xong → nút cam "Đồng ý và tiếp tục" như cũ.
    r = _attach_done(_nth_conv(NTH_CAPS), review={"filled": 22, "optional": 0, "required": 0})
    assert [c for c in r.chips if c.get("cta")] == [lai_chau.next_chip()]
    assert "__action:refill" in [c["send"] for c in r.chips]
    # Extension cũ (chưa có bộ đọc ô trên host bocongan) → giữ luồng cũ: nút hiện ngay, không có Bổ sung.
    old = _attach_done(_nth_conv({**NTH_CAPS, "supportsBcaNthReview": False}))
    assert [c for c in old.chips if c.get("cta")] == [lai_chau.next_chip()]
    assert "__action:field_review_start" not in [c["send"] for c in old.chips]
    # Lệnh đính kèm cùng trang xin extension đếm lại ô sau khi đính.
    action = flow._attach_plan_action(_nth_conv(NTH_CAPS), [{"fileIndex": 0, "target": "fixed-slot"}])
    assert isinstance(action.get("fieldReview"), dict)
    # Bấm "Bổ sung…" → hỏi từng ô (extension tìm ô trống đầu tiên).
    conv = _nth_conv(NTH_CAPS, state="done")
    _attach_done(conv, review={"filled": 20, "optional": 3, "required": 2})
    conv["state"] = "done"
    r = asyncio.run(flow._handle_turn_inner(conv, Intent("action", "field_review_start", {})))
    assert r.actions[0]["type"] == "field_review_next" and r.actions[0]["requiredFirst"] is True


def test_tro_ly_bca_nth_dien_lai_to_khai_sau_khi_da_dinh_kem(monkeypatch):
    from app.channels.handfree.chat import pipeline_runner
    from app.channels.handfree.chat import script_vi as vi

    calls = []
    monkeypatch.setattr(pipeline_runner, "run_process", lambda *a: calls.append("process"))
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a: calls.append("attach"))
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)

    async def save(_conv):
        return None

    monkeypatch.setattr(flow.conv_store, "save", save)

    # Điền xong (form + bảng cùng trang): user 19/11 — KHÔNG tự đính; dừng ở rà soát, hỏi đính kèm (nút "Đính kèm giấy
    # tờ"), có "Điền lại tờ khai" và mời bổ sung ô trống ngay.
    conv = _nth_conv(NTH_CAPS, state="filling", auto_attach_after_fill=True)
    r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {
        "filled": 20, "notFound": [], "review": {"filled": 20, "optional": 3, "required": 2}})))
    assert calls == [] and conv["state"] == "reviewing"
    sends = [c["send"] for c in r.chips]
    assert "__action:confirm_review" in sends and "__action:refill" in sends
    assert any(c["label"] == vi.BCA_NTH_REFILL_CHIP for c in r.chips)
    assert "điền lại tờ khai" in r.display_md
    # Nói "điền lại tờ khai" lúc này (state reviewing) → chạy lại lượt điền, không đính.
    asyncio.run(flow._handle_turn_inner(conv, Intent("action", "refill", {})))
    assert calls == ["process"] and conv["state"] == "filling"
    calls.clear()
    asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {
        "filled": 22, "notFound": [], "review": {"filled": 22, "optional": 1, "required": 0}})))
    assert calls == [] and conv["state"] == "reviewing"
    # Bấm "Đính kèm giấy tờ" → đính ngay trên trang này.
    asyncio.run(flow._handle_turn_inner(conv, Intent("action", "confirm_review", {})))
    assert calls == ["attach"] and conv["state"] == "attaching"

    # Đã đính xong (state done, docs_target đã sang attachment): "Điền lại tờ khai" chạy lại lượt điền, KHÔNG đính lại.
    conv = _nth_conv(NTH_CAPS, state="done", docs_target="attachment", attach_done=True, auto_attach_after_fill=True)
    calls.clear()
    asyncio.run(flow._handle_turn_inner(conv, Intent("action", "refill", {})))
    assert calls == ["process"] and conv["state"] == "filling" and conv["docs_target"] == "declaration"
    assert conv["auto_attach_after_fill"] is False
    calls.clear()
    r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {
        "filled": 22, "notFound": [], "review": {"filled": 22, "optional": 1, "required": 0}})))
    assert calls == [] and conv["state"] == "done"
    assert [c for c in r.chips if c.get("cta")][0]["send"] == "__action:lc_next"


# ── Ảnh chân dung 4x6: ô tải ảnh đầu trang kê khai (filename46, .jpg dưới 2 MB), user 19/11/2026 ──
import io  # noqa: E402

from PIL import Image  # noqa: E402

from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.attach.dinh_kem_khong_tach.planner import (  # noqa: E402
    PORTRAIT,
    build_items,
)


def _image_file(name: str, size=(400, 600), fmt="PNG", mode="RGB", color=(255, 255, 255)) -> dict:
    image = Image.new(mode, size, color)
    if mode == "RGB":
        image.paste((120, 90, 70), (size[0] // 4, size[1] // 4, size[0] * 3 // 4, size[1]))  # "người" giữa nền sáng
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    mime = "image/jpeg" if fmt == "JPEG" else f"image/{fmt.lower()}"
    return {"name": name, "type": mime, "dataUrl": f"data:{mime};base64," + base64.b64encode(buffer.getvalue()).decode()}


def _decoded(field: dict) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(field["value"]["dataUrl"].split(",", 1)[1])))


def test_anh_chan_dung_png_doi_sang_jpg_va_phat_o_filename46():
    files = [{"name": "to-khai.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,eA=="},
             _image_file("IMG_0001.png"), _image_file("cccd.jpg", size=(600, 380), fmt="JPEG")]
    texts = {0: TO_KHAI, 1: "", 2: "CĂN CƯỚC CÔNG DÂN Số định danh 034085000001 Họ và tên TRẦN VĂN AN"}
    assert mapper.find_portrait(files, texts) == 1  # ảnh dọc, nền sáng, không chữ; CCCD có chữ + nằm ngang
    field, notes = mapper.portrait_field(files, texts)
    assert field["name"] == "filename46" and field["comp"] == "bca-photo"
    assert field["value"]["name"].endswith(".jpg") and field["value"]["type"] == "image/jpeg"
    assert field["value"]["dataUrl"].startswith("data:image/jpeg;base64,") and _decoded(field).format == "JPEG"
    assert "IMG_0001.png" in notes[0] and "đã tự đổi sang định dạng .jpg" in notes[0]
    # Ảnh .jpg sẵn thì không báo đổi định dạng.
    _, notes = mapper.portrait_field([_image_file("chan-dung.jpg", fmt="JPEG")], {})
    assert "đổi sang" not in notes[0]


def test_anh_chan_dung_theo_ten_trong_suot_va_anh_lon():
    # Tên tệp "ảnh thẻ 4x6" nhận cả khi ảnh không dọc; nền trong suốt (PNG RGBA) thành nền trắng.
    files = [_image_file("Ảnh thẻ 4x6.png", size=(500, 500), mode="RGBA", color=(0, 0, 0, 0))]
    field, _ = mapper.portrait_field(files, {})
    image = _decoded(field)
    assert image.mode == "RGB" and image.getpixel((5, 5)) == (255, 255, 255)
    # Ảnh lớn → cạnh dài ≤ 1200 px, dưới 2 MB.
    noisy = Image.effect_noise((2400, 3600), 120).convert("RGB")
    buffer = io.BytesIO()
    noisy.save(buffer, format="PNG")
    big = {"name": "chan_dung.png", "type": "image/png",
           "dataUrl": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()}
    field, _ = mapper.portrait_field([big], {})
    assert max(_decoded(field).size) <= 1200
    assert len(base64.b64decode(field["value"]["dataUrl"].split(",", 1)[1])) <= mapper.PORTRAIT_MAX_BYTES


def test_khong_co_anh_chan_dung_thi_nhac_tai_anh_jpg():
    landscape = _image_file("IMG_0002.jpg", size=(800, 500), fmt="JPEG")  # ảnh ngang, không tên chân dung
    dark = _image_file("IMG_0003.jpg", fmt="JPEG", color=(20, 20, 20))  # ảnh dọc nhưng nền tối
    assert mapper.find_portrait([landscape, dark], {}) is None
    field, notes = mapper.portrait_field([landscape, dark], {})
    assert field is None and notes == [mapper.PORTRAIT_WARNING]
    assert ".jpg" in mapper.PORTRAIT_WARNING and "tự đổi sang .jpg" in mapper.PORTRAIT_WARNING


def test_runner_phat_anh_chan_dung_dau_danh_sach(monkeypatch):
    from app.pipelines.cap_ho_chieu_pho_thong_o_trong_nuoc.process import runner as hc_runner

    files = [{"name": "to-khai.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,eA=="},
             _image_file("anh.png")]

    async def fake_ocr(ocr_files):
        return [{"name": f["name"], "text": TO_KHAI if f["name"] == "to-khai.pdf" else ""} for f in ocr_files]

    async def fake_run(files_by_role, **kwargs):
        await kwargs["ocr_fn"](hc_runner.runner.flatten(files_by_role))
        return {"fields": [{"name": k, "value": v} for k, v in HO_SO.items()], "errors": [], "extracted": {}}

    monkeypatch.setattr(ocr_service, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(hc_runner.runner, "run", fake_run)
    res = asyncio.run(hc_runner.run({"": files}, {}))
    assert res["fields"][0]["name"] == "filename46" and res["fields"][0]["comp"] == "bca-photo"
    assert mapper.PORTRAIT_WARNING not in res["errors"]
    assert any("Đã gắn ảnh 'anh.png'" in e for e in res["errors"])
    # Giấy của người khác chủ tài khoản → chặn, không gắn ảnh.
    res = asyncio.run(hc_runner.run({"": files}, {"formContext": {"applicantFullname": "LÊ THỊ MAI"}}))
    assert res["fields"] == [] and res["blocked"]


def test_dinh_kem_bo_qua_anh_chan_dung(monkeypatch):
    names = ["hc.pdf", "chan-dung.png", "tk.pdf"]
    entries = [{"fileIndex": 0, "pages": None, "docType": "ho_chieu", "documentName": "", "text": HO_CHIEU},
               {"fileIndex": 1, "pages": None, "docType": PORTRAIT, "documentName": "", "text": ""},
               {"fileIndex": 2, "pages": None, "docType": "to_khai", "documentName": "", "text": TO_KHAI}]
    attachments, warnings = build_items(names, entries)
    assert attachments[0]["sourceFileIndexes"] == [0, 2]
    assert any("Ảnh chân dung 'chan-dung.png' không đính" in w for w in warnings)
    # Qua planner thật: ảnh chân dung (OCR rỗng) không bị gộp vào dòng 2 như giấy "không xác định".
    photo = _image_file("chan-dung.png")
    files = [_file("hc.pdf"), FileItem(name=photo["name"], type=photo["type"], dataUrl=photo["dataUrl"], role="other"),
             _file("tk.pdf")]
    _mock_io(monkeypatch, {"hc.pdf": HO_CHIEU, "tk.pdf": TO_KHAI}, "không phải JSON")
    result = asyncio.run(attach_planner.plan(files, {"splitDocuments": False}, {}))
    assert _slots(result)[1]["sourceFileIndexes"] == [0, 2]
    assert not any("Không xác định được loại giấy tờ" in e for e in result["errors"])
    # Bước đính kèm trả luôn ô ảnh chân dung để Auto Fill gắn khi chỉ bấm "Đính kèm".
    assert [f["name"] for f in result["pageFields"]] == ["filename46"]
    assert result["pageFields"][0]["comp"] == "bca-photo"


def _pdf_of_image(photo: dict, *, name: str | None = None, pages: int = 1, text: str = "") -> dict:
    """Như lib/imageToPdf.js của Auto Fill: trang đúng cỡ ảnh, ảnh vẽ kín trang."""
    import fitz

    data = base64.b64decode(photo["dataUrl"].split(",", 1)[1])
    width, height = Image.open(io.BytesIO(data)).size
    doc = fitz.open()
    for _ in range(pages):
        page = doc.new_page(width=width, height=height)
        page.insert_image(page.rect, stream=data)
        if text:
            page.insert_text((10, 20), text)
    out = doc.tobytes()
    doc.close()
    return {"name": name or photo["name"].rsplit(".", 1)[0] + ".pdf", "type": "application/pdf",
            "dataUrl": "data:application/pdf;base64," + base64.b64encode(out).decode()}


def test_anh_chan_dung_auto_fill_doi_sang_pdf_van_nhan_ra():
    """User 19/11/2026: Auto Fill đổi ảnh sang PDF trước bước đính kèm (toPdfForAttach) → ảnh chân dung tới BE là PDF một
    trang chỉ có ảnh; vẫn phải nhận ra và gắn được vào ô filename46."""
    portrait = _pdf_of_image(_image_file("500135564_n.jpg", fmt="JPEG"))
    tk = {"name": "to-khai.pdf", "type": "application/pdf", "dataUrl": "data:application/pdf;base64,eA=="}
    assert mapper.find_portrait([tk, portrait], {0: TO_KHAI, 1: "Ảnh 4x6"}) == 1
    field, notes = mapper.portrait_field([tk, portrait], {0: TO_KHAI, 1: ""})
    assert field["name"] == "filename46" and _decoded(field).format == "JPEG"
    assert "đổi sang" not in notes[0]
    # Ảnh ngang (CCCD chụp) gói PDF, PDF hai trang, PDF có lớp chữ → không phải ảnh chân dung.
    landscape = _pdf_of_image(_image_file("cccd.jpg", size=(600, 380), fmt="JPEG"))
    two_pages = _pdf_of_image(_image_file("anh.jpg", fmt="JPEG"), pages=2)
    with_text = _pdf_of_image(_image_file("anh.jpg", fmt="JPEG"), text="TO KHAI")
    for other in (landscape, two_pages, with_text):
        assert mapper.find_portrait([other], {}) is None, other["name"]


def test_dinh_kem_auto_fill_tra_o_anh_chan_dung_du_khong_co_ho_chieu(monkeypatch):
    """Ca req thử 19/11: tờ khai + ảnh chân dung (đã thành PDF), chưa có hộ chiếu cũ → không đính gì vào bảng nhưng vẫn
    trả ô ảnh chân dung; ảnh không bị coi là giấy "không có dòng phù hợp"."""
    photo = _pdf_of_image(_image_file("500135564_n.jpg", fmt="JPEG"))
    files = [_file("tk.pdf"), FileItem(name=photo["name"], type=photo["type"], dataUrl=photo["dataUrl"], role="doc")]
    _mock_io(monkeypatch, {"tk.pdf": TO_KHAI, photo["name"]: "Ảnh 4x6"}, "không phải JSON")
    for split in (False, True):
        result = asyncio.run(attach_planner.plan(files, {"splitDocuments": split}, {}))
        assert result["attachments"] == []
        assert [f["name"] for f in result["pageFields"]] == ["filename46"], split
        assert not any(photo["name"] in e and "không có dòng phù hợp" in e for e in result["errors"]), split
    # Không có ảnh chân dung → không có ô nào.
    _mock_io(monkeypatch, {"tk.pdf": TO_KHAI}, "không phải JSON")
    assert asyncio.run(attach_planner.plan([_file("tk.pdf")], {}, {}))["pageFields"] == []


def test_tro_ly_tai_len_nhan_ra_anh_chan_dung(monkeypatch, tmp_path):
    """Chạy thật 19/11: trợ lý báo ảnh chân dung .jpg (tên số dài, OCR chỉ ra "VÀNG") là "Tệp chưa nhận ra loại", ô Ảnh
    chân dung 0/1. Bộ phân loại lúc tải lên phải xếp ảnh vào ô anh_chan_dung cho cả ba thủ tục eForm Bộ Công an."""
    from app.channels.handfree import procedure_registry as hf
    from app.upload_session import classify, llm_classifier

    photo = _image_file("1795082514202_191706323110575141.jpg", fmt="JPEG")
    path = tmp_path / "f1.jpg"
    path.write_bytes(base64.b64decode(photo["dataUrl"].split(",", 1)[1]))
    cccd = _image_file("cccd.jpg", size=(600, 380), fmt="JPEG")
    cccd_path = tmp_path / "f2.jpg"
    cccd_path.write_bytes(base64.b64decode(cccd["dataUrl"].split(",", 1)[1]))
    payloads = [{"name": "to-khai.pdf", "type": "application/pdf", "path": str(tmp_path / "missing.pdf")},
                {"name": photo["name"], "type": "image/jpeg", "path": str(path)},
                {"name": "cccd.jpg", "type": "image/jpeg", "path": str(cccd_path)}]
    texts = [TO_KHAI, "VÀNG", ""]

    async def fake_ocr(files, **_):
        return [{"name": f["name"], "text": texts[i]} for i, f in enumerate(files)]

    asked = []

    async def fake_llm(file, _result, _spec, _context=None):
        asked.append(file["name"])
        return "to_khai" if file["name"] == "to-khai.pdf" else "unknown"

    monkeypatch.setattr(classify.ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(llm_classifier, "_classify_one", fake_llm)
    for key in (KEY, "cap-thi-thuc-cho-nguoi-nuoc-ngoai-tai-viet-nam", "cap-the-tam-tru-cho-nguoi-nuoc-ngoai-tai-viet-nam"):
        docs = hf.get_procedure(key)["requiredDocs"]
        asked.clear()
        out = asyncio.run(classify.classify_files(payloads, docs, [], None, procedure_key=key))
        assert out[1]["doc_key"] == "anh_chan_dung", key
        assert out[2]["doc_key"] != "anh_chan_dung", key  # ảnh ngang (CCCD) không phải ảnh chân dung
        assert photo["name"] not in asked  # không tốn lượt LLM cho ảnh chân dung
    # Đã có ảnh chân dung trong phiên → ảnh thứ hai không chiếm lại ô; chụp theo dòng khác (hint) thì tin hint.
    docs = hf.get_procedure(KEY)["requiredDocs"]
    out = asyncio.run(classify.classify_files(payloads[1:2], docs, [{"doc_key": "anh_chan_dung"}], None,
                                              procedure_key=KEY))
    assert out[0]["doc_key"] != "anh_chan_dung"
    out = asyncio.run(classify.classify_files(payloads[1:2], docs, [], "ho_chieu", procedure_key=KEY))
    assert out[0]["doc_key"] == "ho_chieu"


def test_tro_ly_noi_dinh_kem_lai_thi_dinh_lai_luon_khong_hoi_khong_dien_lai(monkeypatch):
    """User 19/11/2026: ở bước cuối nói "đính kèm lại" → chạy lại bước đính kèm với tệp đang có, không hỏi "Điều chỉnh
    giấy tờ?", không điền lại tờ khai."""
    from app.channels.handfree.chat import intents, pipeline_runner

    for said in ("đính kèm lại", "Đính kèm lại giúp tôi", "dinh kem lai di", "tải lại file", "đính lại ảnh nhé"):
        assert asyncio.run(intents.resolve(said, "done", {})) == Intent("action", "reattach"), said
    for said in ("điền lại tờ khai", "không đính kèm lại", "thêm giấy tờ"):
        assert not intents.asks_reattach(said), said

    calls = []
    monkeypatch.setattr(pipeline_runner, "run_process", lambda *a: calls.append("process"))
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a: calls.append("attach"))
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)

    async def noop(*_a, **_k):
        return None

    async def reopen(sid):
        return {"_id": sid, "files": [{"name": "ho-so.pdf"}]}

    monkeypatch.setattr(flow.conv_store, "save", noop)
    monkeypatch.setattr(flow.up_store, "reopen_for_supplement", reopen)
    monkeypatch.setattr(flow.upload_service, "sync_for_conversation", noop)
    monkeypatch.setattr(flow.upload_service, "complete_session", noop)

    async def progress(_sid):
        return {"received": 1, "total": 1, "files_count": 1}

    monkeypatch.setattr(flow.upload_service, "progress_of", progress)
    conv = _nth_conv(NTH_CAPS, state="done", docs_target="attachment", attach_done=True,
                     attach_plan=[{"fileIndex": 0, "target": "fixed-slot", "slotIndex": 1}], fields=[{"name": "x"}])
    r = asyncio.run(flow._handle_turn_inner(conv, Intent("action", "reattach", {})))
    assert calls == ["attach"]
    assert conv["docs_target"] == "attachment" and conv["fields"] == [{"name": "x"}]  # tờ khai giữ nguyên
    assert not any(c.get("send") == "__action:docs_done" for c in r.chips or [])  # không hỏi chốt giấy tờ
    # Đã nộp hồ sơ → không đính lại nữa.
    conv = _nth_conv(NTH_CAPS, state="done", attach_done=True, submitted_completed=True)
    calls.clear()
    asyncio.run(flow._handle_turn_inner(conv, Intent("action", "reattach", {})))
    assert calls == []


def test_tro_ly_dieu_chinh_giay_to_sau_dinh_kem_la_dien_lai_khong_dinh_lai(monkeypatch):
    """User 20/11/2026: "Điều chỉnh giấy tờ" ở bước cuối eForm Nth → chốt xong ĐIỀN LẠI tờ khai, không đính lại; nút
    "Đính kèm lại" riêng."""
    from app.channels.handfree.chat import pipeline_runner, tracing

    calls = []
    monkeypatch.setattr(pipeline_runner, "run_process", lambda *a: calls.append("process"))
    monkeypatch.setattr(pipeline_runner, "run_attach", lambda *a: calls.append("attach"))
    monkeypatch.setattr(pipeline_runner, "spawn", lambda _job: None)

    async def noop(*_a, **_k):
        return None

    async def reopen(sid):
        return {"_id": sid, "files": [{"name": "ho-so.pdf"}]}

    async def progress(_sid):
        return {"received": 1, "total": 1, "files_count": 1}

    monkeypatch.setattr(tracing, "set_report", noop)
    monkeypatch.setattr(flow.conv_store, "save", noop)
    monkeypatch.setattr(flow.up_store, "reopen_for_supplement", reopen)
    monkeypatch.setattr(flow.upload_service, "sync_for_conversation", noop)
    monkeypatch.setattr(flow.upload_service, "progress_of", progress)
    conv = _nth_conv({**NTH_CAPS, "supportsPageBoundDocsComplete": True}, state="done", docs_target="attachment",
                     attach_done=True, fields=[{"name": "x"}])
    r = asyncio.run(flow._handle_turn_inner(conv, Intent("action", "add_documents", {})))
    assert [c["label"] for c in r.chips] == ["✅ Hoàn tất điều chỉnh, điền lại tờ khai"]
    asyncio.run(flow._docs_complete(conv, SAME_PAGE))
    assert calls == ["process"] and conv["auto_attach_after_fill"] is False
    r = asyncio.run(flow._handle_turn_inner(conv, Intent("action", "fill_report", {
        "filled": 30, "review": {"filled": 30, "optional": 0, "required": 0}})))
    sends = [c["send"] for c in r.chips]
    assert calls == ["process"] and conv["state"] == "done"
    assert "__action:reattach" in sends and "__action:refill" in sends
