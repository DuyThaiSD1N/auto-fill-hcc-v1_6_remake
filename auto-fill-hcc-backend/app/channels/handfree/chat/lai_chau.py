"""Cổng Lai Châu (dichvucong.laichau.gov.vn, eForm Nth đời cũ) — dẫn các trang của luồng nộp hồ sơ.

Cổng tách MỖI BƯỚC thành một trang riêng (bấm "Đồng ý và tiếp tục" là tải hẳn trang mới, tiêu đề "Bước N - …"):
    1 Trường hợp nộp hồ sơ (chon-truong-hop-ho-so) → 2 Thông tin người nộp → 3 Thành phần hồ sơ → 4 Lệ phí hồ sơ
    → bước xác nhận / nộp.
Nhận giấy tờ, điền (bước 2) và đính kèm (bước 3) vẫn đi đường cũ của flow.py. File này chỉ thêm:
  - trang 1: extension đọc "Cơ quan giải quyết hồ sơ" + "Trường hợp giải quyết" (ô chỉ một lựa chọn thì chọn luôn),
    trợ lý hiện thẻ chọn (dùng chung thẻ nhận kết quả của cổng liên thông) để công dân chọn trường hợp;
  - nút cam "Đồng ý và tiếp tục" (trợ lý bấm nút cùng tên của cổng) ở trang 1, sau khi điền bước 2, sau khi đính kèm
    bước 3 và ở trang Lệ phí;
  - trang 4 Lệ phí: đọc "Hình thức nhận kết quả" + "Mức lệ phí"; nhận kết quả tại nhà mà ô địa chỉ trống thì bấm "Lấy
    địa chỉ của Người nộp", ô Số lượng trống thì để 1; thẻ chọn để công dân đổi cách nhận / chọn mức;
  - sang trang sau Lệ phí: nhắc công dân rà lại và TỰ bấm nộp (trợ lý không nộp).
Trợ lý bấm hay công dân tự bấm đều được: sang trang là sidebar tải lại, watcher báo bước mới (lcStep).

Bật khi thủ tục khai `laiChauFeeStep` và extension khai supportsLaiChauFeeStep; chế độ Mông giữ luồng cũ (câu chỉ có
bản tiếng Việt). flow.py chỉ gọi các hàm ở đây; mỗi hàm tự trả lại reply cũ khi luồng không bật.

Cổng khác cùng nền eForm Nth (Cổng DVC Bộ Công an dichvucong.bocongan.gov.vn — đăng ký xe) dùng lại trang 1 qua các khoá
của `laiChauFeeStep`:
  - `capability`: cờ extension riêng (bản cũ đã khai supportsLaiChauFeeStep nhưng engine chỉ chạy trên host Lai Châu);
  - `caseOnly`: chỉ dẫn trang "Chọn trường hợp hồ sơ" (các trang sau đi luồng chung — không nút "Đồng ý và tiếp tục"
    sau điền / đính kèm, không bước Lệ phí);
  - `caseGroups: "auto"`: không biết trước tên ô → extension tự đọc MỌI ô chọn đang hiện trong khung chọn trường hợp
    (Loại xe, rồi các ô cổng hiện thêm sau khi chọn), nhãn + dấu (*) lấy trên trang;
  - `caseAgencyByProvince`: ô cơ quan trợ lý tự chọn theo tỉnh; `afterPick` = ô đó chỉ hiện SAU một lựa chọn khác (sang
    tên xe 2.000076: chọn Loại xe xong cổng mới hiện "Cơ quan giải quyết hồ sơ") → không chờ ô ở lượt đọc đầu, ô vừa
    hiện mà còn trống thì đọc lại kèm presets.
"""
import json
import re

from app.channels.handfree.chat import lien_thong
from app.channels.handfree.chat import script_vi as vi
from app.channels.handfree.chat import tu_phap_v2
from app.channels.handfree.chat.intents import Intent, asks_next_step

CAPABILITY = "supportsLaiChauFeeStep"
CASE, DECLARATION, ATTACHMENT, FEE = 1, 2, 3, 4
NEXT_SEND = "__action:lc_next"
_COMMANDS = {"lc_next", "lc_step_report", "lc_result_report", "lc_result_pick", "lc_case_changed"}
# Nhãn hiển thị trên thẻ; name = name ô trên cổng. Ô không có trên trang (vd nơi nộp chỉ hiện khi trường hợp đòi) thì
# extension báo present=false, thẻ bỏ dòng đó.
DEFAULT_CASE_GROUPS = [
    {"name": "maCoQuan", "label": "Cơ quan giải quyết hồ sơ"},
    {"name": "maQttt", "label": "Trường hợp giải quyết"},
    {"name": "maQuanHuyenNop", "label": "Quận/Huyện nộp hồ sơ"},
    {"name": "maPhuongXaNop", "label": "Phường/Xã nộp hồ sơ"},
]
# "loaiLePhi" = ô loaiLePhi_<mã loại lệ phí>, extension tự tìm.
DEFAULT_FEE_GROUPS = [
    {"name": "maHinhThucNhanKetQua", "label": "Hình thức nhận kết quả"},
    {"name": "loaiLePhi", "label": "Mức lệ phí (đồng)"},
]
_CASE, _FEE = "maQttt", "loaiLePhi"


def _config(proc: dict | None) -> dict:
    cfg = (proc or {}).get("laiChauFeeStep")
    return cfg if isinstance(cfg, dict) else {}


def is_active(proc: dict | None) -> bool:
    return bool((proc or {}).get("laiChauFeeStep"))


def enabled(conv: dict, proc: dict | None) -> bool:
    caps = conv.get("client_capabilities") or {}
    extra = _config(proc).get("capability")
    return (is_active(proc) and caps.get(CAPABILITY) is True and (not extra or caps.get(extra) is True)
            and (conv.get("lang") or "vi") != "hmong")


def case_only(proc: dict | None) -> bool:
    """Cổng chỉ dùng trang chọn trường hợp của luồng này (Bộ Công an): các bước sau đi luồng chung."""
    return bool(_config(proc).get("caseOnly"))


# Ô "*" = extension tự dò mọi ô chọn đang hiện trong khung chọn trường hợp.
_AUTO = [{"name": "*"}]


def _auto(proc: dict | None, page: int) -> bool:
    return page == CASE and _config(proc).get("caseGroups") == "auto"


def _case_hint(proc: dict | None) -> dict | None:
    """`caseHint` (registry): việc công dân phải làm ở trang chọn trường hợp, dạng markdown (vd "**Cơ quan giải quyết hồ
    sơ** (Công an tỉnh …)"). Nói ngay khi tới trang và khi trợ lý không đọc được ô nào."""
    hint = _clean(_config(proc).get("caseHint"), 300)
    return {"hint_md": hint, "hint_tts": hint.replace("**", "")} if hint else None


def _presets(conv: dict, proc: dict | None) -> list[dict]:
    """`caseAgencyByProvince` (registry, vd hộ chiếu 1.001456): trợ lý tự chọn ô cơ quan (nhãn chứa `label`) theo tỉnh
    của TÀI KHOẢN trợ lý (user 18/11; tài khoản thiếu tỉnh thì theo nơi làm thủ tục) — extension lấy lựa chọn chứa NGUYÊN
    cụm tên tỉnh (`match`), nhiều mục thì ưu tiên mục có `prefer`; không ra đúng một mục thì để công dân chọn trên thẻ."""
    from app.pipelines._shared import fold
    from app.pipelines._shared.area_remap import canonical_province

    cfg = _config(proc).get("caseAgencyByProvince")
    province = (canonical_province((conv.get("auth_user") or {}).get("tinh") or "")
                or canonical_province(((conv.get("location") or {}).get("province")) or ""))
    if not isinstance(cfg, dict) or not cfg.get("label") or not province:
        return []
    return [{"label": cfg["label"], "match": fold(province), "prefer": cfg.get("prefer") or ""}]


def _preset_after_pick(proc: dict | None) -> bool:
    cfg = _config(proc).get("caseAgencyByProvince")
    return isinstance(cfg, dict) and cfg.get("afterPick") is True


def _preset_followup(conv: dict, proc: dict | None, rows: list[dict], payload: dict) -> dict | None:
    """`afterPick`: ô cơ quan theo tỉnh đang hiện mà còn trống (vừa hiện sau khi công dân chọn Loại xe) → lệnh đọc lại
    kèm presets để extension chọn theo tỉnh. Mỗi trạng thái các ô chỉ thử một lần (không ra đúng một mục thì để công dân
    chọn trên thẻ, không lặp)."""
    if not _preset_after_pick(proc):
        return None
    if any(str(x).startswith("preset:") for x in payload.get("prepared") or []):
        return None
    label = _clean(_config(proc)["caseAgencyByProvince"].get("label")).lower()
    row = next((row for row in rows if label and label in row["label"].lower()), None)
    presets = _presets(conv, proc)
    if not row or row["value"] or not presets:
        return None
    signature = json.dumps([[row["name"], row["value"]] for row in rows], ensure_ascii=False)
    st = _st(conv)
    if st.get("preset_try") == signature:
        return None
    st["preset_try"] = signature
    return {"type": "lc_result_scan", "groups": _groups(proc, CASE), "prepare": False, "presets": presets}


# Ô "Điểm đăng ký" (đăng ký xe, ảnh 24/11): danh sách cổng = vài điểm PC08 + mọi Công an xã/phường của tỉnh, thẻ cắt còn
# 8 nút nên không chắc có xã của công dân. User 24/11: thẻ LUÔN chỉ bày các điểm PC08 + một nút "Đăng ký tại <Công an
# xã/phường của TÀI KHOẢN>" (tài khoản thiếu xã thì theo nơi làm thủ tục). Cổng liệt kê xã theo địa chỉ thường trú / tạm
# trú của công dân → xã của tài khoản có thể không có (tài khoản Khánh Hòa, công dân thường trú Hà Nội): nút thành "Đăng ký
# tại Công an xã/phường", bấm thì trợ lý nói rõ không có trong danh sách, mời chọn trên trang.
_PC08 = re.compile(r"^pc\s*0?8\b")
_WARD_POLICE = re.compile(r"^cong an (phuong|xa|dac khu|thi tran)\s+")
_WARD_LEVEL = re.compile(r"^(phuong|xa|dac khu|thi tran)\s+")
# Giá trị giữ chỗ của nút xã/phường khi không khớp được xã của tài khoản (không phải lựa chọn của cổng).
_WARD_ANY = "__ward__"


def _account_ward(conv: dict) -> str:
    return _clean((conv.get("auth_user") or {}).get("xa") or (conv.get("location") or {}).get("ward"), 80)


def _ward_key(text) -> str:
    """"Công an phường Hiệp Hoà" / "Phường Hiệp Hòa" → "phuong hiep hoa" (bỏ dấu, dấu câu, chữ "Công an")."""
    from app.pipelines._shared import fold

    return re.sub(r"^cong an\s+", "", re.sub(r"[^a-z0-9]+", " ", fold(_clean(text))).strip())


def _account_ward_option(conv: dict, options: list[str]) -> str:
    """Lựa chọn của xã/phường tài khoản (rồi nơi làm thủ tục) trong danh sách — ghi "Phường X" hay "Công an phường X"
    đều được; không ra đúng một mục → ""."""
    keyed = [(o, _ward_key(o)) for o in options]
    for ward in ((conv.get("auth_user") or {}).get("xa"), (conv.get("location") or {}).get("ward")):
        want = _ward_key(ward)
        if not want:
            continue
        # Tài khoản ghi đủ cấp ("Phường Ba Đình") thì khớp nguyên cụm; chỉ ghi tên (hoặc cổng ghi cấp khác — danh mục cũ
        # ghi "Xã" khi cổng là "Phường") thì khớp tên, trùng tên thì bỏ.
        found = [o for o, k in keyed if k == want] or [
            o for o, k in keyed if _WARD_LEVEL.sub("", k) == _WARD_LEVEL.sub("", want)]
        if len(found) == 1:
            return found[0]
    return ""


def _account_ward_police(conv: dict, options: list[str]) -> str:
    """Lựa chọn "Công an <xã/phường>" của tài khoản (rồi nơi làm thủ tục) trong danh sách; không ra đúng một mục → ""."""
    from app.pipelines._shared import fold

    return _account_ward_option(conv, [o for o in options if _WARD_POLICE.match(fold(o))])


# Ô "Phường/Xã" của trang chọn trường hợp (trình báo mất hộ chiếu cấp xã 1.010386, ảnh 24/11; Lai Châu "Phường/Xã nộp hồ
# sơ"). User 24/11: thủ tục nào có ô chọn phường/xã thì trợ lý TỰ chọn theo xã/phường của TÀI KHOẢN (thiếu thì theo nơi
# làm thủ tục) như ô tỉnh, không bắt công dân bấm. Danh sách cổng chỉ nạp SAU khi chọn tỉnh → BE đọc danh sách ở lượt báo,
# khớp đúng tên rồi gửi lệnh chọn (lc_result_set — bản extension cũ cũng chạy); danh sách không có xã đó thì để công dân
# chọn và nói rõ.
_WARD_FIELD = re.compile(r"\b(phuong\s*/\s*xa|xa\s*/\s*phuong)\b")


def _ward_field(row: dict) -> bool:
    from app.pipelines._shared import fold

    return bool(_WARD_FIELD.search(fold(row.get("label") or "")))


def _ward_targets(conv: dict, rows: list[dict], groups) -> list[tuple[dict, str]]:
    """Ô Phường/Xã còn trống, chọn được (không khoá, có lựa chọn) → [(dòng, lựa chọn của xã tài khoản hoặc "")]. Thẻ cắt
    còn 8 nút nên xã của tài khoản (hoặc xã đang chọn) được đưa lên đầu dòng."""
    raw = {str(g.get("name")): g for g in groups or [] if isinstance(g, dict)}
    out = []
    for row in rows:
        if row["fixed"] or not _ward_field(row):
            continue
        options = [_clean(o, 80) for o in (raw.get(row["name"]) or {}).get("options") or [] if _clean(o, 80)]
        match = "" if row["value"] else _account_ward_option(conv, options)
        first = row["value"] or match
        if first and first not in row["options"]:
            row["options"] = [first, *row["options"][:lien_thong._MAX_OPTIONS - 1]]
        if not row["value"]:
            out.append((row, match))
    return out


def _ward_followup(conv: dict, proc: dict | None, targets: list[tuple[dict, str]], rows: list[dict]):
    """Ô Phường/Xã trống mà danh sách có đúng xã của tài khoản → (dòng, lệnh chọn). Mỗi trạng thái các ô chỉ thử một lần
    (chọn hỏng thì để công dân chọn trên thẻ, không lặp)."""
    st = _st(conv)
    for row, value in targets:
        if not value:
            continue
        signature = json.dumps([row["name"], value, [[r["name"], r["value"]] for r in rows]], ensure_ascii=False)
        if st.get("ward_try") == signature:
            continue
        st["ward_try"], st["ward_auto"] = signature, {"name": row["name"], "value": value}
        return row, {"type": "lc_result_set", "name": row["name"], "value": value, "groups": _groups(proc, CASE)}
    return None


def _ward_missing_notes(conv: dict, targets: list[tuple[dict, str]]) -> list[dict]:
    """Danh sách Phường/Xã của cổng không có xã của tài khoản → nói một lần cho mỗi danh sách."""
    ward, st, notes = _account_ward(conv), _st(conv), []
    for row, value in targets:
        key = json.dumps([row["name"], row["options"]], ensure_ascii=False)
        if value or not ward or st.get("ward_note") == key:
            continue
        st["ward_note"] = key
        notes.append({k: tpl.format(label=row["label"], ward=ward) for k, tpl in vi.LC_WARD_NOT_LISTED.items()})
    return notes


def _ward_points(conv: dict, rows: list[dict], groups) -> dict[str, str]:
    """Rút gọn dòng Điểm đăng ký (PC08 + Công an xã/phường) trên thẻ còn các điểm PC08 + một nút xã/phường; trả {name ô:
    lựa chọn xã của tài khoản, hoặc _WARD_ANY khi danh sách cổng không có xã đó}."""
    from app.pipelines._shared import fold

    raw = {str(g.get("name")): g for g in groups or [] if isinstance(g, dict)}
    out = {}
    for row in rows:
        if row["fixed"]:
            continue
        options = [_clean(o, 80) for o in (raw.get(row["name"]) or {}).get("options") or [] if _clean(o, 80)]
        points = [o for o in options if _PC08.match(fold(o))]
        if not points or not any(_WARD_POLICE.match(fold(o)) for o in options):
            continue
        ward = _account_ward_police(conv, options) or _WARD_ANY
        keep = [*points[:lien_thong._MAX_OPTIONS - 2], ward]
        # Trên trang đang chọn một xã khác (công dân tự chọn) → vẫn hiện để thẻ khớp trang.
        if row["value"] in options and row["value"] not in keep:
            keep.append(row["value"])
        row["options"], out[row["name"]] = keep, ward
    return out


def _ward_label(card: dict, wards: dict[str, str]) -> None:
    """Chữ trên nút xã/phường; bấm vẫn gửi đúng tên lựa chọn của cổng (hoặc giá trị giữ chỗ)."""
    for row in card["rows"]:
        ward = wards.get(row["name"])
        for option in row["options"] if ward else []:
            if option["label"] == ward:
                option["label"] = vi.LC_WARD_POINT_ANY if ward == _WARD_ANY else vi.LC_WARD_POINT_AT.format(ward=ward)


def _ward_missing(conv: dict):
    """Bấm nút xã/phường mà danh sách cổng không có xã của tài khoản → nói rõ, gửi lại thẻ (sidebar khoá nút khi bấm)."""
    ward = _account_ward(conv)
    r = _reply(_say(vi.LC_WARD_POINT_MISSING, ward=ward) if ward else _say(vi.LC_WARD_POINT_NO_ACCOUNT))
    st = _st(conv)
    r.cards = [st["case_card"]] if st.get("case_card") else []
    r.chips = list(st.get("case_chips") or [])
    return r


def _groups(proc: dict | None, page: int = FEE) -> list[dict]:
    if _auto(proc, page):
        return [dict(g) for g in _AUTO]
    key, default = ("caseGroups", DEFAULT_CASE_GROUPS) if page == CASE else ("groups", DEFAULT_FEE_GROUPS)
    groups = _config(proc).get(key) or default
    return [dict(g) for g in groups if isinstance(g, dict) and g.get("name")]


def _read_configs(proc: dict | None, page: int, read) -> list[dict]:
    """Dòng thẻ theo registry; chế độ tự dò thì theo đúng các ô extension đọc được (tên + nhãn trên trang)."""
    if not _auto(proc, page):
        return _groups(proc, page)
    out = []
    for got in read or []:
        if isinstance(got, dict) and _clean(got.get("name"), 120):
            label = _clean(got.get("label"), 80).rstrip(" :*") or _clean(got.get("name"), 120)
            out.append({"name": _clean(got.get("name"), 120), "label": label})
    return out


def _st(conv: dict) -> dict:
    return conv.setdefault("lai_chau", {})


def _at(conv: dict) -> int:
    return int(_st(conv).get("at") or 0)


def _say(tpl: dict, **kw) -> tuple[str, str]:
    return tpl["md"].format(**kw), tpl["tts"].format(**kw)


def _clean(value, limit: int = 200) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _reply(md_tts: tuple[str, str] = ("", "")):
    from app.channels.handfree.chat.flow import Reply

    return Reply(*md_tts)


def _page_step(payload: dict | None) -> int:
    try:
        step = int((payload or {}).get("lcStep") or 0)
    except (TypeError, ValueError):
        return 0
    return step if 1 <= step <= 9 else 0


def next_chip() -> dict:
    """Nút cam to "Đồng ý và tiếp tục": trợ lý bấm nút cùng tên của cổng."""
    return {"label": vi.LC_CONTINUE_CHIP, "send": NEXT_SEND, "solid": True, "cta": True}


# ── Bước 2: điền xong ──

def fill_report_reply(conv: dict, proc: dict | None, reply):
    """Điền xong bước Thông tin người nộp: thêm nút cam "Đồng ý và tiếp tục" để trợ lý bấm sang Thành phần hồ sơ."""
    if not enabled(conv, proc) or reply is None or case_only(proc):
        return reply
    _st(conv)["at"] = DECLARATION
    if not any(isinstance(c, dict) and c.get("cta") for c in reply.chips or []):
        reply.chips = [*(reply.chips or []), next_chip()]
    return reply


# ── Bước 3: đính kèm xong ──

def attach_done_reply(conv: dict, proc: dict | None, reply, *, attached: int, skipped: int, errors: list[str]):
    """Đính kèm xong: thay lời "tự bấm nộp" bằng nút "Đồng ý và tiếp tục" sang bước Lệ phí hồ sơ."""
    from app.channels.handfree.chat import flow

    if not enabled(conv, proc) or case_only(proc):
        return reply
    _st(conv)["at"] = ATTACHMENT
    card = tu_phap_v2._card(conv, "attach", vi.FLOW2_ATTACH_STEPS, active=1, done=not errors, failed=bool(errors))
    if errors:
        reply.actions = [*reply.actions, card]
        reply.chips = [*[c for c in reply.chips if not c.get("cta")], next_chip()]
        return reply
    if attached == 0 and skipped > 0:
        r = flow.Reply(*_say(vi.FLOW2_ATTACH_ALL_EXIST))
    else:
        plan_list = "\n".join(flow._attachment_plan_line(p) for p in (conv.get("attach_plan") or [])[:10])
        r = flow.Reply(*_say(vi.FLOW2_ATTACH_RESULT, attached=attached, plan_list=plan_list))
    md, tts = _say(vi.LC_ATTACH_NEXT)
    r.actions = [*reply.actions, card, {"type": "trail_message", "md": md}]
    r.tts_text += tts
    r.chips = [flow._supplement_documents_chip(), next_chip()]
    return r


# ── Chuyển trang ──

def next_reply(conv: dict):
    r = _reply(_say(vi.LC_MOVING))
    r.actions = [{"type": "lc_next"}]
    return r


def _step_report(conv: dict, proc: dict | None, payload: dict):
    """Chỉ tới đây khi cổng KHÔNG sang trang (sang trang thì sidebar tải lại, watcher báo trang mới)."""
    message = _clean(payload.get("message"))
    if payload.get("clicked") and not message:
        return _reply()
    note = f": *{message}*" if message else ""
    r = _reply(_say(vi.LC_BLOCKED, message=note))
    r.chips = [{"label": vi.LC_RETRY_CHIP, "send": NEXT_SEND, "solid": True}]
    from app.channels.handfree.chat import field_review

    if _at(conv) != CASE and field_review.bca_nth(proc) and field_review.flow_v2(conv, proc):
        # eForm Nth Bộ Công an có vòng bổ sung ô: cổng chặn vì ô còn trống → mời hỏi từng ô (bộ đọc tô lại theo lỗi cổng).
        r.chips = [*field_review.start_chips(conv, proc, [next_chip()]), *r.chips]
    if _at(conv) == CASE and _auto(proc, CASE):
        # Trang chọn trường hợp tự dò: đọc lại các ô (không làm sẵn gì) để thẻ chọn hiện đúng ô cổng đang đòi. Không kèm
        # nút bấm lại: lượt đọc lại tự hiện nút cam khi các ô bắt buộc đã chọn đủ (user 24/11).
        r.chips = [c for c in r.chips if c.get("send") != NEXT_SEND]
        r.actions = [_case_rescan(conv, proc)]
    return r


def _case_rescan(conv: dict, proc: dict | None) -> dict:
    """Đọc lại trang chọn trường hợp; kèm presets để ô cơ quan nạp chậm (lượt đầu chưa có) vẫn được chọn bù."""
    action = {"type": "lc_result_scan", "groups": _groups(proc, CASE), "prepare": False}
    presets = _presets(conv, proc)
    if presets:
        action["presets"] = presets
    return action


def _on_page(conv: dict, proc: dict | None, payload: dict):
    """Trang vừa đổi bước. None = để flow cũ xử lý (bước 2, 3 và mọi trang lặp lại)."""
    step = _page_step(payload)
    st = _st(conv)
    before = int(st.get("at") or 0)
    if step == CASE and before == CASE:
        # Trang chọn trường hợp có form nên extension báo declarationTarget → luồng cũ tưởng đã vào trang kê khai, xin
        # phép xử lý dữ liệu NGAY ở đây (state consent không được theo dõi trang: sang bước 2 là treo). Im lặng (reply
        # rỗng không đè last_reply) cho tới khi trang thật sự sang bước 2.
        return _reply()
    if case_only(proc) and step != CASE:
        if (before == CASE and payload.get("bcaKeKhaiForm") is False and not payload.get("loginPage")
                and not payload.get("bcaConfirmPage")):
            # Chạy thật 20/11 (sang tên xe 2.000076): chọn Loại xe xong trang báo lcStep 0 + formKind "standard" dù vẫn
            # là trang chọn trường hợp (chưa có form kê khai CongDan_*) → luồng cũ xin phép xử lý dữ liệu ngay ở đây.
            # Chỉ rời trang khi form kê khai thật đã hiện.
            return _reply()
        st["at"] = step  # rời trang chọn trường hợp: các trang sau đi luồng chung
        return None
    if not step or step == before:
        return None
    st["at"] = step
    if step == CASE:
        md, tts = _say(vi.LC_CASE_READING)
        hint = _case_hint(proc)
        if hint:
            hint_md, hint_tts = _say(vi.LC_CASE_HINT, **hint)
            md, tts = md + hint_md, tts + hint_tts
        r = _reply((md, tts))
        action = {"type": "lc_result_scan", "groups": _groups(proc, CASE)}
        # afterPick: ô cơ quan chưa có ở lượt đọc đầu → không gửi presets (extension sẽ chờ ô tới 6 giây vô ích).
        presets = [] if _preset_after_pick(proc) else _presets(conv, proc)
        if presets:
            action["presets"] = presets
        r.actions = [action]
        return r
    if step == FEE:
        r = _reply(_say(vi.LC_RESULT_READING))
        r.actions = [{"type": "lc_result_scan", "groups": _groups(proc, FEE)}]
        return r
    if step > FEE and before == FEE:
        return _reply(_say(vi.LC_AFTER_FEE))
    return None


# ── Trang 1 (trường hợp) / trang 4 (nhận kết quả + lệ phí): thẻ chọn ──

def _summary(rows: list[dict]) -> tuple[str, str]:
    """Các ô đang chọn trên trang (câu tóm tắt của cổng liên thông nói "giấy" — không hợp ô trường hợp / lệ phí)."""
    lines_md = [vi.LC_SUMMARY_LINE.format(label=row["label"], value=row["value"] or vi.LT_RESULT_EMPTY)
                for row in rows]
    lines_tts = [f"{row['label']}: {row['value'] or vi.LT_RESULT_EMPTY}" for row in rows]
    return _say(vi.LC_SUMMARY, lines_md="\n".join(lines_md), lines_tts="; ".join(lines_tts))


def _prepared_notes(proc: dict | None, page: int, rows: list[dict], payload: dict) -> list[dict]:
    """Câu báo những việc extension đã làm sẵn ở lượt đọc (địa chỉ, ô theo tỉnh, ô một lựa chọn)."""
    prepared = {str(x) for x in payload.get("prepared") or []}
    notes = [vi.LC_ADDRESS_PULLED] if "address" in prepared else []
    for row in rows:
        if f"preset:{row['name']}" in prepared and row["value"]:
            notes.append({key: tpl.format(label=row["label"], value=row["value"])
                          for key, tpl in vi.LC_CASE_PRESET.items()})
    if f"auto:{_FEE}" in prepared:
        notes.append(vi.LC_FEE_AUTO)
    if f"auto:{_CASE}" in prepared:
        notes.append(vi.LC_CASE_AUTO)
    elif _auto(proc, page) and any(x.startswith("auto:") for x in prepared):
        notes.append(vi.LC_SINGLE_AUTO)
    return notes


def _result_report(conv: dict, proc: dict | None, payload: dict):
    page = CASE if _at(conv) == CASE else FEE
    rows = lien_thong.result_rows(_read_configs(proc, page, payload.get("groups")), payload.get("groups"))
    preset_label = _clean((_config(proc).get("caseAgencyByProvince") or {}).get("label")).lower() if page == CASE else ""
    for row in rows:
        # Ô cơ quan trợ lý chọn theo tỉnh tài khoản: chỉ hiện giá trị (thẻ tối đa 8 nút — danh sách 34 tỉnh bị cắt).
        if preset_label and row["value"] and preset_label in row["label"].lower():
            row["fixed"], row["options"] = True, []
    wards = _ward_points(conv, rows, payload.get("groups")) if _auto(proc, page) else {}
    ward_rows = _ward_targets(conv, rows, payload.get("groups")) if page == CASE else []
    _st(conv)["result_rows"] = rows
    if not rows:
        hint = _case_hint(proc) if page == CASE else None
        if hint:
            r = _reply(_say(vi.LC_CASE_UNREAD_HINT, **hint))
            r.chips = [next_chip()]
            return r
        unread = vi.LC_CASE_UNREAD_AUTO if _auto(proc, page) else vi.LC_CASE_UNREAD if page == CASE else vi.LC_RESULT_UNREAD
        r = _reply(_say(unread))
        r.chips = [next_chip()]
        return r
    changed = payload.get("changed") if isinstance(payload.get("changed"), dict) else None
    followup = _preset_followup(conv, proc, rows, payload) if page == CASE else None
    if followup:
        # Ô cơ quan vừa hiện: chọn theo tỉnh trước rồi mới hiện thẻ (lượt đọc lại trả về lc_result_report đủ thẻ + nút).
        md, tts = ("", "")
        if changed and changed.get("ok"):
            label = next((row["label"] for row in rows if row["name"] == changed.get("name")), "")
            md, tts = _say(vi.LT_RESULT_CHANGED, label=label, value=_clean(changed.get("value"), 80))
        pick_md, pick_tts = _say(vi.LC_CASE_PRESET_PICKING, label=_clean(
            _config(proc)["caseAgencyByProvince"].get("label"), 80))
        r = _reply(((md + pick_md).lstrip(), (tts + pick_tts).lstrip()))
        r.actions = [followup]
        return r
    ward_pick = _ward_followup(conv, proc, ward_rows, rows)
    if ward_pick:
        # Ô Phường/Xã vừa nạp danh sách: chọn theo xã của tài khoản trước, lượt báo sau mới hiện thẻ + nút.
        row, action = ward_pick
        md, tts = ("", "")
        if changed and changed.get("ok"):
            label = next((x["label"] for x in rows if x["name"] == changed.get("name")), "")
            md, tts = _say(vi.LT_RESULT_CHANGED, label=label, value=_clean(changed.get("value"), 80))
        for note in _prepared_notes(proc, page, rows, payload):
            md, tts = md + note["md"], tts + note["tts"]
        pick_md, pick_tts = _say(vi.LC_WARD_PICKING, label=row["label"], value=action["value"])
        r = _reply(((md + pick_md).lstrip(), (tts + pick_tts).lstrip()))
        r.actions = [action]
        return r
    auto_ward = _st(conv).pop("ward_auto", None) if changed else None
    if changed:
        label = next((row["label"] for row in rows if row["name"] == changed.get("name")), "")
        value = _clean(changed.get("value"), 80)
        if changed.get("ok") and auto_ward == {"name": changed.get("name"), "value": value}:
            # Lượt chọn Phường/Xã của trợ lý: tóm tắt cả trang + nói rõ chọn theo tài khoản (không phải "đã đổi").
            md, tts = _summary(rows)
            picked_md, picked_tts = _say(vi.LC_WARD_PICKED, label=label, value=value)
            md, tts = md + picked_md, tts + picked_tts
        else:
            tpl = vi.LT_RESULT_CHANGED if changed.get("ok") else vi.LT_RESULT_FAILED
            md, tts = _say(tpl, label=label, value=value)
    else:
        md, tts = _summary(rows)
    notes = [*_prepared_notes(proc, page, rows, payload), *_ward_missing_notes(conv, ward_rows)]
    for note in notes:
        md, tts = md + note["md"], tts + note["tts"]
    missing = ", ".join(_clean(x, 60) for x in payload.get("missing") or [] if _clean(x, 60))[:200]
    if missing:
        hint_md, hint_tts = _say(vi.LC_MISSING, fields=missing)
        md, tts = md + hint_md, tts + hint_tts
    must = _CASE if page == CASE else _FEE
    pending = next((row for row in rows if row["name"] == must and not row["value"] and row["options"]), None)
    incomplete = False
    if _auto(proc, page):
        # Tự dò: ô bắt buộc (dấu (*) trên trang) còn trống mà có lựa chọn → mời chọn đúng các ô đó.
        required = {str(g.get("name")) for g in payload.get("groups") or [] if isinstance(g, dict) and g.get("required")}
        empty = [row["label"] for row in rows if row["name"] in required and not row["value"] and row["options"]]
        # Ô bắt buộc còn trống mà trợ lý không đọc được lựa chọn (danh sách cổng chỉ nạp khi gõ tìm) → chọn tay.
        stuck = [row["label"] for row in rows if row["name"] in required and not row["value"] and not row["options"]]
        # User 24/11: còn ô bắt buộc chưa chọn (cùng phép thử emptyRequired của extension) thì ẩn nút cam; chọn đủ — trên
        # thẻ, hoặc trên trang (lưới đỡ watchCase báo đọc lại) — thì lượt đọc sau mới hiện nút.
        incomplete = bool(empty or stuck)
        guide_md, guide_tts = _say(vi.LC_CASE_WAIT) if incomplete else _say(vi.LC_CASE_GUIDE)
        if empty:
            ask_md, ask_tts = _say(vi.LC_CASE_ASK_AUTO, fields_md=", ".join(f"**{x}**" for x in empty),
                                   fields_tts=", ".join(empty))
            guide_md, guide_tts = ask_md + guide_md, ask_tts + guide_tts
        if stuck:
            stuck_md, stuck_tts = _say(vi.LC_CASE_STUCK, fields_md=", ".join(f"**{x}**" for x in stuck),
                                       fields_tts=", ".join(stuck))
            guide_md, guide_tts = stuck_md + guide_md, stuck_tts + guide_tts
    elif page == CASE:
        guide_md, guide_tts = _say(vi.LC_CASE_ASK if pending else vi.LC_CASE_GUIDE)
    else:
        guide_md, guide_tts = _say(vi.LC_FEE_ASK if pending else vi.LC_CONTINUE_GUIDE)
    r = _reply((md, tts))
    card = lien_thong.result_card(rows, "lc_result_pick")
    _ward_label(card, wards)
    r.cards = [card]
    r.actions = [{"type": "trail_message", "md": guide_md}]
    r.tts_text += guide_tts
    r.chips = [] if incomplete else [next_chip()]
    if wards:
        _st(conv).update(case_card=card, case_chips=r.chips)
    return r


def _result_pick(conv: dict, proc: dict | None, payload: dict):
    name, value = str(payload.get("name") or ""), str(payload.get("value") or "")
    row = next((row for row in _st(conv).get("result_rows") or [] if row["name"] == name), None)
    if not row or value not in row["options"]:
        return _reply()
    if value == _WARD_ANY:
        return _ward_missing(conv)
    page = CASE if _at(conv) == CASE else FEE
    _st(conv).pop("ward_auto", None)  # công dân tự chọn: lượt báo sau nói "đã đổi", không nói "chọn theo tài khoản"
    r = _reply()
    r.actions = [{"type": "lc_result_set", "name": name, "value": value, "groups": _groups(proc, page)}]
    return r


def _case_changed(conv: dict, proc: dict | None):
    """Trang chọn trường hợp tự dò: ô trên trang đổi sau lượt đọc (cổng tải chậm, công dân tự chọn trên trang) → đọc lại
    (không làm sẵn gì), kết quả về lc_result_report dựng thẻ mới. Rời trang rồi thì im."""
    if _at(conv) != CASE or not _auto(proc, CASE):
        return _reply()
    r = _reply()
    r.actions = [_case_rescan(conv, proc)]
    return r


# ── Điều phối ──

def handle(conv: dict, proc: dict | None, intent):
    """Lệnh / sự kiện của luồng Lai Châu → Reply; không phải → None (flow cũ xử lý)."""
    if not enabled(conv, proc):
        return None
    payload = intent.payload if isinstance(intent.payload, dict) else {}
    if intent.kind == "event" and intent.value == "page_status":
        return _on_page(conv, proc, payload)
    if intent.kind != "action" or intent.value not in _COMMANDS:
        return None
    if intent.value == "lc_next":
        return next_reply(conv)
    if intent.value == "lc_step_report":
        return _step_report(conv, proc, payload)
    if intent.value == "lc_case_changed":
        return _case_changed(conv, proc)
    if intent.value == "lc_result_report":
        return _result_report(conv, proc, payload)
    return _result_pick(conv, proc, payload)


def voice_intent(conv: dict, message: str, page_context: dict | None) -> Intent | None:
    """"Bước tiếp theo" / "đồng ý và tiếp tục" ở trang có nút cam → bấm "Đồng ý và tiếp tục" của cổng."""
    from app.channels.handfree.procedure_registry import get_procedure

    proc = get_procedure(conv.get("procedure_key") or "")
    if not enabled(conv, proc):
        return None
    at = _page_step(page_context) or _at(conv)
    if case_only(proc) and _page_step(page_context) != CASE and at != CASE:
        return None
    ready = (
        at in (CASE, FEE)
        or (at == ATTACHMENT and conv.get("state") == "done")
        # Bước 2 chỉ sau khi đã điền (trước đó "tiếp theo" là chuyện giấy tờ của flow cũ).
        or (at == DECLARATION and conv.get("pipeline_status") == "waiting_attachment_page")
    )
    if not ready:
        return None
    folded = re.sub(r"\s+", " ", message or "").strip().lower()
    if asks_next_step(message) or "đồng ý và tiếp tục" in folded or "dong y va tiep tuc" in folded:
        return Intent("action", "lc_next", {"voice": True})
    return None
