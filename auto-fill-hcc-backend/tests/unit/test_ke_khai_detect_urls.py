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

    assert result[0]["detect"]["urlIncludes"] == [entry_url]
