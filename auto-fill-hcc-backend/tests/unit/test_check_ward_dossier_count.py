from datetime import datetime, timedelta, timezone

from scripts.check_ward_dossier_count import (
    _content_aware_stem_stats,
    _content_stats,
    _dashboard_without_extension_stats,
    _fingerprint_attachments,
    _fold_text,
    _split_ocr_by_attachment,
)


def _file(name: str, digest: str | None) -> dict:
    return {"name": name, "sha256": digest}


def _ocr(file_name: str, body: str, *, file_index: int | None = None) -> str:
    index = f"fileIndex={file_index} · " if file_index is not None else ""
    return f"===== {index}{file_name} (tiengnoi) =====\n{body}"


_CCCD_NGUYEN_VAN_A = """
CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
CĂN CƯỚC CÔNG DÂN
Số 012345678901
Họ và tên NGUYỄN VĂN A
Ngày sinh 01/01/1990
Quê quán Hà Nội
Nơi thường trú 12 phố Huế phường Hai Bà Trưng Hà Nội
Quốc tịch Việt Nam Giới tính Nam
"""

_CCCD_TRAN_VAN_B = """
CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
CĂN CƯỚC CÔNG DÂN
Số 098765432109
Họ và tên TRẦN VĂN B
Ngày sinh 02/02/1991
Quê quán Đà Nẵng
Nơi thường trú 34 đường Lê Lợi phường Hải Châu Đà Nẵng
Quốc tịch Việt Nam Giới tính Nam
"""


def test_ward_name_match_ignores_case_accents_and_extra_spaces():
    assert _fold_text("  PHƯỜNG   BẮC GIANG ") == _fold_text("Phường Bắc Giang")


def test_name_and_content_fingerprint_is_order_independent():
    first, exact_first = _fingerprint_attachments(
        [_file("A.pdf", "a" * 64), _file("B.pdf", "b" * 64)],
        request_id="req-1",
    )
    second, exact_second = _fingerprint_attachments(
        [_file(" b.PDF ", "b" * 64), _file("a.PDF", "a" * 64)],
        request_id="req-2",
    )

    assert first == second
    assert exact_first is exact_second is True


def test_same_file_name_with_different_content_is_two_dossiers():
    traces = [
        {
            "request_id": "req-1",
            "user_id": "ward-1",
            "procedure": "trich-luc-ks",
            "attachments": [_file("image.pdf", "a" * 64)],
        },
        {
            "request_id": "req-2",
            "user_id": "ward-1",
            "procedure": "trich-luc-ks",
            "attachments": [_file("image.pdf", "b" * 64)],
        },
    ]
    result = _content_stats(traces)
    dashboard_stem = _dashboard_without_extension_stats(traces)

    assert result["totalDossiers"] == 2
    assert dashboard_stem["totalDossiers"] == 1
    assert result["exactDossiers"] == 2
    assert result["totalRequests"] == 2


def test_ocr_sections_are_mapped_by_explicit_file_index_when_one_section_is_missing():
    attachments = [
        _file("A.pdf", "a" * 64),
        _file("B.docx", "b" * 64),
        _file("C.pdf", "c" * 64),
    ]
    sections = "\n\n---\n\n".join([
        _ocr("A.pdf", "noi dung file A", file_index=0),
        _ocr("C.pdf", "noi dung file C", file_index=2),
    ])

    assert _split_ocr_by_attachment(attachments, sections) == [
        "noi dung file A",
        "",
        "noi dung file C",
    ]


def test_content_aware_rule_separates_same_generic_name_with_different_content():
    traces = [
        {
            "request_id": "req-a",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "attachments": [_file("CCCD.pdf", "a" * 64)],
            "ocr_text": _ocr("CCCD.pdf", _CCCD_NGUYEN_VAN_A),
        },
        {
            "request_id": "req-b",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "attachments": [_file("CCCD.pdf", "b" * 64)],
            "ocr_text": _ocr("CCCD.pdf", _CCCD_TRAN_VAN_B),
        },
    ]

    assert _dashboard_without_extension_stats(traces)["totalDossiers"] == 1
    assert _content_aware_stem_stats(traces)["totalDossiers"] == 2


def test_content_aware_rule_matches_jpg_to_pdf_by_similar_ocr():
    traces = [
        {
            "request_id": "req-jpg",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "attachments": [_file("CCCD Nguyễn Văn A.jpg", "a" * 64)],
            "ocr_text": _ocr("CCCD Nguyễn Văn A.jpg", _CCCD_NGUYEN_VAN_A),
        },
        {
            "request_id": "req-pdf",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "attachments": [_file("CCCD Nguyễn Văn A.pdf", "b" * 64)],
            "ocr_text": _ocr(
                "CCCD Nguyễn Văn A.pdf",
                _CCCD_NGUYEN_VAN_A.replace("Nơi thường trú", "Nơi cư trú"),
                file_index=0,
            ),
        },
    ]

    assert _content_aware_stem_stats(traces)["totalDossiers"] == 1


def test_content_aware_rule_keeps_one_dossier_when_later_trace_adds_a_file():
    base_files = [
        _file("ĐKKH THU HẰNG.pdf", "a" * 64),
        _file("CHỨNG SINH THU HẰNG.pdf", "b" * 64),
        _file("CCCD THU HẰNG.pdf", "c" * 64),
        _file("CCCD ANH TUẤN.pdf", "d" * 64),
    ]
    base_ocr = "\n\n---\n\n".join(
        _ocr(item["name"], f"Nội dung tài liệu {index} " + _CCCD_NGUYEN_VAN_A)
        for index, item in enumerate(base_files)
    )
    traces = [
        {
            "request_id": "req-first",
            "user_id": "doan-ket",
            "procedure": "khai-sinh-dang-ky",
            "attachments": base_files,
            "ocr_text": base_ocr,
        },
        {
            "request_id": "req-supplement",
            "user_id": "doan-ket",
            "procedure": "khai-sinh-dang-ky",
            "attachments": base_files + [_file("anh_3914.jpg", "e" * 64)],
            "ocr_text": base_ocr + "\n\n---\n\n" + _ocr(
                "anh_3914.jpg", "Ảnh bổ sung thông tin hồ sơ công dân không có văn bản"
            ),
        },
    ]

    assert _content_aware_stem_stats(traces)["totalDossiers"] == 1


def test_content_aware_rule_only_falls_back_to_name_when_content_is_missing():
    missing_content = [
        {
            "request_id": "req-old-a",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "attachments": [_file("Tờ khai.docx", None)],
        },
        {
            "request_id": "req-old-b",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "attachments": [_file("Tờ khai.pdf", None)],
        },
    ]
    conflicting_sha = [
        {
            "request_id": "req-new-a",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "attachments": [_file("Tờ khai.docx", "a" * 64)],
        },
        {
            "request_id": "req-new-b",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "attachments": [_file("Tờ khai.pdf", "b" * 64)],
        },
    ]

    assert _content_aware_stem_stats(missing_content)["totalDossiers"] == 1
    assert _content_aware_stem_stats(conflicting_sha)["totalDossiers"] == 2


def test_autofill_and_attach_with_same_name_and_content_are_one_dossier():
    attachments = [_file("cancuoc_minh_0001.pdf", "a" * 64)]
    result = _content_stats([
        {
            "request_id": "req-fill",
            "user_id": "ward-1",
            "procedure": "trich-luc-ks",
            "attachments": attachments,
        },
        {
            "request_id": "req-attach",
            "user_id": "ward-1",
            "procedure": "trich-luc-ks",
            "attachments": attachments,
        },
    ])

    assert result["totalDossiers"] == 1
    assert result["totalRequests"] == 2


def test_duplicate_file_inside_one_request_does_not_change_fingerprint():
    one, _ = _fingerprint_attachments([_file("A.pdf", "a" * 64)], request_id="req-1")
    two, _ = _fingerprint_attachments(
        [_file("A.pdf", "a" * 64), _file("A.pdf", "a" * 64)],
        request_id="req-2",
    )

    assert one == two


def test_dossier_id_connects_autofill_jpg_to_attachment_pdf():
    result = _content_stats([
        {
            "request_id": "req-fill",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "stats_version": 2,
            "dossier_ids": ["req-fill"],
            "attachments": [_file("cccd.jpg", "a" * 64)],
        },
        {
            "request_id": "req-attach",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "stats_version": 2,
            "dossier_ids": ["req-fill"],
            "attachments": [_file("cccd.pdf", "b" * 64)],
        },
    ])

    assert result["totalDossiers"] == 1


def test_same_source_name_connects_jpg_to_pdf_when_session_id_was_not_saved():
    start = datetime(2026, 8, 25, 6, 40, tzinfo=timezone.utc)
    result = _content_stats([
        {
            "request_id": "req-fill",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "stats_version": 2,
            "dossier_ids": ["req-fill"],
            "attachments": [_file("1787639998400_unique.jpg", "a" * 64)],
            "created_at": start,
        },
        {
            "request_id": "req-attach",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "stats_version": 2,
            "dossier_ids": ["req-attach"],
            "attachments": [_file("1787639998400_unique.pdf", "b" * 64)],
            "created_at": start + timedelta(minutes=5),
        },
    ])

    assert result["totalDossiers"] == 1


def test_dashboard_stem_rule_ignores_extension_and_does_not_use_time_window():
    start = datetime(2026, 8, 25, 1, tzinfo=timezone.utc)
    base = {
        "user_id": "ward-1",
        "procedure": "khai-tu",
    }
    result = _dashboard_without_extension_stats([
        {
            **base,
            "request_id": "req-jpg",
            "attachments": [_file("ho-so-cong-dan.jpg", "a" * 64)],
            "created_at": start,
        },
        {
            **base,
            "request_id": "req-pdf",
            "attachments": [_file("ho-so-cong-dan.pdf", "b" * 64)],
            "created_at": start + timedelta(minutes=10),
        },
        {
            **base,
            "request_id": "req-later",
            "attachments": [_file("ho-so-cong-dan.png", "c" * 64)],
            "created_at": start + timedelta(hours=2),
        },
    ])

    assert result["totalDossiers"] == 1


def test_dashboard_stem_rule_keeps_current_subset_and_transitive_behavior():
    result = _dashboard_without_extension_stats([
        {
            "request_id": "req-a",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "attachments": [_file("A.jpg", "a" * 64)],
        },
        {
            "request_id": "req-ab",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "attachments": [_file("A.pdf", "b" * 64), _file("B.pdf", "c" * 64)],
        },
        {
            "request_id": "req-b",
            "user_id": "ward-1",
            "procedure": "khai-tu",
            "attachments": [_file("B.png", "d" * 64)],
        },
    ])

    assert result["totalDossiers"] == 1


def test_same_fingerprint_is_retry_only_inside_time_window():
    start = datetime(2026, 8, 25, 1, tzinfo=timezone.utc)
    base = {
        "user_id": "ward-1",
        "procedure": "khai-tu",
        "attachments": [_file("cccd.jpg", "a" * 64)],
    }
    result = _content_stats([
        {**base, "request_id": "req-1", "created_at": start},
        {**base, "request_id": "req-2", "created_at": start + timedelta(minutes=10)},
        {**base, "request_id": "req-3", "created_at": start + timedelta(hours=2)},
    ])

    assert result["totalDossiers"] == 2


def test_hai_chau_retry_duplicate_files_and_pdf_attachment_are_one_dossier():
    start = datetime(2026, 8, 25, 6, 40, tzinfo=timezone.utc)
    jpg_files = [_file("mat-sau.jpg", "a" * 64), _file("mat-truoc.jpg", "b" * 64)]
    result = _content_stats([
        {
            "request_id": "req-first",
            "user_id": "hai-chau",
            "procedure": "khai-tu",
            "stats_version": 2,
            "dossier_ids": ["req-first"],
            "attachments": jpg_files,
            "created_at": start,
        },
        {
            "request_id": "req-retry",
            "user_id": "hai-chau",
            "procedure": "khai-tu",
            "stats_version": 2,
            "dossier_ids": ["req-retry"],
            "attachments": jpg_files + jpg_files,
            "created_at": start + timedelta(minutes=1),
        },
        {
            "request_id": "req-attach",
            "user_id": "hai-chau",
            "procedure": "khai-tu",
            "stats_version": 2,
            "dossier_ids": ["req-retry"],
            "attachments": [
                _file("mat-sau.pdf", "c" * 64),
                _file("mat-truoc.pdf", "d" * 64),
            ],
            "created_at": start + timedelta(minutes=5),
        },
    ])

    assert result["totalDossiers"] == 1


def test_missing_sha_falls_back_to_name_and_is_reported_as_estimated():
    result = _content_stats([
        {
            "request_id": "req-old-1",
            "user_id": "ward-1",
            "procedure": "trich-luc-ks",
            "attachments": [_file("CCCD.pdf", None)],
        },
        {
            "request_id": "req-old-2",
            "user_id": "ward-1",
            "procedure": "trich-luc-ks",
            "attachments": [_file(" cccd.PDF ", None)],
        },
    ])

    assert result["totalDossiers"] == 1
    assert result["estimatedDossiers"] == 1
    assert result["missingShaTraces"] == 2


def test_split_trace_keeps_one_dossier_per_business_id():
    result = _content_stats([
        {
            "request_id": "req-split",
            "user_id": "ward-1",
            "procedure": "chung-thuc-ban-sao",
            "split": True,
            "stats_version": 2,
            "dossier_ids": ["req-split:1", "req-split:2"],
            "attachments": [_file("A.pdf", "a" * 64)],
        }
    ])

    assert result["totalDossiers"] == 2
    assert result["exactDossiers"] == 2
