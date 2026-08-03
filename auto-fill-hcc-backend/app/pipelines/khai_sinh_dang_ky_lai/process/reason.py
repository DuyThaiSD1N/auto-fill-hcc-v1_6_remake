"""Tầng suy luận (PA1) cho "Đăng ký lại khai sinh".

Chạy TRƯỚC bước trích xuất, dùng lại OCR đã có. Luồng:
  OCR -> LLM (roster: phân loại tài liệu + liệt kê người) -> CỔNG PYTHON tất định chốt vai trò
  -> đoạn context tiếng người ghim "ai là ai, lấy từ đâu" -> nối vào prompt trích xuất.

Cổng tất định (không tin LLM ở phần dễ sai) theo luật nghiệp vụ:
- Giấy KHAI TỬ -> người trong giấy là cha/mẹ (theo giới tính) và ĐÃ CHẾT; 2 giấy -> cả cha lẫn mẹ chết.
- Chồng/vợ trong giấy KẾT HÔN KHÔNG phải cha/mẹ của con (bị hạ vai nếu đã có cha/mẹ từ khai tử).
- cha = Nam, mẹ = Nữ (lệch giới -> xóa vai để không điền bừa).
- con = người còn sống, có CCCD/khai sinh cũ/học bạ/bằng, không phải cha/mẹ.
- Người yêu cầu = người trùng tên/số định danh cổng điền sẵn (VNeID); không ai trùng -> để mặc định.
"""

import re
import unicodedata

from app.config import settings
from app.services.llm import client

_ANCHOR_LOAI = {"cccd", "khai_sinh_cu", "trich_luc_ks", "hoc_ba", "bang_tot_nghiep"}
_REASON_MAX_TOKENS = 1200

_ROSTER_PROMPT = """
Bạn là trợ lý phân tích hồ sơ ĐĂNG KÝ LẠI KHAI SINH. KHÔNG trích chi tiết field.
Nhiệm vụ: đọc OCR các tài liệu rồi (1) phân loại từng tài liệu, (2) liệt kê từng người xuất hiện
kèm thông tin nhận dạng và VAI TRÒ trong thủ tục.

loai (loại tài liệu): cccd, khai_sinh_cu, trich_luc_ks, to_khai, ket_hon, khai_tu,
hoc_ba, bang_tot_nghiep, cam_doan, khac.

vai_tro: con (người được đăng ký lại khai sinh), cha, me, nguoi_yeu_cau, chong, vo, khac.

QUY TẮC XÁC ĐỊNH VAI TRÒ:
- "con" (chủ thể) = người được đăng ký lại khai sinh; danh tính lấy từ giấy khai sinh cũ / CCCD /
  học bạ / bằng tốt nghiệp của chính người đó.
- Giấy KHAI TỬ: người trong giấy là CHA hoặc MẸ của con (theo giới tính) và đã chết (da_chet=true).
- Giấy KẾT HÔN: người ghi "chồng"/"vợ" là vợ chồng, KHÔNG phải cha/mẹ của con.
- cha là Nam, mẹ là Nữ.
- Nhiều CCCD: khớp họ tên trên CCCD với vai trò đã biết (tên con / tên cha, mẹ trong khai tử).
  Không có mỏ neo thì suy theo thế hệ (người trẻ nhất là con; người lớn hơn ~18+ tuổi là cha/mẹ
  theo giới tính) và họ (con thường cùng họ với cha).
- TÊN FILE là tín hiệu mạnh: "cccd bố"/"cccd cha" -> người đó là cha; "cccd mẹ" -> mẹ;
  "cccd con"/"cccd" của chủ thể -> con.
- Nếu GIẤY KHAI SINH KHÔNG ghi tên cha (hoặc mẹ) mà hồ sơ CÓ CCCD của người đó -> vẫn gán người
  trên CCCD làm cha/mẹ (cha = CCCD giới tính Nam, mẹ = CCCD giới tính Nữ). KHÔNG lấy chữ trên con
  dấu/tiêu đề (TƯ PHÁP, ỦY BAN, CHỦ TỊCH...) làm tên người.
- KHÔNG bịa người không có trong OCR.

CHỈ trả JSON trong ```json ... ``` đúng cấu trúc, không thêm chữ nào ngoài JSON:
{"documents":[{"name":"<tên file>","loai":"<loai>","ve_ai":"<tên người tài liệu nói tới>"}],
 "persons":[{"ten":"...","gioi_tinh":"Nam|Nữ|","nam_sinh":"...","so_dinh_danh":"...","da_chet":false,"vai_tro":"con|cha|me|nguoi_yeu_cau|chong|vo|khac","nguon":["<tên file>"]}]}
""".strip()


def _fold(value) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", text).strip().lower()


def _digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))


def _requester_hint(options: dict) -> str:
    ctx = (options or {}).get("formContext") or {}
    name = str(ctx.get("applicantFullname") or "").strip()
    idnum = str(ctx.get("applicantIdentityNumber") or "").strip()
    if not name and not idnum:
        return ""
    return (
        f'\n\nNGƯỜI YÊU CẦU đã đăng nhập (VNeID): họ tên="{name}", số định danh="{idnum}". '
        "Gán vai_tro=nguoi_yeu_cau cho người trùng tên/số định danh này."
    )


def _build_user(documents: list[dict]) -> str:
    body = "\n\n---\n\n".join(
        f"===== {d.get('name') or '(không tên)'} =====\n{(d.get('text') or '').strip()}"
        for d in documents
    )
    return "OCR các tài liệu trong hồ sơ:\n\n" + body


def _apply_gate(roster: dict, options: dict | None = None) -> dict:
    """Chốt vai trò tất định. Không tin LLM ở phần dễ sai (khai tử/kết hôn/giới tính/người yêu cầu)."""
    docs = roster.get("documents") or []
    persons = roster.get("persons") or []

    for p in persons:
        p["vai_tro"] = (p.get("vai_tro") or "").strip().lower()
        p["gioi_tinh"] = (p.get("gioi_tinh") or "").strip()
        p["da_chet"] = bool(p.get("da_chet"))

    doc_loai_by_file = {_fold(d.get("name")): (d.get("loai") or "").strip().lower() for d in docs}

    def person_loais(p) -> list[str]:
        return [doc_loai_by_file.get(_fold(s), "") for s in (p.get("nguon") or [])]

    def find(name) -> dict | None:
        key = _fold(name)
        if not key:
            return None
        return next((p for p in persons if _fold(p.get("ten")) == key), None)

    # (b) KHAI TỬ -> người đó là cha/mẹ (theo giới tính) và đã chết.
    for d in docs:
        if (d.get("loai") or "").strip().lower() != "khai_tu":
            continue
        p = find(d.get("ve_ai"))
        if not p:
            continue
        p["da_chet"] = True
        if p["gioi_tinh"] == "Nam":
            p["vai_tro"] = "cha"
        elif p["gioi_tinh"] == "Nữ":
            p["vai_tro"] = "me"
        elif p["vai_tro"] not in ("cha", "me"):
            # Không rõ giới: lấp khe còn trống.
            p["vai_tro"] = "cha" if not any(x["vai_tro"] == "cha" for x in persons) else "me"

    # (a) cha=Nam, mẹ=Nữ. Lệch giới -> xóa vai (không điền bừa).
    for p in persons:
        if p["vai_tro"] == "cha" and p["gioi_tinh"] == "Nữ":
            p["vai_tro"] = ""
        elif p["vai_tro"] == "me" and p["gioi_tinh"] == "Nam":
            p["vai_tro"] = ""

    # (c) Cha/mẹ từ KHAI TỬ là chuẩn. Ai giữ vai cha/mẹ mà KHÔNG đến từ khai tử thì hạ vai:
    #     có nguồn kết hôn -> chồng/vợ (chồng/vợ KHÔNG phải cha/mẹ của con); còn lại xóa vai
    #     để bước "con" xét lại (vd chính chủ thể bị LLM gán nhầm cha/mẹ).
    for role, spouse in (("cha", "chong"), ("me", "vo")):
        khaitu_holder = any(p["vai_tro"] == role and "khai_tu" in person_loais(p) for p in persons)
        if not khaitu_holder:
            continue
        for p in persons:
            if p["vai_tro"] == role and "khai_tu" not in person_loais(p):
                p["vai_tro"] = spouse if "ket_hon" in person_loais(p) else ""

    # (d) Người yêu cầu = trùng formContext; không khớp thì bỏ vai nguoi_yeu_cau (dùng mặc định).
    ctx = (options or {}).get("formContext") or {}
    aid, aname = _digits(ctx.get("applicantIdentityNumber")), _fold(ctx.get("applicantFullname"))
    if aid or aname:
        for p in persons:
            pid, pname = _digits(p.get("so_dinh_danh")), _fold(p.get("ten"))
            matched = (aid and pid and aid == pid) or (aname and pname and aname == pname)
            if matched:
                p["_requester"] = True
            elif p["vai_tro"] == "nguoi_yeu_cau":
                p["vai_tro"] = ""

    # (e) Giấy khai sinh KHÔNG ghi tên cha/mẹ nhưng hồ sơ CÓ CCCD của họ -> gán CCCD làm cha/mẹ.
    #     Ưu tiên TÊN FILE ("cccd bố"/"cccd mẹ"), sau đó giới tính (cha=Nam, mẹ=Nữ).
    def _is_free_cccd(p) -> bool:
        return (not p.get("_requester") and p["vai_tro"] in ("", "khac")
                and "cccd" in person_loais(p))

    def _file_role_hint(p) -> str:
        # "chà" (TÊN người) gấp dấu thành "cha" -> đừng nhầm thành quan hệ "cha". Nếu từ khóa quan hệ
        # xuất hiện trong CHÍNH họ tên người thì đó là tên file gọi theo tên, bỏ qua hint.
        name_words = set(_fold(p.get("ten")).split())
        for s in (p.get("nguon") or []):
            f = _fold(s)
            if re.search(r"(^| )(bo|cha|father)( |\.|$)", f) and not (name_words & {"bo", "cha"}):
                return "cha"
            if re.search(r"(^| )(me|mother)( |\.|$)", f) and "me" not in name_words:
                return "me"
        return ""

    for p in persons:
        if not _is_free_cccd(p):
            continue
        hint = _file_role_hint(p)
        if hint == "cha" and p["gioi_tinh"] != "Nữ":
            p["vai_tro"] = "cha"
        elif hint == "me" and p["gioi_tinh"] != "Nam":
            p["vai_tro"] = "me"

    # Còn CCCD chưa gán + có ngữ cảnh con (đã có "con" hoặc có giấy khai sinh/tờ khai)
    # -> lấp khe cha/mẹ còn trống theo giới tính.
    child_ctx = any(p["vai_tro"] == "con" for p in persons) or any(
        (d.get("loai") or "").strip().lower() in ("khai_sinh_cu", "to_khai") for d in docs)
    if child_ctx:
        has_father = any(p["vai_tro"] == "cha" for p in persons)
        has_mother = any(p["vai_tro"] == "me" for p in persons)
        for p in persons:
            if not _is_free_cccd(p):
                continue
            if p["gioi_tinh"] == "Nam" and not has_father:
                p["vai_tro"], has_father = "cha", True
            elif p["gioi_tinh"] == "Nữ" and not has_mother:
                p["vai_tro"], has_mother = "me", True

    # con = người còn sống, có tài liệu neo (CCCD/KS cũ/học bạ/bằng), không phải cha/mẹ.
    # (KHÔNG loại người yêu cầu: người tự đăng ký lại khai sinh chính là con — BanThan.)
    if not any(p["vai_tro"] == "con" for p in persons):
        cands = [
            p for p in persons
            if not p["da_chet"] and p["vai_tro"] not in ("cha", "me")
            and any(l in _ANCHOR_LOAI for l in person_loais(p))
        ]
        if len(cands) == 1:
            cands[0]["vai_tro"] = "con"
        elif len(cands) > 1:
            # Khi có nhiều ứng viên còn sống: người TRẺ NHẤT (năm sinh lớn nhất) = con.
            # Người già hơn sẽ được gán cha/mẹ theo giới tính ở bước tiếp theo.
            def _birth_year(p) -> int:
                m = re.search(r"\b(19|20)\d{2}\b", str(p.get("nam_sinh") or ""))
                return int(m.group()) if m else 0

            sorted_cands = sorted(cands, key=_birth_year, reverse=True)  # trẻ nhất trước
            youngest = sorted_cands[0]
            youngest_year = _birth_year(youngest)

            # Chỉ gán "con" khi người trẻ nhất rõ ràng trẻ hơn ít nhất 15 tuổi so với người tiếp theo
            # (tránh nhầm giữa hai anh em gần tuổi không ai là cha/mẹ)
            second_year = _birth_year(sorted_cands[1]) if len(sorted_cands) > 1 else 0
            if youngest_year > 0 and second_year > 0 and (youngest_year - second_year) >= 15:
                youngest["vai_tro"] = "con"
                # Người già hơn (còn sống) → gán cha/mẹ theo giới tính nếu chưa có
                for older in sorted_cands[1:]:
                    if older["gioi_tinh"] == "Nam" and not any(x["vai_tro"] == "cha" for x in persons):
                        older["vai_tro"] = "cha"
                    elif older["gioi_tinh"] == "Nữ" and not any(x["vai_tro"] == "me" for x in persons):
                        older["vai_tro"] = "me"

    roster["persons"] = persons
    return roster


def _render(roster: dict) -> str:
    persons = roster.get("persons") or []

    def one(role):
        return next((p for p in persons if p.get("vai_tro") == role), None)

    def src(p):
        return ", ".join(p.get("nguon") or []) or "?"

    def desc(p):
        dead = " (đã chết)" if p.get("da_chet") else ""
        return f'{p.get("ten") or "?"}{dead} — nguồn: {src(p)}'

    con, cha, me = one("con"), one("cha"), one("me")
    req = next((p for p in persons if p.get("_requester")), None)

    lines = []
    if con:
        lines.append(f"- NGƯỜI ĐƯỢC ĐĂNG KÝ LẠI (con): {desc(con)}")
    if cha:
        lines.append(f"- CHA: {desc(cha)}")
    if me:
        lines.append(f"- MẸ: {desc(me)}")
    if req:
        lines.append(f"- NGƯỜI YÊU CẦU: {req.get('ten')} — nguồn: {src(req)}")
    else:
        lines.append("- NGƯỜI YÊU CẦU: không xác định được → để trống, dùng mặc định.")
    for s in (p for p in persons if p.get("vai_tro") in ("chong", "vo")):
        quan_he = "chồng" if s["vai_tro"] == "chong" else "vợ"
        lines.append(f"- LƯU Ý: {s.get('ten')} là {quan_he} trong giấy kết hôn, KHÔNG phải cha/mẹ.")

    if not any((con, cha, me)):
        return ""
    body = "\n".join(lines)
    return (
        "\n\n<ke_hoach_da_xac_dinh>\n"
        "Vai trò từng người ĐÃ được xác định (DÙNG LÀM CHUẨN, không tự gán lại vai trò khác):\n"
        f"{body}\n"
        "Chỉ trích giá trị đúng theo vai trò trên. Người 'đã chết' → *_ResidenceDomestic = "
        '{"quocGia":"","tinh":"","xa":"","diaChi":"Đã chết"}.\n'
        "LƯU Ý: 'đã chết' CHỈ áp cho *_ResidenceDomestic. VẪN phải trích NĂM SINH, DÂN TỘC, QUỐC TỊCH "
        "của cha/mẹ đã mất TỪ chính TRÍCH LỤC KHAI TỬ của người đó (giấy khai tử ghi rõ 'Ngày, tháng, "
        "năm sinh', 'Dân tộc', 'Quốc tịch' của người đã mất). KHÔNG bỏ trống các field này chỉ vì đã chết.\n"
        "LƯU Ý SỐ ĐĂNG KÝ KHAI SINH TRƯỚC ĐÂY (PreviousRegistration_Number/Date/AgencyProvince): CHỈ lấy từ "
        "GIẤY KHAI SINH / TRÍCH LỤC KHAI SINH / BẢN SAO KHAI SINH / TỜ KHAI ĐĂNG KÝ LẠI KHAI SINH của con. "
        "GIẤY CHỨNG NHẬN KẾT HÔN (có 'Số'/'Quyển số' ở đầu) và TRÍCH LỤC KHAI TỬ thì BỎ QUA — KHÔNG lấy "
        "số/ngày/nơi từ chúng. Không có giấy khai sinh trong hồ sơ → để trống PreviousRegistration_*.\n"
        "</ke_hoach_da_xac_dinh>"
    )


async def build_context(documents: list[dict], options: dict | None = None) -> str:
    """Context builder cho runner: OCR docs -> đoạn context ghim vai trò (rỗng nếu không suy được)."""
    if not documents:
        return ""
    messages = [
        {"role": "system", "content": _ROSTER_PROMPT + _requester_hint(options or {})},
        {"role": "user", "content": _build_user(documents)},
    ]
    raw = await client.chat(
        messages,
        max_tokens=_REASON_MAX_TOKENS,
        temperature=0,
        enable_thinking=settings.agent_reasoning,
    )
    roster = client.extract_json_block(raw)
    roster = _apply_gate(roster, options)
    return _render(roster)
