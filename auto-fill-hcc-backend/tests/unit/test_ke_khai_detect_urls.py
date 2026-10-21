from app.procedures.ke_khai_links import with_ke_khai_detect_urls


def test_ke_khai_url_is_added_to_detect_without_mutating_registry_config():
    original_detect = {"urlIncludes": ["maThuTuc=2.000815"]}
    procedures = [
        {
            "key": "chung-thuc-ban-sao",
            "label": "Chứng thực bản sao từ bản chính giấy tờ, văn bản",
            "detect": original_detect,
        }
    ]

    result = with_ke_khai_detect_urls(procedures)

    assert result[0]["detect"]["urlIncludes"] == [
        "maThuTuc=2.000815",
        "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e22-77ef-819f-e49460350904",
        "matthc=2.000815",
        "madvc=2.000815.",
    ]
    assert original_detect == {"urlIncludes": ["maThuTuc=2.000815"]}
    assert result[0] is not procedures[0]


def test_ke_khai_url_is_not_duplicated():
    entry_url = (
        "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/"
        "019d2bfd-8e22-77ef-819f-e49460350904"
    )
    procedures = [
        {
            "key": "chung-thuc-ban-sao",
            "detect": {"urlIncludes": [entry_url]},
        }
    ]

    result = with_ke_khai_detect_urls(procedures)

    assert result[0]["detect"]["urlIncludes"] == [entry_url, "matthc=2.000815", "madvc=2.000815."]


def test_province_only_from_label_prefix_and_url_scope():
    from app.procedures.ke_khai_links import link_province_slugs, procedure_province_slugs

    assert procedure_province_slugs({"label": "[Tỉnh Bắc Ninh] Tách thửa"}) == ["bacninh"]
    assert procedure_province_slugs({"label": "(Lào Cai - Cấp phường/xã) Tách thửa"}) == ["laocai"]
    assert procedure_province_slugs({"label": "[Tỉnh Lào Cai - Cấp Sở] Xóa đăng ký"}) == ["laocai"]
    assert procedure_province_slugs(
        {"label": "Tách thửa", "detect": {"urlScope": ["dichvucong.quangninh.gov.vn"]}}
    ) == ["quangninh"]
    # Cổng bộ ngành / cổng quốc gia không phải tỉnh; gạch nối giữa tên không phải tiền tố tỉnh.
    assert procedure_province_slugs(
        {"label": "Thẩm định BCNCKT", "detect": {"urlScope": ["dvc.moc.gov.vn", "://dichvucong.gov.vn/nop-ho-so"]}}
    ) == []
    assert procedure_province_slugs({"label": "Cấp lại giấy do ngành Lao động - Thương binh quản lý"}) == []
    # Khai tay provinceOnly như registry trợ lý thì dùng đúng danh sách đó.
    assert procedure_province_slugs({"label": "[Đà Nẵng] X", "provinceOnly": ["danang", "bacninh"]}) == [
        "bacninh", "danang",
    ]
    # Link không ghi tỉnh vẫn ăn tỉnh của thủ tục lõi cùng key.
    core = {"k": {"key": "k", "label": "[Lai Châu] Đính chính"}}
    assert link_province_slugs({"key": "k", "label": "Đính chính"}, core) == ["laichau"]


def test_visible_in_province_keeps_shared_and_own_province_only():
    from app.procedures.ke_khai_links import visible_in_province

    items = [{"key": "chung"}, {"key": "bn", "provinceOnly": ["bacninh"]}, {"key": "qn", "provinceOnly": ["quangninh"]}]

    assert [i["key"] for i in visible_in_province(items, "bacninh")] == ["chung", "bn"]
    # Tài khoản chưa gán tỉnh: không lọc, giống is_allowed_in_province bên trợ lý.
    assert [i["key"] for i in visible_in_province(items, "")] == ["chung", "bn", "qn"]


def test_procedure_endpoints_filter_by_account_province():
    import asyncio

    from app.procedures.router import ke_khai_links, procedures

    bac_ninh = {"tinh": "Tỉnh Bắc Ninh"}  # tài khoản cũ còn ghi "Tỉnh" vẫn ra đúng tỉnh
    core = {p["key"]: p for p in asyncio.run(procedures(bac_ninh))["procedures"]}
    assert "chung-thuc-ban-sao" in core
    assert "dinh-chinh-sai-sot-bac-ninh" in core
    assert core["dinh-chinh-sai-sot-bac-ninh"]["provinceOnly"] == ["bacninh"]
    assert "dang-ky-bien-dong-dat-dai-da-nang" not in core
    assert "cap-doi-gcn-quang-ninh-mien-nui-hai-dao" not in core
    # Pipeline cổng Bộ Xây dựng dùng chung, dù link kê khai ghi Ninh Bình.
    assert "tham-dinh-bcnckt" in core

    links = {l["key"] for l in asyncio.run(ke_khai_links(bac_ninh))["links"]}
    assert {"chung-thuc-ban-sao", "ho-tro-chi-phi-hoa-tang-bac-ninh"} <= links
    assert "tach-thua-hop-thua-dat-quang-ninh" not in links
    assert "tham-dinh-bcnckt" not in links

    quang_ninh_links = {l["key"] for l in asyncio.run(ke_khai_links({"tinh": "Tỉnh Quảng Ninh"}))["links"]}
    assert "tach-thua-hop-thua-dat-quang-ninh" in quang_ninh_links
    assert "ho-tro-chi-phi-hoa-tang-bac-ninh" not in quang_ninh_links

    # Chưa đăng nhập (extension bản cũ gọi trơn) vẫn ra đủ danh mục.
    assert len(asyncio.run(ke_khai_links(None))["links"]) > len(links)
