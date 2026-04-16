"""add portfolio and transaction tables

Revision ID: 60bd017ffb73
Revises: cae772f29865
Create Date: 2026-04-14 00:35:54.093617

"""
from alembic import op
import sqlalchemy as sa


revision = '60bd017ffb73'
down_revision = 'cae772f29865'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'portfolios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_portfolios_id', 'portfolios', ['id'])

    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('transaction_type', sa.Enum('BUY', 'SELL', name='transactiontype'), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('price_per_share', sa.Float(), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_transactions_id', 'transactions', ['id'])
    op.create_index('ix_transactions_ticker', 'transactions', ['ticker'])


def downgrade() -> None:
    op.drop_index('ix_transactions_ticker', 'transactions', if_exists=True)
    op.drop_index('ix_transactions_id', 'transactions', if_exists=True)
    op.drop_table('transactions', if_exists=True)
    op.drop_index('ix_portfolios_id', 'portfolios', if_exists=True)
    op.drop_table('portfolios', if_exists=True)
    op.execute('DROP TYPE IF EXISTS transactiontype')
