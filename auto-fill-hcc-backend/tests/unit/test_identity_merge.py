from app.pipelines._shared.identity_merge import (
    merge_identity_attachments,
    merge_identity_records,
)


def _item(index: int, *, target: str = "existing") -> dict:
    return {
        "fileIndex": index,
        "fileName": f"cccd-{index}.jpg",
        "documentName": "Căn cước công dân",
        "componentName": "Dòng căn cước",
        "target": target,
        "componentIndex": 3 if target == "existing" else None,
        "needsAddComponent": target != "existing",
        "detectedType": "Căn cước công dân",
    }


def test_three_cccd_subjects_only_merge_front_and_back_of_same_person():
    numbers = ["012345678901", "109876543210", "024075004310"]
    texts = {
        0: f"CĂN CƯỚC CÔNG DÂN Số {numbers[0]} Họ và tên NGUYỄN A",
        1: f"CĂN CƯỚC CÔNG DÂN Số {numbers[1]} Họ và tên NGUYỄN B",
        2: f"ĐẶC ĐIỂM NHẬN DẠNG IDVNM{numbers[0]}",
        3: f"CĂN CƯỚC CÔNG DÂN Số {numbers[2]} Họ và tên NGUYỄN C",
        4: f"ĐẶC ĐIỂM NHẬN DẠNG IDVNM{numbers[1]}",
        5: f"ĐẶC ĐIỂM NHẬN DẠNG IDVNM{numbers[2]}",
    }

    result = merge_identity_attachments(
        [_item(index) for index in range(6)],
        texts,
        set(range(6)),
    )

    assert len(result) == 3
    assert [item["sourceFileIndexes"] for item in result] == [[0, 2], [1, 4], [3, 5]]
    assert result[0]["target"] == "existing"
    assert result[0]["componentIndex"] == 3
    assert [item["target"] for item in result[1:]] == ["new", "new"]
    assert [item["componentIndex"] for item in result[1:]] == [None, None]
    assert len({item["componentName"] for item in result}) == 3


def test_segment_records_keep_different_subjects_in_different_rows():
    number_a = "012345678901"
    number_b = "109876543210"
    records = []
    for order, text in enumerate([
        f"ĐẶC ĐIỂM NHẬN DẠNG IDVNM{number_a}",
        f"CĂN CƯỚC CÔNG DÂN Số {number_b}",
        f"CĂN CƯỚC CÔNG DÂN Số {number_a}",
        f"ĐẶC ĐIỂM NHẬN DẠNG IDVNM{number_b}",
    ]):
        item = _item(order, target="new")
        item["sourceSegments"] = [{"fileIndex": order, "pageIndexes": [0]}]
        records.append({"item": item, "ocrText": text, "order": order})

    result = merge_identity_records(records, existing_slot=(2, "Dòng căn cước"))

    assert len(result) == 2
    assert [
        [source["fileIndex"] for source in item["sourceSegments"]]
        for item in result
    ] == [[2, 0], [1, 3]]
    assert result[0]["target"] == "existing"
    assert result[1]["target"] == "new"


def test_unknown_identity_sides_are_not_merged_speculatively():
    result = merge_identity_records([
        {"item": _item(0, target="new"), "ocrText": "ĐẶC ĐIỂM NHẬN DẠNG IDVNM OCR LỖI", "order": 0},
        {"item": _item(1, target="new"), "ocrText": "ĐẶC ĐIỂM NHẬN DẠNG IDVNM KHÔNG CÓ SỐ", "order": 1},
    ])

    assert len(result) == 2
    assert all("sourceSegments" not in item for item in result)

