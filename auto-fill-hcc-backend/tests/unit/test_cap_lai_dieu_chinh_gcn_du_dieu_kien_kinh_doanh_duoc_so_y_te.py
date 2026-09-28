"""Unit test pipeline "Cấp lại, điều chỉnh GCN đủ điều kiện kinh doanh dược (Sở Y tế)" — mã 1.014104.

Mapper: ô khoá theo tài khoản không phát; Phần II luôn bỏ tích + ghi đè bằng chủ cơ sở; tự nộp / nộp thay
quyết định Phần I. Planner: PDF gộp tách theo trang → đúng dòng thành phần hồ sơ. Dữ liệu đều là ví dụ bịa.
"""

from app.pipelines.cap_lai_dieu_chinh_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.attach import planner as P
from app.pipelines.cap_lai_dieu_chinh_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.process import mapper
from app.pipelines.cap_lai_dieu_chinh_gcn_du_dieu_kien_kinh_doanh_duoc_so_y_te.process.runner import (
    find_submitter_card,
)
from app.procedures import registry

OWNER_ID = "001190012345"
NOP_ID = "001203098765"


def _fields(**values):
    return [{"name": k, "value": v} for k, v in values.items()]


def _owner(**extra):
    base = dict(
        ChuHoSo_HoTen="DSĐH. Trần Thị Bích",
        ChuHoSo_NgaySinh="05/03/1985",
        ChuHoSo_GioiTinh="Nữ",
        ChuHoSo_SoDinhDanh=OWNER_ID,
        ChuHoSo_ThuongTru={"quocGia": "Việt Nam", "tinh": "Thành phố Đà Nẵng", "xa": "Phường Hải Châu",
                           "diaChi": "Số 12 Lê Lợi"},
        ChuHoSo_DienThoai="0905.111.222",
        NoiDungDeNghi="+ Cập nhật địa chỉ theo tên phường mới: Số 20 Trần Phú, phường Hải Châu, thành phố Đà Nẵng",
    )
    base.update(extra)
    return base


def _by(out):
    return {f["name"]: f["value"] for f in out}


def test_registry_khop_key_ke_khai_links():
    key = "cap-lai-dieu-chinh-gcn-du-dieu-kien-kinh-doanh-duoc-so-y-te"
    assert registry.get_procedure(key)
    assert registry.get_pipeline(key)
    assert registry.get_attach_pipeline(key)


def test_tu_nop_phan_i_theo_chu_co_so_khong_dung_o_khoa():
    ctx = {"formContext": {"applicantFullname": "TRẦN THỊ BÍCH", "applicantIdentityNumber": OWNER_ID}}
    out, warnings = mapper.enrich(_fields(**_owner()), ctx)
    v = _by(out)
    for locked in ("data[fullname]", "data[identityNumber]", "data[chonDoiTuong]"):
        assert locked not in v
    assert v["data[birthday]"] == "05/03/1985"
    assert v["data[gender]"] == "Nữ"
    assert v["data[phoneNumber]"] == "0905111222"
    assert v["data[province]"] == "Thành phố Đà Nẵng"
    assert v["data[isOwnerDossierCheck]"] is False
    assert v["data[ownerFullname]"] == "Trần Thị Bích"  # bỏ tiền tố "DSĐH."
    assert v["data[ownerIdentityNumber]"] == OWNER_ID
    assert v["data[ownerPhoneNumber]"] == "0905111222"
    assert v["data[ownerAddress]"] == "Số 12 Lê Lợi"
    assert v["data[ownerNation]"] == "Việt Nam"
    assert v["data[ghiChu]"].startswith("+ Cập nhật địa chỉ")
    assert not any("Nộp thay" in w for w in warnings)


def test_nop_thay_phan_i_tu_cccd_nguoi_nop_khong_lay_sdt_co_so():
    values = _owner(
        NguoiNop_HoTen="LÊ VĂN AN",
        NguoiNop_SoDinhDanh=NOP_ID,
        NguoiNop_NgaySinh="10/10/2003",
        NguoiNop_GioiTinh="Nam",
        NguoiNop_NgayCap="01/07/2025",
        NguoiNop_NoiCap="BỘ CÔNG AN",
        NguoiNop_ThuongTru="Thôn Đông, Xã Nghi Lộc, Tỉnh Nghệ An",
    )
    ctx = {"formContext": {"applicantFullname": "Lê Văn An", "applicantIdentityNumber": NOP_ID}}
    out, warnings = mapper.enrich(_fields(**values), ctx)
    v = _by(out)
    assert v["data[birthday]"] == "10/10/2003"
    assert v["data[gender]"] == "Nam"
    assert v["data[idIssuePlace]"] == "Bộ Công an"
    assert v["data[province]"] == "Tỉnh Nghệ An"
    assert "data[phoneNumber]" not in v  # SĐT trên Đơn là của cơ sở
    assert v["data[ownerFullname]"] == "Trần Thị Bích"
    assert v["data[ownerIdentityNumber]"] == OWNER_ID
    assert v["data[ownerBirthday]"] == "05/03/1985"
    assert any("số điện thoại người nộp" in w for w in warnings)


def test_nop_thay_cccd_khong_khop_tai_khoan_thi_khong_dien_phan_i():
    values = _owner(NguoiNop_HoTen="PHẠM VĂN BÌNH", NguoiNop_SoDinhDanh="001099000111",
                    NguoiNop_NgaySinh="01/01/1999")
    ctx = {"formContext": {"applicantFullname": "Lê Văn An", "applicantIdentityNumber": NOP_ID}}
    v = _by(mapper.enrich(_fields(**values), ctx)[0])
    assert "data[birthday]" not in v
    assert v["data[ownerFullname]"] == "Trần Thị Bích"


def test_noi_cap_cchn_so_y_te_khong_dien_vao_noi_cap_cccd():
    values = _owner(ChuHoSo_NoiCap="Sở Y tế thành phố Đà Nẵng")
    ctx = {"formContext": {"applicantIdentityNumber": OWNER_ID}}
    v = _by(mapper.enrich(_fields(**values), ctx)[0])
    assert "data[ownerIdIssuePlace]" not in v
    assert "data[idIssuePlace]" not in v


def test_khong_co_tai_khoan_thi_khong_dung_phan_i():
    out, warnings = mapper.enrich(_fields(**_owner()), {})
    v = _by(out)
    assert "data[birthday]" not in v and "data[phoneNumber]" not in v
    assert v["data[ownerFullname]"] == "Trần Thị Bích"
    assert any("tài khoản đang đăng nhập" in w for w in warnings)


def test_neo_nguoi_nop_chi_nhan_trang_cccd_khong_nhan_gcn_dkhkd():
    gcn = (
        "GIẤY CHỨNG NHẬN ĐĂNG KÝ HỘ KINH DOANH\n6. Thông tin về chủ hộ kinh doanh\nHọ và tên: TRẦN THỊ BÍCH\n"
        f"Số định danh cá nhân: {OWNER_ID}"
    )
    cccd = f"CĂN CƯỚC CÔNG DÂN\nSố định danh cá nhân: {OWNER_ID}\nHọ và tên: TRẦN THỊ BÍCH"
    docs = [{"text": f"Trang 1/2\n{gcn}\nTrang 2/2\n{cccd}"}]
    idx, chunk = find_submitter_card(docs, "tran thi bich", OWNER_ID)
    assert idx == 1 and "CĂN CƯỚC" in chunk and "HỘ KINH DOANH" not in chunk
    assert find_submitter_card([{"text": gcn}], "tran thi bich", OWNER_ID) is None


# ---------------- Planner ----------------
def _plan(pages: list[tuple[str, str]], name: str = "ho_so.pdf"):
    """1 PDF gộp: pages = [(type LLM trả, ocr text)], mỗi phần tử 1 trang."""
    raw_files = [{"name": name, "type": "application/pdf"}]
    n = len(pages)
    meta = {0: {"pageCount": n, "pageBoundariesAvailable": True}}
    page_text = {0: {i + 1: text for i, (_, text) in enumerate(pages)}}
    full = {0: "\n".join(text for _, text in pages)}
    raw_segments = [
        {"fileIndex": 0, "pageFrom": i + 1, "pageTo": i + 1, "type": t, "documentName": ""}
        for i, (t, _) in enumerate(pages)
    ]
    errors: list[str] = []
    segments = P._validated_segments(raw_segments, raw_files, meta, errors)
    return P.build_plan_items(raw_files, segments, meta, page_text, full)


def test_pdf_gop_dieu_chinh_tach_dung_dong():
    attachments, classified, warnings = _plan([
        ("giay_to_phap_ly", "GIẤY CHỨNG NHẬN ĐĂNG KÝ HỘ KINH DOANH"),
        ("giay_to_phap_ly", "GIẤY CHỨNG NHẬN ĐẠT THỰC HÀNH TỐT CƠ SỞ BÁN LẺ THUỐC (GPP)"),
        ("don_dieu_chinh", "ĐƠN ĐỀ NGHỊ Điều chỉnh Giấy chứng nhận đủ điều kiện kinh doanh dược"),
        ("cccd", "CĂN CƯỚC CÔNG DÂN"),
    ])
    rows = [(a["componentIndex"], a["sourceSegments"][0]["pageIndexes"]) for a in attachments]
    assert rows == [(5, [0]), (5, [1]), (3, [2])]
    assert all(a["target"] == "attp-row" and a["loaiBan"] == "Bản chính" for a in attachments)
    assert classified[-1]["target"] == "skip"  # CCCD không đính
    assert not any("Không tìm thấy Đơn" in w for w in warnings)


def test_gcn_dkkd_cu_chi_dinh_dong_2_khi_cap_lai():
    gcn = ("gcn_du_dkkd_duoc", "GIẤY CHỨNG NHẬN ĐỦ ĐIỀU KIỆN KINH DOANH DƯỢC Số: 123/ĐKKDD-ABC")
    dieu_chinh = _plan([("don_dieu_chinh", "ĐƠN ĐỀ NGHỊ Điều chỉnh"), gcn])
    assert [a["componentIndex"] for a in dieu_chinh[0]] == [3]
    assert any("dòng 2 chỉ dùng khi CẤP LẠI" in w for w in dieu_chinh[2])

    cap_lai = _plan([("don_cap_lai", "ĐƠN ĐỀ NGHỊ Cấp lại"), gcn])
    assert [a["componentIndex"] for a in cap_lai[0]] == [1, 2]


def test_rule_du_phong_nhan_don_truoc_gcn_va_cchn():
    don = (
        "ĐƠN ĐỀ NGHỊ Điều chỉnh Giấy chứng nhận đủ điều kiện kinh doanh dược\nSố CCHN Dược: 0001/CCHN-D-SYT\n"
        "Đã được cấp Giấy chứng nhận đủ điều kiện kinh doanh dược"
    )
    attachments, _, _ = _plan([("other", don), ("other", "CHỨNG CHỈ HÀNH NGHỀ DƯỢC Số 0002/CCHN-D-SYT")])
    assert [a["detectedType"] for a in attachments] == ["don_dieu_chinh", "cchn_duoc"]


def test_thuyet_minh_mau_11_pl_ii_khong_nham_don_cap_lai():
    text = "TÀI LIỆU THUYẾT MINH cơ sở đáp ứng các biện pháp bảo đảm an ninh, không để thất thoát thuốc"
    attachments, _, _ = _plan([("other", text)])
    assert attachments[0]["componentIndex"] == 6


def test_canh_bao_thieu_thuyet_minh_khi_pham_vi_co_thuoc_gay_nghien():
    _, _, warnings = _plan([
        ("don_dieu_chinh", "ĐƠN ĐỀ NGHỊ Điều chỉnh ... thuốc dạng phối hợp có chứa dược chất gây nghiện"),
    ])
    assert any("Tài liệu thuyết minh" in w for w in warnings)
