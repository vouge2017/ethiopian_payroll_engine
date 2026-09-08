"""
Disbursement Layer — Interface + Adapters

This module defines a jurisdiction-agnostic disbursement interface.
Each payment rail (Telebirr, CBE, M-Pesa, etc.) implements the same interface.

Interface:
    intent(phone, amount, reference) -> DisbursementIntent
    confirm(intent_id) -> DisbursementReceipt
    reconcile(batch_id) -> ReconciliationReport

Adapters:
    - StubDisbursementAdapter: for development/testing (simulates the flow)
    - TelebirrDisbursementAdapter: for production (requires real API credentials)
    - CbeDisbursementAdapter: for production (CBE bulk file format)

The adapter is selected based on configuration, not hardcoded.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Dict, Optional
import uuid
import logging

logger = logging.getLogger('payroll_engine.disbursement')


class DisbursementStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


@dataclass
class DisbursementIntent:
    """A request to disburse funds to one recipient."""
    intent_id: str
    recipient_phone: str
    amount: Decimal
    reference: str  # e.g., "PAYSLIP-EMP001-2026-06"
    status: DisbursementStatus
    created_at: datetime
    provider: str  # "telebirr", "cbe", "stub"
    metadata: Dict = field(default_factory=dict)


@dataclass
class DisbursementReceipt:
    """Confirmation that a disbursement was completed."""
    receipt_id: str
    intent_id: str
    recipient_phone: str
    amount: Decimal
    status: DisbursementStatus
    completed_at: datetime
    provider_reference: str  # Reference from the payment provider
    metadata: Dict = field(default_factory=dict)


@dataclass
class ReconciliationReport:
    """Summary of a batch disbursement for reconciliation."""
    batch_id: str
    total_amount: Decimal
    total_recipients: int
    completed: int
    failed: int
    pending: int
    failures: List[Dict] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)


class DisbursementAdapter(ABC):
    """
    Abstract base class for payment rail adapters.
    
    Every payment rail (Telebirr, CBE, M-Pesa, etc.) must implement
    this interface. The rest of the system only interacts with this
    interface, never with provider-specific code directly.
    """

    @abstractmethod
    def intent(self, phone: str, amount: Decimal, reference: str) -> DisbursementIntent:
        """
        Create a disbursement intent (request to send money).
        
        Args:
            phone: Recipient phone number (normalized: 09XXXXXXXX or 07XXXXXXXX)
            amount: Amount in ETB
            reference: Unique reference for this payment
            
        Returns:
            DisbursementIntent with status PENDING or SUBMITTED
        """
        pass

    @abstractmethod
    def confirm(self, intent_id: str) -> DisbursementReceipt:
        """
        Confirm that a disbursement was completed.
        
        Args:
            intent_id: The intent ID to confirm
            
        Returns:
            DisbursementReceipt with final status
        """
        pass

    @abstractmethod
    def reconcile(self, batch_id: str) -> ReconciliationReport:
        """
        Reconcile a batch of disbursements.
        
        Args:
            batch_id: The batch ID to reconcile
            
        Returns:
            ReconciliationReport with summary of all payments
        """
        pass

    @abstractmethod
    def get_status(self, intent_id: str) -> Optional[DisbursementIntent]:
        """
        Get the current status of a disbursement intent.
        
        Args:
            intent_id: The intent ID to check
            
        Returns:
            DisbursementIntent if found, None otherwise
        """
        pass


class StubDisbursementAdapter(DisbursementAdapter):
    """
    Stub adapter for development and testing.
    
    Simulates the disbursement flow without making real API calls.
    Stores everything in memory (lost on restart).
    
    WARNING: This adapter does NOT move real money. Use only for
    development, testing, and demos.
    """

    def __init__(self):
        self._intents: Dict[str, DisbursementIntent] = {}
        self._receipts: Dict[str, DisbursementReceipt] = {}
        logger.warning("Using StubDisbursementAdapter — no real money will move")

    def intent(self, phone: str, amount: Decimal, reference: str) -> DisbursementIntent:
        """Simulate creating a disbursement intent."""
        intent_id = f"STUB-{uuid.uuid4().hex[:12].upper()}"
        intent = DisbursementIntent(
            intent_id=intent_id,
            recipient_phone=phone,
            amount=amount,
            reference=reference,
            status=DisbursementStatus.SUBMITTED,
            created_at=datetime.utcnow(),
            provider="stub",
        )
        self._intents[intent_id] = intent
        logger.info(f"Stub intent created: {intent_id} for {phone} ETB {amount}")
        return intent

    def confirm(self, intent_id: str) -> DisbursementReceipt:
        """Simulate confirming a disbursement."""
        intent = self._intents.get(intent_id)
        if not intent:
            raise KeyError(f"Intent {intent_id} not found")

        receipt = DisbursementReceipt(
            receipt_id=f"STUB-RCPT-{uuid.uuid4().hex[:12].upper()}",
            intent_id=intent_id,
            recipient_phone=intent.recipient_phone,
            amount=intent.amount,
            status=DisbursementStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            provider_reference=f"STUB-REF-{uuid.uuid4().hex[:8].upper()}",
        )
        self._receipts[intent_id] = receipt
        intent.status = DisbursementStatus.COMPLETED
        logger.info(f"Stub receipt created: {receipt.receipt_id} for {intent_id}")
        return receipt

    def reconcile(self, batch_id: str) -> ReconciliationReport:
        """Simulate reconciling a batch."""
        # In a real implementation, this would query the provider's API
        # For the stub, we just summarize what we have in memory
        batch_intents = [
            i for i in self._intents.values()
            if i.metadata.get("batch_id") == batch_id
        ]

        completed = sum(1 for i in batch_intents if i.status == DisbursementStatus.COMPLETED)
        failed = sum(1 for i in batch_intents if i.status == DisbursementStatus.FAILED)
        pending = len(batch_intents) - completed - failed

        return ReconciliationReport(
            batch_id=batch_id,
            total_amount=sum(i.amount for i in batch_intents),
            total_recipients=len(batch_intents),
            completed=completed,
            failed=failed,
            pending=pending,
        )

    def get_status(self, intent_id: str) -> Optional[DisbursementIntent]:
        """Get the current status of a disbursement intent."""
        return self._intents.get(intent_id)


class DisbursementService:
    """
    High-level service that orchestrates disbursements.
    
    Uses the configured adapter to move money. The adapter is
    selected based on configuration, not hardcoded.
    """

    def __init__(self, adapter: DisbursementAdapter):
        self.adapter = adapter

    def disburse_payroll(
        self,
        payslips: List[Dict],
        batch_id: str,
    ) -> Dict:
        """
        Disburse payroll to multiple employees.
        
        Args:
            payslips: List of dicts with 'employee_phone', 'net_pay', 'reference'
            batch_id: Unique batch identifier for reconciliation
            
        Returns:
            Dict with summary of the batch disbursement
        """
        results = []
        errors = []

        for payslip in payslips:
            phone = payslip.get("employee_phone", "")
            amount = Decimal(str(payslip.get("net_pay", 0)))
            reference = payslip.get("reference", "")

            if not phone or amount <= 0:
                errors.append({
                    "reference": reference,
                    "error": "Invalid phone or amount",
                })
                continue

            try:
                intent = self.adapter.intent(phone, amount, reference)
                intent.metadata["batch_id"] = batch_id
                results.append(intent)
            except Exception as e:
                logger.error(f"Failed to create intent for {reference}: {e}")
                errors.append({
                    "reference": reference,
                    "error": str(e),
                })

        return {
            "batch_id": batch_id,
            "total_requested": len(payslips),
            "successful": len(results),
            "failed": len(errors),
            "intents": results,
            "errors": errors,
        }

    def confirm_batch(self, intent_ids: List[str]) -> List[DisbursementReceipt]:
        """Confirm all intents in a batch."""
        receipts = []
        for intent_id in intent_ids:
            try:
                receipt = self.adapter.confirm(intent_id)
                receipts.append(receipt)
            except Exception as e:
                logger.error(f"Failed to confirm {intent_id}: {e}")
        return receipts


def create_disbursement_adapter(provider: str = "stub") -> DisbursementAdapter:
    """
    Factory function to create the appropriate disbursement adapter.
    
    Args:
        provider: The payment provider ('stub', 'telebirr', 'cbe')
        
    Returns:
        DisbursementAdapter instance
        
    Raises:
        ValueError: If the provider is not supported
    """
    if provider == "stub":
        return StubDisbursementAdapter()
    elif provider == "telebirr":
        # TODO: Implement real Telebirr adapter
        # Requires: merchant_id, client_id, client_secret, api_key
        # See: https://developer.ethiotelecom.et/docs/In%20App%20SDK%20Integration/DevelopmentPreparation
        raise NotImplementedError(
            "Telebirr adapter not yet implemented. "
            "Use 'stub' provider for development. "
            "See: https://developer.ethiotelecom.et/docs/In%20App%20SDK%20Integration/DevelopmentPreparation"
        )
    elif provider == "cbe":
        # TODO: Implement real CBE adapter
        raise NotImplementedError(
            "CBE adapter not yet implemented. Use 'stub' provider for development."
        )
    else:
        raise ValueError(f"Unsupported disbursement provider: {provider}")
