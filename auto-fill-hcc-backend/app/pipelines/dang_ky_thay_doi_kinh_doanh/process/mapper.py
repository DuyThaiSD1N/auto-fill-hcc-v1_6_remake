"""Quyết định luồng/page thay đổi HKD từ facts nguồn.

LLM không được tự bật cờ thay đổi. Mapper so sánh trạng thái hiện tại với giá trị
đề nghị và chỉ dựng field cho trang thực sự cần sửa; trang người nộp luôn có mặt.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines.dang_ky_kinh_doanh.process import mapper as creation_mapper
from app.pipelines._shared.formatting import normalize_date


PAGE_LABELS = {
    "dia-chi": "Địa chỉ",
    "nganh-nghe-kinh-doanh": "Ngành nghề kinh doanh",
    "ten-ho-kinh-doanh": "Tên hộ kinh doanh",
    "chu-ho-kinh-doanh": "Thông tin về chủ hộ kinh doanh",
    "thong-tin-ve-von": "Thông tin về vốn",
    "thong-tin-ve-thue": "Thông tin về thuế",
    "nguoi-nop-ho-so": "Người nộp hồ sơ",
}


def _by_name(fields: list[dict]) -> dict[str, Any]:
    return {item["name"]: item.get("value") for item in fields if item.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def _fold(value: Any) -> str:
    text = _text(value).lower().replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def _digits(value: Any) -> str:
    return re.sub(r"\D", "", _text(value))


def _business_number(value: Any) -> str:
    """Giữ nguyên dấu - trong mã số hộ kinh doanh/MST vì cần thiết cho việc tìm kiếm."""
    text = _text(value)
    # Chỉ loại bỏ ký tự không phải số và dấu gạch ngang
    return re.sub(r"[^\d\-]", "", text)


def _has_letters(value: Any) -> bool:
    return bool(re.search(r"[A-Za-z]", _text(value)))


def _registration_code(value: Any) -> str:
    """Mã đăng ký hộ kinh doanh kiểu cũ có lẫn CHỮ CÁI (vd "32A8010625": mã tỉnh + chữ + số).
    Giữ nguyên chữ + số, bỏ khoảng trắng/dấu chấm/gạch ngang, viết hoa cho khớp định dạng cổng."""
    return re.sub(r"[^0-9A-Za-z]", "", _text(value)).upper()


def _business_code(value: Any) -> str:
    digits = _digits(value)
    return digits if len(digits) == 4 else ""


def _strip_hkd(value: Any) -> str:
    return re.sub(r"^\s*hộ\s+kinh\s+doanh\s+", "", _text(value), flags=re.I).strip()


def _normal_name(value: Any) -> str:
    return _fold(_strip_hkd(value))


def _normal_money(value: Any) -> str:
    digits = _digits(value)
    return digits.lstrip("0") or ("0" if digits else "")


def _normal_address(value: Any) -> str:
    if not isinstance(value, dict):
        return _fold(value)
    normalized = creation_mapper._addr(value)
    return "|".join(_fold(normalized.get(key)) for key in ("quocGia", "tinh", "xa", "diaChi"))


def _person_identity(value: Any) -> tuple[str, str]:
    if not isinstance(value, dict):
        return ("", "")
    return (_fold(value.get("hoTen")), _digits(value.get("soDinhDanh")))


def _different(current: Any, requested: Any, normalizer) -> bool:
    if requested in (None, "", {}, []):
        return False
    req = normalizer(requested)
    if not req:
        return False
    cur = normalizer(current)
    return not cur or cur != req


def _clean_lines(value: Any, *, allow_text_only: bool) -> list[dict[str, Any]]:
    rows = value if isinstance(value, list) else []
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if isinstance(row, dict):
            code = _business_code(row.get("ma") or row.get("code"))
            name = _text(row.get("ten") or row.get("name"))
            main = bool(row.get("chinh") or row.get("main"))
        else:
            code, name, main = "", _text(row), False
        if not code and (not allow_text_only or not name):
            continue
        key = (code, _fold(name))
        if key in seen:
            continue
        seen.add(key)
        out.append({"code": code, "name": name, "main": main})
    return out


def _compact_field(name: str, value: Any) -> dict:
    return {"name": name, "comp": "raw", "value": value}


def _person_fields(person: Any, prefix: str) -> list[dict]:
    if not isinstance(person, dict):
        return []
    mapping = {
        "hoTen": f"{prefix}_HoTen",
        "gioiTinh": f"{prefix}_GioiTinh",
        "ngaySinh": f"{prefix}_NgaySinh",
        "soDinhDanh": f"{prefix}_SoDinhDanh",
        "diaChi": f"{prefix}_DiaChi",
        "dienThoai": f"{prefix}_DienThoai",
        "email": f"{prefix}_Email",
        "fax": f"{prefix}_Fax",
        "website": f"{prefix}_Website",
    }
    return [_compact_field(target, person.get(source)) for source, target in mapping.items() if person.get(source) not in (None, "", {}, [])]


_AUTHORIZATION_IDENTITY_FIELDS = (
    "UyQuyen_NguoiUyQuyen_HoTen",
    "UyQuyen_NguoiUyQuyen_SoDinhDanh",
    "UyQuyen_NguoiDuocUyQuyen_HoTen",
    "UyQuyen_NguoiDuocUyQuyen_SoDinhDanh",
)


def _has_identity_documents(values: dict[str, Any]) -> bool:
    """Hồ sơ có giấy tờ nhân thân ngoài tờ đơn không (CCCD rời hoặc Giấy ủy quyền)."""
    raw = values.get("Cccd_DanhSach")
    if isinstance(raw, list) and any(isinstance(item, dict) and item for item in raw):
        return True
    if values.get("HasMultipleCCCD"):
        return True
    if values.get("UyQuyen_CoGiayUyQuyen"):
        return True
    return any(values.get(name) not in (None, "", {}, []) for name in _AUTHORIZATION_IDENTITY_FIELDS)


def _identity_candidates(values: dict[str, Any]) -> list[dict[str, Any]]:
    """Nhân thân đọc từ MỌI thẻ căn cước trong hồ sơ (đã gộp mặt trước/sau của cùng một thẻ).

    Backend KHÔNG biết ai đang đăng nhập cổng nên không tự chọn người nộp; extension so danh sách này
    với dữ liệu tài khoản (sau khi bấm "Sao chép thông tin đăng ký tài khoản") — khớp số định danh
    hoặc họ tên là ra đúng thẻ của người nộp, rồi ghi nhân thân + địa chỉ đó vào khối người nộp.
    """
    candidates: list[dict[str, Any]] = []
    raw = values.get("Cccd_DanhSach")
    if isinstance(raw, list):
        candidates.extend(item for item in raw if isinstance(item, dict))
    for source in (values.get("NguoiNop"), values.get("DeNghi_ChuHo"), values.get("HienTai_ChuHo")):
        if isinstance(source, dict):
            candidates.append(source)
    # Giấy ủy quyền là căn cứ chính cho người nộp thay → lên đầu, thẻ căn cước chỉ bù field còn trống.
    candidates = creation_mapper.delegate_first(candidates, values)
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in candidates:
        key = _person_identity(item)
        if key == ("", "") or key in seen:
            continue
        seen.add(key)
        normalized = dict(item)
        if item.get("diaChi") not in (None, "", {}, []):
            normalized["diaChi"] = creation_mapper._addr(item["diaChi"])
        out.append(normalized)
    return out


def build(fields: list[dict]) -> tuple[dict[str, list[dict]], dict[str, Any]]:
    values = _by_name(fields)
    additions = _clean_lines(values.get("DeNghi_NganhNgheBoSung"), allow_text_only=True)
    removals = _clean_lines(values.get("DeNghi_NganhNgheBaiBo"), allow_text_only=False)

    flags = {
        "name": _different(values.get("HienTai_Ten"), values.get("DeNghi_Ten"), _normal_name),
        "address": _different(values.get("HienTai_TruSo"), values.get("DeNghi_TruSo"), _normal_address)
        or values.get("DeNghi_KhongKinhDoanhTaiTruSo") is True,
        "industry": bool(additions or removals),
        "owner": bool(values.get("DeNghi_ChuHo")),
        "capital": _different(values.get("HienTai_Von"), values.get("DeNghi_Von"), _normal_money)
        or bool(values.get("DeNghi_Von_HinhThuc") or values.get("DeNghi_Von_ThoiDiem")),
        "tax": bool(values.get("DeNghi_Thue")),
    }

    pages: dict[str, list[dict]] = {}
    order: list[str] = []

    if flags["address"]:
        compact = [_compact_field("TruSo_DiaChi", values.get("DeNghi_TruSo"))]
        for suffix in ("DienThoai", "Email", "Fax", "Website"):
            value = values.get(f"DeNghi_TruSo_{suffix}")
            if value not in (None, ""):
                compact.append(_compact_field(f"TruSo_{suffix}", value))
        pages["dia-chi"] = creation_mapper.enrich(compact, page="dia-chi")
        if values.get("DeNghi_KhongKinhDoanhTaiTruSo") is True:
            pages["dia-chi"].append({"name": "ctl00$C$NO_BUSINESS_HEADOFFICEld", "comp": "dom-checkbox", "value": True})
        order.append("dia-chi")

    if flags["industry"]:
        pages["nganh-nghe-kinh-doanh"] = [{
            "name": "__businessLineChanges",
            "comp": "raw",
            "value": {"add": additions, "remove": removals},
        }]
        order.append("nganh-nghe-kinh-doanh")

    if flags["name"]:
        compact = [_compact_field("HoKinhDoanh_Ten", values.get("DeNghi_Ten"))]
        pages["ten-ho-kinh-doanh"] = creation_mapper.enrich(compact, page="ten-ho-kinh-doanh")
        order.append("ten-ho-kinh-doanh")

    if flags["owner"]:
        compact = _person_fields(values.get("DeNghi_ChuHo"), "ChuHo")
        pages["chu-ho-kinh-doanh"] = creation_mapper.enrich(compact, page="chu-ho-kinh-doanh")
        pages["chu-ho-kinh-doanh"].append({
            "name": "ctl00$C$OWN_PCtl$PERSCtl$PERSONChange", "comp": "dom-checkbox", "value": True,
        })
        # Luôn cố định "Cập nhật thông tin chủ hộ kinh doanh" / "Khác" — KHÔNG dùng giá trị LLM
        # đọc từ Thông báo. "Lý do" là select con phụ thuộc "Loại": chỉ khi "Loại" = "Cập nhật
        # thông tin chủ hộ kinh doanh" thì "Khác" mới xuất hiện trong danh sách để chọn được;
        # các "Loại" khác (vd "Thay đổi chủ hộ kinh doanh") không có option "Khác" nên chọn hụt.
        pages["chu-ho-kinh-doanh"].append({
            "name": "ctl00$C$CHANGE_OWNER_TYPE_TITLE_IDFld", "comp": "dom-select",
            "value": "Cập nhật thông tin chủ hộ kinh doanh",
        })
        pages["chu-ho-kinh-doanh"].append({
            "name": "ctl00$C$CHANGE_OWNER_TYPE_IDFld", "comp": "dom-select",
            "value": "Khác",
        })
        # Lên "chu-ho-kinh-doanh" HAI LẦN liên tiếp trong order: lượt 1 chỉ chốt "Loại đăng ký thay
        # đổi"/"Lý do" (2 select cascade, dễ điền hụt nếu nhồi chung với cả khối nhân thân), lượt 2
        # mới điền nhân thân/địa chỉ + Lưu. Extension (business-registration.js) tách 2 lượt bằng
        # cách "nhìn trước" order — thấy còn 1 "chu-ho-kinh-doanh" nữa phía sau là lượt 1.
        order.append("chu-ho-kinh-doanh")
        order.append("chu-ho-kinh-doanh")

    if flags["capital"]:
        pages["thong-tin-ve-von"] = creation_mapper.enrich(
            [_compact_field("Von_SoTien", values.get("DeNghi_Von"))], page="thong-tin-ve-von"
        )
        if values.get("DeNghi_Von_HinhThuc"):
            pages["thong-tin-ve-von"].append({
                "name": "ctl00$C$DRLCL_INCREASE_DECREASE_TYPEFld", "comp": "dom-select",
                "value": values["DeNghi_Von_HinhThuc"],
            })
        if values.get("DeNghi_Von_ThoiDiem"):
            pages["thong-tin-ve-von"].append({
                "name": "ctl00$C$CPT_CONTR_TIMEFld", "comp": "dom-date",
                "value": normalize_date(values["DeNghi_Von_ThoiDiem"]),
            })
        order.append("thong-tin-ve-von")

    if flags["tax"] and isinstance(values.get("DeNghi_Thue"), dict):
        tax = values["DeNghi_Thue"]
        compact = []
        tax_map = {
            "diaChiNhanThongBao": "Thue_DiaChiNhanThongBao", "dienThoai": "Thue_DienThoai",
            "fax": "Thue_Fax", "email": "Thue_Email", "ngayBatDau": "Thue_NgayBatDau",
            "soLaoDong": "Thue_SoLaoDong", "phuongPhapTinh": "Thue_PhuongPhapTinh",
        }
        for source, target in tax_map.items():
            if tax.get(source) not in (None, "", {}, []):
                compact.append(_compact_field(target, tax[source]))
        if values.get("DeNghi_TruSo"):
            compact.append(_compact_field("TruSo_DiaChi", values["DeNghi_TruSo"]))
        elif values.get("HienTai_TruSo"):
            compact.append(_compact_field("TruSo_DiaChi", values["HienTai_TruSo"]))
        pages["thong-tin-ve-thue"] = creation_mapper.enrich(compact, page="thong-tin-ve-thue")
        order.append("thong-tin-ve-thue")

    # Người nộp là chủ hộ hiện tại (hoặc chủ hộ đề nghị nếu đổi chủ) làm mặc định
    owner = values.get("HienTai_ChuHo") if isinstance(values.get("HienTai_ChuHo"), dict) else (
        values.get("DeNghi_ChuHo") if isinstance(values.get("DeNghi_ChuHo"), dict) else {}
    )
    applicant = values.get("NguoiNop") if isinstance(values.get("NguoiNop"), dict) else {}

    # Trang người nộp dùng NGUYÊN logic của đăng ký hộ kinh doanh: đưa đủ nhân thân người nộp + chủ hộ
    # + danh sách CCCD sang creation_mapper.enrich để nó tự chốt radio vai trò, nhân thân, địa chỉ,
    # __applicantAddress và __identityCandidates. Extension vẫn chốt lại theo tài khoản THẬT sau khi
    # bấm "Sao chép thông tin đăng ký tài khoản" (chỉ cần số định danh HOẶC họ tên khớp chủ hộ là tick
    # "Người có thẩm quyền ký Giấy đề nghị đăng ký Hộ kinh doanh").
    candidates = _identity_candidates(values)
    # Hồ sơ CHỈ có tờ đơn xin thay đổi: không kèm CCCD nào, cũng không có Giấy ủy quyền. Khi đó nhân
    # thân duy nhất đọc được là CHỦ HỘ ghi trong đơn, nên extension không thể đối chiếu tài khoản
    # đang đăng nhập bằng số định danh (đơn hay thiếu/OCR lẫn số) — chỉ còn HỌ TÊN chủ hộ làm căn cứ.
    form_only = not _has_identity_documents(values)
    applicant_compact = _person_fields(applicant, "NguoiNop") + _person_fields(owner, "ChuHo")
    # Người nộp thay có thể CHỈ có tên trong Giấy ủy quyền → chuyển tiếp nguyên nhóm field ủy quyền
    # để creation_mapper dựng nhân thân đó vào __identityCandidates.
    applicant_compact.extend(creation_mapper.authorization_fields(values))
    if isinstance(values.get("Cccd_DanhSach"), list) and values["Cccd_DanhSach"]:
        applicant_compact.append(_compact_field("Cccd_DanhSach", values["Cccd_DanhSach"]))
    # Hồ sơ có từ 2 nhân thân trở lên (kể cả chủ hộ + người ký giấy đề nghị) ⇒ nhiều khả năng có người
    # nộp thay; enrich chỉ đếm được Cccd_DanhSach nên truyền sẵn cờ theo danh sách đầy đủ.
    if values.get("HasMultipleCCCD") or len(candidates) >= 2:
        applicant_compact.append(_compact_field("HasMultipleCCCD", True))

    pages["nguoi-nop-ho-so"] = creation_mapper.enrich(applicant_compact, page="nguoi-nop-ho-so")
    
    # Thêm thông tin ủy quyền KÈM địa chỉ người được ủy quyền (giống logic cấp lại/cấp đổi)
    authorized_person_info = creation_mapper.authorized_person(values)
    authorization_info = {
        "coGiayUyQuyen": bool(values.get("UyQuyen_CoGiayUyQuyen")),
        "nguoiUyQuyen": {
            "hoTen": values.get("UyQuyen_NguoiUyQuyen_HoTen") or "",
            "soDinhDanh": values.get("UyQuyen_NguoiUyQuyen_SoDinhDanh") or "",
        },
    }
    if any(authorization_info["nguoiUyQuyen"].values()):
        authorization_data = dict(authorization_info)
        # Thêm địa chỉ người được ủy quyền (đã gộp từ giấy ủy quyền + CCCD nếu có)
        if authorized_person_info and authorized_person_info.get("diaChi"):
            authorization_data["nguoiDuocUyQuyen"] = {
                "hoTen": authorized_person_info.get("hoTen") or "",
                "soDinhDanh": authorized_person_info.get("soDinhDanh") or "",
                "diaChi": authorized_person_info.get("diaChi"),  # Đã normalize qua _addr()
            }
        pages["nguoi-nop-ho-so"].append(_compact_field("__authorization", authorization_data))
    
    order.append("nguoi-nop-ho-so")

    ma_so = values.get("HoKinhDoanh_MaSo")
    ma_dang_ky = values.get("HoKinhDoanh_MaDangKy")
    # "Mã số Hộ kinh doanh" (ô businessNumber, GDT_CODEFld) chỉ nhận mã THUẦN SỐ (dạng MST). Mã có
    # lẫn CHỮ CÁI (vd "32A8010625" — mã đăng ký hộ kinh doanh kiểu cũ: mã tỉnh + chữ + số) PHẢI vào
    # đúng ô "Mã số đăng ký hộ kinh doanh" (registrationNumber, IMP_BUSINESS_REG_NUMBERFbl) — điền
    # nhầm ô businessNumber sẽ tra cứu ra rỗng. OCR/LLM có thể gán mã này vào field HoKinhDoanh_MaSo
    # theo thói quen nên tự soi lại theo NỘI DUNG (có chữ cái hay không), không tin tuyệt đối tên field.
    if ma_so and _has_letters(ma_so):
        business_number = ""
        registration_number = _registration_code(ma_so)
    else:
        business_number = _business_number(ma_so)
        registration_number = _registration_code(ma_dang_ky) if _has_letters(ma_dang_ky) else _digits(ma_dang_ky)

    search_options = [
        ("businessNumber", business_number),
        ("registrationNumber", registration_number),
        ("internalNumber", _digits(values.get("HoKinhDoanh_MaNoiBo"))),
    ]
    if isinstance(values.get("HienTai_ChuHo"), dict):
        search_options.append(("identityNumber", _digits(values["HienTai_ChuHo"].get("soDinhDanh"))))
    method, value = next(((method, value) for method, value in search_options if value), ("", ""))

    flow = {
        "workflow": "change",
        "wizardType": "change",
        "amendmentType": "CHAPAR",
        "search": {
            "method": method,
            "value": value,
            "expectedName": _text(values.get("HienTai_Ten")),
            "expectedBusinessNumber": _business_number(values.get("HoKinhDoanh_MaSo")),
        },
        "nameChange": flags["name"],
        "changeFlags": flags,
        "pageOrder": order,
        # Hồ sơ không đổi chủ hộ thì KHÔNG có trang chủ hộ để extension đối chiếu → gửi kèm nhân thân
        # chủ hộ. Extension so với tài khoản đang đăng nhập: khớp số định danh HOẶC họ tên ⇒ chủ hộ
        # tự nộp. Không kê khai chủ hộ thì lấy người ký giấy đề nghị (mặc định là chủ hộ).
        "owner": {
            "hoTen": _text((owner or applicant).get("hoTen")),
            "soDinhDanh": _digits((owner or applicant).get("soDinhDanh")),
        },
        "industryChanges": {"add": additions, "remove": removals},
        "identityCandidates": candidates,
        # Chỉ có tờ đơn → extension chốt vai trò người nộp bằng HỌ TÊN chủ hộ (xem
        # isChangeFormOnlyDossier trong business-registration.js).
        "formOnly": form_only,
    }
    return pages, flow
