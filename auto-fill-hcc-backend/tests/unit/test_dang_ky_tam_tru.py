"""Đăng ký tạm trú (Cổng DVC Bộ Công an): mapper ô form + nối registry + luồng trợ lý sau khi chọn cơ quan."""
from app.channels.handfree.chat import flow
from app.channels.handfree.chat.intents import Intent
from app.pipelines.dang_ky_tam_tru.process import mapper
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "dang-ky-tam-tru"


def _enrich(**values):
    out = mapper.enrich([{"name": k, "value": v} for k, v in values.items()])
    return {f["name"]: (f["comp"], f["value"]) for f in out}


def test_nguoi_dang_ky_va_noi_tam_tru_ra_dung_o_form():
    v = _enrich(
        NguoiDangKy_HoTen="Lê Thị Hoa",
        NguoiDangKy_NgaySinh="5/3/1998",
        NguoiDangKy_GioiTinh="Nữ",
        NguoiDangKy_SoDinhDanh="0 0 1 1 9 8 0 1 2 3 4 5",
        NguoiDangKy_SoDienThoai="0912 345 678",
        NoiTamTru_DiaChiChiTiet="Số 12 ngách 3 ngõ 45 phố Hoa Mai, phường Đông Hưng, thành phố Hà Nội",
        NoiDungDeNghi="Đăng ký tạm trú tại Số 12 ngách 3 ngõ 45 phố Hoa Mai",
        ThoiHan_DenNgay="30/9/2027",
    )
    assert v["txtFULLNAME"] == ("dom-input", "LÊ THỊ HOA")
    assert v["cboDATE_FORMAT"] == ("dom-select", "Ngày tháng năm")
    assert v["txtDOB"] == ("dom-date", "05/03/1998")
    assert v["cboGENDER_CODE"] == ("dom-select", "Nữ")
    assert v["txtIDENTIFIER_NUMBER"] == ("dom-input", "001198012345")
    assert v["txtPHONE_NUMBER"] == ("dom-input", "0912345678")
    assert v["txtSUGGEST_ADDRESS"] == ("dom-input", "Số 12 ngách 3 ngõ 45 phố Hoa Mai")
    assert v["txtTEMP_RESIDENT_TO"] == ("dom-date", "30/09/2027")
    assert v["txtCHANGED_NOTE"][1].startswith("Đăng ký tạm trú")


def test_dinh_dang_ngay_sinh_chon_truoc_o_ngay_sinh():
    names = [f["name"] for f in mapper.enrich([{"name": "NguoiDangKy_NgaySinh", "value": "01/02/1990"},
                                               {"name": "NguoiDangKy_HoTen", "value": "A"}])]
    assert names.index("cboDATE_FORMAT") < names.index("txtDOB")


def test_ngay_sinh_chi_co_nam_hoac_thang_nam_doi_dinh_dang():
    assert _enrich(NguoiDangKy_NgaySinh="1975")["cboDATE_FORMAT"][1] == "Năm"
    assert _enrich(NguoiDangKy_NgaySinh="1975")["txtDOB"][1] == "1975"
    assert _enrich(NguoiDangKy_NgaySinh="3/1975")["txtDOB"][1] == "03/1975"
    assert _enrich(NguoiDangKy_NgaySinh="3/1975")["cboDATE_FORMAT"][1] == "Tháng năm"


def test_o_trong_cham_cham_va_so_sai_do_dai_khong_dien():
    v = _enrich(NguoiDangKy_SoDienThoai="....................", NguoiDangKy_Email="………",
                NguoiDangKy_SoDinhDanh="00119801234", ThoiHan_DenNgay="30 tháng … năm 202…")
    assert not {"txtPHONE_NUMBER", "txtEMAIL", "txtIDENTIFIER_NUMBER", "txtTEMP_RESIDENT_TO"} & set(v)


def test_thieu_gioi_tinh_thi_suy_theo_chu_so_thu_tu_so_dinh_danh():
    assert _enrich(NguoiDangKy_SoDinhDanh="001198012345")["cboGENDER_CODE"][1] == "Nữ"
    assert _enrich(NguoiDangKy_SoDinhDanh="001090012345")["cboGENDER_CODE"][1] == "Nam"
    assert _enrich(NguoiDangKy_SoDinhDanh="001305012345")["cboGENDER_CODE"][1] == "Nữ"  # nữ sinh từ năm 2000
    assert _enrich(NguoiDangKy_SoDinhDanh="001205012345")["cboGENDER_CODE"][1] == "Nam"


def test_dia_chi_bo_ghi_chu_dia_gioi_cu_trong_ngoac():
    v = _enrich(NoiTamTru_DiaChiChiTiet="Số 8 ngõ 2 phố Cam (địa giới cũ: phường Tây, quận Nam), phường Đông")
    assert v["txtSUGGEST_ADDRESS"][1] == "Số 8 ngõ 2 phố Cam"


def test_quan_he_voi_chu_ho_chon_chu_ho_khong_ghi_thi_to_vang():
    out = {f["name"]: f for f in mapper.enrich([{"name": "ChuHo_QuanHe", "value": "Chủ\nhộ"}])}
    assert out["cboHH_PERSON_RELATIONSHIP_CODE"]["value"] == "Chủ hộ"
    assert not out["cboHH_PERSON_RELATIONSHIP_CODE"].get("default")
    out = {f["name"]: f for f in mapper.enrich([{"name": "NguoiDangKy_HoTen", "value": "Lê Thị Hoa"}])}
    assert (out["cboHH_PERSON_RELATIONSHIP_CODE"]["value"], out["cboHH_PERSON_RELATIONSHIP_CODE"]["default"]) == (
        "Chủ hộ", True)


def test_chu_so_huu_khac_nguoi_dang_ky_dien_dong_xin_y_kien_vneid():
    v = _enrich(NguoiDangKy_HoTen="Lê Thị Hoa", NguoiDangKy_SoDinhDanh="001198012345",
                ChuSoHuu_HoTen="Trần Văn Bình", ChuSoHuu_SoDinhDanh="CMND số: 001070054321",
                ChuSoHuu_NgaySinh="2/3/1970")
    assert v["txtFULLNAME0"] == ("dom-input", "TRẦN VĂN BÌNH")
    assert v["txtCITIZENNUMBER0"] == ("dom-input", "001070054321")
    assert v["txtDOB0"] == ("dom-date", "02/03/1970")
    assert v["cboROLESID0"] == ("dom-select", "Chủ sở hữu chỗ ở hợp pháp")


def test_gcn_chi_co_nam_sinh_thi_de_trong_ngay_sinh_chu_so_huu():
    v = _enrich(NguoiDangKy_SoDinhDanh="001198012345", ChuSoHuu_HoTen="Trần Văn Bình",
                ChuSoHuu_SoDinhDanh="001070054321", ChuSoHuu_NgaySinh="1970")
    assert "txtDOB0" not in v and v["txtFULLNAME0"][1] == "TRẦN VĂN BÌNH"


def test_nguoi_dang_ky_tu_la_chu_so_huu_thi_khong_dien_dong_xin_y_kien():
    same_id = _enrich(NguoiDangKy_HoTen="Lê Thị Hoa", NguoiDangKy_SoDinhDanh="001198012345",
                      ChuSoHuu_HoTen="Lê Thị Hoa", ChuSoHuu_SoDinhDanh="001198012345")
    same_name = _enrich(NguoiDangKy_HoTen="Lê Thị Hoa", ChuSoHuu_HoTen="LÊ THỊ HOA")
    for v in (same_id, same_name):
        assert not {"txtFULLNAME0", "txtCITIZENNUMBER0", "cboROLESID0"} & set(v)


def test_registry_noi_pipeline_va_link_ke_khai():
    assert registry.get_pipeline(KEY) is not None
    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.004194" and link["needsAgencySelect"] is False
    core = next(p for p in registry.public_list() if p["key"] == KEY)
    assert core["mode"] == "agent"


def _conv_on_agency_block():
    conv = {"state": "greet", "procedure_key": None, "location": {}}
    flow._to_confirm_procedure(conv, KEY)
    flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True}))
    return conv


def test_hoi_co_quan_the_co_san_noi_theo_tai_khoan_thi_hien_luon_nut_dien():
    conv = {"state": "greet", "procedure_key": None,
            "location": {"province": "Thành phố Hà Nội", "province_slug": "ha_noi", "ward": "Phường Ba Đình"}}
    flow._to_confirm_procedure(conv, KEY)
    r = flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True}))
    assert conv["bca_agency_pending"] and [c["send"] for c in r.chips] == ["__action:bca_fill_agency"]
    assert "Phường Ba Đình, Thành phố Hà Nội" in r.display_md and not r.actions
    assert [c["kind"] for c in r.cards] == ["location_picker"]


def test_hoi_co_quan_the_chua_co_xa_thi_chua_co_nut_dien():
    conv = _conv_on_agency_block()
    r = flow._bca_agency_ask({**conv, "location": {"province": "Thành phố Hà Nội", "province_slug": "ha_noi"}})
    assert r.chips == [] and [c["kind"] for c in r.cards] == ["location_picker"]


def test_chon_xong_tinh_xa_tren_the_hien_nut_dien_bam_moi_chon_tren_trang():
    conv = _conv_on_agency_block()
    r = flow._apply_location(conv, {"province_slug": "ha_noi", "province": "Thành phố Hà Nội", "ward": "Phường Ba Đình"})
    assert not r.actions and r.chips[0]["send"] == "__action:bca_fill_agency" and "Phường Ba Đình" in r.display_md
    r = flow._handle_guide_login(conv, Intent("action", "bca_fill_agency"))
    assert r.actions[0] == {"type": "fill_bca_agency", "province": "Thành phố Hà Nội", "ward": "Phường Ba Đình"}
    # Watcher thấy đã chọn đủ trong lúc trợ lý còn chờ kết quả chọn hộ → im, không mời gửi giấy tờ hai lần.
    assert flow._handle_guide_login(conv, Intent("event", "page_status",
                                                 {"bcaAgencyBlock": True, "bcaAgencyDone": True})).display_md == ""
    r = flow._handle_guide_login(conv, Intent("event", "bca_agency_result",
                                              {"ok": True, "province": "Thành phố Hà Nội", "ward": "Phường Ba Đình"}))
    assert conv["state"] == "consent" and conv["agency_done"]
    assert r.actions[0]["type"] == "lead_message" and "Phường Ba Đình" in r.actions[0]["md"]


def test_dang_hoi_co_quan_go_chat_thi_nhac_chon_tren_the_khong_ve_them_the():
    conv = _conv_on_agency_block()
    r = flow._handle_guide_login(conv, Intent("unknown", "", {"free_text": True}))
    assert "phía trên" in r.display_md and r.cards == [] and conv["bca_agency_pending"]


_CT01 = ("TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ\n10. Nội dung đề nghị: Đăng ký tạm trú. Chỗ ở hợp pháp: thuê phòng theo "
         "Hợp đồng cho thuê phòng trọ; nhà, đất thuộc Giấy chứng nhận quyền sử dụng đất số AB 123456")
_HOP_DONG = "HỢP ĐỒNG CHO THUÊ PHÒNG TRỌ\nBÊN CHO THUÊ (Bên A)\nBÊN THUÊ (Bên B)"
_GCN = "GIẤY CHỨNG NHẬN\nQUYỀN SỬ DỤNG ĐẤT\nQUYỀN SỞ HỮU NHÀ Ở VÀ TÀI SẢN KHÁC GẮN LIỀN VỚI ĐẤT"
_CCCD = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001198012345"


_KHAI_SINH = "GIẤY KHAI SINH\nHọ, chữ đệm, tên: TRẦN VĂN AN\nHọ, chữ đệm, tên người mẹ: LÊ THỊ HOA"


def _plan(*texts, llm=None):
    from app.pipelines.dang_ky_tam_tru.attach import planner

    files = [{"name": f"f{i}.pdf"} for i in range(len(texts))]
    kinds, case, source = planner.resolve(list(texts), llm)
    items, warnings, _ = planner.build_plan_items(files, kinds, case)
    return items, warnings, case, source


def test_to_khai_nhac_hop_dong_va_gcn_van_la_to_khai():
    from app.pipelines.dang_ky_tam_tru.attach import planner

    assert planner.doc_type(_CT01) == planner.TO_KHAI


def test_llm_loi_co_hop_dong_thue_thi_nhom_thue_muon_o_nho_gcn_vao_dong_them_moi_bo_cccd():
    items, warnings, case, source = _plan(_CT01, _HOP_DONG, _GCN, _CCCD)
    assert (case, source) == ("rented", "rule") and not warnings
    assert {i["groupIndex"] for i in items} == {2}
    assert [(i["fileIndex"], i["target"], i["newRow"], i["rowKey"]) for i in items] == [
        (0, "bca-row", False, "to khai thay doi thong tin cu tru"),
        (1, "bca-row", False, "hop dong cho thue"),
        (2, "bca-row", True, ""),
    ]
    assert items[2]["componentName"].startswith("Giấy chứng nhận quyền sử dụng đất")


def test_llm_loi_khong_hop_dong_ma_co_gcn_thi_nhom_so_huu_cua_minh():
    items, _, case, _ = _plan(_CT01, _GCN)
    assert case == "owned" and {i["groupIndex"] for i in items} == {0}
    assert items[1]["rowKey"] == "chung minh cho o hop phap" and not items[1]["newRow"]


def test_llm_chon_truong_hop_duoc_chu_ho_dong_y_thi_vao_nhom_1():
    llm = {"case": "consented", "documents": [
        {"index": 0, "docType": "to_khai"}, {"index": 1, "docType": "quan_he"}, {"index": 2, "docType": "gcn"}]}
    items, warnings, case, source = _plan(_CT01, _KHAI_SINH, _GCN, llm=llm)
    assert (case, source) == ("consented", "llm") and not warnings
    assert {i["groupIndex"] for i in items} == {1}
    assert [(i["rowKey"], i["newRow"]) for i in items] == [
        ("to khai thay doi thong tin cu tru", False), ("quan he nhan than", False), ("", True)]


def test_llm_loi_khong_hop_dong_co_giay_khai_sinh_thi_duoc_dong_y():
    _, _, case, _ = _plan(_CT01, _KHAI_SINH, _GCN)
    assert case == "consented"


def test_llm_tra_loai_la_thi_file_do_theo_luat_chu_giay_khong_co_dong_thi_canh_bao():
    llm = {"case": "rented", "documents": [{"index": 0, "docType": "bang_lai"}, {"index": 1, "docType": "quan_he"}]}
    items, warnings, case, _ = _plan(_CT01, _KHAI_SINH, llm=llm)
    assert case == "rented" and [i["rowKey"] for i in items] == ["to khai thay doi thong tin cu tru"]
    assert len(warnings) == 1 and "không có dòng" in warnings[0]


def test_ten_giay_to_dung_lam_ten_tep_khong_co_ky_tu_cong_cam():
    import re

    from app.pipelines.dang_ky_tam_tru.attach import planner

    forbidden = re.compile(r'[.,~"#%&*:<>?/{|}]')
    names = [*planner._DOCUMENT_NAMES.values(), planner.GCN_NEW_ROW_NAME]
    assert not [n for n in names if forbidden.search(n)]
    assert planner._DOCUMENT_NAMES[planner.HOP_DONG] == "Hợp đồng cho thuê"


def test_registry_co_buoc_dinh_kem_cung_trang():
    from app.channels.handfree.procedure_registry import get_procedure

    assert registry.get_attach_pipeline(KEY) is not None
    proc = get_procedure(KEY)
    assert proc["samePageAttach"] and proc["hasAttachmentStep"]


def test_dien_xong_hoi_truoc_khong_tu_dinh_kem():
    import asyncio
    from unittest import mock

    from app.channels.handfree.chat import pipeline_runner, tracing

    conv = {"_id": "c1", "state": "filling", "procedure_key": KEY, "docs_target": "declaration",
            "auto_attach_after_fill": True, "upload_session_id": "s1", "location": {}}
    with mock.patch.object(pipeline_runner, "spawn") as spawn, \
            mock.patch.object(tracing, "set_report", mock.AsyncMock()):
        r = asyncio.run(flow._handle_filling(conv, Intent("action", "fill_report", {"filled": 7})))
    assert not spawn.called and conv["state"] == "reviewing"
    assert r.chips[0]["send"] == "__action:confirm_review"
    assert "Hồ sơ đính kèm" in r.display_md and "Thành phần hồ sơ" not in r.display_md


def test_bam_dinh_kem_khi_dang_o_trang_ke_khai_thi_chay_planner_ngay():
    import asyncio
    from unittest import mock

    from app.channels.handfree.chat import pipeline_runner

    conv = {"_id": "c1", "state": "reviewing", "procedure_key": KEY, "docs_target": "declaration",
            "upload_session_id": "s1", "location": {}}
    with mock.patch.object(pipeline_runner, "spawn") as spawn, \
            mock.patch.object(pipeline_runner, "run_attach", mock.MagicMock(return_value=None)):
        r = asyncio.run(flow._handle_reviewing(conv, Intent("action", "confirm_review")))
    assert spawn.called and conv["state"] == "attaching" and conv["attachment_plan_started"]
    assert "Thành phần hồ sơ" not in (r.display_md or "")


def test_dinh_xong_nhac_tich_o_cam_ket_roi_bam_nop_ho_so():
    from app.channels.handfree.procedure_registry import get_procedure

    tpl, commit = flow._attach_done_template(get_procedure(KEY))
    md, tts = flow._fmt(tpl, attached=3, commit=commit)
    assert "Tôi xin chịu trách nhiệm trước pháp luật về lời khai trên" in md and "Nộp hồ sơ" in md
    assert "rà lại lần cuối, rồi bấm ô" in md and "bấm ô" in tts
    # Thủ tục khác giữ câu cũ.
    assert flow._attach_done_template({})[0] is flow.vi.ATTACH_DONE


def _conv_attaching(caps):
    return {"_id": "c1", "state": "attaching", "procedure_key": KEY, "location": {}, "attach_plan": [{}, {}, {}],
            "client_capabilities": caps}


def _attach_report(conv):
    import asyncio
    from unittest import mock

    from app.channels.handfree.chat import tracing

    with mock.patch.object(tracing, "set_report", mock.AsyncMock()):
        return asyncio.run(flow._handle_attaching(conv, Intent("action", "attach_report", {"attached": 3})))


def test_dinh_xong_hien_nut_cam_tich_o_cam_ket():
    conv = _conv_attaching({"supportsTickCommit": True})
    r = _attach_report(conv)
    chip = r.chips[-1]
    assert conv["state"] == "done"
    assert chip["label"] == "Tôi xin chịu trách nhiệm trước pháp luật về lời khai trên"
    assert chip["send"] == "__action:tick_commit" and chip["cta"]
    # Extension cũ không biết tích ô → không có nút cam.
    r_old = _attach_report(_conv_attaching({}))
    assert all(c["send"] != "__action:tick_commit" for c in r_old.chips)


def test_bam_nut_cam_thi_tich_o_tren_trang_roi_nhac_nop_ho_so():
    import asyncio

    conv = _conv_attaching({"supportsTickCommit": True})
    _attach_report(conv)
    r = asyncio.run(flow._handle_done(conv, Intent("action", "tick_commit")))
    assert r.actions == [{"type": "tick_commit", "id": "chkCHECK_LIABILITY"}] and not r.display_md
    r = asyncio.run(flow._handle_done(conv, Intent("event", "commit_result", {"ok": True})))
    assert "Nộp hồ sơ" in r.display_md and r.actions == [{"type": "chip_used", "send": "__action:tick_commit"}]
    r = asyncio.run(flow._handle_done(conv, Intent("event", "commit_result", {"ok": False})))
    assert "chưa tích được" in r.display_md and r.chips[0]["send"] == "__action:tick_commit"


def test_luat_bat_nut_nop_ho_so_cong_bo_cong_an():
    import re

    from app.procedures.portal_submit import portal_submit_rules

    rule = portal_submit_rules()["dichvucong.dancuquocgia.gov.vn"]
    assert rule["buttonIds"] == ["btn-save-send"] and rule["buttonText"] == ["nop ho so"]
    assert re.match(rule["urlPattern"], "/portal/p/home/dang-ky-tam-tru.html")
    assert not re.match(rule["urlPattern"], "/portal/p/home/ho-so.html")


def test_cong_dan_tu_chon_tren_trang_cung_sang_buoc_giay_to():
    conv = _conv_on_agency_block()
    flow._handle_guide_login(conv, Intent("event", "page_status", {"bcaAgencyBlock": True, "bcaAgencyDone": True}))
    assert conv["state"] == "consent"
    conv["consent"] = {"accepted": True}
    r = flow._to_ask_doc_method(conv)
    assert conv["state"] == "ask_doc_method" and r.cards[0]["kind"] == "doc_options"
