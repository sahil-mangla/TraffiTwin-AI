"""
failure_simulator.py — Synthetic Sensor Failure Simulation
===========================================================
Generates realistic missing-data patterns on the METR-LA traffic
tensor for training and evaluating the Reconstruction Agent.

Two failure regimes are implemented
------------------------------------
1. MCAR  — Missing Completely At Random (random independent node masks)
2. Block — Sustained contiguous outages on specified nodes

Mask convention (used throughout TraffiTwin AI)
------------------------------------------------
    1 = healthy / observed
    0 = failed  / missing

Both simulation methods return:
    masked_data  : np.ndarray  shape (T, N, F)  — NaN at failed positions
    mask_matrix  : np.ndarray  shape (T, N)     — 1=healthy, 0=failed
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class FailureResult:
    """
    Output of a single failure simulation call.

    Attributes
    ----------
    masked_data : np.ndarray, shape (T, N, F)
        Original data array with NaN injected at all (t, n) positions
        where mask_matrix[t, n] == 0.
    mask_matrix : np.ndarray, shape (T, N), dtype uint8
        Binary mask:  1 = observed/healthy,  0 = missing/failed.
    failure_type : str
        One of ``'mcar'`` or ``'block'``.
    actual_missing_rate : float
        Fraction of (t, n) entries that are masked, computed post-simulation.
    failure_events : list[dict]
        Structured metadata for each failure event applied.
    """
    masked_data: np.ndarray
    mask_matrix: np.ndarray
    failure_type: str
    actual_missing_rate: float
    failure_events: List[dict] = field(default_factory=list)

    def summary(self) -> str:
        T, N = self.mask_matrix.shape
        n_failed = int((self.mask_matrix == 0).sum())
        return (
            f"FailureResult [{self.failure_type.upper()}]\n"
            f"  Timesteps : {T}\n"
            f"  Sensors   : {N}\n"
            f"  Failed (t,n) entries : {n_failed:,} / {T * N:,} "
            f"({self.actual_missing_rate * 100:.2f}%)\n"
            f"  Events    : {len(self.failure_events)}"
        )


# ---------------------------------------------------------------------------
# Failure Simulator
# ---------------------------------------------------------------------------

class FailureSimulator:
    """
    Injects synthetic sensor failure patterns into a traffic tensor.

    Parameters
    ----------
    random_seed : int | None
        Seed for the NumPy RNG to guarantee reproducibility.
        Pass ``None`` for non-deterministic behaviour.

    Examples
    --------
    >>> sim = FailureSimulator(random_seed=42)
    >>> result = sim.simulate_mcar(X, missing_rate=0.10)
    >>> result = sim.simulate_block_missing(X, node_ids=[0, 5], start_time=100, duration=48)
    """

    def __init__(self, random_seed: Optional[int] = 42) -> None:
        self.random_seed = random_seed
        self._rng = np.random.default_rng(random_seed)

    # ------------------------------------------------------------------
    # 1. MCAR — Missing Completely At Random
    # ------------------------------------------------------------------

    def simulate_mcar(
        self,
        X: np.ndarray,
        missing_rate: float = 0.10,
    ) -> FailureResult:
        """
        Randomly mask individual (timestep, sensor) observations.

        Each (t, n) entry is independently masked with probability
        ``missing_rate``, regardless of its neighbours or temporal context.
        This simulates sporadic, uncorrelated hardware glitches.

        Parameters
        ----------
        X : np.ndarray, shape (T, N, F)
            Original (clean or already NaN-containing) traffic tensor.
        missing_rate : float in (0, 1)
            Target fraction of (t, n) entries to mask.

        Returns
        -------
        FailureResult
            ``masked_data`` shape (T, N, F), ``mask_matrix`` shape (T, N).

        Raises
        ------
        ValueError
            If ``missing_rate`` is outside (0, 1).
        """
        self._validate_input(X, missing_rate, "missing_rate")

        T, N, F = X.shape
        masked_data = X.copy().astype(np.float32)

        # Draw a binary mask: 1=keep, 0=mask — shape (T, N)
        keep_prob   = 1.0 - missing_rate
        mask_matrix = (self._rng.random((T, N)) < keep_prob).astype(np.uint8)

        # Zero-out positions in the data tensor (NaN for float arrays)
        fail_mask_3d = (mask_matrix == 0)[:, :, np.newaxis]  # (T, N, 1)
        masked_data[np.broadcast_to(fail_mask_3d, masked_data.shape)] = np.nan

        actual_rate = 1.0 - mask_matrix.mean()
        logger.info(
            "MCAR applied — target=%.1f%%, actual=%.2f%% missing",
            missing_rate * 100,
            actual_rate * 100,
        )

        return FailureResult(
            masked_data=masked_data,
            mask_matrix=mask_matrix,
            failure_type="mcar",
            actual_missing_rate=float(actual_rate),
            failure_events=[
                {
                    "type": "mcar",
                    "missing_rate": missing_rate,
                    "n_entries_masked": int((mask_matrix == 0).sum()),
                }
            ],
        )

    # ------------------------------------------------------------------
    # 2. Block Missing — Sustained Contiguous Outages
    # ------------------------------------------------------------------

    def simulate_block_missing(
        self,
        X: np.ndarray,
        node_ids: Union[int, Sequence[int]],
        start_time: int,
        duration: int,
    ) -> FailureResult:
        """
        Simulate a sustained sensor outage for one or more nodes.

        All observations for ``node_ids`` between timestep ``start_time``
        and ``start_time + duration`` (exclusive) are masked.  This models
        real-world scenarios such as power cuts or network cable failures.

        Parameters
        ----------
        X : np.ndarray, shape (T, N, F)
            Original traffic tensor.
        node_ids : int | list[int]
            Sensor index (or list of indices) to fail.
        start_time : int
            First timestep of the outage window (0-indexed, inclusive).
        duration : int
            Number of consecutive timesteps the outage persists (> 0).

        Returns
        -------
        FailureResult
            ``masked_data`` shape (T, N, F), ``mask_matrix`` shape (T, N).

        Raises
        ------
        ValueError
            If indices or time bounds are out of range.
        """
        T, N, F = X.shape

        # Normalise node_ids to a list
        if isinstance(node_ids, (int, np.integer)):
            node_ids = [int(node_ids)]
        else:
            node_ids = [int(n) for n in node_ids]

        # Boundary validation
        if not node_ids:
            raise ValueError("node_ids must not be empty.")
        if any(n < 0 or n >= N for n in node_ids):
            raise ValueError(
                f"All node_ids must be in [0, {N - 1}]. Got: {node_ids}"
            )
        if start_time < 0 or start_time >= T:
            raise ValueError(
                f"start_time={start_time} must be in [0, {T - 1}]."
            )
        if duration <= 0:
            raise ValueError(f"duration must be > 0, got {duration}.")

        end_time = min(start_time + duration, T)  # clip to array bounds
        actual_duration = end_time - start_time

        if actual_duration < duration:
            logger.warning(
                "Requested duration %d clipped to %d (end of array at T=%d).",
                duration, actual_duration, T,
            )

        # Build mask: start all healthy
        masked_data = X.copy().astype(np.float32)
        mask_matrix = np.ones((T, N), dtype=np.uint8)

        # Apply failure window
        mask_matrix[start_time:end_time, node_ids] = 0
        masked_data[start_time:end_time, node_ids, :] = np.nan

        actual_rate = 1.0 - mask_matrix.mean()

        event = {
            "type": "block",
            "node_ids": node_ids,
            "start_time": start_time,
            "end_time": end_time,
            "duration": actual_duration,
            "n_entries_masked": len(node_ids) * actual_duration,
        }

        logger.info(
            "Block outage — nodes=%s, t=%d→%d (%d steps), "
            "%.2f%% of dataset masked",
            node_ids, start_time, end_time, actual_duration,
            actual_rate * 100,
        )

        return FailureResult(
            masked_data=masked_data,
            mask_matrix=mask_matrix,
            failure_type="block",
            actual_missing_rate=float(actual_rate),
            failure_events=[event],
        )

    # ------------------------------------------------------------------
    # 3. Combined — MCAR + Block (convenience helper)
    # ------------------------------------------------------------------

    def simulate_combined(
        self,
        X: np.ndarray,
        mcar_rate: float = 0.05,
        block_node_ids: Optional[Sequence[int]] = None,
        block_start: int = 0,
        block_duration: int = 72,
    ) -> FailureResult:
        """
        Apply MCAR background noise on top of a sustained block failure.

        Useful for stress-testing the Reconstruction Agent against
        realistic mixed-failure regimes.

        Parameters
        ----------
        X : np.ndarray, shape (T, N, F)
        mcar_rate : float
            Background MCAR missing rate (applied to all non-block positions).
        block_node_ids : list[int] | None
            Nodes for the block outage.  Skipped if None.
        block_start : int
            Start timestep for the block outage.
        block_duration : int
            Duration of the block outage in timesteps.

        Returns
        -------
        FailureResult
            Combined mask and data.
        """
        T, N, F = X.shape

        # Start from MCAR base
        result = self.simulate_mcar(X, missing_rate=mcar_rate)
        events = list(result.failure_events)

        if block_node_ids is not None:
            block_result = self.simulate_block_missing(
                result.masked_data,
                node_ids=block_node_ids,
                start_time=block_start,
                duration=block_duration,
            )
            # Merge masks (AND logic: healthy only if BOTH masks say healthy)
            combined_mask = (result.mask_matrix & block_result.mask_matrix)
            combined_data = X.copy().astype(np.float32)
            fail_3d = (combined_mask == 0)[:, :, np.newaxis]
            combined_data[np.broadcast_to(fail_3d, combined_data.shape)] = np.nan

            events.extend(block_result.failure_events)
            actual_rate = 1.0 - combined_mask.mean()

            return FailureResult(
                masked_data=combined_data,
                mask_matrix=combined_mask,
                failure_type="combined",
                actual_missing_rate=float(actual_rate),
                failure_events=events,
            )

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_input(X: np.ndarray, rate: float, name: str) -> None:
        if X.ndim != 3:
            raise ValueError(
                f"Expected 3-D array (T, N, F), got shape {X.shape}."
            )
        if not (0.0 < rate < 1.0):
            raise ValueError(
                f"``{name}`` must be in (0, 1), got {rate}."
            )

    def reset_rng(self) -> None:
        """Reset the random number generator to its original seed."""
        self._rng = np.random.default_rng(self.random_seed)
