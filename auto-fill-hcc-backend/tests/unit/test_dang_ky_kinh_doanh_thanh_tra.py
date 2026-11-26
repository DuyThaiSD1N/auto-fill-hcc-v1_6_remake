"""Lớp soát (điền đợt 2) của đăng ký thành lập hộ kinh doanh: các thanh tra địa chỉ, ngành nghề, nhân thân, tên hộ.
Dữ liệu giả."""

import asyncio

from app.pipelines._shared.thanh_tra import engine, toa_an
from app.pipelines._shared.thanh_tra.ho_so import Case
from app.pipelines.dang_ky_kinh_doanh.process import runner as hkd_runner
from app.pipelines.dang_ky_kinh_doanh.thanh_tra import dia_chi, dinh_danh, dot_hai, nganh_nghe, sync, ten_ho, trang
from app.procedures.registry import PROCEDURES
from app.second_pass import service as second_pass

DON = """Mẫu số 1
CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
GIẤY ĐỀ NGHỊ ĐĂNG KÝ HỘ KINH DOANH
Kính gửi: UBND xã Ka Đô
Tôi là (ghi họ tên bằng chữ in hoa): NGUYỄN VĂN AN
Sinh ngày: 02/03/1990
Số định danh cá nhân: 068090000001
Nơi thường trú:
Số nhà/phòng, ngách/hẻm, ngõ/kệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn: …
Xã/Phường/Đặc khu: …
Tỉnh/Thành phố trực thuộc trung ương: …
Nơi ở hiện tại:
Số nhà/phòng, ngách/hẻm, ngõ/kệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn: Số 5, thôn Lộc Khê
Xã/Phường/Đặc khu: …
Tỉnh/Thành phố trực thuộc trung ương: Lâm Đồng
Đăng ký hộ kinh doanh do tôi là chủ hộ với các nội dung sau:
1. Tên hộ kinh doanh:
Tên hộ kinh doanh viết bằng tiếng Việt (ghi bằng chữ in hoa): QUÁN LÂU AN
2. Trụ sở của hộ kinh doanh:
───── Trang 2/3 ─────
2
Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ấp/thôn:
Số 5, thôn Lạc Khê
Xã/Phường/Đặc khu: Ka Pơ
Tỉnh/Thành phố trực thuộc trung ương: Lâm Đồng
Điện thoại: 0900000001
3. Ngành, nghề kinh doanh¹:
| STT | Tên ngành | Mã ngành² | Ngành, nghề kinh doanh chính³ |
|---|---|---|---|
| 1 | Nhà hàng | 5610 | X |
| 2 | Bán lẻ đồ uống | 4723 | |
| 3 | Ghi mã lạ | 9999 | |
4. Vốn kinh doanh:
Tổng số (bằng số, bằng chữ, VNĐ): 50.000.000
5. Thông tin đăng ký thuế:
5.1. Địa chỉ nhận thông báo thuế (chỉ kê khai nếu địa chỉ nhận thông báo thuế khác địa chỉ trụ sở):
Số nhà/phòng, ngách/hẻm, ngõ/kiệt, đường/phố/đại lộ, tổ/xóm/ap/thôn: ....
Xã/Phường/Đặc khu: ....
Tỉnh/Thành phố trực thuộc trung ương: ....
"""
UY_QUYEN = """CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
GIẤY ỦY QUYỀN
Bên ủy quyền:
Họ và tên: NGUYỄN VĂN AN
Địa chỉ: Thôn Lạc Khê, xã Ka Đô, tỉnh Lâm Đồng
Bên được ủy quyền:
Họ và tên: TRẦN THỊ BÌNH
Địa chỉ: Thôn Lạc Khê, xã Ka Đô, tỉnh Lâm Đồng
1. Nội dung và phạm vi ủy quyền:
"""
CARD = """CĂN CƯỚC
Số / No.: 068090000007
Họ, chữ đệm và tên / Full name: NGUYỄN VĂN AN
Ngày sinh / Date of birth: 02/08/1990
"""
DOCS = [{"name": "uq.pdf", "text": UY_QUYEN}, {"name": "don.pdf", "text": DON}, {"name": "cccd.pdf", "text": CARD}]
VALUES = {
    "ChuHo_HoTen": "NGUYỄN VĂN AN", "ChuHo_SoDinhDanh": "068090000001", "ChuHo_NgaySinh": "02/03/1990",
    "ChuHo_DiaChi": {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Ka Đô", "diaChi": "Số 5, thôn Lộc Khê"},
    "TruSo_DiaChi": {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Ka Pơ", "diaChi": "Số 5, thôn Lạc Khê"},
    "HoKinhDoanh_Ten": "QUÁN LÂU AN",
    "NganhNghe_DanhSach": [{"ma": "5610", "ten": "Nhà hàng", "chinh": True}],
    "NganhNghe_MaChinh": "5610",
    "UyQuyen_NguoiDuocUyQuyen_HoTen": "TRẦN THỊ BÌNH",
}


def test_capability_va_registry_hkd():
    entry = next(p for p in PROCEDURES if p["key"] == "dang-ky-kinh-doanh")
    assert entry["secondPass"] == "hkd"
    assert second_pass.capability(entry) == "secondPassHkd"


def test_trang_giay_de_nghi_nhieu_trang_va_loai_giay():
    kinds = [(page["doc"], page["kind"]) for page in trang.pages(DOCS)]
    assert kinds == [(1, "tu_lap"), (2, "don"), (2, "don"), (3, "ban_in")]


def test_hai_giay_de_nghi_cua_hai_nguoi_chi_giu_giay_cua_chu_ho():
    other = DON.replace("NGUYỄN VĂN AN", "LÊ VĂN CƯỜNG").replace("068090000001", "068091000002").replace("0900000001", "0900000009")
    pages = trang.pages([{"name": "a", "text": other}, {"name": "b", "text": DON}], VALUES)
    assert [page["kind"] for page in pages] == ["khac", "khac", "don", "don"]
    # Không biết giấy nào của chủ hộ → bỏ cả hai.
    pages = trang.pages([{"name": "a", "text": other}, {"name": "b", "text": DON}], {})
    assert {page["kind"] for page in pages} == {"khac"}


def test_cat_khoi_dia_chi_cua_tung_o():
    lines = dia_chi.lines_of(trang.pages(DOCS, VALUES), VALUES)
    assert lines["TruSo_DiaChi"]["text"] == "Số 5, thôn Lạc Khê, Ka Pơ, Lâm Đồng"
    assert lines["ChuHo_DiaChi"]["text"] == "Số 5, thôn Lộc Khê, Lâm Đồng"  # nơi ở hiện tại có giá trị thì thắng thường trú
    assert "Thue_DiaChiNhanThongBao" not in lines  # mục 5.1 bỏ trống
    assert lines["UyQuyen_NguoiDuocUyQuyen_DiaChi"]["text"] == "Thôn Lạc Khê, xã Ka Đô, tỉnh Lâm Đồng"
    # Phần "Bên được ủy quyền" ghi người khác (giấy ủy quyền tải lẫn) → không lấy.
    other = {**VALUES, "UyQuyen_NguoiDuocUyQuyen_HoTen": "PHẠM VĂN DŨNG"}
    assert "UyQuyen_NguoiDuocUyQuyen_DiaChi" not in dia_chi.lines_of(trang.pages(DOCS, other), other)


def test_ho_so_tai_lan_hai_giay_de_nghi_thi_the_va_giay_uy_quyen_khong_lam_bang_chung():
    other = DON.replace("NGUYỄN VĂN AN", "LÊ VĂN CƯỜNG").replace("068090000001", "068091000002").replace(
        "0900000001", "0900000009")
    pages = trang.pages([{"name": "x", "text": other}, *DOCS], VALUES)
    assert {page["kind"] for page in pages if page["doc"] in (2, 4)} == {"khac"}  # giấy ủy quyền, thẻ
    assert dinh_danh.number_finding("NGUYỄN VĂN AN", "068090000001", pages, "02/03/1990") is None
    assert dia_chi.detail_fix("Số 5, thôn Lộc Khê", pages) is None


def test_ten_thon_doc_lech_so_voi_trang_giay_khac_thi_sua():
    fix = dia_chi.detail_fix("Số 5, thôn Lộc Khê", trang.pages(DOCS, VALUES))
    assert fix["diaChi"] == "Số 5, thôn Lạc Khê"
    # Cách viết có trên trang giấy khác thì giữ.
    assert dia_chi.detail_fix("Số 5, thôn Lạc Khê", trang.pages(DOCS, VALUES)) is None


def test_xa_khung_chung_chon_phai_la_chu_o_dong_xa_cua_khoi():
    assert dia_chi._ward_on_block("Xã Ka Đô", {"block": {"xa": "Ka Pơ"}, "line": "", "text": "Số 5, Ka Pơ"})
    assert not dia_chi._ward_on_block("Phường Nam Hoa Lư", {"block": {"xa": "Sơn Hà Tây Hoa Lư"}, "line": "",
                                                           "text": "Thôn A, Sơn Hà Tây Hoa Lư"})
    assert not dia_chi._ward_on_block("Xã Ka Đô", None)  # ô không có khối trên giấy


def test_xa_cua_A_co_tren_giay_khac_khong_tinh_la_lay_nham():
    block = {"xa": "Đơn Dương", "tinh": "Lâm Đồng"}
    current = {"tinh": "Lâm Đồng", "xa": "Ka Đô", "diaChi": "Thôn A"}
    proposed = {"tinh": "Lâm Đồng", "xa": "Xã Đơn Dương", "diaChi": "Thôn A"}
    assert dia_chi.faults(current, proposed, block, "Nơi thường trú: Thôn A, Ka Đô, Lâm Đồng")[:1] == []
    assert dia_chi.faults(current, proposed, block, "")[0].startswith('xã "Ka Đô" của A không phải chữ')


def test_nhan_than_so_va_ngay_sinh_theo_the_cua_chinh_nguoi_do_khop_nam_trong_so():
    pages = trang.pages(DOCS, VALUES)
    # Thẻ in 068090000007 (lệch 1 số), năm 1990 khớp mã năm "90" → sửa.
    assert dinh_danh.number_finding("NGUYỄN VĂN AN", "068090000001", pages, "02/03/1990")[0] == "068090000007"
    # Ngày sinh A khác năm mã hoá trong số trên thẻ → thẻ không đủ căn cứ.
    assert dinh_danh.number_finding("NGUYỄN VĂN AN", "068090000001", pages, "02/03/1985") is None
    assert dinh_danh.date_finding("NGUYỄN VĂN AN", "02/03/1990", pages, "068090000001")[0] == "02/08/1990"
    bad_card = CARD.replace("02/08/1990", "02/08/1930")
    pages = trang.pages([DOCS[0], DOCS[1], {"name": "c", "text": bad_card}], VALUES)
    assert dinh_danh.date_finding("NGUYỄN VĂN AN", "02/03/1990", pages, "068090000001") is None


def test_ho_ten_lech_dau_chi_tren_giay_chinh_thi_theo_trang_giay_khac():
    don = DON.replace("NGUYỄN VĂN AN", "NGUYỄN VẤN AN", 1)
    pages = trang.pages([DOCS[0], {"name": "d", "text": don}, DOCS[2]], {**VALUES, "ChuHo_HoTen": "NGUYỄN VẤN AN"})
    hit = dinh_danh.name_finding("NGUYỄN VẤN AN", "don", pages)
    assert hit[0] == "NGUYỄN VĂN AN"
    assert dinh_danh.name_finding("NGUYỄN VĂN AN", "don", trang.pages(DOCS, VALUES)) is None


def test_nganh_nghe_them_dong_co_ma_trong_danh_muc_ma_luot_trich_bo_sot():
    rows, section, _ = nganh_nghe.table(trang.pages(DOCS, VALUES))
    assert [row["ma"] for row in rows] == ["5610", "4723", "9999"]
    fixed, reasons, quote = nganh_nghe.proposal(VALUES, rows, section, [])
    assert [row["ma"] for row in fixed] == ["5610", "4723"]  # 9999 không có trong danh mục ngành cấp 4
    assert "4723" in quote and len(reasons) == 1
    full = {**VALUES, "NganhNghe_DanhSach": [{"ma": "5610"}, {"ma": "4723"}]}
    assert nganh_nghe.proposal(full, rows, section, [])[0] == []


def test_ten_ho_chi_khac_dau_voi_luot_doc_anh_thi_dua_toa():
    case = Case(DOCS, "", dict(VALUES), {"_vision": {"ten_ho": "Quán Lẩu An"}})
    found = asyncio.run(ten_ho.find(ten_ho.INSPECTOR, case, ""))
    assert found and found[0].values == {"HoKinhDoanh_Ten": "QUÁN LẨU AN"}
    for seen in ("Quán Lâu Anh", "", "QUÁN LÂU AN"):
        case = Case(DOCS, "", dict(VALUES), {"_vision": {"ten_ho": seen}})
        assert asyncio.run(ten_ho.find(ten_ho.INSPECTOR, case, "")) == []


def test_ten_ho_de_xuat_giu_dau_cau_va_khoang_trang_cua_A():
    """Lượt đọc ảnh chèn / bớt dấu cách quanh dấu gạch: đề xuất chỉ lấy dấu thanh của lượt đọc ảnh, giữ chữ của A."""
    values = {**VALUES, "HoKinhDoanh_Ten": "QUÁN CƠM-LÂU AN"}
    docs = [{"name": "don.pdf", "text": DON.replace("QUÁN LÂU AN", "QUÁN CƠM-LÂU AN")}]
    case = Case(docs, "", values, {"_vision": {"ten_ho": "Quán cơm- Lẩu An"}})
    found = asyncio.run(ten_ho.find(ten_ho.INSPECTOR, case, ""))
    assert found and found[0].values == {"HoKinhDoanh_Ten": "QUÁN CƠM-LẨU AN"}


def test_luat_ten_ho_noi_toa_nguon_doc_anh_khong_co_nguyen_van_ocr():
    assert "KHÔNG có nguyên văn trong OCR là đương nhiên" in ten_ho.RULES


def test_chep_chu_ho_da_sua_sang_khoi_cung_nguoi():
    before = {"ChuHo_HoTen": "NGUYỄN VẤN AN", "NguoiNop_HoTen": "NGUYỄN VẤN AN", "UyQuyen_NguoiUyQuyen_HoTen": "LÊ C",
              "HoKinhDoanh_Ten": "NGUYỄN VẤN AN"}
    after = sync(before, {**before, "ChuHo_HoTen": "NGUYỄN VĂN AN"})
    assert after["NguoiNop_HoTen"] == "NGUYỄN VĂN AN"
    assert after["UyQuyen_NguoiUyQuyen_HoTen"] == "LÊ C"  # khối ghi người khác → không đè
    assert after["HoKinhDoanh_Ten"] == "NGUYỄN VĂN AN"


def test_sua_ma_dong_nganh_chinh_thi_nganh_chinh_theo_ma_moi():
    before = {"NganhNghe_MaChinh": "5611", "NganhNghe_DanhSach": [{"ma": "5611", "ten": "Nhà hàng", "chinh": False}]}
    after = sync(before, {**before, "NganhNghe_DanhSach": [{"ma": "5610", "ten": "Nhà hàng", "chinh": False}]})
    assert after["NganhNghe_MaChinh"] == "5610"


def test_dot_hai_tra_nguyen_trang_co_doi(monkeypatch):
    async def split(lines, counter, title):
        return {"TruSo_DiaChi": {"tinh": "Lâm Đồng", "xa": "Xã Ka Đô", "chiTietDuoiXa": "Số 5, thôn Lạc Khê"}}

    async def no_wards(*args, **kwargs):
        return {}

    async def judge(case, disputes, *, title):
        return {d.id: ("B", "") for d in disputes}

    monkeypatch.setattr(dia_chi.common, "_split", split)
    monkeypatch.setattr(dia_chi.ten_xa, "fixes", no_wards)
    monkeypatch.setattr(toa_an, "judge", judge)
    raw = [{"name": name, "value": value} for name, value in VALUES.items()]
    out = asyncio.run(dot_hai.patch(DOCS, raw, {}, vision={"ten_ho": "Quán Lẩu An"}))
    by_page: dict = {}
    for field in out["fields"]:
        by_page.setdefault(field["page"], {})[field["name"]] = field["value"]
    assert by_page["dia-chi"]["ctl00$C$ADDRCtl$WARD_IDFld"] == "Ka Đô"
    assert by_page["chu-ho-kinh-doanh"]["ctl00$C$OWN_PCtl$PERSCtl$ADDRCCtl$STREET_NUMBERFld"] == "Số 5, thôn Lạc Khê"
    assert by_page["chu-ho-kinh-doanh"]["ctl00$C$OWN_PCtl$PERSCtl$PERS_DOC_NOFld"] == "068090000007"
    assert by_page["ten-ho-kinh-doanh"]["ctl00$C$NAMEFld"] == "QUÁN LẨU AN"
    assert "__businessLines" in by_page["nganh-nghe-kinh-doanh"]
    assert "hinh-thuc-dang-ky" not in by_page and "thong-tin-ve-von" not in by_page  # trang không đổi thì không trả


def test_runner_chi_tra_dot_hai_khi_extension_khai_nang_luc(monkeypatch):
    async def fake_run(files_by_role, **kwargs):
        if kwargs.get("context_builder"):
            await kwargs["context_builder"](DOCS, {})
        return {"fields": [{"name": "ChuHo_HoTen", "value": "NGUYỄN VĂN AN"}], "ocr_text": "", "extracted": {}}

    async def fake_vision(files):
        return {"so_dinh_danh": "068090000001"}

    async def no_fix(name):
        return None

    monkeypatch.setattr(hkd_runner.runner, "run", fake_run)
    monkeypatch.setattr(hkd_runner.vision, "read_application", fake_vision)
    monkeypatch.setattr(hkd_runner.vision, "broken_fields", lambda values, text: set())
    monkeypatch.setattr(hkd_runner.ten_ho, "fix_diacritics", no_fix)
    monkeypatch.setattr(hkd_runner.mapper, "fix_addresses_from_ocr", lambda fields, text: [])

    async def go(options):
        return await hkd_runner.run({"documents": []}, options)

    assert "_second_pass" not in asyncio.run(go({"allPages": True}))
    assert "_second_pass" not in asyncio.run(go({"page": "dia-chi", "_secondPass": True}))

    async def started_then_dropped():
        res = await go({"allPages": True, "_secondPass": True})
        second = res["_second_pass"]
        second.cancel()  # nơi gọi huỷ khi second_pass.start không chạy được
        await asyncio.sleep(0)
        return second

    assert callable(asyncio.run(started_then_dropped()))


def test_engine_chay_du_bon_thanh_tra():
    from app.pipelines.dang_ky_kinh_doanh import thanh_tra

    assert [i.key for i in thanh_tra.INSPECTORS] == ["dia_chi", "nganh_nghe", "dinh_danh", "ten_ho"]
    assert all(i.find for i in thanh_tra.INSPECTORS)
    assert engine.run is not None
