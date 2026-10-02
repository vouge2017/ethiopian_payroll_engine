/* Password strength + confirmation UX.
 *
 * Renders a live checklist under the new-password field. As the user
 * types, each requirement flips between:
 *   - "neutral" (gray dot, requirement text)
 *   - "met"      (green check, requirement text struck through)
 *
 * A "match" row beneath tracks whether the confirm field matches the
 * new field AND meets the same complexity bar. A "Strong" badge appears
 * when all rules pass.
 *
 * Activated by the presence of:
 *   <input id="password" name="password" ...>      (new password)
 *   <input id="password2" name="password2" ...>    (confirm)
 *   <ul data-pw-rules data-pw-target="password" data-pw-confirm="password2" data-pw-strong="strongBadge">
 *     <li data-pw-rule="length">...</li>
 *     <li data-pw-rule="upper">...</li>
 *     <li data-pw-rule="lower">...</li>
 *     <li data-pw-rule="digit">...</li>
 *     <li data-pw-rule="symbol">...</li>
 *   </ul>
 *   <span data-pw-match></span>   (match state)
 *   <span data-pw-strong>...</span> (Strong badge — shown when all rules pass)
 *
 * For change_password.html a third field `current_password` is present;
 * we don't apply the checklist to that one (just normal validation).
 */
(function() {
  var RULES = {
    length: function(p) { return p.length >= 8; },
    upper:  function(p) { return /[A-Z]/.test(p); },
    lower:  function(p) { return /[a-z]/.test(p); },
    digit:  function(p) { return /\d/.test(p); },
    symbol: function(p) { return /[^A-Za-z0-9]/.test(p); },
  };

  function allRulesMet(p) {
    for (var k in RULES) if (!RULES[k](p)) return false;
    return true;
  }

  function initBlock(block) {
    var targetId = block.getAttribute('data-pw-target');
    var confirmId = block.getAttribute('data-pw-confirm');
    var target = document.getElementById(targetId);
    var confirm = confirmId ? document.getElementById(confirmId) : null;
    if (!target) return;
    var strongId = block.getAttribute('data-pw-strong');
    var strong = strongId ? document.getElementById(strongId) : null;
    var matchEl = block.querySelector('[data-pw-match]');
    var rules = block.querySelectorAll('[data-pw-rule]');
    // Optional: gate the form submit button until all checks pass.
    var form = target.form;
    var submitBtn = form && form.querySelector('[data-pw-submit]');
    if (submitBtn) submitBtn.disabled = true;

    function updateRule(rule, met) {
      var li = rule;
      li.classList.toggle('pw-rule-met', met);
      li.classList.toggle('pw-rule-unmet', !met);
      var dot = li.querySelector('[data-pw-dot]');
      if (dot) dot.textContent = met ? '\u2713' : '\u00B7';
    }

    function gateSubmit(allow) {
      if (submitBtn) submitBtn.disabled = !allow;
    }

    function update() {
      var p = target.value || '';
      rules.forEach(function(li) {
        var k = li.getAttribute('data-pw-rule');
        if (RULES[k]) updateRule(li, RULES[k](p));
      });
      var allMet = allRulesMet(p);
      if (strong) strong.style.display = allMet ? '' : 'none';

      var matchState = 'empty';
      if (matchEl && confirm) {
        var c = confirm.value || '';
        if (c === '') {
          matchEl.textContent = '';
          matchEl.className = '';
          matchState = 'empty';
        } else if (c === p && allMet) {
          matchEl.textContent = '\u2713 Passwords match and meet all requirements';
          matchEl.className = 'pw-match-ok';
          matchState = 'ok';
        } else if (c === p) {
          matchEl.textContent = '\u2713 Passwords match, but still need to meet the rules above';
          matchEl.className = 'pw-match-warn';
          matchState = 'warn';
        } else {
          matchEl.textContent = '\u2717 Passwords do not match';
          matchEl.className = 'pw-match-bad';
          matchState = 'bad';
        }
      } else {
        matchState = 'noconfirm';
      }

      // Gate the submit button: enabled only when all rules met AND
      // (no confirm field, or confirm matches and also meets all rules).
      var ok = allMet && (matchState === 'noconfirm' || matchState === 'ok');
      gateSubmit(ok);
    }

    target.addEventListener('input', update);
    if (confirm) confirm.addEventListener('input', update);
    update();
  }

  function init() {
    var blocks = document.querySelectorAll('[data-pw-rules]');
    blocks.forEach(initBlock);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
