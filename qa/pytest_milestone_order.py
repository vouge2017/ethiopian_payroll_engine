"""Run date-sensitive tests first if the complete suite crosses midnight."""


def pytest_collection_modifyitems(items):
    items.sort(key=lambda item: 0 if item.path.name == 'test_item_versions.py' else 1)
