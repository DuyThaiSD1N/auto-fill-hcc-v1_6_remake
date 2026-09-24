from app.pipelines.cap_moi_giay_phep_hanh_nghe_chuyen_tiep.process import mapper


def _fields(**values):
    return [{"name": k, "value": v} for k, v in values.items()]


def _names(out):
    return {f["name"]: f["value"] for f in out}


def test_tu_nop_khong_dien_de_o_vneid_da_do_san():
    fields = _fields(
        NguoiHanhNghe_HoTen="NGUYEN VAN AN",
        NguoiHanhNghe_SoDinhDanh="001200000001",
        NguoiHanhNghe_NgaySinh="01/02/2000",
        NguoiHanhNghe_DienThoai="0901234567",
    )
    ctx = {"applicantFullname": "NGUYỄN VĂN AN", "applicantIdentityNumber": "001200000001"}
    out = _names(mapper.enrich(fields, {"formContext": ctx})[0])
    assert "data[fullname]" not in out
    assert "data[identityNumber]" not in out
    assert out["data[birthday]"] == "01/02/2000"
    assert out["data[phoneNumber]"] == "0901234567"


def test_khong_co_vneid_van_dien_ho_ten_cccd():
    fields = _fields(NguoiHanhNghe_HoTen="NGUYEN VAN AN", NguoiHanhNghe_SoDinhDanh="001200000001")
    out = _names(mapper.enrich(fields, {})[0])
    assert out["data[fullname]"] == "NGUYEN VAN AN"
    assert out["data[identityNumber]"] == "001200000001"


def test_nop_thay_giu_o_vneid_va_dien_chu_ho_so():
    fields = _fields(NguoiHanhNghe_HoTen="TRAN THI BINH", NguoiHanhNghe_SoDinhDanh="002300000002")
    ctx = {"applicantFullname": "LE VAN CUONG", "applicantIdentityNumber": "003400000003"}
    out = _names(mapper.enrich(fields, {"formContext": ctx})[0])
    assert "data[fullname]" not in out
    assert "data[identityNumber]" not in out
    assert out["data[isOwnerDossierCheck]"] is False
    assert out["data[ownerFullname]"] == "TRAN THI BINH"
    assert out["data[ownerIdentityNumber]"] == "002300000002"
