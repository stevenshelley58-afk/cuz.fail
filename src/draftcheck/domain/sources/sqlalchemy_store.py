"""Back-compat facade — implementation lives in ``draftcheck.domain.sources.store``."""

from draftcheck.domain.sources.store import SqlAlchemySourceLibrary
from draftcheck.domain.sources.store._helpers import (
    _count_signal_requires_review,
    _parse_repair_profile,
    _source_quality_gates,
)

__all__ = [
    "SqlAlchemySourceLibrary",
    "_count_signal_requires_review",
    "_parse_repair_profile",
    "_source_quality_gates",
]
