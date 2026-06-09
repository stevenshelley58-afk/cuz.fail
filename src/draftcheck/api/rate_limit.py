"""Shared slowapi limiter instance.

Import ``limiter`` here (not from main.py) to avoid circular imports when
router modules need to decorate individual endpoints with custom rates.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
