/* App-owned Gregorian date labels follow the app locale, not the browser UI locale.
 * The original field keeps its name/id and submits the same ISO date contract.
 */
(function () {
  'use strict';
  const config = document.getElementById('localized-date-copy');
  if (!config) return;
  const copy = JSON.parse(config.textContent);

  document.querySelectorAll('input[type="date"]').forEach((input, index) => {
    if (input.disabled || input.readOnly) return;
    const originalValue = input.value;
    const wrapper = document.createElement('div');
    wrapper.className = 'localized-date';
    input.before(wrapper);
    wrapper.append(input);
    input.type = 'text';
    input.value = originalValue;
    input.inputMode = 'numeric';
    input.placeholder = copy.example;
    input.pattern = '[0-9]{4}-[0-9]{2}-[0-9]{2}';

    const help = document.createElement('small');
    help.className = 'form-text';
    help.id = 'date-help-' + index;
    help.textContent = copy.format;
    input.setAttribute('aria-describedby', [input.getAttribute('aria-describedby'), help.id].filter(Boolean).join(' '));
    wrapper.append(help);

    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'btn btn-ghost btn-sm mt-2';
    toggle.textContent = copy.show;
    toggle.setAttribute('aria-expanded', 'false');
    wrapper.append(toggle);

    const picker = document.createElement('fieldset');
    picker.id = 'date-picker-' + index;
    picker.hidden = true;
    picker.className = 'mt-2';
    toggle.setAttribute('aria-controls', picker.id);
    const legend = document.createElement('legend');
    legend.className = 'fs-6';
    const fieldName = input.labels?.[0]?.textContent.trim() || input.getAttribute('aria-label') || '';
    legend.textContent = [fieldName, copy.gregorian].filter(Boolean).join(' · ');
    picker.append(legend);
    const row = document.createElement('div');
    row.className = 'd-flex gap-2';
    picker.append(row);
    const fields = {};
    ['year', 'month', 'day'].forEach(key => {
      const label = document.createElement('label');
      label.className = 'flex-fill';
      label.append(document.createTextNode(copy[key]));
      const field = document.createElement(key === 'year' ? 'input' : 'select');
      field.className = 'form-control';
      field.setAttribute('aria-label', copy[key]);
      if (key === 'year') {
        field.type = 'number';
        field.min = '1';
        field.max = '9999';
        field.placeholder = copy.year;
      } else {
        field.append(new Option('—', ''));
        const count = key === 'month' ? 12 : 31;
        for (let n = 1; n <= count; n++) field.append(new Option(String(n), String(n).padStart(2, '0')));
      }
      fields[key] = field;
      label.append(field);
      row.append(label);
    });
    wrapper.append(picker);

    function validate() {
      let valid = !input.value;
      const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(input.value);
      if (match) {
        const year = Number(match[1]);
        const month = Number(match[2]);
        const day = Number(match[3]);
        const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
        const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
        valid = year > 0 && month >= 1 && month <= 12 && day >= 1 && day <= days[month - 1];
        if (input.min && input.value < input.min) valid = false;
        if (input.max && input.value > input.max) valid = false;
      }
      input.setCustomValidity(valid ? '' : copy.invalid);
    }
    function syncFields() {
      const parts = input.value.split('-');
      ['year', 'month', 'day'].forEach((key, i) => { fields[key].value = parts[i] || ''; });
      validate();
    }
    Object.values(fields).forEach(field => field.addEventListener('input', () => {
      const { year, month, day } = fields;
      if (year.value && month.value && day.value) {
        input.value = year.value.padStart(4, '0') + '-' + month.value + '-' + day.value;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      } else {
        input.value = '';
        input.setCustomValidity(Object.values(fields).some(f => f.value) ? copy.invalid : '');
      }
    }));
    input.addEventListener('input', syncFields);
    input.addEventListener('change', syncFields);
    input.form?.addEventListener('reset', () => setTimeout(syncFields, 0));
    toggle.addEventListener('click', () => {
      picker.hidden = !picker.hidden;
      toggle.setAttribute('aria-expanded', String(!picker.hidden));
      toggle.textContent = picker.hidden ? copy.show : copy.hide;
      if (!picker.hidden) fields.year.focus();
    });
    picker.addEventListener('keydown', event => {
      if (event.key === 'Escape') {
        picker.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
        toggle.textContent = copy.show;
        toggle.focus();
      }
    });
    syncFields();
  });
})();
