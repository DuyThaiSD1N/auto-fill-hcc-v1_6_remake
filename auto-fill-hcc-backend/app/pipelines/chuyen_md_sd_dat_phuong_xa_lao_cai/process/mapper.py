"""Map dữ kiện nguồn → field UI bước 2 cho thủ tục 1.115679 (Lào Cai — nộp tại phường/xã).

Chọn nguồn theo sheet "Ma trận đa nguồn" của "Mapping_CMDSDD_1.115679_LaoCai_CaNhan_ToChuc.xlsx"
(ưu tiên: CCCD → Đơn đề nghị → Giấy uỷ quyền → Giấy chứng nhận/giấy tờ chuyên ngành → các văn bản còn lại):
  Người nộp : "Họ và tên" + "Số Căn cước" readonly, cổng đổ từ tài khoản định danh → KHÔNG phát.
              Ngày sinh/giới tính/dân tộc/ngày cấp/nơi cấp/ĐỊA CHỈ → giấy tờ của CHÍNH người đang đăng nhập:
              CCCD đã upload (khớp số định danh, không có số thì khớp họ tên tài khoản) rồi đến người được
              ghi kèm số CCCD trong Đơn/Giấy uỷ quyền. Hồ sơ nộp thay thì đó là BÊN ĐƯỢC UỶ QUYỀN.
              Không nhận ra người đăng nhập trong hồ sơ → bỏ trống hết, KHÔNG gán bừa.
              Di động/Email chỉ chép lại số trên Đơn khi người đăng nhập CHÍNH LÀ chủ hồ sơ.
              Tên cơ quan/MSDN → tổ chức chủ hồ sơ (người nộp đứng ra đại diện cho tổ chức đó).
  Chủ hồ sơ : người sử dụng đất ở mục 1 của Đơn, 4 nhánh CN/DN/CQ/TC.
              Cá nhân → CCCD rồi Đơn rồi Giấy uỷ quyền; tổ chức → tên + MST theo giấy tờ pháp nhân.
              Địa chỉ → CCCD → Đơn → Giấy uỷ quyền → Giấy chứng nhận/hồ sơ đo đạc → vị trí thửa đất.
              Di động/Email → Đơn → Phiếu chuyển thông tin.

⚠ Ô "Giới tính" của cổng không có option trống nên luôn hiển thị "Nữ": hồ sơ nam giới mà thiếu giới tính là
nộp sai mà form vẫn trông như đã chọn → cố gắng suy từ xưng hô Ông/Bà khi không có ảnh thẻ.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import upper_person_name
from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.process.schema import UI_ALIASES, UI_COMP_BY_NAME

_FULL_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")

# Option value thật của <select name="ChuHoSo_maDoiTuongNopHS"> trên cổng.
_DOI_TUONG_CA_NHAN = "CN"
_DOI_TUONG_DOANH_NGHIEP = "DN"
_DOI_TUONG_CO_QUAN = "CQ"
_DOI_TUONG_TO_CHUC_KHAC = "TC"

# LLM trả nhãn tiếng Việt (schema ChuHoSo_LoaiDoiTuong) → option value của cổng.
_DOI_TUONG_BY_LABEL = {
    "ca nhan": _DOI_TUONG_CA_NHAN,
    "doanh nghiep": _DOI_TUONG_DOANH_NGHIEP,
    "co quan nha nuoc": _DOI_TUONG_CO_QUAN,
    "to chuc khac": _DOI_TUONG_TO_CHUC_KHAC,
}

# LLM trả nhãn lạ (hay gặp: "Tổ chức" chung chung) → đoán lại theo CHÍNH tên tổ chức, vì chọn sai ô này là
# cổng hiện nhầm nhóm trường bắt buộc. Thứ tự kiểm quan trọng: tên vừa có "ban quan ly" vừa có "so " thì
# nhánh tổ chức chính trị - xã hội/tôn giáo phải xét TRƯỚC.
_TO_CHUC_KHAC_HINTS = (
    "mat tran to quoc", "mttq", "hoi nong dan", "hoi lien hiep", "hoi cuu chien binh", "doan thanh nien",
    "cong doan", "lien doan lao dong", "hoi phu nu", "to chuc chinh tri", "giao xu", "giao ho", "nha tho",
    "giao phan", "chua ", "thien vien", "tinh that", "cong dong dan cu", "dong ho",
)
_CO_QUAN_HINTS = (
    "uy ban nhan dan", "ubnd", "so ", "chi cuc", "cuc ", "ban quan ly", "trung tam", "van phong dang ky",
    "phong giao duc", "truong tieu hoc", "truong trung hoc", "truong mam non", "benh vien", "tram y te",
    "bo chi huy", "cong an", "vien kiem sat", "toa an", "kho bac", "tinh uy", "huyen uy", "dang uy",
    "hat kiem lam", "don vi su nghiep",
)
_DOANH_NGHIEP_HINTS = (
    "cong ty", "doanh nghiep", "tap doan", "tong cong ty", "ngan hang", "hop tac xa", "chi nhanh",
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or "").replace("Đ", "D").replace("đ", "d"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _plain(value) -> str | None:
    if not isinstance(value, str):
        return None
    return " ".join(value.split()).strip(" :;,-") or None


def _full_date(value) -> str | None:
    """Chỉ nhận ngày đủ dd/mm/yyyy. "Sinh: 1985" không đủ cho ô DD/MM/YYYY → bỏ, không bịa."""
    match = _FULL_DATE_RE.match(_plain(value) or "")
    if not match:
        return None
    return f"{int(match.group(1)):02d}/{int(match.group(2)):02d}/{match.group(3)}"


def _id_number(value) -> str | None:
    digits = _digits(value)
    return digits if len(digits) in (9, 12) else None


def _tax_code(value) -> str | None:
    digits = _digits(value)
    return digits if len(digits) in (10, 13) else None


def _phone(value) -> str | None:
    text = str(value or "").strip()
    digits = _digits(text)
    if text.startswith("+84") and digits.startswith("84"):
        digits = "0" + digits[2:]
    return digits if 10 <= len(digits) <= 11 and digits.startswith("0") else None


def _email(value) -> str | None:
    text = (_plain(value) or "").replace(" ", "")
    return text if re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", text) else None


def _issuer(value) -> str | None:
    return normalize_issuer(value) or _plain(value)


def _gender(person: dict | None, xung_ho=None) -> str | None:
    text = _fold((person or {}).get("GioiTinh"))
    if text in ("nam", "male"):
        return "Nam"
    if text in ("nu", "female"):
        return "Nữ"
    salutation = _fold(xung_ho)
    if salutation == "ong":
        return "Nam"
    if salutation == "ba":
        return "Nữ"
    return None


def org_option(loai_doi_tuong, org_name) -> str:
    """Option "Đối tượng nộp hồ sơ" cho chủ hồ sơ là TỔ CHỨC.

    Ưu tiên nhãn LLM đọc được; nhãn lạ (trả trống hoặc "Tổ chức" chung chung) thì đoán theo tên tổ chức.
    Không đoán ra được thì "Tổ chức khác" — lựa chọn rộng nhất, không ô nào bị ép bắt buộc thêm.
    """
    mapped = _DOI_TUONG_BY_LABEL.get(_fold(loai_doi_tuong))
    if mapped and mapped != _DOI_TUONG_CA_NHAN:
        return mapped
    name = _fold(org_name)
    if any(hint in name for hint in _TO_CHUC_KHAC_HINTS):
        return _DOI_TUONG_TO_CHUC_KHAC
    if any(hint in name for hint in _CO_QUAN_HINTS):
        return _DOI_TUONG_CO_QUAN
    if any(hint in name for hint in _DOANH_NGHIEP_HINTS):
        return _DOI_TUONG_DOANH_NGHIEP
    return _DOI_TUONG_TO_CHUC_KHAC


def _area(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or "",
        "xa": value.get("xa") or "",
        "diaChi": value.get("diaChi") or "",
    }
    # Thiếu tỉnh hoặc xã thì không chọn được cặp select → bỏ nguồn này, thử nguồn sau.
    if not (area["tinh"] and area["xa"]):
        return None
    hint = value.get("huyen") or value.get("quanHuyen") or ""
    return remap_area(area, huyen_hint=hint) or area


def _people(values: dict, name: str) -> list[dict]:
    items = values.get(name)
    return [p for p in items if isinstance(p, dict)] if isinstance(items, list) else []


def _match_by_id(people: list[dict], wanted) -> dict | None:
    wanted = _digits(wanted)
    if not wanted:
        return None
    matches = [p for p in people if _digits(p.get("SoDinhDanh")) == wanted]
    return matches[0] if len(matches) == 1 else None


def _match_by_name(people: list[dict], name) -> dict | None:
    wanted = _fold(name)
    if not wanted:
        return None
    matches = [p for p in people if _fold(p.get("HoTen")) == wanted]
    # Nhiều người trùng tên → không đoán.
    return matches[0] if len(matches) == 1 else None


def _find_person(people: list[dict], id_number, name) -> dict | None:
    return _match_by_id(people, id_number) if _digits(id_number) else _match_by_name(people, name)


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    values = _by_name(fields)
    ctx = (options or {}).get("formContext") or {}
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if name in UI_ALIASES:
            field["aliases"] = UI_ALIASES[name]
        out.append(field)
        seen.add(name)

    cards = _people(values, "DanhSachCccd")
    named = _people(values, "NguoiTrongGiayTo")

    # ----- Chủ hồ sơ: xác định loại TRƯỚC (người nộp cần biết có đại diện tổ chức không). -----
    org_name = _plain(values.get("ChuHoSo_TenToChuc"))
    org_tax = _tax_code(values.get("ChuHoSo_MaSoThue"))
    is_ca_nhan_label = _fold(values.get("ChuHoSo_LoaiDoiTuong")) == "ca nhan"
    is_org = bool(org_name) and not is_ca_nhan_label

    owner_id = _id_number(values.get("ChuHoSo_SoDinhDanh"))
    owner_card = None if is_org else _find_person(cards, owner_id, values.get("ChuHoSo_HoTen"))
    owner_named = None if is_org else _find_person(named, owner_id, values.get("ChuHoSo_HoTen"))
    person_name = _plain((owner_card or {}).get("HoTen")) or _plain(values.get("ChuHoSo_HoTen"))
    person_id = _id_number((owner_card or {}).get("SoDinhDanh")) or owner_id
    is_person = not is_org and bool(person_name and person_id)

    # ----- Phần I: người nộp (tài khoản đang đăng nhập). -----
    applicant_id = ctx.get("applicantIdentityNumber") or ctx.get("identityNumber")
    applicant_name = ctx.get("applicantFullname")
    applicant_card = _find_person(cards, applicant_id, applicant_name)
    applicant_named = _find_person(named, applicant_id, applicant_name)
    if is_org:
        # Người nộp đứng ra cho tổ chức chủ hồ sơ (mapping: ô Tên cơ quan/MSDN của khối người nộp).
        add("CongDan_tenCoQuanToChuc", org_name)
        add("CongDan_maSoThueNguoiNop", org_tax)
    if applicant_card:
        add("CongDan_ngaySinhCongDan", _full_date(applicant_card.get("NgaySinh")))
        add("CongDan_gioiTinhCongDan", _gender(applicant_card))
        add("CongDan_danTocCongDan", _plain(applicant_card.get("DanToc")))
    # Hồ sơ mẫu của thủ tục này KHÔNG có bản scan CCCD; Đơn và Giấy uỷ quyền vẫn ghi đủ số + ngày cấp + nơi
    # cấp + nơi thường trú của cả hai bên uỷ quyền.
    add("CongDan_ngaySinhCongDan", _full_date((applicant_named or {}).get("NgaySinh")))
    # Ô Giới tính không có option trống (cổng luôn hiện "Nữ") → suy từ xưng hô nếu chỉ có giấy tờ chữ.
    add("CongDan_gioiTinhCongDan", _gender(applicant_named))
    add("CongDan_ngayCapCmnd",
        _full_date((applicant_card or {}).get("NgayCap")) or _full_date((applicant_named or {}).get("NgayCap")))
    add("CongDan_noiCapCmnd",
        _issuer((applicant_card or {}).get("NoiCap")) or _issuer((applicant_named or {}).get("NoiCap")))
    # Tỉnh/Phường-Xã/Số nhà của khối người nộp đều là (*). Cổng đổ sẵn theo tài khoản nhưng vẫn phát lại theo
    # giấy tờ của CHÍNH người đăng nhập để ba ô là một địa chỉ nhất quán — chắp nửa tài khoản nửa giấy tờ là
    # ra địa chỉ không có thật. Tỉnh TRƯỚC xã: danh sách Phường/Xã chỉ nạp AJAX sau khi chọn tỉnh, và cổng
    # đang nạp sẵn danh sách xã của tỉnh theo tài khoản.
    applicant_area = (
        _area((applicant_card or {}).get("NoiCuTru"))
        or _area((applicant_named or {}).get("NoiCuTru"))
    )
    if applicant_area:
        add("CongDan_maTinhThanh", province_label(applicant_area.get("tinh")))
        add("CongDan_maPhuongXa", _plain(applicant_area.get("xa")))
        add("CongDan_diaChi", _plain(applicant_area.get("diaChi")))
    # Di động/Email trên Đơn là của NGƯỜI SỬ DỤNG ĐẤT → chỉ dùng lại cho khối người nộp khi người đăng nhập
    # chính là chủ hồ sơ. Nộp thay mà chép số của chủ hồ sơ sang là cổng gửi thông báo về sai người.
    self_submit = bool(person_id and applicant_id and _digits(person_id) == _digits(applicant_id))
    if self_submit:
        add("CongDan_diDong", _phone(values.get("Don_DienThoai")))
        add("CongDan_email", _email(values.get("Don_Email")))

    # ----- Phần II: chủ hồ sơ. -----
    if is_org:
        # Đối tượng là driver: phát TRƯỚC để cổng hiện nhóm ô tổ chức (tên cơ quan + MST).
        add("ChuHoSo_maDoiTuongNopHS", org_option(values.get("ChuHoSo_LoaiDoiTuong"), org_name))
        add("ChuHoSo_tenCoQuanToChucCHS", org_name)
        add("ChuHoSo_maSoThueChuHoSo", org_tax)
    elif is_person:
        add("ChuHoSo_maDoiTuongNopHS", _DOI_TUONG_CA_NHAN)
        add("ChuHoSo_tenChuHoSo", upper_person_name(person_name))
        add("ChuHoSo_ngaySinhChuHoSo",
            _full_date((owner_card or {}).get("NgaySinh"))
            or _full_date(values.get("ChuHoSo_NgaySinh"))
            or _full_date((owner_named or {}).get("NgaySinh")))
        add("ChuHoSo_gioiTinhChuHoSo",
            _gender(owner_card) or _gender(owner_named, values.get("ChuHoSo_XungHo")))
        add("ChuHoSo_danTocChuHoSo", _plain((owner_card or {}).get("DanToc")))
        add("ChuHoSo_soCMNDChuHoSo", person_id)
        add("ChuHoSo_noiCapCMNDCHS",
            _issuer((owner_card or {}).get("NoiCap"))
            or _issuer(values.get("ChuHoSo_NoiCap"))
            or _issuer((owner_named or {}).get("NoiCap")))
        add("ChuHoSo_ngayCapCMNDCHS",
            _full_date((owner_card or {}).get("NgayCap"))
            or _full_date(values.get("ChuHoSo_NgayCap"))
            or _full_date((owner_named or {}).get("NgayCap")))

    if is_org or is_person:
        # CCCD đứng đầu theo ma trận đa nguồn (địa chỉ lệch nhau ở cả hai hồ sơ mẫu: Đơn ghi "Tổ 39", Giấy uỷ
        # quyền ghi "Tổ dân phố số 9 Xuân Tăng", GCN 2018 còn địa danh cũ "Tổ 24, phường Bình Minh").
        residence = (
            _area((owner_card or {}).get("NoiCuTru"))
            or _area(values.get("ChuHoSo_DiaChiDon"))
            or _area(values.get("ChuHoSo_DiaChiUyQuyen"))
            or _area((owner_named or {}).get("NoiCuTru"))
            or _area(values.get("ChuHoSo_DiaChiGcn"))
            or _area(values.get("ThuaDat_DiaChi"))
        )
        if residence:
            add("ChuHoSo_maTinhThanhCHS", province_label(residence.get("tinh")))
            add("ChuHoSo_maPhuongXaCHS", _plain(residence.get("xa")))
            add("ChuHoSo_diaChiChuHoSo", _plain(residence.get("diaChi")))
        add("ChuHoSo_diDongLienLacCHS",
            _phone(values.get("Don_DienThoai")) or _phone(values.get("PhieuChuyen_DienThoai")))
        add("ChuHoSo_emailChuHoSo", _email(values.get("Don_Email")))

    return out
