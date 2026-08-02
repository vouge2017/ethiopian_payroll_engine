/**
 * EthioPayroll — Core JavaScript Module
 * Provides: skeleton loading, toast notifications, table sorting,
 * keyboard shortcuts, form validation, command palette.
 */

'use strict';

const EthioPayroll = {

    // =============================================
    // TOAST NOTIFICATIONS
    // =============================================

    _toastContainer: null,

    _getToastContainer() {
        if (!this._toastContainer) {
            this._toastContainer = document.createElement('div');
            this._toastContainer.className = 'toast-container';
            this._toastContainer.setAttribute('role', 'status');
            this._toastContainer.setAttribute('aria-live', 'polite');
            document.body.appendChild(this._toastContainer);
        }
        return this._toastContainer;
    },

    /**
     * Show a toast notification.
     * @param {string} message - The message to show
     * @param {string} type - 'success' | 'error' | 'warning' | 'info'
     * @param {string} [title] - Optional title
     * @param {number} [duration] - Auto-dismiss in ms (default: 4000)
     */
    toast(message, type = 'info', title = '', duration = 4000) {
        const container = this._getToastContainer();
        const icons = {
            success: 'bi-check-circle-fill',
            error: 'bi-exclamation-circle-fill',
            warning: 'bi-exclamation-triangle-fill',
            info: 'bi-info-circle-fill',
        };

        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.innerHTML = `
            <i class="bi ${icons[type] || icons.info} toast-icon"></i>
            <div class="toast-body">
                ${title ? `<div class="toast-title">${this._escapeHtml(title)}</div>` : ''}
                <div class="toast-message">${this._escapeHtml(message)}</div>
            </div>
            <button class="toast-close" aria-label="Close">&times;</button>
        `;

        el.querySelector('.toast-close').addEventListener('click', () => this._dismissToast(el));
        container.appendChild(el);

        if (duration > 0) {
            setTimeout(() => this._dismissToast(el), duration);
        }
    },

    _dismissToast(el) {
        el.classList.add('toast-exit');
        setTimeout(() => el.remove(), 300);
    },

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },


    // =============================================
    // SKELETON LOADING
    // =============================================

    /**
     * Show skeleton loading state for an element.
     * @param {HTMLElement} el - The element to show skeleton for
     */
    showSkeleton(el) {
        el.setAttribute('data-skeleton-content', el.innerHTML);
        el.classList.add('skeleton');
    },

    /**
     * Hide skeleton and restore content.
     * @param {HTMLElement} el - The element to restore
     */
    hideSkeleton(el) {
        el.classList.remove('skeleton');
        const original = el.getAttribute('data-skeleton-content');
        if (original) {
            el.innerHTML = original;
            el.removeAttribute('data-skeleton-content');
        }
    },

    /**
     * Wrap an async operation with skeleton loading.
     * @param {HTMLElement} el - Element to show skeleton on
     * @param {Function} asyncFn - Async function to execute
     */
    async withSkeleton(el, asyncFn) {
        this.showSkeleton(el);
        try {
            const result = await asyncFn();
            return result;
        } finally {
            this.hideSkeleton(el);
        }
    },


    // =============================================
    // TABLE SORTING
    // =============================================

    /**
     * Make a table sortable by clicking column headers.
     * @param {HTMLTableElement} table - The table element
     */
    makeSortable(table) {
        if (!table || table.dataset.sortable) return;
        table.dataset.sortable = 'true';

        const headers = table.querySelectorAll('thead th');
        headers.forEach((th, colIndex) => {
            // Skip columns with no-sort attribute
            if (th.hasAttribute('data-no-sort')) return;

            th.style.cursor = 'pointer';
            th.style.userSelect = 'none';
            th.style.position = 'relative';

            // Add sort indicator
            const indicator = document.createElement('span');
            indicator.className = 'sort-indicator';
            indicator.innerHTML = ' <i class="bi bi-chevron-expand" style="opacity:0.3;font-size:0.75em"></i>';
            th.appendChild(indicator);

            th.addEventListener('click', () => {
                const tbody = table.querySelector('tbody');
                if (!tbody) return;

                const rows = Array.from(tbody.querySelectorAll('tr'));
                const currentDir = th.dataset.sortDir || 'none';
                const newDir = currentDir === 'asc' ? 'desc' : 'asc';

                // Reset all headers
                headers.forEach(h => {
                    h.dataset.sortDir = 'none';
                    const ind = h.querySelector('.sort-indicator i');
                    if (ind) { ind.className = 'bi bi-chevron-expand'; ind.style.opacity = '0.3'; }
                });

                // Set this header
                th.dataset.sortDir = newDir;
                const icon = indicator.querySelector('i');
                icon.className = newDir === 'asc' ? 'bi bi-chevron-up' : 'bi bi-chevron-down';
                icon.style.opacity = '1';

                // Sort rows
                rows.sort((a, b) => {
                    const aVal = (a.cells[colIndex]?.textContent || '').trim();
                    const bVal = (b.cells[colIndex]?.textContent || '').trim();

                    // Try numeric comparison
                    const aNum = parseFloat(aVal.replace(/[^0-9.-]/g, ''));
                    const bNum = parseFloat(bVal.replace(/[^0-9.-]/g, ''));

                    if (!isNaN(aNum) && !isNaN(bNum)) {
                        return newDir === 'asc' ? aNum - bNum : bNum - aNum;
                    }

                    // String comparison
                    return newDir === 'asc'
                        ? aVal.localeCompare(bVal)
                        : bVal.localeCompare(aVal);
                });

                rows.forEach(row => tbody.appendChild(row));
            });
        });
    },

    /**
     * Make all tables with class "sortable" sortable.
     */
    initSortableTables() {
        document.querySelectorAll('table.sortable, table[data-sortable]').forEach(
            table => this.makeSortable(table)
        );
    },


    // =============================================
    // TABLE FILTERING
    // =============================================

    /**
     * Add a search filter above a table.
     * @param {HTMLTableElement} table - The table element
     * @param {string} [placeholder] - Input placeholder text
     */
    addTableFilter(table, placeholder = 'Filter...') {
        if (!table || table.dataset.filtered) return;
        table.dataset.filtered = 'true';

        const wrapper = document.createElement('div');
        wrapper.className = 'table-filter mb-2';
        wrapper.innerHTML = `
            <div class="input-group input-group-sm" style="max-width: 300px">
                <span class="input-group-text"><i class="bi bi-search"></i></span>
                <input type="text" class="form-control" placeholder="${placeholder}" aria-label="Filter table">
            </div>
        `;

        table.parentNode.insertBefore(wrapper, table);

        const input = wrapper.querySelector('input');
        input.addEventListener('input', () => {
            const query = input.value.toLowerCase();
            const tbody = table.querySelector('tbody');
            if (!tbody) return;

            tbody.querySelectorAll('tr').forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });
    },

    /**
     * Add filters to all tables with class "filterable".
     */
    initFilterableTables() {
        document.querySelectorAll('table.filterable').forEach(
            table => this.addTableFilter(table)
        );
    },


    // =============================================
    // FORM VALIDATION
    // =============================================

    /**
     * Add real-time validation to a form.
     * @param {HTMLFormElement} form - The form element
     */
    initFormValidation(form) {
        if (!form || form.dataset.validated) return;
        form.dataset.validated = 'true';

        // Validate on blur
        form.querySelectorAll('input, select, textarea').forEach(field => {
            field.addEventListener('blur', () => this._validateField(field));
            field.addEventListener('input', () => {
                if (field.classList.contains('is-invalid')) {
                    this._validateField(field);
                }
            });
        });

        // Validate on submit
        form.addEventListener('submit', (e) => {
            let hasError = false;
            form.querySelectorAll('input[required], select[required], textarea[required]').forEach(field => {
                if (!this._validateField(field)) hasError = true;
            });
            if (hasError) {
                e.preventDefault();
                this.toast('Please fix the errors below', 'error', 'Validation Error');
            }
        });
    },

    _validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        let message = '';

        // Required check
        if (field.hasAttribute('required') && !value) {
            isValid = false;
            message = 'This field is required';
        }

        // Email check
        if (value && field.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
            isValid = false;
            message = 'Please enter a valid email address';
        }

        // Phone check (Ethiopian)
        if (value && (field.name === 'phone' || field.id === 'phone')) {
            if (!/^(\+251|0)[97]\d{8}$/.test(value.replace(/\s/g, ''))) {
                isValid = false;
                message = 'Please enter a valid Ethiopian phone number';
            }
        }

        // Min/max
        if (value && field.type === 'number') {
            const num = parseFloat(value);
            if (field.hasAttribute('min') && num < parseFloat(field.min)) {
                isValid = false;
                message = `Minimum value is ${field.min}`;
            }
            if (field.hasAttribute('max') && num > parseFloat(field.max)) {
                isValid = false;
                message = `Maximum value is ${field.max}`;
            }
        }

        // Update UI
        field.classList.toggle('is-invalid', !isValid);
        field.classList.toggle('is-valid', isValid && value);

        // Show/hide error message
        let feedback = field.parentNode.querySelector('.invalid-feedback');
        if (!isValid) {
            if (!feedback) {
                feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                field.parentNode.appendChild(feedback);
            }
            feedback.textContent = message;
        } else if (feedback) {
            feedback.remove();
        }

        return isValid;
    },


    // =============================================
    // KEYBOARD SHORTCUTS
    // =============================================

    _shortcuts: {},

    /**
     * Register a keyboard shortcut.
     * @param {string} key - The key (e.g., 'k', 'n', 'p')
     * @param {Function} handler - The function to call
     * @param {string} description - Description for help
     * @param {boolean} [ctrl] - Require Ctrl/Cmd key
     */
    registerShortcut(key, handler, description, ctrl = false) {
        this._shortcuts[key] = { handler, description, ctrl };
    },

    _initShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Don't trigger in inputs
            const tag = e.target.tagName;
            if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target.isContentEditable) return;

            const key = e.key.toLowerCase();
            const shortcut = this._shortcuts[key];

            if (shortcut) {
                const ctrlPressed = e.ctrlKey || e.metaKey;
                if (shortcut.ctrl === ctrlPressed) {
                    e.preventDefault();
                    shortcut.handler();
                }
            }
        });

        // Register default shortcuts
        this.registerShortcut('k', () => this.showCommandPalette(), 'Command Palette', true);
        this.registerShortcut('?', () => this.showShortcutHelp(), 'Show Keyboard Shortcuts');
    },

    showShortcutHelp() {
        const shortcuts = Object.entries(this._shortcuts)
            .map(([key, s]) => `<tr><td><kbd>${s.ctrl ? 'Ctrl+' : ''}${key.toUpperCase()}</kbd></td><td>${s.description}</td></tr>`)
            .join('');

        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-dialog modal-sm">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Keyboard Shortcuts</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <table class="table table-sm">
                            <tbody>${shortcuts}</tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        modal.querySelector('.btn-close').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
        document.body.appendChild(modal);
    },


    // =============================================
    // COMMAND PALETTE
    // =============================================

    showCommandPalette() {
        // Collect all navigation links
        const links = Array.from(document.querySelectorAll('.sidebar-nav a[href]')).map(a => ({
            text: a.textContent.trim(),
            href: a.href,
            icon: a.querySelector('i')?.className || '',
        }));

        const modal = document.createElement('div');
        modal.className = 'modal fade show';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-dialog" style="margin-top: 15vh">
                <div class="modal-content">
                    <div class="modal-body p-0">
                        <div class="input-group input-group-lg">
                            <span class="input-group-text bg-transparent border-0"><i class="bi bi-search"></i></span>
                            <input type="text" class="form-control border-0 shadow-none" placeholder="Type a command or search..." autofocus style="font-size:1.1rem;padding:1rem">
                        </div>
                        <div class="command-results" style="max-height:300px;overflow-y:auto;border-top:1px solid var(--border-light)">
                            ${links.map(l => `
                                <a href="${l.href}" class="d-flex align-items-center gap-3 px-3 py-2 text-decoration-none text-body command-item">
                                    <i class="${l.icon}" style="width:20px;text-align:center"></i>
                                    <span>${l.text}</span>
                                </a>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;

        const input = modal.querySelector('input');
        const results = modal.querySelector('.command-results');

        input.addEventListener('input', () => {
            const query = input.value.toLowerCase();
            results.querySelectorAll('.command-item').forEach(item => {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(query) ? '' : 'none';
            });
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') modal.remove();
            if (e.key === 'Enter') {
                const visible = results.querySelector('.command-item:not([style*="display: none"])');
                if (visible) window.location.href = visible.href;
            }
        });

        modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
        document.body.appendChild(modal);
        input.focus();
    },


    // =============================================
    // FLASH MESSAGES → TOASTS
    // =============================================

    /**
     * Convert Flask flash messages to toast notifications.
     */
    convertFlashMessages() {
        document.querySelectorAll('.alert-flash, .flash-message').forEach(el => {
            const message = el.textContent.trim();
            const type = el.classList.contains('alert-danger') ? 'error'
                : el.classList.contains('alert-success') ? 'success'
                : el.classList.contains('alert-warning') ? 'warning'
                : 'info';
            this.toast(message, type);
            el.remove();
        });
    },


    // =============================================
    // INITIALIZATION
    // =============================================

    init() {
        this._initShortcuts();
        this.initSortableTables();
        this.initFilterableTables();

        // Auto-validate forms with data-validate attribute
        document.querySelectorAll('form[data-validate]').forEach(
            form => this.initFormValidation(form)
        );

        // Convert flash messages to toasts
        this.convertFlashMessages();

        // Register N for new employee (if on employees page)
        this.registerShortcut('n', () => {
            const addLink = document.querySelector('a[href*="employees/add"]');
            if (addLink) window.location.href = addLink.href;
        }, 'New Employee');
    },
};

// Auto-init on DOM ready
document.addEventListener('DOMContentLoaded', () => EthioPayroll.init());


// =============================================
// TAB NAVIGATION
// =============================================

/**
 * Initialize tab navigation for a container.
 * @param {string} containerSelector - Selector for the tab container
 */
function initTabs(containerSelector) {
    const container = document.querySelector(containerSelector);
    if (!container) return;

    const tabs = container.querySelectorAll('.tab-nav-item');
    const contents = container.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            e.preventDefault();
            const target = tab.getAttribute('data-tab');

            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Show target content
            contents.forEach(c => {
                c.classList.toggle('active', c.getAttribute('data-tab') === target);
            });

            // Update URL hash
            history.replaceState(null, '', '#' + target);
        });
    });

    // Restore from URL hash
    const hash = window.location.hash.slice(1);
    if (hash) {
        const targetTab = container.querySelector(`.tab-nav-item[data-tab="${hash}"]`);
        if (targetTab) targetTab.click();
    }
}
