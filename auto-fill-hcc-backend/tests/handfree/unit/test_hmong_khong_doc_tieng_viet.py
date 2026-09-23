"""Giọng Mông KHÔNG được đọc chữ Việt.

Lỗi thật tại quầy Lai Châu: câu hướng dẫn Scan kết thúc bằng một vế tiếng Việt —
"Xong hết, công dân bấm Đã đưa đủ giấy tờ ở dưới để em bắt đầu xử lý ạ." — nối vào cuối lời
đọc tiếng Mông. Máy đọc chữ Việt bằng giọng Mông, công dân nghe không ra tiếng gì.

Nguyên nhân KHÔNG phải bản dịch sai, mà là CÁCH NỐI: `r.tts_text += _fmt(vi.X)[1]`. Ở chế độ
Mông, _fmt trả về lời đọc TIẾNG MÔNG cho template chính, nhưng câu phụ chưa có bản dịch nên
trả về tiếng Việt — cộng vào là xong.

File này chặn CẢ LOẠI lỗi: cấm nối tay, và chốt hành vi của note= trong _fmt.
"""
import ast
import pathlib
import re

import pytest

from app.channels.handfree.chat import flow
from app.channels.handfree.chat import script_mong as mong
from app.channels.handfree.chat import script_vi as vi

_FLOW_SRC = pathlib.Path(flow.__file__).read_text(encoding="utf-8")


def test_cam_noi_tay_vao_loi_doc():
    """Mọi câu phụ phải đi qua note= của _fmt. Nối tay là tái hiện đúng lỗi trên."""
    code = re.sub(r"#.*", "", _FLOW_SRC)  # bỏ chú thích: chúng có nhắc lại cú pháp bị cấm
    code = re.sub(r'"""[\s\S]*?"""', "", code)
    assert "tts_text +=" not in code, "nối tay vào lời đọc → giọng Mông đọc chữ Việt"
    assert "display_md +=" not in code, "nối tay vào markdown → lẫn khối Việt–Mông–Việt–Mông"


def test_khong_dung_chuoi_tieng_viet_tran_trong_Reply():
    """LỖI THẬT tại quầy Lai Châu (ảnh chụp 17/09): bật tiếng Mông, hỏi "làm kết hôn cần gì"
    → bot đáp thuần tiếng Việt, không có khối Mông, đọc bằng giọng Việt.

    Nguyên nhân KHÔNG phải thiếu bản dịch mà là câu được dựng thẳng bằng f-string trong
    flow.py, không đi qua _fmt nên chẳng bao giờ tra tới script_mong. Test chặn CẢ LOẠI:
    chữ hiển thị phải nằm ở script_vi (có twin ở script_mong), flow.py chỉ ghép biến.
    """
    tree = ast.parse(_FLOW_SRC)
    offenders = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "Reply"):
            continue
        for arg in node.args:
            if not isinstance(arg, (ast.Constant, ast.JoinedStr)):
                continue
            text = ast.get_source_segment(_FLOW_SRC, arg) or ""
            # Dấu tiếng Việt là bằng chứng đây là chữ hiển thị chứ không phải chuỗi rỗng
            # hay khoá kỹ thuật.
            if re.search(r"[ăâêôơưđĂÂÊÔƠƯĐáàảãạéèẻẽẹíìỉĩịóòỏõọúùủũụýỳỷỹỵ]", text):
                offenders.append((node.lineno, text.replace("\n", " ")[:70]))
    assert not offenders, (
        "Reply() dựng bằng chuỗi tiếng Việt trần → không có bản Mông:\n"
        + "\n".join(f"  flow.py:{ln} {t}" for ln, t in offenders)
    )


# Miễn trừ CÓ LÝ DO, không phải "chưa dịch xong":
#   PROFILE_* — lựa chọn "Lấy dữ liệu đã lưu" đang bị gỡ khỏi _doc_options_card, không nhánh
#     nào tới được. Dịch bây giờ là dịch cho tính năng chưa bật.
#   LANG_OFF  — câu xác nhận CHUYỂN VỀ tiếng Việt; lượt đó _TURN_LANG đã là "vi" nên _fmt
#     không tra twin. Có bản Mông ở đây mới là sai.
# Bật lại PROFILE_* thì bỏ khỏi đây, test sẽ đòi bản dịch.
_NOT_REACHABLE_IN_HMONG = {
    "PROFILE_APPLIED", "PROFILE_ASK_PHONE", "PROFILE_NEED_PHONE", "PROFILE_NOT_FOUND",
    "PROFILE_SAVED", "LANG_OFF",
}


def test_moi_template_duoc_fmt_dung_deu_co_twin_mong():
    """Hàng rào thứ hai: đi qua _fmt nhưng thiếu twin thì _fmt trả nguyên tiếng Việt.

    Chỉ soi những template flow.py THỰC SỰ gọi — script_vi còn template của nhánh chưa bật
    (hộ kinh doanh, profile, đánh giá), ép dịch hết là ép dịch cả phần chưa dùng.
    """
    code = re.sub(r"#.*", "", _FLOW_SRC)  # chú thích có nhắc "_fmt(vi.X)" làm ví dụ
    used = set(re.findall(r"_fmt\(\s*vi\.([A-Z_][A-Z0-9_]*)", code))
    assert used, "không parse được lời gọi _fmt nào — regex hỏng"
    missing = sorted(n for n in used - _NOT_REACHABLE_IN_HMONG
                     if not isinstance(getattr(mong, n, None), dict))
    assert not missing, "template đang dùng nhưng chưa có bản Mông: " + ", ".join(missing)



# Placeholder có nội dung là chữ tiếng Việt lấy từ registry / từ cổng. Nhét vào bản Mông là
# giọng Mông đọc nguyên một danh sách tiếng Việt — đúng cái lỗi file này sinh ra để chặn.
_VIET_PLACEHOLDERS = {"documents_md", "documents_tts", "options_md", "options_tts", "error",
                      "procedures", "missing_note", "doc_list_tts", "intro_md", "intro_tts",
                      # guidedSteps: nhãn bước + nguyên văn lời cổng báo đều là chữ Việt lấy
                      # từ registry/DOM. Bản Mông nhắc tên bước thì viết thẳng tiếng Việt
                      # trong câu (như các câu Mông khác), không nhúng qua placeholder.
                      "missing_tts", "attachment_step", "result_step", "submit_label",
                      "portal_message"}


def test_ban_mong_khong_nhung_placeholder_chua_chu_viet():
    offenders = []
    for name in dir(mong):
        tpl = getattr(mong, name)
        if not (name.isupper() and isinstance(tpl, dict) and "tts" in tpl):
            continue
        for field in ("md", "tts"):
            for ph in re.findall(r"\{(\w+)\}", str(tpl.get(field, ""))):
                if ph in _VIET_PLACEHOLDERS:
                    offenders.append(f"{name}.{field} chèn {{{ph}}}")
    assert not offenders, "bản Mông nhúng chữ tiếng Việt:\n  " + "\n  ".join(offenders)


@pytest.fixture()
def hmong_turn():
    token = flow._TURN_LANG.set("hmong")
    yield
    flow._TURN_LANG.reset(token)


# MỌI câu phụ đang được nối phải có bản Mông. Thiếu một cái là công dân Mông mất hẳn thông
# tin đó (sau bản vá, câu Việt không còn bị đọc bằng giọng Mông nữa — nó chỉ im lặng).
_NOTES = ["SCAN_AUTO_RUN_NOTE", "ATTACH_MODE_PRESET_SPLIT", "WAIT_ATTACHMENT_SAME_PAGE",
          "WAIT_ATTACHMENT_PAGE", "SAME_PAGE_TWO_STEP_SUMMARY", "REVIEW_ATTACHMENT_ACTION"]


@pytest.mark.parametrize("name", _NOTES)
def test_moi_cau_phu_deu_co_ban_mong(name):
    twin = getattr(mong, name, None)
    assert isinstance(twin, dict) and twin.get("tts"), f"{name} chưa có bản Mông"


@pytest.mark.parametrize("name", _NOTES)
def test_ban_mong_khong_lan_tieng_viet(name):
    """Dấu hiệu lẫn: những từ chỉ có trong tiếng Việt. Tên riêng của cổng (Thành phần hồ sơ,
    Nộp hồ sơ, Cài đặt) được giữ nguyên có chủ ý — cán bộ phải dò đúng chữ trên màn hình."""
    tts = getattr(mong, name)["tts"].lower()
    for viet_only in ("công dân", "giấy tờ", "hồ sơ của", "em sẽ", "ở dưới", "chờ em"):
        assert viet_only not in tts, f"{name} còn lẫn tiếng Việt: {viet_only}"


def test_cau_phu_chua_co_ban_mong_thi_KHONG_vao_loi_doc(hmong_turn, monkeypatch):
    """Cơ chế đỡ: câu phụ thiếu bản dịch vẫn hiện ở khối Việt nhưng TUYỆT ĐỐI không đọc.
    Thà nói ít hơn là nói thứ công dân không nghe ra."""
    monkeypatch.delattr(mong, "SCAN_AUTO_RUN_NOTE")
    md, tts = flow._fmt(vi.SCAN_PICK, note=vi.SCAN_AUTO_RUN_NOTE)
    assert "Đã đưa đủ giấy tờ" in md, "vẫn phải hiện để cán bộ đọc được trên màn hình"
    assert "Đã đưa đủ giấy tờ" not in tts
    assert "công dân" not in tts, f"lời đọc Mông còn lẫn tiếng Việt: {tts}"


def test_khoi_mong_nam_o_CUOI_khong_bi_chen_giua(hmong_turn):
    """Bố cục song ngữ: toàn bộ tiếng Việt trước, khối Mông in nghiêng ở cuối. Nối tay khiến
    thứ tự thành Việt–Mông–Việt–Mông, đúng cái cán bộ nhìn thấy."""
    md, _tts = flow._fmt(vi.SCAN_PICK, note=vi.SCAN_AUTO_RUN_NOTE)
    # Khối Mông là đoạn in nghiêng CUỐI CÙNG, nối bằng "\n\n*". Không dò dấu * đầu tiên:
    # phần tiếng Việt vốn đã có **in đậm**.
    viet, _sep, hmong = md.rpartition("\n\n*")
    assert hmong, "thiếu khối Mông"
    assert "Đã đưa đủ giấy tờ" in viet, "câu Việt phải nằm TRƯỚC khối Mông"
    assert mong.SCAN_PICK["md"][:30] in hmong, "khối cuối phải là tiếng Mông"


def test_cau_phu_CO_ban_mong_thi_duoc_doc(hmong_turn):
    """WAIT_ATTACHMENT_PAGE đã có bản dịch → phải vào cả markdown lẫn lời đọc, bằng tiếng Mông."""
    assert isinstance(getattr(mong, "WAIT_ATTACHMENT_PAGE", None), dict)
    _md, tts = flow._fmt(vi.FILL_REPORT_REVIEW, filled=3, missing_note="",
                         note=vi.WAIT_ATTACHMENT_PAGE)
    assert mong.WAIT_ATTACHMENT_PAGE["tts"] in tts


def test_tieng_viet_khong_bi_anh_huong():
    """Lượt tiếng Việt: note nối thẳng như cũ, không thêm khối nào."""
    md, tts = flow._fmt(vi.SCAN_PICK, note=vi.SCAN_AUTO_RUN_NOTE)
    # Bằng ĐÚNG hai chuỗi Việt nối nhau đã chứng minh không có khối Mông nào chen vào.
    assert md == vi.SCAN_PICK["md"] + vi.SCAN_AUTO_RUN_NOTE["md"]
    assert tts == vi.SCAN_PICK["tts"] + vi.SCAN_AUTO_RUN_NOTE["tts"]
