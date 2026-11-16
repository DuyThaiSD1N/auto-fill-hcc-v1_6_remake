"""Thanh tra TÌNH TRẠNG HÔN NHÂN của hai bên nam / nữ: số lần kết hôn, tình trạng, và chi tiết của tình trạng đó
(bản án / quyết định ly hôn; giấy khai tử của vợ / chồng trước).

- Số lần kết hôn: MÃ đọc ô của đúng cột trên hàng "Kết hôn lần thứ mấy" của bảng tờ khai.
- Chi tiết ly hôn / khai tử: dùng lại lượt đọc từng trang và cách lập BỘ (số, ngày, cơ quan) theo thứ bậc nguồn của
  thanh tra giấy hộ tịch thủ tục cấp Giấy XNTTHN, rồi MÃ gắn từng bộ với một bên: văn bản ly hôn phải ghi bên đó là
  đương sự; giấy khai tử phải là của người khác giới, không phải một trong hai bên — hồ sơ kết hôn kèm giấy khai tử
  của một người như vậy thì đó là vợ / chồng trước của bên khác giới với người chết, trừ khi bên đó có văn bản ly hôn
  riêng hoặc tờ khai ghi bên đó kết hôn lần đầu.
- Tình trạng: có văn bản ly hôn / giấy khai tử của đúng bên đó mà lượt trích chưa ghi tình trạng tương ứng → đề xuất;
  lượt trích ghi "đã ly hôn" mà hồ sơ không có văn bản ly hôn của bên đó, chỉ có giấy khai tử → đề xuất "đã chết".
Hồ sơ không có giấy nào làm căn cứ thì không đề xuất gì (tình trạng do người dân khai tại quầy).
"""

import asyncio
import re
from dataclasses import replace

from app.pipelines._shared.thanh_tra.ho_so import Case, Field, Finding, Inspector, Unit, fold
from app.pipelines.xac_nhan_tthn_dvc_moi.thanh_tra import giay_ho_tich as base

from ..process import mapper
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
Mã tình trạng: "3" = đã ly hôn, "4" = vợ / chồng đã chết. Hồ sơ có bản án / quyết định ly hôn ghi bên đang xét là đương
sự → "3"; có giấy khai tử của vợ / chồng trước của bên đó → "4". Không có giấy làm căn cứ → KHONG_DU_CAN_CU. Dòng
ghi gộp "đã ly hôn hoặc góa" không cho biết là ly hôn hay góa: A ghi "3" chỉ theo dòng đó mà hồ sơ không có văn bản ly
hôn của bên đang xét, có giấy khai tử của vợ / chồng trước → "4".
</tinh_trang>
""" + base.RULES

_DIVORCE_KEYS = ("BanAnLyHon_So", "BanAnLyHon_Ngay", "BanAnLyHon_CoQuan")
_DEATH_KEYS = ("KhaiTu_So", "KhaiTu_Ngay", "KhaiTu_CoQuan")
_STATUS = {"ly_hon": "3", "khai_tu": "4"}
_COUNT_WORDS = {"dau": 1, "nhat": 1, "mot": 1, "hai": 2, "ba": 3, "tu": 4}


def _count(value) -> str:
    return str(int(match.group(0))) if (match := re.search(r"\d+", str(value or ""))) else ""


def _units(side: Side) -> dict[str, Unit]:
    def renamed(matter: str, keys: tuple[str, ...], label: str) -> Unit:
        fields = tuple(replace(spec, name=f"{side.card}_{key}") for spec, key in zip(base._UNIT_BY_MATTER[matter].fields, keys))
        return Unit(f"{side.key}.{matter}", f"{label} của {side.label}: số, ngày, cơ quan", fields)

    return {
        "so_lan": Unit(f"{side.key}.so_lan", f"Số lần kết hôn của {side.label}",
                       (Field(f"{side.card}_SoLanKetHon", "kết hôn lần thứ mấy (số nguyên)", "free", canon=_count),)),
        "tinh_trang": Unit(f"{side.key}.tinh_trang", f"Tình trạng hôn nhân của {side.label}",
                           (Field(f"{side.card}_TinhTrangHonNhan", 'mã tình trạng: "3" đã ly hôn, "4" vợ / chồng đã chết',
                                  "free", canon=lambda value: str(value or "").strip()),)),
        "ly_hon": renamed("ly_hon", _DIVORCE_KEYS, "Bản án / quyết định ly hôn"),
        "khai_tu": renamed("khai_tu", _DEATH_KEYS, "Giấy khai tử của vợ / chồng trước"),
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
    """Bộ này thuộc về bên đang xét (xem đầu file). ``widowed``: lượt trích ghi bên này có vợ / chồng chết;
    ``eligible``: bên này không có văn bản ly hôn riêng và tờ khai không ghi kết hôn lần đầu."""
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
    status = str(case.values.get(status_name) or "").strip()
    divorced = any(record["matter"] == "ly_hon" and _mine(record, side, names, False, False) for record in records)
    first_time = any(_declared_count(chu_the.cell(table, "so_lan", side)[0]) == "1"
                     for table in chu_the.declaration_tables(case.documents))
    out = []
    for matter, keys in (("ly_hon", _DIVORCE_KEYS), ("khai_tu", _DEATH_KEYS)):
        mine = [record for record in records
                if record["matter"] == matter and _mine(record, side, names, status == "4", not divorced and not first_time)]
        if not mine:
            continue
        fields = base.DIVORCE_FIELDS if matter == "ly_hon" else base.DEATH_FIELDS
        side_case = Case(case.documents, "", {
            "NguoiDuocCap_HoTen": names[side.key], "NguoiDuocCap_GioiTinh": side.gender,
            **{field: case.values.get(f"{side.card}_{key}") for field, key in zip(fields, keys)}}, case.options)
        finding = base._finding(base._UNIT_BY_MATTER[matter], mine, side_case)
        if not finding:
            continue
        values = {f"{side.card}_{key}": finding.values[field] for field, key in zip(fields, keys) if field in finding.values}
        if matter == "ly_hon":
            # Mapper chỉ điền khối ly hôn khi danh sách đương sự của văn bản có tên bên đó.
            people = next((record["people"] for record in mine if record["line"] == finding.quote and record["people"]),
                          next((record["people"] for record in mine if record["people"]), ""))
            if people:
                # Tên bên đó lượt trích đọc lệch một chữ so với văn bản (mã đã nhận là cùng người) → ghi kèm tên đang
                # dùng, để bước đối chiếu đương sự của mapper không bỏ khối ly hôn.
                listed = people.replace(",", ";")
                if not mapper._divorce_party_matches(names[side.key], listed):
                    listed = f"{listed}; {names[side.key]}"
                values[f"{side.card}_BanAnLyHon_DuongSu"] = listed
            # Văn bản lượt trích đang gán cho bên này ghi đương sự là người khác (văn bản của bên kia, hồ sơ có hai
            # văn bản ly hôn), còn văn bản của B ghi đúng bên này: mã có căn cứ nghiêng về B.
            assigned = case.values.get(f"{side.card}_BanAnLyHon_DuongSu")
            if people and assigned and not mapper._divorce_party_matches(names[side.key], assigned):
                finding = replace(finding, backed=True, evidence=(
                    f"văn bản đang gán cho {side.label} ghi đương sự \"{assigned}\", không có {side.label}; văn bản "
                    f"của B ghi {side.label} là đương sự", *finding.evidence))
        out.append(replace(finding, inspector=INSPECTOR, unit=UNITS_BY_SIDE[side.key][matter], values=values,
                           owner=side.label))
        # Văn bản thật (không phải dòng nhắc lại) của đúng bên đó mà lượt trích chưa ghi tình trạng tương ứng.
        real = [record for record in mine if record["source"] != "nhac_lai"]
        # Lượt trích ghi "đã ly hôn" mà hồ sơ không có văn bản ly hôn nào của bên này, chỉ có giấy khai tử.
        unbacked_divorce = matter == "khai_tu" and status == "3" and not divorced
        if real and (status not in ("3", "4") or unbacked_divorce) and not any(
                f.unit.key.endswith(".tinh_trang") for f in out):
            what = "bản án / quyết định ly hôn ghi người này là đương sự" if matter == "ly_hon" else (
                "giấy khai tử của vợ / chồng trước")
            out.append(Finding(INSPECTOR, UNITS_BY_SIDE[side.key]["tinh_trang"], {status_name: _STATUS[matter]},
                               finding.quote, finding.doc, f"hồ sơ có {what}", side.label, backed=True,
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


def check(unit: Unit, values: dict, case: Case) -> str:
    if unit.key.endswith(".ly_hon"):
        side = next(side for side in SIDES if unit.key.startswith(side.key + "."))
        people = values.get(f"{side.card}_BanAnLyHon_DuongSu")
        if not mapper._divorce_party_matches(chu_the.identity(case.values, side)["name"], people):
            return f"danh sách đương sự của văn bản không có {side.label}"
    return ""


_OWNERS = tuple(side.label for side in SIDES)
INSPECTOR = Inspector("tinh_trang", "TÌNH TRẠNG HÔN NHÂN của hai bên nam / nữ", UNITS, RULES, check=check,
                      owners=_OWNERS, accepted=_OWNERS, find=find)
