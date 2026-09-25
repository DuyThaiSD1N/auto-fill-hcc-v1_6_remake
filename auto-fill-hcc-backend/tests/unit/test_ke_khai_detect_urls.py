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

    assert result[0]["detect"]["urlIncludes"] == [
        entry_url,
        "matthc=2.000815",
        "madvc=2.000815.",
    ]


def test_mae_agency_select_page_is_detected_by_matthc():
    # Trang "Chọn cơ quan thực hiện" của cổng NNMT chỉ có mã TTHC trên URL.
    url = (
        "https://dichvucongnnmt.mae.gov.vn/vi/nps/apply?CapThucHien=1,2&MaTTHC=1.003650"
        "&MaCoQuanThucHien=H05.34&MaDVC=1.003650.01&MaTTHCDP=1.003650&vneid=1"
    ).lower()
    procedures = [{"key": "cap-gcn-dang-ky-tau-ca", "detect": {"urlIncludes": []}}]

    result = with_ke_khai_detect_urls(procedures)

    assert any(part in url for part in result[0]["detect"]["urlIncludes"])
