"""Web and worker must reference the same database encryption key."""

from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize('filename', ['render.yaml', 'render-staging.yaml'])
def test_worker_reuses_web_encryption_key(filename):
    blueprint = yaml.safe_load((Path(__file__).resolve().parents[1] / filename).read_text(encoding='utf-8'))
    services = blueprint['services']
    web_services = {service['name']: service for service in services if service['type'] == 'web'}
    workers = [service for service in services if service['type'] == 'worker']
    assert workers, 'Blueprint must define a worker'
    for worker in workers:
        keys = [entry for entry in worker['envVars'] if entry.get('key') == 'DB_ENCRYPTION_KEY']
        assert len(keys) == 1, 'Worker must declare exactly one encryption-key reference'
        reference = keys[0].get('fromService', {})
        assert reference.get('name') in web_services, 'Worker must reference a web service in this Blueprint'
        assert keys[0] == {
            'key': 'DB_ENCRYPTION_KEY',
            'fromService': {
                'name': reference['name'],
                'type': 'web',
                'envVarKey': 'DB_ENCRYPTION_KEY',
            },
        }, 'Worker must use only the web key reference, without an independently generated or literal key'
        web = web_services[reference['name']]
        assert sum(entry.get('key') == 'DB_ENCRYPTION_KEY' for entry in web['envVars']) == 1
        assert next(entry for entry in worker['envVars'] if entry.get('key') == 'DATABASE_URL') == next(
            entry for entry in web['envVars'] if entry.get('key') == 'DATABASE_URL'
        ), 'Web and worker must target the same database'
