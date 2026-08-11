from scripts.export_thong_ke_bac_ninh import OUT_MAC_DINH, XA_MAC_DINH, _parse_args


def test_mac_dinh_xuat_bac_ninh_co_song_lieu():
    args = _parse_args([])

    assert XA_MAC_DINH == ["Song Liễu"]
    assert args.xa is None
    assert args.out == OUT_MAC_DINH == "thong_ke_bac_ninh.xlsx"


def test_co_the_chon_nhieu_xa_va_moc_ket_thuc():
    args = _parse_args(
        ["--xa", "Song Liễu", "--xa", "Thuận Thành", "--den", "11/08/2026 17:00"]
    )

    assert args.xa == ["Song Liễu", "Thuận Thành"]
    assert args.den == "11/08/2026 17:00"
