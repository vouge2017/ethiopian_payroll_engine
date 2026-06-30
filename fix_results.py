#!/usr/bin/env python3
"""Fix the broken Jinja2 line in results.html"""

filepath = r"D:\d\ethiopian_payroll_engine\web\templates\results.html"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 56 (index 55) is the broken one
old_line = lines[55]
print(f"OLD: {repr(old_line)}")

new_line = '            <small>Score <span class="badge bg-{{ \'success\' if status == \'green\' else \'warning\' if status == \'yellow\' else \'danger\' }}">{{ \'%.1f\'|format(compliance_score) }}%</span> (<span class="text-{{ \'success\' if status == \'green\' else \'warning\' if status == \'yellow\' else \'danger\' }}">{{ status_message }}</span>)</small>\n'

print(f"NEW: {repr(new_line)}")

lines[55] = new_line

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Done — line 56 fixed.")
