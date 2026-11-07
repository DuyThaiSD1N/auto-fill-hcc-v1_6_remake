from replay import replay_options, strip_response


def test_bo_khoa_gan_voi_ho_so_that():
    options = replay_options({
        "dossierId": "d", "sessionId": "s", "conversation_id": "c", "upload_session_id": "u", "consent_id": "k", "channel": "handfree",
        "formContext": {"applicantFullname": "x"}, "submitterMode": "self", "extVersion": "1.0",
    }, "reproduce:1")
    assert options == {"formContext": {"applicantFullname": "x"}, "submitterMode": "self", "extVersion": "1.0", "labRun": "reproduce:1"}


def test_options_rong():
    assert replay_options(None, "t") == {"labRun": "t"}


def test_strip_response():
    assert strip_response({"n": 1, "response": {"fields": []}}) == {"n": 1}
