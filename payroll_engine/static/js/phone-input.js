/* EthioPayroll global phone-input helper.
 *
 * Loads intl-tel-input from CDN (no build step) and applies it to every
 * <input data-intl-tel> on the page. Each input becomes a flag dropdown
 * + national-number field, and on form submit the full E.164 number
 * (e.g. +251911234567) is written into a hidden sibling so the backend
 * can store it without extra parsing.
 *
 * Initial country: data-intl-tel="et" (Ethiopia). Override per-input.
 * The static CSS + JS are loaded here as a one-time boot; subsequent
 * navigations hit the browser cache.
 *
 * Falls back gracefully if intl-tel-input fails to load (e.g., offline)
 * — the input still works as a plain tel field, the backend validation
 * in payroll_engine.models.validate_ethiopian_phone will catch the
 * format error with a flash.
 */
(function() {
  function ensureITILoaded(cb) {
    if (window.intlTelInput) return cb();
    if (window.__itiLoading) return window.__itiLoading.then(cb);
    window.__itiLoading = new Promise(function(resolve) {
      var css = document.createElement('link');
      css.rel = 'stylesheet';
      css.href = 'https://cdn.jsdelivr.net/npm/intl-tel-input@23.0.0/build/css/intlTelInput.min.css';
      document.head.appendChild(css);
      var s = document.createElement('script');
      s.src = 'https://cdn.jsdelivr.net/npm/intl-tel-input@23.0.0/build/js/intlTelInput.min.js';
      s.onload = function() { resolve(); };
      s.onerror = function() { resolve(); }; // graceful fallback
      document.head.appendChild(s);
    }).then(cb);
  }

  function initOne(input) {
    var initialCountry = (input.getAttribute('data-intl-tel') || 'et').toLowerCase();
    var hiddenName = input.getAttribute('data-intl-tel-name') || (input.name + '_full');
    var existingValue = input.value || '';
    var hidden = document.createElement('input');
    hidden.type = 'hidden';
    hidden.name = hiddenName;
    hidden.value = existingValue;
    input.parentNode.insertBefore(hidden, input.nextSibling);

    var iti = window.intlTelInput(input, {
      initialCountry: initialCountry,
      preferredCountries: ['et', 'ke', 'us', 'gb', 'sa', 'ae'],
      separateDialCode: true,
      utilsScript: 'https://cdn.jsdelivr.net/npm/intl-tel-input@23.0.0/build/js/utils.js',
      nationalMode: true,
    });

    // Mark the wrapper so our defensive padding-left rule does not fight
    // with the plugin's own layout. See design-system.css.
    var wrapper = input.closest('.onboarding-phone-wrapper');
    if (wrapper) wrapper.classList.add('iti');

    // If the input has a value, let intl-tel-input parse and format it
    if (existingValue) {
      // Try parsing as full E.164 first
      var parsed = window.intlTelInputGlobals && window.intlTelInputGlobals.utils
        ? window.intlTelInputGlobals.utils.parsePhoneNumber(existingValue)
        : null;
      if (parsed) iti.setNumber(existingValue);
    }

    function sync() {
      hidden.value = iti.getNumber();
    }
    input.addEventListener('blur', sync);
    input.addEventListener('change', sync);
    input.form && input.form.addEventListener('submit', sync);
  }

  function initAll() {
    var inputs = document.querySelectorAll('input[data-intl-tel]');
    if (!inputs.length) return;
    ensureITILoaded(function() {
      if (!window.intlTelInput) return; // offline, give up gracefully
      inputs.forEach(initOne);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
