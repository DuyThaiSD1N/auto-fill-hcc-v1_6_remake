"""Unit test pipeline "[Đà Nẵng] Đăng ký đất đai lần đầu đối với trường hợp được Nhà nước giao đất để quản lý" — mã
1.012756.

Mapper: chủ hồ sơ tổ chức (chọn "Tổ chức", bỏ tích, mã DN), ô khoá theo tài khoản không phát, nhân thân người nộp
theo thứ tự CCCD khớp tài khoản → người đại diện theo pháp luật khớp tài khoản → giấy ủy quyền khớp tài khoản; địa
chỉ đơn vị cũ được chuyển sang đơn vị mới; nội dung yêu cầu = câu khung + ô đề nghị được đánh dấu. Planner: PDF gộp
→ mỗi giấy tờ MỘT file, dòng 1 = Đơn + giấy tờ kèm theo mục 5, dòng 2 = Báo cáo rà soát + trích lục, bỏ trang
trắng. Dữ liệu đều là ví dụ bịa.
"""

from app.pipelines.dang_ky_dat_dai_lan_dau_nha_nuoc_giao_quan_ly.attach import planner as P
from app.pipelines.dang_ky_dat_dai_lan_dau_nha_nuoc_giao_quan_ly.process import mapper
from app.pipelines.dang_ky_dat_dai_lan_dau_nha_nuoc_giao_quan_ly.process.runner import trim_bulky_pages
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

KEY = "dang-ky-dat-dai-lan-dau-nha-nuoc-giao-quan-ly"
DD_ID = "048085001234"  # chữ số thứ 4 = 0 → Nam, sinh thế kỷ 20.
CTX = {"formContext": {"applicantFullname": "Nguyễn Văn Hải", "applicantIdentityNumber": DD_ID}}
TEN = "CÔNG TY TNHH CHẾ BIẾN NÔNG SẢN AN PHÚ"


def _fields(**values):
    return [{"name": k, "value": v} for k, v in values.items()]


def _to_chuc(**extra):
    base = dict(
        ChuHoSo_LoaiChuThe="Tổ chức",
        ChuHoSo_HoTen=TEN,
        ChuHoSo_SoDinhDanh="0401234567",
        ChuHoSo_DiaChi="Lô A2, cụm công nghiệp Tây An, phường Điện Bàn Bắc, thành phố Đà Nẵng",
        ChuHoSo_DienThoai="0236 3888 999 / 0905.123.456",
        ChuHoSo_Email="lienhe@anphu.example.com",
        Don_DeNghi=["☑ b) Đề nghị cấp Giấy chứng nhận", "d) Đề nghị khác (nếu có): ……"],
        DaiDien_HoTen="NGUYỄN VĂN HẢI",
        DaiDien_SoDinhDanh=DD_ID,
        DaiDien_GioiTinh="Nam",
        DaiDien_NgayCap="18/06/2023",
        DaiDien_NoiCap="Cục Cảnh sát QLHC về TTXH",
    )
    base.update(extra)
    return base


def _by(out):
    return {f["name"]: f["value"] for f in out}


def test_registry_khop_key_ke_khai_links():
    assert registry.get_procedure(KEY)
    assert registry.get_pipeline(KEY)
    assert registry.get_attach_pipeline(KEY)
    assert any(link["key"] == KEY and link["code"] == "1.012756" for link in KE_KHAI_LINKS)


def test_to_chuc_nguoi_dai_dien_theo_phap_luat_di_nop():
    out, warnings = mapper.enrich(_fields(**_to_chuc()), CTX)
    got = _by(out)
    assert got["data[chonDoiTuong]"] == "Tổ chức"
    assert got["data[isOwnerDossier]"] is False
    assert got["data[ownerFullname]"] == TEN
    assert got["data[organization]"] == TEN
    assert got["data[taxCode]"] == "0401234567"
    # Người đại diện theo pháp luật (GCN ĐKDN) khớp tài khoản → giới tính, ngày cấp, nơi cấp theo GCN ĐKDN.
    assert got["data[gender]"] == "Nam"
    assert got["data[identityDate]"] == "18/06/2023"
    assert got["data[identityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    # Đơn ghi cả máy bàn trụ sở lẫn di động → lấy di động.
    assert got["data[phoneNumber]"] == "0905123456"
    assert got["data[email]"] == "lienhe@anphu.example.com"
    assert got["data[province]"] == "Thành phố Đà Nẵng"
    assert got["data[district]"] == "Phường Điện Bàn Bắc"
    assert got["data[address]"] == "Lô A2, cụm công nghiệp Tây An"
    for locked in ("data[fullname]", "data[birthday]", "data[identityNumber]", "data[nation]"):
        assert locked not in got
    assert got["data[noidungyeucaugiaiquyet]"] == (
        f"ÔNG/BÀ: {TEN} (chủ hồ sơ) ĐỀ NGHỊ GIẢI QUYẾT Đăng ký đất đai lần đầu đối với trường hợp được Nhà nước "
        "giao đất để quản lý. Đề nghị cấp Giấy chứng nhận."
    )
    assert not any("suy từ số định danh" in w for w in warnings)
    assert not any("không phải người đại diện" in w for w in warnings)
    assert not any("không khớp" in w for w in warnings)


def test_cccd_khop_tai_khoan_uu_tien_hon_gcn_dang_ky_doanh_nghiep():
    values = _to_chuc(NguoiNop_HoTen="NGUYỄN VĂN HẢI", NguoiNop_SoDinhDanh=DD_ID, NguoiNop_GioiTinh="Nam",
                      NguoiNop_NgayCap="02/03/2025", NguoiNop_NoiCap="Bộ Công an")
    got = _by(mapper.enrich(_fields(**values), CTX)[0])
    assert got["data[identityDate]"] == "02/03/2025"
    assert got["data[identityAgency]"] == "Bộ Công an"


def test_danh_xung_ong_ba_thanh_gioi_tinh():
    got = _by(mapper.enrich(_fields(**_to_chuc(DaiDien_GioiTinh="Bà")), CTX)[0])
    assert got["data[gender]"] == "Nữ"


def test_nguoi_duoc_uy_quyen_di_nop():
    ctx = {"formContext": {"applicantFullname": "Trần Thị Mai", "applicantIdentityNumber": "001195004321"}}
    values = _to_chuc(UyQuyen_HoTen="TRẦN THỊ MAI", UyQuyen_SoDinhDanh="001195004321", UyQuyen_NgayCap="10/10/2022",
                      UyQuyen_NoiCap="Cục QLHC về TTXH", UyQuyen_DienThoai="0978 111 333")
    out, warnings = mapper.enrich(_fields(**values), ctx)
    got = _by(out)
    assert got["data[identityDate]"] == "10/10/2022"
    assert got["data[identityAgency]"] == "Cục Cảnh sát quản lý hành chính về trật tự xã hội"
    assert got["data[gender]"] == "Nữ"  # suy từ số định danh (chữ số thứ 4 = 1)
    assert got["data[phoneNumber]"] == "0978111333"
    assert any("suy từ số định danh" in w for w in warnings)
    assert not any("không phải người đại diện" in w for w in warnings)


def test_tai_khoan_khong_khop_ai_thi_bo_trong_nhan_than_va_canh_bao():
    ctx = {"formContext": {"applicantFullname": "Lê Văn Cường", "applicantIdentityNumber": "001090009999"}}
    out, warnings = mapper.enrich(_fields(**_to_chuc()), ctx)
    got = _by(out)
    for name in ("data[gender]", "data[identityDate]", "data[identityAgency]"):
        assert name not in got
    assert got["data[phoneNumber]"] == "0905123456"
    assert any("không khớp" in w for w in warnings)
    assert any("không phải người đại diện theo pháp luật" in w and "NGUYỄN VĂN HẢI" in w for w in warnings)


def test_khong_co_tai_khoan():
    out, warnings = mapper.enrich(_fields(**_to_chuc()), {})
    got = _by(out)
    assert "data[gender]" not in got and "data[identityDate]" not in got
    assert got["data[isOwnerDossier]"] is False
    assert any("Không đọc được tài khoản" in w for w in warnings)


def test_dia_chi_don_vi_cu_chuyen_sang_don_vi_moi():
    values = _to_chuc(ChuHoSo_DiaChi="Lô A2, Cụm CN Tây An, Xã Điện Hòa, Thị xã Điện Bàn, Tỉnh Quảng Nam")
    got = _by(mapper.enrich(_fields(**values), CTX)[0])
    assert got["data[province]"] == "Thành phố Đà Nẵng"
    assert got["data[district]"] == "Phường Điện Bàn Bắc"
    assert got["data[address]"] == "Lô A2, Cụm CN Tây An"


def test_tru_so_ngoai_da_nang_dien_theo_dia_chi_thua_dat():
    values = _to_chuc(
        ChuHoSo_DiaChi={"quocGia": "Việt Nam", "tinh": "Tp. Hồ Chí Minh", "xa": "phường Bến Thành", "diaChi": "25 Lê Lợi"},
        ThuaDat_DiaChi="Lô A2, cụm công nghiệp Tây An, phường Điện Bàn Bắc, thành phố Đà Nẵng",
    )
    out, warnings = mapper.enrich(_fields(**values), CTX)
    got = _by(out)
    assert got["data[province]"] == "Thành phố Đà Nẵng"
    assert got["data[district]"] == "Phường Điện Bàn Bắc"
    assert got["data[address]"] == "Lô A2, cụm công nghiệp Tây An"
    assert any("ngoài Đà Nẵng" in w and "25 Lê Lợi" in w for w in warnings)


def test_noi_dung_de_nghi():
    assert mapper._de_nghi(["x a) Đề nghị đăng ký đất đai, tài sản gắn liền với đất", "☑ b) Đề nghị cấp Giấy chứng "
                            "nhận"]) == "Đề nghị đăng ký đất đai, tài sản gắn liền với đất. Đề nghị cấp Giấy chứng nhận"
    # "x" trơn chỉ là dấu tích khi có khoảng trắng theo sau — không ăn mất chữ đầu "Xác nhận".
    assert mapper._de_nghi("Xác nhận hiện trạng") == "Xác nhận hiện trạng"
    out, warnings = mapper.enrich(_fields(**_to_chuc(Don_DeNghi=None)), CTX)
    assert _by(out)["data[noidungyeucaugiaiquyet]"].endswith("được Nhà nước giao đất để quản lý.")
    assert any("Đơn mục 4" in w for w in warnings)


def test_bo_khoi_quyet_dinh_hop_dong_bien_ban_truoc_khi_gui_llm():
    pages = [
        "Mẫu số 15 CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM ĐƠN ĐĂNG KÝ ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT",
        "5. Những giấy tờ nộp kèm theo: (1) Quyết định cho thuê đất số 12/QĐ-UBND",
        "ỦY BAN NHÂN DÂN TỈNH A Số: 12/QĐ-UBND CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM QUYẾT ĐỊNH Về việc cho thuê đất",
        "Điều 2. Tổ chức thuê đất ...",
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM HỢP ĐỒNG THUÊ ĐẤT Số: 30/HĐTĐ",
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM BIÊN BẢN Triển khai quyết định và giao đất trên thực địa",
        "CÔNG TY TNHH A CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM BÁO CÁO Kết quả rà soát hiện trạng sử dụng đất "
        "Quyết định cho thuê đất số 12/QĐ-UBND của UBND tỉnh",
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP Mã số doanh nghiệp: 0401234567",
    ]
    text = "\n".join(f"───── Trang {i}/{len(pages)} ─────\n{p}" for i, p in enumerate(pages, start=1))
    out = trim_bulky_pages([{"name": "a.pdf", "text": text}])[0]["text"]
    assert [p for p in pages if p in out] == [pages[0], pages[1], pages[6], pages[7]]
    assert trim_bulky_pages([{"text": "không có header trang"}])[0]["text"] == "không có header trang"


# ---------------- Planner ----------------
_QH = "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM Độc lập - Tự do - Hạnh phúc\n"
_DON = ("Mẫu số 15 " + _QH + "ĐƠN ĐĂNG KÝ ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT\n5. Những giấy tờ nộp kèm theo: (1) "
        "Quyết định cho thuê đất; (2) Hợp đồng thuê đất; (10) Báo cáo kết quả rà soát hiện trạng sử dụng đất")
_LPTB = "Mẫu số: 01/LPTB " + _QH + "TỜ KHAI LỆ PHÍ TRƯỚC BẠ NHÀ, ĐẤT [04] Người nộp thuế"
_BC = _QH + "BÁO CÁO Kết quả rà soát hiện trạng sử dụng đất của tổ chức — Quyết định cho thuê đất số 12/QĐ-UBND"
_QD = "ỦY BAN NHÂN DÂN " + _QH + "QUYẾT ĐỊNH Về việc thu hồi đất và cho thuê đất"
_HD = _QH + "HỢP ĐỒNG THUÊ ĐẤT Số 30/HĐTĐ Bên cho thuê đất, Bên thuê đất"
_PL = _QH + "PHỤ LỤC HỢP ĐỒNG THUÊ ĐẤT Số 7/PL-HĐTĐ"
_BB = _QH + "BIÊN BẢN Triển khai quyết định và giao đất trên thực địa"
_TL = _QH + "TRÍCH LỤC SƠ ĐỒ ĐỊA HÌNH thửa đất"
_DKDN = _QH + "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP Mã số doanh nghiệp: 0401234567"
_PHIEU = _QH + "PHIẾU ĐO ĐẠC CHỈNH LÝ THỬA ĐẤT Thửa đất số 88; tờ bản đồ số 9"
_XN = "Mẫu số 04/LCHS " + _QH + "GIẤY XÁC NHẬN hoàn thành nghĩa vụ thuế"
_TB = _QH + "THÔNG BÁO về đơn giá thuê đất, thuê mặt nước"

# Hồ sơ gộp 1 PDF theo đúng thứ tự thường gặp: (type LLM trả cho đoạn, [ocr text từng trang], documentName).
_DOCS = [
    ("don_mau_15", [_DON, "Người sử dụng đất ký", "Cam đoan"], "Đơn đăng ký đất đai Mẫu 15"),       # 1-3
    ("to_khai_thue", [_LPTB, "[11] Điện thoại"], "Tờ khai lệ phí trước bạ"),                     # 4-5
    ("bao_cao_ra_soat", [_BC, "II. Hiện trạng", "VI. Kiến nghị"], "Báo cáo rà soát hiện trạng"),  # 6-8
    ("quyet_dinh", [_QD, "Điều 2", "Điều 3", "Nơi nhận"], "Quyết định 12 QĐ-UBND cho thuê đất"),  # 9-12
    ("quyet_dinh", [_QD, "Điều 1", "Điều 2", "Nơi nhận"], "Quyết định chủ trương đầu tư"),       # 13-16
    ("quyet_dinh", [_QD, "Nơi nhận"], "Quyết định điều chỉnh hình thức thuê đất"),               # 17-18
    ("hop_dong_thue_dat", [_HD, "Điều 2", "Điều 3", "Điều 4"], "Hợp đồng thuê đất 30 HĐTĐ"),     # 19-22
    ("hop_dong_thue_dat", [_PL, "Điều 1", "Ký tên"], "Phụ lục hợp đồng thuê đất"),  # 23-25
    ("bien_ban_giao_dat", [_BB, "", "Các bên ký", " . "], "Biên bản giao đất trên thực địa"),     # 26-29 (27, 29 trắng)
    ("trich_luc_ban_do", [_TL], "Trích lục sơ đồ địa hình"),                                      # 30
    ("gcn_dang_ky_doanh_nghiep", [_DKDN, "Người đại diện theo pháp luật"], "GCN đăng ký doanh nghiệp"),  # 31-32
    ("phieu_do_dac", [_PHIEU], "Phiếu đo đạc chỉnh lý thửa đất"),                                # 33
    ("nghia_vu_tai_chinh", [_XN, "Chi cục trưởng"], "Xác nhận hoàn thành nghĩa vụ thuế"),        # 34-35
    ("nghia_vu_tai_chinh", [_TB, "Cục trưởng"], "Thông báo đơn giá thuê đất"),                   # 36-37
    ("cccd", [_QH + "CĂN CƯỚC CÔNG DÂN"], "Căn cước công dân"),                                         # 38
]


def _plan(docs, llm: bool = True, split_pages: bool = False):
    """Một file PDF có header trang. llm=False: LLM trả other cho từng trang (chỉ còn rule OCR)."""
    texts, raw_segments, page = [], [], 1
    for doc_type, pages, name in docs:
        start = page
        texts += pages
        page += len(pages)
        if not llm or split_pages:
            raw_segments += [{"fileIndex": 0, "pageFrom": p, "pageTo": p, "type": doc_type if llm else "other",
                              "documentName": name} for p in range(start, page)]
        else:
            raw_segments.append({"fileIndex": 0, "pageFrom": start, "pageTo": page - 1, "type": doc_type,
                                 "documentName": name})
    raw_files = [{"name": "ho_so.pdf", "type": "application/pdf"}]
    meta = {0: {"pageCount": len(texts), "pageBoundariesAvailable": True}}
    page_text = {0: {i + 1: t for i, t in enumerate(texts)}}
    full = {0: "\n".join(texts)}
    segments = P._validated_segments(raw_segments, raw_files, meta, [])
    return P.build_plan_items(raw_files, segments, meta, page_text, full)


def test_pdf_gop_moi_giay_to_mot_file_dung_thu_tu():
    attachments, classified, warnings = _plan(_DOCS)
    row1 = [a for a in attachments if a["componentIndex"] == 1]
    row2 = [a for a in attachments if a["componentIndex"] == 2]
    assert [a["sourceSegments"][0]["pageIndexes"] for a in row1] == [
        [0, 1, 2],             # Đơn
        [8, 9, 10, 11],        # QĐ cho thuê đất
        [12, 13, 14, 15],      # QĐ chủ trương đầu tư
        [16, 17],              # QĐ điều chỉnh
        [18, 19, 20, 21],      # Hợp đồng thuê đất
        [22, 23, 24],          # Phụ lục hợp đồng
        [25, 27],              # Biên bản giao đất — bỏ 2 mặt sau trắng
        [30, 31],              # GCN ĐKDN
        [32],                  # Phiếu đo đạc
        [33, 34],              # Xác nhận nghĩa vụ thuế
        [35, 36],              # Thông báo đơn giá thuê đất
        [3, 4],                # Tờ khai lệ phí trước bạ
    ]
    assert [a["sourceSegments"][0]["pageIndexes"] for a in row2] == [[5, 6, 7], [29]]
    assert [a["documentName"][:6] for a in row1] == [f"D1-{i:02d} " for i in range(1, 13)]
    assert [a["documentName"] for a in row2] == ["D2-01 Báo cáo rà soát hiện trạng", "D2-02 Trích lục sơ đồ địa hình"]
    assert row1[1]["documentName"] == "D1-02 Quyết định 12 QĐ-UBND cho thuê đất"
    assert all(a["loaiBan"] == "Bản chính" and a["target"] == "attp-row" for a in attachments)
    assert {a["componentName"] for a in row1} == {"Đơn đăng ký đất đai, tài sản gắn liền với đất"}
    assert all(len(a["documentName"]) <= 50 for a in attachments)
    # FE chống đính trùng theo 24 ký tự đầu của tên → các file cùng dòng phải khác nhau ngay từ đầu.
    assert len({a["documentName"][:24] for a in attachments}) == len(attachments)
    assert classified[-1]["target"] == "skip"  # CCCD
    assert any("trang trắng" in w and "27, 29" in w for w in warnings)
    assert not any("bắt buộc" in w for w in warnings)


def test_llm_tach_tung_trang_cung_loai_gop_lai_theo_van_ban():
    # LLM cắt mỗi trang một đoạn: trang nối tiếp (không quốc hiệu) gộp vào văn bản của nó, nhưng ba quyết định
    # liền nhau vẫn là ba file (trang đầu mỗi quyết định có quốc hiệu).
    split, _, _ = _plan(_DOCS, split_pages=True)
    whole, _, _ = _plan(_DOCS)
    assert [a["sourceSegments"] for a in split] == [a["sourceSegments"] for a in whole]
    assert len([a for a in split if a["detectedType"] == "quyet_dinh"]) == 3


def test_rule_du_phong_khi_llm_tra_other():
    # LLM hỏng hẳn (mọi trang "other"): rule nhận trang có tiêu đề, trang nối tiếp gộp vào văn bản đứng trước.
    ruled, _, _ = _plan(_DOCS, llm=False)
    whole, _, _ = _plan(_DOCS)
    assert [(a["componentIndex"], a["detectedType"], a["sourceSegments"]) for a in ruled] == [
        (a["componentIndex"], a["detectedType"], a["sourceSegments"]) for a in whole
    ]


def test_nhieu_file_rieng_le_khong_tach_trang():
    raw_files = [{"name": f"f{i}.pdf", "type": "application/pdf"} for i in range(3)]
    meta = {0: {"pageCount": 2, "pageBoundariesAvailable": True},
            1: {"pageCount": 1, "pageBoundariesAvailable": True},
            2: {"pageCount": 1, "pageBoundariesAvailable": False}}
    page_text = {0: {1: _DON, 2: "Cam đoan"}, 1: {1: _BC}, 2: {1: _TL}}
    full = {i: "\n".join(p.values()) for i, p in page_text.items()}
    raw = [{"fileIndex": 0, "pageFrom": 1, "pageTo": 2, "type": "don_mau_15"},
           {"fileIndex": 1, "pageFrom": 1, "pageTo": 1, "type": "bao_cao_ra_soat"},
           {"fileIndex": 2, "pageFrom": 1, "pageTo": 1, "type": "trich_luc_ban_do"}]
    segments = P._validated_segments(raw, raw_files, meta, [])
    attachments, _, warnings = P.build_plan_items(raw_files, segments, meta, page_text, full)
    assert [(a["componentIndex"], a["sourceSegments"]) for a in attachments] == [
        (1, [{"fileIndex": 0, "pageIndexes": None}]),
        (2, [{"fileIndex": 1, "pageIndexes": None}]),
        (2, [{"fileIndex": 2, "pageIndexes": None}]),
    ]
    assert [a["documentName"] for a in attachments] == [
        "D1-01 Đơn đăng ký đất đai Mẫu 15", "D2-01 Báo cáo rà soát hiện trạng sử dụng đất", "D2-02 Trích lục bản đồ thửa đất"
    ]
    assert not warnings


def test_thieu_don_va_bao_cao_thi_canh_bao():
    _, _, warnings = _plan([_DOCS[3]])
    assert any("Mẫu số 15 (dòng 1, bắt buộc)" in w for w in warnings)
    assert any("Mẫu số 15đ (dòng 2, bắt buộc)" in w for w in warnings)


def test_component_name_khong_trung_dong_khac():
    portal = {
        1: "Đơn đăng ký đất đai, tài sản gắn liền với đất",
        2: "Báo cáo kết quả rà soát hiện trạng sử dụng đất theo Mẫu số 15đ ban hành kèm theo Nghị định số "
           "151/2025/NĐ-CP",
    }
    for idx, row in P._ROWS.items():
        assert row["componentName"].lower() in portal[idx].lower()
        for other_idx, text in portal.items():
            if other_idx != idx:
                assert row["componentName"].lower() not in text.lower()
