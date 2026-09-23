"""Máy đọc không được nghỉ giữa cụm từ.

Lỗi thật (quầy Phường Kiến Hưng, 22/09): câu "Giấy tờ cần chứng thực bản sao không giới hạn
số lượng" bị đọc thành "Giấy tờ cần chứng thực bản" — nghỉ một nhịp — "sao không giới hạn số
lượng". Ngắt ngay giữa cụm "bản sao".

Nguyên nhân KHÔNG ở câu chữ: chuỗi TTS không có dấu gạch, dấu chấm hay xuống dòng nào ở đó.
Nó ở `generator_config.chunk_length_schedule` gửi cho máy đọc — chốt cứng [20] từ lần port đầu.
Máy gom đủ 20 KÝ TỰ là tổng hợp một khúc audio; mỗi khúc là một lần tổng hợp riêng nên biên
khúc nghe thành nhịp nghỉ, và biên rơi vào đâu thì phụ thuộc đếm ký tự, không theo cụm từ.
"""
import json

import pytest

from app.channels.handfree.voice.ws_tts import _config_frame
from app.config import settings


def _schedule(frame: str) -> list[int]:
    return json.loads(frame)["generator_config"]["chunk_length_schedule"]


def test_khuc_dau_du_dai_de_khong_cat_giua_cum_tu():
    """Cụm từ hành chính tiếng Việt thường 20–40 ký tự ("Giấy tờ cần chứng thực bản sao" là 30).
    Khúc 20 ký tự thì gần như chắc chắn cắt giữa cụm."""
    lengths = _schedule(_config_frame("vi", "phuongnhi-north"))
    assert lengths, "thiếu lịch gom ký tự → máy đọc tự quyết, mất kiểm soát nhịp nghỉ"
    # 250 = p90 của 133 câu trong script_vi + dư — 98% câu gọn trong MỘT khúc, không còn biên
    # nào để rơi vào giữa cụm từ. Hạ xuống dưới p90 là lại có câu bị cắt.
    assert lengths[0] >= 175, f"khúc đầu {lengths[0]} ký tự còn cắt giữa câu ở phần lớn lời thoại"


def test_khuc_sau_khong_ngan_hon_khuc_dau():
    """Lịch phải không giảm. Khúc sau ngắn hơn khúc đầu là càng đọc càng vụn."""
    lengths = _schedule(_config_frame("vi", "phuongnhi-north"))
    assert lengths[-1] > lengths[0]
    assert lengths == sorted(lengths), f"lịch phải tăng dần, đang là {lengths}"


def test_tieng_mong_dung_cung_lich():
    """Tiếng Mông có thể ở server khác nhưng nhịp đọc là cùng một vấn đề."""
    assert _schedule(_config_frame("hmong", "vuado")) == _schedule(_config_frame("vi", "x"))


@pytest.mark.parametrize("value, expected", [
    ("250,290", [250, 290]),
    (" 100 , 200 ", [100, 200]),
    ("", [250, 290]),                   # rỗng → mặc định
    ("abc", [250, 290]),                # rác → mặc định
    ("0,-5", [250, 290]),               # số vô nghĩa → mặc định
    ("100,abc,200", [100, 200]),        # bỏ phần rác, giữ phần dùng được
])
def test_cau_hinh_sai_khong_lam_cau_m_im(monkeypatch, value, expected):
    """Env sai không được để lượt đọc câm hay ném lỗi giữa phiên — rơi về mặc định an toàn."""
    monkeypatch.setattr(settings, "tts_chunk_length_schedule", value)
    assert settings.tts_chunk_lengths == expected


def test_khong_con_chot_cung_trong_ws_tts():
    """Giá trị phải đọc từ settings để sửa được bằng env, không phải sửa code + phát hành lại."""
    import pathlib

    from app.channels.handfree.voice import ws_tts

    src = pathlib.Path(ws_tts.__file__).read_text(encoding="utf-8")
    assert "settings.tts_chunk_lengths" in src
    assert "[20]" not in src, "còn chốt cứng lịch gom ký tự"
