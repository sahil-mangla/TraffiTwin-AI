# Pytest configuration file to enable importing backend modules
import os

# Must be set before any OpenMP-linked library (numpy, scipy, lightgbm) is
# first imported by any test module — OpenMP reads this at library load time,
# not at call time. backend/api/app.py sets the same var, but that only takes
# effect if app.py happens to be the first module in the whole test run to
# touch an OpenMP-linked library, which pytest's collection order does not
# guarantee. Setting it here, in the file pytest always imports before
# collecting any test module, fixes segfaults when unpickling the LightGBM
# checkpoint (lightgbm/basic.py __setstate__) caused by two OpenMP runtimes
# (numpy's and lightgbm's bundled libomp) initializing in the same process.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
