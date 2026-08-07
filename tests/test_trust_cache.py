"""
Tests for trust_cache module.

Verifies:
- Cache hit/miss behavior
- TTL expiration
- Selective invalidation (by company)
- Full flush
- Per-run invalidation
- Cache stats
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from payroll_engine import trust_cache


def setup_function():
    """Clean cache before each test."""
    trust_cache.invalidate_trust_cache()


def teardown_function():
    """Clean cache after each test."""
    trust_cache.invalidate_trust_cache()


# --- Basic get/put ---

def test_get_returns_none_on_empty():
    result = trust_cache.get_change_summary(1, 100)
    assert result is None


def test_put_then_get():
    trust_cache.put_change_summary(1, 100, {'test': 'data'})
    result = trust_cache.get_change_summary(1, 100)
    assert result == {'test': 'data'}


def test_different_keys_isolated():
    trust_cache.put_change_summary(1, 100, 'data_a')
    trust_cache.put_change_summary(2, 100, 'data_b')
    assert trust_cache.get_change_summary(1, 100) == 'data_a'
    assert trust_cache.get_change_summary(2, 100) == 'data_b'


def test_different_companies_isolated():
    trust_cache.put_change_summary(1, 100, 'company_100')
    trust_cache.put_change_summary(1, 200, 'company_200')
    assert trust_cache.get_change_summary(1, 100) == 'company_100'
    assert trust_cache.get_change_summary(1, 200) == 'company_200'


# --- All component types ---

def test_change_summary():
    trust_cache.put_change_summary(1, 100, 'cs')
    assert trust_cache.get_change_summary(1, 100) == 'cs'


def test_narrative():
    trust_cache.put_narrative(1, 100, 'narrative text')
    assert trust_cache.get_narrative(1, 100) == 'narrative text'


def test_evidence():
    trust_cache.put_evidence(1, 100, 'ev')
    assert trust_cache.get_evidence(1, 100) == 'ev'


def test_exceptions():
    trust_cache.put_exceptions(1, 100, 'ex')
    assert trust_cache.get_exceptions(1, 100) == 'ex'


def test_filing_workspace():
    trust_cache.put_filing_workspace(1, 100, 'fw')
    assert trust_cache.get_filing_workspace(1, 100) == 'fw'


# --- TTL ---

def test_fresh_entry_is_hit():
    trust_cache.put_change_summary(1, 100, 'data')
    assert trust_cache.get_change_summary(1, 100) == 'data'


def test_expired_entry_is_miss():
    trust_cache.put_change_summary(1, 100, 'data')
    key = trust_cache._cache_key(1, 100)
    trust_cache._change_cache[key] = (trust_cache._change_cache[key][0], 0)
    result = trust_cache.get_change_summary(1, 100)
    assert result is None


def test_expired_entry_cleaned_up():
    trust_cache.put_change_summary(1, 100, 'data')
    key = trust_cache._cache_key(1, 100)
    trust_cache._change_cache[key] = (trust_cache._change_cache[key][0], 0)
    trust_cache.get_change_summary(1, 100)
    assert key not in trust_cache._change_cache


# --- Invalidation ---

def test_invalidate_company_removes_all_components():
    trust_cache.put_change_summary(1, 100, 'cs')
    trust_cache.put_narrative(1, 100, 'n')
    trust_cache.put_evidence(1, 100, 'ev')
    trust_cache.put_exceptions(1, 100, 'ex')
    trust_cache.put_filing_workspace(1, 100, 'fw')

    trust_cache.invalidate_trust_cache(company_id=100)

    assert trust_cache.get_change_summary(1, 100) is None
    assert trust_cache.get_narrative(1, 100) is None
    assert trust_cache.get_evidence(1, 100) is None
    assert trust_cache.get_exceptions(1, 100) is None
    assert trust_cache.get_filing_workspace(1, 100) is None


def test_invalidate_company_preserves_other_companies():
    trust_cache.put_change_summary(1, 100, 'company_100')
    trust_cache.put_change_summary(1, 200, 'company_200')

    trust_cache.invalidate_trust_cache(company_id=100)

    assert trust_cache.get_change_summary(1, 100) is None
    assert trust_cache.get_change_summary(1, 200) == 'company_200'


def test_invalidate_run_removes_only_that_run():
    trust_cache.put_change_summary(1, 100, 'run_1')
    trust_cache.put_change_summary(2, 100, 'run_2')

    trust_cache.invalidate_run(1, 100)

    assert trust_cache.get_change_summary(1, 100) is None
    assert trust_cache.get_change_summary(2, 100) == 'run_2'


def test_full_flush_clears_everything():
    trust_cache.put_change_summary(1, 100, 'a')
    trust_cache.put_change_summary(2, 200, 'b')
    trust_cache.put_narrative(1, 100, 'c')

    trust_cache.invalidate_trust_cache()

    assert trust_cache.get_change_summary(1, 100) is None
    assert trust_cache.get_change_summary(2, 200) is None
    assert trust_cache.get_narrative(1, 100) is None


# --- Stats ---

def test_empty_cache_stats():
    stats = trust_cache.cache_stats()
    assert stats['total_entries'] == 0
    assert stats['change_summary'] == 0


def test_populated_cache_stats():
    trust_cache.put_change_summary(1, 100, 'a')
    trust_cache.put_narrative(1, 100, 'b')
    trust_cache.put_evidence(2, 100, 'c')

    stats = trust_cache.cache_stats()
    assert stats['change_summary'] == 1
    assert stats['narrative'] == 1
    assert stats['evidence'] == 1
    assert stats['exceptions'] == 0
    assert stats['filing_workspace'] == 0
    assert stats['total_entries'] == 3


# --- Edge cases ---

def test_overwrite_cache_entry():
    trust_cache.put_change_summary(1, 100, 'old')
    trust_cache.put_change_summary(1, 100, 'new')
    assert trust_cache.get_change_summary(1, 100) == 'new'


def test_cache_key_tuple():
    key = trust_cache._cache_key(42, 99)
    assert key == (42, 99)
    assert isinstance(key, tuple)


def test_is_fresh_with_valid_entry():
    entry = ('data', time.time())
    assert trust_cache._is_fresh(entry) is True


def test_is_fresh_with_expired_entry():
    entry = ('data', 0)
    assert trust_cache._is_fresh(entry) is False


def test_is_fresh_with_none():
    assert trust_cache._is_fresh(None) is False
