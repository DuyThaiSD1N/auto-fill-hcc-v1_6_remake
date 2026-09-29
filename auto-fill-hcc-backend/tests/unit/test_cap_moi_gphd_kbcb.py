"""Cấp mới giấy phép hoạt động cơ sở KBCB (1.012278) — đính kèm bảng 11 dòng + mapper form."""

import asyncio
import re
import unicodedata

from app.pipelines.cap_moi_giay_phep_hoat_dong_kham_benh_chua_benh.attach import planner
from app.pipelines.cap_moi_giay_phep_hoat_dong_kham_benh_chua_benh.process import mapper, runner

_DON_MAU_02 = "Đơn theo Mẫu 02 Phụ lục II ban hành kèm theo Nghị định số 96/2023/NĐ-CP"
_MAU_11 = (
    "Bản sao hợp lệ giấy phép hành nghề và giấy xác nhận quá trình hành nghề theo Mẫu 11 Phụ lục I ban hành kèm "
    "theo Nghị định số 96/2023/NĐ-CP {who} (không áp dụng đối với trường hợp các giấy tờ này đã được kết nối, "
    "chia sẻ trên Hệ thống thông tin về quản lý hoạt động khám bệnh, chữa bệnh hoặc cơ sở dữ liệu quốc gia về "
    "y tế)"
)
# Tên 11 dòng NGUYÊN VĂN trên cổng (sheet mapping), theo đúng thứ tự.
_PORTAL_ROWS = [
    _DON_MAU_02,
    "Bản sao hợp lệ quyết định thành lập hoặc văn bản có tên của cơ sở khám bệnh, chữa bệnh của cơ quan nhà "
    "nước có thẩm quyền đối với cơ sở khám bệnh, chữa bệnh của nhà nước hoặc giấy chứng nhận đăng ký doanh "
    "nghiệp đối với cơ sở khám bệnh, chữa bệnh tư nhân hoặc giấy chứng nhận đầu tư đối với cơ sở khám bệnh, "
    "chữa bệnh có vốn đầu tư nước ngoài",
    _MAU_11.format(who="của người chịu trách nhiệm chuyên môn kỹ thuật của cơ sở khám bệnh, chữa bệnh"),
    _MAU_11.format(who="của người phụ trách bộ phận chuyên môn của cơ sở khám bệnh, chữa bệnh"),
    "Bản kê khai cơ sở vật chất, danh mục thiết bị y tế, danh sách nhân sự đáp ứng điều kiện cấp giấy phép "
    "hoạt động tương ứng với từng hình thức tổ chức theo Mẫu 08 Phụ lục II ban hành kèm theo Nghị định số "
    "96/2023/NĐ-CP và các giấy tờ chứng minh, xác nhận các kê khai đó",
    "Danh sách ghi rõ họ tên, số giấy phép hành nghề của từng người hành nghề đăng ký hành nghề tại cơ sở đó "
    "theo Mẫu 01 Phụ lục II ban hành kèm theo Nghị định số 96/2023/NĐ-CP",
    "Văn bản do cấp có thẩm quyền phê duyệt quy định về chức năng nhiệm vụ, cơ cấu tổ chức của bệnh viện của "
    "nhà nước hoặc điều lệ tổ chức và hoạt động đối với bệnh viện tư nhân theo Mẫu 03 Phụ lục II ban hành kèm "
    "theo Nghị định số 96/2023/NĐ-CP",
    "Danh mục chuyên môn kỹ thuật của cơ sở khám bệnh, chữa bệnh đề xuất trên cơ sở danh mục chuyên môn kỹ "
    "thuật do Bộ trưởng Bộ Y tế ban hành",
    "Trường hợp đề nghị cấp lần đầu giấy phép hoạt động cơ sở khám bệnh, chữa bệnh nhân đạo hoặc cơ sở khám "
    "bệnh, chữa bệnh không vì mục đích lợi nhuận thì phải có tài liệu chứng minh nguồn tài chính bảo đảm cho "
    "hoạt động khám bệnh, chữa bệnh nhân đạo hoặc hoạt động khám bệnh, chữa bệnh không vì mục đích lợi nhuận",
    _DON_MAU_02,
    "Tài liệu chứng minh nguồn tài chính cho hoạt động khám bệnh, chữa bệnh nhân đạo",
]

# Bộ hồ sơ phòng khám tư nhân mẫu (tên tệp bịa) — GCN.pdf là bản scan gộp CME + bản kê khai + danh mục KT.
_FILES = ["don.pdf", "gpkd.pdf", "cchn.pdf", "xn_hanh_nghe.pdf", "GCN.pdf", "bang_ths.pdf", "cc_noi_soi.pdf",
          "qd.pdf", "ds_hanh_nghe.pdf"]
_TYPES = {
    0: ["don_de_nghi"],
    1: ["giay_dang_ky"],
    2: ["gphn"],
    3: ["xac_nhan_hanh_nghe"],
    4: ["chung_chi_dao_tao", "ban_ke_khai", "danh_muc_ky_thuat"],
    5: ["van_bang"],
    6: ["chung_chi_dao_tao"],
    7: ["giay_to_chung_minh"],
    8: ["danh_sach_hanh_nghe"],
}


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _fold(value):
    text = str(value or "").replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text).strip().lower()


def _engine_rows(items):
    """Mô phỏng attachFilesByAttpRow: gom theo componentName, tìm dòng bằng (tên, componentIndex)."""
    groups = {}
    for item in items:
        groups.setdefault(_fold(item["componentName"]), []).append(item)
    placed = {}
    for group in groups.values():
        first = group[0]
        want = _fold(first["componentName"])
        matches = lambda text: want in _fold(text) or _fold(text) in want  # noqa: E731
        idx = first.get("componentIndex")
        if idx and matches(_PORTAL_ROWS[idx - 1]):
            row = idx
        else:
            row = next(i for i, text in enumerate(_PORTAL_ROWS, start=1) if matches(text))
        placed.setdefault(row, []).extend(it["fileName"] for it in group)
    return placed


def test_ho_so_mau_dinh_dung_anh_xa_11_dong():
    items, warnings, _ = planner.build_plan_items(_files(_FILES), _TYPES)

    assert _engine_rows(items) == {
        1: ["don.pdf"],
        2: ["gpkd.pdf"],
        3: ["cchn.pdf", "xn_hanh_nghe.pdf"],
        4: ["cchn.pdf", "xn_hanh_nghe.pdf"],
        5: ["GCN.pdf", "bang_ths.pdf", "cc_noi_soi.pdf", "qd.pdf"],
        6: ["ds_hanh_nghe.pdf"],
        8: ["GCN.pdf"],
    }, "dòng 7/9/10/11 (bệnh viện, nhân đạo) để trống"
    assert not warnings
    assert all(i["target"] == "attp-row" for i in items)
    gop = [i for i in items if i["fileName"] == "GCN.pdf"]
    assert [i["detectedType"] for i in gop] == ["ban_ke_khai", "danh_muc_ky_thuat"], "dòng 5 đặt tên bản kê khai"


def test_moi_dong_mot_component_name_rieng_va_khop_dung_dong_cua_no():
    """Engine gom theo componentName: hai dòng trùng tên mà dùng chung componentName sẽ dồn về một dòng."""
    names = [_fold(r["componentName"]) for r in planner._ROWS]
    assert len(set(names)) == len(names)
    assert [r["componentIndex"] for r in planner._ROWS] == list(range(1, 12))
    for row in planner._ROWS:
        assert _fold(row["componentName"]) in _fold(_PORTAL_ROWS[row["componentIndex"] - 1])


def test_loai_ban_theo_anh_xa():
    items, _, _ = planner.build_plan_items(_files(_FILES), _TYPES)
    by_row = {i["componentIndex"]: i["loaiBan"] for i in items}
    assert {by_row[r] for r in (2, 3, 4)} == {"Bản sao"}
    assert {by_row[r] for r in (1, 5, 6, 8)} == {"Bản chính"}


def test_tep_gop_nhieu_loai_chi_dinh_mot_lan_moi_dong():
    items, _, classified = planner.build_plan_items(
        _files(["gop.pdf"]), {0: ["van_bang", "chung_chi_dao_tao", "danh_muc_ky_thuat"]}
    )
    assert _engine_rows(items) == {5: ["gop.pdf"], 8: ["gop.pdf"]}
    assert classified[0]["docType"] == "van_bang"
    dmkt = next(i for i in items if i["componentIndex"] == 8)
    assert dmkt["documentName"] == planner._DOC_NAMES["danh_muc_ky_thuat"], "tên theo loại của dòng"


def test_hai_chung_chi_cung_dong_khong_trung_ten():
    items, _, _ = planner.build_plan_items(
        _files(["don.pdf", "cc_mot.pdf", "cc_hai.pdf"]),
        {0: ["don_de_nghi"], 1: ["chung_chi_dao_tao"], 2: ["chung_chi_dao_tao"]},
    )
    cc = [i["documentName"] for i in items if i["detectedType"] == "chung_chi_dao_tao"]
    assert len(cc) == 2 and cc[0] != cc[1]
    assert "cc_mot" in cc[0]
    don = next(i for i in items if i["detectedType"] == "don_de_nghi")
    assert don["documentName"] == planner._DOC_NAMES["don_de_nghi"], "chỉ một tệp thì giữ tên chuẩn"


def test_co_so_nhan_dao_dinh_them_don_vao_dong_10():
    items, _, _ = planner.build_plan_items(
        _files(["don.pdf", "tai_chinh.pdf"]), {0: ["don_de_nghi"], 1: ["tai_chinh_nhan_dao"]}
    )
    assert _engine_rows(items) == {1: ["don.pdf"], 10: ["don.pdf"], 9: ["tai_chinh.pdf"], 11: ["tai_chinh.pdf"]}


def test_dieu_le_benh_vien_vao_dong_7():
    items, _, _ = planner.build_plan_items(_files(["dieu_le.pdf"]), {0: ["dieu_le_benh_vien"]})
    assert _engine_rows(items) == {7: ["dieu_le.pdf"]}


def test_tep_la_va_llm_loi_don_vao_dong_5_giu_ten_goc():
    items, warnings, classified = planner.build_plan_items(_files(["don.pdf", "la.pdf"]), {0: ["don_de_nghi"]})

    la = [i for i in items if i["fileName"] == "la.pdf"]
    assert len(la) == 1
    assert la[0]["componentIndex"] == 5 and la[0]["documentName"] == "la.pdf"
    assert classified[1]["source"] == "fallback"
    assert any("la.pdf" in w for w in warnings)


def test_cccd_bo_qua():
    items, _, classified = planner.build_plan_items(_files(["cccd.pdf"]), {0: ["cccd"]})
    assert items == [] and classified[0]["skipped"] is True


def test_normalize_doc_types():
    assert planner._normalize_doc_types("chung chi dao tao") == ["chung_chi_dao_tao"]
    assert planner._normalize_doc_types(["GPHN", "gphn"]) == ["gphn"]
    assert planner._normalize_doc_types(["chung_chi"]) == ["other"]
    assert planner._normalize_doc_types(["other", "ban_ke_khai", "cccd"]) == ["ban_ke_khai"]
    assert planner._normalize_doc_types([]) == ["other"]


def test_plan_moi_tep_mot_luot_goi(monkeypatch):
    calls = []

    async def _chat(messages, **_kw):
        calls.append(messages[-1]["content"])
        return '{"documents":[{"index":0,"docTypes":["gphn"]}]}'

    async def _ocr(files):
        return [{"name": f["name"], "text": "CHỨNG CHỈ HÀNH NGHỀ"} for f in files]

    monkeypatch.setattr(planner.client, "chat", _chat)
    from app.services import ocr
    monkeypatch.setattr(ocr, "ocr_per_file", _ocr)

    class _F:
        def __init__(self, name):
            self.name, self.type, self.dataUrl = name, "application/pdf", "data:application/pdf;base64,AA=="

    res = asyncio.run(planner.plan([_F("a.pdf"), _F("b.pdf")]))
    assert len(calls) == 2
    assert len(res["attachments"]) == 4, "2 tệp CCHN × 2 dòng Mẫu 11"


def test_plan_chap_nhan_docType_don_le(monkeypatch):
    async def _chat(messages, **_kw):
        return '{"documents":[{"index":0,"docType":"danh_sach_hanh_nghe"}]}'

    async def _ocr(files):
        return [{"name": f["name"], "text": "DANH SÁCH ĐĂNG KÝ HÀNH NGHỀ"} for f in files]

    monkeypatch.setattr(planner.client, "chat", _chat)
    from app.services import ocr
    monkeypatch.setattr(ocr, "ocr_per_file", _ocr)

    class _F:
        name, type, dataUrl = "ds.pdf", "application/pdf", "data:application/pdf;base64,AA=="

    res = asyncio.run(planner.plan([_F()]))
    assert [a["componentIndex"] for a in res["attachments"]] == [6]


# ------------------------------- mapper -------------------------------

_FACTS = {
    "ChuHoSo_HoTen": "TRẦN VĂN MINH",
    "ChuHoSo_NgaySinh": "3.4.1975",
    "ChuHoSo_GioiTinh": "Nam",
    "ChuHoSo_SoDinhDanh": "001075012345",
    "ChuHoSo_NgayCap": "10/01/2025",
    "ChuHoSo_NoiCap": "BỘ CÔNG AN",
    "ChuHoSo_ThuongTru": {"tinh": "TP Đà Nẵng", "xa": "phường An Hải", "diaChi": "Số 12 đường Lê Lợi"},
    "ChuHoSo_Email": "TranVanMinh @example.com",
    "HoSo_TruongHopDeNghi": "Cấp mới giấy phép hoạt động cơ sở khám bệnh chữa bệnh",
    "CoSo_Ten": "PHÒNG KHÁM NỘI TỔNG HỢP",
    "CoSo_DiaChi": "Số 5 đường Hùng Vương, phường Hải Châu, Thành phố Đà Nẵng",
    "CoSo_DienThoai": "0905 123 456",
    "CoSo_HinhThucToChuc": "Phòng khám chuyên khoa Nội",
    "CoSo_ThoiGianLamViec": "Thứ 2 đến thứ 6: sáng 7 giờ–11 giờ; Thứ 7, Chủ nhật: nghỉ",
}


def _enrich(facts, ctx=None):
    fields = [{"name": k, "value": v} for k, v in facts.items()]
    out, warnings = mapper.enrich(fields, {"formContext": ctx or {}})
    return {f["name"]: f["value"] for f in out}, warnings


def test_tu_nop_dien_phan_1_va_tich_chu_ho_so():
    got, warnings = _enrich(_FACTS, {"applicantFullname": "TRẦN VĂN MINH", "applicantIdentityNumber": "001075012345"})

    assert "data[fullname]" not in got and "data[identityNumber]" not in got, "ô cổng khoá sẵn"
    assert got["data[isOwnerDossierCheck]"] is True
    assert got["data[chonDoiTuong]"] == "Cá nhân"
    assert got["data[birthday]"] == "03/04/1975"
    assert got["data[gender]"] == "Nam"
    assert got["data[province]"] == "Thành phố Đà Nẵng"
    assert got["data[district]"] == "Phường An Hải"
    assert got["data[address]"] == "Số 12 đường Lê Lợi"
    assert got["data[phoneNumber]"] == "0905123456", "không có SĐT cá nhân → lấy SĐT trên Đơn"
    assert got["data[email]"] == "tranvanminh@example.com"
    assert got["data[idIssuePlace]"] == "Bộ Công an"
    assert got["data[ghiChu]"] == (
        "Cấp mới giấy phép hoạt động cơ sở khám bệnh chữa bệnh – PHÒNG KHÁM NỘI TỔNG HỢP – Hình thức tổ chức: "
        "Phòng khám chuyên khoa Nội – Địa chỉ: Số 5 đường Hùng Vương, phường Hải Châu, Thành phố Đà Nẵng – "
        "ĐT: 0905123456 – Thời gian làm việc: Thứ 2 đến thứ 6: sáng 7 giờ–11 giờ; Thứ 7, Chủ nhật: nghỉ"
    )
    assert not any(k.startswith("data[owner") for k in got)
    assert not warnings


def test_nop_thay_bo_tich_va_dien_phan_2():
    got, _ = _enrich(_FACTS, {"applicantFullname": "LÊ THỊ HOA", "applicantIdentityNumber": "002190054321"})

    assert got["data[isOwnerDossierCheck]"] is False
    assert got["data[ownerFullname]"] == "TRẦN VĂN MINH"
    assert got["data[ownerIdentityNumber]"] == "001075012345"
    assert got["data[ownerProvince]"] == "Thành phố Đà Nẵng"
    assert got["data[ownerNation]"] == "Việt Nam"
    assert "data[ghiChu]" in got
    assert "data[birthday]" not in got, "Phần I nộp thay do cổng đổ từ tài khoản"


def test_ghi_chu_bo_hinh_thuc_trung_ten_va_mac_dinh_truong_hop():
    facts = {"CoSo_Ten": "Phòng khám chuyên khoa Nội", "CoSo_HinhThucToChuc": "Phòng khám chuyên khoa Nội"}
    got, _ = _enrich(facts)
    assert got["data[ghiChu]"] == (
        "Cấp mới giấy phép hoạt động cơ sở khám bệnh, chữa bệnh – Phòng khám chuyên khoa Nội"
    )


def test_dia_chi_chuoi_co_viet_nam():
    got, _ = _enrich({
        "ChuHoSo_HoTen": "TRẦN VĂN MINH",
        "ChuHoSo_ThuongTru": "Số 12 đường Lê Lợi, Phường An Hải, Thành phố Đà Nẵng, Việt Nam",
    })
    assert got["data[province]"] == "Thành phố Đà Nẵng"
    assert got["data[district]"] == "Phường An Hải"
    assert got["data[address]"] == "Số 12 đường Lê Lợi"


def test_cmnd_9_so_bi_canh_bao():
    _, warnings = _enrich({**_FACTS, "ChuHoSo_SoDinhDanh": "201234567"})
    assert any("12 chữ số" in w for w in warnings)


def test_ngu_canh_nguoi_nop():
    docs = [{"text": "GIẤY CHỨNG NHẬN ĐĂNG KÝ HỘ KINH DOANH ... Họ và tên: TRẦN VĂN MINH"}]
    text = asyncio.run(runner._submitter_context(docs, {"formContext": {"applicantFullname": "LÊ THỊ HOA"}}))
    assert 'result="khong_co_giay_to"' in text
    text = asyncio.run(runner._submitter_context(docs, {"formContext": {"applicantFullname": "TRẦN VĂN MINH"}}))
    assert 'result="co_giay_to"' in text
