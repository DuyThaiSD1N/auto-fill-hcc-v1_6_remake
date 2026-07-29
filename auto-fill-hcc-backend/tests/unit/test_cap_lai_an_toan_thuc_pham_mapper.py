"""Mapper tests for ATTP certificate reissue process."""

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.cap_lai_an_toan_thuc_pham import process as agent
from app.pipelines.cap_lai_an_toan_thuc_pham.process import mapper
from app.pipelines.cap_lai_an_toan_thuc_pham.process.prompt import EXTRA_RULES
from app.pipelines.cap_lai_an_toan_thuc_pham.process.schema import FIELDS
from app.procedures.registry import get_pipeline, get_procedure


def _field(name, value):
    return {"name": name, "comp": "x-input", "value": value}


def _values(mapped: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in mapped}


def test_cap_lai_an_toan_thuc_pham_registered():
    key = "cap-lai-giay-chung-nhan-du-dieu-kien-an-toan-thuc-pham"
    proc = get_procedure(key)

    assert proc
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert "Cấp lại Giấy chứng nhận đủ điều kiện an toàn thực phẩm" in proc["label"]
    assert get_pipeline(key) is agent.run


def test_cap_lai_an_toan_thuc_pham_maps_reissue_application_and_facility():
    fields = [
        _field("DonCapLai_DiaDanh", "Lai Châu"),
        _field("DonCapLai_NgayDon", "15/9/2025"),
        _field("DonCapLai_KinhGui", "Ủy ban nhân dân tỉnh Lai Châu; Sở Công Thương tỉnh Lai Châu"),
        _field(
            "DonCapLai_TenCoSo",
            "ĐỊA ĐIỂM KINH DOANH WINMART + LCU 01 - CHI NHÁNH LAI CHÂU - CÔNG TY CỔ PHẦN DỊCH VỤ THƯƠNG MẠI TỔNG HỢP WINCOMMERCE",
        ),
        _field(
            "DonCapLai_DiaChiCoSo",
            "Số 56 Đường 30/04, tổ 22, phường Đông Phong, thành phố Lai Châu, tỉnh Lai Châu (nay là Số 56 Đường 30/04, tổ 22, phường Tân Phong, tỉnh Lai Châu)",
        ),
        _field("DonCapLai_GCNCuSo", "05 /2022/GCNATTP-SCT"),
        _field("DonCapLai_NgayCapGCNCu", "08/9/2022"),
        _field("DonCapLai_LyDoCapLai", "Hết hạn Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm."),
        _field("DonCapLai_NguoiKy", "PHAN NGUYÊN TRỌNG HUY"),
        _field("ThuyetMinh_DienThoai", "0247.106.6866"),
        _field("DangKy_MaSo", "0104918404-094"),
    ]

    out, warnings = mapper.enrich(fields, {})
    d = _values(out)

    assert warnings == []
    assert d["data[isOwnerDossier]"] is False
    assert d["data[ownerFullname]"].startswith("ĐỊA ĐIỂM KINH DOANH WINMART + LCU 01")
    assert d["data[ownertaxCode]"] == "0104918404-094"
    assert "data[ownerIdentityNumber]" not in d
    assert d["data[ownerPhoneNumber]"] == "02471066866"
    assert "Số 56 Đường 30/04" in d["data[ownerAddress]"]
    assert d["data[tinhThanhPhoNopDon]"] == "Lai Châu"
    assert d["data[ngayNopDon]"] == "15/09/2025"
    assert d["data[GCNCuSo]"] == "05/2022/GCNATTP-SCT"
    assert d["data[NgayCapGCNCu]"] == "08/09/2022"
    assert d["data[KyTen]"] == "PHAN NGUYÊN TRỌNG HUY"
    assert d["data[noidungyeucaugiaiquyet]"] == "Đề nghị cấp lại Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm"


def test_cap_lai_an_toan_thuc_pham_picks_authorized_requester_by_context():
    fields = [
        _field("UyQuyen_BenUyQuyen_HoTen", "PHAN NGUYÊN TRỌNG HUY"),
        _field("UyQuyen_BenUyQuyen_SoDinhDanh", "052090009343"),
        _field("UyQuyen_BenUyQuyen_NgayCap", "16/09/2022"),
        _field("UyQuyen_BenUyQuyen_NoiCap", "Cục cảnh sát QLHC về TTXH"),
        _field("UyQuyen_BenDuocUyQuyen_HoTen", "LÒ TUẤN ANH"),
        _field("UyQuyen_BenDuocUyQuyen_SoDinhDanh", "012092005828"),
        _field("UyQuyen_BenDuocUyQuyen_NgayCap", "11/08/2021"),
        _field("UyQuyen_BenDuocUyQuyen_NoiCap", "Cục cảnh sát QLHC về TTXH"),
        _field("DonCapLai_TenCoSo", "Địa điểm kinh doanh Winmart + LCU 01"),
    ]

    out, warnings = mapper.enrich(
        fields,
        {"formContext": {"applicantFullname": "Lò Tuấn Anh", "applicantIdentityNumber": "012092005828"}},
    )
    d = _values(out)

    assert warnings == []
    assert d["data[fullname]"] == "LÒ TUẤN ANH"
    assert d["data[identityNumber]"] == "012092005828"
    assert d["data[identityDate]"] == "11/08/2021"
    assert d["data[isOwnerDossier]"] is False


def test_cap_lai_an_toan_thuc_pham_prompt_locks_sources():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Đơn đề nghị cấp lại là nguồn chính" in system_prompt
    assert "Không trả field UI dạng data[...]" in system_prompt
    assert "Không lấy nhầm GCN chuỗi hoặc GCN cấp lại mới hơn" in system_prompt
    assert "DonCapLai_GCNCuSo" in system_prompt
    assert "GCNCu_SoCap" in system_prompt
