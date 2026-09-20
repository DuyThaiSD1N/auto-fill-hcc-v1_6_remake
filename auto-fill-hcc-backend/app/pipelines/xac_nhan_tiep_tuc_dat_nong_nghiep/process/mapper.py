"""Map dữ kiện nguồn → ô bước 2 (`CongDan_*` / `ChuHoSo_*`) của cổng Lào Cai, thủ tục 1.115677.

Ma trận nguồn theo sheet "Ma trận đa nguồn" của file mapping (thứ tự ưu tiên: CCCD → Đơn Mẫu số 39 →
Giấy chứng nhận → mảnh trích đo):

  Phần I  NGƯỜI NỘP  = CHÍNH người đang đăng nhập cổng, KHÔNG mặc định là chủ hồ sơ.
      Họ tên + Số Căn cước : readonly, cổng điền từ tài khoản định danh → KHÔNG phát (sửa họ tên là
                             script cổng xoá trắng Di động + Số Căn cước). Đây đồng thời là MỐC DUY
                             NHẤT (options.formContext) để biết ai đang đi nộp.
      Nhân thân còn lại    : CHỈ lấy từ giấy tờ khớp ĐÚNG mốc đó — CCCD của chính người đăng nhập →
                             Giấy ủy quyền khi bên B chính là người đăng nhập → giấy tờ khác của đúng
                             người đó. Khớp theo SỐ ĐỊNH DANH trước, không khớp thì theo HỌ TÊN tài
                             khoản (Giấy chứng nhận hay in CMND 9 số cũ, lệch số căn cước 12 số).
      Địa chỉ / Di động / Email:
                             của CHÍNH người nộp. Mục 2 Đơn Mẫu số 39 ghi MỘT "Địa chỉ liên hệ" dùng
                             CHUNG cho cả hộ, nên nguồn Đơn được phép dùng cho khối người nộp khi người
                             đăng nhập là MỘT TRONG các người sử dụng đất ở mục 1 (chủ hồ sơ, hoặc
                             vợ/chồng cùng đứng tên — chính là ca mẫu: ông Minh đứng tên đầu, bà Vụ ký
                             đơn và đi nộp). Người ngoài hộ (người được ủy quyền, người đại diện tổ
                             chức) thì KHÔNG — thà để trống ô (*) cho cán bộ nhập còn hơn điền địa chỉ
                             của người khác.
      Tên cơ quan/MST      : tổ chức chủ hồ sơ (người nộp đại diện tổ chức đó).

      ⚠ KHÔNG có formContext (trang chưa đăng nhập, hoặc popup chưa bật thu thập cho key thủ tục này)
        → BỎ TRỐNG toàn bộ nhân thân khối người nộp + cảnh báo. Thiếu mốc thì mọi suy đoán đều sai.

  Phần II CHỦ HỒ SƠ = người sử dụng đất đứng tên ĐẦU TIÊN ở mục 1 Đơn Mẫu số 39.
      Cá nhân  : CCCD → Đơn → giấy tờ khác.      Tổ chức : tên + MST.
      Địa chỉ  : cá nhân CCCD → Đơn mục 2;       tổ chức trụ sở → Đơn mục 2.
      Di động  : Đơn mục 2 (→ tổ chức nếu là pháp nhân).
      Email    : Đơn mục 2 (→ tổ chức nếu là pháp nhân).

Mapper LUÔN phát ĐỦ khối chủ hồ sơ (gồm cả 3 ô địa chỉ) thay vì trông vào checkbox "Người nộp là chủ
hồ sơ" của cổng, và KHÔNG tự bấm checkbox đó — JS `nguoiNopLaChuHoSo()` sao chép Phần I sang Phần II
nên bấm nhầm là ghi đè dữ liệu chủ hồ sơ bằng dữ liệu người nộp.
"""

import re
import unicodedata

from app.pipelines._shared.area_remap import province_label, remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import upper_person_name
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process.schema import (
    UI_ALIASES,
    UI_COMP_BY_NAME,
)

_FULL_DATE_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")

_DOI_TUONG_CA_NHAN = "CN"
_DOI_TUONG_TO_CHUC = "DN"


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
    return " ".join(value.replace("\n", " ").split()).strip(" :;,-") or None


_SALUTATION_RE = re.compile(r"^(ông|bà|anh|chị|cụ|em|ong|ba)\s+", re.IGNORECASE)


def _person_name(value) -> str | None:
    """Bỏ xưng hô dính vào tên ("Bà Nguyễn Thị Vụ" → "Nguyễn Thị Vụ") để so khớp người cho đúng."""
    text = _plain(value)
    if not text:
        return None
    return _SALUTATION_RE.sub("", text).strip() or None


def _full_date(value) -> str | None:
    """Chỉ nhận ngày ĐỦ dd/mm/yyyy — ô datetime-picker của cổng không nhận "1971" trần."""
    match = _FULL_DATE_RE.match(_plain(value) or "")
    if not match:
        return None
    return f"{int(match.group(1)):02d}/{int(match.group(2)):02d}/{match.group(3)}"


def _id_number(value) -> str | None:
    digits = _digits(value)
    return digits if len(digits) in (9, 12) else None


def _prefer_12_digits(*values) -> str | None:
    """Một người thường có CẢ căn cước 12 số LẪN CMND 9 số cũ (Giấy chứng nhận, sổ hộ khẩu in số cũ).
    Ô "Số Căn cước" của cổng cần số 12 số → ưu tiên nó, dù nguồn nào đọc ra trước."""
    candidates = [n for n in (_id_number(v) for v in values) if n]
    return next((n for n in candidates if len(n) == 12), candidates[0] if candidates else None)


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
    text = _fold((person or {}).get("GioiTinh") or (person or {}).get("gioiTinh"))
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


def _area(value) -> dict | None:
    """Chuẩn hoá object địa chỉ; thiếu tỉnh HOẶC xã thì bỏ nguồn này để thử nguồn sau."""
    if not isinstance(value, dict):
        return None
    area = {
        "quocGia": value.get("quocGia") or "Việt Nam",
        "tinh": value.get("tinh") or "",
        "xa": value.get("xa") or "",
        "diaChi": value.get("diaChi") or "",
    }
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
    wanted = _fold(_person_name(name))
    if not wanted:
        return None
    matches = [p for p in people if _fold(_person_name(p.get("HoTen"))) == wanted]
    # Nhiều người trùng tên → không đoán.
    return matches[0] if len(matches) == 1 else None


def _find_person(people: list[dict], id_number, name) -> dict | None:
    """Khớp theo số định danh trước, KHÔNG khớp thì lùi về họ tên.

    Bắt buộc phải có bước lùi: Giấy chứng nhận cấp từ lâu (và mục "Những thay đổi sau khi cấp Giấy
    chứng nhận") chỉ in CMND 9 SỐ CŨ, trong khi thẻ Căn cước là 12 số. Nếu chỉ khớp theo số thì không
    tìm ra thẻ của chính người đó và mapper sẽ điền số CMND cũ vào ô "Số Căn cước" — cổng coi là sai
    người. `_match_by_name` vẫn bỏ qua khi có từ hai người trùng tên trở lên nên không đoán bừa.
    """
    return _match_by_id(people, id_number) or _match_by_name(people, name)


def _find_applicant(people: list[dict], ctx_id, ctx_name) -> dict | None:
    """Tìm giấy tờ của CHÍNH người đang đăng nhập: khớp số định danh trước, KHÔNG có thì khớp HỌ TÊN.

    Cổng luôn prefill sẵn cả Họ tên lẫn Số Căn cước từ tài khoản định danh, nhưng số ghi trên giấy tờ
    vừa upload có thể lệch với số của tài khoản (OCR sai một chữ số, hoặc Giấy chứng nhận chỉ in CMND
    9 số cũ trong khi tài khoản dùng căn cước 12 số). Khi đó HỌ TÊN trùng tài khoản là đủ để chốt đúng
    người — vẫn an toàn vì `_match_by_name` bỏ qua khi có từ hai người trùng tên trở lên.
    """
    return _match_by_id(people, ctx_id) or _match_by_name(people, ctx_name)


def _is_one_of(people: list[dict], ctx_id, ctx_name) -> bool:
    """Người đăng nhập có nằm trong danh sách này không (khớp số định danh HOẶC họ tên)."""
    if ctx_id:
        if any(_digits(p.get("SoDinhDanh")) == ctx_id for p in people):
            return True
    if ctx_name:
        wanted = _fold(ctx_name)
        if any(_fold(_person_name(p.get("HoTen"))) == wanted for p in people):
            return True
    return False


def _proxy(values: dict) -> dict | None:
    """Bên được ủy quyền: chỉ nhận khi có ĐỦ họ tên + số định danh ghi trong giấy ủy quyền."""
    raw = values.get("NguoiDuocUyQuyen")
    if not isinstance(raw, dict):
        return None
    if not (_person_name(raw.get("hoTen")) and _id_number(raw.get("soDinhDanh"))):
        return None
    return raw


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    ctx = (options or {}).get("formContext") or {}
    out: list[dict] = []
    seen: set[str] = set()
    warnings: list[str] = []

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
    ho_su_dung_dat = _people(values, "Don_NguoiSuDungDat")
    proxy = _proxy(values)

    # ---- Chủ hồ sơ: chốt loại đối tượng trước (khối người nộp cần biết có đại diện tổ chức không).
    org_name = _plain(values.get("ChuHoSo_TenToChuc"))
    org_tax = _tax_code(values.get("ChuHoSo_MaSoThue"))
    is_org = _fold(values.get("ChuHoSo_LoaiDoiTuong")) == "to chuc" and bool(org_name)

    owner_id = _id_number(values.get("ChuHoSo_SoDinhDanh"))
    owner_card = None if is_org else _find_person(cards, owner_id, values.get("ChuHoSo_HoTen"))
    owner_named = None if is_org else _find_person(named, owner_id, values.get("ChuHoSo_HoTen"))
    owner_name = _person_name((owner_card or {}).get("HoTen")) or _person_name(values.get("ChuHoSo_HoTen"))
    owner_identity = _prefer_12_digits(
        (owner_card or {}).get("SoDinhDanh"), owner_id, (owner_named or {}).get("SoDinhDanh")
    )
    is_person = not is_org and bool(owner_name and owner_identity)

    # Mục 2 "Địa chỉ liên hệ" của Đơn Mẫu số 39 là nơi cư trú dùng CHUNG cho cả hộ; với tổ chức thì
    # trụ sở chính đứng trước.
    owner_residence = (
        (_area(values.get("ChuHoSo_DiaChiToChuc")) or _area(values.get("ChuHoSo_DiaChiDon")))
        if is_org
        else (_area((owner_card or {}).get("NoiCuTru")) or _area(values.get("ChuHoSo_DiaChiDon")))
    )
    owner_phone = _phone(values.get("Don_DienThoai")) or (
        _phone(values.get("ToChuc_DienThoai")) if is_org else None
    )
    owner_email = _email(values.get("Don_Email")) or (
        _email(values.get("ToChuc_Email")) if is_org else None
    )

    # ---- Phần I: người nộp.
    # ⚑ MỐC DUY NHẤT để biết AI đang đi nộp là tài khoản định danh mà cổng đã điền sẵn vào hai ô
    # readonly `CongDan_tenCongDan` / `CongDan_soCmnd` (extension gửi lên trong options.formContext).
    # KHÔNG có mốc đó thì MỌI suy đoán đều sai: người đi nộp có thể là người đứng tên đầu, là vợ/chồng
    # ký đơn, là người được ủy quyền, hoặc một người thứ ba không hề xuất hiện trong hồ sơ. Trường hợp
    # này phải BỎ TRỐNG toàn bộ nhân thân khối người nộp — thà để cán bộ nhập tay còn hơn điền nhầm.
    ctx_id = _id_number(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    ctx_name = _person_name(ctx.get("applicantFullname"))
    has_anchor = bool(ctx_id or ctx_name)

    # Dữ liệu người nộp CHỈ được lấy từ giấy tờ khớp ĐÚNG mốc trên.
    applicant_card = _find_applicant(cards, ctx_id, ctx_name) if has_anchor else None
    applicant_named = _find_applicant(named, ctx_id, ctx_name) if has_anchor else None

    # Giấy ủy quyền chỉ dùng cho khối người nộp khi tài khoản đăng nhập ĐÚNG là bên được ủy quyền.
    proxy_data = None
    if proxy and has_anchor:
        proxy_id = _digits(proxy.get("soDinhDanh"))
        if (ctx_id and proxy_id == ctx_id) or (
            ctx_name and _fold(_person_name(proxy.get("hoTen"))) == _fold(ctx_name)
        ):
            proxy_data = proxy

    # NGƯỜI TRONG HỘ SỬ DỤNG ĐẤT: người đăng nhập là chủ hồ sơ, HOẶC là một trong những người cùng
    # đứng tên ở mục 1 Đơn Mẫu số 39 (vd vợ ký đơn và đi nộp thay chồng đứng tên đầu). Chỉ khi đó mới
    # được dùng "Địa chỉ liên hệ" + điện thoại/email ở mục 2 của Đơn cho khối người nộp, vì mục 2 là
    # địa chỉ chung của cả hộ.
    is_owner_himself = bool(
        is_person
        and has_anchor
        and (
            (ctx_id and owner_identity and ctx_id == _digits(owner_identity))
            or (ctx_name and owner_name and _fold(ctx_name) == _fold(owner_name))
        )
    )
    is_household_member = bool(
        has_anchor
        and not is_org
        and (is_owner_himself or _is_one_of(ho_su_dung_dat, ctx_id, ctx_name))
    )
    don_area = _area(values.get("ChuHoSo_DiaChiDon"))

    if is_org:
        # Người nộp đứng ra cho tổ chức chủ hồ sơ → ô tên cơ quan/MST khối người nộp là của tổ chức đó.
        add("CongDan_tenCoQuanToChuc", org_name.upper())
        add("CongDan_maSoThueNguoiNop", org_tax)

    add("CongDan_ngaySinhCongDan",
        _full_date((applicant_card or {}).get("NgaySinh"))
        or _full_date((proxy_data or {}).get("ngaySinh"))
        or _full_date((applicant_named or {}).get("NgaySinh")))
    add("CongDan_gioiTinhCongDan",
        _gender(applicant_card) or _gender(proxy_data) or _gender(applicant_named))
    add("CongDan_danTocCongDan",
        _plain((applicant_card or {}).get("DanToc")) or _plain((proxy_data or {}).get("danToc")))
    add("CongDan_ngayCapCmnd",
        _full_date((applicant_card or {}).get("NgayCap"))
        or _full_date((proxy_data or {}).get("ngayCapCccd"))
        or _full_date((applicant_named or {}).get("NgayCap")))
    add("CongDan_noiCapCmnd",
        _issuer((applicant_card or {}).get("NoiCap"))
        or _issuer((proxy_data or {}).get("noiCapCccd"))
        or _issuer((applicant_named or {}).get("NoiCap")))

    applicant_area = (
        _area((applicant_card or {}).get("NoiCuTru"))
        or _area((proxy_data or {}).get("thuongTru"))
        or (don_area if is_household_member else None)
    )
    if applicant_area:
        # Tỉnh TRƯỚC xã: danh mục Phường/Xã chỉ nạp sau khi chọn tỉnh (mặc định cổng là Lào Cai).
        add("CongDan_maTinhThanh", province_label(applicant_area.get("tinh")))
        add("CongDan_maPhuongXa", _plain(applicant_area.get("xa")))
        add("CongDan_diaChi", _plain(applicant_area.get("diaChi")))
    add("CongDan_diDong",
        _phone((proxy_data or {}).get("dienThoai"))
        or _phone((applicant_named or {}).get("DienThoai"))
        or (_phone(values.get("Don_DienThoai")) if is_household_member else None))
    add("CongDan_email",
        _email((proxy_data or {}).get("email"))
        or _email((applicant_named or {}).get("Email"))
        or (_email(values.get("Don_Email")) if is_household_member else None))

    if not has_anchor:
        warnings.append(
            "Không xác định được NGƯỜI ĐANG ĐI NỘP: cổng chưa điền sẵn Họ tên/Số Căn cước từ tài khoản "
            "định danh (hoặc trang chưa đăng nhập). Trợ lý bỏ trống toàn bộ nhân thân khối 'Thông tin "
            "người nộp' để khỏi điền nhầm người sử dụng đất hay người được ủy quyền — cán bộ đăng nhập "
            "đúng tài khoản của người đi nộp rồi quét lại, hoặc nhập tay."
        )
    else:
        missing = [
            label
            for label, name in (
                ("Tỉnh/Thành phố", "CongDan_maTinhThanh"),
                ("Phường/Xã", "CongDan_maPhuongXa"),
                ("Số nhà/Đường", "CongDan_diaChi"),
                ("Di động", "CongDan_diDong"),
            )
            if name not in seen
        ]
        if missing:
            warnings.append(
                "Trợ lý không điền được ô bắt buộc của khối 'Thông tin người nộp': " + ", ".join(missing)
                + ". Hồ sơ không có giấy tờ ghi thông tin này của CHÍNH người đang đăng nhập"
                + (f" ({ctx_name})" if ctx_name else "")
                + ". Đơn Mẫu số 39 thường không ghi số điện thoại — nếu cổng chưa tự điền sẵn từ tài "
                "khoản thì cán bộ nhập tay, KHÔNG lấy của người khác trong hồ sơ."
            )

    # ---- Phần II: chủ hồ sơ. "Đối tượng nộp hồ sơ" là driver → phát TRƯỚC để cổng hiện đúng nhóm ô.
    if is_org:
        add("ChuHoSo_maDoiTuongNopHS", _DOI_TUONG_TO_CHUC)
        add("ChuHoSo_tenCoQuanToChucCHS", org_name.upper())
        add("ChuHoSo_maSoThueChuHoSo", org_tax)
        if not org_tax:
            warnings.append(
                "Chủ hồ sơ là tổ chức nhưng chưa đọc được Mã số thuế — ô này bắt buộc khi 'Đối tượng nộp "
                "hồ sơ' khác Cá nhân, cán bộ nhập tay."
            )
    elif is_person:
        add("ChuHoSo_maDoiTuongNopHS", _DOI_TUONG_CA_NHAN)
        add("ChuHoSo_tenChuHoSo", upper_person_name(owner_name))
        add("ChuHoSo_soCMNDChuHoSo", owner_identity)
        add("ChuHoSo_ngaySinhChuHoSo",
            _full_date((owner_card or {}).get("NgaySinh"))
            or _full_date(values.get("ChuHoSo_NgaySinh"))
            or _full_date((owner_named or {}).get("NgaySinh")))
        add("ChuHoSo_gioiTinhChuHoSo",
            _gender(owner_card)
            or _gender({"GioiTinh": values.get("ChuHoSo_GioiTinh")}, values.get("ChuHoSo_XungHo"))
            or _gender(owner_named))
        add("ChuHoSo_danTocChuHoSo",
            _plain((owner_card or {}).get("DanToc")) or _plain(values.get("ChuHoSo_DanToc")))
        add("ChuHoSo_noiCapCMNDCHS",
            _issuer((owner_card or {}).get("NoiCap"))
            or _issuer(values.get("ChuHoSo_NoiCap"))
            or _issuer((owner_named or {}).get("NoiCap")))
        add("ChuHoSo_ngayCapCMNDCHS",
            _full_date((owner_card or {}).get("NgayCap"))
            or _full_date(values.get("ChuHoSo_NgayCap"))
            or _full_date((owner_named or {}).get("NgayCap")))
    else:
        warnings.append(
            "Chưa xác định được chủ hồ sơ (người sử dụng đất đứng tên đầu mục 1 Đơn Mẫu số 39): thiếu họ "
            "tên hoặc số căn cước với cá nhân, thiếu tên tổ chức với pháp nhân. Cán bộ kiểm tra lại Đơn "
            "Mẫu số 39 và Giấy chứng nhận đã cấp."
        )

    if is_org or is_person:
        if owner_residence:
            add("ChuHoSo_maTinhThanhCHS", province_label(owner_residence.get("tinh")))
            add("ChuHoSo_maPhuongXaCHS", _plain(owner_residence.get("xa")))
            add("ChuHoSo_diaChiChuHoSo", _plain(owner_residence.get("diaChi")))
        else:
            warnings.append(
                "Không đọc được địa chỉ chủ hồ sơ (mục 2 'Địa chỉ liên hệ' của Đơn Mẫu số 39). Nút "
                "\"Người nộp là chủ hồ sơ\" của cổng sao chép nguyên khối Phần I sang Phần II nên KHÔNG "
                "dùng được khi hai người khác nhau — cán bộ nhập tay Tỉnh/Phường-Xã/Địa chỉ ở khối chủ "
                "hồ sơ."
            )
        add("ChuHoSo_diDongLienLacCHS", owner_phone)
        add("ChuHoSo_emailChuHoSo", owner_email)

    return out, warnings
