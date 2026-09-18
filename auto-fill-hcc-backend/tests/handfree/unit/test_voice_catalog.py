"""Danh mục giọng đọc TTS: máy quầy tự chọn, client không được bơm giọng tuỳ ý.

Trước đây giọng chốt cứng ở env cho MỌI phường. Giờ danh mục khai ở catalog.py, lựa chọn nằm
ở màn Cài đặt và gửi kèm ?voice= mỗi lần mở /ws/tts.
"""
import pytest

from app.channels.handfree.voice import catalog


@pytest.fixture()
def voices(monkeypatch):
    """Đặt lại env về trạng thái đang triển khai: tiếng Việt chưa có giọng nam."""
    monkeypatch.setattr(catalog.settings, "tts_voice", "phuongnhi-north")
    monkeypatch.setattr(catalog.settings, "tts_voice_vi_male", "")
    monkeypatch.setattr(catalog.settings, "tts_voice_hmong", "vuado")
    return catalog


def test_tieng_mong_co_hai_giong(voices):
    assert voices.voices_for("hmong") == [
        {"id": "xi", "label": "Cô Xi", "gender": "nu"},
        {"id": "vuado", "label": "Anh Dơ", "gender": "nam"},
    ]


def test_giong_chua_co_id_thi_khong_hien(voices):
    """Giọng nam tiếng Việt chưa có id → danh sách chỉ còn một giọng → FE tự ẩn ô chọn.
    Trả về entry id rỗng là màn Cài đặt hiện một lựa chọn bấm vào không kêu."""
    assert voices.voices_for("vi") == [
        {"id": "phuongnhi-north", "label": "Cô Phương Nhi", "gender": "nu"},
    ]


def test_dien_id_giong_nam_la_tu_hien_khong_phai_sua_code(voices, monkeypatch):
    """Cam kết với người deploy: có id thì chỉ cần điền .env, không phát hành lại extension."""
    monkeypatch.setattr(catalog.settings, "tts_voice_vi_male", "giong-nam-abc")
    ids = [entry["id"] for entry in voices.voices_for("vi")]
    assert ids == ["phuongnhi-north", "giong-nam-abc"]


def test_mac_dinh_tieng_mong_la_anh_do(voices):
    assert voices.default_voice("hmong") == "vuado"
    assert voices.default_voice("vi") == "phuongnhi-north"


def test_id_la_bi_loai_ve_mac_dinh(voices):
    """CHỐT AN NINH: ?voice= đi qua query string của WebSocket, trang web nào cũng gọi được.
    Không lọc là cho phép bơm voiceId tuỳ ý lên server TTS."""
    assert voices.resolve_voice("hmong", "../../etc/passwd") == "vuado"
    assert voices.resolve_voice("hmong", "") == "vuado"
    assert voices.resolve_voice("hmong", None) == "vuado"
    # Giọng của NGÔN NGỮ KHÁC cũng không được mượn.
    assert voices.resolve_voice("vi", "vuado") == "phuongnhi-north"


def test_chon_dung_giong_trong_danh_muc_thi_duoc_giu(voices):
    assert voices.resolve_voice("hmong", "xi") == "xi"
    assert voices.resolve_voice("hmong", "vuado") == "vuado"


def test_ngon_ngu_la_coi_nhu_tieng_viet(voices):
    assert voices.default_voice("klingon") == "phuongnhi-north"
    assert voices.resolve_voice("klingon", "xi") == "phuongnhi-north"
