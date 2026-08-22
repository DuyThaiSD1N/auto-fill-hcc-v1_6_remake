// Script để crawl form elements và hiển thị thông tin lên console
// Chạy script này trong Developer Tools Console của trình duyệt

(function () {
    'use strict';

    console.log('=== BẮT ĐẦU CRAWL FORM ELEMENTS ===');

    // Function để lấy tất cả input elements
    function getAllFormElements() {
        const elements = {
            inputs: [],
            selects: [],
            textareas: [],
            radios: [],
            checkboxes: [],
            buttons: []
        };

        // Lấy tất cả input elements
        document.querySelectorAll('input').forEach((input, index) => {
            const elementInfo = {
                index: index,
                type: input.type,
                name: input.name || '',
                id: input.id || '',
                className: input.className || '',
                value: input.value || '',
                placeholder: input.placeholder || '',
                required: input.required,
                disabled: input.disabled,
                readonly: input.readOnly,
                element: input
            };

            if (input.type === 'radio') {
                elements.radios.push(elementInfo);
            } else if (input.type === 'checkbox') {
                elements.checkboxes.push(elementInfo);
            } else {
                elements.inputs.push(elementInfo);
            }
        });

        // Lấy tất cả select elements
        document.querySelectorAll('select').forEach((select, index) => {
            const options = Array.from(select.options).map(option => ({
                value: option.value,
                text: option.text,
                selected: option.selected
            }));

            elements.selects.push({
                index: index,
                name: select.name || '',
                id: select.id || '',
                className: select.className || '',
                value: select.value || '',
                required: select.required,
                disabled: select.disabled,
                options: options,
                element: select
            });
        });

        // Lấy tất cả textarea elements
        document.querySelectorAll('textarea').forEach((textarea, index) => {
            elements.textareas.push({
                index: index,
                name: textarea.name || '',
                id: textarea.id || '',
                className: textarea.className || '',
                value: textarea.value || '',
                placeholder: textarea.placeholder || '',
                required: textarea.required,
                disabled: textarea.disabled,
                readonly: textarea.readOnly,
                rows: textarea.rows,
                cols: textarea.cols,
                element: textarea
            });
        });

        // Lấy tất cả button elements
        document.querySelectorAll('button, input[type="button"], input[type="submit"], input[type="reset"]').forEach((button, index) => {
            elements.buttons.push({
                index: index,
                type: button.type || 'button',
                name: button.name || '',
                id: button.id || '',
                className: button.className || '',
                value: button.value || '',
                textContent: button.textContent || button.value || '',
                disabled: button.disabled,
                element: button
            });
        });

        return elements;
    }

    // Function để lấy thông tin label
    function getLabelsInfo() {
        const labels = [];
        document.querySelectorAll('label').forEach((label, index) => {
            labels.push({
                index: index,
                text: label.textContent.trim(),
                htmlFor: label.htmlFor || '',
                className: label.className || '',
                element: label
            });
        });
        return labels;
    }

    // Function để tìm form containers
    function getFormContainers() {
        const forms = [];
        document.querySelectorAll('form').forEach((form, index) => {
            forms.push({
                index: index,
                name: form.name || '',
                id: form.id || '',
                className: form.className || '',
                action: form.action || '',
                method: form.method || 'get',
                element: form
            });
        });
        return forms;
    }

    // Function để lấy thông tin các div có thể chứa form fields
    function getFormDivs() {
        const formDivs = [];
        // Tìm các div có class hoặc id liên quan đến form
        document.querySelectorAll('div[class*="form"], div[id*="form"], div[class*="field"], div[class*="input"], .form-group, .form-control').forEach((div, index) => {
            formDivs.push({
                index: index,
                id: div.id || '',
                className: div.className || '',
                textContent: div.textContent.trim().substring(0, 100) + (div.textContent.length > 100 ? '...' : ''),
                element: div
            });
        });
        return formDivs;
    }

    // Thực hiện crawl
    const formElements = getAllFormElements();
    const labels = getLabelsInfo();
    const forms = getFormContainers();
    const formDivs = getFormDivs();

    // Hiển thị kết quả
    console.log('\n📝 THÔNG TIN FORMS:');
    console.table(forms);

    console.log('\n📋 INPUT ELEMENTS:');
    console.table(formElements.inputs);

    console.log('\n📋 SELECT ELEMENTS:');
    console.table(formElements.selects);
    if (formElements.selects.length > 0) {
        formElements.selects.forEach(select => {
            console.log(`Options cho select [${select.name || select.id}]:`, select.options);
        });
    }

    console.log('\n📋 TEXTAREA ELEMENTS:');
    console.table(formElements.textareas);

    console.log('\n📋 RADIO BUTTONS:');
    console.table(formElements.radios);

    console.log('\n📋 CHECKBOXES:');
    console.table(formElements.checkboxes);

    console.log('\n📋 BUTTONS:');
    console.table(formElements.buttons);

    console.log('\n🏷️ LABELS:');
    console.table(labels);

    console.log('\n📦 FORM DIVS:');
    console.table(formDivs);

    // Tạo một object tổng hợp để dễ export
    window.formCrawlData = {
        forms: forms,
        inputs: formElements.inputs,
        selects: formElements.selects,
        textareas: formElements.textareas,
        radios: formElements.radios,
        checkboxes: formElements.checkboxes,
        buttons: formElements.buttons,
        labels: labels,
        formDivs: formDivs
    };

    console.log('\n✅ HOÀN THÀNH! Data đã được lưu vào window.formCrawlData');
    console.log('💡 Để export data: copy(JSON.stringify(window.formCrawlData, null, 2))');

    // Function helper để highlight element
    window.highlightElement = function (selector) {
        document.querySelectorAll('.crawl-highlight').forEach(el => {
            el.classList.remove('crawl-highlight');
            el.style.border = '';
            el.style.backgroundColor = '';
        });

        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            el.classList.add('crawl-highlight');
            el.style.border = '2px solid red';
            el.style.backgroundColor = 'rgba(255, 0, 0, 0.1)';
        });
        console.log(`Highlighted ${elements.length} elements with selector: ${selector}`);
    };

    // Function để lấy thông tin chi tiết của một element
    window.getElementDetails = function (element) {
        const rect = element.getBoundingClientRect();
        return {
            tagName: element.tagName,
            id: element.id,
            className: element.className,
            name: element.name,
            type: element.type,
            value: element.value,
            textContent: element.textContent?.trim().substring(0, 200),
            attributes: Array.from(element.attributes).reduce((acc, attr) => {
                acc[attr.name] = attr.value;
                return acc;
            }, {}),
            position: {
                top: rect.top,
                left: rect.left,
                width: rect.width,
                height: rect.height
            },
            xpath: getXPath(element)
        };
    };

    // Function để tạo XPath
    function getXPath(element) {
        if (element === document.body) return '/html/body';

        let ix = 0;
        const siblings = element.parentNode?.childNodes || [];

        for (let i = 0; i < siblings.length; i++) {
            const sibling = siblings[i];
            if (sibling === element) {
                const tagName = element.tagName.toLowerCase();
                return getXPath(element.parentNode) + '/' + tagName + '[' + (ix + 1) + ']';
            }
            if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                ix++;
            }
        }
    }

    console.log('\n🛠️ HELPER FUNCTIONS:');
    console.log('- highlightElement("selector"): Highlight elements');
    console.log('- getElementDetails(element): Lấy chi tiết element');
    console.log('- copy(JSON.stringify(window.formCrawlData, null, 2)): Export data');

})();