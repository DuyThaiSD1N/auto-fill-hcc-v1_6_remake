"""Cấp giấy chứng nhận đủ điều kiện kinh doanh dược (1.014076) — cổng Bộ Y tế, nộp tại Sở Y tế.

Dữ liệu trong test là giả định, không trùng bộ hồ sơ mẫu.
"""
import asyncio
import json
from pathlib import Path

from app.pipelines.cap_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.attach import planner as attach
from app.pipelines.cap_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.cap_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.attach.dinh_kem_tach import planner as tach
from app.pipelines.cap_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.process import mapper, runner
from app.pipelines.cap_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.process.schemas import FileItem
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline
from app.services import ocr
from app.services.llm import client as llm_client

KEY = "cap-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te"
ROOT = Path(__file__).resolve().parents[2]
LINKS = ROOT / "app" / "procedures" / "data" / "ke_khai_links.json"

OWNER_ID = "001000000101"
SUBMITTER_ID = "034000000202"
OWNER_ACCOUNT = {"applicantFullname": "NGUYỄN VĂN AN", "applicantIdentityNumber": OWNER_ID}
OTHER_ACCOUNT = {"applicantFullname": "TRẦN THỊ BÌNH", "applicantIdentityNumber": SUBMITTER_ID}
OWNER = {
    "ChuHoSo_HoTen": "Ông Nguyễn Văn An – Giám đốc",
    "ChuHoSo_NgaySinh": "02/03/1981",
    "ChuHoSo_GioiTinh": "Nam",
    "ChuHoSo_SoDinhDanh": OWNER_ID,
    "ChuHoSo_NgayCap": "05/06/2021",
    "ChuHoSo_NoiCap": "CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI",
    "ChuHoSo_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Thành phố Hà Nội", "xa": "Phường Yên Hòa",
                          "diaChi": "Số 1 ngõ 2 phố Mẫu"},
    "ChuHoSo_DienThoai": "024 3000 0000 - Di động: 0912 000 111",
    "ChuHoSo_Email": "coso.mau@example.com",
    "ChuHoSo_Fax": "024 3000 0001",
    "CoSo_Ten": "CÔNG TY TNHH DƯỢC PHẨM MẪU",
    "CoSo_MaSoDoanhNghiep": "0100000001",
    "CoSo_LoaiHinh": "Cơ sở bán buôn thuốc, nguyên liệu làm thuốc",
    "CoSo_DiaDiemKinhDoanh": "Số 9 đường Mẫu, Xã Thanh Trì, Thành phố Hà Nội",
}
SUBMITTER = {
    "NguoiNop_HoTen": "TRẦN THỊ BÌNH",
    "NguoiNop_NgaySinh": "03/12/2003",
    "NguoiNop_GioiTinh": "Nữ",
    "NguoiNop_SoDinhDanh": SUBMITTER_ID,
    "NguoiNop_NgayCap": "01/07/2026",
    "NguoiNop_NoiCap": "Bộ Công an",
    "NguoiNop_ThuongTru": {"quocGia": "Việt Nam", "tinh": "Tỉnh Hưng Yên", "xa": "Xã Đông Quan", "diaChi": "Thôn A"},
}


def _entry(key: str) -> dict:
    return next(p for p in PROCEDURES if p["key"] == key)


def _enrich(values: dict, account: dict | None = OWNER_ACCOUNT, **options):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    opts = {**options, **({"formContext": account} if account else {})}
    out, warnings = mapper.enrich(fields, opts)
    return {f["name"]: f for f in out}, warnings


# ── Registry ──

def test_key_trung_link_va_folder_va_registry():
    link = next(i for i in json.loads(LINKS.read_text(encoding="utf-8"))["links"] if i["key"] == KEY)
    assert link["code"] == "1.014076" and link["selectSo"] is True
    assert (ROOT / "app" / "pipelines" / KEY.replace("-", "_")).is_dir()
    entry = _entry(KEY)
    assert entry["supportsSplitDocuments"] is True and entry["hasAttachmentStep"] is True
    assert entry["mode"] == "agent"
    assert get_pipeline(KEY) is runner.run and get_attach_pipeline(KEY) is attach.plan


def test_cum_nhan_dien_khong_lan_thu_tuc_cap_lai_dieu_chinh():
    phrase = _entry(KEY)["detect"]["textIncludes"][0]
    sister = _entry("cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te")
    assert phrase not in sister["label"].lower()
    assert phrase in _entry(KEY)["label"].lower()
    # Trùng trang thì cụm dài hơn của 1.014104 thắng (extension chọn tổng độ dài cụm lớn nhất).
    assert len(sister["detect"]["textIncludes"][0]) > len(phrase)


def test_ten_o_dung_ban_mapping():
    assert set(UI_COMP_BY_NAME) >= {"data[ownerFullname]", "data[ownerFax]", "data[ghiChu]", "data[isOwnerDossierCheck]"}
    assert "data[chonDoiTuong]" not in UI_COMP_BY_NAME  # khoá "Cá nhân"
    assert {"ChuHoSo_HoTen", "ChuHoSo_Fax", "CoSo_Ten", "NguoiNop_SoDinhDanh"} <= ALLOWED


# ── Điền form (mapper) ──

def test_tu_nop_phan_i_va_ii_theo_nguoi_dai_dien():
    by, warnings = _enrich(OWNER)
    assert "data[fullname]" not in by and "data[identityNumber]" not in by  # khoá theo tài khoản
    assert by["data[birthday]"]["value"] == "02/03/1981"
    assert by["data[phoneNumber]"]["value"] == "0912000111"  # số bàn bị bỏ
    assert by["data[isOwnerDossierCheck]"]["value"] is False
    assert by["data[ownerFullname]"]["value"] == "Nguyễn Văn An"
    assert by["data[ownerIdentityNumber]"]["value"] == OWNER_ID
    assert by["data[ownerIdIssuePlace]"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert by["data[ownerProvince]"]["value"] == "Thành phố Hà Nội"
    assert by["data[ownerDistrict]"]["value"] == "Phường Yên Hòa"
    assert by["data[ownerPhoneNumber]"]["value"] == "0912000111"
    assert by["data[ownerEmail]"]["value"] == "coso.mau@example.com"
    assert by["data[ownerFax]"]["value"] == "024 3000 0001"
    assert by["data[ownerNation]"]["value"] == "Việt Nam"
    note = by["data[ghiChu]"]["value"]
    assert "CÔNG TY TNHH DƯỢC PHẨM MẪU" in note and "0100000001" in note and "Xã Thanh Trì" in note
    assert not warnings


def test_nop_thay_phan_i_lay_cccd_nguoi_nop():
    by, warnings = _enrich({**OWNER, **SUBMITTER}, OTHER_ACCOUNT)
    assert by["data[birthday]"]["value"] == "03/12/2003"
    assert by["data[gender]"]["value"] == "Nữ"
    assert by["data[province]"]["value"] == "Tỉnh Hưng Yên"
    assert "data[phoneNumber]" not in by  # SĐT trên Đơn là của cơ sở
    assert "data[fullname]" not in by
    assert by["data[ownerFullname]"]["value"] == "Nguyễn Văn An"
    assert any("số điện thoại người nộp" in w for w in warnings)


def test_chi_nhan_so_di_dong():
    assert mapper._mobile("024 3000 0000") is None
    assert mapper._mobile("024 3000 0000 – Di động: 0912 000 111") == "0912000111"
    assert mapper._mobile("+84 912 000 111") == "0912000111"
    assert mapper._mobile("0912-000-111") == "0912000111"


def test_lay_nguoi_nop_theo_to_khai_mo_khoa_khi_khac_tai_khoan():
    by, warnings = _enrich({**OWNER, **SUBMITTER}, OTHER_ACCOUNT, submitterMode="owner_as_submitter")
    assert by["data[fullname]"] == {"name": "data[fullname]", "comp": "dom-input", "value": "Nguyễn Văn An",
                                    "enableInput": True}
    assert by["data[identityNumber]"]["value"] == OWNER_ID and by["data[identityNumber]"]["enableInput"] is True
    assert by["data[birthday]"]["value"] == "02/03/1981"  # theo người đại diện, không theo CCCD người nộp
    assert by["data[province]"]["value"] == "Thành phố Hà Nội"
    assert by["data[phoneNumber]"]["value"] == "0912000111"
    assert by["data[ownerFullname]"]["value"] == "Nguyễn Văn An"
    assert any("Lấy người nộp theo tờ khai" in w and "khác tài khoản" in w for w in warnings)
    assert any("CCCD của người khác" in w for w in warnings)


def test_lay_nguoi_nop_theo_to_khai_thieu_ngay_sinh_thi_xoa_o_cua_tai_khoan():
    values = {k: v for k, v in OWNER.items() if k != "ChuHoSo_NgaySinh"}
    by, _ = _enrich(values, OTHER_ACCOUNT, submitterMode="owner_as_submitter")
    assert by["data[birthday]"]["clear"] is True and by["data[birthday]"]["value"] == ""


def test_lay_nguoi_nop_theo_to_khai_trung_tai_khoan_khong_mo_khoa():
    by, warnings = _enrich(OWNER, OWNER_ACCOUNT, submitterMode="owner_as_submitter")
    assert "data[fullname]" not in by and "data[identityNumber]" not in by
    assert by["data[birthday]"]["value"] == "02/03/1981"
    assert not warnings


def test_lay_nguoi_nop_theo_to_khai_khong_neo_cccd_tai_khoan():
    docs = [{"text": "CĂN CƯỚC CÔNG DÂN Citizen Identity Card TRẦN THỊ BÌNH 034000000202"}]
    on = asyncio.run(runner._submitter_context(docs, {"formContext": OTHER_ACCOUNT,
                                                       "submitterMode": "owner_as_submitter"}))
    off = asyncio.run(runner._submitter_context(docs, {"formContext": OTHER_ACCOUNT}))
    assert on == "" and "co_giay_to" in off


# ── Đính kèm ──

_PAGES = [
    ("CÔNG TY TNHH MẪU DANH MỤC HỒ SƠ Đề nghị cấp Giấy chứng nhận đủ điều kiện kinh doanh dược STT Thành phần hồ sơ "
     "1 Đơn đề nghị cấp Giấy chứng nhận đủ điều kiện kinh doanh dược 2 Giấy chứng nhận đăng ký doanh nghiệp "
     "5 Chứng chỉ hành nghề dược"),
    "Trường dữ liệu Giá trị Có ở giấy tờ Người chịu trách nhiệm chuyên môn Số CCHN dược",
    ("Mẫu số 10 CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM ĐƠN ĐỀ NGHỊ Cấp Giấy chứng nhận đủ điều kiện kinh doanh dược "
     "Kính gửi: Sở Y tế Số CCHN Dược"),
    "Phạm vi kinh doanh: thuốc dạng phối hợp có chứa dược chất gây nghiện NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT",
    "SỞ TÀI CHÍNH PHÒNG ĐĂNG KÝ KINH DOANH GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP Mã số doanh nghiệp",
    "Địa chỉ thường trú TRƯỞNG PHÒNG",
    "CÔNG TY TNHH MẪU TÀI LIỆU KỸ THUẬT Về cơ sở vật chất, tài liệu chuyên môn kỹ thuật và nhân sự (GDP)",
    "III. CƠ SỞ VẬT CHẤT Kho bảo quản",
    "Mẫu số 11 TÀI LIỆU THUYẾT MINH CƠ SỞ ĐÁP ỨNG BIỆN PHÁP VỀ AN NINH",
    "SỞ Y TẾ Số: 00001/CCHN-D-SYT CHỨNG CHỈ HÀNH NGHỀ DƯỢC",
    "CĂN CƯỚC CÔNG DÂN Citizen Identity Card Số 001000000101",
]
_OCR = "\n".join(f"───── Trang {i + 1}/{len(_PAGES)} ─────\n{t}" for i, t in enumerate(_PAGES))
_SPLIT = {
    "tep": [{"fileIndex": 0, "tieuDeTrang": ["Danh mục hồ sơ", "", "Đơn đề nghị", "", "Giấy chứng nhận đăng ký doanh "
             "nghiệp", "", "Tài liệu kỹ thuật", "", "Tài liệu thuyết minh", "Chứng chỉ hành nghề dược", "Căn cước"]}],
    "documents": [
        {"fileIndex": 0, "pages": [1, 2], "docType": "danh_muc_ho_so", "documentName": "Danh mục hồ sơ"},
        {"fileIndex": 0, "pages": [3, 4], "docType": "don_de_nghi", "documentName": "Đơn đề nghị"},
        {"fileIndex": 0, "pages": [5, 6], "docType": "giay_to_phap_ly", "documentName": "Giấy chứng nhận ĐKDN"},
        {"fileIndex": 0, "pages": [7], "docType": "tai_lieu_ky_thuat", "documentName": "Tài liệu kỹ thuật"},
        # trang 8 LLM bỏ sót → gộp vào giấy liền trước (tài liệu kỹ thuật), không mất trang.
        {"fileIndex": 0, "pages": [9], "docType": "thuyet_minh_an_ninh", "documentName": "Tài liệu thuyết minh"},
        {"fileIndex": 0, "pages": [10], "docType": "cchn_duoc", "documentName": "Chứng chỉ hành nghề dược"},
        {"fileIndex": 0, "pages": [11], "docType": "cccd", "documentName": "Căn cước công dân"},
    ],
}


def _files(*names):
    return [FileItem(name=n, type="application/pdf", dataUrl="data:,", role="") for n in names]


def _patch(monkeypatch, texts, chat):
    async def fake_ocr(files):
        return [{"text": texts[i]} for i in range(len(files))]

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)
    monkeypatch.setattr(llm_client, "chat", chat)


def test_tach_file_dung_dong_va_khong_sot_trang(monkeypatch):
    async def fake_chat(messages, **_):
        return json.dumps(_SPLIT, ensure_ascii=False)

    _patch(monkeypatch, [_OCR], fake_chat)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    got = [(i["componentIndex"], i["documentName"], i["detectedType"],
            [s["pageIndexes"] for s in i.get("sourceSegments", [])]) for i in res["attachments"]]
    assert got == [
        (1, "Đơn đề nghị", "don_de_nghi", [[2, 3]]),
        # Danh mục hồ sơ + tài liệu kỹ thuật: MỘT tệp ở dòng 2, ghép đúng trang (kể cả trang 8 LLM bỏ sót).
        (2, "Danh mục hồ sơ_ tài liệu", "tai_lieu_ky_thuat", [[0, 1], [6, 7]]),
        (3, "Đăng ký KD", "giay_to_phap_ly", [[4, 5]]),
        (4, "Tài liệu thuyết minh", "thuyet_minh_an_ninh", [[8]]),
        (5, "Chứng chỉ dược", "cchn_duoc", [[9]]),
        (1, "Căn cước công dân", "cccd", [[10]]),
    ]
    assert all(i["target"] == "attp-row" and i["loaiBan"] == "Bản chính" for i in res["attachments"])
    pages = sorted(p for i in res["attachments"] for s in i["sourceSegments"] for p in s["pageIndexes"])
    assert pages == list(range(len(_PAGES)))
    assert not [e for e in res["errors"] if "chưa có" in e]
    assert any("hoso.pdf (trang 11)" in e for e in res["errors"])


def test_tat_tach_thi_dinh_nguyen_tep(monkeypatch):
    calls = []

    async def fake_chat(messages, **_):
        calls.append(messages)
        return '{"documents":[{"fileIndex":4,"docTypes":["cchn_duoc"],"documentName":"Chứng chỉ"}]}'

    texts = [_PAGES[2], _PAGES[0] + "\n" + _PAGES[6], _PAGES[4], _PAGES[8], "Văn bản scan mờ không có tiêu đề"]
    _patch(monkeypatch, texts, fake_chat)
    names = ("don.pdf", "danhmuc_kythuat.pdf", "dkkd.pdf", "mau11.pdf", "cchn.pdf")
    for options in ({}, {"splitDocuments": "true"}, None):
        res = asyncio.run(attach.plan(_files(*names), options))
        got = [(i["componentIndex"], i["fileName"], i["documentName"]) for i in res["attachments"]]
        assert got == [(1, "don.pdf", "Đơn đề nghị"), (2, "danhmuc_kythuat.pdf", "Danh mục hồ sơ_ tài liệu"),
                       (3, "dkkd.pdf", "Đăng ký KD"), (4, "mau11.pdf", "Tài liệu thuyết minh"),
                       (5, "cchn.pdf", "Chứng chỉ dược")]
        assert all("sourceSegments" not in i and "sourceFileIndexes" not in i for i in res["attachments"])
    # Chỉ tệp không có tiêu đề mới hỏi LLM.
    assert all('"fileIndex": 4' in c[1]["content"] and '"fileIndex": 0' not in c[1]["content"] for c in calls)


def test_tat_tach_tep_gop_dinh_vao_moi_dong_no_chua(monkeypatch):
    async def fake_chat(*_a, **_k):
        raise AssertionError("tiêu đề đã nhận đủ, không hỏi LLM")

    _patch(monkeypatch, [_OCR], fake_chat)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {}))
    assert [i["componentIndex"] for i in res["attachments"]] == [1, 2, 3, 4, 5]
    assert all(i["fileIndex"] == 0 and "sourceSegments" not in i for i in res["attachments"])
    assert any("đính nguyên tệp vào cả dòng" in e for e in res["errors"])


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    async def fake_chat(messages, **_):
        if "TỪNG TRANG" in messages[0]["content"]:
            raise RuntimeError("llm hỏng")
        return '{"documents":[]}'

    _patch(monkeypatch, [_PAGES[2], _PAGES[9]], fake_chat)
    res = asyncio.run(attach.plan(_files("don.pdf", "cchn.pdf"), {"splitDocuments": True}))
    assert [(i["componentIndex"], i["fileName"]) for i in res["attachments"]] == [(1, "don.pdf"), (5, "cchn.pdf")]
    assert all("sourceSegments" not in i for i in res["attachments"])
    assert any("(tách)" in e for e in res["errors"])
    # Thiếu dòng 2, 3 + có thuốc kiểm soát đặc biệt? (không) → báo thiếu đúng dòng.
    assert any("(dòng 2)" in e for e in res["errors"]) and any("(dòng 3)" in e for e in res["errors"])


def test_tieu_de_trang_danh_muc_khong_nhan_nham_giay_ke_ten():
    assert khong_tach.page_type(_PAGES[0]) == "danh_muc_ho_so"
    assert khong_tach.page_type(_PAGES[2]) == "don_de_nghi"
    assert khong_tach.page_type(_PAGES[9]) == "cchn_duoc"
    assert khong_tach.page_type(_PAGES[1]) is None


def test_thieu_thuyet_minh_ma_co_thuoc_kiem_soat_dac_biet_thi_canh_bao():
    segments = [{"fileIndex": 0, "pages": None, "doc": {"docType": "don_de_nghi"}}]
    _, warnings = tach.build_split_items(["don.pdf"], segments, {0: [_PAGES[2], _PAGES[3]]})
    assert any("Mẫu số 11, dòng 4" in w for w in warnings)


# ── Trợ lý người dân ──

def test_tro_ly_cung_key_luong_bo_y_te_cap_so():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat import script_mong
    from app.channels.handfree.chat.field_review import registry as field_review
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS

    proc = handfree.get_procedure(KEY)
    assert proc["flowProfile"] == "xay-dung" and proc["supportsSplitDocuments"] is True
    assert proc["agencyProvinceOnly"] is True and proc["agencySoFirst"] is True
    assert proc["agencyDeptLabel"] == "Sở Y tế"
    assert "maThuTuc=1.014076" in proc["detect"]["urlIncludes"]
    link = next(i for i in json.loads(LINKS.read_text(encoding="utf-8"))["links"] if i["key"] == KEY)
    assert proc["keKhaiUrl"] == link["url"]
    assert "provinceOnly" not in proc
    assert handfree._HOAN_THIEN_THEO_TINH[KEY] == handfree._TAT_CA
    assert KEY in PROCEDURE_HINTS
    assert KEY in script_mong.PROCEDURE_HMONG
    config = field_review.get(KEY)
    assert config["required"] == () and config["noAsk"] == ("ghiChu",)
