/* Keep edits local to this page; native POST remains the save authority. */
(() => {
  const form = document.querySelector('[data-employee-form]');
  if (!form) return;
  const feedback = form.querySelector('[data-form-feedback]');
  const button = form.querySelector('button[type="submit"]');
  const label = button.textContent;
  let dirty = false;
  let submitting = false;
  form.addEventListener('input', () => {
    dirty = true;
    feedback.textContent = 'Unsaved changes. Save when you are ready.';
  });
  form.addEventListener('invalid', event => {
    const details = event.target.closest('details');
    if (details) details.open = true;
    feedback.textContent = 'Check the highlighted field. Your entries are still here.';
  }, true);
  form.addEventListener('submit', event => {
    if (submitting) { event.preventDefault(); return; }
    submitting = true;
    button.disabled = true;
    button.textContent = 'Saving…';
    form.setAttribute('aria-busy', 'true');
    feedback.textContent = 'Saving employee details…';
  });
  window.addEventListener('beforeunload', event => {
    if (dirty && !submitting) { event.preventDefault(); event.returnValue = ''; }
  });
  window.addEventListener('pageshow', () => {
    submitting = false;
    button.disabled = false;
    button.textContent = label;
    form.removeAttribute('aria-busy');
  });
})();
