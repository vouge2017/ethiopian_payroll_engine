"""Compatibility for two historical branches owning the same JSON column."""

import sqlalchemy as sa
from alembic import context, op
from alembic.script import ScriptDirectory


def add_compliance_column():
    columns = sa.inspect(op.get_bind()).get_columns('company')
    existing = next((c for c in columns if c['name'] == 'compliance_deadlines'), None)
    if existing is None:
        op.add_column('company', sa.Column('compliance_deadlines', sa.JSON(), nullable=True))
    elif not isinstance(existing['type'], sa.JSON) or not existing['nullable']:
        raise RuntimeError('Existing company.compliance_deadlines has an incompatible definition')


def drop_compliance_column_unless_applied(other_revision):
    # Version rows reflect completed migration steps. Keep the data while any
    # still-applied branch depends on the other historical owner of this column.
    scripts = ScriptDirectory.from_config(context.config)
    pending = list(context.get_context().get_current_heads())
    visited = set()
    while pending:
        revision = pending.pop()
        if revision in visited:
            continue
        if revision == other_revision:
            return
        visited.add(revision)
        node = scripts.get_revision(revision)
        for parents in (node.down_revision, node.dependencies):
            if parents:
                pending.extend((parents,) if isinstance(parents, str) else parents)
    op.drop_column('company', 'compliance_deadlines')
