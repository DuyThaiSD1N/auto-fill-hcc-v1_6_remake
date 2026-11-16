"""Cấp đổi thẻ căn cước 2.001195 (Cổng DVC Bộ Công an): mapper ô form + nối registry / link kê khai."""
from app.pipelines.cap_doi_the_can_cuoc.process import mapper
from app.pipelines.cap_doi_the_can_cuoc.process.prompt import EXTRA_RULES
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "cap-doi-the-can-cuoc"
SELF = {
    "CoQuan_Tinh": "tỉnh Lai Châu", "CoQuan_Xa": "phường Đoàn Kết",
    "LyDoCap": "Đổi thẻ căn cước khi công dân đủ 25 tuổi",
    "NoiDungDeNghi": "Cấp đổi thẻ căn cước do đủ 25 tuổi.",
    "NguoiCanCap_HoTen": "Nguyen Van An", "NguoiCanCap_NgaySinh": "1/2/2001", "NguoiCanCap_GioiTinh": "Nam",
    "NguoiCanCap_SoDinhDanh": "0122 0100 0001", "NguoiCanCap_SoDienThoai": "0912 000 111",
    "NguoiCanCap_Email": "An.Mau@Example.com",
    "NguoiDaiDien_HoTen": "……", "NguoiDaiDien_SoDienThoai": "………",
    "NhanKetQua_HinhThuc": "Qua dịch vụ bưu chính",
    "NhanKetQua_Tinh": "Lai Châu", "NhanKetQua_Xa": "Phường Đoàn Kết",
    "NhanKetQua_DiaChiChiTiet": "Số 3, tổ dân phố số 5, phường Đoàn Kết, tỉnh Lai Châu",
    "NhanKetQua_SoDienThoai": "0912000111",
}


def _enrich(values: dict, options=None) -> list[dict]:
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)


def _by(out: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in out}


def test_tu_ke_khai_thu_tu_va_gia_tri():
    out = _enrich(SELF)
    names = [f["name"] for f in out]
    by = _by(out)
    # Không đụng khối người cần cấp (cổng ẩn khi tự kê khai) và Phần I khoá theo tài khoản.
    assert not {"txtFULLNAME_NCC", "txtIDENTIFY_NUMBER_NCC", "cboRELATIONSHIP_WITH_NDN", "txtFULLNAME_NDN"} & set(by)
    assert by["radIsNCC"] == "Người kê khai là người cần cấp đổi căn cước"
    assert by["txtPHONE_NUMBER_NDN"] == "0912000111" and by["txtEMAIL_ADDRESS_NDN"] == "an.mau@example.com"
    assert by["cboLyDoCap"] == "Đổi thẻ căn cước khi công dân đủ 25 tuổi"
    # Lý do trước nhóm nhận kết quả; radio cấp thực hiện trước ô cơ quan.
    assert names.index("cboLyDoCap") < names.index("radCapThucHien") < names.index("cboORG") < names.index("radNhanKetQua")
    agency = next(f for f in out if f["name"] == "cboORG")
    assert agency["comp"] == "bca-agency" and agency["onlyIfEmpty"] is True and "default" not in agency
    assert agency["value"] == {"province": "Tỉnh Lai Châu", "ward": "Phường Đoàn Kết", "cityId": "cboORGTinh",
                               "wardId": "cboORGXa", "readySelect": "cboDiaChiTram", "readyPick": True}
    assert by["radCapThucHien"] == "Cấp Xã"
    assert by["radNhanKetQua"] == "Nhận kết quả qua dịch vụ bưu chính"
    assert by["cboGET_RESULT_CITY_ADDR"] == "Tỉnh Lai Châu" and by["cboGET_RESULT_VILLAGE_ADDR"] == "Phường Đoàn Kết"
    assert by["txtGET_RESULT_DETAIL_ADDR"] == "Số 3, tổ dân phố số 5"
    # Mục IV không ghi người nhận riêng → người cần cấp đổi nhận.
    assert by["txtFULLNAME_NN"] == "NGUYEN VAN AN" and by["txtPHONE_NUMBER_NN"] == "0912000111"


def test_cha_me_ke_khai_thay_khai_nguoi_can_cap_o_phan_ii():
    values = {**SELF, "NguoiDaiDien_HoTen": "Tran Thi Binh", "NguoiDaiDien_SoDinhDanh": "012170000002",
              "NguoiDaiDien_SoDienThoai": "0987 000 222", "NguoiDaiDien_QuanHe": "Mẹ",
              "NguoiCanCap_GioiTinh": ""}
    out = _enrich(values)
    names = [f["name"] for f in out]
    by = _by(out)
    assert by["radIsNCC"] == "Người kê khai là cha/mẹ/người đại diện hợp pháp của người cần cấp đổi căn cước"
    assert names.index("radIsNCC") < names.index("txtFULLNAME_NCC")
    assert by["txtFULLNAME_NCC"] == "NGUYEN VAN AN" and by["txtBIRTHDATE_NCC"] == "01/02/2001"
    assert by["txtIDENTIFY_NUMBER_NCC"] == "012201000001"
    # Không đọc được giới tính → chữ số thứ 4 của số định danh (2 = chẵn = nam).
    assert by["cboGENDER_ID_NCC"] == "Nam"
    assert by["cboRELATIONSHIP_WITH_NDN"] == "Mẹ"
    # SĐT Phần I là của người kê khai (mục II.5), không lấy SĐT người cần cấp.
    assert by["txtPHONE_NUMBER_NDN"] == "0987000222"
    assert "txtEMAIL_ADDRESS_NDN" not in by


def test_muc_ii_ghi_chinh_nguoi_can_cap_van_la_tu_ke_khai():
    by = _by(_enrich({**SELF, "NguoiDaiDien_HoTen": "Nguyễn Văn An", "NguoiDaiDien_SoDinhDanh": "012201000001"}))
    assert by["radIsNCC"] == "Người kê khai là người cần cấp đổi căn cước"


def test_nop_cong_an_tinh_chi_chon_tinh_va_nhan_tinh_theo_cong():
    by = _by(_enrich({**SELF, "CoQuan_Tinh": "Đồng Nai", "CoQuan_Xa": ""}))
    assert by["radCapThucHien"] == "Cấp Tỉnh"
    # Cổng ghi "Thành phố Đồng Nai" (lệch nhãn chuẩn "Tỉnh Đồng Nai").
    assert by["cboORG"]["province"] == "Thành phố Đồng Nai" and by["cboORG"]["ward"] == ""


def test_ly_do_doan_theo_cum_khi_llm_lech_chu():
    assert _by(_enrich({**SELF, "LyDoCap": "đủ 40 tuổi"}))["cboLyDoCap"] == "Đổi thẻ căn cước khi công dân đủ 40 tuổi"
    by = _by(_enrich({**SELF, "LyDoCap": "", "NoiDungDeNghi": "Đổi thẻ do thay đổi tên đơn vị hành chính"}))
    assert by["cboLyDoCap"].endswith("do sắp xếp đơn vị hành chính")
    by = _by(_enrich({**SELF, "LyDoCap": "", "NoiDungDeNghi": "Thẻ bị hư hỏng, gãy chíp"}))
    assert by["cboLyDoCap"] == "Đổi thẻ căn cước do bị hư hỏng, không sử dụng được"
    assert "cboLyDoCap" not in _by(_enrich({**SELF, "LyDoCap": "", "NoiDungDeNghi": ""}))


def test_nhan_ket_qua_truc_tiep_chi_chon_radio():
    by = _by(_enrich({**SELF, "NhanKetQua_HinhThuc": "Trực tiếp tại cơ quan công an"}))
    assert by["radNhanKetQua"] == "Nhận kết quả tại cơ quan công an nơi tiếp nhận hồ sơ"
    assert not {"cboGET_RESULT_CITY_ADDR", "txtGET_RESULT_DETAIL_ADDR", "txtFULLNAME_NN"} & set(by)


def test_giay_khong_ghi_co_quan_thi_lay_xa_tai_khoan_to_vang():
    values = {k: v for k, v in SELF.items() if not k.startswith("CoQuan_")}
    options = mapper.with_account_process_options({}, {"tinh": "Lai Châu", "xa": "Phường Mẫu"}, KEY)
    out = _enrich(values, options)
    agency = next(f for f in out if f["name"] == "cboORG")
    level = next(f for f in out if f["name"] == "radCapThucHien")
    assert agency["value"]["ward"] == "Phường Mẫu" and agency["default"] is True and level["default"] is True
    # Thủ tục khác không mang xã tài khoản sang.
    assert "_accountAgency" not in mapper.with_account_process_options({}, {"tinh": "A", "xa": "B"}, "khac")


def test_email_llm_chep_lech_thi_lay_ban_ocr_gan_nhat():
    docs = [{"text": "19. Địa chỉ thư điện tử: nguyenvanan.mau@example.com\nEmail: ……"},
            {"text": "Liên hệ: hotro.khac@example.vn"}]
    raw = [{"name": "NguoiCanCap_Email", "value": "nguyenvnan.mau@example.com"},
           {"name": "NguoiDaiDien_Email", "value": ""}, {"name": "LyDoCap", "value": "x"}]
    out = mapper.email_ocr_fallback(raw, docs)
    assert out["NguoiCanCap_Email"] == "nguyenvanan.mau@example.com"
    # Không bịa email cho ô LLM để trống; email khác hẳn (không gần bản nào trong OCR) giữ nguyên.
    assert out["NguoiDaiDien_Email"] == "" and out["LyDoCap"] == "x"
    assert mapper.email_ocr_fallback({"NguoiCanCap_Email": "zz@q.io"}, docs)["NguoiCanCap_Email"] == "zz@q.io"


def test_prompt_liet_ke_du_nhan_ly_do_va_khong_lay_cha_me_muc_20():
    assert "Đổi thẻ căn cước khi công dân đủ 14 tuổi" in EXTRA_RULES
    assert "Cấp thẻ căn cước chuyển từ CCCD gắn chíp" in EXTRA_RULES
    assert "KHÔNG lấy cha, mẹ ở" in EXTRA_RULES


def test_registry_va_link_ke_khai():
    assert registry.get_pipeline(KEY) is not None
    assert registry.get_attach_pipeline(KEY) is None
    proc = registry.get_procedure(KEY)
    assert proc["hasAttachmentStep"] is False
    # Trang dùng chung với cấp lại: urlScope chặn đúng trang, urlIncludes chốt TT=CAP_DOI.
    assert proc["detect"]["urlScope"] == ["dvc-CCCD-cap-doi-hoac-cap-lai.html"]
    assert proc["detect"]["urlIncludes"] == ["TT=CAP_DOI"]
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "2.001195" and link["url"].endswith("dvc-CCCD-cap-doi-hoac-cap-lai.html?TT=CAP_DOI")
    assert link["needsAgencySelect"] is False


# ── Trợ lý người dân (handfree) ──
from app.channels.handfree.chat import flow  # noqa: E402
from app.channels.handfree.chat.intents import Intent  # noqa: E402

CAPS = {"supportsBcaCanCuoc": True}


def test_tro_ly_entry_cung_key_url_detect_va_hien_moi_tinh():
    from app.channels.handfree import procedure_registry as hf

    proc = hf.get_procedure(KEY)
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert proc["keKhaiUrl"] == link["url"] and proc["detect"] == registry.get_procedure(KEY)["detect"]
    assert proc["bcaPortal"] is True and proc["hasAttachmentStep"] is False
    assert proc["requiresCapability"] == "supportsBcaCanCuoc" and "provinceOnly" not in proc
    assert hf.get_pipeline(KEY) is registry.get_pipeline(KEY)
    # Toàn quốc: tài khoản tỉnh theo dõi nào cũng thấy (vd Khánh Hòa — Nha Trang).
    for slug in ("khanhhoa", "laichau", "bacninh", ""):
        assert KEY in {p["key"] for p in hf.public_list_for(slug)}, slug


def test_tro_ly_ban_cu_thi_bao_cap_nhat_ban_moi_khong_hoi_noi_sang_thang_giay_to():
    conv = {"state": "greet", "procedure_key": None, "location": {}}
    r = flow._to_confirm_procedure(conv, KEY)
    assert "chưa hỗ trợ" in r.display_md and not r.actions
    conv = {"state": "greet", "procedure_key": None, "client_capabilities": dict(CAPS),
            "location": {"province": "Tỉnh Khánh Hòa", "province_slug": "khanhhoa", "ward": "Phường Nha Trang"}}
    r = flow._to_confirm_procedure(conv, KEY)
    assert conv["state"] == "guide_login" and r.actions[0]["type"] == "navigate"
    # Trang chưa hiện khối cơ quan (đang tải / còn đăng nhập) → im lặng chờ.
    assert not flow._handle_guide_login(conv, Intent("event", "page_status", {})).display_md
    # Thấy trang kê khai → KHÔNG hỏi nơi cư trú, không nút "Điền cơ quan thực hiện": sang thẳng bước giấy tờ (cơ quan
    # điền theo "Kính gửi" DC02 lúc điền form).
    r = flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True}))
    assert conv["state"] in ("ask_doc_method", "consent") and conv["agency_done"] is True
    assert "__action:bca_fill_agency" not in [c.get("send") for c in r.chips]
    assert "nơi cư trú" not in (r.display_md or "") and not conv.get("bca_agency_pending")


def test_tro_ly_giay_khong_ghi_co_quan_lay_xa_tai_khoan():
    from app.channels.handfree.chat import pipeline_runner

    assert pipeline_runner.with_cap_doi_the_can_cuoc_account_process_options(
        {}, {"tinh": "Khánh Hòa", "xa": "Phường Nam Nha Trang"}, KEY)["_accountAgency"]["xa"] == "Phường Nam Nha Trang"


def test_tro_ly_dien_xong_khong_moi_dinh_kem_ma_nhac_cam_doan_roi_luu_tiep_tuc():
    import asyncio
    from unittest import mock

    from app.channels.handfree.chat import tracing

    conv = {"_id": "c1", "state": "filling", "procedure_key": KEY, "docs_target": "declaration",
            "auto_attach_after_fill": True, "upload_session_id": "s1", "location": {},
            "client_capabilities": dict(CAPS)}
    with mock.patch.object(tracing, "set_report", mock.AsyncMock()):
        r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {"filled": 9})))
    sends = [c["send"] for c in r.chips]
    assert "__action:confirm_review" not in sends and "__action:tick_commit" not in sends
    assert "Lưu và Tiếp tục" in r.display_md and "Tôi xin cam đoan" in r.display_md
    assert "Đính kèm" not in r.display_md


def test_tro_ly_ten_mong_va_cau_chon_thu_tuc():
    from app.channels.handfree.chat import script_mong
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS

    assert script_mong.PROCEDURE_HMONG[KEY] and script_mong.BCA_CCCD_SUBMIT_HINT["tts"]
    assert "đổi thẻ căn cước" in PROCEDURE_HINTS[KEY]
