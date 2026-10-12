"""Fixture dùng chung cho toàn bộ test."""
import errno
import os
import socket

import pytest

from app.config import Settings, settings

# Test chạy theo giá trị mặc định của Settings, không theo .env/biến môi trường của máy:
# mock respx canh URL mặc định — .env đổi LLM_BASE_URL là mock trượt, request thật bay ra
# LLM/OCR/OpenAI và cùng một commit cho kết quả khác nhau giữa các máy. Phải chạy TRƯỚC mọi
# import khác của app (module nào đọc settings lúc import sẽ thấy giá trị đã chuẩn hoá) và
# sửa tại chỗ vì nhiều module giữ tham chiếu `from app.config import settings`.
for _ten in Settings.model_fields:
    os.environ.pop(_ten.upper(), None)
for _ten, _gia_tri in Settings(_env_file=None).model_dump().items():
    setattr(settings, _ten, _gia_tri)


# Chặn mọi kết nối mạng (kể cả localhost: Mongo dev, server phụ): test phải giả lập hết.
# AF_UNIX vẫn cho qua vì event loop asyncio dùng socket nội bộ.
_connect_goc = socket.socket.connect
_connect_ex_goc = socket.socket.connect_ex


def _chan_connect(sock, address):
    if sock.family == socket.AF_UNIX:
        return _connect_goc(sock, address)
    raise ConnectionRefusedError(errno.ECONNREFUSED, f"Test không được mở kết nối mạng: {address!r}")


def _chan_connect_ex(sock, address):
    if sock.family == socket.AF_UNIX:
        return _connect_ex_goc(sock, address)
    return errno.ECONNREFUSED


socket.socket.connect = _chan_connect
socket.socket.connect_ex = _chan_connect_ex

from app.users import tdp_rollup  # noqa: E402


@pytest.fixture(autouse=True)
def _khong_co_to_dan_pho(monkeypatch):
    """Mặc định CHƯA có tổ dân phố nào: app/stats/cutover.py tra bảng tổ dân phố → xã cha ở
    mọi lần đếm; không chặn ở đây là test số liệu gọi Mongo thật. Test cần tổ dân phố tự
    monkeypatch lại `tdp_rollup.load_tdp_parents`."""
    async def _none() -> dict:
        return {}

    monkeypatch.setattr(tdp_rollup, "load_tdp_parents", _none)
