/**
 * Location management for auto-selecting province and ward/commune
 * Ported from tro-ly-nguoi-dan-backend/app/locations/
 */

class LocationManager {
    constructor() {
        this.provinces = [];
        this.wardsBySlug = {};
        this.loaded = false;
    }

    /**
     * Modernize tone marks from old style to new style
     * Old: "Hoà", "Thuỵ" → New: "Hòa", "Thụy"
     */
    _modernTone(text) {
        if (!text) return '';

        const toneO = {
            'oà': 'òa', 'oá': 'óa', 'oả': 'ỏa', 'oã': 'õa', 'oạ': 'ọa',
            'oè': 'òe', 'oé': 'óe', 'oẻ': 'ỏe', 'oẽ': 'õe', 'oẹ': 'ọe'
        };
        const toneU = {
            'uỳ': 'ùy', 'uý': 'úy', 'uỷ': 'ủy', 'uỹ': 'ũy', 'uỵ': 'ụy'
        };

        // Replace oa patterns (not followed by word characters)
        Object.entries(toneO).forEach(([old, modern]) => {
            const regex = new RegExp(old + '(?!\\w)', 'g');
            text = text.replace(regex, modern);
        });

        // Replace uy patterns (not preceded by q/Q)
        Object.entries(toneU).forEach(([old, modern]) => {
            const regex = new RegExp('(?<![qQ])' + old + '(?!\\w)', 'g');
            text = text.replace(regex, modern);
        });

        return text;
    }

    /**
     * Load province and ward data from JSON file
     */
    async load() {
        if (this.loaded) return;

        try {
            const url = chrome.runtime.getURL('data/vn_provinces_wards.json');
            const response = await fetch(url);
            const data = await response.json();

            this.provinces = [];
            this.wardsBySlug = {};

            for (const p of data.provinces) {
                // "bac_ninh" → "bacninh": match with old 9-province manual list
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
            console.log('[LocationManager] Loaded', this.provinces.length, 'provinces');
        } catch (error) {
            console.error('[LocationManager] Failed to load data:', error);
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
