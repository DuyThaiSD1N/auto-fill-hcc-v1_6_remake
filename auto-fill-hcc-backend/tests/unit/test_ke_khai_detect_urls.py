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

    assert result[0]["detect"]["urlIncludes"].count(entry_url) == 1


def test_ma_tthc_da_co_khong_bi_them_trung_du_khac_hoa_thuong():
    procedures = [
        {
            "key": "cap-gcn-diem-tro-choi-dien-tu-cong-cong",
            "detect": {"urlIncludes": ["MaTTHC=1.013792"]},
        }
    ]

    url_includes = with_ke_khai_detect_urls(procedures)[0]["detect"]["urlIncludes"]

    assert [u.lower() for u in url_includes].count("matthc=1.013792") == 1


def _detect_by_url(procedures, url):
    """Mô phỏng bước 1 của popup.js detectProcedureKeyFromSignals: urlScope rồi urlIncludes."""
    url = url.lower()
    for p in procedures:
        detect = p.get("detect") or {}
        if p.get("detectDisabled"):
            continue
        scope = detect.get("urlScope") or []
        if scope and not any(s.lower() in url for s in scope):
            continue
        if any(u and u.lower() in url for u in detect.get("urlIncludes") or []):
            return p["key"]
    return ""


def test_buoc_chon_quy_trinh_cong_bo_xay_dung_nhan_dien_theo_ma_tthc():
    from app.procedures.registry import public_list

    procedures = with_ke_khai_detect_urls(public_list())
    url = (
        "https://dvc.moc.gov.vn/vi/nps/apply?MaTTHC=1.013229&MaCoQuanThucHien=H26.170"
        "&MaDVC=1.013229.01&MaTTHCDP=1.013229&vneid=1"
    )

    assert _detect_by_url(procedures, url) == "sua-chua-cai-tao-gpxd-cong-trinh"


def test_ma_tthc_dung_chung_giua_cac_tinh_van_bi_urlscope_chan():
    from app.procedures.registry import public_list

    procedures = with_ke_khai_detect_urls(public_list())
    url = "https://dichvucong.danang.gov.vn/nop-ho-so?MaTTHC=1.011443"

    assert _detect_by_url(procedures, url) == "xoa-dang-ky-bien-phap-bao-dam-da-nang"
