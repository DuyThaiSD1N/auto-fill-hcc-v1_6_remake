"""Danh mục thủ tục: key, label, roles, useDangKyBy. Port FORM_CONFIG trong popup.js.

`pipeline` map key → module pipeline xử lý.
"""
# Pipeline đính kèm theo thủ tục (package-by-feature, app/pipelines/<thủ tục>/attach).
from app.pipelines.cap_ban_sao_so_goc.attach import plan as cap_ban_sao_so_goc_attach
from app.pipelines.an_toan_thuc_pham.attach import plan as an_toan_thuc_pham_attach
from app.pipelines.an_toan_thuc_pham.process import run as an_toan_thuc_pham_process
from app.pipelines.cap_gcn_attp_nong_lam_thuy_san.attach import plan as cap_gcn_attp_nong_lam_thuy_san_attach
from app.pipelines.cap_gcn_attp_nong_lam_thuy_san.process import run as cap_gcn_attp_nong_lam_thuy_san_process
from app.pipelines.cap_lai_an_toan_thuc_pham.process import run as cap_lai_an_toan_thuc_pham_process
from app.pipelines.cap_lai_an_toan_thuc_pham.attach import plan as cap_lai_an_toan_thuc_pham_attach
from app.pipelines.cap_giay_phep_xay_dung.attach import plan as cap_giay_phep_xay_dung_attach
from app.pipelines.cap_giay_phep_xay_dung.process import run as cap_giay_phep_xay_dung_process
from app.pipelines.cap_doi_gcn_bac_ninh.attach import plan as cap_doi_gcn_bac_ninh_attach
from app.pipelines.cap_doi_gcn_bac_ninh.process import run as cap_doi_gcn_bac_ninh_process
from app.pipelines.dinh_chinh_gcn_da_cap_bac_ninh.attach import plan as dinh_chinh_gcn_da_cap_bac_ninh_attach
from app.pipelines.dinh_chinh_gcn_da_cap_bac_ninh.process import run as dinh_chinh_gcn_da_cap_bac_ninh_process
from app.pipelines.dang_ky_dat_dai_lan_dau_lam_dong.attach import plan as dang_ky_dat_dai_lan_dau_lam_dong_attach
from app.pipelines.dang_ky_dat_dai_lan_dau_lam_dong.process import run as dang_ky_dat_dai_lan_dau_lam_dong_process
from app.pipelines.dang_ky_kinh_doanh.attach import plan as dang_ky_kinh_doanh_attach
from app.pipelines.dang_ky_thay_doi_kinh_doanh.attach import plan as dang_ky_thay_doi_kinh_doanh_attach
from app.pipelines.cham_dut_hoat_dong_ho_kinh_doanh.attach import plan as cham_dut_hoat_dong_ho_kinh_doanh_attach
from app.pipelines.cap_lai_cap_doi_gcn_ho_kinh_doanh.attach import plan as cap_lai_cap_doi_gcn_ho_kinh_doanh_attach
from app.pipelines.cap_nuoc_sach.attach import plan as cap_nuoc_sach_attach
from app.pipelines.chung_thuc_ban_sao.attach import plan as chung_thuc_ban_sao_attach
from app.pipelines.chung_thuc_chu_ky.attach import plan as chung_thuc_chu_ky_attach
from app.pipelines.chung_thuc_di_chuc.attach import plan as chung_thuc_di_chuc_attach
from app.pipelines.chung_thuc_giao_dich_tai_san.attach import plan as chung_thuc_giao_dich_tai_san_attach
from app.pipelines.chung_thuc_phan_chia_di_san.attach import plan as chung_thuc_phan_chia_di_san_attach
from app.pipelines.chung_thuc_sua_doi_giao_dich.attach import plan as chung_thuc_sua_doi_giao_dich_attach
from app.pipelines.chung_thuc_tu_choi_di_san.attach import plan as chung_thuc_tu_choi_di_san_attach
from app.pipelines.cap_nuoc_sach.process import run as cap_nuoc_sach_process
from app.pipelines.dang_ky_dat_dai.process import run as dang_ky_dat_dai_process
from app.pipelines.dang_ky_dat_dai_tai_san.process import run as dang_ky_dat_dai_tai_san_process
from app.pipelines.dang_ky_kinh_doanh.process import run as dang_ky_kinh_doanh_process
from app.pipelines.dang_ky_thay_doi_kinh_doanh.process import run as dang_ky_thay_doi_kinh_doanh_process
from app.pipelines.cham_dut_hoat_dong_ho_kinh_doanh.process import run as cham_dut_hoat_dong_ho_kinh_doanh_process
from app.pipelines.cap_lai_cap_doi_gcn_ho_kinh_doanh.process import run as cap_lai_cap_doi_gcn_ho_kinh_doanh_process
from app.pipelines.dieu_chinh_dat_dai.process import run as dieu_chinh_dat_dai_process
from app.pipelines.dinh_chinh_sai_sot.process import run as dinh_chinh_sai_sot_process
from app.pipelines.dinh_chinh_sai_sot.attach import plan as dinh_chinh_sai_sot_attach
from app.pipelines.dinh_chinh_sai_sot_bac_ninh.process import run as dinh_chinh_sai_sot_bac_ninh_process
from app.pipelines.dinh_chinh_sai_sot_bac_ninh.attach import plan as dinh_chinh_sai_sot_bac_ninh_attach
from app.pipelines.dinh_chinh_sai_sot_lam_dong.process import run as dinh_chinh_sai_sot_lam_dong_process
from app.pipelines.dinh_chinh_sai_sot_lam_dong.attach import plan as dinh_chinh_sai_sot_lam_dong_attach
from app.pipelines.cung_cap_thong_tin_quy_hoach.process import run as cung_cap_thong_tin_quy_hoach_process
from app.pipelines.cung_cap_thong_tin_quy_hoach.attach import plan as cung_cap_thong_tin_quy_hoach_attach
from app.pipelines.cap_gcn_diem_tro_choi_dien_tu.process import run as cap_gcn_diem_tro_choi_dien_tu_process
from app.pipelines.cap_gcn_diem_tro_choi_dien_tu.attach import plan as cap_gcn_diem_tro_choi_dien_tu_attach
from app.pipelines.giao_thue_chuyen_muc_dich_dat_bac_ninh.process import run as giao_thue_chuyen_muc_dich_dat_bac_ninh_process
from app.pipelines.giao_thue_chuyen_muc_dich_dat_bac_ninh.attach import plan as giao_thue_chuyen_muc_dich_dat_bac_ninh_attach
from app.pipelines.giao_thue_chuyen_muc_dich_dat_ninh_binh.process import run as giao_thue_chuyen_muc_dich_dat_ninh_binh_process
from app.pipelines.giao_thue_chuyen_muc_dich_dat_ninh_binh.attach import plan as giao_thue_chuyen_muc_dich_dat_ninh_binh_attach
from app.pipelines.dinh_chinh_gcn_da_cap_ninh_binh.process import run as dinh_chinh_gcn_da_cap_ninh_binh_process
from app.pipelines.dinh_chinh_gcn_da_cap_ninh_binh.attach import plan as dinh_chinh_gcn_da_cap_ninh_binh_attach
from app.pipelines.dang_ky_dat_dai_lan_dau_quang_ninh_mien_nui_hai_dao.attach import plan as dang_ky_dat_dai_lan_dau_quang_ninh_mien_nui_hai_dao_attach
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_quang_ninh_mien_nui_hai_dao.attach import plan as dang_ky_bien_dong_chuyen_nhuong_quang_ninh_mien_nui_hai_dao_attach
from app.pipelines.chuyen_muc_dich_su_dung_dat_quang_ninh_mien_nui_hai_dao.attach import plan as chuyen_muc_dich_su_dung_dat_quang_ninh_mien_nui_hai_dao_attach
from app.pipelines.dang_ky_dat_dai_lan_dau_bac_ninh.process import run as dang_ky_dat_dai_lan_dau_bac_ninh_process
from app.pipelines.dang_ky_dat_dai_lan_dau_bac_ninh.attach import plan as dang_ky_dat_dai_lan_dau_bac_ninh_attach
from app.pipelines.thu_hoi_gcn_cap_sai_bac_ninh.process import run as thu_hoi_gcn_cap_sai_bac_ninh_process
from app.pipelines.thu_hoi_gcn_cap_sai_bac_ninh.attach import plan as thu_hoi_gcn_cap_sai_bac_ninh_attach
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_bac_ninh.process import run as dang_ky_bien_dong_chuyen_nhuong_bac_ninh_process
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_bac_ninh.attach import plan as dang_ky_bien_dong_chuyen_nhuong_bac_ninh_attach
from app.pipelines.tach_hop_thua_dat_bac_ninh.process import run as tach_hop_thua_dat_bac_ninh_process
from app.pipelines.tach_hop_thua_dat_bac_ninh.attach import plan as tach_hop_thua_dat_bac_ninh_attach
from app.pipelines.doi_ten_nuoc_sach.attach import plan as doi_ten_nuoc_sach_attach
from app.pipelines.doi_ten_nuoc_sach.process import run as doi_ten_nuoc_sach_process
from app.pipelines.ho_tro_mai_tang.attach import plan as ho_tro_mai_tang_attach
from app.pipelines.ho_tro_mai_tang.process import run as ho_tro_mai_tang_process
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.attach import plan as ho_tro_mai_tang_huu_tri_xa_hoi_attach
from app.pipelines.ho_tro_mai_tang_huu_tri_xa_hoi.process import run as ho_tro_mai_tang_huu_tri_xa_hoi_process
from app.pipelines.dieu_chinh_huu_tri_xa_hoi.attach import plan as dieu_chinh_huu_tri_xa_hoi_attach
from app.pipelines.dieu_chinh_huu_tri_xa_hoi.process import run as dieu_chinh_huu_tri_xa_hoi_process
from app.pipelines.khai_sinh_lien_thong.attach import plan as khai_sinh_lien_thong_attach
from app.pipelines.khai_sinh_lien_thong.process import run as khai_sinh_lien_thong_process
from app.pipelines.khai_sinh_dang_ky_lai.attach import plan as khai_sinh_dang_ky_lai_attach
from app.pipelines.khai_sinh_dang_ky_lai.process import run as khai_sinh_dang_ky_lai_process
from app.pipelines.khai_sinh_thuong.attach import plan as khai_sinh_thuong_attach
from app.pipelines.khai_sinh_thuong.process import run as khai_sinh_thuong_process
from app.pipelines.khai_sinh_ket_hop_nhan_cmc.attach import plan as khai_sinh_ket_hop_nhan_cmc_attach
from app.pipelines.khai_sinh_ket_hop_nhan_cmc.process import run as khai_sinh_ket_hop_nhan_cmc_process
from app.pipelines.ket_hon.attach import plan as ket_hon_attach
from app.pipelines.ket_hon.process import run as ket_hon_process
from app.pipelines.ket_hon_nuoc_ngoai.attach import plan as ket_hon_nuoc_ngoai_attach
from app.pipelines.ket_hon_nuoc_ngoai.process import run as ket_hon_nuoc_ngoai_process
from app.pipelines.ket_hon_lai.attach import plan as ket_hon_lai_attach
from app.pipelines.ket_hon_lai.process import run as ket_hon_lai_process
from app.pipelines.dang_ky_giam_ho.attach import plan as dang_ky_giam_ho_attach
from app.pipelines.dang_ky_giam_ho.process import run as dang_ky_giam_ho_process
from app.pipelines.nhan_cha_me_con.attach import plan as nhan_cha_me_con_attach
from app.pipelines.nhan_cha_me_con.process import run as nhan_cha_me_con_process
from app.pipelines.khai_tu.attach import plan as khai_tu_attach
from app.pipelines.khai_tu.process import run as khai_tu_process
from app.pipelines.khai_tu_dang_ky_lai.attach import plan as khai_tu_dang_ky_lai_attach
from app.pipelines.khai_tu_dang_ky_lai.process import run as khai_tu_dang_ky_lai_process
from app.pipelines.khuyet_tat.attach import plan as khuyet_tat_attach
from app.pipelines.khuyet_tat.process import run as khuyet_tat_process
from app.pipelines.mai_tang_dan_cong.process import run as mai_tang_dan_cong_process
from app.pipelines.trich_luc.attach import plan as trich_luc_attach
from app.pipelines.trich_luc.process import run as trich_luc_process
from app.pipelines.thay_doi_ho_tich.attach import plan as thay_doi_ho_tich_attach
from app.pipelines.thay_doi_ho_tich.process import run as thay_doi_ho_tich_process
from app.pipelines.xac_nhan_tthn.attach import plan as xac_nhan_tthn_attach
from app.pipelines.xac_nhan_tthn.process import run as xac_nhan_tthn_process
from app.pipelines.thi_tuyen_cong_chuc.attach import plan as thi_tuyen_cong_chuc_attach
from app.pipelines.thi_tuyen_cong_chuc.process import run as thi_tuyen_cong_chuc_process
from app.pipelines.xet_tuyen_cong_chuc.attach import plan as xet_tuyen_cong_chuc_attach
from app.pipelines.xet_tuyen_cong_chuc.process import run as xet_tuyen_cong_chuc_process
from app.pipelines.xet_tuyen_vien_chuc.attach import plan as xet_tuyen_vien_chuc_attach
from app.pipelines.xet_tuyen_vien_chuc.process import run as xet_tuyen_vien_chuc_process
from app.pipelines.xet_tuyen_vien_chuc_lai_chau.attach import plan as xet_tuyen_vien_chuc_lai_chau_attach
from app.pipelines.xet_tuyen_vien_chuc_lai_chau.process import run as xet_tuyen_vien_chuc_lai_chau_process
from app.pipelines.cap_lai_to_quoc_ghi_cong.attach import plan as cap_lai_to_quoc_ghi_cong_attach
from app.pipelines.cap_lai_to_quoc_ghi_cong.process import run as cap_lai_to_quoc_ghi_cong_process
from app.pipelines.bo_sung_than_nhan_liet_si.attach import plan as bo_sung_than_nhan_liet_si_attach
from app.pipelines.bo_sung_than_nhan_liet_si.process import run as bo_sung_than_nhan_liet_si_process
from app.pipelines.tham_vieng_mo_liet_si.attach import plan as tham_vieng_mo_liet_si_attach
from app.pipelines.tham_vieng_mo_liet_si.process import run as tham_vieng_mo_liet_si_process
from app.pipelines.tro_cap_tho_cung_liet_si.attach import plan as tro_cap_tho_cung_liet_si_attach
from app.pipelines.tro_cap_tho_cung_liet_si.process import run as tro_cap_tho_cung_liet_si_process
from app.pipelines.uu_dai_ncc_tu_tran.attach import plan as uu_dai_ncc_tu_tran_attach
from app.pipelines.uu_dai_ncc_tu_tran.process import run as uu_dai_ncc_tu_tran_process
from app.pipelines.giai_quyet_che_do_khang_chien.attach import plan as giai_quyet_che_do_khang_chien_attach
from app.pipelines.giai_quyet_che_do_khang_chien.process import run as giai_quyet_che_do_khang_chien_process
from app.pipelines.sua_doi_thong_tin_ho_so_nguoi_co_cong.attach import plan as sua_doi_ttncc_attach
from app.pipelines.sua_doi_thong_tin_ho_so_nguoi_co_cong.process import run as sua_doi_ttncc_process
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.attach import plan as di_chuyen_ho_so_attach
from app.pipelines.di_chuyen_ho_so_nguoi_huong_tro_cap.process import run as di_chuyen_ho_so_process
from app.pipelines.tro_cap_xa_hoi_hang_thang.attach import plan as tro_cap_xa_hoi_hang_thang_attach
from app.pipelines.tro_cap_xa_hoi_hang_thang.process import run as tro_cap_xa_hoi_hang_thang_process
from app.pipelines.cap_giay_phep_lien_van_viet_lao.attach import plan as cap_giay_phep_lien_van_viet_lao_attach
from app.pipelines.cap_giay_phep_lien_van_viet_lao.process import run as cap_giay_phep_lien_van_viet_lao_process
from app.pipelines.xoa_dang_ky_tau_ca.attach import plan as xoa_dang_ky_tau_ca_attach
from app.pipelines.xoa_dang_ky_tau_ca.process import run as xoa_dang_ky_tau_ca_process
from app.pipelines.cap_moi_giay_phep_hanh_nghe_chuyen_tiep.attach import plan as cap_moi_gphn_chuyen_tiep_attach
from app.pipelines.cap_moi_giay_phep_hanh_nghe_chuyen_tiep.process import run as cap_moi_gphn_chuyen_tiep_process
from app.pipelines.cap_chung_chi_hanh_nghe_duoc.attach import plan as cap_cchn_duoc_attach
from app.pipelines.cap_chung_chi_hanh_nghe_duoc.process import run as cap_cchn_duoc_process
from app.pipelines.cap_van_ban_chap_thuan_tau_ca.attach import plan as cap_vb_chap_thuan_tau_ca_attach
from app.pipelines.cap_van_ban_chap_thuan_tau_ca.process import run as cap_vb_chap_thuan_tau_ca_process
from app.pipelines.cap_giay_phep_khai_thac_thuy_san.attach import plan as cap_gp_khai_thac_ts_attach
from app.pipelines.cap_giay_phep_khai_thac_thuy_san.process import run as cap_gp_khai_thac_ts_process
from app.pipelines.dang_ky_bien_phap_bao_dam_qsdd.attach import plan as dk_bien_phap_bao_dam_attach
from app.pipelines.dang_ky_bien_phap_bao_dam_qsdd.process import run as dk_bien_phap_bao_dam_process
from app.pipelines.xoa_dang_ky_phuong_tien_thuy.attach import plan as xoa_dk_phuong_tien_thuy_attach
from app.pipelines.xoa_dang_ky_phuong_tien_thuy.process import run as xoa_dk_phuong_tien_thuy_process
from app.pipelines.dang_ky_bien_dong_dat_dai_da_nang.attach import plan as dk_bien_dong_dat_dai_dn_attach
from app.pipelines.dang_ky_bien_dong_dat_dai_da_nang.process import run as dk_bien_dong_dat_dai_dn_process
from app.pipelines.cap_gcn_so_nha_da_nang.attach import plan as cap_gcn_so_nha_dn_attach
from app.pipelines.cap_gcn_so_nha_da_nang.process import run as cap_gcn_so_nha_dn_process
from app.pipelines.xac_nhan_ho_so_so_nha_da_nang.attach import plan as xn_ho_so_so_nha_dn_attach
from app.pipelines.xac_nhan_ho_so_so_nha_da_nang.process import run as xn_ho_so_so_nha_dn_process
from app.pipelines.cap_phep_long_duong_via_he.attach import plan as cap_phep_via_he_attach
from app.pipelines.cap_phep_long_duong_via_he.process import run as cap_phep_via_he_process
from app.pipelines.cap_giay_phep_chat_ha_cay_xanh.attach import plan as cap_gp_chat_ha_cay_xanh_attach
from app.pipelines.cap_giay_phep_chat_ha_cay_xanh.process import run as cap_gp_chat_ha_cay_xanh_process
from app.pipelines.cap_ban_sao_van_bang_so_goc.attach import plan as cap_ban_sao_van_bang_attach
from app.pipelines.cap_ban_sao_van_bang_so_goc.process import run as cap_ban_sao_van_bang_process
from app.pipelines.chap_thuan_dau_noi_tam.attach import plan as chap_thuan_dau_noi_tam_attach
from app.pipelines.chap_thuan_dau_noi_tam.process import run as chap_thuan_dau_noi_tam_process

PROCEDURES: list[dict] = [
    {
        "key": "chung-thuc-ban-sao",
        # detect: nhận diện theo mã TTHC trên URL (maThuTuc — ổn định); heading khớp label là dự phòng.
        "detect": {"urlIncludes": ["maThuTuc=2.000815"]},
        "label": (
            "Chứng thực bản sao từ bản chính giấy tờ, văn bản do cơ quan, tổ chức có thẩm quyền "
            "của Việt Nam; cơ quan, tổ chức có thẩm quyền của nước ngoài; cơ quan, tổ chức có thẩm "
            "quyền của Việt Nam liên kết với cơ quan, tổ chức có thẩm quyền của nước ngoài cấp hoặc "
            "chứng nhận"
        ),
        # Không cần OCR/LLM: extension gắn trực tiếp các file đã chọn vào thành phần hồ sơ.
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Bản chính giấy tờ, văn bản làm cơ sở để chứng thực bản sao.\n"
            "2. Bản sao cần chứng thực.\n"
            "Tất cả file đã chọn sẽ được đính kèm vào thành phần hồ sơ bắt buộc."
        ),
    },
    {
        # Thủ tục RIÊNG, module đính kèm riêng (chung_thuc_chu_ky_attach): form 2 ô cố định
        # STT1 giấy tờ / STT2 giấy tùy thân — xem _ATTACH_PIPELINE bên dưới.
        "key": "chung-thuc-chu-ky",
        "detect": {"urlIncludes": ["maThuTuc=2.000884"]},
        "label": (
            "Chứng thực chữ ký trong các giấy tờ, văn bản (áp dụng cho cả trường hợp chứng thực "
            "điểm chỉ và trường hợp người yêu cầu chứng thực không thể ký, không thể điểm chỉ được)"
        ),
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy tờ, văn bản cần chứng thực chữ ký/điểm chỉ.\n"
            "2. Nếu có: CCCD của người yêu cầu chứng thực.\n"
            "Tất cả file đã chọn sẽ được đính kèm vào thành phần hồ sơ bắt buộc."
        ),
    },
    {
        "key": "chung-thuc-chu-ky-nguoi-dich-ctv",
        "detect": {"urlIncludes": ["maThuTuc=2.000992"]},
        "label": (
            "Chứng thực chữ ký người dịch mà người dịch là cộng tác viên dịch thuật của "
            "Ủy ban nhân dân cấp xã, tổ chức hành nghề công chứng"
        ),
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        # File chỉ được xử lý local ở extension; thủ tục này không yêu cầu màn xác nhận PDPL.
        "skipConsent": True,
        # Extension tự đính local: không gửi binary/dataUrl lên backend. Một file là một hồ sơ/tab.
        "clientAttachmentCase": {
            "type": "single-row-local-split",
            "componentName": "Bản dịch và giấy tờ, văn bản cần dịch.",
            "componentIndex": 1,
            "normalizeDocumentName": True,
        },
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Bản dịch và giấy tờ, văn bản cần dịch.\n"
            "Mỗi file được đính vào một hồ sơ riêng trên một tab riêng."
        ),
    },
    {
        "key": "chung-thuc-giao-dich-tai-san",
        "detect": {"urlIncludes": ["maThuTuc=2.001035"]},
        "label": "Chứng thực giao dịch liên quan đến tài sản là động sản, quyền sử dụng đất, nhà ở",
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy chứng nhận quyền sở hữu/quyền sử dụng hoặc giấy tờ thay thế của tài sản.\n"
            "2. Dự thảo giao dịch/hợp đồng.\n"
            "3. Nếu có: CCCD, văn bản ủy quyền hoặc tài liệu khác; hệ thống sẽ thêm thành phần hồ sơ mới."
        ),
    },
    {
        "key": "chung-thuc-phan-chia-di-san",
        "detect": {
            "urlIncludes": ["maThuTuc=2.001406"],
            # Tách 2 cụm rời: cổng mới ghi "văn bản THỎA THUẬN phân chia di sản", cổng cũ ghi
            # "văn bản phân chia di sản" — một cụm liền mạch sẽ trượt ở cổng mới.
            "textIncludes": ["chứng thực văn bản", "phân chia di sản"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Chứng thực văn bản thỏa thuận phân chia di sản mà di sản là động sản, quyền sử dụng đất, nhà ở",
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy chứng nhận quyền sở hữu/quyền sử dụng hoặc giấy tờ thay thế của tài sản.\n"
            "2. Nếu có: giấy chứng tử/trích lục khai tử, phiếu đo đạc/chỉnh lý thửa đất, "
            "CCCD người được hưởng di sản.\n"
            "3. Dự thảo/văn bản thỏa thuận phân chia di sản thừa kế.\n"
            "Bước 3: BE yêu cầu FE gộp các giấy tờ nhóm 1-2 vào cùng PDF để upload dòng STT 1; "
            "dự thảo/văn bản thỏa thuận phân chia di sản thừa kế upload riêng dòng STT 2; "
            "không thêm dòng mới."
        ),
    },
    {
        "key": "chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich",
        "detect": {
            "urlIncludes": ["maThuTuc=2.000913"],
            "textIncludes": ["chứng thực việc sửa đổi, bổ sung, hủy bỏ giao dịch"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Chứng thực việc sửa đổi, bổ sung, hủy bỏ giao dịch",
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Dự thảo/văn bản sửa đổi, bổ sung, hủy bỏ giao dịch đã được chứng thực.\n"
            "2. Nếu giao dịch liên quan tài sản phải đăng ký quyền sở hữu/quyền sử dụng: "
            "giấy chứng nhận quyền sở hữu/quyền sử dụng hoặc giấy tờ thay thế.\n"
            "3. Giao dịch/hợp đồng cũ đã được chứng thực.\n"
            "4. Nếu có: CCCD/căn cước công dân của các bên, văn bản ủy quyền hoặc tài liệu khác; "
            "hệ thống sẽ thêm thành phần hồ sơ mới.\n"
            "Bước 3: BE yêu cầu FE gộp dự thảo sửa đổi/bổ sung/hủy bỏ với giấy tờ tài sản "
            "vào cùng PDF để upload dòng STT 1; giao dịch cũ đã chứng thực upload dòng STT 2."
        ),
    },
    {
        "key": "chung-thuc-tu-choi-nhan-di-san",
        "detect": {
            "textIncludes": ["chứng thực văn bản từ chối nhận di sản"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Chứng thực văn bản từ chối nhận di sản",
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Dự thảo/văn bản từ chối nhận di sản.\n"
            "2. Giấy chứng nhận quyền sở hữu/quyền sử dụng hoặc giấy tờ thay thế đối với tài sản.\n"
            "3. Nếu có: CCCD/căn cước công dân của các bên, giấy chứng tử/trích lục khai tử, "
            "văn bản ủy quyền hoặc tài liệu khác.\n"
            "Bước 3: văn bản từ chối nhận di sản upload dòng STT 1; GCN/CCCD/trích lục khai tử "
            "gộp chung vào một PDF để upload dòng STT 2; ủy quyền/tài liệu khác thêm thành phần hồ sơ mới."
        ),
    },
    {
        "key": "chung-thuc-di-chuc",
        "detect": {
            "urlIncludes": ["maThuTuc=2.001019"],
            "textIncludes": ["chứng thực di chúc"],
            "headingDisabled": True,
        },
        "label": "Chứng thực di chúc",
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Dự thảo di chúc.\n"
            "2. CCCD/giấy tờ tùy thân của các bên liên quan trong di chúc.\n"
            "3. Giấy chứng nhận quyền sở hữu, quyền sử dụng hoặc giấy tờ thay thế đối với tài sản.\n"
            "Bước 3: nếu có CCCD/giấy tờ tùy thân riêng, BE yêu cầu FE gộp chúng vào PDF dự thảo di chúc "
            "để upload dòng STT 1; giấy tờ tài sản đính vào dòng STT 2. Nếu không có dự thảo di chúc, "
            "CCCD/giấy tờ tùy thân mới thêm thành phần hồ sơ."
        ),
    },
    {
        "key": "dang-ky-kinh-doanh",
        # Mã TTHC quốc gia 1.001612. KHÔNG đưa vào urlIncludes: cả hai nơi đều không mang mã trên URL —
        # HkdOnline dạng DW_DOCUMENTEdit.aspx?h=<handle phiên>, cổng QG dạng /thu-tuc-hanh-chinh/<uuid>.
        # Trang trên cổng QG chỉ là điểm vào (xem PROCEDURE_KE_KHAI_LINKS ở extension); việc điền diễn ra
        # sau khi cổng chuyển sang HkdOnline, nơi rule domain bên dưới bắt đúng mọi trang con.
        # Cổng riêng (ASP.NET) nhiều trang con .aspx nhưng CÙNG domain → nhận diện theo domain,
        # đúng trên mọi trang con (Địa chỉ, Tên hộ KD, Vốn, Thuế, Ngành nghề, Người nộp, Đính kèm...).
        "detect": {"urlIncludes": ["hokinhdoanh.dkkd.gov.vn"], "headingDisabled": True},
        "label": "Đăng ký thành lập hộ kinh doanh",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy đề nghị đăng ký hộ kinh doanh.\n"
            "2. Nếu có: CCCD của chủ hộ/người nộp hoặc giấy tờ bổ sung."
        ),
        "pages": [
            {"key": "hinh-thuc-dang-ky", "label": "Hình thức đăng ký"},
            {"key": "dia-chi", "label": "Địa chỉ"},
            {"key": "nganh-nghe-kinh-doanh", "label": "Ngành nghề kinh doanh"},
            {"key": "ten-ho-kinh-doanh", "label": "Tên hộ kinh doanh"},
            {"key": "chu-ho-kinh-doanh", "label": "Thông tin về chủ hộ kinh doanh"},
            {"key": "thong-tin-ve-von", "label": "Thông tin về vốn"},
            {"key": "thong-tin-ve-thue", "label": "Thông tin về thuế"},
            {"key": "nguoi-nop-ho-so", "label": "Người nộp hồ sơ"},
        ],
    },
    {
        "key": "dang-ky-thay-doi-noi-dung-ho-kinh-doanh",
        # Không nhận diện bằng body text: màn chọn chung cũng chứa label thủ tục này dù người dùng
        # chưa chọn. Extension gửi businessProcedureHint theo active wizard step/loại hồ sơ.
        "detect": {"headingDisabled": True},
        "label": "Đăng ký thay đổi nội dung đăng ký hộ kinh doanh",
        "mode": "agent",
        "businessWorkflow": "change",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Thông báo thay đổi nội dung đăng ký hộ kinh doanh (thường đi cùng GCN đăng ký HKD hiện tại).\n"
            "2. Bản sao CCCD/căn cước của cá nhân liên quan.\n"
            "3. Tài liệu điều kiện nếu thay đổi chủ hộ/thành viên hộ gia đình."
        ),
        "pages": [
            {"key": "dia-chi", "label": "Địa chỉ"},
            {"key": "nganh-nghe-kinh-doanh", "label": "Ngành nghề kinh doanh"},
            {"key": "ten-ho-kinh-doanh", "label": "Tên hộ kinh doanh"},
            {"key": "chu-ho-kinh-doanh", "label": "Thông tin về chủ hộ kinh doanh"},
            {"key": "thong-tin-ve-von", "label": "Thông tin về vốn"},
            {"key": "thong-tin-ve-thue", "label": "Thông tin về thuế"},
            {"key": "nguoi-nop-ho-so", "label": "Người nộp hồ sơ"},
        ],
    },
    {
        "key": "cham-dut-hoat-dong-ho-kinh-doanh",
        # Bốn bước wizard đầu dùng chung URL/heading với các nhánh thay đổi khác. Extension chỉ
        # nhận diện chắc chắn khi session đã chọn nhánh này hoặc trang Dissolution.aspx đang mở.
        "detect": {"headingDisabled": True},
        "label": "Chấm dứt hoạt động hộ kinh doanh",
        "mode": "agent",
        "businessWorkflow": "dissolution",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Thông báo về việc chấm dứt hoạt động hộ kinh doanh (Mẫu số 1).\n"
            "2. Thông báo của cơ quan thuế về chấm dứt hiệu lực mã số thuế/hoàn thành nghĩa vụ thuế.\n"
            "3. Bản gốc Giấy chứng nhận đăng ký hộ kinh doanh.\n"
            "4. Nếu hộ gia đình cùng thành lập: biên bản họp thành viên hộ gia đình.\n"
            "5. CCCD, ủy quyền hoặc giấy tờ bổ sung khác (đính vào loại Khác)."
        ),
        "pages": [
            {"key": "cham-dut-hoat-dong", "label": "Chấm dứt hoạt động"},
            {"key": "nguoi-nop-ho-so", "label": "Người nộp hồ sơ"},
        ],
    },
    {
        "key": "cap-lai-cap-doi-gcn-ho-kinh-doanh",
        # Wizard REI dùng chung màn chọn/tìm kiếm với các nhánh HKD khác; extension giữ lựa chọn
        # hiện tại ở màn mơ hồ và chỉ xác nhận lại bằng loại hồ sơ/trang DW_RE_ISSUANCEEdit.
        "detect": {"headingDisabled": True},
        "label": "Cấp lại Giấy chứng nhận đăng ký hộ kinh doanh, Cấp đổi sang Giấy chứng nhận đăng ký hộ kinh doanh",
        "mode": "agent",
        "businessWorkflow": "reissue",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy đề nghị cấp lại/cấp đổi Giấy chứng nhận đăng ký hộ kinh doanh (Mẫu số 2).\n"
            "2. CCCD, GCN cũ, giấy ủy quyền hoặc giấy tờ bổ sung khác được đính vào loại Khác."
        ),
        "pages": [
            {"key": "thong-tin-de-nghi-cap-lai", "label": "Thông tin đề nghị cấp lại GCN/GXNTĐ"},
            {"key": "nguoi-nop-ho-so", "label": "Người nộp hồ sơ"},
        ],
    },
    {
        "key": "khai-sinh-dang-ky-thuong",
        "detect": {"urlIncludes": ["maThuTuc=1.001193"]},
        "label": "Thủ tục đăng ký khai sinh",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của cha (cả 2 mặt).\n"
            "2. CCCD của mẹ (cả 2 mặt).\n"
            "3. Giấy chứng sinh của con.\n"
            "Bước 3: hệ thống có thể đính giấy chứng sinh vào thành phần hồ sơ có sẵn, "
            "hoặc thêm thành phần CCCD bố/mẹ nếu cần."
        ),
    },
    {
        "key": "khai-sinh-ket-hop-nhan-cha-me-con",
        "detect": {"urlIncludes": ["maThuTuc=1.000689"]},
        "label": "Thủ tục đăng ký khai sinh kết hợp đăng ký nhận cha, mẹ, con",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để điền cả hai mẫu điện tử:\n"
            "1. Tờ khai đăng ký khai sinh.\n"
            "2. Tờ khai đăng ký nhận cha, mẹ, con.\n"
            "3. Giấy chứng sinh.\n"
            "4. CCCD/Căn cước của người yêu cầu và các bên liên quan.\n"
            "5. Kết quả ADN hoặc văn bản xác nhận quan hệ cha, mẹ, con.\n"
            "6. Nếu có: giấy chứng tử, quyết định/bản án ly hôn chứng minh tình trạng hôn nhân.\n"
            "Bước đính kèm: tờ khai giấy chỉ dùng để OCR; giấy chứng sinh vào STT 3; "
            "kết quả ADN/văn bản giám định vào STT 4; CCCD và chứng cứ tình trạng hôn nhân "
            "được thêm thành phần hồ sơ mới."
        ),
    },
    {
        "key": "khai-sinh-dang-ky",
        # Liên thông nằm trên cổng riêng (lienthong.dichvucong.gov.vn), không có heading chuẩn
        # → nhận diện THEO URL (mã thủ tục 2.000986 trên route ke-khai).
        "detect": {
            "urlIncludes": ["lienthong.dichvucong.gov.vn/#/ke-khai/2.000986"],
            "headingDisabled": True,
        },
        "review": False,  
        "label": (
            "Liên thông thủ tục hành chính về đăng ký khai sinh, đăng ký thường trú, "
            "cấp thẻ bảo hiểm y tế cho trẻ em dưới 6 tuổi"
        ),
        # Form mới (Angular) — chế độ agent: không gắn role, BE tự suy luận cha/mẹ/con.
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của cha (cả 2 mặt) + CCCD của mẹ (cả 2 mặt).\n"
            "   Hoặc Giấy chứng nhận kết hôn của cha mẹ (nếu KHÔNG có CCCD cha/mẹ): "
            "hệ thống tự lấy thông tin cha/mẹ từ giấy kết hôn.\n"
            "2. Giấy chứng sinh của con.\n"
            "Bước 3: hệ thống có thể đính giấy chứng sinh vào thành phần hồ sơ có sẵn, "
            "hoặc thêm thành phần CCCD bố/mẹ nếu cần."
        ),
    },
    {
        "key": "khai-sinh-dang-ky-lai",
        "detect": {"urlIncludes": ["maThuTuc=1.004884"]},
        "label": "Thủ tục đăng ký lại khai sinh",
        "mode": "agent",
        "hasAttachmentStep": True,
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên: CCCD cha, CCCD mẹ, giấy khai sinh cũ/bản sao hoặc giấy tờ thay thế.\n"
            "Nếu có: tờ khai giấy, ủy quyền, học bạ, hộ chiếu, bằng/chứng chỉ."
        ),
    },
    {
        "key": "ket-hon",
        "detect": {"urlIncludes": ["maThuTuc=1.000894"]},
        "label": "Thủ tục đăng ký kết hôn",
        "mode": "agent",
        "hasAttachmentStep": True,
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy tờ tùy thân của hai bên (CCCD/CMND/hộ chiếu; có thể tải từng mặt hoặc nhiều file).\n"
            "2. Nếu có: tờ khai bản giấy, bản cam đoan và giấy tờ liên quan khác.\n"
            "Hệ thống sẽ gộp các mặt giấy tờ tùy thân vào đúng thành phần hồ sơ và tách tài liệu nếu một PDF chứa nhiều loại giấy tờ."
        ),
    },
    {
        "key": "ket-hon-nuoc-ngoai",
        # Form riêng có yếu tố nước ngoài — nhận diện theo tiêu đề (chưa có maThuTuc; cập nhật sau nếu cần).
        "detect": {"textIncludes": ["kết hôn có yếu tố nước ngoài"], "textPriority": True},
        "label": "Thủ tục đăng ký kết hôn có yếu tố nước ngoài",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy tờ tùy thân bên nam (CCCD Việt Nam hoặc giấy tờ nước ngoài: hộ chiếu/CMND + bản dịch công chứng).\n"
            "2. Giấy tờ tùy thân bên nữ.\n"
            "3. Nếu có: giấy xác nhận tình trạng hôn nhân của bên nước ngoài (đã hợp pháp hoá lãnh sự).\n"
            "Hệ thống tự phân biệt nam/nữ theo giới tính và đọc quốc tịch/nơi cư trú thật (không mặc định Việt Nam)."
        ),
    },
    {
        "key": "dang-ky-lai-ket-hon",
        "detect": {"urlIncludes": ["maThuTuc=1.004746"]},
        "label": "Thủ tục đăng ký lại kết hôn",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của bên nam (chồng).\n"
            "2. CCCD của bên nữ (vợ).\n"
            "3. Bản sao Giấy chứng nhận kết hôn cũ (để lấy số/ngày/nơi đăng ký kết hôn trước đây).\n"
            "Không cần chọn trước giấy tờ là của chồng hay vợ; hệ thống tự phân biệt theo giới tính trên CCCD.\n"
            "Nếu thiếu CCCD của một bên, hệ thống lấy thông tin bên đó từ giấy chứng nhận kết hôn."
        ),
    },
    {
        "key": "dang-ky-giam-ho",
        "detect": {"textIncludes": ["Thủ tục đăng ký giám hộ"], "headingDisabled": True},
        "label": "Thủ tục đăng ký giám hộ",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Tờ khai đăng ký giám hộ.\n"
            "2. CCCD/CMND của người yêu cầu và người giám hộ.\n"
            "3. Giấy khai sinh/giấy tờ định danh của người được giám hộ.\n"
            "4. Nếu có: trích xuất CSDL dân cư hoặc giấy tờ chứng minh điều kiện giám hộ."
            "\nBước 3: tờ khai bản giấy thêm thành phần hồ sơ mới; văn bản cử người giám hộ vào STT 2; "
            "bản cam đoan, sổ đỏ/giấy tờ chỗ ở, giấy khai sinh và mọi CCCD/căn cước vào STT 3; "
            "văn bản ủy quyền vào STT 4."
        ),
    },
    {
        "key": "dang-ky-nhan-cha-me-con",
        "detect": {"textIncludes": ["Thủ tục đăng ký nhận cha, mẹ, con"], "headingDisabled": True},
        "label": "Thủ tục đăng ký nhận cha, mẹ, con",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Tờ khai đăng ký nhận cha, mẹ, con.\n"
            "2. CCCD/Căn cước của người yêu cầu và các bên liên quan.\n"
            "3. Giấy khai sinh/giấy chứng sinh của con.\n"
            "4. Chứng cứ chứng minh quan hệ cha, mẹ, con như kết quả xét nghiệm ADN."
            "\nBước 3: eForm online ở STT 1 bỏ qua; kết quả ADN/văn bản y tế/giám định vào STT 2; "
            "nếu không có văn bản xác nhận quan hệ thì văn bản cam đoan + người làm chứng vào STT 3; "
            "tờ khai bản giấy, CCCD/căn cước và giấy khai sinh/giấy chứng sinh thêm thành phần hồ sơ mới."
        ),
    },
    {
        "key": "trich-luc-ks",
        "detect": {"urlIncludes": ["maThuTuc=2.000635"]},
        "label": "Cấp bản sao Trích lục hộ tịch, bản sao Giấy khai sinh",
        # Chế độ agent: không gắn role, BE tự suy luận từ text OCR.
        "mode": "agent",
        "hasAttachmentStep": True,
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của người yêu cầu.\n"
            "2. Giấy tờ hộ tịch cần cấp bản sao: giấy khai sinh, giấy đăng ký kết hôn hoặc trích lục khai tử.\n"
            "3. Nếu có: văn bản ủy quyền hoặc giấy tờ chứng minh cư trú."
        ),
    },
    {
        "key": "trich-luc-khai-tu",
        "detect": {"urlIncludes": ["1.006714"]},
        "label": "Trích lục khai tử",
        "mode": "agent",
        "hasAttachmentStep": True,
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của người yêu cầu.\n"
            "2. Giấy khai tử hoặc trích lục khai tử hiện có (nếu có).\n"
            "3. Nếu có: văn bản ủy quyền hoặc giấy tờ chứng minh quan hệ với người đã khai tử."
        ),
    },
    {
        "key": "cap-ban-sao-so-goc",
        # Cổng dùng chung layout eForm, nhận diện theo TÊN thủ tục hiển thị trên trang.
        "detect": {
            "urlIncludes": ["maThuTuc=2.000908"],
            "textIncludes": ["cấp bản sao từ sổ gốc"],
            "headingDisabled": True,
        },
        "label": "Thủ tục cấp bản sao từ sổ gốc",
        # Chỉ đính kèm: BE OCR phân loại rồi xếp file vào 2 ô có sẵn (không điền bước Kê khai).
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy tờ chứng minh quan hệ với người được cấp bản chính (giấy khai sinh, "
            "giấy chứng nhận kết hôn, giấy báo tử/trích lục khai tử...).\n"
            "2. CCCD/giấy tờ tùy thân của người yêu cầu.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR và "
            "đính CCCD vào ô STT 2, giấy tờ chứng minh quan hệ vào ô STT 1."
        ),
    },
    {
        "key": "khai-tu",
        "detect": {"urlIncludes": ["maThuTuc=1.000656"]},
        "label": "Thủ tục đăng ký khai tử",
        "mode": "agent",
        "hasAttachmentStep": True,
        "review": False,  # pilot rà soát bbox
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD/CMND/Hộ chiếu có trong hồ sơ; có thể tải riêng từng mặt hoặc nhiều người.\n"
            "2. Giấy báo tử/giấy chứng tử hoặc giấy tờ thay giấy báo tử.\n"
            "3. Nếu có: tờ khai bản giấy, văn bản ủy quyền, giấy tờ chứng minh sự kiện chết hoặc nơi chết.\n"
            "Không cần chọn trước loại giấy tờ; hệ thống tự phân biệt theo nội dung OCR, tách tài liệu trong PDF "
            "và gộp tất cả giấy tờ tùy thân thành một nhóm.\n"
            "Bước 3: hệ thống đưa giấy tờ vào đúng thành phần hồ sơ có sẵn; giấy tờ tùy thân và tờ khai "
            "bản giấy được thêm thành phần mới."
        ),
    },
    {
        "key": "khai-tu-dang-ky-lai",
        "detect": {"urlIncludes": ["maThuTuc=1.005461"]},
        "label": "Thủ tục đăng ký lại khai tử",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Tờ khai đăng ký lại khai tử bản giấy nếu có.\n"
            "2. CCCD/giấy tờ tùy thân của người yêu cầu.\n"
            "3. CCCD/giấy tờ liên quan của người đã chết.\n"
            "4. Nếu có: giấy chứng tử, trích lục khai tử hoặc giấy tờ thể hiện thông tin đăng ký khai tử trước đây.\n"
            "Hệ thống tự phân biệt người yêu cầu, người đã chết và thông tin đăng ký trước đây theo nội dung OCR.\n"
            "Bước 3: giấy chứng tử/giấy tờ chứng minh sự kiện chết vào ô STT 2; văn bản ủy quyền vào STT 3; "
            "CCCD, tờ khai bản giấy và giấy tờ khác thêm thành phần hồ sơ mới."
        ),
    },
    {
        "key": "thay-doi-cai-chinh-ho-tich",
        "detect": {"urlIncludes": ["maThuTuc=1.004859"]},
        "label": (
            "Thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc"
        ),
        "review": False,
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy tờ làm căn cứ thay đổi/cải chính: giấy khai sinh, trích lục hộ tịch, đăng ký kết hôn, "
            "khai tử, học bạ, bằng cấp, giấy xác nhận, quyết định hoặc giấy tờ liên quan khác.\n"
            "2. CCCD/CMND/Hộ chiếu có trong hồ sơ; có thể tải riêng từng mặt hoặc nhiều người.\n"
            "3. Nếu có: tờ khai bản giấy và văn bản ủy quyền.\n"
            "Mục I (người yêu cầu) do cổng tự điền; hệ thống chỉ đặt mặc định cư trú và "
            "phương thức nhận kết quả (viền vàng). Không tự chọn cấp/số lượng bản sao.\n"
            "Bước 3: giấy tờ làm căn cứ vào ô 'Giấy tờ liên quan', văn bản ủy quyền vào ô ủy quyền; "
            "mọi giấy tờ tùy thân được gộp thành một thành phần mới, tờ khai bản giấy thêm thành phần mới."
        ),
    },
    {
        "key": "xac-nhan-tinh-trang-hon-nhan",
        "detect": {"urlIncludes": ["maThuTuc=1.004873"]},
        "label": "Thủ tục cấp Giấy xác nhận tình trạng hôn nhân",
        "mode": "agent",
        "hasAttachmentStep": True,
        "review": False,  # pilot rà soát bbox
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của cá nhân yêu cầu xác nhận tình trạng hôn nhân.\n"
            "Mặc định người yêu cầu là bản thân; không cần chọn trước vai trò giấy tờ.\n"
            "Bước 3: hệ thống có thể đính kèm CCCD hoặc giấy tờ điều kiện vào thành phần hồ sơ phù hợp."
        ),
    },
    {
        "key": "dinh-chinh-sai-sot",
        # Cổng Lai Châu là SPA, URL con/sid thay đổi theo phiên nên dùng đúng host làm cổng chặn rồi
        # khớp tiêu đề đầy đủ. Không yêu cầu thêm chữ "Lai Châu" trong body vì footer có thể nằm ngoài
        # 6.000 ký tự mà extension thu thập; host cụ thể đã tách an toàn khỏi thủ tục cùng tên ở Lâm Đồng.
        "detect": {
            "urlScope": ["dichvucong.laichau.gov.vn"],
            "textIncludes": ["đính chính giấy chứng nhận đã cấp lần đầu có sai sót"],
            "headingDisabled": True,
        },
        "label": "[Lai Châu] Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai theo Mẫu số 11/ĐK hoặc Mẫu số 18.\n"
            "2. Bản gốc/bản chụp Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất "
            "đã cấp.\n"
            "3. Giấy tờ chứng minh nội dung sai sót cần đính chính (CCCD, giấy khai sinh, quyết định, "
            "văn bản xác nhận...).\n"
            "4. Nếu có: Văn bản ủy quyền khi thực hiện thủ tục qua người đại diện.\n"
            "Mỗi file tối đa 6 MB; hệ thống tự chọn đúng nhóm Mẫu 11/ĐK hoặc Mẫu 18."
        ),
    },
    {
        "key": "dinh-chinh-sai-sot-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay + select2) — nền tảng RIÊNG, engine fill-bacninh.js.
        # maThuTucHanhChinh=1.012796 là duy nhất → nhận diện chắc chắn theo URL.
        "detect": {"urlIncludes": ["maThuTucHanhChinh=1.012796"]},
        "label": "[Tỉnh Bắc Ninh] Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai (Mẫu số 18) người yêu cầu đã khai.\n"
            "2. CCCD/giấy tờ tùy thân của người yêu cầu.\n"
            "3. Bản gốc Giấy chứng nhận QSDĐ/quyền sở hữu tài sản đã cấp.\n"
            "4. Nếu có: giấy tờ chứng minh sai sót, văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Bước điền đơn: khớp ô theo NHÃN (a) Tên, b) Giấy tờ nhân thân, c) Địa chỉ, 2) Nội dung biến động.\n"
            "Bước đính kèm: Đơn + CCCD vào nhóm 'Đơn đăng ký biến động Mẫu số 18'; bản gốc GCN vào nhóm "
            "'Bản gốc Giấy chứng nhận đã cấp'."
        ),
    },
    {
        "key": "dinh-chinh-sai-sot-lam-dong",
        # Cổng dichvucong.lamdong.gov.vn (Form.io/Angular apply-online) — CÙNG nền tảng GPXD lamdong,
        # engine fill standard dom-*. URL chỉ có ObjectId THEO PHƯỜNG (đổi theo mỗi phường/xã) → KHÔNG
        # dùng urlIncludes được. Detect theo VĂN BẢN: tiêu đề + MÃ THỦ TỤC "1.012796.H36" (H36 = mã tỉnh
        # Lâm Đồng, giống mọi phường). Mã H36 KHÔNG có ở trang Lai Châu (tiêu đề trùng) → tách được 2 tỉnh;
        # tổng cụm dài hơn rule Lai Châu ("đính chính"+"sai sót") nên thắng điểm trên trang Lâm Đồng.
        # urlScope = cổng gate: chỉ tin text khi URL đúng cổng Lâm Đồng (URL chỉ có ObjectId theo
        # phường, không định danh thủ tục) → tránh dương tính giả nếu trang khác trùng cụm text.
        "detect": {"urlScope": ["lamdong.gov.vn"], "textIncludes": [
            "đính chính giấy chứng nhận đã cấp lần đầu có sai sót",
            "1.012796.H36",
        ]},
        "label": "[Tỉnh Lâm Đồng] Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai (Mẫu số 18) người yêu cầu đã khai — dùng để điền thân đơn.\n"
            "2. CCCD/giấy tờ tùy thân của chủ hồ sơ (người có sai sót trên Giấy chứng nhận).\n"
            "3. Giấy chứng nhận QSDĐ đã cấp cần đính chính.\n"
            "4. Giấy khai sinh (bằng chứng thông tin đúng, vd năm sinh); nếu có: Giấy ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Điền đơn (Form.io): Phần I Người nộp, Phần II Thửa đất, Phần III Chủ hồ sơ, Phần IV Chi tiết GCN "
            "(số phát hành, ngày cấp, đơn vị cấp, nơi cấp); nội dung đính chính vào ô Ghi chú.\n"
            "Nếu nộp qua người được ủy quyền: Phần I là người đại diện, Phần III là chủ hồ sơ (chủ GCN).\n"
            "Đính kèm: GCN + Giấy khai sinh vào dòng 'Giấy tờ chứng minh sai sót'; Đơn Mẫu 18 + CCCD vào dòng "
            "'Đơn đăng ký biến động Mẫu số 18'; Giấy ủy quyền (nếu có) vào dòng 'Văn bản ủy quyền'. Bản gốc "
            "GCN nộp trực tiếp một cửa, không scan.\n"
            "Tỉnh/Phường (3 khối địa chỉ) là select cascade Choices.js — extension tự chọn theo tên MỚI."
        ),
    },
    {
        "key": "dang-ky-dat-dai-lan-dau-lam-dong",
        # Cổng dichvucong.lamdong.gov.vn (Form.io apply-online) — CÙNG form đính chính lamdong. URL chỉ có
        # ObjectId THEO PHƯỜNG (đổi mỗi phường) → KHÔNG dùng urlIncludes. Detect theo VĂN BẢN: tiêu đề +
        # MÃ THỦ TỤC "1.013978.H36" (H36 = mã tỉnh Lâm Đồng, giống mọi phường; mã duy nhất). Phần IV GCN
        # "không cần điền".
        # urlScope = cổng gate Lâm Đồng (xem thủ tục đính chính lamdong ở trên): URL chỉ có ObjectId
        # theo phường nên cần chắc đúng cổng trước khi tin cụm text + mã "1.013978.H36".
        "detect": {"urlScope": ["lamdong.gov.vn"], "textIncludes": [
            "đăng ký đất đai, tài sản gắn liền với đất, cấp giấy chứng nhận",
            "1.013978.H36",
        ]},
        "label": (
            "[Tỉnh Lâm Đồng] Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng "
            "đất, quyền sở hữu tài sản gắn liền với đất lần đầu đối với hộ gia đình, cá nhân, cộng đồng dân "
            "cư, người gốc Việt Nam định cư ở nước ngoài"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu 15/ĐK) — dùng để điền thân đơn.\n"
            "2. CCCD/giấy tờ tùy thân của chủ hộ; nếu có: Giấy ủy quyền.\n"
            "3. Sơ đồ ranh giới sử dụng đất, Trích lục bản đồ địa chính, Mảnh đo đạc chỉnh lý, Bản mô tả "
            "ranh giới mốc giới (Phụ lục 12).\n"
            "4. Giấy tờ nguồn gốc: đơn xác nhận nguồn gốc, giấy xác nhận UBND, sổ hộ khẩu, hợp đồng nước...\n"
            "5. Biên lai thu thuế/phí (chứng từ nghĩa vụ tài chính) nếu có.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Điền đơn (Form.io): Phần I Người nộp, Phần II Thửa đất, Phần III Chủ hồ sơ. Phần IV 'Thông tin "
            "chi tiết' (GCN) KHÔNG cần điền (đăng ký lần đầu). Nếu nộp thay qua ủy quyền: Phần I là người "
            "đại diện, Phần III là chủ hộ.\n"
            "Đính kèm: hệ thống GỘP file thành 1 PDF cho mỗi nhóm — Đơn+CCCD+ủy quyền → 'Đơn đăng ký đất "
            "đai'; mô tả ranh giới+đo đạc+trích lục → 'Mảnh trích đo bản đồ'; biên lai → 'Chứng từ nghĩa vụ "
            "tài chính'; giấy tờ nguồn gốc → 'Một trong các loại giấy tờ (Điều 137, khoản 1,5)'.\n"
            "Tỉnh/Phường (3 khối địa chỉ) là select cascade — extension tự chọn."
        ),
    },
    {
        "key": "cung-cap-thong-tin-quy-hoach",
        # Cổng Bộ Xây dựng dvc.moc.gov.vn (Form.io apply-online) — CÙNG nền tảng/engine fill standard
        # dom-* với các thủ tục Lâm Đồng. URL KHÔNG có maThuTucHanhChinh (chỉ ObjectId mờ) → detect theo
        # ObjectId apply-online riêng (khớp bước 1 URL). urlIncludes là OR: khớp id đơn hoặc id process.
        "detect": {"urlIncludes": [
            "apply-online/6943a4f15d981376a5fd95c1",
            "process=6960b049541b9f57ac65f185",
        ]},
        "label": "Cung cấp thông tin quy hoạch đô thị và nông thôn",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn (Văn bản) đề nghị cung cấp thông tin quy hoạch — dùng để điền thông tin người nộp.\n"
            "2. CCCD/giấy tờ tùy thân của người nộp hồ sơ.\n"
            "3. Giấy chứng nhận quyền sử dụng đất (sổ đỏ) của thửa đất cần tra cứu quy hoạch.\n"
            "Nếu nộp thay: thêm Giấy ủy quyền + CCCD người được ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Điền đơn (Form.io): CHỈ Phần I 'Thông tin người nộp hồ sơ' (họ tên, ngày sinh, giới tính, "
            "CCCD, ngày/nơi cấp, quốc gia, tỉnh/phường/địa chỉ, điện thoại). Thông tin thửa đất KHÔNG có "
            "ô riêng — nộp qua bản scan.\n"
            "Đính kèm: hệ thống GỘP Đơn đề nghị + Giấy chứng nhận + CCCD thành 1 PDF vào thành phần "
            "'Văn bản đề nghị cung cấp thông tin về quy hoạch đô thị và nông thôn'.\n"
            "Tỉnh/Phường là select Choices.js — extension tự chọn theo tên MỚI (sau sáp nhập)."
        ),
    },
    {
        "key": "cap-gcn-diem-tro-choi-dien-tu-cong-cong",
        # Cổng Bộ VHTTDL dichvucong.bvhttdl.gov.vn — Angular Material `liz-*`, DOM strip formcontrolname.
        # Engine RIÊNG content/fill-liz.js khớp ô theo (section .group-header, nhãn <mat-label>).
        # URL có MaTTHC riêng → detect theo mã thủ tục.
        "detect": {"urlIncludes": ["matthc=1.013792"]},
        "label": (
            "Cấp giấy chứng nhận đủ điều kiện hoạt động điểm cung cấp dịch vụ "
            "trò chơi điện tử công cộng"
        ),
        "mode": "agent",
        # Đính kèm: bảng style_table 3 dòng, mỗi dòng input file trong <app-upload-flie-multi> → engine
        # fixed-slot bơm thẳng theo slotIndex 0/1/2 (Đơn 51a / CCCD / GCN hộ KD).
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. CCCD của chủ điểm (cá nhân).\n"
            "2. Đơn đề nghị cấp GCN — Mẫu số 51a.\n"
            "3. Giấy phép kinh doanh (Giấy chứng nhận đăng ký hộ kinh doanh).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Chủ điểm là cá nhân → thông tin người nộp = người được giải quyết = chủ hộ kinh doanh "
            "(người đại diện pháp luật), extension điền cả 3 phần.\n"
            "Phần 'Thông tin chung' (cơ quan/lĩnh vực/thủ tục) hệ thống tự điền; ô 'Dịch vụ công' bạn tự "
            "chọn mức độ. Đính kèm bản scan (Đơn 51a, CCCD chứng thực, GCN hộ KD chứng thực) làm thủ công."
        ),
    },
    {
        "key": "giao-thue-chuyen-muc-dich-dat-bac-ninh",
        # maThuTucHanhChinh=1.013949 là mã QG dùng chung nhiều cổng iGate (Lâm Đồng cũng có mã này) → PHẢI
        # khóa host bacninh, nếu không sẽ nhận nhầm trên cổng tỉnh khác.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.013949"],
        },
        "label": (
            "[Tỉnh Bắc Ninh] Giao đất, cho thuê đất, chuyển mục đích sử dụng đất; "
            "giao đất và giao rừng; cho thuê đất và cho thuê rừng; gia hạn sử dụng đất"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị (Mẫu số 01/02) người yêu cầu đã khai — dùng để tự động điền thân đơn.\n"
            "2. Bản gốc/bản sao Giấy chứng nhận QSDĐ (sổ đỏ/hồng).\n"
            "3. CCCD/giấy tờ tùy thân của người đề nghị.\n"
            "4. Nếu có: văn bản ủy quyền, Đơn Mẫu 01/04, phương án sử dụng tầng đất mặt (Mẫu 26).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Điền đơn: khớp ô theo NHÃN (Người đề nghị, Địa chỉ, Địa điểm thửa đất, Diện tích, Mục đích, "
            "Thời hạn...) + khối người nhận kết quả (họ tên, CCCD, SĐT, địa chỉ).\n"
            "Đính kèm: GCN vào ô 'Bản sao giấy chứng nhận' (KQ005881); CCCD/ủy quyền vào ô đính kèm bổ sung. "
            "Cơ quan tiếp nhận và tỉnh/phường người nhận là select theo địa bàn — chọn tay."
        ),
    },
    {
        "key": "giao-thue-chuyen-muc-dich-dat-ninh-binh",
        # URL SPA không mang mã thủ tục ổn định: khóa đúng domain rồi yêu cầu đủ hai đoạn tên đặc trưng.
        "detect": {
            "urlScope": ["dichvucong.ninhbinh.gov.vn"],
            "textIncludes": [
                "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất đối với trường hợp giao đất",
                "gia hạn sử dụng đất khi hết thời hạn sử dụng đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Ninh Bình] Giao đất, cho thuê đất, chuyển mục đích sử dụng đất đối với trường hợp giao đất, cho thuê "
            "đất không đấu giá quyền sử dụng đất, không đấu thầu lựa chọn nhà đầu tư thực hiện dự án có "
            "sử dụng đất; trường hợp giao đất, cho thuê đất thông qua đấu thầu lựa chọn nhà đầu tư thực "
            "hiện dự án có sử dụng đất; giao đất và giao rừng; cho thuê đất và cho thuê rừng, gia hạn sử "
            "dụng đất khi hết thời hạn sử dụng đất"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Đơn theo Mẫu số 04 hoặc Mẫu số 01 đã kê khai.\n"
            "2. Giấy chứng nhận quyền sử dụng đất/quyết định giao, cho thuê hoặc chuyển mục đích đất.\n"
            "3. Nếu nộp thay: văn bản ủy quyền; nếu có: CCCD của đúng người nộp.\n"
        ),
    },
    {
        "key": "dinh-chinh-gcn-da-cap-ninh-binh",
        # SPA không có mã thủ tục ổn định trong URL: khóa domain Ninh Bình và tiêu đề đầy đủ đặc trưng.
        "detect": {
            "urlScope": ["dichvucong.ninhbinh.gov.vn"],
            "textIncludes": ["Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Tỉnh Ninh Bình] Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18 đã kê khai.\n"
            "2. Bản gốc Giấy chứng nhận đã cấp cần đính chính.\n"
            "3. Giấy tờ chứng minh sai sót như giấy khai sinh, trích lục, quyết định, giấy xác nhận hoặc "
            "hồ sơ địa chính liên quan.\n"
            "4. CCCD/CMND của người sử dụng đất; nếu nộp thay: văn bản ủy quyền và giấy tờ của người được ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR."
        ),
    },
    {
        "key": "dang-ky-dat-dai-lan-dau-quang-ninh-mien-nui-hai-dao",
        # URL /nop-ho-so/145099 có thể đổi theo cấu hình cổng; khóa domain và hai đoạn tiêu đề đặc
        # trưng để không nhận nhầm các biến thể đồng bằng hoặc thủ tục đất đai khác tại Quảng Ninh.
        "detect": {
            "urlScope": ["dichvucong.quangninh.gov.vn"],
            "textIncludes": [
                "[Đặc thù] Thủ tục đăng ký đất đai, tài sản gắn liền với đất, cấp giấy chứng nhận",
                "Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Quảng Ninh] [Đặc thù] Thủ tục đăng ký đất đai, tài sản gắn liền với đất, cấp giấy "
            "chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất lần đầu đối với hộ "
            "gia đình, cá nhân, cộng đồng dân cư, người gốc việt nam định cư ở nước ngoài - Trường "
            "hợp thực hiện thủ tục đăng ký đất đai, tài sản gắn liền với đất, cấp giấy chứng nhận "
            "quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất lần đầu (gồm trường hợp chưa "
            "thực hiện đăng ký đất đai lần đầu; trường hợp đã có thông báo kết quả đăng ký đất đai, "
            "tài sản gắn liền với đất không thể hiện đủ điều kiện cấp giấy chứng nhận) - Miền núi, "
            "hải đảo"
        ),
        # Trang chỉ có bước thành phần hồ sơ; không chạy compact-agent/process pipeline.
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đăng ký đất đai, tài sản gắn liền với đất theo Mẫu số 15 đã kê khai.\n"
            "2. Mảnh trích đo hoặc bộ phiếu đo đạc, xác nhận hiện trạng, ranh giới thửa đất (nếu có).\n"
            "3. Các giấy tờ về nguồn gốc, quyền sử dụng đất/tài sản; nghĩa vụ tài chính hoặc biểu mẫu "
            "thuế tương ứng với hồ sơ thực tế.\n"
            "Mỗi file được phân loại theo nội dung và chỉ đính vào một hàng thành phần hồ sơ."
        ),
    },
    {
        "key": "dang-ky-bien-dong-chuyen-nhuong-quang-ninh-mien-nui-hai-dao",
        # URL /nop-ho-so/145156 có thể đổi theo cấu hình cổng; dùng domain và hai đoạn tiêu đề đặc
        # trưng để tách khỏi các nhánh đăng ký biến động khác tại Quảng Ninh.
        "detect": {
            "urlScope": ["dichvucong.quangninh.gov.vn"],
            "textIncludes": [
                "[Đặc thù] Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
                "Đối với cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài - Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Quảng Ninh] [Đặc thù] Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản "
            "gắn liền với đất trong các trường hợp chuyển đổi quyền sử dụng đất nông nghiệp mà không "
            "theo phương án dồn điền, đổi thửa; chuyển nhượng, thừa kế, tặng cho quyền sử dụng đất, "
            "quyền sở hữu tài sản gắn liền với đất, góp vốn bằng quyền sử dụng đất, quyền sở hữu tài "
            "sản gắn liền với đất; cho thuê, cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh "
            "doanh kết cấu hạ tầng; bán hoặc tặng cho hoặc để thừa kế hoặc góp vốn bằng tài sản gắn "
            "liền với đất thuê của Nhà nước theo hình thức thuê đất trả tiền hàng năm; chuyển quyền "
            "khai thác khoáng sản theo quy định của pháp luật về địa chất và khoáng sản - Chuyển đổi "
            "quyền sử dụng đất nông nghiệp mà không theo phương án dồn điền, đổi thửa hoặc trường hợp "
            "chuyển nhượng, thừa kế, tặng cho quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất, "
            "góp vốn bằng quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất; bán, thừa kế, tặng "
            "cho hoặc góp vốn bằng tài sản gắn liền với đất được Nhà nước cho thuê đất thu tiền thuê "
            "đất hằng năm - Đối với cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài "
            "- Miền núi, hải đảo"
        ),
        # Trang chỉ có bước thành phần hồ sơ; không chạy compact-agent/process pipeline.
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18.\n"
            "2. Giấy chứng nhận đã cấp và hợp đồng/văn bản chuyển quyền tương ứng.\n"
            "3. Mảnh trích đo, các tờ khai lệ phí trước bạ, thuế sử dụng đất và thuế thu nhập cá nhân "
            "theo hồ sơ thực tế.\n"
            "4. Nếu thực hiện thông qua người đại diện: văn bản đại diện hoặc ủy quyền.\n"
            "Mỗi file được phân loại theo tài liệu chính và chỉ đính vào một thành phần hồ sơ."
        ),
    },
    {
        "key": "chuyen-muc-dich-su-dung-dat-quang-ninh-mien-nui-hai-dao",
        # URL /nop-ho-so/145077 có thể đổi theo cấu hình cổng; khóa domain và các đoạn tiêu đề
        # đặc trưng để tách khỏi những biến thể cùng nhóm đất đai tại Quảng Ninh.
        "detect": {
            "urlScope": ["dichvucong.quangninh.gov.vn"],
            "textIncludes": [
                "[Đặc thù] Thủ tục chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất",
                "Trường hợp thuê đất trả tiền thuê đất hằng năm",
                "Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Quảng Ninh] [Đặc thù] Thủ tục chuyển mục đích sử dụng đất; chuyển hình thức sử "
            "dụng đất; gia hạn sử dụng đất khi hết thời hạn sử dụng đất; điều chỉnh thời hạn sử dụng "
            "đất của dự án đầu tư - Trường hợp thuê đất trả tiền thuê đất hằng năm hoặc trường hợp dự "
            "án có nhiều hình thức sử dụng đất mà không có trường hợp nào thuộc thẩm quyền của chủ "
            "tịch ủy ban nhân dân tỉnh theo quy định - Miền núi, hải đảo"
        ),
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Tải lên các giấy tờ đúng với nhánh hồ sơ thực tế: đơn chuyển mục đích Mẫu số 02, đơn "
            "chuyển hình thức Mẫu số 03, đơn gia hạn Mẫu số 23 hoặc đơn điều chỉnh thời hạn dự án Mẫu "
            "số 10; kèm Giấy chứng nhận, trích lục, quyết định/văn bản dự án và tờ khai thuế tương ứng.\n"
            "Nếu nộp thay, tải thêm văn bản ủy quyền. Mỗi file chỉ được đính vào một thành phần hồ sơ."
        ),
    },
    {
        "key": "dang-ky-dat-dai-lan-dau-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay + select2) — dùng engine fill-bacninh.js.
        "detect": {"urlIncludes": ["maThuTucHanhChinh=1.013978"]},
        "label": (
            "[Tỉnh Bắc Ninh] Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử "
            "dụng đất, quyền sở hữu tài sản gắn liền với đất lần đầu"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký đất đai (Mẫu số 15) người yêu cầu đã khai — dùng để tự động điền thân đơn.\n"
            "2. CCCD/giấy tờ tùy thân của người đề nghị.\n"
            "3. Nếu có: Giấy chứng nhận kết hôn (đồng sử dụng), Mẫu 15a (danh sách đồng sử dụng), "
            "phiếu thu/chứng từ tài chính, giấy tờ nguồn gốc đất, hợp đồng ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Điền đơn: khớp ô theo NHÃN (Họ tên, Địa chỉ, thửa đất, diện tích, mục đích, thời hạn, nguồn "
            "gốc...) + người nhận kết quả; ô 'Đề nghị' tự tick a) đăng ký + b) cấp Giấy chứng nhận.\n"
            "Đính kèm: Đơn Mẫu 15→KQ005747, Mẫu 15a→KQ006106, phiếu thu→KQ006110, ủy quyền→KQ005910, "
            "giấy tờ nguồn gốc→KQ006114; CCCD/kết hôn→ô đính kèm bổ sung. Cơ quan tiếp nhận, tỉnh/phường "
            "người nhận và khối ủy quyền là select/khối riêng theo địa bàn — chọn/khai tay."
        ),
    },
    {
        "key": "thu-hoi-gcn-cap-sai-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay + select2) — dùng engine fill-bacninh.js.
        "detect": {"urlIncludes": ["maThuTucHanhChinh=1.012818"]},
        "label": (
            "[Tỉnh Bắc Ninh] Thu hồi Giấy chứng nhận đã cấp lần đầu không đúng quy định do người sử dụng "
            "đất, chủ sở hữu tài sản gắn liền với đất phát hiện và cấp lại Giấy chứng nhận sau khi thu hồi"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Văn bản kiến nghị việc cấp GCN không đúng quy định (thường là Biên bản họp gia đình).\n"
            "2. Bản gốc Giấy chứng nhận QSDĐ (sổ đỏ) đang xin thu hồi.\n"
            "3. CCCD/giấy tờ tùy thân của chủ hồ sơ.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Điền đơn: khớp ô theo NHÃN (Kính gửi, a) Tên, b) Giấy tờ nhân thân, c) Địa chỉ, d) Số điện thoại) "
            "+ người nhận kết quả.\n"
            "Đính kèm: Văn bản kiến nghị→KQ004767, GCN bản gốc→KQ004768; CCCD/khác→ô đính kèm bổ sung. "
            "Cơ quan tiếp nhận + tỉnh/phường người nhận + khối ủy quyền là select/khối riêng theo địa bàn — "
            "chọn/khai tay."
        ),
    },
    {
        "key": "dang-ky-bien-dong-chuyen-nhuong-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay + select2) — dùng engine fill-bacninh.js.
        "detect": {"urlIncludes": ["maThuTucHanhChinh=1.013831"]},
        "label": (
            "[Tỉnh Bắc Ninh] Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất "
            "trong các trường hợp chuyển nhượng, thừa kế, tặng cho, góp vốn bằng quyền sử dụng đất, quyền "
            "sở hữu tài sản gắn liền với đất; cho thuê, cho thuê lại quyền sử dụng đất"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai (Mẫu số 18) bên NHẬN chuyển quyền đã khai — dùng để điền thân đơn.\n"
            "2. Bản gốc Giấy chứng nhận QSDĐ đã cấp (sổ đỏ/sổ hồng).\n"
            "3. Hợp đồng/văn bản chuyển quyền (chuyển nhượng/tặng cho/thừa kế/góp vốn) + Lời chứng chứng thực/công chứng.\n"
            "4. CCCD/giấy tờ tùy thân của bên nhận (và các bên).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Lưu ý: mọi thông tin điền là của BÊN NHẬN chuyển quyền (Bên B), không phải bên chuyển.\n"
            "Điền đơn: khớp ô theo NHÃN (Kính gửi, a) Tên, b) Giấy tờ nhân thân, c) Địa chỉ, d) Điện thoại, "
            "2. Nội dung biến động, (3) hợp đồng) + khối người nhận kết quả (họ tên, CCCD, SĐT, địa chỉ).\n"
            "Đính kèm: Đơn Mẫu 18→KQ005897, GCN gốc→KQ0777, Hợp đồng chuyển quyền→KQ005898 (và các thành phần "
            "KQ005899–KQ005907, KQ004869 khi có); CCCD/khác→ô đính kèm bổ sung. Cơ quan tiếp nhận và tỉnh/phường "
            "người nhận là select theo địa bàn — chọn tay."
        ),
    },
    {
        "key": "tach-hop-thua-dat-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay + select2) — dùng engine fill-bacninh.js.
        "detect": {"urlIncludes": ["maThuTucHanhChinh=1.012784"]},
        "label": "[Tỉnh Bắc Ninh] Tách thửa đất hoặc hợp thửa đất",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị tách thửa/hợp thửa đất (Mẫu số 21) chủ đất đã khai — dùng để điền thân đơn.\n"
            "2. Giấy chứng nhận QSDĐ (sổ đỏ/sổ hồng) đã cấp.\n"
            "3. Bản vẽ tách thửa/hợp thửa (Mẫu số 22).\n"
            "4. CCCD/giấy tờ tùy thân của chủ đất; nếu có: văn bản của cơ quan thẩm quyền về tách/hợp thửa.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Điền đơn (chỉ nhánh TÁCH THỬA): khớp ô theo NHÃN (Kính gửi, a) Tên, b) Giấy tờ nhân thân, thửa "
            "đất số/tờ bản đồ/diện tích/loại đất/địa chỉ thửa/số vào sổ GCN/ngày cấp, diện tích thửa mới, lý "
            "do, giấy tờ kèm, đề nghị cấp GCN) + khối người nhận kết quả (họ tên, CCCD, SĐT, địa chỉ).\n"
            "Đính kèm: Đơn Mẫu 21→KQ006017, GCN→KQ004751, Văn bản cơ quan→KQ004752, Bản vẽ Mẫu 22→KQ006018; "
            "CCCD/khác→ô đính kèm bổ sung.\n"
            "Để user tự làm: Tỉnh/Xã (địa chỉ thường trú) là select cascade; nhánh HỢP THỬA (nếu có); cơ quan "
            "tiếp nhận và tỉnh/phường người nhận."
        ),
    },
    {
        "key": "cap-doi-gcn-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay + select2) — dùng engine fill-bacninh.js.
        # Cấu trúc = đơn Mẫu 18 (giống đính chính) + khối người nhận kết quả (giống thu hồi).
        "detect": {"urlIncludes": ["maThuTucHanhChinh=1.012783"]},
        "label": "[Tỉnh Bắc Ninh] Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai (Mẫu số 18) người yêu cầu đã khai — dùng để điền thân đơn.\n"
            "2. Bản gốc Giấy chứng nhận QSDĐ đã cấp (sổ đỏ/sổ hồng) cần cấp đổi.\n"
            "3. CCCD/giấy tờ tùy thân của người sử dụng đất; nếu có: văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Điền đơn: khớp ô theo NHÃN (Kính gửi, a) Tên, b) Giấy tờ nhân thân, c) Địa chỉ, d) Điện thoại, "
            "2. Nội dung biến động [Cấp đổi GCN], (2)(3) giấy tờ liên quan) + khối người nhận kết quả (họ "
            "tên, CCCD, SĐT, địa chỉ).\n"
            "Đính kèm: Đơn Mẫu 18 + CCCD → nhóm 'Đơn đăng ký biến động đất đai... Mẫu số 18'; Bản gốc GCN → "
            "nhóm 'Bản gốc Giấy chứng nhận đã cấp'.\n"
            "Để user tự làm: cơ quan tiếp nhận, hình thức/nơi nhận kết quả, tỉnh/phường người nhận (select "
            "theo địa bàn)."
        ),
    },
    {
        "key": "dinh-chinh-gcn-da-cap-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay + select2) — dùng engine fill-bacninh.js.
        # Cấu trúc = đơn Mẫu 18 + người nhận (giống cấp đổi) + đính kèm 4 nhóm (giống đính chính sai sót).
        "detect": {"urlIncludes": ["maThuTucHanhChinh=1.012790"]},
        "label": "[Tỉnh Bắc Ninh] Đính chính giấy chứng nhận đã cấp",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai (Mẫu số 18) người yêu cầu đã khai — dùng để điền thân đơn.\n"
            "2. Bản gốc Giấy chứng nhận QSDĐ đã cấp (sổ đỏ/sổ hồng).\n"
            "3. Giấy tờ chứng minh sai sót thông tin trên GCN (giấy khai sinh, CCCD, quyết định...).\n"
            "4. CCCD/giấy tờ tùy thân của người sử dụng đất; nếu có: văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Điền đơn: khớp ô theo NHÃN (Kính gửi, a) Tên, b) Giấy tờ nhân thân, c) Địa chỉ, d) Điện thoại, "
            "2. Nội dung biến động [đính chính], (2)(3) giấy tờ liên quan) + khối người nhận kết quả (họ "
            "tên, CCCD, SĐT, địa chỉ).\n"
            "Đính kèm: Đơn Mẫu 18 + CCCD → nhóm 'Đơn đăng ký biến động đất đai... Mẫu số 18'; Bản gốc GCN → "
            "nhóm 'Bản gốc Giấy chứng nhận đã cấp'; giấy chứng minh sai sót → nhóm 'Giấy tờ chứng minh sai "
            "sót'; văn bản ủy quyền → nhóm 'Văn bản về việc ủy quyền'.\n"
            "Để user tự làm: cơ quan tiếp nhận, hình thức/nơi nhận kết quả, tỉnh/phường người nhận (select "
            "theo địa bàn)."
        ),
    },
    {
        "key": "dieu-chinh-dat-dai",
        "detect": {"textIncludes": ["điều chỉnh", "giao đất"], "headingDisabled": True},
        "label": "Điều chỉnh quyết định giao đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất",
        "mode": "agent",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của người nộp hồ sơ.\n"
            "2. Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất."
        ),
    },
    {
        "key": "cap-giay-phep-xay-dung-moi-nha-o-rieng-le",
        "detect": {
            "urlIncludes": ["maThuTuc=1.013225"],
            "textIncludes": [
                "cấp giấy phép xây dựng mới",
                "công trình cấp iii",
                "nhà ở riêng lẻ",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Cấp giấy phép xây dựng mới đối với công trình cấp III, cấp IV "
            "và nhà ở riêng lẻ"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn đề nghị cấp phép xây dựng.\n"
            "2. CCCD/giấy tờ định danh của chủ hộ/người nộp.\n"
            "3. Giấy chứng nhận quyền sử dụng đất hoặc giấy tờ về quyền sử dụng đất.\n"
            "4. Bản vẽ xin cấp phép xây dựng, bản kê khai/chứng chỉ năng lực thiết kế, "
            "chứng chỉ hành nghề chủ nhiệm/chủ trì thiết kế nếu có.\n"
            "Bước thành phần hồ sơ: đính từng file vào các hàng có sẵn: "
            "Đơn + CCCD + Bản cam kết vào STT 1; Sổ đỏ/GCN QSDĐ vào STT 11; "
            "Bản vẽ + kê khai + chứng chỉ thiết kế vào STT 27."
        ),
    },
    {
        "key": "dang-ky-dat-dai-lan-dau",
        # Cổng laichau (SPA) — urlScope gate đúng cổng laichau.gov.vn + dấu tỉnh "lai châu" (chống dính trang lạ).
        "detect": {"urlScope": ["laichau.gov.vn"], "textIncludes": ["đăng ký đất đai", "lần đầu", "tổ chức đang sử dụng đất", "lai châu"], "headingDisabled": True},
        "label": "[Lai Châu] Đăng ký đất đai, tài sản gắn liền với đất, cấp giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất lần đầu đối với tổ chức đang sử dụng đất",
        "mode": "agent",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của người nộp hồ sơ.\n"
            "2. Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất."
        ),
    },
    {
        "key": "dang-ky-dat-dai-tai-san-lan-dau-nguoi-o-nuoc-ngoai",
        "detect": {"urlScope": ["laichau.gov.vn"], "textIncludes": [
            "Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất lần đầu đối với hộ gia đình, cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài",
            "lai châu",
        ], "headingDisabled": True},
        "label": "[Lai Châu] Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất lần đầu đối với hộ gia đình, cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài",
        "mode": "agent",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của người nộp hồ sơ.\n"
            "2. Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất."
        ),
    },
    {
        "key": "dang-ky-lap-dat-su-dung-nuoc-sach",
        "detect": {"textIncludes": ["đăng ký lắp đặt sử dụng nước sạch"], "headingDisabled": True},
        "label": "Thủ tục đăng ký lắp đặt sử dụng nước sạch",
        "mode": "agent",
        "roles": [],
        "useDangKyBy": False,
        "hasAttachmentStep": True,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của người nộp hồ sơ.\n"
            "2. Đơn đăng ký/đơn đề nghị cấp nước sạch.\n"
            "3. Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất nếu là hộ gia đình/cá nhân.\n"
            "4. Giấy ĐKKD/giấy tờ tổ chức nếu là doanh nghiệp/cơ quan/tổ chức."
        ),
    },
    {
        "key": "chuyen-doi-ten-hop-dong-nuoc-sach",
        "detect": {"textIncludes": ["chuyển đổi tên trong hợp đồng dịch vụ sử dụng nước sạch"], "headingDisabled": True},
        "label": "Thủ tục chuyển đổi tên trong Hợp đồng dịch vụ sử dụng nước sạch",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của người nộp hồ sơ.\n"
            "2. Đơn xin đổi tên trong hợp đồng dịch vụ cấp nước.\n"
            "3. Giấy chứng nhận quyền sử dụng đất/quyền sở hữu tài sản gắn liền với đất.\n"
            "4. Nếu là doanh nghiệp/cơ quan/tổ chức: giấy ĐKKD, quyết định thành lập hoặc giấy tờ thuê/ủy quyền liên quan."
        ),
    },
    {
        "key": "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham",
        "detect": {
            "textIncludes": [
                "Cấp giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm đối với cơ sở kinh doanh dịch vụ ăn uống, cơ sở sản xuất thực phẩm thuộc phạm vi quản lý của Bộ Y tế"
            ],
            "headingDisabled": True,
        },
        "label": (
            "Cấp giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm đối với cơ sở kinh doanh "
            "dịch vụ ăn uống, cơ sở sản xuất thực phẩm thuộc phạm vi quản lý của Bộ Y tế"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của người nộp hồ sơ.\n"
            "2. Đơn đề nghị cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm.\n"
            "3. Nếu có: giấy khám sức khỏe, biên bản/kết luận giám định y khoa hoặc giấy tờ liên quan."
        ),
    },
    {
        "key": "cap-gcn-attp-nong-lam-thuy-san",
        "detect": {
            "urlIncludes": [
                "apply-online/693a99efda87c4718ece1bc7",
                "process=695dbb6de184634c1f3648af",
            ],
            "headingDisabled": True,
        },
        "label": (
            "Cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm đối với cơ sở sản xuất, "
            "kinh doanh thực phẩm nông, lâm, thủy sản"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. CCCD của người nộp hồ sơ.\n"
            "2. Nếu người nộp khác đại diện/chủ cơ sở: CCCD của đại diện/chủ cơ sở.\n"
            "3. Đơn đề nghị cấp Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm theo Phụ lục I.\n"
            "4. Bản thuyết minh điều kiện bảo đảm an toàn thực phẩm theo Phụ lục II.\n"
            "5. Nếu có: Giấy chứng nhận đăng ký kinh doanh/doanh nghiệp/hộ kinh doanh để đối chiếu."
        ),
    },
    {
        "key": "cap-lai-giay-chung-nhan-du-dieu-kien-an-toan-thuc-pham",
        "detect": {
            "textIncludes": [
                "Cấp lại Giấy chứng nhận đủ điều kiện an toàn thực phẩm đối với cơ sở sản xuất, kinh doanh thực phẩm"
            ],
            "headingDisabled": True,
        },
        "label": "Cấp lại Giấy chứng nhận đủ điều kiện an toàn thực phẩm đối với cơ sở sản xuất, kinh doanh thực phẩm",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp lại Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm.\n"
            "2. Giấy chứng nhận cơ sở đủ điều kiện an toàn thực phẩm đã được cấp.\n"
            "3. Nếu có: giấy đăng ký doanh nghiệp/địa điểm kinh doanh, bản thuyết minh CSVC, "
            "giấy xác nhận tập huấn ATTP, danh sách/giấy xác nhận đủ sức khỏe, giấy ủy quyền."
        ),
    },
    {
        "key": "ho-tro-mai-tang",
        "detect": {
            "urlIncludes": ["maThuTuc=1.001731"],
            "textIncludes": ["Hỗ trợ chi phí mai táng cho đối tượng bảo trợ xã hội"],
            "headingDisabled": True,
        },
        "label": "Hỗ trợ chi phí mai táng cho đối tượng bảo trợ xã hội",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Nếu người nộp hồ sơ là chủ hồ sơ: tải CCCD của người đó.\n"
            "2. Nếu người nộp và chủ hồ sơ khác nhau: tải CCCD của cả hai người; "
            "hệ thống sẽ so với thông tin người nộp đang có trên form để xác định chủ hồ sơ.\n"
            "Bước 3 (đính kèm) — chuẩn bị các giấy tờ sau, hệ thống tự xếp vào đúng ô:\n"
            "1. Tờ khai đề nghị hỗ trợ chi phí mai táng (Mẫu số 04).\n"
            "2. Bản sao giấy chứng tử/giấy báo tử (hoặc trích lục khai tử) của đối tượng.\n"
            "3. Nếu có: bản sao quyết định/danh sách thôi hưởng trợ cấp BHXH."
        ),
    },
    {
        "key": "ho-tro-mai-tang-huu-tri-xa-hoi",
        "detect": {
            "textIncludes": ["Hỗ trợ chi phí mai táng đối với đối tượng hưởng trợ cấp hưu trí xã hội"],
            "headingDisabled": True,
        },
        "label": "Hỗ trợ chi phí mai táng đối với đối tượng hưởng trợ cấp hưu trí xã hội",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Nếu người nộp hồ sơ là chủ hồ sơ: tải CCCD của người đó.\n"
            "2. Nếu người nộp và chủ hồ sơ khác nhau: tải CCCD của cả hai người; "
            "hệ thống sẽ so với thông tin người nộp đang có trên form để xác định chủ hồ sơ.\n"
            "Bước 3 (đính kèm) — chuẩn bị các giấy tờ sau, hệ thống tự xếp vào đúng ô:\n"
            "1. Tờ khai đề nghị hỗ trợ chi phí mai táng (Mẫu số 04).\n"
            "2. Bản sao giấy chứng tử/giấy báo tử (hoặc trích lục khai tử) của đối tượng.\n"
            "3. Nếu có: bản sao quyết định/danh sách thôi hưởng trợ cấp BHXH."
        ),
    },
    {
        "key": "dieu-chinh-huu-tri-xa-hoi",
        "detect": {
            "urlIncludes": ["maThuTuc=1.014027"],
            "textIncludes": ["Thực hiện, điều chỉnh, thôi hưởng trợ cấp hưu trí xã hội"],
            "headingDisabled": True,
        },
        "label": "Thực hiện, điều chỉnh, thôi hưởng trợ cấp hưu trí xã hội",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Văn bản đề nghị Mẫu số 01.\n"
            "2. CCCD của người nộp/chủ hồ sơ.\n"
            "Hệ thống lấy chủ hồ sơ từ mục thông tin người đề nghị cấp/hưởng trợ cấp hưu trí xã hội."
        ),
    },
    {
        "key": "mai-tang-dan-cong-hoa-tuyen",
        "detect": {
            "textIncludes": [
                "Giải quyết chế độ mai táng phí đối với dân công hỏa tuyến tham gia kháng chiến chống Pháp, chống Mỹ, chiến tranh bảo vệ Tổ quốc và làm nhiệm vụ quốc tế"
            ],
            "headingDisabled": True,
        },
        "label": (
            "Giải quyết chế độ mai táng phí đối với dân công hỏa tuyến tham gia kháng chiến chống Pháp, "
            "chống Mỹ, chiến tranh bảo vệ Tổ quốc và làm nhiệm vụ quốc tế"
        ),
        "mode": "agent",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Bản khai của thân nhân đề nghị hưởng chế độ mai táng phí theo Quyết định số 49/2015/QĐ-TTg.\n"
            "2. CCCD/CMND của thân nhân/người đứng khai nhận trợ cấp."
        ),
    },
    {
        "key": "xac-dinh-muc-do-khuyet-tat",
        "detect": {
            "urlIncludes": ["maThuTuc=1.001699"],
            "textIncludes": ["Xác định, xác định lại mức độ khuyết tật và cấp Giấy xác nhận khuyết tật"],
            "headingDisabled": True,
        },
        "label": "Xác định, xác định lại mức độ khuyết tật và cấp Giấy xác nhận khuyết tật",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị xác định/xác định lại mức độ khuyết tật.\n"
            "2. CCCD của chủ hồ sơ/người đại diện đứng đơn.\n"
            "Bước 3 (đính kèm) — chuẩn bị nếu có:\n"
            "1. Bản sao giấy tờ liên quan đến khuyết tật: bệnh án, giấy khám, điều trị, phẫu thuật.\n"
            "2. Bản sao kết luận của Hội đồng Giám định y khoa/kết luận cơ sở y tế.\n"
            "3. Đơn đề nghị theo Mẫu số 01."
        ),
    },
    {
        "key": "xet-tuyen-vien-chuc",
        "detect": {"textIncludes": ["Thủ tục xét tuyển Viên chức (85/2023/NĐ-CP)"], "headingDisabled": True},
        "label": "Thủ tục xét tuyển Viên chức (85/2023/NĐ-CP)",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Phiếu đăng ký dự tuyển theo Mẫu số 01.\n"
            "2. Nếu người nộp khác người dự tuyển: CCCD của người nộp hồ sơ.\n"
            "Hệ thống lấy chủ hồ sơ từ phiếu đăng ký, rồi so với thông tin người nộp trên form."
        ),
    },
    {
        "key": "xet-tuyen-vien-chuc-lai-chau",
        # Cổng dichvucong.laichau.gov.vn — eForm chuẩn Lai Châu (CongDan_*, _fc*), engine fillFormStandard.
        # KHÁC "xet-tuyen-vien-chuc" (Form.io data[...]). SPA dùng chung domain → detect theo VĂN BẢN tên
        # thủ tục + "lai châu" (đặc trưng, không đụng bản Form.io do cụm "(Nghị định số 85..." khác).
        "detect": {
            "urlScope": ["laichau.gov.vn"],
            "textIncludes": ["Thủ tục xét tuyển Viên Chức (Nghị định số 85/2023/NĐ-CP) (Lai Châu)"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Tỉnh Lai Châu] Thủ tục xét tuyển Viên Chức (Nghị định số 85/2023/NĐ-CP) (Lai Châu)",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Phiếu đăng ký dự tuyển theo Mẫu số 01 (Nghị định 85/2023/NĐ-CP).\n"
            "2. CCCD của người dự tuyển.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "E-form chỉ thu THÔNG TIN NGƯỜI DỰ TUYỂN (họ tên, ngày sinh, giới tính, dân tộc, CCCD, ngày/nơi "
            "cấp, tỉnh/phường/địa chỉ thường trú, di động, email). Chi tiết dự tuyển (đào tạo, gia đình, quá "
            "trình công tác, nguyện vọng) nằm trong Phiếu Mẫu 01 đính kèm, không nhập e-form.\n"
            "Tỉnh/Phường/Dân tộc là dropdown Semantic UI — extension tự chọn theo tên (theo nơi thường trú, "
            "tên phường/xã MỚI sau sáp nhập).\n"
            "Đính kèm: Phiếu Mẫu 01 + CCCD → ô 'Phiếu đăng ký dự tuyển theo mẫu số 01'."
        ),
    },
    {
        "key": "xet-tuyen-cong-chuc",
        "detect": {"textIncludes": ["Xét tuyển công chức"], "headingDisabled": True, "textPriority": True},
        "label": "Xét tuyển công chức",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Phiếu đăng ký dự tuyển theo Mẫu số 01.\n"
            "2. Nếu có: CCCD/giấy tờ định danh hoặc tài liệu khác theo yêu cầu của cơ quan tuyển dụng.\n"
            "Hệ thống lấy người nộp/chủ hồ sơ và toàn bộ mẫu khai chi tiết từ Phiếu đăng ký dự tuyển."
        ),
    },
    {
        "key": "thi-tuyen-cong-chuc",
        "detect": {"textIncludes": ["Thi tuyển công chức"], "headingDisabled": True, "textPriority": True},
        "label": "Thi tuyển công chức",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Phiếu đăng ký dự tuyển theo Mẫu số 01.\n"
            "2. Nếu có: CCCD/giấy tờ định danh hoặc tài liệu khác theo yêu cầu của cơ quan tuyển dụng.\n"
            "Hệ thống lấy người nộp/chủ hồ sơ và toàn bộ mẫu khai chi tiết từ Phiếu đăng ký dự tuyển."
        ),
    },
    {
        "key": "cap-lai-to-quoc-ghi-cong",
        "detect": {
            "textIncludes": ["Cấp lại Bằng", "Tổ quốc ghi công"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": 'Cấp lại Bằng "Tổ quốc ghi công"',
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị cấp đổi/cấp lại Bằng \"Tổ quốc ghi công\" (Mẫu số 16) — nguồn chính điền mẫu khai.\n"
            "2. CCCD của người đề nghị (bản sao chứng thực) — bổ sung số định danh, ngày/nơi cấp, nơi cư trú.\n"
            "3. Nếu có: Bằng \"Tổ quốc ghi công\" cũ, Công văn của UBND cấp xã, Danh sách đề nghị cấp lại.\n"
            "Bước đính kèm: Đơn Mẫu 16 vào ô số 1; CCCD/Công văn/Danh sách xếp vào mục 'Thêm giấy tờ'."
        ),
    },
    {
        "key": "bo-sung-than-nhan-liet-si",
        "detect": {
            "urlIncludes": ["maThuTuc=1.010825"],
            "textIncludes": ["Bổ sung tình hình thân nhân trong hồ sơ liệt sĩ"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Bổ sung tình hình thân nhân trong hồ sơ liệt sĩ",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị Sửa đổi, bổ sung thông tin trong hồ sơ liệt sĩ (Mẫu số 26/06) — nguồn chính điền mẫu khai.\n"
            "2. CCCD của người khai (bản sao chứng thực) — bổ sung số định danh, ngày/nơi cấp, nơi cư trú.\n"
            "3. Bản sao chứng thực giấy tờ chứng minh quan hệ với liệt sĩ (CCCD/giấy khai sinh/trích lục khai sinh/"
            "đăng ký kết hôn/lý lịch) của các thân nhân.\n"
            "4. Nếu có: Hồ sơ liệt sĩ gốc, Bằng \"Tổ quốc ghi công\", Công văn của UBND cấp xã.\n"
            "Bước đính kèm: giấy tờ chứng minh quan hệ vào ô số 1, Đơn Mẫu 26 vào ô số 2; "
            "Hồ sơ liệt sĩ/Bằng TQGC/Công văn xếp vào mục 'Thêm giấy tờ'."
        ),
    },
    {
        "key": "tham-vieng-mo-liet-si",
        "detect": {
            "textIncludes": ["Thăm viếng mộ liệt sĩ"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Thăm viếng mộ liệt sĩ",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy giới thiệu/Đơn đề nghị thăm viếng mộ liệt sĩ (Mẫu 31/42) — nguồn chính điền mẫu khai.\n"
            "2. CCCD của người khai (bản sao) — bổ sung số định danh, ngày/nơi cấp, nơi cư trú.\n"
            "3. Nếu có: Bằng \"Tổ quốc ghi công\", trích lục hồ sơ liệt sĩ/giấy xác nhận nơi hy sinh (Mẫu 44), "
            "giấy chứng nhận thân nhân liệt sĩ/QĐ trợ cấp thờ cúng.\n"
            "Bước đính kèm: hồ sơ/trích lục liệt sĩ vào ô 1, giấy chứng nhận thân nhân vào ô 2, "
            "Đơn/Giấy giới thiệu vào ô 3; CCCD/Bằng TQGC xếp vào mục 'Thêm giấy tờ'."
        ),
    },
    {
        "key": "tro-cap-tho-cung-liet-si",
        "detect": {
            "textIncludes": ["Giải quyết chế độ trợ cấp thờ cúng liệt sĩ"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Giải quyết chế độ trợ cấp thờ cúng liệt sĩ",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị giải quyết chế độ trợ cấp thờ cúng liệt sĩ (Mẫu số 18) — nguồn chính điền mẫu khai.\n"
            "2. CCCD của người đề nghị (bản sao) — bổ sung số định danh, ngày/nơi cấp, nơi cư trú.\n"
            "3. Bản sao chứng thực Bằng \"Tổ quốc ghi công\" — thông tin liệt sĩ (số bằng, quyết định, quê quán).\n"
            "4. Nếu có: Văn bản ủy quyền thờ cúng, Trích lục khai tử của thân nhân liệt sĩ.\n"
            "Bước đính kèm: Văn bản ủy quyền vào ô 1, Đơn Mẫu 18 vào ô 2, Bằng TQGC vào ô 3; "
            "CCCD/Trích lục khai tử xếp vào mục 'Thêm giấy tờ'."
        ),
    },
    {
        "key": "uu-dai-ncc-tu-tran",
        "detect": {
            "urlIncludes": ["apply-online/696072f4b066193e95eb9d5e", "process=69706da26cabcb44db2cea08"],
            "textIncludes": ["Hưởng trợ cấp khi người có công đang hưởng trợ cấp ưu đãi từ trần"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Hưởng trợ cấp khi người có công đang hưởng trợ cấp ưu đãi từ trần",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Bản khai giải quyết chế độ ưu đãi khi người có công từ trần (Mẫu số 12) — nguồn chính điền mẫu khai.\n"
            "2. CCCD của người khai/người nhận trợ cấp (bản sao).\n"
            "3. Trích lục khai tử/giấy báo tử của người có công đã từ trần.\n"
            "4. Nếu có: giấy khai sinh (thân nhân là con chưa đủ 18 tuổi), biên bản họp gia đình, danh sách đề nghị.\n"
            "Lưu ý: người khai (còn sống) và người có công từ trần là HAI người khác nhau.\n"
            "Bước đính kèm: Bản khai Mẫu 12 vào ô 1; CCCD/trích lục khai tử/khác xếp vào mục 'Thêm giấy tờ'."
        ),
    },
    {
        "key": "giai-quyet-che-do-khang-chien",
        # Cổng Bộ Nội vụ dichvucongbnv.moha.gov.vn — Form.io, engine fillFormStandard dom-* + attach MOHA
        # ("Chọn tệp"). URL SPA khác nhau theo ObjectId và process ID → detect theo urlIncludes + text.
        "detect": {
            "urlIncludes": ["apply-online/6960726b36973e2430327813", "process=69706a4ce528a8797931839f"],
            "textIncludes": ["hoạt động kháng chiến giải phóng dân tộc", "làm nghĩa vụ quốc tế"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Giải quyết chế độ người hoạt động kháng chiến giải phóng dân tộc, bảo vệ Tổ quốc "
            "và làm nghĩa vụ quốc tế"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Bản khai theo Mẫu số 11 (Phụ lục I Nghị định 131/2021, có xác nhận UBND cấp xã) — nguồn chính.\n"
            "2. CCCD của đối tượng hoạt động kháng chiến.\n"
            "3. Giấy chứng nhận Huân/Huy chương Kháng chiến, Chiến thắng (hoặc quyết định tặng thưởng).\n"
            "4. Nếu có: Sổ BHXH (quá trình đóng BHXH) để bổ sung quá trình tham gia kháng chiến.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Đối tượng là chủ hồ sơ (thường còn sống, tự khai): extension BỎ TÍCH ô 'Người nộp là chủ hồ sơ' "
            "để mở Phần II rồi điền chủ hồ sơ + Phần IV Mục 1. Phần V (đại diện thân nhân) chỉ khi đối tượng "
            "đã chết. Phần I (người nộp) hệ thống tự đổ từ tài khoản.\n"
            "Bước đính kèm: Bản khai Mẫu 11 → ô 1; Giấy báo tử → ô 2 (nếu có); Huân/Huy chương → ô 3; "
            "CCCD/Sổ BHXH → mục 'Thêm giấy tờ'."
        ),
    },
    {
        "key": "sua-doi-thong-tin-ho-so-nguoi-co-cong",
        # Cổng Bộ Nội vụ dichvucongbnv.moha.gov.vn — Form.io, engine fillFormStandard dom-* + attach MOHA
        # ("Chọn tệp"). URL SPA không có MaTTHC trong DOM → detect theo cụm tên thủ tục (như MOHA khác).
        "detect": {
            "textIncludes": ["sửa đổi, bổ sung thông tin", "hồ sơ người có công"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Sửa đổi, bổ sung thông tin cá nhân trong hồ sơ người có công",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn đề nghị theo Mẫu số 26 (Phụ lục I Nghị định 131/2021) — nguồn chính về nội dung sửa đổi.\n"
            "2. CCCD của người khai đơn (thân nhân đứng đơn) — nguồn nhân thân người nộp.\n"
            "3. Nếu có: Bản khai thân nhân, Giấy khai sinh, Trích lục khai tử của liệt sĩ, Bằng Tổ quốc ghi công, "
            "Công văn/Tờ trình của Sở Nội vụ để bổ sung nội dung đơn.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form do MỘT người khai (thân nhân = người nộp = chủ hồ sơ); người có công (liệt sĩ) chỉ xuất hiện "
            "ở tên hồ sơ và nội dung đề nghị sửa. Extension TÍCH ô 'Người nộp là chủ hồ sơ' (ẩn Phần II) rồi "
            "điền Phần I + Phần IV (nội dung đơn Mẫu 26).\n"
            "Bước đính kèm: CCCD → ô 1; Đơn đề nghị Mẫu 26 → ô 2. Các giấy tờ khác đính kèm bổ sung thủ công."
        ),
    },
    {
        "key": "di-chuyen-ho-so-nguoi-huong-tro-cap",
        # Cổng Bộ Nội vụ dichvucongbnv.moha.gov.vn — Form.io, engine fillFormStandard dom-* + attach MOHA
        # ("Chọn tệp"). URL SPA không có MaTTHC trong DOM → detect theo cụm tên thủ tục.
        "detect": {
            "textIncludes": ["di chuyển hồ sơ", "trợ cấp ưu đãi"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Di chuyển hồ sơ khi người hưởng trợ cấp ưu đãi thay đổi nơi thường trú",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn đề nghị di chuyển hồ sơ theo Mẫu số 27 (Phụ lục I Nghị định 131/2021) — nguồn chính.\n"
            "2. CCCD của người hưởng trợ cấp ưu đãi (người làm đơn).\n"
            "3. Xác nhận thông tin về cư trú (Mẫu CT07) tại nơi thường trú mới.\n"
            "4. Nếu có: Bản khai thân nhân, Giấy khai sinh, Giấy chứng nhận gia đình liệt sĩ, Bằng Tổ quốc ghi "
            "công, Phiếu báo di chuyển hồ sơ.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Người hưởng trợ cấp (chủ hồ sơ) là người làm đơn; nếu người khác NỘP THAY thì Phần I (người nộp) "
            "hệ thống tự đổ từ tài khoản, extension BỎ TÍCH ô 'Người nộp là chủ hồ sơ' rồi điền chủ hồ sơ + "
            "Phần III (đơn Mẫu 27). Người có công gốc (liệt sĩ) chỉ nêu ở tên hồ sơ và diện hưởng.\n"
            "Bước đính kèm: Đơn đề nghị Mẫu 27 → ô 1; CCCD (hoặc Xác nhận cư trú CT07) → ô 2. Giấy tờ khác "
            "đính kèm bổ sung thủ công."
        ),
    },
    {
        "key": "tro-cap-xa-hoi-hang-thang",
        # Cổng Bộ Y tế dichvucongbyt.moh.gov.vn — Form.io, engine fillFormStandard dom-* + attach BẢNG
        # checkbox (engine attp-row như ATTP). URL SPA là ObjectId không có MaTTHC → detect theo cụm tên.
        "detect": {
            "textIncludes": [
                "thực hiện, điều chỉnh, thôi hưởng trợ cấp xã hội",
                "chăm sóc, nuôi dưỡng hàng tháng",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Thực hiện, điều chỉnh, thôi hưởng trợ cấp xã hội hàng tháng, hỗ trợ kinh phí chăm sóc, "
                 "nuôi dưỡng hàng tháng",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Tờ khai đề nghị trợ giúp xã hội của đối tượng (Mẫu số 1a/1b/1c/1d/1đ) HOẶC Tờ khai nhận chăm "
            "sóc, nuôi dưỡng (Mẫu 2a/2b/03) — nguồn chính.\n"
            "2. CCCD của đối tượng hưởng trợ cấp (nếu là trẻ em thì Giấy khai sinh thay CCCD).\n"
            "3. Giấy xác nhận khuyết tật / Biên bản giám định y khoa (nếu đối tượng khuyết tật).\n"
            "4. Nếu có: Giấy xác nhận thông tin về cư trú, Giấy tờ xác nhận nhiễm HIV / đang mang thai, và "
            "CCCD của người nộp/khai thay.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Đối tượng hưởng trợ cấp (chủ hồ sơ) là người đứng tên hồ sơ; nếu người khác NỘP/KHAI THAY thì "
            "extension điền Phần 1 (người nộp) từ tài khoản + CCCD người nộp, BỎ TÍCH ô 'Người nộp là chủ hồ "
            "sơ' rồi điền Phần 2 (đối tượng).\n"
            "Bước đính kèm: mỗi giấy tờ được tick vào đúng dòng thành phần hồ sơ (Mẫu 1x/2a/2b/03, CCCD/cư "
            "trú, khai sinh, HIV, mang thai, khuyết tật) và chọn 'Scan tệp tin'."
        ),
    },
    {
        "key": "cap-moi-giay-phep-hanh-nghe-chuyen-tiep",
        # Cổng Bộ Y tế dichvucongbyt.moh.gov.vn — Form.io, engine fillFormStandard dom-* + attach BẢNG
        # attp-row (như #62 tro-cap-xa-hoi-hang-thang, field-key data[...] TRÙNG KHÍT). CHỈ MỘT người =
        # người hành nghề. URL SPA là ObjectId không có MaTTHC → detect theo cụm tên đặc trưng.
        "detect": {
            "textIncludes": [
                "cấp mới giấy phép hành nghề trong giai đoạn chuyển tiếp",
                "kiểm tra đánh giá năng lực hành nghề",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp mới giấy phép hành nghề trong giai đoạn chuyển tiếp đối với hồ sơ nộp từ ngày 01 "
                 "tháng 01 năm 2024 đến thời điểm kiểm tra đánh giá năng lực hành nghề đối với các chức "
                 "danh bác sỹ, y sỹ, điều dưỡng, hộ sinh, kỹ thuật y, dinh dưỡng lâm sàng, cấp cứu viên "
                 "ngoại viện, tâm lý lâm sàng",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền (đều là của NGƯỜI HÀNH NGHỀ đề nghị cấp phép):\n"
            "1. Đơn đề nghị cấp giấy phép hành nghề khám bệnh, chữa bệnh / Thừa nhận GPHN (Mẫu 08 PL I "
            "NĐ 96/2023) — đã ký.\n"
            "2. Bản sao văn bằng chuyên môn (bằng tốt nghiệp/cử nhân).\n"
            "3. Giấy khám sức khỏe do cơ sở KCB đủ điều kiện cấp.\n"
            "4. Sơ yếu lý lịch tự thuật của người hành nghề (Mẫu 09 PL I).\n"
            "5. Giấy xác nhận hoàn thành quá trình thực hành (Mẫu 07 PL I).\n"
            "6. 02 ảnh chân dung 4x6 nền trắng (≤ 6 tháng).\n"
            "7. Thẻ Căn cước công dân của người hành nghề để đối chiếu; nếu người KHÁC nộp thay: tải kèm "
            "CCCD của người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Nếu TỰ NỘP (người nộp = người hành nghề): extension chỉ điền Phần 1 và GIỮ tích 'Người nộp là "
            "chủ hồ sơ' — cổng tự đổ sang Phần 2. Nếu NỘP THAY: extension bỏ tích ô đó, điền Phần 1 (người "
            "nộp) và Phần 2 (người hành nghề) riêng.\n"
            "Bước đính kèm: mỗi giấy tờ được tick vào đúng dòng thành phần hồ sơ (a Đơn Mẫu 08 / b Văn bằng "
            "/ d Sức khỏe / e Sơ yếu Mẫu 09 / g Xác nhận thực hành Mẫu 07 / h Ảnh chân dung) và chọn 'Scan "
            "tệp tin' (CCCD chỉ dùng ở bước thông tin, không đính ở bước này)."
        ),
    },
    {
        "key": "cap-chung-chi-hanh-nghe-duoc",
        # Cổng Bộ Y tế dichvucongbyt.moh.gov.vn — Form.io, engine fillFormStandard dom-* + attach BẢNG
        # attp-row (field-key data[...] TRÙNG KHÍT #92/#62). 1 người=người đề nghị (tự nộp / nộp thay như
        # #92). URL SPA là ObjectId không MaTTHC → detect theo cụm tên đặc trưng.
        "detect": {
            "textIncludes": [
                "cấp chứng chỉ hành nghề dược",
                "điều 28 của luật dược",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp Chứng chỉ hành nghề dược (bao gồm cả trường hợp cấp Chứng chỉ hành nghề dược cho "
                 "người bị thu hồi Chứng chỉ hành nghề dược theo quy định tại các khoản 1, 2, 4, 5, 6, 7, "
                 "8, 9, 10, 11 Điều 28 của Luật Dược) theo hình thức xét hồ sơ",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền (đều là của NGƯỜI ĐỀ NGHỊ cấp CCHN dược):\n"
            "1. Đơn đề nghị cấp Chứng chỉ hành nghề dược (Mẫu số 02) — đã ký, kèm ảnh chân dung 4x6 (≤ 6 "
            "tháng).\n"
            "2. Thẻ Căn cước công dân / Căn cước (mặt trước + mặt sau) của người đề nghị.\n"
            "3. Văn bằng chuyên môn (bằng tốt nghiệp dược).\n"
            "4. Phiếu lý lịch tư pháp.\n"
            "5. Giấy chứng nhận đủ sức khỏe hành nghề dược (giấy khám sức khỏe).\n"
            "6. Giấy xác nhận thời gian thực hành (Mẫu số 03). Trường hợp bị THU HỒI CCHN thì thay bằng "
            "Giấy xác nhận hoàn thành đào tạo, cập nhật kiến thức chuyên môn về dược (Mẫu số 08).\n"
            "7. Nếu người KHÁC nộp thay: tải kèm CCCD của người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Nếu TỰ NỘP: extension chỉ điền Phần 1 và GIỮ tích 'Người nộp là chủ hồ sơ' — cổng tự đổ sang "
            "Phần 2. Nếu NỘP THAY: extension bỏ tích ô đó, điền Phần 1 (người nộp) và Phần 2 (người đề "
            "nghị) riêng.\n"
            "Bước đính kèm: mỗi giấy tờ được tick vào đúng dòng thành phần hồ sơ (Đơn Mẫu 02 + ảnh, văn "
            "bằng, LLTP, sức khỏe, thời gian thực hành Mẫu 03...) và chọn 'Scan tệp tin' (CCCD chỉ dùng ở "
            "bước thông tin)."
        ),
    },
    {
        "key": "cap-van-ban-chap-thuan-tau-ca",
        # Cổng Nông nghiệp & Môi trường dichvucongnnmt.mae.gov.vn — Form.io, engine fillFormStandard dom-*
        # + attach attp-row (field-key nhân thân data[...] TRÙNG KHÍT #92/#101). Có thêm nội dung tờ khai
        # Mẫu 12 (occurrence=1) + thông số tàu. URL SPA ObjectId → detect theo cụm tên đặc trưng.
        "detect": {
            "textIncludes": [
                "cấp văn bản chấp thuận đóng mới, cải hoán, thuê, mua tàu cá",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp văn bản chấp thuận đóng mới, cải hoán, thuê, mua tàu cá Việt Nam",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền (của NGƯỜI ĐỀ NGHỊ — chủ tàu/cá nhân, tổ chức đề nghị):\n"
            "1. Tờ khai về việc chấp thuận đóng mới/cải hoán/thuê/mua tàu cá (Mẫu số 12.TC) — đã ký.\n"
            "2. Thẻ Căn cước công dân / Căn cước (mặt trước + mặt sau) của người đề nghị để đối chiếu.\n"
            "3. Nếu người KHÁC nộp thay: tải kèm CCCD của người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Nếu TỰ NỘP: extension chỉ điền Phần 1 và GIỮ tích 'Người nộp là chủ hồ sơ' — cổng tự đổ sang "
            "Phần 2. Nếu NỘP THAY: extension bỏ tích ô đó, điền Phần 1 (người nộp) và Phần 2 (người đề "
            "nghị) riêng.\n"
            "Extension còn điền Nội dung tờ khai (kính gửi, địa danh, mã định danh, địa chỉ) và thông số "
            "tàu (đóng mới HOẶC cải hoán/thuê/mua tùy Tờ khai khai).\n"
            "Bước đính kèm: Tờ khai Mẫu 12 được tick vào dòng thành phần hồ sơ và chọn 'Scan tệp tin' "
            "(CCCD chỉ dùng ở bước thông tin)."
        ),
    },
    {
        "key": "cap-giay-phep-khai-thac-thuy-san",
        # Cổng Nông nghiệp & Môi trường dichvucongnnmt.mae.gov.vn — Form.io, engine fillFormStandard dom-*
        # + attach attp-row (field-key nhân thân data[...] TRÙNG KHÍT #97/#92). CHỈ nhân thân Phần I/II;
        # ô isOwnerDossierCheck mặc định CHƯA tick (như #97). URL SPA ObjectId → detect theo cụm tên.
        "detect": {
            "textIncludes": [
                "cấp, cấp lại giấy phép khai thác thủy sản",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp, cấp lại Giấy phép khai thác thủy sản",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền (của NGƯỜI ĐỀ NGHỊ — chủ tàu):\n"
            "1. Đơn đề nghị cấp Giấy phép khai thác thủy sản (Mẫu số 04.KT — cấp mới) HOẶC Đơn đề nghị cấp "
            "lại (Mẫu số 05.KT — cấp lại) — đã ký.\n"
            "2. Thẻ Căn cước công dân / Căn cước (mặt trước + mặt sau) của chủ tàu để đối chiếu.\n"
            "3. Nếu người KHÁC nộp thay: tải kèm CCCD của người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form online CHỈ thu nhân thân người nộp/chủ tàu; thông tin tàu (số đăng ký, an toàn kỹ thuật, "
            "giám sát hành trình, nghề khai thác...) nằm trong file Mẫu 04/05.KT, không nhập lại.\n"
            "Nếu TỰ NỘP: extension chỉ điền Phần 1 và TICH ô 'Người nộp là chủ hồ sơ' (ô này cổng để sẵn "
            "CHƯA tick) — cổng tự đổ sang Phần 2. Nếu NỘP THAY: extension bỏ tích, điền Phần 1 (người nộp) "
            "và Phần 2 (chủ tàu) riêng.\n"
            "Bước đính kèm: Đơn Mẫu 04 (cấp mới) hoặc Mẫu 05 (cấp lại) được tick vào đúng dòng thành phần "
            "hồ sơ và chọn 'Scan tệp tin' (CCCD chỉ dùng ở bước thông tin)."
        ),
    },
    {
        "key": "dang-ky-bien-phap-bao-dam-qsdd",
        # Cổng dịch vụ công Đà Nẵng dichvucong.danang.gov.vn — Form.io (field-key RIÊNG), engine
        # fillFormStandard dom-* + attach attp-row. Form chỉ thu NGƯỜI YÊU CẦU (cá nhân/tổ chức); nội dung
        # thế chấp trong Phiếu Mẫu 01a đính kèm. URL SPA ObjectId → detect theo cụm tên.
        "detect": {
            "urlScope": ["dichvucong.danang.gov.vn"],
            "textIncludes": [
                "đăng ký biện pháp bảo đảm bằng quyền sử dụng đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Đà Nẵng] Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Phiếu yêu cầu đăng ký biện pháp bảo đảm (Mẫu số 01a) — đã ký.\n"
            "2. Thẻ Căn cước công dân / Căn cước của NGƯỜI YÊU CẦU ĐĂNG KÝ (người đứng nộp) để đối chiếu.\n"
            "3. Hợp đồng bảo đảm (thế chấp) và Giấy chứng nhận QSDĐ (sổ đỏ/sổ hồng) — để đính kèm.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form chỉ điền thông tin người yêu cầu đăng ký (cá nhân: nhân thân; tổ chức: tên + mã số thuế) "
            "và tự tích 'Chủ hồ sơ cũng là người nộp'. Nội dung thế chấp (bên bảo đảm/nhận, thửa đất) nằm "
            "trong Phiếu Mẫu 01a, không nhập lại trên form.\n"
            "Bước đính kèm: Phiếu 01a (dòng 1), Hợp đồng bảo đảm (dòng 2), Giấy chứng nhận (dòng 3) được "
            "tick vào đúng dòng thành phần hồ sơ (CCCD chỉ dùng ở bước thông tin)."
        ),
    },
    {
        "key": "xoa-dang-ky-phuong-tien-thuy",
        # Cổng DVC Bộ Xây dựng dvc.moc.gov.vn — Form.io, engine fillFormStandard dom-* + attach attp-row
        # (CÙNG cổng #63 liên vận & quy-hoach). HAI vai: Người nộp (Phần I) / Chủ phương tiện (Phần II,
        # cá nhân HOẶC tổ chức). Key trùng Phần I↔II điền bằng occurrence. Nút "Sao chép thông tin người
        # nộp" là BUTTON → bỏ qua, điền Phần II trực tiếp. URL SPA ObjectId → detect theo cụm tên.
        "detect": {
            "textIncludes": [
                "xóa đăng ký phương tiện thủy nội địa",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Xóa đăng ký phương tiện thủy nội địa",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền (của CHỦ PHƯƠNG TIỆN — người/tổ chức đề nghị xóa đăng ký):\n"
            "1. Đơn đề nghị xóa đăng ký phương tiện thủy nội địa (Mẫu số 3/10) — đã ký, đóng dấu.\n"
            "2. Nếu chủ phương tiện là CÁ NHÂN: Thẻ Căn cước công dân / Căn cước của chủ phương tiện để đối "
            "chiếu.\n"
            "3. Nếu người KHÁC nộp thay: tải kèm CCCD của người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Extension điền Phần I (người nộp), Phần II (chủ phương tiện — tự nhận cá nhân/tổ chức), Phần "
            "III (đặc điểm phương tiện: tên, số đăng ký, số GCN, lý do xóa) và Phần IV (nơi lập đơn).\n"
            "Bước đính kèm: Đơn đề nghị được tick vào dòng thành phần hồ sơ và chọn 'Bản chính' (CCCD chỉ "
            "dùng ở bước thông tin)."
        ),
    },
    {
        "key": "dang-ky-bien-dong-dat-dai-da-nang",
        # Cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn — Form.io, engine fillFormStandard dom-* + attach
        # attp-row (CÙNG cổng #95). HAI vai trong 1 panel: Chủ hồ sơ (ownerFullname/organization) / Người
        # nộp (fullname/CCCD/địa chỉ + chonDoiTuong + taxCode). isOwnerDossier bỏ tích khi ủy quyền. URL
        # SPA ObjectId → detect theo cụm tên đặc trưng (phân biệt các thủ tục biến động khác).
        "detect": {
            "urlScope": ["dichvucong.danang.gov.vn"],
            "textIncludes": [
                "chuyển đổi quyền sử dụng đất nông nghiệp mà không theo phương án dồn điền",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Đà Nẵng] Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất trong các trường "
            "hợp chuyển đổi quyền sử dụng đất nông nghiệp mà không theo phương án dồn điền, đổi thửa; "
            "chuyển nhượng, thừa kế, tặng cho quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất, "
            "góp vốn bằng quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất; cho thuê, cho thuê lại "
            "quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu hạ tầng; bán hoặc tặng cho hoặc để "
            "thừa kế hoặc góp vốn bằng tài sản gắn liền với đất thuê của Nhà nước theo hình thức thuê đất "
            "trả tiền hàng năm"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Hợp đồng chuyển nhượng/tặng cho/thừa kế/góp vốn QSDĐ (bản công chứng) — xác định chủ hồ sơ "
            "(bên nhận) và thửa đất.\n"
            "2. Nếu chủ hồ sơ ỦY QUYỀN cho người khác nộp: tải kèm Hợp đồng ủy quyền + CCCD người được ủy "
            "quyền.\n"
            "3. Nếu chủ hồ sơ là TỔ CHỨC: tải kèm Giấy chứng nhận đăng ký doanh nghiệp.\n"
            "4. Đơn đăng ký biến động (Mẫu số 18) và Bản gốc Giấy chứng nhận QSDĐ — để đính kèm.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Chủ hồ sơ (họ tên/tên tổ chức) + Người nộp (nhân thân, địa chỉ, loại đối tượng). "
            "Nếu ủy quyền → BỎ tích 'Chủ hồ sơ cũng là người nộp' và điền cả hai. Nội dung yêu cầu giải "
            "quyết tự ghép theo tên chủ hồ sơ.\n"
            "Bước đính kèm: Đơn Mẫu 18, Hợp đồng chuyển quyền, Bản gốc Giấy chứng nhận... được tick vào "
            "đúng dòng thành phần hồ sơ và chọn 'Bản chính' (CCCD chỉ dùng ở bước thông tin)."
        ),
    },
    {
        "key": "cap-gcn-so-nha-da-nang",
        # Cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn — Form.io, engine fillFormStandard dom-* + attach
        # attp-row (CÙNG cổng #68/#75, field-key data[...] y hệt). HAI vai 1 panel: Chủ hồ sơ (chủ sở hữu
        # nhà ký đơn) / Người nộp; mặc định tự nộp → tick isOwnerDossier. noidungyeucaugiaiquyet ghép tên
        # chủ hồ sơ + địa chỉ xin cấp. URL SPA ObjectId → detect theo cụm tên đặc trưng.
        "detect": {
            "urlScope": ["dichvucong.danang.gov.vn"],
            "textIncludes": [
                "Cấp mới/cấp lại Giấy chứng nhận số nhà",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Đà Nẵng] Cấp mới/cấp lại Giấy chứng nhận số nhà",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn đề nghị cấp/cấp lại giấy chứng nhận số nhà (đã điền tay, có sơ đồ, đã ký) — xác định "
            "chủ hồ sơ (chủ sở hữu nhà) và địa chỉ xin cấp số nhà.\n"
            "2. Giấy chứng nhận quyền sử dụng đất (sổ đỏ/sổ hồng); nếu là CẤP LẠI thì tải kèm Giấy chứng "
            "nhận biển số nhà cũ — để đính kèm làm minh chứng (Bản sao).\n"
            "3. CCCD của chủ hồ sơ (để đối chiếu nhân thân — không có dòng đính kèm riêng).\n"
            "4. Nếu người KHÁC nộp thay: tải kèm Hợp đồng ủy quyền + CCCD người được ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Chủ hồ sơ (họ tên) + Người nộp (nhân thân, địa chỉ liên hệ). Mặc định tự nộp → "
            "tích 'Chủ hồ sơ cũng là người nộp'; nếu ủy quyền → BỎ tích và điền cả hai. Nội dung yêu cầu "
            "giải quyết tự ghép theo tên chủ hồ sơ + địa chỉ xin cấp số nhà.\n"
            "Bước đính kèm: Đơn đề nghị → dòng 1 (Bản chính); Giấy chứng nhận QSDĐ/biển số nhà cũ → dòng 2 "
            "(Bản sao); CCCD chỉ dùng ở bước thông tin."
        ),
    },
    {
        "key": "xac-nhan-ho-so-so-nha-da-nang",
        # Cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn — Form.io, engine fillFormStandard dom-* + attach
        # attp-row. CÙNG cổng + field-key data[...] Y HỆT #110 (cap-gcn-so-nha-da-nang); chỉ khác tên thủ
        # tục + đính kèm 1 dòng (Đơn đề nghị + GCN QSDĐ minh chứng cùng dòng). URL SPA ObjectId → detect
        # theo cụm tên. ⚠ Trang này CÓ CHỨA cụm "Cấp mới/cấp lại Giấy chứng nhận số nhà" (dòng quy trình)
        # trùng detect của #110 → phải dùng cụm breadcrumb DÀI hơn "Thủ tục xác nhận hồ sơ..." để thắng
        # điểm (detect chọn tổng độ dài cụm dài nhất).
        "detect": {
            "urlScope": ["dichvucong.danang.gov.vn"],
            "textIncludes": [
                "Thủ tục xác nhận hồ sơ cấp mới/cấp lại Giấy chứng nhận biển số nhà",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Đà Nẵng] Thủ tục xác nhận hồ sơ cấp mới/cấp lại Giấy chứng nhận biển số nhà",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn đề nghị cấp giấy chứng nhận số nhà (đã điền tay, đã ký) — xác định chủ hồ sơ (chủ sở "
            "hữu nhà) và địa chỉ xin cấp số nhà.\n"
            "2. Giấy chứng nhận quyền sử dụng đất (sổ đỏ/sổ hồng) — đính kèm làm minh chứng.\n"
            "3. CCCD của chủ hồ sơ (để đối chiếu nhân thân — không có dòng đính kèm riêng).\n"
            "4. Nếu người KHÁC nộp thay: tải kèm Hợp đồng ủy quyền + CCCD người được ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Chủ hồ sơ (họ tên) + Người nộp (nhân thân, địa chỉ liên hệ). Mặc định tự nộp → "
            "tích 'Chủ hồ sơ cũng là người nộp'; nếu ủy quyền → BỎ tích và điền cả hai. Nội dung yêu cầu "
            "giải quyết tự ghép theo tên chủ hồ sơ + địa chỉ xin cấp số nhà.\n"
            "Bước đính kèm: cổng chỉ có 1 ô 'Đơn đề nghị cấp giấy chứng nhận số nhà' (Bản chính) — Đơn đề "
            "nghị và Giấy chứng nhận QSDĐ đều đính vào ô này; CCCD chỉ dùng ở bước thông tin."
        ),
    },
    {
        "key": "cap-phep-long-duong-via-he",
        # Cổng DVC Bộ Xây dựng dvc.moc.gov.vn — Form.io, engine fillFormStandard dom-* + attach attp-row
        # (CÙNG cổng #63/#76/#78). EFORM RIÊNG nhiều phần: Phần I người nộp (cá nhân đại diện) + Phần I-b
        # doanh nghiệp (điều kiện, khi Tổ chức) + Phần II đơn đề nghị + Phần III thông tin đề nghị
        # (vị trí/mục đích/thời gian) + Phần IV liên hệ. Field-key data[...] FLAT. Attach 2 dòng (Phương
        # án / Văn bản đề nghị, cả 2 Bản chính). URL SPA ObjectId → detect theo cụm tên.
        "detect": {
            "urlScope": ["dvc.moc.gov.vn"],
            "textIncludes": [
                "Cấp phép sử dụng tạm thời lòng đường, vỉa hè vào mục đích khác",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp phép sử dụng tạm thời lòng đường, vỉa hè vào mục đích khác",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn đề nghị cấp phép sử dụng tạm thời lòng đường, vỉa hè (đã ký, đóng dấu) — nội dung, vị "
            "trí, mục đích, thời gian sử dụng.\n"
            "2. Giấy chứng nhận đăng ký doanh nghiệp (nếu nộp danh nghĩa tổ chức) — tên/mã số/địa chỉ công "
            "ty + người đại diện.\n"
            "3. CCCD người nộp/đại diện; Giấy cam kết; Hợp đồng thuê nhà (nếu có) — để đối chiếu nhân thân "
            "và địa chỉ.\n"
            "4. Phương án sử dụng/tổ chức giao thông hoặc Sơ đồ vị trí / Giấy phép vỉa hè cũ — để đính kèm.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Người nộp (nhân thân, địa chỉ) + Doanh nghiệp (khi Tổ chức) + Đơn đề nghị (đơn vị, "
            "kính gửi, ngày lập) + Thông tin đề nghị (mục đích, tuyến đường, đoạn đường, địa bàn, từ/đến "
            "ngày) + Liên hệ.\n"
            "Bước đính kèm: Phương án/Sơ đồ vị trí → dòng 1; Đơn/Văn bản đề nghị → dòng 2 (đều Bản chính). "
            "CCCD/GCN ĐKDN/cam kết/hợp đồng chỉ dùng ở bước thông tin."
        ),
    },
    {
        "key": "cap-giay-phep-chat-ha-cay-xanh",
        # Cổng DVC Bộ Xây dựng dvc.moc.gov.vn — Form.io, engine fillFormStandard dom-* + attach attp-row
        # (CÙNG cổng #63/#103). HAI vai: Người nộp (flat data[...]) / Chủ hồ sơ + đơn (nested
        # data[panel][...]). Có DATAGRID bảng kê cây data[panel][tbantest][N][...] (cần FE parse grid lồng
        # trong panel). Nút "Sao chép" là BUTTON → bỏ qua. URL SPA ObjectId → detect theo cụm tên.
        "detect": {
            "urlScope": ["dvc.moc.gov.vn"],
            "textIncludes": [
                "cấp giấy phép chặt hạ, dịch chuyển cây xanh",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp giấy phép chặt hạ, dịch chuyển cây xanh",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền (của CHỦ HỒ SƠ — người/tổ chức đề nghị cấp phép):\n"
            "1. Đơn đề nghị cấp giấy phép chặt hạ, dịch chuyển cây xanh (Mẫu số 01) có bảng kê cây xanh — "
            "đã ký.\n"
            "2. Thẻ Căn cước công dân / Căn cước của chủ hồ sơ để đối chiếu.\n"
            "3. Giấy chứng nhận QSDĐ (nếu có) và Ảnh chụp hiện trạng cây xanh — để đính kèm.\n"
            "4. Nếu người KHÁC nộp thay: tải kèm CCCD của người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Extension điền Phần I (người nộp), Phần II (chủ hồ sơ + nội dung đơn), bảng kê cây xanh (nhiều "
            "dòng), lý do và thông tin ký.\n"
            "Bước đính kèm: Đơn Mẫu 01 chọn 'Bản chính', Ảnh hiện trạng cây chọn 'Scan tệp tin' (CCCD chỉ "
            "dùng ở bước thông tin)."
        ),
    },
    {
        "key": "cap-ban-sao-van-bang-so-goc",
        # Cổng DVC Bộ GD&ĐT dvc.moet.gov.vn — Form.io, engine fillFormStandard dom-* + attach attp-row.
        # Field-key PHẲNG data[...]. Người nộp (Phần I) lấy tên+CCCD từ formContext (collectFormContext);
        # nút "Người nộp là chủ hồ sơ" (data[isOwnerDossier]) KHÔNG tick → điền thẳng chủ hồ sơ (owner*/
        # ownerOrganization*) + Phần VIII kê khai BM04 (checkbox Nam/Nu, THPT/THPT1/THCS). URL SPA ObjectId
        # → detect theo domain + cụm tên.
        "detect": {
            "urlScope": ["dvc.moet.gov.vn"],
            "textIncludes": [
                "cấp bản sao văn bằng, chứng chỉ từ sổ gốc",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp bản sao văn bằng, chứng chỉ từ sổ gốc (tại cấp tỉnh)",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền (của CHỦ VĂN BẰNG — người được cấp bản sao):\n"
            "1. Phiếu yêu cầu cấp bản sao văn bằng (Mẫu BM04) đã điền, đã ký.\n"
            "2. Thẻ Căn cước công dân / Căn cước của chủ văn bằng.\n"
            "3. Bản photo văn bằng / bằng tốt nghiệp cần cấp bản sao.\n"
            "4. Nếu người KHÁC yêu cầu thay: tải kèm giấy ủy quyền hoặc giấy tờ chứng minh quan hệ.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Extension điền Phần thông tin người nộp (theo tài khoản), chủ hồ sơ và nội dung kê khai theo "
            "Phiếu BM04. Nút 'Người nộp là chủ hồ sơ' để nguyên (không tự tích).\n"
            "Bước đính kèm: Phiếu BM04, bản photo văn bằng và CCCD cùng đính dòng 'Đơn đề nghị' (Bản chính); "
            "giấy ủy quyền/chứng minh quan hệ đính dòng riêng."
        ),
    },
    {
        "key": "chap-thuan-dau-noi-tam",
        # Cổng DVC Bộ Xây dựng dvc.moc.gov.vn — Form.io, engine fillFormStandard dom-* + attach attp-row
        # (CÙNG cổng #63/#76). Field-key PHẲNG data[...]. HAI vai: Người nộp (Phần I) / Đơn vị đề nghị +
        # nội dung Đơn (Phần II). URL SPA ObjectId → detect theo cụm tên.
        "detect": {
            "urlScope": ["dvc.moc.gov.vn"],
            "textIncludes": [
                "chấp thuận vị trí đấu nối tạm vào đường bộ đang khai thác",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Chấp thuận vị trí đấu nối tạm vào đường bộ đang khai thác",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn/Văn bản đề nghị chấp thuận vị trí đấu nối tạm (Mẫu Mucb) — đã ký.\n"
            "2. Thẻ Căn cước công dân / Căn cước của NGƯỜI NỘP để đối chiếu (không đính kèm).\n"
            "3. Hợp đồng thi công xây dựng HOẶC Văn bản chấp thuận chủ trương đầu tư (kèm công văn, nghị "
            "quyết, hồ sơ pháp lý dự án).\n"
            "4. Hồ sơ thiết kế bản vẽ thi công nút giao đấu nối tạm, phương án tổ chức giao thông.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Extension điền Phần I (người nộp) và Phần II (đơn vị đề nghị, vị trí đấu nối, trường hợp, cam "
            "kết, người ký).\n"
            "Bước đính kèm: HĐ thi công/chủ trương + công văn/pháp lý → dòng 1; Đơn đề nghị → dòng 2; hồ sơ "
            "bản vẽ → dòng 3 (đều 'Bản chính')."
        ),
    },
    {
        "key": "cap-giay-phep-lien-van-viet-lao",
        # Cổng Bộ Xây dựng dvc.moc.gov.vn (Form.io apply-online) — CÙNG nền tảng/engine fill standard
        # dom-* với cung_cap_thong_tin_quy_hoach. URL chỉ ObjectId (không có MaTTHC) → detect theo id
        # đơn/process của bước 1 (urlIncludes là OR).
        "detect": {"urlIncludes": [
            "apply-online/69551d8635dc1d6a4c6b887b",
            "process=69551d9f5ad52521f43d247b",
        ]},
        "label": "Cấp, cấp lại Giấy phép liên vận giữa Việt Nam và Lào",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy đề nghị cấp, cấp lại Giấy phép liên vận Việt Nam - Lào (Mẫu Mucb) — nguồn chính về đề nghị.\n"
            "2. CCCD của người/đơn vị đứng đơn — nguồn nhân thân người nộp.\n"
            "3. Giấy chứng nhận đăng ký xe ô tô của phương tiện xin cấp phép.\n"
            "4. Nếu có: Hợp đồng/tài liệu chứng minh công trình, dự án tại Lào (phi thương mại); Quyết định cử "
            "đi công tác (xe công vụ); Hợp đồng thuê phương tiện (xe không chính chủ).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Điền đơn (Form.io): Phần I 'Thông tin người nộp' + Phần II 'Thông tin đề nghị' (dịch vụ, kính gửi "
            "Sở Xây dựng, mục đích chuyến đi, người làm đơn). DANH SÁCH PHƯƠNG TIỆN (Phần III) do hệ thống nạp "
            "từ hồ sơ xe đã đăng ký của tài khoản — người dùng tự bấm 'Thêm xe' chọn biển số.\n"
            "Đính kèm: mỗi giấy tờ tick vào đúng dòng (đăng ký xe / giấy đề nghị / hợp đồng dự án / quyết định "
            "công tác) theo nhóm thương mại hoặc phi thương mại, chọn Bản chính/Bản sao."
        ),
    },
    {
        "key": "xoa-dang-ky-tau-ca",
        # Cổng dichvucongnnmt.mae.gov.vn dùng Form.io + bảng Angular. URL không có mã TTHC dạng số,
        # nhận diện bằng id thủ tục hoặc id quy trình lấy trực tiếp từ snapshot apply-online thật.
        "detect": {"urlIncludes": [
            "apply-online/69394b62da87c4718eca03a3",
            "process=6a588c510c8bb839cdfb06c8",
        ]},
        "label": "Xóa đăng ký tàu cá, tàu phục vụ nuôi trồng thủy sản",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai xóa đăng ký tàu cá/tàu phục vụ nuôi trồng thủy sản (Mẫu số 10.ĐKT) — nguồn chính.\n"
            "2. Giấy chứng nhận đăng ký tàu cá cũ.\n"
            "3. Giấy tờ chứng minh lý do xóa đăng ký, ví dụ Hợp đồng mua bán/chuyển nhượng tàu cá.\n"
            "4. CCCD của người đề nghị xóa đăng ký/chủ hồ sơ.\n"
            "5. Theo quy trình trên cổng, bổ sung Mẫu 11.ĐKT, Mẫu 12.ĐKT và Mẫu 13.ĐKT nếu hồ sơ thuộc "
            "trường hợp bắt buộc.\n"
            "Có thể tải một PDF gộp; hệ thống vẫn đọc riêng người đề nghị/bên mua, chủ tàu cũ/bên bán và "
            "thông tin GCN. Người nộp trên cổng được giữ theo tài khoản, không bị CCCD chủ hồ sơ ghi đè.\n"
            "Đính kèm tự động vào bốn dòng Mẫu 10/11/12/13.ĐKT. Hợp đồng, GCN cũ và CCCD tách riêng cần "
            "đính bằng nút 'Thêm giấy tờ'; nếu chúng nằm chung PDF có Mẫu 10.ĐKT thì PDF gộp được đưa vào "
            "dòng Tờ khai."
        ),
    },
]


# Map procedure key → hàm pipeline.run
_PIPELINE = {
    "khai-sinh-dang-ky-thuong": khai_sinh_thuong_process,
    "khai-sinh-ket-hop-nhan-cha-me-con": khai_sinh_ket_hop_nhan_cmc_process,
    "khai-sinh-dang-ky": khai_sinh_lien_thong_process,
    "khai-sinh-dang-ky-lai": khai_sinh_dang_ky_lai_process,
    "ket-hon": ket_hon_process,
    "ket-hon-nuoc-ngoai": ket_hon_nuoc_ngoai_process,
    "dang-ky-lai-ket-hon": ket_hon_lai_process,
    "dang-ky-giam-ho": dang_ky_giam_ho_process,
    "dang-ky-nhan-cha-me-con": nhan_cha_me_con_process,
    "trich-luc-ks": trich_luc_process,
    "trich-luc-khai-tu": trich_luc_process,  # Dùng chung process với trích lục khai sinh
    "khai-tu": khai_tu_process,
    "khai-tu-dang-ky-lai": khai_tu_dang_ky_lai_process,
    "thay-doi-cai-chinh-ho-tich": thay_doi_ho_tich_process,
    "xac-nhan-tinh-trang-hon-nhan": xac_nhan_tthn_process,
    "dinh-chinh-sai-sot": dinh_chinh_sai_sot_process,
    "dinh-chinh-sai-sot-bac-ninh": dinh_chinh_sai_sot_bac_ninh_process,
    "dinh-chinh-sai-sot-lam-dong": dinh_chinh_sai_sot_lam_dong_process,
    "dang-ky-dat-dai-lan-dau-lam-dong": dang_ky_dat_dai_lan_dau_lam_dong_process,
    "cung-cap-thong-tin-quy-hoach": cung_cap_thong_tin_quy_hoach_process,
    "cap-gcn-diem-tro-choi-dien-tu-cong-cong": cap_gcn_diem_tro_choi_dien_tu_process,
    "giao-thue-chuyen-muc-dich-dat-bac-ninh": giao_thue_chuyen_muc_dich_dat_bac_ninh_process,
    "giao-thue-chuyen-muc-dich-dat-ninh-binh": giao_thue_chuyen_muc_dich_dat_ninh_binh_process,
    "dinh-chinh-gcn-da-cap-ninh-binh": dinh_chinh_gcn_da_cap_ninh_binh_process,
    "dang-ky-dat-dai-lan-dau-bac-ninh": dang_ky_dat_dai_lan_dau_bac_ninh_process,
    "thu-hoi-gcn-cap-sai-bac-ninh": thu_hoi_gcn_cap_sai_bac_ninh_process,
    "dang-ky-bien-dong-chuyen-nhuong-bac-ninh": dang_ky_bien_dong_chuyen_nhuong_bac_ninh_process,
    "tach-hop-thua-dat-bac-ninh": tach_hop_thua_dat_bac_ninh_process,
    "cap-doi-gcn-bac-ninh": cap_doi_gcn_bac_ninh_process,
    "dinh-chinh-gcn-da-cap-bac-ninh": dinh_chinh_gcn_da_cap_bac_ninh_process,
    "dang-ky-lap-dat-su-dung-nuoc-sach": cap_nuoc_sach_process,
    "chuyen-doi-ten-hop-dong-nuoc-sach": doi_ten_nuoc_sach_process,
    "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham": an_toan_thuc_pham_process,
    "cap-gcn-attp-nong-lam-thuy-san": cap_gcn_attp_nong_lam_thuy_san_process,
    "cap-lai-giay-chung-nhan-du-dieu-kien-an-toan-thuc-pham": cap_lai_an_toan_thuc_pham_process,
    "cap-giay-phep-xay-dung-moi-nha-o-rieng-le": cap_giay_phep_xay_dung_process,
    "dieu-chinh-dat-dai": dieu_chinh_dat_dai_process,
    "dang-ky-dat-dai-lan-dau": dang_ky_dat_dai_process,
    "dang-ky-dat-dai-tai-san-lan-dau-nguoi-o-nuoc-ngoai": dang_ky_dat_dai_tai_san_process,
    "ho-tro-mai-tang": ho_tro_mai_tang_process,
    "ho-tro-mai-tang-huu-tri-xa-hoi": ho_tro_mai_tang_huu_tri_xa_hoi_process,
    "dieu-chinh-huu-tri-xa-hoi": dieu_chinh_huu_tri_xa_hoi_process,
    "mai-tang-dan-cong-hoa-tuyen": mai_tang_dan_cong_process,
    "xac-dinh-muc-do-khuyet-tat": khuyet_tat_process,
    "xet-tuyen-vien-chuc": xet_tuyen_vien_chuc_process,
    "xet-tuyen-vien-chuc-lai-chau": xet_tuyen_vien_chuc_lai_chau_process,
    "xet-tuyen-cong-chuc": xet_tuyen_cong_chuc_process,
    "thi-tuyen-cong-chuc": thi_tuyen_cong_chuc_process,
    "cap-lai-to-quoc-ghi-cong": cap_lai_to_quoc_ghi_cong_process,
    "bo-sung-than-nhan-liet-si": bo_sung_than_nhan_liet_si_process,
    "tham-vieng-mo-liet-si": tham_vieng_mo_liet_si_process,
    "tro-cap-tho-cung-liet-si": tro_cap_tho_cung_liet_si_process,
    "uu-dai-ncc-tu-tran": uu_dai_ncc_tu_tran_process,
    "giai-quyet-che-do-khang-chien": giai_quyet_che_do_khang_chien_process,
    "sua-doi-thong-tin-ho-so-nguoi-co-cong": sua_doi_ttncc_process,
    "di-chuyen-ho-so-nguoi-huong-tro-cap": di_chuyen_ho_so_process,
    "tro-cap-xa-hoi-hang-thang": tro_cap_xa_hoi_hang_thang_process,
    "cap-moi-giay-phep-hanh-nghe-chuyen-tiep": cap_moi_gphn_chuyen_tiep_process,
    "cap-chung-chi-hanh-nghe-duoc": cap_cchn_duoc_process,
    "cap-van-ban-chap-thuan-tau-ca": cap_vb_chap_thuan_tau_ca_process,
    "cap-giay-phep-khai-thac-thuy-san": cap_gp_khai_thac_ts_process,
    "dang-ky-bien-phap-bao-dam-qsdd": dk_bien_phap_bao_dam_process,
    "xoa-dang-ky-phuong-tien-thuy": xoa_dk_phuong_tien_thuy_process,
    "dang-ky-bien-dong-dat-dai-da-nang": dk_bien_dong_dat_dai_dn_process,
    "cap-gcn-so-nha-da-nang": cap_gcn_so_nha_dn_process,
    "xac-nhan-ho-so-so-nha-da-nang": xn_ho_so_so_nha_dn_process,
    "cap-phep-long-duong-via-he": cap_phep_via_he_process,
    "cap-giay-phep-chat-ha-cay-xanh": cap_gp_chat_ha_cay_xanh_process,
    "cap-ban-sao-van-bang-so-goc": cap_ban_sao_van_bang_process,
    "chap-thuan-dau-noi-tam": chap_thuan_dau_noi_tam_process,
    "cap-giay-phep-lien-van-viet-lao": cap_giay_phep_lien_van_viet_lao_process,
    "xoa-dang-ky-tau-ca": xoa_dang_ky_tau_ca_process,
    "dang-ky-kinh-doanh": dang_ky_kinh_doanh_process,
    "dang-ky-thay-doi-noi-dung-ho-kinh-doanh": dang_ky_thay_doi_kinh_doanh_process,
    "cham-dut-hoat-dong-ho-kinh-doanh": cham_dut_hoat_dong_ho_kinh_doanh_process,
    "cap-lai-cap-doi-gcn-ho-kinh-doanh": cap_lai_cap_doi_gcn_ho_kinh_doanh_process,
}

# Map procedure key → hàm đính kèm (mỗi thủ tục migrate sang app/pipelines thêm 1 dòng ở đây,
# router chỉ dispatch qua registry).
_ATTACH_PIPELINE = {
    "cap-ban-sao-so-goc": cap_ban_sao_so_goc_attach,
    "dinh-chinh-sai-sot": dinh_chinh_sai_sot_attach,
    "dinh-chinh-sai-sot-bac-ninh": dinh_chinh_sai_sot_bac_ninh_attach,
    "dinh-chinh-sai-sot-lam-dong": dinh_chinh_sai_sot_lam_dong_attach,
    "dang-ky-dat-dai-lan-dau-lam-dong": dang_ky_dat_dai_lan_dau_lam_dong_attach,
    "cung-cap-thong-tin-quy-hoach": cung_cap_thong_tin_quy_hoach_attach,
    "cap-gcn-diem-tro-choi-dien-tu-cong-cong": cap_gcn_diem_tro_choi_dien_tu_attach,
    "giao-thue-chuyen-muc-dich-dat-bac-ninh": giao_thue_chuyen_muc_dich_dat_bac_ninh_attach,
    "giao-thue-chuyen-muc-dich-dat-ninh-binh": giao_thue_chuyen_muc_dich_dat_ninh_binh_attach,
    "dinh-chinh-gcn-da-cap-ninh-binh": dinh_chinh_gcn_da_cap_ninh_binh_attach,
    "dang-ky-dat-dai-lan-dau-quang-ninh-mien-nui-hai-dao": dang_ky_dat_dai_lan_dau_quang_ninh_mien_nui_hai_dao_attach,
    "dang-ky-bien-dong-chuyen-nhuong-quang-ninh-mien-nui-hai-dao": dang_ky_bien_dong_chuyen_nhuong_quang_ninh_mien_nui_hai_dao_attach,
    "chuyen-muc-dich-su-dung-dat-quang-ninh-mien-nui-hai-dao": chuyen_muc_dich_su_dung_dat_quang_ninh_mien_nui_hai_dao_attach,
    "dang-ky-dat-dai-lan-dau-bac-ninh": dang_ky_dat_dai_lan_dau_bac_ninh_attach,
    "thu-hoi-gcn-cap-sai-bac-ninh": thu_hoi_gcn_cap_sai_bac_ninh_attach,
    "dang-ky-bien-dong-chuyen-nhuong-bac-ninh": dang_ky_bien_dong_chuyen_nhuong_bac_ninh_attach,
    "tach-hop-thua-dat-bac-ninh": tach_hop_thua_dat_bac_ninh_attach,
    "cap-doi-gcn-bac-ninh": cap_doi_gcn_bac_ninh_attach,
    "dinh-chinh-gcn-da-cap-bac-ninh": dinh_chinh_gcn_da_cap_bac_ninh_attach,
    "dang-ky-kinh-doanh": dang_ky_kinh_doanh_attach,
    "dang-ky-thay-doi-noi-dung-ho-kinh-doanh": dang_ky_thay_doi_kinh_doanh_attach,
    "cham-dut-hoat-dong-ho-kinh-doanh": cham_dut_hoat_dong_ho_kinh_doanh_attach,
    "cap-lai-cap-doi-gcn-ho-kinh-doanh": cap_lai_cap_doi_gcn_ho_kinh_doanh_attach,
    "chung-thuc-ban-sao": chung_thuc_ban_sao_attach,
    # Chứng thực chữ ký: module RIÊNG (form 2 ô — STT1 giấy tờ, STT2 giấy tùy thân).
    "chung-thuc-chu-ky": chung_thuc_chu_ky_attach,
    "chung-thuc-di-chuc": chung_thuc_di_chuc_attach,
    "chung-thuc-giao-dich-tai-san": chung_thuc_giao_dich_tai_san_attach,
    "chung-thuc-phan-chia-di-san": chung_thuc_phan_chia_di_san_attach,
    "chung-thuc-sua-doi-bo-sung-huy-bo-giao-dich": chung_thuc_sua_doi_giao_dich_attach,
    "chung-thuc-tu-choi-nhan-di-san": chung_thuc_tu_choi_di_san_attach,
    "ho-tro-mai-tang": ho_tro_mai_tang_attach,
    "ho-tro-mai-tang-huu-tri-xa-hoi": ho_tro_mai_tang_huu_tri_xa_hoi_attach,
    "dieu-chinh-huu-tri-xa-hoi": dieu_chinh_huu_tri_xa_hoi_attach,
    "khai-sinh-dang-ky-thuong": khai_sinh_thuong_attach,
    "khai-sinh-ket-hop-nhan-cha-me-con": khai_sinh_ket_hop_nhan_cmc_attach,
    "khai-sinh-dang-ky": khai_sinh_lien_thong_attach,
    "khai-sinh-dang-ky-lai": khai_sinh_dang_ky_lai_attach,
    "ket-hon": ket_hon_attach,
    # Đính kèm RIÊNG: form nhiều ô cố định (y tế/TTHN nước ngoài/hộ chiếu/văn bản ngành/TTHN ĐSQ VN).
    "ket-hon-nuoc-ngoai": ket_hon_nuoc_ngoai_attach,
    "dang-ky-lai-ket-hon": ket_hon_lai_attach,
    "dang-ky-giam-ho": dang_ky_giam_ho_attach,
    "dang-ky-nhan-cha-me-con": nhan_cha_me_con_attach,
    "trich-luc-ks": trich_luc_attach,
    "trich-luc-khai-tu": trich_luc_attach,  # Dùng chung attachment với trích lục khai sinh
    "khai-tu": khai_tu_attach,
    "khai-tu-dang-ky-lai": khai_tu_dang_ky_lai_attach,
    "thay-doi-cai-chinh-ho-tich": thay_doi_ho_tich_attach,
    "xac-dinh-muc-do-khuyet-tat": khuyet_tat_attach,
    "xac-nhan-tinh-trang-hon-nhan": xac_nhan_tthn_attach,
    "xet-tuyen-vien-chuc": xet_tuyen_vien_chuc_attach,
    "xet-tuyen-vien-chuc-lai-chau": xet_tuyen_vien_chuc_lai_chau_attach,
    "xet-tuyen-cong-chuc": xet_tuyen_cong_chuc_attach,
    "thi-tuyen-cong-chuc": thi_tuyen_cong_chuc_attach,
    "cap-lai-to-quoc-ghi-cong": cap_lai_to_quoc_ghi_cong_attach,
    "bo-sung-than-nhan-liet-si": bo_sung_than_nhan_liet_si_attach,
    "tham-vieng-mo-liet-si": tham_vieng_mo_liet_si_attach,
    "tro-cap-tho-cung-liet-si": tro_cap_tho_cung_liet_si_attach,
    "uu-dai-ncc-tu-tran": uu_dai_ncc_tu_tran_attach,
    "giai-quyet-che-do-khang-chien": giai_quyet_che_do_khang_chien_attach,
    "sua-doi-thong-tin-ho-so-nguoi-co-cong": sua_doi_ttncc_attach,
    "di-chuyen-ho-so-nguoi-huong-tro-cap": di_chuyen_ho_so_attach,
    "tro-cap-xa-hoi-hang-thang": tro_cap_xa_hoi_hang_thang_attach,
    "cap-moi-giay-phep-hanh-nghe-chuyen-tiep": cap_moi_gphn_chuyen_tiep_attach,
    "cap-chung-chi-hanh-nghe-duoc": cap_cchn_duoc_attach,
    "cap-van-ban-chap-thuan-tau-ca": cap_vb_chap_thuan_tau_ca_attach,
    "cap-giay-phep-khai-thac-thuy-san": cap_gp_khai_thac_ts_attach,
    "dang-ky-bien-phap-bao-dam-qsdd": dk_bien_phap_bao_dam_attach,
    "xoa-dang-ky-phuong-tien-thuy": xoa_dk_phuong_tien_thuy_attach,
    "dang-ky-bien-dong-dat-dai-da-nang": dk_bien_dong_dat_dai_dn_attach,
    "cap-gcn-so-nha-da-nang": cap_gcn_so_nha_dn_attach,
    "xac-nhan-ho-so-so-nha-da-nang": xn_ho_so_so_nha_dn_attach,
    "cap-phep-long-duong-via-he": cap_phep_via_he_attach,
    "cap-giay-phep-chat-ha-cay-xanh": cap_gp_chat_ha_cay_xanh_attach,
    "cap-ban-sao-van-bang-so-goc": cap_ban_sao_van_bang_attach,
    "chap-thuan-dau-noi-tam": chap_thuan_dau_noi_tam_attach,
    "cap-giay-phep-lien-van-viet-lao": cap_giay_phep_lien_van_viet_lao_attach,
    "xoa-dang-ky-tau-ca": xoa_dang_ky_tau_ca_attach,
    "dang-ky-lap-dat-su-dung-nuoc-sach": cap_nuoc_sach_attach,
    "chuyen-doi-ten-hop-dong-nuoc-sach": doi_ten_nuoc_sach_attach,
    "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham": an_toan_thuc_pham_attach,
    "cap-gcn-attp-nong-lam-thuy-san": cap_gcn_attp_nong_lam_thuy_san_attach,
    "cap-lai-giay-chung-nhan-du-dieu-kien-an-toan-thuc-pham": cap_lai_an_toan_thuc_pham_attach,
    "cap-giay-phep-xay-dung-moi-nha-o-rieng-le": cap_giay_phep_xay_dung_attach,
}

_BY_KEY = {p["key"]: p for p in PROCEDURES}


def get_procedure(key: str) -> dict | None:
    return _BY_KEY.get(key)


def get_pipeline(key: str):
    return _PIPELINE.get(key)


def get_attach_pipeline(key: str):
    return _ATTACH_PIPELINE.get(key)


def public_list() -> list[dict]:
    return PROCEDURES
