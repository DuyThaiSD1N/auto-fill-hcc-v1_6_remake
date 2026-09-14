"""Map compact source facts → Form.io data[...] fields cho thủ tục "Đăng ký hành nghề".

CHỦ HỒ SƠ LÀ CƠ SỞ KHÁM BỆNH, CHỮA BỆNH, ĐI XUỐNG PHẦN II — KHÔNG LÊN PHẦN I. Phần I "Thông tin người nộp
hồ sơ" là tài khoản VNeID đang đăng nhập do cổng tự đổ; mapper không phát ô nhân thân nào của khối đó, chỉ
bỏ tích "Người nộp hồ sơ là chủ hồ sơ" để mở khoá Phần II.

Phần II ghép HAI nguồn theo bảng mapping nghiệp vụ:
  - tên + địa chỉ  ← Danh sách đăng ký hành nghề (cơ sở);
  - ngày sinh, giới tính, CCCD, ngày cấp, nơi cấp ← CCCD người đại diện của cơ sở.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.dang_ky_hanh_nghe.process.schema import UI_COMP_BY_NAME

_CITY_MARKERS = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []):
        return None
    if isinstance(value, dict):
        direct = value.get("fullText") or value.get("full") or value.get("text")
        return _text(direct) if direct else None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(r"^(tỉnh|thành\s*phố|t\.?\s*p\.?)\s+", "", text, flags=re.IGNORECASE).strip()


def _province_label(value: Any) -> str | None:
    """Nhãn option select Tỉnh/Thành phố: "Tỉnh Lai Châu" / "Thành phố Hà Nội"."""
    bare = _strip_admin_prefix(_text(value) or "")
    if not bare:
        return None
    return f"{'Thành phố' if _fold(bare) in _CITY_MARKERS else 'Tỉnh'} {bare}"


def _parse_area_text(value: str) -> dict | None:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip(" .")
    parts = [p.strip(" .") for p in re.split(r"\s*(?:,|;|\s+-\s+)\s*", text) if p.strip(" .")]
    if not parts:
        return None
    out = {"quocGia": "Việt Nam", "tinh": "", "xa": "", "diaChi": ""}
    if len(parts) >= 3:
        out.update(tinh=parts[-1], xa=parts[-2], diaChi=", ".join(parts[:-2]))
    elif len(parts) == 2:
        out.update(tinh=parts[-1], xa=parts[0])
    else:
        out["diaChi"] = parts[0]
    return out


def _area(value: Any) -> dict | None:
    """Parse + remap địa chỉ cơ sở để xã/phường khớp option sau sáp nhập hành chính."""
    if isinstance(value, str):
        out = _parse_area_text(value)
    elif isinstance(value, dict):
        out = {
            "quocGia": value.get("quocGia") or "Việt Nam",
            "tinh": value.get("tinh") or value.get("tỉnh") or "",
            "xa": value.get("xa") or value.get("xã") or value.get("phuong") or "",
            "diaChi": value.get("diaChi") or value.get("chiTiet") or "",
        }
    else:
        return None
    if not out or not any(out.get(k) for k in ("tinh", "xa", "diaChi")):
        return None
    return remap_area(out, allow_diachi_fallback=True)


def _identity(value: Any) -> str | None:
    digits = re.sub(r"\D+", "", _text(value) or "")
    return digits or None


def _date(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", text)
    return normalize_date(m.group(0).replace("-", "/") if m else text) or None


def _gender(value: Any) -> str | None:
    folded = _fold(value)
    if folded in {"nam", "male", "m"}:
        return "Nam"
    if folded in {"nu", "female", "f"}:
        return "Nữ"
    return None


def _same_person(a: Any, b: Any) -> bool:
    """So họ tên bỏ dấu, bỏ khoảng trắng/ký tự lạ — chịu được IN HOA và OCR dính chữ."""
    key_a = re.sub(r"[^a-z]+", "", _fold(a))
    key_b = re.sub(r"[^a-z]+", "", _fold(b))
    return bool(key_a) and key_a == key_b


_NGUOI_DAI_DIEN_FIELDS = (
    "NguoiDaiDien_HoTen",
    "NguoiDaiDien_NgaySinh",
    "NguoiDaiDien_GioiTinh",
    "NguoiDaiDien_SoDinhDanh",
    "NguoiDaiDien_NgayCapCCCD",
    "NguoiDaiDien_NoiCapCCCD",
)


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    context = (options or {}).get("formContext") or {}
    submitter = context.get("applicantFullname") or context.get("fullname") or ""
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    co_so = _text(values.get("CoSo_Ten"))
    nguoi_chiu_tn = _text(values.get("CoSo_NguoiChiuTrachNhiem"))
    dai_dien = _text(values.get("NguoiDaiDien_HoTen"))

    # CHẶN CCCD SAI NGƯỜI (req_bb6d9a7bfd29): hồ sơ có danh sách do Lò Văn Sơn ký + CCCD của người NỘP,
    # LLM vẫn đổ CCCD người nộp vào NguoiDaiDien_* → Phần II mang ngày sinh/số CCCD của người khác.
    # Danh sách đã ghi người chịu trách nhiệm mà CCCD KHÁC tên đó → CCCD không phải của người đại diện,
    # bỏ TOÀN BỘ nhân thân từ CCCD. Không chờ LLM tự tuân prompt.
    rejected_cccd = None
    if dai_dien and nguoi_chiu_tn and not _same_person(dai_dien, nguoi_chiu_tn):
        rejected_cccd = dai_dien
        for key in _NGUOI_DAI_DIEN_FIELDS:
            values.pop(key, None)
        dai_dien = None
    identity = _identity(values.get("NguoiDaiDien_SoDinhDanh"))
    dia_chi = _area(values.get("CoSo_DiaChi"))

    # Bỏ tích "Người nộp hồ sơ là chủ hồ sơ": chủ hồ sơ là cơ sở, không phải tài khoản đang đăng nhập.
    add("data[isOwnerDossierCheck]", False)

    # Tên chủ hồ sơ = tên cơ sở; danh sách không ghi tên cơ sở thì mới lấy người chịu trách nhiệm.
    owner_name = co_so or nguoi_chiu_tn or dai_dien
    add("data[ownerFullname]", owner_name)
    add("data[ownerBirthday]", _date(values.get("NguoiDaiDien_NgaySinh")))
    add("data[ownerGender]", _gender(values.get("NguoiDaiDien_GioiTinh")))
    add("data[ownerIdentityNumber]", identity)
    add("data[ownerIdentityDate]", _date(values.get("NguoiDaiDien_NgayCapCCCD")))
    add("data[ownerIdIssuePlace]", normalize_issuer(values.get("NguoiDaiDien_NoiCapCCCD")) or None)
    if dia_chi:
        add("data[ownerProvince]", _province_label(dia_chi.get("tinh")))
        add("data[ownerDistrict]", _text(dia_chi.get("xa")))
        chi_tiet = _text(dia_chi.get("diaChi"))
        # Danh sách của trạm y tế thường chỉ ghi "xã X, tỉnh Y" (không số nhà/thôn bản) nhưng ô "Địa chỉ chi
        # tiết" là BẮT BUỘC → điền đúng phần địa chỉ danh sách có (tên xã) thay vì để trống chặn nộp.
        if not chi_tiet and _text(dia_chi.get("xa")):
            chi_tiet = _text(dia_chi.get("xa"))
            warnings.append(
                f"Danh sách chỉ ghi địa chỉ cơ sở tới cấp xã — ô Địa chỉ chi tiết đang điền '{chi_tiet}', vui "
                "lòng bổ sung thôn/bản/số nhà nếu có."
            )
        add("data[ownerAddress]", chi_tiet)
    add("data[ownerNation]", "Việt Nam" if owner_name or identity else None)

    if not co_so:
        warnings.append(
            "Không đọc được tên cơ sở khám bệnh, chữa bệnh trong Danh sách đăng ký hành nghề — kiểm tra "
            "lại ô Họ và tên ở mục Thông tin chủ hồ sơ."
        )
    if not dia_chi:
        warnings.append(
            "Không đọc được địa chỉ cơ sở khám bệnh, chữa bệnh — vui lòng chọn Tỉnh/Phường xã và nhập địa "
            "chỉ chi tiết ở mục Thông tin chủ hồ sơ."
        )
    if rejected_cccd:
        warnings.append(
            f"CCCD trong hồ sơ là của {rejected_cccd}, KHÔNG phải người chịu trách nhiệm chuyên môn ghi trên "
            f"danh sách ({nguoi_chiu_tn}) — không dùng CCCD này cho mục Thông tin chủ hồ sơ. Vui lòng tải CCCD "
            f"của {nguoi_chiu_tn} hoặc điền tay ngày sinh, giới tính, số CCCD."
        )
    elif not identity:
        warnings.append(
            "Hồ sơ không có CCCD của người đại diện cơ sở — ngày sinh, giới tính, số CCCD ở mục Thông tin "
            "chủ hồ sơ còn trống, vui lòng điền tay."
        )
    elif not nguoi_chiu_tn and submitter and _same_person(dai_dien, submitter):
        # Danh sách không ghi người chịu trách nhiệm nên không đối chiếu được; CCCD lại trùng tài khoản
        # đang nộp → có thể là CCCD người nộp chứ không phải người đại diện.
        warnings.append(
            f"Danh sách không ghi người chịu trách nhiệm chuyên môn; CCCD đang dùng cho chủ hồ sơ trùng với "
            f"người nộp ({submitter}) — vui lòng kiểm tra đúng là người đại diện cơ sở."
        )
    khac = _text(values.get("CoSo_CacCoSoKhac"))
    if khac and co_so:
        warnings.append(
            f"Hồ sơ có danh sách của nhiều cơ sở; mục Thông tin chủ hồ sơ đang điền theo {co_so}. Các cơ sở "
            f"khác: {khac}."
        )
    warnings.append("Số điện thoại chủ hồ sơ (bắt buộc) không có trong giấy tờ — vui lòng nhập tay.")

    return out, warnings
