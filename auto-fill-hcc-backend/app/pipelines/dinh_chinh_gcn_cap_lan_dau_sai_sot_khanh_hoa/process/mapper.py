"""Map facts nguồn sang Form.io cổng iGate Khánh Hòa (đính chính GCN đã cấp lần đầu có sai sót, 1.012796).

Cùng template ba khối và cùng tên facts với đính chính GCN đã cấp Khánh Hòa (1.012790) nên gọi lại mapper đó:
- Phần I  người nộp  -> data[fullname]/phoneNumber/birthday/email/identityNumber/identityDate/identityAgency_text/
                         province/village/address + data[noidungyeucaugiaiquyet] (NGUYÊN VĂN Đơn mục 2).
- Phần II chủ hồ sơ  -> data[chonDoiTuong]/owner*/province1/village1/ownerAddress.
- Phần III thửa đất  -> data[diaChiThuaDat]/SoThuaDat/SoToBanDo/province2/village2/nation2.
Ô giấy tờ không có dữ liệu thì TRẢ VỀ TRỐNG (Phần I cổng đổ sẵn theo tài khoản đăng nhập); "Lấy người nộp theo tờ khai"
(options.submitterMode) xử lý trong mapper gốc.

Riêng thủ tục này:
- Đơn mục 2 trống -> câu mặc định mang đúng tên thủ tục "…lần đầu có sai sót".
- Giấy chứng nhận đứng tên nhiều người (vợ chồng) mà Đơn chỉ kê khai một người (người có thông tin sai) -> nhắc cán bộ
  hỏi người còn lại có phải cùng ký Đơn không (file mapping: "Cần xác nhận với bộ phận tiếp nhận có phải kê khai/ký thêm").
"""

from __future__ import annotations

from typing import Any

from app.pipelines.dinh_chinh_gcn_da_cap_khanh_hoa.process import mapper as _base

DEFAULT_REQUEST = "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót"
_REQUEST_FIELD = "data[noidungyeucaugiaiquyet]"


def gcn_co_holder_warning(gcn_name: Any, owner_name: Any, co_users: Any, request: Any) -> list[str]:
    """Chủ hồ sơ có tên trên GCN nhưng GCN còn người khác mà Đơn không kê khai, Đơn mục 2 cũng không nhắc."""
    gcn = _base._people(gcn_name)
    owner = set(_base._people(owner_name))
    if len(gcn) < 2 or not owner or not owner & set(gcn):
        return []  # một người, hoặc GCN không có chủ hồ sơ (mapper gốc đã cảnh báo lệch hồ sơ)
    known = owner | set(_base._people(co_users))
    folded_request = _base._fold(_base._text(request) or "")
    others = [name for name in gcn if name not in known and name not in folded_request]
    if not others:
        return []
    names = [part for part in _base._PERSON_SEP.split(_base._text(gcn_name) or "")
             if _base._fold(_base._HONORIFIC.sub("", part)) in others]
    shown = ", ".join(" ".join(_base._HONORIFIC.sub("", part).split()) for part in names) or ", ".join(others)
    return [f"Giấy chứng nhận còn đứng tên {shown} nhưng Đơn chỉ kê khai {_base._text(owner_name)} — cán bộ xác nhận "
            "người cùng đứng tên có phải cùng ký Đơn đề nghị đính chính không."]


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    out, warnings = _base.enrich(fields, options)
    for item in out:
        if item["name"] == _REQUEST_FIELD and item.get("default"):
            item["value"] = str(item["value"]).replace(_base.DEFAULT_REQUEST, DEFAULT_REQUEST, 1)
    values = _base._by_name(fields)
    request = next((item["value"] for item in out if item["name"] == _REQUEST_FIELD), None)
    warnings.extend(gcn_co_holder_warning(values.get("GCN_NguoiSuDung"), values.get("ChuHoSo_HoTen"),
                                          values.get("ChuHoSo_NguoiCungSuDung"), request))
    return out, warnings
