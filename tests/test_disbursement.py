"""
Tests for the disbursement adapter layer.

Verifies:
1. Stub adapter simulates the full disbursement flow
2. DisbursementService orchestrates batch disbursements
3. Factory function creates the correct adapter
4. Telebirr/CBE adapters raise NotImplementedError (not yet built)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from decimal import Decimal

from payroll_engine.disbursement import (
    StubDisbursementAdapter,
    DisbursementService,
    DisbursementStatus,
    create_disbursement_adapter,
)


class TestStubDisbursementAdapter:
    """Test the stub adapter simulates the disbursement flow."""

    def test_intent_creates_pending_intent(self):
        adapter = StubDisbursementAdapter()
        intent = adapter.intent("0912345678", Decimal("5000.00"), "PAY-001")

        assert intent.intent_id.startswith("STUB-")
        assert intent.recipient_phone == "0912345678"
        assert intent.amount == Decimal("5000.00")
        assert intent.reference == "PAY-001"
        assert intent.status == DisbursementStatus.SUBMITTED
        assert intent.provider == "stub"

    def test_confirm_creates_receipt(self):
        adapter = StubDisbursementAdapter()
        intent = adapter.intent("0912345678", Decimal("5000.00"), "PAY-001")
        receipt = adapter.confirm(intent.intent_id)

        assert receipt.receipt_id.startswith("STUB-RCPT-")
        assert receipt.intent_id == intent.intent_id
        assert receipt.recipient_phone == "0912345678"
        assert receipt.amount == Decimal("5000.00")
        assert receipt.status == DisbursementStatus.COMPLETED

    def test_confirm_raises_for_unknown_intent(self):
        adapter = StubDisbursementAdapter()
        with pytest.raises(KeyError):
            adapter.confirm("STUB-NONEXISTENT")

    def test_get_status_returns_intent(self):
        adapter = StubDisbursementAdapter()
        intent = adapter.intent("0912345678", Decimal("5000.00"), "PAY-001")
        status = adapter.get_status(intent.intent_id)

        assert status is not None
        assert status.intent_id == intent.intent_id

    def test_get_status_returns_none_for_unknown(self):
        adapter = StubDisbursementAdapter()
        assert adapter.get_status("STUB-NONEXISTENT") is None

    def test_reconcile_returns_report(self):
        adapter = StubDisbursementAdapter()
        intent1 = adapter.intent("0912345678", Decimal("5000.00"), "PAY-001")
        intent1.metadata["batch_id"] = "BATCH-001"
        intent2 = adapter.intent("0987654321", Decimal("3000.00"), "PAY-002")
        intent2.metadata["batch_id"] = "BATCH-001"

        report = adapter.reconcile("BATCH-001")

        assert report.batch_id == "BATCH-001"
        assert report.total_amount == Decimal("8000.00")
        assert report.total_recipients == 2


class TestDisbursementService:
    """Test the high-level disbursement service."""

    def test_disburse_payroll_creates_intents(self):
        adapter = StubDisbursementAdapter()
        service = DisbursementService(adapter)

        payslips = [
            {"employee_phone": "0912345678", "net_pay": 5000.00, "reference": "PAY-001"},
            {"employee_phone": "0987654321", "net_pay": 3000.00, "reference": "PAY-002"},
        ]

        result = service.disburse_payroll(payslips, "BATCH-001")

        assert result["total_requested"] == 2
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert len(result["intents"]) == 2

    def test_disburse_payroll_skips_invalid(self):
        adapter = StubDisbursementAdapter()
        service = DisbursementService(adapter)

        payslips = [
            {"employee_phone": "0912345678", "net_pay": 5000.00, "reference": "PAY-001"},
            {"employee_phone": "", "net_pay": 3000.00, "reference": "PAY-002"},  # Invalid phone
            {"employee_phone": "0987654321", "net_pay": -100.00, "reference": "PAY-003"},  # Negative
        ]

        result = service.disburse_payroll(payslips, "BATCH-001")

        assert result["total_requested"] == 3
        assert result["successful"] == 1
        assert result["failed"] == 2

    def test_confirm_batch_creates_receipts(self):
        adapter = StubDisbursementAdapter()
        service = DisbursementService(adapter)

        payslips = [
            {"employee_phone": "0912345678", "net_pay": 5000.00, "reference": "PAY-001"},
        ]

        result = service.disburse_payroll(payslips, "BATCH-001")
        intent_ids = [i.intent_id for i in result["intents"]]
        receipts = service.confirm_batch(intent_ids)

        assert len(receipts) == 1
        assert receipts[0].status == DisbursementStatus.COMPLETED


class TestFactory:
    """Test the adapter factory function."""

    def test_create_stub_adapter(self):
        adapter = create_disbursement_adapter("stub")
        assert isinstance(adapter, StubDisbursementAdapter)

    def test_create_telebirr_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            create_disbursement_adapter("telebirr")

    def test_create_cbe_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            create_disbursement_adapter("cbe")

    def test_create_unknown_raises_value_error(self):
        with pytest.raises(ValueError):
            create_disbursement_adapter("unknown")
