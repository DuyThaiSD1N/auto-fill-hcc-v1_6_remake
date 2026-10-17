"""Pipeline "Cấp CCHN luật sư đối với người được miễn đào tạo, miễn tập sự" (1.000688): mapper eForm + planner bước 3."""

from app.pipelines.cap_chung_chi_hanh_nghe_luat_su_mien_dao_tao_tap_su.attach.planner import (
    PAPER_REQUEST_NAME,
    _rule_doc_type,
    build_plan_items,
)
from app.pipelines.cap_chung_chi_hanh_nghe_luat_su_mien_dao_tao_tap_su.process.mapper import enrich
from app.pipelines.cap_chung_chi_hanh_nghe_luat_su_mien_dao_tao_tap_su.process.schema import UI_COMP_BY_NAME
from app.procedures import registry
from app.procedures.ke_khai_links import KE_KHAI_LINKS

_KEY = "cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su"


def _compact(**values) -> list[dict]:
    return [{"name": name, "comp": "x-input", "value": value} for name, value in values.items()]


def _by_name(fields: list[dict]) -> dict:
    return {f["name"]: f for f in fields}


def _facts(**extra) -> list[dict]:
    base = dict(
        KinhGui="Chủ tịch Ủy ban nhân dân thành phố Hải Phòng",
        Ndn_HoTen="Phạm Văn Bình",
        Ndn_NgaySinh="02/03/1980",
        Ndn_GioiTinh="Nam",
        Ndn_QuocTich="Việt Nam",
        Ndn_ThuongTru={"quocGia": "Việt Nam", "tinh": "TP. Hải Phòng", "xa": "phường Lê Chân", "diaChi": "Tổ 7a"},
        Ndn_NoiOHienTai={"quocGia": "Việt Nam", "tinh": "TP. Hải Phòng", "xa": "P. Hồng Bàng", "diaChi": "số 12 Lê Lợi"},
        LLTP_NoiOHienNay={"quocGia": "Việt Nam", "tinh": "thành phố Hải Phòng", "xa": "phường An Biên",
                          "diaChi": "Số 9 đường Trần Phú"},
        Ndn_DienThoai="0901000111",
        Ndn_LoaiGiayTo="Thẻ căn cước",
        Ndn_SoDinhDanh="031080000111",
        Ndn_NgayCap="10/08/2026",
        Ndn_NoiCap="Cục CSQLHC – TTXH BCA",
        MienTapSu_LyDo="Bản thân là Điều tra viên trung cấp từ năm 2015 đến 01/6/2026.",
        QuaTrinh=[
            {"tuNgay": "5/9/1998", "denNgay": "20/9/2002", "chucDanh": "Sinh viên", "coQuan": "Trường Đại học Luật Hà Nội",
             "ghiChu": "Hệ đào tạo tập trung"},
            {"tuNgay": "1/10/2002", "denNgay": "1/6/2026", "chucDanh": "Điều tra viên",
             "coQuan": "Cơ quan CSĐT Công an TP. Hải Phòng"},
        ],
        KhenThuong="Nhiều năm đạt chiến sĩ thi đua cơ sở.",
        TruyCuu="không",
        LamDon_NoiNgay={"diaDanh": "Hải Phòng", "ngay": "15/10/2026"},
    )
    base.update(extra)
    return _compact(**base)


def test_registry_wires_key_from_ke_khai_links():
    link = next(item for item in KE_KHAI_LINKS if item["key"] == _KEY)
    assert link["code"] == "1.000688"
    assert link["needsAgencySelect"] is True and link["selectSo"] is True
    assert registry.get_procedure(_KEY)["label"] == link["label"]
    assert registry.get_pipeline(_KEY) is not None
    assert registry.get_attach_pipeline(_KEY) is not None


def test_ui_fields_exist_in_eform_template():
    fields, _ = enrich(_facts(), {})
    assert fields
    for field in fields:
        assert field["comp"] == UI_COMP_BY_NAME[field["name"]]


def test_identity_and_addresses():
    fields, warnings = enrich(_facts(), {})
    ui = _by_name(fields)
    assert ui["HoVaTenC"]["value"] == "PHẠM VĂN BÌNH"
    assert ui["NgaySinhC"]["value"] == "02/03/1980"
    assert ui["GioiTinhC"]["value"] == "Nam"
    assert ui["TT_TinhThanhC"]["value"] == "Thành phố Hải Phòng"
    assert ui["TT_NoiThuongTruC"]["value"] == "Tổ 7a"
    # Nơi ở hiện tại theo đơn, lệch Phiếu LLTP thì cảnh báo.
    assert ui["TT_NoiOHienTaiC"]["value"] == "số 12 Lê Lợi"
    assert any("Nơi ở hiện tại lệch" in w for w in warnings)
    # Thẻ cấp sau 01/7/2024: Thẻ căn cước do Bộ Công an cấp dù đơn ghi Cục CSQLHC.
    assert ui["LoaiGiayToDinhDanhC"]["value"] == "Thẻ căn cước"
    assert ui["NoiCapDDC"]["value"] == "Bộ Công an"
    assert ui["NgayCapDDC"]["value"] == "10/08/2026"


def test_table_reason_and_signing_date():
    fields, _ = enrich(_facts(), {})
    ui = _by_name(fields)
    rows = ui["HoSo_QuaTrinhHoatDong"]["value"]
    assert rows[0] == {"tuNgay": "05/09/1998", "denNgay": "20/09/2002", "chucDanh": "Sinh viên",
                       "coQuan": "Trường Đại học Luật Hà Nội", "ghiChu": "Hệ đào tạo tập trung"}
    assert rows[1]["denNgay"] == "01/06/2026" and rows[1]["ghiChu"] == ""
    assert ui["HoSo_LyDoMien"]["value"] == "Bản thân là Điều tra viên trung cấp từ năm 2015 đến 01/6/2026."
    assert ui["HoSo_KhenThuong"]["value"] == "Nhiều năm đạt chiến sĩ thi đua cơ sở."
    assert ui["HoSo_TruyCuuTrachNhiem"]["value"] == "không"
    assert ui["LamTai"]["value"] == "Thành phố Hải Phòng" and "default" not in ui["LamTai"]
    assert (ui["Ngay"]["value"], ui["Thang"]["value"], ui["Nam"]["value"]) == ("15", "10", "2026")
    assert "HoSo_ToChucHanhNghe" not in ui and "HoSo_DeNghiCapLai" not in ui


def test_reason_built_from_decisions_without_request():
    facts = _facts(
        MienTapSu_LyDo="", TruyCuu="", LLTP_AnTich="Không có án tích",
        QD_BoNhiem=[
            {"so": "20 /QĐ-CA", "ngay": "01/02/2016", "chucDanh": "Điều tra viên trung cấp", "coQuan": "Công an tỉnh X"},
            {"so": "10/QĐ-CA", "ngay": "01/02/2011", "chucDanh": "Điều tra viên sơ cấp", "coQuan": "Công an tỉnh X"},
        ],
        QD_XuatNgu={"so": "5/QĐ-CA", "ngay": "20/05/2026", "ngayHieuLuc": "01/06/2026"},
    )
    fields, warnings = enrich(facts, {})
    ui = _by_name(fields)
    reason = ui["HoSo_LyDoMien"]
    assert reason["default"] is True
    assert "Điều tra viên trung cấp" in reason["value"] and "Quyết định số 20/QĐ-CA ngày 01/02/2016" in reason["value"]
    assert reason["value"].endswith("đến 01/06/2026.")
    assert ui["HoSo_TruyCuuTrachNhiem"]["value"] == "Không" and ui["HoSo_TruyCuuTrachNhiem"]["default"] is True
    assert any("lý do miễn tập sự được dựng" in w for w in warnings)


def test_account_mismatch_warns():
    _, warnings = enrich(_facts(), {"formContext": {"applicantFullname": "Lê Thị Cúc"}})
    assert any("không phải người đề nghị" in w for w in warnings)
    _, warnings = enrich(_facts(), {"formContext": {"applicantFullname": "PHẠM VĂN BÌNH"}})
    assert not any("không phải người đề nghị" in w for w in warnings)


def _files(*names):
    return [{"name": name} for name in names]


def test_plan_routes_rows_like_portal_guide():
    raw = _files("BANG.pdf", "QD.pdf", "LLTP.pdf", "DON.pdf")
    types = {0: "degree", 1: "exemption_proof", 2: "criminal_record", 3: "paper_request"}
    attachments, classified, warnings = build_plan_items(raw, {}, {i: {"type": t, "documentName": ""}
                                                                   for i, t in types.items()})
    by_file = {a["fileIndex"]: a for a in attachments}
    assert (by_file[0]["componentIndex"], by_file[0]["target"]) == (1, "existing")
    assert by_file[1]["componentIndex"] == 2
    assert by_file[2]["componentIndex"] == 4
    assert by_file[3]["target"] == "new" and by_file[3]["componentName"] == PAPER_REQUEST_NAME
    assert by_file[3]["documentName"] == "Đơn đề nghị cấp Chứng chỉ hành nghề luật sư"
    # Không bao giờ đính đè dòng 5 (Tờ khai cổng tự sinh) và không tách trang.
    assert all(a["componentIndex"] != 5 for a in attachments)
    assert all("pageRange" not in a for a in attachments)
    assert len(classified) == 4
    assert any("sức khỏe" in w for w in warnings)


def test_plan_merges_several_files_into_one_row():
    raw = _files("QD1.pdf", "QD2.pdf", "CAMKET.pdf", "LLTP.pdf", "SK.pdf")
    types = {0: "exemption_proof", 1: "exemption_proof", 2: "commitment", 3: "criminal_record", 4: "health"}
    attachments, _, warnings = build_plan_items(raw, {}, {i: {"type": t, "documentName": ""} for i, t in types.items()})
    row2 = next(a for a in attachments if a["componentIndex"] == 2)
    assert row2["sourceFileIndexes"] == [0, 1]
    row4 = next(a for a in attachments if a["componentIndex"] == 4)
    assert row4["sourceFileIndexes"] == [2, 3]  # văn bản cam kết đứng trước Phiếu LLTP
    assert next(a for a in attachments if a["componentIndex"] == 3)["fileIndex"] == 4
    assert not any("sức khỏe" in w for w in warnings)


def test_rule_fallback_types():
    assert _rule_doc_type("VĂN BẢN ĐỀ NGHỊ CẤP CHỨNG CHỈ HÀNH NGHỀ LUẬT SƯ Tôi tên là A Số định danh 031080000111") \
        == "paper_request"
    assert _rule_doc_type("PHIẾU LÝ LỊCH TƯ PHÁP SỐ 1 Họ và tên Số 031080000111") == "criminal_record"
    assert _rule_doc_type("BẰNG TỐT NGHIỆP ĐẠI HỌC Cử nhân Luật") == "degree"
    assert _rule_doc_type("QUYẾT ĐỊNH Về việc bổ nhiệm chức danh Điều tra viên") == "exemption_proof"
    assert _rule_doc_type("") == "other"
