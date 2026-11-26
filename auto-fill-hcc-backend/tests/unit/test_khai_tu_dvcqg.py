import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import pytest

from app.pipelines.khai_tu_dvcqg.attach.dinh_kem_khong_tach.planner import ROW_GIAY_BAO_TU, ROWS, build_plan_items
from app.pipelines.khai_tu_dvcqg.process import mapper, reason
from app.pipelines.khai_tu_dvcqg.process.schema import UI_COMP_BY_NAME
from app.procedures.registry import PROCEDURES

HTML_DIR = Path(__file__).resolve().parents[3] / "html mới"
SNAPSHOTS = {
    "khai-tu": HTML_DIR / "khai tử" / "khai tử html mới.html",
    "khai-sinh-dang-ky-thuong": HTML_DIR / "khai sinh" / "khai sinh html mới.html",
    "trich-luc-ks": HTML_DIR / "trích lụcc" / "trích lục html mới.html",
    "thay-doi-cai-chinh-ho-tich": HTML_DIR / "cải chính" / "cải chính html mới.html",
    "xac-nhan-tinh-trang-hon-nhan": HTML_DIR / "tình trạng hôn nhân" / "tình trạng hôn nhân form mới.html",
}
ACCOUNT = {"applicantFullname": "NGUYEN VAN B", "applicantIdentityNumber": "001090000002"}


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFD", value).replace("Đ", "D").replace("đ", "d")
    return re.sub(r"\s+", " ", "".join(c for c in text if unicodedata.category(c) != "Mn")).lower()


def _body(path: Path) -> str:
    html = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", path.read_text(encoding="utf-8"))
    return _fold(re.sub(r"<[^>]+>", " ", html))


def _context(relation="", loai="", gbt="Giấy báo tử"):
    return (
        "<phan_vai_da_xac_dinh>\n<nguoi_mat>\nHọ tên: NGUYEN VAN A\n</nguoi_mat>\n"
        f"<quan_he>\nKết luận: {relation}\n</quan_he>\n"
        f"<loai_dang_ky>\nKết luận: {loai}\nGiấy báo tử: {gbt}\n</loai_dang_ky>\n</phan_vai_da_xac_dinh>"
    )


def _enrich(values: dict, context: str = "", account=ACCOUNT):
    fields = [{"name": k, "comp": "x-input", "value": v} for k, v in values.items()]
    return mapper.enrich(fields, {"formContext": account, "_reasoning_context": context})


def _by(out):
    return {f["name"]: f for f in out}


BASE = {
    "NguoiMat_HoTen": "Nguyen Van A",
    "NguoiMat_SoDinhDanh": "001050000001",
    "NguoiMat_NgaySinh": "1950",
    "NguoiMat_GioiTinh": "Nam",
    "NguoiMat_DanToc": "Kinh",
    "NguoiMat_SoGiayTo": "001050000001",
    "NguoiMat_NgayCap": "02/03/2021",
    "NguoiMat_NoiCuTru": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Xã Tam Hợp", "diaChi": "Xóm 5"},
    "NguoiMat_NgayMat": (date.today() - timedelta(days=3)).strftime("%d/%m/%Y"),
    "NguoiMat_GioMat": "09:30",
    "NguoiMat_NoiChet": {"quocGia": "Việt Nam", "tinh": "Nghệ An", "xa": "Xã Tam Hợp", "diaChi": "Tại nhà"},
    "Gbt_Loai": "Giấy báo tử",
    "Gbt_So": "01/UBND-GBT",
    "Gbt_NgayCap": "05/10/2026",
    "Gbt_CoQuanCap": "UBND xã Tam Hợp",
    "NguoiYeuCau_HoTen": "Nguyen Van B",
    "NguoiYeuCau_SoDinhDanh": "001090000002",
    "NguoiYeuCau_QuanHe": "Con",
    "SoLuongBanSao": "2",
}


def test_contract_uses_shared_new_portal_engine():
    assert all(comp.startswith("sjs-") for comp in UI_COMP_BY_NAME.values())
    assert UI_COMP_BY_NAME["citizenNoichet"] == "sjs-radio"
    assert UI_COMP_BY_NAME["citizenNoichet_TrongNuoc"] == "sjs-area"


@pytest.mark.skipif(not all(p.exists() for p in SNAPSHOTS.values()), reason="thiếu snapshot cổng")
def test_detect_text_unique_across_new_portal_forms():
    bodies = {key: _body(path) for key, path in SNAPSHOTS.items()}
    for key in SNAPSHOTS:
        phrases = [_fold(p) for p in next(p for p in PROCEDURES if p["key"] == key)["detect"]["textIncludes"]]
        for page, body in bodies.items():
            assert all(p in body for p in phrases) == (key == page), (key, page)


def test_new_portal_forms_detect_by_formality_id():
    # Thiếu formalityId thì popup chỉ nhận theo chữ trên form (chưa render là trượt) và không coi là "định danh
    # mạnh" → đang giữ tệp của thủ tục khác thì bỏ qua, panel kẹt "Chưa có thủ tục nào được chọn".
    from app.procedures.ke_khai_links import KE_KHAI_LINKS

    for key in SNAPSHOTS:
        detect = next(p for p in PROCEDURES if p["key"] == key)["detect"]
        uuid = next(link["url"] for link in KE_KHAI_LINKS if link["key"] == key).rstrip("/").rsplit("/", 1)[1]
        assert f"formalityId={uuid}" in detect["urlIncludes"], key
        assert any("dichvucong.gov.vn/nop-ho-so" in scope for scope in detect["urlScope"]), key


@pytest.mark.skipif(not SNAPSHOTS["khai-tu"].exists(), reason="thiếu snapshot cổng")
def test_static_ui_keys_exist_in_snapshot():
    data_names = set(re.findall(r'data-name="([A-Za-z0-9_]+?)__\d+"',
                                SNAPSHOTS["khai-tu"].read_text(encoding="utf-8")))
    always = {"citizenmoiquanhe", "citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh",
              "citizenNDKnoicutru", "citizenNoichet", "citizenLoaigiaybaotu", "citizenSoluongbansaonguoiyeucaudenghi",
              "citizenGioitinh_NgdcKT", "citizenField56", "citizenNDKLoaidangky"}
    assert always <= data_names


def test_full_case_order_codes_and_relation():
    out, warnings = _enrich(BASE, _context("Con"))
    names = [f["name"] for f in out]
    by = _by(out)
    assert names[:4] == ["citizenmoiquanhe", "citizenNDK_HoVaTen", "citizenNDK_SoDinhDanh", "citizenNDK_NgaySinh"]
    assert by["citizenmoiquanhe"]["value"] == "Con" and not by["citizenmoiquanhe"].get("default")
    assert all(by[n].get("lookup") for n in names[1:4]) and not by["citizenGioitinh_NgdcKT"].get("lookup")
    assert by["citizenNDK_NgaySinh"]["value"] == "1950"
    assert by["citizenGioitinh_NgdcKT"]["code"] == "1" and by["citizenDantoc_NgdcKT"]["code"] == "01"
    assert by["citizenField19"]["code"] == "2021-03-02"
    assert by["citizenNoicapgiaytotuythan_NgdcKT"]["value"]       # thẻ 12 số → mặc định theo ngày cấp
    assert by["citizenGiomat"]["value"] == "09" and by["citizenPhutmat"]["value"] == "30"
    assert by["citizenNDKLoaidangky"]["code"] == "1"             # chết 3 ngày trước → đúng hạn
    assert names.index("citizenNDKnoicutru") < names.index("citizenNDKTinh_Thtru")
    assert by["citizenNDKXa_Thtru"]["value"] == "Xã Tam Hợp"
    assert by["citizenNoichet_TrongNuoc"]["radio"] == "citizenNoichet"
    assert names.index("citizenNoichet") < names.index("citizenNoichet_TrongNuoc")
    assert by["citizenSogiaybaotu_NgdcKT"]["value"] == "01/UBND-GBT"
    assert by["citizenSoluongbansaonguoiyeucaudenghi"]["value"] == "2"
    assert not warnings


def test_giay_khong_doc_duoc_ngay_cap_thi_tra_o_ngay_cap_ve_trong():
    # OCR làm rơi cụm "cấp ngày" viết tay → cổng tra CSDL tự đổ ngày cấp khác giấy; BE xoá ô cho cán bộ nhập.
    values = {k: v for k, v in BASE.items() if k != "NguoiMat_NgayCap"}
    values["NguoiMat_NoiCap"] = "Cục Cảnh sát QLHC về TTXH"
    out, warnings = _enrich(values, _context("Con"))
    by = _by(out)
    assert by["citizenField19"] == {"name": "citizenField19", "comp": "sjs-date", "value": "", "clear": True}
    assert by["citizenSogiaytotuythan_NgdcKT"]["value"] == "001050000001"
    names = [f["name"] for f in out]
    assert names.index("citizenSogiaytotuythan_NgdcKT") < names.index("citizenField19")
    assert any("ngày cấp giấy tờ tùy thân của người mất" in w for w in warnings)
    # Không có số giấy tờ thì cả cụm không phát, không xoá ô.
    bare = {k: v for k, v in values.items() if k not in ("NguoiMat_SoGiayTo", "NguoiMat_NoiCap")}
    assert "citizenField19" not in _by(_enrich(bare, _context("Con"))[0])


def test_late_and_long_dead_registration():
    late = {**BASE, "NguoiMat_NgayMat": "01/01/2020"}
    assert _by(_enrich(late, _context("Con"))[0])["citizenNDKLoaidangky"]["code"] == "4"
    long_dead = _enrich(late, _context("Con", loai="Đăng ký khai tử cho người chết đã lâu"))[0]
    assert _by(long_dead)["citizenNDKLoaidangky"]["code"] == "5"


def test_relation_from_declaration_only_when_requester_is_account():
    other = {"applicantFullname": "LE THI C", "applicantIdentityNumber": "001190000003"}
    out, warnings = _enrich(BASE, _context(""), account=other)
    assert "citizenmoiquanhe" not in _by(out) and warnings
    out, _ = _enrich(BASE, _context("Cháu nội"), account=other)
    assert _by(out)["citizenmoiquanhe"]["value"] == "Cháu nội" and _by(out)["citizenmoiquanhe"]["default"]


def test_quan_he_to_khai_khi_so_lech_vai_chu_so_ma_trung_ten():
    # Số tờ khai viết tay lệch 1 chữ số (OCR) với tài khoản, họ tên trùng khi bỏ dấu → người nộp chính là người yêu cầu.
    near = {**BASE, "NguoiYeuCau_HoTen": "Nguyễn Văn B", "NguoiYeuCau_SoDinhDanh": "001090000003",
            "NguoiYeuCau_QuanHe": "Con đẻ"}
    by = _by(_enrich(near, _context(""))[0])
    assert by["citizenmoiquanhe"]["value"] == "Con đẻ"
    other = {**near, "NguoiYeuCau_HoTen": "Trần Thị C"}
    assert "citizenmoiquanhe" not in _by(_enrich(other, _context(""))[0])


def test_quan_he_khong_ghi_chu_khong_xac_dinh():
    vague = {**BASE, "NguoiYeuCau_HoTen": "Nguyen Van B", "NguoiYeuCau_SoDinhDanh": "001090000002",
             "NguoiYeuCau_QuanHe": "Không xác định"}
    assert "citizenmoiquanhe" not in _by(_enrich(vague, _context(""))[0])


def test_hai_the_khong_giay_khai_tu_agent_bo_trong_thi_nguoi_sinh_truoc_la_nguoi_mat():
    docs = [{"text": "CĂN CƯỚC CÔNG DÂN\nSố định danh: 001150000011"}, {"text": "CĂN CƯỚC\nSố định danh: 001190000022"}]
    empty = "<nguoi_mat>\nHọ tên: không có\nSố định danh: không có\n</nguoi_mat>"
    assert "Số định danh: 001150000011" in reason._render_context(empty, {}, docs)
    # Một thẻ là của tài khoản → thẻ còn lại là người mất.
    account = {"formContext": {"applicantIdentityNumber": "001150000011"}}
    assert "Số định danh: 001190000022" in reason._render_context(empty, account, docs)
    # Có giấy báo tử hoặc agent đã chốt người mất → không đụng.
    assert "001150000011" not in reason._render_context(empty, {}, [*docs, {"text": "GIẤY BÁO TỬ"}])
    chosen = "<nguoi_mat>\nHọ tên: NGUYEN VAN A\n</nguoi_mat>"
    assert "001150000011" not in reason._render_context(chosen, {}, docs)
    # Giấy khai sinh (khai tử trẻ nhỏ): số trên giấy khai sinh không phải thẻ → không áp.
    assert "001150000011" not in reason._render_context(empty, {}, [*docs, {"text": "GIẤY KHAI SINH"}])
    # Agent dẫn luật hai thẻ mà chốt người sinh sau → theo luật đã dẫn; chốt vì căn cứ khác thì giữ.
    inverted = ("<nguoi_mat>\nHọ tên: B\nSố định danh: 001190000022\n"
                "Căn cứ phân vai: Chỉ có 2 CCCD, người sinh sau là người mất\n</nguoi_mat>")
    assert "Số định danh: 001150000011" in reason.section(reason._render_context(inverted, {}, docs), "nguoi_mat")
    own = inverted.replace("Chỉ có 2 CCCD, người sinh sau là người mất", "Bản cam đoan ghi người này đã chết")
    assert "001150000011" not in reason._render_context(own, {}, docs)
    both = "<nguoi_yeu_cau>\nHọ tên: A\nSố định danh: 001150000011\n</nguoi_yeu_cau>\n" + empty
    assert "001150000011" not in reason.section(reason._render_context(both, {}, docs), "nguoi_yeu_cau")


def test_nguoi_mat_trung_tai_khoan_thi_lay_the_con_lai():
    docs = [{"text": "CĂN CƯỚC CÔNG DÂN\nSố định danh: 001150000011"}, {"text": "CĂN CƯỚC\nSố định danh: 001190000022"}]
    account = {"formContext": {"applicantIdentityNumber": "001150000011"}}
    agent = "<nguoi_mat>\nHọ tên: A\nSố định danh: 001150000011\nCăn cứ phân vai: CCCD\n</nguoi_mat>"
    assert "Số định danh: 001190000022" in reason.section(reason._render_context(agent, account, docs), "nguoi_mat")


def test_agent_ghi_chu_tai_khoan_la_nguoi_mat_thi_bo():
    docs = [{"text": "GIẤY KHAI SINH\nHọ tên: A"}, {"text": "CĂN CƯỚC\nSố định danh: 001190000022"}]
    account = {"formContext": {"applicantIdentityNumber": "001190000022"}}
    agent = "<nguoi_mat>\nHọ tên: B\nSố định danh: 001190000022\n</nguoi_mat>\n<quan_he>\nKết luận: Cha\n</quan_he>"
    out = reason._render_context(agent, account, docs)
    assert "001190000022" not in reason.section(out, "nguoi_mat") and "Cha" in reason.section(out, "quan_he")


def test_nguoi_mat_trung_chu_tai_khoan_thi_bo_trong():
    own = {**BASE, "NguoiMat_HoTen": "Nguyen Van B", "NguoiMat_SoDinhDanh": "001090000002", "NguoiMat_SoGiayTo": ""}
    out, warnings = _enrich(own, _context("Con"))
    by = _by(out)
    assert "citizenNDK_HoVaTen" not in by and "citizenNDK_SoDinhDanh" not in by and warnings
    assert "citizenNDK_HoVaTen" in _by(_enrich(BASE, _context("Con"))[0])
    # Tờ khai chép nhầm số của người yêu cầu sang dòng người mất: giữ họ tên, chỉ bỏ số giấy tờ.
    copied = {**BASE, "NguoiMat_SoDinhDanh": "001090000002", "NguoiMat_SoGiayTo": "001090000002"}
    by = _by(_enrich(copied, _context("Con"))[0])
    assert by["citizenNDK_HoVaTen"]["value"] == "NGUYEN VAN A" and "citizenNDK_SoDinhDanh" not in by
    assert "citizenSogiaytotuythan_NgdcKT" not in by


def test_cmnd_issuer_not_defaulted_and_copies_default_zero():
    values = {**BASE, "NguoiMat_SoDinhDanh": "", "NguoiMat_SoGiayTo": "210369831", "NguoiMat_NoiCap": ""}
    values.pop("SoLuongBanSao")
    by = _by(_enrich(values, _context("Con"))[0])
    assert by["citizenLoaiGiaytotuythan_NgdcKT"]["code"] == "2"
    assert "citizenNoicapgiaytotuythan_NgdcKT" not in by
    assert by["citizenSoluongbansaonguoiyeucaudenghi"]["value"] == "0"
    assert by["citizenSoluongbansaonguoiyeucaudenghi"]["default"]


def test_reason_parsing():
    raw = "<nguoi_mat>\nHọ tên: A\n</nguoi_mat>\n<quan_he>\nKết luận: Con\n</quan_he>\n<loai_dang_ky>\nKết luận:"
    ctx = reason._render_context(raw, {"formContext": ACCOUNT})
    assert reason.labeled_value(reason.section(ctx, "quan_he"), "Kết luận") == "Con"
    assert reason._render_context("rỗng", {}) == ""


def test_attach_rows_no_file_dropped():
    items = build_plan_items(["gbt.pdf", "uq.pdf", "bb.pdf", "nc.pdf", "cccd.pdf"],
                             {0: "death_notice", 1: "authorization", 2: "death_event_proof",
                              3: "death_place_proof", 4: "other"})
    assert [i["slotName"] for i in items] == [
        ROW_GIAY_BAO_TU["slotName"], ROWS["authorization"]["slotName"], ROWS["death_event_proof"]["slotName"],
        ROWS["death_place_proof"]["slotName"], ROW_GIAY_BAO_TU["slotName"],
    ]
    assert all(i["target"] == "fixed-slot" for i in items)


def _context_nguoi_nop(co: str):
    return _context("Con").replace("<phan_vai_da_xac_dinh>\n",
                                   f"<phan_vai_da_xac_dinh>\n<nguoi_nop>\nCó trong hồ sơ: {co}\n</nguoi_nop>\n")


def test_so_dien_thoai_nguoi_nop_co_trong_ho_so():
    out, _ = _enrich({**BASE, "NguoiNop_SoDienThoai": "0912.345.678"}, _context_nguoi_nop("Có"))
    assert _by(out)["citizenPhone"]["value"] == "0912345678"
    out, _ = _enrich({**BASE, "NguoiNop_SoDienThoai": "+84 912 345 678"}, _context_nguoi_nop("Có"))
    assert _by(out)["citizenPhone"]["value"] == "0912345678"


def test_so_dien_thoai_bo_khi_nguoi_nop_khong_co_trong_ho_so_hoac_sai_dang():
    out, _ = _enrich({**BASE, "NguoiNop_SoDienThoai": "0912345678"}, _context_nguoi_nop("Không"))
    assert "citizenPhone" not in _by(out)
    out, _ = _enrich({**BASE, "NguoiNop_SoDienThoai": "091234"}, _context_nguoi_nop("Có"))
    assert "citizenPhone" not in _by(out)


_TO_KHAI = ("TỜ KHAI ĐĂNG KÝ KHAI TỬ\nHọ, chữ đệm, tên người yêu cầu: Tran Thi C\nDân tộc: Tày\n"
            "Đề nghị cơ quan đăng ký khai tử cho người có tên dưới đây:\nHọ, chữ đệm, tên: NGUYEN VAN A\n"
            "Giới tính: (2) Nam Dân tộc: (2) Kinh Quốc tịch: (2) Việt Nam\nNơi cư trú cuối cùng: Xóm 5\n")


def test_dan_toc_llm_bo_sot_thi_doc_tu_to_khai():
    from app.pipelines.khai_tu_dvcqg.process.runner import _compact_field_fallback

    docs = [{"name": "cccd.pdf", "text": "CĂN CƯỚC CÔNG DÂN\nHọ và tên: NGUYEN VAN A"}, {"name": "tk.pdf", "text": _TO_KHAI}]
    assert _compact_field_fallback({"NguoiMat_HoTen": "NGUYEN VAN A"}, docs)["NguoiMat_DanToc"] == "Kinh"
    assert _compact_field_fallback({"NguoiMat_DanToc": "Mường"}, docs)["NguoiMat_DanToc"] == "Mường"
    trong = _TO_KHAI.replace("(2) Kinh", "......")
    assert "NguoiMat_DanToc" not in _compact_field_fallback({}, [{"name": "tk.pdf", "text": trong}])
    assert "NguoiMat_DanToc" not in _compact_field_fallback({}, docs[:1])


def test_ngay_chet_llm_chi_tra_nam_thi_lay_ngay_du_tren_giay():
    from app.pipelines.khai_tu_dvcqg.process.runner import _compact_field_fallback

    to_khai = "Đã chết vào lúc: giờ phút, ngày ...30... tháng 5.... năm 1989...\nNơi chết: thôn 3"
    xac_minh = "Ông Nguyễn Văn A chết ngày 30 tháng 5 năm 1989; gia đình chưa đăng ký khai tử."
    phieu = "Sinh : 01 - 02 - 1920\nMất : 30 - 05 - 1989"
    for text in (to_khai, xac_minh, phieu):
        assert _compact_field_fallback({"NguoiMat_NgayMat": "1989"}, [{"text": text}])["NguoiMat_NgayMat"] == "30/05/1989"
    out = _compact_field_fallback([{"name": "NguoiMat_NgayMat", "value": "05/1989"}], [{"text": to_khai}])
    assert {"name": "NguoiMat_NgayMat", "value": "30/05/1989"} in out
    # Lệch năm/tháng, hoặc các giấy ghi ngày khác nhau → giữ nguyên, không đoán.
    assert _compact_field_fallback({"NguoiMat_NgayMat": "1990"}, [{"text": to_khai}])["NguoiMat_NgayMat"] == "1990"
    assert _compact_field_fallback({"NguoiMat_NgayMat": "06/1989"}, [{"text": to_khai}])["NguoiMat_NgayMat"] == "06/1989"
    lech = [{"text": to_khai}, {"text": "Mất : 29 - 05 - 1989"}]
    assert _compact_field_fallback({"NguoiMat_NgayMat": "1989"}, lech)["NguoiMat_NgayMat"] == "1989"
    # LLM đã đọc đủ ngày thì không đụng.
    assert _compact_field_fallback({"NguoiMat_NgayMat": "29/05/1989"}, [{"text": to_khai}])["NguoiMat_NgayMat"] == "29/05/1989"


def test_dan_toc_kem_so_chu_thich_van_snap_danh_muc():
    out, _ = _enrich({**BASE, "NguoiMat_DanToc": "(2) Kinh"})
    assert _by(out)["citizenDantoc_NgdcKT"]["code"] == "01"
