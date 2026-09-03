from app.channels.handfree.procedure_registry import public_list


def test_public_procedure_cards_put_common_civil_status_first_and_certification_last():
    keys = [procedure["key"] for procedure in public_list()]

    assert keys[:6] == [
        "ket-hon",
        "khai-sinh-dang-ky",
        "trich-luc-ks",
        "xac-nhan-tinh-trang-hon-nhan",
        "khai-sinh-dang-ky-lai",
        "khai-tu",
    ]
    assert keys[-2:] == ["chung-thuc-ban-sao", "chung-thuc-chu-ky"]
    assert len(keys) == len(set(keys))
