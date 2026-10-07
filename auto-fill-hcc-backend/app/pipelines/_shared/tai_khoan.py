"""Thông tin TÀI KHOẢN đăng nhập cổng (options.formContext) — nguồn chuẩn nhất cho người trùng tài khoản.

Extension đọc dữ liệu VNeID cổng đổ sẵn cho chủ tài khoản (eForm Bộ Tư pháp: API getDataEform). Mọi khoá
đều tuỳ chọn: bản extension cũ chỉ gửi tên + số. Dùng chung cho các thủ tục eForm Bộ Tư pháp (TTHN,
kết hôn...): đọc + chuẩn hoá tài khoản, và xét một khối nhân thân đã điền có phải CHÍNH chủ tài khoản.
"""
from __future__ import annotations

import difflib
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Callable

from app.locations.catalog import names_by_code
from app.monitor import recorder as mon
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date, upper_person_name

ACCOUNT_KEYS = {
    "HoTen": "applicantFullname",
    "SoDinhDanh": "applicantIdentityNumber",
    "NgaySinh": "applicantBirthday",
    "GioiTinh": "applicantGender",
    "DanToc": "applicantEthnicity",
    "NgayCap": "applicantIdDate",
    "NoiCap": "applicantIdIssuer",
    "NoiCuTru": "applicantAddress",
}

_DATA_DIR = Path(__file__).resolve().parent / "data"

CCCD_LEN = 12          # số định danh cá nhân luôn đúng 12 chữ số
ID_OCR_SLIP_MAX = 2    # số chữ số OCR được phép đọc thừa/thiếu so với thẻ
# Hai tên cùng một người mà OCR lệch vài chữ ("Phan Thị Hiền" / "PHẠM THỊ HIỀN") vẫn trên mức này.
SAME_NAME_RATIO = 0.8


def digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def date_key(value) -> tuple | None:
    """dd/mm/yyyy -> tuple so sánh được; sai định dạng trả None (không kết luận)."""
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(value or "").strip())
    if not match:
        return None
    day, month, year = match.groups()
    return (int(year), int(month), int(day))


def fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _is_subsequence(short: str, long: str) -> bool:
    """`short` có phải `long` sau khi XÓA bớt vài ký tự (giữ nguyên thứ tự) không."""
    it = iter(long)
    return all(ch in it for ch in short)


def _is_ocr_slip_of_card(left_digits: str, right_digits: str) -> bool:
    """Hai chuỗi số là CÙNG một số trên thẻ, chỉ khác vì OCR đọc RƠI (hoặc nhân đôi) vài chữ số.

    Tờ khai viết tay hay bị OCR nuốt mất một chữ số: "046175013623" ra "04617503623". Chuỗi thiếu
    số đó không phải số định danh hợp lệ của BẤT KỲ ai (không đủ 12 chữ số), nên coi nó là số của
    một người khác là vô nghĩa — nhưng so bằng `==` thì nó vẫn "khác số" và kéo theo cả mục I:
    tên viết tay sai được giữ lại, ô quan hệ tick "Khác", và ô số định danh nhận 11 chữ số mà cổng
    chắc chắn từ chối.

    Chỉ nhận khi một bên là số thẻ ĐỦ 12 chữ số và chuỗi ngắn hơn nằm gọn trong nó theo đúng thứ
    tự (chỉ XÓA, không đổi chữ số nào) — lệch tối đa 2 chữ số. Ràng buộc này rất chặt: một số 11
    chữ số ngẫu nhiên chỉ có cỡ 12 phần 10^11 cơ hội lọt qua, nên không thể vô tình ghép nhân thân
    của hai người khác nhau. OCR đọc NHẦM chữ số (5 thành 6) vẫn bị coi là khác người như cũ.
    """
    short, long = sorted((left_digits, right_digits), key=len)
    if len(long) != CCCD_LEN or len(short) == CCCD_LEN:
        return False
    if not 0 < len(long) - len(short) <= ID_OCR_SLIP_MAX:
        return False
    return _is_subsequence(short, long)


def id_match(left, right) -> bool | None:
    """Hai số định danh có cùng một người không; thiếu một bên → None (không kết luận)."""
    left_digits, right_digits = digits(left), digits(right)
    if not (left_digits and right_digits):
        return None
    if left_digits == right_digits:
        return True
    return True if _is_ocr_slip_of_card(left_digits, right_digits) else False


def is_one_digit_misread(left, right) -> bool:
    """Hai số 12 chữ số chỉ lệch ĐÚNG MỘT vị trí — dấu hiệu OCR đọc nhầm một chữ số viết tay.

    Cố ý KHÔNG gộp vào `id_match`: ở đó đọc nhầm chữ số vẫn tính là khác người (quyết định quan
    hệ, mượn tên). Hàm này chỉ dùng kèm một bằng chứng độc lập khác (năm sinh / họ) ở chỗ gọi.
    """
    left_digits, right_digits = digits(left), digits(right)
    if len(left_digits) != CCCD_LEN or len(right_digits) != CCCD_LEN:
        return False
    return sum(a != b for a, b in zip(left_digits, right_digits)) == 1


def name_match(left, right) -> bool | None:
    """Hai họ tên có trùng không (bỏ dấu, gộp khoảng trắng); thiếu một bên → None."""
    left_name, right_name = fold(left), fold(right)
    if left_name and right_name:
        return left_name == right_name
    return None


def name_similarity(left, right) -> float:
    left_name, right_name = fold(left), fold(right)
    if not (left_name and right_name):
        return 0.0
    return difflib.SequenceMatcher(None, left_name, right_name).ratio()


@lru_cache(maxsize=None)
def _moj_catalog(name: str) -> dict[str, str]:
    """Danh mục mã → tên của eForm Bộ Tư pháp (dữ liệu VNeID trên cổng lưu dân tộc/giới tính bằng MÃ)."""
    rows = json.loads((_DATA_DIR / name).read_text(encoding="utf-8"))
    return {str(row["Ma"]).strip(): re.sub(r"\s+", " ", str(row["Ten"])).strip() for row in rows}


def _catalog_label(value, catalog: str) -> str:
    """Giá trị là MÃ danh mục thì đổi ra tên; không phải mã thì giữ nguyên chữ."""
    text = str(value or "").strip()
    return _moj_catalog(catalog).get(text, text) if text.isdigit() else text


def _gender_label(value) -> str:
    folded = fold(value)
    if folded in ("nam", "male", "m", "1"):
        return "Nam"
    if folded in ("nu", "female", "f", "0", "2"):
        return "Nữ"
    return ""


def account_context(options: dict | None) -> dict:
    """Thông tin tài khoản từ options.formContext, đã chuẩn hoá; rỗng nếu không có.

    "NoiCuTru" trả object {tinh, xa, diaChi} đã đổi mã danh mục ra tên, CHƯA remap — mỗi mapper tự
    chuẩn hoá theo ô địa chỉ của form mình.
    """
    ctx = (options or {}).get("formContext") or {}
    if not isinstance(ctx, dict):
        return {}
    out = {}
    for key, ctx_key in ACCOUNT_KEYS.items():
        value = ctx.get(ctx_key)
        if key == "NoiCuTru":
            if isinstance(value, dict):
                # Dữ liệu VNeID trên cổng lưu tỉnh/xã bằng MÃ danh mục hành chính.
                tinh, xa = names_by_code(value.get("tinh"), value.get("xa"))
                value = {**value, "tinh": tinh or value.get("tinh"), "xa": xa or value.get("xa")}
                if value.get("tinh") or value.get("xa") or value.get("diaChi"):
                    out[key] = value
            continue
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            continue
        if key == "SoDinhDanh":
            text = digits(text)
        elif key in ("NgaySinh", "NgayCap"):
            text = normalize_date(text)
            if not date_key(text):
                continue
        elif key == "GioiTinh":
            text = _gender_label(_catalog_label(text, "moj_eform_gioi_tinh.json"))
        elif key == "DanToc":
            text = _catalog_label(text, "moj_eform_dan_toc.json")
        elif key == "NoiCap":
            text = normalize_issuer(text)
        if text:
            out[key] = text
    return out


def is_account_person(account: dict, name, id_number, birthday) -> bool:
    """Khối nhân thân (tên, số, ngày sinh đã điền) có phải CHÍNH chủ tài khoản không.

    Số trùng hẳn là đủ (tên lệch là do OCR). Số lệch vì OCR (rơi/thừa chữ số, sai đúng một chữ số)
    phải kèm tên gần giống. Số trên tờ khai viết tay có khi lệch 2–3 chữ số: khi đó cần tên trùng
    (bỏ dấu) VÀ cùng ngày sinh. Khối không có số thì cần tên gần giống VÀ cùng ngày sinh — chỉ giống
    tên thì không đủ vì tên Việt trùng nhau rất nhiều.
    """
    account_id, block_id = account.get("SoDinhDanh"), digits(id_number)
    account_dob, block_dob = date_key(account.get("NgaySinh")), date_key(birthday)
    same_dob = bool(account_dob and block_dob and account_dob == block_dob)
    similarity = name_similarity(account.get("HoTen"), name)
    if account_id and block_id:
        if account_id == block_id:
            return True
        near_id = id_match(account_id, block_id) is True or is_one_digit_misread(account_id, block_id)
        if near_id and similarity >= SAME_NAME_RATIO:
            return True
        return same_dob and name_match(account.get("HoTen"), name) is True
    return same_dob and similarity >= SAME_NAME_RATIO


# Tờ khai kết hôn eForm Bộ Tư pháp (kết hôn, kết hôn có yếu tố nước ngoài, đăng ký lại kết hôn dùng
# chung một mẫu): mỗi bên một bộ ô, hậu tố theo bên.
_MARRIAGE_SIDES = {"BenNam": "Nam", "BenNu": "Nữ"}


def apply_account_marriage(out: list[dict], options: dict | None,
                           make_field: Callable[[str, object], dict | None],
                           area: Callable[[dict], dict | None],
                           id_type: Callable[[str], str]) -> list[dict]:
    """Bên nam/nữ nào là CHÍNH chủ tài khoản thì mọi ô tài khoản có giá trị ghi đè theo tài khoản.

    Bên do giấy tờ quyết định; tài khoản chỉ thay giá trị khi ĐÚNG MỘT bên đã điền trùng người tài
    khoản (`is_account_person`, giới tính tài khoản không trái bên). Dữ liệu VNeID là bản chuẩn
    CSDLQG, còn giấy tờ (nhất là tờ khai viết tay) hay bị OCR đọc sai. Mọi ô bị sửa ghi vào trace.

    ``make_field(name, value)``: dựng field UI theo schema của thủ tục (None nếu form không có ô đó).
    ``area(dict)``: chuẩn hoá địa chỉ theo ô của thủ tục. ``id_type(issuer)``: loại giấy tờ theo nơi cấp.
    """
    account = account_context(options)
    if not (account.get("HoTen") or account.get("SoDinhDanh")):
        return out
    values = {f["name"]: f.get("value") for f in out}
    matched = [
        side for side, gender in _MARRIAGE_SIDES.items()
        if (values.get(f"HoTen{side}") or values.get(f"SoDinhDanh_{side}"))
        and account.get("GioiTinh") in (None, gender)
        and is_account_person(account, values.get(f"HoTen{side}"), values.get(f"SoDinhDanh_{side}"),
                              values.get(f"NgaySinh{side}"))
    ]
    if len(matched) != 1:
        return out
    side = matched[0]

    updates: dict[str, object] = {}
    if account.get("HoTen"):
        updates[f"HoTen{side}"] = upper_person_name(account["HoTen"])
    if account.get("SoDinhDanh"):
        updates[f"SoDinhDanh_{side}"] = account["SoDinhDanh"]
        updates[f"SoGiayToDinhDanh_{side}"] = account["SoDinhDanh"]
    for key, name in (("NgaySinh", f"NgaySinh{side}"), ("DanToc", f"DanToc{side}"),
                      ("NgayCap", f"NgayCapDD_{side}"), ("NoiCap", f"NoiCapDD_{side}")):
        if account.get(key):
            updates[name] = account[key]
    if account.get("NoiCap"):
        updates[f"LoaiGiayToDinhDanh_{side}"] = id_type(account["NoiCap"])
    removed: set[str] = set()
    if account.get("DanToc"):
        # Dân tộc tài khoản lấy từ danh mục của chính cổng → luôn là option có sẵn, bỏ ô "Khác".
        removed |= {f"DanTocKhac{side}", f"NhapDanToc{side}Khac"}
    resident = area(account["NoiCuTru"]) if account.get("NoiCuTru") else None
    if resident:
        updates[f"NoiCuTru_{side}"] = "1"
        updates[f"NoiCuTru_{side}_TrongNuoc"] = resident
        removed.add(f"NoiCuTru_{side}_NuocNgoai")

    changes: list[dict] = []
    result: list[dict] = []
    for f in out:
        name = f["name"]
        if name in removed:
            changes.append({"field": name, "cu": f.get("value"), "moi": None})
            continue
        if name in updates:
            field = make_field(name, updates.pop(name))
            if field is None:
                result.append(f)
                continue
            if field["value"] != f.get("value"):
                changes.append({"field": name, "cu": f.get("value"), "moi": field["value"]})
            f = field
        result.append(f)
    # Ô tài khoản có mà giấy tờ không có (vd dân tộc, ngày cấp): thêm vào cuối khối của bên đó.
    for name, value in updates.items():
        field = make_field(name, value)
        if field is not None:
            result.append(field)
            changes.append({"field": name, "cu": None, "moi": field["value"]})
    if changes:
        mon.output("account_override", {"ben": side, "o": changes})
    return result
