from scripts.repair_attach_trace_files import rebuild_attachments


def test_rebuild_attachments_restores_original_file_name_and_order():
    trace = {
        "request_id": "req_attach",
        "procedure": "trich-luc-ks",
        "kind": "attach",
        "split": False,
        "attachments": [{"name": "Căn cước công dân.pdf"}],
        "llm_output": {
            "attachments": [{
                "fileIndex": 0,
                "fileName": "Căn cước công dân.pdf",
                "componentName": "Giấy tờ tùy thân",
            }]
        },
    }
    request = {
        "files": [{
            "name": "cancuoc_minh_0001.pdf",
            "type": "application/pdf",
            "role": "doc",
            "sha256": "a" * 64,
        }]
    }

    assert rebuild_attachments(trace, request) == [{
        "name": "cancuoc_minh_0001.pdf",
        "role": "Giấy tờ tùy thân",
        "sha256": "a" * 64,
        "uses": 1,
    }]
