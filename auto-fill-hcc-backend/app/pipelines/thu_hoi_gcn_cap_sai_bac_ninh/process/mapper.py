"""Map compact facts → UI field cho e-form Bắc Ninh (thu hồi GCN cấp sai & cấp lại)."""

import re

from app.pipelines.thu_hoi_gcn_cap_sai_bac_ninh.process import schema as S

# Chấm giữ chỗ của mẫu in ("tổ ... Tứ Cờ ....") và gạch ngăn cấp hành chính ("Tứ Cờ - Thuận Thành").
_PLACEHOLDER_DOTS_RE = re.compile(r"\s*(?:\.\s*){2,}|\s*…+\s*")
_DASH_SEP_RE = re.compile(r"\s+[–—-]\s+")


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in fields if f.get("value") not in (None, "", {}, [])}


def _text(value) -> str | None:
    if value in (None, "", {}, []):
        return None
    text = _PLACEHOLDER_DOTS_RE.sub(" ", str(value))
    return " ".join(text.split()).strip(" ,;") or None


def _digits(value) -> str | None:
    return re.sub(r"\D+", "", str(value or "")) or None


def _flatten(value) -> str | None:
    if isinstance(value, str):
        text = _PLACEHOLDER_DOTS_RE.sub(" ", value)
        text = _DASH_SEP_RE.sub(", ", text)
        text = " ".join(text.split())
        text = re.sub(r"\s+,", ",", text)
        return text.strip(" ,;.") or None
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


def _gcn_label(so_phat_hanh) -> str:
    so = _text(so_phat_hanh)
    return f"Giấy chứng nhận số {so}" if so else "Giấy chứng nhận"


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

    dia_chi = _flatten(v.get("Don_DiaChi"))
    ho_ten = _text(v.get("Cccd_HoTen"))
    so_dd = _digits(v.get("Cccd_SoDinhDanh"))
    phone = _digits(v.get("Don_DienThoai"))
    gcn = _gcn_label(v.get("Gcn_SoPhatHanh"))

    # 1. Người sử dụng đất: a) Họ và tên = tên chủ SDĐ trên GCN (dạng "Hộ ông…"); fallback họ tên CCCD.
    add(S.K_KINHGUI, _text(v.get("Don_KinhGui")))
    add(S.K_TEN, _text(v.get("TenChuSuDungDat")) or ho_ten)
    add(S.K_GIAYTO, _giay_to(so_dd, v.get("Cccd_NoiCap"), v.get("Cccd_NgayCap")))
    add(S.K_DIACHI, dia_chi)
    add(S.K_DIENTHOAI, phone)
    add(S.K_EMAIL, _text(v.get("Don_Email")))

    # 2. Thửa đất của GCN xin thu hồi. Tài sản gắn liền với đất (mục 3) để user tự khai nếu có.
    add(S.K_THUA, _text(v.get("Dat_ThuaSo")))
    add(S.K_TOBANDO, _text(v.get("Dat_ToBanDo")))
    add(S.K_DAT_DIACHI, _flatten(v.get("Dat_DiaChi")))
    add(S.K_DIENTICH, _text(v.get("Dat_DienTich")))
    add(S.K_SD_CHUNG, _text(v.get("Dat_SuDungChung")))
    add(S.K_SD_RIENG, _text(v.get("Dat_SuDungRieng")))
    add(S.K_MUCDICH, _text(v.get("Dat_MucDich")))
    add(S.K_TUTHOIDIEM, _text(v.get("Dat_TuThoiDiem")))
    add(S.K_THOIHAN, _text(v.get("Dat_ThoiHan")))
    add(S.K_NGUONGOC, _text(v.get("Dat_NguonGoc")))

    # 4. Đề nghị: thủ tục = thu hồi GCN cấp sai rồi cấp lại → d) nêu rõ việc thu hồi; a)+b) tick bên dưới.
    add(S.K_DENGHI_KHAC, f"Thu hồi {gcn} đã cấp lần đầu không đúng quy định và cấp lại Giấy chứng nhận")

    # 5. Giấy tờ nộp kèm = đúng 2 thành phần hồ sơ của thủ tục: văn bản kiến nghị + bản gốc GCN.
    kien_nghi = _text(v.get("Don_VanBanKienNghi"))
    add(S.K_KEM1, kien_nghi)
    add(S.K_KEM2, f"Bản gốc {gcn} đã cấp")

    # Người nhận (dùng họ tên CCCD thật, KHÔNG "Hộ ông").
    add(S.N_HOTEN, ho_ten)
    add(S.N_CCCD, so_dd)
    add(S.N_SDT, phone)
    add(S.N_DIACHI, dia_chi)

    # Checkbox "Đề nghị": cấp lại sau thu hồi = đăng ký đất đai + cấp Giấy chứng nhận (giống đăng ký
    # lần đầu). KHÔNG tick c) ghi nợ tiền sử dụng đất. value = cụm nhãn để FE khớp.
    out.append({
        "name": S.L_DENGHI, "comp": "bn-radio",
        "value": ["đề nghị đăng ký đất đai", "đề nghị cấp giấy chứng nhận"],
    })

    return out
