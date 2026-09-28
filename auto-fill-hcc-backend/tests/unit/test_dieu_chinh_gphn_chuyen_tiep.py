"""Điều chỉnh GPHN giai đoạn chuyển tiếp (1.012292) — đính kèm bảng 10 dòng trùng tên + mapper form."""

import asyncio
import re
import unicodedata

from app.pipelines.dieu_chinh_giay_phep_hanh_nghe_chuyen_tiep.attach import planner
from app.pipelines.dieu_chinh_giay_phep_hanh_nghe_chuyen_tiep.process import mapper, runner

# Tên 10 dòng NGUYÊN VĂN trên cổng (sheet mapping), theo đúng thứ tự.
_PORTAL_ROWS = [
    "Đơn theo Mẫu 08 Phụ lục I ban hành kèm theo Nghị định số 96/2023/NĐ-CP;",
    "a) Đơn theo Mẫu 08 Phụ lục I ban hành kèm theo Nghị định số 96/2023/NĐ-CP.",
    "b) Bản sao hợp lệ giấy phép hành nghề đã cấp (không áp dụng đối với trường hợp giấy phép hành nghề đã "
    "được kết nối, chia sẻ trên Hệ thống thông tin về quản lý hoạt động khám bệnh, chữa bệnh hoặc cơ sở dữ "
    "liệu quốc gia về y tế) hoặc chứng chỉ hành nghề  được cấp trước ngày 01 tháng 01 năm 2024.",
    ") Bản sao hợp lệ của một trong các giấy tờ sau (không áp dụng đối với trường hợp các giấy tờ này đã được "
    "kết nối, chia sẻ trên Hệ thống thông tin về quản lý hoạt động khám bệnh, chữa bệnh hoặc cơ sở dữ liệu "
    "quốc gia về y tế): - Văn bằng đào tạo theo quy định tại điểm b, c, d, đ hoặc e khoản 1 Điều 127 Nghị "
    "định số 96/2023/NĐ-CP; - Chứng chỉ đào tạo chuyên khoa cơ bản theo quy định tại khoản 2 Điều 128 Nghị "
    "định số 96/2023/NĐ-CP.",
    "Bản chính hoặc bản sao hợp lệ giấy xác nhận hoàn thành quá trình thực hành theo Mẫu 07 Phụ lục I ban "
    "hành kèm theo Nghị định (không áp dụng đối với trường hợp kết quả thực hành đã được kết nối) này đối "
    "với một trong các trường hợp sau: - Người hành nghề thuộc trường hợp quy định tại điểm b, c khoản 2 "
    "Điều 125 Nghị định số 96/2023/NĐ-CP.",
    "Bản sao hợp lệ giấy phép hành nghề đã cấp (không áp dụng đối với trường hợp giấy phép hành nghề đã được "
    "kết nối, chia sẻ trên Hệ thống thông tin về quản lý hoạt động khám bệnh, chữa bệnh hoặc cơ sở dữ liệu "
    "quốc gia về y tế) hoặc chứng chỉ hành nghề được cấp trước   ngày 01 tháng 01 năm 2024.",
    "d) Bản chính hoặc bản sao hợp lệ giấy xác nhận hoàn thành quá trình thực hành theo Mẫu 07 Phụ lục I ban "
    "hành kèm theo Nghị định số 96/2023/NĐ-CP (không áp dụng đối với trường hợp kết quả thực hành đã được "
    "kết nối) đối với người hành nghề thuộc một trong các trường hợp sau.",
    "Bản sao hợp lệ giấy phép hành nghề đã cấp (không áp dụng đối với trường hợp giấy phép hành nghề đã được "
    "kết nối, chia sẻ trên Hệ thống thông tin về quản lý hoạt động khám bệnh, chữa bệnh hoặc cơ sở dữ liệu "
    "quốc gia về y tế) hoặc chứng chỉ hành nghề được cấp trước ngày 01 tháng 01 năm 2024",
    "c) Bản sao hợp lệ giấy chứng nhận người có bài thuốc gia truyền hoặc giấy chứng nhận người có phương "
    "pháp chữa bệnh gia truyền (không áp dụng đối với trường hợp các giấy chứng nhận này đã được kết nối).",
    "c) Bản sao hợp lệ văn bằng đào tạo theo quy định tại điểm b, c, d, đ hoặc e khoản 1 Điều 127 Nghị định "
    "số 96/2023/NĐ-CP (không áp dụng đối với trường hợp văn bằng đào tạo đã được kết nối).",
]

_FILES = ["don.pdf", "cchn.pdf", "cc_mot.pdf", "cc_hai.pdf", "bang_ck2.pdf"]
_TYPES = {0: "don_de_nghi", 1: "gphn", 2: "chung_chi_dao_tao", 3: "chung_chi_dao_tao", 4: "van_bang"}


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


def test_ho_so_mau_dinh_dung_anh_xa_10_dong():
    items, warnings, _ = planner.build_plan_items(_files(_FILES), _TYPES)

    assert _engine_rows(items) == {
        1: ["don.pdf"], 2: ["don.pdf"],
        3: ["cchn.pdf"], 6: ["cchn.pdf"], 8: ["cchn.pdf"],
        4: ["cc_mot.pdf", "cc_hai.pdf", "bang_ck2.pdf"],
        10: ["bang_ck2.pdf"],
    }
    assert not warnings
    assert all(i["target"] == "attp-row" for i in items)


def test_moi_dong_mot_component_name_rieng_va_khop_dung_dong_cua_no():
    """Engine gom theo componentName: hai dòng trùng tên mà dùng chung componentName sẽ dồn về một dòng."""
    names = [_fold(r["componentName"]) for r in planner._ROWS]
    assert len(set(names)) == len(names)
    for row in planner._ROWS:
        assert _fold(row["componentName"]) in _fold(_PORTAL_ROWS[row["componentIndex"] - 1])


def test_loai_ban_don_ban_chinh_con_lai_ban_sao():
    items, _, _ = planner.build_plan_items(_files(_FILES), _TYPES)
    by_row = {i["componentIndex"]: i["loaiBan"] for i in items}
    assert by_row[1] == by_row[2] == "Bản chính"
    assert {by_row[r] for r in (3, 4, 6, 8, 10)} == {"Bản sao"}


def test_hai_chung_chi_cung_dong_khong_trung_ten():
    items, _, _ = planner.build_plan_items(_files(_FILES), _TYPES)
    cc = [i["documentName"] for i in items if i["detectedType"] == "chung_chi_dao_tao"]
    assert len(cc) == 2 and cc[0] != cc[1]
    assert "cc_mot" in cc[0]
    don = next(i for i in items if i["detectedType"] == "don_de_nghi")
    assert don["documentName"] == planner._DOC_NAMES["don_de_nghi"], "chỉ một tệp thì giữ tên chuẩn"


def test_thuc_hanh_vao_hai_dong_mau_07():
    items, _, _ = planner.build_plan_items(_files(["gxn.pdf"]), {0: "thuc_hanh"})
    assert _engine_rows(items) == {5: ["gxn.pdf"], 7: ["gxn.pdf"]}


def test_tep_la_va_llm_loi_don_vao_dong_1_giu_ten_goc():
    items, warnings, classified = planner.build_plan_items(_files(["don.pdf", "la.pdf"]), {0: "don_de_nghi"})

    la = [i for i in items if i["fileName"] == "la.pdf"]
    assert len(la) == 1
    assert la[0]["componentIndex"] == 1 and la[0]["documentName"] == "la.pdf"
    assert classified[1]["source"] == "fallback"
    assert any("la.pdf" in w for w in warnings)


def test_cccd_bo_qua():
    items, _, classified = planner.build_plan_items(_files(["cccd.pdf"]), {0: "cccd"})
    assert items == [] and classified[0]["skipped"] is True


def test_normalize_doc_type_chi_nhan_dung_nhan():
    assert planner._normalize_doc_type("chung chi dao tao") == "chung_chi_dao_tao"
    assert planner._normalize_doc_type("GPHN") == "gphn"
    assert planner._normalize_doc_type("chung_chi") == "other"


def test_plan_moi_tep_mot_luot_goi(monkeypatch):
    calls = []

    async def _chat(messages, **_kw):
        calls.append(messages[-1]["content"])
        return '{"documents":[{"index":0,"docType":"gphn"}]}'

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
    assert len(res["attachments"]) == 6, "2 tệp GPHN × 3 dòng giấy phép"


# ------------------------------- mapper -------------------------------

_FACTS = {
    "NguoiHanhNghe_HoTen": "NGUYỄN VĂN AN",
    "NguoiHanhNghe_NgaySinh": "01/02/1980",
    "NguoiHanhNghe_SoDinhDanh": "001080012345",
    "NguoiHanhNghe_NgayCap": "05/06/2024",
    "NguoiHanhNghe_NoiCap": "Bộ Công An",
    "NguoiHanhNghe_ThuongTru": {"tinh": "t.p Hải Phòng", "xa": "phường An Biên", "diaChi": ""},
    "NguoiHanhNghe_DienThoai": "0912 345 678",
    "NguoiHanhNghe_Email": "NguyenVanAn @example.com",
    "HoSo_TruongHopDeNghi": "Cấp điều chỉnh giấy phép hành nghề (bổ sung phạm vi hành nghề)",
    "HoSo_PhamViHanhNghe": "Nội khoa, Hồi sức cấp cứu",
}


def _enrich(facts, ctx=None):
    fields = [{"name": k, "value": v} for k, v in facts.items()]
    out, warnings = mapper.enrich(fields, {"formContext": ctx or {}})
    return {f["name"]: f["value"] for f in out}, warnings


def test_tu_nop_dien_phan_1_va_tich_chu_ho_so():
    got, warnings = _enrich(_FACTS, {"applicantFullname": "NGUYỄN VĂN AN", "applicantIdentityNumber": "001080012345"})

    assert "data[fullname]" not in got and "data[identityNumber]" not in got, "ô cổng khoá sẵn"
    assert got["data[isOwnerDossierCheck]"] is True, "cổng này để trống mặc định"
    assert got["data[province]"] == "Thành phố Hải Phòng"
    assert got["data[district]"] == "Phường An Biên"
    assert got["data[address]"] == "Phường An Biên, Thành phố Hải Phòng", "ô (*) mà đơn không ghi số nhà"
    assert got["data[phoneNumber]"] == "0912345678"
    assert got["data[email]"] == "nguyenvanan@example.com"
    assert got["data[idIssuePlace]"] == "Bộ Công an"
    assert got["data[ghiChu]"] == (
        "Cấp điều chỉnh giấy phép hành nghề (bổ sung phạm vi hành nghề); "
        "Phạm vi hành nghề đề nghị cấp: Nội khoa, Hồi sức cấp cứu"
    )
    assert not any(k.startswith("data[owner") for k in got)
    assert not warnings


def test_nop_thay_bo_tich_va_dien_phan_2():
    got, _ = _enrich(_FACTS, {"applicantFullname": "TRẦN THỊ BÌNH", "applicantIdentityNumber": "002190054321"})

    assert got["data[isOwnerDossierCheck]"] is False
    assert got["data[ownerFullname]"] == "NGUYỄN VĂN AN"
    assert got["data[ownerIdentityNumber]"] == "001080012345"
    assert got["data[ownerNation]"] == "Việt Nam"
    assert "data[ghiChu]" in got
    assert "data[birthday]" not in got, "Phần I nộp thay do cổng đổ từ tài khoản"


def test_cmnd_9_so_bi_canh_bao():
    _, warnings = _enrich({**_FACTS, "NguoiHanhNghe_SoDinhDanh": "201234567"})
    assert any("12 chữ số" in w for w in warnings)


def test_ngu_canh_nguoi_nop_khong_co_giay_to():
    docs = [{"text": "ĐƠN ĐỀ NGHỊ ... Họ và tên: NGUYỄN VĂN AN"}]
    text = asyncio.run(runner._submitter_context(docs, {"formContext": {"applicantFullname": "TRẦN THỊ BÌNH"}}))
    assert 'result="khong_co_giay_to"' in text
    text = asyncio.run(runner._submitter_context(docs, {"formContext": {"applicantFullname": "NGUYỄN VĂN AN"}}))
    assert 'result="co_giay_to"' in text
