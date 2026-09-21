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
from app.pipelines.chuyen_muc_dich_su_dung_dat_lam_dong.attach import plan as chuyen_muc_dich_su_dung_dat_lam_dong_attach
from app.pipelines.chuyen_muc_dich_su_dung_dat_lam_dong.process import run as chuyen_muc_dich_su_dung_dat_lam_dong_process
from app.pipelines.dang_ky_dien_tich_tang_them_lam_dong.attach import plan as dang_ky_dien_tich_tang_them_lam_dong_attach
from app.pipelines.dang_ky_dien_tich_tang_them_lam_dong.process import run as dang_ky_dien_tich_tang_them_lam_dong_process
from app.pipelines.dang_ky_kinh_doanh.attach import plan as dang_ky_kinh_doanh_attach
from app.pipelines.dang_ky_thay_doi_kinh_doanh.attach import plan as dang_ky_thay_doi_kinh_doanh_attach
from app.pipelines.cham_dut_hoat_dong_ho_kinh_doanh.attach import plan as cham_dut_hoat_dong_ho_kinh_doanh_attach
from app.pipelines.tam_ngung_kinh_doanh.attach import plan as tam_ngung_kinh_doanh_attach
from app.pipelines.cap_lai_cap_doi_gcn_ho_kinh_doanh.attach import plan as cap_lai_cap_doi_gcn_ho_kinh_doanh_attach
from app.pipelines.cap_nuoc_sach.attach import plan as cap_nuoc_sach_attach
from app.pipelines.chung_thuc_ban_sao.attach import plan as chung_thuc_ban_sao_attach
from app.pipelines.chung_thuc_chu_ky.attach import plan as chung_thuc_chu_ky_attach
from app.pipelines.chung_thuc_chu_ky_nguoi_dich_ctv.attach import (
    plan as chung_thuc_chu_ky_nguoi_dich_ctv_attach,
)
from app.pipelines.chung_thuc_di_chuc.attach import plan as chung_thuc_di_chuc_attach
from app.pipelines.chung_thuc_giao_dich_tai_san.attach import plan as chung_thuc_giao_dich_tai_san_attach
from app.pipelines.chung_thuc_phan_chia_di_san.attach import plan as chung_thuc_phan_chia_di_san_attach
from app.pipelines.chung_thuc_sua_doi_giao_dich.attach import plan as chung_thuc_sua_doi_giao_dich_attach
from app.pipelines.chung_thuc_tu_choi_di_san.attach import plan as chung_thuc_tu_choi_di_san_attach
from app.pipelines.cap_nuoc_sach.process import run as cap_nuoc_sach_process
from app.pipelines.dang_ky_dat_dai.process import run as dang_ky_dat_dai_process
from app.pipelines.dang_ky_dat_dai_tai_san.process import run as dang_ky_dat_dai_tai_san_process
from app.pipelines.dang_ky_dat_dai_tai_san.attach import plan as dang_ky_dat_dai_tai_san_attach
from app.pipelines.cap_GCN_nhan_chuyen_nhuong.attach import plan as cap_gcn_nhan_chuyen_nhuong_attach
from app.pipelines.cap_GCN_nhan_chuyen_nhuong.process import run as cap_gcn_nhan_chuyen_nhuong_process
from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.attach import plan as chuyen_doi_md_sd_dat_lao_cai_attach
from app.pipelines.chuyen_doi_md_sd_dat_lao_cai.process import run as chuyen_doi_md_sd_dat_lao_cai_process
from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.attach import (
    plan as chuyen_md_sd_dat_phuong_xa_lao_cai_attach,
)
from app.pipelines.chuyen_md_sd_dat_phuong_xa_lao_cai.process import (
    run as chuyen_md_sd_dat_phuong_xa_lao_cai_process,
)
from app.pipelines.dang_ky_bien_dong_lao_cai.attach import plan as dang_ky_bien_dong_lao_cai_attach
from app.pipelines.dang_ky_bien_dong_lao_cai.process import run as dang_ky_bien_dong_lao_cai_process
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.attach import plan as dang_ky_quyen_su_dung_dat_lao_cai_attach
from app.pipelines.dang_ky_quyen_su_dung_dat_lao_cai.process import run as dang_ky_quyen_su_dung_dat_lao_cai_process
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
from app.pipelines.giao_thue_chuyen_muc_dich_dat_quang_ngai.process import run as giao_thue_chuyen_muc_dich_dat_quang_ngai_process
from app.pipelines.giao_thue_chuyen_muc_dich_dat_quang_ngai.attach import plan as giao_thue_chuyen_muc_dich_dat_quang_ngai_attach
from app.pipelines.dang_ky_dat_dai_lan_dau_quang_ngai.process import run as dang_ky_dat_dai_lan_dau_quang_ngai_process
from app.pipelines.dang_ky_dat_dai_lan_dau_quang_ngai.attach import plan as dang_ky_dat_dai_lan_dau_quang_ngai_attach
from app.pipelines.xac_dinh_lai_dien_tich_dat_o_quang_ngai.process import run as xac_dinh_lai_dien_tich_dat_o_quang_ngai_process
from app.pipelines.xac_dinh_lai_dien_tich_dat_o_quang_ngai.attach import plan as xac_dinh_lai_dien_tich_dat_o_quang_ngai_attach
from app.pipelines.dinh_chinh_sai_sot_quang_ngai.process import run as dinh_chinh_sai_sot_quang_ngai_process
from app.pipelines.dinh_chinh_sai_sot_quang_ngai.attach import plan as dinh_chinh_sai_sot_quang_ngai_attach
from app.pipelines.dinh_chinh_gcn_da_cap_ninh_binh.process import run as dinh_chinh_gcn_da_cap_ninh_binh_process
from app.pipelines.dinh_chinh_gcn_da_cap_ninh_binh.attach import plan as dinh_chinh_gcn_da_cap_ninh_binh_attach
from app.pipelines.dinh_chinh_da_cap_ninh_binh.process import run as dinh_chinh_da_cap_ninh_binh_process
from app.pipelines.dinh_chinh_da_cap_ninh_binh.attach import plan as dinh_chinh_da_cap_ninh_binh_attach
from app.pipelines.dang_ky_dat_dai_lan_dau_ninh_binh.process import run as dang_ky_dat_dai_lan_dau_ninh_binh_process
from app.pipelines.dang_ky_dat_dai_lan_dau_ninh_binh.attach import plan as dang_ky_dat_dai_lan_dau_ninh_binh_attach
from app.pipelines.cap_doi_gcn_ninh_binh.process import run as cap_doi_gcn_ninh_binh_process
from app.pipelines.cap_doi_gcn_ninh_binh.attach import plan as cap_doi_gcn_ninh_binh_attach
from app.pipelines.dang_ky_bien_dong_dat_dai_ninh_binh.process import run as dang_ky_bien_dong_dat_dai_ninh_binh_process
from app.pipelines.dang_ky_bien_dong_dat_dai_ninh_binh.attach import plan as dang_ky_bien_dong_dat_dai_ninh_binh_attach
from app.pipelines.dang_ky_dat_dai_lan_dau_quang_ninh_mien_nui_hai_dao.attach import plan as dang_ky_dat_dai_lan_dau_quang_ninh_mien_nui_hai_dao_attach
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_quang_ninh_mien_nui_hai_dao.attach import plan as dang_ky_bien_dong_chuyen_nhuong_quang_ninh_mien_nui_hai_dao_attach
from app.pipelines.chuyen_muc_dich_su_dung_dat_quang_ninh_mien_nui_hai_dao.attach import plan as chuyen_muc_dich_su_dung_dat_quang_ninh_mien_nui_hai_dao_attach
from app.pipelines.cap_doi_gcn_quang_ninh_mien_nui_hai_dao.attach import plan as cap_doi_gcn_quang_ninh_mien_nui_hai_dao_attach
from app.pipelines.cap_doi_gcn_do_do_dac_khong_nvtc_quang_ninh_mien_nui_hai_dao.attach import plan as cap_doi_gcn_do_do_dac_khong_nvtc_quang_ninh_mien_nui_hai_dao_attach
from app.pipelines.tach_hop_thua_dat_quang_ninh_mien_nui_hai_dao.attach import plan as tach_hop_thua_dat_quang_ninh_mien_nui_hai_dao_attach
from app.pipelines.dang_ky_tai_san_dat_quang_ninh_mien_nui_hai_dao.attach import plan as dang_ky_tai_san_dat_quang_ninh_mien_nui_hai_dao_attach
from app.pipelines.dang_ky_bien_dong_doi_ten_quang_ninh_mien_nui_hai_dao.attach import plan as dang_ky_bien_dong_doi_ten_quang_ninh_mien_nui_hai_dao_attach
from app.pipelines.dang_ky_bien_phap_bao_dam_quang_ninh.attach import plan as dang_ky_bien_phap_bao_dam_quang_ninh_attach
from app.pipelines.dieu_chinh_giao_dat_lao_cai.attach import plan as dieu_chinh_giao_dat_lao_cai_attach
from app.pipelines.dieu_chinh_giao_dat_lao_cai.process import run as dieu_chinh_giao_dat_lao_cai_process
from app.pipelines.giao_thue_dat_lao_cai.attach import plan as giao_thue_dat_lao_cai_attach
from app.pipelines.giao_thue_dat_lao_cai.process import run as giao_thue_dat_lao_cai_process
from app.pipelines.dk_giay_cn_thua_dat_dien_tich_tang_them.process import (
    run as dk_giay_cn_thua_dat_dien_tich_tang_them_process,
)
from app.pipelines.dk_giay_cn_thua_dat_dien_tich_tang_them.attach import (
    plan as dk_giay_cn_thua_dat_dien_tich_tang_them_attach,
)
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.process import (
    run as xac_nhan_tiep_tuc_dat_nong_nghiep_process,
)
from app.pipelines.xac_nhan_tiep_tuc_dat_nong_nghiep.attach import (
    plan as xac_nhan_tiep_tuc_dat_nong_nghiep_attach,
)
from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_quang_ninh.attach import plan as xoa_dang_ky_bien_phap_bao_dam_quang_ninh_attach
from app.pipelines.dang_ky_dat_dai_lan_dau_bac_ninh.process import run as dang_ky_dat_dai_lan_dau_bac_ninh_process
from app.pipelines.dang_ky_dat_dai_lan_dau_bac_ninh.attach import plan as dang_ky_dat_dai_lan_dau_bac_ninh_attach
from app.pipelines.dk_dat_dai_gan_tai_san_lao_cai.attach import (
    plan as dk_dat_dai_gan_tai_san_lao_cai_attach,
)
from app.pipelines.dk_dat_dai_gan_tai_san_lao_cai.process import (
    run as dk_dat_dai_gan_tai_san_lao_cai_process,
)
from app.pipelines.thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai.attach import (
    plan as thu_hoi_gcn_cap_lan_dau_lao_cai_attach,
)
from app.pipelines.thu_hoi_gcn_cap_lan_dau_khong_dung_quy_dinh_cap_lai.process import (
    run as thu_hoi_gcn_cap_lan_dau_lao_cai_process,
)
from app.pipelines.thu_hoi_gcn_cap_sai_bac_ninh.process import run as thu_hoi_gcn_cap_sai_bac_ninh_process
from app.pipelines.thu_hoi_gcn_cap_sai_bac_ninh.attach import plan as thu_hoi_gcn_cap_sai_bac_ninh_attach
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_bac_ninh.process import run as dang_ky_bien_dong_chuyen_nhuong_bac_ninh_process
from app.pipelines.dang_ky_bien_dong_chuyen_nhuong_bac_ninh.attach import plan as dang_ky_bien_dong_chuyen_nhuong_bac_ninh_attach
from app.pipelines.dang_ky_bien_dong_dat_dai_bac_ninh.process import run as dang_ky_bien_dong_dat_dai_bac_ninh_process
from app.pipelines.dang_ky_bien_dong_dat_dai_bac_ninh.attach import plan as dang_ky_bien_dong_dat_dai_bac_ninh_attach
from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_bac_ninh.process import run as xoa_dk_bpbd_bac_ninh_process
from app.pipelines.xoa_dang_ky_bien_phap_bao_dam_bac_ninh.attach import plan as xoa_dk_bpbd_bac_ninh_attach
from app.pipelines.dien_thong_tin_tai_khoan_bac_ninh.process import run as dien_tk_bac_ninh_process
from app.pipelines.dang_ky_bien_phap_bao_dam_bac_ninh.process import run as dang_ky_bpbd_bac_ninh_process
from app.pipelines.dang_ky_bien_phap_bao_dam_bac_ninh.attach import plan as dang_ky_bpbd_bac_ninh_attach
from app.pipelines.ho_tro_nguoi_cao_tuoi_bac_ninh.attach import plan as ho_tro_nguoi_cao_tuoi_bac_ninh_attach
from app.pipelines.ho_tro_nguoi_cao_tuoi_bac_ninh.process import run as ho_tro_nguoi_cao_tuoi_bac_ninh_process
from app.pipelines.ho_tro_chi_phi_hoa_tang_bac_ninh.attach import plan as ho_tro_chi_phi_hoa_tang_bac_ninh_attach
from app.pipelines.ho_tro_chi_phi_hoa_tang_bac_ninh.process import run as ho_tro_chi_phi_hoa_tang_bac_ninh_process
from app.pipelines.ho_tro_chi_phi_hoa_tang_quang_ngai.attach import plan as ho_tro_chi_phi_hoa_tang_quang_ngai_attach
from app.pipelines.ho_tro_chi_phi_hoa_tang_quang_ngai.process import run as ho_tro_chi_phi_hoa_tang_quang_ngai_process
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
from app.pipelines.khai_tu_lien_thong.attach import plan as khai_tu_lien_thong_attach
from app.pipelines.khai_tu_lien_thong.process import run as khai_tu_lien_thong_process
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
from app.pipelines.thi_tuyen_cong_chuc_mot_cua_moha.attach import (
    plan as thi_tuyen_cong_chuc_mot_cua_moha_attach,
)
from app.pipelines.thi_tuyen_cong_chuc_mot_cua_moha.process import (
    run as thi_tuyen_cong_chuc_mot_cua_moha_process,
)
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
from app.pipelines.cap_gcnkncm_cccm.attach import plan as cap_gcnkncm_cccm_attach
from app.pipelines.cap_gcnkncm_cccm.process import run as cap_gcnkncm_cccm_process
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
from app.pipelines.cong_bo_du_dk_tiem_chung.attach import plan as cong_bo_du_dk_tiem_chung_attach
from app.pipelines.cong_bo_du_dk_tiem_chung.process import run as cong_bo_du_dk_tiem_chung_process

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
        # Như nhóm chứng thực còn lại: đi thẳng vào luồng đính kèm, không mở màn xin consent.
        # Văn bản consent của Auto Fill nói về việc "đọc, xử lý và tự động điền dữ liệu vào biểu
        # mẫu" — thủ tục mode=attach không điền ô nào nên câu đó không đúng việc đang làm.
        "skipConsent": True,
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
            "CCCD người được hưởng di sản, giấy ủy quyền đi nộp hồ sơ.\n"
            "3. Dự thảo/văn bản thỏa thuận phân chia di sản thừa kế.\n"
            "Đính kèm theo Cài đặt 'Không gộp giấy tờ': MẶC ĐỊNH (tắt) = gộp nhóm 1-2 vào cùng PDF dòng STT 1, "
            "dự thảo upload dòng STT 2, không thêm dòng mới. BẬT = mỗi giấy tờ 1 dòng: giấy đầu tiên vào STT 1, "
            "các giấy sau thêm thành phần hồ sơ mới; dự thảo vẫn ở dòng riêng STT 2."
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
            "Bước 3: đính giấy chứng sinh vào ô STT1; các giấy tờ khác (CCCD cha/mẹ, giấy kết hôn) "
            "được GỘP CHUNG vào cùng ô STT1 với giấy chứng sinh; tờ khai thay đổi cư trú (CT01) vào "
            "ô STT2 nếu có."
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
        # Form Angular (app-input formcontrolname) như liên thông khai sinh. Trích xuất dùng chung agent
        # "khai-tu" (cùng bộ giấy tờ), mapper riêng khớp DOM liên thông. Phạm vi theo mapping BA
        # "126_Liên thông khai tử": điền người được khai tử, nơi cư trú cuối cùng, thời gian/nơi chết,
        # giấy báo tử, bản sao. Người yêu cầu do cổng đổ từ VNeID; chủ hộ và mai táng phí để cán bộ
        # chọn (nhánh "Hưởng theo luật BHXH" BA đã bỏ ngày 2026-09-14).
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Tờ khai đăng ký khai tử (bản giấy nếu có).\n"
            "2. Giấy báo tử hoặc giấy tờ thay thế Giấy báo tử.\n"
            "3. CCCD của người yêu cầu và người được khai tử nếu có (chỉ để đọc thông tin, không đính kèm).\n"
            "Người yêu cầu do cổng điền sẵn từ VNeID; thông tin chủ hộ và mai táng phí cán bộ tự chọn.\n"
            "Bước đính kèm: giấy báo tử và tờ khai vào dòng 1; chứng cứ thay thế giấy báo tử "
            "(người chết đã lâu) vào dòng 2."
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
        # maThuTucHanhChinh là duy nhất → nhận diện chắc chắn theo URL.
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
        # dùng urlIncludes được. Detect theo VĂN BẢN: tiêu đề + MÃ THỦ TỤC "1.115446.H36" (H36 = mã tỉnh
        # Lâm Đồng, giống mọi phường). Mã H36 KHÔNG có ở trang Lai Châu (tiêu đề trùng) → tách được 2 tỉnh;
        # tổng cụm dài hơn rule Lai Châu ("đính chính"+"sai sót") nên thắng điểm trên trang Lâm Đồng.
        # urlScope = cổng gate: chỉ tin text khi URL đúng cổng Lâm Đồng (URL chỉ có ObjectId theo
        # phường, không định danh thủ tục) → tránh dương tính giả nếu trang khác trùng cụm text.
        "detect": {"urlScope": ["lamdong.gov.vn"], "textIncludes": [
            "đính chính giấy chứng nhận đã cấp lần đầu có sai sót",
            # Mã đổi 1.012796 -> 1.115446 (thông báo 1283/TB-SNNMT ngày 04/8/2026), giống Bắc Ninh ở trên.
            "1.115446.H36",
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
        # MÃ QUY TRÌNH in trên trang. Phần IV GCN "không cần điền".
        # Mã đã đổi 1.013978.H36 -> 1.116360 (trang in "Quy trình: 1.116360 - Phường/Xã"). Cổng chỉ còn
        # phát mã mới nên chỉ bắt mã mới, giống bản Bắc Ninh.
        # urlScope = cổng gate Lâm Đồng (xem thủ tục đính chính lamdong ở trên): URL chỉ có ObjectId
        # theo phường nên cần chắc đúng cổng trước khi tin cụm text + mã.
        "detect": {"urlScope": ["lamdong.gov.vn"], "textIncludes": [
            "đăng ký đất đai, tài sản gắn liền với đất, cấp giấy chứng nhận",
            "1.116360",
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
            "5. Văn bản xác nhận tài sản riêng/chung của vợ chồng, văn bản xác định thành viên có chung "
            "quyền sử dụng đất của hộ (nếu có).\n"
            "6. Biên lai thu thuế/phí (chứng từ nghĩa vụ tài chính) nếu có.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Điền đơn (Form.io): Phần I Người nộp, Phần II Thửa đất, Phần III Chủ hồ sơ. Phần IV 'Thông tin "
            "chi tiết' (GCN) KHÔNG cần điền (đăng ký lần đầu). Nếu nộp thay qua ủy quyền: Phần I là người "
            "đại diện, Phần III là chủ hộ.\n"
            "Đính kèm (bảng 20 dòng theo QĐ 40/2026/QĐ-UBND, KHÔNG gộp PDF — nhiều file vào chung 1 ô): "
            "Đơn Mẫu 15 + CCCD + tài liệu chưa rõ loại → STT 19 'Đơn đăng ký đất đai, tài sản gắn liền "
            "với đất, Mẫu số 15'; Giấy ủy quyền → STT 18 'Văn bản về việc đại diện... thông qua người "
            "đại diện'; văn bản xác nhận tài sản riêng/thành viên chung quyền → "
            "STT 8; mảnh trích đo + trích lục + mô tả ranh giới → STT 14 'Mảnh trích đo bản đồ địa chính "
            "thửa đất'; biên lai → STT 16 'Chứng từ nghĩa vụ tài chính'; giấy tờ nguồn gốc → STT 1 'Một "
            "trong các loại giấy tờ (Điều 137, khoản 1...)'.\n"
            "Tỉnh/Phường (3 khối địa chỉ) là select cascade — extension tự chọn."
        ),
    },
    {
        "key": "chuyen-muc-dich-su-dung-dat-lam-dong",
        # Cổng dichvucong.lamdong.gov.vn (Form.io apply) — CÙNG form/nền tảng 2 thủ tục Lâm Đồng ở trên,
        # có THÊM ô "Cơ quan/ tổ chức" (data[organization]). URL /vi/padsvc/apply chỉ mang ObjectId theo
        # phường → KHÔNG dùng urlIncludes. Detect theo VĂN BẢN: tiêu đề + MÃ THỦ TỤC "1.116365".
        # ⚠ Mã này hiển thị KHÔNG có hậu tố ".H36" (khác 1.115446.H36 / 1.013978.H36 của 2 thủ tục trên)
        # nên là mã QUỐC GIA có thể dùng chung nhiều cổng → urlScope Lâm Đồng là bắt buộc để khỏi cướp
        # trang cùng mã ở tỉnh khác. Cả 2 cụm nằm trong ~600 ký tự đầu của innerText (extension cắt 6.000).
        "detect": {"urlScope": ["lamdong.gov.vn"], "textIncludes": [
            "chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất",
            "1.116365",
        ]},
        "label": (
            "[Tỉnh Lâm Đồng] Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia hạn sử dụng "
            "đất khi hết thời hạn sử dụng đất; điều chỉnh thời hạn sử dụng đất của dự án đầu tư"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị — một trong 4 mẫu Phụ lục VI (QĐ 40/2026/QĐ-UBND): Mẫu 02 chuyển mục đích · "
            "Mẫu 03 chuyển hình thức · Mẫu 4a gia hạn · Mẫu 4b điều chỉnh thời hạn dự án đầu tư.\n"
            "2. Giấy chứng nhận QSDĐ đã cấp (dùng cho cả Phần IV 'Thông tin chi tiết').\n"
            "3. Bản trích lục bản đồ địa chính hoặc trích đo bản đồ địa chính.\n"
            "4. CCCD của chủ hồ sơ (và của người nộp thay); nếu nộp thay: Giấy ủy quyền.\n"
            "5. Nếu có: tờ khai lệ phí trước bạ, tờ khai thuế SDĐ phi nông nghiệp, văn bản về thời hạn dự "
            "án đầu tư, quyết định giao/thuê/chuyển mục đích đất, giấy tờ miễn giảm tiền sử dụng đất.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Điền đơn (Form.io): Phần I Người nộp, Phần II Thửa đất, Phần III Chủ hồ sơ, Phần IV Chi tiết "
            "GCN (số phát hành, ngày cấp, đơn vị cấp, nơi cấp); nội dung đề nghị vào ô Ghi chú. Ô 'Cơ "
            "quan/ tổ chức' chỉ điền khi hồ sơ đứng tên PHÁP NHÂN, hồ sơ cá nhân/hộ gia đình để trống.\n"
            "Tự nộp: extension điền Phần I rồi BẤM nút 'Người nộp là chủ hồ sơ' để form tự chép xuống "
            "Phần III. Nộp thay theo ủy quyền: điền lần lượt cả hai khối, KHÔNG bấm nút đó.\n"
            "Đính kèm (3 mục): Đơn + Giấy ủy quyền + CCCD đính vào CÙNG MỘT DÒNG của đúng mẫu đơn — vẫn "
            "là các TỆP RIÊNG, không gộp PDF; Trích lục bản đồ → dòng 'Bản trích lục bản đồ địa chính'; "
            "Giấy chứng nhận → dòng 'khoản 21 Điều 3... hoặc Điều 137 Luật Đất đai'.\n"
            "Tỉnh/Phường (3 khối địa chỉ) là select cascade Choices.js — extension tự chọn theo tên MỚI."
        ),
    },
    {
        "key": "dang-ky-dien-tich-tang-them-lam-dong",
        # Cổng dichvucong.lamdong.gov.vn (Form.io apply-online) — form kê khai GIỐNG HỆT thủ tục
        # 1.116365 ở trên (đã đối chiếu đủ 35 ô data[...]: trùng tên/tag/nhãn/cờ bắt buộc); chỉ khác
        # bảng thành phần hồ sơ (6 dòng thay vì 24). URL chỉ mang ObjectId theo phường → detect theo
        # VĂN BẢN: cụm tiêu đề đặc trưng + MÃ THỦ TỤC "1.116356" (không có hậu tố .H36 → là mã QUỐC
        # GIA, nên urlScope Lâm Đồng là thứ duy nhất chống cướp trang ở tỉnh khác cùng mã).
        # Đã kiểm: cả 2 cụm nằm trong ~850 ký tự đầu innerText (extension cắt 6.000), và KHÔNG entry
        # Lâm Đồng nào đang có khớp được trang này.
        "detect": {"urlScope": ["lamdong.gov.vn"], "textIncludes": [
            "diện tích tăng thêm do thay đổi ranh giới so với giấy chứng nhận đã cấp",
            "1.116356",
        ]},
        "label": (
            "[Tỉnh Lâm Đồng] Đăng ký, cấp Giấy chứng nhận đối với thửa đất có diện tích tăng thêm do "
            "thay đổi ranh giới so với Giấy chứng nhận đã cấp; đăng ký, cấp Giấy chứng nhận quyền sử "
            "dụng đất, quyền sở hữu tài sản gắn liền với đất đối với toàn bộ diện tích đất đang sử dụng"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 18 Phụ lục VI) — dùng để "
            "điền thân đơn; nội dung biến động sẽ được ghi vào ô Ghi chú.\n"
            "2. Giấy chứng nhận QSDĐ đã cấp (dùng cho cả Phần IV 'Thông tin chi tiết').\n"
            "3. Giấy tờ chứng minh phần diện tích tăng thêm: bản mô tả ranh giới - mốc giới thửa đất "
            "(Phụ lục 12), công văn công khai ranh giới, văn bản xác nhận không có tranh chấp.\n"
            "4. Mảnh trích đo / mảnh đo đạc chỉnh lý bản đồ địa chính thửa đất.\n"
            "5. CCCD của người sử dụng đất; nếu nộp thay: văn bản ủy quyền/đại diện. Nếu có: tờ khai thuế.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Điền đơn (Form.io): Phần I Người nộp, Phần II Thửa đất, Phần III Chủ hồ sơ, Phần IV Chi tiết "
            "GCN đã cấp. Ô 'Cơ quan/ tổ chức' chỉ điền khi hồ sơ đứng tên PHÁP NHÂN.\n"
            "Tự nộp: extension điền Phần I rồi BẤM nút 'Người nộp là chủ hồ sơ' để form tự chép xuống "
            "Phần III. Nộp thay theo ủy quyền: điền lần lượt cả hai khối, KHÔNG bấm nút đó.\n"
            "Đính kèm: MỖI TỆP chỉ vào ĐÚNG MỘT dòng theo loại giấy tờ chính của tệp; CCCD đính chung "
            "dòng Đơn Mẫu 18. Nếu một tệp quét gộp cả mảnh đo đạc lẫn bản mô tả ranh giới thì tệp đó chỉ "
            "vào một dòng và hệ thống cảnh báo dòng còn lại đang trống — nên TÁCH thành hai tệp.\n"
            "Tỉnh/Phường (3 khối địa chỉ) là select cascade Choices.js — extension tự chọn theo tên MỚI."
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
        "key": "giao-thue-chuyen-muc-dich-dat-quang-ngai",
        # SPA Angular: URL /vi/padsvc/apply-online/<ObjectId> chỉ mang ObjectId theo cơ quan, KHÔNG có
        # mã thủ tục ổn định -> không dùng urlIncludes. Khóa host quangngai rồi khớp cụm tên thủ tục.
        # urlScope là thứ ngăn va chạm với bản Ninh Bình/Đà Nẵng cùng họ (tên thủ tục gần như y hệt).
        "detect": {
            "urlScope": ["dichvucong.quangngai.gov.vn"],
            "textIncludes": [
                "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất đối với trường hợp giao đất, "
                "cho thuê đất không đấu giá"
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Quảng Ngãi] Giao đất, cho thuê đất, chuyển mục đích sử dụng đất đối với trường hợp "
            "giao đất, cho thuê đất không đấu giá quyền sử dụng đất, không đấu thầu lựa chọn nhà đầu tư "
            "thực hiện dự án có sử dụng đất; trường hợp giao đất, cho thuê đất thông qua đấu thầu lựa "
            "chọn nhà đầu tư thực hiện dự án có sử dụng đất; giao đất và giao rừng; cho thuê đất và cho "
            "thuê rừng, gia hạn sử dụng đất khi hết thời hạn sử dụng đất"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đề nghị giao đất/thuê đất/chuyển mục đích sử dụng đất (Mẫu số 01) hoặc Đơn đề nghị "
            "gia hạn sử dụng đất đã kê khai — dùng để điền thân đơn.\n"
            "2. Giấy chứng nhận quyền sử dụng đất/quyết định giao, cho thuê, cho phép chuyển mục đích.\n"
            "3. CCCD của người sử dụng đất và người đồng sử dụng đất (nếu Giấy chứng nhận ghi 2 người).\n"
            "4. Nếu nộp thay: văn bản ủy quyền và CCCD của đúng người nộp.\n"
            "5. Nếu có: đơn đề nghị thẩm định nhu cầu, tờ khai thuế/lệ phí trước bạ, phương án sử dụng "
            "tầng đất mặt (Mẫu số 26), phương án sử dụng đất, giấy tờ dự án đầu tư/đấu giá thuê rừng.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Đính kèm: bảng có sẵn 15 dòng; Giấy chứng nhận được đính vào CẢ dòng 11 và dòng 13. Giấy tờ "
            "không có dòng riêng (CCCD, ủy quyền, tờ khai thuế…) đính chung tại dòng Đơn đề nghị (dòng "
            "14). Ô Bản chính/Bản sao do cán bộ tự chọn.\n"
        ),
    },
    {
        "key": "dang-ky-dat-dai-lan-dau-quang-ngai",
        # Cùng cổng dichvucong.quangngai.gov.vn với thủ tục giao/thuê/chuyển mục đích đất ở trên: SPA
        # Angular, URL /vi/padsvc/apply-online/<ObjectId> chỉ mang ObjectId theo cơ quan -> KHÔNG dùng
        # urlIncludes. TÊN THỦ TỤC TRÙNG KHÍT với bản Ninh Bình (dang-ky-dat-dai-lan-dau-ninh-binh) nên
        # urlScope là thứ DUY NHẤT chống tráo giữa hai tỉnh; cụm text bên dưới chỉ dùng để tách khỏi 2
        # thủ tục Quảng Ngãi còn lại (đã pre-check: cụm này không xuất hiện trên trang giao đất/hỏa táng).
        "detect": {
            "urlScope": ["dichvucong.quangngai.gov.vn"],
            "textIncludes": [
                "Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, "
                "quyền sở hữu tài sản gắn liền với đất lần đầu"
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Quảng Ngãi] Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử "
            "dụng đất, quyền sở hữu tài sản gắn liền với đất lần đầu đối với hộ gia đình, cá nhân, cộng "
            "đồng dân cư, người gốc Việt Nam định cư ở nước ngoài"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15) đã kê khai — dùng để điền "
            "thân đơn và địa chỉ thửa đất.\n"
            "2. Mảnh trích đo/phiếu xác nhận kết quả đo đạc hiện trạng thửa đất, bản mô tả ranh giới.\n"
            "3. Giấy tờ về quyền sử dụng đất theo Điều 137 hoặc giấy tờ nhận thừa kế/chuyển quyền "
            "chưa sang tên.\n"
            "4. CCCD của người sử dụng đất và người đồng sử dụng đất; giấy xác nhận số định danh cá "
            "nhân nếu giấy tờ cũ ghi số CMND 9 số.\n"
            "5. Tờ khai thuế/lệ phí trước bạ, chứng từ thực hiện nghĩa vụ tài chính (nếu có).\n"
            "6. Trường hợp nhiều người chung quyền: văn bản thỏa thuận cấp chung một Giấy chứng nhận "
            "hoặc văn bản xác định thành viên hộ gia đình có chung quyền sử dụng đất.\n"
            "7. Nếu nộp thay: văn bản về việc đại diện/ủy quyền và CCCD của đúng người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Đính kèm: bảng có sẵn 20 dòng, trong đó dòng 17/18/19 TRÙNG nội dung dòng 3/4/16 nên chỉ "
            "đính vào dòng chính; dòng 20 (Thông báo xác nhận kết quả) do cơ quan phát hành sau, không "
            "đính. CCCD và giấy xác nhận số định danh đính chung tại dòng 1 (Đơn đăng ký); tờ khai "
            "thuế/lệ phí trước bạ đính tại dòng 13 (Chứng từ nghĩa vụ tài chính). Ô Bản chính/Bản sao "
            "do cán bộ tự chọn.\n"
        ),
    },
    {
        "key": "ho-tro-chi-phi-hoa-tang-quang-ngai",
        # Cùng cổng dichvucong.quangngai.gov.vn với thủ tục đất đai ở trên: SPA Angular, URL
        # /vi/padsvc/apply-online/<ObjectId> chỉ mang ObjectId theo cơ quan -> KHÔNG dùng urlIncludes.
        # Khóa host rồi khớp cụm tên thủ tục; cụm này không xuất hiện trên trang giao đất nên hai
        # entry cùng host không cướp trang của nhau.
        "detect": {
            "urlScope": ["dichvucong.quangngai.gov.vn"],
            "textIncludes": ["Hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Quảng Ngãi] Hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Tờ khai đề nghị hỗ trợ chi phí khuyến khích sử dụng hình thức hỏa táng — Mẫu số 01 "
            "(cá nhân) hoặc Mẫu số 02 (cơ quan, tổ chức) đã kê khai, ký tên.\n"
            "2. Hợp đồng dịch vụ hỏa táng VÀ hóa đơn tài chính của cơ sở hỏa táng — phải có ĐỦ cả "
            "hai chứng từ.\n"
            "3. Trích lục khai tử/Giấy báo tử của người được hỏa táng.\n"
            "4. CCCD của người đứng tờ khai (và của người nộp thay nếu có).\n"
            "5. Nếu nộp thay: văn bản ủy quyền của cá nhân đã được chứng thực hoặc giấy giới thiệu "
            "của cơ quan, tổ chức.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Đính kèm: bảng có sẵn 4 dòng. Hợp đồng và hóa đơn đính CHUNG một dòng; hồ sơ cá nhân chỉ "
            "dùng dòng Mẫu số 01, hồ sơ cơ quan/tổ chức chỉ dùng dòng Mẫu số 02. Trích lục khai tử, "
            "CCCD và giấy tờ không có dòng riêng được đính chung tại dòng Tờ khai đề nghị — cán bộ có "
            "thể tách sang dòng '+ Thêm giấy tờ' nếu cổng yêu cầu. Ô Bản chính/Bản sao do cán bộ tự "
            "chọn.\n"
        ),
    },
    {
        "key": "xac-dinh-lai-dien-tich-dat-o-quang-ngai",
        # Cùng cổng dichvucong.quangngai.gov.vn với 3 thủ tục Quảng Ngãi ở trên: SPA Angular, URL
        # /vi/padsvc/apply-online/<ObjectId> chỉ mang ObjectId theo cơ quan -> KHÔNG dùng urlIncludes.
        # Khóa host rồi khớp cụm tên thủ tục. Đã pre-check ma trận detect trên cả 8 snapshot Quảng
        # Ngãi (4 thủ tục x 2 bước): mỗi trang chỉ khớp ĐÚNG một entry, không entry nào cướp trang.
        "detect": {
            "urlScope": ["dichvucong.quangngai.gov.vn"],
            "textIncludes": [
                "Xác định lại diện tích đất ở của hộ gia đình, cá nhân đã được cấp Giấy chứng nhận "
                "trước ngày 01 tháng 7 năm 2004"
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Quảng Ngãi] Xác định lại diện tích đất ở của hộ gia đình, cá nhân đã được cấp "
            "Giấy chứng nhận trước ngày 01 tháng 7 năm 2004"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 11/ĐK đã kê "
            "khai — dùng để điền thân đơn và nội dung yêu cầu giải quyết. Hồ sơ đang dùng mẫu đơn "
            "biến động cũ (Mẫu số 18) vẫn đọc được, nhưng cổng yêu cầu Mẫu số 11/ĐK nên nên viết "
            "lại theo đúng mẫu trước khi nộp.\n"
            "2. Giấy chứng nhận quyền sử dụng đất ĐÃ CẤP (cấp trước ngày 01/7/2004) — chụp/scan cả "
            "bìa và trang 'Những thay đổi sau khi cấp Giấy chứng nhận'.\n"
            "3. CCCD của người sử dụng đất; giấy xác nhận số định danh cá nhân nếu giấy tờ cũ ghi "
            "số CMND 9 số.\n"
            "4. Nếu nộp thay: văn bản về việc đại diện/ủy quyền và CCCD của đúng người nộp.\n"
            "5. Nếu có: giấy xác nhận thông tin về cư trú, văn bản trả lời của cơ quan đăng ký đất "
            "đai về dữ liệu thửa đất, tờ khai thuế/lệ phí trước bạ.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Đính kèm: bảng có 5 dòng nhưng chỉ 3 dòng là giấy tờ thật (Giấy chứng nhận đã cấp; Đơn "
            "Mẫu số 11/ĐK; Văn bản về việc đại diện); 2 dòng còn lại là ghi chú pháp lý của cổng nên "
            "để trống. CCCD và giấy tờ không có dòng riêng được đính chung tại dòng Đơn Mẫu số "
            "11/ĐK — cán bộ có thể tách sang dòng '+ Thêm giấy tờ' nếu cổng yêu cầu. Ô Bản chính/"
            "Bản sao do cán bộ tự chọn (nộp bản số hóa thì chọn Bản sao).\n"
        ),
    },
    {
        "key": "dinh-chinh-sai-sot-quang-ngai",
        # Cùng cổng dichvucong.quangngai.gov.vn với 4 thủ tục Quảng Ngãi ở trên: SPA Angular, URL
        # /vi/padsvc/apply-online/<ObjectId> chỉ mang ObjectId theo cơ quan -> KHÔNG dùng urlIncludes.
        # TÊN THỦ TỤC TRÙNG KHÍT với bản Lai Châu (dinh-chinh-sai-sot), Bắc Ninh, Lâm Đồng, Ninh Bình
        # (dinh-chinh-gcn-da-cap-ninh-binh) và Đà Nẵng nên urlScope là thứ DUY NHẤT chống tráo giữa các
        # tỉnh; cụm text bên dưới chỉ dùng để tách khỏi 4 thủ tục Quảng Ngãi còn lại. Đã pre-check ma
        # trận detect trên 10 snapshot Quảng Ngãi (5 thủ tục x 2 bước) + snapshot đính chính của Ninh
        # Bình/Lâm Đồng/Đà Nẵng: mỗi trang chỉ khớp ĐÚNG một entry, không entry nào cướp trang.
        "detect": {
            "urlScope": ["dichvucong.quangngai.gov.vn"],
            "textIncludes": ["Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Tỉnh Quảng Ngãi] Đính chính Giấy chứng nhận đã cấp lần đầu có sai sót",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18 đã kê khai — "
            "dùng để điền thân đơn, địa chỉ liên hệ và nội dung yêu cầu giải quyết. Hồ sơ dùng mẫu "
            "đơn biến động khác (Mẫu số 11/ĐK) vẫn đọc được.\n"
            "2. Bản gốc Giấy chứng nhận đã cấp cần đính chính — chụp/scan cả bìa, mục thửa đất và "
            "trang 'Những thay đổi sau khi cấp Giấy chứng nhận'.\n"
            "3. Giấy tờ chứng minh sai sót: CCCD/thẻ căn cước của người bị sai thông tin, giấy khai "
            "sinh, trích lục hộ tịch, quyết định/giấy xác nhận, sao y trích lục hồ sơ đất hoặc bản "
            "trích đo nếu sai sót về thửa đất.\n"
            "4. CCCD của người sử dụng đất đứng đơn (cần cho ngày sinh và ngày cấp giấy tờ tùy thân "
            "— Giấy chứng nhận và Đơn thường chỉ ghi năm sinh).\n"
            "5. Nếu nộp thay: văn bản về việc ủy quyền theo quy định của pháp luật về dân sự và CCCD "
            "của đúng người nộp.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Đính kèm: bảng có sẵn 4 dòng, tất cả đều là giấy tờ thật. CCCD/giấy tờ tùy thân được "
            "đính vào dòng 'Giấy tờ chứng minh sai sót' (dòng 3) vì đó là chứng cứ đối chiếu tên "
            "đúng với tên sai trên Giấy chứng nhận. Giấy tờ không có dòng riêng (giấy xác nhận cư "
            "trú, tờ khai thuế...) đính chung tại dòng Đơn Mẫu số 18 (dòng 1) — cán bộ có thể tách "
            "sang dòng '+ Thêm giấy tờ' nếu cổng yêu cầu. Ô Bản chính/Bản sao do cán bộ tự chọn.\n"
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
        "key": "dinh-chinh-da-cap-ninh-binh",
        # SPA không có mã thủ tục ổn định trong URL: khóa domain Ninh Bình và tiêu đề đầy đủ đặc trưng.
        # Tiêu đề "Đính chính Giấy chứng nhận đã cấp" NGẮN hơn bản sai sót ("…lần đầu có sai sót"): trên
        # trang sai sót, entry sai sót (chuỗi dài) khớp và thắng; trên trang đã-cấp, entry sai sót bị loại
        # vì thiếu "lần đầu có sai sót" nên chỉ entry này khớp. Đã mô phỏng trên HTML thật: đúng.
        "detect": {
            "urlScope": ["dichvucong.ninhbinh.gov.vn"],
            "textIncludes": ["Đính chính Giấy chứng nhận đã cấp"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Tỉnh Ninh Bình] Đính chính Giấy chứng nhận đã cấp",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 11/ĐK đã kê khai.\n"
            "2. Bản gốc Giấy chứng nhận đã cấp cần đính chính.\n"
            "3. Giấy tờ chứng minh sai sót thông tin của người được cấp Giấy chứng nhận (giấy khai sinh, "
            "trích lục, quyết định, giấy xác nhận hoặc hồ sơ địa chính liên quan).\n"
            "4. CCCD/CMND của người sử dụng đất; nếu nộp thay: văn bản ủy quyền và giấy tờ của người được ủy quyền.\n"
            "Hệ thống tự phân loại bằng LLM: Bản gốc GCN -> dòng 1; giấy tờ chứng minh sai sót -> dòng 2; "
            "văn bản ủy quyền -> dòng 3; Đơn Mẫu 11/ĐK + CCCD -> dòng 4 (form không có dòng CCCD riêng). "
            "Cán bộ tự chọn Bản chính/Bản sao."
        ),
    },
    {
        "key": "dang-ky-dat-dai-lan-dau-ninh-binh",
        # SPA không có mã thủ tục ổn định trong URL: khóa domain Ninh Bình và tiêu đề đầy đủ đặc trưng.
        "detect": {
            "urlScope": ["dichvucong.ninhbinh.gov.vn"],
            "textIncludes": [
                "Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, "
                "quyền sở hữu tài sản gắn liền với đất lần đầu"
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Ninh Bình] Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử "
            "dụng đất, quyền sở hữu tài sản gắn liền với đất lần đầu đối với hộ gia đình, cá nhân, cộng "
            "đồng dân cư, người gốc Việt Nam định cư ở nước ngoài"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đăng ký đất đai, tài sản gắn liền với đất theo Mẫu số 15 đã kê khai.\n"
            "2. Giấy tờ về quyền sử dụng đất theo Điều 137 hoặc giấy tờ nhận thừa kế quyền sử dụng đất.\n"
            "3. Mảnh trích đo bản đồ địa chính thửa đất (nếu có).\n"
            "4. Trường hợp nhiều người chung quyền: văn bản thỏa thuận cấp chung một Giấy chứng nhận "
            "hoặc danh sách người cùng sử dụng chung.\n"
            "5. Chứng từ thực hiện nghĩa vụ tài chính (nếu có).\n"
            "6. Nếu nộp thay: văn bản ủy quyền/đại diện của đúng người nộp.\n"
            "CCCD/Căn cước của người liên quan đính kèm chung trong file giấy tờ nhận thừa kế (form "
            "không có dòng CCCD riêng).\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân loại bằng LLM và đính đúng dòng, "
            "cán bộ tự chọn Bản chính/Bản sao."
        ),
    },
    {
        "key": "cap-doi-gcn-ninh-binh",
        # SPA không có mã thủ tục ổn định trong URL: khóa domain Ninh Bình và tiêu đề đầy đủ đặc trưng.
        "detect": {
            "urlScope": ["dichvucong.ninhbinh.gov.vn"],
            "textIncludes": [
                "Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất"
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Ninh Bình] Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn "
            "liền với đất"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 11/ĐK đã kê khai.\n"
            "2. Giấy chứng nhận đã cấp cần cấp đổi.\n"
            "3. Mảnh trích đo bản đồ địa chính thửa đất/phiếu đo đạc chỉnh lý (nếu có).\n"
            "4. Nếu nộp thay: văn bản ủy quyền/đại diện của đúng người nộp; kèm CCCD/Căn cước.\n"
            "Hệ thống tự phân loại bằng LLM: mảnh trích đo -> dòng 1; Đơn Mẫu 11 + Giấy chứng nhận đã "
            "cấp + văn bản ủy quyền + CCCD -> dòng 2 (form chỉ có 2 dòng). Cán bộ tự chọn Bản chính/Bản sao."
        ),
    },
    {
        "key": "dang-ky-bien-dong-dat-dai-ninh-binh",
        # SPA không có mã thủ tục ổn định trong URL: khóa domain Ninh Bình và tiêu đề đầy đủ đặc trưng.
        # Đoạn "…trong các trường hợp chuyển đổi" đủ đặc trưng để tách khỏi các thủ tục đất đai NB khác.
        "detect": {
            "urlScope": ["dichvucong.ninhbinh.gov.vn"],
            "textIncludes": [
                "Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất trong các "
                "trường hợp chuyển đổi"
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Ninh Bình] Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với "
            "đất trong các trường hợp chuyển đổi quyền sử dụng đất nông nghiệp mà không theo phương án "
            "dồn điền, đổi thửa; chuyển nhượng, thừa kế, tặng cho quyền sử dụng đất, quyền sở hữu tài "
            "sản gắn liền với đất; góp vốn bằng quyền sử dụng đất, quyền sở hữu tài sản gắn liền với "
            "đất; cho thuê, cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu hạ "
            "tầng; bán hoặc tặng cho hoặc để thừa kế hoặc góp vốn bằng tài sản gắn liền với đất thuê "
            "của Nhà nước theo hình thức thuê đất trả tiền hàng năm"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18 đã kê khai.\n"
            "2. Bản gốc Giấy chứng nhận đã cấp.\n"
            "3. Hợp đồng/văn bản chuyển quyền sử dụng đất (chuyển đổi/chuyển nhượng/thừa kế/tặng cho/"
            "góp vốn); hợp đồng tặng cho quyền sử dụng đất có công chứng cũng thuộc dòng này.\n"
            "4. Tờ khai thuế/lệ phí (thuế TNCN, lệ phí trước bạ, thuế SDĐ phi nông nghiệp) và giấy tờ "
            "hộ tịch chứng minh quan hệ (khai sinh, kết hôn) nếu thuộc diện miễn, giảm.\n"
            "5. CCCD/Căn cước của các bên; nếu nộp thay: văn bản ủy quyền/đại diện của đúng người nộp.\n"
            "Hệ thống tự phân loại bằng LLM và đính đúng dòng: văn bản ủy quyền -> dòng 1; Bản gốc GCN "
            "-> dòng 2; hợp đồng chuyển quyền -> dòng 5; Đơn Mẫu 18 -> dòng 11. CCCD, tờ khai thuế, "
            "giấy tờ hộ tịch đính chung dòng Đơn Mẫu 18 (form không có dòng riêng). Cán bộ tự chọn "
            "Bản chính/Bản sao."
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
        "key": "cap-doi-gcn-quang-ninh-mien-nui-hai-dao",
        # URL /nop-ho-so/145224 có thể đổi theo cấu hình cổng; khóa domain + hai đoạn tiêu đề đặc trưng
        # để tách khỏi các thủ tục đất đai khác (cùng có "Miền núi, hải đảo") tại Quảng Ninh.
        "detect": {
            "urlScope": ["dichvucong.quangninh.gov.vn"],
            "textIncludes": [
                "[Đặc thù] Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
                "Các trường hợp khác - Đối với cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài - Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Quảng Ninh] [Đặc thù] Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài "
            "sản gắn liền với đất - Các trường hợp khác - Đối với cá nhân, cộng đồng dân cư, người gốc "
            "Việt Nam định cư ở nước ngoài - Miền núi, hải đảo"
        ),
        # Trang chỉ có bước thành phần hồ sơ; không chạy compact-agent/process pipeline.
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18.\n"
            "2. Giấy chứng nhận đã cấp (bản cần cấp đổi).\n"
            "3. Mảnh trích đo bản đồ địa chính thửa đất (nếu có nhu cầu đo đạc lại kích thước, diện tích).\n"
            "4. Các tờ khai lệ phí trước bạ (01/LPTB), thuế sử dụng đất phi nông nghiệp (04/TK-SDDPNN), "
            "thuế thu nhập cá nhân (03/BĐS-TNCN) theo hồ sơ thực tế.\n"
            "5. Nếu thực hiện thông qua người đại diện: văn bản đại diện hoặc ủy quyền.\n"
            "Mỗi file được phân loại theo tài liệu chính và chỉ đính vào một thành phần hồ sơ."
        ),
    },
    {
        "key": "cap-doi-gcn-do-do-dac-khong-nvtc-quang-ninh-mien-nui-hai-dao",
        # BIẾN THỂ cùng maThuTuc 1.115848 (URL /nop-ho-so/145216) — "Trường hợp do đo đạc lại thửa đất
        # (ranh giới không đổi) + KHÔNG phải thực hiện nghĩa vụ tài chính". Thành phần hồ sơ Y HỆT
        # "cap-doi-gcn-quang-ninh-mien-nui-hai-dao" → DÙNG CHUNG attach planner. Detect phải dùng đoạn
        # tiêu đề RIÊNG (không có "Các trường hợp khác") để không đè lên biến thể kia.
        "detect": {
            "urlScope": ["dichvucong.quangninh.gov.vn"],
            "textIncludes": [
                "[Đặc thù] Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất",
                "do thay đổi kích thước các cạnh, diện tích, số hiệu của thửa đất do đo đạc",
                "Trường hợp không phải thực hiện nghĩa vụ tài chính",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Quảng Ninh] [Đặc thù] Cấp đổi Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài "
            "sản gắn liền với đất - Trường hợp cấp đổi Giấy chứng nhận do thay đổi kích thước các cạnh, "
            "diện tích, số hiệu của thửa đất do đo đạc lập bản đồ địa chính, trích đo địa chính thửa đất "
            "mà ranh giới thửa đất không thay đổi - Trường hợp không phải thực hiện nghĩa vụ tài chính - "
            "Đối với cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài - Miền núi, hải đảo"
        ),
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên (trường hợp cấp đổi do đo đạc lại thửa đất, không phải nộp nghĩa vụ "
            "tài chính):\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18.\n"
            "2. Giấy chứng nhận đã cấp (bản cần cấp đổi).\n"
            "3. Mảnh trích đo/Phiếu đo đạc chỉnh lý bản đồ địa chính thửa đất (ranh giới không thay đổi).\n"
            "4. Nếu có: tờ khai lệ phí trước bạ (01/LPTB), thuế sử dụng đất phi nông nghiệp (04/TK-SDDPNN), "
            "thuế thu nhập cá nhân (03/BĐS-TNCN); văn bản đại diện/ủy quyền khi nộp thay.\n"
            "Mỗi file được phân loại theo tài liệu chính và chỉ đính vào một thành phần hồ sơ. Giấy tờ "
            "ngoài danh mục (vd công văn xác nhận thông tin nhà ở) sẽ cần đính thủ công."
        ),
    },
    {
        "key": "tach-hop-thua-dat-quang-ninh-mien-nui-hai-dao",
        # URL /nop-ho-so/145146 (maThuTuc 1.115832) đổi theo cấu hình cổng → khóa domain + đoạn tiêu đề
        # đặc trưng "Tách thửa cùng tên" để tách khỏi các biến thể tách/hợp thửa khác tại Quảng Ninh.
        "detect": {
            "urlScope": ["dichvucong.quangninh.gov.vn"],
            "textIncludes": [
                "[Đặc thù] Tách thửa đất, hợp thửa đất",
                "Đối với trường hợp Tách thửa cùng tên - Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Quảng Ninh] [Đặc thù] Tách thửa đất, hợp thửa đất - Đối với trường hợp Giấy chứng nhận "
            "đã cấp khi thực hiện các quyền của hộ gia đình, cá nhân, cộng đồng dân cư, người Việt Nam định "
            "cư ở nước ngoài được sở hữu nhà ở gắn liền với quyền sử dụng đất ở tại Việt Nam - Đối với "
            "trường hợp Tách thửa cùng tên - Miền núi, hải đảo"
        ),
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đề nghị tách thửa đất, hợp thửa đất theo Mẫu số 26.\n"
            "2. Bản vẽ tách thửa đất, hợp thửa đất theo Mẫu số 27.\n"
            "3. Bản gốc Giấy chứng nhận đã cấp.\n"
            "4. Nếu có: tờ khai lệ phí trước bạ (01/LPTB), thuế sử dụng đất phi nông nghiệp (04/TK-SDDPNN), "
            "thuế thu nhập cá nhân (03/BĐS-TNCN); văn bản của cơ quan có thẩm quyền về tách/hợp thửa.\n"
            "Mỗi file được phân loại (LLM) theo tài liệu chính và đính vào đúng thành phần hồ sơ; giấy tờ "
            "ngoài danh mục được thêm thành một thành phần hồ sơ mới."
        ),
    },
    {
        "key": "dang-ky-tai-san-dat-quang-ninh-mien-nui-hai-dao",
        # URL /nop-ho-so/145196 đổi theo cấu hình cổng → khóa domain + đoạn tiêu đề đặc trưng ("phải thực
        # hiện nghĩa vụ tài chính") để tách khỏi biến thể "không phải nghĩa vụ tài chính".
        "detect": {
            "urlScope": ["dichvucong.quangninh.gov.vn"],
            "textIncludes": [
                "[Đặc thù] Đăng ký tài sản gắn liền với thửa đất đã được cấp Giấy chứng nhận",
                "Trường hợp phải thực hiện nghĩa vụ tài chính",
                "Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Quảng Ninh] [Đặc thù] Đăng ký tài sản gắn liền với thửa đất đã được cấp Giấy chứng nhận "
            "hoặc đăng ký thay đổi về tài sản gắn liền với đất; gia hạn thời hạn sở hữu nhà ở của tổ chức, "
            "cá nhân nước ngoài - Trường hợp phải thực hiện nghĩa vụ tài chính - Đối với cá nhân, cộng đồng "
            "dân cư, người gốc Việt Nam định cư ở nước ngoài - Miền núi, hải đảo"
        ),
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Thủ tục này KHÔNG có dòng thành phần hồ sơ sẵn — MỌI giấy tờ đều được thêm thành một thành "
            "phần hồ sơ mới, đặt tên theo loại tài liệu.\n"
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất.\n"
            "2. Bản gốc Giấy chứng nhận đã cấp.\n"
            "3. Giấy phép xây dựng, hồ sơ thiết kế, sơ đồ/phiếu đo đạc tài sản gắn liền với đất.\n"
            "4. Giấy tờ chứng minh quyền sở hữu tài sản; các tờ khai lệ phí trước bạ (01/LPTB), thuế sử "
            "dụng đất phi nông nghiệp (04/TK-SDDPNN), thuế thu nhập cá nhân (03/BĐS-TNCN).\n"
            "Hệ thống tự phân loại (LLM) để đặt tên thành phần; giấy tờ không nhận ra được đặt tên theo tệp."
        ),
    },
    {
        "key": "dang-ky-bien-dong-doi-ten-quang-ninh-mien-nui-hai-dao",
        # URL /nop-ho-so/<id> đổi theo cấu hình cổng → khóa domain + đoạn tiêu đề đặc trưng
        # ("đổi tên hoặc thay đổi thông tin về người sử dụng đất") để tách khỏi các biến thể biến động khác.
        "detect": {
            "urlScope": ["dichvucong.quangninh.gov.vn"],
            "textIncludes": [
                "[Đặc thù] Đăng ký biến động đối với trường hợp đổi tên hoặc thay đổi thông tin về người sử dụng đất",
                "đổi tên hoặc thay đổi thông tin về người sử dụng đất",
                "Miền núi, hải đảo",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Quảng Ninh] [Đặc thù] Đăng ký biến động đối với trường hợp đổi tên hoặc thay đổi thông "
            "tin về người sử dụng đất, chủ sở hữu tài sản gắn liền với đất - Đối với cá nhân, cộng đồng dân "
            "cư, người gốc Việt Nam định cư ở nước ngoài - Miền núi, hải đảo"
        ),
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Thủ tục này CÓ SẴN các dòng thành phần hồ sơ; hệ thống tự phân loại (LLM) để đính đúng dòng. "
            "Giấy tờ ngoài danh mục sẽ được thêm thành một thành phần hồ sơ mới, đặt tên theo tệp.\n"
            "Giấy tờ nên tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất theo Mẫu số 18.\n"
            "2. Giấy tờ chứng minh việc đổi tên/thay đổi thông tin của người sử dụng đất, chủ sở hữu tài sản.\n"
            "3. Văn bản của cơ quan có thẩm quyền cho phép hoặc công nhận việc đổi tên (nếu có).\n"
            "4. Bản gốc Giấy chứng nhận đã cấp; mảnh trích đo bản đồ địa chính; văn bản đại diện (nếu có)."
        ),
    },
    {
        "key": "xoa-dang-ky-bien-phap-bao-dam-quang-ninh",
        # URL /nop-ho-so/141949 đổi theo cấu hình cổng → khóa domain + tiêu đề đặc trưng ("Xóa đăng ký
        # biện pháp bảo đảm"). Bản GENERAL (không "Miền núi, hải đảo") — chỉ có ở QN nên tiêu đề đủ tách.
        "detect": {
            "urlScope": ["dichvucong.quangninh.gov.vn"],
            "textIncludes": [
                "Xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Tỉnh Quảng Ninh] Xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất",
        # Trang chỉ có bước thành phần hồ sơ; engine wallet-modal (React/Radix), không chạy process.
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Thủ tục này CÓ SẴN các dòng thành phần hồ sơ; hệ thống tự phân loại (LLM) để đính đúng dòng. "
            "Giấy tờ ngoài danh mục sẽ được thêm thành một thành phần hồ sơ mới, đặt tên theo tệp.\n"
            "Giấy tờ nên tải lên:\n"
            "1. Giấy chứng nhận (bản gốc) — nếu tài sản bảo đảm có Giấy chứng nhận → dòng 1.\n"
            "2. Phiếu yêu cầu xóa đăng ký biện pháp bảo đảm (Mẫu số 02a) → dòng 2.\n"
            "3. Văn bản của bên nhận bảo đảm (ngân hàng) đồng ý/xác nhận xóa đăng ký thế chấp → dòng 5.\n"
            "Lưu ý: nếu Phiếu yêu cầu và Công văn ngân hàng nằm CHUNG 1 file PDF, hệ thống phân theo tài "
            "liệu chính (phiếu) → đính dòng 2; cần đính công văn vào dòng 5 thì tách file riêng."
        ),
    },
    {
        "key": "giao-thue-dat-lao-cai",
        # TỈNH MỚI: dichvucong.laocai.gov.vn — eForm iGate legacy (ô CongDan_*/ChuHoSo_*), CÙNG nền tảng
        # với các thủ tục Lai Châu nên dùng lại engine fill-legacy.js và engine đính kèm fixed-slot.
        # Cổng là SPA, URL có ?sid=<phiên> đổi mỗi lần nộp → khóa host + cụm tên thủ tục (như Lai Châu).
        "detect": {
            "urlScope": ["dichvucong.laocai.gov.vn"],
            "textIncludes": [
                "giao đất, cho thuê đất đối với trường hợp giao đất, cho thuê đất không đấu giá",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Lào Cai] Giao đất, cho thuê đất đối với trường hợp giao đất, cho thuê đất không đấu "
            "giá quyền sử dụng đất, không đấu thầu lựa chọn nhà đầu tư thực hiện dự án có sử dụng đất và "
            "trường hợp giao đất, cho thuê đất thông qua đấu thầu lựa chọn nhà đầu tư thực hiện dự án có "
            "sử dụng đất; giao đất và giao rừng; cho thuê đất và cho thuê rừng"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn xin giao đất/thuê đất (Mẫu số 01) — dùng để điền thân đơn.\n"
            "2. Quyết định chấp thuận chủ trương đầu tư và CÁC quyết định điều chỉnh chủ trương (tất cả "
            "vào cùng một dòng).\n"
            "3. Giấy chứng nhận đăng ký doanh nghiệp (hồ sơ tổ chức) — lấy tên công ty, mã số doanh "
            "nghiệp, địa chỉ trụ sở, người đại diện.\n"
            "4. Nếu có: phương án sử dụng đất, giấy phép khai thác khoáng sản, hồ sơ giao/thuê rừng, "
            "giấy tờ miễn giảm tiền sử dụng đất.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân loại theo nội dung OCR. Giấy tờ chưa "
            "rõ loại vẫn được đính vào dòng 'Giấy tờ khác' — không bỏ sót tệp nào.\n"
            "⚠ ĐIỀN FORM: nút/checkbox 'Người nộp là chủ hồ sơ' của cổng chỉ sao chép sang khối chủ hồ sơ "
            "tới Nơi cấp/Ngày cấp căn cước, KHÔNG sao chép Tỉnh/Phường-Xã/Địa chỉ. Hệ thống vì vậy luôn "
            "điền đầy đủ cả khối chủ hồ sơ kể cả khi người nộp trùng chủ hồ sơ."
        ),
    },
    {
        "key": "dang-ky-bien-phap-bao-dam-quang-ninh",
        # URL /nop-ho-so/141946 (thủ tục XÓA là /141949) — id đổi theo cấu hình cổng → khóa domain +
        # tiêu đề. ⚠ Cụm "Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất" là CHUỖI CON của tiêu đề
        # thủ tục XÓA ("Xóa đăng ký biện pháp bảo đảm bằng…") nên TRANG XÓA khớp CẢ HAI entry. FE
        # (popup.js detectProcedure, nhánh textPriority) chọn entry có TỔNG ĐỘ DÀI CỤM LỚN NHẤT, nên
        # trang xóa vẫn về đúng thủ tục xóa nhờ cụm dài hơn — KHÔNG phụ thuộc thứ tự entry. Hệ quả:
        # đừng rút ngắn textIncludes của thủ tục XÓA xuống ngắn hơn cụm này (có test chặn).
        "detect": {
            "urlScope": ["dichvucong.quangninh.gov.vn"],
            "textIncludes": [
                "Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Tỉnh Quảng Ninh] Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất",
        # Trang chỉ có bước thành phần hồ sơ; engine wallet-modal (React/Radix), không chạy process.
        "mode": "attach",
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Thủ tục này CÓ SẴN các dòng thành phần hồ sơ; hệ thống tự phân loại (LLM) để đính đúng dòng. "
            "Giấy tờ ngoài danh mục sẽ được thêm thành một thành phần hồ sơ mới, đặt tên theo tệp.\n"
            "Giấy tờ nên tải lên:\n"
            "1. Phiếu yêu cầu đăng ký biện pháp bảo đảm (theo mẫu Phụ lục NĐ 99/2022/NĐ-CP) → dòng 2.\n"
            "2. Hợp đồng thế chấp quyền sử dụng đất, tài sản gắn liền với đất (đã công chứng) → thêm "
            "thành phần hồ sơ mới (form không có dòng sẵn cho hợp đồng gốc).\n"
            "3. Giấy chứng nhận (bản gốc) — nếu tài sản bảo đảm có Giấy chứng nhận → dòng 1.\n"
            "4. Văn bản ủy quyền/đại diện khi nộp thay → thêm thành phần hồ sơ mới.\n"
            "Lưu ý: nếu Phiếu yêu cầu và Hợp đồng thế chấp nằm CHUNG 1 file PDF, hệ thống phân theo tài "
            "liệu chính (phiếu) → đính dòng 2; muốn tách riêng thì tải lên 2 tệp."
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
        "key": "dang-ky-bien-dong-dat-dai-bac-ninh",
        # Cổng dichvucong.bacninh.gov.vn (Liferay eForm) — engine fill-bacninh.js. KHÁC 1.013831 (chuyển
        # nhượng): 1.115468 phạm vi rộng hơn (thêm chuyển đổi QSDĐ nông nghiệp + mua bán nhà ở có thời hạn),
        # đơn có thêm Mã số thuế/Email, đính kèm dùng mã TP-H05.
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["maThuTucHanhChinh=1.115468"],
        },
        "label": (
            "[Tỉnh Bắc Ninh] Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất "
            "trong các trường hợp chuyển đổi quyền sử dụng đất nông nghiệp mà không theo phương án dồn "
            "điền, đổi thửa; chuyển nhượng, thừa kế, tặng cho quyền sử dụng đất, quyền sở hữu tài sản gắn "
            "liền với đất, góp vốn bằng quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất; cho thuê, "
            "cho thuê lại quyền sử dụng đất trong dự án xây dựng kinh doanh kết cấu hạ tầng; bán hoặc tặng "
            "cho hoặc để thừa kế hoặc góp vốn bằng tài sản gắn liền với đất thuê của Nhà nước theo hình "
            "thức thuê đất trả tiền hàng năm; mua bán nhà ở có thời hạn"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai (Mẫu số 18) bên NHẬN chuyển quyền đã khai — dùng để điền thân đơn.\n"
            "2. Bản gốc Giấy chứng nhận QSDĐ đã cấp (sổ đỏ/sổ hồng).\n"
            "3. Hợp đồng/văn bản chuyển quyền (chuyển đổi/chuyển nhượng/tặng cho/thừa kế/góp vốn/cho thuê/mua "
            "bán nhà ở có thời hạn) + Lời chứng chứng thực/công chứng.\n"
            "4. Giấy ủy quyền/văn bản đại diện (nếu nộp qua người được ủy quyền — BẮT BUỘC).\n"
            "5. CCCD/hộ tịch (kết hôn, khai sinh), 3 tờ khai thuế (03/BĐS-TNCN, 01/LPTB, 01/TK-SDDPNN), biên "
            "bản bàn giao đất.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Lưu ý: mọi thông tin điền là của BÊN NHẬN chuyển quyền (Bên B), không phải bên chuyển; người được "
            "ủy quyền chỉ đi nộp thay.\n"
            "Điền đơn: khớp ô theo class ổn định (Kính gửi, Tên, Giấy tờ nhân thân/pháp nhân, Địa chỉ, Mã số "
            "thuế, Điện thoại, Hộp thư điện tử, Nội dung biến động, (3) giấy tờ kèm) + khối người nhận kết quả "
            "(họ tên, CCCD, SĐT, email, địa chỉ).\n"
            "Đính kèm (16 thành phần TP-H05): Đơn Mẫu 18→TP-H05.000026, GCN gốc→TP-H05.000040, HĐ tặng cho→"
            "TP-H05.000080, HĐ chuyển nhượng/chuyển đổi/thừa kế/góp vốn→TP-H05.000069, VB đại diện/ủy quyền→"
            "TP-H05.000079 (và 000070–000078, 000033, 000045 khi có); CCCD/hộ tịch/tờ khai thuế/biên bản bàn "
            "giao→ô 'File đính kèm khác'. Cơ quan tiếp nhận và tỉnh/phường người nhận là select theo địa bàn "
            "— chọn tay."
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
        "key": "dien-thong-tin-tai-khoan-bac-ninh",
        # Trang HOÀN THIỆN TÀI KHOẢN lần đầu sau đăng nhập VNeID SSO: dichvucong.bacninh.gov.vn/web/guest/
        # vneidsso. ⚠ Detect theo PATH /vneidsso, KHÔNG dùng maTTHC (URL mang maTTHC=1.011443 của thủ tục
        # đang làm → trùng thủ tục Xóa ĐK BPBĐ). Portlet prefix MỚI _org_bn_taikhoan_sso_vneid_* → engine
        # FE fillAccountBacNinh (khớp ô theo NAME suffix). Process-only (không đính kèm).
        "detect": {
            "urlScope": ["dichvucong.bacninh.gov.vn"],
            "urlIncludes": ["/vneidsso"],
        },
        "label": "[Tỉnh Bắc Ninh] Điền thông tin tài khoản",
        "mode": "agent",
        "hasAttachmentStep": False,
        "roles": [],
        "useDangKyBy": False,
        "fillButtonLabel": "Điền thông tin tài khoản",
        "uploadHint": (
            "Trang hoàn thiện thông tin tài khoản lần đầu trên Cổng DVC Bắc Ninh (sau khi đăng nhập VNeID).\n"
            "Giấy tờ cần tải lên:\n"
            "1. Căn cước công dân (mặt trước + mặt sau) của chủ tài khoản — nguồn chính.\n"
            "2. Hoặc tờ khai/đơn/Giấy chứng nhận QSDĐ có ghi thông tin CCCD của chính người đó (nếu không "
            "có ảnh CCCD).\n"
            "Hệ thống lấy Họ tên + Số định danh cổng đã điền sẵn (VNeID) làm mốc để chọn ĐÚNG người trong "
            "giấy tờ, rồi điền: họ tên, giới tính, ngày sinh, số/ngày/nơi cấp CCCD, quê quán, nơi thường "
            "trú (Tỉnh/Phường-Xã/địa chỉ chi tiết). Nơi ở hiện tại chỉ điền khi giấy tờ ghi rõ; số điện "
            "thoại/email chỉ điền khi có. Tỉnh/Phường-Xã là select theo danh mục — hệ thống chọn theo tên."
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
            "1. Đơn đề nghị tách thửa/hợp thửa đất (Mẫu số 22) chủ đất đã khai — dùng để điền thân đơn.\n"
            "2. Giấy chứng nhận QSDĐ (sổ đỏ/sổ hồng) đã cấp.\n"
            "3. Bản vẽ tách thửa/hợp thửa (Mẫu số 22a).\n"
            "4. CCCD/giấy tờ tùy thân của chủ đất; nếu có: văn bản của cơ quan thẩm quyền về tách/hợp "
            "thửa, giấy ủy quyền, giấy phép hoạt động đo đạc và bản đồ của đơn vị lập bản vẽ.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Điền đơn (chỉ nhánh TÁCH THỬA): khớp ô theo NHÃN (Kính gửi, a) Tên, b) Giấy tờ nhân thân, thửa "
            "đất số/tờ bản đồ/diện tích/loại đất/địa chỉ thửa/số vào sổ GCN/ngày cấp, diện tích thửa mới, lý "
            "do, giấy tờ kèm, đề nghị cấp GCN) + khối người nhận kết quả (họ tên, CCCD, SĐT, địa chỉ).\n"
            "Đính kèm (khớp theo MÃ THÀNH PHẦN in trong dòng tiêu đề trên cổng): Đơn Mẫu 22→TP-H05.000032, "
            "Bản vẽ Mẫu 22a→TP-H05.000033, GCN đã cấp→TP-H05.000040, Văn bản cơ quan có thẩm quyền→"
            "TP-H05.000047; CCCD, giấy ủy quyền, giấy phép đo đạc và giấy tờ chưa rõ loại→ô 'File đính kèm "
            "khác' (không bỏ sót tệp nào).\n"
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
            "Đính kèm (khớp theo mã TP-H05): Đơn Mẫu 18 → TP-H05.000026; Bản gốc GCN đã cấp → TP-H05.000040; "
            "CCCD/văn bản ủy quyền/giấy tờ khác → ô 'File đính kèm khác' (form cấp đổi không có ô riêng cho "
            "các giấy tờ này).\n"
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
        # ⚠ TẠM ẨN KHỎI TỰ NHẬN DIỆN (detectDisabled) — vẫn chọn tay được.
        # detect cũ chỉ có 2 cụm ngắn ["điều chỉnh", "giao đất"] và KHÔNG khóa cổng nào: đây là rule
        # lỏng nhất toàn registry nên mọi trang đất đai có 2 chữ đó đều bị nó nhận, đã cướp trang của
        # thủ tục giao/thuê đất Lào Cai. Bản gắn đúng cổng Lào Cai nằm ở entry
        # "dieu-chinh-quyet-dinh-giao-dat-lao-cai" ngay dưới; khi xác định được cổng gốc của entry này
        # thì khóa urlScope cho nó rồi bỏ detectDisabled.
        "detect": {"textIncludes": ["điều chỉnh", "giao đất"], "headingDisabled": True},
        "detectDisabled": True,
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
        "key": "dieu-chinh-quyet-dinh-giao-dat-lao-cai",
        # Cùng nghiệp vụ với "dieu-chinh-dat-dai" nhưng KHÓA ĐÚNG CỔNG Lào Cai và khớp bằng CỤM TÊN
        # THỦ TỤC ĐẦY ĐỦ thay vì 2 chữ rời, nên không cướp trang của thủ tục khác. Dùng lại pipeline
        # process sẵn có (app/pipelines/dieu_chinh_dat_dai).
        "detect": {
            "urlScope": ["dichvucong.laocai.gov.vn"],
            # Mã thủ tục in trên trang ổn định hơn ?sid= (đổi mỗi phiên nộp).
            "urlIncludes": ["1.115652"],
            "textIncludes": [
                "điều chỉnh quyết định giao đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": (
            "[Tỉnh Lào Cai] Điều chỉnh quyết định giao đất, cho thuê đất, cho phép chuyển mục đích "
            "sử dụng đất"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị điều chỉnh (Mẫu số 04 kèm QĐ 47/2026/QĐ-UBND) → dòng 1.\n"
            "2. Quyết định giao đất/cho thuê đất/cho phép chuyển mục đích ĐANG ĐỀ NGHỊ ĐIỀU CHỈNH, Giấy "
            "chứng nhận QSDĐ, hồ sơ bản đồ kèm theo → dòng 2.\n"
            "3. Văn bản làm THAY ĐỔI CĂN CỨ: quyết định phê duyệt/điều chỉnh quy hoạch chi tiết, quyết "
            "định chấp thuận (điều chỉnh) chủ trương đầu tư các lần → dòng 3.\n"
            "4. Giấy tờ khác (ĐKKD, ủy quyền…) sẽ được thêm thành dòng 'Giấy tờ khác' kèm tên tài liệu.\n"
            "Một dòng nhận được NHIỀU tệp; nếu một tệp gộp nhiều quyết định thì ghi rõ danh mục văn bản "
            "vào ô 'Ghi chú'.\n"
            "⚠ ĐIỀN FORM: ô 'Về việc' (*) ở bước Thành phần hồ sơ được cổng điền sẵn TÊN THỦ TỤC — hệ "
            "thống ghi đè bằng trích yếu thật của Đơn (số/ngày quyết định bị điều chỉnh + tên dự án).\n"
            "⚠ Nút 'Người nộp là chủ hồ sơ' của cổng KHÔNG sao chép Tỉnh/Phường-Xã/Địa chỉ, nên hệ thống "
            "luôn điền đầy đủ khối chủ hồ sơ. Địa chỉ ghi theo đơn vị hành chính CŨ (trước sáp nhập) sẽ "
            "được chuẩn hoá; xã/phường cũ không còn thì hệ thống báo để cán bộ chọn tay."
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
            "Bước thành phần hồ sơ: bảng của cổng (Nghị định 217/2026) chia 29 dòng thành 5 KHỐI theo "
            "LOẠI CÔNG TRÌNH, mỗi khối lặp lại gần như y hệt bộ giấy tờ — phải đính đúng khối.\n"
            "• Nhà ở riêng lẻ: Đơn + CCCD + Bản cam kết vào STT 12; Sổ đỏ/GCN QSDĐ vào STT 13; "
            "Bản vẽ + kê khai + chứng chỉ thiết kế vào STT 16.\n"
            "• Công trình tín ngưỡng, tôn giáo (chùa, nhà thờ, đình, đền…): lần lượt STT 6, 7, 10.\n"
            "Hệ thống tự nhận loại công trình từ đơn/bản vẽ, mặc định là nhà ở riêng lẻ."
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
        # process= ĐỔI THEO TỪNG ĐƠN VỊ (mỗi phường/xã sinh một quy trình riêng) nên KHÔNG thể chỉ dựa vào
        # URL. Nhận diện chính = dòng "Quy trình: Cấp giấy phép xây dựng sửa chữa, cải tạo đối với nhà ở
        # riêng lẻ" in ngay dưới h2 tên thủ tục — đây là chỗ DUY NHẤT trên trang nói rõ biến thể nhà ở riêng
        # lẻ (h2 luôn là tên thủ tục gộp cả hai loại). Cụm tên thủ tục đi kèm để không dính trang thủ tục
        # khác. urlIncludes giữ lại process= đã biết: rule URL chạy TRƯỚC rule text nên vẫn là đường tắt.
        # KHÔNG khai urlScope: cùng hệ thống Bộ Xây dựng nhưng địa phương vào bằng host khác nhau, mà
        # urlScope chặn CẢ rule text → chỉ cần lệch host là thủ tục chết lặng. Hai cụm dưới đây đủ đặc
        # trưng (tên thủ tục + tên quy trình) nên không cần hàng rào host.
        "detect": {
            "urlIncludes": ["process=696899ffadf251292a49d6cb"],
            "textIncludes": [
                "giấy phép xây dựng sửa chữa, cải tạo đối với công trình cấp III, cấp IV",
                "sửa chữa, cải tạo đối với nhà ở riêng lẻ",
            ],
            # textPriority: rule text của entry này phải chạy TRƯỚC rule heading của entry "…-chung"
            # (h2 giống nhau ở cả ba quy trình), nếu không trang nhà ở riêng lẻ sẽ rơi vào entry chung
            # và mất phần ép đúng bộ element ...NhaO.
            "textPriority": True,
            "headingDisabled": True,
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
        # Đây là entry mang MÃ QG 1.013229 (xem ke_khai_links.json) → nhận diện CHUNG cho cả thủ tục:
        # process= đổi theo từng phường/xã nên KHÔNG bám vào nó; bám vào (1) apply-online id = id THỦ TỤC,
        # dùng chung mọi đơn vị, (2) H2 TÊN THỦ TỤC in trên trang. Trang nào ghi rõ "Quy trình: … đối với
        # nhà ở riêng lẻ" thì entry nhà ở riêng lẻ ở trên đã chặn trước bằng textPriority, nên rơi xuống
        # đây nghĩa là quy trình công trình → ép ...KhongTheoTuyen là đúng.
        # KHÔNG khai urlScope: địa phương vào hệ thống Bộ Xây dựng bằng host khác nhau, mà urlScope chặn
        # CẢ rule text lẫn URL kê khai DVCQG mà with_ke_khai_detect_urls() ghép thêm vào urlIncludes.
        # heading: h2 trang cổng là tên thủ tục ĐẦY ĐỦ (có thêm "và nhà ở riêng lẻ" + dấu ":"), label của
        # entry này là phần đầu của nó → popup khớp bằng startsWith. textIncludes là lớp dự phòng khi h2
        # không vào được mảng headings (content.js chỉ nhặt heading <= 250 ký tự, h2 này ~305).
        "detect": {
            "urlIncludes": [
                "apply-online/69440eb769ebc10b31e81dba",
                "process=696899ffadf251292a49d6ca",
            ],
            "textIncludes": [
                "giấy phép xây dựng sửa chữa, cải tạo đối với công trình cấp III, cấp IV",
                "và nhà ở riêng lẻ",
            ],
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
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 13; hồ sơ lập theo Mẫu số 15 vẫn "
            "nhận, kèm danh sách người sử dụng chung Mẫu số 13a nếu có).\n"
            "2. Sơ đồ/bản trích lục bản đồ địa chính hoặc mảnh trích đo bản đồ địa chính thửa đất, kèm "
            "bản mô tả ranh giới, mốc giới thửa đất.\n"
            "3. Giấy tờ về việc chuyển quyền sử dụng đất hoặc bản cam kết nguồn gốc đất (nếu đất nhận "
            "chuyển quyền/tự khai hoang).\n"
            "4. Giấy chứng nhận của thửa đất liền kề (nếu cần đối chiếu ranh giới) hoặc Giấy chứng nhận "
            "đã cấp cho phần diện tích tăng thêm.\n"
            "5. CCCD/thẻ căn cước của người nộp hồ sơ.\n"
            "6. Nếu nộp thay: văn bản về việc đại diện/ủy quyền theo quy định của pháp luật dân sự.\n"
            "LƯU Ý: mỗi tệp tải lên KHÔNG QUÁ 6 MB — file scan gộp nhiều giấy tờ thường nặng hơn, hãy "
            "tách nhỏ theo từng giấy tờ (hoặc giảm DPI) trước khi tải lên, nếu không cổng sẽ từ chối."
        ),
    },
    {
        "key": "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai",
        # Cổng dichvucong.laocai.gov.vn (iGate VNPT, maCoQuan=STNMT_LCI) — engine dom-* chuẩn, khớp ô
        # theo name CongDan_*/ChuHoSo_*. Map bước 2 "Thông tin người nộp" + đính kèm bảng Thành phần hồ sơ
        # (fixed-slot theo nhánh a/b — attach/catalog.py); eForm Mẫu 24 chưa có DOM nên chưa điền. Key trùng
        # mục ke_khai_links để popup tự
        # nhận cả trang chi tiết thủ tục trên Cổng DVC quốc gia.
        "detect": {
            "urlScope": ["laocai.gov.vn"],
            "textIncludes": [
                "cho người nhận chuyển nhượng quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng "
                "trong dự án bất động sản",
            ],
            "headingDisabled": True,
        },
        "label": (
            "[Lào Cai] Đăng ký, cấp Giấy chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với "
            "đất cho người nhận chuyển nhượng quyền sử dụng đất, quyền sở hữu nhà ở, công trình xây dựng "
            "trong dự án bất động sản"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 24).\n"
            "2. Hợp đồng chuyển nhượng quyền sử dụng đất, quyền sở hữu nhà ở/công trình đã công chứng.\n"
            "3. CCCD/thẻ căn cước của người nhận chuyển nhượng (chủ hồ sơ) và của người nộp hồ sơ.\n"
            "4. Nếu có: Giấy chứng nhận của dự án, biên bản bàn giao/kiểm tra hiện trạng, biên bản nghiệm thu.\n"
            "Trợ lý điền bước Thông tin người nộp và Thông tin chủ hồ sơ; hai vợ chồng cùng nhận chuyển "
            "nhượng thì điền theo người đứng tên đầu trên Đơn.\n"
            "Thành phần hồ sơ: tự tích + đính kèm vào nhánh b) (người nhận chuyển nhượng tự nộp), hoặc nhánh "
            "a) khi chủ đầu tư nộp; GCN của chủ đầu tư được đính kèm cả dòng Sơ đồ tài sản. CCCD không có "
            "dòng riêng nên không đính kèm."
        ),
    },
    {
        "key": "dang-ky-bien-dong-dat-dai-lao-cai",
        # Cổng dichvucong.laocai.gov.vn (iGate VNPT, maCoQuan=STNMT_LCI) — CÙNG form bước 2 CongDan_*/ChuHoSo_*
        # với 1.115667 (engine dom-*), đính kèm fixed-slot theo nhánh a/b + "Giấy tờ khác" (attach/catalog.py).
        # Cụm "dồn điền" cũng có ở bản Đà Nẵng/Ninh Bình/Bắc Ninh → urlScope khóa host Lào Cai. Trang 1.115667
        # không chứa cụm này và ngược lại. Key trùng mục ke_khai_links (1.115668).
        "detect": {
            "urlScope": ["laocai.gov.vn"],
            "textIncludes": ["chuyển đổi quyền sử dụng đất nông nghiệp mà không theo phương án dồn điền"],
            "headingDisabled": True,
        },
        "label": (
            "[Lào Cai] Đăng ký biến động quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất trong các "
            "trường hợp chuyển đổi quyền sử dụng đất nông nghiệp mà không theo phương án dồn điền, đổi thửa; "
            "chuyển nhượng, thừa kế, tặng cho quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất, góp vốn "
            "bằng quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất; cho thuê, cho thuê lại quyền sử dụng "
            "đất trong dự án xây dựng kinh doanh kết cấu hạ tầng; bán hoặc tặng cho hoặc để thừa kế hoặc góp vốn "
            "bằng tài sản gắn liền với đất thuê của Nhà nước theo hình thức thuê đất trả tiền hàng năm; chuyển "
            "nhượng quyền khai thác khoáng sản"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 24).\n"
            "2. Giấy chứng nhận quyền sử dụng đất đã cấp.\n"
            "3. Hợp đồng/văn bản chuyển quyền (chuyển nhượng, mua bán tài sản đấu giá, thừa kế, tặng cho, góp "
            "vốn) đã công chứng.\n"
            "4. Nếu có: Giấy ủy quyền, GCN đăng ký doanh nghiệp (chủ hồ sơ là tổ chức), hóa đơn, tờ khai thuế.\n"
            "5. CCCD của chủ hồ sơ (cá nhân) và của người nộp hồ sơ.\n"
            "Chủ hồ sơ = bên NHẬN quyền đứng tên Đơn (cá nhân hoặc tổ chức). Người nộp: chỉ bổ sung nhân thân "
            "từ CCCD của chính người nộp; số điện thoại/email trên Đơn điền cho chủ hồ sơ.\n"
            "Thành phần hồ sơ: tự tích + đính kèm theo dòng nhánh a) (hoặc b) khi tặng cho QSDĐ cho Nhà nước/"
            "cộng đồng); Giấy ủy quyền + GCN ĐKDN vào dòng 'Văn bản về việc đại diện'; hóa đơn, tờ khai thuế, "
            "giấy tờ khác vào 'Thành phần hồ sơ khác'. CCCD không đính kèm."
        ),
    },
    {
        "key": "thu-hoi-gcn-cap-lan-dau-khong-dung-quy-dinh-cap-lai",
        # Cổng dichvucong.laocai.gov.vn (iGate VNPT) — CÙNG form bước 2 CongDan_*/ChuHoSo_* với
        # 1.115651/1.115667/1.115668/1.115671 (engine dom-*), mapping theo
        # "mapping_thu_hoi_huy_GCN_laocai.xlsx". Khác các thủ tục anh em: ba ô địa chỉ của khối NGƯỜI NỘP là
        # bắt buộc (*) và cổng để TRỐNG → pipeline điền thêm CongDan_maTinhThanh/maPhuongXa/diaChi.
        # Bước 3 "Thành phần hồ sơ" là bảng PHẲNG đúng 2 dòng (văn bản kiến nghị + GCN đã cấp) + "Giấy tờ khác".
        # 1.115687 là mã QUỐC GIA, bản Bắc Ninh (thu-hoi-gcn-cap-sai-bac-ninh) là DOM khác hẳn (Liferay) →
        # urlScope khóa host Lào Cai. Key trùng mục ke_khai_links (1.115687).
        "detect": {
            "urlScope": ["laocai.gov.vn"],
            "textIncludes": [
                "thu hồi giấy chứng nhận đã cấp lần đầu không đúng quy định",
                "do người sử dụng đất, chủ sở hữu tài sản gắn liền với đất phát hiện",
            ],
            "headingDisabled": True,
        },
        "label": (
            "[Lào Cai] Thu hồi Giấy chứng nhận đã cấp lần đầu không đúng quy định của pháp luật đất đai do "
            "người sử dụng đất, chủ sở hữu tài sản gắn liền với đất phát hiện và cấp lại Giấy chứng nhận sau "
            "khi thu hồi"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị thu hồi/hủy Giấy chứng nhận quyền sử dụng đất (văn bản kiến nghị việc cấp Giấy "
            "chứng nhận không đúng quy định) — BẢN CHÍNH, có chữ ký/điểm chỉ của chủ sử dụng đất → dòng 1.\n"
            "2. Giấy chứng nhận quyền sử dụng đất ĐÃ CẤP (bản gốc) — quét đủ trang bìa (có số phát hành) và "
            "trang ghi số vào sổ, thửa đất, sơ đồ → dòng 2. Nhiều trang rời đều vào chung dòng này.\n"
            "3. Nếu người khác đi nộp thay: Giấy ủy quyền có công chứng/chứng thực.\n"
            "4. Nếu có: văn bản rà soát của Chi nhánh Văn phòng đăng ký đất đai, giấy tờ của người cùng đứng "
            "tên trên Giấy chứng nhận (văn bản đồng ý, giấy báo tử, đăng ký kết hôn), bản sao Giấy chứng nhận "
            "bị cấp trùng — trợ lý đưa hết xuống 'Giấy tờ khác'.\n"
            "5. CCCD của chủ hồ sơ và của người nộp hồ sơ — KHÔNG đính kèm, chỉ dùng để đọc nhân thân.\n"
            "⚠ MỖI TỆP KHÔNG QUÁ 6 MB — đây là trần của chính cổng Lào Cai, tệp nặng hơn thì cả trợ lý lẫn cán "
            "bộ đính tay đều không đưa lên được. Bản scan màu sổ đỏ rất hay vượt: quét lại ở DPI thấp hơn / "
            "chuyển xám, hoặc tách theo từng trang trước khi tải lên.\n"
            "Chủ hồ sơ = người ĐỨNG ĐƠN (khi nộp thay là Bên A của Giấy ủy quyền), KHÔNG phải người đi nộp và "
            "cũng KHÔNG phải người đang đứng tên trên Giấy chứng nhận bị cấp sai.\n"
            "⚠ Ô 'Họ và tên' và 'Số Căn cước' của khối người nộp là readonly, cổng điền từ tài khoản định "
            "danh — phải đăng nhập đúng tài khoản của NGƯỜI ĐI NỘP. Tỉnh/Phường-Xã/Số nhà của khối này là bắt "
            "buộc và cổng để trống: trợ lý điền theo nơi thường trú của chính người đi nộp đọc được từ CCCD "
            "hoặc Giấy ủy quyền; Di động/Email phải gõ tay.\n"
            "Ô 'Người nộp là chủ hồ sơ' trợ lý KHÔNG tích (tích là cổng chép khối người nộp đè lên khối chủ "
            "hồ sơ) — thông tin chủ hồ sơ đã được điền thẳng từ giấy tờ.\n"
            "Ô 'Về việc' (*) và 'Ghi chú' ở bước Thành phần hồ sơ do cổng điền sẵn — trợ lý KHÔNG ghi đè.\n"
            "Lưu ý số liệu hay lệch giữa các giấy tờ (số thửa, số CCCD, năm sinh ghi trên Giấy chứng nhận cũ) "
            "— cán bộ rà lại Đơn trước khi ký số và nộp."
        ),
    },
    {
        "key": "dang-ky-dat-dai-cap-gcn-lan-dau-to-chuc",
        # Cổng dichvucong.laocai.gov.vn (Nth.FormBuilder — iGate VNPT) — CÙNG form bước 2 CongDan_*/ChuHoSo_*
        # với 1.115651/1.115667/1.115668/1.115671/1.115687 (engine dom-*), mapping theo
        # "Mapping_1.115688_DangKyDatDai_LanDau_LaoCai.xlsx" (2 file HTML: biến thể tổ chức và cá nhân của
        # ô "Đối tượng nộp hồ sơ"). Khác 1.115687: Tỉnh/Phường-Xã khối NGƯỜI NỘP được cổng đổ sẵn theo tài
        # khoản, chỉ "Số nhà/Đường/Tổ/Thôn" và "Di động" là (*) mà để trống.
        # Bước 3 "Thành phần hồ sơ" là bảng PHẲNG nhiều dòng cố định + "Giấy tờ khác" (khớp theo TỪ KHÓA dòng
        # vì cổng render số dòng khác nhau giữa biến thể tổ chức và cá nhân).
        # 1.115688 là mã QUỐC GIA, cổng iGate tỉnh khác cũng dùng đúng mã/đúng tên đó → urlScope khóa host
        # Lào Cai. Key trùng mục ke_khai_links (1.115688).
        "detect": {
            "urlScope": ["laocai.gov.vn"],
            "textIncludes": [
                "đăng ký đất đai, tài sản gắn liền với đất, cấp giấy chứng nhận",
                "lần đầu đối với tổ chức đang sử dụng đất",
            ],
            "headingDisabled": True,
        },
        "label": (
            "[Lào Cai] Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận quyền sử dụng đất, "
            "quyền sở hữu tài sản gắn liền với đất lần đầu đối với tổ chức đang sử dụng đất"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký đất đai, tài sản gắn liền với đất (Mẫu số 15, bản mới ghi Mẫu số 21) — nguồn "
            "chính để điền thân đơn, kèm Danh sách người sử dụng chung thửa đất (Mẫu 15a) hoặc Danh sách "
            "các thửa đất (Mẫu 15b) nếu có.\n"
            "2. Trích lục/mảnh trích đo bản đồ địa chính thửa đất, bản đồ ranh giới - mốc giới sử dụng đất.\n"
            "3. Hồ sơ TỔ CHỨC: Báo cáo kết quả rà soát hiện trạng sử dụng đất (Mẫu 15d/21d), Quyết định "
            "thành lập tổ chức, Quyết định phê duyệt phương án sử dụng đất.\n"
            "4. Hồ sơ HỘ GIA ĐÌNH, CÁ NHÂN: giấy tờ về quyền sử dụng đất theo Điều 137 Luật Đất đai, giấy tờ "
            "nhận thừa kế, Đơn đề nghị xác nhận các thành viên có chung quyền sử dụng đất.\n"
            "5. Nếu có: chứng từ thực hiện nghĩa vụ tài chính, hồ sơ thiết kế/nghiệm thu công trình, Giấy ủy "
            "quyền khi người khác đi nộp thay.\n"
            "6. CCCD của chủ hồ sơ và của người nộp hồ sơ — KHÔNG đính kèm, chỉ dùng để đọc nhân thân.\n"
            "⚠ MỖI TỆP KHÔNG QUÁ 6 MB — trần của chính cổng Lào Cai, tệp nặng hơn thì cả trợ lý lẫn cán bộ "
            "đính tay đều không đưa lên được; bản scan màu bản đồ địa chính rất hay vượt, nên quét lại ở DPI "
            "thấp hơn hoặc tách theo từng giấy tờ.\n"
            "⚠ MỖI TỆP CHỈ ĐÍNH ĐƯỢC VÀO MỘT DÒNG. Hồ sơ thủ tục này hay quét gộp cả Đơn + Danh sách 15a/15b "
            "+ Báo cáo rà soát + Trích lục vào một PDF: trợ lý xếp tệp theo giấy tờ CHÍNH (dòng Đơn đăng ký) "
            "rồi cảnh báo những dòng còn trống — muốn đính đủ từng dòng thì tách tệp theo từng giấy tờ.\n"
            "Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT ở mục 1 Đơn Mẫu 15 (tổ chức thì lấy tên theo Quyết định thành "
            "lập/Trích lục, không lấy tên cũ trước sáp nhập), KHÔNG phải người đi nộp thay. Nhiều người cùng "
            "sử dụng đất thì form chỉ nhận một chủ hồ sơ — người còn lại kê ở Mẫu 15a.\n"
            "⚠ Ô 'Họ và tên' và 'Số Căn cước' của khối người nộp là readonly, cổng điền từ tài khoản định "
            "danh — phải đăng nhập đúng tài khoản của NGƯỜI ĐI NỘP. Ô 'Số nhà/Đường/Tổ/Thôn' và 'Di động' "
            "của khối này là bắt buộc mà cổng để trống: trợ lý điền theo giấy tờ của chính người đi nộp, "
            "không có thì cán bộ gõ tay.\n"
            "Ô 'Người nộp là chủ hồ sơ' trợ lý KHÔNG tích (tích là cổng ép Đối tượng = Cá nhân rồi chép khối "
            "người nộp đè lên khối chủ hồ sơ) — thông tin chủ hồ sơ đã được điền thẳng từ giấy tờ.\n"
            "Lưu ý số liệu hay lệch giữa các giấy tờ (ngày sinh trên Đơn khác Mẫu 15a, số CCCD lệch một chữ "
            "số) — cán bộ đối chiếu CCCD/CSDLQG về dân cư trước khi ký số và nộp."
        ),
    },
    {
        "key": "dang-ky-bien-dong-thoa-thuan-thanh-vien-ho-gia-dinh-theo-ban-an",
        # Cổng dichvucong.laocai.gov.vn (iGate VNPT, maCoQuan=STNMT_LCI) — CÙNG form bước 2 CongDan_*/ChuHoSo_*
        # với 1.115667/1.115668/1.115651 (engine dom-*), mapping theo
        # "mapping_dang-ky-bien-dong_1.115671_LaoCai_MTTQ.xlsx".
        # Bước 3 "Thành phần hồ sơ" chia 5 NHÓM "(1)…(5) Đối với trường hợp…", chọn nhóm theo VĂN BẢN CĂN CỨ
        # (attach/catalog.py) + "Giấy tờ khác"; nhóm (1) không có dòng tiêu đề nên neo vào dòng tiêu đề cột.
        # Cụm tên thủ tục dùng chung với bản Quảng Ninh/Lâm Đồng (1.115839/1.013980) → urlScope khóa host Lào Cai.
        # Cụm "theo thỏa thuận của các thành viên hộ gia đình" KHÔNG có ở trang 1.115668 và ngược lại.
        # Key trùng mục ke_khai_links (1.115671).
        "detect": {
            "urlScope": ["laocai.gov.vn"],
            "textIncludes": ["thỏa thuận của các thành viên hộ gia đình hoặc của vợ và chồng"],
            "headingDisabled": True,
        },
        "label": (
            "[Lào Cai] Đăng ký biến động đối với trường hợp thay đổi quyền sử dụng đất, quyền sở hữu tài sản "
            "gắn liền với đất theo thỏa thuận của các thành viên hộ gia đình hoặc của vợ và chồng; quyền sử "
            "dụng đất xây dựng công trình trên mặt đất phục vụ cho việc vận hành, khai thác sử dụng công trình "
            "ngầm, quyền sở hữu công trình ngầm; bán tài sản, điều chuyển, chuyển nhượng quyền sử dụng đất là "
            "tài sản công; nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất theo kết quả giải "
            "quyết tranh chấp, khiếu nại, tố cáo về đất đai hoặc bản án, quyết định của Tòa án, quyết định thi "
            "hành án, quyết định hoặc phán quyết của Trọng tài thương mại Việt Nam; nhận quyền sử dụng đất, "
            "quyền sở hữu tài sản gắn liền với đất do xử lý tài sản thế chấp đã được đăng ký, bao gồm cả xử lý "
            "khoản nợ có nguồn gốc từ khoản nợ xấu của tổ chức tín dụng, chi nhánh ngân hàng nước ngoài"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 24 ban hành kèm theo Quyết "
            "định số 47/2026/QĐ-UBND) → dòng 1 của nhóm.\n"
            "2. Giấy chứng nhận quyền sử dụng đất ĐÃ CẤP → dòng 2. Quyết định giao đất/cấp Giấy chứng nhận "
            "của chính thửa đất đó cũng đính chung vào dòng này (Đơn mục 3 liệt kê chung một gạch đầu dòng).\n"
            "3. VĂN BẢN CĂN CỨ — đây là thứ quyết định trợ lý tích vào nhóm nào trong 5 nhóm, nên phải có:\n"
            "   • (1) Văn bản thỏa thuận của các thành viên hộ gia đình hoặc của vợ và chồng;\n"
            "   • (2) Văn bản cho phép thay đổi QSDĐ xây dựng công trình trên mặt đất phục vụ công trình ngầm;\n"
            "   • (3) Quyết định/thông báo cho phép bán, ĐIỀU CHUYỂN, chuyển nhượng QSDĐ là tài sản công, biên "
            "bản bàn giao tiếp nhận tài sản công (kèm hợp đồng mua bán tài sản công nếu là trường hợp bán);\n"
            "   • (4) Bản án, quyết định của Tòa án, quyết định thi hành án, biên bản hòa giải thành, phán "
            "quyết của Trọng tài thương mại;\n"
            "   • (5) Hợp đồng thế chấp/chuyển nhượng do xử lý tài sản thế chấp, hợp đồng mua bán tài sản đấu giá.\n"
            "4. Nếu có: bản vẽ tách thửa/hợp thửa (Mẫu số 28), mảnh trích đo bản đồ địa chính, giấy ủy quyền, "
            "GCN đăng ký doanh nghiệp hoặc quyết định về chức năng, nhiệm vụ (chứng minh tư cách pháp nhân).\n"
            "5. CCCD của chủ hồ sơ (cá nhân) và của người nộp hồ sơ — KHÔNG đính kèm, chỉ dùng để đọc nhân thân.\n"
            "⚠ MỖI TỆP KHÔNG QUÁ 6 MB — đây là trần của chính cổng Lào Cai, tệp nặng hơn thì cả trợ lý lẫn "
            "cán bộ đính tay đều không đưa lên được. Bản scan màu Giấy chứng nhận (có sơ đồ thửa đất) và văn "
            "bản nhiều trang rất hay vượt: quét lại ở DPI thấp hơn / chuyển xám, hoặc tách nhỏ theo từng "
            "giấy tờ trước khi tải lên.\n"
            "Chủ hồ sơ = bên ĐỨNG TÊN SAU BIẾN ĐỘNG ở mục 1.a của Đơn (với hồ sơ điều chuyển tài sản công là "
            "cơ quan/tổ chức TIẾP NHẬN trên biên bản bàn giao, không phải tên cũ trên Giấy chứng nhận). Người "
            "ký 'TM. Cơ quan' chỉ là người đại diện.\n"
            "Ô 'Đối tượng nộp hồ sơ' có 4 lựa chọn: Mặt trận Tổ quốc/hội/đoàn thể → 'Tổ chức khác'; UBND, sở, "
            "ban, ngành, đơn vị sự nghiệp → 'Cơ quan nhà nước'; công ty, hợp tác xã, ngân hàng → 'Doanh "
            "nghiệp'. Mã số thuế thường không có trong hồ sơ dạng này, để trống cho cán bộ nhập.\n"
            "⚠ Ô 'Họ và tên' và 'Số Căn cước' của khối người nộp là readonly, cổng điền từ tài khoản định "
            "danh — phải đăng nhập đúng tài khoản của NGƯỜI ĐI NỘP. Ngày/nơi cấp căn cước lấy được từ mục 1.d "
            "của Đơn khi hồ sơ chưa có bản sao CCCD; ngày sinh/giới tính/dân tộc thì phải có CCCD mới điền.\n"
            "Thành phần hồ sơ: trợ lý tự tích checkbox + đính kèm từng dòng trong ĐÚNG MỘT nhóm; giấy tờ không "
            "có dòng trong nhóm đó (vd mảnh trích đo khi hồ sơ thuộc nhóm (3)) xuống 'Giấy tờ khác'.\n"
            "Ô 'Về việc' (*) và 'Ghi chú' ở bước Thành phần hồ sơ do cổng điền sẵn — trợ lý KHÔNG ghi đè."
        ),
    },
    {
        "key": "chuyen-muc-dich-su-dung-dat-lao-cai",
        # Cổng dichvucong.laocai.gov.vn (iGate VNPT, maCoQuan=STNMT_LCI) — CÙNG form bước 2 CongDan_*/ChuHoSo_*
        # với 1.115667/1.115668. Đính kèm fixed-slot theo 4 nhóm "(1)…(4) Hồ sơ đề nghị…" chọn theo mẫu đơn
        # (attach/catalog.py) + "Giấy tờ khác". Cụm tên cũng có ở Lâm Đồng/Quảng Ninh → urlScope khóa host Lào Cai.
        # Key trùng mục ke_khai_links (1.115651).
        "detect": {
            "urlScope": ["laocai.gov.vn"],
            "textIncludes": ["chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất"],
            "headingDisabled": True,
        },
        "label": (
            "[Lào Cai] Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia hạn sử dụng đất khi hết thời "
            "hạn sử dụng đất; điều chỉnh thời hạn sử dụng đất của dự án đầu tư đối với trường hợp quy định tại khoản "
            "1 Điều 175 Luật Đất đai năm 2024"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị: Mẫu số 02 (chuyển mục đích), 03 (chuyển hình thức), 17 (gia hạn) hoặc 18 (điều chỉnh "
            "thời hạn dự án).\n"
            "2. Giấy chứng nhận quyền sử dụng đất; quyết định giao đất/cho thuê đất/cho phép chuyển mục đích (nếu có).\n"
            "3. Nếu có: mảnh đo đạc chỉnh lý bản đồ địa chính, văn bản về thời hạn dự án đầu tư, GCN đăng ký doanh "
            "nghiệp, giấy ủy quyền.\n"
            "4. CCCD của người nộp hồ sơ (và của chủ hồ sơ nếu là cá nhân).\n"
            "Chủ hồ sơ = người sử dụng đất đứng tên Đơn (tổ chức: tên + mã số thuế). Người nộp: chỉ bổ sung nhân thân "
            "từ CCCD của chính người nộp; số điện thoại/email trên Đơn điền cho chủ hồ sơ.\n"
            "Thành phần hồ sơ: tự chọn nhóm (1)-(4) theo mẫu đơn, tích + đính kèm từng dòng; bản đồ riêng, GCN đăng "
            "ký doanh nghiệp, giấy ủy quyền vào 'Giấy tờ khác'. Tệp không đính được sẽ được bỏ qua. CCCD không đính kèm."
        ),
    },
    {
        "key": "chuyen-muc-dich-su-dung-dat-khoan-1-dieu-175",
        # Cổng dichvucong.laocai.gov.vn (Nth.FormBuilder — iGate VNPT) — bản nộp ở PHƯỜNG/XÃ của cụm thủ tục
        # "chuyển mục đích / chuyển hình thức / gia hạn / điều chỉnh thời hạn". TÊN TRÙNG Y HỆT 1.115651
        # (bản nộp ở Sở, key chuyen-muc-dich-su-dung-dat-lao-cai) nên nhãn ghi kèm MÃ 1.115679 để cán bộ tìm
        # và phân biệt được; hai thủ tục để hai pipeline riêng vì bảng bước 3 khác cấu trúc.
        # Bước 2 dùng CÙNG bộ ô CongDan_*/ChuHoSo_* với 1.115651/1.115667/1.115671/1.115687/1.115688 (engine
        # dom-*), mapping theo "Mapping_CMDSDD_1.115679_LaoCai_CaNhan_ToChuc.xlsx"; khác 1.115651 ở chỗ SÁU ô
        # của khối NGƯỜI NỘP là (*) mà cổng chỉ đổ theo tài khoản → pipeline điền thêm giới tính, dân tộc,
        # cụm địa chỉ và di động.
        # Bước 3 "Thành phần hồ sơ" in MỘT LẦN cả bốn nhóm, tiêu đề nhóm đánh CHỮ CÁI "a) b) c) d)" (1.115651
        # đánh "(1)…(4)") → attach/catalog.py khớp dòng theo từ khóa, neo vùng bằng tiêu đề cột hoặc tiêu đề
        # nhóm d).
        # NHẬN DIỆN THEO MÃ THỦ TỤC. Tên thủ tục trùng y hệt 1.115651 nên không tách được bằng tên; nhưng
        # cổng in MÃ ngay trong banner "thủ tục đã chọn" của cả luồng nộp hồ sơ:
        #     <section id="thu-tuc-da-chon-wrapper"><h4><span class="label label-warning">Một phần</span>
        #       1.115679 - Lào Cai - Chuyển mục đích sử dụng đất; … Khoản 1 Điều 175 Luật Đất đai năm 2024
        # <h4> là chữ HIỂN THỊ nên nằm trong document.body.innerText (nguồn của signals.bodyText), và banner
        # này có ở MỌI bước của luồng — nhờ vậy bước 2 (nhập thông tin) lẫn bước 3 (thành phần hồ sơ) đều
        # nhận đúng, không phải dựa vào cấu trúc bảng đính kèm nữa. URL chỉ có sid nên không dùng urlIncludes
        # được. textPriority để thắng rule theo TÊN của 1.115651 (không có textPriority) ngay ở vòng ưu tiên.
        # Mã là chuỗi ngắn nên urlScope khoá host Lào Cai vẫn bắt buộc.
        # Key trùng mục ke_khai_links (1.115679).
        "detect": {
            "urlScope": ["laocai.gov.vn"],
            "textIncludes": ["1.115679"],
            "textPriority": True,
            "headingDisabled": True,
        },
        "label": (
            "[Lào Cai] Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia hạn sử dụng đất khi "
            "hết thời hạn sử dụng đất; điều chỉnh thời hạn sử dụng đất của dự án đầu tư đối với trường hợp "
            "quy định tại Khoản 1 Điều 175 Luật Đất đai năm 2024 (1.115679 - cho Phường/Xã)"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Thủ tục này nộp tại UBND PHƯỜNG/XÃ (mã 1.115679). Bản cùng tên nộp ở Sở là mã 1.115651 — chọn "
            "nhầm là sai cơ quan tiếp nhận.\n"
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị: Mẫu số 02 (chuyển mục đích), Mẫu số 03 (chuyển hình thức) hoặc Mẫu số 17 (gia "
            "hạn) ban hành kèm Quyết định số 47/2026/QĐ-UBND — nguồn chính để điền thân đơn.\n"
            "2. Giấy chứng nhận quyền sử dụng đất (sổ đỏ/sổ hồng) của thửa đất xin chuyển mục đích.\n"
            "3. Quyết định giao đất/cho thuê đất/cho phép chuyển mục đích và quyết định điều chỉnh (nếu có).\n"
            "4. Nếu có: Giấy uỷ quyền khi người khác đi nộp thay, hồ sơ nghĩa vụ tài chính (phiếu chuyển "
            "thông tin, thông báo thuế, giấy nộp tiền), hồ sơ đo đạc chỉnh lý thửa đất, văn bản về thời hạn "
            "hoạt động của dự án đầu tư.\n"
            "5. CCCD của chủ hồ sơ và của người đi nộp — KHÔNG đính kèm, chỉ dùng để đọc nhân thân.\n"
            "⚠ MỖI TỆP KHÔNG QUÁ 6 MB — trần của chính cổng Lào Cai. Cụm nghĩa vụ tài chính + đo đạc quét "
            "gộp rất hay vượt (hồ sơ mẫu 14 trang nặng 6,33 MB): tách làm hai tệp hoặc quét lại ở DPI thấp "
            "hơn, tệp vượt trần thì cả trợ lý lẫn cán bộ đính tay đều không đưa lên được.\n"
            "Chủ hồ sơ = NGƯỜI SỬ DỤNG ĐẤT đứng tên mục 1 của Đơn, KHÔNG phải người đi nộp thay. Hai vợ "
            "chồng cùng đứng tên thì form chỉ có một ô họ tên — nhập người đứng đầu mục 1, người còn lại đã "
            "có trong Đơn và Giấy chứng nhận đính kèm.\n"
            "⚠ Ô 'Họ và tên' và 'Số Căn cước' của khối người nộp là readonly, cổng điền từ tài khoản định "
            "danh — phải đăng nhập đúng tài khoản của NGƯỜI ĐI NỘP. Giới tính, Dân tộc, Tỉnh/Phường-Xã, Số "
            "nhà và Di động của khối này là (*) mà cổng để trống: trợ lý điền theo giấy tờ của chính người "
            "đi nộp, không có thì cán bộ gõ tay. Riêng ô Giới tính không có lựa chọn trống nên luôn hiện "
            "sẵn 'Nữ' — hồ sơ của nam giới phải kiểm lại ô này trước khi nộp.\n"
            "Ô 'Người nộp là chủ hồ sơ' trợ lý KHÔNG tích (tích là cổng ép Đối tượng = Cá nhân rồi chép khối "
            "người nộp đè lên khối chủ hồ sơ) — thông tin chủ hồ sơ đã được điền thẳng từ giấy tờ.\n"
            "Thành phần hồ sơ: trợ lý tích và đính Đơn Mẫu số 02 vào dòng của nhóm a); Giấy chứng nhận và "
            "Quyết định cho phép chuyển mục đích vào hai dòng CUỐI BẢNG theo ảnh hướng dẫn của bộ phận một "
            "cửa; giấy uỷ quyền, hồ sơ nghĩa vụ tài chính, hồ sơ đo đạc xuống 'Giấy tờ khác'. Mỗi giấy tờ "
            "chỉ tải ở MỘT dòng.\n"
            "Ô 'Về việc' (*) và 'Ghi chú' ở bước Thành phần hồ sơ do cổng điền sẵn — trợ lý KHÔNG ghi đè.\n"
            "Lưu ý số liệu hay lệch giữa các giấy tờ (Đơn ghi 'Tổ 39', Giấy uỷ quyền ghi 'Tổ dân phố số 9 "
            "Xuân Tăng', Giấy chứng nhận 2018 còn địa danh cũ 'Tổ 24, phường Bình Minh'; Giấy chứng nhận cũ "
            "ghi CMND 9 số khác số CCCD hiện tại) — cán bộ đối chiếu CCCD/CSDLQG về dân cư trước khi ký số "
            "và nộp."
        ),
    },
    {
        "key": "dang-ky-cap-gcn-dien-tich-tang-them-nhan-chuyen-quyen-mot-phan-thua",
        # Cổng dichvucong.laocai.gov.vn (iGate VNPT, maCoQuan=STNMT_LCI) — bước 2 dùng CÙNG bộ ô
        # CongDan_*/ChuHoSo_* với 1.115667/1.115668 (engine dom-*), mapping theo
        # "Mapping_DVC_LaoCai_Buoc2_TranThiMinhHue.xlsx".
        # Bước 3 "Thành phần hồ sơ" là bảng PHẲNG 5 dòng (attach/planner.py), khớp ô theo slotIndex +
        # tích checkbox từng dòng; giấy tờ không có dòng riêng xuống "Giấy tờ khác".
        # Cụm "diện tích tăng thêm do thay đổi ranh giới…" cũng có ở bản Lâm Đồng (1.116356, form
        # Form.io hoàn toàn khác) → urlScope khóa host Lào Cai; cụm thứ hai ("nhận chuyển quyền sử
        # dụng một phần thửa đất…") là phần CHỈ 1.115694 có, không trùng thủ tục Lào Cai nào khác.
        # Key trùng mục ke_khai_links (1.115694).
        "detect": {
            "urlScope": ["laocai.gov.vn"],
            "textIncludes": [
                "diện tích tăng thêm do thay đổi ranh giới so với giấy chứng nhận đã cấp",
                "nhận chuyển quyền sử dụng một phần thửa đất đã được cấp giấy chứng nhận",
            ],
            "headingDisabled": True,
        },
        "label": (
            "[Lào Cai] Đăng ký, cấp Giấy chứng nhận đối với thửa đất có diện tích tăng thêm do thay đổi "
            "ranh giới so với Giấy chứng nhận đã cấp đối với trường hợp thửa đất gốc đã có Giấy chứng "
            "nhận, phần diện tích đất tăng thêm do nhận chuyển quyền sử dụng một phần thửa đất đã được "
            "cấp Giấy chứng nhận"
        ),
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đăng ký biến động đất đai, tài sản gắn liền với đất (Mẫu số 24) → dòng 1.\n"
            "2. Giấy chứng nhận đã cấp cho thửa đất GỐC → dòng 2.\n"
            "3. Hợp đồng/văn bản chuyển quyền phần diện tích tăng thêm đã công chứng, kèm phụ lục và "
            "biên bản bàn giao; hóa đơn, văn bản xác nhận đã thanh toán → cùng dòng 3.\n"
            "4. Mảnh trích đo/chỉnh lý bản đồ địa chính thửa đất → dòng 4.\n"
            "5. Giấy ủy quyền/văn bản về việc đại diện (nếu nộp thay) → dòng 5.\n"
            "6. CCCD của chủ hồ sơ và của người nộp; nếu có: giấy chứng nhận kết hôn, GCN đăng ký doanh "
            "nghiệp, tờ khai lệ phí trước bạ, tờ khai thuế → xuống 'Giấy tờ khác'.\n"
            "Chủ hồ sơ = bên NHẬN chuyển quyền đứng tên mục 1 của Đơn, KHÔNG phải người đứng tên trên "
            "Giấy chứng nhận đã cấp (GCN có thể vẫn mang tên chủ đầu tư/bên chuyển quyền). Hai vợ chồng "
            "cùng nhận thì điền theo người đứng tên đầu trên Đơn — bước 2 không có ô cho đồng sở hữu.\n"
            "Ngày sinh/số căn cước/ngày cấp lấy theo CCCD khi đơn hoặc hợp đồng ghi lệch.\n"
            "⚠ Ô 'Họ và tên' và 'Số Căn cước' của khối người nộp là readonly, cổng điền từ tài khoản "
            "định danh — phải đăng nhập đúng tài khoản của NGƯỜI ĐI NỘP. Trợ lý chỉ điền nhân thân người "
            "nộp khi hồ sơ có giấy tờ của CHÍNH người đó (khớp số căn cước, hoặc khớp họ tên tài khoản); "
            "Tỉnh/Phường-Xã/Địa chỉ/Di động còn thiếu sẽ được cảnh báo để cán bộ nhập tay, KHÔNG lấy của "
            "chủ hồ sơ.\n"
            "Đính kèm: trợ lý tự tích dòng và bơm tệp theo loại giấy tờ CHÍNH của từng tệp; MỖI TỆP chỉ "
            "vào ĐÚNG MỘT dòng. Hồ sơ quét gộp (tờ khai thuế nằm chung file với Đơn, CCCD nằm chung file "
            "với Giấy ủy quyền) thì phần đi kèm nằm cùng dòng với giấy tờ chính — trợ lý cảnh báo để cán "
            "bộ đề nghị tách tệp nếu nơi tiếp nhận yêu cầu. Dòng 'Mảnh trích đo' thường không có trong "
            "hồ sơ dân nộp; trợ lý nhắc chứ không tự tích.\n"
            "Ô 'Về việc' (*) ở bước Thành phần hồ sơ do cổng điền sẵn tên thủ tục — trợ lý KHÔNG ghi đè."
        ),
    },
    {
        "key": "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep",
        # Cổng dichvucong.laocai.gov.vn (iGate VNPT, Nth.FormBuilder) — bước 2 dùng CÙNG bộ ô
        # CongDan_*/ChuHoSo_* với 1.115667/1.115668/1.115694 (engine dom-*), mapping theo
        # "Mapping_XN_thoi_han_SDD_nong_nghiep_LaoCai.xlsx".
        # Bước 3 "Thành phần hồ sơ" là bảng PHẲNG 2 dòng (attach/planner.py), khớp ô theo slotIndex +
        # tích checkbox từng dòng; giấy tờ không có dòng riêng xuống "Giấy tờ khác".
        # urlScope khóa host Lào Cai vì mã QG 1.115677 dùng chung cho nhiều cổng iGate tỉnh khác.
        # Key trùng mục ke_khai_links (1.115677).
        "detect": {
            "urlScope": ["laocai.gov.vn"],
            "textIncludes": ["xác nhận tiếp tục sử dụng đất nông nghiệp"],
            "headingDisabled": True,
        },
        "label": "[Lào Cai] Xác nhận tiếp tục sử dụng đất nông nghiệp",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên:\n"
            "1. Đơn đề nghị xác nhận lại thời hạn sử dụng đất nông nghiệp (Mẫu số 39 ban hành kèm theo "
            "Quyết định số 47/2026/QĐ-UBND) → dòng 1.\n"
            "2. Giấy chứng nhận quyền sử dụng đất ĐÃ CẤP → dòng 2. File này thường quét gộp luôn mảnh "
            "trích đo địa chính ở trang cuối — cứ để nguyên một tệp, trợ lý nhắc để cán bộ tự quyết có "
            "cần tách hay không.\n"
            "3. Nếu có: mảnh trích đo nộp riêng, giấy ủy quyền, CCCD/giấy chứng nhận kết hôn → xuống "
            "'Giấy tờ khác'. CCCD không thuộc thành phần hồ sơ của thủ tục này, chỉ đính khi nơi tiếp "
            "nhận yêu cầu.\n"
            "Chủ hồ sơ = người sử dụng đất đứng tên ĐẦU TIÊN ở mục 1 của Đơn Mẫu số 39. Hai vợ chồng "
            "cùng sử dụng đất thì điền theo người đứng tên đầu — bước 2 không có ô cho đồng sử dụng "
            "đất; việc VỢ/CHỒNG ký mục 'Người làm đơn' KHÔNG làm đổi chủ hồ sơ.\n"
            "Ngày sinh/số căn cước/ngày cấp lấy theo CCCD. Giấy chứng nhận cũ chỉ in số CMND 9 số — "
            "trợ lý luôn chọn số căn cước 12 số. Đơn Mẫu số 39 không có ngày sinh/giới tính/dân tộc, "
            "không nộp kèm CCCD thì các ô đó để trống cho cán bộ nhập.\n"
            "⚠ Ô 'Họ và tên' và 'Số Căn cước' của khối người nộp là readonly, cổng điền từ tài khoản "
            "định danh — phải đăng nhập đúng tài khoản của NGƯỜI ĐI NỘP. Trợ lý chỉ điền nhân thân "
            "người nộp khi hồ sơ có giấy tờ của CHÍNH người đó. Địa chỉ/điện thoại ở mục 2 của Đơn là "
            "của cả hộ nên chỉ dùng lại cho người nộp khi người đăng nhập có tên ở mục 1; ô (*) còn "
            "thiếu sẽ được cảnh báo để cán bộ nhập tay.\n"
            "Ô 'Về việc' (*) và 'Ghi chú' ở bước Thành phần hồ sơ do cổng điền sẵn — trợ lý KHÔNG ghi đè."
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
            "3. Nếu có: bản sao quyết định/danh sách thôi hưởng trợ cấp BHXH.\n"
            "Bước thành phần hồ sơ: cổng chỉ còn ĐÚNG MỘT dòng (Tờ khai Mẫu số 02 - NĐ 176/2025) nên "
            "MỌI file đều được đính vào dòng đó; file không phải Tờ khai vẫn đính kèm nhưng có cảnh báo."
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
            "3. Nếu có: bản sao quyết định/danh sách thôi hưởng trợ cấp BHXH.\n"
            "Bước thành phần hồ sơ: cổng chỉ còn ĐÚNG MỘT dòng (Tờ khai Mẫu số 02 - NĐ 176/2025) nên "
            "MỌI file đều được đính vào dòng đó; file không phải Tờ khai vẫn đính kèm nhưng có cảnh báo."
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
            "1. Văn bản đề nghị Mẫu số 01 (Nghị định 176/2025/NĐ-CP).\n"
            "2. CCCD của người nộp/chủ hồ sơ.\n"
            "Hệ thống lấy chủ hồ sơ từ mục thông tin người đề nghị cấp/hưởng trợ cấp hưu trí xã hội.\n"
            "Bước thành phần hồ sơ: cổng chỉ còn ĐÚNG MỘT dòng nên MỌI file đều được đính vào dòng đó; "
            "file không phải Văn bản đề nghị vẫn được đính kèm nhưng có cảnh báo để cán bộ soát."
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
        # Cùng form Form.io "Thi tuyển công chức" nhưng chạy trên cổng Một cửa Bộ Nội vụ
        # (motcua.moha.gov.vn, VNPT iGate). ĐẶT TRƯỚC bản gốc (không urlScope): trên motcua điểm
        # textPriority bằng nhau → so sánh `>` strict cho entry ĐỨNG TRƯỚC thắng ⇒ bản scoped này thắng.
        # urlScope khóa cổng nên KHÔNG rò rỉ sang cổng khác (bản gốc vẫn thắng ở mọi nơi ≠ motcua).
        "key": "thi-tuyen-cong-chuc-mot-cua-moha",
        "detect": {
            "urlScope": ["motcua.moha.gov.vn"],
            "textIncludes": ["Thi tuyển công chức"],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "[Một cửa Bộ nội vụ] Thi tuyển công chức",
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
        "key": "dang-ky-hanh-nghe",
        # Mã TTHC 1.012275 (khám bệnh, chữa bệnh — QĐ 2976/QĐ-BYT), nộp tại SỞ Y tế: ke_khai_links đặt
        # selectSo, phải tích "Sở" ở khối "Chọn cơ quan thực hiện" mới vào được form. URL trang chi tiết
        # DVCQG được with_ke_khai_detect_urls ghép thêm vào urlIncludes. Cụm tên ngắn và dễ trùng
        # ("đăng ký hành nghề công chứng"...) nên KHÔNG bật textPriority và tắt heading (heading so
        # startsWith sẽ ăn nhầm tên dài hơn). CHƯA có pipeline điền — mới bật tìm kiếm + nhận diện.
        "detect": {
            "urlIncludes": ["maThuTuc=1.012275"],
            "textIncludes": ["Đăng ký hành nghề"],
            "headingDisabled": True,
        },
        "label": "Đăng ký hành nghề",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
    },
    {
        "key": "cong-bo-co-so-du-dieu-kien-tiem-chung",
        # Mã TTHC 2.000655, nộp tại SỞ Y tế (ke_khai_links đặt selectSo). Form.io trên hệ thống TTHC Bộ Y tế,
        # engine fillFormStandard dom-* + attach attp-row (bảng 1 dòng Văn bản thông báo). Phần I chỉ bổ sung
        # khi có CCCD khớp tài khoản đăng nhập (extension gửi formContext); Phần II theo tờ Thông báo.
        "detect": {
            "textIncludes": [
                "công bố cơ sở đủ điều kiện tiêm chủng",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Công bố cơ sở đủ điều kiện tiêm chủng",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên để tự động điền:\n"
            "1. Thông báo cơ sở đủ điều kiện tiêm chủng (mẫu Phụ lục NĐ 104/2016/NĐ-CP) — đã ký, đóng dấu. Có "
            "thể tải cả file gộp Tờ trình + Danh sách cơ sở + Thông báo.\n"
            "2. CCCD của NGƯỜI NỘP (tài khoản VNeID đang đăng nhập) — có thẻ này mới bổ sung được ngày sinh, "
            "giới tính, ngày cấp ở mục Thông tin người nộp hồ sơ.\n"
            "3. CCCD của NGƯỜI ĐỨNG ĐẦU CƠ SỞ ghi trên Thông báo (bỏ qua nếu trùng người nộp) — để điền ngày "
            "sinh, giới tính, số CCCD ở mục Thông tin chủ hồ sơ.\n"
            "Không cần chọn trước vai trò giấy tờ; hệ thống tự phân biệt theo nội dung OCR.\n"
            "Extension bỏ tích 'Người nộp hồ sơ là chủ hồ sơ' và điền chủ hồ sơ theo Thông báo (người đứng "
            "đầu, địa chỉ, điện thoại, email của cơ sở).\n"
            "Bước đính kèm: Thông báo (kèm Tờ trình/Danh sách nếu có) được tick vào dòng 'Văn bản thông báo đủ "
            "điều kiện tiêm chủng', loại '1 Bản chính' (CCCD chỉ dùng ở bước thông tin)."
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
            "ĐỐI TƯỢNG (huân/huy chương, kỷ niệm chương, thẻ hội viên hội chính sách, người có công, "
            "miễn giảm tiền thuê) → dòng 'Giấy tờ chứng minh đối tượng… và giấy tờ chứng minh thuộc đối "
            "tượng được miễn, giảm tiền thuê nhà ở xã hội (nếu có)'; giấy chứng minh ĐIỀU KIỆN (thu nhập, "
            "hộ nghèo, thực trạng nhà ở) → dòng 'Giấy tờ chứng minh điều kiện được hưởng chính sách'; "
            "CCCD → dòng 'Trường hợp thuê nhà ở xã hội' (đều Bản chính). Tài liệu chưa nhận ra loại cũng "
            "được đính vào dòng 'chứng minh đối tượng… (nếu có)' kèm cảnh báo — không bỏ sót tệp nào."
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
        "key": "cap-gcnkncm-cccm",
        # Cổng Bộ Xây dựng dvc.moc.gov.vn (Form.io apply-online) — CÙNG engine fill standard dom-* +
        # đính kèm attp-row với lien_van/chat_ha_cay_xanh. URL chỉ ObjectId → DETECT THEO TÊN (text) để
        # bền khi id form đổi theo đơn vị. ⚠ Phần II HTML là biểu mẫu con nhúng SAI (khu neo đậu) — bỏ.
        "detect": {
            "urlScope": ["dvc.moc.gov.vn"],
            "textIncludes": [
                "Cấp, cấp lại, chuyển đổi giấy chứng nhận khả năng chuyên môn, chứng chỉ chuyên môn",
            ],
            "headingDisabled": True,
            "textPriority": True,
        },
        "label": "Cấp, cấp lại, chuyển đổi giấy chứng nhận khả năng chuyên môn, chứng chỉ chuyên môn",
        "mode": "agent",
        "hasAttachmentStep": True,
        "roles": [],
        "useDangKyBy": False,
        "uploadHint": (
            "Giấy tờ cần tải lên (thuyền viên xin cấp/cấp lại/chuyển đổi GCNKNCM, CCCM):\n"
            "1. Đơn đề nghị theo mẫu (Mauon) đã ký — nguồn chính về đề nghị + nhân thân.\n"
            "2. Giấy chứng nhận khả năng chuyên môn/Chứng chỉ chuyên môn (GCNKNCM) đang xin cấp lại.\n"
            "3. Giấy chứng nhận sức khỏe do cơ sở y tế có thẩm quyền cấp.\n"
            "4. 02 ảnh màu 2x3 nền trắng (người dân tự chuẩn bị).\n"
            "5. CCCD của người nộp (nguồn điền nhân thân; nếu là tổ chức/hộ KD thì thêm Giấy chứng nhận "
            "đăng ký doanh nghiệp/hộ kinh doanh).\n"
            "Điền 'Thông tin chung' (họ tên, ngày sinh, giới tính, số/ngày/nơi cấp CCCD, SĐT, Tỉnh/Phường-"
            "Xã nơi cư trú) và khối 'Cá nhân/Tổ chức đề nghị'. Ưu tiên địa chỉ mới nhất trong Đơn đề nghị.\n"
            "Đính kèm tự động vào 4 dòng (Đơn/GCNKNCM/Giấy sức khỏe/Ảnh); CCCD chỉ dùng để điền."
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
    "khai-tu-lien-thong": khai_tu_lien_thong_process,
    "khai-tu-dang-ky-lai": khai_tu_dang_ky_lai_process,
    "thay-doi-cai-chinh-ho-tich": thay_doi_ho_tich_process,
    "xac-nhan-tinh-trang-hon-nhan": xac_nhan_tthn_process,
    "dinh-chinh-sai-sot": dinh_chinh_sai_sot_process,
    "dinh-chinh-sai-sot-bac-ninh": dinh_chinh_sai_sot_bac_ninh_process,
    "dinh-chinh-sai-sot-lam-dong": dinh_chinh_sai_sot_lam_dong_process,
    "giao-thue-dat-lao-cai": giao_thue_dat_lao_cai_process,
    "dang-ky-dat-dai-lan-dau-lam-dong": dang_ky_dat_dai_lan_dau_lam_dong_process,
    "chuyen-muc-dich-su-dung-dat-lam-dong": chuyen_muc_dich_su_dung_dat_lam_dong_process,
    "dang-ky-dien-tich-tang-them-lam-dong": dang_ky_dien_tich_tang_them_lam_dong_process,
    "cung-cap-thong-tin-quy-hoach": cung_cap_thong_tin_quy_hoach_process,
    "cap-gcn-diem-tro-choi-dien-tu-cong-cong": cap_gcn_diem_tro_choi_dien_tu_process,
    "giao-thue-chuyen-muc-dich-dat-bac-ninh": giao_thue_chuyen_muc_dich_dat_bac_ninh_process,
    "giao-thue-chuyen-muc-dich-dat-ninh-binh": giao_thue_chuyen_muc_dich_dat_ninh_binh_process,
    "giao-thue-chuyen-muc-dich-dat-quang-ngai": giao_thue_chuyen_muc_dich_dat_quang_ngai_process,
    "dang-ky-dat-dai-lan-dau-quang-ngai": dang_ky_dat_dai_lan_dau_quang_ngai_process,
    "xac-dinh-lai-dien-tich-dat-o-quang-ngai": xac_dinh_lai_dien_tich_dat_o_quang_ngai_process,
    "dinh-chinh-sai-sot-quang-ngai": dinh_chinh_sai_sot_quang_ngai_process,
    "dinh-chinh-gcn-da-cap-ninh-binh": dinh_chinh_gcn_da_cap_ninh_binh_process,
    "dinh-chinh-da-cap-ninh-binh": dinh_chinh_da_cap_ninh_binh_process,
    "dang-ky-dat-dai-lan-dau-ninh-binh": dang_ky_dat_dai_lan_dau_ninh_binh_process,
    "cap-doi-gcn-ninh-binh": cap_doi_gcn_ninh_binh_process,
    "dang-ky-bien-dong-dat-dai-ninh-binh": dang_ky_bien_dong_dat_dai_ninh_binh_process,
    "dang-ky-dat-dai-lan-dau-bac-ninh": dang_ky_dat_dai_lan_dau_bac_ninh_process,
    "thu-hoi-gcn-cap-sai-bac-ninh": thu_hoi_gcn_cap_sai_bac_ninh_process,
    "dang-ky-bien-dong-chuyen-nhuong-bac-ninh": dang_ky_bien_dong_chuyen_nhuong_bac_ninh_process,
    "dang-ky-bien-dong-dat-dai-bac-ninh": dang_ky_bien_dong_dat_dai_bac_ninh_process,
    "xoa-dang-ky-bien-phap-bao-dam-bac-ninh": xoa_dk_bpbd_bac_ninh_process,
    "dien-thong-tin-tai-khoan-bac-ninh": dien_tk_bac_ninh_process,
    "dang-ky-bien-phap-bao-dam-bac-ninh": dang_ky_bpbd_bac_ninh_process,
    "ho-tro-nguoi-cao-tuoi-bac-ninh": ho_tro_nguoi_cao_tuoi_bac_ninh_process,
    "ho-tro-chi-phi-hoa-tang-bac-ninh": ho_tro_chi_phi_hoa_tang_bac_ninh_process,
    "ho-tro-chi-phi-hoa-tang-quang-ngai": ho_tro_chi_phi_hoa_tang_quang_ngai_process,
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
    "dieu-chinh-quyet-dinh-giao-dat-lao-cai": dieu_chinh_giao_dat_lao_cai_process,
    "dang-ky-dat-dai-lan-dau": dang_ky_dat_dai_process,
    "dang-ky-dat-dai-tai-san-lan-dau-nguoi-o-nuoc-ngoai": dang_ky_dat_dai_tai_san_process,
    "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai": cap_gcn_nhan_chuyen_nhuong_process,
    "dang-ky-bien-dong-dat-dai-lao-cai": dang_ky_quyen_su_dung_dat_lao_cai_process,
    "dang-ky-bien-dong-thoa-thuan-thanh-vien-ho-gia-dinh-theo-ban-an": dang_ky_bien_dong_lao_cai_process,
    "thu-hoi-gcn-cap-lan-dau-khong-dung-quy-dinh-cap-lai": thu_hoi_gcn_cap_lan_dau_lao_cai_process,
    "dang-ky-dat-dai-cap-gcn-lan-dau-to-chuc": dk_dat_dai_gan_tai_san_lao_cai_process,
    "chuyen-muc-dich-su-dung-dat-lao-cai": chuyen_doi_md_sd_dat_lao_cai_process,
    "chuyen-muc-dich-su-dung-dat-khoan-1-dieu-175": chuyen_md_sd_dat_phuong_xa_lao_cai_process,
    "dang-ky-cap-gcn-dien-tich-tang-them-nhan-chuyen-quyen-mot-phan-thua":
        dk_giay_cn_thua_dat_dien_tich_tang_them_process,
    "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep": xac_nhan_tiep_tuc_dat_nong_nghiep_process,
    "ho-tro-mai-tang": ho_tro_mai_tang_process,
    "ho-tro-mai-tang-huu-tri-xa-hoi": ho_tro_mai_tang_huu_tri_xa_hoi_process,
    "dieu-chinh-huu-tri-xa-hoi": dieu_chinh_huu_tri_xa_hoi_process,
    "mai-tang-dan-cong-hoa-tuyen": mai_tang_dan_cong_process,
    "xac-dinh-muc-do-khuyet-tat": khuyet_tat_process,
    "xet-tuyen-vien-chuc": xet_tuyen_vien_chuc_process,
    "xet-tuyen-vien-chuc-lai-chau": xet_tuyen_vien_chuc_lai_chau_process,
    "xet-tuyen-cong-chuc": xet_tuyen_cong_chuc_process,
    "thi-tuyen-cong-chuc": thi_tuyen_cong_chuc_process,
    "thi-tuyen-cong-chuc-mot-cua-moha": thi_tuyen_cong_chuc_mot_cua_moha_process,
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
    "cong-bo-co-so-du-dieu-kien-tiem-chung": cong_bo_du_dk_tiem_chung_process,
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
    "cap-gcnkncm-cccm": cap_gcnkncm_cccm_process,
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
    "dang-ky-cap-gcn-nhan-chuyen-nhuong-du-an-bat-dong-san-lao-cai": cap_gcn_nhan_chuyen_nhuong_attach,
    "dang-ky-bien-dong-dat-dai-lao-cai": dang_ky_quyen_su_dung_dat_lao_cai_attach,
    "dang-ky-bien-dong-thoa-thuan-thanh-vien-ho-gia-dinh-theo-ban-an": dang_ky_bien_dong_lao_cai_attach,
    "thu-hoi-gcn-cap-lan-dau-khong-dung-quy-dinh-cap-lai": thu_hoi_gcn_cap_lan_dau_lao_cai_attach,
    "dang-ky-dat-dai-cap-gcn-lan-dau-to-chuc": dk_dat_dai_gan_tai_san_lao_cai_attach,
    "chuyen-muc-dich-su-dung-dat-lao-cai": chuyen_doi_md_sd_dat_lao_cai_attach,
    "chuyen-muc-dich-su-dung-dat-khoan-1-dieu-175": chuyen_md_sd_dat_phuong_xa_lao_cai_attach,
    "dang-ky-cap-gcn-dien-tich-tang-them-nhan-chuyen-quyen-mot-phan-thua":
        dk_giay_cn_thua_dat_dien_tich_tang_them_attach,
    "xac-nhan-tiep-tuc-su-dung-dat-nong-nghiep": xac_nhan_tiep_tuc_dat_nong_nghiep_attach,
    "dang-ky-dat-dai-tai-san-lan-dau-nguoi-o-nuoc-ngoai": dang_ky_dat_dai_tai_san_attach,
    "dinh-chinh-sai-sot-bac-ninh": dinh_chinh_sai_sot_bac_ninh_attach,
    "dinh-chinh-sai-sot-lam-dong": dinh_chinh_sai_sot_lam_dong_attach,
    "dang-ky-dat-dai-lan-dau-lam-dong": dang_ky_dat_dai_lan_dau_lam_dong_attach,
    "chuyen-muc-dich-su-dung-dat-lam-dong": chuyen_muc_dich_su_dung_dat_lam_dong_attach,
    "dang-ky-dien-tich-tang-them-lam-dong": dang_ky_dien_tich_tang_them_lam_dong_attach,
    "cung-cap-thong-tin-quy-hoach": cung_cap_thong_tin_quy_hoach_attach,
    "cap-gcn-diem-tro-choi-dien-tu-cong-cong": cap_gcn_diem_tro_choi_dien_tu_attach,
    "giao-thue-chuyen-muc-dich-dat-bac-ninh": giao_thue_chuyen_muc_dich_dat_bac_ninh_attach,
    "giao-thue-chuyen-muc-dich-dat-ninh-binh": giao_thue_chuyen_muc_dich_dat_ninh_binh_attach,
    "giao-thue-chuyen-muc-dich-dat-quang-ngai": giao_thue_chuyen_muc_dich_dat_quang_ngai_attach,
    "dang-ky-dat-dai-lan-dau-quang-ngai": dang_ky_dat_dai_lan_dau_quang_ngai_attach,
    "xac-dinh-lai-dien-tich-dat-o-quang-ngai": xac_dinh_lai_dien_tich_dat_o_quang_ngai_attach,
    "dinh-chinh-sai-sot-quang-ngai": dinh_chinh_sai_sot_quang_ngai_attach,
    "dinh-chinh-gcn-da-cap-ninh-binh": dinh_chinh_gcn_da_cap_ninh_binh_attach,
    "dinh-chinh-da-cap-ninh-binh": dinh_chinh_da_cap_ninh_binh_attach,
    "dang-ky-dat-dai-lan-dau-ninh-binh": dang_ky_dat_dai_lan_dau_ninh_binh_attach,
    "cap-doi-gcn-ninh-binh": cap_doi_gcn_ninh_binh_attach,
    "dang-ky-bien-dong-dat-dai-ninh-binh": dang_ky_bien_dong_dat_dai_ninh_binh_attach,
    "dang-ky-dat-dai-lan-dau-quang-ninh-mien-nui-hai-dao": dang_ky_dat_dai_lan_dau_quang_ninh_mien_nui_hai_dao_attach,
    "dang-ky-bien-dong-chuyen-nhuong-quang-ninh-mien-nui-hai-dao": dang_ky_bien_dong_chuyen_nhuong_quang_ninh_mien_nui_hai_dao_attach,
    "chuyen-muc-dich-su-dung-dat-quang-ninh-mien-nui-hai-dao": chuyen_muc_dich_su_dung_dat_quang_ninh_mien_nui_hai_dao_attach,
    "cap-doi-gcn-quang-ninh-mien-nui-hai-dao": cap_doi_gcn_quang_ninh_mien_nui_hai_dao_attach,
    # Biến thể "do đo đạc lại thửa đất, không nghĩa vụ tài chính" — package RIÊNG (thành phần hồ sơ hiện
    # y hệt nhưng tách để sửa độc lập về sau).
    "cap-doi-gcn-do-do-dac-khong-nvtc-quang-ninh-mien-nui-hai-dao": cap_doi_gcn_do_do_dac_khong_nvtc_quang_ninh_mien_nui_hai_dao_attach,
    "tach-hop-thua-dat-quang-ninh-mien-nui-hai-dao": tach_hop_thua_dat_quang_ninh_mien_nui_hai_dao_attach,
    "dang-ky-tai-san-dat-quang-ninh-mien-nui-hai-dao": dang_ky_tai_san_dat_quang_ninh_mien_nui_hai_dao_attach,
    "dang-ky-bien-dong-doi-ten-quang-ninh-mien-nui-hai-dao": dang_ky_bien_dong_doi_ten_quang_ninh_mien_nui_hai_dao_attach,
    "dieu-chinh-quyet-dinh-giao-dat-lao-cai": dieu_chinh_giao_dat_lao_cai_attach,
    "giao-thue-dat-lao-cai": giao_thue_dat_lao_cai_attach,
    "dang-ky-bien-phap-bao-dam-quang-ninh": dang_ky_bien_phap_bao_dam_quang_ninh_attach,
    "xoa-dang-ky-bien-phap-bao-dam-quang-ninh": xoa_dang_ky_bien_phap_bao_dam_quang_ninh_attach,
    "dang-ky-dat-dai-lan-dau-bac-ninh": dang_ky_dat_dai_lan_dau_bac_ninh_attach,
    "thu-hoi-gcn-cap-sai-bac-ninh": thu_hoi_gcn_cap_sai_bac_ninh_attach,
    "dang-ky-bien-dong-chuyen-nhuong-bac-ninh": dang_ky_bien_dong_chuyen_nhuong_bac_ninh_attach,
    "dang-ky-bien-dong-dat-dai-bac-ninh": dang_ky_bien_dong_dat_dai_bac_ninh_attach,
    "xoa-dang-ky-bien-phap-bao-dam-bac-ninh": xoa_dk_bpbd_bac_ninh_attach,
    "dang-ky-bien-phap-bao-dam-bac-ninh": dang_ky_bpbd_bac_ninh_attach,
    "ho-tro-nguoi-cao-tuoi-bac-ninh": ho_tro_nguoi_cao_tuoi_bac_ninh_attach,
    "ho-tro-chi-phi-hoa-tang-bac-ninh": ho_tro_chi_phi_hoa_tang_bac_ninh_attach,
    "ho-tro-chi-phi-hoa-tang-quang-ngai": ho_tro_chi_phi_hoa_tang_quang_ngai_attach,
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
    # Kênh popup KHÔNG dùng planner này (nó tự đính cục bộ theo clientAttachmentCase, rẽ nhánh
    # trước khi gọi backend); đăng ký ở đây để kênh Handfree có kế hoạch đính kèm.
    "chung-thuc-chu-ky-nguoi-dich-ctv": chung_thuc_chu_ky_nguoi_dich_ctv_attach,
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
    "khai-tu-lien-thong": khai_tu_lien_thong_attach,
    "khai-tu-dang-ky-lai": khai_tu_dang_ky_lai_attach,
    "thay-doi-cai-chinh-ho-tich": thay_doi_ho_tich_attach,
    "xac-dinh-muc-do-khuyet-tat": khuyet_tat_attach,
    "xac-nhan-tinh-trang-hon-nhan": xac_nhan_tthn_attach,
    "xet-tuyen-vien-chuc": xet_tuyen_vien_chuc_attach,
    "xet-tuyen-vien-chuc-lai-chau": xet_tuyen_vien_chuc_lai_chau_attach,
    "xet-tuyen-cong-chuc": xet_tuyen_cong_chuc_attach,
    "thi-tuyen-cong-chuc": thi_tuyen_cong_chuc_attach,
    "thi-tuyen-cong-chuc-mot-cua-moha": thi_tuyen_cong_chuc_mot_cua_moha_attach,
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
    "cong-bo-co-so-du-dieu-kien-tiem-chung": cong_bo_du_dk_tiem_chung_attach,
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
    "cap-gcnkncm-cccm": cap_gcnkncm_cccm_attach,
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
