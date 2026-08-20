/**
 * Location management for auto-selecting province and ward/commune
 * Ported from tro-ly-nguoi-dan-backend/app/locations/
 */

const LOCATIONS_CACHE_KEY = 'autofill_locations_catalog';
const LOCATIONS_CACHE_TTL_MS = 24 * 60 * 60 * 1000;

class LocationManager {
    constructor() {
        this.provinces = [];
        this.wardsBySlug = {};
        this.loaded = false;
    }

    /**
     * Nạp danh mục tỉnh/xã từ BACKEND (app/locations/data/vn_provinces_wards.json) — extension không
     * đóng gói bản sao nữa. BE đã chuẩn hoá dấu kiểu mới nên client dùng thẳng.
     *
     * Hai điểm bắt buộc phải chiều ở context content script:
     *  - Fetch đi qua background (action apiFetch): fetch thẳng từ content script dính CSP
     *    connect-src của trang cổng.
     *  - Content script chạy ở MỌI frame → cache vào chrome.storage.local để một trang nhiều iframe
     *    không gọi BE hàng chục lần.
     */
    async load() {
        if (this.loaded) return;

        const data = (await this._readCache()) || (await this._fetchCatalog());
        if (!data) return;   // BE chưa sẵn sàng: giữ loaded=false để lượt sau thử lại

        this.provinces = Array.isArray(data.provinces) ? data.provinces : [];
        this.wardsBySlug = data.wardsBySlug || {};
        this.loaded = this.provinces.length > 0;
        console.log('[LocationManager] Loaded', this.provinces.length, 'provinces');
    }

    async _readCache() {
        try {
            const res = await chrome.storage.local.get(LOCATIONS_CACHE_KEY);
            const hit = res[LOCATIONS_CACHE_KEY];
            if (!hit || !hit.at || Date.now() - hit.at > LOCATIONS_CACHE_TTL_MS) return null;
            return hit.data && hit.data.provinces?.length ? hit.data : null;
        } catch (error) {
            return null;
        }
    }

    async _fetchCatalog() {
        try {
            const res = await new Promise((resolve) => {
                chrome.runtime.sendMessage({
                    action: 'apiFetch',
                    url: BACKEND_URL + '/api/v1/locations/catalog',
                    method: 'GET',
                    headers: {},
                }, (out) => resolve(chrome.runtime.lastError ? null : out));
            });
            if (!res || !res.ok) throw new Error(res?.error || `HTTP ${res?.status}`);
            const data = JSON.parse(res.body);
            try { await chrome.storage.local.set({ [LOCATIONS_CACHE_KEY]: { at: Date.now(), data } }); }
            catch (error) { /* hết quota: vẫn dùng được, chỉ là lượt sau phải gọi lại */ }
            return data;
        } catch (error) {
            console.error('[LocationManager] Failed to load data:', error);
            return null;
        }
    }

    /**
     * Get all provinces
     */
    getProvinces() {
        return this.provinces;
    }

    /**
     * Get wards/communes for a province by slug
     */
    getWards(slug) {
        return this.wardsBySlug[slug] || null;
    }

    /**
     * Find province by text (full name or short name)
     */
    findProvince(provinceName) {
        if (!provinceName) return null;

        const name = provinceName.trim();

        // Try exact match with full name first
        let prov = this.provinces.find(p => p.text === name);

        // Fallback: match with short name (for old manually-entered accounts)
        if (!prov) {
            prov = this.provinces.find(p => p.name === name);
        }

        return prov || null;
    }

    /**
     * Find ward/commune in a province
     */
    findWard(slug, wardName) {
        if (!slug || !wardName) return '';

        const data = this.wardsBySlug[slug];
        if (!data) return '';

        const name = wardName.trim();
        const communes = data.communes;

        // Try exact match first
        if (communes.includes(name)) {
            return name;
        }

        // Fallback: strip "Phường/Xã/Đặc khu" prefix and match
        const stripped = name.replace(/^(Phường|Xã|Đặc khu)\s+/i, '');
        const match = communes.find(w => {
            const wStripped = w.replace(/^(Phường|Xã|Đặc khu)\s+/i, '');
            return wStripped === stripped;
        });

        return match || '';
    }

    /**
     * Auto-select location from account data (tinh, xa)
     * Returns: { province: "Tỉnh Hà Nội", provinceSlug: "hanoi", ward: "Phường Tân Phong" } or null
     */
    locationFor(tinh, xa) {
        const prov = this.findProvince(tinh);
        if (!prov) return null;

        const ward = xa ? this.findWard(prov.slug, xa) : '';

        return {
            province: prov.text,
            provinceSlug: prov.slug,
            ward
        };
    }

    /**
     * Auto-fill province and ward selects on current page
     * @param {string} tinh - Province name from account
     * @param {string} xa - Ward/commune name from account
     * @param {Object} options - { provinceSelector, wardSelector, waitForWardLoad }
     */
    async autoFillLocation(tinh, xa, options = {}) {
        const {
            provinceSelector = '[name*="tinh"], [name*="province"], select[id*="province"]',
            wardSelector = '[name*="xa"], [name*="ward"], [name*="phuong"], select[id*="ward"], select[id*="district"]',
            waitForWardLoad = 1000
        } = options;

        const location = this.locationFor(tinh, xa);
        if (!location) {
            console.log('[LocationManager] No location found for:', tinh, xa);
            return false;
        }

        console.log('[LocationManager] Auto-filling location:', location);

        // Fill province select
        const provinceSelect = document.querySelector(provinceSelector);
        if (provinceSelect) {
            // Try to find option by text
            const provinceOption = Array.from(provinceSelect.options).find(opt =>
                opt.text.includes(location.province) ||
                location.province.includes(opt.text)
            );

            if (provinceOption) {
                provinceSelect.value = provinceOption.value;
                provinceSelect.dispatchEvent(new Event('change', { bubbles: true }));
                console.log('[LocationManager] Selected province:', provinceOption.text);

                // Wait for ward options to load
                if (location.ward && waitForWardLoad) {
                    await new Promise(resolve => setTimeout(resolve, waitForWardLoad));
                }
            }
        }

        // Fill ward select if provided
        if (location.ward) {
            const wardSelect = document.querySelector(wardSelector);
            if (wardSelect) {
                // Try to find option by text
                const wardOption = Array.from(wardSelect.options).find(opt =>
                    opt.text.includes(location.ward) ||
                    location.ward.includes(opt.text)
                );

                if (wardOption) {
                    wardSelect.value = wardOption.value;
                    wardSelect.dispatchEvent(new Event('change', { bubbles: true }));
                    console.log('[LocationManager] Selected ward:', wardOption.text);
                } else {
                    console.log('[LocationManager] Ward option not found:', location.ward);
                }
            }
        }

        return true;
    }
}

// Global singleton instance
window.locationManager = new LocationManager();
