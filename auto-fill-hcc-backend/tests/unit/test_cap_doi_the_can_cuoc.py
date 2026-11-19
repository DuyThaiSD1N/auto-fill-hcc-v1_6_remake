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


def _field(out: list[dict], name: str) -> dict:
    return next(f for f in out if f["name"] == name)


def test_tu_ke_khai_thu_tu_va_gia_tri():
    out = _enrich(SELF)
    names = [f["name"] for f in out]
    by = _by(out)
    # Phần I khoá theo tài khoản → không ghi họ tên / số định danh người kê khai.
    assert not {"txtFULLNAME_NDN", "txtIDENTIFY_NUMBER_NDN"} & set(by)
    # Radio người kê khai do extension chọn theo TÀI KHOẢN đăng nhập (so với người cần cấp đổi trên giấy), không theo giấy.
    declarant = _field(out, "radIsNCC")
    assert declarant["comp"] == "bca-declarant"
    assert declarant["value"]["subject"] == {"name": "NGUYEN VAN AN", "id": "012201000001"}
    assert declarant["value"]["selfLabel"] == "Người kê khai là người cần cấp đổi căn cước"
    assert declarant["value"]["otherLabel"] == ("Người kê khai là cha/mẹ/người đại diện hợp pháp của người cần cấp "
                                                "đổi căn cước")
    assert declarant["value"]["accountNameId"] == "txtFULLNAME_NDN"
    assert declarant["value"]["accountIdId"] == "txtIDENTIFY_NUMBER_NDN"
    # Khối người cần cấp đổi chỉ điền khi tài khoản là người khác (bcaOtherOnly), đứng sau radio.
    for name in ("txtFULLNAME_NCC", "txtBIRTHDATE_NCC", "cboGENDER_ID_NCC", "txtIDENTIFY_NUMBER_NCC",
                 "cboRELATIONSHIP_WITH_NDN"):
        assert _field(out, name).get("bcaOtherOnly") is True
        assert names.index("radIsNCC") < names.index(name)
    assert not any(f.get("bcaOtherOnly") or f.get("bcaSelfOnly") for f in out if f["name"] in ("cboLyDoCap", "cboORG"))
    # SĐT / email người cần cấp đổi chỉ vào Phần I khi tài khoản chính là người đó (tài khoản khác → để ô cho chủ tài
    # khoản tự nhập, không ghi số / email người trên giấy).
    for name in ("txtPHONE_NUMBER_NDN", "txtEMAIL_ADDRESS_NDN"):
        assert _field(out, name).get("bcaSelfOnly") is True and not _field(out, name).get("bcaOtherOnly")
    assert by["txtFULLNAME_NCC"] == "NGUYEN VAN AN" and by["txtIDENTIFY_NUMBER_NCC"] == "012201000001"
    # Giấy không ghi mục II → tài khoản khác người cần cấp đổi thì chọn "Người đại diện hợp pháp".
    assert by["cboRELATIONSHIP_WITH_NDN"]["people"] == []
    assert by["cboRELATIONSHIP_WITH_NDN"]["fallback"] == "Người đại diện hợp pháp"
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
    assert by["radIsNCC"]["subject"] == {"name": "NGUYEN VAN AN", "id": "012201000001"}
    assert names.index("radIsNCC") < names.index("txtFULLNAME_NCC")
    assert by["txtFULLNAME_NCC"] == "NGUYEN VAN AN" and by["txtBIRTHDATE_NCC"] == "01/02/2001"
    assert by["txtIDENTIFY_NUMBER_NCC"] == "012201000001"
    # Không đọc được giới tính → chữ số thứ 4 của số định danh (2 = chẵn = nam).
    assert by["cboGENDER_ID_NCC"] == "Nam"
    # Quan hệ theo tài khoản: trùng người ở mục II thì "Mẹ", không trùng thì "Người đại diện hợp pháp".
    assert by["cboRELATIONSHIP_WITH_NDN"]["people"] == [
        {"relation": "Mẹ", "name": "TRAN THI BINH", "id": "012170000002"}]
    assert by["cboRELATIONSHIP_WITH_NDN"]["fallback"] == "Người đại diện hợp pháp"
    # SĐT Phần I là của người kê khai (mục II.5), không lấy SĐT người cần cấp; chỉ điền khi tài khoản là người khác.
    assert by["txtPHONE_NUMBER_NDN"] == "0987000222"
    phone = _field(out, "txtPHONE_NUMBER_NDN")
    assert phone.get("bcaOtherOnly") is True and not phone.get("bcaSelfOnly")
    assert "txtEMAIL_ADDRESS_NDN" not in by


def test_muc_ii_ghi_chinh_nguoi_can_cap_van_la_tu_ke_khai():
    by = _by(_enrich({**SELF, "NguoiDaiDien_HoTen": "Nguyễn Văn An", "NguoiDaiDien_SoDinhDanh": "012201000001",
                      "NguoiDaiDien_QuanHe": "Mẹ"}))
    # Mục II ghi chính người cần cấp → không phải người kê khai thay: SĐT của người cần cấp, quan hệ không lấy mục II.
    assert by["txtPHONE_NUMBER_NDN"] == "0912000111"
    assert by["cboRELATIONSHIP_WITH_NDN"]["people"] == []


def test_giay_chi_co_ho_ten_van_so_tai_khoan_theo_ho_ten():
    values = {k: v for k, v in SELF.items() if k != "NguoiCanCap_SoDinhDanh"}
    out = _enrich(values)
    assert _field(out, "radIsNCC")["value"]["subject"] == {"name": "NGUYEN VAN AN"}
    assert "txtIDENTIFY_NUMBER_NCC" not in _by(out)


def test_khong_doc_duoc_nguoi_can_cap_thi_khong_chon_radio():
    values = {k: v for k, v in SELF.items() if not k.startswith("NguoiCanCap_")}
    out = _enrich(values)
    by = _by(out)
    assert not {"radIsNCC", "txtFULLNAME_NCC", "cboRELATIONSHIP_WITH_NDN"} & set(by)
    # Không có radio thì không gắn cờ theo người kê khai (extension không bỏ qua ô).
    assert not any(f.get("bcaSelfOnly") or f.get("bcaOtherOnly") for f in out)


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


# ── Trợ lý, luồng có vòng bổ sung ô (extension cờ supportsBcaFlow): tô ô, "Bổ sung các thông tin còn thiếu", Nộp hồ sơ ──
BCA_FLOW_CAPS = {"supportsBcaCanCuoc": True, "supportsFieldReview": True, "supportsBcaFlow": True,
                 "supportsTickCommit": True}
CAM_DOAN = "Tôi xin cam đoan những thông tin kê khai trên là đúng sự thật"


def _bca_fill(review: dict, caps: dict | None = None):
    import asyncio
    from unittest import mock

    from app.channels.handfree.chat import tracing

    conv = {"_id": "c1", "state": "filling", "procedure_key": KEY, "docs_target": "declaration",
            "auto_attach_after_fill": True, "upload_session_id": "s1", "location": {},
            "client_capabilities": dict(caps or BCA_FLOW_CAPS)}
    with mock.patch.object(tracing, "set_report", mock.AsyncMock()):
        r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {"filled": 9, "review": review})))
    return conv, r


def _trail(r) -> str:
    return " ".join(a.get("md", "") for a in r.actions if a.get("type") == "trail_message")


def test_tro_ly_bca_flow_dien_xong_con_o_bat_buoc_thi_moi_bo_sung_chua_cho_nop():
    import asyncio

    from app.channels.handfree.chat import field_review
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(KEY)
    conv, r = _bca_fill({"filled": 9, "optional": 2, "required": 3})
    sends = [c["send"] for c in r.chips]
    assert sends[0] == "__action:field_review_start" and "Bổ sung các thông tin còn thiếu" in r.chips[0]["label"]
    assert "__action:bca_submit" not in sends and "__action:tick_commit" not in sends
    assert "3 ô bắt buộc" in _trail(r) and "🟥" in _trail(r)
    # Lệnh điền mang quy tắc ô → extension tô xanh / cam / đỏ ngay sau khi điền (ô bắt buộc theo dấu * của cổng).
    assert field_review.fill_action_extra(conv, proc) == {"required": [], "commitId": "chkRULE",
                                                         "commitLabel": CAM_DOAN}
    # Bấm "Bổ sung…" → extension tìm ô trống đầu tiên (bắt buộc trước).
    r = asyncio.run(field_review.handle(conv, proc, Intent("action", "field_review_start")))
    assert r.actions[0]["type"] == "field_review_next" and r.actions[0]["requiredFirst"] is True
    # Công dân tự điền đủ trên trang → extension đếm lại → trợ lý hiện nút cam kết + Nộp hồ sơ.
    conv["field_review"]["running"] = False
    r = asyncio.run(field_review.handle(conv, proc, Intent("event", "field_review_status",
                                                           {"stats": {"filled": 12, "optional": 2, "required": 0}})))
    assert "đủ các ô bắt buộc" in r.display_md and "Nộp hồ sơ" in r.display_md
    assert [c["send"] for c in r.chips if c.get("cta")] == ["__action:tick_commit"]


def test_tro_ly_bca_flow_du_o_thi_nut_tich_cam_doan_va_nop_ho_so():
    conv, r = _bca_fill({"filled": 12, "optional": 0, "required": 0})
    cta = [c for c in r.chips if c.get("cta")]
    # Chỉ nút tích ô cam đoan; tích xong mới hiện Nộp hồ sơ.
    assert [c["send"] for c in cta] == ["__action:tick_commit"] and cta[0]["label"] == "☑️ " + CAM_DOAN
    assert "đủ các ô bắt buộc" in _trail(r) and "tích xong tôi hiện nút **Nộp hồ sơ**" in _trail(r)
    # Còn ô không bắt buộc: mời bổ sung (nút thường) nhưng vẫn cho nộp.
    conv, r = _bca_fill({"filled": 12, "optional": 3, "required": 0})
    assert r.chips[0]["send"] == "__action:field_review_start" and not r.chips[0].get("solid")
    assert "__action:tick_commit" in [c["send"] for c in r.chips] and "3 ô không bắt buộc" in _trail(r)
    # Extension cũ: giữ câu cũ (Lưu và Tiếp tục), không nút nộp.
    conv, r = _bca_fill({"filled": 12, "optional": 0, "required": 0}, CAPS)
    assert "__action:bca_submit" not in [c["send"] for c in r.chips] and "Lưu và Tiếp tục" in r.display_md


def test_tro_ly_bca_flow_trang_khong_tra_so_o_van_co_nut_tich_cam_doan_va_nop():
    import asyncio
    from unittest import mock

    from app.channels.handfree.chat import tracing

    for payload, reload_note in (({"filled": 5}, False), ({"filled": 5, "reviewMissing": True}, True)):
        conv = {"_id": "c1", "state": "filling", "procedure_key": KEY, "docs_target": "declaration",
                "auto_attach_after_fill": True, "upload_session_id": "s1", "location": {},
                "client_capabilities": dict(BCA_FLOW_CAPS)}
        with mock.patch.object(tracing, "set_report", mock.AsyncMock()):
            r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", payload)))
        cta = [c for c in r.chips if c.get("cta")]
        assert [c["send"] for c in cta] == ["__action:tick_commit"]
        assert cta[0]["label"] == "☑️ " + CAM_DOAN and "Lưu và Tiếp tục" not in r.display_md
        assert ("chrome://extensions" in r.display_md) is reload_note
    from app.channels.handfree.procedure_registry import get_procedure

    r = flow._bca_flow_handle(conv, get_procedure(KEY), Intent("action", "bca_submit_report", {"noEngine": True}))
    assert "Tải lại" in r.display_md and r.chips == [flow._bca_submit_chip()]


def test_tro_ly_bca_flow_tich_o_cam_doan_theo_nhan_roi_moi_nop():
    import asyncio

    conv, _ = _bca_fill({"filled": 12, "optional": 0, "required": 0})
    r = asyncio.run(flow._handle_reviewing(conv, Intent("action", "tick_commit")))
    assert r.actions == [{"type": "tick_commit", "id": "chkRULE", "label": CAM_DOAN}]
    r = asyncio.run(flow._handle_reviewing(conv, Intent("event", "commit_result", {"ok": True})))
    assert "Nộp hồ sơ" in r.display_md and r.chips == [flow._bca_submit_chip()]
    # Bộ nút đã lưu: nút tích thay bằng Nộp hồ sơ (hiện lại khi công dân tự điền đủ ô / hỏi xong).
    saved = [c["send"] for c in conv["field_review"]["chips"] if c.get("cta")]
    assert saved == ["__action:bca_submit"]


def test_tro_ly_bca_flow_cong_dan_tu_tich_tren_trang_thi_hien_nut_nop():
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(KEY)
    conv, _ = _bca_fill({"filled": 12, "optional": 0, "required": 0})
    tick = Intent("event", "commit_result", {"ok": True, "source": "page"})
    r = flow._bca_flow_handle(conv, proc, tick)
    assert "Công dân đã tích" in r.display_md and r.chips == [flow._bca_submit_chip()]
    r = flow._bca_flow_handle(conv, proc, Intent("event", "commit_result", {"ok": False, "source": "page"}))
    assert "bỏ tích" in r.display_md and [c["send"] for c in r.chips] == ["__action:tick_commit"]
    assert [c["send"] for c in conv["field_review"]["chips"] if c.get("cta")] == ["__action:tick_commit"]
    # Chưa tới bước rà (đang nhận giấy tờ) → im.
    assert flow._bca_flow_handle({**conv, "state": "collecting_docs"}, proc, tick).display_md == ""


def test_tro_ly_bca_flow_nut_nop_soat_o_roi_bam_nut_cua_cong():
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(KEY)
    conv, _ = _bca_fill({"filled": 12, "optional": 0, "required": 0})
    r = flow._bca_flow_handle(conv, proc, Intent("action", "bca_submit"))
    action = r.actions[0]
    assert action["type"] == "bca_submit" and action["buttonIds"][0] == "btnFinishPage1"
    assert "btn-save-send" in action["buttonIds"] and action["nextIds"] == ["btnSaveNextToPage2"]
    assert action["commitId"] == "chkRULE" and action["commitLabel"] == CAM_DOAN
    assert action["fieldReview"]["commitId"] == "chkRULE"

    def report(**payload):
        return flow._bca_flow_handle(conv, proc, Intent("action", "bca_submit_report", payload))

    r = report(clicked=False, missing=["required"], stats={"filled": 10, "optional": 0, "required": 2})
    assert "2 ô bắt buộc" in r.display_md and r.chips[0]["send"] == "__action:field_review_start"
    assert conv["field_review"]["stats"]["required"] == 2
    r = report(clicked=False, missing=["commit"])
    assert CAM_DOAN in r.display_md and [c["send"] for c in r.chips] == ["__action:tick_commit"]
    r = report(clicked=True, stage="next", button="Lưu và Tiếp tục >")
    assert "**Lưu và Tiếp tục**" in r.display_md and "sinh trắc học" in r.display_md
    assert r.chips == [flow._bca_submit_chip()]
    assert "Đồng ý" in report(clicked=True, stage="submit", confirm=True).display_md
    r = report(clicked=True, stage="submit", message="Vui lòng chọn lịch hẹn")
    assert "chưa nộp được" in r.display_md and "Vui lòng chọn lịch hẹn" in r.display_md
    # Cổng chặn nộp, extension đọc lại thấy ô bắt buộc tô đỏ → nêu số ô đỏ + nút Bổ sung (kể cả cổng không hiện toast).
    for message in ("Dữ liệu không hợp lệ. Vui lòng kiểm tra lại", ""):
        r = report(clicked=True, stage="submit", message=message, stats={"filled": 9, "optional": 3, "required": 1})
        assert "chưa nộp được" in r.display_md and "1 ô bắt buộc" in r.display_md and "tô đỏ" in r.display_md
        assert r.chips[0]["send"] == "__action:field_review_start"
        assert conv["field_review"]["stats"]["required"] == 1
    # Sang Bước 2 đặt lịch: ô đỏ của bước mới không phải lỗi nộp.
    r = report(clicked=True, stage="next", button="Lưu và Tiếp tục", stats={"filled": 1, "optional": 0, "required": 2})
    assert "sinh trắc học" in r.display_md
    assert report(clicked=True, stage="submit").display_md == ""  # đã bấm nộp: chờ watcher báo submitted
    assert "chưa thấy nút" in report(clicked=False).display_md
    # Extension cũ không có lệnh này.
    assert flow._bca_flow_handle({**conv, "client_capabilities": CAPS}, proc,
                                 Intent("action", "bca_submit")) is None


def test_tro_ly_bca_bo_sung_khong_doc_ten_html():
    """Extension không đọc được nhãn ô mà gửi tên HTML → hỏi theo tên phần, không đọc tên HTML (user 18/11/2026)."""
    from app.channels.handfree.chat import field_review

    f = field_review._field({"key": "accomStay_cboACCOMMODATION_TYPE", "name": "accomStay_cboACCOMMODATION_TYPE",
                             "label": "accomStay_cboACCOMMODATION_TYPE", "section": "THÔNG TIN CƠ SỞ LƯU TRÚ",
                             "kind": "select"})
    assert "accomStay" not in f["label"] and f["label"].lower() == "cơ sở lưu trú" and f["where"] == ""
    f = field_review._field({"key": "x", "name": "accomStay_cboACCOMMODATION_TYPE",
                             "label": "Loại hình cơ sở lưu trú", "section": "THÔNG TIN CƠ SỞ LƯU TRÚ"})
    assert f["label"] == "Loại hình cơ sở lưu trú" and f["where"].lower() == "cơ sở lưu trú"


def test_tro_ly_bca_flow_noi_nop_ho_so_thi_hoi_xac_nhan():
    from app.channels.handfree.procedure_registry import get_procedure

    conv, _ = _bca_fill({"filled": 12, "optional": 0, "required": 0})
    intent = flow._bca_voice_intent(conv, "nộp hồ sơ")
    assert intent.value == "bca_submit" and intent.payload == {"voice": True}
    r = flow._bca_flow_handle(conv, get_procedure(KEY), intent)
    assert r.chips[0]["send"] == "__action:bca_submit" + flow._VOICE_CONFIRMED
    assert flow._bca_voice_intent({**conv, "client_capabilities": CAPS}, "nộp hồ sơ") is None
