"""Repository pattern for Polymarket data access."""
from .markets import MarketsRepository
from .trades import TradesRepository
from .wallets import WalletsRepository

__all__ = ['MarketsRepository', 'TradesRepository', 'WalletsRepository']
