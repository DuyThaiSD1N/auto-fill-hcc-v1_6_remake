from app.pipelines._shared.locked_submitter import unlock_locked_submitter


def test_o_da_phat_duoc_gan_co_mo_khoa():
    fields = [{"name": "data[fullname]", "comp": "dom-input", "value": "A"},
              {"name": "data[identityNumber]", "comp": "dom-input", "value": "1"}]
    unlock_locked_submitter(fields)
    assert len(fields) == 2
    assert all(f["enableInput"] is True for f in fields)


def test_o_khong_phat_thi_chi_mo_khoa_khong_ghi_de():
    fields = [{"name": "data[address]", "comp": "dom-input", "value": "x"}]
    unlock_locked_submitter(fields)
    added = {f["name"]: f for f in fields[1:]}
    assert set(added) == {"data[fullname]", "data[identityNumber]"}
    for f in added.values():
        assert f["comp"] == "dom-expect" and f["value"] == "" and f["enableInput"] is True


def test_form_khong_phai_formio_khong_dung():
    fields = [{"name": "CongDan_HoTen", "comp": "dom-input", "value": "x"}]
    unlock_locked_submitter(fields)
    assert fields == [{"name": "CongDan_HoTen", "comp": "dom-input", "value": "x"}]
    assert unlock_locked_submitter([]) == []
    assert unlock_locked_submitter(None) is None
