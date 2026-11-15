"""Điền đợt 2 trên kênh handfree: chỉ bản extension khai supportsSecondPass mới chạy lớp soát và nhận khoá secondPass."""
from app.channels.handfree.chat import flow, pipeline_runner, router, store
from app.config import settings

KEY = "xac-nhan-tinh-trang-hon-nhan"


def test_co_supports_second_pass_phai_la_true_that():
    assert router._clean_client_capabilities({"supportsSecondPass": True})["supportsSecondPass"] is True
    assert router._clean_client_capabilities({"supportsSecondPass": "true"})["supportsSecondPass"] is False
    assert router._clean_client_capabilities({})["supportsSecondPass"] is False


def _conv(**extra) -> dict:
    conv = store.new_conversation()
    conv.update({"procedure_key": KEY, "state": "filling", "client_capabilities": {},
                 "auth_user": {"id": "u1"}, "fields": [{"name": "a", "value": "1"}], "trace_request_id": "req_1"})
    conv.update(extra)
    return conv


def test_lenh_dien_chi_kem_second_pass_khi_luot_soat_da_chay():
    assert "secondPass" not in flow._fill_fields_reply(_conv()).actions[0]
    assert flow._fill_fields_reply(_conv(second_pass=True)).actions[0]["secondPass"] == {"requestId": "req_1"}
    # Lượt lưu vết hỏng thì không có mã để hỏi kết quả.
    assert "secondPass" not in flow._fill_fields_reply(_conv(second_pass=True, trace_request_id=None)).actions[0]


async def _run(monkeypatch, caps: dict) -> tuple[dict, dict, list]:
    conversation = {"_id": "c1", "form_context": {}, "client_capabilities": caps, "auth_user": {"id": "u1"}}
    seen: dict = {}
    started: list = []

    async def get_session(_sid):
        return {"_id": "HS-1", "files": [{"fid": "f1", "name": "to-khai.pdf", "type": "application/pdf"}]}

    async def get_conversation(_conv_id):
        return conversation

    async def pipeline(_files_by_role, options):
        seen.update(options)
        result = {"fields": [{"name": "a", "value": "1"}], "stats": {}, "errors": []}
        if options.get("_secondPass"):
            result["_second_pass"] = "lượt soát"
        return result

    async def record_process(_conv, _key, _proc, _files, result, *_args, **_kwargs):
        assert "_second_pass" not in result  # không lọt vào lưu vết
        return "req_hf"

    async def start(request_id, user_id, run, base_fields):
        started.append((request_id, user_id, run, base_fields))
        return True

    async def noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(settings, "second_pass_enabled", True)
    monkeypatch.setattr(settings, "second_pass_usernames", "")
    monkeypatch.setattr(pipeline_runner.up_store, "get", get_session)
    monkeypatch.setattr(pipeline_runner.up_store, "file_to_data_url", lambda _sid, _file: "data:application/pdf;base64,AAA")
    monkeypatch.setattr(pipeline_runner.conv_store, "get", get_conversation)
    monkeypatch.setattr(pipeline_runner.conv_store, "save", noop)
    monkeypatch.setattr(pipeline_runner, "get_procedure", lambda _key: {"review": False})
    monkeypatch.setattr(pipeline_runner, "get_pipeline", lambda _key: pipeline)
    monkeypatch.setattr(pipeline_runner.tracing, "record_process", record_process)
    monkeypatch.setattr(pipeline_runner, "broadcast", noop)
    monkeypatch.setattr(pipeline_runner.second_pass, "start", start)
    await pipeline_runner.run_process("c1", "HS-1", KEY)
    return conversation, seen, started


async def test_extension_khai_co_thi_luot_soat_chay_nen_theo_ma_luot_dien(monkeypatch):
    conversation, seen, started = await _run(monkeypatch, {"supportsSecondPass": True})
    assert seen["_secondPass"] is True
    assert started == [("req_hf", "u1", "lượt soát", [{"name": "a", "value": "1"}])]
    assert conversation["second_pass"] is True


async def test_extension_cu_khong_khai_thi_luong_y_nhu_cu(monkeypatch):
    conversation, seen, started = await _run(monkeypatch, {})
    assert seen["_secondPass"] is False
    assert started == []
    assert conversation["second_pass"] is False
