"""Mapper tests for Thi tuyển công chức."""

from app.pipelines._shared.compact_agent import prompt as compact_prompt
from app.pipelines.thi_tuyen_cong_chuc import process as agent
from app.pipelines.thi_tuyen_cong_chuc.process import mapper
from app.pipelines.thi_tuyen_cong_chuc.process.prompt import EXTRA_RULES
from app.pipelines.thi_tuyen_cong_chuc.process.schema import FIELDS
from app.process.schemas import FieldOut
from app.procedures.registry import get_attach_pipeline, get_pipeline, get_procedure


def _field(name, value):
    return {"name": name, "comp": "x-input", "value": value}


def _values(mapped: list[dict]) -> dict:
    return {f["name"]: f["value"] for f in mapped}


def _sample_fields() -> list[dict]:
    return [
        _field("Phieu_ViTriViecLam", "Chuyên viên lĩnh vực tài chính: Quản lý tài chính – ngân sách nhà nước"),
        _field("Phieu_CoQuanDuTuyen", "Phòng kinh tế xã Nậm Cuổi"),
        _field("Phieu_HoTen", "Vàng Thị Thu"),
        _field("Phieu_NgaySinh", "23/07/1994"),
        _field("Phieu_GioiTinh", "Nữ"),
        _field("Phieu_SoDinhDanh", "012194003716"),
        _field("Phieu_NgayCap", "17/06/2021"),
        _field("Phieu_NoiCap", "Công an tỉnh Hưng Yên"),
        _field("Phieu_TonGiao", "Không"),
        _field("Phieu_DanToc", "Thái"),
        _field("Phieu_DienThoai", "0963831658"),
        _field("Phieu_Email", "thu2307neu@gmail.com"),
        _field("Phieu_QueQuan", {"quocGia": "Việt Nam", "tinh": "Tỉnh Lai Châu", "xa": "Xã Sìn Hồ", "diaChi": "Nậm Mạ"}),
        _field("Phieu_NoiThuongTru", {"quocGia": "Việt Nam", "tinh": "Tỉnh Hưng Yên", "xa": "Xã Hưng Hà", "diaChi": "Thôn Đồng Hàn"}),
        _field("Phieu_NoiOHienTai", {"quocGia": "Việt Nam", "tinh": "Thành phố Hà Nội", "xa": "Phường Láng", "diaChi": ""}),
        _field("Phieu_TinhTrangSucKhoe", "Tốt"),
        _field("Phieu_ChieuCao", "161 cm"),
        _field("Phieu_CanNang", "53 kg"),
        _field("Phieu_TrinhDoVanHoa", "12/12"),
        _field("Phieu_TrinhDoChuyenMon", "Đại học"),
        _field(
            "Phieu_VanBangChungChi",
            [
                {
                    "tenTruong": "ĐH Kinh tế Quốc dân",
                    "ngayCap": "29/03/2018",
                    "trinhDo": "Cử nhân",
                    "soHieu": "0700-MT56",
                    "chuyenNganh": "Kinh tế - Quản lý tài nguyên và môi trường",
                    "nganh": "Kinh tế",
                    "hinhThuc": "Chính quy",
                    "xepLoai": "Khá",
                },
                {
                    "tenTruong": "ĐH Tài nguyên và Môi trường Hà Nội",
                    "ngayCap": "30/06/2020",
                    "trinhDo": "Cử nhân",
                    "soHieu": "TNMT-2020",
                    "chuyenNganh": "Quản lý đất đai",
                    "nganh": "Quản lý đất đai",
                    "hinhThuc": "Chính quy",
                    "xepLoai": "Giỏi",
                },
            ],
        ),
        _field("Phieu_CoDoiTuongUuTien", "Có"),
        _field("Phieu_DoiTuongUuTien", "Là người dân tộc thiểu số, sinh viên cử tuyển"),
        _field("Phieu_DiemUuTien", "5 điểm"),
        _field("Phieu_ThuTuUuTien", [{"tenCoQuan": "Phòng kinh tế xã Nậm Cuổi", "nguyenVong": "Nguyện vọng 1"}]),
    ]


def test_thi_tuyen_cong_chuc_registered():
    key = "thi-tuyen-cong-chuc"
    proc = get_procedure(key)

    assert proc
    assert proc["label"] == "Thi tuyển công chức"
    assert proc["mode"] == "agent"
    assert proc["hasAttachmentStep"] is True
    assert get_pipeline(key) is agent.run
    assert get_attach_pipeline(key)


def test_thi_tuyen_cong_chuc_maps_full_sample():
    out, warnings = mapper.enrich(
        _sample_fields(),
        {"formContext": {"applicantFullname": "Vàng Thị Thu", "applicantIdentityNumber": "012194003716"}},
    )
    d = _values(out)

    assert warnings == []
    assert d["data[chonDoiTuong]"] == "Cá nhân"
    assert d["data[fullname]"] == "Vàng Thị Thu"
    assert d["data[birthday]"] == "23/07/1994"
    assert d["data[gender]"] == "Nữ"
    assert d["data[identityNumber]"] == "012194003716"
    assert d["data[identityDate]"] == "17/06/2021"
    assert d["data[idIssuePlace]"] == "Công an tỉnh Hưng Yên"
    assert "data[chonDoiTuong1]" not in d
    applicant_province = [f for f in out if f["name"] == "data[province]" and f.get("occurrence") == 0][0]
    applicant_district = [f for f in out if f["name"] == "data[district]" and f.get("occurrence") == 0][0]
    applicant_address = [f for f in out if f["name"] == "data[address]" and f.get("occurrence") == 0][0]
    assert applicant_province["value"] == "Tỉnh Hưng Yên"
    assert applicant_district["value"] == "Xã Hưng Hà"
    assert applicant_address["value"] == "Thôn Đồng Hàn"
    assert d["data[phoneNumber]"] == "0963831658"
    assert d["data[email]"] == "thu2307neu@gmail.com"
    assert d["data[isOwnerDossierCheck]"] is True
    assert d["data[ownerFullname]"] == "Vàng Thị Thu"
    assert d["data[ownerIdentityNumber]"] == "012194003716"
    assert d["data[ownerNation]"] == "Việt Nam"
    assert d["data[hoSoDinhKem][0][textField1]"] == "Phiếu đăng ký dự tuyển (Mẫu 01, NĐ 170/2025/NĐ-CP)"
    assert d["data[hoSoDinhKem][0][textField2]"] == "Bản chính"
    assert d["data[VtVlDt]"] == "Chuyên viên lĩnh vực tài chính: Quản lý tài chính – ngân sách nhà nước"
    assert d["data[CqTcDt]"] == "Phòng kinh tế xã Nậm Cuổi"
    assert [f for f in out if f["name"] == "data[fullname]" and f.get("occurrence") == 1][0]["value"] == "Vàng Thị Thu"
    assert d["data[identityAgency]"] == "Công an tỉnh Hưng Yên"
    assert d["data[TonGiao]"] == "Không"
    assert d["data[DanToc]"] == "Thái"
    assert d["data[province1]"] == "Tỉnh Lai Châu"
    assert d["data[district1]"] == "Xã Sìn Hồ"
    assert d["data[address1]"] == "Nậm Mạ"
    assert d["data[province2]"] == "Tỉnh Hưng Yên"
    assert d["data[district2]"] == "Xã Hưng Hà"
    assert d["data[address2]"] == "Thôn Đồng Hàn"
    current_province = [f for f in out if f["name"] == "data[province]" and f.get("occurrence") == 1][0]
    assert current_province["value"] == "Thành phố Hà Nội"
    assert d["data[village]"] == "Phường Láng"
    assert d["data[TtSk]"] == "Tốt"
    assert d["data[ChieuCao]"] == "161"
    assert d["data[CanNang]"] == "53"
    assert d["data[DataGrid][0][TenTruong]"] == "ĐH Kinh tế Quốc dân"
    assert d["data[DataGrid][0][NgayCap1]"] == "29/03/2018"
    assert d["data[DataGrid][0][XhVbCc]"] == "Khá"
    assert d["data[DataGrid][1][TenTruong]"] == "ĐH Tài nguyên và Môi trường Hà Nội"
    assert d["data[DataGrid][1][XhVbCc]"] == "Giỏi"
    assert d["data[CoKhong]"] == "Có"
    assert d["data[DtUt]"] == "Là người dân tộc thiểu số, sinh viên cử tuyển"
    assert d["data[Dut]"] == "5"
    assert d["data[XacNhan]"] is True
    assert d["data[DataGrid2][0][txtDonViNV]"] == "Phòng kinh tế xã Nậm Cuổi"
    assert d["data[DataGrid2][0][txtNguyenVong]"] == "Nguyện vọng 1"


def test_thi_tuyen_cong_chuc_does_not_overwrite_mismatched_requester():
    out, warnings = mapper.enrich(
        _sample_fields(),
        {"formContext": {"applicantFullname": "Nguyễn Văn Khác", "applicantIdentityNumber": "012345678901"}},
    )
    d = _values(out)

    assert warnings == []
    assert d["data[isOwnerDossierCheck]"] is False
    assert d["data[chonDoiTuong1]"] == "Cá nhân"
    assert not [f for f in out if f["name"] == "data[fullname]" and f.get("occurrence") == 0]
    assert not [f for f in out if f["name"] == "data[identityNumber]" and f.get("occurrence") == 0]
    assert d["data[ownerFullname]"] == "Vàng Thị Thu"
    assert [f for f in out if f["name"] == "data[fullname]" and f.get("occurrence") == 1][0]["value"] == "Vàng Thị Thu"


def test_thi_tuyen_cong_chuc_prompt_requires_long_schema():
    system_prompt = compact_prompt.build_system_prompt(FIELDS, EXTRA_RULES)

    assert "Không dùng schema ngắn của xét tuyển viên chức" in system_prompt
    assert "Mẫu số 01 hoặc Mẫu số 02" in system_prompt
    assert "PHIẾU ĐĂNG KÝ THI TUYỂN CÔNG CHỨC" in system_prompt
    assert "Phieu_VanBangChungChi là mảng tất cả dòng" in system_prompt
    assert "Nếu địa chỉ chỉ có 2 phần và phần đầu là xã/phường/thị trấn" in system_prompt
    assert "Không lấy đoạn cam đoan pháp lý mặc định" in system_prompt
    assert "Nghị định số 170/2025" in system_prompt


def test_thi_tuyen_cong_chuc_occurrence_survives_response_model_dump():
    field = FieldOut(name="data[province]", comp="dom-select", value="Tỉnh Hưng Yên", occurrence=0)

    assert field.model_dump()["occurrence"] == 0
