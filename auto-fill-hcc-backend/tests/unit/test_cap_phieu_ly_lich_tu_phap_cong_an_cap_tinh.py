"""Cấp Phiếu lý lịch tư pháp (3.000333, Công an cấp tỉnh) — SurveyJS Cổng DVC quốc gia mới, radio Cá nhân / Khai hộ."""
import asyncio
import json
from pathlib import Path

from app.pipelines.cap_phieu_ly_lich_tu_phap_cong_an_cap_tinh.attach import planner as attach
from app.pipelines.cap_phieu_ly_lich_tu_phap_cong_an_cap_tinh.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.cap_phieu_ly_lich_tu_phap_cong_an_cap_tinh.attach.dinh_kem_tach import planner as tach
from app.pipelines.cap_phieu_ly_lich_tu_phap_cong_an_cap_tinh.process import mapper
from app.pipelines.cap_phieu_ly_lich_tu_phap_cong_an_cap_tinh.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.process.schemas import FileItem
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline
from app.services import ocr

KEY = "cap-phieu-ly-lich-tu-phap-cong-an-cap-tinh"
ROOT = Path(__file__).resolve().parents[2]
LINKS = ROOT / "app" / "procedures" / "data" / "ke_khai_links.json"
URL = "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bf7-bd79-75fb-a4c6-ba1bf85d20ad"

# Dữ liệu giả (không phải người thật).
NYC_ID = "001205000001"
NGUOI_KHAI_ID = "001080000002"
VALUES = {
    "ToKhai_UyQuyen": True,
    "NguoiKhai_HoTen": "Trần Văn Bình",
    "NguoiKhai_SoGiayTo": NGUOI_KHAI_ID,
    "NguoiKhai_SoDienThoai": "0912 345 678",
    "NguoiKhai_QuanHe": "Cha",
    "NYC_HoTen": "Trần Văn An",
    "NYC_TenGoiKhac": "Không",
    "NYC_GioiTinh": "Nam",
    "NYC_NgaySinh": "02/10/2005",
    "NYC_NoiSinh": {"quocGia": "Việt Nam", "tinh": "Lai Châu", "xa": "Tân Uyên"},
    "NYC_QuocTich": "Việt Nam",
    "NYC_DanToc": "Dao",
    "NYC_LoaiGiayTo": "Thẻ Căn cước",
    "NYC_SoGiayTo": NYC_ID,
    "NYC_NgayCap": "29/12/2025",
    "NYC_NoiCap": "Bộ Công an",
    "NYC_NoiThuongTru": {"quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "xa": "Xã Tân Uyên", "diaChi": "Bản A"},
    "NYC_NoiTamTru": {"quocGia": "Việt Nam", "tinh": "Tỉnh Bắc Ninh", "xa": "Phường Tiền Phong",
                      "chiTietDuoiXa": "Tổ dân phố B"},
    "NYC_SoDienThoai": "0912345678",
    "NYC_HoTenCha": "Trần Văn Bình",
    "NYC_HoTenMe": "Lò Thị Cúc",
    "YeuCauCDNCV": "Không",
    "SoLuongPhieu": "2",
}


def _fields(values: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in values.items()]


def _account(name: str, number: str) -> dict:
    return {"formContext": {"applicantFullname": name, "applicantIdentityNumber": number}}


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f for f in fields}


def _entry(key: str) -> dict:
    return next(p for p in PROCEDURES if p["key"] == key)


# ── Đăng ký ──

def test_registry_va_link_ke_khai_chon_tinh_tren_dvcqg():
    entry = _entry(KEY)
    assert entry["supportsSplitDocuments"] is True and entry["hasAttachmentStep"] is True
    assert entry["collectFormContext"] is True
    assert entry["detect"]["urlIncludes"] == ["formalityId=019d2bf7-bd79-75fb-a4c6-ba1bf85d20ad"]
    assert get_pipeline(KEY) is not None and get_attach_pipeline(KEY) is not None
    link = next(item for item in json.loads(LINKS.read_text(encoding="utf-8"))["links"] if item["key"] == KEY)
    assert (link["code"], link["url"]) == ("3.000333", URL)
    # Form SurveyJS nằm ngay trên DVCQG: chỉ chọn Tỉnh rồi Nộp trực tuyến, không sang cổng Bộ Công an.
    assert link["needsAgencySelect"] is True and link["provinceOnlyAgency"] is True
    assert "bcaSubmit" not in link and "directSubmit" not in link


def test_ten_o_khop_mapping():
    for name in ("citizenLoaiToKhai", "citizenField18", "citizenDateOfBirth", "citizenCauhoi1", "citizenField33",
                 "citizenDiaChiCuThe", "citizenPhone", "citizenSoDienThoai_NYC_UyQuyen",
                 "citizenMoiQuanHe_NYC_NguoiUyQuyen", "citizenSoGiayTo_NguoiUyQuyen", "QuocTich_NguoiUyQuyen",
                 "citizenNoiTamTru_MaXa_NguoiUyQuyen", "citizenLoaiPhieu", "YeuCauCDNCV"):
        assert name in UI_COMP_BY_NAME, name
    assert UI_COMP_BY_NAME["citizenLoaiToKhai"] == "sjs-radio"
    assert UI_COMP_BY_NAME["citizenNgayCap_NguoiUyQuyen"] == "sjs-date"
    assert {"NYC_HoTen", "NguoiKhai_QuanHe", "LoaiPhieu", "YeuCauCDNCV"} <= ALLOWED


# ── Điền ──

def test_khai_ho_tai_khoan_la_nguoi_khai():
    fields, warnings = mapper.enrich(_fields(VALUES), _account("TRẦN VĂN BÌNH", NGUOI_KHAI_ID))
    got = _by_name(fields)
    assert fields[0]["name"] == "citizenLoaiToKhai"          # radio chốt trước, cổng hiện khối theo nó
    assert (got["citizenLoaiToKhai"]["value"], got["citizenLoaiToKhai"]["code"]) == ("Khai hộ", "2")
    assert "default" not in got["citizenLoaiToKhai"]
    assert got["citizenSoDienThoai_NYC_UyQuyen"]["value"] == "0912345678"
    assert got["citizenMoiQuanHe_NYC_NguoiUyQuyen"]["value"] == "Cha"
    assert got["citizenLoaiGiayTo_NguoiUyQuyen"]["value"] == "Căn cước"
    assert got["citizenSoGiayTo_NguoiUyQuyen"]["value"] == NYC_ID
    assert got["citizenNgayCap_NguoiUyQuyen"]["value"] == "29/12/2025"
    assert got["citizenNoiCap_NguoiUyQuyen"]["value"] == "Bộ Công an"
    assert got["citizenHoVaTen_NguoiUyQuyen"]["value"] == "TRẦN VĂN AN"
    assert "citizenField32" not in got                         # tên gọi khác "Không" → để trống
    assert got["citizenGioiTinh_NguoiUyQuyen"]["value"] == "Nam"
    assert got["NoiSinhDangKy_QuocGia_NguoiUyQuyen"]["value"] == "Việt Nam"
    # Tỉnh/Xã nơi sinh (panel động, tên ô chưa biết): một cụm sjs-area, extension dò theo nhãn sau ô Quốc gia.
    birth = got["NoiSinhDangKy_NguoiUyQuyen"]
    assert (birth["comp"], birth["radio"]) == ("sjs-area", "NoiSinhDangKy_QuocGia_NguoiUyQuyen")
    assert "Lai Châu" in birth["value"]["tinh"] and "Tân Uyên" in birth["value"]["xa"]
    names = [f["name"] for f in fields]
    assert names.index("NoiSinhDangKy_QuocGia_NguoiUyQuyen") < names.index("NoiSinhDangKy_NguoiUyQuyen")
    assert got["QuocTich_NguoiUyQuyen"]["value"] == "Việt Nam" and "default" not in got["QuocTich_NguoiUyQuyen"]
    assert got["citizenDanToc_NguoiUyQuyen"]["value"] == "Dao"
    assert "Lai Châu" in got["citizenNoiThuongTru_MaTinh_NguoiUyQuyen"]["value"]
    assert got["citizenNoiThuongTru_DiaChiChiTiet_NguoiUyQuyen"]["value"] == "Bản A"
    assert "Bắc Ninh" in got["citizenNoiTamTru_MaTinh_NguoiUyQuyen"]["value"]
    assert "Tiền Phong" in got["citizenNoiTamTru_MaXa_NguoiUyQuyen"]["value"]
    assert got["citizenNoiTamTru_DiaChiChiTiet_NguoiUyQuyen"]["value"] == "Tổ dân phố B"
    assert got["citizenHoTenCha_NguoiUyQuyen"]["value"] == "TRẦN VĂN BÌNH"
    assert got["citizenHoVaTenMe_NguoiUyQuyen"]["value"] == "LÒ THỊ CÚC"
    assert got["citizenSoDienThoai_NguoiUyQuyen"]["value"] == "0912345678"
    # Ủy quyền cho người đã thành niên → chỉ Phiếu số 1 (ô vàng); tờ khai đánh "Không" ô cấm đảm nhiệm chức vụ.
    assert got["citizenLoaiPhieu"]["value"] == "Loại phiếu số 1" and got["citizenLoaiPhieu"]["default"] is True
    assert got["YeuCauCDNCV"]["value"] == "Không" and "default" not in got["YeuCauCDNCV"]
    # Khối Cá nhân không phát.
    assert not {"citizenField18", "citizenPhone", "citizenDateOfBirth"} & set(got)
    assert mapper.FEE_WARNING in warnings and mapper.RELATION_WARNING not in warnings
    assert any("'từ bản thứ 3' = 0" in w for w in warnings)
    # Tỉnh trước xã ở mọi cụm địa chỉ (xã nạp theo tỉnh).
    names = [f["name"] for f in fields]
    assert names.index("citizenNoiTamTru_MaTinh_NguoiUyQuyen") < names.index("citizenNoiTamTru_MaXa_NguoiUyQuyen")


def test_ca_nhan_tai_khoan_la_nguoi_yeu_cau_chi_phat_o_mo():
    fields, warnings = mapper.enrich(_fields(VALUES), _account("Trần Văn An", NYC_ID))
    got = _by_name(fields)
    assert (got["citizenLoaiToKhai"]["value"], got["citizenLoaiToKhai"]["code"]) == ("Cá nhân", "1")
    assert got["citizenField18"]["value"] == "Căn cước"
    assert got["citizenDateOfBirth"]["value"] == "02/10/2005"
    assert "Bắc Ninh" in got["citizenCauhoi1"]["value"] and "Tiền Phong" in got["citizenField33"]["value"]
    assert got["citizenDiaChiCuThe"]["value"] == "Tổ dân phố B"
    assert got["citizenPhone"]["value"] == "0912345678"
    assert "citizenTenGoiKhac_NYC" not in got
    # Ô khoá theo CSDLQG / khối Khai hộ không phát.
    assert not [n for n in got if n.endswith("_NguoiUyQuyen") or n.endswith("_NYC_UyQuyen")]
    assert "citizenLoaiPhieu" not in got                       # cá nhân: giữ lựa chọn cổng để sẵn
    assert mapper.RELATION_WARNING not in warnings


def test_khong_co_moc_tai_khoan_theo_mau_to_khai():
    got = _by_name(mapper.enrich(_fields(VALUES), {})[0])
    assert got["citizenLoaiToKhai"]["value"] == "Khai hộ" and got["citizenLoaiToKhai"]["default"] is True
    # Không có mốc → điện thoại / quan hệ của tài khoản lấy theo người khai trên tờ khai.
    assert got["citizenMoiQuanHe_NYC_NguoiUyQuyen"]["value"] == "Cha"
    personal = {k: v for k, v in VALUES.items() if not k.startswith("NguoiKhai_")} | {"ToKhai_UyQuyen": False}
    got = _by_name(mapper.enrich(_fields(personal), {})[0])
    assert got["citizenLoaiToKhai"]["value"] == "Cá nhân" and got["citizenLoaiToKhai"]["default"] is True


def test_khai_ho_nguoi_khai_khac_tai_khoan_khong_lay_sdt_quan_he():
    fields, warnings = mapper.enrich(_fields(VALUES), _account("Nguyễn Thị Dung", "001190000003"))
    got = _by_name(fields)
    assert got["citizenLoaiToKhai"]["value"] == "Khai hộ"
    assert "citizenSoDienThoai_NYC_UyQuyen" not in got and "citizenMoiQuanHe_NYC_NguoiUyQuyen" not in got
    assert mapper.RELATION_WARNING in warnings
    assert got["citizenHoVaTen_NguoiUyQuyen"]["value"] == "TRẦN VĂN AN"


def test_loai_phieu_theo_to_khai_va_cdncv_mac_dinh():
    values = {**VALUES, "LoaiPhieu": "2", "YeuCauCDNCV": ""}
    got = _by_name(mapper.enrich(_fields(values), _account("Trần Văn An", NYC_ID))[0])
    assert got["citizenLoaiPhieu"]["value"] == "Loại phiếu số 2" and "default" not in got["citizenLoaiPhieu"]
    assert got["YeuCauCDNCV"]["value"] == "Không" and got["YeuCauCDNCV"]["default"] is True


def test_ngay_cap_noi_cap_theo_mat_sau_the_mrz():
    ocr_text = ("Ngày, tháng, năm cấp / Date of issue: 15/03/2024\nCỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI\n"
                f"IDVNM2050000011{NYC_ID}<<6\n")
    got = _by_name(mapper.enrich(_fields(VALUES), {**_account("TRẦN VĂN BÌNH", NGUOI_KHAI_ID),
                                                    "_ocr_text": ocr_text})[0])
    assert got["citizenNgayCap_NguoiUyQuyen"]["value"] == "15/03/2024"
    assert got["citizenNoiCap_NguoiUyQuyen"]["value"] == "Cục Cảnh sát QLHC về TTXH"
    assert got["citizenLoaiGiayTo_NguoiUyQuyen"]["value"] == "Căn cước công dân"


# ── Đính kèm ──

_PAGES = ["TỜ KHAI YÊU CẦU CẤP PHIẾU LÝ LỊCH TƯ PHÁP", "Mục đích yêu cầu cấp Phiếu", "CĂN CƯỚC",
          "GIẤY XÁC NHẬN HỘ NGHÈO", "Trang ký xác nhận"]
_OCR = "\n".join(f"───── Trang {i + 1}/{len(_PAGES)} ─────\n{t}" for i, t in enumerate(_PAGES))


def _files(*names):
    return [FileItem(name=n, type="application/pdf", dataUrl="data:,", role="") for n in names]


def _patch_ocr(monkeypatch, text=_OCR):
    async def fake_ocr(files):
        return [{"text": text} for _ in files]

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)


def test_khong_tach_dinh_moi_tep_vao_dong_duy_nhat_mien_giam_dau_ghep_hai_mat(monkeypatch):
    _patch_ocr(monkeypatch, "GIẤY TỜ")

    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": [
            {"index": 0, "docType": "to_khai", "documentName": "Tờ khai yêu cầu cấp Phiếu lý lịch tư pháp"},
            {"index": 1, "docType": "can_cuoc", "documentName": "Căn cước", "matThe": "truoc", "chuThe": "Trần Văn An"},
            {"index": 2, "docType": "can_cuoc", "documentName": "Căn cước", "matThe": "sau", "chuThe": "TRAN VAN AN"},
            {"index": 3, "docType": "mien_giam_phi", "documentName": "Giấy xác nhận hộ nghèo"},
        ]})

    monkeypatch.setattr(khong_tach.client, "chat", fake_chat)
    for options in ({}, {"splitDocuments": "true"}, None):
        res = asyncio.run(attach.plan(_files("tokhai.pdf", "mt.jpg", "ms.jpg", "hongheo.pdf"), options))
        got = [(i["fileIndex"], i["documentName"], i.get("sourceFileIndexes")) for i in res["attachments"]]
        assert got == [
            (3, "Giấy xác nhận hộ nghèo", None),
            (0, "Tờ khai yêu cầu cấp Phiếu lý lịch tư pháp", None),
            (1, "CCCD Trần Văn An", [1, 2]),
        ]
        for item in res["attachments"]:
            assert item["target"] == "fixed-slot" and item["slotName"] == khong_tach.ROW["slotName"]
            assert "sourceSegments" not in item


def test_khong_tach_llm_loi_van_dinh_du_tep(monkeypatch):
    _patch_ocr(monkeypatch, "GIẤY TỜ")

    async def fake_chat(*_a, **_k):
        raise RuntimeError("llm hỏng")

    monkeypatch.setattr(khong_tach.client, "chat", fake_chat)
    res = asyncio.run(attach.plan(_files("cccd.pdf", "tokhai.pdf"), {}))
    assert [i["documentName"] for i in res["attachments"]] == ["cccd", "tokhai"]


def test_tach_moi_giay_mot_muc_khong_sot_trang(monkeypatch):
    _patch_ocr(monkeypatch)

    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pages": [1, 2], "docType": "to_khai", "documentName": "Tờ khai"},
            {"fileIndex": 0, "pages": [3], "docType": "can_cuoc", "documentName": "Căn cước"},
            {"fileIndex": 0, "pages": [4], "docType": "mien_giam_phi", "documentName": "Giấy xác nhận hộ nghèo"},
            # trang 5 LLM bỏ sót → gộp vào giấy liền trước (giấy hộ nghèo), không mất trang.
        ]})

    monkeypatch.setattr(tach.client, "chat", fake_chat)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    assert [(i["documentName"], i["sourceSegments"]) for i in res["attachments"]] == [
        ("Giấy xác nhận hộ nghèo", [{"fileIndex": 0, "pageIndexes": [3, 4]}]),
        ("Tờ khai", [{"fileIndex": 0, "pageIndexes": [0, 1]}]),
        ("Căn cước", [{"fileIndex": 0, "pageIndexes": [2]}]),
    ]
    covered = sorted(p for i in res["attachments"] for s in i["sourceSegments"] for p in s["pageIndexes"])
    assert covered == [0, 1, 2, 3, 4]
    assert all(i["slotName"] == khong_tach.ROW["slotName"] for i in res["attachments"])


def test_tach_tep_mot_giay_thi_dinh_nguyen_tep(monkeypatch):
    _patch_ocr(monkeypatch, "GIẤY XÁC NHẬN HỘ NGHÈO")

    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pages": [1], "docType": "mien_giam_phi", "documentName": "Giấy xác nhận hộ nghèo"},
        ]})

    monkeypatch.setattr(tach.client, "chat", fake_chat)
    res = asyncio.run(attach.plan(_files("hongheo.pdf"), {"splitDocuments": True}))
    assert len(res["attachments"]) == 1 and "sourceSegments" not in res["attachments"][0]


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    _patch_ocr(monkeypatch)

    async def fake_chat(messages, **_):
        if "TỪNG TRANG" in messages[0]["content"]:
            raise RuntimeError("llm hỏng")
        return '{"documents":[{"index":0,"docType":"mien_giam_phi","documentName":"Giấy xác nhận hộ nghèo"}]}'

    monkeypatch.setattr(tach.client, "chat", fake_chat)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    item = res["attachments"][0]
    assert item["slotName"] == khong_tach.ROW["slotName"] and "sourceSegments" not in item
    assert any("(tách)" in e for e in res["errors"])


# ── Trợ lý người dân ──

def test_tro_ly_cung_key_trang_mot_trang_chi_chon_tinh_toan_quoc():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    proc = handfree.get_procedure(KEY)
    assert proc["detect"] == _entry(KEY)["detect"]
    assert proc["flowProfile"] == "tu-phap-moi" and proc["singlePageDossier"] is True
    assert proc["needsAgencySelect"] is True and proc["agencyProvinceOnly"] is True
    assert proc["supportsSplitDocuments"] is True and proc["keKhaiUrl"] == URL
    assert "provinceOnly" not in proc and handfree._HOAN_THIEN_THEO_TINH[KEY] == handfree._TAT_CA
    assert KEY in PROCEDURE_HINTS and KEY in PROCEDURE_HMONG
    assert field_review.get(KEY) is not None
