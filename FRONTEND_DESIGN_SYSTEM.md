# Frontend Design System
### Ethiopian Workforce Operating System
**Frozen:** 2026-07-28
**Referenced by:** All PRDs (section 8, 9)
**Stack:** Jinja2 templates + Bootstrap 5 + vanilla JavaScript

---

## Screen Specification Template

Every screen must define:

```
Screen: [Name]
URL: [route]
Purpose: [one sentence]
Auth: [required role(s)]

Layout:
  Header: [what's shown]
  Sidebar: [navigation state]
  Main Content: [what's shown]
  Footer: [what's shown]

States:
  Empty: [what user sees when no data]
  Loading: [what user sees while loading]
  Error: [what user sees on error]
  Success: [what user sees on success]
  Partial: [what user sees with warnings]

Actions:
  Primary: [main CTA button]
  Secondary: [other buttons]
  Destructive: [delete/cancel — always with confirmation]

Responsive:
  Desktop: [layout]
  Tablet: [layout]
  Mobile: [layout]

Accessibility:
  Tab order: [sequence]
  Screen reader: [labels]
  Keyboard shortcuts: [if any]
```

---

## Component Inventory

### Form Components

#### TextInput
```
Properties:
  label: string
  placeholder: string
  value: string
  required: boolean
  disabled: boolean
  readonly: boolean
  error: string (validation message)
  help: string (help text)
  maxLength: number

States:
  default → focus → typing → validated → error

Events:
  onChange(value)
  onBlur() → triggers validation
  onFocus()
```

#### NumberInput (salary, amounts)
```
Properties:
  label: string
  value: Decimal
  currency: string (default: 'ETB')
  min: number
  max: number
  decimals: number (default: 2)
  required: boolean
  error: string

Display:
  Formatted with commas: ETB 15,000.00
  No scientific notation
  No floating-point artifacts

Events:
  onChange(value)
  onBlur() → triggers validation + impact preview
```

#### SelectInput (bank, department)
```
Properties:
  label: string
  options: array of {value, label}
  value: string
  searchable: boolean
  required: boolean
  error: string

Events:
  onChange(value)
```

#### DateInput
```
Properties:
  label: string
  value: Date
  min: Date
  max: Date
  format: string (default: 'YYYY-MM-DD')
  required: boolean

Events:
  onChange(value)
```

#### FileUpload
```
Properties:
  label: string
  accept: string (e.g., '.xlsx,.csv')
  maxSize: number (bytes)
  multiple: boolean
  dragDrop: boolean

States:
  empty → dragover → uploading → processing → complete → error

Events:
  onUpload(file)
  onProgress(percent)
  onComplete(result)
  onError(message)
```

### Validation Components

#### InlineValidation
```
Properties:
  state: 'idle' | 'validating' | 'valid' | 'invalid' | 'warning'
  message: string
  icon: checkmark / spinner / X / warning

Display:
  idle: no icon
  validating: spinner
  valid: green checkmark + message
  invalid: red X + message
  warning: yellow warning + message
```

#### ValidationSummary
```
Properties:
  results: array of {rule, severity, message, employee?, fix?}
  counts: {block, flag, warn}

Display:
  Block: red, must fix before proceeding
  Flag: yellow, can override with reason
  Warn: blue, informational only

Actions:
  Fix: link to fix location
  Override: text input for reason + confirm
  Dismiss: acknowledge warning
```

### Trust Components

#### TrustScore
```
Properties:
  score: number (0-100)
  subScores: array of {name, score, status}
  trend: 'up' | 'down' | 'stable'

Display:
  Large number (94) with color coding
  Green: 90-100
  Yellow: 70-89
  Red: 0-69
  Sub-scores in grid below
  Trend arrow next to each

Events:
  onDrillDown(subScoreName)
```

#### ConfidenceReport
```
Properties:
  employees: number
  gross: Decimal
  tax: Decimal
  pension: Decimal
  net: Decimal
  crosschecks: array of {name, status, details}
  warnings: array of {message, acknowledged}
  confidence: number (0-100)

Display:
  Summary block (employees, gross, tax, pension, net)
  Crosscheck results (green checkmarks or red X)
  Warnings (yellow, require acknowledgment)
  Confidence percentage (large, color-coded)

Actions:
  Approve (only if no BLOCKs)
  Acknowledge warnings (must do all before approve)
  Drill down (click any number → ExplainPanel)
```

#### ExplainPanel
```
Properties:
  title: string
  value: Decimal
  formula: string
  inputs: array of {name, value}
  lawReference: string
  calculatedAt: DateTime
  calculatedBy: string
  approvedBy: string

Display:
  Slide-over panel from right
  Value at top (large)
  Formula in plain language
  Inputs listed
  Law citation
  Timestamp and approver

Triggered by:
  Click/tap on any number with ⓘ icon
```

#### EvidenceBadge
```
Properties:
  evidenceCount: number
  allPassed: boolean

Display:
  Small badge next to numbers
  Green: all evidence present
  Yellow: partial evidence
  Red: missing evidence

Triggered by:
  Click → opens ExplainPanel
```

### Dashboard Components

#### StatCard
```
Properties:
  label: string
  value: string
  change: number (percentage)
  trend: 'up' | 'down' | 'stable'
  icon: string
  link: string

Display:
  Card with value, label, trend arrow
  Color: green (positive), red (negative), gray (neutral)
  Click → navigates to detail
```

#### PayrollTimeline
```
Properties:
  steps: array of {date, label, status, icon}

Display:
  Vertical timeline
  Completed: green checkmark
  Current: blue highlight
  Pending: gray
  Failed: red X

Events:
  onStepClick(step) → navigate to detail
```

#### CashForecast
```
Properties:
  payroll: Decimal
  tax: Decimal
  pension: Decimal
  available: Decimal
  date: Date

Display:
  Stacked amounts
  Surplus/deficit indicator
  Status: SUFFICIENT / WARNING / SHORTFALL
```

### Empty States

Every list/detail screen must have an empty state:

```
Empty State:
  Icon: relevant to context
  Title: "No [entity] yet"
  Description: "Create your first [entity] to get started"
  CTA: [primary action button]
  Example: [link to demo/sample]
```

### Loading States

```
Loading:
  Skeleton screens (not spinners) for lists
  Spinner for single operations
  Progress bar for long operations (import, payroll)
  Estimated time remaining for operations > 10 seconds
```

### Error States

```
Error:
  Title: "Something went wrong"
  Message: human-readable explanation
  Action: "Try again" button
  Support: "Contact support" link
  Technical: error code (collapsed, for support)
```

---

## Responsive Behavior

| Screen | Desktop (>1024) | Tablet (768-1024) | Mobile (<768) |
|--------|----------------|-------------------|---------------|
| Dashboard | 4-column grid | 2-column grid | Single column, cards stack |
| Employee list | Table | Table (scrollable) | Card list |
| Payroll summary | Table + sidebar | Table (scrollable) | Card list |
| Forms | 2-column | 2-column | Single column |
| Modals | Centered, 600px | Centered, 90% width | Full screen |
| Slide-over panels | Right panel, 400px | Right panel, 80% width | Full screen |

---

## Accessibility

- All form inputs must have labels (not just placeholders)
- Tab order follows visual flow
- Focus indicators visible on all interactive elements
- Error messages linked to inputs via `aria-describedby`
- Status changes announced via `aria-live` regions
- Color is never the only indicator (always paired with icon/text)
- Minimum contrast ratio: 4.5:1 for text

---

*Frontend Design System version: 1.0*
