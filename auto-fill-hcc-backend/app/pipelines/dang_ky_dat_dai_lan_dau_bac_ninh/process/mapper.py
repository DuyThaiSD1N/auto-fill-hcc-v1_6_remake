"""Map compact facts → UI field cho e-form Bắc Ninh (đăng ký đất đai, cấp GCN lần đầu)."""

import re

from app.pipelines.dang_ky_dat_dai_lan_dau_bac_ninh.process import schema as S

# Vạch ngắt trang OCR ("───── Trang 2/2 ─────") hay dính vào cuối ô văn bản dài.
_PAGE_MARK_RE = re.compile(r"[─━—-]{3,}\s*Trang\s*\d+\s*/\s*\d+\s*[─━—-]{3,}", re.IGNORECASE)
# Dòng chấm chừa chỗ trống của mẫu đơn ("....68....", "…").
_FILLER_RE = re.compile(r"\.{2,}|…+|_{2,}")
# Chỉ còn đơn vị in sẵn trên mẫu (".... m²" → "m²") thì ô coi như trống.
_UNIT_ONLY_RE = re.compile(r"m²|m2|\btầng\b", re.IGNORECASE)


def _clean(value):
    """Bỏ vạch ngắt trang + dòng chấm của mẫu; ô chỉ còn đơn vị/dấu câu → None (để trống)."""
    if not isinstance(value, str):
        return value
    s = _FILLER_RE.sub(" ", _PAGE_MARK_RE.sub(" ", value))
    s = " ".join(s.split()).strip(" ,;:")
    if not re.search(r"\w", _UNIT_ONLY_RE.sub("", s)):
        return None
    return s


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _flatten(value) -> str | None:
    if isinstance(value, str):
        return " ".join(value.split()).strip(" ,;") or None
    if isinstance(value, dict):
        parts = [value.get(k) for k in ("diaChi", "xa", "phuong", "huyen", "quan", "tinh")]
        parts = [" ".join(str(p).split()) for p in parts if p]
        return ", ".join(dict.fromkeys(parts)) or None
    return None


def _giay_to(so, noi_cap, ngay) -> str | None:
    so = (so or "").strip()
    if not so:
        return None
    out = f"CCCD số {so}"
    if (noi_cap or "").strip():
        out += f" do {noi_cap.strip()}"
    if (ngay or "").strip():
        out += f" cấp ngày {ngay.strip()}"
    return out


def enrich(fields: list[dict]) -> list[dict]:
    v = _by_name(fields)
    out: list[dict] = []
    seen: set[str] = set()

    def add(name: str, value) -> None:
        value = _clean(value)
        if name in seen or value in (None, "", {}, []):
            return
        comp = S.UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    dia_chi = _clean(_flatten(v.get("Don_DiaChi")))
    ho_ten = _clean(v.get("Cccd_HoTen"))
    so_dd = _clean(v.get("Cccd_SoDinhDanh"))
    phone = _clean(v.get("Don_DienThoai"))

    # Thân đơn (Phần II).
    add(S.L_KINHGUI, v.get("Don_KinhGui"))
    add(S.L_HOTEN, ho_ten)
    add(S.L_GIAYTO, _giay_to(so_dd, _clean(v.get("Cccd_NoiCap")), _clean(v.get("Cccd_NgayCap"))))
    add(S.L_DIACHI, dia_chi)
    add(S.L_DIENTHOAI, phone)
    add(S.C_EMAIL, v.get("Don_Email"))
    add(S.C_THUA_SO, v.get("Dat_ThuaSo"))
    add(S.C_TO_BAN_DO, v.get("Dat_ToBanDo"))
    add(S.L_DAT_DIACHI, _flatten(v.get("Dat_DiaChi")))
    add(S.L_DAT_DIENTICH, v.get("Dat_DienTich"))
    add(S.L_SD_CHUNG, v.get("Dat_SuDungChung"))
    add(S.L_SD_RIENG, v.get("Dat_SuDungRieng"))
    add(S.L_MUCDICH, v.get("Dat_MucDich"))
    add(S.L_TUTHOIDIEM, v.get("Dat_TuThoiDiem"))
    add(S.L_THOIHAN, v.get("Dat_ThoiHan"))
    add(S.L_NGUONGOC, v.get("Dat_NguonGoc"))
    # Mục 3 nhà ở, công trình xây dựng.
    add(S.C_NHA_LOAI, v.get("Nha_Loai"))
    add(S.C_NHA_DT_XD, v.get("Nha_DienTichXayDung"))
    add(S.C_NHA_DT_SAN, v.get("Nha_DienTichSan"))
    add(S.C_NHA_SH_CHUNG, v.get("Nha_SoHuuChung"))
    add(S.C_NHA_SH_RIENG, v.get("Nha_SoHuuRieng"))
    add(S.C_NHA_SO_TANG, v.get("Nha_SoTang"))
    add(S.C_NHA_TANG_NOI, v.get("Nha_SoTangNoi"))
    add(S.C_NHA_TANG_HAM, v.get("Nha_SoTangHam"))
    add(S.C_NHA_NGUON_GOC, v.get("Nha_NguonGoc"))
    add(S.C_NHA_NAM_HT, v.get("Nha_NamHoanThanh"))
    add(S.C_NHA_THOI_HAN, v.get("Nha_ThoiHanSoHuu"))
    # Mục 5 "Những giấy tờ nộp kèm theo": (1)(2) = danh sách giấy tờ đính kèm (KHÔNG phải chú thích).
    # Form chỉ còn 2 ô → giấy tờ (3) nối vào sau (2).
    add(S.L_KT1, v.get("Don_KemTheo1"))
    kem_theo_sau = [_clean(v.get(k)) for k in ("Don_KemTheo2", "Don_KemTheo3")]
    add(S.L_KT2, "; ".join(x for x in kem_theo_sau if x))
    add(S.L_NOIKHAI, v.get("Don_NoiKhai"))

    # Người nhận kết quả (Phần IV) — mặc định = người đề nghị (bỏ luồng ủy quyền theo yêu cầu).
    add(S.N_HOTEN, ho_ten)
    add(S.N_CCCD, so_dd)
    add(S.N_SDT, phone)
    add(S.N_DIACHI, dia_chi)

    # Radio "Đề nghị (a/b/c)": mặc định tick a) đăng ký đất đai + b) cấp Giấy chứng nhận.
    # value = danh sách CỤM NHÃN để FE khớp radio (không phụ thuộc id/value cứng).
    out.append({
        "name": S.L_DENGHI, "comp": "bn-radio",
        "value": ["đăng ký đất đai", "cấp Giấy chứng nhận"],
    })

    return out
