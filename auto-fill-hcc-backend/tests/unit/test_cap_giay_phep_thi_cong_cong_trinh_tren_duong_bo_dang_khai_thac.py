"""Unit test "Cấp giấy phép thi công công trình trên đường bộ đang khai thác" (1.013061).

Theo file mapping 24/11/2026: form chỉ có Phần I người nộp (Form.io: chonDoiTuong, fullname, identityNumber … + panel
thongTinDoanhNghiep), bảng thành phần hồ sơ 5 dòng. Ảnh ánh xạ: Đơn → dòng 1, hồ sơ khoảng cách dải phân cách giữa →
dòng 2, báo cáo thẩm tra + tính toán chịu lực → dòng 3, thuyết minh / bản vẽ BPTC-BĐGT + hoàn trả → dòng 4, bản vẽ
thiết kế thi công → dòng 5; KHÔNG đính tệp gộp cả bộ vào một dòng. Dữ liệu trong test là bịa.
"""

import asyncio
import base64
import json

import fitz

from app.pipelines.cap_giay_phep_thi_cong_cong_trinh_tren_duong_bo_dang_khai_thac import attach
from app.pipelines.cap_giay_phep_thi_cong_cong_trinh_tren_duong_bo_dang_khai_thac.attach.dinh_kem_khong_tach import (
    planner as khong_tach,
)
from app.pipelines.cap_giay_phep_thi_cong_cong_trinh_tren_duong_bo_dang_khai_thac.attach.dinh_kem_tach import (
    planner as tach,
)
from app.pipelines.cap_giay_phep_thi_cong_cong_trinh_tren_duong_bo_dang_khai_thac.process import mapper, schema
from app.process.schemas import FileItem

_KEY = "cap-giay-phep-thi-cong-cong-trinh-tren-duong-bo-dang-khai-thac"

_SAMPLE = {
    "NguoiDeNghi_LoaiDoiTuong": "Cá nhân",
    "NguoiDeNghi_HoTen": "Trần Văn Bình",
    "NguoiDeNghi_NgaySinh": "05/03/1990",
    "NguoiDeNghi_SoDinhDanh": "001090001234",
    "NguoiDeNghi_NgayCap": "10/05/2021",
    "NguoiDeNghi_DienThoai": "0912 345 678",
    "NguoiDeNghi_Email": "binh.tv@example.com",
    "NguoiDeNghi_DiaChi": {"quocGia": "Việt Nam", "tinh": "Tỉnh Hưng Yên", "xa": "Xã Vũ Thư", "diaChi": "Thôn Đông"},
    "Don_KinhGui": "Khu Quản lý đường bộ I – Cục Đường bộ Việt Nam",
    "Don_NhanKetQua": "truc_tuyen",
}


def _fields(values: dict) -> list[dict]:
    return [{"name": k, "value": v} for k, v in values.items()]


def _ui(values: dict, options: dict | None = None) -> tuple[dict, list[str]]:
    out, warnings = mapper.enrich(_fields(values), options)
    return {f["name"]: f["value"] for f in out}, warnings


# ── Điền Phần I ──

def test_nguoi_dung_don_tu_nop_dien_du_phan_i_theo_mapping():
    ui, warnings = _ui(_SAMPLE)
    assert ui == {
        "data[fullname]": "Trần Văn Bình",
        "data[identityNumber]": "001090001234",
        "data[birthday]": "05/03/1990",
        "data[identityDate]": "10/05/2021",
        "data[identityAgency]": "Cục Cảnh sát quản lý hành chính về trật tự xã hội",  # mặc định theo ngày cấp
        "data[email]": "binh.tv@example.com",
        "data[phoneNumber]": "0912345678",                                            # bỏ dấu cách
        "data[province]": "Tỉnh Hưng Yên",
        "data[district]": "Xã Vũ Thư",
        "data[address]": "Thôn Đông",
        "data[nation]": "Việt Nam",
        "data[gender]": "Nam",                                                         # suy từ số định danh
        **_KHOI_CHI_TIET,
    }
    assert "data[chonDoiTuong]" not in ui  # Cá nhân là mặc định của form
    assert any("TRỰC TUYẾN" in w for w in warnings)


# Khối "Thông tin chi tiết" (ảnh DOM 24/11): container "Thông tin Tổ chức, cá nhân" + Tại + Ký tên = người đứng đơn.
_KHOI_CHI_TIET = {
    "data[container][organization]": "Trần Văn Bình",
    "data[container][province]": "Tỉnh Hưng Yên",
    "data[container][district]": "Xã Vũ Thư",
    "data[container][address]": "Thôn Đông",
    "data[container][phoneNumber]": "0912345678",
    "data[TinTTTe]": "Tỉnh Hưng Yên",
    "data[kyTen]": "Trần Văn Bình",
}


def test_khop_tai_khoan_va_nop_thay_khong_co_cccd():
    ctx = {"formContext": {"fullname": "TRẦN VĂN BÌNH", "identityNumber": "001090001234"}}
    ui, _ = _ui(_SAMPLE, ctx)
    assert ui["data[fullname]"] == "Trần Văn Bình" and ui["data[phoneNumber]"] == "0912345678"

    other = {"formContext": {"fullname": "LÊ THỊ HOA", "identityNumber": "001190005678"}}
    ui, warnings = _ui(_SAMPLE, other)
    # Không có CCCD của người nộp → Phần I chỉ ghi lại họ tên / số theo tài khoản; khối "Thông tin chi tiết" vẫn
    # điền đủ theo người đứng đơn (ca tài khoản cán bộ phường nộp thay trong ảnh 24/11).
    assert ui == {"data[fullname]": "LÊ THỊ HOA", "data[identityNumber]": "001190005678", "data[gender]": "Nữ",
                  **_KHOI_CHI_TIET}
    assert any("khác người đứng đơn" in w for w in warnings)
    assert any("Số điện thoại" in w for w in warnings)


_THEO_TO_KHAI = {"submitterMode": "owner_as_submitter",
                 "formContext": {"fullname": "LÊ THỊ HOA", "identityNumber": "001190005678"}}


def test_cai_dat_lay_nguoi_nop_theo_to_khai_bo_moc_tai_khoan():
    out, warnings = mapper.enrich(_fields(_SAMPLE), _THEO_TO_KHAI)
    by_name = {f["name"]: f for f in out}
    ui = {k: f["value"] for k, f in by_name.items()}
    # Người nộp = người đứng đơn dù tài khoản là người khác; ô cổng khoá theo VNeID được mở khoá.
    for key, value in (("data[fullname]", "Trần Văn Bình"), ("data[identityNumber]", "001090001234"),
                       ("data[birthday]", "05/03/1990")):
        assert ui[key] == value and by_name[key]["enableInput"] is True, key
    assert ui["data[phoneNumber]"] == "0912345678" and ui["data[district]"] == "Xã Vũ Thư"
    assert ui["data[gender]"] == "Nam"  # theo số định danh người đứng đơn, không theo tài khoản (Nữ)
    assert ui["data[container][district]"] == "Xã Vũ Thư"
    assert any("Lấy người nộp theo tờ khai" in w for w in warnings)
    assert not any("khác người đứng đơn" in w for w in warnings)


def test_theo_to_khai_khong_co_ngay_sinh_thi_xoa_ngay_sinh_tai_khoan():
    values = {k: v for k, v in _SAMPLE.items() if k != "NguoiDeNghi_NgaySinh"}
    by_name = {f["name"]: f for f in mapper.enrich(_fields(values), _THEO_TO_KHAI)[0]}
    assert by_name["data[birthday]"] == {"name": "data[birthday]", "comp": "dom-date", "value": "", "clear": True,
                                         "markEmpty": True}


def test_theo_to_khai_trung_tai_khoan_thi_khong_mo_khoa_khong_canh_bao():
    opts = {"submitterMode": "owner_as_submitter",
            "formContext": {"fullname": "TRẦN VĂN BÌNH", "identityNumber": "001090001234"}}
    out, warnings = mapper.enrich(_fields(_SAMPLE), opts)
    assert not any(f.get("enableInput") or f.get("clear") for f in out)
    assert not any("Lấy người nộp theo tờ khai" in w for w in warnings)


def test_runner_theo_to_khai_khong_neo_the_cccd_tai_khoan():
    from app.pipelines.cap_giay_phep_thi_cong_cong_trinh_tren_duong_bo_dang_khai_thac.process import runner

    ctx = asyncio.run(runner._context([{"text": "CĂN CƯỚC CÔNG DÂN LÊ THỊ HOA 001190005678"}], _THEO_TO_KHAI))
    assert 'result="theo_to_khai"' in ctx and "KHÔNG trả NguoiNop_*" in ctx


def test_khoi_chi_tiet_co_aliases_cho_o_chua_thay_key():
    out, _ = mapper.enrich(_fields(_SAMPLE))
    by_name = {f["name"]: f for f in out}
    assert "aliases" not in by_name["data[container][province]"]  # key đã thấy trên DOM
    assert by_name["data[container][district]"]["comp"] == "dom-select"
    assert "data[container][ward]" in by_name["data[container][district]"]["aliases"]
    assert "data[TinTTTe1]" in by_name["data[TinTTTe]"]["aliases"]


def test_nop_thay_co_cccd_nguoi_nop():
    values = {**_SAMPLE, "NguoiNop_HoTen": "Lê Thị Hoa", "NguoiNop_SoDinhDanh": "001190005678",
              "NguoiNop_NgayCap": "02/08/2024", "NguoiNop_DiaChi": "Số 5 phố Huế, Phường Hai Bà Trưng, Hà Nội"}
    ui, _ = _ui(values, {"formContext": {"fullname": "LÊ THỊ HOA", "identityNumber": "001190005678"}})
    assert ui["data[fullname]"] == "Lê Thị Hoa" and ui["data[identityDate]"] == "02/08/2024"
    assert ui["data[identityAgency]"] == "Bộ Công an"  # thẻ cấp từ 01/7/2024
    assert ui["data[address]"] == "Số 5 phố Huế" and "data[birthday]" not in ui
    assert "data[phoneNumber]" not in ui  # SĐT trên đơn là của người đứng đơn


def test_so_dien_thoai_bi_nham_lam_so_dinh_danh_thi_bo():
    ui, _ = _ui({**_SAMPLE, "NguoiDeNghi_SoDinhDanh": "0912345678"})
    assert "data[identityNumber]" not in ui and ui["data[fullname]"] == "Trần Văn Bình"


def test_to_chuc_dung_don_chon_to_chuc_truoc_roi_dien_panel_doanh_nghiep():
    values = {**_SAMPLE, "NguoiDeNghi_LoaiDoiTuong": "Tổ chức", "ToChuc_Ten": "Công ty TNHH Cấp nước An Bình",
              "ToChuc_MaSoThue": "0101 234 567", "ToChuc_DienThoai": "024.3456.7890",
              "ToChuc_DiaChi": {"tinh": "Thành phố Hà Nội", "xa": "Phường Cầu Giấy", "diaChi": "Số 1 Trần Thái Tông"}}
    out, warnings = mapper.enrich(_fields(values))
    assert out[0] == {"name": "data[chonDoiTuong]", "comp": "dom-select", "value": "Tổ chức"}
    ui = {f["name"]: f["value"] for f in out}
    assert ui["data[organization]"] == "Công ty TNHH Cấp nước An Bình" and ui["data[taxCode]"] == "0101234567"
    assert ui["data[organizationPhoneNumber]"] == "02434567890"
    assert ui["data[province1]"] == "Thành phố Hà Nội" and ui["data[address1]"] == "Số 1 Trần Thái Tông"
    assert ui["data[nation1]"] == "Việt Nam"
    assert any("Tổ chức" in w for w in warnings)


def test_schema_chi_phat_o_co_trong_mapping():
    assert set(schema.UI_COMP_BY_NAME) == {
        f"data[{k}]" for k in ("chonDoiTuong", "fullname", "birthday", "gender", "email", "identityNumber",
                               "identityDate", "identityAgency", "phoneNumber", "nation", "province", "district",
                               "address", "organization", "nation1", "address1", "taxCode", "province1",
                               "organizationPhoneNumber", "district1", "TinTTTe", "kyTen")} | {
        f"data[container][{k}]" for k in ("organization", "province", "district", "address", "phoneNumber")}
    # Ô ẩn / ô không có nguồn không phát.
    for key in ("tenHoSo", "AuthorityApplicantPhoneNumber", "note", "ownerFullname", "receivingKind"):
        assert f"data[{key}]" not in schema.UI_COMP_BY_NAME


# ── Đính kèm ──

# Bộ hồ sơ gộp 35 trang như tệp mẫu: (nội dung trang, loại LLM trả, mở thành phần mới).
_TRANG = [
    ("ĐƠN ĐỀ NGHỊ CẤP PHÉP THI CÔNG CÔNG TRÌNH TRÊN ĐƯỜNG BỘ ĐANG KHAI THÁC băng qua dải phân cách giữa", "don_de_nghi"),
    ("Căn cứ Quyết định phê duyệt; Báo cáo kết quả thẩm tra thiết kế số 18/BCTT; Ông Bình đề nghị", "don_de_nghi"),
    ("Đề nghị phương thức nhận kết quả như sau: NGƯỜI ĐỀ NGHỊ", "don_de_nghi"),
    ("CHỦ ĐẦU TƯ: ÔNG TRẦN VĂN BÌNH HỒ SƠ THÔNG TIN KHOẢNG CÁCH DẢI PHÂN CÁCH GIỮA", "khoang_cach_dpc"),
    ("CÔNG TY TƯ VẤN CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM THUYẾT MINH THÔNG TIN VỀ KHOẢNG CÁCH", "khoang_cach_dpc"),
    ("4 Đỉnh ống lồng 5. Đánh giá CHỦ ĐẦU TƯ", "khoang_cach_dpc"),
    ("CHỦ ĐẦU TƯ TÊN BẢN VẼ: MẶT BẰNG QUA DẢI PHÂN CÁCH Số hiệu BV DPC-01", "khoang_cach_dpc"),
    ("CHỦ ĐẦU TƯ TÊN BẢN VẼ: MẶT CẮT QUA DẢI PHÂN CÁCH Số hiệu BV DPC-02", "khoang_cach_dpc"),
    ("CÔNG TY KIỂM ĐỊNH CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM BÁO CÁO KẾT QUẢ THẨM TRA THIẾT KẾ VÀ KẾT QUẢ TÍNH TOÁN "
     "KHẢ NĂNG CHỊU LỰC", "tham_tra_chiu_luc"),
    ("Chủ đầu tư CCCD số 001090001234 4.1 Sự phù hợp", "tham_tra_chiu_luc"),
    ("4.4 Kết cấu giá đỡ 4.5. Biện pháp tổ chức thi công, bảo đảm giao thông 4.6 Hoàn trả", "tham_tra_chiu_luc"),
    ("Tổ hợp Cường độ I 5.4 Kiểm toán sức kháng 6. KẾT LUẬN", "tham_tra_chiu_luc"),
    ("Nơi nhận CHỦ TRÌ THẨM TRA", "tham_tra_chiu_luc"),
    ("CHỦ ĐẦU TƯ: ÔNG TRẦN VĂN BÌNH THUYẾT MINH VÀ BẢN VẼ BIỆN PHÁP TỔ CHỨC THI CÔNG, BIỆN PHÁP BẢO ĐẢM GIAO THÔNG",
     "bptc_bdgt_hoan_tra"),
    ("DANH MỤC BẢN VẼ STT Số hiệu Tên bản vẽ HT-01 Thiết kế hoàn trả hố khoan", "bptc_bdgt_hoan_tra"),
    ("4. Biện pháp kỹ thuật thi công chủ yếu 4.1 Khoan ngầm", "bptc_bdgt_hoan_tra"),
    ("2. Giai đoạn 1 3. Giai đoạn 2 PHẦN III", "bptc_bdgt_hoan_tra"),
    ("PHẦN IV CHỦ ĐẦU TƯ ĐƠN VỊ THI CÔNG", "bptc_bdgt_hoan_tra"),
    ("HẠNG MỤC: BIỆN PHÁP TCTC Số hiệu BV HT-01", "bptc_bdgt_hoan_tra"),
    ("HẠNG MỤC: BIỆN PHÁP TCTC Số hiệu BV HT-02", "bptc_bdgt_hoan_tra"),
    ("SƠ ĐỒ TCTC GIAI ĐOẠN 1 Số hiệu BV TCGT-01", "bptc_bdgt_hoan_tra"),
    ("SƠ ĐỒ TCTC GIAI ĐOẠN 2 Số hiệu BV TCGT-02", "bptc_bdgt_hoan_tra"),
    ("CHI TIẾT BIỂN BÁO Số hiệu BV TCGT-03", "bptc_bdgt_hoan_tra"),
    ("CHỦ ĐẦU TƯ: ÔNG TRẦN VĂN BÌNH HỒ SƠ THIẾT KẾ BẢN VẼ THI CÔNG", "thiet_ke_thi_cong"),
    ("DANH MỤC HỒ SƠ BẢN VẼ THIẾT KẾ THI CÔNG TC-01 Bình đồ", "thiet_ke_thi_cong"),
    ("Thông tư 41 3. QUY CHUẨN 4. HIỆN TRẠNG", "thiet_ke_thi_cong"),
    ("5.2. Khoảng cách của công trình so với công trình đường bộ dải phân cách giữa 1,00 mỗi bên", "thiet_ke_thi_cong"),
    ("2 Ống lồng HDPE 7. YÊU CẦU KỸ THUẬT", "thiet_ke_thi_cong"),
    ("BÌNH ĐỒ VỊ TRÍ Số hiệu BV TC-01", "thiet_ke_thi_cong"),
    ("MẶT BẰNG Số hiệu BV TC-02", "thiet_ke_thi_cong"),
    ("MẶT CẮT DỌC Số hiệu BV TC-03", "thiet_ke_thi_cong"),
    ("MẶT CẮT NGANG Số hiệu BV TC-04", "thiet_ke_thi_cong"),
    ("LẮP ĐẶT ỐNG TRÊN CẦU Số hiệu BV TC-05", "thiet_ke_thi_cong"),
    ("CHI TIẾT GIÁ ĐỠ Số hiệu BV TC-06", "thiet_ke_thi_cong"),
    ("THỐNG KÊ BỘ PHẬN PHẢI ĐÀO hoàn trả theo bản vẽ HT-01 Số hiệu BV TC-07", "thiet_ke_thi_cong"),
]
_BO = "\n".join(f"───── Trang {i}/{len(_TRANG)} ─────\n{body}" for i, (body, _) in enumerate(_TRANG, 1))
# Khoảng trang (1-based) của từng thành phần → dòng.
_DOAN = [(1, 3, "don_de_nghi", 1), (4, 8, "khoang_cach_dpc", 2), (9, 13, "tham_tra_chiu_luc", 3),
         (14, 23, "bptc_bdgt_hoan_tra", 4), (24, 35, "thiet_ke_thi_cong", 5)]


def _pdf(pages: int) -> str:
    with fitz.open() as doc:
        for _ in range(pages):
            doc.new_page()
        return "data:application/pdf;base64," + base64.b64encode(doc.tobytes()).decode()


def _bo_ho_so() -> list[FileItem]:
    return [FileItem(name="00_toan_bo_ho_so.pdf", type="application/pdf", dataUrl=_pdf(len(_TRANG)), role="")]


def _patch_ocr(monkeypatch, texts: dict[str, str]):
    async def fake_ocr(files):
        return [{"name": f["name"], "text": texts[f["name"]]} for f in files]

    monkeypatch.setattr(tach.ocr, "ocr_per_file", fake_ocr)


def _patch_llm(monkeypatch, reply, calls: list | None = None):
    async def fake_chat(messages, *_a, **_k):
        if calls is not None:
            calls.append(messages[0]["content"])
        if isinstance(reply, Exception):
            raise reply
        return json.dumps(reply)

    monkeypatch.setattr(tach.client, "chat", fake_chat)


def test_tach_bo_ho_so_gop_moi_thanh_phan_ve_dung_dong_khong_sot_trang(monkeypatch):
    _patch_ocr(monkeypatch, {"00_toan_bo_ho_so.pdf": _BO})
    calls: list = []
    _patch_llm(monkeypatch, {"documents": [{"fileIndex": 0, "pageFrom": a, "pageTo": b, "type": t, "documentName": ""}
                                           for a, b, t, _ in _DOAN]}, calls)
    res = asyncio.run(attach.plan(_bo_ho_so(), {"splitDocuments": True}))
    got = [(a["componentIndex"], a["sourceSegments"][0]["pageIndexes"]) for a in res["attachments"]]
    assert got == [(row, list(range(a - 1, b))) for a, b, _, row in _DOAN]
    assert sorted(p for _, ps in got for p in ps) == list(range(len(_TRANG)))
    assert all(a["target"] == "attp-row" and a["loaiBan"] == "Bản chính" for a in res["attachments"])
    assert res["attachments"][4]["componentName"] == "Bản vẽ thiết kế thi công có các thông tin về"
    assert "untickRows" not in res["attachments"][0]  # có đủ dòng 2, 3
    assert not any("Chưa có" in e for e in res["errors"])
    assert calls == [tach.prompt.SYSTEM_PROMPT]  # MỘT lượt LLM cho cả bộ


def test_tach_llm_tra_other_thi_rule_tieu_de_va_khung_ten_ban_ve_van_ra_dung_dong(monkeypatch):
    _patch_ocr(monkeypatch, {"00_toan_bo_ho_so.pdf": _BO})
    _patch_llm(monkeypatch, {"documents": [{"fileIndex": 0, "pageFrom": i, "pageTo": i, "type": "other"}
                                           for i in range(1, len(_TRANG) + 1)]})
    res = asyncio.run(attach.plan(_bo_ho_so(), {"splitDocuments": True}))
    got = [(a["componentIndex"], a["sourceSegments"][0]["pageIndexes"]) for a in res["attachments"]]
    assert got == [(row, list(range(a - 1, b))) for a, b, _, row in _DOAN]


def test_rule_khong_nhan_nham_cum_nhac_toi_trong_than_van_ban():
    assert tach._rule_type(_TRANG[1][0]) == "other"   # Đơn trang 2 nhắc "Báo cáo kết quả thẩm tra"
    assert tach._rule_type(_TRANG[10][0]) == "other"  # báo cáo thẩm tra mục "Biện pháp tổ chức thi công…"
    assert tach._rule_type(_TRANG[26][0]) == "other"  # thuyết minh thiết kế có bảng khoảng cách DPC
    assert tach._rule_type(_TRANG[34][0]) == "thiet_ke_thi_cong"  # TC-07 ghi chú "xem HT-01"
    assert tach._rule_type(_TRANG[9][0]) == "other"   # "CCCD số" trong bảng không phải thẻ


def test_tach_loi_thi_dinh_nguyen_tep_vao_dong_don(monkeypatch):
    _patch_ocr(monkeypatch, {"00_toan_bo_ho_so.pdf": _BO})
    _patch_llm(monkeypatch, RuntimeError("LLM hỏng"))
    res = asyncio.run(attach.plan(_bo_ho_so(), {"splitDocuments": True}))
    assert [(a["componentIndex"], "sourceSegments" in a) for a in res["attachments"]] == [(1, False)]
    assert res["errors"][0].startswith("attachment_agent (tách)")
    # Tệp gộp vào dòng Đơn → dòng 2 / 3 không có tệp → bỏ tick để cổng cho chuyển bước.
    assert len(res["attachments"][0]["untickRows"]) == 2


def test_tat_tach_tep_gop_dinh_mot_lan_va_canh_bao_bat_tach(monkeypatch):
    _patch_ocr(monkeypatch, {"00_toan_bo_ho_so.pdf": _BO})
    _patch_llm(monkeypatch, {"documents": [{"index": 0, "docTypes": [t for _, _, t, _ in _DOAN]}]})
    for options in ({}, {"splitDocuments": False}, {"splitDocuments": "true"}):
        res = asyncio.run(attach.plan(_bo_ho_so(), options))
        assert [(a["componentIndex"], "sourceSegments" in a) for a in res["attachments"]] == [(1, False)]
        assert any("Tách giấy tờ" in e for e in res["errors"])
        assert not any("Chưa có" in e for e in res["errors"])


_TEP_RIENG = {
    "01_Don.pdf": "ĐƠN ĐỀ NGHỊ CẤP PHÉP THI CÔNG CÔNG TRÌNH TRÊN ĐƯỜNG BỘ ĐANG KHAI THÁC",
    "02_Khoang_cach.pdf": "HỒ SƠ THÔNG TIN KHOẢNG CÁCH DẢI PHÂN CÁCH GIỮA",
    "03_Tham_tra.pdf": "BÁO CÁO KẾT QUẢ THẨM TRA THIẾT KẾ VÀ KẾT QUẢ TÍNH TOÁN KHẢ NĂNG CHỊU LỰC",
    "04_BPTC.pdf": "THUYẾT MINH VÀ BẢN VẼ BIỆN PHÁP TỔ CHỨC THI CÔNG, BIỆN PHÁP BẢO ĐẢM GIAO THÔNG",
    "05_TKTC.pdf": "HỒ SƠ THIẾT KẾ BẢN VẼ THI CÔNG",
}


def _tep_rieng() -> list[FileItem]:
    files = [FileItem(name=n, type="application/pdf", dataUrl=_pdf(2), role="") for n in _TEP_RIENG]
    files.append(FileItem(name="01_Don.docx", role="", dataUrl="data:application/octet-stream;base64,AA==",
                          type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
    return files


def test_nam_tep_rieng_nhu_ho_so_mau_ca_hai_che_do(monkeypatch):
    texts = {n: f"───── Trang 1/2 ─────\n{t}\n───── Trang 2/2 ─────\ntrang tiếp" for n, t in _TEP_RIENG.items()}
    _patch_ocr(monkeypatch, texts)
    _patch_llm(monkeypatch, {"documents": []})  # LLM không trả gì → rule theo tiêu đề
    for options in ({}, {"splitDocuments": True}):
        res = asyncio.run(attach.plan(_tep_rieng(), options))
        got = [(a["fileIndex"], a["componentIndex"], "sourceSegments" in a) for a in res["attachments"]]
        # Bản Word của đơn (không OCR được) đính chung dòng 1, sau bản PDF.
        assert got == [(0, 1, False), (5, 1, False), (1, 2, False), (2, 3, False), (3, 4, False), (4, 5, False)], options
        assert "untickRows" not in res["attachments"][0]
        assert not any("chưa rõ loại" in e for e in res["errors"])


def test_khong_co_dong_2_3_thi_bo_tick_va_cccd_di_chung_dong_don():
    raw = [{"name": n, "type": "application/pdf"} for n in ("don.pdf", "bptc.pdf", "tktc.pdf", "cccd.pdf")]
    texts = {0: "ĐƠN ĐỀ NGHỊ CẤP PHÉP THI CÔNG", 1: "THUYẾT MINH VÀ BẢN VẼ BIỆN PHÁP TỔ CHỨC THI CÔNG",
             2: "HỒ SƠ THIẾT KẾ BẢN VẼ THI CÔNG", 3: "CĂN CƯỚC CÔNG DÂN IDVNM0900012345"}
    attachments, _, warnings = khong_tach.build_plan_items(raw, texts, {})
    assert [(a["fileIndex"], a["componentIndex"]) for a in attachments] == [(0, 1), (3, 1), (1, 4), (2, 5)]
    assert attachments[0]["untickRows"] == [tach._ROWS[2]["componentName"], tach._ROWS[3]["componentName"]]
    assert any("đã bỏ tick dòng 2" in w for w in warnings) and any("CCCD" in w for w in warnings)
    assert not any("Chưa có" in w for w in warnings)


def test_bang_dong_khop_5_thanh_phan_cua_mapping():
    rows = tach._ROWS
    assert sorted(rows) == [1, 2, 3, 4, 5]
    assert {r["loaiBan"] for r in rows.values()} == {"Bản chính"}
    # Dòng 2, 3 đều chứa "ngoài Bản vẽ thiết kế thi công" → componentName dòng 5 không được là cụm chung đó.
    names = [r["componentName"] for r in rows.values()]
    assert all(a == b or a not in b for a in names for b in names)  # không dòng nào là chuỗi con của dòng khác
    prompt = tach.prompt.SYSTEM_PROMPT
    assert all(t in prompt for t in ("don_de_nghi", "khoang_cach_dpc", "tham_tra_chiu_luc", "bptc_bdgt_hoan_tra",
                                     "thiet_ke_thi_cong"))
    assert "khoang_cach_dpc" in khong_tach.SYSTEM_PROMPT


# ── Registry lõi + trợ lý ──

def test_registry_loi_va_link_ke_khai_cung_key():
    from app.procedures.ke_khai_links import KE_KHAI_LINKS
    from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

    proc = get_procedure(_KEY)
    assert proc["supportsSplitDocuments"] is True and proc["collectFormContext"] is True
    assert proc["hasAttachmentStep"] is True
    assert get_pipeline(_KEY) is not None and get_attach_pipeline(_KEY) is not None
    link = next(link for link in KE_KHAI_LINKS if link["key"] == _KEY)
    assert link["code"] == "1.013061" and proc["label"] == link["label"]


def test_tro_ly_toan_quoc_luong_bo_xay_dung():
    from app.channels.handfree.chat.field_review import registry
    from app.channels.handfree.procedure_registry import _HOAN_THIEN_THEO_TINH, get_procedure, procedure_code

    tl = get_procedure(_KEY)
    assert procedure_code(tl) == "1.013061"
    assert tl["flowProfile"] == "xay-dung" and tl["bxdFlow"]["resultGroups"][0]["name"] == "receivingKind"
    assert tl["supportsSplitDocuments"] is True and "provinceOnly" not in tl
    assert "agencyProvinceOnly" not in tl and "agencySoFirst" not in tl  # ke_khai không selectSo → Tỉnh + Xã
    assert registry.get(_KEY)["noAsk"] == ("tenHoSo", "AuthorityApplicantPhoneNumber")
    assert len(_HOAN_THIEN_THEO_TINH[_KEY]) == len(_HOAN_THIEN_THEO_TINH["chap-thuan-dau-noi-tam"])  # _TAT_CA
