"""Thanh tra + điền đợt 2 của thay đổi, cải chính hộ tịch (tên, số giả)."""

import asyncio

from app.pipelines._shared.thanh_tra.ho_so import Case, Result
from app.pipelines.cai_chinh_dvc_moi import thanh_tra
from app.pipelines.cai_chinh_dvc_moi.process import mapper
from app.pipelines.cai_chinh_dvc_moi.thanh_tra import dinh_danh, dot_hai, noi_dung
from app.procedures.registry import get_procedure
from app.second_pass import service

_TO_KHAI = ("TỜ KHAI ĐĂNG KÝ VIỆC THAY ĐỔI, CẢI CHÍNH, BỔ SUNG THÔNG TIN HỘ TỊCH\n"
            "Đề nghị cơ quan đăng ký việc (4) Cải chính giấy khai sinh\ncho người có tên dưới đây:\n"
            "Họ, chữ đệm, tên: Lê Văn Con\nĐã đăng ký (5) Khai sinh tại UBND xã Mẫu\n"
            "Nội dung: Cải chính năm sinh của người cha từ 1950 thành 1951\nLý do: khai nhầm")


def test_registry_bat_dot_hai_surveyjs():
    proc = get_procedure("thay-doi-cai-chinh-ho-tich")
    assert proc["secondPass"] is True
    assert service.capability(proc) == "secondPass"
    assert [i.key for i in thanh_tra.INSPECTORS] == ["dinh_danh", "dia_chi", "giay_to", "noi_dung", "sdt_nguoi_nop"]


def test_ban_than_chi_soat_giay_to_va_noi_dung(monkeypatch):
    seen = []

    async def fake_run(case, inspectors, *, title):
        seen.append([i.key for i in inspectors])
        return Result(case.values, [], {})
    monkeypatch.setattr(thanh_tra.engine, "run", fake_run)
    ctx = "<nguoi_thay_doi>\nHọ tên: LE VAN CON\n</nguoi_thay_doi>\n<quan_he>\nKết luận: {}\n</quan_he>"
    opts = {"formContext": {"applicantFullname": "Le Van Con", "applicantIdentityNumber": "001090000001"}}
    asyncio.run(thanh_tra.review([], ctx.format("Bản thân"), {"NguoiThayDoi_HoTen": "Le Van Con"}, opts))
    asyncio.run(thanh_tra.review([], ctx.format("Khác"), {"NguoiThayDoi_HoTen": "Tran Thi Khac"}, opts))
    assert seen == [["giay_to", "noi_dung", "sdt_nguoi_nop"],
                    ["giay_to", "noi_dung", "sdt_nguoi_nop", "dinh_danh", "dia_chi"]]


def test_o_dia_chi_chi_vao_ban_va_khi_extension_khai_biet_ghi(monkeypatch):
    area = {"quocGia": "Việt Nam", "tinh": "Lâm Đồng", "xa": "Phường Xuân Hương - Đà Lạt", "diaChi": "Số 2"}

    async def fake_review(documents, context, values, options):
        return Result({**values, "NguoiThayDoi_NoiCuTru": area, "LyDo": "Khai nhầm"}, [], {})
    monkeypatch.setattr(dot_hai, "review", fake_review)
    ctx = "<nguoi_thay_doi>\nHọ tên: TRAN THI KHAC\n</nguoi_thay_doi>\n<quan_he>\nKết luận: Khác\n</quan_he>"
    raw = [{"name": "NguoiThayDoi_HoTen", "value": "Tran Thi Khac"}, {"name": "LyDo", "value": "Tôi cam đoan"}]
    opts = {"_reasoning_context": ctx}
    base, _ = mapper.enrich([dict(f) for f in raw], opts)
    names = lambda out: [f["name"] for f in out["fields"]]  # noqa: E731
    old = asyncio.run(dot_hai.patch([], ctx, raw, base, opts))
    assert names(old) == ["citizenLydothaydoi"]
    new = asyncio.run(dot_hai.patch([], ctx, raw, base, {**opts, "_secondPassArea": True}))
    assert names(new) == ["citizenNDKNoiCuTru", "citizenNDKNoiCuTru_TrongNuoc", "citizenLydothaydoi"]
    assert new["fields"][1]["radio"] == "citizenNDKNoiCuTru" and new["fields"][1]["by"] == "dia_chi"


def test_dinh_danh_bac_gia_tri_moi_de_nghi_sua_thanh():
    case = Case([], "", {"NoiDung": "Cải chính họ, chữ đệm, tên từ Lê Văn Con thành Lê Văn Còn"}, {})
    unit = next(u for u in dinh_danh.UNITS if u.key == "ho_ten")
    assert dinh_danh.check(unit, {"NguoiThayDoi_HoTen": "Lê Văn Còn"}, case) == \
        "giá trị mới đề nghị sửa thành, không phải giá trị đang có"
    assert not dinh_danh._is_new_value(unit, {"NguoiThayDoi_HoTen": "Lê Văn Con"}, case)
    # Thẻ có thể ghi họ tên sau cải chính: chỉ sửa dấu, không đổi chữ cái của họ tên lượt trích.
    case = Case([], "", {"NguoiThayDoi_HoTen": "LE VAN CON"}, {})
    assert dinh_danh.check(unit, {"NguoiThayDoi_HoTen": "Lê Văn Còn"}, case) == ""
    named = lambda name: Case([], "", {"NguoiThayDoi_HoTen": name}, {})  # noqa: E731
    assert dinh_danh.check(unit, {"NguoiThayDoi_HoTen": "Lê Văn Cơn"}, named("Lê Văn Cờn")) == ""
    assert dinh_danh.check(unit, {"NguoiThayDoi_HoTen": "Lê Trọng Con"}, named("Lê Trung Con"))
    assert dinh_danh.check(unit, {"NguoiThayDoi_HoTen": "LE TRUNG CON"}, named("Lê Trung Con"))
    birth = next(u for u in dinh_danh.UNITS if u.key == "ngay_sinh")
    year_changed = Case([], "", {"NoiDung": "Cải chính năm sinh từ 1925 thành 1927"}, {})
    assert dinh_danh.check(birth, {"NguoiThayDoi_NgaySinh": "01/04/1927"}, year_changed)


def test_noi_dung_chi_ra_toa_khi_ma_chi_ra_loi_cua_luot_trich():
    case = Case([{"name": "tk", "text": _TO_KHAI}], "", {}, {})
    unit = {u.key: u for u in noi_dung.UNITS}
    good = "Cải chính năm sinh của người cha từ 1950 thành 1951"
    # Mục "từ A thành A" và giá trị không có trên giấy.
    assert noi_dung.faults(unit["noi_dung"], "Cải chính năm sinh từ 1950 thành 1950", good, case)
    assert noi_dung.faults(unit["noi_dung"], "Cải chính năm sinh của người cha từ 1960 thành 1951", good, case)
    # Chỉ khác cách viết, mọi giá trị đều có trên giấy (chữ đơn vị "tuổi" tự thêm không tính) → không có lỗi.
    assert not noi_dung.faults(unit["noi_dung"], "Cải chính năm sinh người cha từ 1950 thành 1951", good, case)
    assert noi_dung.faults(unit["ly_do"], "Tôi cam đoan những nội dung khai trên đây là đúng sự thật", "Khai nhầm",
                           case)
    # Chỉ khác dấu ("Tạm" / "Tâm") là một mục cải chính thật, không phải "từ A thành A".
    accent = "Cải chính tên mẹ từ Trần Thị Tạm thành Trần Thị Tâm"
    assert not noi_dung.faults(unit["noi_dung"], accent, good, Case([{"name": "a", "text": accent}], "", {}, {}))
    # Loại việc không soát theo dòng (4); tên giấy theo dòng "Đã đăng ký <loại> tại".
    assert not noi_dung.faults(unit["viec"], "Thay đổi", "Cải chính", case)
    assert noi_dung.faults(unit["loai_giay"], "kết hôn", "khai sinh", case)


def test_noi_dung_khong_soat_khi_khong_co_to_khai_lan_ban_cam_doan():
    assert noi_dung._has_source(Case([{"name": "tk", "text": _TO_KHAI}], "", {}, {}))
    assert not noi_dung._has_source(Case([{"name": "ks", "text": "GIẤY KHAI SINH\nHọ, chữ đệm, tên: Lê Văn Con"}],
                                         "", {}, {}))
    assert asyncio.run(noi_dung.find(noi_dung.INSPECTOR, Case([{"name": "ks", "text": "GIẤY KHAI SINH"}], "", {}, {}),
                                     "")) == []


def test_noi_dung_tu_ban_cam_doan_xet_loi_tren_gia_tri_mapper_da_don(monkeypatch):
    unit = next(u for u in noi_dung.UNITS if u.key == "noi_dung")
    proposed = "Cải chính họ tên, năm sinh của Lê Văn Con từ 1950 thành 1951"

    async def fake(inspector, case, title):
        return [noi_dung.Finding(inspector, unit, {"NoiDung": proposed}, "BẢN CAM ĐOAN", 1, owner="bản cam đoan")]
    monkeypatch.setattr(noi_dung.engine, "llm_findings", fake)
    ctx = "<viec_dang_ky>\nThông tin cần sửa:\n- năm sinh: đang ghi 1950 | đúng theo CCCD: 1951\n</viec_dang_ky>"
    docs = [{"name": "cd", "text": "BẢN CAM ĐOAN\nLê Văn Con năm sinh 1950, căn cước ghi 1951"}]
    values = {"NoiDung": "Cải chính họ tên từ Lê Văn Con thành Lê Văn Con; cải chính năm sinh từ 1950 thành 1951"}
    out = asyncio.run(noi_dung.find(noi_dung.INSPECTOR, Case(docs, ctx, values, {}), ""))
    assert out and not out[0].backed  # mapper đã bỏ mục "từ A thành A" → không còn lỗi để thay


def test_giay_to_bo_moi_muc_cua_tai_lieu_co_ngay_dang_ky_lech_xa_ngay_sinh(monkeypatch):
    from app.pipelines.cai_chinh_dvc_moi.thanh_tra import giay_to

    async def fake_chat(*args, **kwargs):
        return ('{"co_quan": {"dong": 1, "value": "UBND phường Mới", "thuoc_ve": "giấy hộ tịch cần sửa của người có '
                'nội dung thay đổi"}, "ngay_dang_ky": {"dong": 2, "value": "23/09/2023", "thuoc_ve": "giấy hộ tịch '
                'cần sửa của người có nội dung thay đổi"}, "so": null, "quyen_so": null}')
    monkeypatch.setattr(giay_to.client, "chat", fake_chat)
    docs = [{"name": "ks", "text": "Nơi đăng ký khai sinh: UBND phường Mới\nNgày, tháng, năm đăng ký: 23/09/2023"}]
    values = {"NguoiThayDoi_NgaySinh": "01/01/1980", "HoSo_LoaiGiayTo": "khai sinh"}
    assert asyncio.run(giay_to.find(giay_to.INSPECTOR, Case(docs, "", values, {}), "")) == []


def test_giay_to_chi_lay_dong_dang_ky_cua_giay_dung_ten_nguoi_co_noi_dung_thay_doi():
    from app.pipelines.cai_chinh_dvc_moi.thanh_tra import giay_to

    other = ("GIẤY KHAI SINH\nHọ, chữ đệm, tên: TRẦN VĂN CHA\nHọ, chữ đệm, tên người đi khai sinh: LÊ VĂN CON\n"
             "Nơi đăng ký khai sinh: UBND phường Mới")
    own = "GIẤY KHAI SINH\nHọ, chữ đệm, tên: LÊ VĂN CON\nNơi đăng ký khai sinh: UBND xã Cũ"
    marriage = "TRÍCH LỤC KẾT HÔN\nHọ, chữ đệm, tên vợ: A Thị B Họ, chữ đệm, tên chồng: TRẦN VĂN CHA\nĐăng ký kết hôn tại: X"
    case = Case([{"name": "a", "text": other}, {"name": "b", "text": own}, {"name": "c", "text": marriage}],
                "<nguoi_thay_doi>\nHọ tên: Lê Văn Con\n</nguoi_thay_doi>", {}, {})
    unit = giay_to.UNITS[0]
    line = lambda doc, quote: giay_to.Finding(giay_to.INSPECTOR, unit, {}, quote, doc)  # noqa: E731
    assert not giay_to._of_subject(line(1, "Nơi đăng ký khai sinh: UBND phường Mới"), case)
    assert giay_to._of_subject(line(2, "Nơi đăng ký khai sinh: UBND xã Cũ"), case)
    assert not giay_to._of_subject(line(3, "Đăng ký kết hôn tại: X"), case)


def test_ten_xa_doc_lech_chi_sua_ten_xa_giu_chi_tiet(monkeypatch):
    # Tên phường viết tay OCR đọc lệch 2 chữ, không có trong danh mục: chỉ đổi tên xã sang xã DUY NHẤT gần chữ đó của tỉnh
    # (tên đó có nguyên văn trên giấy in của hồ sơ), giữ chi tiết; không ghép lại địa chỉ cũ trên thẻ.
    import json
    from app.pipelines._shared.thanh_tra import ten_xa
    from app.pipelines.cai_chinh_dvc_moi.thanh_tra import dia_chi_ghep
    from app.services.llm import client

    async def no_answer(messages, **kwargs):
        return json.dumps({"xa": "", "dong_dia_chi": "", "dong_phu": "", "ly_do": ""})

    monkeypatch.setattr(client, "chat", no_answer)
    to_khai = "TỜ KHAI ĐĂNG KÝ VIỆC THAY ĐỔI\nNơi cư trú: 12 Tổ Mẫu Phường Yên Chiểu TP Đà Nẵng"
    giay = "TRÍCH LỤC KHAI SINH\nNơi đăng ký khai sinh: Ủy ban nhân dân phường Liên Chiểu, thành phố Đà Nẵng"
    value = {"quocGia": "Việt Nam", "tinh": "Đà Nẵng", "xa": "Phường Yên Chiểu", "diaChi": "12 Tổ Mẫu"}
    case = Case([{"text": to_khai}, {"text": giay}], "", {dia_chi_ghep.FIELD: value}, {})
    [finding] = asyncio.run(dia_chi_ghep.find(dia_chi_ghep.INSPECTOR, case, "thử"))
    assert finding.values[dia_chi_ghep.FIELD] == {**value, "xa": "Phường Liên Chiểu"}
    assert finding.quote.startswith("Nơi cư trú: 12 Tổ Mẫu")
    # Không có giấy nào ghi tên xã gần chữ đó → không đoán.
    assert ten_xa._only_near_named("yên chiểu", {ten_xa._bare(w): w for w in ten_xa.wards_of("Đà Nẵng")},
                                   [{"text": to_khai}]) == ""


_KS_CHA = ("GIẤY KHAI SINH\nHọ, chữ đệm, tên: NGUYỄN VĂN A\nNgày, tháng, năm sinh: 01/01/1950\nSố: 509\n"
           "Ngày, tháng, năm đăng ký: 13/4/2021")
_KS_CON = ("ỦY BAN NHÂN DÂN\nXã, phường...Mẫu...\nSố...40\nGIẤY KHAI SINH\n(BẢN SAO)\nHọ và tên Nguyễn Thị Cũ\n"
           "Ngày, tháng, năm sinh 26-03-1985\nĐăng ký ngày 09 tháng 04 năm 1985")


def test_giay_khai_sinh_trong_ho_so_ghi_cung_khac_nam_sinh():
    from app.pipelines.cai_chinh_dvc_moi.process import reason

    context = "<nguoi_thay_doi>\nHọ tên: Nguyễn Thị Mới\nNgày sinh: 25/03/1985\n</nguoi_thay_doi>"
    note = reason._birth_certificates_note([{"name": "cha.pdf", "text": _KS_CHA}, {"name": "con.pdf", "text": _KS_CON}],
                                          context)
    assert "Tài liệu 1 (cha.pdf): người được khai sinh sinh 01/01/1950 — KHÁC năm sinh" in note
    assert "Tài liệu 2 (con.pdf): người được khai sinh sinh 26/03/1985 — CÙNG năm sinh" in note
    # Một giấy khai sinh thì không cần khối đối chiếu.
    assert reason._birth_certificates_note([{"text": _KS_CON}], context) == ""


def test_giay_to_bo_de_xuat_lay_tu_giay_khai_sinh_khac_nam_sinh(monkeypatch):
    import json
    from app.pipelines.cai_chinh_dvc_moi.thanh_tra import giay_to
    from app.services.llm import client

    async def pick_father(messages, **kwargs):
        lines = messages[1]["content"].splitlines()
        at = next(i for i, line in enumerate(lines) if line.endswith("Ngày, tháng, năm đăng ký: 13/4/2021"))
        number = int(lines[at].split("]")[0].strip("["))
        return json.dumps({"co_quan": None, "so": None, "quyen_so": None,
                           "ngay_dang_ky": {"dong": number, "value": "13/04/2021", "thuoc_ve": giay_to._OWNERS[0]}})

    monkeypatch.setattr(client, "chat", pick_father)
    values = {"NguoiThayDoi_NgaySinh": "25/03/1985", "HoSo_LoaiGiayTo": "khai sinh", "HoSo_NgayDangKy": "09/04/1985"}
    case = Case([{"text": _KS_CHA}, {"text": _KS_CON}], "", values, {})
    assert asyncio.run(giay_to.find(giay_to.INSPECTOR, case, "thử")) == []


def test_bo_so_ngay_dang_ky_cua_giay_khai_sinh_cha_me():
    from app.pipelines.cai_chinh_dvc_moi.process import reason

    docs = [{"text": _KS_CHA}, {"text": _KS_CON}]
    wrong = {"NguoiThayDoi_NgaySinh": "25/03/1985", "HoSo_So": "509", "HoSo_NgayDangKy": "13/04/2021",
             "HoSo_NoiDangKy": "UBND phường Mẫu"}
    assert reason.drop_other_holder_registration(wrong, docs) == {"NguoiThayDoi_NgaySinh": "25/03/1985"}
    right = {**wrong, "HoSo_So": "40", "HoSo_NgayDangKy": "09/04/1985"}
    assert reason.drop_other_holder_registration(right, docs) == right
    # Ngày sinh lấy ở khối phân vai khi lượt trích không có; hồ sơ không có giấy cùng năm sinh thì giữ nguyên.
    context = "<nguoi_thay_doi>\nNgày sinh: 25/03/1985\n</nguoi_thay_doi>"
    no_birth = {k: v for k, v in wrong.items() if k != "NguoiThayDoi_NgaySinh"}
    assert reason.drop_other_holder_registration(no_birth, docs, context) == {}
    assert reason.drop_other_holder_registration(wrong, [{"text": _KS_CHA}]) == wrong


def test_chot_giay_khai_sinh_uu_tien_ngay_sinh_khoi_phan_vai():
    from app.pipelines.cai_chinh_dvc_moi.process import reason

    docs = [{"text": _KS_CHA}, {"text": _KS_CON}]
    context = "<nguoi_thay_doi>\nNgày sinh: 25/03/1985\n</nguoi_thay_doi>"
    # Lượt trích chép nhầm ngày sinh của cha vào ngày sinh người có nội dung thay đổi.
    wrong = {"NguoiThayDoi_NgaySinh": "01/01/1950", "HoSo_So": "509", "HoSo_NgayDangKy": "13/04/2021"}
    assert reason.drop_other_holder_registration(wrong, docs, context) == {"NguoiThayDoi_NgaySinh": "01/01/1950"}


def test_noi_dung_ten_viet_tay_lech_dau_theo_chu_in_tren_giay():
    from app.pipelines._shared.thanh_tra.ho_so import Case
    from app.pipelines.cai_chinh_dvc_moi.thanh_tra import noi_dung
    docs = [{"name": "a.pdf", "text": "GIẤY KHAI SINH\nHọ, chữ đệm, tên người mẹ: NGUYỄN THỊ NHỮ\n"
                                      "TRÍCH LỤC KHAI TỬ\nHọ, chữ đệm, tên: NGUYỄN THỊ THỮ\n"
                                      "TỜ KHAI\nNội dung: từ Nguyễn Thị Như thành Nguyễn Thị Thử\n"}]
    text = "Cải chính tên người mẹ từ Nguyễn Thị Như thành Nguyễn Thị Thử"
    fixed = noi_dung._printed_spelling(text, Case(docs, "", {"NoiDung": text}, {}))
    assert fixed[0] == "Cải chính tên người mẹ từ Nguyễn Thị Nhữ thành Nguyễn Thị Thữ"


def test_noi_dung_sua_chinh_la_doi_dau_hoac_lech_tieng_chung_thi_giu():
    from app.pipelines._shared.thanh_tra.ho_so import Case
    from app.pipelines.cai_chinh_dvc_moi.thanh_tra import noi_dung
    docs = [{"name": "a.pdf", "text": "CĂN CƯỚC\nHọ và tên: NGUYỄN THỊ VỊNH\nGIẤY KHAI SINH\nHọ tên cha: NGUYỄN HỮU CỐN\n"}]
    same = "Cải chính họ tên từ Nguyễn Thị Vinh thành Nguyễn Thị Vịnh"
    assert noi_dung._printed_spelling(same, Case(docs, "", {"NoiDung": same}, {})) is None
    shared = "Cải chính chữ đệm của người cha từ Nguyễn Hữu Cồn thành Nguyễn Văn Cồn"
    assert noi_dung._printed_spelling(shared, Case(docs, "", {"NoiDung": shared}, {})) is None
