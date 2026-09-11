"""FieldOut phải GIỮ các khoá điều khiển DOM mà mapper gắn thêm.

Bug thật: model chỉ khai name/comp/value/default/clear/occurrence nên pydantic LỌC SẠCH
scope/scopeNear/scopeAway/optionLabel trên đường trả về. Extension nhận field trần, mất khoanh vùng,
rồi điền vào ô trùng tên ĐẦU TIÊN trên trang — tức khối "Thông tin người nộp hồ sơ" của tài khoản
đang đăng nhập. Không lỗi, không cảnh báo, hai đầu nhìn đều thấy đúng.
"""

from app.pipelines.cap_lai_CCHN_thu_y.process import mapper
from app.process.schemas import ProcessResp


def _payload(fields):
    return {"fields": fields, "extracted": {}, "stats": {}}


def test_process_resp_giu_scope_cua_to_don():
    compact = [
        {"name": "NguoiDeNghi_HoTen", "value": "TRẦN THỊ BÍCH THUỶ"},
        {"name": "NguoiDeNghi_NgaySinh", "value": "19/05/1989"},
        {"name": "Don_BangCapChuyenMon", "value": "Bác sĩ thú y"},
    ]
    fields, _ = mapper.enrich(compact, {})

    out = ProcessResp.model_validate(_payload(fields)).model_dump(mode="json")
    by_name = {f["name"]: f for f in out["fields"]}

    don = by_name["data[fullname]"]
    assert don["scope"] == ".formio-component-thongTinChung:has(.formio-component-bangCapChuyenMon)"
    assert don["scopeNear"] == "data[bangCapChuyenMon]"
    assert "data[isOwnerDossierCheck]" in don["scopeAway"]

    # Ô của khối chủ hồ sơ không khai scope — không được tự sinh ra selector nào.
    assert by_name["data[ownerFullname]"].get("scope") is None


def test_process_resp_giu_option_label_cua_checkbox():
    compact = [
        {"name": "NguoiDeNghi_HoTen", "value": "TRẦN THỊ BÍCH THUỶ"},
        {
            "name": "Don_PhamViHanhNghe",
            "value": "Buôn bán thuốc thú y dùng trong thú y cho động vật trên cạn.",
        },
    ]
    fields, _ = mapper.enrich(compact, {})

    out = ProcessResp.model_validate(_payload(fields)).model_dump(mode="json")
    checkboxes = [f for f in out["fields"] if f["name"] == "data[deNghi][]"]

    assert checkboxes, "Phải phát ít nhất một ô phạm vi hành nghề"
    # Mất optionLabel thì extension tick ô ĐẦU TIÊN của nhóm, tức sai phạm vi hành nghề.
    assert checkboxes[0]["optionLabel"] == (
        "Buôn bán thuốc thú y dùng trong thú y cho động vật trên cạn."
    )
