import pytest

from app.channels.handfree.flow_profiles import resolve_flow_profile
from app.channels.handfree.procedure_registry import (
    get_attach_pipeline,
    get_owner_info_pipeline,
    get_pipeline,
    public_list,
)
from app.procedures import registry as core_registry


def test_tu_phap_profile_materializes_owner_wizard_without_mutating_raw_entry():
    raw = {"key": "thu-tuc-moi", "flowProfile": "tu-phap", "mode": "agent"}

    resolved = resolve_flow_profile(raw)

    assert "ownerInfo" not in raw and "wizard" not in raw
    assert resolved["needsAgencySelect"] is True
    assert resolved["hasAttachmentStep"] is True
    assert resolved["wizard"] == {
        "ownerStep": 1,
        "declarationStep": 2,
        "attachmentStep": 3,
        "resultStep": 4,
    }
    fields = resolved["ownerInfo"]["fields"]
    assert fields["Owner_PhoneNumber"]["name"] == "soDienThoai"
    assert fields["Owner_DetailedAddress"]["name"] == "diaChiThuongTru"
    assert resolved["executionSubject"] == {
        "enabled": True,
        "default": "self",
        "options": [
            {
                "key": "self",
                "label": "Làm thủ tục cho bản thân",
                    "shortLabel": "cho bản thân",
                "portalValue": "null",
            },
            {
                "key": "authorized_person",
                "label": "Người khác ủy quyền",
                    "shortLabel": "do người khác ủy quyền",
                "portalValue": "canhan",
            },
            {
                "key": "enterprise_authorized",
                "label": "Doanh nghiệp ủy quyền",
                    "shortLabel": "do doanh nghiệp ủy quyền",
                "portalValue": "",
            },
            {
                "key": "other_person",
                "label": "Làm thủ tục cho người khác",
                    "shortLabel": "cho người khác",
                "portalValue": "",
            },
            {
                "key": "organization_representative",
                "label": "Đại diện cơ quan, tổ chức",
                    "shortLabel": "với tư cách đại diện cơ quan, tổ chức",
                "portalValue": "",
            },
        ],
    }
    authorization = resolved["authorizationInfo"]
    assert authorization["activeWhen"] == {"executionSubject": "authorized_person"}
    assert authorization["sectionLabel"] == "Thông tin ủy quyền cá nhân"
    assert authorization["fields"]["Authorization_GrantorFullName"]["name"] == "hoTen"
    assert authorization["fields"]["Authorization_GrantorDateOfBirth"]["comp"] == "owner-date"


def test_tu_phap_profile_allows_narrow_procedure_override():
    resolved = resolve_flow_profile({
        "key": "thu-tuc-khac-control",
        "flowProfile": "tu-phap",
        "ownerInfo": {
            "fields": {
                "Owner_PhoneNumber": {"name": "phoneNumber"},
            },
        },
    })

    phone = resolved["ownerInfo"]["fields"]["Owner_PhoneNumber"]
    assert phone["name"] == "phoneNumber"
    assert phone["key"] == "phoneNumber" and phone["comp"] == "owner-input"
    assert resolved["ownerInfo"]["fields"]["Owner_IssueDate"]["comp"] == "owner-date"


def test_unknown_flow_profile_fails_fast():
    with pytest.raises(ValueError, match="flowProfile không tồn tại"):
        resolve_flow_profile({"key": "sai-profile", "flowProfile": "khong-co"})


def test_tu_phap_profile_rejects_invalid_execution_subject_default():
    with pytest.raises(ValueError, match="executionSubject không hợp lệ"):
        resolve_flow_profile({
            "key": "sai-doi-tuong",
            "flowProfile": "tu-phap",
            "executionSubject": {"default": "khong-ton-tai"},
        })


def test_tu_phap_profile_rejects_authorization_subject_outside_declared_options():
    with pytest.raises(ValueError, match="authorizationInfo không hợp lệ"):
        resolve_flow_profile({
            "key": "sai-nhanh-uy-quyen",
            "flowProfile": "tu-phap",
            "authorizationInfo": {
                "activeWhen": {"executionSubject": "doanhnghiep"},
            },
        })


def test_registered_procedures_use_their_declared_flow_family():
    procedures = {procedure["key"]: procedure for procedure in public_list()}

    linked_birth = procedures.pop("khai-sinh-dang-ky")
    assert linked_birth.get("flowProfile") is None
    # Liên thông khai tử: cùng cổng lienthong (Angular) với liên thông khai sinh, nhận theo URL.
    linked_death = procedures.pop("khai-tu-lien-thong")
    assert linked_death.get("flowProfile") is None
    assert linked_death["detect"]["urlIncludes"] == ["lienthong.dichvucong.gov.vn/#/ke-khai/1.006714"]
    business = procedures.pop("dang-ky-kinh-doanh")
    assert business.get("flowProfile") is None
    assert business["businessWorkflow"] == "create"
    assert len(business["pages"]) == 8
    # Cổng Bộ NN&MT: không dùng profile tư pháp — wizard riêng (kê khai 1, đính kèm 2)
    # + luồng chọn cơ quan 2 tầng (DVCQG chỉ tỉnh → trang MAE chọn Sở + trường hợp).
    mae_fishing = procedures.pop("cap-giay-phep-khai-thac-thuy-san")
    assert mae_fishing.get("flowProfile") is None
    assert mae_fishing["agencyProvinceOnly"] is True
    assert mae_fishing["maePortal"] is True
    assert mae_fishing["wizard"]["declarationStep"] == 1
    assert mae_fishing["wizard"]["attachmentStep"] == 2
    # Bộ GD&ĐT: cùng nền iGate (wizard 1/2) nhưng KHÔNG có trang chọn nơi/loại;
    # DVCQG chọn Tỉnh + toggle "Sở" rồi lấy Sở đầu tiên (agencySoFirst).
    moet_diploma = procedures.pop("cap-ban-sao-van-bang-so-goc")
    assert moet_diploma.get("flowProfile") is None
    assert moet_diploma["agencyProvinceOnly"] is True
    assert moet_diploma["agencySoFirst"] is True
    assert "maePortal" not in moet_diploma
    assert moet_diploma["wizard"]["declarationStep"] == 1
    assert moet_diploma["wizard"]["attachmentStep"] == 2
    # Bộ Xây dựng (NOXH): cùng khuôn agencySoFirst + wizard iGate như văn bằng, nay đi luồng chung
    # "xay-dung" (hộp thoại "Chọn trường hợp giải quyết" đọc từ cổng).
    moc_housing = procedures.pop("cho-thue-thue-mua-nha-o-xa-hoi")
    assert moc_housing["flowProfile"] == "xay-dung"
    assert moc_housing["agencyProvinceOnly"] is True
    assert moc_housing["agencySoFirst"] is True
    assert moc_housing["maePortal"] is True
    assert moc_housing["wizard"]["declarationStep"] == 1
    assert moc_housing["wizard"]["attachmentStep"] == 2
    # Bộ Y tế (trợ cấp hưu trí xã hội): CÙNG wizard iGate 1 kê khai / 2 đính kèm, nhưng bước
    # chọn cơ quan lại giống tư pháp — DVCQG chọn ĐỦ Tỉnh + Xã rồi vào thẳng trang kê khai,
    # KHÔNG gạt toggle "Sở". Đây là điểm phân biệt với ba cổng bộ ở trên.
    # Bộ Xây dựng (cấp phép xây dựng mới): cũng wizard iGate 1/2 + chọn cơ quan Tỉnh+Xã, nhưng
    # cổng còn chèn HỘP THOẠI "Chọn trường hợp giải quyết" → maePortal + variants. Trợ lý hỏi
    # trường hợp ngay tại hộp thoại đó, nên variants phải có ít nhất 2 option kèm token khớp.
    moc_permit = procedures.pop("cap-giay-phep-xay-dung-moi-nha-o-rieng-le")
    assert moc_permit["flowProfile"] == "xay-dung"
    assert moc_permit["needsAgencySelect"] is True
    assert moc_permit["maePortal"] is True
    assert "agencyProvinceOnly" not in moc_permit
    assert "agencySoFirst" not in moc_permit
    assert moc_permit["wizard"]["declarationStep"] == 1
    assert moc_permit["wizard"]["attachmentStep"] == 2
    variant_options = moc_permit["variants"]["options"]
    assert [o["key"] for o in variant_options] == ["nha_o_rieng_le", "cong_trinh"]
    assert all(o.get("label") and o.get("portalMatch") for o in variant_options)

    # Các thủ tục khác của cổng Bộ Xây dựng: cùng luồng chung "xay-dung", cùng hộp thoại.
    for key in ("dieu-chinh-giay-phep-xay-dung", "sua-chua-cai-tao-gpxd-nha-o-rieng-le",
                "cung-cap-thong-tin-quy-hoach", "cap-phep-long-duong-via-he",
                "cap-giay-phep-lien-van-viet-lao"):
        moc_other = procedures.pop(key)
        assert moc_other["flowProfile"] == "xay-dung", key
        assert moc_other["maePortal"] is True, key
        assert moc_other["maeDialogChoice"]["enabled"] is True, key

    byt_pension = procedures.pop("dieu-chinh-huu-tri-xa-hoi")
    assert byt_pension.get("flowProfile") is None
    assert byt_pension["needsAgencySelect"] is True
    assert "agencyProvinceOnly" not in byt_pension
    assert "agencySoFirst" not in byt_pension
    assert "maePortal" not in byt_pension
    assert byt_pension["wizard"]["declarationStep"] == 1
    assert byt_pension["wizard"]["attachmentStep"] == 2
    # ATTP Bộ Y tế: cùng khung với hưu trí, chỉ khác phải bấm ĐÚNG thẻ UBND ở trang kết quả DVCQG
    # (chi tiết ở test_agency_card_dvcqg.py).
    byt_food_safety = procedures.pop("cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham")
    assert byt_food_safety.get("flowProfile") is None
    assert byt_food_safety["wizard"] == byt_pension["wizard"]
    assert byt_food_safety["agencyCardIncludes"] == "Cơ quan thực hiện: UBND"
    assert byt_food_safety["hideRepeatableHint"] is True
    assert len(byt_food_safety["shortLabel"]) >= 30
    # Trợ cấp xã hội hàng tháng: cùng cổng Bộ Y tế, cùng cách chọn cơ quan với hưu trí, nhưng bảng
    # thành phần hồ sơ là bảng NHIỀU DÒNG tích chọn → không được dồn hết tệp vào một dòng.
    byt_allowance = procedures.pop("tro-cap-xa-hoi-hang-thang")
    assert byt_allowance.get("flowProfile") is None
    assert byt_allowance["needsAgencySelect"] is True
    assert "agencyProvinceOnly" not in byt_allowance
    assert "agencySoFirst" not in byt_allowance
    assert "maePortal" not in byt_allowance
    assert byt_allowance["wizard"] == byt_pension["wizard"]
    assert byt_allowance["hasAttachmentStep"] is True
    assert "hideRepeatableHint" not in byt_allowance
    assert byt_allowance["detect"]["urlScope"] == ["dichvucongbyt.moh.gov.vn"]
    # Tên hai thủ tục gần trùng: dấu hiệu nhận trang phải là cụm CHỈ thủ tục này có.
    assert byt_allowance["detect"]["textIncludes"] == ["chăm sóc, nuôi dưỡng hàng tháng"]
    # Bản NĐ 335 (1.116909) của trợ cấp xã hội: cùng khung, bảng 2 dòng (không dồn tệp); tên gần trùng
    # nên dấu hiệu nhận trang của mỗi bên KHÔNG được khớp nhãn bên kia.
    byt_allowance_335 = procedures.pop("thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang")
    assert byt_allowance_335.get("flowProfile") is None
    assert byt_allowance_335["needsAgencySelect"] is True
    assert "agencyProvinceOnly" not in byt_allowance_335 and "agencySoFirst" not in byt_allowance_335
    assert byt_allowance_335["wizard"] == byt_pension["wizard"]
    assert byt_allowance_335["hasAttachmentStep"] is True
    assert "hideRepeatableHint" not in byt_allowance_335
    assert byt_allowance_335["detect"]["urlIncludes"][0] == "maThuTuc=1.116909"
    for marker, other in ((byt_allowance_335, byt_allowance), (byt_allowance, byt_allowance_335)):
        phrase = marker["detect"]["textIncludes"][0].lower()
        assert phrase in marker["label"].lower()
        assert phrase not in other["label"].lower(), "dấu hiệu nhận trang trùng sang thủ tục kia"
    assert byt_allowance_335["shortLabel"] != byt_allowance["shortLabel"]
    assert len(byt_allowance_335["shortLabel"]) >= 30
    # Hỗ trợ mai táng: cùng khung hưu trí, bảng CHỈ MỘT DÒNG nên vẫn dồn tệp (hideRepeatableHint).
    byt_funeral = procedures.pop("ho-tro-mai-tang-huu-tri-xa-hoi")
    assert byt_funeral.get("flowProfile") is None
    assert byt_funeral["needsAgencySelect"] is True
    assert byt_funeral["wizard"] == byt_pension["wizard"]
    assert byt_funeral["hideRepeatableHint"] is True
    # Mai táng cho đối tượng BẢO TRỢ xã hội: cùng khung, chỉ khác nhóm đối tượng.
    byt_funeral_social = procedures.pop("ho-tro-mai-tang-1116910")
    assert byt_funeral_social.get("flowProfile") is None
    assert byt_funeral_social["needsAgencySelect"] is True
    assert byt_funeral_social["wizard"] == byt_pension["wizard"]
    assert byt_funeral_social["hideRepeatableHint"] is True
    # Ba nhãn dùng chung chữ với nhau ("trợ cấp hưu trí xã hội" / "mai táng") → dấu hiệu nhận trang
    # phải ghép đủ cả hai vế, nếu không hai thủ tục mai táng nhận nhầm sang nhau.
    assert byt_funeral["detect"]["textIncludes"] == ["mai táng đối với đối tượng hưởng trợ cấp hưu trí"]
    assert byt_funeral_social["detect"]["textIncludes"] == ["mai táng cho đối tượng bảo trợ xã hội"]
    for marker in (byt_funeral, byt_funeral_social):
        other = byt_funeral_social if marker is byt_funeral else byt_funeral
        phrase = marker["detect"]["textIncludes"][0].lower()
        assert phrase in marker["label"].lower()
        assert phrase not in other["label"].lower(), "dấu hiệu nhận trang trùng sang thủ tục kia"
    assert "mai táng" not in byt_pension["label"]
    # Tên hiển thị trên danh sách phải nói RÕ nhóm đối tượng, không rút gọn thành "Hỗ trợ mai táng".
    for entry in (byt_funeral, byt_funeral_social, byt_allowance, byt_pension):
        assert len(entry["shortLabel"]) >= 30, entry["shortLabel"]
    assert byt_funeral["shortLabel"] != byt_funeral_social["shortLabel"]
    # Xác định mức độ khuyết tật: CÙNG cổng nhưng bước đính kèm là các Ô CỐ ĐỊNH (fixed-slot của
    # pipelines/khuyet_tat) → dồn hết tệp vào một ô là sai ô, nên KHÔNG được bật hideRepeatableHint.
    byt_disability = procedures.pop("xac-dinh-muc-do-khuyet-tat")
    assert byt_disability.get("flowProfile") is None
    assert byt_disability["needsAgencySelect"] is True
    assert byt_disability["wizard"] == byt_pension["wizard"]
    assert "hideRepeatableHint" not in byt_disability
    assert byt_disability["detect"]["urlIncludes"][0] == "maThuTuc=1.001699"
    assert len(byt_disability["shortLabel"]) >= 30
    # Đổi, cấp lại Giấy xác nhận khuyết tật: CÙNG eForm Mẫu số 01 nhưng bảng thành phần hồ sơ chỉ
    # MỘT dòng → ngược với thủ tục trên, phải bật hideRepeatableHint.
    byt_disability_reissue = procedures.pop("doi-cap-lai-giay-xac-nhan-khuyet-tat")
    assert byt_disability_reissue.get("flowProfile") is None
    assert byt_disability_reissue["needsAgencySelect"] is True
    assert byt_disability_reissue["wizard"] == byt_pension["wizard"]
    assert byt_disability_reissue["hideRepeatableHint"] is True
    assert byt_disability_reissue["detect"]["urlIncludes"][0] == "maThuTuc=1.001653"
    reissue_phrase = byt_disability_reissue["detect"]["textIncludes"][0].lower()
    assert reissue_phrase in byt_disability_reissue["label"].lower()
    assert reissue_phrase not in byt_disability["label"].lower(), "dấu hiệu nhận trang trùng sang thủ tục kia"
    assert byt_disability_reissue["shortLabel"] != byt_disability["shortLabel"]
    # Bộ Nội vụ: chọn cơ quan HAI BƯỚC — DVCQG bật "Sở" (agencySoFirst) rồi hộp thoại cổng bộ
    # (maePortal) chọn Sở Nội vụ; hộp thoại không có trường hợp giải quyết nên KHÔNG có variants.
    moha_move = procedures.pop("di-chuyen-ho-so-nguoi-huong-tro-cap")
    assert moha_move.get("flowProfile") is None
    assert moha_move["needsAgencySelect"] is True
    assert moha_move["agencyProvinceOnly"] is True and moha_move["agencySoFirst"] is True
    assert moha_move["maePortal"] is True and moha_move["agencyDeptLabel"] == "Sở Nội vụ"
    assert "variants" not in moha_move
    assert "hideRepeatableHint" not in moha_move
    # CÙNG cổng Bộ Nội vụ nhưng giải quyết ở CẤP XÃ: DVCQG chọn đủ Tỉnh + Xã (không
    # agencyProvinceOnly/agencySoFirst), hộp thoại cổng bộ gạt radio "Phường/Xã".
    # Chi tiết hành vi cấp xã nằm ở test_mae_agency_cap_xa.py; ở đây chỉ chốt hình dạng entry.
    for moha_ward_key in ("uu-dai-ncc-tu-tran", "tro-cap-tho-cung-liet-si"):
        moha_ward = procedures.pop(moha_ward_key)
        assert moha_ward.get("flowProfile") is None
        assert moha_ward["needsAgencySelect"] is True
        assert "agencyProvinceOnly" not in moha_ward and "agencySoFirst" not in moha_ward
        assert moha_ward["maePortal"] is True and moha_ward["maeAgencyLevel"] == "ward"
        assert "agencyDeptLabel" not in moha_ward, "cấp xã thì không có tên Sở để đọc"
        assert moha_ward["wizard"] == moha_move["wizard"]
        assert "variants" not in moha_ward
        assert "hideRepeatableHint" not in moha_ward
        assert len(moha_ward["shortLabel"]) >= 30
    # HkdOnline nhánh THAY ĐỔI: cùng cổng với thành lập mới nhưng workflow "change"
    # (wizard 4 bước + pageOrder động), không dùng profile tư pháp.
    business_change = procedures.pop("dang-ky-thay-doi-noi-dung-ho-kinh-doanh")
    assert business_change.get("flowProfile") is None
    assert business_change["businessWorkflow"] == "change"
    assert len(business_change["pages"]) == 7
    # Chấm dứt hoạt động: CÙNG wizard "Chọn loại đăng ký thay đổi" với nhánh thay đổi (radio
    # DISSOLU) nên cũng dừng ở màn tra cứu mã số; chỉ khác workflow + chỉ có 2 trang phải điền.
    business_dissolution = procedures.pop("cham-dut-hoat-dong-ho-kinh-doanh")
    assert business_dissolution.get("flowProfile") is None
    assert business_dissolution["businessWorkflow"] == "dissolution"
    assert len(business_dissolution["pages"]) == 2
    # Tạm ngừng (radio SUSPEN) đi chung wizard với chấm dứt; cấp lại GCN rẽ ngay ở màn chọn loại
    # đăng ký (radio REI). Cả hai dừng ở màn tra cứu mã số, chỉ 2 trang phải điền.
    for business_key, workflow in (("tam-ngung-kinh-doanh", "suspension"),
                                   ("cap-lai-cap-doi-gcn-ho-kinh-doanh", "reissue")):
        business_two_page = procedures.pop(business_key)
        assert business_two_page.get("flowProfile") is None
        assert business_two_page["businessWorkflow"] == workflow
        assert len(business_two_page["pages"]) == 2
    # Cổng tỉnh Bắc Ninh (Liferay eForm 2 tab cùng trang): không profile tư pháp, không wizard;
    # tỉnh chọn cố định Bắc Ninh + toggle "Sở" (agencySoFirst), điền xong tự đính kèm ngay.
    for bn_key in ("dang-ky-bien-phap-bao-dam-bac-ninh", "xoa-dang-ky-bien-phap-bao-dam-bac-ninh",
                   "dinh-chinh-gcn-da-cap-bac-ninh", "dang-ky-bien-dong-dat-dai-bac-ninh",
                   "tach-hop-thua-dat-bac-ninh", "cap-doi-gcn-bac-ninh",
                   "dang-ky-bien-dong-chuyen-nhuong-bac-ninh"):
        bn_secured = procedures.pop(bn_key)
        assert bn_secured.get("flowProfile") is None
        assert bn_secured["samePageAttach"] is True
        assert bn_secured["agencyProvince"] == "Bắc Ninh"
        assert bn_secured["agencyProvinceOnly"] is True
        assert bn_secured["agencySoFirst"] is True
        assert "wizard" not in bn_secured and "maePortal" not in bn_secured
    # 1.115470: ke_khai_links chỉ provinceOnlyAgency (không selectSo) → không gạt toggle "Sở".
    bn_thoa_thuan = procedures.pop("dang-ky-bien-dong-thoa-thuan-bac-ninh")
    assert bn_thoa_thuan["samePageAttach"] is True
    assert bn_thoa_thuan["agencyProvince"] == "Bắc Ninh"
    assert bn_thoa_thuan["agencyProvinceOnly"] is True
    assert not bn_thoa_thuan.get("agencySoFirst")
    assert "wizard" not in bn_thoa_thuan and "maePortal" not in bn_thoa_thuan
    # 1.115443: ke_khai_links không provinceOnlyAgency / selectSo → chọn đủ Tỉnh + Phường/Xã.
    bn_lan_dau = procedures.pop("dang-ky-dat-dai-lan-dau-bac-ninh")
    assert bn_lan_dau["samePageAttach"] is True
    assert bn_lan_dau["agencyProvince"] == "Bắc Ninh"
    assert bn_lan_dau["needsAgencySelect"] is True
    assert not bn_lan_dau.get("agencyProvinceOnly")
    assert not bn_lan_dau.get("agencySoFirst")
    assert "wizard" not in bn_lan_dau and "maePortal" not in bn_lan_dau
    # 1.115447: ke_khai_links cũng không provinceOnlyAgency / selectSo → chọn đủ Tỉnh + Phường/Xã.
    bn_thu_hoi = procedures.pop("thu-hoi-gcn-cap-sai-bac-ninh")
    assert bn_thu_hoi["samePageAttach"] is True
    assert bn_thu_hoi["agencyProvince"] == "Bắc Ninh"
    assert bn_thu_hoi["needsAgencySelect"] is True
    assert not bn_thu_hoi.get("agencyProvinceOnly")
    assert not bn_thu_hoi.get("agencySoFirst")
    assert "wizard" not in bn_thu_hoi and "maePortal" not in bn_thu_hoi
    # 1.115446: ke_khai_links cũng không provinceOnlyAgency / selectSo → chọn đủ Tỉnh + Phường/Xã.
    bn_sai_sot = procedures.pop("dinh-chinh-sai-sot-bac-ninh")
    assert bn_sai_sot["samePageAttach"] is True
    assert bn_sai_sot["agencyProvince"] == "Bắc Ninh"
    assert bn_sai_sot["needsAgencySelect"] is True
    assert not bn_sai_sot.get("agencyProvinceOnly")
    assert not bn_sai_sot.get("agencySoFirst")
    assert "wizard" not in bn_sai_sot and "maePortal" not in bn_sai_sot
    # 1.115438: ke_khai_links cũng không provinceOnlyAgency / selectSo → chọn đủ Tỉnh + Phường/Xã.
    bn_giao_thue = procedures.pop("giao-thue-chuyen-muc-dich-dat-bac-ninh")
    assert bn_giao_thue["samePageAttach"] is True
    assert bn_giao_thue["agencyProvince"] == "Bắc Ninh"
    assert bn_giao_thue["needsAgencySelect"] is True
    assert not bn_giao_thue.get("agencyProvinceOnly")
    assert not bn_giao_thue.get("agencySoFirst")
    assert "wizard" not in bn_giao_thue and "maePortal" not in bn_giao_thue

    # Trang nộp một trang của Cổng DVC quốc gia: không wizard, không modal bản thân/ủy quyền,
    # không bước chủ hồ sơ; detect giống hệt core.
    core_detect = {procedure["key"]: procedure["detect"] for procedure in core_registry.PROCEDURES}
    for key in ("khai-sinh-dang-ky-thuong", "trich-luc-ks", "khai-tu", "thay-doi-cai-chinh-ho-tich",
                "xac-nhan-tinh-trang-hon-nhan"):
        single_page = procedures.pop(key)
        assert single_page["flowProfile"] == "tu-phap-moi"
        assert single_page["singlePageDossier"] is True
        assert single_page["needsAgencySelect"] is True and single_page["hasAttachmentStep"] is True
        assert "wizard" not in single_page and "executionSubject" not in single_page
        assert "ownerInfo" not in single_page
        assert single_page["detect"] == core_detect[key]
        assert get_owner_info_pipeline(key) is None

    assert procedures
    assert {
        key for key, procedure in procedures.items()
        if procedure.get("flowProfile") != "tu-phap"
    } == set()

    attach_only = {
        "chung-thuc-ban-sao", "chung-thuc-chu-ky", "chung-thuc-giao-dich-tai-san",
        "chung-thuc-chu-ky-nguoi-dich-ctv", "chung-thuc-chu-ky-nguoi-dich-khong-ctv",
        "chung-thuc-phan-chia-di-san",
        "chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich", "chung-thuc-tu-choi-nhan-di-san",
        "chung-thuc-di-chuc", "cap-ban-sao-so-goc", "bau-to-truong-to-hoa-giai",
    }
    for key, procedure in procedures.items():
        owner_enabled = procedure["ownerInfo"]["enabled"]
        assert owner_enabled is (key not in attach_only)
        assert procedure["needsAgencySelect"] is True
        assert procedure["hasAttachmentStep"] is True
        assert procedure["executionSubject"]["default"] == "self"
        assert [
            option["portalValue"] for option in procedure["executionSubject"]["options"]
        ] == ["null", "canhan", "", "", ""]
        assert get_owner_info_pipeline(key) is not None


def test_all_handfree_procedures_delegate_business_core_to_autofill_registry():
    procedures = public_list()
    # So với mốc 21 ban đầu: +1 "khai-sinh-dang-ky-thuong" (khai sinh đơn lẻ),
    # +1 "chung-thuc-giao-dich-tai-san", +1 "chung-thuc-chu-ky-nguoi-dich-ctv" (attach-only)
    # +1 "dieu-chinh-huu-tri-xa-hoi" (Bộ Y tế), +1 "cham-dut-hoat-dong-ho-kinh-doanh"
    # +1 "cap-giay-phep-xay-dung-moi-nha-o-rieng-le" (Bộ Xây dựng)
    # +4 cổng Bộ Y tế dùng lại core sẵn có: "tro-cap-xa-hoi-hang-thang",
    # "ho-tro-mai-tang-huu-tri-xa-hoi", "ho-tro-mai-tang" (nay là "ho-tro-mai-tang-1116910"), "xac-dinh-muc-do-khuyet-tat";
    # +3 cổng Bộ Nội vụ: "di-chuyen-ho-so-nguoi-huong-tro-cap" (cấp Sở),
    # "uu-dai-ncc-tu-tran" + "tro-cap-tho-cung-liet-si" (cấp xã);
    # +1 cổng Bộ Y tế "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham" (ATTP);
    # +2 attach-only tư pháp "chung-thuc-phan-chia-di-san", "chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich";
    # +5 cổng Bộ Xây dựng (luồng chung "xay-dung"): điều chỉnh GPXD, sửa chữa cải tạo, thông tin
    # quy hoạch, thẩm định BCNCKT, lòng đường vỉa hè; +1 liên vận Việt Nam - Lào (cùng luồng).
    # (Trước khi thêm liên vận danh sách thực tế đã là 42, số cũ 41 chưa được cập nhật.)
    # +1 attach-only tư pháp "chung-thuc-tu-choi-nhan-di-san".
    # +1 attach-only tư pháp "chung-thuc-di-chuc".
    # +1 attach-only tư pháp "cap-ban-sao-so-goc".
    # +1 attach-only tư pháp "bau-to-truong-to-hoa-giai".
    # +1 "khai-tu-lien-thong"; +1 tư pháp chọn Sở "yeu-cau-tro-giup-phap-ly".
    # +1 tư pháp "xac-nhan-thong-tin-ho-tich"; +2 HkdOnline "tam-ngung-kinh-doanh",
    # "cap-lai-cap-doi-gcn-ho-kinh-doanh".
    # +1 cổng Bộ Y tế "doi-cap-lai-giay-xac-nhan-khuyet-tat" (1.001653).
    # +1 cổng Bộ Y tế "thuc-hien-tro-cap-xa-hoi-nhan-cham-soc-nuoi-duong-hang-thang" (1.116909).
    # +3 tư pháp: "dang-ky-cham-dut-giam-ho", "chung-thuc-chu-ky-nguoi-dich-khong-ctv" (attach-only),
    # "cap-chung-chi-hanh-nghe-luat-su-mien-dao-tao-tap-su" (chọn Sở).
    # +2 hộ tịch "khai-sinh-ket-hop-nhan-cha-me-con", "dang-ky-nuoi-con-nuoi-trong-nuoc".
    # +1 cổng Bắc Ninh "dinh-chinh-gcn-da-cap-bac-ninh".
    # +1 cổng Bắc Ninh "dang-ky-bien-dong-thoa-thuan-bac-ninh" (1.115470).
    # +1 cổng Bắc Ninh "dang-ky-bien-dong-dat-dai-bac-ninh" (1.115468).
    # +1 cổng Bắc Ninh "tach-hop-thua-dat-bac-ninh" (1.115458).
    # +1 cổng Bắc Ninh "cap-doi-gcn-bac-ninh" (1.115464).
    # +1 cổng Bắc Ninh "dang-ky-dat-dai-lan-dau-bac-ninh" (1.115443).
    # +1 cổng Bắc Ninh "thu-hoi-gcn-cap-sai-bac-ninh" (1.115447).
    # +1 cổng Bắc Ninh "dinh-chinh-sai-sot-bac-ninh" (1.115446).
    # +1 cổng Bắc Ninh "giao-thue-chuyen-muc-dich-dat-bac-ninh" (1.115438).
    # +1 cổng Bắc Ninh "dang-ky-bien-dong-chuyen-nhuong-bac-ninh" (1.013831).
    assert len(procedures) == 69

    for procedure in procedures:
        key = procedure["key"]
        assert get_pipeline(key) is core_registry.get_pipeline(key)
        assert get_attach_pipeline(key) is core_registry.get_attach_pipeline(key)
        if procedure.get("mode") != "attach":
            assert get_pipeline(key) is not None, key
        if procedure.get("hasAttachmentStep"):
            assert get_attach_pipeline(key) is not None, key


def test_thu_tuc_bac_ninh_hien_dung_ten_hanh_chinh_cua_registry_loi():
    # label = tên hành chính thật (bỏ tiền tố "[Tỉnh Bắc Ninh] " của lõi); shortLabel chỉ cắt gọn tên
    # đó, không diễn đạt lại ("Cấp đổi sổ đỏ") và không gắn "(Bắc Ninh)".
    core_label = {procedure["key"]: procedure["label"] for procedure in core_registry.PROCEDURES}
    bac_ninh = [p for p in public_list() if p["key"].endswith("-bac-ninh")]
    assert len(bac_ninh) == 12
    for procedure in bac_ninh:
        assert core_label[procedure["key"]] == "[Tỉnh Bắc Ninh] " + procedure["label"], procedure["key"]
        short = procedure.get("shortLabel", "")
        assert "Bắc Ninh" not in short and "sổ" not in short.lower(), procedure["key"]
