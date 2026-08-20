/**
 * Location management for popup (standalone version)
 * Copy of content/locations.js adapted for popup context
 */

class PopupLocationManager {
    constructor() {
        this.provinces = [];
        this.wardsBySlug = {};
        this.loaded = false;
    }

    async load() {
        if (this.loaded) return;

        try {
            // Danh mục nằm ở backend (app/locations/data/vn_provinces_wards.json), extension KHÔNG
            // đóng gói bản sao nữa. BE đã chuẩn hoá dấu kiểu mới nên client khỏi xử lý lại.
            const data = await window.api.locationsCatalog();

            this.provinces = Array.isArray(data?.provinces) ? data.provinces : [];
            this.wardsBySlug = data?.wardsBySlug || {};

            this.loaded = this.provinces.length > 0;
            console.log('[PopupLocationManager] Loaded', this.provinces.length, 'provinces');
        } catch (error) {
            console.error('[PopupLocationManager] Failed to load data:', error);
        }
    }

    getProvinces() {
        return this.provinces;
    }

    getWards(slug) {
        return this.wardsBySlug[slug] || null;
    }

    /** Tìm tỉnh theo tên đầy đủ ("Tỉnh Lâm Đồng") hoặc tên ngắn ("Lâm Đồng"). */
    findProvince(provinceName) {
        const name = String(provinceName || '').trim();
        if (!name) return null;
        return this.provinces.find(p => p.text === name)
            || this.provinces.find(p => p.name === name)
            || null;
    }

    /** Tên xã/phường ĐẦY ĐỦ trong tỉnh; chấp nhận cả tên ngắn (bỏ tiền tố Phường/Xã/Đặc khu). */
    findWard(slug, wardName) {
        const name = String(wardName || '').trim();
        if (!slug || !name) return '';
        const data = this.wardsBySlug[slug];
        if (!data) return '';
        if (data.communes.includes(name)) return name;
        const strip = (value) => value.replace(/^(Phường|Xã|Thị trấn|Đặc khu)\s+/i, '');
        const stripped = strip(name);
        return data.communes.find(w => strip(w) === stripped) || '';
    }

    /**
     * Tỉnh/xã lưu trong tài khoản -> object địa chỉ chuẩn của popup.
     * Cùng hợp đồng với location_for() bên tro-ly-nguoi-dan-backend (app/locations/lookup.py):
     * không khớp tỉnh thì trả null, khớp tỉnh mà không khớp xã thì ward rỗng.
     */
    locationFor(tinh, xa) {
        const prov = this.findProvince(tinh);
        if (!prov) return null;
        return {
            province: prov.text,
            provinceSlug: prov.slug,
            ward: xa ? this.findWard(prov.slug, xa) : '',
        };
    }
}

// Export for popup.js
window.popupLocationManager = new PopupLocationManager();
