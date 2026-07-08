"""
Disbursement Module — Telebirr Integration Stub

Provides intent/confirm pattern for mobile money disbursement.
In production, this would call Telebirr's intent API.
"""

import uuid
from datetime import datetime
from typing import Dict, Optional

# In-memory store for demo (replace with DB in production)
_intents: Dict[str, dict] = {}


def record_disbursement_intent(
    employee_id: str,
    amount: float,
    method: str = "telebirr"
) -> dict:
    """
    Record a disbursement intent (initiate payment to employee).

    Args:
        employee_id: Employee identifier
        amount: Net pay amount in ETB
        method: Payment method ('telebirr', 'bank_transfer', 'cash')

    Returns:
        Dict with intent_id, status, and metadata
    """
    intent_id = str(uuid.uuid4())[:8]
    record = {
        'intent_id': intent_id,
        'employee_id': employee_id,
        'amount': round(amount, 2),
        'method': method,
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'confirmed_at': None,
    }
    _intents[intent_id] = record
    return {
        'intent_id': intent_id,
        'status': record['status'],
        'amount': record['amount'],
        'method': record['method'],
    }


def confirm_disbursement(intent_id: str) -> dict:
    """
    Confirm a previously recorded disbursement intent.

    Args:
        intent_id: The intent ID to confirm

    Returns:
        Dict with updated status

    Raises:
        KeyError: If intent_id not found
    """
    if intent_id not in _intents:
        raise KeyError(f"Disbursement intent '{intent_id}' not found")

    _intents[intent_id]['status'] = 'confirmed'
    _intents[intent_id]['confirmed_at'] = datetime.now().isoformat()

    return {
        'intent_id': intent_id,
        'status': 'confirmed',
        'confirmed_at': _intents[intent_id]['confirmed_at'],
    }


def get_disbursement_status(intent_id: str) -> Optional[dict]:
    """
    Get the current status of a disbursement intent.

    Args:
        intent_id: The intent ID to look up

    Returns:
        Dict with intent details, or None if not found
    """
    record = _intents.get(intent_id)
    if record is None:
        return None
    return {
        'intent_id': record['intent_id'],
        'employee_id': record['employee_id'],
        'amount': record['amount'],
        'status': record['status'],
        'created_at': record['created_at'],
        'confirmed_at': record['confirmed_at'],
    }


def list_pending_disbursements() -> list:
    """Return all pending disbursement intents."""
    return [
        {'intent_id': r['intent_id'], 'employee_id': r['employee_id'], 'amount': r['amount']}
        for r in _intents.values()
        if r['status'] == 'pending'
    ]
