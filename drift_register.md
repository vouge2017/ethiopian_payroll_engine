# Drift Register — model vs DB schema
#
# Accounting: 88 raw `alembic check` lines (88 structural add/remove ops +
# 17 modify_nullable/modify_type ops = 105 total) collapse into 49 logical
# rows. Grouping rule: raw operations are grouped by (table,
# column/constraint, drift-type) into one register row. Multiple ops on the
# same logical entity — e.g. 52 remove_index across 13 tables, 9
# modify_nullable across 4+ tables, 8 modify_type across type-mismatch
# rows — are collapsed into a single register row.

| # | Table | Column | Direction | Disposition | Evidence |
|---|-------|--------|-----------|-------------|----------|
| 1 | employee | first_name | model-only | migrate | Model: String(50) nullable; DB: absent |
| 2 | employee | father_name | model-only | migrate | Model: String(50) nullable; DB: absent |
| 3 | employee | grandfather_name | model-only | migrate | Model: String(50) nullable; DB: absent |
| 4 | employee | employee_type | model-only | migrate | Model: String(20) nullable=False default='monthly'; DB: absent |
| 5 | employee | daily_rate | model-only | migrate | Model: Numeric(12,2) nullable; DB: absent |
| 6 | filing_record | created_at | model-only | migrate | Model: DateTime nullable; DB: absent |
| 12 | filing_record | filed_at | model-only | migrate | Model: DateTime NOT NULL; DB: nullable |
| 7 | notification | company_id | model-only | migrate | Model: FK company NOT NULL; DB: absent |
| 8 | notification | type | model-only | migrate | Model: String(20) NOT NULL default='info'; DB: absent |
| 9 | payroll_run | source | model-only | migrate | Model: String(20) NOT NULL default='upload'; DB: absent |
| 10 | payslip_acknowledgment | company_id | model-only | migrate | Model: FK company NOT NULL; DB: absent |
| 11 | payslip_acknowledgment | acknowledged_at | model-only | migrate | Model: DateTime NOT NULL; DB: nullable |
| 12 | payslip_acknowledgment | uq_payslip_ack | model-only | migrate | Model: unique(payslip_id,employee_id); DB: absent |
| 13 | filing_record | status | db-only | deferred | DB: VARCHAR(20) NOT NULL; Model: absent |
| 14 | filing_record | payroll_run_id | db-only | deferred | DB: FK payroll_run; Model: absent |
| 15 | notification | notif_type | db-only | deferred | DB: VARCHAR(50) NOT NULL; Model: absent |
| 16 | notification | read_at | db-only | deferred | DB: TIMESTAMP; Model: absent |
| 17 | payslip_acknowledgment | user_agent | db-only | deferred | DB: VARCHAR(500); Model: absent |
| 18 | employee | bank_account | type | migrated | `f4a5b6c7d8ef` uses BYTEA for EncryptedType bytes; migrated PG write/read and existing ciphertext round-trip verified |
| 19 | employee | tin | type | migrated | `f4a5b6c7d8ef` uses BYTEA for EncryptedType bytes; migrated PG write/read and existing ciphertext round-trip verified |
| 20 | employee | fayda_fin | type | migrated | `f4a5b6c7d8ef` uses BYTEA for EncryptedType bytes; migrated PG write/read and existing ciphertext round-trip verified |
| 21 | pay_item_type | classification | type | model-fixed | PG variant matches native `payitem_classification`; ORM bulk write verified on migrated PG schema |
| 22 | pay_item_type | calculation_method | type | model-fixed | PG variant matches native `payitem_calc_method`; ORM bulk write verified on migrated PG schema |
| 23 | pay_item_type | tax_treatment | type | model-fixed | PG variant matches native `payitem_tax_treatment`; ORM bulk write verified on migrated PG schema |
| 24 | filing_record | filing_type | type | deferred | DB VARCHAR(50) wider than model String(30) — not a narrowing |
| 25 | system_setting | key | type | deferred | DB VARCHAR(200) wider than model String(100) — not a narrowing |
| 26 | api_key | token_hash | constraint | deferred | DB has unique; model removed — check writers |
| 27 | employee | indexes (4 removed) | constraint | deferred | DB has indexes; model removed — check writers |
| 28 | employee_allowance | indexes (3 removed) | constraint | deferred | DB has indexes; model removed — check writers |
| 29 | employee_deduction | indexes (5 removed) | constraint | deferred | DB has indexes; model removed — check writers |
| 30 | filing_record | uq_filing_per_period | constraint | deferred | DB has unique; model has it — match |
| 31 | holiday | is_national/is_recurring | constraint | deferred | DB nullable; model default True — match |
| 32 | leave | company_id/days_requested | constraint | migrate | DB nullable; model NOT NULL — mismatch; ee:93-98 backfill (UPDATE SET company_id = 0) + alter_column NOT NULL |
| 33 | leave | indexes (4 removed) | constraint | deferred | DB has indexes; model removed |
| 34 | leave_balance | indexes (2 removed) | constraint | deferred | DB has indexes; model removed |
| 35 | notification | is_read | constraint | deferred | DB nullable; model default False — match |
| 36 | overtime_entry | indexes (3 removed) | constraint | deferred | DB has indexes; model removed |
| 37 | pay_item_type | indexes (4 removed) | constraint | deferred | DB has indexes; model removed |
| 38 | payroll_draft | indexes (1 removed) | constraint | deferred | DB has index; model removed |
| 39 | payroll_item_assignment | indexes (3 removed) | constraint | deferred | DB has indexes; model removed |
| 40 | payroll_preview | indexes/FKs/unique | constraint | deferred | DB has different FKs than model |
| 41 | payroll_run | source/period/indexes | constraint | deferred | DB different from model |
| 42 | payroll_validation_result | indexes (2 removed) | constraint | deferred | DB has indexes; model removed |
| 43 | payslip | indexes (6 removed) | constraint | deferred | DB has indexes; model removed |
| 44 | payslip_generation_job | indexes (3 removed) | constraint | deferred | DB has indexes; model removed |
| 45 | tax_rule | indexes (2 removed) | constraint | deferred | DB has indexes; model removed |
| 46 | user | company_id | constraint | deferred | DB nullable; model NOT NULL — mismatch |
| 47 | billing_payment | FKs (3 changed) | constraint | deferred | DB has different FKs than model |
| 48 | payroll_preview | FKs (2 changed) | constraint | deferred | DB has different FKs than model |
