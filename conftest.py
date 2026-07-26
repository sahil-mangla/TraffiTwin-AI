# Pytest configuration file to enable importing backend modules

# Must be applied before any OpenMP-linked library (numpy, scipy, lightgbm)
# is first imported by any test module — OpenMP reads this at library load
# time, not at call time. backend/api/app.py applies the same workaround,
# but that only takes effect if app.py happens to be the first module in the
# whole test run to touch an OpenMP-linked library, which pytest's
# collection order does not guarantee. Applying it here, in the file pytest
# always imports before collecting any test module, fixes segfaults when
# unpickling the LightGBM checkpoint. See backend/_omp_compat.py for details.
from backend._omp_compat import apply_openmp_compat_workaround

apply_openmp_compat_workaround()

# No DATABASE_URL default needed here: backend.config.Settings already
# defaults to postgres:postgres@localhost:5432/traffitwin, which matches the
# docker-compose.yml postgres service — running `pytest` locally against
# `docker compose up -d postgres` works with no extra env setup. CI sets its
# own DATABASE_URL explicitly for the ephemeral service container (ci.yml).
