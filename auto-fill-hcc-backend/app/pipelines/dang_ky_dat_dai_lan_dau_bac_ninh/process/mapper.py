"""Map compact facts → UI field cho e-form Bắc Ninh (đăng ký đất đai, cấp GCN lần đầu)."""

from app.pipelines.dang_ky_dat_dai_lan_dau_bac_ninh.process import schema as S


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
        if name in seen or value in (None, "", {}, []):
            return
        comp = S.UI_COMP_BY_NAME.get(name)
        if not comp:
            return
        out.append({"name": name, "comp": comp, "value": value})
        seen.add(name)

    dia_chi = _flatten(v.get("Don_DiaChi"))
    ho_ten = v.get("Cccd_HoTen")
    so_dd = v.get("Cccd_SoDinhDanh")
    phone = v.get("Don_DienThoai")

    # Thân đơn (Phần II).
    add(S.L_KINHGUI, v.get("Don_KinhGui"))
    add(S.L_HOTEN, ho_ten)
    add(S.L_GIAYTO, _giay_to(so_dd, v.get("Cccd_NoiCap"), v.get("Cccd_NgayCap")))
    add(S.L_DIACHI, dia_chi)
    add(S.L_DIENTHOAI, phone)
    add(S.L_DAT_DIACHI, _flatten(v.get("Dat_DiaChi")))
    add(S.L_DAT_DIENTICH, v.get("Dat_DienTich"))
    add(S.L_SD_CHUNG, v.get("Dat_SuDungChung"))
    add(S.L_SD_RIENG, v.get("Dat_SuDungRieng"))
    add(S.L_MUCDICH, v.get("Dat_MucDich"))
    add(S.L_TUTHOIDIEM, v.get("Dat_TuThoiDiem"))
    add(S.L_THOIHAN, v.get("Dat_ThoiHan"))
    add(S.L_NGUONGOC, v.get("Dat_NguonGoc"))
    # Mục 5 "Những giấy tờ nộp kèm theo": (1)(2)(3) = danh sách giấy tờ đính kèm (KHÔNG phải chú thích).
    add(S.L_KT1, v.get("Don_KemTheo1"))
    add(S.L_KT2, v.get("Don_KemTheo2"))
    add(S.L_KT3, v.get("Don_KemTheo3"))
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
