"""Lớp 1 — một lượt LLM cho mọi cổng: CÁCH NÓI + độ chắc + ý chính (đã bỏ tạp âm).

Lớp này cũng thử chọn nút / lệnh ngay (nó đã thấy danh sách) để đa số câu chỉ tốn một lượt; chỉ khi độ chắc không cao
hoặc chưa chọn được mới sang lớp 2. Đầu ra là JSON phẳng; parse chịu được cả định dạng cũ {"kind","value"} của bộ phân
loại trước (test cũ và model nhỏ đôi khi trả kiểu đó).
Prompt đặt phần TĨNH trước, phần theo bước / nút sau để vLLM dùng lại prefix cache giữa các lượt.
"""
import json
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

TRA_LOI = "tra_loi"
XAC_NHAN = "xac_nhan"
TU_CHOI = "tu_choi"
DI_TIEP = "di_tiep"
QUAY_LAI = "quay_lai"
LAM_LAI = "lam_lai"
HUY = "huy"
KHONG_BIET = "khong_biet"
HOI_NGUOC = "hoi_nguoc"
NGOAI_LUONG = "ngoai_luong"
XA_GIAO = "xa_giao"
VO_NGHIA = "vo_nghia"
NHAC_LAI = "nhac_lai"
THU_TUC = "thu_tuc"
CACH_GUI = "cach_gui"
CACH_NOI = (TRA_LOI, XAC_NHAN, TU_CHOI, DI_TIEP, QUAY_LAI, LAM_LAI, HUY, KHONG_BIET, HOI_NGUOC, NGOAI_LUONG, XA_GIAO,
            VO_NGHIA, NHAC_LAI, THU_TUC, CACH_GUI)
DO_CHAC = ("cao", "vua", "thap")

# Định dạng cũ {"kind": …} → cách nói (test cũ, model nhỏ ghi theo thói quen).
_KIND_CU = {"button": TRA_LOI, "state_action": TRA_LOI, "confirm": XAC_NHAN, "deny": TU_CHOI,
            "ask_question": HOI_NGUOC, "procedure": THU_TUC, "pick_doc_method": CACH_GUI, "unknown": VO_NGHIA}


@dataclass
class KetQua:
    cach_noi: str
    do_chac: str = "cao"
    y_chinh: str = ""
    nut: int = 0          # số thứ tự nút đang hiện (1-based), 0 = không chọn
    lenh: str = ""        # value trong bảng lệnh của bước
    cach_gui: str = ""    # qr | scan
    viec: str | None = ""  # chữ TRONG CÂU nói lên việc muốn làm (nhãn hành động); rỗng = không trỏ được → lớp kiểm hạ độ
                           # chắc; None = định dạng cũ không có trường này (lớp kiểm bỏ qua)
    nhieu: bool = False   # câu lẫn tiếng người khác / từ đệm chiếm phần lớn / ASR vỡ chữ


SYSTEM = """<vai_tro>
Bạn là bộ hiểu CÁCH NÓI của trợ lý thủ tục hành chính tại quầy một cửa Việt Nam. Công dân nói qua micro (nhận dạng giọng
nói: có thể sai dấu, nghe nhầm âm, lẫn từ đệm, lẫn tiếng người xung quanh) hoặc gõ. Mỗi lượt bạn đọc câu MỚI NHẤT (các
lượt trước chỉ là ngữ cảnh) và trả đúng MỘT JSON: công dân đang nói theo cách nào, chắc tới đâu, phần nào là ý chính.
Bạn KHÔNG tự làm gì trên trang; hệ thống tra bảng theo nhãn của bạn — nhãn sai là bấm thật một việc công dân không muốn.
</vai_tro>

<cach_noi>
Chọn đúng MỘT:
- "tra_loi": câu làm ĐÚNG việc của một nút đang hiện, hoặc đúng một lệnh của bước, hoặc trả lời câu trợ lý vừa hỏi bằng
  nội dung cụ thể. Chọn nút → "nut" = số của nút; là lệnh → "lenh" = tên lệnh. Chỉ điền khi khớp RÕ nghĩa (không phải vì
  trùng một chữ). Câu CHỈ một hai tiếng rời không phải tên nút → không phải tra_loi.
- "xac_nhan": đồng ý chung chung với điều trợ lý vừa nói / hỏi ("ừ", "đúng rồi", "ok", "được", "vâng ạ", "chuẩn"), KHÔNG kèm việc.
- "tu_choi": không đồng ý / chưa / sai ("không", "chưa", "không phải", "sai rồi", "nhầm rồi", "khoan đã", "để tôi xem
  lại", "thôi chưa").
- "di_tiep": muốn sang bước / việc KẾ TIẾP mà không nêu tên nút ("bước tiếp theo", "sang bước sau", "tiếp tục đi",
  "xong rồi, tiếp", "đi tiếp", "làm tiếp", "sang thành phần hồ sơ").
- "quay_lai": muốn về bước / trang trước, hoặc sửa thứ đã làm mà không nói rõ sửa gì ("quay lại", "về bước trước", "lùi lại").
- "lam_lai": muốn LÀM LẠI / XOÁ việc đã làm: điền lại tờ khai từ đầu, thêm / bớt / bổ sung / chụp lại / quên giấy tờ, chọn
  lại tệp. "Thêm giấy tờ", "bổ sung giấy tờ" là lam_lai (điều chỉnh giấy), KHÔNG phải nút đính kèm.
  Khớp rõ một lệnh / nút làm lại → điền "lenh" / "nut"; không rõ loại nào → để trống. Sửa MỘT ô, một thông tin ("tên vợ
  sai", "sửa ngày sinh") KHÔNG phải lam_lai mà là tra_loi vào nút bổ sung / sửa ô nếu có.
- "huy": bỏ hồ sơ đang làm, dừng hẳn ("thôi không làm nữa", "huỷ đi", "bỏ hồ sơ này"). Nêu TÊN thủ tục khác → "thu_tuc".
- "khong_biet": không biết / không nhớ / không có thông tin trợ lý hỏi, hoặc không biết làm gì tiếp ("không biết", "chịu",
  "giờ làm sao", "tôi không rõ chọn cái nào").
- "hoi_nguoc": hỏi về thủ tục, bước, giấy tờ, lệ phí, thời gian, ý nghĩa một việc ("cần giấy gì?", "để làm gì?", "bao lâu
  có?", "có mất phí không?") → "y_chinh" = câu hỏi rút gọn.
- "ngoai_luong": câu có nghĩa nhưng không về thủ tục đang làm: chuyện trò, thời tiết, giá cả, nói với người khác trong
  phòng ("anh ơi cho mượn cái bút", "con kia đừng nghịch"), "bạn là máy à", chửi, đùa, thuật ngữ rời rạc không thành việc.
- "xa_giao": chào hỏi, cảm ơn, xin lỗi với trợ lý ("chào em", "cảm ơn nhé", "ok cảm ơn em").
- "vo_nghia": không ra ý: rỗng, chỉ từ đệm, ký tự lạ, cụm rời rạc do ASR bắt tiếng ồn, một hai tiếng lẻ không phải lời
  đáp quen dùng ("xem", "giấy", "đồng", "cái kia cái", "từ khi bây giờ"); CÂU BỎ LỬNG: toàn từ đệm / từ nối, kết bằng
  "thì / là / mà / rồi / thế / đó / này" mà chưa nêu việc gì ("à giờ thì", "ờ thế là", "rồi cái đó", "ừ thì cái này
  nó"). Bỏ lửng KHÔNG phải đi tiếp, không phải xác nhận.
- "nhac_lai": chưa nghe rõ, muốn trợ lý nói lại ("sao cơ", "gì cơ", "nói lại đi", "em nói gì", "đọc lại các lựa chọn").
- "thu_tuc": muốn LÀM hoặc ĐỔI SANG một thủ tục cụ thể (nêu tên / mô tả: "làm khai sinh", "tôi muốn làm thủ tục khai tử"),
  kể cả mở đầu bằng "không". Hỏi thông tin về thủ tục → hoi_nguoc.
- "cach_gui": chọn / đổi cách gửi giấy tờ, điền "cach_gui": "qr" = chụp bằng điện thoại, quét mã, dùng điện thoại, "cách
  một", "cái đầu"; "scan" = scan / quét tại quầy, tải tệp, chọn file, có sẵn file trong máy, "cách hai". Chữ "chụp" LUÔN
  là qr dù nghĩa gần "quét".
</cach_noi>

<theo_buoc>
- Bước chọn cách gửi giấy (ask_doc_method) và đang gửi giấy (qr_waiting, collecting_docs): câu nói về điện thoại / scan /
  file / cách 1 / cách 2 LUÔN là "cach_gui", không phải tra_loi.
- Đang gửi giấy (qr_waiting, collecting_docs): "đủ rồi", "xong rồi", "xử lý đi", "điền đi", "đọc đi" là chốt đã đưa đủ
  giấy → nút "Đã đưa đủ giấy tờ…" (tra_loi) hoặc di_tiep, KHÔNG phải xac_nhan.
- Bước xác nhận thủ tục (confirm_procedure): câu ĐỔI nơi làm (tỉnh, xã, phường) hoặc ĐỔI người làm (cho người khác, được
  uỷ quyền, doanh nghiệp) — kể cả mở đầu "không phải" — là tra_loi với "lenh": "change_place"; KHÔNG phải tu_choi, KHÔNG
  phải nút "Chọn thủ tục khác". "Không" / "không phải" / "sai rồi" MỘT MÌNH (không nêu nơi, người hay thủ tục khác) →
  tu_choi cao.
- Bước đồng ý xử lý dữ liệu (consent): "đồng ý", "đồng ý tất cả", "đồng ý hết", "chọn tất cả" đều là đồng ý (xac_nhan hoặc
  nút đồng ý). Hỏi "đồng ý để làm gì" là hoi_nguoc.
- Đang điền / đang đọc giấy (filling, owner_filling): câu giục ("nhanh lên", "sang bước đi") là di_tiep.
- Đã nộp xong, trợ lý đang hỏi đăng xuất hay nộp thêm (done): "thoát ra", "đăng xuất", "kết thúc", "về thôi" là chọn nút
  Đăng xuất (tra_loi) — KHÔNG phải huy (không còn hồ sơ để bỏ). "Xong rồi" / "ok" không nói rõ chọn gì → xac_nhan
  (trợ lý sẽ hỏi lại hai lựa chọn).
- Trợ lý vừa hỏi lại cho chắc trước việc không rút lại được ("chắc chắn nộp chứ?", "điền lại cả tờ khai nhé?"): "có",
  "nộp đi", "chắc chắn" → xac_nhan; "không", "khoan", "để xem lại" → tu_choi (không phải lam_lai / tra_loi).
</theo_buoc>

<tap_am_va_do_chac>
- "viec": với tra_loi / di_tiep / lam_lai / huy / quay_lai, chép lại NGUYÊN CHỮ trong câu nói lên việc muốn làm ("xem
  trước tờ khai", "sang bước tiếp", "điền lại", "thôi không làm nữa"). Không chỉ ra được chữ nào như thế → câu KHÔNG
  phải nhãn hành động (thường là vo_nghia / xac_nhan / tu_choi / khong_biet). Nhãn khác để "viec" rỗng.
- "nhieu": true khi câu lẫn lời nói với người khác, từ đệm / lặp chữ chiếm phần lớn, hoặc chữ vỡ do nhận dạng giọng nói.
- Câu dài lẫn tiếng người khác / từ đệm / lặp chữ: tách PHẦN hướng tới trợ lý làm "y_chinh" (viết lại ngắn, giữ ý) và
  phân loại theo phần đó. Phần nhiễu chiếm phần lớn câu → "do_chac" = "vua" hoặc "thap".
- "do_chac": "cao" khi câu rõ, một ý, khớp rõ nhãn; "vua" khi phải suy đoán hoặc câu nhiều ý; "thap" khi gần như không chắc.
  Hệ thống CHỈ làm khi "cao"; "vua" → hỏi lại công dân. Nghi ngờ thì hạ độ chắc, đừng đoán cho tròn câu.
- Lời đáp ngắn quen dùng ("ừ", "vâng", "ok", "đúng rồi", "được", "không", "chưa", "khoan") là xac_nhan / tu_choi với
  do_chac cao. Tiếng ngập ngừng ("ừm", "hừm", "ờ", "à", "ừ hừ") KHÔNG phải "ừ" → vo_nghia. Một tiếng lẻ KHÔNG phải lời
  đáp quen dùng ("đồng", "xem", "giấy", "để") → vo_nghia.
- Câu có "chưa" / "không" / "khoan" là PHỦ ĐỊNH — không coi là đã xong / đồng ý.
- Câu nhiều ý: ưu tiên huy > thu_tuc > lam_lai > quay_lai > hoi_nguoc > tra_loi > di_tiep > tu_choi > xac_nhan > khong_biet
  > ngoai_luong. Ví dụ "ừ nhưng mà thôi làm cái khác" → huy; "đúng rồi, mà cần giấy gì nữa?" → hoi_nguoc; "điền lại đi…
  mà thôi khoan để tôi xem đã" → tu_choi (ý sau cùng rút lại ý trước).
- TUYỆT ĐỐI không gán tra_loi / xac_nhan / di_tiep / lam_lai / huy cho tiếng ồn hay câu không thành việc.
- Câu có thể là tiếng Mông (chữ RPA: "pom zoo"/"yog" = đồng ý, "tsis yog" = không) — hiểu nghĩa rồi phân loại như tiếng Việt.
</tap_am_va_do_chac>

<vi_du_nhieu>
Câu nhiễu / bỏ lửng hay gặp qua micro ở quầy (bước nào cũng vậy):
- "à giờ thì" → {{"cach_noi": "vo_nghia", "do_chac": "cao", "viec": "", "nhieu": false}}
- "ờ thế là" → vo_nghia · "rồi cái đó là" → vo_nghia · "ừ thì cái này nó" → vo_nghia
- Cụm lặp liền nhau không có việc (ASR bắt tiếng ồn): "tiếp tiếp cái cái" → vo_nghia · "để tôi để tôi" → vo_nghia
- "đồng" → vo_nghia (một tiếng lẻ, không phải lời đáp quen dùng) · "ừm" → vo_nghia (ngập ngừng) · "ừ" → xac_nhan cao
  · "không" → tu_choi cao · "không phải" → tu_choi cao
- "giờ thì sang bước tiếp theo đi" → {{"cach_noi": "di_tiep", "do_chac": "cao", "viec": "sang bước tiếp theo", "nhieu": false}}
- "con ơi đừng nghịch, ngồi im mẹ làm cái này đã" → {{"cach_noi": "ngoai_luong", "do_chac": "cao", "nhieu": true}}
- "alo ừ tao đang ở xã, tí về" → ngoai_luong, nhieu true · "chị ơi quầy số ba ở đâu ạ" → ngoai_luong
- "ờ ờ anh cứ để đấy em ra ngay, à mà xem trước tờ khai đi" → {{"cach_noi": "tra_loi", "do_chac": "vua", "viec": "xem
  trước tờ khai", "nhieu": true, "nut": <số nút Xem trước nếu có>}}
- "ờ thì xem… à mà thôi" → {{"cach_noi": "tu_choi", "do_chac": "vua", "viec": "", "nhieu": true}} (ý sau rút lại ý trước)
- "được rồi đó ok" → xac_nhan cao · "thôi không làm nữa" → {{"cach_noi": "huy", "do_chac": "cao", "viec": "thôi không làm nữa"}}
</vi_du_nhieu>

<dau_ra>
Chỉ trả JSON, không giải thích. "y_chinh" chỉ điền khi câu có tạp âm cần lọc hoặc là hoi_nguoc; còn lại để rỗng.
{{"cach_noi": "<nhãn>", "do_chac": "cao|vua|thap", "viec": "", "nhieu": false, "y_chinh": "", "nut": 0, "lenh": "", "cach_gui": ""}}
</dau_ra>

<buoc_hien_tai>
Bước: {state} — {mo_ta_buoc}
Họ cổng: {ho}
Câu trợ lý vừa nói: {cau_tro_ly}
</buoc_hien_tai>

<nut_dang_hien>{nut_dang_hien}
</nut_dang_hien>

<lenh_cua_buoc>{lenh_cua_buoc}
</lenh_cua_buoc>"""


def nut_block(buttons: list[dict]) -> str:
    if not buttons:
        return "\n(không có nút nào — đừng điền \"nut\")"
    lines = []
    for n, b in enumerate(buttons, 1):
        desc = f" — {b['desc']}" if b.get("desc") else ""
        lines.append(f"\n[{n}] {b.get('label') or ''}{desc}")
    return "".join(lines)


def lenh_block(entries: list[dict]) -> str:
    if not entries:
        return "\n(bước này không có lệnh riêng — đừng điền \"lenh\")"
    return "".join(f'\n- "{e["value"]}": công dân {e["desc"]}' for e in entries)


def parse(raw: str, buttons_n: int, lenh_values: set[str]) -> KetQua | None:
    m = re.search(r"\{[\s\S]*\}", raw or "")
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    kind = str(data.get("kind") or "")
    if kind and "cach_noi" not in data:
        # Định dạng cũ: kind/value. Không có độ chắc → coi là cao (hành vi của bộ phân loại trước).
        value = str(data.get("value") or "")
        if kind in lenh_values:
            kind, value = "state_action", kind
        kq = KetQua(_KIND_CU.get(kind, VO_NGHIA), "cao" if kind != "unknown" else "thap", viec=None)
        if kind == "button":
            kq.nut = _int(value)
        elif kind == "state_action":
            kq.lenh = value if value in lenh_values else ""
        elif kind == "ask_question":
            kq.y_chinh = value
        elif kind == "pick_doc_method":
            kq.cach_gui = value if value in ("qr", "scan") else ""
        return kq
    cach_noi = str(data.get("cach_noi") or "").strip().lower()
    if cach_noi not in CACH_NOI:
        # Model ghi thẳng tên lệnh vào cach_noi.
        if cach_noi in lenh_values:
            return KetQua(TRA_LOI, _do_chac(data), str(data.get("y_chinh") or ""), lenh=cach_noi)
        return None
    kq = KetQua(cach_noi, _do_chac(data), str(data.get("y_chinh") or "")[:200])
    nut = _int(data.get("nut"))
    kq.nut = nut if 1 <= nut <= buttons_n else 0
    lenh = str(data.get("lenh") or "").strip()
    kq.lenh = lenh if lenh in lenh_values else ""
    gui = str(data.get("cach_gui") or "").strip().lower()
    kq.cach_gui = gui if gui in ("qr", "scan") else ""
    kq.viec = str(data.get("viec") or "")[:120]
    kq.nhieu = data.get("nhieu") is True or str(data.get("nhieu") or "").strip().lower() == "true"
    return kq


def _do_chac(data: dict) -> str:
    value = str(data.get("do_chac") or "cao").strip().lower()
    return value if value in DO_CHAC else "vua"


def _int(value) -> int:
    try:
        return int(str(value).strip().strip("[]"))
    except (TypeError, ValueError):
        return 0


async def run(text: str, state: str, conv: dict, *, ho: str, buttons: list[dict], entries: list[dict],
              history: list[dict], cau_tro_ly: str) -> KetQua | None:
    """Một lượt LLM; None khi LLM lỗi / không parse được (bên gọi coi là không hiểu)."""
    from app.channels.handfree.chat import intents  # llm_chat tra qua intents để test cũ patch một chỗ
    from app.channels.handfree.chat.cach_noi.ho_luong import mo_ta_buoc

    system = SYSTEM.format(state=state, mo_ta_buoc=mo_ta_buoc(state, conv), ho=ho,
                           cau_tro_ly=(cau_tro_ly or "(chưa có)")[:300],
                           nut_dang_hien=nut_block(buttons), lenh_cua_buoc=lenh_block(entries))
    try:
        raw = await intents.llm_chat(
            [{"role": "system", "content": system}, *history, {"role": "user", "content": text[:500]}],
            temperature=0.0, max_tokens=160, purpose="cach_noi.lop1",
        )
    except Exception as e:  # noqa: BLE001 — LLM là best-effort
        logger.warning("[cach_noi] lớp 1 lỗi: %s", e)
        return None
    return parse(raw, len(buttons), {e["value"] for e in entries})
