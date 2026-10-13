"""Lỗi ASR gửi về sidebar không được chứa chi tiết nội bộ (địa chỉ dịch vụ, thông điệp gRPC).

Ca thật: sidebar hiện "⚠️ Lỗi giọng nói: errors resolving http://<ip>:<port> …" vì BE gửi nguyên
`e.details()` của gRPC. Đồng thời lỗi đó do cấu hình ghi kèm http:// mà gRPC chỉ nhận host:port.
"""
import ast
from pathlib import Path

from app.channels.handfree.voice import ws_asr

SRC = Path(ws_asr.__file__).read_text(encoding="utf-8")


def test_grpc_target_bo_scheme():
    assert ws_asr._grpc_target("http://10.0.0.5:10089") == "10.0.0.5:10089"
    assert ws_asr._grpc_target("https://asr.local:443/") == "asr.local:443"
    assert ws_asr._grpc_target("grpc://asr:9113") == "asr:9113"
    assert ws_asr._grpc_target(" 10.0.0.5:10089 ") == "10.0.0.5:10089"


def test_moi_loi_gui_ve_client_la_cau_co_dinh():
    tree = ast.parse(SRC)
    messages = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
            if "type" in keys and "message" in keys:
                messages.append(node.values[keys.index("message")])
    assert messages, "không tìm thấy lỗi gửi client"
    for value in messages:
        assert isinstance(value, ast.Name) and value.id == "_CLIENT_ERROR", ast.unparse(value)
    assert "details()" not in ws_asr._CLIENT_ERROR and "http" not in ws_asr._CLIENT_ERROR


def test_ket_noi_dung_dia_chi_da_boc_scheme():
    assert "grpc_uri = _grpc_target(" in SRC
