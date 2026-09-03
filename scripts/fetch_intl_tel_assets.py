"""One-shot downloader for intl-tel-input static assets.

Run this once after cloning if you do not have node/npm, to populate:
  payroll_engine/static/css/intl-tel-input/intlTelInput.min.css  (plugin CSS)
  payroll_engine/static/js/intl-tel-input/intlTelInput.min.js    (plugin JS)
  payroll_engine/static/js/intl-tel-input/utils.js               (country metadata)
  payroll_engine/static/img/flags.png                              (the flag sprite)

The script pulls from jsdelivr and writes into the static/ tree. The
phone-input.js loader on the page uses local paths only, sidestepping
the CSP `script-src 'self'` rule that blocks external scripts.
"""
import os
import urllib.request

BASE = 'https://cdn.jsdelivr.net/npm/intl-tel-input@23.0.0'

ASSETS = [
    ('build/css/intlTelInput.min.css', 'payroll_engine/static/css/intl-tel-input/intlTelInput.min.css'),
    ('build/js/intlTelInput.min.js', 'payroll_engine/static/js/intl-tel-input/intlTelInput.min.js'),
    ('build/js/utils.js', 'payroll_engine/static/js/intl-tel-input/utils.js'),
    ('build/img/flags.png', 'payroll_engine/static/img/flags.png'),
]


def main():
    # Resolve paths relative to the repo root (one level up from scripts/).
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for src, dst in ASSETS:
        abs_dst = os.path.join(repo, dst)
        os.makedirs(os.path.dirname(abs_dst), exist_ok=True)
        url = f'{BASE}/{src}'
        print(f'  {url}  ->  {dst}')
        with urllib.request.urlopen(url, timeout=60) as r, open(abs_dst, 'wb') as out:
            out.write(r.read())
        print(f'  ok ({os.path.getsize(abs_dst)} bytes)')


if __name__ == '__main__':
    main()

