"""[Lai Châu] Tổ chức kinh tế nhận chuyển nhượng, thuê QSDĐ, nhận góp vốn bằng QSDĐ để thực hiện dự án (mã 1.115591).

Khóa theo file mapping "Mapping_TTHC_1.115591_ToChucKinhTe_NhanCNQSDD_DuAn_DVC_LaiChau" + ảnh ánh xạ đính kèm:
  - process: "Đối tượng nộp" = Tổ chức; tên tổ chức, MSDN (= MST = Số GCN/GP), ngày cấp lần đầu, nơi cấp, trụ sở từ văn
    bản Mẫu số 30; ô cá nhân CCCD → mục 2 văn bản; ô không có nguồn xoá giá trị cổng đổ theo tài khoản;
  - attach: bảng 2 dòng (trích đo → dòng 1, Mẫu số 30 → dòng 2), CCCD / giấy lạ vào "Giấy tờ khác", tệp quá 6 MB bị loại;
    bật "Tách giấy tờ" thì chia trang đúng dòng, không sót trang; tách lỗi quay về đính nguyên tệp.

Dữ liệu trong test là PLACEHOLDER, không phải hồ sơ thật.
"""

import asyncio
import base64

import fitz
import pytest

from app.pipelines._shared import fold, lao_cai_tach_giay_to
from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhuong_qsdd_du_an_lai_chau.attach import planner as dispatcher
from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhuong_qsdd_du_an_lai_chau.attach.dinh_kem_khong_tach import planner
from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhuong_qsdd_du_an_lai_chau.process import mapper
from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhuong_qsdd_du_an_lai_chau.process.schema import (
    ALLOWED,
    UI_COMP_BY_NAME,
)
from app.process.schemas import FileItem
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure
from app.services import ocr

KEY = "to-chuc-kinh-te-nhan-chuyen-nhuong-qsdd-du-an-lai-chau"
ORG = "Công ty TNHH MTV Mẫu Một"
REP_ID = "012190000001"


def _fields(fields: list[dict]) -> dict:
    return {item["name"]: item for item in fields}


def _values(fields: list[dict]) -> dict:
    return {item["name"]: item["value"] for item in fields if not item.get("clear")}


def _facts(**extra) -> list[dict]:
    """Hồ sơ như mẫu: văn bản Mẫu số 30 + mảnh trích đo, KHÔNG có thẻ CCCD."""
    base = {
        "Vb_ToChuc": ORG,
        "Vb_MaSoDoanhNghiep": "6200000001",
        "Vb_GcnNgayCap": "1/9/2020",
        "Vb_GcnNoiCap": "Phòng Đăng ký kinh doanh - Sở Kế hoạch và Đầu tư tỉnh Lai Châu",
        "Vb_NguoiDaiDien": "Lê Thị Mẫu",
        "Vb_NgaySinh": "3/9/1990",
        "Vb_GioiTinh": "Nữ",
        "Vb_SoDinhDanh": REP_ID,
        "Vb_DiaChiTruSo": {"tinh": "tỉnh Lai Châu", "xa": "phường Tân Phong", "chiTietDuoiXa": "Bản Mẫu"},
        "TrichDo_DiaBan": {"tinh": "Lai Châu", "xa": "Phường Tân Phong"},
    }
    base.update(extra)
    return [{"name": name, "value": value} for name, value in base.items() if value is not None]


CARD = {
    "Cccd_HoTen": "LÊ THỊ MẪU", "Cccd_SoDinhDanh": REP_ID, "Cccd_NgaySinh": "03/09/1990", "Cccd_GioiTinh": "Nữ",
    "Cccd_NgayCap": "12/07/2021", "Cccd_NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "Cccd_NoiCuTru": {"tinh": "Lai Châu", "xa": "Phường Tân Phong", "chiTietDuoiXa": "Tổ 5"},
}


# ---------------------------------------------------------------- process/mapper


def test_mapper_khong_the_dien_to_chuc_va_nguoi_dai_dien_theo_van_ban():
    fields, warnings = mapper.enrich(_facts())
    values, by_name = _values(fields), _fields(fields)

    assert values["CongDan__select_1"] == "Tổ chức"
    assert values["CongDan_tenCoQuanToChuc"] == ORG
    # MSDN = MST = Số GCN/GP; ngày cấp LẦN ĐẦU; nơi cấp nguyên văn (mapping STT 4, 23–25).
    assert values["CongDan_maSoThueNguoiNop"] == values["CongDan_soGCNGP"] == "6200000001"
    assert values["CongDan_ngayCapGCNGP"] == "01/09/2020"
    assert values["CongDan_noiCapGCNGP"].startswith("Phòng Đăng ký kinh doanh")
    # Người đại diện (mục 2) khi không có thẻ.
    assert values["CongDan_tenCongDan"] == "LÊ THỊ MẪU"
    assert values["CongDan_ngaySinhCongDan"] == "03/09/1990"
    assert values["CongDan_gioiTinhCongDan"] == "Nữ"
    assert values["CongDan_soCmnd"] == values["CongDan_soCCCD"] == REP_ID
    # Địa chỉ theo trụ sở mục 3.
    assert values["CongDan_maTinhThanh"] == "Tỉnh Lai Châu"
    assert values["CongDan_maPhuongXa"] == "Phường Tân Phong"
    assert values["CongDan_diaChi"] == "Bản Mẫu"
    # Ô chỉ có trên thẻ / người nộp tự cung cấp → xoá giá trị cổng đổ theo tài khoản.
    for name in ("CongDan_ngayCapCmnd", "CongDan_noiCapCmnd", "CongDan_noiOHienTai", "CongDan_diaChiThuongTru",
                 "CongDan_diDong", "CongDan_email"):
        assert by_name[name]["clear"] is True and by_name[name]["value"] == "", name
    assert not any(item.get("markEmpty") for item in fields)
    assert all(item["comp"] == "dom-input" for item in fields if item.get("clear"))
    assert any("Dân tộc" in w for w in warnings)


def test_mapper_ten_to_chuc_cat_theo_ten_co_quan_ban_hanh():
    # OCR nuốt nửa dòng GCN ĐKDN bị chữ ký đè, chữ sót "thành viên" dính vào tên mục 1.
    values = _values(mapper.enrich(_facts(
        Vb_ToChuc="Công ty TNHH MTV Mẫu Một thành viên", Vb_TenCoQuanBanHanh="CÔNG TY TNHH MTV MẪU MỘT",
    ))[0])
    assert values["CongDan_tenCoQuanToChuc"] == ORG
    # Tên góc trái trên không phải phần đầu mục 1 → giữ nguyên mục 1; thiếu mục 1 → dùng tên góc trái trên.
    values = _values(mapper.enrich(_facts(Vb_TenCoQuanBanHanh="CÔNG TY KHÁC"))[0])
    assert values["CongDan_tenCoQuanToChuc"] == ORG
    values = _values(mapper.enrich(_facts(Vb_ToChuc=None, Vb_TenCoQuanBanHanh="CÔNG TY TNHH MTV MẪU MỘT"))[0])
    assert values["CongDan_tenCoQuanToChuc"] == "CÔNG TY TNHH MTV MẪU MỘT"


def test_mapper_co_the_cung_nguoi_lay_the():
    fields, warnings = mapper.enrich(_facts(**CARD))
    values = _values(fields)

    assert values["CongDan_ngayCapCmnd"] == "12/07/2021"
    assert values["CongDan_noiCapCmnd"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Nơi cấp không phải công an tỉnh → ô CA Tỉnh để trống.
    assert "CongDan_maTinhCapCMND" not in _fields(fields)
    # Nơi ở / thường trú là của cá nhân → theo thẻ; Số nhà vẫn theo trụ sở.
    assert values["CongDan_noiOHienTai"] == values["CongDan_diaChiThuongTru"] == "Tổ 5, Phường Tân Phong, Tỉnh Lai Châu"
    assert values["CongDan_diaChi"] == "Bản Mẫu"
    assert not any("khác người đại diện" in w for w in warnings)


def test_mapper_the_nguoi_khac_khong_tron_van_ban_va_canh_bao():
    card = {"Cccd_HoTen": "TRẦN VĂN KHÁC", "Cccd_SoDinhDanh": "012000000002"}
    fields, warnings = mapper.enrich(_facts(**card))
    values, by_name = _values(fields), _fields(fields)

    assert values["CongDan_tenCongDan"] == "TRẦN VĂN KHÁC"
    assert values["CongDan_soCmnd"] == "012000000002"
    # Không lấy ngày sinh / giới tính của người đại diện bù cho thẻ người khác.
    assert by_name["CongDan_ngaySinhCongDan"]["clear"] and by_name["CongDan_ngaySinhCongDan"]["markEmpty"]
    assert "CongDan_gioiTinhCongDan" not in by_name
    assert any("khác người đại diện" in w for w in warnings)


def test_mapper_tai_khoan_la_nguoi_dai_dien_giu_o_cong():
    fields, _ = mapper.enrich(_facts(), {"formContext": {"applicantIdentityNumber": REP_ID}})
    assert not any(item.get("clear") for item in fields)


def test_mapper_thieu_tru_so_lay_lien_he_roi_dia_ban_trich_do():
    values = _values(mapper.enrich(_facts(
        Vb_DiaChiTruSo=None,
        Vb_DiaChiLienHe={"tinh": "Lai Châu", "xa": "Phường Tân Phong", "chiTietDuoiXa": "Tổ Mẫu"},
    ))[0])
    assert values["CongDan_diaChi"] == "Tổ Mẫu"

    fields, warnings = mapper.enrich(_facts(Vb_DiaChiTruSo=None))
    values = _values(fields)
    # Trích đo chỉ cho tỉnh/xã; chi tiết là vị trí khu đất, không phải trụ sở.
    assert values["CongDan_maTinhThanh"] == "Tỉnh Lai Châu" and values["CongDan_maPhuongXa"] == "Phường Tân Phong"
    assert "CongDan_diaChi" not in _fields(fields)
    assert any("trụ sở" in w for w in warnings)


def test_schema_ui_va_o_khong_phat():
    fields, _ = mapper.enrich(_facts(**CARD))
    assert set(_fields(fields)) <= set(UI_COMP_BY_NAME)
    for name in ("CongDan_fax", "CongDan_website", "CongDan_maDMDiaChi", "CongDan_diaChiNuocNgoai",
                 "CongDan_maDMQuocGia"):
        assert name not in UI_COMP_BY_NAME
    assert UI_COMP_BY_NAME["CongDan__select_1"] == "dom-select"
    assert {"Vb_ToChuc", "Vb_MaSoDoanhNghiep", "Vb_NguoiDaiDien", "Vb_DiaChiTruSo", "TrichDo_DiaBan"} <= ALLOWED


# ---------------------------------------------------------------- attach (đính nguyên tệp)

_VB = ("CÔNG TY TNHH MTV MẪU MỘT CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nSố: 01/CV-MTV\nV/v Đề nghị chấp thuận cho Công ty "
       "nhận chuyển nhượng, thuê quyền sử dụng đất, nhận góp vốn bằng quyền sử dụng đất để thực hiện dự án đầu tư\n"
       "1. Tổ chức đề nghị thực hiện dự án: Công ty TNHH MTV Mẫu Một")
_VB_2 = ("8a. Hình thức giao đất/cho thuê đất sau khi nhận chuyển nhượng, thuê quyền sử dụng đất, nhận góp vốn bằng "
         "quyền sử dụng đất\n9. Thông tin về khả năng thực hiện dự án\nGIÁM ĐỐC")
_TRICH_DO = ("PHƯỜNG TÂN PHONG\nMẢNH TRÍCH ĐO ĐỊA CHÍNH\nHỆ TỌA ĐỘ VN-2000\nPHỤC VỤ CÔNG TÁC THẨM ĐỊNH CHẤP THUẬN CHO "
             "NHẬN CHUYỂN NHƯỢNG QUYỀN SỬ DỤNG ĐẤT ĐỂ THỰC HIỆN DỰ ÁN\nTỶ LỆ 1:1000")
_CCCD = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nCĂN CƯỚC CÔNG DÂN\nHọ và tên / Full name:\nLÊ THỊ MẪU"
_TEXTS = {
    "cong-van.pdf": _VB, "trich-do.pdf": _TRICH_DO, "cccd.pdf": _CCCD,
    "ban-ve-meo.pdf": "475 552-1 475 552-1 Tờ số 195\nTỷ lệ 1:1000 1059,3 984,8",
    "bien-lai.pdf": "Biên lai thu phí",
}


def _files(names: list[str], sizes: dict | None = None) -> list[dict]:
    out = []
    for name in names:
        size = (sizes or {}).get(name)
        data = base64.b64encode(b"x" * size).decode() if size else "QQ=="
        out.append({"name": name, "type": "application/pdf", "dataUrl": f"data:application/pdf;base64,{data}"})
    return out


def _texts(names: list[str]) -> dict[int, str]:
    return {index: _TEXTS[name] for index, name in enumerate(names) if name in _TEXTS}


def test_bang_2_dong_tu_khoa_khong_chong_nhau():
    assert [slot["slotIndex"] for slot in planner.SLOTS] == [0, 1]
    assert planner.SLOTS[0]["slotName"].startswith("Trích lục vị trí khu đất")
    assert planner.SLOTS[1]["slotName"].startswith("Mẫu số 30. Văn bản đề nghị chấp thuận")
    for slot in planner.SLOTS:
        for keyword in slot["slotKeywords"]:
            owners = [other["slotIndex"] for other in planner.SLOTS if keyword in fold(other["slotName"])]
            assert owners == [slot["slotIndex"]], keyword


def test_moi_tep_dung_mot_dong_cccd_vao_giay_to_khac():
    names = ["cong-van.pdf", "cccd.pdf", "trich-do.pdf"]
    attachments, warnings, _ = planner.build_plan_items(_files(names), _texts(names))

    slots = [(item["fileName"], item["slotIndex"], item["detectedType"]) for item in attachments
             if item["target"] == "fixed-slot"]
    # Tiêu đề trích đo có cụm "chấp thuận cho nhận chuyển nhượng" nhưng vẫn vào dòng 1.
    assert slots == [("trich-do.pdf", 0, "trich_luc_vi_tri"), ("cong-van.pdf", 1, "van_ban_de_nghi")]
    assert all(item["tickRow"] for item in attachments if item["target"] == "fixed-slot")
    others = [item for item in attachments if item["target"] == "new"]
    assert [item["componentName"] for item in others] == ["Căn cước người đại diện - Lê Thị Mẫu"]
    assert warnings == []


def test_ban_ve_ocr_meo_van_la_trich_luc_giay_la_canh_bao():
    names = ["ban-ve-meo.pdf", "bien-lai.pdf"]
    attachments, warnings, _ = planner.build_plan_items(_files(names), _texts(names))

    assert attachments[0]["slotIndex"] == 0 and attachments[0]["detectedType"] == "trich_luc_vi_tri"
    assert attachments[1]["target"] == "new" and attachments[1]["componentName"] == "bien-lai"
    assert any("Giấy tờ khác" in w for w in warnings)
    assert any("Mẫu số 30" in w for w in warnings)  # thiếu văn bản đề nghị


def test_ocr_rong_doan_theo_ten_tep():
    names = ["Cv01mau_signed_1.pdf", "Sodomau_signed_2.pdf"]
    attachments, _, classified = planner.build_plan_items(_files(names), {})
    assert [(item["fileName"], item["slotIndex"]) for item in attachments] == [
        ("Sodomau_signed_2.pdf", 0), ("Cv01mau_signed_1.pdf", 1),
    ]
    assert {entry["source"] for entry in classified} == {"filename"}


def test_tep_qua_6mb_bi_loai_tep_sat_nguong_canh_bao():
    names = ["cong-van.pdf", "trich-do.pdf"]
    files = _files(names, {"cong-van.pdf": 7 * 1024 * 1024, "trich-do.pdf": 6_100_000})
    attachments, warnings, classified = planner.build_plan_items(files, _texts(names))

    assert [item["fileName"] for item in attachments] == ["trich-do.pdf"]
    assert classified[0]["skipped"] is True
    assert any("vượt giới hạn 6 MB" in w and "cong-van.pdf" in w for w in warnings)
    assert any("sát giới hạn 6 MB" in w and "6.100.000" in w for w in warnings)


# ---------------------------------------------------------------- attach (tách giấy tờ)

_PAGES = [_VB, _VB_2, _TRICH_DO]


def _pdf_data_url(pages: int) -> str:
    with fitz.open() as doc:
        for n in range(pages):
            doc.new_page().insert_text((72, 72), f"page {n + 1}")
        data = doc.tobytes()
    return "data:application/pdf;base64," + base64.b64encode(data).decode("ascii")


def _ocr_text(pages: list[str]) -> str:
    return "\n".join(f"───── Trang {n + 1}/{len(pages)} ─────\n{text}" for n, text in enumerate(pages))


@pytest.fixture
def gia_lap(monkeypatch):
    """OCR giả: tệp gộp ra chữ 3 trang (văn bản 2 trang + trích đo); tệp con lấy chữ nạp sẵn (ocr.preset_texts)."""
    original = _pdf_data_url(len(_PAGES))

    async def fake_ocr(files):
        return [{"name": f.get("name"),
                 "text": ocr.preset_text(f.get("dataUrl")) or (_ocr_text(_PAGES) if f.get("dataUrl") == original else "")}
                for f in files]

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    return [FileItem(name="ho_so_gop.pdf", type="application/pdf", dataUrl=original, role="other")]


def test_bat_tach_chia_dung_dong_khong_sot_trang(gia_lap, monkeypatch):
    async def fake_segment(pages_by_file):
        return {0: [(0, "Văn bản đề nghị"), (2, "Mảnh trích đo")]}

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", fake_segment)
    items = asyncio.run(dispatcher.plan(gia_lap, {"splitDocuments": True}))["attachments"]

    assert [(i["slotIndex"], i["fileIndex"], i["sourceSegments"]) for i in items] == [
        (0, 0, [{"fileIndex": 0, "pageIndexes": [2]}]),
        (1, 0, [{"fileIndex": 0, "pageIndexes": [0, 1]}]),
    ]
    pages = sorted(p for i in items for s in i["sourceSegments"] for p in s["pageIndexes"])
    assert pages == [0, 1, 2]


def test_bat_tach_gop_trang_noi_tiep_van_ban_bi_chia_nham(gia_lap, monkeypatch):
    async def fake_segment(pages_by_file):
        # Chạy thật 25/11: LLM mở giấy mới ở trang 2 văn bản (bắt đầu "8a. ...", không tiêu đề).
        return {0: [(0, "Công văn đề nghị"), (1, "Công văn đề nghị"), (2, "Mảnh trích đo")]}

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", fake_segment)
    items = asyncio.run(dispatcher.plan(gia_lap, {"splitDocuments": True}))["attachments"]
    assert [(i["slotIndex"], i["sourceSegments"]) for i in items] == [
        (0, [{"fileIndex": 0, "pageIndexes": [2]}]),
        (1, [{"fileIndex": 0, "pageIndexes": [0, 1]}]),
    ]


def test_gop_doan_khong_gop_can_cuoc_hoac_khong_lien_trang():
    from app.pipelines.to_chuc_kinh_te_nhan_chuyen_nhuong_qsdd_du_an_lai_chau.attach.dinh_kem_tach import (
        planner as planner_tach,
    )

    def item(doc_type, target, slot, pages):
        return {"target": target, "detectedType": doc_type, "slotIndex": slot,
                "sourceSegments": [{"fileIndex": 0, "pageIndexes": pages}]}

    out = planner_tach.gop_doan_lien_trang([
        item("identity", "new", None, [0]), item("identity", "new", None, [1]),  # hai thẻ → không gộp
        item("van_ban_de_nghi", "fixed-slot", 1, [2]), item("van_ban_de_nghi", "fixed-slot", 1, [4]),  # không liền trang
    ])
    assert len(out) == 4


def test_tat_tach_dinh_nguyen_tep(gia_lap, monkeypatch):
    async def must_not_split(pages_by_file):
        raise AssertionError("tắt tách thì không được chia trang")

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", must_not_split)
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"},
                    {"splitDocuments": True, "supportsSourceSegments": False}):
        items = asyncio.run(dispatcher.plan(gia_lap, options))["attachments"]
        assert len(items) == 1 and "sourceSegments" not in items[0], options
        assert items[0]["slotIndex"] == 1  # tệp gộp mở đầu bằng văn bản đề nghị


def test_tach_loi_quay_ve_dinh_nguyen_tep(gia_lap, monkeypatch):
    async def broken(pages_by_file):
        raise RuntimeError("LLM hỏng")

    monkeypatch.setattr(lao_cai_tach_giay_to, "_segment", broken)
    result = asyncio.run(dispatcher.plan(gia_lap, {"splitDocuments": True}))
    items = result["attachments"]
    assert len(items) == 1 and "sourceSegments" not in items[0] and items[0]["fileIndex"] == 0
    assert any("Tách giấy tờ" in e for e in result["errors"])


# ---------------------------------------------------------------- registry + trợ lý


def test_registry_va_ke_khai_links_cung_key():
    procedure = get_procedure(KEY)
    assert procedure["label"].startswith("[Lai Châu]")
    assert procedure["hasAttachmentStep"] is True and procedure["supportsSplitDocuments"] is True
    assert "6 MB" in procedure["uploadHint"]
    assert callable(get_pipeline(KEY)) and callable(get_attach_pipeline(KEY))

    link = next(item for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert link["code"] == "1.115591" and link["needsAgencySelect"] is True
    assert link["label"].startswith("Lai Châu - ")
    assert not link.get("provinceOnlyAgency") and not link.get("selectSo")
    # Trang nộp in "1.115591 - <tên thủ tục>": đủ mọi cụm nhận diện; bản Lào Cai 1.115681 cùng tên thì không khớp.
    page = ("Một phần 1.115591 - Tổ chức kinh tế nhận chuyển nhượng, thuê quyền sử dụng đất, nhận góp vốn bằng quyền sử "
            "dụng đất để thực hiện dự án đầu tư Nơi tiếp nhận hồ sơ")
    phrases = procedure["detect"]["textIncludes"]
    assert all(fold(p) in fold(page) for p in phrases)
    assert not all(fold(p) in fold(page.replace("1.115591", "1.115681")) for p in phrases)
    assert procedure["detect"]["urlScope"] == ["dichvucong.laichau.gov.vn"]


def test_tro_ly_cung_key_va_dung_pipeline_loi():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    procedure = handfree.get_procedure(KEY)
    assert procedure["provinceOnly"] == ["laichau"]
    assert procedure["laiChauFeeStep"] and procedure["agencyProvince"] == "Lai Châu"
    assert procedure["supportsSplitDocuments"] is True
    assert procedure["detect"] == get_procedure(KEY)["detect"]
    assert procedure["keKhaiUrl"] == next(item["url"] for item in KE_KHAI_LINKS if item["key"] == KEY)
    assert get_procedure(KEY)["label"] == "[Lai Châu] " + procedure["label"]
    assert handfree.get_pipeline(KEY) is get_pipeline(KEY)
    assert handfree.get_attach_pipeline(KEY) is get_attach_pipeline(KEY)
    assert handfree.is_allowed_in_province(procedure, "laichau")
    assert not handfree.is_allowed_in_province(procedure, "bacninh")
    assert "Lai Châu" not in procedure["shortLabel"]
    assert {doc["key"] for doc in procedure["requiredDocs"] if not doc.get("optional")} == {"van_ban", "trich_luc"}
    assert PROCEDURE_HMONG[KEY] and PROCEDURE_HINTS[KEY]
