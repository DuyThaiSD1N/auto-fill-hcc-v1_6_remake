"""Phiếu đánh giá của Auto Fill (POST /api/v1/dossiers/rating).

Điểm sống còn: mức chọn ở BƯỚC 1 phải được ghi NGAY. Công dân chạm mặt cười rồi bỏ đi, không
bấm "Gửi đánh giá" — vẫn phải còn con số đó, y như Handfree (`rate_level` ghi liền). Gom lại
chờ bước 2 là mất phần lớn phiếu, vì bước 2 mới là bước người ta hay bỏ dở.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.deps import require_auth
from app.dossiers.router import router as dossiers_router


@pytest.fixture()
def client(monkeypatch):
    saved: list[dict] = []

    async def fake_save_rating(**kwargs):
        saved.append(kwargs)

    import app.dossiers.router as module
    monkeypatch.setattr(module.dossiers_repo, "save_rating", fake_save_rating)

    app = FastAPI()
    app.include_router(dossiers_router)
    app.dependency_overrides[require_auth] = lambda: {"id": "u1", "username": "hcctanphong"}
    return TestClient(app), saved


def test_buoc_1_chi_co_muc_van_duoc_ghi_ngay(client):
    c, saved = client
    assert c.post("/api/v1/dossiers/rating", json={"dossierId": "d1", "level": 5}).status_code == 200

    (call,) = saved
    assert call["level"] == 5
    assert call["level_label"] == "Rất hài lòng", "nhãn suy từ rating_card, không để client tự gửi"
    assert call["skipped"] is False, "chọn mức rồi bỏ dở KHÔNG phải là bỏ qua đánh giá"
    assert call["reasons"] == [] and call["note"] == ""
    assert call["owner_user_id"] == "u1"


def test_buoc_2_ghi_de_len_phieu_buoc_1(client):
    c, saved = client
    c.post("/api/v1/dossiers/rating", json={"dossierId": "d1", "level": 4})
    c.post("/api/v1/dossiers/rating", json={
        "dossierId": "d1", "level": 4,
        "reasons": ["Làm nhanh hơn trước", "  "], "note": "  cán bộ nhiệt tình  ",
    })

    assert len(saved) == 2, "hai lượt ghi riêng biệt — bước 1 không chờ bước 2"
    assert saved[1]["reasons"] == ["Làm nhanh hơn trước"], "bỏ lý do rỗng"
    assert saved[1]["note"] == "cán bộ nhiệt tình"
    assert saved[1]["skipped"] is False


def test_bo_qua_han_thi_danh_dau_skipped(client):
    c, saved = client
    c.post("/api/v1/dossiers/rating", json={"dossierId": "d1", "skipped": True})
    assert saved[0]["skipped"] is True and saved[0]["level"] is None


def test_khong_cham_gi_cung_tinh_la_bo_qua(client):
    # Client cũ/lỗi không gửi cờ skipped: tự suy thay vì tin cờ, để phiếu rỗng không bị đếm
    # thành phiếu có ý kiến.
    c, saved = client
    c.post("/api/v1/dossiers/rating", json={"dossierId": "d1"})
    assert saved[0]["skipped"] is True


@pytest.mark.parametrize("level", [0, 6, -1])
def test_muc_ngoai_thang_bi_tu_choi(client, level):
    c, saved = client
    r = c.post("/api/v1/dossiers/rating", json={"dossierId": "d1", "level": level})
    assert r.status_code == 422 and saved == []


def test_gioi_han_do_dai_de_khong_phinh_document(client):
    c, saved = client
    r = c.post("/api/v1/dossiers/rating", json={
        "dossierId": "d1", "level": 3, "reasons": [f"ly do {i}" for i in range(11)],
    })
    assert r.status_code == 422, "tối đa 10 lý do"

    c.post("/api/v1/dossiers/rating", json={"dossierId": "d1", "level": 3, "reasons": ["x" * 300]})
    assert len(saved[0]["reasons"][0]) == 120, "cắt lý do quá dài thay vì từ chối cả phiếu"


def test_card_dung_chung_mot_nguon_voi_handfree():
    from app.channels.handfree.chat import script_vi as vi
    from app.dossiers.rating_card import RATING_CARD

    assert vi.RATING_CARD is RATING_CARD, "hai kênh phải hỏi CÙNG câu chữ, không được chép hai bản"
