"""Cấp Giấy XNTTHN trên Cổng DVC quốc gia mới: mapper ra câu hỏi SurveyJS + planner đính kèm."""

import re
from pathlib import Path

import pytest

from app.pipelines.xac_nhan_tthn_dvc_moi.attach.dinh_kem_khong_tach import planner
from app.pipelines.xac_nhan_tthn_dvc_moi.process import mapper
from app.pipelines.xac_nhan_tthn_dvc_moi.process.schema import UI_COMP_BY_NAME

SNAPSHOT = Path(__file__).resolve().parents[3] / "html mới" / "tình trạng hôn nhân" / "tình trạng hôn nhân form mới.html"
ACCOUNT = {"applicantFullname": "NGUYEN VAN B", "applicantIdentityNumber": "001090000002"}
BASE = {
    "NguoiDuocCap_HoTen": "Nguyễn Văn B",
    "NguoiDuocCap_NgaySinh": "5/3/1990",
    "NguoiDuocCap_SoDinhDanh": "001090000002",
    "NguoiDuocCap_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "Phường Hoàn Kiếm", "diaChi": "Số 1"},
}


def _context(relation="Bản thân", loai="khac", noi_dung="Bổ sung hồ sơ vay vốn", chac="cao", co_trong_ho_so="Có"):
    return (
        "<phan_vai_da_xac_dinh>\n"
        f"<nguoi_nop>\nCó trong hồ sơ: {co_trong_ho_so}\n</nguoi_nop>\n"
        "<nguoi_duoc_cap>\nHọ tên: NGUYEN VAN B\n</nguoi_duoc_cap>\n"
        f"<quan_he>\nKết luận: {relation}\n</quan_he>\n"
        f"<muc_dich>\nLoại: {loai}\nNội dung: {noi_dung}\nĐộ chắc: {chac}\n</muc_dich>\n"
        "</phan_vai_da_xac_dinh>"
    )


def _enrich(values: dict, context: str = "", account=ACCOUNT):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    out, warnings = mapper.enrich(fields, {"formContext": account, "_reasoning_context": context})
    return {f["name"]: f for f in out}, warnings


def test_ban_than_tra_cuu_dan_cu_va_dia_chi():
    v, warnings = _enrich(BASE, _context())
    assert (v["citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan"]["code"], warnings) == ("1", [])
    assert v["citizenNDKNgaythangnamsinh"]["code"] == "1990-03-05"
    assert all(v[n].get("lookup") for n in
               ("citizenNDKHochudemtenngdccap", "citizenNDKNgaythangnamsinh", "citizenNDKSoDinhDanh"))
    assert v["citizenNDKnoicutru"]["code"] == "1" and v["citizenNDKLoaicutru"]["default"] is True
    assert "citizenField13" not in v
    assert v["citizenNycNoicutru"]["code"] == "1" and v["citizenNycNoicutru"]["default"] is True


def test_quan_he_khac_ghi_o_moi_quan_he():
    v, _ = _enrich(BASE, _context(relation="Người được ủy quyền"))
    assert v["citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan"]["code"] == "2"
    assert v["citizenField13"]["value"] == "Người được ủy quyền"


def test_khong_ket_luan_quan_he_thi_doi_chieu_tai_khoan():
    v, warnings = _enrich(BASE, "")
    assert v["citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan"]["default"] is True
    v, warnings = _enrich({**BASE, "NguoiDuocCap_HoTen": "Trần Thị C", "NguoiDuocCap_SoDinhDanh": "001190000003",
                           "NguoiDuocCap_NgaySinh": "01/01/1999"}, "")
    assert v["citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan"]["code"] == "2" and warnings


def test_ma_tinh_trang_theo_cong_moi():
    # Cổng mới: 1 = chưa đăng ký, 2 = đang có vợ/chồng (ngược eForm cũ).
    v, _ = _enrich({**BASE, "TinhTrangHonNhan": "chua_ket_hon"}, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "1"
    v, _ = _enrich({**BASE, "TinhTrangHonNhan": "co_vo_chong", "Marriage_SpouseName": "Trần Thị C",
                    "Marriage_Number": "12", "Marriage_Date": "1/2/2020", "Marriage_Agency": "UBND xã A"}, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "2"
    assert v["citizenHovatencuavochongnguoicoyeucauxacnhantinhtranghonnhan"]["value"] == "TRẦN THỊ C"
    assert (v["citizenField40"]["value"], v["citizenField41"]["code"]) == ("12", "2020-02-01")


def test_khong_co_to_khai_chi_doc_duoc_ten_vo_chong_thi_dang_co_vo_chong():
    # Hồ sơ chỉ CCCD + phiếu tra CSDL dân cư: không có mã tình trạng, chỉ có tên vợ/chồng hiện tại.
    v, _ = _enrich({**BASE, "Marriage_SpouseName": "Trần Thị C"}, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "2"
    assert v["citizenHovatencuavochongnguoicoyeucauxacnhantinhtranghonnhan"]["value"] == "TRẦN THỊ C"


def test_chua_ket_hon_nhung_co_ban_an_thi_ly_hon_theo_van_ban():
    values = {**BASE, "TinhTrangHonNhan": "chua_ket_hon", "DivorceDecision_Number": "5/2011/HNGĐ-ST",
              "DivorceDecision_Date": "15/07/2021", "BanAn_Date": "15/07/2011", "BanAn_Agency": "Tòa án nhân dân A"}
    v, _ = _enrich(values, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "3"
    assert v["citizenSoBananQuyetdinhlyhon"]["value"] == "5/2011/HNGĐ-ST"
    assert (v["citizenField46"]["value"], v["citizenField47"]["value"]) == ("15/07/2011", "Tòa án nhân dân A")


def test_goa_va_khoang_thoi_gian():
    v, _ = _enrich({**BASE, "TinhTrangHonNhan": "goa", "DeathCert_Number": "167/TLKT-BS",
                    "DeathCert_Date": "07/11/2024", "DeathCert_Agency": "UBND xã A"}, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "4" and v["citizenField50"]["code"] == "2024-11-07"
    v, _ = _enrich({**BASE, "Period_TuNgay": "27/04/2016", "Period_DenNgay": "14/09/2016",
                    "Marriage_SpouseName": "Trần Thị C"}, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "5"
    assert (v["citizenField56"]["code"], v["citizenField57"]["code"]) == ("2016-04-27", "2016-09-14")


def test_muc_dich_khac_va_khong_chac_thi_to_vang():
    v, _ = _enrich(BASE, _context(chac="thap"))
    assert v["citizenField60"]["code"] == "3"
    assert v["citizenField69"]["value"] == "Bổ sung hồ sơ vay vốn" and v["citizenField69"]["default"] is True


def test_muc_dich_ket_hon_nuoc_ngoai_dien_nguoi_du_dinh_ket_hon():
    v, _ = _enrich({**BASE, "KetHonVoi_HoTen": "John Smith", "KetHonVoi_LoaiGiayTo": "Hộ chiếu"},
                   _context(loai="ket_hon_nuoc_ngoai", noi_dung="Để đăng ký kết hôn tại Hoa Kỳ"))
    assert v["citizenField60"]["code"] == "2" and "citizenField69" not in v
    assert v["citizenHochudemtendaiienncngoai"]["value"] == "JOHN SMITH"
    assert v["citizenDaidiengiaytotuythan"]["code"] == "6"


def test_so_dien_thoai_va_so_ban_sao():
    v, _ = _enrich({**BASE, "NguoiNop_SoDienThoai": "0912.345.678"}, _context())
    assert v["citizenPhone"]["value"] == "0912345678"
    assert v["citizenField70"]["value"] == "0" and v["citizenField70"]["default"] is True
    v, _ = _enrich({**BASE, "NguoiNop_SoDienThoai": "0912345678", "SoLuongBanSao": "02"},
                   _context(co_trong_ho_so="Không"))
    assert "citizenPhone" not in v and v["citizenField70"]["value"] == "2"


def test_planner_xep_dong_theo_loai_giay_con_lai_vao_dong_hon_nhan():
    types = ["previous_certificate", "divorce_decision", "death_certificate", "authorization", "declaration",
             "identity", "la_qua"]
    items = planner.build_plan_items([f"{i}.pdf" for i in range(len(types))], dict(enumerate(types)), {})
    assert [i["slotIndex"] for i in items] == [0, 1, 1, 2, 1, 1, 1]
    assert items[-1]["detectedType"] == "other"


@pytest.mark.skipif(not SNAPSHOT.exists(), reason="thiếu snapshot cổng")
def test_static_ui_keys_exist_in_snapshot():
    data_names = set(re.findall(r'data-name="([A-Za-z0-9_]+?)__\d+"', SNAPSHOT.read_text(encoding="utf-8")))
    always = {"citizenPhone", "citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan",
              "citizenNDKHochudemtenngdccap", "citizenNDKNgaythangnamsinh", "citizenNDKSoDinhDanh",
              "citizenNDKLoaicutru", "citizenNDKnoicutru", "citizenNDKTinh_ThTru", "citizenNDKXa_ThTru",
              "citizenNDKDiaChi_ThTru", "citizenTinhtranghonnhan", "citizenField60", "citizenField69", "citizenField70"}
    assert always <= data_names and always <= set(UI_COMP_BY_NAME)


def test_khoang_thoi_gian_ma_khong_co_hon_nhan_hien_tai_thi_chua_ket_hon():
    v, _ = _enrich({**BASE, "TinhTrangHonNhan": "khoang_thoi_gian", "Period_TuNgay": "19/06/2000",
                    "Period_DenNgay": "12/10/2024"}, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "1" and "citizenField56" not in v


def test_khong_xac_dinh_muc_dich_thi_mac_dinh_muc_dich_khac():
    v, _ = _enrich(BASE, _context(loai="không xác định", noi_dung="Không có"))
    assert (v["citizenField60"]["code"], v["citizenField60"]["default"]) == ("3", True)
    assert "citizenField69" not in v


def test_tu_khai_tren_to_khai_nhung_nguoi_nop_khac_thi_quan_he_khac():
    # Tài khoản (cán bộ nộp hộ) khác hẳn người được cấp: dù bước phân vai lỡ kết luận "Bản thân" vẫn không tích Bản thân.
    other = {**BASE, "NguoiDuocCap_HoTen": "Trần Thị C", "NguoiDuocCap_SoDinhDanh": "001190000003",
             "NguoiDuocCap_NgaySinh": "01/01/1999"}
    v, warnings = _enrich(other, _context(relation="Bản thân"))
    assert v["citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan"]["code"] == "2"
    assert v["citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan"]["default"] is True and warnings


def test_cong_tra_khong_ra_thi_van_dien_gioi_tinh_giay_to_theo_giay():
    v, _ = _enrich({**BASE, "NguoiDuocCap_GioiTinh": "Nữ", "NguoiDuocCap_DanToc": "Kinh",
                    "NguoiDuocCap_SoGiayTo": "001090000002", "NguoiDuocCap_NgayCap": "02/07/2021",
                    "NguoiDuocCap_NoiCap": "Cục CS QLHC về TTXH"}, _context())
    assert v["citizenNDKGioitinh"]["code"] == "2" and v["citizenNDKDantoc"]["value"] == "Kinh"
    assert (v["citizenField20"]["code"], v["citizenField20"]["default"]) == ("VN", True)
    assert v["citizenNDKLoaigiayto"]["code"] in ("5", "9") and v["citizenNDKSogiaytotuythan"]["value"] == "001090000002"
    assert v["citizenNDKNgaycap"]["code"] == "2021-07-02"
    assert v["citizenNDKNocap"]["value"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    names = list(v)
    assert names.index("citizenNDKSoDinhDanh") < names.index("citizenNDKGioitinh")  # sau 3 ô tra cứu


def test_dan_toc_lay_tu_giay_to_khac_khi_to_khai_khong_ghi():
    v, _ = _enrich({**BASE, "GiayToKhac_DanToc": "Tày"}, _context())
    assert v["citizenNDKDantoc"]["value"] == "Tày"
    v, _ = _enrich({**BASE, "NguoiDuocCap_DanToc": "Kinh", "GiayToKhac_DanToc": "Tày"}, _context())
    assert v["citizenNDKDantoc"]["value"] == "Kinh"


DONG_HA = {"tinh": "Tỉnh Quảng Trị", "xa": "Phường Đông Hà"}


def test_dong_ha_chi_dinh_uy_quyen_theo_tai_khoan():
    from app.pipelines.xac_nhan_tthn_dvc_moi.attach.nghia_hung import with_account_attach_options

    key = "xac-nhan-tinh-trang-hon-nhan"
    assert with_account_attach_options({}, DONG_HA, key) == {"onlyAuthorization": True}
    # Client không tự bật được; phường khác tên gần giống / thủ tục khác → không có cờ.
    assert with_account_attach_options({"onlyAuthorization": True}, {"tinh": "Tỉnh Quảng Trị", "xa": "Phường Nam Đông Hà"}, key) == {}
    assert with_account_attach_options({}, {"tinh": "Tỉnh Lâm Đồng", "xa": "Xã Đông Hà"}, key) == {}
    assert with_account_attach_options({}, DONG_HA, "ket-hon") == {}


def _fake_portal(monkeypatch, module, chat_json: dict, texts: list[str]):
    import json

    from app.services import ocr

    async def fake_ocr_per_file(files):
        return [{"name": f["name"], "text": texts[i]} for i, f in enumerate(files)]

    async def fake_chat(messages, max_tokens, enable_thinking):
        return json.dumps(chat_json, ensure_ascii=False)

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr_per_file)
    monkeypatch.setattr(module.client, "chat", fake_chat)


def _files(n: int):
    from app.process.schemas import FileItem

    return [FileItem(name=f"{i}.pdf", type="application/pdf", dataUrl="data:application/pdf;base64,JVBERi0=", role="doc")
            for i in range(n)]


async def test_dong_ha_khong_tach_chi_giu_uy_quyen(monkeypatch):
    _fake_portal(monkeypatch, planner, {"documents": [
        {"index": 0, "docType": "declaration", "documentName": "Tờ khai"},
        {"index": 1, "docType": "authorization", "documentName": "Văn bản ủy quyền"},
        {"index": 2, "docType": "divorce_decision", "documentName": "Quyết định ly hôn"},
    ]}, ["tờ khai", "ủy quyền", "ly hôn"])
    result = await planner.plan(_files(3), {"onlyAuthorization": True})
    assert [(a["fileIndex"], a["slotIndex"]) for a in result["attachments"]] == [(1, 2)]
    # Bỏ im lặng: không có thông báo "Chưa đính kèm được" cho các giấy bị bỏ.
    assert result["errors"] == [] and result["nothingToAttach"] is None
    # Không có cờ → đính đủ như mọi nơi.
    assert len((await planner.plan(_files(3), {}))["attachments"]) == 3


async def test_dong_ha_tach_cat_dung_trang_uy_quyen(monkeypatch):
    from app.pipelines.xac_nhan_tthn_dvc_moi.attach.dinh_kem_tach import planner as split_planner

    _fake_portal(monkeypatch, split_planner, {"documents": [
        {"fileIndex": 0, "pages": [1], "docType": "declaration", "documentName": "Tờ khai"},
        {"fileIndex": 0, "pages": [2], "docType": "authorization", "documentName": "Văn bản ủy quyền"},
    ]}, ["Trang 1/2\ntờ khai\nTrang 2/2\nủy quyền"])
    result = await split_planner.plan(_files(1), {"onlyAuthorization": True})
    assert len(result["attachments"]) == 1
    item = result["attachments"][0]
    assert item["slotIndex"] == 2 and item["sourceSegments"] == [{"fileIndex": 0, "pageIndexes": [1]}]


async def test_dong_ha_khong_thay_uy_quyen_thi_khong_dinh_va_khong_bao_loi(monkeypatch):
    _fake_portal(monkeypatch, planner, {"documents": [{"index": 0, "docType": "identity", "documentName": "CCCD"}]},
                 ["căn cước"])
    result = await planner.plan(_files(1), {"onlyAuthorization": True})
    assert result["attachments"] == []
    # Extension coi là đính xong (nothingToAttach), không báo lỗi.
    assert result["errors"] == [] and result["nothingToAttach"] is True


CCCD_SONG = {"name": "cccd.jpg", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 001090000002\nHọ và tên: NGUYỄN VĂN B\nNgày sinh: 05/03/1990"}
KHAI_TU = {"name": "trich_luc.pdf", "text": "TRÍCH LỤC KHAI TỬ\nHọ, chữ đệm, tên: TRẦN THỊ D\nNgày sinh: 01/02/1950\n"
                                             "Số định danh cá nhân: 001150000004\nNgày chết: 10/10/2025"}


def _role(name: str, number: str) -> str:
    return (f"<nguoi_duoc_cap>\nHọ tên: {name}\nSố định danh: {number}\nNgày sinh: 01/02/1950\nNguồn: x\n</nguoi_duoc_cap>\n"
            "<quan_he>\nKết luận: Con\n</quan_he>")


def test_cccd_va_khai_tu_khong_lay_nguoi_chet_lam_nguoi_duoc_cap():
    from app.pipelines.xac_nhan_tthn_dvc_moi.process import reason

    docs = [CCCD_SONG, KHAI_TU]
    assert "Giấy khai tử: tài liệu 2" in reason._document_hints(docs, {"formContext": ACCOUNT})
    out = reason._render_context(_role("TRẦN THỊ D", "001150000004"), {"formContext": ACCOUNT}, docs)
    subject = reason.section(out, "nguoi_duoc_cap")
    assert "tài liệu 1" in subject and "001150000004" not in subject
    assert "Con" not in reason.section(out, "quan_he")
    # Phân vai đã đúng người đứng tên thẻ → giữ nguyên.
    out = reason._render_context(_role("NGUYỄN VĂN B", "001090000002"), {"formContext": ACCOUNT}, docs)
    assert "001090000002" in reason.section(out, "nguoi_duoc_cap")


def test_co_to_khai_thi_khong_can_thiep_nguoi_duoc_cap():
    from app.pipelines.xac_nhan_tthn_dvc_moi.process import reason

    to_khai = {"name": "to_khai.pdf", "text": "TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\nĐề nghị cấp ... TRẦN THỊ D\n"
                                               "Số định danh: 001150000004\nGóa, theo giấy chứng tử số 01"}
    assert not reason._is_death_doc(to_khai)
    out = reason._render_context(_role("TRẦN THỊ D", "001150000004"), {}, [to_khai, CCCD_SONG, KHAI_TU])
    assert "001150000004" in reason.section(out, "nguoi_duoc_cap")


CCCD_HAI_DONG = ("CĂN CƯỚC CÔNG DÂN\nSố / No.: 001090000002\nHọ và tên / Full name:\nNGUYỄN VĂN B\n"
                 "Nơi thường trú / Place of residence: Xóm Mới\nKim Chân, Thành phố Bắc Ninh, Bắc Ninh\n")


def _enrich_ocr(residence: dict, ocr_text: str):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in {**BASE, "NguoiDuocCap_NoiCuTru": residence}.items()]
    out, warnings = mapper.enrich(fields, {"formContext": ACCOUNT, "_reasoning_context": _context(),
                                           "_ocr_text": ocr_text})
    return {f["name"]: f for f in out}, warnings


def test_cccd_noi_thuong_tru_hai_dong_lay_xa_dong_sau():
    for read in ("Xóm Mới", "Mới"):
        v, warnings = _enrich_ocr({"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": read, "diaChi": ""}, CCCD_HAI_DONG)
        assert v["citizenNDKXa_ThTru"]["value"] == "Phường Vũ Ninh"
        assert v["citizenNDKDiaChi_ThTru"]["value"] == read and not v["citizenNDKDiaChi_ThTru"].get("default")
        assert warnings == []


def test_xa_khong_co_trong_danh_muc_thi_bo_trong_va_bao():
    v, warnings = _enrich_ocr({"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Xóm Mới", "diaChi": "Số 2"}, "")
    assert "citizenNDKXa_ThTru" not in v
    assert v["citizenNDKDiaChi_ThTru"]["value"] == "Số 2, Xóm Mới" and v["citizenNDKDiaChi_ThTru"]["default"] is True
    assert any("phường/xã" in w for w in warnings)


def test_xa_cu_doc_dung_van_remap_nhu_cu():
    v, _ = _enrich_ocr({"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Kim Chân", "diaChi": "Xóm Mới"},
                       CCCD_HAI_DONG)
    assert v["citizenNDKXa_ThTru"]["value"] == "Phường Vũ Ninh"
    assert v["citizenNDKDiaChi_ThTru"]["value"] == "Xóm Mới, Kim Chân"
