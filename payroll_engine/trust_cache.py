"""
Trust Component Cache — In-memory caching for expensive trust computations.

Caches: Change Summary, Narrative, Evidence, Exceptions, Filing Workspace.
Keyed by (run_id, company_id). TTL: 5 minutes.

Invalidation:
    - Call invalidate_trust_cache(company_id) when payroll is approved/locked
    - Call invalidate_trust_cache(company_id) when employee data changes
    - Call invalidate_trust_cache(company_id) when a new payroll run is created

Pattern follows existing rule caches (tax.py, pension.py, overtime.py).
"""
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# Cache storage
# ─────────────────────────────────────────

# Each cache maps (run_id, company_id) → (result, timestamp)
_change_cache: dict = {}
_narrative_cache: dict = {}
_evidence_cache: dict = {}
_exceptions_cache: dict = {}
_filing_cache: dict = {}

_TTL = 300  # 5 minutes in seconds


def _cache_key(run_id: int, company_id: int) -> tuple:
    """Build a cache key from run_id and company_id."""
    return (run_id, company_id)


def _is_fresh(entry: tuple) -> bool:
    """Check if a cache entry is still within TTL."""
    if not entry:
        return False
    _, timestamp = entry
    return (time.time() - timestamp) < _TTL


def _get(cache: dict, run_id: int, company_id: int):
    """Get a value from cache if fresh. Returns None if expired or missing."""
    key = _cache_key(run_id, company_id)
    entry = cache.get(key)
    if _is_fresh(entry):
        logger.debug("Trust cache HIT for %s", key)
        return entry[0]
    if entry:
        # Expired — clean up
        del cache[key]
    logger.debug("Trust cache MISS for %s", key)
    return None


def _put(cache: dict, run_id: int, company_id: int, value):
    """Store a value in cache with current timestamp."""
    key = _cache_key(run_id, company_id)
    cache[key] = (value, time.time())
    logger.debug("Trust cache PUT for %s", key)


# ─────────────────────────────────────────
# Public API — Getters
# ─────────────────────────────────────────

def get_change_summary(run_id: int, company_id: int):
    """Get cached ChangeSummary or None."""
    return _get(_change_cache, run_id, company_id)


def get_narrative(run_id: int, company_id: int) -> Optional[str]:
    """Get cached narrative text or None."""
    return _get(_narrative_cache, run_id, company_id)


def get_evidence(run_id: int, company_id: int):
    """Get cached Evidence or None."""
    return _get(_evidence_cache, run_id, company_id)


def get_exceptions(run_id: int, company_id: int):
    """Get cached Exceptions or None."""
    return _get(_exceptions_cache, run_id, company_id)


def get_filing_workspace(run_id: int, company_id: int):
    """Get cached FilingWorkspace or None."""
    return _get(_filing_cache, run_id, company_id)


# ─────────────────────────────────────────
# Public API — Setters
# ─────────────────────────────────────────

def put_change_summary(run_id: int, company_id: int, value):
    """Cache a ChangeSummary result."""
    _put(_change_cache, run_id, company_id, value)


def put_narrative(run_id: int, company_id: int, value: str):
    """Cache a narrative text."""
    _put(_narrative_cache, run_id, company_id, value)


def put_evidence(run_id: int, company_id: int, value):
    """Cache an Evidence result."""
    _put(_evidence_cache, run_id, company_id, value)


def put_exceptions(run_id: int, company_id: int, value):
    """Cache an Exceptions result."""
    _put(_exceptions_cache, run_id, company_id, value)


def put_filing_workspace(run_id: int, company_id: int, value):
    """Cache a FilingWorkspace result."""
    _put(_filing_cache, run_id, company_id, value)


# ─────────────────────────────────────────
# Invalidation
# ─────────────────────────────────────────

def invalidate_trust_cache(company_id: int = None):
    """Invalidate all cached trust components.

    Args:
        company_id: If provided, only invalidate entries for this company.
                    If None, clear ALL cached entries (full flush).
    """
    if company_id is None:
        _change_cache.clear()
        _narrative_cache.clear()
        _evidence_cache.clear()
        _exceptions_cache.clear()
        _filing_cache.clear()
        logger.info("Trust cache: full flush (all companies)")
        return

    # Selective invalidation — only remove entries for this company
    for cache in (_change_cache, _narrative_cache, _evidence_cache,
                  _exceptions_cache, _filing_cache):
        keys_to_remove = [k for k in cache if k[1] == company_id]
        for key in keys_to_remove:
            del cache[key]

    logger.info("Trust cache: invalidated for company_id=%d", company_id)


def invalidate_run(run_id: int, company_id: int):
    """Invalidate all cached trust components for a specific run."""
    key = _cache_key(run_id, company_id)
    for cache in (_change_cache, _narrative_cache, _evidence_cache,
                  _exceptions_cache, _filing_cache):
        if key in cache:
            del cache[key]
    logger.info("Trust cache: invalidated for run_id=%d, company_id=%d",
                run_id, company_id)


# ─────────────────────────────────────────
# Stats (for monitoring)
# ─────────────────────────────────────────

def cache_stats() -> dict:
    """Return cache size stats for monitoring."""
    return {
        'change_summary': len(_change_cache),
        'narrative': len(_narrative_cache),
        'evidence': len(_evidence_cache),
        'exceptions': len(_exceptions_cache),
        'filing_workspace': len(_filing_cache),
        'total_entries': (
            len(_change_cache) + len(_narrative_cache) +
            len(_evidence_cache) + len(_exceptions_cache) +
            len(_filing_cache)
        ),
    }
