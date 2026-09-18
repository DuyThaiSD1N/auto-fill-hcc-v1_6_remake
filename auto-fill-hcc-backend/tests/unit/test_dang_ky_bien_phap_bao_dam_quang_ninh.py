"""[QN] Đăng ký biện pháp bảo đảm bằng QSDĐ — định tuyến đính kèm + detect không lẫn với thủ tục XÓA."""

from app.pipelines.dang_ky_bien_phap_bao_dam_quang_ninh.attach import planner
from app.procedures.registry import public_list

_KEY = "dang-ky-bien-phap-bao-dam-quang-ninh"
_KEY_XOA = "xoa-dang-ky-bien-phap-bao-dam-quang-ninh"


def _files(names):
    return [{"name": n, "type": "application/pdf"} for n in names]


def _entry(key):
    return next(p for p in public_list() if p["key"] == key)


def test_co_trong_registry_va_la_thu_tuc_attach():
    entry = _entry(_KEY)
    assert entry["mode"] == "attach"
    assert entry["label"].startswith("[Tỉnh Quảng Ninh] Đăng ký biện pháp bảo đảm")
    assert entry["detect"]["urlScope"] == ["dichvucong.quangninh.gov.vn"]


def test_detect_khong_cuop_trang_cua_thu_tuc_xoa():
    """Tiêu đề trang XÓA chứa CẢ hai cụm; FE chọn entry có tổng độ dài cụm lớn nhất."""
    dang_ky = _entry(_KEY)["detect"]["textIncludes"]
    xoa = _entry(_KEY_XOA)["detect"]["textIncludes"]

    body_xoa = "xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất".lower()
    assert all(p.lower() in body_xoa for p in dang_ky), "cụm đăng ký vẫn khớp trang xóa (chuỗi con)"
    assert all(p.lower() in body_xoa for p in xoa)
    # → phải thắng bằng ĐỘ DÀI, nếu không trang xóa sẽ về nhầm thủ tục đăng ký.
    assert sum(len(p) for p in xoa) > sum(len(p) for p in dang_ky)

    body_dang_ky = "đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất".lower()
    assert not all(p.lower() in body_dang_ky for p in xoa), "thủ tục xóa KHÔNG được khớp trang đăng ký"


def test_sau_hang_san_tren_form_dung_text_nguyen_van():
    """componentName phải là đoạn text có thật trên trang (FE khớp substring đã fold dấu)."""
    rows = {
        1: "Giấy chứng nhận (bản gốc) trong trường hợp tài sản bảo đảm có Giấy chứng nhận.",
        2: "Phiếu yêu cầu theo Mẫu số 02a tại Phụ lục (01 bản chính).",
        4: "Văn bản chuyển giao quyền đòi nợ, chuyển giao nghĩa vụ trong trường hợp đăng ký thay đổi "
           "do chuyển giao quyền đòi nợ, chuyển giao nghĩa vụ;",
        5: "Văn bản khác chứng minh có căn cứ đăng ký thay đổi đối với trường hợp không thuộc điểm a "
           "và điểm b khoản 2 Điều 32 Nghị định số 99/2022/NĐ-CP.",
        6: "Văn bản sửa đổi, bổ sung hợp đồng bảo đảm trong trường hợp đăng ký thay đổi theo thỏa "
           "thuận trong văn bản này;",
    }
    for doc_type, route in planner._ROUTES.items():
        assert route["name"] in rows[route["index"]], doc_type
    # Hàng 3 là ĐIỀU KIỆN, không phải giấy tờ → không được route vào.
    assert 3 not in {r["index"] for r in planner._ROUTES.values()}


def test_hop_dong_the_chap_va_uy_quyen_them_thanh_phan_moi():
    """Form không có dòng cho hợp đồng thế chấp gốc (6 dòng đều nói về đăng ký THAY ĐỔI)."""
    items, _, _ = planner.build_plan_items(
        _files(["hd.pdf", "uq.pdf"]), [], {0: "hop_dong_the_chap", 1: "van_ban_dai_dien"}
    )

    assert all(i["target"] == "new" and i["needsAddComponent"] for i in items)
    assert items[0]["componentName"] == "Hợp đồng thế chấp quyền sử dụng đất, tài sản gắn liền với đất"
    assert items[1]["componentName"] == "Văn bản đại diện hoặc ủy quyền"


def test_cac_loai_co_hang_san_vao_dung_hang():
    items, _, _ = planner.build_plan_items(
        _files(["gcn.pdf", "phieu.pdf", "khac.pdf"]),
        [],
        {0: "gcn", 1: "phieu_yeu_cau", 2: "van_ban_khac_can_cu"},
    )

    assert [i["componentIndex"] for i in items] == [1, 2, 5]
    assert all(i["target"] == "existing" and i["loaiBan"] == "Bản chính" for i in items)


def test_khong_bo_sot_file_nao():
    names = ["a.pdf", "b.pdf", "c.pdf"]
    items, warnings, classified = planner.build_plan_items(_files(names), [], {0: "gcn"})

    assert [i["fileIndex"] for i in items] == [0, 1, 2]
    # File chưa rõ loại → thêm thành phần mới đặt tên theo tệp, có cảnh báo.
    la = [i for i in items if i["detectedType"] == "other"]
    assert len(la) == 2 and all(i["target"] == "new" for i in la)
    assert any("không bỏ sót" in w for w in warnings)
    assert not any(c.get("skipped") for c in classified)


def test_llm_chet_van_dinh_du_file():
    items, warnings, _ = planner.build_plan_items(_files(["x.pdf", "y.pdf"]), [], {})

    assert len(items) == 2
    assert all(i["target"] == "new" for i in items)
    assert warnings


def test_thuan_llm_khong_doc_ocr_de_doan():
    import inspect

    src = inspect.getsource(planner.build_plan_items)
    assert "del ocr_results" in src
    for name in ("_label_by_keywords", "_label_by_filename", "_rule_doc_type"):
        assert not hasattr(planner, name), name


def test_prompt_co_bay_gcn_va_phan_biet_hop_dong():
    from app.pipelines.dang_ky_bien_phap_bao_dam_quang_ninh.attach.prompt import SYSTEM_PROMPT

    assert "hop_dong_the_chap" in SYSTEM_PROMPT
    assert "NHẮC TỚI số Giấy chứng nhận" in SYSTEM_PROMPT
    assert "KHÔNG BỊA" in SYSTEM_PROMPT or "Không đủ bằng chứng" in SYSTEM_PROMPT
    assert "Lời chứng thực/công chứng ở trang cuối KHÔNG quyết định loại" in SYSTEM_PROMPT
