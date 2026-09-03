/* EthioPayroll phone-input helper (tab-based, no intl-tel-input).
 *
 * Handles the phone-or-email tab switch on the login and forgot_password
 * pages. The single <input id="login_id"> element is reused: in Phone
 * mode it's type=tel with a 9-digit Ethiopian format enforced; in Email
 * mode it's type=email with email validation.
 *
 * Activated by:
 *   <div class="phone-input-tabs" data-phone-tabs>
 *     <button data-phone-tab="phone">Phone</button>
 *     <button data-phone-tab="email">Email</button>
 *   </div>
 *   <div class="onboarding-phone-wrapper" id="loginPhoneWrapper">
 *     <div class="phone-input-with-prefix">
 *       <span class="phone-prefix-box">+251</span>
 *       <input type="tel" id="login_id" name="login_id" ...>
 *     </div>
 *   </div>
 *
 * On tab change:
 *   - Phone tab: input becomes type=tel, +251 prefix box shown,
 *     placeholder "91 234 5678", maxlength 9, 7/9 validation
 *   - Email tab: input becomes type=email, +251 prefix box hidden,
 *     placeholder "name@company.com", maxlength 254 (email standard)
 */
(function() {
  var PREFIX = '+251';

  function stripNonDigits(val) {
    return (val || '').replace(/\D/g, '');
  }

  function enforcePhoneInput(e) {
    var input = e.target;
    var digits = stripNonDigits(input.value);
    digits = digits.replace(/^0+/, '');
    if (digits.length > 9) digits = digits.substring(0, 9);
    if (digits.length === 1 && digits[0] !== '7' && digits[0] !== '9') {
      digits = '';
    }
    input.value = digits;
  }

  function initTabs(container) {
    var tabButtons = container.querySelectorAll('[data-phone-tab]');
    if (!tabButtons.length) return;

    // The phone field is the one inside the .phone-input-with-prefix
    // wrapper that the tabs visually control. We find it by the closest
    // form's `login_id` (login) or `phone` (other forms) field.
    var wrapper = container.parentNode.querySelector('.onboarding-phone-wrapper');
    if (!wrapper) return;
    var input = wrapper.querySelector('input');
    var prefixBox = wrapper.querySelector('.phone-prefix-box');
    if (!input) return;

    // Snapshot the original tel-mode attributes so we can restore them
    // when switching back to phone mode.
    var telPlaceholder = input.getAttribute('data-tel-placeholder') || '91 234 5678';
    var emailPlaceholder = input.getAttribute('data-email-placeholder') || 'name@company.com';

    function showPhoneMode() {
      tabButtons.forEach(function(b) {
        b.classList.toggle('active', b.getAttribute('data-phone-tab') === 'phone');
      });
      if (prefixBox) prefixBox.style.display = '';
      input.type = 'tel';
      input.inputMode = 'tel';
      input.maxLength = 9;
      input.placeholder = telPlaceholder;
      input.autocomplete = 'username';
      swapHint('phone');
    }

    function showEmailMode() {
      tabButtons.forEach(function(b) {
        b.classList.toggle('active', b.getAttribute('data-phone-tab') === 'email');
      });
      if (prefixBox) prefixBox.style.display = 'none';
      input.type = 'email';
      input.inputMode = 'email';
      input.maxLength = 254;
      input.placeholder = emailPlaceholder;
      input.autocomplete = 'email';
      // Strip any non-email-friendly content left over from phone mode.
      input.value = input.value.replace(/[^\w@.\-+]/g, '');
      swapHint('email');
    }

    function swapHint(mode) {
      var phoneHint = wrapper.parentNode.querySelector('[data-hint-phone]');
      var emailHint = wrapper.parentNode.querySelector('[data-hint-email]');
      if (phoneHint) phoneHint.style.display = mode === 'phone' ? '' : 'none';
      if (emailHint) emailHint.style.display = mode === 'email' ? '' : 'none';
    }

    tabButtons.forEach(function(btn) {
      btn.addEventListener('click', function() {
        var mode = btn.getAttribute('data-phone-tab');
        if (mode === 'phone') showPhoneMode();
        else if (mode === 'email') showEmailMode();
      });
    });

    // Phone input validation (only fires when in tel mode)
    input.addEventListener('input', function(e) {
      if (input.type === 'tel') enforcePhoneInput(e);
    });

    // Show phone tab by default
    var phoneTab = Array.prototype.find.call(tabButtons, function(b) {
      return b.getAttribute('data-phone-tab') === 'phone';
    });
    if (phoneTab) showPhoneMode();
  }

  function initAll() {
    var containers = document.querySelectorAll('[data-phone-tabs]');
    containers.forEach(initTabs);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
