"""Map compact facts → UI field cho e-form Bắc Ninh (Xóa đăng ký biện pháp bảo đảm bằng QSDĐ).

Ô eForm khớp theo class `eform-element-<Key>` (name UI = <Key>). Radio tick theo nhãn option.
"""

import re
import unicodedata

from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_bac_ninh.process import schema as S


def _fold(text: str) -> str:
    t = (text or "").replace("Đ", "D").replace("đ", "d")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(t.lower().split())


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _flatten(value) -> str | None:
    if isinstance(value, str):
        return " ".join(value.split()).strip(" ,;") or None
    if isinstance(value, dict):
        parts = [value.get(k) for k in ("diaChi", "chiTiet", "xa", "phuong", "huyen", "quan", "tinh")]
        parts = [" ".join(str(p).split()) for p in parts if p]
        return ", ".join(dict.fromkeys(parts)) or None
    return None


# Tư cách người yêu cầu (NĐ 99/2022) → nhãn option radio trên eForm (TT 07/2019). Thứ tự QUAN TRỌNG:
# "bên nhận bảo đảm" phải xét TRƯỚC "bên bảo đảm" (chuỗi con).
def _tu_cach_option(raw: str | None) -> str:
    h = _fold(raw or "")
    if "nhan bao dam" in h or "nhan the chap" in h:
        return "Bên nhận thế chấp"
    if "dai dien" in h:
        return "Người đại diện của bên thế chấp, bên nhận thế chấp"
    if "quan tai vien" in h:
        return "Quản tài viên"
    if "mua tai san thi hanh an" in h:
        return "Người mua tài sản thi hành án"
    if "to chuc thi hanh an" in h:
        return "Tổ chức thi hành án dân sự"
    # Mặc định (đa số hồ sơ): bên bảo đảm ⇔ bên thế chấp.
    return "Bên thế chấp"


def _tai_lieu_kem(v: dict) -> str | None:
    """Mục 5 'Tài liệu kèm theo' — ưu tiên bản khai; nếu thiếu, ghép mô tả GCN."""
    kem = _flatten(v.get("Don_TaiLieuKemTheo"))
    if kem:
        return kem
    so_ph = (v.get("Gcn_SoPhatHanh") or "").strip()
    if not so_ph:
        return None
    parts = ["Giấy chứng nhận quyền sử dụng đất, quyền sở hữu nhà ở và tài sản khác gắn liền với đất"]
    parts.append(f"số phát hành {so_ph}")
    if (v.get("Gcn_SoVaoSo") or "").strip():
        parts.append(f"số vào sổ cấp GCN {v['Gcn_SoVaoSo'].strip()}")
    cq = (v.get("Gcn_CoQuanCap") or "").strip()
    ngay = (v.get("Gcn_NgayCap") or "").strip()
    if cq or ngay:
        tail = cq
        if ngay:
            tail = f"{tail} cấp ngày {ngay}" if tail else f"cấp ngày {ngay}"
        parts.append(tail)
    return "; ".join(parts)


def _truthy(value) -> bool:
    if value is True or value == 1:
        return True
    return str(value or "").strip().lower() in {"true", "yes", "co", "có", "1"}


def _authorized_fields(v: dict) -> list[dict]:
    """Khối 'Thông tin trong trường hợp được ủy quyền' (nút 'Điền thông tin người ủy quyền').

    Chỉ phát khi hồ sơ có Văn bản ủy quyền + đủ họ tên & CCCD người được ủy quyền."""
    if not _truthy(v.get("UyQuyen_CoVanBan")):
        return []
    name = " ".join(str(v.get("NguoiDuocUyQuyen_HoTen") or "").split()).strip()
    identity = re.sub(r"\D+", "", str(v.get("NguoiDuocUyQuyen_SoDinhDanh") or ""))
    if not name or not identity:
        return []

    out: list[dict] = []

    def add(key: str, value, comp: str = "bn-input") -> None:
        value = " ".join(str(value or "").split()).strip() if not isinstance(value, dict) else value
        if value in (None, "", {}, []):
            return
        out.append({"name": key, "comp": comp, "value": value})

    add("doiTuongKhachoTen", name)
    add("doiTuongKhacgioiTinhId", v.get("NguoiDuocUyQuyen_GioiTinh"), "bn-select")
    add("doiTuongKhacsoDinhDanh", identity)
    add("doiTuongKhacngayCap", v.get("NguoiDuocUyQuyen_NgayCap"))
    add("doiTuongKhacnoiCap", v.get("NguoiDuocUyQuyen_NoiCap"))
    add("doiTuongKhacngaySinh", v.get("NguoiDuocUyQuyen_NgaySinh"))
    add("doiTuongKhacemail", v.get("NguoiDuocUyQuyen_Email"))
    add("doiTuongKhacsoDienThoai", v.get("NguoiDuocUyQuyen_SoDienThoai"))
    address = v.get("NguoiDuocUyQuyen_ThuongTru")
    if isinstance(address, dict):
        add("doiTuongKhactinhThanhId", address.get("tinh"), "bn-select")
        add("doiTuongKhacphuongXaId", address.get("xa"), "bn-select")
        add("doiTuongKhacdiaChiChiTiet", address.get("diaChi"))
    return out


def enrich(fields: list[dict], options: dict | None = None) -> list[dict]:
    v = _by_name(fields)
    # Nút "Điền thông tin người ủy quyền" gọi lại pipeline với purpose=authorized_person.
    if str((options or {}).get("purpose") or "registration_form") == "authorized_person":
        return _authorized_fields(v)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        if name in seen or value in (None, "", {}, []):
            return
        comp = S.UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    ho_ten = v.get("NguoiYeuCau_HoTen")
    ten_day_du = v.get("NguoiYeuCau_TenDayDu") or ho_ten
    so_dd = v.get("NguoiYeuCau_SoDinhDanh")
    dia_chi = _flatten(v.get("NguoiYeuCau_DiaChi"))
    dien_thoai = v.get("NguoiYeuCau_DienThoai")
    kinh_gui = v.get("Don_KinhGui")

    # --- Bước 1: cơ quan tiếp nhận (select theo địa bàn — FE khớp text, không khớp thì chọn tay) ---
    add(S.N_DONVI, kinh_gui)

    # --- Bước 2: eForm phiếu yêu cầu xóa ---
    add(S.K_KINHGUI, kinh_gui)
    add(S.K_TUCACH, [_tu_cach_option(v.get("NguoiYeuCau_TuCach"))])  # radio: tick 1 nhãn
    add(S.K_TENDAYDU, ten_day_du)
    add(S.K_DIACHILH, dia_chi)
    add(S.K_SDT, dien_thoai)
    add(S.K_LOAIGT, ["Chứng minh nhân dân/Căn cước công dân/Chứng minh QĐND"])  # mặc định CCCD
    add(S.K_SO_NYC, so_dd)
    add(S.K_COQUANCAP_NYC, v.get("NguoiYeuCau_NoiCap"))
    add(S.K_CAPNGAY_NYC, v.get("NguoiYeuCau_NgayCap"))

    # Mục 2.1 — QSDĐ
    add(S.K_THUADAT, v.get("Gcn_ThuaDatSo"))
    add(S.K_TOBANDO, v.get("Gcn_ToBanDoSo"))
    add(S.K_MUCDICH, v.get("Gcn_MucDichSuDung"))
    add(S.K_THOIHAN, v.get("Gcn_ThoiHanSuDung"))
    add(S.K_DIACHITHUADAT, _flatten(v.get("Gcn_DiaChiThuaDat")))
    add(S.K_DIENTICH, re.sub(r"[^\d]", "", str(v.get("Gcn_DienTich") or "")) or None)
    add(S.K_BANGCHU, v.get("Gcn_DienTichBangChu"))
    add(S.K_SOPHATHANH, v.get("Gcn_SoPhatHanh"))
    add(S.K_SOVAOSO, v.get("Gcn_SoVaoSo"))
    add(S.K_COQUANCAP_GCN, v.get("Gcn_CoQuanCap"))
    add(S.K_CAPNGAY_GCN, v.get("Gcn_NgayCap"))

    # Mục 3, 5, 7
    add(S.K_HDTC_SO, v.get("TheChap_SoHopDong"))
    add(S.K_HDTC_NGAY, v.get("TheChap_NgayKy"))
    add(S.K_TAILIEUKEM, _tai_lieu_kem(v))
    add(S.K_PHUONGTHUC, ["Nhận trực tiếp"])  # mặc định

    # --- Bước 4: nơi nhận kết quả (mặc định tại nơi nộp hồ sơ) ---
    add(S.K_NOINHAN, ["Tại nơi nộp hồ sơ"])

    return out
