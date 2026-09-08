"""
Design System for Ethiopian Payroll Engine
===========================================

This document defines the visual design system for the mobile-first UI.
It is based on:
- User research (personas defined from stakeholder conversations)
- UX best practices for low-end devices and intermittent connectivity
- Cultural adaptation for Ethiopian users
- Accessibility (WCAG AA compliance)

Personas:
1. "Alem" — HR Manager at a 15-person retail shop in Bole
   - Device: Tecno Spark, 512MB RAM, intermittent 3G
   - Goals: "Did everyone get paid?" "Am I in trouble with ERCA?"
   - Pain points: Slow UI, confusing navigation, no trust signals

2. "Dawit" — Accountant managing 3 companies
   - Device: Laptop with intermittent WiFi
   - Goals: "How much cash do I need?" "Can I export to CBE?"
   - Pain points: No bulk operations, no error recovery, no reconciliation

3. "Bekele" — Business owner
   - Device: Phone, checks bank balance 5x/day
   - Goals: "How much did I pay?" "Can I get a loan?"
   - Pain points: No bank-ready reports, no clean records

4. "Tigist" — Employee
   - Device: Any phone, limited data
   - Goals: "Did I get paid?" "How much is my pension?"
   - Pain points: No payslip history, no transparency
"""

# ============================================
# DESIGN TOKENS
# ============================================

COLORS = {
    # Primary (trust, banks, professionalism)
    "primary": "#1a5276",
    "primary_dark": "#154360",
    "primary_light": "#eaf2f8",
    
    # Success (paid, complete, compliant)
    "success": "#059669",
    "success_light": "#d1fae5",
    
    # Warning (attention needed, approaching deadline)
    "warning": "#d97706",
    "warning_light": "#fef3c7",
    
    # Error (action required, failed, non-compliant)
    "error": "#dc2626",
    "error_light": "#fee2e2",
    
    # Ethiopian accent (cultural identity)
    "ethiopian_teal": "#0d9488",
    "ethiopian_green": "#059669",
    "ethiopian_yellow": "#d97706",
    "ethiopian_red": "#dc2626",
    
    # Neutrals
    "gray_50": "#f9fafb",
    "gray_100": "#f3f4f6",
    "gray_200": "#e5e7eb",
    "gray_300": "#d1d5db",
    "gray_400": "#9ca3af",
    "gray_500": "#6b7280",
    "gray_600": "#4b5563",
    "gray_700": "#374151",
    "gray_800": "#1f2937",
    "gray_900": "#111827",
    
    # Surfaces
    "surface": "#ffffff",
    "background": "#f4f6f9",
    
    # Dark mode
    "dark_surface": "#1f2937",
    "dark_background": "#111827",
    "dark_text": "#f9fafb",
    "dark_text_muted": "#9ca3af",
}

TYPOGRAPHY = {
    # Font families
    "font_sans": "'Noto Sans', 'Noto Sans Ethiopic', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    "font_mono": "'Source Code Pro', 'Courier New', monospace",
    
    # Font sizes (rem)
    "xs": "0.75rem",      # 12px
    "sm": "0.875rem",     # 14px
    "base": "1rem",       # 16px
    "lg": "1.125rem",     # 18px
    "xl": "1.25rem",      # 20px
    "2xl": "1.5rem",      # 24px
    "3xl": "1.875rem",    # 30px
    "4xl": "2.25rem",     # 36px
    
    # Font weights
    "normal": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700,
    
    # Line heights
    "tight": 1.25,
    "normal": 1.5,
    "relaxed": 1.75,
}

SPACING = {
    "0": "0",
    "1": "4px",
    "2": "8px",
    "3": "12px",
    "4": "16px",
    "5": "20px",
    "6": "24px",
    "8": "32px",
    "10": "40px",
    "12": "48px",
    "16": "64px",
}

BORDER_RADIUS = {
    "none": "0",
    "sm": "4px",
    "md": "8px",
    "lg": "12px",
    "xl": "16px",
    "full": "9999px",
}

SHADOWS = {
    "sm": "0 1px 2px rgba(0, 0, 0, 0.05)",
    "md": "0 4px 6px rgba(0, 0, 0, 0.1)",
    "lg": "0 10px 15px rgba(0, 0, 0, 0.1)",
    "xl": "0 20px 25px rgba(0, 0, 0, 0.15)",
}

TOUCH_TARGETS = {
    "min": "44px",        # WCAG minimum
    "comfortable": "48px", # Recommended for primary actions
    "spacious": "56px",   # For critical actions (approve, pay)
}

# ============================================
# COMPONENT STYLES
# ============================================

BUTTONS = {
    "primary": {
        "background": COLORS["primary"],
        "color": "#ffffff",
        "border": "none",
        "border_radius": BORDER_RADIUS["md"],
        "padding": f"{SPACING['3']} {SPACING['4']}",
        "min_height": TOUCH_TARGETS["comfortable"],
        "font_weight": TYPOGRAPHY["semibold"],
        "transition": "all 0.2s ease",
    },
    "primary_active": {
        "transform": "scale(0.98)",
        "background": COLORS["primary_dark"],
    },
    "success": {
        "background": COLORS["success"],
        "color": "#ffffff",
    },
    "danger": {
        "background": COLORS["error"],
        "color": "#ffffff",
    },
    "outline": {
        "background": "transparent",
        "color": COLORS["primary"],
        "border": f"2px solid {COLORS['primary']}",
    },
}

CARDS = {
    "default": {
        "background": COLORS["surface"],
        "border_radius": BORDER_RADIUS["md"],
        "shadow": SHADOWS["sm"],
        "padding": SPACING["4"],
        "margin_bottom": SPACING["4"],
    },
    "stat": {
        "text_align": "center",
        "padding": SPACING["6"],
    },
}

# ============================================
# TRUST SIGNALS
# ============================================

TRUST_BADGES = {
    "encryption": {
        "icon": "bi-shield-lock",
        "text": "Bank-grade encryption",
        "color": COLORS["success"],
    },
    "pension_compliant": {
        "icon": "bi-check-circle",
        "text": "Pension-compliant",
        "color": COLORS["ethiopian_teal"],
    },
    "tax_ready": {
        "icon": "bi-file-earmark-check",
        "text": "Tax-ready",
        "color": COLORS["primary"],
    },
    "audit_trail": {
        "icon": "bi-clock-history",
        "text": "Full audit trail",
        "color": COLORS["gray_500"],
    },
}

# ============================================
# EMPTY STATES
# ============================================

EMPTY_STATES = {
    "no_employees": {
        "icon": "bi-people",
        "title": "No employees yet",
        "description": "Add your first employee to get started",
        "action": "Add Employee",
    },
    "no_payroll_runs": {
        "icon": "bi-receipt",
        "title": "No payroll runs yet",
        "description": "Run your first payroll to see it here",
        "action": "Run Payroll",
    },
    "no_reports": {
        "icon": "bi-bar-chart",
        "title": "No reports yet",
        "description": "Generate reports for compliance and insights",
        "action": "Generate Report",
    },
    "offline": {
        "icon": "bi-wifi-off",
        "title": "You're offline",
        "description": "Check your connection and try again",
        "action": "Retry",
    },
}

# ============================================
# DARK MODE
# ============================================

DARK_MODE = {
    "background": COLORS["dark_background"],
    "surface": COLORS["dark_surface"],
    "text": COLORS["dark_text"],
    "text_muted": COLORS["dark_text_muted"],
    "border": COLORS["gray_700"],
}
