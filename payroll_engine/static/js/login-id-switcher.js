/* Phone-or-email input switcher.
 *
 * Used on auth pages where the same `login_id` field accepts either an
 * Ethiopian phone (with country code) or an email. The field is wrapped
 * in the intl-tel-input widget by default. When the user types an '@'
 * the country selector hides and the field acts as a plain email input;
 * clearing the '@' brings the selector back.
 *
 * Activated by the presence of:
 *   <input id="login_id" data-intl-tel="et" ...>
 *   <span id="loginIdPhoneHint">...</span>
 *   <span id="loginIdEmailHint" style="display:none;">...</span>
 */
(function() {
  function init() {
    var input = document.getElementById('login_id');
    var wrapper = document.getElementById('loginPhoneWrapper');
    if (!input || !wrapper) return;

    var phoneHint = document.getElementById('loginIdPhoneHint');
    var emailHint = document.getElementById('loginIdEmailHint');

    function isEmailMode() {
      return input.value.indexOf('@') !== -1;
    }

    function applyMode() {
      var emailMode = isEmailMode();
      // The intl-tel-input widget is the .iti div. Hide it in email mode.
      var iti = wrapper.querySelector('.iti');
      if (iti) iti.style.display = emailMode ? 'none' : '';
      // In email mode, show the bare input and hide the plugin's internal
      // tel-input so only the plain <input> receives keystrokes.
      var telInput = wrapper.querySelector('.iti__tel-input');
      if (telInput) telInput.style.display = emailMode ? 'none' : '';
      // Toggle the bare input visibility. We only change type between
      // 'tel' and 'email' so mobile keyboards and intl-tel-input both
      // get appropriate input modes. We never remove the 'type' attribute
      // entirely — intl-tel-input expects 'tel'.
      input.style.display = emailMode ? '' : 'none';
      input.setAttribute('inputmode', emailMode ? 'email' : 'tel');
      input.setAttribute('type', emailMode ? 'email' : 'tel');
      // Swap hints
      if (phoneHint) phoneHint.style.display = emailMode ? 'none' : '';
      if (emailHint) emailHint.style.display = emailMode ? '' : 'none';
    }

    input.addEventListener('input', applyMode);
    // Run once on load in case the browser autofilled an email
    setTimeout(applyMode, 0);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
