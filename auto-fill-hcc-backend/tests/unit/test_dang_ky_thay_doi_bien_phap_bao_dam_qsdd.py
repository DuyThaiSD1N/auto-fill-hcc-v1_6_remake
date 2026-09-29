"""Unit test [Đà Nẵng] Đăng ký thay đổi biện pháp bảo đảm bằng QSDĐ (1.011442).

Mapper: chủ hồ sơ tổ chức (ô họ tên = người đại diện theo pháp luật), mốc tài khoản chọn nhân thân người nộp,
ghép tài sản bảo đảm + nội dung thay đổi vào nội dung yêu cầu, remap địa chỉ cũ. Planner: 12 dòng attp-row, đính
chung nhiều GCN vào dòng 5, GCN ĐKDN + ủy quyền vào dòng (i), tên tệp không trùng. Dữ liệu đều là ví dụ bịa."""

from app.pipelines._shared import fold
from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_qsdd.attach.planner import _ROWS, build_plan_items
from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_qsdd.process.mapper import enrich
from app.pipelines.dang_ky_thay_doi_bien_phap_bao_dam_qsdd.process.schema import ALLOWED, COMPACT_COMP_BY_NAME
from app.procedures import registry

_KEY = "dang-ky-thay-doi-bien-phap-bao-dam-qsdd"

_TO_CHUC = {
    "ChuHoSo_LoaiChuThe": "Tổ chức",
    "ChuHoSo_HoTen": "CÔNG TY TNHH MINH HỌA",
    "ChuHoSo_SoDinhDanh": "0400000001",
    "ChuHoSo_DiaChi": {"tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Vân", "diaChi": "Tầng 3, Tòa A1"},
    "ChuHoSo_DienThoai": "0905 000 111",
    "ChuHoSo_Email": "lienhe@minhhoa.vn",
    "DaiDien_HoTen": "TRẦN THỊ MẪU",
    "DaiDien_SoDinhDanh": "049180000001",
    "DaiDien_GioiTinh": "Nữ",
    "TaiSan_DanhSach": [
        {"soThua": "7", "toBanDo": "12", "diaChi": "Thị trấn Mẫu, huyện Mẫu, tỉnh Quảng Nam",
         "dienTich": "1.234,5 m²", "soPhatHanh": "AB 123456", "soVaoSo": "CT 01234"},
        {"soThua": "9", "toBanDo": "3", "soPhatHanh": "cd654321"},
    ],
    "Don_NoiDungThayDoi": "Bổ sung tài sản bảo đảm theo văn bản sửa đổi số 01/2026",
}


def _flds(d: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in d.items()]


def _run(vals: dict, ctx: dict | None = None) -> tuple[dict, list[str]]:
    options = {"formContext": ctx} if ctx else {}
    fields, warnings = enrich(_flds(vals), options)
    return {f["name"]: f["value"] for f in fields}, warnings


# ---------------------------------------------------------------- mapper


def test_to_chuc_nguoi_nop_duoc_uy_quyen():
    ctx = {"applicantFullname": "LÊ VĂN AN", "applicantIdentityNumber": "001090012345"}
    out, warnings = _run({
        **_TO_CHUC,
        "UyQuyen_HoTen": "LÊ VĂN AN", "UyQuyen_SoDinhDanh": "001090012345",
        "UyQuyen_NgayCap": "10/05/2022", "UyQuyen_NoiCap": "Cục CSQLHC về TTXH", "UyQuyen_GioiTinh": "Ông",
    }, ctx)
    assert out["data[chonDoiTuong]"] == "Tổ chức"
    assert out["data[ownerFullname]"] == "TRẦN THỊ MẪU"
    assert out["data[organization]"] == "CÔNG TY TNHH MINH HỌA"
    assert out["data[taxCode]"] == "0400000001"
    assert out["data[isOwnerDossier]"] is False
    assert out["data[gender]"] == "Nam"
    assert out["data[identityDate]"] == "10/05/2022"
    assert out["data[identityAgency]"].startswith("Cục Cảnh sát quản lý hành chính")
    assert out["data[phoneNumber]"] == "0905000111"
    assert out["data[email]"] == "lienhe@minhhoa.vn"
    assert out["data[province]"] == "Thành phố Đà Nẵng"
    assert out["data[district]"] == "Phường Hải Vân"
    assert out["data[address]"] == "Tầng 3, Tòa A1"
    # Ô khoá theo tài khoản: không phát.
    for locked in ("data[fullname]", "data[birthday]", "data[identityNumber]"):
        assert locked not in out
    assert not any("ủy quyền" in w and "cần văn bản" in w for w in warnings)


def test_noi_dung_ghep_tai_san_va_noi_dung_thay_doi():
    out, _ = _run(_TO_CHUC)
    nd = out["data[noidungyeucaugiaiquyet]"]
    assert nd.startswith(
        "ÔNG/BÀ: TRẦN THỊ MẪU (chủ hồ sơ) ĐỀ NGHỊ GIẢI QUYẾT Đăng ký thay đổi biện pháp bảo đảm bằng quyền sử "
        "dụng đất, tài sản gắn liền với đất đối với: (1) Thửa đất số 7, tờ bản đồ số 12"
    )
    assert "Giấy chứng nhận số phát hành AB 123456, số vào sổ cấp GCN: CT 01234" in nd
    assert "(2) Thửa đất số 9, tờ bản đồ số 3, Giấy chứng nhận số phát hành CD 654321" in nd
    assert nd.endswith("Nội dung thay đổi: Bổ sung tài sản bảo đảm theo văn bản sửa đổi số 01/2026.")


def test_mot_tai_san_khong_danh_so_va_gop_trang_bo_sung():
    out, _ = _run({
        **_TO_CHUC,
        "TaiSan_DanhSach": [{"soThua": "7", "soPhatHanh": "AB 123456", "dienTich": "250"},
                            {"soThua": "7", "soPhatHanh": "ab123456"}],
    })
    nd = out["data[noidungyeucaugiaiquyet]"]
    assert "đối với: Thửa đất số 7, diện tích 250 m², Giấy chứng nhận số phát hành AB 123456." in nd
    assert "(1)" not in nd


def test_to_chuc_nguoi_dai_dien_tu_nop():
    ctx = {"applicantFullname": "Trần Thị Mẫu", "applicantIdentityNumber": "049180000001"}
    out, warnings = _run(_TO_CHUC, ctx)
    assert out["data[isOwnerDossier]"] is True
    assert out["data[gender]"] == "Nữ"
    assert not any("không phải người đại diện" in w for w in warnings)


def test_to_chuc_nguoi_nop_khac_khong_uy_quyen_canh_bao():
    ctx = {"applicantFullname": "PHẠM VĂN BÌNH", "applicantIdentityNumber": "001090099999"}
    out, warnings = _run(_TO_CHUC, ctx)
    assert out["data[isOwnerDossier]"] is False
    assert "data[gender]" not in out
    assert any("không phải người đại diện theo pháp luật" in w for w in warnings)


def test_ca_nhan_tu_nop_theo_cccd():
    ctx = {"applicantFullname": "NGUYỄN VĂN A", "applicantIdentityNumber": "049074001234"}
    out, _ = _run({
        "ChuHoSo_LoaiChuThe": "Cá nhân", "ChuHoSo_HoTen": "NGUYỄN VĂN A", "ChuHoSo_SoDinhDanh": "049074001234",
        "ChuHoSo_DiaChi": {"tinh": "Quảng Nam", "xa": "Thị trấn Nam Phước", "diaChi": "Khối 1"},
        "NguoiNop_HoTen": "NGUYỄN VĂN A", "NguoiNop_SoDinhDanh": "049074001234",
        "NguoiNop_GioiTinh": "Nam", "NguoiNop_NgayCap": "01/07/2024", "NguoiNop_NoiCap": "Bộ Công an",
    }, ctx)
    assert out["data[chonDoiTuong]"] == "Cá nhân"
    assert out["data[ownerFullname]"] == "NGUYỄN VĂN A"
    assert out["data[isOwnerDossier]"] is True
    assert "data[organization]" not in out and "data[taxCode]" not in out
    assert out["data[identityDate]"] == "01/07/2024"
    # Quảng Nam cũ → Đà Nẵng sau sáp nhập.
    assert out["data[province]"] == "Thành phố Đà Nẵng"
    assert out["data[district]"] == "Xã Nam Phước"


def test_khong_co_moc_tai_khoan():
    out, warnings = _run(_TO_CHUC)
    assert "data[isOwnerDossier]" not in out
    assert "data[gender]" not in out
    assert any("tài khoản đang đăng nhập" in w for w in warnings)


def test_thieu_phieu_va_sdt_canh_bao():
    vals = {k: v for k, v in _TO_CHUC.items() if k not in ("Don_NoiDungThayDoi", "ChuHoSo_DienThoai")}
    out, warnings = _run(vals)
    assert "data[phoneNumber]" not in out
    assert any("Mẫu số 02a" in w for w in warnings)
    assert any("số điện thoại" in w for w in warnings)


def test_to_chuc_thieu_nguoi_dai_dien_dung_ten_to_chuc():
    vals = {k: v for k, v in _TO_CHUC.items() if not k.startswith("DaiDien_")}
    out, warnings = _run(vals)
    assert out["data[ownerFullname]"] == "CÔNG TY TNHH MINH HỌA"
    assert out["data[noidungyeucaugiaiquyet]"].startswith("ÔNG/BÀ: CÔNG TY TNHH MINH HỌA (chủ hồ sơ)")
    assert any("người đại diện theo pháp luật" in w for w in warnings)


def test_schema_comp():
    assert COMPACT_COMP_BY_NAME["TaiSan_DanhSach"] == "x-array"
    assert COMPACT_COMP_BY_NAME["ChuHoSo_DiaChi"] == "x-select-area"
    assert {"ChuHoSo_HoTen", "DaiDien_HoTen", "UyQuyen_HoTen", "NguoiNop_NgayCap"} <= ALLOWED


# ---------------------------------------------------------------- planner

# Nhãn 12 dòng "Thành phần hồ sơ" trên cổng (rút gọn phần đầu, đủ để khớp componentName).
_PORTAL_ROWS = [
    "Phiếu yêu cầu theo Mẫu số 02a tại Phụ lục (01 bản chính).",
    "Văn bản sửa đổi, bổ sung hợp đồng bảo đảm trong trường hợp đăng ký thay đổi theo thỏa thuận trong văn bản này;",
    "Văn bản chuyển giao quyền đòi nợ, chuyển giao nghĩa vụ trong trường hợp đăng ký thay đổi do chuyển giao quyền "
    "đòi nợ, chuyển giao nghĩa vụ;",
    "Văn bản khác chứng minh có căn cứ đăng ký thay đổi đối với trường hợp không thuộc điểm a và điểm b khoản 2 "
    "Điều 32 Nghị định số 99/2022/NĐ-CP.",
    "Giấy chứng nhận (bản gốc) trong trường hợp tài sản bảo đảm có Giấy chứng nhận.",
    "Trường hợp đăng ký thay đổi quy định tại điểm b khoản 1 Điều 18 Nghị định số 99/2022/NĐ-CP thì ngoài giấy tờ "
    "quy định tại khoản 1 Điều 32 Nghị định số 99/2022/NĐ-CP, hồ sơ đăng ký còn có thêm Giấy chứng nhận đối với "
    "quyền sử dụng đất",
    "(i) Trường hợp thực hiện thông qua người đại diện thì văn bản có nội dung về đại diện là tài liệu phải có",
    "(ii) Trường hợp chi nhánh của pháp nhân, chi nhánh hoặc phòng giao dịch của pháp nhân là tổ chức tín dụng",
    "(iii) Trường hợp được miễn nghĩa vụ nộp phí, thanh toán giá dịch vụ, nghĩa vụ thanh toán khác",
    "(iv) Trường hợp bên bảo đảm hoặc bên nhận bảo đảm gồm nhiều người thì phải có đầy đủ chữ ký",
    "(v) Trường hợp Công ty quản lý tài sản của các tổ chức tín dụng Việt Nam hoặc chủ thể khác trở thành bên nhận "
    "bảo đảm mới mà thuộc diện không phải đăng ký thay đổi bên nhận bảo đảm quy định tại điểm a khoản 1 Điều 18",
    "(vi) Trường hợp thay đổi bên nhận bảo đảm quy định tại điểm a khoản 1 và khoản 2 Điều 18 Nghị định số "
    "99/2022/NĐ-CP liên quan đến nhiều biện pháp bảo đảm đã được đăng ký mà có cùng một bên nhận bảo đảm thì người "
    "yêu cầu đăng ký nộp 01 bộ hồ sơ đăng ký thay đổi và 01 Danh mục văn bản được kê khai theo Mẫu số 01đ",
]
_EXPECTED_ROW = {
    "phieu_02a": 1, "van_ban_sua_doi_hdbd": 2, "van_ban_chuyen_giao": 3, "van_ban_can_cu_khac": 4, "gcn": 5,
    "van_ban_dai_dien": 7, "dkdn": 7, "van_ban_giao_nhiem_vu": 8, "hop_dong_bao_dam": 9, "danh_muc_01d": 12,
}


def test_component_name_khop_dung_dong_dau_tien():
    for doc_type, row in _ROWS.items():
        want = fold(row["componentName"])
        first = next(i for i, label in enumerate(_PORTAL_ROWS, start=1) if want in fold(label))
        assert first == _EXPECTED_ROW[doc_type], doc_type


_GCN_1 = "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT ... CÔNG TY CỔ PHẦN MẪU GCNĐKDN số: 4000000002 ... AB 123456"
_GCN_2 = "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT ... Thửa đất số 9 ... CD 654321"
_DKDN = ("GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP CÔNG TY TNHH MỘT THÀNH VIÊN Mã số doanh nghiệp: 0400000001 "
         "Đăng ký lần đầu: ngày 01 tháng 01 năm 2026")


def test_plan_ho_so_mau():
    files = [{"name": n} for n in ("gcn1.pdf", "gcn2.pdf", "dkdn.pdf", "phieu.docx", "uq.pdf", "cccd.jpg")]
    ocr = [
        {"name": "gcn1.pdf", "text": _GCN_1},
        {"name": "gcn2.pdf", "text": _GCN_2},
        {"name": "dkdn.pdf", "text": _DKDN},
        {"name": "phieu.docx", "text": "PHIẾU YÊU CẦU ĐĂNG KÝ THAY ĐỔI NỘI DUNG BIỆN PHÁP BẢO ĐẢM Mẫu số 02a"},
        {"name": "uq.pdf", "text": "GIẤY ỦY QUYỀN Bên được ủy quyền: Ông LÊ VĂN AN"},
        {"name": "cccd.jpg", "text": "CĂN CƯỚC CÔNG DÂN Số 001090012345"},
    ]
    items, warnings, classified = build_plan_items(files, ocr, {})
    by_file = {i["fileName"]: i for i in items}
    assert by_file["phieu.docx"]["componentName"] == "Phiếu yêu cầu theo Mẫu số 02a"
    assert by_file["phieu.docx"]["loaiBan"] == "Bản chính"
    # Hai GCN đính CHUNG dòng 5, tên tệp riêng theo số phát hành.
    assert by_file["gcn1.pdf"]["componentName"] == by_file["gcn2.pdf"]["componentName"] == "Giấy chứng nhận (bản gốc)"
    assert by_file["gcn1.pdf"]["loaiBan"] == "Bản chính"
    assert by_file["gcn1.pdf"]["documentName"] == "Giấy chứng nhận AB 123456 (bản gốc)"
    assert by_file["gcn2.pdf"]["documentName"] == "Giấy chứng nhận CD 654321 (bản gốc)"
    # GCN ĐKDN + ủy quyền đính CHUNG dòng (i).
    assert by_file["dkdn.pdf"]["componentName"] == by_file["uq.pdf"]["componentName"] == "thông qua người đại diện"
    assert by_file["dkdn.pdf"]["loaiBan"] == "Bản sao"
    assert "cccd.jpg" not in by_file
    assert any(c["fileName"] == "cccd.jpg" and c.get("skipped") for c in classified)
    assert all(i["target"] == "attp-row" for i in items)
    assert not warnings


def test_plan_llm_uu_tien_va_thieu_phieu():
    files = [{"name": "a.pdf"}, {"name": "b.pdf"}]
    ocr = [{"name": "a.pdf", "text": "văn bản bất kỳ"}, {"name": "b.pdf", "text": ""}]
    items, warnings, _ = build_plan_items(files, ocr, {0: "van_ban_chuyen_giao"})
    assert [i["componentName"] for i in items] == ["Văn bản chuyển giao quyền đòi nợ"]
    assert any("b.pdf" in w for w in warnings)
    assert any("Mẫu số 02a" in w for w in warnings)


def test_plan_gcn_khong_doc_duoc_so_danh_so_ten():
    files = [{"name": "x.pdf"}, {"name": "y.pdf"}]
    ocr = [{"name": "x.pdf", "text": "giấy chứng nhận quyền sử dụng đất"},
           {"name": "y.pdf", "text": "giấy chứng nhận quyền sử dụng đất"}]
    items, _, _ = build_plan_items(files, ocr, {})
    assert [i["documentName"] for i in items] == ["Giấy chứng nhận (bản gốc)", "Giấy chứng nhận (bản gốc) 2"]


def test_plan_hop_dong_canh_bao_mien_phi():
    files = [{"name": "hd.pdf"}]
    ocr = [{"name": "hd.pdf", "text": "HỢP ĐỒNG THẾ CHẤP QUYỀN SỬ DỤNG ĐẤT số 01/2026"}]
    items, warnings, _ = build_plan_items(files, ocr, {})
    assert items[0]["componentName"] == "miễn nghĩa vụ nộp phí"
    assert any("miễn phí" in w for w in warnings)


# ---------------------------------------------------------------- registry


def test_registry_dang_ky_du():
    assert registry.get_procedure(_KEY) is not None
    assert registry.get_pipeline(_KEY) is not None
    assert registry.get_attach_pipeline(_KEY) is not None
    detect = registry.get_procedure(_KEY)["detect"]
    assert detect["urlScope"] == ["dichvucong.danang.gov.vn"]
    phrase = fold(detect["textIncludes"][0])
    # Không dính trang Xóa đăng ký / Đăng ký lần đầu cùng cổng.
    for other in ("xoa-dang-ky-bien-phap-bao-dam-da-nang", "dang-ky-bien-phap-bao-dam-qsdd"):
        assert phrase not in fold(registry.get_procedure(other)["label"])
