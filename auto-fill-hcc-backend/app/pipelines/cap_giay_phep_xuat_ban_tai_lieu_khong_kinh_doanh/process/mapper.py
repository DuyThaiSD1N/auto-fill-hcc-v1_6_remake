"""Map facts → UI fields (section, mat-label) cho engine fill-liz.js — cấp GPXB tài liệu không KD.

Mỗi field emit {name=<mat-label>, comp, value, section=<group-header>}; nhãn LẶP giữa các section
(Ngày sinh/Ngày cấp/Nơi cấp/Địa chỉ/Email/Cơ quan cấp) nên `section` là bắt buộc.

Ba vai đi vào ba section khác nhau: người nộp → Phần II, tổ chức đề nghị → Phần III, cơ sở in →
Phần IV. Phần V lấy nội dung Đơn Mẫu 04 và tên/địa chỉ cơ sở in.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.area_remap import remap_area
from app.pipelines._shared.compact_agent.issuer import normalize_issuer
from app.pipelines._shared.formatting import normalize_date
from app.pipelines.cap_giay_phep_xuat_ban_tai_lieu_khong_kinh_doanh.process.schema import (
    COMP_BY_UI,
    S_DN,
    S_DON,
    S_GQ,
    S_NOP,
)


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value: Any) -> str | None:
    if value in (None, "", {}, []) or isinstance(value, dict):
        return None
    text = " ".join(str(value).replace("\n", " ").split()).strip(" :;,-")
    return text or None


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _strip_admin_prefix(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.sub(
        r"^(xã|phường|thị trấn|tt\.?|tỉnh|thành phố|tp\.?|huyện|quận|thị xã)\s+",
        "", text, flags=re.IGNORECASE,
    ).strip()


def _province_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    if folded.startswith(("tinh ", "thanh pho ", "tp ")):
        return text
    city_markers = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hue"}
    return f"{'Thành phố' if folded in city_markers else 'Tỉnh'} {_strip_admin_prefix(text)}"


def _commune_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    return text if folded.startswith(("xa ", "phuong ", "thi tran ", "dac khu ")) else f"Phường {text}"


def _area(value: Any) -> dict | None:
    if isinstance(value, str):
        text = _text(value)
        return {"tinh": "", "xa": "", "diaChi": text} if text else None
    if not isinstance(value, dict):
        return None
    out = {
        "tinh": value.get("tinh") or value.get("tinhThanh") or "",
        "xa": value.get("xa") or value.get("phuong") or "",
        "diaChi": value.get("diaChi") or value.get("diachi") or value.get("chiTiet") or "",
    }
    if not any(out.values()):
        return None
    return remap_area(out, allow_diachi_fallback=True)


def _full_address(area: dict | None) -> str | None:
    if not area:
        return None
    parts = [_text(area.get("diaChi")), _commune_label(area.get("xa")), _province_label(area.get("tinh"))]
    return ", ".join(p for p in parts if p) or None


def _phone(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if text.lstrip().startswith("+84") and digits.startswith("84"):
        digits = "0" + digits[2:]
    return digits if 9 <= len(digits) <= 11 else None


def _date(value: Any) -> str | None:
    """Chỉ nhận ngày ĐỦ ngày/tháng/năm — chỉ có năm thì bỏ, không ghép 01/01."""
    text = _text(value)
    if not text:
        return None
    normalized = normalize_date(text)
    return normalized if normalized and re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", normalized) else None


def _identity(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return re.sub(r"\D", "", text) or None


def _tax_code(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return re.sub(r"[^0-9-]", "", text).strip("-") or None


def _issuer(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    folded = _fold(text)
    return normalize_issuer(text) if ("canh sat" in folded or "cong an" in folded) else text


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    del options
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []

    def put(section: str, label: str, value) -> None:
        if value in (None, "", {}, []):
            return
        comp = COMP_BY_UI.get((section, label))
        if not comp:
            return
        out.append({"name": label, "comp": comp, "value": value, "section": section})

    # ---- Phần II: NGƯỜI NỘP (Tên + CMND + Địa chỉ hành chính bị cổng khoá → không phát) ----
    nop_area = _area(values.get("NguoiNop_NoiCuTru"))
    put(S_NOP, "Ngày sinh", _date(values.get("NguoiNop_NgaySinh")))
    put(S_NOP, "Số điện thoại", _phone(values.get("NguoiNop_DienThoai")))
    put(S_NOP, "Email", _text(values.get("NguoiNop_Email")))
    put(S_NOP, "Ngày cấp", _date(values.get("NguoiNop_NgayCapCccd")))
    put(S_NOP, "Nơi cấp", _issuer(values.get("NguoiNop_NoiCapCccd")))
    put(S_NOP, "Địa chỉ", _text(nop_area.get("diaChi")) if nop_area else None)

    # ---- Phần III: TỔ CHỨC ĐỀ NGHỊ cấp phép (KHÔNG phải cơ sở in) ----
    to_chuc_ten = _text(values.get("ToChucDeNghi_Ten"))
    to_chuc_area = _area(values.get("ToChucDeNghi_DiaChi"))
    put(S_GQ, "Tên người / Tên đơn vị được giải quyết", to_chuc_ten)
    put(S_GQ, "Số điện thoại", _phone(values.get("ToChucDeNghi_DienThoai")))
    put(S_GQ, "Email", _text(values.get("ToChucDeNghi_Email")))
    # Ô "Địa chỉ" của khối này là một dòng text tự do → ghi địa chỉ ĐẦY ĐỦ vì ô "Địa chỉ hành chính"
    # bên cạnh bị cổng khoá, không có chỗ nào khác mang phường/tỉnh.
    put(S_GQ, "Địa chỉ", _full_address(to_chuc_area))

    # ---- Phần IV: CƠ SỞ IN ----
    in_truso = _area(values.get("CoSoIn_TruSo"))
    in_ten = _text(values.get("CoSoIn_TenTiengViet"))
    put(S_DN, "Mã số thuế", _tax_code(values.get("CoSoIn_MaSoThue")))
    put(S_DN, "Cơ quan cấp", _text(values.get("CoSoIn_CoQuanCap")))
    put(S_DN, "Đăng ký lần đầu", _date(values.get("CoSoIn_NgayDangKyLanDau")))
    put(S_DN, "Ngày đăng ký thay đổi", _date(values.get("CoSoIn_NgayDangKyThayDoi")))
    put(S_DN, "Tên tiếng việt", in_ten)
    put(S_DN, "Tên nước ngoài", _text(values.get("CoSoIn_TenNuocNgoai")))
    put(S_DN, "Tên viết tắt", _text(values.get("CoSoIn_TenVietTat")))
    put(S_DN, "Điện thoại", _phone(values.get("CoSoIn_DienThoai")))
    put(S_DN, "Fax", _text(values.get("CoSoIn_Fax")))
    put(S_DN, "Email", _text(values.get("CoSoIn_Email")))
    put(S_DN, "Website", _text(values.get("CoSoIn_Website")))
    if in_truso:
        put(S_DN, "Địa chỉ trụ sở - Tỉnh/TP", _province_label(in_truso.get("tinh")))
        put(S_DN, "Địa chỉ trụ sở - Xã", _commune_label(in_truso.get("xa")))
        put(S_DN, "Địa chỉ chi tiết trụ sở", _text(in_truso.get("diaChi")))
    put(S_DN, "Số CCCD người đại diện pháp luật", _identity(values.get("CoSoIn_NguoiDaiDien_SoDinhDanh")))
    put(S_DN, "Tên người đại diện pháp luật", _text(values.get("CoSoIn_NguoiDaiDien_HoTen")))
    put(S_DN, "Địa chỉ người đại diện pháp luật", _full_address(_area(values.get("CoSoIn_NguoiDaiDien_DiaChi"))))

    # ---- Phần V: nội dung Đơn Mẫu 04 ----
    put(S_DON, "TÊN CƠ QUAN CHỦ QUẢN (NẾU CÓ)", _text(values.get("ToChucDeNghi_CoQuanChuQuan")))
    put(S_DON, "Số GCN đăng ký kinh doanh/ GCN đầu tư/ GCN đăng ký doanh nghiệp (đối với doanh nghiệp)",
        _text(values.get("ToChucDeNghi_SoGcnDangKyKinhDoanh")))
    put(S_DON, "Số quyết định thành lập (đối với đơn vị sự nghiệp công lập)",
        _text(values.get("ToChucDeNghi_SoQuyetDinhThanhLap")))
    put(S_DON, "Số giấy phép hoạt động (đối với cơ quan, tổ chức nước ngoài)",
        _text(values.get("ToChucDeNghi_SoGiayPhepHoatDong")))
    put(S_DON, "Cơ quan cấp", _text(values.get("ToChucDeNghi_CoQuanCapGiayTo")))
    put(S_DON, "Ngày cấp", _date(values.get("ToChucDeNghi_NgayCapGiayTo")))
    put(S_DON, "Tên tài liệu", _text(values.get("TaiLieu_Ten")))
    put(S_DON, "Xuất xứ (nếu là tài liệu dịch từ tiếng nước ngoài)", _text(values.get("TaiLieu_XuatXu")))
    put(S_DON, "Người dịch (cá nhân hoặc tập thể)", _text(values.get("TaiLieu_NguoiDich")))
    put(S_DON, "Hình thức tài liệu", _text(values.get("TaiLieu_HinhThuc")))
    put(S_DON, "Số trang (hoặc dung lượng - byte)", _text(values.get("TaiLieu_SoTrang")))
    put(S_DON, "Phụ bản (nếu có)", _text(values.get("TaiLieu_PhuBan")))
    put(S_DON, "Khuôn khổ (định dạng) (cm)", _text(values.get("TaiLieu_KhuonKho")))
    put(S_DON, "Số lượng in (bản)", _text(values.get("TaiLieu_SoLuongIn")))
    put(S_DON, "Ngôn ngữ xuất bản", _text(values.get("TaiLieu_NgonNgu")))
    # Mục 8 của đơn thường trùng khối cơ sở in — đơn không ghi thì dùng lại dữ liệu GCN ĐKDN.
    put(S_DON, "Tên cơ sở in", _text(values.get("TaiLieu_TenCoSoIn")) or in_ten)
    put(S_DON, "Địa chỉ cơ sở in",
        _text(values.get("TaiLieu_DiaChiCoSoIn")) or _full_address(in_truso))
    put(S_DON, "Mục đích xuất bản", _text(values.get("TaiLieu_MucDichXuatBan")))
    put(S_DON, "Nội dung tóm tắt của tài liệu", _text(values.get("TaiLieu_TomTatNoiDung")))
    put(S_DON, "Kèm theo đơn này gồm", _text(values.get("TaiLieu_KemTheoDon")))

    if not to_chuc_ten:
        warnings.append(
            "Không đọc được tên cơ quan/tổ chức ĐỀ NGHỊ cấp giấy phép (mục 1 Đơn Mẫu 04) — cán bộ nhập "
            "tay ô \"Tên người / Tên đơn vị được giải quyết\". Không dùng tên công ty in thay vào."
        )
    if not _text(values.get("TaiLieu_Ten")):
        warnings.append("Không đọc được tên tài liệu xin cấp phép (mục 3 Đơn Mẫu 04) — cán bộ nhập tay.")
    return out, warnings
