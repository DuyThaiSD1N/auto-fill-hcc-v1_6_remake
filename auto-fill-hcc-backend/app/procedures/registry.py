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
from app.pipelines.cap_gcn_attp_cong_thuong.process import run as cap_gcn_attp_ct_process
from app.pipelines.cap_gcn_attp_cong_thuong.attach import plan as cap_gcn_attp_ct_attach
from app.pipelines.cap_giay_phep_xay_dung.attach import plan as cap_giay_phep_xay_dung_attach
from app.pipelines.cap_giay_phep_xay_dung.process import run as cap_giay_phep_xay_dung_process
from app.pipelines.dieu_chinh_giay_phep_xay_dung.attach import plan as dieu_chinh_gpxd_attach
from app.pipelines.dieu_chinh_giay_phep_xay_dung.process import run as dieu_chinh_gpxd_process
from app.pipelines.sua_chua_cai_tao_gpxd.attach import plan as sua_chua_gpxd_attach
from app.pipelines.sua_chua_cai_tao_gpxd.process import run_nha_o as sua_chua_gpxd_nha_o_process
from app.pipelines.sua_chua_cai_tao_gpxd.process import run_cong_trinh as sua_chua_gpxd_cong_trinh_process
from app.pipelines.cap_doi_gcn_bac_ninh.attach import plan as cap_doi_gcn_bac_ninh_attach
from app.pipelines.cap_doi_gcn_bac_ninh.process import run as cap_doi_gcn_bac_ninh_process
from app.pipelines.dinh_chinh_gcn_da_cap_bac_ninh.attach import plan as dinh_chinh_gcn_da_cap_bac_ninh_attach
from app.pipelines.dinh_chinh_gcn_da_cap_bac_ninh.process import run as dinh_chinh_gcn_da_cap_bac_ninh_process
from app.pipelines.dang_ky_dat_dai_lan_dau_lam_dong.attach import plan as dang_ky_dat_dai_lan_dau_lam_dong_attach
from app.pipelines.dang_ky_dat_dai_lan_dau_lam_dong.process import run as dang_ky_dat_dai_lan_dau_lam_dong_process
from app.pipelines.dang_ky_kinh_doanh.attach import plan as dang_ky_kinh_doanh_attach
from app.pipelines.dang_ky_thay_doi_kinh_doanh.attach import plan as dang_ky_thay_doi_kinh_doanh_attach
from app.pipelines.cham_dut_hoat_dong_ho_kinh_doanh.attach import plan as cham_dut_hoat_dong_ho_kinh_doanh_attach
from app.pipelines.tam_ngung_kinh_doanh.attach import plan as tam_ngung_kinh_doanh_attach
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
from app.pipelines.thanh_lap_ctcp.process import run as thanh_lap_ctcp_process
from app.pipelines.thanh_lap_ctcp.attach import plan as thanh_lap_ctcp_attach
from app.pipelines.thanh_lap_ctythnn_2_nguoi.process import run as thanh_lap_tnhh2_process
from app.pipelines.thanh_lap_ctythnn_2_nguoi.attach import plan as thanh_lap_tnhh2_attach
from app.pipelines.dang_ky_thay_doi_kinh_doanh.process import run as dang_ky_thay_doi_kinh_doanh_process
from app.pipelines.cham_dut_hoat_dong_ho_kinh_doanh.process import run as cham_dut_hoat_dong_ho_kinh_doanh_process
from app.pipelines.tam_ngung_kinh_doanh.process import run as tam_ngung_kinh_doanh_process
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
from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_bac_ninh.process import run as xoa_dk_bpbd_bac_ninh_process
from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_bac_ninh.attach import plan as xoa_dk_bpbd_bac_ninh_attach
from app.pipelines.dang_ky_bien_phap_bao_dam_bac_ninh.process import run as dang_ky_bpbd_bac_ninh_process
from app.pipelines.dang_ky_bien_phap_bao_dam_bac_ninh.attach import plan as dang_ky_bpbd_bac_ninh_attach
from app.pipelines.ho_tro_nguoi_cao_tuoi_bac_ninh.attach import plan as ho_tro_nguoi_cao_tuoi_bac_ninh_attach
from app.pipelines.ho_tro_nguoi_cao_tuoi_bac_ninh.process import run as ho_tro_nguoi_cao_tuoi_bac_ninh_process
from app.pipelines.ho_tro_chi_phi_hoa_tang_bac_ninh.attach import plan as ho_tro_chi_phi_hoa_tang_bac_ninh_attach
from app.pipelines.ho_tro_chi_phi_hoa_tang_bac_ninh.process import run as ho_tro_chi_phi_hoa_tang_bac_ninh_process
from app.pipelines.ho_tro_chi_phi_hoa_tang.attach import plan as ho_tro_chi_phi_hoa_tang_attach
from app.pipelines.ho_tro_chi_phi_hoa_tang.process import run as ho_tro_chi_phi_hoa_tang_process
from app.pipelines.dang_ky_nha_o_xa_hoi_bac_ninh.attach import plan as dang_ky_nha_o_xa_hoi_bac_ninh_attach
from app.pipelines.dang_ky_nha_o_xa_hoi_bac_ninh.process import run as dang_ky_nha_o_xa_hoi_bac_ninh_process
from app.pipelines.cap_hoc_tap_bac_ninh.attach import plan as cap_hoc_tap_bac_ninh_attach
from app.pipelines.cap_hoc_tap_bac_ninh.process import run as cap_hoc_tap_bac_ninh_process
from app.pipelines.dinh_chinh_gcn_da_cap_da_nang.process import run as dinh_chinh_gcn_dn_process
from app.pipelines.dinh_chinh_gcn_da_cap_da_nang.attach import plan as dinh_chinh_gcn_dn_attach
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
from app.pipelines.khai_sinh_co_ho_so.attach import plan as khai_sinh_co_ho_so_attach
from app.pipelines.khai_sinh_co_ho_so.process import run as khai_sinh_co_ho_so_process
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
from app.pipelines.mai_tang_dan_cong.attach import plan as mai_tang_dan_cong_attach
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
from app.pipelines.cap_lai_CCHN_thu_y.attach import plan as cap_lai_cchn_thu_y_attach
from app.pipelines.cap_lai_CCHN_thu_y.process import run as cap_lai_cchn_thu_y_process
from app.pipelines.cap_gcn_dang_ky_tau_ca.attach import plan as cap_gcn_dang_ky_tau_ca_attach
from app.pipelines.cap_gcn_dang_ky_tau_ca.process import run as cap_gcn_dang_ky_tau_ca_process
from app.pipelines.dang_ky_bien_phap_bao_dam_qsdd.attach import plan as dk_bien_phap_bao_dam_attach
from app.pipelines.dang_ky_bien_phap_bao_dam_qsdd.process import run as dk_bien_phap_bao_dam_process
from app.pipelines.xoa_dang_ky_phuong_tien_thuy.attach import plan as xoa_dk_phuong_tien_thuy_attach
from app.pipelines.xoa_dang_ky_phuong_tien_thuy.process import run as xoa_dk_phuong_tien_thuy_process
from app.pipelines.dang_ky_bien_dong_dat_dai_da_nang.attach import plan as dk_bien_dong_dat_dai_dn_attach
from app.pipelines.dang_ky_bien_dong_dat_dai_da_nang.process import run as dk_bien_dong_dat_dai_dn_process
from app.pipelines.chuyen_muc_dich_su_dung_dat_da_nang.attach import plan as chuyen_muc_dich_dat_dn_attach
from app.pipelines.chuyen_muc_dich_su_dung_dat_da_nang.process import run as chuyen_muc_dich_dat_dn_process
from app.pipelines.cap_gcn_so_nha_da_nang.attach import plan as cap_gcn_so_nha_dn_attach
from app.pipelines.cap_gcn_so_nha_da_nang.process import run as cap_gcn_so_nha_dn_process
from app.pipelines.tach_hop_thua_dat_da_nang.attach import plan as tach_hop_thua_dat_dn_attach
from app.pipelines.tach_hop_thua_dat_da_nang.process import run as tach_hop_thua_dat_dn_process
from app.pipelines.giao_thue_chuyen_muc_dich_dat_da_nang.attach import plan as giao_thue_cmd_dat_dn_attach
from app.pipelines.giao_thue_chuyen_muc_dich_dat_da_nang.process import run as giao_thue_cmd_dat_dn_process
from app.pipelines.dang_ky_dat_dai_lan_dau_da_nang.attach import plan as dk_dat_dai_lan_dau_dn_attach
from app.pipelines.dang_ky_dat_dai_lan_dau_da_nang.process import run as dk_dat_dai_lan_dau_dn_process
from app.pipelines.cap_doi_gcn_da_nang.attach import plan as cap_doi_gcn_dn_attach
from app.pipelines.cap_doi_gcn_da_nang.process import run as cap_doi_gcn_dn_process
from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_da_nang.attach import plan as xoa_bpbd_dn_attach
from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_da_nang.process import run as xoa_bpbd_dn_process
from app.pipelines.xac_nhan_ho_so_so_nha_da_nang.attach import plan as xn_ho_so_so_nha_dn_attach
from app.pipelines.xac_nhan_ho_so_so_nha_da_nang.process import run as xn_ho_so_so_nha_dn_process
from app.pipelines.cap_phep_long_duong_via_he.attach import plan as cap_phep_via_he_attach
from app.pipelines.cap_phep_long_duong_via_he.process import run as cap_phep_via_he_process
from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.attach import plan as cho_thue_noxh_attach
from app.pipelines.cho_thue_thue_mua_nha_o_xa_hoi.process import run as cho_thue_noxh_process
from app.pipelines.tham_dinh_bcnckt.attach import plan as tham_dinh_bcnckt_attach
from app.pipelines.tham_dinh_bcnckt.process import run as tham_dinh_bcnckt_process
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
        # OCR một batch + một request LLM để tách PDF hỗn hợp và gom các phần của cùng giấy tờ.
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        # Hai thủ tục chứng thực này đi thẳng vào luồng đính kèm, không mở màn xin consent.
        "skipConsent": True,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Bản chính giấy tờ, văn bản làm cơ sở để chứng thực bản sao.\n"
            "2. Bản sao cần chứng thực.\n"
            "Hệ thống sẽ nhận diện, tách/gộp các phần cùng giấy tờ và đính đúng hồ sơ."
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
        # Hai thủ tục chứng thực này đi thẳng vào luồng đính kèm, không mở màn xin consent.
        "skipConsent": True,
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
        "key": "thanh-lap-cong-ty-co-phan",
        # Cổng ĐKKD qua mạng (dangkyquamang.dkkd.gov.vn) là hệ thống RIÊNG, khác cổng hộ kinh doanh
        # (hokinhdoanh.dkkd.gov.vn). Nhận diện theo domain giống HKD: nhiều trang con .aspx nhưng cùng
        # domain, còn URL chỉ mang handle phiên (Registration.aspx?h=..., DW_DOCUMENTEdit.aspx?h=...)
        # nên không suy được thủ tục. Domain mới chỉ chốt "đang ở cổng doanh nghiệp"; khi hồ sơ đã tạo,
        # extension gửi thêm enterpriseEntityLabel đọc từ dòng "Loại hình doanh nghiệp" trên chính hồ sơ
        # để phân biệt CTCP với TNHH/DNTN/hợp danh.
        "detect": {"urlIncludes": ["dangkyquamang.dkkd.gov.vn"], "headingDisabled": True},
        "label": "Đăng ký thành lập công ty cổ phần",
        "mode": "agent",
        # Cờ cho extension: thủ tục thuộc cổng ĐKKD qua mạng. Panel dùng để KHÔNG giữ nhầm thủ tục hộ
        # kinh doanh của phiên trước khi cán bộ chuyển sang cổng doanh nghiệp.
        "enterprisePortal": True,
        # Đối chiếu với dòng "Loại hình doanh nghiệp" in trên hồ sơ (và nhãn radio bước 2 của wizard).
        # Thêm loại hình khác (TNHH một/hai thành viên, DNTN, hợp danh) = thêm entry tương tự.
        "enterpriseEntityLabel": "Công ty cổ phần",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy đề nghị đăng ký doanh nghiệp (công ty cổ phần).\n"
            "2. Điều lệ công ty.\n"
            "3. Danh sách cổ đông sáng lập và cổ đông là nhà đầu tư nước ngoài.\n"
            "4. CCCD/căn cước của người đại diện theo pháp luật và các cổ đông là cá nhân."
        ),
        # CHỈ khai 7 trang ĐÃ CÓ ĐẶC TẢ field (app/pipelines/thanh_lap_ctcp/process/schema.py).
        # Menu khối dữ liệu của cổng còn: Cổ đông sáng lập, Cổ đông là nhà đầu tư nước ngoài, Người
        # đại diện theo pháp luật, Chủ sở hữu hưởng lợi, Đại diện của tổ chức, Bảo hiểm xã hội —
        # chưa có bảng field nên CHƯA khai, tránh điền mò vào hồ sơ thật.
        "pages": [
            {"key": "hinh-thuc-dang-ky", "label": "Hình thức đăng ký"},
            {"key": "dia-chi", "label": "Địa chỉ"},
            {"key": "nganh-nghe-kinh-doanh", "label": "Ngành nghề kinh doanh"},
            {"key": "ten-doanh-nghiep", "label": "Tên doanh nghiệp/đơn vị trực thuộc"},
            {"key": "thong-tin-ve-von", "label": "Thông tin về vốn"},
            {"key": "thong-tin-ve-co-phan", "label": "Thông tin về cổ phần"},
            {"key": "thong-tin-ve-thue", "label": "Thông tin về thuế"},
            {"key": "nguoi-nop-ho-so", "label": "Người nộp hồ sơ"},
        ],
    },
    {
        "key": "thanh-lap-cong-ty-tnhh-hai-thanh-vien",
        # CÙNG cổng, CÙNG wizard ba bước với thủ tục công ty cổ phần ở trên: chỉ khác dòng loại hình
        # phải tick ở bước 2 ("Công ty trách nhiệm hữu hạn hai thành viên trở lên", value LLC2).
        # Vì vậy phần điều hướng của extension (content/procedures/enterprise-registration.js) KHÔNG
        # phải sửa gì — nó đọc loại hình từ chính entry này qua cờ "lên đạn" của panel.
        "detect": {"urlIncludes": ["dangkyquamang.dkkd.gov.vn"], "headingDisabled": True},
        # KHÔNG tự nhận diện thủ tục này: panel phải để cán bộ tự chọn.
        #
        # Cổng này tải lại trang ở MỌI bước (postback), mà cờ giữ lựa chọn tay của panel
        # (manualProcedureOverride) lại reset sau mỗi lần tải trang — nên nhận diện tự động
        # chạy lại liên tục và có quyền đổi thủ tục ngay giữa lúc đang điền dở. Với loại hình
        # này thì rủi ro đó không đáng đánh đổi: cứ để cán bộ chọn một lần rồi giữ nguyên.
        # Vẫn giữ "detect" ở trên để biết thủ tục này thuộc cổng nào; cờ dưới mới là thứ
        # extension đọc để loại nó khỏi vòng nhận diện.
        "detectDisabled": True,
        "label": "Đăng ký thành lập công ty trách nhiệm hữu hạn hai thành viên trở lên",
        "mode": "agent",
        "enterprisePortal": True,
        # Đối chiếu với dòng "Loại hình doanh nghiệp" in trên hồ sơ (và nhãn radio bước 2 của wizard).
        # Đây là thứ DUY NHẤT phân biệt hồ sơ TNHH hai thành viên với hồ sơ CTCP trên cùng domain.
        "enterpriseEntityLabel": "Công ty trách nhiệm hữu hạn hai thành viên trở lên",
        # Lưới đỡ khi cổng đổi chữ nhãn: value radio $CtlEntType của dòng này.
        "enterpriseEntityValue": "LLC2",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy đề nghị đăng ký doanh nghiệp (công ty TNHH hai thành viên trở lên).\n"
            "2. Điều lệ công ty.\n"
            "3. Danh sách thành viên.\n"
            "4. Danh sách chủ sở hữu hưởng lợi của doanh nghiệp (nếu có).\n"
            "5. CCCD/căn cước của người đại diện theo pháp luật và các thành viên là cá nhân.\n"
            "6. Giấy ủy quyền cho người đi nộp hồ sơ (nếu người nộp không phải người đại diện "
            "theo pháp luật)."
        ),
        # 9 trang khối dữ liệu ĐÃ CÓ ĐẶC TẢ FIELD (app/pipelines/thanh_lap_ctythnn_2_nguoi/process/
        # schema.py). KHÔNG có "Thông tin về cổ phần" (chỉ CTCP mới có) và KHÔNG khai "Người đại diện
        # của tổ chức": bước đó chỉ hiện khi thành viên là TỔ CHỨC và bảng đặc tả ghi "không áp dụng"
        # cho mọi dòng — khai mà không có nguồn dữ liệu là điền mò vào hồ sơ thật.
        # Hai trang riêng của loại hình này (Thông tin thành viên, Người đại diện theo pháp luật) là
        # trang kiểu DANH SÁCH: engine phải bấm "Tạo mới" cho từng bản ghi. Cả hai đã được khai trong
        # PAGE_SPEC của content/procedures/enterprise-registration.js. Lượt đọc hồ sơ không rút được
        # dữ liệu thì engine BÁO cho cán bộ và bỏ qua, không tạo bản ghi rỗng (xem pageHasData).
        "pages": [
            {"key": "hinh-thuc-dang-ky", "label": "Hình thức đăng ký"},
            {"key": "dia-chi", "label": "Địa chỉ"},
            {"key": "nganh-nghe-kinh-doanh", "label": "Ngành nghề kinh doanh"},
            {"key": "ten-doanh-nghiep", "label": "Tên doanh nghiệp/đơn vị trực thuộc"},
            {"key": "thong-tin-ve-von", "label": "Thông tin về vốn"},
            {"key": "thong-tin-thanh-vien", "label": "Thông tin thành viên"},
            {"key": "nguoi-dai-dien-phap-luat", "label": "Người đại diện theo pháp luật"},
            {"key": "thong-tin-ve-thue", "label": "Thông tin về thuế"},
            {"key": "thong-tin-bao-hiem-xa-hoi", "label": "Thông tin về bảo hiểm xã hội"},
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
        "key": "tam-ngung-kinh-doanh",
        # Cùng wizard "Chọn loại đăng ký thay đổi" với chấm dứt hoạt động (radio SUSPEN). Trang chính
        # DW_SUSPENSIONEdit.aspx đã xác nhận field DOM thật qua đặc tả HTML (ngày bắt đầu/kết thúc,
        # lý do tạm ngừng); trang "Người nộp hồ sơ" dùng chung logic các thủ tục HKD khác. Nhãn menu
        # trái "Tạm ngừng kinh doanh" đã xác nhận qua ảnh chụp cổng thật (không phải "Tạm ngừng hoạt
        # động" như suy đoán ban đầu) — extension dùng đúng nhãn này để bấm vào mục trong sidebar.
        "detect": {"headingDisabled": True},
        "label": "Tạm ngừng kinh doanh hộ kinh doanh",
        "mode": "agent",
        "businessWorkflow": "suspension",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy đề nghị đăng ký tạm ngừng kinh doanh (ghi rõ thời gian tạm ngừng kể từ ngày ... "
            "đến hết ngày ..., lý do tạm ngừng).\n"
            "2. Bản gốc/bản sao Giấy chứng nhận đăng ký hộ kinh doanh.\n"
            "3. CCCD, ủy quyền hoặc giấy tờ bổ sung khác (đính vào loại Khác)."
        ),
        "pages": [
            {"key": "tam-ngung-hoat-dong", "label": "Tạm ngừng kinh doanh"},
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
        # → nhận diện THEO URL (mã thủ tục trên route ke-khai). headingDisabled=True nghĩa là URL
        # là đường DUY NHẤT: mã nào không khai ở đây thì panel không nhận ra thủ tục, không có lưới đỡ.
        #
        # Cổng chạy SONG SONG hai mã cho cùng một biểu mẫu liên thông khai sinh:
        #   2.000986 — khai sinh + thường trú + BHYT
        #   2.000987 — khai sinh + thường trú + CẤP THẺ CĂN CƯỚC + BHYT (bản mới, thêm thẻ căn cước)
        # Hai mã, nhưng cùng một form kê khai nên dùng chung pipeline điền. Liệt kê TƯỜNG MINH từng
        # mã chứ không khớp lỏng theo route "ke-khai/": route đó còn có liên thông KHAI TỬ (1.006714),
        # khớp lỏng là hai thủ tục nhận nhầm nhau.
        "detect": {
            "urlIncludes": [
                "lienthong.dichvucong.gov.vn/#/ke-khai/2.000986",
                "lienthong.dichvucong.gov.vn/#/ke-khai/2.000987",
            ],
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
        # Option chỉ được bật khi client gửi boolean true; extension cũ tiếp tục giữ nguyên file.
        "supportsSplitDocuments": True,
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên: CCCD cha, CCCD mẹ, giấy khai sinh cũ/bản sao hoặc giấy tờ thay thế.\n"
            "Nếu có: tờ khai giấy, ủy quyền, học bạ, hộ chiếu, bằng/chứng chỉ."
        ),
    },
    {
        # Cùng eForm "Tờ khai đăng ký khai sinh" với 1.004884, nhưng người được khai sinh CHƯA TỪNG
        # đăng ký khai sinh → không có khối "đăng ký trước đây"; nguồn dữ liệu là hồ sơ, giấy tờ cá
        # nhân đã có (CCCD, BHYT, học bạ, bằng cấp, GCN kết hôn, trích lục khai tử của cha/mẹ…).
        "key": "khai-sinh-da-co-ho-so",
        "detect": {"urlIncludes": ["maThuTuc=1.004772"]},
        "label": "Thủ tục đăng ký khai sinh cho người đã có hồ sơ, giấy tờ cá nhân",
        "mode": "agent",
        "hasAttachmentStep": True,
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai đăng ký khai sinh (nếu có) — nguồn chính của nơi sinh, quê quán, năm sinh cha/mẹ.\n"
            "2. Bản cam đoan về việc chưa được đăng ký khai sinh.\n"
            "3. Hồ sơ, giấy tờ cá nhân đã có: CCCD/CMND, thẻ BHYT, giấy tờ cư trú, học bạ, bằng tốt "
            "nghiệp, chứng chỉ, giấy chứng nhận kết hôn, trích lục khai tử của cha/mẹ, giấy đề nghị "
            "xác nhận của cơ quan quản lý.\n"
            "Bước 3: bản cam đoan vào STT 2; toàn bộ giấy tờ cá nhân dồn chung vào STT 3; văn bản xác "
            "nhận của cơ quan (cán bộ/CCVC) vào STT 4; ủy quyền vào STT 5. STT 1 do cổng tự sinh."
        ),
    },
    {
        "key": "ket-hon",
        "detect": {"urlIncludes": ["maThuTuc=1.000894"]},
        "label": "Thủ tục đăng ký kết hôn",
        "mode": "agent",
        "hasAttachmentStep": True,
        # Cho phép người dùng chọn có tách các giấy tờ nằm chung một file hay không. Client cũ hoặc
        # không gửi option luôn đi nhánh giữ nguyên file để không làm thay đổi hồ sơ ngoài ý muốn.
        "supportsSplitDocuments": True,
        "review": False,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy tờ tùy thân của hai bên (CCCD/CMND/hộ chiếu; có thể tải từng mặt hoặc nhiều file).\n"
            "2. Nếu có: tờ khai bản giấy, bản cam đoan và giấy tờ liên quan khác."
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
        # Client cũ hoặc không gửi option luôn giữ nguyên file; chỉ boolean True mới tách theo trang.
        "supportsSplitDocuments": True,
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
        "key": "khai-tu-lien-thong",
        # Cổng riêng lienthong.dichvucong.gov.vn (SPA hash-route), KHÔNG dùng chung eForm legacy
        # với "khai-tu". Mã 1.006714 đã được xác nhận qua breadcrumb trang thật là thủ tục này.
        "detect": {"urlIncludes": ["lienthong.dichvucong.gov.vn/#/ke-khai/1.006714"]},
        "label": "Liên thông đăng ký khai tử, xóa đăng ký thường trú, trợ cấp mai táng phí",
        # TẠM dùng chung pipeline "khai-tu": DOM trang SPA này khác hẳn form legacy (input/select
        # HTML thường, không phải web-component x-*) nên bấm điền sẽ CHƯA điền được field nào —
        # chỉ mới đăng ký để nhận diện đúng thủ tục, không nhận nhầm sang "Trích lục hộ tịch" hay
        # "Trích lục khai tử". Cần dựng mapper/schema/prompt riêng khớp đúng DOM này để điền thật.
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "⚠️ Thủ tục liên thông này CHƯA hỗ trợ tự động điền — mới nhận diện đúng tên để khỏi lẫn "
            "với thủ tục khác. Giấy tờ vẫn có thể tải lên để lưu hồ sơ, nhưng cán bộ cần tự điền form.\n"
            "Giấy tờ cần tải lên (khi có pipeline riêng): CCCD người yêu cầu, giấy báo tử/giấy chứng "
            "tử, giấy tờ chứng minh nơi thường trú, giấy tờ liên quan đến trợ cấp mai táng phí."
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
        # Client cũ không có option sẽ giữ nguyên từng file; chỉ boolean True mới tách theo trang.
        "supportsSplitDocuments": True,
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
        # Client cũ không có option sẽ giữ nguyên từng file; chỉ boolean True mới cho phép tách trang.
        "supportsSplitDocuments": True,
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
        # Mã thủ tục đã đổi 1.012796 -> 1.115446 theo danh mục đất đai của Sở Nông nghiệp và
        # Môi trường (thông báo 1283/TB-SNNMT ngày 04/8/2026). Cổng chỉ còn phát mã mới.
        # urlScope khoá host: 1.115446 là mã QUỐC GIA, cổng iGate tỉnh khác cũng dùng đúng mã đó —
        # không khoá thì mở trang ở tỉnh khác sẽ bị nhận nhầm rồi chạy engine fill-bacninh.js
        # trên DOM không phải của Bắc Ninh.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115446"],
        },
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
        # Mã thủ tục đã đổi 1.013949 -> 1.115438 (nhánh CẤP XÃ) theo danh mục đất đai của Sở
        # Nông nghiệp và Môi trường (thông báo 1283/TB-SNNMT ngày 04/8/2026). Danh mục có hai mã
        # cùng mô tả: 1.115428 (cấp tỉnh) và 1.115438 (cấp xã) — bản Bắc Ninh dùng bản CẤP XÃ.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115438"],
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
        #
        # Mã thủ tục đã đổi 1.013978 -> 1.115443 theo danh mục đất đai của Sở Nông nghiệp và Môi
        # trường (thông báo 1283/TB-SNNMT ngày 04/8/2026). Cổng chỉ còn phát mã mới nên chỉ bắt mã
        # mới; hồ sơ mở bằng đường dẫn mã cũ sẽ KHÔNG tự nhận diện, cán bộ chọn tay.
        #
        # urlScope khoá host: 1.115443 là mã QUỐC GIA, cổng iGate tỉnh khác cũng dùng đúng mã đó —
        # không khoá thì mở trang thủ tục này ở tỉnh khác sẽ bị nhận nhầm thành bản Bắc Ninh rồi
        # chạy engine fill-bacninh.js trên DOM không phải của Bắc Ninh.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115443"],
        },
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
        # Mã thủ tục đã đổi 1.012818 -> 1.115447 theo danh mục đất đai của Sở Nông nghiệp và
        # Môi trường (thông báo 1283/TB-SNNMT ngày 04/8/2026). Cổng chỉ còn phát mã mới.
        # urlScope khoá host: 1.115447 là mã QUỐC GIA, cổng iGate tỉnh khác cũng dùng đúng mã đó —
        # không khoá thì mở trang ở tỉnh khác sẽ bị nhận nhầm rồi chạy engine fill-bacninh.js
        # trên DOM không phải của Bắc Ninh.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115447"],
        },
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
        "key": "xoa-dang-ky-bien-phap-bao-dam-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm) — engine fill-bacninh.js. Ô eForm khớp theo class
        # eform-element-<Key> (name UI = <Key>); radio tick theo nhãn option. maThuTucHanhChinh=1.011443 là
        # mã QG (biện pháp bảo đảm) có thể dùng chung nhiều cổng iGate → khóa host bacninh.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.011443"],
        },
        "label": "[Tỉnh Bắc Ninh] Xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu số 03a) đã ký, có chữ ký & con dấu bên nhận "
            "bảo đảm (ngân hàng) — dùng để điền thân phiếu.\n"
            "2. Bản gốc Giấy chứng nhận QSDĐ (sổ đỏ/sổ hồng), GỒM cả trang mục IV 'Những thay đổi sau khi cấp'.\n"
            "3. CCCD của người yêu cầu (bên bảo đảm); Hợp đồng thế chấp (nếu có).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Lưu ý: thông tin người yêu cầu là CHỦ HIỆN TẠI (mục IV của GCN), KHÔNG lấy chủ cũ ở trang 1 GCN. "
            "Nếu đồng bảo đảm (vợ chồng) → ô '1.1. Tên đầy đủ' ghi cả hai.\n"
            "Điền phiếu: Kính gửi, tư cách người yêu cầu (Bên thế chấp), tên đầy đủ, địa chỉ liên hệ, SĐT, "
            "loại giấy tờ (CCCD) + số/cơ quan/ngày cấp, thửa đất/tờ bản đồ/mục đích/thời hạn/địa chỉ thửa/"
            "diện tích, GCN (số phát hành/số vào sổ/cơ quan/ngày cấp), hợp đồng thế chấp (số/ngày), tài liệu "
            "kèm theo, phương thức nhận kết quả.\n"
            "Đính kèm: Phiếu 03a→KQ003715 (Bản chính), GCN gốc→KQ003716 (Bản chính); các thành phần "
            "KQ003717–KQ003723 khi có; CCCD/HĐ thế chấp/khác→ô đính kèm bổ sung. Cơ quan tiếp nhận và tỉnh/"
            "phường là select theo địa bàn — chọn tay."
        ),
    },
    {
        "key": "dang-ky-bien-phap-bao-dam-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm 01a) — engine fill-bacninh.js, 3 nút (ủy quyền/đơn/
        # đính kèm) như xóa-đăng-ký-biện-pháp (1.011443). Đơn khớp ô theo NAME element_478xx (2 bên + hợp
        # đồng + tài sản, nhiều semantic trùng). Checkbox tư cách/loại giấy tờ để user tự tích. Khóa host.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.011441"],
        },
        "label": "[Tỉnh Bắc Ninh] Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Phiếu yêu cầu đăng ký biện pháp bảo đảm (Mẫu số 01a) đã kê khai, ký — nguồn chính điền đơn.\n"
            "2. Hợp đồng thế chấp/bảo đảm (kèm lời chứng công chứng nếu có).\n"
            "3. Bản gốc Giấy chứng nhận QSDĐ (sổ đỏ/sổ hồng).\n"
            "4. Giấy tờ tư cách pháp lý: CCCD (cá nhân) hoặc Giấy chứng nhận đăng ký doanh nghiệp (tổ chức) "
            "của bên bảo đảm/bên nhận; nếu nộp thay: Giấy giới thiệu/Văn bản ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Nút 'Nhập đơn đăng ký' điền các ô CHỮ của đơn: người yêu cầu (mục 1), hợp đồng bảo đảm (mục 2), "
            "BÊN BẢO ĐẢM=bên thế chấp/chủ đất (mục 3: tên/địa chỉ/giấy tờ pháp lý số-cơ quan-ngày), BÊN NHẬN "
            "bảo đảm=ngân hàng (mục 4), mô tả tài sản GCN (mục 5: thửa/tờ bản đồ/mục đích/thời hạn/địa chỉ "
            "thửa/tên GCN/số phát hành/số vào sổ/cơ quan/ngày cấp). Nút 'Điền thông tin người ủy quyền' chỉ "
            "dùng khi có Văn bản ủy quyền/Giấy giới thiệu.\n"
            "⚠ ĐỂ USER TỰ TÍCH các checkbox: tư cách người yêu cầu (Bên bảo đảm/Bên nhận bảo đảm), loại giấy "
            "tờ pháp lý (CMND/CCCD hoặc Mã số thuế) ở mục 3 & 4, và tài sản 5.1 (nhãn trùng nên không tự tích "
            "đúng được).\n"
            "Đính kèm: Phiếu 01a→KQ003675, Hợp đồng bảo đảm→KQ003676, GCN gốc→KQ003684; CCCD/GCN ĐKDN/Giấy "
            "giới thiệu/khác→ô đính kèm bổ sung. Cơ quan tiếp nhận và Tỉnh/Xã khối ủy quyền là select — chọn tay."
        ),
    },
    {
        "key": "ho-tro-nguoi-cao-tuoi-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm) — engine attachBacNinhByPlan. ATTACH-ONLY (mode
        # "attach"): thủ tục chỉ có bước đính kèm, 1 thành phần bắt buộc (Tờ khai Mẫu 01 → KQ001012).
        # maThuTucHanhChinh=1.014589 khóa host bacninh.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.014589"],
        },
        "label": (
            "[Tỉnh Bắc Ninh] Hỗ trợ cho Người cao tuổi từ đủ 70 tuổi đến dưới 75 tuổi; Người cao tuổi dưới "
            "75 tuổi thường trú trên địa bàn tỉnh, là Đảng viên được tặng huy hiệu 40 năm tuổi đảng trở "
            "lên, không có lương hưu, trợ cấp bảo hiểm xã hội, trợ cấp xã hội hàng tháng"
        ),
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai đề nghị hưởng trợ cấp xã hội (Mẫu số 01) đã kê khai, có xác nhận của UBND cấp xã.\n"
            "2. Nếu có: CCCD của người cao tuổi; Kết quả tra cứu thông tin dân cư.\n"
            "Tờ khai được đính vào thành phần hồ sơ bắt buộc (KQ001012 — 01 bản chính); giấy tờ khác vào ô "
            "đính kèm bổ sung. Cổng tự điền thông tin nhân thân từ tài khoản VNeID — thủ tục này chỉ đính kèm."
        ),
    },
    {
        "key": "ho-tro-chi-phi-hoa-tang-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm): điền đơn + khối người được ủy quyền bằng
        # fill-bacninh.js, đính hai thành phần bắt buộc theo mã KQ. Khóa cả host và mã QG 1.014582
        # để không nhận nhầm thủ tục cùng mã hiển thị trên cổng khác.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.014582"],
        },
        "label": (
            "[Tỉnh Bắc Ninh] Thủ tục hỗ trợ chi phí hỏa táng (bao gồm cả điện táng) "
            "trên địa bàn tỉnh Bắc Ninh"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn/Tờ khai đề nghị hỗ trợ kinh phí hỏa táng (Mẫu số 01) đã kê khai.\n"
            "2. Hợp đồng với cơ sở hỏa táng/điện táng.\n"
            "3. Nếu có: Biên bản/Văn bản ủy quyền; Trích lục khai tử/Giấy báo tử; hóa đơn dịch vụ; "
            "CCCD của người đứng ra hỏa táng hoặc người được ủy quyền.\n"
            "Nút 'Điền thông tin người ủy quyền' chỉ dùng dữ liệu BÊN ĐƯỢC ỦY QUYỀN trong văn bản ủy "
            "quyền. Nút 'Nhập đơn đăng ký' điền riêng thông tin người chết và người đứng ra hỏa táng. "
            "PDF gộp có cả Đơn và Hợp đồng sẽ được gắn vào cả hai thành phần bắt buộc."
        ),
    },
    {
        "key": "dang-ky-nha-o-xa-hoi-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm 2836): điền ĐƠN Giấy xác nhận điều kiện nhà ở
        # (Mẫu 02) theo NAME element_762xx bằng fill-bacninh.js + khối người được ủy quyền + đính kèm
        # thành phần KQ005445 (Bản chính Mẫu 02 / Bản sao CCCD+Giấy KH). Cấu trúc 3 phần giống hỏa táng.
        # Khóa host + mã QG 1.014632 để không nhận nhầm thủ tục cùng tên trên cổng Bộ Xây dựng (dvc.moc).
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.014632"],
        },
        "label": (
            "[Tỉnh Bắc Ninh] Đăng ký mua, thuê mua, thuê nhà ở xã hội, vay vốn để hộ gia đình, cá nhân "
            "tự xây dựng hoặc cải tạo, sửa chữa nhà ở"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Giấy xác nhận về điều kiện nhà ở (Mẫu số 02) đã kê khai, ký — nguồn chính điền đơn. Hồ sơ "
            "hộ gia đình thường có 2 bản (vợ và chồng).\n"
            "2. Bản sao chứng thực Căn cước công dân của người kê khai và vợ/chồng.\n"
            "3. Bản sao Giấy chứng nhận kết hôn (nếu đã kết hôn).\n"
            "4. Nếu nộp thay: Văn bản/Giấy ủy quyền; nếu đối tượng ở mục 8 cần: giấy xác nhận của doanh "
            "nghiệp/nơi làm việc.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Nút 'Nhập đơn đăng ký' điền đơn Mẫu 02: người kê khai (mục 2-5), vợ/chồng (mục 6), đăng ký "
            "kết hôn số, đối tượng (mục 8), tỉnh nơi có dự án (mục 9), ngày khai. Nút 'Điền thông tin người "
            "ủy quyền' chỉ dùng khi có Văn bản ủy quyền (điền khối người được ủy quyền).\n"
            "Đính kèm: Mẫu 02 → Bản chính, CCCD + Giấy chứng nhận kết hôn → Bản sao của thành phần "
            "'Giấy tờ chứng minh điều kiện về nhà ở'; giấy tờ chứng minh đối tượng → ô đính kèm bổ sung.\n"
            "Để user tự làm: cơ quan tiếp nhận (Bước 1), Tỉnh/Xã của khối ủy quyền (select cascade), "
            "khối xác nhận của cơ quan (trang 2, cơ quan xác nhận sau), và thông tin nhận kết quả."
        ),
    },
    {
        "key": "cap-hoc-tap-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm 1.014581) — thủ tục KHÔNG có màn kê khai eForm
        # (eformId rỗng, wizard chỉ 2 tab). Chỉ 2 việc: (1) ỦY QUYỀN — điền khối doiTuongKhac* = HỌC
        # SINH/SINH VIÊN (chủ hồ sơ) vì HSSV chưa có VNeID nên cha/mẹ nộp thay; (2) ĐÍNH KÈM.
        # mode "attach" → nút chính "Đính kèm vào hồ sơ"; nút phụ "Điền thông tin người ủy quyền"
        # (popup.js BAC_NINH_AUTHORIZED_PERSON_CONFIG). KHÔNG vào BAC_NINH_THREE_STEP (không có đơn).
        # supportsSplitDocuments: BE luôn tách file gộp theo trang → route vào 4 mã KQ + fileDinhKem.
        # Khóa host + mã QG 1.014581 (mã hiển thị trùng trên cổng khác).
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.014581"],
        },
        "label": "[Tỉnh Bắc Ninh] Chính sách hỗ trợ chi phí học tập cho học sinh, sinh viên",
        "mode": "attach",
        "supportsSplitDocuments": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (có thể là MỘT file PDF gộp — hệ thống tự tách theo trang):\n"
            "1. Đơn đề nghị hỗ trợ chi phí học tập (Mẫu số 01) đã ký.\n"
            "2. Giấy xác nhận của cơ sở đào tạo (Mẫu số 02).\n"
            "3. Bằng tốt nghiệp THCS/THPT (bản sao chứng thực).\n"
            "4. Nếu thuộc diện ưu tiên: Giấy chứng nhận hộ nghèo/cận nghèo/khuyết tật hoặc QĐ trợ cấp xã hội.\n"
            "5. Nếu nộp thay (cha/mẹ nộp cho con chưa có VNeID): Đơn xin xác nhận ủy quyền + Lời chứng "
            "chứng thực chữ ký + CCCD của học sinh, sinh viên.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân loại theo nội dung OCR.\n"
            "Nút 'Điền thông tin người ủy quyền' điền khối thông tin HỌC SINH/SINH VIÊN (chủ hồ sơ) — cổng "
            "tự điền người nộp (cha/mẹ) từ tài khoản VNeID.\n"
            "Đính kèm: Mẫu 01→KQ001000, Mẫu 02→KQ001001, Bằng tốt nghiệp→KQ001002, giấy ưu tiên→KQ001003 "
            "(đều Bản chính); CCCD/Đơn ủy quyền/Lời chứng→ô 'File đính kèm khác'.\n"
            "Để user tự làm: cơ quan tiếp nhận (Bước 1) và Tỉnh/Xã của khối ủy quyền (select)."
        ),
    },
    {
        "key": "tach-hop-thua-dat-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay + select2) — dùng engine fill-bacninh.js.
        # Mã thủ tục đã đổi 1.012784 -> 1.115458 theo danh mục đất đai của Sở Nông nghiệp và
        # Môi trường (thông báo 1283/TB-SNNMT ngày 04/8/2026). Cổng chỉ còn phát mã mới.
        # urlScope khoá host: 1.115458 là mã QUỐC GIA, cổng iGate tỉnh khác cũng dùng đúng mã đó —
        # không khoá thì mở trang ở tỉnh khác sẽ bị nhận nhầm rồi chạy engine fill-bacninh.js
        # trên DOM không phải của Bắc Ninh.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115458"],
        },
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
        # Mã thủ tục đã đổi 1.012783 -> 1.115464 theo danh mục đất đai của Sở Nông nghiệp và
        # Môi trường (thông báo 1283/TB-SNNMT ngày 04/8/2026). Cổng chỉ còn phát mã mới.
        # urlScope khoá host: 1.115464 là mã QUỐC GIA, cổng iGate tỉnh khác cũng dùng đúng mã đó —
        # không khoá thì mở trang ở tỉnh khác sẽ bị nhận nhầm rồi chạy engine fill-bacninh.js
        # trên DOM không phải của Bắc Ninh.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115464"],
        },
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
        # Mã thủ tục đã đổi 1.012790 -> 1.115476 theo danh mục đất đai của Sở Nông nghiệp và
        # Môi trường (thông báo 1283/TB-SNNMT ngày 04/8/2026). Cổng chỉ còn phát mã mới.
        # urlScope khoá host: 1.115476 là mã QUỐC GIA, cổng iGate tỉnh khác cũng dùng đúng mã đó —
        # không khoá thì mở trang ở tỉnh khác sẽ bị nhận nhầm rồi chạy engine fill-bacninh.js
        # trên DOM không phải của Bắc Ninh.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115476"],
        },
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
        "key": "dieu-chinh-giay-phep-xay-dung",
        # Cổng Bộ Xây dựng dvc.moc.gov.vn — Form.io, engine fillFormStandard dom-* + attach attp-row (mat-table).
        # CÙNG contact-block với cap_giay_phep_xay_dung (data[fullname]/chủ hộ/chủ đầu tư/địa điểm), NHƯNG
        # KHÁC phần công trình: điều chỉnh KHÔNG có panel loại/cấp công trình + thiết kế/thẩm tra; thay bằng
        # GPXD đã cấp + data[noiDungDeNghiDieuChinh]. URL SPA ObjectId → detect apply-online id + process id.
        "detect": {
            "urlScope": ["dvc.moc.gov.vn"],
            "urlIncludes": [
                "apply-online/694404ab0348b24138aac04c",
                "process=696742774a2ad24c8486bb01",
            ],
        },
        "label": (
            "Cấp điều chỉnh giấy phép xây dựng đối với công trình cấp III, cấp IV (công trình Không theo "
            "tuyến/Theo tuyến trong đô thị/Tín ngưỡng, tôn giáo/Tượng đài, tranh hoành tráng/Theo giai đoạn "
            "cho công trình không theo tuyến/Theo giai đoạn cho công trình theo tuyến trong đô thị/Dự án) "
            "và nhà ở riêng lẻ"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn đề nghị điều chỉnh, gia hạn, cấp lại giấy phép xây dựng (Mẫu số 02) — nguồn chính điền "
            "nội dung điều chỉnh, người nộp, chủ đầu tư, địa điểm.\n"
            "2. Giấy phép xây dựng ĐÃ ĐƯỢC CẤP (kèm bản vẽ đã cấp) — số GPXD, tên/loại công trình.\n"
            "3. Bộ bản vẽ thiết kế xây dựng điều chỉnh (hồ sơ thiết kế điều chỉnh).\n"
            "4. Giấy chứng nhận QSDĐ (khi điều chỉnh làm thay đổi diện tích/chức năng sử dụng đất).\n"
            "5. CCCD chủ hộ/người nộp; nếu ủy quyền: Giấy ủy quyền + CCCD người được ủy quyền; nếu người nộp "
            "là tổ chức: Giấy chứng nhận ĐKDN.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Người nộp (nhân thân/địa chỉ), Chủ hộ/Chủ đầu tư, Địa điểm xây dựng, và khối ĐIỀU "
            "CHỈNH (tên công trình, nội dung đề nghị điều chỉnh, thời gian dự kiến hoàn thành). Ô nhân thân "
            "người nộp thiếu dữ liệu sẽ được tô đỏ để bổ sung tay.\n"
            "Bước đính kèm: GPXD đã cấp / Bộ bản vẽ điều chỉnh / Báo cáo thẩm định / Giấy tờ đất đai / Đơn "
            "Mẫu 02 tick đúng dòng thành phần hồ sơ + chọn 'Bản chính' (CCCD chỉ dùng ở bước thông tin)."
        ),
    },
    {
        "key": "sua-chua-cai-tao-gpxd-nha-o-rieng-le",
        # Cổng Bộ Xây dựng dvc.moc.gov.vn — Form.io, engine fillFormStandard dom-* + attach attp-row.
        # TÁI SỬ DỤNG process của cap_giay_phep_xay_dung (giống ~95%), nhánh nhà ở riêng lẻ (element ...NhaO).
        # HAI biến thể sửa chữa DÙNG CHUNG apply-online id, KHÁC process= → detect CHỈ theo process= (urlIncludes
        # là OR, nếu thêm apply-online id sẽ khớp cả 2). Quy trình 15 ngày = nhà ở riêng lẻ.
        "detect": {
            "urlScope": ["dvc.moc.gov.vn"],
            "urlIncludes": ["process=696899ffadf251292a49d6cb"],
        },
        "label": (
            "Cấp giấy phép xây dựng sửa chữa, cải tạo đối với công trình cấp III, cấp IV và nhà ở riêng lẻ "
            "(nhà ở riêng lẻ)"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn đề nghị cấp giấy phép xây dựng (Mẫu số 01) — thông tin người nộp, chủ hộ, địa điểm, "
            "thông số công trình sửa chữa/cải tạo.\n"
            "2. Giấy chứng nhận QSDĐ (sổ đỏ) hoặc giấy tờ hợp pháp về đất đai.\n"
            "3. Bản vẽ hiện trạng bộ phận công trình sửa chữa/cải tạo; Bộ bản vẽ thiết kế sửa chữa; Ảnh chụp "
            "hiện trạng công trình và công trình lân cận.\n"
            "4. CCCD chủ hộ/người nộp; nếu ủy quyền: Giấy ủy quyền + CCCD người được ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Người nộp + Chủ hộ/Chủ đầu tư + Địa điểm + THÔNG TIN CÔNG TRÌNH (nhánh nhà ở riêng "
            "lẻ). Ô nhân thân người nộp thiếu dữ liệu sẽ được tô đỏ để bổ sung tay.\n"
            "Bước đính kèm: Đơn / GCN QSDĐ / Bản vẽ hiện trạng / Bản vẽ thiết kế / Ảnh hiện trạng tick đúng "
            "dòng thành phần hồ sơ + chọn 'Bản chính'."
        ),
    },
    {
        "key": "sua-chua-cai-tao-gpxd-cong-trinh",
        # Như trên nhưng nhánh CÔNG TRÌNH (element ...KhongTheoTuyen + data[loaiCongTrinh]). Quy trình 10 ngày.
        "detect": {
            "urlScope": ["dvc.moc.gov.vn"],
            "urlIncludes": ["process=696899ffadf251292a49d6ca"],
        },
        "label": (
            "Cấp giấy phép xây dựng sửa chữa, cải tạo đối với công trình cấp III, cấp IV (công trình Không "
            "theo tuyến/Theo tuyến trong đô thị/Tín ngưỡng, tôn giáo/Tượng đài, tranh hoành tráng/Theo giai "
            "đoạn cho công trình không theo tuyến/Theo giai đoạn cho công trình theo tuyến trong đô thị/Dự án)"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn đề nghị cấp giấy phép xây dựng (Mẫu số 01) — thông tin người nộp, chủ đầu tư, địa điểm, "
            "thông số công trình sửa chữa/cải tạo.\n"
            "2. Giấy chứng nhận QSDĐ (sổ đỏ) hoặc giấy tờ hợp pháp về đất đai.\n"
            "3. Bản vẽ hiện trạng bộ phận công trình sửa chữa/cải tạo; Bộ bản vẽ thiết kế sửa chữa; Ảnh chụp "
            "hiện trạng công trình và công trình lân cận.\n"
            "4. CCCD/GCN ĐKDN chủ đầu tư; nếu ủy quyền: Giấy ủy quyền + CCCD người được ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Người nộp + Chủ đầu tư + Địa điểm + THÔNG TIN CÔNG TRÌNH (nhánh công trình không theo "
            "tuyến — có ô 'Loại hình công trình' và 'Loại công trình'). Ô nhân thân người nộp thiếu dữ liệu "
            "sẽ được tô đỏ để bổ sung tay.\n"
            "Bước đính kèm: Đơn / GCN QSDĐ / Bản vẽ hiện trạng / Bản vẽ thiết kế / Ảnh hiện trạng tick đúng "
            "dòng thành phần hồ sơ + chọn 'Bản chính'."
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
        "key": "cap-gcn-attp-cong-thuong",
        # Cổng DVC Bộ Công Thương dichvucong-tthc.moit.gov.vn — Form.io + attach attp-row (CÙNG cổng/engine
        # #42 cap-lai-...). Bản CẤP LẦN ĐẦU: form kê khai cơ sở SXKD (Mẫu 01a) + 4 checkbox loại hình.
        # ⚠ Field-key data[...] TRÙNG Phần I (tài khoản) / Phần IV (cơ sở) → mapper gắn OCCURRENCE 0/1.
        # Attach 5 dòng (Đơn 01a / Thuyết minh 02a-02b / GCN ĐKKD / tập huấn / sức khỏe). detect textPriority
        # để phân biệt với "Cấp LẠI…" (#42) — cùng cổng, tiêu đề chỉ khác "lại".
        "detect": {
            "textIncludes": [
                "Cấp Giấy chứng nhận đủ điều kiện an toàn thực phẩm đối với cơ sở sản xuất, kinh doanh thực phẩm"
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp Giấy chứng nhận đủ điều kiện an toàn thực phẩm đối với cơ sở sản xuất, kinh doanh thực phẩm",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. CCCD người nộp (nếu nộp thay: thêm CCCD/Giấy ủy quyền của người nộp thay).\n"
            "2. Giấy chứng nhận đăng ký hộ kinh doanh/doanh nghiệp — tên cơ sở, mã số, địa chỉ trụ sở, "
            "ngành nghề, chủ hộ.\n"
            "3. Đơn đề nghị cấp Giấy chứng nhận cơ sở đủ điều kiện ATTP theo Mẫu số 01a (đã ký).\n"
            "4. Bản thuyết minh về cơ sở vật chất, trang thiết bị, dụng cụ (Mẫu 02a/02b).\n"
            "5. Giấy xác nhận đã tập huấn kiến thức ATTP; Danh sách/Giấy khám sức khỏe.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Tài khoản nộp (Phần I) + Chủ hồ sơ/cơ sở (Phần II) + Đơn 01a (nơi/ngày lập, kính "
            "gửi) + Cơ sở SXKD (Phần IV: tên, địa chỉ, ngành nghề) + Loại hình (sản xuất/kinh doanh/vừa "
            "SX vừa KD/chuỗi).\n"
            "Bước đính kèm: Đơn 01a / Bản thuyết minh 02a-02b / Bản sao GCN ĐKKD / Giấy tập huấn / Danh "
            "sách sức khỏe → 5 dòng tương ứng. CCCD/ủy quyền chỉ dùng ở bước thông tin."
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
        "key": "ho-tro-chi-phi-hoa-tang",
        # Cổng DVC quốc gia, eForm Form.io. KHÁC "ho-tro-chi-phi-hoa-tang-bac-ninh" (eForm riêng của
        # tỉnh, field element_757xx): bản này nộp tại UBND cấp xã theo khối "Chọn cơ quan thực hiện".
        "detect": {
            "urlIncludes": ["maThuTuc=1.012749"],
            "textIncludes": ["Hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng"],
            "headingDisabled": True,
        },
        "label": "Hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Tờ khai đề nghị hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng "
            "(Mẫu số 01 cho cá nhân, Mẫu số 02 cho cơ quan, tổ chức).\n"
            "2. Hợp đồng dịch vụ hỏa táng và Hóa đơn tài chính của cơ sở hỏa táng (đủ CẢ HAI).\n"
            "3. Trích lục khai tử/giấy chứng tử của người chết.\n"
            "4. Nếu nộp thay: Văn bản ủy quyền đã chứng thực (hoặc giấy giới thiệu của cơ quan, tổ chức).\n"
            "5. CCCD của người nộp hồ sơ (chỉ dùng để đọc nhân thân, không đính kèm).\n"
            "Form điền: Thông tin chung (họ tên chủ hồ sơ, ngày sinh, giới tính, điện thoại, điện thoại "
            "ủy quyền) + Thông tin người nộp (họ tên, số định danh, ngày cấp, nơi cấp, ghi chú ủy quyền) "
            "+ Nội dung yêu cầu giải quyết + Địa chỉ người nộp. Panel Địa chỉ thửa đất KHÔNG áp dụng.\n"
            "Bước đính kèm: Mẫu 01 → dòng 1, Mẫu 02 → dòng 2, Hợp đồng và Hóa đơn → cùng dòng 3, "
            "Văn bản ủy quyền → dòng 4; Trích lục khai tử được thêm thành một thành phần hồ sơ mới.\n"
            "Mã xác nhận (captcha) và ô cam kết ở bước cuối vẫn phải tự nhập."
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
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Bản khai của thân nhân đề nghị hưởng chế độ mai táng phí (Mẫu 02-MTP, có xác nhận UBND xã) "
            "theo Quyết định số 49/2015/QĐ-TTg — nguồn chính điền form.\n"
            "2. Bản trích sao Quyết định của đối tượng từ trần đã được hưởng chế độ trợ cấp một lần (QĐ-BTL).\n"
            "3. Trích lục khai tử/Giấy chứng tử của người từ trần.\n"
            "4. Biên bản họp đồng thuận của những người cùng hàng thừa kế (Mẫu số 80A) — nếu có nhiều thân "
            "nhân.\n"
            "5. CCCD/CMND của thân nhân/người đứng khai nhận trợ cấp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Bước đính kèm: Bản trích sao Quyết định trợ cấp một lần và Trích lục khai tử vào 2 ô cố định; "
            "Bản khai Mẫu 02-MTP, Biên bản 80A và CCCD đính qua nút 'Thêm giấy tờ'."
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
        "key": "cap-lai-chung-chi-hanh-nghe-thu-y",
        # Mã TTHC 1.005319 — nộp tại SỞ Nông nghiệp và Môi trường (ke_khai_links đặt selectSo). Form.io,
        # engine fillFormStandard dom-* + attach attp-row (bảng 1 dòng Đơn 03.HNTY). Field-key nhân thân
        # data[...] TRÙNG KHÍT #97/#101; Phần III là nội dung Đơn 03.HNTY. URL kê khai DVCQG được
        # with_ke_khai_detect_urls ghép thêm vào urlIncludes; form thật là SPA → detect theo cụm tên.
        "detect": {
            "textIncludes": [
                "cấp lại chứng chỉ hành nghề thú y",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp lại Chứng chỉ hành nghề thú y",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền (của NGƯỜI ĐỨNG ĐƠN — người được cấp lại chứng chỉ):\n"
            "1. Đơn đăng ký cấp lại Chứng chỉ hành nghề thú y (Mẫu 03.HNTY) — đã ký.\n"
            "2. Thẻ Căn cước công dân / Căn cước (mặt trước + mặt sau) của người đứng đơn. Thiếu thẻ "
            "này thì ô 'Căn cước công dân số' và 'Ngày cấp' phải sửa tay vì đơn thường không ghi.\n"
            "3. Chứng chỉ hành nghề thú y ĐÃ CẤP (bản cũ) — để lấy Số đăng ký và ngày chứng chỉ hết "
            "hiệu lực; thiếu bản này thì hai ô đó phải nhập tay.\n"
            "4. Ảnh 4x6 nền xanh (theo mẫu đơn yêu cầu) — để đính kèm.\n"
            "5. Nếu người KHÁC nộp thay: tải kèm CCCD của người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "⚠ Form bước kê khai CHỈ LÀ TỜ ĐƠN nên khối 'Thông tin chung' phải là người ĐỨNG ĐƠN. Cổng "
            "prefill sẵn thông tin tài khoản đăng nhập, extension sẽ GHI ĐÈ bằng thông tin đọc từ đơn — "
            "nộp thay cũng không cần bấm nút 'Sao chép thông tin người nộp'.\n"
            "Extension tự tích mục 'Đã được cấp Chứng chỉ hành nghề thú y' theo đúng dòng phạm vi được "
            "đánh dấu trong đơn; dòng nào đơn ghi tắt không khớp được thì báo ở phần cảnh báo để tích "
            "tay.\n"
            "Bước đính kèm: Đơn 03.HNTY được tick vào dòng 'Đơn đăng ký cấp lại', chọn loại bản '1 Bản "
            "chính' rồi đính tệp scan (CCCD chỉ dùng ở bước thông tin)."
        ),
    },
    {
        "key": "cap-gcn-dang-ky-tau-ca",
        # Cổng Nông nghiệp & Môi trường dichvucongnnmt.mae.gov.vn — Form.io, engine fillFormStandard dom-*
        # + attach attp-row (16 dòng thành phần hồ sơ). Field-key nhân thân data[...] TRÙNG KHÍT #66/#92.
        # Form CHỈ thu nhân thân 2 vai (KHÔNG occurrence, KHÔNG ô thông số tàu — tàu chỉ ở file đính kèm).
        # URL SPA ObjectId → detect theo apply-online id + process id lấy từ HTML thật.
        "detect": {"urlIncludes": [
            "apply-online/6943d234d7c2fb1812f2c3c4",
            "process=6a5dad038f4b564db2488af7",
        ]},
        "label": "Cấp giấy chứng nhận đăng ký tàu cá, tàu phục vụ nuôi trồng thủy sản",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền (của CHỦ TÀU — người/tổ chức đứng tên đăng ký):\n"
            "1. Tờ khai đăng ký tàu cá (Mẫu số 02a.ĐKT) — đã ký.\n"
            "2. Thẻ Căn cước công dân / Căn cước (mặt trước + mặt sau) của chủ tàu để đối chiếu.\n"
            "3. Tùy hồ sơ: Hợp đồng mua bán/chuyển nhượng tàu, Giấy chứng nhận đăng ký tàu cá cũ, Giấy "
            "chứng nhận xóa đăng ký, Thông báo nộp lệ phí trước bạ, Giấy chứng nhận an toàn kỹ thuật, "
            "Giấy chứng nhận cải hoán/xuất xưởng — để đính kèm.\n"
            "4. Nếu người KHÁC nộp thay: tải kèm CCCD của người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form online CHỈ thu nhân thân người nộp/chủ tàu; toàn bộ thông tin tàu (số đăng ký, kích "
            "thước, máy chính, nghề, vùng hoạt động…) nằm trong file đính kèm, KHÔNG nhập lại trên form.\n"
            "⚠ Chủ tàu là chủ MỚI (bên mua Hợp đồng / người khai Tờ khai 02a.ĐKT) — không lấy chủ cũ trên "
            "Giấy chứng nhận đăng ký cũ.\n"
            "Nếu TỰ NỘP: extension chỉ điền Phần 1 và TICH ô 'Người nộp là chủ hồ sơ' (cổng để sẵn CHƯA "
            "tick) — cổng tự đổ sang Phần 2. Nếu NỘP THAY: extension bỏ tích, điền Phần 1 (người nộp) và "
            "Phần 2 (chủ tàu) riêng.\n"
            "Bước đính kèm: mỗi giấy tờ được tick vào đúng dòng thành phần hồ sơ và chọn 'Scan tệp tin'; "
            "ảnh tàu và CCCD cần đính thủ công (CCCD chỉ dùng ở bước thông tin)."
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
        "key": "chuyen-muc-dich-su-dung-dat-da-nang",
        # Cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn — Form.io, engine fillFormStandard dom-* + attach
        # attp-row. CÙNG form/contact-block + attach biến động với #75 (dang-ky-bien-dong-dat-dai-da-nang):
        # near-clone, chỉ khác _PROC_TITLE (nội dung yêu cầu) + detect. KHÁC bản chất: chuyển MỤC ĐÍCH SDĐ
        # (1 chủ đất, không xin phép) — KHÔNG có bên chuyển nhượng/bên nhận. URL SPA ObjectId → detect cụm
        # tên đặc trưng (phân biệt #75 "chuyển đổi QSDĐ nông nghiệp").
        "detect": {
            "urlScope": ["dichvucong.danang.gov.vn"],
            "textIncludes": [
                "chuyển mục đích sử dụng đất không phải xin phép",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Đà Nẵng] Đăng ký biến động chuyển mục đích sử dụng đất không phải xin phép cơ quan nhà nước "
            "có thẩm quyền"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn đăng ký biến động đất đai (Mẫu số 18/09) — xác định chủ đất đề nghị chuyển mục đích.\n"
            "2. Giấy chứng nhận QSDĐ (sổ đỏ) của thửa đất chuyển mục đích.\n"
            "3. CCCD chủ đất / người nộp.\n"
            "4. Nếu chủ hồ sơ ỦY QUYỀN cho người khác nộp: Hợp đồng ủy quyền + CCCD người được ủy quyền.\n"
            "5. Nếu chủ hồ sơ là TỔ CHỨC: Giấy chứng nhận đăng ký doanh nghiệp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Chủ hồ sơ (chủ đất) + Người nộp (nhân thân, địa chỉ, loại đối tượng). Nếu ủy quyền "
            "→ BỎ tích 'Chủ hồ sơ cũng là người nộp' và điền cả hai. Nội dung yêu cầu tự ghép theo tên chủ "
            "hồ sơ.\n"
            "Bước đính kèm: Đơn Mẫu 18, Bản gốc Giấy chứng nhận... tick đúng dòng + chọn 'Bản chính' (CCCD "
            "chỉ dùng ở bước thông tin)."
        ),
    },
    {
        "key": "tach-hop-thua-dat-da-nang",
        # Cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn — Form.io, engine fillFormStandard dom-* + attach
        # attp-row. CÙNG form/contact-block với #75/chuyen_muc_dich (data[...] y hệt, 1 panel thongTinChung,
        # HAI vai Chủ hồ sơ/Người nộp). KHÁC: bảng thành phần hồ sơ RIÊNG 4 dòng của form tách/hợp thửa
        # (Đơn Mẫu 21 Bản chính / GCN Bản sao / Văn bản CQCTQ Bản sao / Bản vẽ Mẫu 22 Bản sao + Giấy phép
        # đo đạc gộp chung dòng Bản vẽ). Detect theo TÊN THỦ TỤC trong trang (textPriority). Cụm duy nhất,
        # không đụng thủ tục nào khác. (ObjectId cũ apply-online 68a3e64234503f3a1eb5b4ca / process
        # 68a82092e4dd3b57f2bdca15 giữ trong comment nếu cần đổi lại URL.)
        "detect": {
            "urlScope": ["dichvucong.danang.gov.vn"],
            "textIncludes": [
                "Tách thửa hoặc hợp thửa đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Đà Nẵng] Tách thửa đất hoặc hợp thửa đất",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn đề nghị tách thửa đất, hợp thửa đất (Mẫu số 21) — xác định chủ đất đề nghị.\n"
            "2. Giấy chứng nhận QSDĐ (sổ đỏ) của thửa đất tách/hợp.\n"
            "3. Bản vẽ tách thửa đất, hợp thửa đất (Mẫu số 22) do đơn vị đo đạc lập (kèm Giấy phép hoạt "
            "động đo đạc của đơn vị nếu có).\n"
            "4. Văn bản của cơ quan có thẩm quyền về nội dung tách/hợp thửa (nếu có).\n"
            "5. CCCD chủ đất / người nộp.\n"
            "6. Nếu chủ hồ sơ ỦY QUYỀN cho người khác nộp: Hợp đồng/Giấy ủy quyền + CCCD người được ủy "
            "quyền. Nếu chủ hồ sơ là TỔ CHỨC: Giấy chứng nhận đăng ký doanh nghiệp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Chủ hồ sơ (chủ đất) + Người nộp (nhân thân, địa chỉ, loại đối tượng). Nếu ủy quyền "
            "→ BỎ tích 'Chủ hồ sơ cũng là người nộp' và điền cả hai. Nội dung yêu cầu tự ghép theo tên chủ "
            "hồ sơ.\n"
            "⚠ Tải TỪNG giấy tờ thành file RIÊNG (thủ tục này đính kèm nguyên file, không tự tách trang một "
            "PDF gộp). Bước đính kèm: Đơn Mẫu 21→'Bản chính'; GCN, Bản vẽ Mẫu 22, Giấy phép đo đạc, Văn bản "
            "CQCTQ→'Bản sao', tick đúng dòng thành phần hồ sơ (CCCD chỉ dùng ở bước thông tin)."
        ),
    },
    {
        "key": "giao-thue-chuyen-muc-dich-dat-da-nang",
        # Cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn — Form.io, engine fillFormStandard dom-* + attach
        # attp-row. CÙNG contact-block với #75/chuyen_muc_dich (data[...] người nộp/chủ hồ sơ y hệt, HAI vai).
        # KHÁC: form có THÊM panel "Thông tin thửa đất" (data[SoThuaDat]/[SoToBanDo]/[diaChiThuaDat]/
        # [province2]/[district2]/[nation2]) → mapper điền thêm Số thửa/Số tờ/Địa chỉ thửa. Bảng thành phần
        # hồ sơ ~12 dòng theo nhiều nhánh (giao đất/thuê đất/chuyển MĐ/giao rừng/thuê rừng/gia hạn), chỉ
        # route Đơn Mẫu 01 + GCN/quyết định + vài dòng điều kiện. Detect theo TÊN THỦ TỤC (textPriority) —
        # cụm đuôi đặc trưng "giao đất và giao rừng..." duy nhất. (ObjectId cũ apply-online
        # 686290378ab0bd7d9e56a5bc / process 68b125060d40786af8e8746f giữ trong comment nếu cần đổi lại URL.)
        "detect": {
            "urlScope": ["dichvucong.danang.gov.vn"],
            "textIncludes": [
                "giao đất và giao rừng; cho thuê đất và cho thuê rừng, gia hạn sử dụng đất khi hết thời hạn sử dụng đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Đà Nẵng] Giao đất, cho thuê đất, chuyển mục đích sử dụng đất (không đấu giá, không đấu thầu); "
            "giao đất và giao rừng; cho thuê đất và cho thuê rừng; gia hạn sử dụng đất"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn đề nghị theo Mẫu số 01 (giao đất/cho thuê đất/chuyển mục đích/giao rừng/thuê rừng/gia "
            "hạn) — xác định người đề nghị + nội dung yêu cầu + thửa đất.\n"
            "2. Giấy chứng nhận QSDĐ (sổ đỏ) hoặc quyết định giao/cho thuê/cho phép chuyển mục đích — nguồn "
            "Số thửa, Số tờ, địa chỉ thửa đất.\n"
            "3. CCCD chủ hồ sơ / người nộp.\n"
            "4. Nếu chủ hồ sơ ỦY QUYỀN cho người khác nộp: Hợp đồng/Giấy ủy quyền + CCCD người được ủy "
            "quyền. Nếu chủ hồ sơ là TỔ CHỨC: Giấy chứng nhận đăng ký doanh nghiệp.\n"
            "5. Theo trường hợp: Phương án sử dụng tầng đất mặt Mẫu 26 (đất trồng lúa) / Dự án đầu tư + báo "
            "cáo, bản đồ hiện trạng rừng (giao rừng) / kết quả đấu giá thuê rừng (thuê rừng).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Chủ hồ sơ + Người nộp (nhân thân, địa chỉ, loại đối tượng) + Thông tin thửa đất (Số "
            "thửa, Số tờ, Địa chỉ thửa đất). Nếu ủy quyền → BỎ tích 'Chủ hồ sơ cũng là người nộp' và điền cả "
            "hai. Nội dung yêu cầu chép đầy đủ từ Đơn Mẫu 01.\n"
            "⚠ Tải TỪNG giấy tờ thành file RIÊNG (đính kèm nguyên file, không tự tách trang một PDF gộp). "
            "Bước đính kèm: Đơn Mẫu 01→'Bản chính'; GCN/quyết định→'Bản sao', tick đúng dòng thành phần hồ "
            "sơ (CCCD/tờ khai thuế/cam kết/ủy quyền chỉ dùng để đối chiếu, không có dòng riêng)."
        ),
    },
    {
        "key": "dang-ky-dat-dai-lan-dau-da-nang",
        # Cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn — Form.io, engine fillFormStandard dom-* + attach
        # attp-row. Form field-key data[...] Y HỆT #136 giao_thue (contact-block 2 vai + panel thửa đất
        # data[SoThuaDat]/[SoToBanDo]/[diaChiThuaDat]/[province2]/[district2]/[nation2]). KHÁC bản chất:
        # đăng ký/cấp GCN LẦN ĐẦU → chưa có GCN; nội dung từ Đơn Mẫu 15, thửa đất từ Đơn M15 + Hồ sơ đo đạc;
        # chủ hồ sơ có thể là NGƯỜI ĐƯỢC CỬ ĐẠI DIỆN (VB thỏa thuận cho hộ gia đình/nhiều người/thừa kế).
        # Bảng thành phần hồ sơ ~20 dòng theo nhiều trường hợp; route Đơn M15 + giấy tờ đất cũ + trích đo +
        # thừa kế + nghĩa vụ tài chính + VB đại diện. Detect theo TÊN THỦ TỤC (textPriority) — cụm đuôi "lần
        # đầu đối với hộ gia đình...người gốc Việt Nam..." đặc trưng, KHÁC cap_doi dù cùng "Giấy chứng nhận".
        # (ObjectId cũ apply-online 6864f140dbb5ad66c1bc54fc / process 68b2f4fa151bdc7657f1665e giữ comment.)
        "detect": {
            "urlScope": ["dichvucong.danang.gov.vn"],
            "textIncludes": [
                "lần đầu đối với hộ gia đình, cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Đà Nẵng] Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, "
            "quyền sở hữu tài sản gắn liền với đất lần đầu (hộ gia đình, cá nhân, cộng đồng dân cư, người "
            "gốc Việt Nam định cư ở nước ngoài)"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15 + phụ lục 15a/15b) — xác định "
            "người sử dụng đất + nội dung yêu cầu + thửa đất.\n"
            "2. Hồ sơ đo đạc (mảnh trích đo bản đồ địa chính/sơ đồ thửa) — nguồn Số thửa, Số tờ, địa chỉ thửa.\n"
            "3. Giấy tờ về quyền sử dụng đất/nhà đất cũ (theo Điều 137/148/149 Luật Đất đai) nếu có.\n"
            "4. CCCD chủ hồ sơ / người nộp.\n"
            "5. Nếu là hộ gia đình/nhiều người chung/thừa kế: Văn bản thỏa thuận cử người đại diện đứng tên "
            "GCN (+ giấy tờ thừa kế: giấy chứng tử, trích lục khai tử, giấy khai sinh).\n"
            "6. Chứng từ nghĩa vụ tài chính (tờ khai thuế/lệ phí trước bạ/tiền sử dụng đất) nếu có.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Chủ hồ sơ + Người nộp (nhân thân, địa chỉ, loại đối tượng) + Thông tin thửa đất (Số "
            "thửa, Số tờ, Địa chỉ thửa đất). Nếu ủy quyền/đại diện → BỎ tích 'Chủ hồ sơ cũng là người nộp' "
            "và điền cả hai. Nội dung yêu cầu chép đầy đủ từ Đơn Mẫu 15.\n"
            "⚠ Tải TỪNG giấy tờ thành file RIÊNG (đính kèm nguyên file, không tự tách trang một PDF gộp). "
            "Bước đính kèm: Đơn Mẫu 15→'Bản chính'; trích đo→'Bản chính'; giấy tờ đất cũ/thừa kế/nghĩa vụ "
            "tài chính/VB đại diện→'Bản sao', tick đúng dòng thành phần hồ sơ (CCCD chỉ dùng để đối chiếu)."
        ),
    },
    {
        "key": "cap-doi-gcn-da-nang",
        # Cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn — Form.io (Sở NN&MT), engine fillFormStandard dom-*
        # + attach attp-row. CÙNG contact-block với chuyen_muc_dich/tach_hop_thua/#75 (1 panel thongTinChung,
        # data[...] người nộp/chủ hồ sơ y hệt + data[organization]/[taxCode] cho tổ chức). KHÁC #135-137:
        # KHÔNG có panel thửa đất. Nguồn: Đơn Mẫu 18 + Bản gốc GCN + Phiếu đo đạc. ⚠ Form KHÔNG có ô số GCN
        # → mapper ghép số GCN cần cấp đổi (GCN_So) vào data[noidungyeucaugiaiquyet]. Chủ hồ sơ có thể ĐỒNG
        # SỞ HỮU vợ+chồng (ownerFullname ghép 2 tên). Attach 3 dòng: Đơn M18 Bản chính / Bản gốc GCN Bản gốc
        # / Mảnh trích đo Bản sao. Detect theo TÊN THỦ TỤC (textPriority) — "Cấp đổi Giấy chứng nhận..." đặc
        # trưng ("cấp đổi" phân biệt với dang-ky-dat-dai "cấp Giấy chứng nhận"). (ObjectId cũ apply-online
        # 68a3e45c34503f3a1eb5b445 / process 68aed0c549125908ceb83ad8 giữ comment nếu cần đổi lại URL.)
        # ⚠ Đây là FORM 1 (quy trình gốc). Cổng còn FORM 2 (05 NLV - iLis, key data[village]...) chưa hỗ trợ.
        "detect": {
            "urlScope": ["dichvucong.danang.gov.vn"],
            "textIncludes": [
                "Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Đà Nẵng] Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18) — xác định người sử dụng "
            "đất + nội dung/lý do cấp đổi.\n"
            "2. Bản gốc Giấy chứng nhận đã cấp (+ Trang bổ sung nếu có) — nguồn SỐ Giấy chứng nhận cần cấp "
            "đổi (số phát hành + số vào sổ).\n"
            "3. Mảnh trích đo bản đồ địa chính / Phiếu đo đạc chỉnh lý thửa đất (nếu có).\n"
            "4. CCCD chủ hồ sơ / người nộp.\n"
            "5. Nếu ỦY QUYỀN cho người khác nộp: Giấy ủy quyền + CCCD người được ủy quyền. Nếu chủ hồ sơ là "
            "TỔ CHỨC: Giấy chứng nhận đăng ký doanh nghiệp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Chủ hồ sơ (đứng tên GCN; đồng sở hữu vợ+chồng ghi đủ 2 tên) + Người nộp (nhân thân, "
            "địa chỉ, loại đối tượng). Nếu ủy quyền → BỎ tích 'Chủ hồ sơ cũng là người nộp' và điền cả hai. "
            "Số Giấy chứng nhận cần cấp đổi được ghép vào 'Nội dung yêu cầu giải quyết' (form không có ô riêng).\n"
            "⚠ Tải TỪNG giấy tờ thành file RIÊNG (đính kèm nguyên file). Bước đính kèm: Đơn Mẫu 18→'Bản "
            "chính'; Bản gốc Giấy chứng nhận→'Bản gốc'; Mảnh trích đo→'Bản sao', tick đúng dòng thành phần "
            "hồ sơ (CCCD/ủy quyền/GCN ĐKDN chỉ dùng để đối chiếu)."
        ),
    },
    {
        "key": "xoa-dang-ky-bien-phap-bao-dam-da-nang",
        # Cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn — Form.io, engine fillFormStandard dom-* + attach
        # attp-row. Form contact-block Y HỆT cap_doi_gcn/chuyen_muc_dich (1 panel, data[...] người nộp/chủ
        # hồ sơ + organization/taxCode, KHÔNG panel thửa). Near-clone cap_doi. ⚠ Form KHÔNG có ô số GCN →
        # mapper ghép số GCN tài sản bảo đảm (GCN_So) vào data[noidungyeucaugiaiquyet]. HAI vai: bên bảo đảm
        # (chủ hồ sơ, có thể tổ chức) / người được ủy quyền (người nộp). Attach 9 dòng (nhiều dòng điều kiện)
        # → route Phiếu Mẫu 03a (Bản chính) / Bản gốc GCN / VB đồng ý xóa của bên nhận bảo đảm / VB đại diện.
        # Detect theo TÊN THỦ TỤC (textPriority) trong trang. ⚠ Cụm của #68 dang-ky-bien-phap-bao-dam-qsdd
        # ("đăng ký biện pháp bảo đảm bằng quyền sử dụng đất") là SUBSTRING của trang này, nhưng textPriority
        # chấm điểm theo ĐỘ DÀI cụm → tiêu đề đầy đủ (có "Xóa" + ", tài sản gắn liền với đất") DÀI HƠN nên
        # thắng trên trang xóa; trang #68 không chứa "Xóa" nên chỉ #68 khớp. (2 ObjectId apply-online
        # 68b01d569d1db539542d7399 / process 68b01d7c49125908ceb85012 giữ trong ghi chú nếu cần đổi lại URL.)
        "detect": {
            "urlScope": ["dichvucong.danang.gov.vn"],
            "textIncludes": [
                "Xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Đà Nẵng] Xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu số 03a) — xác định bên bảo đảm + nội dung "
            "yêu cầu xóa + số Giấy chứng nhận tài sản bảo đảm.\n"
            "2. Bản gốc Giấy chứng nhận của tài sản bảo đảm.\n"
            "3. Văn bản đồng ý xóa/xác nhận giải chấp của bên nhận bảo đảm (ngân hàng) nếu có.\n"
            "4. CCCD chủ hồ sơ / người nộp.\n"
            "5. Nếu ỦY QUYỀN cho người khác nộp: Giấy ủy quyền + CCCD người được ủy quyền. Nếu chủ hồ sơ là "
            "TỔ CHỨC (bên bảo đảm là doanh nghiệp): Giấy chứng nhận đăng ký doanh nghiệp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Chủ hồ sơ (bên bảo đảm) + Người nộp (nhân thân, địa chỉ, loại đối tượng). Nếu ủy "
            "quyền → BỎ tích 'Chủ hồ sơ cũng là người nộp' và điền cả hai. Số Giấy chứng nhận tài sản bảo "
            "đảm được ghép vào 'Nội dung yêu cầu giải quyết' (form không có ô riêng).\n"
            "⚠ Tải TỪNG giấy tờ thành file RIÊNG (đính kèm nguyên file). Bước đính kèm: Phiếu Mẫu 03a→'Bản "
            "chính'; Bản gốc Giấy chứng nhận→'Bản chính'; Văn bản đồng ý xóa→'Bản chính'; Giấy ủy quyền→'Bản "
            "sao', tick đúng dòng thành phần hồ sơ (CCCD chỉ dùng để đối chiếu)."
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
        "key": "dinh-chinh-gcn-da-cap-da-nang",
        # Cổng DVC TP Đà Nẵng dichvucong.danang.gov.vn — Form.io, engine fillFormStandard dom-* + attach
        # attp-row. CÙNG cổng + field-key contact block Y HỆT #110 (cap-gcn-so-nha-da-nang); THÊM Phần II
        # thửa đất (diaChiThuaDat/SoToBanDo/SoThuaDat/province2/district2). noidungyeucaugiaiquyet = nội
        # dung ĐÍNH CHÍNH (mục 2 Đơn Mẫu 18). Attach 4 dòng. URL SPA ObjectId → detect theo cụm tên.
        "detect": {
            "urlScope": ["dichvucong.danang.gov.vn"],
            "textIncludes": [
                "Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Đà Nẵng] Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (ưu tiên scan RIÊNG từng loại để đính đúng ô):\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18) đã ký — nội dung đính "
            "chính + nhân thân người đề nghị.\n"
            "2. Bản gốc Giấy chứng nhận đã cấp (giấy đang đề nghị đính chính) — thông tin thửa đất.\n"
            "3. Giấy tờ chứng minh sai sót: CCCD (thông tin đúng), Trích lục kết hôn, Giấy khai sinh, Hợp "
            "đồng chuyển dịch…\n"
            "4. Nếu nộp thay: Văn bản ủy quyền + CCCD người được ủy quyền.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Chủ hồ sơ (người đề nghị đính chính) + Người nộp (nhân thân, địa chỉ). Mặc định tự "
            "nộp → tích 'Chủ hồ sơ cũng là người nộp'; nếu ủy quyền → BỎ tích và điền cả hai. Nội dung yêu "
            "cầu = nội dung đính chính (chép mục 2 Đơn Mẫu 18). Phần II điền địa chỉ/tờ bản đồ/số thửa từ GCN.\n"
            "Bước đính kèm: GCN đã cấp→dòng 1; Giấy tờ chứng minh sai sót→dòng 2; Văn bản ủy quyền→dòng 3 "
            "(khi có); Đơn Mẫu 18→dòng 4 (đều Bản chính)."
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
        "key": "cho-thue-thue-mua-nha-o-xa-hoi",
        # Cổng DVC Bộ Xây dựng dvc.moc.gov.vn — Form.io, engine fillFormStandard dom-* + attach attp-row
        # (CÙNG cổng #76/#78/#113). ⚠ Field-key data[...] TRÙNG giữa Phần I (người nộp) và Phần III (người
        # viết đơn) → mapper gắn OCCURRENCE 0/1. Có DATAGRID thành viên gia đình (dtgrid1, như #76) +
        # checkbox hình thức (mua/thuemua/thue) + thực trạng nhà ở + cam đoan. URL SPA ObjectId → detect
        # theo cụm tên. Attach 4 dòng (Tờ đơn / chứng minh ĐỐI TƯỢNG chính sách / chứng minh ĐIỀU KIỆN
        # nhà ở - thu nhập / CCCD, đều Bản chính).
        "detect": {
            "urlScope": ["dvc.moc.gov.vn"],
            "textIncludes": [
                "Cho thuê, cho thuê mua nhà ở xã hội do Nhà nước đầu tư xây dựng bằng vốn đầu tư công",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cho thuê, cho thuê mua nhà ở xã hội do Nhà nước đầu tư xây dựng bằng vốn đầu tư công",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Tờ đơn đăng ký thuê (hoặc thuê mua) nhà ở xã hội theo mẫu (đã ký) — nội dung khai: nhân "
            "thân, nghề nghiệp, nơi ở hiện tại, thường trú, đối tượng chính sách, thực trạng nhà ở, thành "
            "viên gia đình, hình thức đăng ký.\n"
            "2. CCCD/Căn cước người viết đơn — họ tên, ngày sinh, giới tính, số định danh, ngày/nơi cấp, "
            "nơi thường trú.\n"
            "3. Giấy tờ chứng minh ĐỐI TƯỢNG chính sách (Huân/Huy chương kháng chiến, bằng khen, Giấy "
            "chứng nhận thương binh, Giấy báo tử liệt sĩ, giấy tờ quân nhân/công an, quyết định miễn "
            "giảm tiền thuê…) nếu có.\n"
            "4. Giấy tờ chứng minh ĐIỀU KIỆN về nhà ở/thu nhập (xác nhận hộ nghèo, xác nhận thu nhập, "
            "xác nhận thực trạng nhà ở…) nếu có.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Người nộp (Phần I) + Người viết đơn (Phần III: nhân thân, nơi ở hiện tại, thường "
            "trú, nghề nghiệp, đối tượng) + Hình thức (thuê/thuê mua) + Thành viên gia đình + Thực trạng "
            "nhà ở + Cam đoan + Ký.\n"
            "Bước đính kèm: Tờ đơn thuê → dòng 'Đơn đăng ký thuê nhà ở xã hội theo mẫu'; giấy chứng minh "
            "ĐỐI TƯỢNG (huân/huy chương, người có công, miễn giảm tiền thuê) → dòng 'Giấy tờ chứng minh "
            "đối tượng theo hướng dẫn của Bộ trưởng Bộ Xây dựng…'; giấy chứng minh ĐIỀU KIỆN (thu nhập, "
            "hộ nghèo, thực trạng nhà ở) → dòng 'Giấy tờ chứng minh điều kiện được hưởng chính sách'; "
            "CCCD → dòng 'Trường hợp thuê nhà ở xã hội' (đều Bản chính). GCN ĐKDN/sổ hộ khẩu chỉ dùng ở "
            "bước thông tin."
        ),
    },
    {
        "key": "tham-dinh-bcnckt",
        # Cổng DVC Bộ Xây dựng dvc.moc.gov.vn — Form.io + attach attp-row (CÙNG cổng #113/#76/#91). Form
        # PHỨC TẠP (~70 field): người nộp + doanh nghiệp/chủ đầu tư + dự án + 4 container quy hoạch/phê
        # duyệt + năng lực nhà thầu (khảo sát/thiết kế/thẩm tra) + 2 datagrid bộ môn. Nguồn CHÍNH = Tờ trình
        # thẩm định (Mẫu 01). ⚠ province/district/address TRÙNG 2× → OCCURRENCE 0 (nơi ở người nộp) / 1
        # (địa điểm xây dựng dự án). Nhiều field không có trong Tờ trình → để trống. Attach 8 dòng chính.
        "detect": {
            "urlScope": ["dvc.moc.gov.vn"],
            "textIncludes": [
                "Thẩm định Báo cáo nghiên cứu khả thi đầu tư xây dựng",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "Thẩm định Báo cáo nghiên cứu khả thi đầu tư xây dựng/Báo cáo nghiên cứu khả thi "
            "đầu tư xây dựng điều chỉnh"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Tờ trình thẩm định Báo cáo nghiên cứu khả thi (Mẫu số 01) — nguồn chính: chủ đầu tư, dự án, "
            "quy hoạch/phê duyệt, năng lực nhà thầu khảo sát/thiết kế/thẩm tra.\n"
            "2. CCCD người nộp hồ sơ (đại diện chủ đầu tư) — để điền Phần I; hệ thống xác định người nộp "
            "theo tài khoản VNeID.\n"
            "3. Kèm nếu có (để đính kèm): QĐ phê duyệt ĐTM/giấy phép môi trường, Văn bản chủ trương đầu tư, "
            "Thỏa thuận đấu nối hạ tầng, Danh sách nhà thầu + chứng chỉ, QĐ phê duyệt quy hoạch + bản vẽ, "
            "Hồ sơ khảo sát/thiết kế cơ sở, Giấy chứng nhận đầu tư.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Form điền: Người nộp + Chủ đầu tư (I.4-I.5) + Dự án (nhóm, loại/cấp công trình, tổng mức đầu "
            "tư, nguồn vốn, quy mô, tiến độ, địa điểm) + Quy hoạch/phê duyệt (4 văn bản) + Năng lực nhà thầu "
            "(khảo sát/thiết kế/thẩm tra + chủ trì bộ môn).\n"
            "Lưu ý: các field không có trong Tờ trình (diện tích đất, chi phí xây dựng/thiết bị, mục tiêu "
            "đầu tư, hình thức QLDA, loại dự án, PCCC) để trống — cán bộ bổ sung từ hồ sơ thiết kế cơ sở.\n"
            "Bước đính kèm: mỗi loại giấy tờ vào 1 dòng (Tờ trình / ĐTM / chủ trương / đấu nối / nhà thầu / "
            "quy hoạch / khảo sát-thiết kế / GCN đầu tư)."
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
    "khai-sinh-da-co-ho-so": khai_sinh_co_ho_so_process,
    "ket-hon": ket_hon_process,
    "ket-hon-nuoc-ngoai": ket_hon_nuoc_ngoai_process,
    "dang-ky-lai-ket-hon": ket_hon_lai_process,
    "dang-ky-giam-ho": dang_ky_giam_ho_process,
    "dang-ky-nhan-cha-me-con": nhan_cha_me_con_process,
    "trich-luc-ks": trich_luc_process,
    "khai-tu": khai_tu_process,
    "khai-tu-lien-thong": khai_tu_process,  # TẠM: chưa có mapper riêng khớp DOM SPA liên thông
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
    "xoa-dang-ky-bien-phap-bao-dam-bac-ninh": xoa_dk_bpbd_bac_ninh_process,
    "dang-ky-bien-phap-bao-dam-bac-ninh": dang_ky_bpbd_bac_ninh_process,
    "ho-tro-nguoi-cao-tuoi-bac-ninh": ho_tro_nguoi_cao_tuoi_bac_ninh_process,
    "ho-tro-chi-phi-hoa-tang-bac-ninh": ho_tro_chi_phi_hoa_tang_bac_ninh_process,
    "ho-tro-chi-phi-hoa-tang": ho_tro_chi_phi_hoa_tang_process,
    "dang-ky-nha-o-xa-hoi-bac-ninh": dang_ky_nha_o_xa_hoi_bac_ninh_process,
    "cap-hoc-tap-bac-ninh": cap_hoc_tap_bac_ninh_process,
    "tach-hop-thua-dat-bac-ninh": tach_hop_thua_dat_bac_ninh_process,
    "cap-doi-gcn-bac-ninh": cap_doi_gcn_bac_ninh_process,
    "dinh-chinh-gcn-da-cap-bac-ninh": dinh_chinh_gcn_da_cap_bac_ninh_process,
    "dang-ky-lap-dat-su-dung-nuoc-sach": cap_nuoc_sach_process,
    "chuyen-doi-ten-hop-dong-nuoc-sach": doi_ten_nuoc_sach_process,
    "cap-giay-chung-nhan-co-so-du-dieu-kien-an-toan-thuc-pham": an_toan_thuc_pham_process,
    "cap-gcn-attp-nong-lam-thuy-san": cap_gcn_attp_nong_lam_thuy_san_process,
    "cap-lai-giay-chung-nhan-du-dieu-kien-an-toan-thuc-pham": cap_lai_an_toan_thuc_pham_process,
    "cap-gcn-attp-cong-thuong": cap_gcn_attp_ct_process,
    "cap-giay-phep-xay-dung-moi-nha-o-rieng-le": cap_giay_phep_xay_dung_process,
    "dieu-chinh-giay-phep-xay-dung": dieu_chinh_gpxd_process,
    "sua-chua-cai-tao-gpxd-nha-o-rieng-le": sua_chua_gpxd_nha_o_process,
    "sua-chua-cai-tao-gpxd-cong-trinh": sua_chua_gpxd_cong_trinh_process,
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
    "cap-lai-chung-chi-hanh-nghe-thu-y": cap_lai_cchn_thu_y_process,
    "cap-gcn-dang-ky-tau-ca": cap_gcn_dang_ky_tau_ca_process,
    "dang-ky-bien-phap-bao-dam-qsdd": dk_bien_phap_bao_dam_process,
    "xoa-dang-ky-phuong-tien-thuy": xoa_dk_phuong_tien_thuy_process,
    "dang-ky-bien-dong-dat-dai-da-nang": dk_bien_dong_dat_dai_dn_process,
    "chuyen-muc-dich-su-dung-dat-da-nang": chuyen_muc_dich_dat_dn_process,
    "cap-gcn-so-nha-da-nang": cap_gcn_so_nha_dn_process,
    "tach-hop-thua-dat-da-nang": tach_hop_thua_dat_dn_process,
    "giao-thue-chuyen-muc-dich-dat-da-nang": giao_thue_cmd_dat_dn_process,
    "dang-ky-dat-dai-lan-dau-da-nang": dk_dat_dai_lan_dau_dn_process,
    "cap-doi-gcn-da-nang": cap_doi_gcn_dn_process,
    "xoa-dang-ky-bien-phap-bao-dam-da-nang": xoa_bpbd_dn_process,
    "dinh-chinh-gcn-da-cap-da-nang": dinh_chinh_gcn_dn_process,
    "xac-nhan-ho-so-so-nha-da-nang": xn_ho_so_so_nha_dn_process,
    "cap-phep-long-duong-via-he": cap_phep_via_he_process,
    "cho-thue-thue-mua-nha-o-xa-hoi": cho_thue_noxh_process,
    "tham-dinh-bcnckt": tham_dinh_bcnckt_process,
    "cap-giay-phep-chat-ha-cay-xanh": cap_gp_chat_ha_cay_xanh_process,
    "cap-ban-sao-van-bang-so-goc": cap_ban_sao_van_bang_process,
    "chap-thuan-dau-noi-tam": chap_thuan_dau_noi_tam_process,
    "cap-giay-phep-lien-van-viet-lao": cap_giay_phep_lien_van_viet_lao_process,
    "xoa-dang-ky-tau-ca": xoa_dang_ky_tau_ca_process,
    "dang-ky-kinh-doanh": dang_ky_kinh_doanh_process,
    "thanh-lap-cong-ty-co-phan": thanh_lap_ctcp_process,
    "thanh-lap-cong-ty-tnhh-hai-thanh-vien": thanh_lap_tnhh2_process,
    "dang-ky-thay-doi-noi-dung-ho-kinh-doanh": dang_ky_thay_doi_kinh_doanh_process,
    "cham-dut-hoat-dong-ho-kinh-doanh": cham_dut_hoat_dong_ho_kinh_doanh_process,
    "tam-ngung-kinh-doanh": tam_ngung_kinh_doanh_process,
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
    "xoa-dang-ky-bien-phap-bao-dam-bac-ninh": xoa_dk_bpbd_bac_ninh_attach,
    "dang-ky-bien-phap-bao-dam-bac-ninh": dang_ky_bpbd_bac_ninh_attach,
    "ho-tro-nguoi-cao-tuoi-bac-ninh": ho_tro_nguoi_cao_tuoi_bac_ninh_attach,
    "ho-tro-chi-phi-hoa-tang-bac-ninh": ho_tro_chi_phi_hoa_tang_bac_ninh_attach,
    "ho-tro-chi-phi-hoa-tang": ho_tro_chi_phi_hoa_tang_attach,
    "dang-ky-nha-o-xa-hoi-bac-ninh": dang_ky_nha_o_xa_hoi_bac_ninh_attach,
    "cap-hoc-tap-bac-ninh": cap_hoc_tap_bac_ninh_attach,
    "tach-hop-thua-dat-bac-ninh": tach_hop_thua_dat_bac_ninh_attach,
    "cap-doi-gcn-bac-ninh": cap_doi_gcn_bac_ninh_attach,
    "dinh-chinh-gcn-da-cap-bac-ninh": dinh_chinh_gcn_da_cap_bac_ninh_attach,
    "dang-ky-kinh-doanh": dang_ky_kinh_doanh_attach,
    "thanh-lap-cong-ty-co-phan": thanh_lap_ctcp_attach,
    "thanh-lap-cong-ty-tnhh-hai-thanh-vien": thanh_lap_tnhh2_attach,
    "dang-ky-thay-doi-noi-dung-ho-kinh-doanh": dang_ky_thay_doi_kinh_doanh_attach,
    "cham-dut-hoat-dong-ho-kinh-doanh": cham_dut_hoat_dong_ho_kinh_doanh_attach,
    "tam-ngung-kinh-doanh": tam_ngung_kinh_doanh_attach,
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
    "mai-tang-dan-cong-hoa-tuyen": mai_tang_dan_cong_attach,
    "dieu-chinh-huu-tri-xa-hoi": dieu_chinh_huu_tri_xa_hoi_attach,
    "khai-sinh-dang-ky-thuong": khai_sinh_thuong_attach,
    "khai-sinh-ket-hop-nhan-cha-me-con": khai_sinh_ket_hop_nhan_cmc_attach,
    "khai-sinh-dang-ky": khai_sinh_lien_thong_attach,
    "khai-sinh-dang-ky-lai": khai_sinh_dang_ky_lai_attach,
    "khai-sinh-da-co-ho-so": khai_sinh_co_ho_so_attach,
    "ket-hon": ket_hon_attach,
    # Đính kèm RIÊNG: form nhiều ô cố định (y tế/TTHN nước ngoài/hộ chiếu/văn bản ngành/TTHN ĐSQ VN).
    "ket-hon-nuoc-ngoai": ket_hon_nuoc_ngoai_attach,
    "dang-ky-lai-ket-hon": ket_hon_lai_attach,
    "dang-ky-giam-ho": dang_ky_giam_ho_attach,
    "dang-ky-nhan-cha-me-con": nhan_cha_me_con_attach,
    "trich-luc-ks": trich_luc_attach,
    "khai-tu": khai_tu_attach,
    "khai-tu-lien-thong": khai_tu_attach,  # TẠM: chưa có attach plan riêng
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
    "cap-lai-chung-chi-hanh-nghe-thu-y": cap_lai_cchn_thu_y_attach,
    "cap-gcn-dang-ky-tau-ca": cap_gcn_dang_ky_tau_ca_attach,
    "dang-ky-bien-phap-bao-dam-qsdd": dk_bien_phap_bao_dam_attach,
    "xoa-dang-ky-phuong-tien-thuy": xoa_dk_phuong_tien_thuy_attach,
    "dang-ky-bien-dong-dat-dai-da-nang": dk_bien_dong_dat_dai_dn_attach,
    "chuyen-muc-dich-su-dung-dat-da-nang": chuyen_muc_dich_dat_dn_attach,
    "cap-gcn-so-nha-da-nang": cap_gcn_so_nha_dn_attach,
    "tach-hop-thua-dat-da-nang": tach_hop_thua_dat_dn_attach,
    "giao-thue-chuyen-muc-dich-dat-da-nang": giao_thue_cmd_dat_dn_attach,
    "dang-ky-dat-dai-lan-dau-da-nang": dk_dat_dai_lan_dau_dn_attach,
    "cap-doi-gcn-da-nang": cap_doi_gcn_dn_attach,
    "xoa-dang-ky-bien-phap-bao-dam-da-nang": xoa_bpbd_dn_attach,
    "dinh-chinh-gcn-da-cap-da-nang": dinh_chinh_gcn_dn_attach,
    "xac-nhan-ho-so-so-nha-da-nang": xn_ho_so_so_nha_dn_attach,
    "cap-phep-long-duong-via-he": cap_phep_via_he_attach,
    "cho-thue-thue-mua-nha-o-xa-hoi": cho_thue_noxh_attach,
    "tham-dinh-bcnckt": tham_dinh_bcnckt_attach,
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
    "cap-gcn-attp-cong-thuong": cap_gcn_attp_ct_attach,
    "cap-giay-phep-xay-dung-moi-nha-o-rieng-le": cap_giay_phep_xay_dung_attach,
    "dieu-chinh-giay-phep-xay-dung": dieu_chinh_gpxd_attach,
    "sua-chua-cai-tao-gpxd-nha-o-rieng-le": sua_chua_gpxd_attach,
    "sua-chua-cai-tao-gpxd-cong-trinh": sua_chua_gpxd_attach,
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
