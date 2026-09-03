from app.traces.metadata import build_attach_trace_attachments


def test_trace_keeps_original_names_and_upload_order():
    files = [
        {"name": "mat-truoc.jpg", "role": ""},
        {"name": "mat-sau.jpg", "role": ""},
        {"name": "khong-phan-loai.pdf", "role": ""},
    ]
    plan = [{
        "fileIndex": 0,
        "fileName": "Căn cước công dân.pdf",
        "componentName": "Giấy tờ tùy thân",
        "sourceFileIndexes": [0, 1],
    }]

    assert build_attach_trace_attachments(plan, files) == [
        {"name": "mat-truoc.jpg", "role": "Giấy tờ tùy thân"},
        {"name": "mat-sau.jpg", "role": "Giấy tờ tùy thân"},
        {"name": "khong-phan-loai.pdf", "role": ""},
    ]


def test_trace_maps_split_segments_back_to_source_file():
    files = [{"name": "ho-so-gop.pdf", "role": ""}]
    plan = [
        {
            "fileName": "CCCD.pdf",
            "documentName": "Căn cước công dân",
            "sourceSegments": [{"fileIndex": 0, "pageIndexes": [0]}],
        },
        {
            "fileName": "Giấy khai sinh.pdf",
            "documentName": "Giấy khai sinh",
            "sourceSegments": [{"fileIndex": 0, "pageIndexes": [1]}],
        },
    ]

    assert build_attach_trace_attachments(plan, files) == [{
        "name": "ho-so-gop.pdf",
        "role": "Căn cước công dân · Giấy khai sinh",
    }]
