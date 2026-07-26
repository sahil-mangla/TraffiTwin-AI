"""
_omp_compat.py — OpenMP duplicate-runtime workaround
=======================================================
numpy and lightgbm each ship their own bundled OpenMP runtime in their pip
wheels. On macOS, having both loaded in the same process crashes on unpickle
(lightgbm/basic.py __setstate__) once a second OpenMP runtime initializes.
KMP_DUPLICATE_LIB_OK=TRUE silences that abort.

This has only been observed on macOS pip wheels; Linux (CI, Docker) is not
known to need it, so the workaround is scoped to darwin rather than applied
unconditionally.
"""

import os
import sys


def apply_openmp_compat_workaround() -> None:
    """Set KMP_DUPLICATE_LIB_OK on macOS to avoid the numpy/lightgbm OpenMP crash.

    Must be called before any OpenMP-linked library (numpy, scipy, lightgbm)
    is first imported in the process, since OpenMP reads this at library
    load time, not at call time.
    """
    if sys.platform == "darwin":
        os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
