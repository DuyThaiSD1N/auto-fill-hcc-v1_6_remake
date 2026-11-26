"""Map compact source facts → Form.io data[...] fields cho "Cấp giấy phép thi công công trình trên đường bộ đang khai
thác" (1.013061).

Theo mapping 1.013061 (DOM cá nhân + DOM tổ chức), form chỉ có Phần I người nộp:
- Người đứng đơn khớp tài khoản đăng nhập (hoặc extension không gửi được tài khoản) → điền Phần I theo người đứng đơn:
  họ tên, số CCCD, ngày sinh, giới tính, ngày cấp, nơi cấp, SĐT, email, địa chỉ (Đơn trước CCCD). Ghi lại họ tên / số
  CCCD trùng tài khoản là vô hại, còn đỡ trường hợp cổng không tự đổ.
- Nộp thay: chỉ lấy nhân thân từ CCCD KHỚP tài khoản; không có thẻ thì chỉ ghi lại họ tên / số theo tài khoản.
- ⚑ Cài đặt "Lấy người nộp theo tờ khai" (`options.submitterMode="owner_as_submitter"`, Auto Fill + trợ lý): bỏ mốc
  tài khoản, người nộp = người đứng đơn; khác tài khoản thì Họ tên + CCCD + ngày sinh phát kèm enableInput (cổng khoá
  theo VNeID), hồ sơ không có ngày sinh thì xoá ngày sinh của tài khoản.
- Tổ chức đứng đơn → data[chonDoiTuong] = "Tổ chức" (phát TRƯỚC để cổng mở panel) + panel thongTinDoanhNghiep.
- Hình thức nhận kết quả (bước 3, mat-select) không điền: chỉ cảnh báo khi Đơn chọn khác "Nhận trực tiếp" mặc định.
"""

from __future__ import annotations

from typing import Any

from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines.bao_cao_to_chuc_dai_hoi_hoi_cap_tinh.process.mapper import _date
from app.pipelines.cap_giay_phep_thi_cong_cong_trinh_tren_duong_bo_dang_khai_thac.process.schema import (
    UI_ALIASES,
    UI_COMP_BY_NAME,
)
from app.pipelines.cap_moi_chung_chi_hanh_nghe_moi_gioi_bat_dong_san.process.mapper import _province
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process.mapper import _person_matches
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.mapper import (
    _area,
    _by_name,
    _email,
    _fold,
    _gender,
    _gender_from_identity,
    _identity,
    _issuer,
    _phone,
    _text,
)


OWNER_AS_SUBMITTER = "owner_as_submitter"


def _person_id(value: Any) -> str | None:
    """CMND 9 / CCCD 12 số; loại số kiểu SĐT (10 số) LLM vớ nhầm từ dòng liên hệ của Đơn."""
    digits = _identity(value)
    return digits if digits and len(digits) in (9, 12) else None


def _issuer_or_default(value: Any, ngay_cap: str | None, identity: str | None) -> str | None:
    """Nơi cấp đọc được thì chuẩn hóa; CCCD 12 số có ngày cấp mà không đọc được nơi cấp → mặc định theo ngày cấp."""
    issuer = _issuer(value)
    if issuer:
        return issuer
    return default_issuer(ngay_cap) if ngay_cap and identity and len(identity) == 12 else None


def _nhan_ket_qua(value: Any) -> str | None:
    folded = _fold(value).replace("_", " ")
    if "truc tuyen" in folded or "online" in folded:
        return "truc_tuyen"
    if "buu" in folded:
        return "buu_chinh"
    if "truc tiep" in folded:
        return "truc_tiep"
    return None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[str] = set()

    def add(name: str, value, extra: dict | None = None) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value, **(extra or {})}
        if name in UI_ALIASES:
            field["aliases"] = list(UI_ALIASES[name])
        out.append(field)
        seen.add(name)

    def clear(name: str) -> None:
        # Cổng đổ sẵn giá trị của tài khoản VNeID, không phải của người theo tờ khai → xoá trắng + tô đỏ.
        if name in seen or name not in UI_COMP_BY_NAME:
            return
        out.append({"name": name, "comp": UI_COMP_BY_NAME[name], "value": "", "clear": True, "markEmpty": True})
        seen.add(name)

    def add_area(province_key: str, district_key: str, address_key: str, area: dict | None) -> bool:
        if not area:
            return False
        add(province_key, _province(area.get("tinh")))
        add(district_key, _text(area.get("xa")))
        add(address_key, _text(area.get("diaChi")))
        return True

    # --- Mốc tài khoản đăng nhập (extension gửi formContext) ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    has_ctx = bool(ctx_name or ctx_identity)

    # --- Tổ chức đứng đơn ---
    org_name = _text(values.get("ToChuc_Ten"))
    org_tax = _identity(values.get("ToChuc_MaSoThue"))
    is_to_chuc = "to chuc" in _fold(values.get("NguoiDeNghi_LoaiDoiTuong")) or bool(org_name)
    if is_to_chuc:
        add("data[chonDoiTuong]", "Tổ chức")

    # --- Phần I: người nộp hồ sơ ---
    name = _text(values.get("NguoiDeNghi_HoTen"))
    id_number = _person_id(values.get("NguoiDeNghi_SoDinhDanh"))
    has_person = bool(name or id_number)
    matches_account = has_ctx and has_person and _person_matches(name, id_number, ctx_name, ctx_identity)
    # Cài đặt "Lấy người nộp theo tờ khai": bỏ mốc tài khoản, người nộp = người đứng đơn.
    theo_to_khai = str((options or {}).get("submitterMode") or "") == OWNER_AS_SUBMITTER
    self_submit = has_person and (not has_ctx or matches_account or theo_to_khai)
    # Theo tờ khai mà người đứng đơn khác tài khoản → mở khoá Họ tên / CCCD / ngày sinh cổng khoá theo VNeID.
    override = self_submit and has_ctx and not matches_account
    unlock = {"enableInput": True} if override else None

    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_id = _person_id(values.get("NguoiNop_SoDinhDanh"))
    nop_ok = (not self_submit and has_ctx and bool(nop_name or nop_id)
              and _person_matches(nop_name, nop_id, ctx_name, ctx_identity))

    area_filled = False
    if self_submit:
        ngay_cap = _date(values.get("NguoiDeNghi_NgayCap"))
        add("data[fullname]", name, unlock)
        add("data[identityNumber]", id_number, unlock)
        add("data[birthday]", _date(values.get("NguoiDeNghi_NgaySinh")), unlock)
        if override:
            clear("data[birthday]")  # hồ sơ không có ngày sinh người đứng đơn → bỏ ngày sinh của tài khoản
        add("data[gender]", _gender(values.get("NguoiDeNghi_GioiTinh")))
        add("data[identityDate]", ngay_cap)
        add("data[identityAgency]", _issuer_or_default(values.get("NguoiDeNghi_NoiCap"), ngay_cap, id_number))
        add("data[email]", _email(values.get("NguoiDeNghi_Email")))
        add("data[phoneNumber]", _phone(values.get("NguoiDeNghi_DienThoai")))
        area_filled = add_area("data[province]", "data[district]", "data[address]",
                               _area(values.get("NguoiDeNghi_DiaChi")))
    elif nop_ok:
        ngay_cap = _date(values.get("NguoiNop_NgayCap"))
        add("data[fullname]", nop_name)
        add("data[identityNumber]", nop_id)
        add("data[gender]", _gender(values.get("NguoiNop_GioiTinh")))
        add("data[identityDate]", ngay_cap)
        add("data[identityAgency]", _issuer_or_default(values.get("NguoiNop_NoiCap"), ngay_cap, nop_id))
        add("data[phoneNumber]", _phone(values.get("NguoiNop_DienThoai")))
        area_filled = add_area("data[province]", "data[district]", "data[address]",
                               _area(values.get("NguoiNop_DiaChi")))
    if not override:
        add("data[fullname]", ctx_name)
        add("data[identityNumber]", ctx_identity)
    if area_filled:
        add("data[nation]", "Việt Nam")
    gender_id = (id_number if self_submit else None) or (None if override else ctx_identity)
    add("data[gender]", _gender_from_identity(gender_id))
    if override:
        warnings.append(f"Đang bật \"Lấy người nộp theo tờ khai\": phần người nộp ghi theo người đứng đơn "
                        f"({name or id_number}), khác tài khoản đăng nhập ({ctx_name or ctx_identity}) — kiểm tra lại "
                        "trước khi nộp.")

    # --- Phần II: panel thông tin doanh nghiệp ---
    if is_to_chuc:
        add("data[organization]", org_name)
        add("data[taxCode]", org_tax)
        add("data[organizationPhoneNumber]", _phone(values.get("ToChuc_DienThoai")))
        org_area = _area(values.get("ToChuc_DiaChi"))
        if org_area:
            add("data[nation1]", "Việt Nam")
            add_area("data[province1]", "data[district1]", "data[address1]", org_area)

    # --- Thông tin chi tiết: "Thông tin Tổ chức, cá nhân" = NGƯỜI ĐỨNG ĐƠN (không phụ thuộc tài khoản nộp) ---
    person_area = _area(values.get("NguoiDeNghi_DiaChi"))
    org_area = _area(values.get("ToChuc_DiaChi")) if is_to_chuc else None
    don_area = org_area or person_area
    person_phone = _phone(values.get("NguoiDeNghi_DienThoai"))
    add("data[container][organization]", (org_name if is_to_chuc else None) or name)
    don_area_filled = add_area("data[container][province]", "data[container][district]", "data[container][address]",
                               don_area)
    add("data[container][phoneNumber]",
        (_phone(values.get("ToChuc_DienThoai")) if is_to_chuc else None) or person_phone)
    # "Tại" (tỉnh nơi làm đơn, bắt buộc): cổng đổ sẵn theo tài khoản → ghi theo tỉnh của người đứng đơn.
    add("data[TinTTTe]", _province((person_area or don_area or {}).get("tinh")))
    add("data[kyTen]", name)

    # --- Cảnh báo ---
    if has_person and not don_area_filled:
        warnings.append("Chưa đọc được địa chỉ liên hệ của người đứng đơn — khối 'Thông tin Tổ chức, cá nhân': Tỉnh/TP, "
                        "Phường/xã (bắt buộc) vui lòng chọn tay.")
    warnings.append("Khối 'Thông tin công trình' (tên công trình, vị trí, thời gian thi công) chưa tự điền — vui lòng "
                    "nhập theo Đơn đề nghị.")
    if not has_person:
        warnings.append("Không đọc được người đứng đơn (CCCD / Đơn đề nghị cấp phép thi công) — kiểm tra lại Phần I "
                        "người nộp hồ sơ.")
    if has_ctx and has_person and not self_submit and not nop_ok:
        warnings.append("Người nộp (tài khoản đăng nhập) khác người đứng đơn và hồ sơ không có CCCD của người nộp — "
                        "vui lòng tự nhập ngày cấp, nơi cấp, số điện thoại, địa chỉ của người nộp.")
    if "data[phoneNumber]" not in seen:
        warnings.append("Hồ sơ không ghi số điện thoại của người nộp — ô Số điện thoại (bắt buộc) vui lòng nhập tay.")
    if has_person and not area_filled:
        warnings.append("Chưa đọc được địa chỉ người nộp — ô Tỉnh/TP, Phường/xã (bắt buộc) vui lòng chọn tay.")
    if is_to_chuc:
        warnings.append("Đơn do tổ chức đứng tên — đã chọn đối tượng 'Tổ chức' và điền thông tin doanh nghiệp, kiểm "
                        "tra lại.")
        if not org_name:
            warnings.append("Chưa đọc được tên tổ chức đứng đơn — ô Tên Doanh nghiệp/Hộ kinh doanh vui lòng nhập tay.")
    nhan = _nhan_ket_qua(values.get("Don_NhanKetQua"))
    if nhan == "truc_tuyen":
        warnings.append("Đơn chọn nhận kết quả TRỰC TUYẾN — bước 'Hình thức nhận kết quả' cổng để mặc định 'Nhận "
                        "trực tiếp', vui lòng chọn lại cho khớp đơn.")
    elif nhan == "buu_chinh":
        warnings.append("Đơn chọn nhận kết quả qua BƯU CHÍNH — chọn lại 'Hình thức nhận kết quả' ở bước 3 và kiểm tra "
                        "đơn đã ghi địa chỉ nhận.")
    return out, warnings
