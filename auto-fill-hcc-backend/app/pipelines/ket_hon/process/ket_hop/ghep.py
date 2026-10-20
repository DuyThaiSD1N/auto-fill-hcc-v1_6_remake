"""Ghép trường THÔ của 2 AI (Vintern = V, Qwen = Q) cho thủ tục kết hôn:

Bậc của một giá trị: HỢP LỆ (2) > HỎNG (1, có giá trị nhưng sai khuôn) > THIẾU (0, trống / "[?]" / "không đọc được").
Bậc cao hơn thắng; cùng bậc mà khác nhau → rule riêng của trường, không phân định được → Vintern.

0. Ghép người theo số định danh / họ tên: Q xếp người vào nhóm Nam mà V xếp vào Nữ (hoặc ngược lại) → đảo cả nhóm của Q.
1. Số định danh: 12 số (CMND 9 số), 3 số đầu là mã tỉnh 001–096, số thứ 4 khớp giới tính bên đó, số 5–6 khớp năm sinh.
   Cùng hợp lệ mà khác → lấy số khớp MRZ hoặc khớp nguồn còn lại (CCCD ↔ tờ khai, của cả 2 AI).
2. Họ tên: cùng hợp lệ mà khác → lấy tên khớp dòng tên MRZ (bỏ dấu); chỉ lệch dấu → V.
3. Ngày sinh: ngày có thật, năm khớp số định danh đã chọn. Khác → lấy ngày khớp MRZ (YYMMDD).
4. Ngày cấp: ngày có thật, sau ngày sinh, không quá hôm nay.
5. Nơi cấp: khác → lấy bên khớp loại thẻ theo ngày cấp (từ 01/7/2024 Bộ Công an, trước đó Cục Cảnh sát QLHC về TTXH).
6. Dân tộc: giá trị CHỈ Q có → chỉ nhận khi chữ OCR có nhãn "Dân tộc" (chốt chống bịa như prod).
7. Nơi cư trú: lấy CẢ CỤM (tỉnh + xã + chi tiết) của một bên, không trộn; hợp lệ = có tỉnh và xã.
8. Cụm ly hôn của mỗi người: luôn lấy cả cụm V, Q không vá.
9. Ô tích của tờ khai (bản sao, số lượng, loại đăng ký): Q quyết định kể cả khi Q bỏ trống — Vintern chỉ trả chữ nên
   hay in ô trống thành "☑" (``o_tich_theo_qwen``).
Mỗi trường ghi lại nguồn đã chọn và lý do.

Soát thêm (soat=True):
  a. Số định danh / ngày / loại đăng ký của một AI phải CÓ trong chính chữ OCR của AI đó (nhánh có chữ OCR);
     không có → LLM bịa hoặc lấy nhầm chỗ khác → coi như THIẾU.
  b. Nơi cư trú: xã phải có thật — trong danh mục hiện hành, hoặc là tên cũ có trong bảng sáp nhập.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

from app.pipelines._shared.cccd import id_birth_year, id_gender

SIDES = ("Nam", "Nu")
_NHOM = ("Ben", "ToKhai")
_DOI_BEN = ("Ben", "ToKhai")   # mọi nhóm có hậu tố Nam/Nu cần đảo khi Qwen gán ngược bên
_LY_HON = ("SoLanKetHon", "TinhTrangHonNhan", "BanAnLyHon_So", "BanAnLyHon_Ngay", "BanAnLyHon_CoQuan",
           "BanAnLyHon_DuongSu")
_MOC_CAN_CUOC = date(2024, 7, 1)


# ---------------------------------------------------------------- chuẩn hoá
def _fold(v) -> str:
    s = unicodedata.normalize("NFD", str(v or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", s).strip().lower()


def _digits(v) -> str:
    return re.sub(r"\D", "", str(v or ""))


def _same(a, b) -> bool:
    if isinstance(a, dict) or isinstance(b, dict):
        return {k: _fold(v) for k, v in (a or {}).items()} == {k: _fold(v) for k, v in (b or {}).items()}
    return _fold(a) == _fold(b)


def thieu(v) -> bool:
    if v in (None, "", {}, []):
        return True
    if isinstance(v, dict):
        return not any(str(x or "").strip() for x in v.values())
    s = _fold(v)
    return not s or "[?]" in str(v) or "khong doc duoc" in s


def _ngay(v) -> date | None:
    m = re.fullmatch(r"\s*(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})\s*", str(v or ""))
    if not m:
        return None
    try:
        d = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date()
    except ValueError:
        return None
    return d if date(1900, 1, 1) <= d <= date.today() else None


def _nam(v) -> int | None:
    d = _ngay(v)
    return d.year if d else None


# ---------------------------------------------------------------- MRZ trong chữ OCR
def doc_mrz(texts: list[str]) -> dict:
    """Số định danh, ngày sinh (YYMMDD), họ tên (bỏ dấu, chữ thường) đọc được ở dòng MRZ mặt sau thẻ."""
    ids, births, names = set(), set(), set()
    for t in texts:
        for line in str(t or "").splitlines():
            s = re.sub(r"\s+", "", line).upper()
            m = re.search(r"IDVNM\d{9}\d(\d{12})", s)
            if m:
                ids.add(m.group(1))
                continue
            m = re.match(r"^(\d{6})\d[MF<](\d{6})\dVNM", s)
            if m:
                births.add(m.group(1))
                continue
            if "<<" in s and re.fullmatch(r"[A-Z<]{8,}", s):
                n = re.sub(r"<+", " ", s).strip().lower()
                if len(n.split()) >= 2:
                    names.add(n)
    return {"ids": ids, "births": births, "names": names}


# ---------------------------------------------------------------- hợp lệ
def _gioi(side: str) -> str:
    return "Nam" if side == "Nam" else "Nữ"


def id_hop_le(v, side: str, nam_sinh: int | None = None) -> bool:
    d = _digits(v)
    if len(re.sub(r"[\d\s.\-]", "", str(v or ""))) > 0:      # lẫn chữ cái → hỏng
        return False
    if len(d) == 9:
        return True
    if len(d) != 12 or not 1 <= int(d[:3]) <= 96:
        return False
    g = id_gender(d)
    if g and g != _gioi(side):
        return False
    by = id_birth_year(d)
    return not (nam_sinh and by and by != nam_sinh)


def xa_co_that(v: dict) -> bool:
    from app.pipelines._shared import area_remap as ar
    if ar.is_current_area(v.get("tinh"), v.get("xa")):
        return True
    r = ar.remap_area(dict(v), correct_spelling=False) or {}
    return bool(r.get("xa") and ar.is_current_area(r.get("tinh"), r.get("xa")))


def co_trong_chu(name: str, v, chu: str) -> bool:
    """Giá trị có xuất hiện trong chữ OCR không (chỉ xét trường dễ bị LLM bịa: số, ngày, loại đăng ký)."""
    field = name.split("_", 1)[1] if "_" in name else name
    if field == "SoDinhDanh":
        return _digits(v) in re.sub(r"[\s.\-]", "", chu)
    if field in ("NgaySinh", "NgayCap", "BanAnLyHon_Ngay"):
        d = _ngay(v)
        return not d or bool(re.search(rf"\b0?{d.day}\s*\D{{1,3}}\s*0?{d.month}\s*\D{{1,3}}\s*{d.year}\b", chu))
    if name == "ToKhai_LoaiDangKy":
        return _fold(v) in _fold(chu)
    return True


def _bac(name: str, v, side: str | None, ctx: dict) -> int:
    if thieu(v):
        return 0
    field = name.split("_", 1)[1] if "_" in name else name
    if ctx.get("chu") is not None and not co_trong_chu(name, v, ctx["chu"]):
        return 0       # không có trên giấy → coi như thiếu (thà thiếu còn hơn điền giá trị bịa)
    if ctx.get("soat") and field.endswith("NoiCuTru_TrongNuoc") and isinstance(v, dict) and not xa_co_that(v):
        return 1
    if field == "SoDinhDanh":
        return 2 if id_hop_le(v, side, ctx.get("nam_sinh")) else 1
    if field == "HoTen":
        return 2 if len(_fold(v).split()) >= 2 and not re.search(r"\d", str(v)) else 1
    if field == "NgaySinh":
        d = _ngay(v)
        if not d:
            return 1
        by = id_birth_year(ctx.get("so_dinh_danh"))
        return 2 if not by or by == d.year else 1
    if field in ("NgayCap", "BanAnLyHon_Ngay"):
        d, ns = _ngay(v), _ngay(ctx.get("ngay_sinh"))
        return 2 if d and (not ns or d > ns) else 1
    if field.endswith("NoiCuTru_TrongNuoc"):
        return 2 if isinstance(v, dict) and str(v.get("tinh") or "").strip() and str(v.get("xa") or "").strip() else 1
    return 2


# ---------------------------------------------------------------- bước 0: ghép người
def _nguoi(raw: dict, side: str) -> tuple[set, set]:
    ids = {_digits(raw.get(f"{n}{side}_SoDinhDanh")) for n in _NHOM}
    names = {_fold(raw.get(f"{n}{side}_HoTen")) for n in _NHOM}
    return {i for i in ids if len(i) >= 9}, {n for n in names if n}


def _doi_ben(raw: dict) -> dict:
    out = {}
    for k, v in raw.items():
        for n in _DOI_BEN:
            if k.startswith(f"{n}Nam_"):
                k = f"{n}Nu_" + k[len(f"{n}Nam_"):]
                break
            if k.startswith(f"{n}Nu_"):
                k = f"{n}Nam_" + k[len(f"{n}Nu_"):]
                break
        out[k] = v
    return out


def can_doi_ben(v: dict, q: dict) -> bool:
    vn, vu, qn, qu = _nguoi(v, "Nam"), _nguoi(v, "Nu"), _nguoi(q, "Nam"), _nguoi(q, "Nu")
    cheo = bool(qn[0] & vu[0] or qu[0] & vn[0] or qn[1] & vu[1] or qu[1] & vn[1])
    dung = bool(qn[0] & vn[0] or qu[0] & vu[0] or qn[1] & vn[1] or qu[1] & vu[1])
    return cheo and not dung


# ---------------------------------------------------------------- ghép
def ghep(v: dict, q: dict, texts: list[str], soat: bool = False,
         chu_v: str | None = None, chu_q: str | None = None) -> tuple[dict, list[dict]]:
    """v, q: trường thô {name: value}; texts: chữ OCR có được (để đọc MRZ, soát nhãn Dân tộc).
    soat: bật soát thêm (a)(b); chu_v / chu_q: chữ OCR riêng của từng AI (None = AI đó không có chữ, vd Qwen JSON).
    → (trường thô đã ghép, quyết định từng trường)."""
    sv = {"soat": True, "chu": chu_v} if soat else {}
    sq = {"soat": True, "chu": chu_q} if soat else {}
    v, q = dict(v or {}), dict(q or {})
    quyet: list[dict] = []
    if can_doi_ben(v, q):
        q = _doi_ben(q)
        quyet.append({"field": "*", "nguon": "Q", "ly_do": "Qwen gán nam/nữ ngược Vintern → đảo nhóm của Qwen"})
    mrz = doc_mrz(texts)
    co_nhan_dan_toc = "dan toc" in _fold("\n".join(texts))
    out: dict = {}
    cum_da_xet: set[str] = set()

    def chon(name, side=None, ctx=None, tie=None):
        a, b = v.get(name), q.get(name)
        ta, tb = _bac(name, a, side, {**(ctx or {}), **sv}), _bac(name, b, side, {**(ctx or {}), **sq})
        if ta == 0 and tb == 0:
            return
        if ta > tb:
            src, why = "V", ("Qwen thiếu" if tb == 0 else "giá trị Qwen sai khuôn")
        elif tb > ta:
            src, why = "Q", ("Vintern thiếu" if ta == 0 else "giá trị Vintern sai khuôn")
        elif _same(a, b):
            src, why = "V", "giống nhau"
        else:
            src = tie(a, b) if tie else None
            why = "khớp đối chiếu" if src else "khác nhau, lấy Vintern"
            src = src or "V"
        if src == "Q" and name.endswith("_DanToc") and ta == 0 and not co_nhan_dan_toc:
            quyet.append({"field": name, "v": a, "q": b, "nguon": "-", "ly_do": "chỉ Qwen có, chữ OCR không có nhãn Dân tộc → bỏ"})
            return
        out[name] = a if src == "V" else b
        quyet.append({"field": name, "v": a, "q": b, "nguon": src, "ly_do": why})

    def tie_khop(tap):
        def _t(a, b):
            ia, ib = _fold(a) in tap or _digits(a) in tap, _fold(b) in tap or _digits(b) in tap
            return "V" if ia and not ib else "Q" if ib and not ia else None
        return _t

    for side in SIDES:
        for n in _NHOM:
            p = f"{n}{side}_"
            if not any(k.startswith(p) for k in v) and any(k.startswith(p) for k in q):
                quyet.append({"field": p + "*", "nguon": "Q", "ly_do": "Vintern không đọc ra người này → lấy từ Qwen"})
        for n in _NHOM:
            p = f"{n}{side}_"
            # Số định danh: hợp lệ xét theo năm sinh CỦA CHÍNH AI đó đọc ra → tính bậc riêng từng bên.
            ids_khac = {_digits(r.get(f"{m}{side}_SoDinhDanh")) for r in (v, q) for m in _NHOM if m != n} | mrz["ids"]
            a, b = v.get(p + "SoDinhDanh"), q.get(p + "SoDinhDanh")
            ta = _bac(p + "SoDinhDanh", a, side, {"nam_sinh": _nam(v.get(p + "NgaySinh")), **sv})
            tb = _bac(p + "SoDinhDanh", b, side, {"nam_sinh": _nam(q.get(p + "NgaySinh")), **sq})
            if ta or tb:
                if ta != tb:
                    src = "V" if ta > tb else "Q"
                    why = (("Qwen thiếu" if tb == 0 else "số Qwen sai khuôn") if src == "V"
                           else ("Vintern thiếu" if ta == 0 else "số Vintern sai khuôn"))
                elif _digits(a) == _digits(b):
                    src, why = "V", "giống nhau"
                else:
                    src = tie_khop({i for i in ids_khac if i})(a, b)
                    why = "khớp MRZ / nguồn còn lại" if src else "khác nhau, lấy Vintern"
                    src = src or "V"
                out[p + "SoDinhDanh"] = a if src == "V" else b
                quyet.append({"field": p + "SoDinhDanh", "v": a, "q": b, "nguon": src, "ly_do": why})
            sdd = out.get(p + "SoDinhDanh")
            chon(p + "HoTen", side, tie=tie_khop(mrz["names"] | {
                _fold(r.get(f"{m}{side}_HoTen")) for r in (v, q) for m in _NHOM if m != n} - {""}))
            chon(p + "NgaySinh", side, {"so_dinh_danh": sdd},
                 tie=lambda a, b: _tie_ngay_mrz(a, b, mrz["births"]))
            chon(p + "NgayCap", side, {"ngay_sinh": out.get(p + "NgaySinh")})
            chon(p + "NoiCap", side, tie=lambda a, b, _p=p: _tie_noi_cap(a, b, out.get(_p + "NgayCap")))
            for f in ("DanToc", "QuocTich", "LoaiGiayTo", "NoiCuTru_TrongNuoc"):
                chon(p + f, side)
        # Cụm ly hôn: luôn theo Vintern, Qwen không vá. "Không có" là câu trả lời hợp lệ (người chưa ly hôn); điền nhầm
        # quyết định của Tòa án cho người chưa ly hôn tệ hơn để trống cho cán bộ bổ sung.
        cum = [f"Ben{side}_{f}" for f in _LY_HON]
        nguon = v
        cum_da_xet.update(cum)
        for k in cum:
            if not thieu(nguon.get(k)):
                out[k] = nguon[k]
                quyet.append({"field": k, "v": v.get(k), "q": q.get(k), "nguon": "V" if nguon is v else "Q",
                              "ly_do": "cả cụm ly hôn theo một bên"})
    for name in sorted(set(v) | set(q)):
        if name not in out and name not in cum_da_xet and not any(d["field"] == name for d in quyet):
            chon(name)
    return out, quyet


def _tie_ngay_mrz(a, b, births: set) -> str | None:
    def _k(x):
        d = _ngay(x)
        return d.strftime("%y%m%d") if d else ""
    ia, ib = _k(a) in births, _k(b) in births
    return "V" if ia and not ib else "Q" if ib and not ia else None


def _tie_noi_cap(a, b, ngay_cap) -> str | None:
    d = _ngay(ngay_cap)
    if not d:
        return None
    want = "bo cong an" if d >= _MOC_CAN_CUOC else "cuc canh sat"
    ia, ib = want in _fold(a), want in _fold(b)
    return "V" if ia and not ib else "Q" if ib and not ia else None


O_TICH = ("CopyRequest_", "ToKhai_LoaiDangKy")
TIEU_DE_TO_KHAI = "TỜ KHAI ĐĂNG KÝ KẾT HÔN"


def co_to_khai(chu_v: str) -> bool:
    return TIEU_DE_TO_KHAI in str(chu_v or "").upper()


def o_tich_theo_qwen(out: dict, q: dict, quyet: list[dict]) -> dict:
    """Luật 9 — chỉ áp khi hồ sơ có tờ khai (gọi ở bước điều phối)."""
    out = {k: val for k, val in out.items() if not k.startswith(O_TICH)}
    for k, val in (q or {}).items():
        if k.startswith(O_TICH):
            out[k] = val
    quyet.append({"field": "|".join(O_TICH), "nguon": "Q", "ly_do": "ô tích của tờ khai theo Qwen"})
    return out

