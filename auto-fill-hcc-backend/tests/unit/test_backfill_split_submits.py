"""Script tái tạo lần nộp chứng thực bản sao đa tab — ghi vào DỮ LIỆU THẬT nên khoá kỹ phạm vi."""
from datetime import datetime

import pytest

mongomock = pytest.importorskip("mongomock")

from scripts import backfill_split_submits as bf  # noqa: E402

SUBMIT_AT = datetime(2026, 9, 18, 9, 0)  # 16:00 giờ VN
ATTACH_AT = datetime(2026, 9, 18, 8, 58)


def _db():
    return mongomock.MongoClient()["t"]


def _dossier(db, _id, *, experience="handfree", procedure="chung-thuc-ban-sao",
             submit_count=1, events=None, ref="144725"):
    if events is None:
        events = [{"at": SUBMIT_AT, "host": "dichvucong.gov.vn", "ref": ref}] * submit_count
    db.dossiers.insert_one({
        "_id": _id, "experience": experience, "procedure": procedure,
        "ward": "Phường Vũ Ninh", "started_at": datetime(2026, 9, 18, 8, 52),
        "submit_count": submit_count, "submit_events": events,
        "submit_clicked_at": SUBMIT_AT if submit_count else None,
        "portal_dossier_ref": ref, "portal_host": "dichvucong.gov.vn",
    })


def _trace(db, dossier_id, n_files, *, split=True, status="done", at=ATTACH_AT, attachments=None):
    db.traces.insert_one({
        "dossier_id": dossier_id, "kind": "attach", "split": split, "status": status,
        "attachments": attachments if attachments is not None
        else [{"name": f"f{i}.pdf"} for i in range(n_files)],
        "created_at": at,
    })


def test_ca_vu_ninh_4_tep_1_lan_nop_them_3_lan_y_nguyen():
    db = _db()
    _dossier(db, "vn")
    _trace(db, "vn", 4)

    todo, ambiguous = bf.plan_backfill(db)
    assert [(r["id"], r["current"], r["expected"], r["missing"]) for r in todo] == [("vn", 1, 4, 3)]
    assert ambiguous == []

    assert bf.apply_backfill(db, todo) == 1
    doc = db.dossiers.find_one({"_id": "vn"})
    assert doc["submit_count"] == 4
    assert len(doc["submit_events"]) == 4
    # Y NGUYÊN giờ + mã của lần nộp gốc.
    assert {(e["at"], e["ref"]) for e in doc["submit_events"]} == {(SUBMIT_AT, "144725")}
    # 3 bản tái tạo mang cờ để gỡ lại được; bản gốc thì không.
    assert sum(1 for e in doc["submit_events"] if e.get("reconstructed")) == 3


def test_chay_lai_khong_cong_don():
    db = _db()
    _dossier(db, "vn")
    _trace(db, "vn", 4)
    bf.apply_backfill(db, bf.plan_backfill(db)[0])
    todo, _ = bf.plan_backfill(db)
    assert todo == []
    assert db.dossiers.find_one({"_id": "vn"})["submit_count"] == 4


def test_khong_dung_ban_popup_vi_popup_da_dem_dung():
    db = _db()
    _dossier(db, "af", experience="autofill")
    _trace(db, "af", 4)
    assert bf.plan_backfill(db) == ([], [])


def test_khong_dung_hoso_gop_khong_da_tab():
    db = _db()
    _dossier(db, "gop")
    _trace(db, "gop", 4, split=False)
    assert bf.plan_backfill(db) == ([], [])


def test_khong_dung_hoso_chua_nop_lan_nao():
    db = _db()
    _dossier(db, "chua", submit_count=0, events=[])
    _trace(db, "chua", 4)
    assert bf.plan_backfill(db) == ([], [])


def test_khong_dung_thu_tuc_ngoai_chung_thuc():
    db = _db()
    _dossier(db, "kh", procedure="ket-hon")
    _trace(db, "kh", 4)
    assert bf.plan_backfill(db) == ([], [])


def test_chu_ky_khong_tinh_cccd_thanh_ho_so_rieng():
    """3 văn bản + 1 CCCD = 4 tệp nhưng chỉ 3 hồ sơ: CCCD chỉ đi kèm hồ sơ đầu (STT2)."""
    db = _db()
    _dossier(db, "ck", procedure="chung-thuc-chu-ky")
    _trace(db, "ck", 0, attachments=[
        {"name": "Hop_dong.pdf", "role": "Giấy tờ cần chứng thực chữ ký"},
        {"name": "Giay_uy_quyen.pdf", "role": "Giấy tờ cần chứng thực chữ ký"},
        {"name": "Don.pdf", "role": "Giấy tờ cần chứng thực chữ ký"},
        {"name": "CCCD_mat_truoc.jpg", "role": "Căn cước công dân"},
    ])
    todo, _ = bf.plan_backfill(db)
    assert [(r["id"], r["expected"], r["missing"]) for r in todo] == [("ck", 3, 2)]


def test_ban_sao_van_tinh_ca_tep_can_cuoc():
    """Bản sao: căn cước CŨNG là giấy cần sao → vẫn là một hồ sơ riêng, không được bỏ."""
    db = _db()
    _dossier(db, "bs")
    _trace(db, "bs", 0, attachments=[
        {"name": "CCCD.jpg", "role": "Căn cước công dân"}, {"name": "Bang.pdf", "role": ""},
    ])
    todo, _ = bf.plan_backfill(db)
    assert [(r["id"], r["expected"]) for r in todo] == [("bs", 2)]


def test_ctv_moi_tep_mot_ho_so():
    db = _db()
    _dossier(db, "ctv", procedure="chung-thuc-chu-ky-nguoi-dich-ctv")
    _trace(db, "ctv", 3)
    todo, _ = bf.plan_backfill(db)
    assert [(r["id"], r["missing"]) for r in todo] == [("ctv", 2)]


def test_loc_theo_thu_tuc():
    db = _db()
    _dossier(db, "bs")
    _trace(db, "bs", 4)
    _dossier(db, "ck", procedure="chung-thuc-chu-ky")
    _trace(db, "ck", 4)
    todo, _ = bf.plan_backfill(db, procedures=("chung-thuc-chu-ky",))
    assert [r["id"] for r in todo] == ["ck"]


def test_da_du_hoac_thua_thi_bo_qua():
    db = _db()
    _dossier(db, "du", submit_count=4)
    _trace(db, "du", 4)
    _dossier(db, "thua", submit_count=5)  # bấm hụt rồi bấm lại → thừa là thật, không trừ
    _trace(db, "thua", 4)
    assert bf.plan_backfill(db) == ([], [])


def test_trace_loi_khong_tinh():
    db = _db()
    _dossier(db, "loi")
    _trace(db, "loi", 4, status="error")
    assert bf.plan_backfill(db) == ([], [])


def test_nhieu_luot_da_tab_so_tep_khac_nhau_la_mo_ho_khong_tu_sua():
    db = _db()
    _dossier(db, "mh")
    _trace(db, "mh", 4, at=datetime(2026, 9, 18, 8, 50))
    _trace(db, "mh", 2, at=datetime(2026, 9, 18, 8, 58))
    todo, ambiguous = bf.plan_backfill(db)
    assert todo == [] and [r["id"] for r in ambiguous] == ["mh"]
    # --gom-mo-ho: lấy lượt MỚI NHẤT (2 tệp) → chỉ thêm 1.
    todo, _ = bf.plan_backfill(db, take_ambiguous=True)
    assert [(r["id"], r["missing"]) for r in todo] == [("mh", 1)]


def test_nhieu_luot_cung_so_tep_khong_mo_ho():
    db = _db()
    _dossier(db, "rt")
    _trace(db, "rt", 4, at=datetime(2026, 9, 18, 8, 50))
    _trace(db, "rt", 4, at=datetime(2026, 9, 18, 8, 58))  # đính lại y hệt
    todo, ambiguous = bf.plan_backfill(db)
    assert [(r["id"], r["missing"]) for r in todo] == [("rt", 3)] and ambiguous == []


def test_mang_su_kien_rong_thi_dung_lai_tu_truong_rut_gon():
    db = _db()
    _dossier(db, "cu", submit_count=1, events=[])  # hồ sơ cũ ghi trước khi có mảng
    _trace(db, "cu", 3)
    todo, _ = bf.plan_backfill(db)
    assert todo[0]["template"]["at"] == SUBMIT_AT and todo[0]["template"]["ref"] == "144725"
    bf.apply_backfill(db, todo)
    assert db.dossiers.find_one({"_id": "cu"})["submit_count"] == 3


def test_so_lan_nop_doi_giua_chung_thi_khong_ghi():
    """Có lần nộp thật chen vào giữa lúc đọc và lúc ghi → bỏ qua, không cộng dồn sai."""
    db = _db()
    _dossier(db, "vn")
    _trace(db, "vn", 4)
    todo, _ = bf.plan_backfill(db)
    db.dossiers.update_one({"_id": "vn"}, {"$inc": {"submit_count": 1}})  # nộp thật chen vào
    assert bf.apply_backfill(db, todo) == 0
    assert db.dossiers.find_one({"_id": "vn"})["submit_count"] == 2


def test_revert_go_sach_ve_nhu_cu():
    db = _db()
    _dossier(db, "vn")
    _trace(db, "vn", 4)
    bf.apply_backfill(db, bf.plan_backfill(db)[0])
    assert bf.revert_backfill(db, write=True) == 1
    doc = db.dossiers.find_one({"_id": "vn"})
    assert doc["submit_count"] == 1
    assert [e.get("reconstructed") for e in doc["submit_events"]] == [None]


def test_revert_chay_thu_khong_ghi():
    db = _db()
    _dossier(db, "vn")
    _trace(db, "vn", 4)
    bf.apply_backfill(db, bf.plan_backfill(db)[0])
    bf.revert_backfill(db, write=False)
    assert db.dossiers.find_one({"_id": "vn"})["submit_count"] == 4
