from app.pipelines._shared.ethnic_normalize import ethnicity_for_form
from app.pipelines.khai_sinh_lien_thong.process.mapper import _ethnicity_for_form as khai_sinh_ethnicity


def test_cao_lan_goes_to_other_instead_of_san_chay():
    assert ethnicity_for_form("Cao Lan") == ("Khác", "Cao Lan")
    assert ethnicity_for_form(" cao lan ") == ("Khác", "cao lan")
    assert khai_sinh_ethnicity("Cao Lan") == ("Khác", "Cao Lan")


def test_cill_and_standard_names_unchanged():
    assert ethnicity_for_form("Cill") == ("Khác", "Cill")
    assert ethnicity_for_form("Sán Chay") == ("Sán Chay", "")
    assert ethnicity_for_form("Kinh") == ("Kinh", "")
