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
    return "|".join(_fold(value.get(key)) for key in ("quocGia", "tinh", "xa", "diaChi"))


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


def _proper_name(value: Any) -> str:
    """Chuẩn hóa họ tên về dạng viết hoa chữ đầu mỗi từ."""
    text = _text(value)
    if not text:
        return ""
    return " ".join(word.capitalize() for word in text.split())


def _has_address(value: Any) -> bool:
    """Địa chỉ có nội dung thật hay không (chỉ mỗi quốc gia mặc định thì coi như trống)."""
    if not isinstance(value, dict):
        return bool(_text(value))
    return any(value.get(key) for key in ("tinh", "xa", "diaChi"))


def _submitter_is_owner(values: dict[str, Any]) -> bool | None:
    """Người nộp có phải chính chủ hộ không, dựa trên nhân thân hồ sơ kê khai.

    Trả None khi hồ sơ không kê khai riêng người nộp (không đủ dữ liệu để kết luận) —
    lúc đó caller suy tiếp từ số lượng CCCD trong hồ sơ.
    """
    submitter_id = _digits(values.get("NguoiNop", {}).get("soDinhDanh") if isinstance(values.get("NguoiNop"), dict) else "")
    # So với chủ hộ hiện tại (thay đổi) hoặc chủ hộ đề nghị
    owner_id = _digits(
        values.get("HienTai_ChuHo", {}).get("soDinhDanh") if isinstance(values.get("HienTai_ChuHo"), dict) else ""
    ) or _digits(
        values.get("DeNghi_ChuHo", {}).get("soDinhDanh") if isinstance(values.get("DeNghi_ChuHo"), dict) else ""
    )
    if submitter_id and owner_id:
        return submitter_id == owner_id

    submitter_name = _fold(values.get("NguoiNop", {}).get("hoTen") if isinstance(values.get("NguoiNop"), dict) else "")
    owner_name = _fold(
        values.get("HienTai_ChuHo", {}).get("hoTen") if isinstance(values.get("HienTai_ChuHo"), dict) else ""
    ) or _fold(
        values.get("DeNghi_ChuHo", {}).get("hoTen") if isinstance(values.get("DeNghi_ChuHo"), dict) else ""
    )
    if submitter_name and owner_name:
        return submitter_name == owner_name

    return None


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
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in candidates:
        key = _person_identity(item)
        if key == ("", "") or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


_PERS_SUB_SELF_LABEL = "Người có thẩm quyền ký Giấy đề nghị đăng ký Hộ kinh doanh"
_PERS_SUB_AUTHORIZED_LABEL = "Người được ủy quyền"


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
        if values.get("DeNghi_ChuHo_LoaiThayDoi"):
            pages["chu-ho-kinh-doanh"].append({
                "name": "ctl00$C$CHANGE_OWNER_TYPE_TITLE_IDFld", "comp": "dom-select",
                "value": values["DeNghi_ChuHo_LoaiThayDoi"],
            })
        if values.get("DeNghi_ChuHo_LyDo"):
            pages["chu-ho-kinh-doanh"].append({
                "name": "ctl00$C$CHANGE_OWNER_TYPE_IDFld", "comp": "dom-select",
                "value": values["DeNghi_ChuHo_LyDo"],
            })
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
    
    # Vai trò người nộp: so khớp nhân thân người nộp với chủ hộ (khi hồ sơ kê khai riêng); hồ sơ
    # không kê khai thì suy từ số lượng CCCD (2+ CCCD ⇒ có người nộp thay). Extension chốt lại
    # theo tài khoản THẬT sau khi bấm "Sao chép thông tin đăng ký tài khoản".
    candidates = _identity_candidates(values)
    has_multiple_cccd = bool(values.get("HasMultipleCCCD", False)) or len(candidates) >= 2
    is_self = _submitter_is_owner(values) is not False and not has_multiple_cccd

    # Tạo page người nộp theo đúng logic của đăng ký kinh doanh
    applicant_page = []
    
    # 1. Radio vai trò
    pers_sub_role = _PERS_SUB_SELF_LABEL if is_self else _PERS_SUB_AUTHORIZED_LABEL
    applicant_page.append({"name": "ctl00$C$PERS_SUBGroup", "comp": "dom-radio", "value": pers_sub_role})

    # 2. Nhân thân người nộp (mặc định là chủ hộ, extension sẽ override nếu là người nộp thay)
    applicant_page.append({
        "name": "ctl00$C$PERSCtl$FULL_NAMEFld", "comp": "dom-input",
        "value": _proper_name(applicant.get("hoTen") or owner.get("hoTen"))
    })
    applicant_page.append({
        "name": "ctl00$C$PERSCtl$DATE_OF_BIRTHFld", "comp": "dom-date",
        "value": applicant.get("ngaySinh") or owner.get("ngaySinh")
    })
    applicant_page.append({
        "name": "ctl00$C$PERSCtl$PERS_DOC_NOFld", "comp": "dom-input",
        "value": applicant.get("soDinhDanh") or owner.get("soDinhDanh")
    })

    # 3. ĐỊA CHỈ người nộp (cổng KHÔNG tự điền khi bấm "Sao chép tài khoản"):
    # - Người nộp là chủ hộ → địa chỉ cá nhân trên ĐƠN.
    # - Người nộp thay      → địa chỉ trên CCCD của chính người đăng nhập, do extension chọn từ
    #   __identityCandidates; không khớp được thẻ nào thì KHÔNG điền.
    self_address = next(
        (value for value in (owner.get("diaChi"), applicant.get("diaChi"))
         if _has_address(value)),
        None,
    )
    if is_self:
        # Dùng creation_mapper.enrich để xử lý địa chỉ đúng cách
        addr_compact = [_compact_field("NguoiNop_DiaChi", self_address)] if self_address else []
        addr_enriched = creation_mapper.enrich(addr_compact, page="nguoi-nop-ho-so")
        # Chỉ lấy field địa chỉ (ADDRCCtl)
        applicant_page.extend(f for f in addr_enriched if "ADDRCCtl" in f.get("name", ""))

    # 4. Extension chốt lại vai trò theo radio THẬT trên cổng (sau khi bấm "Sao chép tài khoản" mới
    # biết tài khoản đăng nhập có phải chủ hộ không) → gửi kèm địa chỉ nhánh "chủ hộ tự nộp".
    from app.pipelines.dang_ky_kinh_doanh.process.mapper import _addr
    applicant_address = {"role": "self" if is_self else "authorized", "self": _addr(self_address)}
    if applicant_address["self"]:
        applicant_page.append({"name": "__applicantAddress", "comp": "raw", "value": applicant_address})

    # 5. Mọi CCCD trong hồ sơ: extension chọn đúng thẻ của người đang đăng nhập rồi ghi đè nhân thân
    # + địa chỉ vào khối người nộp (dữ liệu nút "Sao chép tài khoản" đổ vào không có địa chỉ).
    if candidates:
        applicant_page.append({"name": "__identityCandidates", "comp": "raw", "value": candidates})
    
    pages["nguoi-nop-ho-so"] = applicant_page
    order.append("nguoi-nop-ho-so")

    search_options = [
        ("businessNumber", _digits(values.get("HoKinhDoanh_MaSo"))),
        ("registrationNumber", _digits(values.get("HoKinhDoanh_MaDangKy"))),
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
            "expectedBusinessNumber": _digits(values.get("HoKinhDoanh_MaSo")),
        },
        "nameChange": flags["name"],
        "changeFlags": flags,
        "pageOrder": order,
        "industryChanges": {"add": additions, "remove": removals},
        "identityCandidates": _identity_candidates(values),
    }
    return pages, flow
