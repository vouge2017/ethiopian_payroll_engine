/* EthioPayroll global phone-input helper.
 *
 * Loads intl-tel-input from local static assets and applies it to every
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
  // The plugin and its flag sprite are hosted locally under /static/ so the
  // browser's CSP img-src 'self' data: rule does not block the flag sprite.
  // Derive the static base path from the <script> tag that loaded this file.
  // phone-input.js is loaded by the template as
  //   <script src="{{ url_for('static', filename='js/phone-input.js') }}?v=...">
  // so we can derive the local base path from the script's own src.
  // We use a data attribute on the script tag for reliability, falling back
  // to querying the DOM if the attribute is absent.
  var _scriptEl = document.currentScript || document.querySelector('script[src*="phone-input.js"]');
  function localBase() {
    if (!_scriptEl) return '/static';
    var src = _scriptEl.getAttribute('data-static-base');
    if (!src) {
      src = _scriptEl.getAttribute('src') || '';
      src = src.replace(/phone-input\.js.*$/, '');
    }
    return src;
  }

  function ensureITILoaded(cb) {
    if (window.intlTelInput) return cb();
    if (window.__itiLoading) return window.__itiLoading.then(cb);
    var base = localBase();
    window.__itiLoading = new Promise(function(resolve) {
      // Load CSS from local path (CSP-safe)
      var link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = base + 'css/intl-tel-input/intlTelInput.min.css';
      document.head.appendChild(link);
      // Load intl-tel-input JS from local path (CSP-safe)
      var s = document.createElement('script');
      s.src = base + 'js/intl-tel-input/intlTelInput.min.js';
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

    var base = localBase();
    var iti = window.intlTelInput(input, {
      initialCountry: initialCountry,
      preferredCountries: ['et', 'ke', 'us', 'gb', 'sa', 'ae'],
      separateDialCode: true,
      // LOCAL assets (CSP-safe: served from /static/ under our origin)
      utilsScript: base + 'js/intl-tel-input/utils.js',
      // Override the plugin's default flag sprite URL by patching the
      // <style> that the plugin injects. The plugin's _init() creates a
      // stylesheet using its own default path; we replace that path with
      // our local sprite. Done after init() below.
      nationalMode: true,
    });

    // Override the plugin's flag sprite URL with the local one. The plugin
    // sets a background-image on the .iti__flag class via a <style> it
    // injects; we look for that style and replace the URL.
    var style = Array.from(document.styleSheets).find(function(s) {
      try { return Array.from(s.cssRules).some(function(r) { return /\.iti__flag/.test(r.cssText); }); }
      catch (e) { return false; }
    });
    if (style) {
      Array.from(style.cssRules).forEach(function(r) {
        if (r.style && r.style.backgroundImage) {
          r.style.backgroundImage = 'url("' + base + 'img/flags.png")';
        }
      });
    }

    // Mark the wrapper so our defensive padding-left rule does not fight
    // with the plugin's own layout. See design-system.css.
    var wrapper = input.closest('.onboarding-phone-wrapper');
    if (wrapper) wrapper.classList.add('iti');

    // If the input has a value, let intl-tel-input parse and format it
    if (existingValue) {
      try { iti.setNumber(existingValue); } catch (e) { /* ignore */ }
    }

    // Frontend validation: enforce 9-digit Ethiopian format
    // - Strip leading 0 automatically
    // - Limit to 9 digits max
    // - Only allow 7 or 9 as first digit (Ethiopian mobile)
    function enforceFormat(e) {
      var digits = e.target.value.replace(/\D/g, '');
      // Strip leading zeros
      digits = digits.replace(/^0+/, '');
      // Enforce first digit must be 7 or 9 for Ethiopia
      if (digits.length > 0 && digits[0] !== '7' && digits[0] !== '9') {
        if (digits.length === 1) {
          digits = ''; // reject invalid first digit
        }
      }
      // Max 9 digits
      if (digits.length > 9) {
        digits = digits.substring(0, 9);
      }
      e.target.value = digits;
      sync();
    }
    input.addEventListener('input', enforceFormat);
    input.addEventListener('blur', enforceFormat);

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

