#!/usr/bin/env python3
"""Canonical alias for build reproducibility comparison.

Wraps tools/u11_repro_compare.py to resolve legacy naming debt.
"""

import sys
from pathlib import Path

# Support running directly as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.u11_repro_compare import (  # noqa: F401
    REQUIRED,
    REQUIRED_METADATA,
    atomic_write,
    compare,
    inventory,
    main,
    markdown,
    metadata_errors,
    sha256,
)

if __name__ == "__main__":
    raise SystemExit(main())
