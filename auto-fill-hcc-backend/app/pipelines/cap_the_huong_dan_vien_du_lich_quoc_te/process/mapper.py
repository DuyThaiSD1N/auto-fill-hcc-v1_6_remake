"""Map facts → UI fields (section, mat-label) cho engine fill-liz.js — cấp thẻ HDV du lịch quốc tế (1.004628).

Cùng cổng Bộ VHTTDL, cùng bộ ô người nộp / người ủy quyền với GCN khóa cập nhật kiến thức HDV 1.004605 nên dùng lại các
hàm chuẩn hoá của pipeline đó. Mỗi field emit {name=<mat-label>, comp, value, section=<cụm group-header>, aliases};
nhãn LẶP giữa các khối (Ngày sinh/Ngày cấp/Nơi cấp/Email/Địa chỉ…) nên `section` là bắt buộc.

Người nộp theo mốc tài khoản đăng nhập (formContext) so với người đề nghị trên đơn — so SỐ CCCD khi cả hai bên đều đọc
được số thật, không thì so HỌ TÊN (bỏ dấu, không phân biệt hoa thường):
  - CÙNG người (tự nộp): điền nhân thân vào khối "Thông tin người nộp hồ sơ" (Tên + CMND cổng khoá sẵn).
  - KHÁC người (nộp thay): tích "Thông tin người ủy quyền" rồi điền người đề nghị vào khối đó.
  - Không có mốc / không có gì để so: không đụng hai khối trên, chỉ điền khối đề nghị cấp thẻ.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.pipelines.cap_giay_chung_nhan_khoa_cap_nhat_kien_thuc_huong_dan_vien_du_lich.process.mapper import (
    _area,
    _by_name,
    _commune_label,
    _date,
    _digits,
    _email,
    _fold,
    _gender,
    _identity,
    _is_placeholder_digits,
    _issuer,
    _loai_the,
    _parse,
    _phone,
    _province_label,
    _text,
)
from app.pipelines.cap_the_huong_dan_vien_du_lich_quoc_te.process.schema import (
    ALIASES_BY_UI,
    COMP_BY_UI,
    LABEL_CHUYEN_MON,
    LABEL_GIOI_TINH,
    LABEL_NGOAI_NGU,
    S_NOP,
    S_THE,
    S_UQ,
    UY_QUYEN_CHECKBOX,
)


def _chuyen_mon(values: dict) -> str | None:
    """Đơn ghi thì lấy nguyên văn; đơn trống thì ghép trình độ + chuyên ngành của văn bằng."""
    tren_don = _text(values.get("NguoiDeNghi_TrinhDoChuyenMon"))
    if tren_don:
        return tren_don
    trinh_do = _text(values.get("VanBang_TrinhDo"))
    nganh = _text(values.get("VanBang_ChuyenNganh"))
    if trinh_do and nganh:
        return f"{trinh_do} chuyên ngành {nganh}"
    return trinh_do or nganh


def _la_nganh_huong_dan(major: Any) -> bool:
    """Chỉ chuyên ngành HƯỚNG DẪN du lịch mới miễn chứng chỉ nghiệp vụ (quản trị du lịch, lữ hành… vẫn phải có)."""
    return "huong dan du lich" in _fold(major)


def enrich(
    fields: list[dict], options: dict | None = None, today: date | None = None,
) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    today = today or date.today()
    out: list[dict] = []
    warnings: list[str] = []

    def put(section: str, label: str, value) -> None:
        if value in (None, "", {}, []):
            return
        comp = COMP_BY_UI.get((section, label))
        if not comp:
            return
        item = {"name": label, "comp": comp, "value": value, "section": section}
        aliases = ALIASES_BY_UI.get((section, label))
        if aliases:
            item["aliases"] = aliases
        out.append(item)

    ho_ten = _text(values.get("NguoiDeNghi_HoTen"))
    raw_identity = _digits(values.get("NguoiDeNghi_SoDinhDanh"))
    identity = _identity(raw_identity)
    ngay_sinh = _date(values.get("NguoiDeNghi_NgaySinh"))
    ngay_cap = _date(values.get("NguoiDeNghi_NgayCap"))
    noi_cap = _issuer(values.get("NguoiDeNghi_NoiCap"))
    phone = _phone(values.get("NguoiDeNghi_DienThoai"))
    email = _email(values.get("NguoiDeNghi_Email"))

    area = _area(values.get("NguoiDeNghi_DiaChi"))
    xa = _commune_label(area.get("xa")) if area else None
    tinh = _province_label(area.get("tinh")) if area else None
    hanh_chinh = f"{xa}, {tinh}" if xa and tinh else None
    chi_tiet = _text(area.get("diaChi")) if area else None
    # Ô chi tiết bắt buộc: đơn chỉ ghi tới phường/xã thì ghi lại "<xã>, <tỉnh>" cho khớp ô hành chính vừa chọn.
    chi_tiet_dien = chi_tiet or hanh_chinh

    # ---- Người nộp: cùng người với tài khoản đăng nhập (tự nộp) hay nộp thay ----
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(_digits(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber")))
    if ctx_identity and identity:
        cung_nguoi: bool | None = ctx_identity == identity
        so_theo = "số CCCD"
    elif ctx_name and ho_ten:
        cung_nguoi = _fold(ctx_name) == _fold(ho_ten)
        so_theo = "họ tên (đơn chưa đọc được số định danh)"
    else:
        cung_nguoi, so_theo = None, ""

    if cung_nguoi:
        put(S_NOP, "Ngày sinh", ngay_sinh)
        put(S_NOP, "Ngày cấp", ngay_cap)
        put(S_NOP, "Nơi cấp", noi_cap)
        put(S_NOP, "Số điện thoại", phone)
        put(S_NOP, "Email", email)
        put(S_NOP, "Địa chỉ hành chính", hanh_chinh)
        put(S_NOP, "Địa chỉ chi tiết", chi_tiet_dien)
        thieu = [label for label, value in (
            ("Số điện thoại", phone), ("E-mail", email), ("Địa chỉ hành chính", hanh_chinh),
        ) if not value]
        if thieu:
            warnings.append(
                "Khối \"Thông tin người nộp hồ sơ\" còn trống ô bắt buộc: " + ", ".join(thieu)
                + " — giấy tờ không ghi hoặc bị che/mờ, cán bộ nhập tay theo Đơn Mẫu 04 hoặc CCCD."
            )
    elif cung_nguoi is False:
        # Tích TRƯỚC: khối chỉ render sau khi tích, engine dựng lại chỉ mục rồi mới tìm ô bên dưới.
        out.append({"name": UY_QUYEN_CHECKBOX, "comp": "liz-checkbox", "value": True, "section": ""})
        put(S_UQ, "Tên người / Tên đơn vị ủy quyền", ho_ten.upper() if ho_ten else None)
        put(S_UQ, "Ngày sinh", ngay_sinh)
        put(S_UQ, "CMND/Hộ chiếu/MST Doanh nghiệp", identity)
        put(S_UQ, "Ngày cấp", ngay_cap)
        put(S_UQ, "Nơi cấp", noi_cap)
        put(S_UQ, "Số điện thoại", phone)
        put(S_UQ, "Email", email)
        put(S_UQ, "Địa chỉ hành chính", hanh_chinh)
        put(S_UQ, "Địa chỉ chi tiết", chi_tiet_dien)
        warnings.append(
            f"Tài khoản đăng nhập ({ctx_name or ctx_identity}) khác người đề nghị cấp thẻ ({ho_ten or identity}) theo "
            f"{so_theo} → coi là nộp thay: khối \"Thông tin người nộp hồ sơ\" giữ thông tin tài khoản, đã tích "
            "\"Thông tin người ủy quyền\" và điền người đề nghị vào đó."
        )
    else:
        ly_do = ("chưa có thông tin tài khoản đang đăng nhập" if not (ctx_name or ctx_identity)
                 else "chưa đọc được họ tên hoặc số định danh trên Đơn Mẫu 04")
        warnings.append(
            f"Không điền khối \"Thông tin người nộp hồ sơ\" / \"Thông tin người ủy quyền\" vì {ly_do} — chỉ điền khối "
            "đề nghị cấp thẻ. Nộp thay thì cán bộ tự tích \"Thông tin người ủy quyền\" và nhập người đề nghị."
        )
    if (cung_nguoi is not None) and hanh_chinh and not chi_tiet:
        warnings.append(
            "Địa chỉ liên lạc trên đơn chỉ ghi tới phường/xã — ô \"Địa chỉ chi tiết\" tạm ghi \"" + hanh_chinh
            + "\", cán bộ bổ sung số nhà/đường/thôn nếu có."
        )

    # ---- Khối đề nghị cấp thẻ (Đơn Mẫu 04) ----
    ngoai_ngu = _text(values.get("NguoiDeNghi_TrinhDoNgoaiNgu")) or _text(values.get("NgoaiNgu_ChungChi"))
    put(S_THE, LABEL_GIOI_TINH, _gender(values.get("NguoiDeNghi_GioiTinh"), identity))
    put(S_THE, LABEL_CHUYEN_MON, _chuyen_mon(values))
    put(S_THE, LABEL_NGOAI_NGU, ngoai_ngu)

    # ---- Cảnh báo ----
    if _is_placeholder_digits(raw_identity):
        warnings.append(f"Đơn ghi số định danh điền MẪU \"{raw_identity}\" — không dùng, cán bộ nhập số thật.")
    elif raw_identity and not identity:
        warnings.append(
            f"Số định danh trên giấy tờ chỉ đọc được \"{raw_identity}\" (không đủ 12 số) — không điền, cán bộ đối "
            "chiếu CCCD/VNeID của người đề nghị."
        )

    loai_the = _loai_the(values.get("Don_LoaiThe"))
    if loai_the in ("Nội địa", "Tại điểm"):
        warnings.append(
            f"LỆCH THỦ TỤC: Đơn Mẫu 04 ghi đề nghị cấp thẻ hướng dẫn viên du lịch {loai_the.upper()} nhưng thủ tục "
            "đang chọn là thẻ QUỐC TẾ. Xác nhận lại với người đề nghị; đúng là thẻ "
            f"{loai_the.lower()} thì chọn lại thủ tục — danh mục thành phần hồ sơ sẽ khác."
        )
    if not ngoai_ngu:
        warnings.append(
            "Chưa có TRÌNH ĐỘ NGOẠI NGỮ — điều kiện bắt buộc của thẻ quốc tế (từ bậc 4/B2 trở lên). Đơn không ghi và hồ "
            "sơ chưa thấy chứng chỉ/văn bằng ngoại ngữ; cán bộ bổ sung."
        )
    het_han = _date(values.get("NgoaiNgu_NgayHetHan"))
    if het_han and (_parse(het_han) or today) < today:
        warnings.append(
            f"Chứng chỉ ngoại ngữ đã HẾT HẠN ({het_han}) — thẻ quốc tế đòi chứng chỉ còn thời hạn, cán bộ yêu cầu bổ "
            "sung chứng chỉ mới."
        )

    major = _text(values.get("VanBang_ChuyenNganh"))
    chung_chi = _text(values.get("ChungChi_Ten"))
    if chung_chi and "noi dia" in _fold(chung_chi) and "quoc te" not in _fold(chung_chi):
        warnings.append(
            f"Hồ sơ kèm \"{chung_chi}\" — thẻ QUỐC TẾ cần chứng chỉ nghiệp vụ hướng dẫn du lịch QUỐC TẾ, chứng chỉ nội "
            "địa không thay được."
        )
    elif major and not _la_nganh_huong_dan(major) and not chung_chi:
        warnings.append(
            f"Văn bằng chuyên ngành \"{major}\" không phải chuyên ngành hướng dẫn du lịch nên phải nộp KÈM chứng chỉ "
            "nghiệp vụ hướng dẫn du lịch quốc tế (cùng dòng giấy tờ nghiệp vụ) — hồ sơ chưa thấy chứng chỉ này."
        )

    kinh_gui = _text(values.get("Don_CoQuanNhan"))
    if kinh_gui:
        warnings.append(
            f"Đơn gửi \"{kinh_gui}\" — ô \"Cơ quan giải quyết\" cổng khoá theo link nộp, kiểm tra đúng Sở này trước "
            "khi nộp."
        )
    return out, warnings
