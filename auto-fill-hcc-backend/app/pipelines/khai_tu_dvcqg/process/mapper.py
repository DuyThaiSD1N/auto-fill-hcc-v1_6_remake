"""Map compact facts khai tử sang tờ khai SurveyJS của Cổng DVC quốc gia bản mới.

Chọn nguồn (tờ khai → giấy báo tử → CCCD), phân vai người yêu cầu/người mất và thay giấy báo tử bằng
trích lục khai tử đã có sẵn và đã được kiểm thử ở pipeline "khai-tu". Module này KHÔNG chọn nguồn lại:
gọi mapper "khai-tu" ra bộ field biểu mẫu cũ rồi dịch sang câu hỏi SurveyJS (tên + mã choice của
formJson, xem schema.py). Đổi tên field ở mapper "khai-tu" thì phải sửa phần dịch ở đây;
tests/unit/test_khai_tu_dvcqg.py bắt lỗi này.

- Khối "Thông tin người nộp" + "Kính gửi": cổng tự điền → KHÔNG ghi. Chỉ điền ô quan hệ.
- Khối "Người được đăng ký khai tử", "Giấy báo tử", "Số lượng bản sao": điền.
- Giá trị nào không khớp được danh mục/định dạng của cổng thì BỎ TRỐNG cho cán bộ, không gửi giá
  trị cổng sẽ báo lỗi validate.
"""

import re
import unicodedata
from datetime import date

from app.pipelines._shared.ethnic_normalize import normalize_ethnic
from app.pipelines.khai_tu.process import mapper as khai_tu_mapper
from app.pipelines.khai_tu.process import runner as khai_tu_runner
from app.pipelines.khai_tu_dvcqg.process.schema import (
    DAN_TOC,
    GIOI_TINH,
    LOAI_CU_TRU,
    LOAI_DANG_KY,
    LOAI_GIAY_TO,
    NDK_ADDRESS_FIELDS,
    NOI_CU_TRU,
    QUOC_TICH,
    UI_COMP_BY_NAME,
)

# Số hiệu đầy đủ trên giấy báo tử, vd "Số: 01/UBND-GBT".
_NOTICE_NUMBER_RE = re.compile(r"\bs[ốo]\s*[:.]?\s*(\d{1,6}\s*/\s*[0-9a-zđ][0-9a-zđ.\-/]*)", re.IGNORECASE)
_DATE_RE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b")

# Tên gọi khác của dân tộc → mã danh mục cổng (khóa đã bỏ dấu, bỏ khoảng trắng/gạch nối).
_DAN_TOC_ALIAS = {
    "khmer": "05", "mong": "08", "hmong": "08", "meo": "08", "ede": "12", "jrai": "10",
    "bahnar": "13", "xodang": "14", "koho": "16", "kho": "16", "stieng": "22", "katu": "26",
    "kmu": "29", "khmu": "29", "taoi": "31", "bru": "23", "vankieu": "23",
}


def _compact(value) -> str:
    """Bỏ dấu, lowercase, bỏ mọi ký tự không phải chữ/số: "Khơ-me" ≡ "khome", "H'Mông" ≡ "hmong"."""
    text = unicodedata.normalize("NFD", str(value or "").replace("Đ", "D").replace("đ", "d"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _snap(table: dict, label, aliases: dict | None = None) -> tuple[str, str] | None:
    """(code, nhãn danh mục) khớp đúng nhãn; không khớp chắc thì None."""
    key = _compact(label)
    if not key:
        return None
    for code, text in table.items():
        if _compact(text) == key:
            return code, text
    code = (aliases or {}).get(key)
    return (code, table[code]) if code else None


def _ngay(value) -> str:
    """Theo regex của cổng: dd/mm/yyyy | mm/yyyy | yyyy, có số 0 đứng trước."""
    text = str(value or "").strip()
    full = _DATE_RE.search(text)
    if full:
        day, month, year = full.groups()
        return f"{int(day):02d}/{int(month):02d}/{year}"
    month_year = re.search(r"(?<!\d)(\d{1,2})[/\-.](\d{4})(?!\d)", text)
    if month_year:
        return f"{int(month_year.group(1)):02d}/{month_year.group(2)}"
    year = re.search(r"(?<!\d)(1[89]\d{2}|20\d{2})(?!\d)", text)
    return year.group(1) if year else ""


def _full_date(value) -> str:
    text = _ngay(value)
    return text if re.fullmatch(r"\d{2}/\d{2}/\d{4}", text) else ""


def _iso(ddmmyyyy: str) -> str:
    day, month, year = ddmmyyyy.split("/")
    return f"{year}-{month}-{day}"


# Tiêu đề giấy tờ chứng minh sự kiện chết thay giấy báo tử (đứng riêng một dòng trên OCR đã bỏ dấu).
_DEATH_PROOF_TITLE_RE = re.compile(r"(?m)^[^a-z0-9\n]*(bien ban xac minh|ban cam doan)\b")
# Luật Hộ tịch Đ.33: đăng ký khai tử trong 15 ngày kể từ ngày có người chết.
_DUNG_HAN_NGAY = 15


def _fold_lines(text) -> str:
    folded = unicodedata.normalize("NFD", str(text or "").replace("Đ", "D").replace("đ", "d"))
    folded = "".join(ch for ch in folded if unicodedata.category(ch) != "Mn").lower()
    return "\n".join(line.strip() for line in folded.splitlines())


def _loai_dang_ky(legacy_code: str, from_declaration: bool, ngay_mat, has_notice: bool, ocr_text: str,
                  today: date | None = None) -> tuple[str, bool]:
    """(mã loại đăng ký, có phải suy luận không).

    Tờ khai ghi rõ thì theo tờ khai. Không ghi thì suy: không có giấy báo tử mà có biên bản xác minh /
    bản cam đoan → người chết đã lâu (5); đủ ngày mất → trong 15 ngày là đúng hạn (1), quá là quá hạn (4).
    Mapper cũ mặc định luôn "1" — sai với hồ sơ người chết đã lâu.
    """
    if legacy_code in LOAI_DANG_KY and from_declaration:
        return legacy_code, False
    if not has_notice and _DEATH_PROOF_TITLE_RE.search(_fold_lines(ocr_text)):
        return "5", True
    text = _full_date(ngay_mat)
    if text:
        day, month, year = (int(part) for part in text.split("/"))
        try:
            died = date(year, month, day)
        except ValueError:
            died = None
        if died:
            elapsed = ((today or date.today()) - died).days
            return ("1" if 0 <= elapsed <= _DUNG_HAN_NGAY else "4"), True
    return (legacy_code if legacy_code in LOAI_DANG_KY else "1"), True


def _so_nguyen(value) -> str:
    text = str(value or "").strip()
    return str(int(text)) if text.isdigit() else ""


def _death_notice_number(number, ocr_text: str) -> str:
    """Số hiệu đầy đủ của giấy báo tử ("01/UBND-GBT").

    Prompt "khai-tu" chỉ lấy phần số đầu vì biểu mẫu cũ chỉ nhận số. Ô của cổng mới là ô chữ, nên tìm
    lại trên OCR số hiệu có cùng phần số đầu; không thấy thì giữ giá trị agent trả. Bỏ qua số trích lục
    khai tử (TLKT) vì đó không phải giấy báo tử.
    """
    raw = " ".join(str(number or "").split())
    if not raw or not raw.isdigit():
        return raw
    for match in _NOTICE_NUMBER_RE.finditer(ocr_text or ""):
        full = re.sub(r"\s+", "", match.group(1)).rstrip(".-/")
        if int(re.match(r"\d+", full).group()) == int(raw) and "tlkt" not in full.lower():
            return full
    return raw


def _noi_chet(lua_chon, area) -> dict:
    """{luaChon, quocGia, tinh, xa, diaChi} cho comp "sv-diachi" của nơi chết, bỏ khóa rỗng."""
    value = {"luaChon": NOI_CU_TRU.get(str(lua_chon or ""), "")}
    if isinstance(area, dict):
        for key in ("quocGia", "tinh", "xa", "diaChi"):
            value[key] = str(area.get(key) or "").strip()
    return {key: text for key, text in value.items() if text}


def translate(legacy_fields: list[dict], ocr_text: str = "") -> list[dict]:
    """Dịch output mapper "khai-tu" sang câu hỏi SurveyJS, theo đúng thứ tự cần điền."""
    legacy = {
        item["name"]: item
        for item in legacy_fields
        if item.get("value") not in (None, "", {}, [])
    }
    out: list[dict] = []

    def value(name: str):
        return (legacy.get(name) or {}).get("value")

    def is_default(*names: str) -> bool:
        return any((legacy.get(name) or {}).get("default") for name in names)

    def add(name: str, val, *, code: str | None = None, default: bool = False) -> None:
        if val in (None, "", {}, []):
            return
        item = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": val}
        if code:
            item["code"] = code
        if default:
            item["default"] = True  # extension tô viền vàng để cán bộ rà
        out.append(item)

    def add_choice(name: str, snapped: tuple[str, str] | None, *, default: bool = False) -> None:
        if snapped:
            add(name, snapped[1], code=snapped[0], default=default)

    def add_date(name: str, raw) -> None:
        text = _full_date(raw)
        if text:
            add(name, text, code=_iso(text))

    # ===== Người nộp: chỉ ô quan hệ =====
    add("citizenmoiquanhe", value("QuanHe"))

    # ===== NGƯỜI ĐƯỢC ĐĂNG KÝ KHAI TỬ =====
    # Ba ô tra cứu CSDL dân cư đi đầu: cổng tra được thì tự đổ + khóa các ô bên dưới.
    add("citizenNDK_HoVaTen", value("HoTen"), default=is_default("HoTen"))
    so_dinh_danh = re.sub(r"\D", "", str(value("SoDinhDanh") or ""))
    if len(so_dinh_danh) == 12:  # regex của cổng chỉ nhận 12 số
        add("citizenNDK_SoDinhDanh", so_dinh_danh, default=is_default("SoDinhDanh"))
    add("citizenNDK_NgaySinh", _ngay(value("NgaySinh")), default=is_default("NgaySinh"))

    add_choice("citizenGioitinh_NgdcKT", _snap(GIOI_TINH, value("GioiTinh")), default=is_default("GioiTinh"))
    dan_toc = value("nktDanToc")
    add_choice(
        "citizenDantoc_NgdcKT",
        _snap(DAN_TOC, dan_toc, _DAN_TOC_ALIAS) or _snap(DAN_TOC, normalize_ethnic(dan_toc), _DAN_TOC_ALIAS),
    )
    quoc_tich = value("nktQuocTich")
    if quoc_tich:
        add("citizenQuoctich_NgdcKT", quoc_tich, code=(_snap(QUOC_TICH, quoc_tich) or (None,))[0])
    add_choice(
        "citizenLoaiGiaytotuythan_NgdcKT",
        _snap(LOAI_GIAY_TO, value("LoaiGiayToDinhDanh")),
        default=is_default("LoaiGiayToDinhDanh"),
    )
    add("citizenSogiaytotuythan_NgdcKT", value("SoGiayToDinhDanh"), default=is_default("SoGiayToDinhDanh"))
    add_date("citizenField19", value("NgayCapDD"))
    add("citizenNoicapgiaytotuythan_NgdcKT", value("NoiCapDD"))
    add("citizenField56", _ngay(value("NgayMat")))
    add("citizenGiomat", _so_nguyen(value("GioMat")))
    add("citizenPhutmat", _so_nguyen(value("PhutMat")))
    loai_dang_ky, suy_luan = _loai_dang_ky(
        str(value("loaiDangKy") or ""),
        bool(value("loaiDangKy")) and not is_default("loaiDangKy"),
        value("NgayMat"),
        bool(value("gbtLoai")),
        ocr_text,
    )
    add("citizenNDKLoaidangky", LOAI_DANG_KY[loai_dang_ky], code=loai_dang_ky, default=suy_luan)

    # Nơi cư trú cuối cùng: loại cư trú + radio quyết định cụm ô địa chỉ nào hiện ra, nên đi trước.
    # Loại cư trú không in trên giấy tờ nào: mặc định của mapper cũ, tô vàng.
    loai_cu_tru = _snap(LOAI_CU_TRU, value("nktLoaiCuTru"))
    add_choice("citizenNDKLoaicutru", loai_cu_tru, default=True)
    noi_cu_tru = str(value("nktNoiCuTru") or "")
    if noi_cu_tru in NOI_CU_TRU:
        area = value("nktNoiCuTru_TrongNuoc") or {}
        area_default = is_default("nktNoiCuTru", "nktNoiCuTru_TrongNuoc")
        add("citizenNDKnoicutru", NOI_CU_TRU[noi_cu_tru], code=noi_cu_tru, default=area_default)
        if noi_cu_tru == "1":
            tinh, xa, dia_chi = NDK_ADDRESS_FIELDS[loai_cu_tru[0] if loai_cu_tru else "1"]
            add(tinh, str(area.get("tinh") or "").strip(), default=area_default)
            add(xa, str(area.get("xa") or "").strip(), default=area_default)
            add(dia_chi, str(area.get("diaChi") or "").strip(), default=area_default)
        else:
            quoc_gia = str(area.get("quocGia") or "").strip()
            add("citizenNDKQG_Khac", quoc_gia, code=(_snap(QUOC_TICH, quoc_gia) or (None,))[0],
                default=area_default)
            add("citizenNDKDiaChi_Khac", str(area.get("diaChi") or "").strip(), default=area_default)

    if value("nktNoiChet"):
        add(
            "citizenNoichet",
            _noi_chet(value("nktNoiChet"), value("nktNoiChet_TrongNuoc")),
            default=is_default("nktNoiChet", "nktNoiChet_TrongNuoc"),
        )
    add("citizenNguyennhanchet_NgdcKT", value("NguyenNhanMat"))

    # ===== Giấy báo tử (hoặc trích lục khai tử thay thế) =====
    if value("gbtLoai"):
        add("citizenLoaigiaybaotu", value("gbtLoai"))
        add("citizenSogiaybaotu_NgdcKT", _death_notice_number(value("gbtSo"), ocr_text))
        add_date("citizenNgaythangnamcapgiaybaotu", value("gbtNgay"))
        add("citizenCoquancapgiaybaotucochuthichneukhongcothidetrong", value("gbtCoQuanCap"))

    # ===== Số lượng bản sao: bắt buộc, cổng ghi "điền 0 nếu không cần" =====
    copy_request = value("CapBanSao")
    if copy_request == "Có" and _so_nguyen(value("SoLuong")):
        add("citizenSoluongbansaonguoiyeucaudenghi", _so_nguyen(value("SoLuong")))
    else:
        # Không đọc được yêu cầu bản sao thì vẫn điền 0 cho qua ô bắt buộc, tô vàng để cán bộ rà.
        add("citizenSoluongbansaonguoiyeucaudenghi", "0", default=copy_request != "Không")
    return out


def enrich(
    fields: list[dict],
    options: dict | None = None,
    *,
    reasoning_context: str = "",
    ocr_text: str = "",
) -> list[dict]:
    """Compact facts → field SurveyJS: qua mapper "khai-tu" (kể cả trích lục thay giấy báo tử) rồi dịch."""
    legacy = khai_tu_mapper.enrich(fields, options, reasoning_context=reasoning_context)
    legacy = khai_tu_runner._fill_death_extract_substitute(legacy, ocr_text)
    return translate(legacy, ocr_text)
