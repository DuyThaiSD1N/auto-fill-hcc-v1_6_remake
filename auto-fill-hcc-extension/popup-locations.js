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

    _modernTone(text) {
        if (!text) return '';

        const toneO = {
            'oà': 'òa', 'oá': 'óa', 'oả': 'ỏa', 'oã': 'õa', 'oạ': 'ọa',
            'oè': 'òe', 'oé': 'óe', 'oẻ': 'ỏe', 'oẽ': 'õe', 'oẹ': 'ọe'
        };
        const toneU = {
            'uỳ': 'ùy', 'uý': 'úy', 'uỷ': 'ủy', 'uỹ': 'ũy', 'uỵ': 'ụy'
        };

        Object.entries(toneO).forEach(([old, modern]) => {
            const regex = new RegExp(old + '(?!\\w)', 'g');
            text = text.replace(regex, modern);
        });

        Object.entries(toneU).forEach(([old, modern]) => {
            const regex = new RegExp('(?<![qQ])' + old + '(?!\\w)', 'g');
            text = text.replace(regex, modern);
        });

        return text;
    }

    async load() {
        if (this.loaded) return;

        try {
            const url = chrome.runtime.getURL('data/vn_provinces_wards.json');
            const response = await fetch(url);
            const data = await response.json();

            this.provinces = [];
            this.wardsBySlug = {};

            for (const p of data.provinces) {
                const slug = p.code_name.replace(/_/g, '');
                const text = this._modernTone(p.full_name);
                const name = this._modernTone(p.name);

                this.provinces.push({ text, slug, name });

                this.wardsBySlug[slug] = {
                    slug,
                    province: text,
                    communes: p.wards.map(w => this._modernTone(w.full_name))
                };
            }

            this.loaded = true;
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
