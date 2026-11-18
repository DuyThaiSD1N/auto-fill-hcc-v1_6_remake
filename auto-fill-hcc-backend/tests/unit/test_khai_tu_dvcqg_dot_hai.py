"""Thanh tra + điền đợt 2 của thủ tục đăng ký khai tử (Cổng DVC quốc gia mới) — phần mã, không gọi LLM."""

from app.pipelines._shared.thanh_tra.ho_so import Case
from app.pipelines.khai_tu_dvcqg.thanh_tra import dinh_danh

_MRZ_BACK = """Ngày, tháng, năm / Date, month, year: 23/04/2021
CỤC TRƯỞNG CỤC CẢNH SÁT QUẢN LÝ HÀNH CHÍNH VỀ TRẬT TỰ XÃ HỘI
IDVNM0601234567001160012345<<1
6001014F2601014VNM<<<<<<<<<<<0
TRAN<<THI<MAU<<<<<<<<<<<<<<<<<"""


def _case(values, *texts):
    return Case([{"name": f"g{i}.pdf", "text": text} for i, text in enumerate(texts)], "", values, {})


def test_ho_ten_nhieu_trang_ghi_hon_thi_doi_dau():
    case = _case({"NguoiMat_HoTen": "TRẦN THỊ MẪN"},
                 "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nHọ, chữ đệm, tên: TRẦN THỊ MẪN",
                 "GIẤY BÁO TỬ\nHọ, chữ đệm, tên người chết: TRẦN THỊ MẬN",
                 "BẢN CAM ĐOAN\nMẹ tôi là bà Trần Thị Mận")
    finding = dinh_danh.name_finding(case, dinh_danh.trang.pages(case.documents))
    assert finding and finding.values["NguoiMat_HoTen"] == "TRẦN THỊ MẬN"


def test_ho_ten_khong_doi_sang_ban_roi_dau_hoac_bang_trang():
    rơi = _case({"NguoiMat_HoTen": "ĐINH VĂN HẺ"}, "GIẤY BÁO TỬ\nHọ tên: DINH VAN HE", "BẢN CAM ĐOAN\nDinh Van He")
    assert dinh_danh.name_finding(rơi, dinh_danh.trang.pages(rơi.documents)) is None
    bang = _case({"NguoiMat_HoTen": "LÊ VĂN TÂM"}, "GIẤY BÁO TỬ\nHọ tên: LÊ VĂN TÂM", "BẢN CAM ĐOAN\nông Lê Văn Tám")
    assert dinh_danh.name_finding(bang, dinh_danh.trang.pages(bang.documents)) is None


def test_ho_ten_doi_chu_cai_chi_khi_trang_mang_so_cua_nguoi_chet():
    values = {"NguoiMat_HoTen": "NGUYỄN THỊ QUẾ", "NguoiMat_SoDinhDanh": "001160000011"}
    anchored = _case(values, "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nHọ tên: NGUYỄN THỊ QUẾ",
                     "GIẤY BÁO TỬ\nHọ tên: NGUYỄN THỊ QUẢ\nSố định danh: 001160000011",
                     "BẢN CAM ĐOAN\nMẹ tôi là bà Nguyễn Thị Quả, số 001160000011")
    finding = dinh_danh.name_finding(anchored, dinh_danh.trang.pages(anchored.documents))
    assert finding and finding.values["NguoiMat_HoTen"] == "NGUYỄN THỊ QUẢ"
    loose = _case(values, "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nHọ tên: NGUYỄN THỊ QUẾ",
                  "GIẤY BÁO TỬ\nHọ tên: NGUYỄN THỊ QUẢ", "BẢN CAM ĐOAN\nbà Nguyễn Thị Quả")
    assert dinh_danh.name_finding(loose, dinh_danh.trang.pages(loose.documents)) is None


def test_so_ngay_sinh_ngay_cap_theo_mrz_the_nguoi_chet():
    case = _case({"NguoiMat_HoTen": "TRẦN THỊ MẪU", "NguoiMat_SoDinhDanh": "001160012845",
                  "NguoiMat_SoGiayTo": "001160012845", "NguoiMat_NgaySinh": "1960"},
                 "CĂN CƯỚC CÔNG DÂN\nSố: 001160012345\nNgày sinh: 01/01/1960", _MRZ_BACK)
    by = {f.unit.key: f.values for f in dinh_danh.card_findings(case)}
    assert by["nguoi_mat.so_dinh_danh"] == {"NguoiMat_SoDinhDanh": "001160012345"}
    assert by["nguoi_mat.so_giay_to"] == {"NguoiMat_SoGiayTo": "001160012345"}
    assert by["nguoi_mat.ngay_sinh"] == {"NguoiMat_NgaySinh": "01/01/1960"}
    assert by["nguoi_mat.ngay_cap"] == {"NguoiMat_NgayCap": "23/04/2021"}
    # Số giấy tờ là CMND 9 số → không đụng.
    cmnd = _case({**case.values, "NguoiMat_SoGiayTo": "160012345"}, _MRZ_BACK)
    assert "nguoi_mat.so_giay_to" not in {f.unit.key for f in dinh_danh.card_findings(cmnd)}


def test_dia_chi_cu_tru_theo_dong_cua_nguoi_chet_ghi_dung_xa_hien_tai():
    from app.pipelines.khai_tu_dvcqg.thanh_tra import dia_chi
    to_khai = ("TỜ KHAI ĐĂNG KÝ KHAI TỬ\nNơi cư trú: TDP Khác Ba, phường Hòa Bình\n"
               "Đề nghị cơ quan đăng ký khai tử cho người có tên dưới đây:\nNơi cư trú cuối cùng: TDP Mới Hai, phường Hòa Bình")
    old = "GIẤY BÁO TỬ\nNơi thường trú: Thôn Cũ Một, xã Đông Lỗ, huyện Hiệp Hòa"
    value = {"quocGia": "Việt Nam", "tinh": "Bắc Ninh", "xa": "Phường Hòa Bình", "diaChi": "Thôn Cũ Một"}
    case = _case({"NguoiMat_NoiCuTru": value}, to_khai, old)
    found = dia_chi.findings_from(case)
    assert [f.values["NguoiMat_NoiCuTru"]["diaChi"] for f in found] == ["TDP Mới Hai"]
    # Dòng của người yêu cầu (trên câu "Đề nghị...") không tính; chi tiết đã có trên dòng của người chết thì giữ.
    same = _case({"NguoiMat_NoiCuTru": {**value, "diaChi": "TDP Mới Hai"}}, to_khai, old)
    assert dia_chi.findings_from(same) == []


async def test_dia_chi_xa_cat_cut_ngoai_danh_muc_sua_theo_dong_cua_nguoi_chet(monkeypatch):
    from app.pipelines._shared.thanh_tra import ten_xa
    from app.pipelines.khai_tu_dvcqg.thanh_tra import dia_chi

    async def no_answer(*args, **kwargs):
        return "{}"

    monkeypatch.setattr(ten_xa.client, "chat", no_answer)
    to_khai = ("TỜ KHAI ĐĂNG KÝ KHAI TỬ\nNơi cư trú: (2) Tổ dân phố Một, phường Nam Nha Trang, tỉnh Khánh Hòa\n"
               "Đề nghị cơ quan đăng ký khai tử cho người có tên dưới đây:\n"
               "Nơi cư trú cuối cùng: (2) Tổ dân phố Một, phường Nam Nha Trang, tỉnh Khánh Hòa")
    cut = {"quocGia": "Việt Nam", "tinh": "Khánh Hòa", "xa": "Nam", "diaChi": "Tổ dân phố Một"}
    case = _case({"NguoiMat_NoiCuTru": cut}, to_khai)
    found = await dia_chi.find(dia_chi.INSPECTOR, case, "")
    assert [f.values["NguoiMat_NoiCuTru"]["xa"] for f in found] == ["Phường Nam Nha Trang"]
    # Căn cứ là dòng có nhãn của chính người chết, không phải dòng cùng địa chỉ của người yêu cầu.
    assert found[0].quote.startswith("Nơi cư trú cuối cùng")


async def test_dia_chi_xa_trong_danh_muc_khong_hoi_model(monkeypatch):
    from app.pipelines._shared.thanh_tra import ten_xa
    from app.pipelines.khai_tu_dvcqg.thanh_tra import dia_chi

    async def must_not_call(*args, **kwargs):
        raise AssertionError("ô xã đã chọn được thì không hỏi model")

    monkeypatch.setattr(ten_xa.client, "chat", must_not_call)
    value = {"quocGia": "Việt Nam", "tinh": "Khánh Hòa", "xa": "Phường Nam Nha Trang", "diaChi": "Tổ dân phố Một"}
    case = _case({"NguoiMat_NoiCuTru": value}, "GIẤY BÁO TỬ\nNơi thường trú: Tổ dân phố Một, phường Nam Nha Trang")
    assert await dia_chi.find(dia_chi.INSPECTOR, case, "") == []


def test_ngay_chet_nhieu_trang_ghi_hon_thi_doi():
    from app.pipelines.khai_tu_dvcqg.thanh_tra import thong_tin_chet
    case = _case({"NguoiMat_NgayMat": "23/03/2025"},
                 "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nĐã chết vào lúc 10 giờ ngày 23/03/2025",
                 "GIẤY BÁO TỬ\nĐã chết vào lúc 10 giờ ngày 23/03/2005\nNgày cấp 25/03/2005",
                 "BẢN CAM ĐOAN\nBố tôi mất ngày 23 tháng 3 năm 2005")
    assert [f.values for f in thong_tin_chet.findings_from(case)] == [{"NguoiMat_NgayMat": "23/03/2005"}]
    even = _case({"NguoiMat_NgayMat": "23/03/2025"}, "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nchết ngày 23/03/2025",
                 "GIẤY BÁO TỬ\nĐã chết ngày 23/03/2005")
    assert thong_tin_chet.findings_from(even) == []


def test_ngay_chet_bo_ngay_am_lich():
    from app.pipelines.khai_tu_dvcqg.thanh_tra import thong_tin_chet
    case = _case({"NguoiMat_NgayMat": "19/06/1975"},
                 "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nĐã chết ngày 19 tháng 6 năm 1975 (tức ngày 10/5/1975 âm lịch)",
                 "BIÊN BẢN XÁC MINH\nĐã chết ngày 19/6/1975 (tức ngày 10/5/1975 âm lịch)",
                 "ĐƠN\nMẹ tôi chết ngày 10/5/1975 âm lịch", "GIẤY XÁC NHẬN\nchết ngày 10/5/1975 âm lịch")
    assert thong_tin_chet.findings_from(case) == []


def test_ngay_cap_co_tren_to_khai_thi_giu():
    case = _case({"NguoiMat_HoTen": "TRẦN THỊ MẪU", "NguoiMat_SoDinhDanh": "001160012345", "NguoiMat_NgayCap": "17/12/2021"},
                 "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nGiấy tờ tùy thân: CCCD số 001160012345 cấp ngày 17/12/2021", _MRZ_BACK)
    assert "nguoi_mat.ngay_cap" not in {f.unit.key for f in dinh_danh.card_findings(case)}


def test_hoa_so_trang_to_khai_hon_ban_cam_doan():
    case = _case({"NguoiMat_HoTen": "THÀO A DINH"}, "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nHọ, chữ đệm, tên: THÀO A DINH",
                 "BẢN CAM ĐOAN\nHọ và tên người chết: THÀO A DỊNH")
    assert dinh_danh.name_finding(case, dinh_danh.trang.pages(case.documents)) is None


def test_ngay_cap_co_tren_giay_bao_tu_thi_giu():
    case = _case({"NguoiMat_HoTen": "TRẦN THỊ MẪU", "NguoiMat_SoDinhDanh": "001160012345", "NguoiMat_NgayCap": "17/12/2021"},
                 "GIẤY BÁO TỬ\nSố: 001160012345 Cấp ngày 17 tháng 12 năm 2021", _MRZ_BACK)
    assert "nguoi_mat.ngay_cap" not in {f.unit.key for f in dinh_danh.card_findings(case)}


def _rel_case(relation, death_birth, *texts, death_date=""):
    values = {"NguoiYeuCau_HoTen": "NGUYEN VAN B", "NguoiYeuCau_SoDinhDanh": "001073000002", "NguoiYeuCau_QuanHe": relation,
              "NguoiMat_NgaySinh": death_birth, "NguoiMat_NgayMat": death_date}
    return Case([{"name": f"g{i}.pdf", "text": t} for i, t in enumerate(texts)], "", values,
                {"formContext": {"applicantFullname": "NGUYEN VAN B", "applicantIdentityNumber": "001073000002"}})


def test_quan_he_mau_thuan_nam_sinh_thi_theo_giay_bao_tu():
    from app.pipelines.khai_tu_dvcqg.thanh_tra import quan_he
    case = _rel_case("Con đẻ", "01/01/1973", "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nQuan hệ với người đã chết: Con đẻ",
                     "GIẤY BÁO TỬ\nQuan hệ với người chết: Vợ")
    assert [f.values for f in quan_he.findings_from(case)] == [{"NguoiYeuCau_QuanHe": "Vợ"}]


def test_quan_he_to_khai_ghi_vai_nguoi_mat_thi_dao():
    from app.pipelines.khai_tu_dvcqg.thanh_tra import quan_he
    case = _rel_case("Ông ngoại", "1890", "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nQuan hệ với người đã chết: Ông ngoại")
    assert [f.values for f in quan_he.findings_from(case)] == [{"NguoiYeuCau_QuanHe": "Cháu ngoại"}]
    cu = _rel_case("Cha cố", "", "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nQuan hệ với người đã chết: Cha cố", death_date="16/08/1968")
    assert [f.values for f in quan_he.findings_from(cu)] == [{"NguoiYeuCau_QuanHe": "Chắt"}]


def test_quan_he_hop_nam_sinh_thi_giu():
    from app.pipelines.khai_tu_dvcqg.thanh_tra import quan_he
    # Người mất là trẻ sinh sau người nộp: tờ khai "Bố" đúng chiều.
    child = _rel_case("Bố", "05/07/2026", "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nQuan hệ với người đã chết: Bố")
    assert quan_he.findings_from(child) == []
    son = _rel_case("Con đẻ", "1940", "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nQuan hệ với người đã chết: Con đẻ")
    assert quan_he.findings_from(son) == []


def test_quan_he_cap_quan_he_khong_kiem_va_cha_noi_la_chau_noi():
    from app.pipelines.khai_tu_dvcqg.thanh_tra import quan_he
    pair = _rel_case("Bố con", "1940", "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nQuan hệ với người đã chết: Bố con")
    assert quan_he.findings_from(pair) == []
    noi = _rel_case("Cha nội", "1910", "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nQuan hệ với người đã chết: Cha nội")
    assert [f.values for f in quan_he.findings_from(noi)] == [{"NguoiYeuCau_QuanHe": "Cháu nội"}]


def test_quan_he_luot_trich_dao_sai_thi_theo_dong_to_khai():
    from app.pipelines.khai_tu_dvcqg.thanh_tra import quan_he
    case = _rel_case("Cháu ngoại", "19/09/2026", "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nQuan hệ với người đã chết: ông ngoại")
    assert [f.values for f in quan_he.findings_from(case)] == [{"NguoiYeuCau_QuanHe": "ông ngoại"}]


def test_ten_khong_dau_nhung_dong_con_dau_la_cach_viet_that():
    # "Võ Thị Lan" có dấu ở chữ khác → dòng không bị OCR rơi dấu: tên viết đúng là "Lan", nhiều trang hơn thì thắng.
    docs = [{"name": "tk.pdf", "text": "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nHọ, chữ đệm, tên: VÕ THỊ LÀN"},
            {"name": "cd.pdf", "text": "BẢN CAM ĐOAN\nMẹ tôi tên là Võ Thị Lan"},
            {"name": "xn.pdf", "text": "GIẤY XÁC NHẬN\nTôi xác nhận bà Võ Thị Lan đã chết"}]
    case = Case(docs, "", {"NguoiMat_HoTen": "VÕ THỊ LẢN"}, {})
    finding = dinh_danh.name_finding(case, dinh_danh.trang.pages(docs))
    assert finding and finding.values == {"NguoiMat_HoTen": "VÕ THỊ LAN"}


def test_the_nhan_theo_ngay_sinh_va_so_lech_khi_to_khai_doc_sai_ca_ten():
    # Tờ khai viết tay đọc sai cả tên + số lệch 2 chữ số: thẻ có ngày sinh MRZ trùng, số lệch ≤2 → tên, số theo thẻ.
    front = "CĂN CƯỚC CÔNG DÂN\nSố / No.: 001060000123\nHọ và tên / Full name:\nTRẦN VĂN BÌNH"
    back = "IDVNM0600001230001060000123<<0\n6003154M9912315VNM<<<<<<<<<<<<6\nTRAN<<VAN<BINH<<<<<<<<<<<<<<<"
    case = _case({"NguoiMat_HoTen": "Trần Văn Bành", "NguoiMat_SoDinhDanh": "001068000123",
                  "NguoiMat_NgaySinh": "15/03/1960"},
                 "TỜ KHAI ĐĂNG KÝ KHAI TỬ\nHọ, chữ đệm, tên: Trần Văn Bành", f"{front}\n{back}")
    values = [f.values for f in dinh_danh.findings_from(case)]
    assert {"NguoiMat_HoTen": "TRẦN VĂN BÌNH"} in values
    assert {"NguoiMat_SoDinhDanh": "001060000123"} in values
    # Ngày sinh không trùng → không nhận thẻ đó.
    other = _case({"NguoiMat_HoTen": "Trần Văn Bành", "NguoiMat_SoDinhDanh": "001068000123",
                   "NguoiMat_NgaySinh": "16/03/1960"}, f"{front}\n{back}")
    assert dinh_danh.findings_from(other) == []
