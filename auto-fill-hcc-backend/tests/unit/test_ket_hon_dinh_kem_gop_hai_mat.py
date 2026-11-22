"""Kết hôn (không tách): giấy hai mặt không phải CCCD quét thành hai file → một tài liệu gộp, mặt có tiêu đề đứng trước."""
from app.pipelines.ket_hon.attach.dinh_kem_khong_tach import planner

_TRUOC = "GIẤY PHÉP LÁI XE\nHọ tên: NGUYEN VAN A"
_SAU = "CÁC LOẠI XE CƠ GIỚI ĐƯỜNG BỘ ĐƯỢC ĐIỀU KHIỂN\nB0000001"


def _items(names):
    return [{"fileIndex": i, "documentName": n, "componentName": n, "target": "new"} for i, n in enumerate(names)]


def _run(llm, names=("Giấy phép lái xe", "Giấy phép lái xe 2", "Thông báo cư trú"), texts=(_SAU, _TRUOC, "THÔNG BÁO")):
    classified = [{"fileIndex": i, "type": "other"} for i in range(len(names))]
    by_index = planner._validated_classifications(llm, len(names))
    return planner._merge_two_sided(_items(names), classified, by_index, dict(enumerate(texts)))


def test_hai_mat_gop_mot_tai_lieu_mat_co_tieu_de_dung_truoc():
    out = _run([{"fileIndex": 0, "type": "other", "otherSide": 1}, {"fileIndex": 1, "type": "other"},
                {"fileIndex": 2, "type": "other"}])
    assert [(a["fileIndex"], a.get("sourceFileIndexes")) for a in out] == [(1, [1, 0]), (2, None)]
    assert out[0]["documentName"] == "Giấy phép lái xe"


def test_khong_gop_khi_llm_khong_ghep_hoac_chi_ve_file_khac():
    assert all("sourceFileIndexes" not in a for a in _run([{"fileIndex": i, "type": "other"} for i in range(3)]))
    out = _run([{"fileIndex": 0, "type": "other", "otherSide": 1}, {"fileIndex": 1, "type": "other", "otherSide": 2},
                {"fileIndex": 2, "type": "other"}])
    assert [a["fileIndex"] for a in out if a.get("sourceFileIndexes")] == [1]
    assert len(out) == 2


def test_khong_gop_voi_file_khong_phai_other():
    classified = [{"fileIndex": 0, "type": "other"}, {"fileIndex": 1, "type": "identity"}]
    by_index = planner._validated_classifications([{"fileIndex": 0, "type": "other", "otherSide": 1}], 2)
    out = planner._merge_two_sided(_items(["Giấy phép lái xe", "Căn cước công dân"]), classified, by_index, {})
    assert all("sourceFileIndexes" not in a for a in out) and len(out) == 2
