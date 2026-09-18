"""Map compact facts khai tử sang biểu mẫu liên thông khai tử (Angular, formcontrolname).

Chọn nguồn (tờ khai → giấy báo tử → CCCD) và phân vai người yêu cầu/người mất đã có sẵn và đã
được kiểm thử ở mapper của "khai-tu". Module này KHÔNG chọn nguồn lại: gọi mapper đó ra bộ field
biểu mẫu cũ rồi dịch sang tên field liên thông. Đổi tên field ở mapper "khai-tu" thì phải sửa
phần dịch ở đây; tests/unit/test_khai_tu_lien_thong.py bắt lỗi này.

Phạm vi bám ĐÚNG mapping BA "126_Liên thông khai tử- Quảng ngãi" (file "Người có công" là bản đủ
nhất, 109 dòng). Quy tắc: dòng nào BA ghi nguồn là giấy tờ (CCCD / Tờ khai / Giấy báo tử) thì điền;
dòng ghi "Tự chọn" mà BA có giá trị mặc định thì điền mặc định và đánh dấu để cán bộ rà; dòng ghi
"Tự nhập" hoặc "Không có trong giấy tờ đã cung cấp" thì KHÔNG điền.

- PHẦN I người yêu cầu (dòng 1-12): KHÔNG ghi đè — cổng đã đổ sẵn từ tài khoản đăng nhập (CSDL dân
  cư), chính xác hơn OCR. Chỉ chọn "Quan hệ với người chết" (ô cổng để trống).
- PHẦN II người được khai tử (dòng 15-44): điền. Ba ô tick BA ghi "Tự chọn"/"Không tick" nên bỏ.
- PHẦN III chủ hộ (dòng 45-49): sao họ tên + số định danh từ khối người yêu cầu trên trang; quan hệ
  của người được khai tử với chủ hộ suy ngược từ quan hệ trên tờ khai (mẹ khai cho con → "Con").
- PHẦN IV-A "Hưởng theo luật BHXH" (dòng 50-78): BA đã bỏ khỏi phạm vi (2026-09-14).
- PHẦN IV-B/IV-C (dòng 79-109): tick "Là người yêu cầu" để cổng tự chuyển danh tính người nhận mai
  táng phí, thêm quan hệ với người chết và hai ô quốc gia mặc định. Đối tượng bảo trợ/người có công,
  quyết định trợ cấp, thời gian và nơi mai táng, quê quán: BA ghi không có trong giấy tờ nên bỏ.
"""

import re
import unicodedata

from app.pipelines._shared.ethnic_normalize import normalize_ethnic
from app.pipelines.khai_tu.process import mapper as khai_tu_mapper
from app.pipelines.khai_tu_lien_thong.process.schema import UI_COMP_BY_NAME

# Số hiệu đầy đủ trên giấy báo tử, vd "Số: 01/UBND-GBT".
_NOTICE_NUMBER_RE = re.compile(r"\bs[ốo]\s*[:.]?\s*(\d{1,6}\s*/\s*[0-9a-zđ][0-9a-zđ.\-/]*)", re.IGNORECASE)
_DATE_RE = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b")


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _split_name(full_name) -> tuple[str, str, str]:
    """Form tách 3 ô: Họ = tiếng đầu, Tên = tiếng cuối, Chữ đệm = phần giữa."""
    parts = str(full_name or "").split()
    if not parts:
        return "", "", ""
    if len(parts) == 1:
        return "", "", parts[0]
    return parts[0], " ".join(parts[1:-1]), parts[-1]


def _full_date(value) -> str:
    """Ô ngày để định dạng mặc định Ngày/Tháng/Năm; nguồn chỉ có năm thì để cán bộ tự đổi định dạng."""
    match = _DATE_RE.search(str(value or ""))
    if not match:
        return ""
    day, month, year = match.groups()
    return f"{int(day):02d}/{int(month):02d}/{year}"


def _ngay_hoac_nam(value) -> str:
    """Giấy tờ ghi đủ ngày thì trả dd/mm/yyyy; chỉ có tháng/năm hay năm thì trả đúng phần đọc được.

    Ô "ngaysinh" của cổng có mat-select định dạng nên vẫn điền được; trước đây bỏ trống hoàn toàn.
    """
    text = str(value or "").strip()
    du_ngay = _DATE_RE.search(text)
    if du_ngay:
        day, month, year = du_ngay.groups()
        return f"{int(day):02d}/{int(month):02d}/{year}"
    thang_nam = re.search(r"(?<!\d)(\d{1,2})[/\-.](\d{4})(?!\d)", text)
    if thang_nam:
        return f"{int(thang_nam.group(1)):02d}/{thang_nam.group(2)}"
    nam = re.search(r"(?<!\d)(1[89]\d{2}|20\d{2})(?!\d)", text)
    return nam.group(1) if nam else ""


def _thoi_diem_chet(ngay, gio, phut) -> str:
    """BA dòng 31 yêu cầu cả giờ phút: "18 giờ 15 phút, ngày 01/08/2026".

    Có đủ ngày + giờ + phút thì trả "dd/mm/yyyy HH:MM" để extension chọn định dạng
    "Ngày/Tháng/Năm giờ:phút"; thiếu giờ thì giữ nguyên phần ngày đọc được.
    """
    ngay_chuan = _ngay_hoac_nam(ngay)
    gio_text, phut_text = str(gio or "").strip(), str(phut or "").strip()
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", ngay_chuan) and gio_text.isdigit() and phut_text.isdigit():
        return f"{ngay_chuan} {int(gio_text):02d}:{int(phut_text):02d}"
    return ngay_chuan


def _form_area(value) -> dict | None:
    """{tinh, xa, diaChi} cho app-input type="diachi".

    Extension gõ tên rồi chọn option CHỨA chuỗi đã gõ, nên bỏ tiền tố đơn vị hành chính: gõ
    "Tỉnh Quảng Ngãi" sẽ trượt khi danh mục chỉ ghi "Quảng Ngãi".
    """
    if not isinstance(value, dict):
        return None
    tinh = re.sub(r"^(tỉnh|thành phố|tp\.?)\s+", "", str(value.get("tinh") or "").strip(), flags=re.IGNORECASE)
    xa = re.sub(r"^(xã|phường|thị trấn|đặc khu|tt\.?)\s+", "", str(value.get("xa") or "").strip(), flags=re.IGNORECASE)
    area = {"tinh": tinh.strip(), "xa": xa.strip(), "diaChi": str(value.get("diaChi") or "").strip()}
    area = {key: text for key, text in area.items() if text}
    return area if area.get("tinh") or area.get("xa") else None


def _death_notice_number(number, ocr_text: str) -> str:
    """Số hiệu đầy đủ của giấy báo tử ("01/UBND-GBT" theo mẫu BA).

    Prompt "khai-tu" chỉ lấy phần số đầu vì biểu mẫu cũ chỉ nhận số. Biểu mẫu liên thông ghi đủ số
    hiệu, nên tìm lại trên OCR số hiệu có cùng phần số đầu; không thấy thì giữ giá trị agent trả.
    Bỏ qua số trích lục khai tử (TLKT) vì đó không phải giấy báo tử.
    """
    raw = " ".join(str(number or "").split())
    if not raw or _digits(raw) != raw:
        return raw
    for match in _NOTICE_NUMBER_RE.finditer(ocr_text or ""):
        full = re.sub(r"\s+", "", match.group(1)).rstrip(".-/")
        if int(re.match(r"\d+", full).group()) == int(raw) and "tlkt" not in _fold(full):
            return full
    return raw


# Quan hệ NGƯỜI YÊU CẦU với người chết (đọc trên tờ khai) → quan hệ NGƯỜI CHẾT với người yêu cầu.
# Dùng cho ô "Mối quan hệ của người được khai tử với chủ hộ" khi chủ hộ chính là người kê khai:
# tờ khai ghi "Mẹ" (mẹ khai cho con) thì người chết là "Con". Nhãn lấy đúng danh mục của cổng.
_QUAN_HE_NGUOC = {
    ("cha", "bo", "ba", "tia", "cha de", "cha nuoi", "me", "me de", "me nuoi"): "Con",
    ("vo",): "Chồng",
    ("chong",): "Vợ",
    ("ong", "ong noi", "ong ngoai", "ba", "ba noi", "ba ngoai"): "Cháu",
    ("anh", "anh ruot", "chi", "chi ruot"): "Em",
}
# Nhóm phải nhìn giới tính NGƯỜI CHẾT mới chốt được nhãn.
_QUAN_HE_NGUOC_THEO_GIOI = {
    ("con", "con de", "con nuoi", "con dau", "con re"): ("Cha", "Mẹ"),
    ("chau", "chau noi", "chau ngoai"): ("Ông", "Bà"),
    ("em", "em ruot"): ("Anh", "Chị"),
}


def _quan_he_nguoc(quan_he, gioi_tinh_nguoi_mat) -> str:
    """Trả nhãn trong danh mục của cổng; không chắc thì trả rỗng, KHÔNG đoán."""
    khoa = _fold(quan_he)
    if not khoa:
        return ""
    for cac_khoa, nhan in _QUAN_HE_NGUOC.items():
        if khoa in cac_khoa:
            return nhan
    gioi = _fold(gioi_tinh_nguoi_mat)
    for cac_khoa, (nam, nu) in _QUAN_HE_NGUOC_THEO_GIOI.items():
        if khoa in cac_khoa:
            if gioi.startswith("nam"):
                return nam
            if gioi.startswith("nu"):
                return nu
            return ""  # thiếu giới tính người chết thì không chốt được
    return ""


def enrich(
    fields: list[dict],
    options: dict | None = None,
    *,
    reasoning_context: str = "",
    ocr_text: str = "",
) -> list[dict]:
    """Dịch output mapper "khai-tu" sang field biểu mẫu liên thông, theo đúng thứ tự trên form."""
    values = {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}
    # Field "default" của mapper cũ là giá trị giữ chỗ cho biểu mẫu cũ ("NGƯỜI YÊU CẦU", địa chỉ chỉ
    # có quốc gia...), không phải dữ kiện giấy tờ.
    legacy = {
        item["name"]: item["value"]
        for item in khai_tu_mapper.enrich(fields, options, reasoning_context=reasoning_context)
        if not item.get("default")
    }
    out: list[dict] = []

    def add(name: str, value, default: bool = False, sao_tu: str = "") -> None:
        """`sao_tu` = tên ô trên trang để extension sao giá trị sang (khi giấy tờ không có dữ liệu)."""
        if not sao_tu and value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME[name]
        if isinstance(comp, tuple):
            comp = comp[1] if sao_tu else comp[0]
        item = {"name": name, "comp": comp, "value": {"tu": sao_tu} if sao_tu else value}
        if default:
            item["default"] = True  # extension tô viền vàng để cán bộ rà
        out.append(item)

    # ===== PHẦN I: người yêu cầu (BA dòng 1-12) =====
    # Cổng đã đổ sẵn khối này từ tài khoản đăng nhập (CSDL dân cư) — chuẩn hơn OCR và có thể lệch
    # dấu so với giấy tờ, nên KHÔNG ghi đè. Chỉ chọn quan hệ với người chết, ô cổng để trống.
    quan_he = legacy.get("QuanHe")
    add("NycQuanHe", quan_he)

    ho, chu_dem, ten = _split_name(legacy.get("HoTen"))
    add("NdktHo", ho)
    add("NdktChuDem", chu_dem)
    add("NdktTen", ten)
    add("NdktNgaySinh", _ngay_hoac_nam(legacy.get("NgaySinh")))
    add("NdktGioiTinh", legacy.get("GioiTinh"))
    add("NdktSoGiayto", legacy.get("SoDinhDanh"))
    add("NdktNgayCapGiayTo", _full_date(legacy.get("NgayCapDD")))
    add("NdktNoiCapGiayTo", legacy.get("NoiCapDD"))
    add("NdktMaQuoctich", legacy.get("nktQuocTich"))
    add("NdktMaDantoc", normalize_ethnic(legacy.get("nktDanToc")))

    residence = legacy.get("nktNoiCuTru_TrongNuoc")
    residence_area = _form_area(residence)
    if residence_area:
        # Loại cư trú không in trên giấy tờ nào: mặc định Thường trú, tô vàng.
        add("NctccLoaiCutru", "Thường trú", default=True)
        add("NctccMaQuocgia", residence.get("quocGia") or "Việt Nam")
        add("NctccDiaChi", residence_area)
    add("NctccNgayChet", _thoi_diem_chet(legacy.get("NgayMat"), legacy.get("GioMat"), legacy.get("PhutMat")))

    # Mapper cũ lấy nơi cư trú trên CCCD thế chỗ nơi chết khi giấy tờ không ghi. BA chỉ nhận nơi chết
    # từ tờ khai/giấy báo tử, nên chỉ điền khi agent đọc được nơi chết thật.
    death_place = legacy.get("nktNoiChet_TrongNuoc") if values.get("NguoiMat_NoiChet") else None
    death_place_area = _form_area(death_place)
    if death_place_area:
        add("NoichetMaQuocgia", death_place.get("quocGia") or "Việt Nam")
        add("NoichetDiachi", death_place_area)
    add("NguyenNhanChet", legacy.get("NguyenNhanMat"))

    if legacy.get("gbtLoai"):
        add("GbtLoaiGiayto", "Giấy báo tử")
        add("GbtSogiayto", _death_notice_number(legacy.get("gbtSo"), ocr_text))
        add("GbtNgaycap", _full_date(legacy.get("gbtNgay")))
        add("GbtNoicap", legacy.get("gbtCoQuanCap"))

    # Radio đi trước để Angular hiện ô số lượng rồi extension mới điền số.
    copy_request = legacy.get("CapBanSao")
    if copy_request == "Có":
        add("CapBanSao", "1")
        add("BanSaoSoluong", legacy.get("SoLuong"))
    elif copy_request == "Không":
        add("CapBanSao", "0")

    # ===== PHẦN III: chủ hộ, phần xóa đăng ký thường trú (BA dòng 47-49) =====
    # BA ghi giá trị hai ô đầu là của người yêu cầu → sao thẳng từ khối người yêu cầu trên trang.
    # KHÔNG tự tick "Là người kê khai" (BA xếp "Tự chọn"): chủ hộ là dữ kiện hộ khẩu, giấy tờ trong
    # hồ sơ không nói. Đánh dấu vàng để cán bộ rà.
    add("XoaChuhoHoten", None, default=True, sao_tu="NycHoTen")
    add("XoaChuhoGiayto", None, default=True, sao_tu="NycSoGiayto")
    add("XoaChuhoQuanhe", _quan_he_nguoc(quan_he, legacy.get("GioiTinh")), default=True)

    # ===== PHẦN IV-B/IV-C: người nhận mai táng phí (BA dòng 84-95, 100, 106) =====
    # Tick "Là người yêu cầu": cổng tự chuyển danh tính người nhận từ khối người yêu cầu sang và
    # khoá lại — đúng giá trị BA mô tả ở dòng 85-94 mà không phải gõ lại từ OCR. Cán bộ bỏ tick khi
    # người nhận là người khác.
    add("CanhanIsNyc", True, default=True)
    add("NnmtpQqMaQuocgia", "Việt Nam")
    add("NnmtpQuanheNguoichet", quan_he, default=True)
    # Chỉ hiện ở nhánh "Người có công"; nhánh khác extension báo không khớp ô này, chấp nhận được.
    add("NccQqMaQuocgia", "Việt Nam")
    return out
