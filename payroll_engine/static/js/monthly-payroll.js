(() => {
    const reviewTools = document.getElementById('review-employee-tools');
    if (reviewTools) {
        const search = document.getElementById('review-employee-search');
        const employees = [...document.querySelectorAll('[data-review-employee]')];
        const buttons = [...reviewTools.querySelectorAll('[data-review-filter]')];
        let selected = 'all';
        const filter = () => {
            const query = search.value.trim().toLocaleLowerCase();
            let count = 0;
            employees.forEach(employee => {
                const matches = employee.dataset.reviewSearch.includes(query)
                    && (selected === 'all' || employee.dataset[selected === 'issues' ? 'reviewIssues' : 'reviewChanged'] === 'true');
                employee.hidden = !matches;
                if (matches) count++;
            });
            buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.reviewFilter === selected)));
            document.getElementById('review-employee-count').textContent = `${count} of ${employees.length} employees shown · totals include everyone`;
            document.getElementById('review-no-match').hidden = count !== 0;
        };
        buttons.forEach(button => button.addEventListener('click', () => { selected = button.dataset.reviewFilter; filter(); }));
        search.addEventListener('input', filter);
        document.getElementById('review-clear-filters').addEventListener('click', () => { search.value = ''; selected = 'all'; filter(); search.focus(); });
        reviewTools.hidden = false;
        filter();
    }
    // Keep keyboard focus within the visible area between compact navigation bars.
    document.querySelector('.monthly-payroll')?.addEventListener('focusin', event => {
        const target = event.target;
        if (!target.matches(':focus-visible')) return;
        requestAnimationFrame(() => {
            if (document.activeElement !== target) return;
            const rect = target.getBoundingClientRect();
            const header = document.getElementById('sidebar')?.getBoundingClientRect();
            const footer = document.querySelector('.bottom-nav')?.getBoundingClientRect();
            const top = header && header.width >= innerWidth * .9 ? Math.max(0, header.bottom) : 0;
            const bottom = footer && footer.height > 0 ? footer.top : innerHeight;
            if (rect.top < top + 8 || rect.bottom > bottom - 8) {
                target.scrollIntoView({block: 'center', inline: 'nearest', behavior: 'auto'});
            }
        });
    });
    const form = document.getElementById('spreadsheet-form');
    if (!form) return;
    const fields = [...form.querySelectorAll('input[type="number"]')];
    const saved = fields.map(field => field.value);
    const editors = [...form.querySelectorAll('.monthly-editor')];
    if (matchMedia('(max-width: 800px)').matches) {
        editors.forEach(editor => { editor.open = editor.dataset.inputWarning === 'true'; });
    }
    const state = document.getElementById('worksheet-state');
    const review = document.getElementById('worksheet-review-button');
    let dirty = false;
    let leaving = false;
    let submitting = false;
    const save = document.getElementById('worksheet-save');
    const originalSave = save.textContent;
    const originalReview = review.textContent;
    const update = () => {
        dirty = fields.some((field, index) => field.value !== saved[index]);
        fields.forEach((field, index) => field.classList.toggle('monthly-edited', field.value !== saved[index]));
        editors.forEach(editor => {
            const edited = fields.some((field, index) => editor.contains(field) && field.value !== saved[index]);
            editor.classList.toggle('monthly-editor-edited', edited);
            editor.querySelector('.monthly-edit-state').hidden = !edited;
            editor.querySelector('.monthly-estimate-label').textContent = edited ? 'Last saved net · ETB' : 'Estimated net · ETB';
        });
        state.textContent = dirty ? 'Unsaved changes · estimates reflect the last save' : 'Saved inputs · estimates shown below';
        review.disabled = dirty;
        document.getElementById('review-guidance').textContent = dirty
            ? 'Save & recalculate before reviewing. Your edits are not yet included in the estimates.'
            : 'Review uses saved inputs. An existing review keeps its preserved amounts until you explicitly refresh it.';
        document.getElementById('saved-estimates').classList.toggle('monthly-stale', dirty);
    };
    form.addEventListener('input', update);
    window.addEventListener('pageshow', () => {
        leaving = false;
        submitting = false;
        [save, review].forEach(button => { button.classList.remove('is-busy'); button.removeAttribute('aria-disabled'); });
        [form, document.getElementById('worksheet-review')].forEach(target => target.removeAttribute('aria-busy'));
        save.textContent = originalSave;
        review.textContent = originalReview;
        update();
    });
    const beginSubmit = (event, button, label) => {
        if (submitting) { event.preventDefault(); return; }
        submitting = true;
        leaving = true;
        button.textContent = label;
        button.classList.add('is-busy');
        button.setAttribute('aria-disabled', 'true');
        event.currentTarget.setAttribute('aria-busy', 'true');
        // Keep the named save button enabled so its action value reaches the server.
    };
    form.addEventListener('submit', event => beginSubmit(event, save, 'Saving & recalculating…'));
    document.getElementById('worksheet-review').addEventListener('submit', event => {
        update();
        if (dirty) { event.preventDefault(); document.getElementById('worksheet-save').focus(); }
        else beginSubmit(event, review, 'Opening saved review…');
    });
    const search = document.getElementById('employee-search');
    const employees = [...form.querySelectorAll('[data-employee-search]')];
    const filter = () => {
        const query = search.value.trim().toLocaleLowerCase();
        employees.forEach(employee => { employee.hidden = !employee.dataset.employeeSearch.includes(query); });
        const count = employees.filter(employee => !employee.hidden).length;
        if (query && count === 1) employees.find(employee => !employee.hidden).querySelector('.monthly-editor').open = true;
        document.getElementById('employee-no-match').hidden = count !== 0;
        document.getElementById('employee-search-count').textContent = query ? `${count} of ${employees.length} employees shown` : '';
    };
    search.addEventListener('input', filter);
    form.addEventListener('invalid', event => {
        search.value = '';
        filter();
        const editor = event.target.closest('.monthly-editor');
        if (editor) editor.open = true;
    }, true);
    window.addEventListener('beforeunload', event => {
        if (dirty && !leaving) { event.preventDefault(); event.returnValue = ''; }
    });
})();
