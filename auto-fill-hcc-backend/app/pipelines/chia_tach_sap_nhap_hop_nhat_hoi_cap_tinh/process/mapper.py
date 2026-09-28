"""Map compact source facts → Form.io data[...] fields cho "Thủ tục chia, tách; sáp nhập; hợp nhất hội (cấp tỉnh)"
(1.012945, cổng DVCQG).

Theo mapping của thủ tục:
- Phần I người nộp: data[fullname] / data[birthday] / data[identityNumber] / data[chonDoiTuong] cổng khoá theo tài
  khoản → KHÔNG phát. Giới tính, ngày cấp, nơi cấp, địa chỉ chỉ lấy từ CCCD KHỚP tài khoản (không có tài khoản thì
  khớp người được BCH giao làm thủ tục).
- Phần II chủ hồ sơ = Chủ tịch dự kiến (CCCD → Phiếu LLTP số 1). data[isOwnerDossierCheck] tích khi chủ hồ sơ
  chính là người nộp, còn lại bỏ tích.
- Phần III datagrid "Hồ sơ kèm theo gồm": mỗi giấy tờ trong hồ sơ một dòng, Loại bản "Bản chính".
- Phần IV: data[noiGui] = tỉnh ở dòng "Kính gửi"; data[ChonTruongHop] mở MỘT trong 4 fieldset, các ô còn lại điền
  theo bộ field-key của fieldset đó (MAU_DON). Mẫu tách trùng field-key Phần I → gắn scope fieldset2.
"""

from __future__ import annotations

import re
from typing import Any

from app.pipelines._shared.area_remap import province_label
from app.pipelines.chia_tach_sap_nhap_hop_nhat_hoi_cap_tinh.process.schema import (
    MAU_DON,
    MAU_DON_COMP,
    MAX_HO_SO_ROWS,
    NGUOI_NOP_MARKERS,
    TACH_SCOPE,
    TACH_SCOPE_NEAR,
    UI_COMP_BY_NAME,
)
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.mapper import (
    _area,
    _by_name,
    _date,
    _fold,
    _gender,
    _identity,
    _issuer,
    _phone,
    _same_name,
    _text,
)

_NGHI_DINH_HOI = "126/2024/NĐ-CP"
_NGAY_NGHI_DINH_HOI = "08/10/2024"
_TACH_SCOPED_ROLES = ("ho_ten", "dien_thoai", "tinh", "xa", "dia_chi")
_NOTE_RE = re.compile(r"\s*\((?:mới|cũ|moi|cu)\)\s*$", re.IGNORECASE)


def _names(value: Any) -> list[str]:
    """Mảng tên hội / giấy tờ → list chuỗi sạch (bỏ chú thích "(mới)"/"(cũ)" cuối tên, bỏ trùng)."""
    items = value if isinstance(value, list) else [value] if value not in (None, "") else []
    out: list[str] = []
    for item in items:
        if isinstance(item, dict):
            item = item.get("ten") or item.get("name") or item.get("value") or ""
        text = _text(item)
        if not text:
            continue
        text = _NOTE_RE.sub("", text).strip()
        if text and not any(_same_name(text, seen) for seen in out):
            out.append(text)
    return out


def _paper_names(value: Any) -> list[str]:
    """Danh mục giấy tờ: giữ nguyên chú thích (vd "(dự thảo)"), chỉ bỏ số thứ tự đầu dòng và CCCD lọt vào."""
    items = value if isinstance(value, list) else [value] if value not in (None, "") else []
    out: list[str] = []
    for item in items:
        if isinstance(item, dict):
            item = item.get("ten") or item.get("name") or item.get("value") or ""
        text = _text(item)
        if not text:
            continue
        text = re.sub(r"^\s*(?:\d{1,2}\s*[).:-]|[-–•+])\s*", "", text).strip()
        folded = _fold(text)
        if not text or "can cuoc" in folded or "cccd" in folded or "chung minh nhan dan" in folded:
            continue
        if text not in out:
            out.append(text)
    return out


def _multiline(value: Any) -> str | None:
    """Textarea: giữ xuống dòng giữa các đoạn, gộp khoảng trắng trong từng đoạn."""
    if value in (None, "", {}, []):
        return None
    if isinstance(value, list):
        value = "\n".join(str(v) for v in value if v)
    lines = [" ".join(line.split()) for line in str(value).replace("\r", "").split("\n")]
    text = "\n".join(line for line in lines if line).strip()
    return text or None


def _loai(value: Any, tham_gia: list[str], moi: list[str]) -> tuple[str | None, bool]:
    """(khoá MAU_DON, có_mơ_hồ). Hồ sơ ghi gộp "sáp nhập, hợp nhất" → hợp nhất (mẫu hồ sơ thực tế đều bầu BCH mới,
    Điều lệ mới); không đọc được loại thì suy theo số hội."""
    folded = _fold(value)
    has_sap = "sap nhap" in folded
    has_hop = "hop nhat" in folded
    if has_sap and has_hop:
        return "hop_nhat", True
    if has_hop:
        return "hop_nhat", False
    if has_sap:
        return "sap_nhap", False
    if re.search(r"\btach\b", folded):
        return "tach", False
    if re.search(r"\bchia\b", folded):
        return "chia", False
    if len(moi) >= 2 and len(tham_gia) <= 1:
        return "chia", True
    if len(tham_gia) >= 2:
        continues = bool(moi) and any(_same_name(moi[0], t) for t in tham_gia)
        return ("sap_nhap" if continues else "hop_nhat"), True
    return None, True


def _hoi_values(loai: str, tham_gia: list[str], moi: list[str]) -> dict[str, str | None]:
    """Tên hội → vai của fieldset (hoi_goc / hoi_goc_2 / hoi_moi_1 / hoi_moi_2)."""
    join = " và ".join
    if loai == "sap_nhap":
        receiving = next((t for t in tham_gia if moi and _same_name(t, moi[0])), None)
        if receiving is None:
            receiving = moi[0] if moi else (tham_gia[-1] if len(tham_gia) >= 2 else None)
        merged = [t for t in tham_gia if not (receiving and _same_name(t, receiving))]
        return {"hoi_goc": join(merged) or None, "hoi_moi_1": receiving}
    if loai == "hop_nhat":
        return {
            "hoi_goc": tham_gia[0] if tham_gia else None,
            "hoi_goc_2": join(tham_gia[1:]) or None,
            "hoi_moi_1": moi[0] if moi else None,
        }
    # chia / tách: một hội gốc → hai hội sau thay đổi.
    return {
        "hoi_goc": tham_gia[0] if tham_gia else None,
        "hoi_moi_1": moi[0] if moi else None,
        "hoi_moi_2": join(moi[1:]) or None,
    }


def _person_matches(name: str | None, identity: str | None, ctx_name: str | None, ctx_identity: str | None) -> bool:
    """Khớp tài khoản: có số ở cả 2 phía thì so số, không thì so tên."""
    if ctx_identity and identity:
        return identity == ctx_identity
    return bool(ctx_name and name and _same_name(name, ctx_name))


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    values = _by_name(fields)
    out: list[dict] = []
    warnings: list[str] = []
    seen: set[tuple[str, bool]] = set()

    def add(name: str, value, *, scoped: bool = False) -> None:
        key = (name, scoped)
        if key in seen or value in (None, "", {}, []):
            return
        comp = UI_COMP_BY_NAME.get(name) or MAU_DON_COMP.get(name)
        if not comp:
            return
        field = {"name": name, "comp": comp, "value": value}
        if scoped:
            field["scope"] = TACH_SCOPE
            field["scopeNear"] = TACH_SCOPE_NEAR
            field["scopeAway"] = list(NGUOI_NOP_MARKERS)
        out.append(field)
        seen.add(key)

    # --- Mốc tài khoản đăng nhập (extension gửi formContext) ---
    ctx = (options or {}).get("formContext") or {}
    ctx_name = _text(ctx.get("applicantFullname") or ctx.get("fullname"))
    ctx_identity = _identity(ctx.get("applicantIdentityNumber") or ctx.get("identityNumber"))
    has_ctx = bool(ctx_name or ctx_identity)

    lien_he = _text(values.get("NguoiLienHe_HoTen"))
    nguoi_ky = _text(values.get("NguoiKy_TMBCH"))
    lien_he = lien_he or nguoi_ky
    phone = _phone(values.get("NguoiLienHe_DienThoai"))
    lien_he_la_nguoi_nop = (not has_ctx) or (bool(lien_he) and _person_matches(lien_he, None, ctx_name, None))

    # --- Phần I: người nộp — chỉ từ CCCD khớp tài khoản (không có tài khoản: khớp người liên hệ) ---
    nop_name = _text(values.get("NguoiNop_HoTen"))
    nop_id = _identity(values.get("NguoiNop_SoDinhDanh"))
    if has_ctx:
        nop_ok = bool(nop_name or nop_id) and _person_matches(nop_name, nop_id, ctx_name, ctx_identity)
    else:
        nop_ok = bool(nop_name and lien_he and _same_name(nop_name, lien_he))
    if nop_ok:
        add("data[gender]", _gender(values.get("NguoiNop_GioiTinh")))
        add("data[identityDate]", _date(values.get("NguoiNop_NgayCap")))
        add("data[idIssuePlace]", _issuer(values.get("NguoiNop_NoiCap")))
        nop_area = _area(values.get("NguoiNop_DiaChi"))
        if nop_area:
            add("data[province]", province_label(nop_area.get("tinh")))
            add("data[district]", _text(nop_area.get("xa")))
            add("data[address]", _text(nop_area.get("diaChi")))
    if lien_he_la_nguoi_nop:
        add("data[phoneNumber]", phone)

    # --- Phần II: chủ hồ sơ = Chủ tịch dự kiến ---
    owner_name = _text(values.get("ChuHoSo_HoTen"))
    owner_id = _identity(values.get("ChuHoSo_SoDinhDanh"))
    if owner_name:
        if has_ctx:
            self_submit = _person_matches(owner_name, owner_id, ctx_name, ctx_identity)
        else:
            self_submit = bool(lien_he) and _same_name(owner_name, lien_he)
        add("data[isOwnerDossierCheck]", self_submit)
        add("data[ownerFullname]", owner_name)
        add("data[ownerBirthday]", _date(values.get("ChuHoSo_NgaySinh")))
        add("data[ownerGender]", _gender(values.get("ChuHoSo_GioiTinh")))
        add("data[ownerIdentityNumber]", owner_id)
        add("data[ownerIdentityDate]", _date(values.get("ChuHoSo_NgayCap")))
        add("data[ownerIdIssuePlace]", _issuer(values.get("ChuHoSo_NoiCap")))
        owner_area = _area(values.get("ChuHoSo_DiaChi"))
        if owner_area:
            add("data[ownerProvince]", province_label(owner_area.get("tinh")))
            add("data[ownerDistrict]", _text(owner_area.get("xa")))
            add("data[ownerAddress]", _text(owner_area.get("diaChi")))
        nation = _text(values.get("ChuHoSo_QuocTich"))
        add("data[ownerNation]", "Việt Nam" if not nation or "viet nam" in _fold(nation) else nation)

    # --- Phần III: datagrid hồ sơ kèm theo ---
    papers = _paper_names(values.get("DanhMucHoSo"))
    for i, paper in enumerate(papers[:MAX_HO_SO_ROWS]):
        add(f"data[hoSoDinhKem][{i}][textField1]", paper)
        add(f"data[hoSoDinhKem][{i}][textField2]", "Bản chính")

    # --- Phần IV: mẫu đơn ---
    tru_so = _area(values.get("TruSo_DiaChi"))
    noi_gui = province_label(values.get("KinhGui_Tinh")) or (province_label(tru_so.get("tinh")) if tru_so else None)
    add("data[noiGui]", noi_gui)

    tham_gia = _names(values.get("HoiThamGia"))
    moi = _names(values.get("HoiMoi"))
    raw_loai = values.get("LoaiThuTuc")
    loai, ambiguous = _loai(raw_loai, tham_gia, moi)
    mau = MAU_DON.get(loai or "")
    if mau:
        # "Chọn mẫu đơn" phát TRƯỚC: fieldset của mẫu chỉ render sau khi chọn.
        add("data[ChonTruongHop]", mau["label"])
        for role, value in _hoi_values(loai, tham_gia, moi).items():
            if role in mau:
                add(mau[role], value)

        nghi_dinh = _text(values.get("NghiDinhSo"))
        ngay_nd = _date(values.get("NgayNghiDinh"))
        if not nghi_dinh or _fold(nghi_dinh).startswith("126/2024"):
            nghi_dinh = nghi_dinh or _NGHI_DINH_HOI
            ngay_nd = ngay_nd or _NGAY_NGHI_DINH_HOI
        add(mau["nghi_dinh"], nghi_dinh)
        add(mau["ngay_nd"], ngay_nd)
        add(mau["ly_do"], _multiline(values.get("LyDo")))
        if papers:
            add(mau["ho_so"], "\n".join(f"{i}) {p}" for i, p in enumerate(papers, start=1)))

        scoped = loai == "tach"
        contact = {
            "ho_ten": lien_he,
            "dien_thoai": phone,
            "tinh": province_label(tru_so.get("tinh")) if tru_so else None,
            "xa": _text(tru_so.get("xa")) if tru_so else None,
            "dia_chi": _text(tru_so.get("diaChi")) if tru_so else None,
        }
        for role, value in contact.items():
            add(mau[role], value, scoped=scoped and role in _TACH_SCOPED_ROLES)

        add(mau["tmbch"], nguoi_ky or lien_he)
        if "tmbch_hoi_khac" in mau:
            add(mau["tmbch_hoi_khac"], _text(values.get("NguoiKy_HoiKhac")) or nguoi_ky or lien_he)

    # --- Cảnh báo ---
    if not mau:
        warnings.append("Không xác định được trường hợp chia / tách / sáp nhập / hợp nhất từ Đơn, Nghị quyết — vui "
                        "lòng tự chọn 'Chọn mẫu đơn' và nhập tên các hội.")
    elif ambiguous:
        warnings.append(f"Hồ sơ không ghi rõ một trường hợp — đã chọn mẫu '{mau['label']}'. Nếu không đúng, đổi 'Chọn "
                        "mẫu đơn' rồi nhập lại tên các hội.")
    if mau and (not tham_gia or not moi):
        warnings.append("Không đọc đủ tên các hội trước/sau thay đổi — vui lòng kiểm tra các ô tên Hội trong mẫu đơn.")
    if mau and not _multiline(values.get("LyDo")):
        warnings.append("Không đọc được lý do trong Đề án / Đơn — ô 'Lý do' (bắt buộc) vui lòng nhập tay.")
    if not tru_so:
        warnings.append("Không đọc được địa chỉ trụ sở của hội (Đề án / Điều lệ) — vui lòng chọn Tỉnh/TP, Phường/xã "
                        "và nhập số nhà, đường ở phần liên hệ.")
    if not phone:
        warnings.append("Hồ sơ không ghi số điện thoại liên hệ — ô SĐT (bắt buộc) vui lòng nhập tay.")
    if not owner_name:
        warnings.append("Không đọc được Chủ tịch dự kiến (Phiếu LLTP số 1 / Danh sách BCH) — vui lòng nhập tay thông "
                        "tin chủ hồ sơ.")
    elif not owner_id:
        warnings.append("Chưa có số CCCD của chủ hồ sơ (Phiếu LLTP mục 8 / CCCD) — vui lòng nhập tay.")
    if not has_ctx and nop_ok:
        warnings.append("Không đọc được tài khoản đang đăng nhập trên form — giới tính, ngày cấp, nơi cấp của người "
                        "nộp lấy theo CCCD của người được giao làm thủ tục, kiểm tra lại.")
    if not nop_ok:
        warnings.append("Hồ sơ không có CCCD khớp người nộp — vui lòng tự nhập giới tính, ngày cấp, nơi cấp, địa chỉ "
                        "của người nộp.")
    return out, warnings
