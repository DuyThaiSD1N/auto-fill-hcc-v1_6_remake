"""[Bộ Y tế] Điều chỉnh giấy phép hoạt động KCB — chủ hồ sơ là CƠ SỞ, 2 chế độ người nộp, đính kèm không bỏ tệp."""

import re
from pathlib import Path

from app.pipelines.dieu_chinh_giay_phep_hoat_dong_kcb.attach import planner, prompt
from app.pipelines.dieu_chinh_giay_phep_hoat_dong_kcb.process import mapper
from app.procedures.registry import public_list

_KEY = "dieu-chinh-giay-phep-hoat-dong-kcb"
_ROOT = Path(__file__).resolve().parents[2].parent

_FACTS = {
    "CoSo_Ten": "Trung tâm Y tế Mẫu A",
    "CoSo_LoaiDoiTuong": "Cơ quan nhà nước",
    "CoSo_DiaChi": {"tinh": "Tỉnh Lai Châu", "xa": "Xã Mẫu", "diaChi": "Tổ dân phố 1"},
    "CoSo_DienThoai": "02130000001",
    "CoSo_Fax": "02130000002",
    "DaiDien_HoTen": "Nguyễn Văn A",
}
_REP_CCCD = {"DaiDien_SoDinhDanh": "001000000001", "DaiDien_NgaySinh": "01/02/1980", "DaiDien_GioiTinh": "Nam"}
_SUBMITTER = {"NguoiNop_HoTen": "TRAN THI B", "NguoiNop_SoDinhDanh": "001000000002", "NguoiNop_NgaySinh": "05/06/1992"}


def _run(values, options=None):
    fields, warnings = mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options)
    return {f["name"]: f for f in fields}, [f["name"] for f in fields], warnings


def _account(name, identity=None):
    ctx = {"applicantFullname": name}
    if identity:
        ctx["applicantIdentityNumber"] = identity
    return {"formContext": ctx}


def test_registry():
    entry = next(p for p in public_list() if p["key"] == _KEY)
    assert entry["mode"] == "agent" and entry["hasAttachmentStep"] is True


def test_chon_loai_to_chuc_truoc_moi_o_to_chuc():
    ui, order, _ = _run(_FACTS)
    assert ui["data[chonDoiTuong]"]["value"] == "Cơ quan nhà nước"
    assert order[0] == "data[chonDoiTuong]"
    assert ui["data[organization]"]["value"] == "Trung tâm Y tế Mẫu A"


def test_khong_moc_tai_khoan_la_tu_nop_phan_mot_theo_co_so_tich_o():
    ui, order, _ = _run(_FACTS)
    assert ui["data[isOwnerDossierCheck]"]["value"] is True
    assert ui["data[fullname]"]["value"] == "Nguyễn Văn A"
    assert ui["data[province]"]["value"] == "Tỉnh Lai Châu" and ui["data[address]"]["value"] == "Tổ dân phố 1"
    assert ui["data[phoneNumber]"]["value"] == "02130000001" and ui["data[fax]"]["value"] == "02130000002"
    assert not any(k.startswith("data[owner") for k in ui)


def test_theo_tai_khoan_khop_nguoi_ky_don_la_tu_nop_khong_de_o_cong_da_dien():
    ui, _, _ = _run({**_FACTS, **_REP_CCCD}, _account("NGUYỄN VĂN A", "001000000001"))
    assert ui["data[isOwnerDossierCheck]"]["value"] is True
    assert "data[fullname]" not in ui and "data[identityNumber]" not in ui
    assert ui["data[birthday]"]["value"] == "01/02/1980"


def test_nop_thay_bo_tich_dien_phan_hai_co_so_va_nguoi_dai_dien():
    ui, order, warnings = _run({**_FACTS, **_SUBMITTER}, _account("TRẦN THỊ B", "001000000002"))
    assert ui["data[isOwnerDossierCheck]"]["value"] is False
    assert order.index("data[isOwnerDossierCheck]") < order.index("data[ownerOrganizationFullname]")
    assert ui["data[ownerOrganizationFullname]"]["value"] == "Trung tâm Y tế Mẫu A"
    assert ui["data[ownerFullname]"]["value"] == "Nguyễn Văn A"
    assert ui["data[ownerFax]"]["value"] == "02130000002"
    assert ui["data[birthday]"]["value"] == "05/06/1992", "Phần I = CCCD người nộp khớp tài khoản"
    assert "data[phoneNumber]" not in ui, "SĐT cơ sở không đổ sang người nộp thay"
    assert any("không có CCCD của người đại diện" in w for w in warnings)


def test_nop_thay_cccd_nguoi_nop_khong_khop_thi_khong_dien_phan_mot():
    ui, _, _ = _run({**_FACTS, **_SUBMITTER}, _account("LE VAN C", "001000000003"))
    assert "data[birthday]" not in ui and ui["data[isOwnerDossierCheck]"]["value"] is False


def test_che_do_nguoi_nop_la_chu_ho_so_bo_qua_moc_va_ghi_de_ten_cccd_tai_khoan():
    options = {**_account("TRẦN THỊ B", "001000000002"), "submitterMode": "owner_as_submitter"}
    ui, _, _ = _run({**_FACTS, **_REP_CCCD}, options)
    assert ui["data[isOwnerDossierCheck]"]["value"] is True
    assert ui["data[fullname]"]["value"] == "Nguyễn Văn A", "cả khối Phần I là người đại diện, không nửa tài khoản"
    assert ui["data[identityNumber]"]["value"] == "001000000001"
    assert not any(k.startswith("data[owner") for k in ui)


def test_khong_ro_loai_to_chuc_chon_mac_dinh_co_canh_bao():
    values = {k: v for k, v in _FACTS.items() if k != "CoSo_LoaiDoiTuong"}
    ui, _, warnings = _run(values)
    assert ui["data[chonDoiTuong]"]["value"] == "Tổ chức/Doanh nghiệp" and ui["data[chonDoiTuong]"].get("default")
    assert any("Đối tượng nộp hồ sơ" in w for w in warnings)


def test_dinh_kem_dung_dong_va_khong_bo_tep():
    names = ["don.pdf", "gphd.pdf", "qd_syt.pdf", "kekhai.pdf", "qd_ubnd.pdf", "cccd.jpg", "la.pdf"]
    types = {0: "don_de_nghi", 1: "giay_phep_hoat_dong", 2: "quyet_dinh_so_y_te", 3: "ke_khai",
             4: "quyet_dinh_to_chuc_lai", 5: "cccd", 6: "other"}
    items, warnings, _ = planner.build_plan_items([{"name": n} for n in names], types)
    assert [i["fileIndex"] for i in items] == list(range(7))
    comp = [i["componentName"] for i in items]
    assert comp[1] == comp[2] == "Bản gốc giấy phép hoạt động", "GPHĐ + QĐ Sở Y tế chung một dòng"
    assert comp[4] == comp[5] == comp[6] == "Các giấy tờ quy định tại điểm b khoản 3 Điều 54"
    assert items[5]["documentName"] == "cccd.jpg" and items[6]["documentName"] == "la.pdf"
    assert warnings and "la.pdf" in warnings[0]


def test_ocr_dai_bi_cat_truoc_khi_gui_llm():
    user = prompt.build_user_prompt("a.pdf", "x" * 50000)
    assert len(user) < 13000


def _fe_fold(text: str) -> str:
    import unicodedata

    text = str(text or "").replace("Đ", "D").replace("đ", "d")
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    text = re.sub(r"\s*[-‐-―]\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def test_moi_component_khop_dong_that_tren_snapshot():
    pages = [f.read_text(encoding="utf-8", errors="replace") for d in (_ROOT / "thongtin").glob("77_*")
             for f in d.glob("*.html")]
    html = next((p for p in pages if "table-tbt" in p and "rdo_File" in p), None)
    if html is None:
        return
    rows = [_fe_fold(re.sub(r"(?s)<[^>]+>", " ", r))
            for r in re.findall(r'(?s)<tr[^>]*class="[^"]*item[^"]*"[^>]*>(.*?)</tr>', html)]
    assert len(rows) == 5
    for doc_type, row in planner._ROWS.items():
        key = _fe_fold(row["componentName"])
        assert any(key in r for r in rows), doc_type
