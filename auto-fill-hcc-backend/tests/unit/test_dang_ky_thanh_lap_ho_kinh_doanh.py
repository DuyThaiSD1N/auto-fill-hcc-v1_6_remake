"""Đăng ký thành lập hộ kinh doanh (1.001612) trên Cổng DVC quốc gia mới — pipeline dang_ky_thanh_lap_ho_kinh_doanh."""
import asyncio
import json
from pathlib import Path

from app.pipelines.dang_ky_thanh_lap_ho_kinh_doanh.attach import planner as attach
from app.pipelines.dang_ky_thanh_lap_ho_kinh_doanh.attach.dinh_kem_khong_tach import planner as khong_tach
from app.pipelines.dang_ky_thanh_lap_ho_kinh_doanh.attach.dinh_kem_tach import planner as tach
from app.pipelines.dang_ky_thanh_lap_ho_kinh_doanh.process import mapper
from app.pipelines.dang_ky_thanh_lap_ho_kinh_doanh.process import runner as process_runner
from app.pipelines.dang_ky_thanh_lap_ho_kinh_doanh.process.schema import ALLOWED, UI_COMP_BY_NAME
from app.process.schemas import FileItem
from app.procedures.registry import PROCEDURES, get_attach_pipeline, get_pipeline
from app.services import ocr

KEY = "dang-ky-thanh-lap-ho-kinh-doanh"
ROOT = Path(__file__).resolve().parents[2]
LINKS = ROOT / "app" / "procedures" / "data" / "ke_khai_links.json"
URL = "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfb-d76d-737f-81b9-69258b07240b"

# Dữ liệu giả (không phải người thật).
CHU_HO_ID = "001190000011"
NOP_THAY_ID = "001203000022"
VALUES = {
    "ChuHo_HoTen": "LÊ THỊ HOA",
    "ChuHo_SoDinhDanh": CHU_HO_ID,
    "ChuHo_NgaySinh": "05/06/1990",
    "ChuHo_GioiTinh": "Nữ",
    "ChuHo_DanToc": "Kinh",
    "ChuHo_QuocTich": "Việt Nam",
    "ChuHo_DienThoai": "0912 000 111",
    "ChuHo_Email": "lethihoa@gmail.com",
    "ChuHo_NoiThuongTru": {"quocGia": "Việt Nam", "tinh": "Tỉnh Ninh Bình", "xa": "Phường Hoa Lư",
                           "chiTietDuoiXa": "Xóm A"},
    "ChuHo_NoiOHienTai": {"quocGia": "Việt Nam", "tinh": "Thành phố Hà Nội", "xa": "Phường Đại Mỗ",
                          "chiTietDuoiXa": "Số 2 ngõ B"},
    "HoKinhDoanh_Ten": "Hộ kinh doanh Quán Hoa",
    "TruSo_DiaChi": {"quocGia": "Việt Nam", "tinh": "Thành phố Hà Nội", "xa": "Phường Đại Mỗ",
                     "chiTietDuoiXa": "Số 9 phố C"},
    "TruSo_DienThoai": "0912000111",
    "NganhNghe_DanhSach": [
        {"ma": "56 10", "ten": "Nhà hàng và các dịch vụ ăn uống phục vụ lưu động", "chinh": True},
        {"ma": "4781", "ten": "Bán lẻ lương thực (gạo nếp)", "chinh": False},
    ],
    "Von_SoTien": "100.000.000 đồng",
    "Thue_SoLaoDong": "02",
    "Thue_PhuongPhapTinh": "Phương pháp kê khai",
    "Thue_NgayBatDau": "01/12/2026",
    "ChuTheThanhLap": "Cá nhân",
}
UY_QUYEN = {
    "UyQuyen_CoGiayUyQuyen": True,
    "UyQuyen_NguoiDuocUyQuyen_HoTen": "PHẠM VĂN NAM",
    "UyQuyen_NguoiDuocUyQuyen_SoDinhDanh": NOP_THAY_ID,
    "UyQuyen_NguoiDuocUyQuyen_DienThoai": "0988 000 222",
    "UyQuyen_NguoiDuocUyQuyen_Email": "phamnam@gmail.com",
    "UyQuyen_NguoiDuocUyQuyen_DiaChi": {"quocGia": "Việt Nam", "tinh": "Tỉnh Hưng Yên", "xa": "Xã Đông Hưng",
                                        "chiTietDuoiXa": "Thôn D"},
    "UyQuyen_NguoiDuocUyQuyen_NoiOHienTai": {"quocGia": "Việt Nam", "tinh": "Tỉnh Hưng Yên", "xa": "Xã Đông Hưng",
                                             "chiTietDuoiXa": "Thôn E"},
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

def test_registry_va_link_ke_khai_cap_xa_tren_dvcqg():
    entry = _entry(KEY)
    assert entry["supportsSplitDocuments"] is True and entry["hasAttachmentStep"] is True
    assert entry["collectFormContext"] is True
    assert entry["detect"]["urlIncludes"] == ["formalityId=019d2bfb-d76d-737f-81b9-69258b07240b"]
    assert entry["detect"]["urlScope"] == ["://dichvucong.gov.vn/nop-ho-so"]
    assert get_pipeline(KEY) is not None and get_attach_pipeline(KEY) is not None
    links = json.loads(LINKS.read_text(encoding="utf-8"))["links"]
    link = next(item for item in links if item["key"] == KEY)
    assert (link["code"], link["url"]) == ("1.001612", URL)
    # Cấp phường/xã: chọn Tỉnh + Phường/Xã như thủ tục thường, không chỉ chọn tỉnh, không chọn Sở.
    assert link["needsAgencySelect"] is True and link["autoConfirm"] is True
    assert "provinceOnlyAgency" not in link and "selectSo" not in link
    # Bản cổng HkdOnline giữ nguyên link và pipeline cũ.
    old = next(item for item in links if item["key"] == "dang-ky-kinh-doanh")
    assert old["url"] == "https://hokinhdoanh.dkkd.gov.vn/HkdOnline/Default.aspx"
    assert get_pipeline("dang-ky-kinh-doanh") is not get_pipeline(KEY)


def test_ten_o_khop_mapping():
    for name in ("citizenloaitokhai", "citizenPhone1", "citizenEmail1", "tinhThanhhientai", "phuongXahientai",
                 "citizensdt", "citizenEmail", "citizennguoidangkyhkd", "citizenngaythang", "SoDinhdanhcanhanNDK",
                 "citizenQuocTich_NDK", "citizenDantoc_NDK", "Noiohientaitinh", "tenHoKinhDoanh", "diaChiChiTiet",
                 "nganhNgheKinhDoanh", "vonKinhDoanh", "soLuongLaoDong", "phuongPhapTinhThue", "doiTuongThanhLap"):
        assert name in UI_COMP_BY_NAME, name
    assert UI_COMP_BY_NAME["nganhNgheKinhDoanh"] == "sjs-matrix"
    assert UI_COMP_BY_NAME["khongHoatDongTaiTruSo"] == "sjs-boolean"
    # Ô tên chung trùng tiền tố giữa khối → gửi nguyên data-name kèm hậu tố.
    assert UI_COMP_BY_NAME["câu hỏi5__1761724625529"] == "sjs-dropdown"
    assert UI_COMP_BY_NAME["câu hỏi5__1779097616381"] == "sjs-text"
    assert {"ChuHo_NoiThuongTru", "ChuHo_NoiOHienTai", "ChuTheThanhLap", "NganhNghe_DanhSach"} <= ALLOWED


# ── Điền ──

def test_chu_ho_tu_nop_chi_phat_o_mo():
    fields, warnings = mapper.enrich(_fields(VALUES), _account("Lê Thị Hoa", CHU_HO_ID))
    got = _by_name(fields)
    assert fields[0]["name"] == "citizenloaitokhai"          # radio chốt trước, cổng hiện khối theo nó
    assert (got["citizenloaitokhai"]["value"], got["citizenloaitokhai"]["code"]) == (mapper.CHU_HO, "1")
    assert "default" not in got["citizenloaitokhai"]
    assert got["citizenPhone1"]["value"] == "0912000111"
    assert got["citizenEmail1"]["value"] == "lethihoa@gmail.com"
    assert got["phuongXahientai"]["value"].endswith("Đại Mỗ")
    assert got["câu hỏi1__1782221422172"]["value"] == "Số 2 ngõ B"
    # Nhân thân + thường trú cổng khoá theo tài khoản → không phát; khối ủy quyền cũng không phát.
    for name in ("citizennguoidangkyhkd", "citizensdt", "citizenEmail", "SoDinhdanhcanhanNDK"):
        assert name not in got
    assert got["tenHoKinhDoanh"]["value"] == "HỘ KINH DOANH QUÁN HOA"
    assert got["diaChiChiTiet"]["value"] == "Số 9 phố C"
    assert got["vonKinhDoanh"]["value"] == "100000000"
    assert got["soLuongLaoDong"]["value"] == "2"
    assert got["ngayBatDauHoatDong"]["value"] == "01/12/2026"
    assert (got["doiTuongThanhLap"]["value"], got["doiTuongThanhLap"]["code"]) == ("Cá nhân", "CA_NHAN")
    assert got["phuongPhapTinhThue"]["onlyIfEmpty"] is True
    # Hình thức nhận kết quả mặc định option thứ 2 của cổng (ô cc-select ngoài form SurveyJS).
    assert (got["hinhThucNhanKetQua"]["value"], got["hinhThucNhanKetQua"]["comp"]) == (
        "Trả kết quả tại bộ phận tiếp nhận và trả kết quả", "dvc-result-method")
    assert not any("nhập tay" in w and "người nộp" in w for w in warnings)


def test_ten_ho_kinh_doanh_bat_dau_bang_ho_kinh_doanh_in_hoa_dau_theo_ocr():
    # Cổng chỉ nhận tên bắt đầu bằng "HỘ KINH DOANH", chữ IN HOA, số và vài ký tự.
    assert mapper.business_name("Quán Hoa!", "") == ("HỘ KINH DOANH QUÁN HOA", False)
    assert mapper.business_name("HỘ KINH DOANH  QUÁN HOA", "") == ("HỘ KINH DOANH QUÁN HOA", False)
    # LLM / lượt sửa dấu làm mất dấu → dòng tên trên OCR cùng chữ thì lấy theo OCR.
    ocr = "1. Tên hộ kinh doanh:\nTên hộ kinh doanh viết bằng tiếng Việt (ghi bằng chữ in hoa): QUÁN CƠM THÀNH ĐẠT\n"
    assert mapper.business_name("QUAN COM THANH ĐẠT", "", ocr) == ("HỘ KINH DOANH QUÁN CƠM THÀNH ĐẠT", False)
    # OCR khác chữ (đọc sai) → giữ tên LLM.
    assert mapper.business_name("QUÁN HOA", "", ocr) == ("HỘ KINH DOANH QUÁN HOA", False)
    # Không có tên → tên chủ hộ, ô vàng.
    assert mapper.business_name("", "Lê Thị Hoa") == ("HỘ KINH DOANH LÊ THỊ HOA", True)
    fields, _ = mapper.enrich(_fields({**VALUES, "HoKinhDoanh_Ten": "QUAN HOA"}),
                              {"_ocr_text": ocr.replace("QUÁN CƠM THÀNH ĐẠT", "QUÁN HOA")})
    assert _by_name(fields)["tenHoKinhDoanh"]["value"] == "HỘ KINH DOANH QUÁN HOA"


def test_nganh_nghe_ma_chuan_ten_chuan_chi_tiet_va_mot_nganh_chinh():
    lines = _by_name(mapper.enrich(_fields(VALUES), _account("Lê Thị Hoa", CHU_HO_ID))[0])["nganhNgheKinhDoanh"]["value"]
    assert [(r["ma"], r["chinh"]) for r in lines] == [("5610", True), ("4781", False)]
    # Tên trên giấy chỉ là tên chuẩn của mã → không ghi chi tiết; ghi thêm mặt hàng thì giữ làm chi tiết.
    assert lines[0]["chiTiet"] == ""
    assert lines[1]["chiTiet"] == "Bán lẻ lương thực (gạo nếp)"
    assert lines[1]["ten"] and lines[1]["ten"] != lines[1]["chiTiet"]


def test_nganh_thieu_ma_bao_chon_tay():
    values = {**VALUES, "NganhNghe_DanhSach": [{"ma": "", "ten": "Bán nước mía", "chinh": False}]}
    fields, warnings = mapper.enrich(_fields(values), {})
    row = _by_name(fields)["nganhNgheKinhDoanh"]["value"][0]
    assert row == {"ma": "", "ten": "Bán nước mía", "chiTiet": "Bán nước mía", "chinh": True}
    assert any("chưa có mã ngành" in w for w in warnings)


def test_nguoi_duoc_uy_quyen_nop_phat_khoi_nguoi_nop_va_khoi_chu_ho():
    fields, warnings = mapper.enrich(_fields({**VALUES, **UY_QUYEN}), _account("Phạm Văn Nam", NOP_THAY_ID))
    got = _by_name(fields)
    assert (got["citizenloaitokhai"]["value"], got["citizenloaitokhai"]["code"]) == (mapper.UY_QUYEN, "2")
    assert got["citizensdt"]["value"] == "0988000222"
    assert got["citizenEmail"]["value"] == "phamnam@gmail.com"
    assert got["câu hỏi3__1761724625529"]["value"] == "Thôn E"           # nơi ở hiện tại theo giấy ủy quyền
    assert "default" not in got["câu hỏi3__1761724625529"]
    assert got["citizennguoidangkyhkd"]["value"] == "LÊ THỊ HOA"
    assert got["citizenngaythang"]["value"] == "05/06/1990"
    assert got["citizengioitinhnguoidangky"]["value"] == "Nữ"
    assert got["SoDinhdanhcanhanNDK"]["value"] == CHU_HO_ID
    assert got["câu hỏi5__1779097616381"]["value"] == "0912000111"       # điện thoại chủ hộ
    assert got["citizenQuocTich_NDK"]["value"] == "Việt Nam" and "default" not in got["citizenQuocTich_NDK"]
    assert got["citizenDantoc_NDK"]["value"] == "Kinh"
    assert got["Diachichitietnoithuongtrunguoidangky"]["value"] == "Xóm A"
    assert got["Noiohientaichitiet"]["value"] == "Số 2 ngõ B"
    # Khối chủ hộ tự nộp ẩn khi chọn ủy quyền → không phát.
    assert "citizenPhone1" not in got and "tinhThanhhientai" not in got


def test_khong_co_moc_tai_khoan_theo_giay_uy_quyen_o_vang():
    got = _by_name(mapper.enrich(_fields({**VALUES, **UY_QUYEN}), {})[0])
    assert got["citizenloaitokhai"]["code"] == "2" and got["citizenloaitokhai"]["default"] is True
    got = _by_name(mapper.enrich(_fields(VALUES), {})[0])
    assert got["citizenloaitokhai"]["code"] == "1" and got["citizenloaitokhai"]["default"] is True


def test_tai_khoan_khac_ca_chu_ho_lan_ben_duoc_uy_quyen_khong_lay_lien_he():
    fields, warnings = mapper.enrich(_fields({**VALUES, **UY_QUYEN}), _account("Người Khác", "001299000033"))
    got = _by_name(fields)
    assert got["citizenloaitokhai"]["code"] == "2"
    assert "citizensdt" not in got and "citizenEmail" not in got
    assert mapper.ACCOUNT_WARNING in warnings
    assert got["SoDinhdanhcanhanNDK"]["value"] == CHU_HO_ID


def test_noi_o_hien_tai_trong_thi_lay_thuong_tru_o_vang():
    values = {k: v for k, v in VALUES.items() if k != "ChuHo_NoiOHienTai"}
    got = _by_name(mapper.enrich(_fields(values), _account("Lê Thị Hoa", CHU_HO_ID))[0])
    assert got["câu hỏi1__1782221422172"]["value"] == "Xóm A" and got["câu hỏi1__1782221422172"]["default"] is True


def test_dia_chi_thue_chi_phat_khi_khac_tru_so():
    same = {**VALUES, "Thue_DiaChiNhanThongBao": dict(VALUES["TruSo_DiaChi"])}
    assert "câu hỏi7__1782890713158" not in _by_name(mapper.enrich(_fields(same), {})[0])
    other = {**VALUES, "Thue_DiaChiNhanThongBao": {"quocGia": "Việt Nam", "tinh": "Thành phố Hà Nội",
                                                   "xa": "Phường Đại Mỗ", "chiTietDuoiXa": "Số 77 phố K"}}
    got = _by_name(mapper.enrich(_fields(other), {})[0])
    assert got["câu hỏi7__1782890713158"]["value"] == "Số 77 phố K"
    assert "câu hỏi8__1782890713158" in got and "câu hỏi9__1782890713158" in got


def test_phuong_phap_khoan_canh_bao_ho_gia_dinh_va_khong_kinh_doanh_tai_tru_so():
    values = {**VALUES, "Thue_PhuongPhapTinh": "Phương pháp khoán", "ChuTheThanhLap": "Các thành viên hộ gia đình",
              "TruSo_KhongKinhDoanhTaiTruSo": True}
    fields, warnings = mapper.enrich(_fields(values), {})
    got = _by_name(fields)
    assert mapper.KHOAN_WARNING in warnings and mapper.HO_GIA_DINH_WARNING in warnings
    assert (got["doiTuongThanhLap"]["value"], got["doiTuongThanhLap"]["code"]) == (mapper.HO_GIA_DINH, "HO_GIA_DINH")
    assert got["khongHoatDongTaiTruSo"]["value"] is True


def test_cau_hinh_theo_tai_khoan_phuong_lieu_bo_ngay_bat_dau():
    user = {"tinh": "Tỉnh Bắc Ninh", "xa": "Phường Phương Liễu"}
    options = mapper.with_account_process_options({}, user, KEY)
    assert options[mapper.SKIP_START_DATE_OPTION] is True
    assert "ngayBatDauHoatDong" not in _by_name(mapper.enrich(_fields(VALUES), options)[0])
    # Thủ tục khác / client tự gửi cờ: server luôn ghi đè.
    assert mapper.SKIP_START_DATE_OPTION not in mapper.with_account_process_options(
        {mapper.SKIP_START_DATE_OPTION: True}, user, "dang-ky-kinh-doanh")
    assert mapper.SKIP_START_DATE_OPTION not in mapper.with_account_process_options(
        {mapper.SKIP_START_DATE_OPTION: True}, {"tinh": "Hà Nội", "xa": "Đại Mỗ"}, KEY)


def test_runner_doc_on_huy_luot_anh_va_tra_canh_bao(monkeypatch):
    async def fake_run(files_by_role, **kwargs):
        assert kwargs["fields"] is process_runner.FIELDS and kwargs["options"]["formContext"]
        return {"fields": _fields(VALUES), "ocr_text": "", "errors": [], "extracted": {}}

    async def fake_vision(_files):
        await asyncio.sleep(10)  # đọc ổn → lượt ảnh bị huỷ, không chờ
        return {"so_dinh_danh": "999999999999"}

    async def fake_diacritics(_name):
        return None

    monkeypatch.setattr(process_runner.runner, "run", fake_run)
    monkeypatch.setattr(process_runner.vision, "read_application", fake_vision)
    monkeypatch.setattr(process_runner.ten_ho, "fix_diacritics", fake_diacritics)
    res = asyncio.run(asyncio.wait_for(process_runner.run({"files": []}, _account("Lê Thị Hoa", CHU_HO_ID)), 5))
    assert "visionPatched" not in res["extracted"]
    assert _by_name(res["fields"])["citizenloaitokhai"]["code"] == "1"
    assert any("trụ sở" in e for e in res["errors"])


# ── Đính kèm ──

def _files(*names):
    return [FileItem(name=n, type="application/pdf", dataUrl="data:,", role="") for n in names]


def _ocr_pages(*pages: str) -> str:
    return "\n".join(f"───── Trang {i + 1}/{len(pages)} ─────\n{t}" for i, t in enumerate(pages))


_HO_SO = _ocr_pages("GIẤY ĐỀ NGHỊ ĐĂNG KÝ HỘ KINH DOANH", "2. Trụ sở", "6. Chủ thể", "Chú thích",
                    "GIẤY ỦY QUYỀN", "IV. CAM KẾT")


def _patch_ocr(monkeypatch, text=_HO_SO):
    async def fake_ocr(files):
        return [{"text": text} for _ in files]

    monkeypatch.setattr(ocr, "ocr_per_file", fake_ocr)


def test_khong_tach_giay_de_nghi_dau_dong_1_uy_quyen_ho_gia_dinh_dong_2(monkeypatch):
    _patch_ocr(monkeypatch, "GIẤY TỜ")

    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": [
            {"index": 0, "docType": "can_cuoc", "documentName": "Căn cước", "matThe": "truoc", "chuThe": "Lê Thị Hoa"},
            {"index": 1, "docType": "uy_quyen_nop_ho_so", "documentName": "Giấy ủy quyền"},
            {"index": 2, "docType": "giay_de_nghi", "documentName": "Giấy đề nghị đăng ký hộ kinh doanh"},
            {"index": 3, "docType": "uy_quyen_ho_gia_dinh", "documentName": "Văn bản ủy quyền"},
        ]})

    monkeypatch.setattr(khong_tach.client, "chat", fake_chat)
    for options in ({}, {"splitDocuments": "true"}, None):
        res = asyncio.run(attach.plan(_files("cccd.jpg", "uq.pdf", "gdn.pdf", "uqhgd.pdf"), options))
        got = [(i["fileIndex"], i["slotIndex"]) for i in res["attachments"]]
        assert got == [(2, 0), (0, 0), (3, 1), (1, 2)]
        for item in res["attachments"]:
            assert item["target"] == "fixed-slot" and "sourceSegments" not in item
        assert res["attachments"][2]["slotName"] == khong_tach.ROW_UY_QUYEN_HGD["slotName"]
        # Giấy ủy quyền nộp hồ sơ: chọn "Trường hợp ủy quyền…" trước, đính dòng "ủy quyền cho cá nhân", không thấy dòng
        # thì về dòng Giấy đề nghị. Chỉ mục này mang trường hợp thực hiện.
        uq = res["attachments"][3]
        assert uq["slotName"] == "ủy quyền cho cá nhân"
        assert uq["fallbackSlotName"] == "Giấy đề nghị đăng ký hộ kinh doanh"
        assert (uq["executionCase"], uq["executionCasePrefer"]) == ("Trường hợp ủy quyền thực hiện thủ tục", "ca nhan")
        assert [i for i in res["attachments"] if i.get("executionCase")] == [uq]
        # Router trả kế hoạch qua AttachmentPlanResp: thiếu khai field thì response_model lược mất (chạy thật 27/11:
        # extension không nhận executionCase → không chọn trường hợp, giấy ủy quyền rơi dòng 1).
        from app.attachments.schemas import AttachmentPlanResp

        sent = AttachmentPlanResp.model_validate(res).model_dump(exclude_none=True)["attachments"][3]
        for key in ("executionCase", "executionCasePrefer", "fallbackSlotName", "slotName"):
            assert sent[key] == uq[key], key


def test_khong_tach_llm_loi_van_dinh_du_tep_vao_dong_1(monkeypatch):
    _patch_ocr(monkeypatch, "GIẤY TỜ")

    async def fake_chat(*_a, **_k):
        raise RuntimeError("llm hỏng")

    monkeypatch.setattr(khong_tach.client, "chat", fake_chat)
    res = asyncio.run(attach.plan(_files("gdn.pdf", "uq.pdf"), {}))
    assert [(i["documentName"], i["slotIndex"]) for i in res["attachments"]] == [("gdn", 0), ("uq", 0)]


def test_tach_dung_dong_khong_sot_trang(monkeypatch):
    _patch_ocr(monkeypatch)

    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pages": [1, 2, 3, 4], "docType": "giay_de_nghi",
             "documentName": "Giấy đề nghị đăng ký hộ kinh doanh"},
            {"fileIndex": 0, "pages": [5], "docType": "uy_quyen_nop_ho_so", "documentName": "Giấy ủy quyền"},
            # trang 6 LLM bỏ sót → gộp vào giấy liền trước (giấy ủy quyền), không mất trang.
        ]})

    monkeypatch.setattr(tach.client, "chat", fake_chat)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    assert [(i["documentName"], i["slotIndex"], i["sourceSegments"]) for i in res["attachments"]] == [
        ("Giấy đề nghị đăng ký hộ kinh doanh", 0, [{"fileIndex": 0, "pageIndexes": [0, 1, 2, 3]}]),
        ("Giấy ủy quyền", 2, [{"fileIndex": 0, "pageIndexes": [4, 5]}]),
    ]
    covered = sorted(p for i in res["attachments"] for s in i["sourceSegments"] for p in s["pageIndexes"])
    assert covered == [0, 1, 2, 3, 4, 5]


def test_tach_giay_de_nghi_mot_tep_thi_dinh_nguyen_tep(monkeypatch):
    _patch_ocr(monkeypatch, _ocr_pages("GIẤY ĐỀ NGHỊ ĐĂNG KÝ HỘ KINH DOANH", "2. Trụ sở", "6. Chủ thể", "Chú thích"))

    async def fake_chat(*_a, **_k):
        return json.dumps({"documents": [
            {"fileIndex": 0, "pages": [1, 2, 3, 4], "docType": "giay_de_nghi",
             "documentName": "Giấy đề nghị đăng ký hộ kinh doanh"},
        ]})

    monkeypatch.setattr(tach.client, "chat", fake_chat)
    res = asyncio.run(attach.plan(_files("gdn.pdf"), {"splitDocuments": True}))
    assert len(res["attachments"]) == 1 and "sourceSegments" not in res["attachments"][0]
    assert res["attachments"][0]["slotIndex"] == 0


def test_tach_loi_quay_ve_khong_tach(monkeypatch):
    _patch_ocr(monkeypatch)

    async def fake_chat(messages, **_):
        if "TỪNG TRANG" in messages[0]["content"]:
            raise RuntimeError("llm hỏng")
        return '{"documents":[{"index":0,"docType":"giay_de_nghi","documentName":"Giấy đề nghị đăng ký hộ kinh doanh"}]}'

    monkeypatch.setattr(tach.client, "chat", fake_chat)
    res = asyncio.run(attach.plan(_files("hoso.pdf"), {"splitDocuments": True}))
    item = res["attachments"][0]
    assert item["slotIndex"] == 0 and "sourceSegments" not in item
    assert any("(tách)" in e for e in res["errors"])


# ── Trợ lý người dân ──

def test_tro_ly_cung_key_trang_mot_trang_chon_tinh_xa_toan_quoc():
    from app.channels.handfree import procedure_registry as handfree
    from app.channels.handfree.chat.field_review import registry as field_review
    from app.channels.handfree.chat.procedure_picker.prompt import PROCEDURE_HINTS
    from app.channels.handfree.chat.script_mong import PROCEDURE_HMONG

    proc = handfree.get_procedure(KEY)
    assert proc["detect"] == _entry(KEY)["detect"]
    assert proc["flowProfile"] == "tu-phap-moi" and proc["singlePageDossier"] is True
    assert proc["needsAgencySelect"] is True and "agencyProvinceOnly" not in proc
    assert proc["supportsSplitDocuments"] is True and proc["keKhaiUrl"] == URL
    assert "businessWorkflow" not in proc                      # không đi luồng HkdOnline
    assert "provinceOnly" not in proc and handfree._HOAN_THIEN_THEO_TINH[KEY] == handfree._TAT_CA
    assert KEY in PROCEDURE_HINTS and KEY in PROCEDURE_HMONG
    assert field_review.get(KEY) is not None
    assert handfree.procedure_code(proc) == "1.001612"
    # Bản HkdOnline của trợ lý giữ nguyên.
    old = handfree.get_procedure("dang-ky-kinh-doanh")
    assert old["businessWorkflow"] == "create" and old["keKhaiUrl"].startswith("https://hokinhdoanh.dkkd.gov.vn")
