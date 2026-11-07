"""Import every domain's `models` module here so `Base.metadata` is complete for Alembic.

For example: `from app.billing import models as billing_models`, then add it to `__all__`.
"""

from app.core.db import Base

__all__ = ["Base"]
