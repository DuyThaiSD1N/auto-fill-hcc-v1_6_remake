"""Khai tử trên Cổng DVC quốc gia bản mới (SurveyJS): nhận diện, mapper sang tên câu hỏi, đính kèm.

Tên câu hỏi lấy theo crawl form dichvucong.gov.vn/nop-ho-so (2026-10-05). Dữ liệu dưới đây là hồ sơ GIẢ.
"""

from app.pipelines.khai_tu import process as khai_tu_process
from app.pipelines.khai_tu.attach import planner as khai_tu_planner
from app.pipelines.khai_tu_dvcqg import attach as dvcqg_attach
from app.pipelines.khai_tu_dvcqg import process as dvcqg_process
from app.pipelines.khai_tu_dvcqg.attach import planner
from app.pipelines.khai_tu_dvcqg.process import mapper
from app.pipelines.khai_tu_dvcqg.process.schema import UI_COMP_BY_NAME
from app.process.schemas import FileItem
from app.procedures.ke_khai_links import KE_KHAI_LINKS
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure

KEY = "khai-tu-dvcqg"

_DOSSIER = {
    "NguoiYeuCau_HoTen": "Trần Thị Mai",
    "NguoiYeuCau_SoDinhDanh": "001190000001",
    "ToKhai_QuanHeNguoiYeuCau": "Con",
    "ToKhai_LoaiDangKy": "Đăng ký khai tử đúng hạn",
    "NguoiMat_HoTen": "Lê Văn An",
    "NguoiMat_NgaySinh": "07/03/1940",
    "NguoiMat_GioiTinh": "Nam",
    "NguoiMat_DanToc": "kinh",
    "NguoiMat_QuocTich": "Việt Nam",
    "NguoiMat_SoDinhDanh": "001040000002",
    "NguoiMat_NgayCapGiayTo": "6/11/2021",
    "NguoiMat_NoiCapGiayTo": "Bộ Công an",
    "NguoiMat_NoiCuTruCuoiCung": {"tinh": "Tỉnh Nghệ An", "xa": "Xã Nghi Lộc", "diaChi": "Xóm 3"},
    "NguoiMat_NgayMat": "01/08/2026",
    "NguoiMat_GioMat": "18:05",
    "NguoiMat_NguyenNhanMat": "Bệnh già",
    "NguoiMat_NoiChet": {"tinh": "Tỉnh Nghệ An", "xa": "Xã Nghi Lộc", "diaChi": "Xóm 3"},
    "Gbt_So": "01",
    "Gbt_CoQuanCap": "UBND xã Nghi Lộc",
    "Gbt_NgayCap": "11/08/2026",
    "CopyRequest_WantsCopy": "Có",
    "CopyRequest_Quantity": "3",
}
_NOTICE_OCR = "ỦY BAN NHÂN DÂN\nXÃ NGHI LỘC\nSố: 01/UBND-GBT\nGIẤY BÁO TỬ\nHọ tên người chết: Lê Văn An"


def _enrich(values: dict, options: dict | None = None, ocr_text: str = "") -> list[dict]:
    return mapper.enrich([{"name": k, "value": v} for k, v in values.items()], options, ocr_text=ocr_text)


def _by_name(rows: list[dict]) -> dict:
    return {row["name"]: row for row in rows}


def test_registered_with_own_pipelines_and_old_khai_tu_untouched():
    procedure = get_procedure(KEY)
    assert procedure["mode"] == "agent"
    assert procedure["hasAttachmentStep"] is True
    assert get_pipeline(KEY) is dvcqg_process.run
    assert get_attach_pipeline(KEY) is dvcqg_attach.plan
    assert get_pipeline("khai-tu") is khai_tu_process.run


def test_detect_targets_new_portal_khai_tu_only():
    detect = get_procedure(KEY)["detect"]
    # formalityId trên URL nộp hồ sơ chính là mã trang thủ tục khai tử trong danh mục kê khai.
    khai_tu_link = next(item for item in KE_KHAI_LINKS if item["key"] == "khai-tu")["url"]
    formality_id = detect["urlIncludes"][0].split("=", 1)[1]
    assert khai_tu_link.endswith(formality_id)
    # Chỉ xét trên trang nộp hồ sơ của cổng quốc gia, không lan sang cổng tỉnh hay liên thông.
    assert detect["urlScope"] == ["//dichvucong.gov.vn/nop-ho-so"]
    assert "//dichvucong.gov.vn/nop-ho-so" not in "https://lienthong.dichvucong.gov.vn/nop-ho-so"
    assert "//dichvucong.gov.vn/nop-ho-so" not in "https://dichvucong.quangninh.gov.vn/nop-ho-so"
    assert detect["textPriority"] is True and detect["headingDisabled"] is True
    # "Đăng ký lại khai tử" không được khớp cụm của khai tử thường.
    assert "thủ tục đăng ký khai tử" not in "thủ tục đăng ký lại khai tử"


def test_mapper_fills_deceased_block_with_survey_question_names():
    rows = _by_name(_enrich(_DOSSIER, {}, _NOTICE_OCR))
    values = {name: row["value"] for name, row in rows.items()}

    assert values["citizenmoiquanhe"] == "Con"
    assert values["citizenNDK_HoVaTen"] == "LÊ VĂN AN"
    assert values["citizenNDK_SoDinhDanh"] == "001040000002"
    assert values["citizenNDK_NgaySinh"] == "07/03/1940"
    codes = {name: row.get("code") for name, row in rows.items()}
    # Dropdown danh mục tĩnh: nhãn đúng formJson + mã choice để extension setValue vào model SurveyJS.
    assert (values["citizenGioitinh_NgdcKT"], codes["citizenGioitinh_NgdcKT"]) == ("Nam", "1")
    assert (values["citizenDantoc_NgdcKT"], codes["citizenDantoc_NgdcKT"]) == ("Kinh", "01")
    assert (values["citizenQuoctich_NgdcKT"], codes["citizenQuoctich_NgdcKT"]) == ("Việt Nam", "VN")
    assert values["citizenSogiaytotuythan_NgdcKT"] == "001040000002"
    assert (values["citizenField19"], codes["citizenField19"]) == ("06/11/2021", "2021-11-06")
    assert values["citizenNoicapgiaytotuythan_NgdcKT"] == "Bộ Công an"
    assert values["citizenField56"] == "01/08/2026"
    assert (values["citizenGiomat"], values["citizenPhutmat"]) == ("18", "5")
    assert (values["citizenNDKLoaidangky"], codes["citizenNDKLoaidangky"]) == ("Đăng ký đúng hạn", "1")
    assert (values["citizenNDKLoaicutru"], codes["citizenNDKLoaicutru"]) == ("Thường trú", "1")
    assert rows["citizenNDKLoaicutru"]["default"] is True
    assert (values["citizenNDKnoicutru"], codes["citizenNDKnoicutru"]) == ("Trong nước", "1")
    # Thường trú trong nước → cụm ô *_Thtru. Dropdown tỉnh/xã của cổng ghi đủ tiền tố nên giữ nguyên.
    assert values["citizenNDKTinh_Thtru"] == "Tỉnh Nghệ An"
    assert values["citizenNDKXa_Thtru"] == "Xã Nghi Lộc"
    assert values["citizenNDKDiaChi_Thtru"] == "Xóm 3"
    assert values["citizenNoichet"]["luaChon"] == "Trong nước"
    assert values["citizenNguyennhanchet_NgdcKT"] == "Bệnh già"
    assert values["citizenLoaigiaybaotu"] == "Giấy báo tử"
    # Ô chữ của cổng mới nhận đủ số hiệu, không chỉ phần số như biểu mẫu cũ.
    assert values["citizenSogiaybaotu_NgdcKT"] == "01/UBND-GBT"
    assert codes["citizenNgaythangnamcapgiaybaotu"] == "2026-08-11"
    assert values["citizenCoquancapgiaybaotucochuthichneukhongcothidetrong"] == "UBND xã Nghi Lộc"
    assert values["citizenSoluongbansaonguoiyeucaudenghi"] == "3"


def test_lookup_trio_goes_first_so_portal_can_fetch_population_data():
    """Họ tên + số định danh + ngày sinh kích hoạt get-citizen-by-code; cổng tự đổ + khóa ô còn lại."""
    names = [row["name"] for row in _enrich(_DOSSIER, {}, _NOTICE_OCR)]
    assert names[:4] == ["citizenmoiquanhe", "citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh"]
    # Loại cư trú + radio quyết định cụm ô địa chỉ nào hiện ra → phải đi trước cụm đó.
    assert names.index("citizenNDKLoaicutru") < names.index("citizenNDKnoicutru") < names.index("citizenNDKTinh_Thtru")


def test_values_respect_portal_validators():
    values = dict(_DOSSIER, NguoiMat_SoDinhDanh="040123456", NguoiMat_NgaySinh="1940",
                  NguoiMat_NgayMat="1/8/2026", NguoiMat_DanToc="Khmer")
    rows = _by_name(_enrich(values, {}))
    # Regex cổng chỉ nhận số định danh 12 số → CMND 9 số không đưa vào ô này.
    assert "citizenNDK_SoDinhDanh" not in rows
    assert rows["citizenNDK_NgaySinh"]["value"] == "1940"
    assert rows["citizenField56"]["value"] == "01/08/2026"
    assert (rows["citizenDantoc_NgdcKT"]["value"], rows["citizenDantoc_NgdcKT"]["code"]) == ("Khơ-me", "05")


def test_registration_type_inferred_when_declaration_is_silent():
    """Tờ khai không ghi loại đăng ký: hồ sơ biên bản xác minh / bản cam đoan, không giấy báo tử → người chết
    đã lâu; còn lại theo 15 ngày kể từ ngày mất. Suy luận thì tô vàng."""
    from datetime import date

    proof_ocr = "TỜ KHAI ĐĂNG KÝ KHAI TỬ\n...\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nBIÊN BẢN XÁC MINH\nVề việc người chết"
    assert mapper._loai_dang_ky("", False, "01/01/1990", False, proof_ocr) == ("5", True)
    # Có giấy báo tử thì không phải "người chết đã lâu" dù hồ sơ kèm biên bản.
    today = date(2026, 10, 5)
    assert mapper._loai_dang_ky("", False, "01/10/2026", True, proof_ocr, today) == ("1", True)
    assert mapper._loai_dang_ky("", False, "01/08/2026", False, "TỜ KHAI", today) == ("4", True)
    # Câu "Tôi cam đoan…" trong tờ khai không phải tiêu đề BẢN CAM ĐOAN.
    assert mapper._loai_dang_ky("", False, "", False, "Tôi cam đoan những nội dung khai trên") == ("1", True)
    # Tờ khai ghi rõ thì theo tờ khai, không tô vàng.
    assert mapper._loai_dang_ky("4", True, "01/10/2026", True, proof_ocr, today) == ("4", False)

    values = {k: v for k, v in _DOSSIER.items() if k != "ToKhai_LoaiDangKy" and not k.startswith("Gbt_")}
    row = _by_name(_enrich(values, {}, proof_ocr))["citizenNDKLoaidangky"]
    assert (row["value"], row["code"], row["default"]) == ("Đăng ký khai tử cho người chết đã lâu", "5", True)


def test_ethnic_snap_never_guesses():
    assert mapper._snap(mapper.DAN_TOC, "H'Mông") == ("08", "H'Mông")
    assert mapper._snap(mapper.DAN_TOC, "Mông", mapper._DAN_TOC_ALIAS) == ("08", "H'Mông")
    assert mapper._snap(mapper.DAN_TOC, "Ê Đê") == ("12", "Ê-đê")
    assert mapper._snap(mapper.DAN_TOC, "Xơ Đăng") == ("14", "Xơ-Đăng")
    assert mapper._snap(mapper.DAN_TOC, "Dân tộc lạ", mapper._DAN_TOC_ALIAS) is None


def test_residence_fields_follow_residence_type_and_abroad_branch():
    legacy = [
        {"name": "nktLoaiCuTru", "value": "Tạm trú"},
        {"name": "nktNoiCuTru", "value": "1"},
        {"name": "nktNoiCuTru_TrongNuoc", "value": {"tinh": "Tỉnh Nghệ An", "xa": "Xã Nghi Lộc", "diaChi": "Xóm 3"}},
    ]
    names = [row["name"] for row in mapper.translate(legacy)]
    assert {"citizenNDKTinh_Tamtru", "citizenNDKXa_Tamtru", "citizenNDKDiachi_Tamtru"} <= set(names)
    assert not [n for n in names if n.endswith("_Thtru")]

    abroad = [
        {"name": "nktNoiCuTru", "value": "2"},
        {"name": "nktNoiCuTru_TrongNuoc", "value": {"quocGia": "Lào", "diaChi": "Viêng Chăn"}},
    ]
    rows = _by_name(mapper.translate(abroad))
    assert rows["citizenNDKnoicutru"]["code"] == "2"
    assert rows["citizenNDKQG_Khac"]["value"] == "Lào" and "code" not in rows["citizenNDKQG_Khac"]
    assert rows["citizenNDKDiaChi_Khac"]["value"] == "Viêng Chăn"


def test_every_row_uses_declared_comp_and_requester_block_is_never_written():
    rows = _enrich(_DOSSIER, {}, _NOTICE_OCR)
    assert all(row["comp"] == UI_COMP_BY_NAME[row["name"]] for row in rows)
    names = [row["name"] for row in rows]
    # Khối người nộp cổng đổ từ VNeID và khóa readonly.
    khoi_nguoi_nop = ("citizenName", "citizenIdentity", "citizenDateOfBirth", "citizenField18",
                      "citizenField16", "citizenIssuePlace", "citizenIssueDate", "citizenNyc")
    assert not [n for n in names if n.startswith(khoi_nguoi_nop)]
    # Kính gửi + địa điểm/ngày lập tờ khai: giấy tờ không có, cổng tự điền ngày.
    assert not set(names) & {"citizenField27", "citizenField29", "citizenField28", "citizenField31", "citizenField32"}
    assert len(names) == len(set(names))


def test_copy_quantity_is_required_so_zero_when_no_request():
    values = dict(_DOSSIER)
    values.pop("CopyRequest_WantsCopy")
    values.pop("CopyRequest_Quantity")
    row = _by_name(_enrich(values, {}))["citizenSoluongbansaonguoiyeucaudenghi"]
    assert row["value"] == "0" and row["default"] is True

    values["CopyRequest_WantsCopy"] = "Không"
    row = _by_name(_enrich(values, {}))["citizenSoluongbansaonguoiyeucaudenghi"]
    assert row["value"] == "0" and "default" not in row


def test_death_extract_replaces_missing_death_notice():
    """Không có giấy báo tử mà có trích lục khai tử → ghi trích lục là giấy tờ thay thế (quy tắc "khai-tu")."""
    values = {k: v for k, v in _DOSSIER.items() if not k.startswith("Gbt_")}
    extract_ocr = (
        "TRÍCH LỤC KHAI TỬ\nHọ, chữ đệm, tên: LÊ VĂN AN\n"
        "Đã được đăng ký khai tử tại UBND xã Nghi Lộc\nSố: 15/2026\n"
    )
    rows = _by_name(_enrich(values, {}, extract_ocr))
    assert rows["citizenLoaigiaybaotu"]["value"] == "Giấy tờ thay thế"
    assert rows["citizenSogiaybaotu_NgdcKT"]["value"] == "15/2026"


def test_death_notice_number_recovers_full_serial_from_ocr():
    assert mapper._death_notice_number("01", "Số: 01/UBND-GBT") == "01/UBND-GBT"
    assert mapper._death_notice_number("1", "SỐ 01 / UBND-GBT.") == "01/UBND-GBT"
    assert mapper._death_notice_number("01", "Số: 01/TLKT-BS") == "01"
    assert mapper._death_notice_number("5", "Số: 12/UBND-GBT") == "5"


def test_portal_rows_follow_new_table_order():
    """Cổng mới đổi thứ tự: ủy quyền lên dòng 2, chứng cứ sự kiện chết xuống dòng 3."""
    options = planner._with_portal_rows({})
    assert khai_tu_planner._slot_for_type(options, "death_notice")[0] == 1
    assert khai_tu_planner._slot_for_type(options, "authorization")[0] == 2
    assert khai_tu_planner._slot_for_type(options, "death_event_proof")[0] == 3
    assert khai_tu_planner._slot_for_type(options, "death_place_proof")[0] == 4
    # Extension đã gửi bảng thật thì dùng bảng đó.
    real = {"attachmentContext": {"components": [{"index": 7, "componentName": "Văn bản ủy quyền"}]}}
    assert planner._with_portal_rows(real) == real


async def test_attach_drops_documents_without_a_row(monkeypatch):
    seen = {}

    async def fake_plan(files, options, session):
        seen["options"] = options
        return {
            "attachments": [
                {"fileIndex": 0, "fileName": "gbt.pdf", "documentName": "Giấy báo tử",
                 "target": "existing", "componentIndex": 1},
                {"fileIndex": 1, "fileName": "cccd.pdf", "documentName": "Căn cước công dân",
                 "target": "new", "componentIndex": None},
            ],
            "extracted": {"classified": []},
            "errors": [],
        }

    monkeypatch.setattr(khai_tu_planner, "plan", fake_plan)
    files = [FileItem(name=n, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")
             for n in ("gbt.pdf", "cccd.pdf")]

    result = await planner.plan(files, {}, {})

    assert len(seen["options"]["attachmentContext"]["components"]) == 4
    assert [item["fileIndex"] for item in result["attachments"]] == [0]
    assert result["extracted"]["skipped"] == ["cccd.pdf (Căn cước công dân)"]


async def test_attach_puts_same_type_documents_on_one_row(monkeypatch):
    """Ô "Tài liệu đính kèm" của cổng mới nhận nhiều tệp: biên bản xác minh + bản cam đoan cùng vào dòng 3
    (planner "khai-tu" cho tệp thứ hai đi "thêm thành phần", cổng mới không có nút đó)."""
    async def fake_plan(files, options, session):
        return {
            "attachments": [
                {"fileIndex": 0, "fileName": "a.pdf", "documentName": "Biên bản xác minh",
                 "target": "existing", "componentIndex": 3, "componentName": "chứng cứ"},
                {"fileIndex": 1, "fileName": "b.pdf", "documentName": "Bản cam đoan",
                 "target": "new", "componentIndex": None, "componentName": "Bản cam đoan", "needsAddComponent": True},
                {"fileIndex": 2, "fileName": "c.pdf", "documentName": "Căn cước công dân", "target": "new"},
            ],
            "extracted": {"classified": [
                {"fileIndex": 0, "documentName": "Biên bản xác minh", "type": "death_event_proof"},
                {"fileIndex": 1, "documentName": "Bản cam đoan", "type": "death_event_proof"},
                {"fileIndex": 2, "documentName": "Căn cước công dân", "type": "identity"},
            ]},
            "errors": [],
        }

    monkeypatch.setattr(khai_tu_planner, "plan", fake_plan)
    files = [FileItem(name=n, type="application/pdf", dataUrl="data:application/pdf;base64,AAA", role="doc")
             for n in ("a.pdf", "b.pdf", "c.pdf")]

    result = await planner.plan(files, {}, {})

    assert [(i["fileIndex"], i["componentIndex"], i["target"]) for i in result["attachments"]] == [
        (0, 3, "existing"), (1, 3, "existing"),
    ]
    assert result["attachments"][1]["needsAddComponent"] is False
    assert result["extracted"]["skipped"] == ["c.pdf (Căn cước công dân)"]
