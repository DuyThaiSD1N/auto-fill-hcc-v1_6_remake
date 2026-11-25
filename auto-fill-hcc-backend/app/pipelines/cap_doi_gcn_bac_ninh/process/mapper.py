"""Map compact facts → UI field cho e-form Bắc Ninh (cấp đổi GCN).

Thân đơn khớp theo NHÃN (title đã fold); khối người nhận kết quả khớp theo NAME. Tự nộp →
người nhận kết quả = chính chủ hồ sơ (dùng lại Cccd_*/Don_*).
"""

import re
import unicodedata

from app.pipelines.cap_doi_gcn_bac_ninh.process import schema as S


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _flatten_address(value) -> str | None:
    """Don_DiaChi nên là chuỗi (fallback đã đảm bảo). Nếu lỡ là object → ghép ĐỦ phường/xã."""
    if isinstance(value, str):
        return " ".join(value.split()).strip(" ,;") or None
    if isinstance(value, dict):
        parts = [value.get(k) for k in ("diaChi", "xa", "phuong", "huyen", "quan", "tinh")]
        parts = [" ".join(str(p).split()) for p in parts if p]
        return ", ".join(dict.fromkeys(parts)) or None
    return None


def _giay_to_nhan_than(so: str | None, ngay: str | None, noi_cap: str | None) -> str | None:
    """Ghép "b) Giấy tờ nhân thân/pháp nhân" = "CCCD số {số}, cấp {ngày}, {nơi cấp}"."""
    so = (so or "").strip()
    if not so:
        return None
    parts = [f"CCCD số {so}"]
    if (ngay or "").strip():
        parts.append(f"cấp {ngay.strip()}")
    if (noi_cap or "").strip():
        parts.append(noi_cap.strip())
    return ", ".join(parts)


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text.casefold().replace("đ", "d"))
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _thanh_vien_ho(chep: str | None, theo_giay: str | None) -> str | None:
    """Dùng bản LLM đối chiếu giấy khác chỉ khi nó là CÙNG danh sách, mỗi người chỉ đổi tên chính lệch
    ít chữ (cùng họ + chữ đệm) — chặn trường hợp LLM thêm/bớt/đổi người."""
    if not isinstance(theo_giay, str) or not theo_giay.strip():
        return chep
    if not isinstance(chep, str) or not chep.strip():
        return chep
    sep = r"\s*[,;]\s*"
    a, b = re.split(sep, chep.strip()), re.split(sep, theo_giay.strip())
    if len(a) != len(b) or re.findall(r"[,;]", chep) != re.findall(r"[,;]", theo_giay):
        return chep
    for x, y in zip(a, b):
        wx, wy = x.split(), y.split()
        if len(wx) != len(wy) or not wx:
            return chep
        if [w.casefold() for w in wx[:-1]] != [w.casefold() for w in wy[:-1]]:
            return chep
        if _edit_distance(_fold(wx[-1]), _fold(wy[-1])) > 2:
            return chep
    return theo_giay.strip()


def enrich(fields: list[dict]) -> list[dict]:
    v = _by_name(fields)
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

    ho_ten = v.get("Cccd_HoTen")
    so_dd = v.get("Cccd_SoDinhDanh")
    phone = v.get("Don_DienThoai")
    dia_chi = _flatten_address(v.get("Don_DiaChi"))

    # Thân đơn (Đơn Mẫu 18).
    add(S.L_KINHGUI, v.get("Don_KinhGui"))
    add(S.L_TEN, ho_ten)
    add(S.L_GIAYTO, _giay_to_nhan_than(so_dd, v.get("Cccd_NgayCap"), v.get("Cccd_NoiCap")))
    add(S.L_DIACHI, dia_chi)
    add(S.L_MST, v.get("Don_MaSoThue"))
    add(S.L_DIENTHOAI, phone)
    add(S.L_EMAIL, v.get("Don_Email"))
    add(S.L_NOIDUNG, v.get("Don_NoiDungBienDong"))
    add(S.L_GIAYTO2, v.get("Don_GiayTo2"))
    add(S.L_GIAYTO3, v.get("Don_GiayTo3"))
    # Mục V - Cam kết của chủ sử dụng đất.
    add(S.L_THANHVIEN, _thanh_vien_ho(v.get("Don_ThanhVienHo"), v.get("Don_ThanhVienHo_TheoGiayTo")))
    add(S.L_TRANHCHAP, v.get("Don_TinhTrangTranhChap"))
    add(S.L_RANHGIOI, v.get("Don_ThayDoiRanhGioi"))

    # Người nhận kết quả (tự nộp → cùng người đứng đơn). Tỉnh/phường người nhận là select cascade,
    # để user chọn tay theo địa bàn.
    add(S.N_HOTEN, ho_ten)
    add(S.N_CCCD, so_dd)
    add(S.N_SDT, phone)
    add(S.N_DIACHI, dia_chi)

    return out
