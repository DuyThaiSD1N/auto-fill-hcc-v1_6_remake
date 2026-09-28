"""Unit test pipeline "[Đà Nẵng] Đăng ký biến động ... do chia, tách, hợp nhất, sáp nhập tổ chức..." — mã 1.013977.

Mapper: chủ hồ sơ tổ chức theo tên mới (chọn "Tổ chức", bỏ tích, mã DN), ô khoá theo tài khoản không phát, nhân
thân người nộp từ CCCD khớp tài khoản rồi mới tới giấy ủy quyền khớp tài khoản, SĐT của người được ủy quyền khi họ
là người nộp. Planner: PDF gộp nhiều chục trang → mỗi dòng MỘT file gộp, giấy tờ chính trước, đính kèm chung sau.
Dữ liệu đều là ví dụ bịa.
"""

from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.attach import (
    planner as P,
)
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process import mapper
from app.pipelines.dang_ky_bien_dong_chia_tach_hop_nhat_sap_nhap_to_chuc_cap_gcn_tung_thua.process.runner import (
    find_submitter_card,
    trim_bulky_pages,
)
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "dang-ky-bien-dong-chia-tach-hop-nhat-sap-nhap-to-chuc-cap-gcn-tung-thua"
NOP_ID = "001205098765"  # chữ số thứ 4 = 2 → Nam, sinh thế kỷ 21.
CTX = {"formContext": {"applicantFullname": "Trần Văn Bình", "applicantIdentityNumber": NOP_ID}}
TEN_MOI = "CÔNG TY TNHH PHÁT TRIỂN NHÀ HOA SEN"


def _fields(**values):
    return [{"name": k, "value": v} for k, v in values.items()]


def _to_chuc(**extra):
    base = dict(
        ChuHoSo_LoaiChuThe="Tổ chức",
        ChuHoSo_HoTen=TEN_MOI,
        ChuHoSo_SoDinhDanh="0301234567",
        ChuHoSo_DiaChi="12A Nguyễn Văn Linh, phường Hải Châu, TP. Đà Nẵng",
        ChuHoSo_DienThoai="0905111222",
        ChuHoSo_Email="www.hoasen.example.com",
        NoiDungBienDong="Thay đổi tên người sử dụng đất trên Giấy chứng nhận số AB 123456",
        UyQuyen_HoTen="TRẦN VĂN BÌNH",
        UyQuyen_SoDinhDanh=NOP_ID,
        UyQuyen_NgayCap="21/08/2022",
        UyQuyen_NoiCap="Cục QLHC về TTXH",
        UyQuyen_DienThoai="0978 111 333",
    )
    base.update(extra)
    return base


def _by(out):
    return {f["name"]: f["value"] for f in out}


def test_registry_khop_key_ke_khai_links():
    assert registry.get_procedure(KEY)
    assert registry.get_pipeline(KEY)
    assert registry.get_attach_pipeline(KEY)
    assert any(link["key"] == KEY and link["code"] == "1.013977" for link in KE_KHAI_LINKS)


def test_to_chuc_nop_qua_nguoi_duoc_uy_quyen():
    out, warnings = mapper.enrich(_fields(**_to_chuc()), CTX)
    got = _by(out)
    assert got["data[chonDoiTuong]"] == "Tổ chức"
    assert got["data[isOwnerDossier]"] is False
    assert got["data[ownerFullname]"] == TEN_MOI
    assert got["data[organization]"] == TEN_MOI
    assert got["data[taxCode]"] == "0301234567"
    # Không có CCCD → lấy ngày cấp/nơi cấp theo giấy UQ khớp tài khoản; giới tính suy từ số định danh.
    assert got["data[identityDate]"] == "21/08/2022"
    assert got["data[identityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert got["data[gender]"] == "Nam"
    assert any("suy từ số định danh" in w for w in warnings)
    # SĐT của người được ủy quyền (người nộp), không phải SĐT tổ chức trên Đơn.
    assert got["data[phoneNumber]"] == "0978111333"
    # Website không phải email.
    assert "data[email]" not in got
    assert got["data[province]"] == "Thành phố Đà Nẵng"
    assert got["data[district]"] == "Phường Hải Châu"
    assert got["data[address]"] == "12A Nguyễn Văn Linh"
    for locked in ("data[fullname]", "data[birthday]", "data[identityNumber]"):
        assert locked not in got
    request = got["data[noidungyeucaugiaiquyet]"]
    assert request.startswith(f"ÔNG/BÀ: {TEN_MOI} ĐỀ NGHỊ GIẢI QUYẾT Đăng ký biến động thay đổi quyền sử dụng đất")
    assert request.endswith("Nội dung biến động: Thay đổi tên người sử dụng đất trên Giấy chứng nhận số AB 123456")


def test_cccd_khop_tai_khoan_uu_tien_hon_giay_uy_quyen():
    values = _to_chuc(NguoiNop_HoTen="TRẦN VĂN BÌNH", NguoiNop_SoDinhDanh=NOP_ID, NguoiNop_GioiTinh="Nữ",
                      NguoiNop_NgayCap="01/07/2025", NguoiNop_NoiCap="Bộ Công an")
    out, warnings = mapper.enrich(_fields(**values), CTX)
    got = _by(out)
    assert got["data[gender]"] == "Nữ"
    assert got["data[identityDate]"] == "01/07/2025"
    assert got["data[identityAgency]"] == "Bộ Công an"
    assert not any("suy từ số định danh" in w for w in warnings)


def test_nguoi_duoc_uy_quyen_khac_tai_khoan_thi_dung_sdt_don_va_bo_trong_nhan_than():
    values = _to_chuc(UyQuyen_HoTen="LÊ THỊ HOA", UyQuyen_SoDinhDanh="001190011111")
    out, warnings = mapper.enrich(_fields(**values), CTX)
    got = _by(out)
    assert got["data[phoneNumber]"] == "0905111222"
    for name in ("data[gender]", "data[identityDate]", "data[identityAgency]"):
        assert name not in got
    assert any("khác tài khoản" in w for w in warnings)
    assert any("không có CCCD hay giấy ủy quyền khớp" in w for w in warnings)


def test_khong_co_tai_khoan():
    got = _by(mapper.enrich(_fields(**_to_chuc()), {})[0])
    assert "data[gender]" not in got and "data[identityDate]" not in got
    assert got["data[isOwnerDossier]"] is False
    assert got["data[phoneNumber]"] == "0905111222"


_TRU_SO_HCM = {"quocGia": "Việt Nam", "tinh": "Tp. Hồ Chí Minh", "xa": "phường Bến Thành", "diaChi": "25 Lê Lợi"}


def test_tru_so_ngoai_da_nang_dien_theo_dia_chi_thua_dat():
    # Cổng Đà Nẵng không chọn được tỉnh khác → theo mapping, 3 ô địa chỉ lấy theo thửa đất (phường cũ → mới).
    values = _to_chuc(
        ChuHoSo_DiaChi=_TRU_SO_HCM,
        ThuaDat_DiaChi="Lô B2 đường Võ Văn Kiệt, phường An Hải Đông, quận Sơn Trà, thành phố Đà Nẵng",
    )
    out, warnings = mapper.enrich(_fields(**values), CTX)
    got = _by(out)
    assert got["data[province]"] == "Thành phố Đà Nẵng"
    assert got["data[district]"] == "Phường An Hải"
    assert got["data[address]"] == "Lô B2 đường Võ Văn Kiệt"
    assert any("ngoài Đà Nẵng" in w and "25 Lê Lợi" in w for w in warnings)


def test_tru_so_da_nang_khong_dung_dia_chi_thua_dat():
    values = _to_chuc(ThuaDat_DiaChi="Lô B2 đường Võ Văn Kiệt, phường An Hải, thành phố Đà Nẵng")
    got = _by(mapper.enrich(_fields(**values), CTX)[0])
    assert got["data[district]"] == "Phường Hải Châu"
    assert got["data[address]"] == "12A Nguyễn Văn Linh"


def test_tru_so_ngoai_da_nang_khong_co_thua_dat():
    out, warnings = mapper.enrich(_fields(**_to_chuc(ChuHoSo_DiaChi=_TRU_SO_HCM)), CTX)
    got = _by(out)
    assert "data[province]" not in got and "data[district]" not in got
    assert got["data[address]"].startswith("25 Lê Lợi, Phường ")
    assert got["data[address]"].endswith(", Thành phố Hồ Chí Minh")
    assert any("tự chọn" in w for w in warnings)


def test_neo_nguoi_nop_chi_nhan_trang_cccd():
    uq = f"GIẤY ỦY QUYỀN\nBên được ủy quyền: TRẦN VĂN BÌNH Số CCCD {NOP_ID}"
    cccd = f"CĂN CƯỚC\nSố định danh cá nhân: {NOP_ID}\nHọ, chữ đệm và tên khai sinh: TRẦN VĂN BÌNH"
    docs = [{"text": f"Trang 1/2\n{uq}\nTrang 2/2\n{cccd}"}]
    idx, chunk = find_submitter_card(docs, "tran van binh", NOP_ID)
    assert idx == 1 and "CĂN CƯỚC" in chunk and "GIẤY ỦY QUYỀN" not in chunk


def test_bo_khoi_giay_phep_xay_dung_va_bien_ban_hdtv_truoc_khi_gui_llm():
    pages = [
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐƠN ĐĂNG KÝ BIẾN ĐỘNG Mẫu số 18",
        "Cam đoan nội dung kê khai",
        "CÔNG TY TNHH A Số 01/2026/QĐ-HĐTV CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM QUYẾT ĐỊNH",
        "Điều 2. Tên công ty ...",
        "UBND THÀNH PHỐ ĐÀ NẴNG CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM SỞ XÂY DỰNG GIẤY PHÉP XÂY DỰNG",
        "2 - Nhà thầu thiết kế ...",
        "Mẫu số: 01/LPTB TỜ KHAI LỆ PHÍ TRƯỚC BẠ",
        "2 - Địa chỉ thửa đất ...",
    ]
    text = "\n".join(f"───── Trang {i}/{len(pages)} ─────\n{p}" for i, p in enumerate(pages, start=1))
    out = trim_bulky_pages([{"name": "a.pdf", "text": text}])[0]["text"]
    assert [p for p in pages if p in out] == [pages[0], pages[1], pages[6], pages[7]]
    assert trim_bulky_pages([{"text": "không có header trang"}])[0]["text"] == "không có header trang"


# ---------------- Planner ----------------
_GCN_BIA = "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT QUYỀN SỞ HỮU NHÀ Ở VÀ TÀI SẢN KHÁC GẮN LIỀN VỚI ĐẤT AB 123456"
_GCN_BS = "TRANG BỔ SUNG GIẤY CHỨNG NHẬN Số vào sổ cấp GCN: CT01234"
_DON = ("ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\nMẫu số 18\n"
        "3. Giấy tờ: (1) Giấy chứng nhận đã cấp; (2) Giấy chứng nhận đăng ký doanh nghiệp; (3) Giấy ủy quyền")
_CV_NH = "V/v chấp thuận đăng ký biến động tài sản bảo đảm do thay đổi tên doanh nghiệp — Ngân hàng TMCP X"
_UQ = "GIẤY ỦY QUYỀN\nI. BÊN ỦY QUYỀN: NGÂN HÀNG\nII. BÊN ĐƯỢC ỦY QUYỀN: Họ và tên ..."
_BANG = "TÌNH HÌNH THAY ĐỔI ĐĂNG KÝ DOANH NGHIỆP TỪ THỜI ĐIỂM CẤP GIẤY CHỨNG NHẬN QSDĐ"
_DKDN = "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP CÔNG TY TNHH\nMã số doanh nghiệp: 0301234567\nĐăng ký thay đổi lần thứ: 14"
_QD = "HỘI ĐỒNG THÀNH VIÊN\nQUYẾT ĐỊNH V/v thay đổi tên công ty\nCăn cứ Giấy chứng nhận đăng ký doanh nghiệp"
_GPXD = "GIẤY PHÉP XÂY DỰNG Số: 12/GPXD\nThông báo kết quả thẩm định"
_LPTB = "TỜ KHAI LỆ PHÍ TRƯỚC BẠ NHÀ, ĐẤT Mẫu số 01/LPTB [04] Người nộp thuế"
_SDDPNN = "TỜ KHAI THUẾ SỬ DỤNG ĐẤT PHI NÔNG NGHIỆP Mẫu số 02/TK-SDDPNN"

# Hồ sơ gộp 1 PDF theo đúng thứ tự thường gặp (trang 1-based).
_PAGES = [
    ("gcn_da_cap", _GCN_BIA), ("gcn_da_cap", _GCN_BS),       # 1-2
    ("don_mau_18", _DON), ("don_mau_18", "Cam đoan ... người viết đơn"),  # 3-4
    ("van_ban_the_chap", _CV_NH),                               # 5
    ("van_ban_dai_dien", _UQ),                                  # 6
    ("bang_thay_doi_dkdn", _BANG),                              # 7
    ("gcn_dang_ky_doanh_nghiep", _DKDN), ("gcn_dang_ky_doanh_nghiep", _DKDN),  # 8-9
    ("qd_to_chuc_lai", _QD), ("qd_to_chuc_lai", "BIÊN BẢN HỌP HỘI ĐỒNG THÀNH VIÊN"),  # 10-11
    ("giay_to_tai_san", _GPXD),                                 # 12
    ("to_khai_thue", _LPTB),                                    # 13
    ("to_khai_thue", _SDDPNN),                                  # 14
    ("cccd", "CĂN CƯỚC CÔNG DÂN"),                              # 15
]


def _plan_files(files: list[list[tuple[str, str]]], llm: bool = True):
    """files = [[(type LLM trả, ocr text trang), ...], ...] — mỗi file có header trang."""
    raw_files, meta, page_text, full, raw_segments = [], {}, {}, {}, []
    for fi, pages in enumerate(files):
        raw_files.append({"name": f"file{fi}.pdf", "type": "application/pdf"})
        meta[fi] = {"pageCount": len(pages), "pageBoundariesAvailable": True}
        page_text[fi] = {i + 1: text for i, (_, text) in enumerate(pages)}
        full[fi] = "\n".join(text for _, text in pages)
        raw_segments += [
            {"fileIndex": fi, "pageFrom": i + 1, "pageTo": i + 1, "type": t if llm else "other", "documentName": ""}
            for i, (t, _) in enumerate(pages)
        ]
    segments = P._validated_segments(raw_segments, raw_files, meta, [])
    return P.build_plan_items(raw_files, segments, meta, page_text, full)


def _rows(attachments):
    return {a["componentIndex"]: [s["pageIndexes"] for s in a["sourceSegments"]] for a in attachments}


def test_pdf_gop_moi_dong_mot_file_chinh_truoc_dinh_kem_chung_sau():
    attachments, classified, warnings = _plan_files([_PAGES])
    assert _rows(attachments) == {
        1: [[2, 3], [12, 13]],       # Đơn + tờ khai LPTB, SDĐPNN (liền trang → 1 đoạn)
        2: [[0, 1], [11]],           # GCN + giấy phép xây dựng
        3: [[5], [4]],               # Giấy UQ trước, công văn ngân hàng sau
        7: [[7, 8], [6]],            # GCN ĐKDN trước, bảng tình hình thay đổi sau
        8: [[9, 10]],                # QĐ + biên bản họp HĐTV
    }
    assert len(attachments) == 5
    assert [a["loaiBan"] for a in attachments] == ["Bản chính"] + ["Bản sao"] * 4
    assert all(a["target"] == "attp-row" and a["fileIndex"] == 0 for a in attachments)
    assert classified[-1]["target"] == "skip"  # CCCD
    assert not any("bắt buộc" in w for w in warnings)


def test_rule_du_phong_khi_llm_tra_other():
    attachments, _, _ = _plan_files([_PAGES], llm=False)
    rows = _rows(attachments)
    assert rows[1][0] == [2]            # trang Đơn có tiêu đề
    assert rows[2] == [[0, 1], [11]]
    assert rows[3] == [[5], [4]]
    assert rows[7] == [[7, 8], [6]]
    assert rows[8][0][0] == 9


def test_nhieu_file_rieng_le_khong_tach_trang():
    attachments, _, _ = _plan_files([
        [("don_mau_18", _DON)],
        [("gcn_da_cap", _GCN_BIA), ("gcn_da_cap", _GCN_BS)],
        [("to_khai_thue", _LPTB)],
    ])
    by_row = {a["componentIndex"]: a["sourceSegments"] for a in attachments}
    assert by_row[1] == [{"fileIndex": 0, "pageIndexes": None}, {"fileIndex": 2, "pageIndexes": None}]
    assert by_row[2] == [{"fileIndex": 1, "pageIndexes": None}]


def test_nghia_vu_tai_chinh_theo_qd_dieu_chinh_quy_hoach():
    with_qd, _, _ = _plan_files([[("qd_dieu_chinh_quy_hoach", "QĐ"), ("nghia_vu_tai_chinh", "Giấy nộp tiền")]])
    assert _rows(with_qd) == {9: [[0], [1]]}
    without_qd, _, _ = _plan_files([[("don_mau_18", _DON), ("nghia_vu_tai_chinh", "Giấy nộp tiền")]])
    assert _rows(without_qd) == {1: [[0], [1]]}


def test_component_name_khong_trung_dong_khac():
    portal = {
        4: "(4) Quyết định phê duyệt quy hoạch xây dựng chi tiết của cơ quan có thẩm quyền kèm theo bản đồ quy "
           "hoạch xây dựng chi tiết và bản đồ địa chính hoặc mảnh trích đo bản đồ địa chính.",
        9: "(4) Quyết định phê duyệt điều chỉnh quy hoạch xây dựng chi tiết của cơ quan có thẩm quyền kèm theo bản "
           "đồ điều chỉnh quy hoạch xây dựng chi tiết và bản đồ địa chính hoặc mảnh trích đo bản đồ địa chính; "
           "trường hợp phải xác định lại giá đất thì nộp thêm giấy tờ chứng minh đã hoàn thành nghĩa vụ tài chính "
           "về đất đai.",
    }
    for idx, row in P._ROWS.items():
        for other_idx, text in portal.items():
            if other_idx != idx:
                assert row["componentName"].lower() not in text.lower()
