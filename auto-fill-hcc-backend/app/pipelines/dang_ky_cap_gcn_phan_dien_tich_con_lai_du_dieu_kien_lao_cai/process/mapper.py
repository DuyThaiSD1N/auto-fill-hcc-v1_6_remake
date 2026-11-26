"""Map dữ kiện nguồn → ô Form.io bước 1 cho thủ tục 1.115692 (Lào Cai, cổng iGate mới, cấp phường/xã).

Chọn người + phát ô dùng mapper chung của form "FORM NGUOI NOP" (chuyen_doi_md_sd_dat_igate_lao_cai): chủ hồ sơ cá nhân
điền thẳng từ giấy tờ, KHÔNG tích "Người nộp hồ sơ là chủ hồ sơ" (mapping đề xuất tích ở Bộ B, nhưng tích là cổng
calculateValue chép đè khối chủ hồ sơ — như mọi pipeline iGate Lào Cai), ô (*) thiếu → dom-expect.

⚑ HAI CHẾ ĐỘ NGƯỜI NỘP (`options.submitterMode`, cài đặt "Lấy người nộp theo tờ khai" của extension):
  - theo tài khoản (mặc định): khối người nộp = người trong hồ sơ KHỚP tài khoản đăng nhập (người sử dụng đất, hoặc
    người đại diện / bên nhận ủy quyền); không khớp ai → để trống nhân thân khối người nộp + cảnh báo.
  - theo tờ khai (`owner_as_submitter`): người nộp = NGƯỜI VIẾT ĐƠN. Bộ A nộp thay (người viết đơn là người đại diện
    theo ủy quyền, khác người sử dụng đất) → người nộp là người đại diện, lấy nhân thân/địa chỉ/SĐT/email theo Giấy ủy
    quyền (Bên B) + CCCD của người đó; còn lại người nộp = người sử dụng đất mục 1 Đơn (mapper chung). Khác tài khoản
    (hoặc không có mốc) → Họ tên/CCCD/Ngày sinh phát kèm enableInput (extension bỏ khoá rồi ghi đè) + cảnh báo.

Điểm riêng theo mapping 1.115692 (địa chỉ + nơi cấp dùng lại `_chuan_hoa` của 1.115684):
1. Địa chỉ: Tỉnh/Phường-Xã chỉ còn đơn vị hành chính mới → chủ hồ sơ theo Đơn mục 1 c), người đại diện theo "Nơi thường
   trú" trong Giấy ủy quyền; CCCD/GCN in địa danh trước 01/7/2025 → giấy mới thắng địa chỉ trên thẻ + cảnh báo khi
   khác nơi.
2. Nơi cấp "Cục Cảnh sát đăng ký, quản lý cư trú và DLQG về dân cư" → "Bộ Công An".
3. "Ghi chú" (data[tenHoSo]) = NGUYÊN VĂN mục 2 "Nội dung biến động" của Đơn (mapping: không cắt bớt).
"""

from app.pipelines.chuyen_doi_md_sd_dat_igate_lao_cai.process import mapper as _igate
from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.process import mapper as _goc
from app.pipelines.dang_ky_cap_gcn_phan_dien_tich_con_lai_du_dieu_kien_lao_cai.process.schema import UI_COMP_BY_NAME
from app.pipelines.giao_dat_o_khong_dau_gia_lao_cai.process import mapper as _giao_dat

_TRONG = (None, "", {}, [])


def _cung(left: dict | None, right: dict | None) -> bool:
    return bool(left and right) and _igate._cung_nguoi(
        left.get("SoDinhDanh"), left.get("HoTen"), right.get("SoDinhDanh"), right.get("HoTen")
    )


def _dai_dien(values: dict) -> dict | None:
    """Người viết đơn thay người sử dụng đất (bên nhận ủy quyền) — None khi người sử dụng đất tự viết đơn."""
    chu = {"HoTen": _goc._plain(values.get("ChuHoSo_HoTen")), "SoDinhDanh": values.get("ChuHoSo_SoDinhDanh")}
    noi_cap = values.get("DaiDien_NoiCap")
    rep = {
        "HoTen": _goc._plain(values.get("DaiDien_HoTen")),
        "SoDinhDanh": _goc._id_number(values.get("DaiDien_SoDinhDanh")),
        "NgaySinh": values.get("DaiDien_NgaySinh"),
        "GioiTinh": values.get("DaiDien_GioiTinh"),
        "NgayCap": values.get("DaiDien_NgayCap"),
        "NoiCap": _giao_dat._noi_cap_c06(noi_cap) if noi_cap else None,
        "NoiCuTru": values.get("DaiDien_DiaChi") if isinstance(values.get("DaiDien_DiaChi"), dict) else None,
        "DienThoai": values.get("DaiDien_DienThoai"),
        "Email": values.get("DaiDien_Email"),
    }
    if not (rep["HoTen"] or rep["SoDinhDanh"]):
        # LLM không trả khối đại diện nhưng người ký "Người viết đơn" khác người sử dụng đất.
        viet_don = _goc._plain(values.get("Don_NguoiVietDon"))
        if viet_don and chu["HoTen"] and _goc._fold(viet_don) != _goc._fold(chu["HoTen"]):
            rep["HoTen"] = viet_don
    rep = {k: v for k, v in rep.items() if v not in _TRONG}
    if not (rep.get("HoTen") or rep.get("SoDinhDanh")):
        return None
    if (chu["HoTen"] or chu["SoDinhDanh"]) and _cung(rep, chu):
        return None
    return rep


def _gop_dai_dien(fields: list[dict], rep: dict) -> list[dict]:
    """Đưa người đại diện vào NguoiTrongGiayTo (gộp mọi bản ghi cùng người — mapper chung đòi khớp số DUY NHẤT)."""
    out: list[dict] = []
    done = False
    for field in fields:
        if field.get("name") == "NguoiTrongGiayTo" and isinstance(field.get("value"), list):
            items: list = []
            merged: dict = {}
            vi_tri = None
            for person in field["value"]:
                if isinstance(person, dict) and _cung(person, rep):
                    merged.update({k: v for k, v in person.items() if v not in _TRONG})
                    vi_tri = len(items) if vi_tri is None else vi_tri
                    continue
                items.append(person)
            items.insert(len(items) if vi_tri is None else vi_tri, {**merged, **rep})
            field = {**field, "value": items}
            done = True
        out.append(field)
    if not done:
        out.append({"name": "NguoiTrongGiayTo", "value": [dict(rep)]})
    return out


def _doi_the(fields: list[dict], fn) -> list[dict]:
    return [{**f, "value": fn(f["value"])} if f.get("name") == "DanhSachCccd" and isinstance(f.get("value"), list)
            else f for f in fields]


def _chuan_hoa(fields: list[dict], rep: dict | None) -> tuple[list[dict], list[str]]:
    values = _goc._by_name(fields)
    the_dai_dien: list[dict] = []
    if rep and not (values.get("ChuHoSo_HoTen") or values.get("ChuHoSo_SoDinhDanh")):
        # _chuan_hoa lấy thẻ duy nhất làm người sử dụng đất khi Đơn thiếu — thẻ đó có thể là của người đại diện.
        the_dai_dien = [c for c in _goc._people(values, "DanhSachCccd") if _cung(c, rep)]
        fields = _doi_the(fields, lambda cards: [c for c in cards if not any(c is t for t in the_dai_dien)])
    fields, warnings = _giao_dat._chuan_hoa(fields)
    warnings = [
        w.replace("người đề nghị ở mục 1 của Đơn", "người sử dụng đất ở mục 1 của Đơn")
         .replace("ghi ở mục 2 của Đơn", "ghi ở mục 1 c) của Đơn")
        for w in warnings
    ]
    if the_dai_dien:
        fields = _doi_the(fields, lambda cards: [*cards, *(_giao_dat._person_noi_cap(c) for c in the_dai_dien)])
    if not rep:
        return fields, warnings

    fields = _gop_dai_dien(fields, rep)
    noi_moi = _igate._area(rep.get("NoiCuTru"))
    if noi_moi:
        # Giấy ủy quyền ghi nơi thường trú theo địa danh mới → thắng địa chỉ in trên thẻ của người đại diện.
        def bo_dia_chi_the(cards: list) -> list:
            items = []
            for card in cards:
                if isinstance(card, dict) and card.get("NoiCuTru") and _cung(card, rep):
                    noi_the = _igate._area(card.get("NoiCuTru"))
                    if noi_the and not _giao_dat._cung_noi(noi_the, noi_moi):
                        warnings.append(
                            f"Địa chỉ in trên thẻ căn cước của người đại diện ({_giao_dat._o_dia_chi(noi_the)}) khác "
                            f"nơi thường trú ghi trong Giấy ủy quyền ({_giao_dat._o_dia_chi(noi_moi)}) — trợ lý điền "
                            "theo Giấy ủy quyền; cán bộ kiểm tra lại."
                        )
                    card = {k: v for k, v in card.items() if k != "NoiCuTru"}
                items.append(card)
            return items

        fields = _doi_the(fields, bo_dia_chi_the)
    return fields, warnings


def _dat_o(out: list[dict], name: str, value) -> None:
    """Ghi ô người nộp: thay dom-expect cùng tên; chưa có thì chèn trước khối chủ hồ sơ."""
    if value in _TRONG:
        return
    field = {"name": name, "comp": UI_COMP_BY_NAME[name], "value": value}
    for index, current in enumerate(out):
        if current["name"] == name:
            if current.get("comp") == "dom-expect":
                out[index] = field
            return
    chu = next((i for i, f in enumerate(out) if f["name"] == "data[ChuHS]" or f["name"].startswith("data[owner")),
               len(out))
    out.insert(chu, field)


def _ghi_chu(values: dict) -> str | None:
    text = values.get("Don_NoiDungBienDong")
    return " ".join(text.split()) or None if isinstance(text, str) else None


def enrich(fields: list[dict], options: dict | None = None) -> tuple[list[dict], list[str]]:
    rep = _dai_dien(_goc._by_name(fields))
    fields, warnings = _chuan_hoa(fields, rep)
    if rep:
        # Chỉ biết tên người viết đơn → bù số CCCD/ngày sinh/ngày cấp từ thẻ / Giấy ủy quyền của chính người đó.
        values = _goc._by_name(fields)
        rep = _goc._merge_person(rep, _goc._people(values, "NguoiTrongGiayTo"), _goc._people(values, "DanhSachCccd"))

    opts = options or {}
    ctx = opts.get("formContext") or {}
    theo_to_khai = str(opts.get("submitterMode") or "") == "owner_as_submitter"
    tk_so = ctx.get("applicantIdentityNumber") or ctx.get("identityNumber")
    tk_ten = ctx.get("applicantFullname")
    co_moc = bool(_goc._digits(tk_so) or _goc._fold(tk_ten))

    if theo_to_khai and rep:
        # Người nộp = người viết đơn (đại diện): chạy mapper chung như thể tài khoản là người đại diện.
        gia = {**opts, "submitterMode": "", "formContext": {
            **ctx, "applicantIdentityNumber": rep.get("SoDinhDanh") or "",
            "identityNumber": rep.get("SoDinhDanh") or "", "applicantFullname": rep.get("HoTen") or "",
        }}
        out, chung = _igate.enrich_with_warnings(fields, gia)
        nop_dai_dien = True
        if not (co_moc and _igate._cung_nguoi(tk_so, tk_ten, rep.get("SoDinhDanh"), rep.get("HoTen"))):
            the = _goc._find_person(_goc._people(_goc._by_name(fields), "DanhSachCccd"),
                                    rep.get("SoDinhDanh"), rep.get("HoTen"))
            o_khoa = _igate.o_khoa_theo_to_khai(rep.get("HoTen"), rep.get("SoDinhDanh"),
                                                rep.get("NgaySinh"), (the or {}).get("NgaySinh"))
            if o_khoa:
                _igate.ghi_o_khoa(out, {f["name"] for f in out}, o_khoa)
                chung.append(_igate.canh_bao_mo_khoa(
                    f"{_goc._plain(rep['HoTen'])} (người viết đơn thay — đại diện theo ủy quyền)", tk_ten))
    else:
        out, chung = _igate.enrich_with_warnings(fields, options)
        nop_dai_dien = bool(rep) and not theo_to_khai and co_moc and _igate._cung_nguoi(
            tk_so, tk_ten, rep.get("SoDinhDanh"), rep.get("HoTen"))

    if nop_dai_dien:
        # Mapper chung chỉ lấy SĐT/Email khi người nộp là chủ hồ sơ (số trên Đơn) → người đại diện lấy theo Giấy ủy quyền.
        _dat_o(out, "data[phoneNumber]", _goc._phone(rep.get("DienThoai")))
        _dat_o(out, "data[email]", _goc._email(rep.get("Email")))

    ghi_chu = _ghi_chu(_goc._by_name(fields))
    if ghi_chu:
        out.append({"name": "data[tenHoSo]", "comp": UI_COMP_BY_NAME["data[tenHoSo]"], "value": ghi_chu})
    return out, [*warnings, *chung]
