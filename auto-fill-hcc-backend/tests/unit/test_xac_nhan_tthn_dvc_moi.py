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


def test_ban_than_khoi_nguoi_duoc_cap_lay_theo_tai_khoan():
    # Tờ khai viết tay: OCR lệch tên, ngày sinh, số định danh, địa chỉ; tài khoản (cổng đổ theo định danh) mới chuẩn.
    account = {"applicantFullname": "Nguyễn Văn Bình", "applicantIdentityNumber": "001090000002",
               "applicantBirthday": "05/03/1990", "applicantGender": "Nam", "applicantIdDate": "02/07/2021",
               "applicantAddress": {"tinh": "Hà Nội", "xa": "Phường Hoàn Kiếm", "diaChi": "Số 9"}}
    paper = {"NguoiDuocCap_HoTen": "Nguyễn Văn Binh", "NguoiDuocCap_NgaySinh": "06/03/1990",
             "NguoiDuocCap_SoDinhDanh": "001090000082", "NguoiDuocCap_SoGiayTo": "001090000082",
             "NguoiDuocCap_NgayCap": "02/07/2027", "NguoiDuocCap_DanToc": "Tày",
             "NguoiDuocCap_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Hà Nội", "xa": "Phường Hoàn Kiếm", "diaChi": "Số 1"}}
    v, warnings = _enrich(paper, _context(), account)
    assert (v["citizenQuanhevoinguoiduoccapGiayxacnhantinhtranghonnhan"]["code"], warnings) == ("1", [])
    assert v["citizenNDKHochudemtenngdccap"]["value"] == "NGUYỄN VĂN BÌNH"
    assert v["citizenNDKNgaythangnamsinh"]["code"] == "1990-03-05"
    assert v["citizenNDKSoDinhDanh"]["value"] == "001090000002" and v["citizenNDKSogiaytotuythan"]["value"] == "001090000002"
    assert v["citizenNDKNgaycap"]["code"] == "2021-07-02" and v["citizenNDKDiaChi_ThTru"]["value"] == "Số 9"
    # Ô tài khoản không gửi (dân tộc) thì vẫn theo giấy.
    assert v["citizenNDKDantoc"]["value"] == "Tày"
    assert v["citizenNycNoicutru"]["code"] == "1" and v["citizenNycNoicutru"]["default"] is True


def test_ban_than_tai_khoan_chi_co_ten_khong_dau_va_so_thi_cac_o_khac_theo_giay():
    # Bản extension cũ chỉ gửi họ tên + số: tên không dấu không đè tên có dấu trên giấy, các ô khác theo giấy.
    v, _ = _enrich(BASE, _context())
    assert v["citizenNDKHochudemtenngdccap"]["value"] == "NGUYỄN VĂN B"
    assert v["citizenNDKNgaythangnamsinh"]["code"] == "1990-03-05" and v["citizenNDKSoDinhDanh"]["value"] == "001090000002"
    assert all(v[n].get("lookup") for n in
               ("citizenNDKHochudemtenngdccap", "citizenNDKNgaythangnamsinh", "citizenNDKSoDinhDanh"))


def test_nguoi_khac_tra_cuu_dan_cu_va_dia_chi():
    v, _ = _enrich(BASE, _context(relation="Con"))
    assert v["citizenNDKNgaythangnamsinh"]["code"] == "1990-03-05"
    assert all(v[n].get("lookup") for n in
               ("citizenNDKHochudemtenngdccap", "citizenNDKNgaythangnamsinh", "citizenNDKSoDinhDanh"))
    assert v["citizenNDKnoicutru"]["code"] == "1" and v["citizenNDKLoaicutru"]["default"] is True


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


def test_ly_hon_tu_o_gop_csdl_nhung_chi_co_giay_khai_tu_thi_goa():
    # Phiếu CSDL dân cư ghi gộp "Đã ly hôn hoặc góa vợ/chồng", model lấy "ly_hon"; hồ sơ chỉ có trích lục khai tử của chồng.
    death = {"DeathCert_Number": "487/2026", "DeathCert_Date": "24/07/2026", "DeathCert_Agency": "UBND xã A"}
    v, _ = _enrich({**BASE, "TinhTrangHonNhan": "ly_hon", **death}, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "4" and v["citizenSogiaychungtuTrichluckhaituBanan"]["value"] == "487/2026"
    # Có bản án ly hôn thì vẫn là ly hôn.
    v, _ = _enrich({**BASE, "TinhTrangHonNhan": "ly_hon", **death, "DivorceDecision_Number": "5/2011/HNGĐ-ST"}, _context())
    assert v["citizenTinhtranghonnhan"]["code"] == "3"


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


@pytest.mark.parametrize("noi_dung", ["Giấy này được sử dụng để: Bổ sung hồ sơ vay vốn ngân hàng",
                                      "Giấy được sử dụng để:Bổ sung hồ sơ vay vốn ngân hàng"])
def test_muc_dich_bo_nhan_cua_giay_xnttthn_cu(noi_dung):
    v, _ = _enrich(BASE, _context(noi_dung=noi_dung))
    assert v["citizenField69"]["value"] == "Bổ sung hồ sơ vay vốn ngân hàng"


def test_so_giay_to_doc_nham_dong_mrz_thi_lay_lai_so_dinh_danh():
    """MRZ thẻ căn cước: "IDVNM" + số hiệu thẻ (9 số cuối số định danh) + số định danh 12 số."""
    v, _ = _enrich({**BASE, "NguoiDuocCap_SoDinhDanh": "001090000002", "NguoiDuocCap_SoGiayTo": "IDVNM090000002",
                    "NguoiDuocCap_LoaiGiayTo": "Căn cước", "NguoiDuocCap_NgayCap": "20/10/2024"}, _context(relation="Con"))
    assert v["citizenNDKSogiaytotuythan"]["value"] == "001090000002"
    assert v["citizenNDKLoaigiayto"]["value"] != "Chứng minh nhân dân"
    # CMND 9 số thật (không trùng đuôi số định danh) giữ nguyên.
    cmnd, _ = _enrich({**BASE, "NguoiDuocCap_SoDinhDanh": "001090000002", "NguoiDuocCap_SoGiayTo": "123456789",
                       "NguoiDuocCap_LoaiGiayTo": "Chứng minh nhân dân", "NguoiDuocCap_NgayCap": "02/07/2010"},
                      _context(relation="Con"))
    assert cmnd["citizenNDKSogiaytotuythan"]["value"] == "123456789"


def test_ten_xa_chi_lech_dau_thanh_thi_chon_xa_hien_hanh():
    from app.pipelines._shared.area_remap import accent_only_ward
    assert accent_only_ward("Quảng Ngãi", "Phường Đăk Cẩm") == "Phường Đăk Cấm"
    assert accent_only_ward("Quảng Ngãi", "Phường Không Có") == ""
    area = mapper._area({"quocGia": "Việt Nam", "tinh": "Quảng Ngãi", "xa": "Đăk Cẩm", "diaChi": "Tổ dân phố 8"})
    assert (area["xa"], area["diaChi"], area.get("_xaChuaChon")) == ("Phường Đăk Cấm", "Tổ dân phố 8", None)


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
                    "NguoiDuocCap_NoiCap": "Cục CS QLHC về TTXH"}, _context(relation="Con"))
    assert v["citizenNDKGioitinh"]["code"] == "2" and v["citizenNDKDantoc"]["value"] == "Kinh"
    assert (v["citizenField20"]["code"], v["citizenField20"]["default"]) == ("VN", True)
    assert v["citizenNDKLoaigiayto"]["code"] in ("5", "9") and v["citizenNDKSogiaytotuythan"]["value"] == "001090000002"
    assert v["citizenNDKNgaycap"]["code"] == "2021-07-02"
    assert v["citizenNDKNocap"]["value"] == "Cục Cảnh sát QLHC về TTXH"  # ô chữ tự do: ghi tên Cục dạng viết tắt
    names = list(v)
    assert names.index("citizenNDKSoDinhDanh") < names.index("citizenNDKGioitinh")  # sau 3 ô tra cứu


def test_to_khai_in_san_cuc_ma_ngay_cap_tu_01_07_2024_thi_co_quan_cap_la_bo_cong_an():
    """Mẫu tờ khai in sẵn tên Cục trước chỗ ghi ngày cấp, người dân chỉ điền được ngày → chốt lại theo ngày cấp."""
    card = {**BASE, "NguoiDuocCap_SoGiayTo": "001090000002", "NguoiDuocCap_LoaiGiayTo": "Căn cước",
            "NguoiDuocCap_NoiCap": "Cục CSQLHC về TTXH"}
    new, _ = _enrich({**card, "NguoiDuocCap_NgayCap": "01/07/2024"}, _context(relation="Con"))
    old, _ = _enrich({**card, "NguoiDuocCap_NgayCap": "30/06/2024"}, _context(relation="Con"))
    assert new["citizenNDKNocap"]["value"] == "Bộ Công an"
    assert old["citizenNDKNocap"]["value"] == "Cục Cảnh sát QLHC về TTXH"
    # Loại thẻ đi cùng cơ quan cấp: từ 01/7/2024 là thẻ căn cước, trước đó là căn cước công dân.
    assert new["citizenNDKLoaigiayto"]["value"] == "Thẻ căn cước"
    assert old["citizenNDKLoaigiayto"]["value"] == "Căn cước công dân"


def test_dan_toc_lay_tu_giay_to_khac_khi_to_khai_khong_ghi():
    v, _ = _enrich({**BASE, "GiayToKhac_DanToc": "Tày"}, _context(relation="Con"))
    assert v["citizenNDKDantoc"]["value"] == "Tày"
    v, _ = _enrich({**BASE, "NguoiDuocCap_DanToc": "Kinh", "GiayToKhac_DanToc": "Tày"}, _context(relation="Con"))
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
    ]}, ["───── Trang 1/2 ─────\ntờ khai\n───── Trang 2/2 ─────\nủy quyền"])
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


TRICH_LUC_KHAI_TU = (
    "TỈNH BẮC NINH CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nUBND PHƯỜNG ĐÔNG MAI\n"
    "Số: 25/TLKT Đông Mai, ngày 7 tháng 5 năm 2022\nTRÍCH LỤC KHAI TỬ\nHọ, chữ đệm, tên: TRẦN VĂN K\n"
    "Ngày, tháng, năm sinh: 1/2/1970 Giới tính: Nam Dân tộc: Kinh\n"
    "Đã chết vào lúc 8 giờ, ngày 01 tháng 5 năm 2022\nHọ, chữ đệm, tên người đi khai tử: Trần Văn L\n"
)


def _ocr(*docs: tuple[str, str]) -> str:
    return "\n\n---\n\n".join(f"===== {name} (tiengnoi) =====\n{text}" for name, text in docs)


def test_cccd_va_trich_luc_khai_tu_llm_bo_sot_thi_goa_theo_giay():
    values = {**BASE, "NguoiDuocCap_HoTen": "Lê Thị M", "NguoiDuocCap_GioiTinh": "Nữ"}
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    ocr = _ocr(("a.jpg", TRICH_LUC_KHAI_TU), ("b.jpg", "CĂN CƯỚC CÔNG DÂN\nHọ và tên / Full name: LÊ THỊ M\n"))
    out, _ = mapper.enrich(fields, {"formContext": ACCOUNT, "_reasoning_context": _context(), "_ocr_text": ocr})
    v = {f["name"]: f for f in out}
    assert v["citizenTinhtranghonnhan"]["code"] == "4"
    assert v["citizenSogiaychungtuTrichluckhaituBanan"]["value"] == "25/TLKT"
    assert v["citizenField50"]["value"] == "07/05/2022"
    assert v["citizenField51"]["value"] == "Ủy ban nhân dân phường Đông Mai"


def test_trich_luc_khai_tu_co_dong_dang_ky_goc_thi_bu_theo_dong_do():
    values = {**BASE, "NguoiDuocCap_HoTen": "Lê Thị M", "NguoiDuocCap_GioiTinh": "Nữ"}
    body = ("Đã được đăng ký khai tử tại: UBND xã Đông Mai, huyện Yên Phong, tỉnh Bắc Ninh\n"
            "Số: 12/2020 ngày 3 tháng 4 năm 2020\n")
    found = mapper._death_cert_from_ocr(_ocr(("a.jpg", TRICH_LUC_KHAI_TU + body)), values)
    assert found == {"DeathCert_Number": "12/2020", "DeathCert_Date": "3/4/2020",
                     "DeathCert_Agency": "Ủy ban nhân dân xã Đông Mai, huyện Yên Phong, tỉnh Bắc Ninh"}
    # Dòng đăng ký gốc không ghi ngày → ngày lấy ở đầu giấy, không để trống.
    partial = mapper._death_cert_from_ocr(_ocr(("a.jpg", TRICH_LUC_KHAI_TU + body.replace(" ngày 3 tháng 4 năm 2020", ""))), values)
    assert partial["DeathCert_Number"] == "12/2020" and partial["DeathCert_Date"] == "7/5/2022"


@pytest.mark.parametrize("raw,number", [
    ("12/2020", "12/2020"), ("27/TLKT-BS", "27/TLKT-BS"), ("05/04/2021", ""), ("UBND xã A", ""), (None, ""),
])
def test_so_giay_khai_tu_phai_la_so_khong_phai_ngay_hay_co_quan(raw, number):
    assert mapper._document_number(raw) == number


def test_co_quan_cap_giay_khai_tu_viet_du_chu_uy_ban_nhan_dan():
    v, _ = _enrich({**BASE, "TinhTrangHonNhan": "goa", "DeathCert_Number": "12/2020", "DeathCert_Date": "07/11/2024",
                    "DeathCert_Agency": "UBND xã A, huyện B, tỉnh C"}, _context())
    assert v["citizenField51"]["value"] == "Ủy ban nhân dân xã A, huyện B, tỉnh C"


def test_dong_dang_ky_goc_dang_cap_so_ngay_dang_ky():
    text = "Đã đăng ký khai tử tại: UBND xã A, TP B, tỉnh C\nCấp số: 08/2008 Quyển số: 01/2008 Ngày đăng ký: 22/5/2008\n"
    assert mapper._death_registration(text) == {"DeathCert_Number": "08/2008", "DeathCert_Date": "22/05/2008",
                                                "DeathCert_Agency": "Ủy ban nhân dân xã A, TP B, tỉnh C"}


def test_dong_dang_ky_goc_dang_noi_ghi_so_dang_ky_khai_tu():
    text = ("Đã được ghi vào Sổ đăng ký khai tử\n"
            "Nơi ghi: Ủy ban nhân dân Xã A, tỉnh C, Sổ đăng ký khai tử, quyển số 01/2025, số 09/2025, ngày 11/07/2025\n")
    assert mapper._death_registration(text) == {"DeathCert_Number": "09/2025", "DeathCert_Date": "11/07/2025",
                                                "DeathCert_Agency": "Ủy ban nhân dân Xã A, tỉnh C"}


def test_so_ly_hon_khong_co_chu_so_thi_bo():
    v, _ = _enrich({**BASE, "TinhTrangHonNhan": "ly_hon", "BanAn_Number": "Không xác định", "BanAn_Date": "02/03/2019"},
                   _context())
    assert "citizenSoBananQuyetdinhlyhon" not in v and v["citizenField46"]["value"] == "02/03/2019"


def test_giay_khai_tu_cung_gioi_hoac_llm_da_tra_thi_khong_bu():
    ocr = _ocr(("a.jpg", TRICH_LUC_KHAI_TU))
    same_gender = {**BASE, "NguoiDuocCap_GioiTinh": "Nam"}
    assert mapper._death_cert_from_ocr(ocr, same_gender) == {}
    values = {**BASE, "NguoiDuocCap_GioiTinh": "Nữ", "TinhTrangHonNhan": "goa", "DeathCert_Number": "9/TLKT"}
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    out, _ = mapper.enrich(fields, {"formContext": ACCOUNT, "_reasoning_context": _context(), "_ocr_text": ocr})
    v = {f["name"]: f for f in out}
    assert v["citizenSogiaychungtuTrichluckhaituBanan"]["value"] == "9/TLKT" and "citizenField50" not in v


CCCD_HAI_DONG = ("CĂN CƯỚC CÔNG DÂN\nSố / No.: 001090000002\nHọ và tên / Full name:\nNGUYỄN VĂN B\n"
                 "Nơi thường trú / Place of residence: Xóm Mới\nKim Chân, Thành phố Bắc Ninh, Bắc Ninh\n")


def _enrich_ocr(residence: dict, ocr_text: str):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in {**BASE, "NguoiDuocCap_NoiCuTru": residence}.items()]
    # Khối địa chỉ người được cấp chỉ điền khi người nộp KHÔNG phải chính họ.
    out, warnings = mapper.enrich(fields, {"formContext": ACCOUNT, "_reasoning_context": _context(relation="Con"),
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
    # Ô chi tiết chỉ chứa phần dưới xã: không ghép tên xã cũ đã quy đổi.
    assert v["citizenNDKDiaChi_ThTru"]["value"] == "Xóm Mới"


# --- Phân vai: mỏ neo do mã đối chiếu + các nhánh dự phòng -------------------------------------------------------

TO_KHAI_CON_NOP = {"name": "to_khai.pdf", "text": (
    "TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN\n"
    "Họ, chữ đệm, tên người yêu cầu: NGUYỄN VĂN B\n"
    "Ngày, tháng, năm sinh: 05/03/1990\n"
    "Giấy tờ tùy thân: (3) Căn cước số/CCCD số...001090000082....do\n"
    "Quan hệ với người được cấp Giấy xác nhận tình trạng hôn nhân: Con đẻ\n"
    "Đề nghị cấp Giấy xác nhận tình trạng hôn nhân cho người có tên dưới đây:\n"
    "Họ, chữ đệm, tên: TRẦN THỊ D\nNgày, tháng, năm sinh: 01/02/1950\n")}
QD_LY_HON = {"name": "qd.pdf", "text": "TÒA ÁN NHÂN DÂN HUYỆN TÂN LẬP\nQUYẾT ĐỊNH CÔNG NHẬN THUẬN TÌNH LY HÔN\n"
                                         "Anh Nguyễn Văn B và chị Lê Thị C thuận tình ly hôn."}


def _raw(name="Không xác định", number="Không xác định", relation="Không xác định", birthday="Không xác định"):
    return (f"<nguoi_duoc_cap>\nHọ tên: {name}\nSố định danh: {number}\nNgày sinh: {birthday}\nNguồn: x\n"
            f"Căn cứ phân vai: y\n</nguoi_duoc_cap>\n<quan_he>\nKết luận: {relation}\nCăn cứ: z\n</quan_he>")


def test_ma_doi_chieu_nguoi_yeu_cau_tren_to_khai_voi_tai_khoan():
    from app.pipelines.xac_nhan_tthn_dvc_moi.process import reason

    options = {"formContext": ACCOUNT}
    # Số trên tờ khai viết tay lệch một chữ số, họ tên trùng → vẫn là chủ tài khoản.
    assert reason.declaration_requester([TO_KHAI_CON_NOP])["relation"] == "Con đẻ"
    assert reason.requester_is_account([TO_KHAI_CON_NOP], options) is True
    hints = reason._document_hints([TO_KHAI_CON_NOP], options)
    assert "LÀ chủ tài khoản" in hints and 'tờ khai: "Con đẻ"' in hints
    other = {"formContext": {"applicantFullname": "LÊ VĂN E", "applicantIdentityNumber": "001080000009"}}
    assert reason.requester_is_account([TO_KHAI_CON_NOP], other) is False
    assert reason.requester_is_account([CCCD_SONG], options) is None


@pytest.mark.parametrize("model_relation", ["Không xác định", "Mẹ"])
def test_nguoi_yeu_cau_la_chu_tai_khoan_thi_quan_he_chep_dong_cua_to_khai(model_relation):
    # Model bỏ trống hoặc đảo chiều ("Mẹ" là vai của người được cấp) → mã chép đúng chữ của tờ khai.
    from app.pipelines.xac_nhan_tthn_dvc_moi.process import reason

    out = reason._render_context(_raw("TRẦN THỊ D", "001150000004", model_relation), {"formContext": ACCOUNT},
                                 [TO_KHAI_CON_NOP])
    assert reason.labeled_value(reason.section(out, "quan_he"), "Kết luận") == "Con đẻ"
    # Người khác nộp hộ bằng tài khoản của mình: dòng quan hệ trên tờ khai không phải của người nộp.
    other = {"formContext": {"applicantFullname": "LÊ VĂN E", "applicantIdentityNumber": "001080000009"}}
    out = reason._render_context(_raw("TRẦN THỊ D", "001150000004"), other, [TO_KHAI_CON_NOP])
    assert reason.labeled_value(reason.section(out, "quan_he"), "Kết luận") == ""


def test_khong_chon_duoc_ai_va_khong_co_the_cua_nguoi_khac_thi_nguoi_duoc_cap_la_chu_tai_khoan():
    from app.pipelines.xac_nhan_tthn_dvc_moi.process import reason

    options = {"formContext": ACCOUNT}
    for docs in ([QD_LY_HON], [KHAI_TU], [QD_LY_HON, CCCD_SONG]):   # thẻ của chính chủ tài khoản không cản
        out = reason._render_context(_raw(), options, docs)
        subject = reason.section(out, "nguoi_duoc_cap")
        assert reason.labeled_value(subject, "Họ tên") == "NGUYEN VAN B"
        assert "tài khoản người nộp" in reason.labeled_value(subject, "Nguồn")
        assert reason.labeled_value(reason.section(out, "quan_he"), "Kết luận") == "Bản thân"
    # Có thẻ của người khác, hoặc có tờ khai: không biết ai xin giấy → giữ "Không xác định".
    other_card = {"name": "the.jpg", "text": "CĂN CƯỚC CÔNG DÂN\nSố: 001185000007\nHọ và tên: LÊ THỊ C"}
    for docs in ([QD_LY_HON, other_card], [TO_KHAI_CON_NOP]):
        out = reason._render_context(_raw(), options, docs)
        assert reason.labeled_value(reason.section(out, "nguoi_duoc_cap"), "Họ tên") == ""


@pytest.mark.parametrize("relation,number,birthday,docs,dropped", [
    ("Người được ủy quyền", "001150000004", "01/02/1950", [CCCD_SONG], True),          # không có văn bản ủy quyền
    ("Người được ủy quyền", "001150000004", "01/02/1950",
     [{"name": "uq.pdf", "text": "GIẤY ỦY QUYỀN\nBên ủy quyền: TRẦN THỊ D"}], False),
    ("Người khác", "001150000004", "01/02/1950", [CCCD_SONG], True),                   # nhãn tự đặt
    ("Vợ", "001150000004", "01/02/1950", [CCCD_SONG], True),                           # chủ tài khoản là nam
    ("Chồng", "001190000004", "01/02/1990", [CCCD_SONG], False),
    ("Cha", "001150000004", "01/02/1950", [CCCD_SONG], True),                          # "cha" mà sinh sau 40 năm
    ("Con", "001150000004", "01/02/1950", [CCCD_SONG], False),
])
def test_quan_he_model_viet_ma_khong_co_can_cu_thi_bo(relation, number, birthday, docs, dropped):
    from app.pipelines.xac_nhan_tthn_dvc_moi.process import reason

    out = reason._render_context(_raw("TRẦN THỊ D", number, relation, birthday), {"formContext": ACCOUNT}, docs)
    assert (reason.labeled_value(reason.section(out, "quan_he"), "Kết luận") == "") is dropped


def test_trung_du_so_dinh_danh_la_ban_than_du_ocr_doc_lech_ho():
    values = {"NguoiDuocCap_HoTen": "NGUYỄN VĂN B", "NguoiDuocCap_SoDinhDanh": "001090000002"}
    account = {"applicantFullname": "NGÔ VĂN B", "applicantIdentityNumber": "001090000002"}
    code, other, _, _ = mapper._relation(values, _context(), {"formContext": account})
    assert (code, other) == ("1", "")


@pytest.mark.parametrize("raw,expected", [
    ("121/2021/QĐST-HNGD", "121/2021/QĐST-HNGĐ"),
    ("125/2022/QDST-HNGĐ", "125/2022/QĐST-HNGĐ"),
    ("97/2012/QĐ/HN-GDST", "97/2012/QĐ/HN-GĐST"),
    ("57 /2016/QĐST-HNGĐ", "57/2016/QĐST-HNGĐ"),
    ("12/2020/QĐDS-ST", "12/2020/QĐDS-ST"),          # "DS" là dân sự, không đổi
])
def test_so_quyet_dinh_ly_hon_chuan_chu_d(raw, expected):
    assert mapper._court_code(raw) == expected


def test_ma_khac_ma_ho_so_chi_co_giay_khai_tu_thi_chon_vo_chong_da_chet():
    assert mapper._marital_status({"TinhTrangHonNhan": "khac", "DeathCert_Number": "12/2020"}) == "4"
    assert mapper._marital_status({"TinhTrangHonNhan": "khac", "BanAn_Number": "5/2019/QĐST-HNGĐ"}) == "3"
    # Có cả giấy kết hôn hiện tại, hoặc không có giấy nào: giữ mã lượt trích.
    assert mapper._marital_status({"TinhTrangHonNhan": "khac", "DeathCert_Number": "12/2020", "Marriage_Number": "3"}) == "6"
    assert mapper._marital_status({"TinhTrangHonNhan": "khac"}) == "6"


def test_giay_khai_tu_ban_sao_doc_du_phong_lay_dau_ban_sao_ban_chinh_lay_so_goc():
    sao = ("UBND XÃ MẪU\nSố: 7/TLKT-BS\nMẫu, ngày 05 tháng 4 năm 2021\nTRÍCH LỤC KHAI TỬ\n(BẢN SAO)\n"
           "Họ, chữ đệm, tên: NGUYỄN VĂN A\nGiới tính: Nam\n"
           "Đã được đăng ký khai tử tại: UBND xã Mẫu, huyện B, tỉnh C\nSố: 3 ngày 02/03/2015")
    values = {"NguoiDuocCap_HoTen": "Trần Thị B", "NguoiDuocCap_GioiTinh": "Nữ"}
    found = mapper._death_cert_from_ocr(sao, values)
    assert found["DeathCert_Number"] == "7/TLKT-BS" and mapper._full_date(found["DeathCert_Date"]) == "05/04/2021"
    chinh = sao.replace("7/TLKT-BS", "7/TLKT").replace("(BẢN SAO)\n", "")
    assert not mapper.is_death_copy(chinh)
    assert mapper._death_cert_from_ocr(chinh, values)["DeathCert_Number"] == "3"


def test_giay_khai_tu_ban_sao_don_vi_cau_hinh_lay_so_goc():
    sao = ("UBND XÃ MẪU\nSố: 7/TLKT-BS\nMẫu, ngày 05 tháng 4 năm 2021\nTRÍCH LỤC KHAI TỬ\n"
           "Họ, chữ đệm, tên: NGUYỄN VĂN A\nGiới tính: Nam\n"
           "Đã được đăng ký khai tử tại: UBND xã Mẫu, huyện B, tỉnh C\nSố: 3 ngày 02/03/2015")
    values = {"NguoiDuocCap_HoTen": "Trần Thị B", "NguoiDuocCap_GioiTinh": "Nữ"}
    assert mapper._death_cert_from_ocr(sao, values, original_number=True)["DeathCert_Number"] == "3"
    options = mapper.with_account_process_options({}, {"tinh": "Tỉnh Quảng Ngãi", "xa": "Xã Bình Sơn"}, mapper.PROCEDURE_KEY)
    assert mapper.death_original_number(options)
    assert not mapper.with_account_process_options({}, {"tinh": "Tỉnh Quảng Ngãi", "xa": "Xã Bình Sơn"}, "khac")


def _ly_hon(dau=None, so=None):
    return {"docType": "divorce_decision", "trangDau": dau, "trangSo": so}


def test_anh_roi_quyet_dinh_ly_hon_gop_mot_tep_theo_thu_tu_trang():
    # Tải lên đảo thứ tự: tệp 0 trang cuối, tệp 1 trang giữa, tệp 2 trang đầu; tệp 3 là CCCD.
    docs = [_ly_hon(2, 3), _ly_hon(2, 2), _ly_hon(2, 1), {"docType": "identity"}]
    groups = planner.join_divorce_pages(docs, [[0], [1], [2], [3]], [0, 1, 2, 3])
    assert groups == [[2, 1, 0], [3]]
    items = planner._merge_groups(planner.build_plan_items(
        ["a.jpg", "b.jpg", "c.jpg", "d.jpg"], {i: d["docType"] for i, d in enumerate(docs)},
        {0: "Quyết định công nhận thuận tình ly hôn", 1: "Quyết định công nhận thuận tình ly hôn",
         2: "Quyết định công nhận thuận tình ly hôn", 3: "CCCD Nguyen Van A"}, {1, 0}), groups)
    assert [(i["fileIndex"], i.get("sourceFileIndexes"), i["documentName"]) for i in items] == [
        (2, [2, 1, 0], "Quyết định công nhận thuận tình ly hôn"), (3, None, "CCCD Nguyen Van A")]


def test_quyet_dinh_ly_hon_khong_gop_sai():
    # Hai quyết định riêng; phần chỉ tới tệp không phải quyết định ly hôn đứng riêng; cặp hai mặt thẻ giữ nguyên.
    docs = [_ly_hon(0, 1), _ly_hon(1, 1), _ly_hon(1, 2), _ly_hon(4, 2), {"docType": "identity"},
            {"docType": "identity"}]
    assert planner.join_divorce_pages(docs, [[0], [1], [2], [3], [4, 5]], list(range(6))) == [
        [0], [1, 2], [3], [4, 5]]
    # LLM không trả trangDau / trangSo → như cũ, mỗi tệp một mục.
    assert planner.join_divorce_pages([_ly_hon(), _ly_hon()], [[0], [1]], [0, 1]) == [[0], [1]]


@pytest.mark.skipif(not SNAPSHOT.exists(), reason="thiếu snapshot cổng")
def test_o_sdt_nguoi_nop_co_trong_khoi_nguoi_nop_cong_moi():
    # Trích lục / cải chính / khai sinh / khai tử cổng mới dùng chung ô này; snapshot của các form đó chụp trước khi cổng
    # thêm ô SĐT vào khối người nộp.
    assert 'data-name="citizenPhone__' in SNAPSHOT.read_text(encoding="utf-8")



def test_ten_chu_the_khong_in_tren_mat_sau_thi_khong_ghep_theo_ten():
    # Mặt sau CMND cũ không in họ tên: tên LLM mượn từ thẻ khác không được làm khoá ghép.
    back_cmnd = "Dân tộc: Kinh\nDẤU VẾT RIÊNG VÀ DỊ HÌNH\nNGÓN TRỎ TRÁI\nGIÁM ĐỐC CA TỈNH X\nTRẦN VĂN K"
    assert planner.ten_tren_mat("NGUYỄN VĂN A", back_cmnd) is False
    assert planner.ten_tren_mat("NGUYỄN VĂN A", "IDVNM0010\nNGUYEN<<VAN<A<<<<") is True
    docs = [
        {"docType": "identity", "matThe": "truoc", "chuThe": "NGUYEN VAN A", "_soThe": "001190000001"},
        {"docType": "identity", "matThe": "sau", "chuThe": "NGUYEN VAN A", "_soThe": "",
         "_tenTrenMat": planner.ten_tren_mat("NGUYEN VAN A", back_cmnd)},
    ]
    assert planner.pair_card_sides(docs) == [[0], [1]]
    docs[1]["_tenTrenMat"] = True
    assert planner.pair_card_sides(docs) == [[0, 1]]


CCCD_MAT_SAU = ("Đặc điểm nhận dạng / Personal identification:\nsẹo chấm mép trái\n"
                "Ngày, tháng, năm / Date, month, year: 25/05/2022\nCỤC TRƯỞNG CỤC CẢNH SÁT\n"
                "QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI\nIDVNM0900000022001090000002<<2\n"
                "9003055M3003051VNM<<<<<<<<<<<<6\nNGUYEN<<VAN<B<<<<<<<<<<<<<<<\n")
CCCD_MAT_TRUOC = ("CĂN CƯỚC CÔNG DÂN\nSố / No.: 001090000002\nHọ và tên / Full name:\nNGUYỄN VĂN B\n"
                  "Ngày sinh / Date of birth: 05/03/1990\nCó giá trị đến: 05/03/2030\n")


def _enrich_the(values: dict, ocr_text: str):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    out, _ = mapper.enrich(fields, {"formContext": {"applicantFullname": "TRAN THI C",
                                                    "applicantIdentityNumber": "001190000009"},
                                    "_reasoning_context": _context(relation="Con"), "_ocr_text": ocr_text})
    return {f["name"]: f for f in out}


def test_llm_bo_sot_ngay_cap_mat_sau_cccd_thi_doc_lai_theo_mrz():
    values = {**BASE, "NguoiDuocCap_LoaiGiayTo": "Căn cước công dân", "NguoiDuocCap_SoGiayTo": "001090000002"}
    v = _enrich_the(values, _ocr(("sau.jpg", CCCD_MAT_SAU), ("truoc.jpg", CCCD_MAT_TRUOC)))
    assert v["citizenNDKNgaycap"]["value"] == "25/05/2022" and v["citizenNDKNgaycap"]["code"] == "2022-05-25"
    assert v["citizenNDKNocap"]["value"] == "Cục Cảnh sát QLHC về TTXH"


def test_ngay_cap_mat_sau_cua_nguoi_khac_hoac_ngay_het_han_thi_khong_lay():
    values = {**BASE, "NguoiDuocCap_LoaiGiayTo": "Căn cước công dân", "NguoiDuocCap_SoGiayTo": "001090000002"}
    other = CCCD_MAT_SAU.replace("001090000002", "001190000009")
    v = _enrich_the(values, _ocr(("sau.jpg", other), ("truoc.jpg", CCCD_MAT_TRUOC)))
    assert "citizenNDKNgaycap" not in v and "citizenNDKNocap" not in v
    assert mapper._card_back_issue_date(_ocr(("a.jpg", CCCD_MAT_TRUOC + CCCD_MAT_SAU.split("Ngày, tháng")[0]
                                              + "IDVNM0900000022001090000002<<2\n")), "001090000002") == ""
    # Căn cước 2024: ngày cấp rơi xuống dòng dưới nhãn, không nhầm với ngày hết hạn.
    moi = ("Ngày, tháng, năm hết hạn / Date of expiry: 05/03/2040\nNgày, tháng, năm cấp / Date of issue:\n"
           "10/08/2024\nIDVNM0900000022001090000002<<2\n")
    assert mapper._card_back_issue_date(_ocr(("a.jpg", moi)), "001090000002") == "10/08/2024"
