"""Thanh tra TÌNH TRẠNG HÔN NHÂN của hai bên nam / nữ (kết hôn có yếu tố nước ngoài): số lần kết hôn, tình trạng và
bản án / quyết định ly hôn. Cùng cách làm với thanh tra kết hôn trong nước (ket_hon/thanh_tra/tinh_trang.py), khác ở
schema: tình trạng là mã chữ ("ly_hon", "goa"), không có danh sách đương sự, form không có khối giấy khai tử.

- Số lần kết hôn: MÃ đọc ô của đúng cột trên hàng "Kết hôn lần thứ mấy" của bảng tờ khai.
- Văn bản ly hôn / giấy khai tử: dùng lại lượt đọc từng trang và cách lập BỘ (số, ngày, cơ quan) của thanh tra giấy hộ
  tịch thủ tục cấp Giấy XNTTHN, rồi MÃ gắn từng bộ với một bên: văn bản ly hôn phải ghi bên đó là đương sự; giấy khai tử
  phải là của người khác giới, không phải một trong hai bên, và bên đó không có văn bản ly hôn riêng, tờ khai không ghi
  kết hôn lần đầu.
- Tình trạng: có văn bản ly hôn / giấy khai tử của đúng bên đó mà lượt trích chưa ghi tình trạng tương ứng → đề xuất.
Hồ sơ không có giấy nào làm căn cứ thì không đề xuất gì (tình trạng do người dân khai tại quầy).
"""

import asyncio
import re
from dataclasses import replace

from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import giay_ho_tich as base

from . import chu_the
from .chu_the import SIDES, Side

RULES = """
<hai_ben>
Mỗi vụ xét MỘT bên (nêu ở tên mục). "Người được cấp" trong các luật dưới đây là BÊN ĐANG XÉT. Mã đã gắn từng giấy với
đúng một bên: văn bản ly hôn ghi bên đó là đương sự; giấy khai tử là của vợ / chồng trước của bên đó. Không lấy văn
bản của bên kia.
</hai_ben>

<so_lan_ket_hon>
Số lần kết hôn lấy ở ô của ĐÚNG CỘT bên đang xét trên hàng "Kết hôn lần thứ mấy" của tờ khai (thứ tự cột theo dòng
tiêu đề "Bên nữ | Bên nam"). Dòng "Tín hiệu mã" ghi ô đó do mã tách cột → chọn B.
</so_lan_ket_hon>

<tinh_trang>
Mã tình trạng: "ly_hon" = đã ly hôn, "goa" = vợ / chồng đã chết. Hồ sơ có bản án / quyết định ly hôn (của Tòa án Việt
Nam hoặc cơ quan nước ngoài) ghi bên đang xét là đương sự → "ly_hon"; có giấy khai tử của vợ / chồng trước của bên đó →
"goa". Không có giấy làm căn cứ → KHONG_DU_CAN_CU.
</tinh_trang>
""" + base.RULES

_DIVORCE_KEYS = ("BanAnLyHon_So", "BanAnLyHon_Ngay", "BanAnLyHon_CoQuan")
_STATUS = {"ly_hon": "ly_hon", "khai_tu": "goa"}
_COUNT_WORDS = {"dau": 1, "nhat": 1, "mot": 1, "hai": 2, "ba": 3, "tu": 4}


def _count(value) -> str:
    return str(int(match.group(0))) if (match := re.search(r"\d+", str(value or ""))) else ""


def _units(side: Side) -> dict[str, Unit]:
    divorce = tuple(replace(spec, name=f"{side.card}_{key}")
                    for spec, key in zip(base._UNIT_BY_MATTER["ly_hon"].fields, _DIVORCE_KEYS))
    return {
        "so_lan": Unit(f"{side.key}.so_lan", f"Số lần kết hôn của {side.label}",
                       (Field(f"{side.card}_SoLanKetHon", "kết hôn lần thứ mấy (số nguyên)", "free", canon=_count),)),
        "tinh_trang": Unit(f"{side.key}.tinh_trang", f"Tình trạng hôn nhân của {side.label}",
                           (Field(f"{side.card}_TinhTrangHonNhan", 'mã tình trạng: "ly_hon" đã ly hôn, "goa" vợ / chồng '
                                  "đã chết", "free", canon=lambda value: fold(value).replace(" ", "_")),)),
        "ly_hon": Unit(f"{side.key}.ly_hon", f"Bản án / quyết định ly hôn của {side.label}: số, ngày, cơ quan", divorce),
    }


UNITS_BY_SIDE = {side.key: _units(side) for side in SIDES}
UNITS = tuple(unit for side in SIDES for unit in UNITS_BY_SIDE[side.key].values())


def _declared_count(cell: str) -> str:
    """Số lần ghi trong một ô của hàng "Kết hôn lần thứ mấy": "lần 1", "02", "Lần đầu", "lần thứ hai"."""
    digits = re.search(r"\d+", cell)
    if digits:
        return str(int(digits.group(0))) if 0 < int(digits.group(0)) < 10 else ""
    words = fold(cell).split()
    return next((str(number) for word, number in _COUNT_WORDS.items() if word in words), "")


def _count_finding(side: Side, case: Case) -> Finding | None:
    name = f"{side.card}_SoLanKetHon"
    for table in chu_the.declaration_tables(case.documents):
        cell, row = chu_the.cell(table, "so_lan", side)
        count = _declared_count(cell)
        if count and count != _count(case.values.get(name)):
            return Finding(INSPECTOR, UNITS_BY_SIDE[side.key]["so_lan"], {name: count}, row, table["doc"],
                           f'ô cột {side.label} của hàng "Kết hôn lần thứ mấy" ghi: {cell}', side.label, backed=True,
                           evidence=(f"mã tách cột theo dòng tiêu đề của bảng tờ khai; ô của {side.label} ghi \"{cell}\"",))
    return None


def _parties(record: dict) -> list[str]:
    return [name.strip() for name in re.split(r"[;,]", record["people"]) if name.strip()]


def _mine(record: dict, side: Side, names: dict[str, str], widowed: bool, eligible: bool) -> bool:
    """Bộ này thuộc về bên đang xét (xem đầu file). ``widowed``: lượt trích ghi bên này góa; ``eligible``: bên này không
    có văn bản ly hôn riêng và tờ khai không ghi kết hôn lần đầu."""
    parties = _parties(record)
    if record["matter"] == "ly_hon":
        return bool(names[side.key]) and any(base._near_name(name, names[side.key]) for name in parties)
    other = any(base._near_name(name, own) for name in parties for own in names.values() if own)
    if record["source"] == "nhac_lai":
        # Dòng nhắc lại không cho biết là lời khai của bên nào: chỉ nhận khi lượt trích đã ghi bên này góa.
        return widowed and not other
    return ((widowed or eligible) and record["gender"] in ("nam", "nu") and record["gender"] != fold(side.gender)
            and bool(parties) and not other)


def _side_findings(side: Side, case: Case, records: list[dict], names: dict[str, str]) -> list[Finding]:
    status_name = f"{side.card}_TinhTrangHonNhan"
    status = fold(case.values.get(status_name)).replace(" ", "_")
    divorced = any(record["matter"] == "ly_hon" and _mine(record, side, names, False, False) for record in records)
    first_time = any(_declared_count(chu_the.cell(table, "so_lan", side)[0]) == "1"
                     for table in chu_the.declaration_tables(case.documents))
    out = []
    for matter in ("ly_hon", "khai_tu"):
        mine = [record for record in records
                if record["matter"] == matter and _mine(record, side, names, status == "goa", not divorced and not first_time)]
        if not mine:
            continue
        quote, doc = mine[0]["line"], mine[0].get("doc", 0)
        if matter == "ly_hon":
            side_case = Case(case.documents, "", {
                "NguoiDuocCap_HoTen": names[side.key], "NguoiDuocCap_GioiTinh": side.gender,
                **{field: case.values.get(f"{side.card}_{key}") for field, key in zip(base.DIVORCE_FIELDS, _DIVORCE_KEYS)}},
                case.options)
            finding = base._finding(base._UNIT_BY_MATTER["ly_hon"], mine, side_case)
            if finding:
                values = {f"{side.card}_{key}": finding.values[field]
                          for field, key in zip(base.DIVORCE_FIELDS, _DIVORCE_KEYS) if field in finding.values}
                out.append(replace(finding, inspector=INSPECTOR, unit=UNITS_BY_SIDE[side.key]["ly_hon"], values=values,
                                   owner=side.label))
                quote, doc = finding.quote, finding.doc
        # Văn bản thật (không phải dòng nhắc lại) của đúng bên đó mà lượt trích chưa ghi tình trạng tương ứng. Tờ khai
        # ghi kết hôn lần đầu thì không đề xuất: mapper chốt "chưa đăng ký kết hôn" theo số lần.
        real = [record for record in mine if record["source"] != "nhac_lai"]
        if real and not first_time and status not in ("ly_hon", "goa") and not any(
                f.unit.key.endswith(".tinh_trang") for f in out):
            what = "bản án / quyết định ly hôn ghi người này là đương sự" if matter == "ly_hon" else (
                "giấy khai tử của vợ / chồng trước")
            out.append(Finding(INSPECTOR, UNITS_BY_SIDE[side.key]["tinh_trang"], {status_name: _STATUS[matter]},
                               quote, doc, f"hồ sơ có {what}", side.label, backed=True,
                               evidence=(f"mã đã gắn giấy này với {side.label}: {what}",)))
    return out


async def find(inspector: Inspector, case: Case, title: str) -> list[Finding]:
    names = {side.key: chu_the.identity(case.values, side)["name"] for side in SIDES}
    findings = [finding for side in SIDES if (finding := _count_finding(side, case))]
    read = await asyncio.gather(*(base._read_page(page, title) for page in base.pages(case)), return_exceptions=True)
    records = [record for answer in read if not isinstance(answer, BaseException) for record in answer]
    for side in SIDES:
        findings += _side_findings(side, case, records, names)
    return findings


_OWNERS = tuple(side.label for side in SIDES)
INSPECTOR = Inspector("tinh_trang", "TÌNH TRẠNG HÔN NHÂN của hai bên nam / nữ", UNITS, RULES,
                      owners=_OWNERS, accepted=_OWNERS, find=find)
