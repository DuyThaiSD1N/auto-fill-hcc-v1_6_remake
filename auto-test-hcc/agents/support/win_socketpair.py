"""Plugin pytest cho Windows, theo ghi chú bước 2 trong CLAUDE.md.

tests/conftest.py của backend chặn mọi socket.connect trừ AF_UNIX, mà Windows không có AF_UNIX còn
asyncio lại tạo socketpair qua 127.0.0.1. Plugin này chỉ nới cho socketpair, kết nối mạng thật vẫn bị chặn.
"""
import socket

_connect_goc = socket.socket.connect
if not hasattr(socket, "AF_UNIX"):
    socket.AF_UNIX = -1  # conftest vẫn chặn kết nối mạng thật
_pair_goc = socket.socketpair


def _pair(*a, **k):
    cur = socket.socket.connect
    socket.socket.connect = _connect_goc
    try:
        return _pair_goc(*a, **k)
    finally:
        socket.socket.connect = cur


socket.socketpair = _pair
