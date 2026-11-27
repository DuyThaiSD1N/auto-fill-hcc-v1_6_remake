"""Trang Danh mục thủ tục (thống kê): gộp Auto Fill + Trợ lý người dân, theo tỉnh của tài khoản.

Tài khoản xã/tỉnh thấy thủ tục áp dụng cho tỉnh mình (dùng chung + riêng của tỉnh); không xác định được tỉnh
thì chỉ dùng chung; admin thấy hết kèm mọi tỉnh đã có đơn vị. Mỗi thủ tục ghi tỉnh mà Trợ lý người dân chưa chạy.
"""
import pytest

from app.dashboard import procedures as dashboard_procedures

_PROCS = [
    {"key": "chung", "label": "Thủ tục chung", "shortLabel": "Chung", "mode": "agent", "hasAttachmentStep": True,
     "detect": {"urlIncludes": ["maThuTuc=1.004772"]}},
    {"key": "lien-thong", "label": "Liên thông", "keKhaiUrl": "https://x/#/ke-khai/2.000987",
     "mode": "agent", "hasAttachmentStep": True,
     "detect": {"urlIncludes": ["#/ke-khai/2.000986", "#/ke-khai/2.000987"]}},
    {"key": "rieng-lai-chau", "label": "Riêng Lai Châu", "provinceOnly": ["laichau"], "mode": "attach",
     "hasAttachmentStep": True},
    {"key": "rieng-hai-tinh", "label": "Riêng hai tỉnh", "provinceOnly": ["quangtri", "danang"], "mode": "agent",
     "hasAttachmentStep": False},
]
# Danh mục Auto Fill: đủ thủ tục trợ lý + thủ tục chỉ có ở Auto Fill (riêng Ninh Bình nhận theo tiền tố tên).
_CORE = [*({k: v for k, v in p.items() if k not in ("shortLabel", "provinceOnly")} | (
    {"provinceOnly": p["provinceOnly"]} if p.get("provinceOnly") else {}) for p in _PROCS),
    {"key": "dat-dai-ninh-binh", "label": "[Tỉnh Ninh Bình] Đăng ký đất đai", "mode": "agent", "hasAttachmentStep": True},
    {"key": "chi-auto-fill", "label": "Chỉ Auto Fill", "mode": "attach", "hasAttachmentStep": False}]


@pytest.fixture(autouse=True)
def registry(monkeypatch):
    monkeypatch.setattr(dashboard_procedures, "public_list", lambda: _PROCS)
    monkeypatch.setattr(dashboard_procedures, "core_public_list", lambda: _CORE)
    # Bảng hoàn thiện giả: liên thông chưa hoàn thiện trên Trợ lý người dân ở Lai Châu.
    monkeypatch.setattr(dashboard_procedures, "is_visible_in_province",
                        lambda proc, slug: not (proc["key"] == "lien-thong" and slug == "laichau"))


def _scope(kind, province=None, units=()):
    return {"scopeKind": kind, "province": province, "units": [{"tinh": t} for t in units]}


def _keys(body):
    return [item["key"] for item in body["items"]]


@pytest.mark.parametrize("kind", ["unit", "province"])
def test_tai_khoan_tinh_thay_chung_va_rieng_tinh_minh(kind):
    body = dashboard_procedures.catalog(_scope(kind, "Tỉnh Lai Châu"))
    assert _keys(body) == ["chung", "lien-thong", "rieng-lai-chau", "chi-auto-fill"]
    assert body["province"] == {"slug": "laichau", "name": "Lai Châu"}
    assert body["provinces"] == [{"slug": "laichau", "name": "Lai Châu", "count": 1}]
    items = {i["key"]: i for i in body["items"]}
    # Chưa hoàn thiện trên Trợ lý người dân ở Lai Châu → vẫn áp dụng (qua Auto Fill), ghi tỉnh chưa chạy handfree.
    assert items["lien-thong"]["handfree"] is True and items["lien-thong"]["handfreeOff"] == ["laichau"]
    assert items["chi-auto-fill"]["handfree"] is False and items["chung"]["handfreeOff"] == []


def test_tai_khoan_khong_xac_dinh_tinh_chi_thay_dung_chung():
    body = dashboard_procedures.catalog(_scope("unit", None))
    assert _keys(body) == ["chung", "lien-thong", "chi-auto-fill"]
    assert body["province"] is None
    assert body["provinces"] == []


def test_admin_thay_het_va_moi_tinh_da_trien_khai():
    """Ô chọn tỉnh có cả tỉnh chỉ dùng thủ tục chung (đã có đơn vị), không chỉ tỉnh có thủ tục riêng."""
    body = dashboard_procedures.catalog(_scope("all", units=["Tỉnh Lào Cai", "Tỉnh Lai Châu", "Bộ Công an"]))
    assert _keys(body) == ["chung", "lien-thong", "rieng-lai-chau", "rieng-hai-tinh", "dat-dai-ninh-binh", "chi-auto-fill"]
    assert {p["name"]: p["count"] for p in body["provinces"]} == {
        "Đà Nẵng": 1, "Lai Châu": 1, "Lào Cai": 0, "Ninh Bình": 1, "Quảng Trị": 1}
    items = {i["key"]: i for i in body["items"]}
    assert [p["slug"] for p in items["rieng-hai-tinh"]["provinces"]] == ["danang", "quangtri"]
    assert [p["slug"] for p in items["dat-dai-ninh-binh"]["provinces"]] == ["ninhbinh"]
    assert items["lien-thong"]["handfreeOff"] == ["laichau"]


def test_tai_khoan_ninh_binh_thay_thu_tuc_chung_va_dat_dai_rieng():
    body = dashboard_procedures.catalog(_scope("unit", "Tỉnh Ninh Bình"))
    assert _keys(body) == ["chung", "lien-thong", "dat-dai-ninh-binh", "chi-auto-fill"]


def test_ma_tthc_lay_tu_url_ke_khai_va_nhan_dien_khong_trung():
    items = {i["key"]: i for i in dashboard_procedures.catalog(_scope("all"))["items"]}
    assert items["chung"]["codes"] == ["1.004772"]
    # URL kê khai có mã thì không lấy thêm mã của biến thể chỉ dùng để nhận diện trang.
    assert items["lien-thong"]["codes"] == ["2.000987"]
    assert items["rieng-lai-chau"]["codes"] == []


def test_khong_tra_cau_hinh_noi_bo():
    item = dashboard_procedures.catalog(_scope("all"))["items"][0]
    assert set(item) == {"key", "label", "shortLabel", "codes", "support", "provinces", "autofill", "autofillProvinces",
                         "handfree", "handfreeOff"}


def test_tro_ly_ho_tro_dien_hay_chi_dinh_kem():
    items = {i["key"]: i["support"] for i in dashboard_procedures.catalog(_scope("all"))["items"]}
    assert items == {"chung": "fill_attach", "lien-thong": "fill_attach", "rieng-lai-chau": "attach",
                     "rieng-hai-tinh": "fill", "dat-dai-ninh-binh": "fill_attach", "chi-auto-fill": "attach"}


def test_registry_that_khop_auto_fill_va_tro_ly(monkeypatch):
    """Không mock: thủ tục áp dụng cho Ninh Bình = đúng tập Auto Fill hiện cho tỉnh đó (có 6 thủ tục đất đai riêng);
    thủ tục ghi chạy được trên Trợ lý người dân = đúng tập trợ lý hiện cho tỉnh."""
    monkeypatch.undo()
    from app.channels.handfree.procedure_registry import public_list_for
    from app.procedures.ke_khai_links import procedure_province_slugs, visible_in_province, with_province_only
    from app.procedures.registry import public_list as core_list

    body = dashboard_procedures.catalog(_scope("unit", "Tỉnh Ninh Bình"))
    auto_fill = {p["key"] for p in visible_in_province(with_province_only(core_list(), procedure_province_slugs), "ninhbinh")}
    handfree = {p["key"] for p in public_list_for("ninhbinh")}
    # Áp dụng = có ít nhất một kênh chạy ở tỉnh; 6 thủ tục đất đai riêng Ninh Bình (chỉ Auto Fill) có mặt.
    # Thủ tục kênh nào đó khoá cho tỉnh khác (cổng riêng tỉnh khác) không tính cho Ninh Bình dù kênh kia mở.
    keys = set(_keys(body))
    assert keys <= auto_fill | handfree
    every = {i["key"]: i for i in dashboard_procedures.catalog(_scope("all"))["items"]}
    for key in auto_fill - keys:
        assert every[key]["provinces"] and "ninhbinh" not in [p["slug"] for p in every[key]["provinces"]]
    # 6 thủ tục đất đai (26/11) + tách thửa hoặc hợp thửa đất 1.012784 (27/11).
    assert sum(1 for i in body["items"] if [p["slug"] for p in i["provinces"]] == ["ninhbinh"]) == 7
    on_handfree = {i["key"] for i in body["items"] if i["handfree"] and "ninhbinh" not in i["handfreeOff"]}
    assert on_handfree == handfree & keys


def test_registry_that_thu_tuc_nao_co_ma_cung_tra_ma(monkeypatch):
    """Mã ở trường `code` hoặc ở link kê khai cùng key cũng phải lên danh mục, không chỉ mã trong URL."""
    monkeypatch.undo()
    items = {i["key"]: i for i in dashboard_procedures.catalog(_scope("all"))["items"]}
    assert "1.115820" in items["dang-ky-dat-dai-lan-dau-quang-ninh-mien-nui-hai-dao"]["codes"]
    assert "1.013229" in items["sua-chua-cai-tao-gpxd-nha-o-rieng-le"]["codes"]
    # Thủ tục của Trợ lý người dân đều có mã (một số thủ tục chỉ Auto Fill chưa ghi mã trong cấu hình).
    assert sum(1 for i in items.values() if i["handfree"] and not i["codes"]) <= 1
    assert items["khai-sinh-dang-ky"]["codes"] == ["2.000987"]


def test_xuat_excel_dung_dong_dang_loc_va_trong_pham_vi():
    import io
    from datetime import datetime, timezone

    from openpyxl import load_workbook

    from app.dashboard.export import build_catalog_workbook

    items = dashboard_procedures.catalog(_scope("unit", "Tỉnh Lai Châu"))["items"]
    by_key = {i["key"]: i for i in items}
    picked = [by_key[k] for k in ["lien-thong", "chung", "rieng-lai-chau"]]
    raw = build_catalog_workbook(picked, "Dùng chung", datetime(2026, 11, 13, tzinfo=timezone.utc))
    ws = load_workbook(io.BytesIO(raw)).active
    rows = [r for r in ws.iter_rows(min_row=4, values_only=True)]
    assert rows[0] == ("STT", "Tên thủ tục", "Mã TTHC", "Trợ lý hỗ trợ", "Kênh", "Áp dụng")
    assert rows[1:] == [
        (1, "Liên thông", "2.000987", "Điền + đính kèm", "Auto Fill + Trợ lý người dân", "Dùng chung"),
        (2, "Thủ tục chung", "1.004772", "Điền + đính kèm", "Auto Fill + Trợ lý người dân", "Dùng chung"),
        (3, "Riêng Lai Châu", None, "Chỉ đính kèm", "Auto Fill + Trợ lý người dân", "Riêng · Lai Châu"),
    ]
    # Xuất cho Lai Châu: liên thông chưa chạy trên Trợ lý người dân ở tỉnh này.
    raw = build_catalog_workbook(picked, "", datetime(2026, 11, 13, tzinfo=timezone.utc), "laichau")
    assert load_workbook(io.BytesIO(raw)).active.cell(row=5, column=5).value == "Chỉ Auto Fill"
    assert "Dùng chung" in ws["A2"].value and "3 thủ tục" in ws["A2"].value

