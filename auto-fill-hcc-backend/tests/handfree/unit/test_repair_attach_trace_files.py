from scripts.repair_attach_trace_files import rebuild_attachments


def test_rebuild_attachments_restores_original_file_name():
    trace = {
        "request_id": "req_attach",
        "kind": "attach",
        "attachments": [{"name": "Căn cước công dân.pdf"}],
        "llm_output": {
            "attachments": [{
                "fileIndex": 0,
                "fileName": "Căn cước công dân.pdf",
                "componentName": "Giấy tờ tùy thân",
            }]
        },
    }
    request = {"files": [{"name": "cancuoc_minh_0001.pdf", "role": "doc"}]}

    assert rebuild_attachments(trace, request) == [{
        "name": "cancuoc_minh_0001.pdf",
        "role": "Giấy tờ tùy thân",
    }]
