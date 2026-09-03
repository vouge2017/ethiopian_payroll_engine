/* EthioPayroll phone-input helper (simplified, no intl-tel-input).
 *
 * This script replaces the previous intl-tel-input integration with a
 * simpler tab-based UX: a fixed "+251" prefix box + text input for the
 * 9-digit national number, or an email-style input.
 *
 * Activated by the presence of:
 *   <div class="phone-input-tabs" id="..." data-phone-input="phone">
 *     <tab ...>Phone</tab>  (shows prefix box + tel input)
 *     <tab ...>Email</tab>  (shows email input, hides prefix)
 *   </div>
 *
 * The script enforces:
 *   - Max 9 digits in phone mode
 *   - First digit must be 7 or 9
 *   - Leading zeros are stripped automatically
 *   - On form submit, a hidden field "phone_full" gets the value
 */
(function() {
  var PREFIX = '+251';

  function stripNonDigits(val) {
    return (val || '').replace(/\D/g, '');
  }

  function validateEthiopianPhone(digits) {
    digits = digits.replace(/^0+/, '');
    if (!digits) return true;
    if (digits[0] !== '7' && digits[0] !== '9') return false;
    return true;
  }

  function formatForSubmit(digits) {
    digits = digits.replace(/^0+/, '');
    if (digits.length > 9) digits = digits.substring(0, 9);
    if (digits.length === 9) return PREFIX + ' ' + digits;
    return PREFIX + ' ' + digits;
  }

  function initPhoneTabs(container) {
    var phoneInputId = container.getAttribute('data-phone-input');
    var emailInputId = container.getAttribute('data-email-input');
    var tabButtons = container.querySelectorAll('[data-phone-tab]');
    var phoneField = phoneInputId ? document.getElementById(phoneInputId) : null;
    var emailField = emailInputId ? document.getElementById(emailInputId) : null;
    var prefixBox = container.querySelector('.phone-prefix-box');

    if (!tabButtons.length) return;

    function showTab(tab) {
      var isPhone = tab.getAttribute('data-phone-tab') === 'phone';

      // Update active tab button state
      tabButtons.forEach(function(b) {
        b.classList.toggle('active', b === tab);
      });

      if (phoneField) phoneField.style.display = isPhone ? '' : 'none';
      if (emailField) emailField.style.display = isPhone ? 'none' : '';
      if (prefixBox) prefixBox.style.display = isPhone ? '' : 'none';

      // Sync hidden field values
      syncHiddenFields();
    }

    function enforcePhoneInput(e) {
      var input = e.target;
      var digits = stripNonDigits(input.value);
      digits = digits.replace(/^0+/, '');
      if (digits.length > 9) digits = digits.substring(0, 9);
      if (!validateEthiopianPhone(digits) && digits.length === 1) {
        digits = '';
      }
      input.value = digits;
      syncHiddenFields();
    }

    function syncHiddenFields() {
      var form = container.closest('form');
      if (!form) return;

      // Update hidden phone_full field
      if (phoneField) {
        var hiddenPhone = form.querySelector('input[name="phone_full"], input[name="login_phone_full"]');
        if (hiddenPhone) {
          var digits = stripNonDigits(phoneField.value || '');
          hiddenPhone.value = formatForSubmit(digits);
        }
      }

      // If phone tab is hidden, clear the hidden phone field
      if (emailField && emailField.style.display === 'none') {
        var hiddenPhone = form.querySelector('input[name="phone_full"], input[name="login_phone_full"]');
        if (hiddenPhone && phoneField && phoneField.style.display === 'none') {
          hiddenPhone.value = '';
        }
      }
    }

    // Tab click handlers
    tabButtons.forEach(function(btn) {
      btn.addEventListener('click', function() {
        showTab(btn);
      });
    });

    // Input handlers for phone field
    if (phoneField) {
      phoneField.addEventListener('input', enforcePhoneInput);
      phoneField.addEventListener('blur', enforcePhoneInput);
    }

    // Form submit handler to sync final values
    var form = container.closest('form');
    if (form) {
      form.addEventListener('submit', function() {
        syncHiddenFields();
      });
    }

    // Initialize: show phone tab by default
    var phoneTab = Array.prototype.find.call(tabButtons, function(b) {
      return b.getAttribute('data-phone-tab') === 'phone';
    });
    if (phoneTab) showTab(phoneTab);

    return {
      showTab: showTab,
      syncHiddenFields: syncHiddenFields
    };
  }

  // Auto-init all phone-input-tabs containers
  function initAll() {
    var containers = document.querySelectorAll('[data-phone-tabs]');
    containers.forEach(function(c) {
      initPhoneTabs(c);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
