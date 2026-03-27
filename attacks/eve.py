"""
Eve — Eavesdropper / MITM Attack Simulator.

Demonstrates why BB84 defeats man‑in‑the‑middle attacks:
  • Eve intercepts qubits, measures them (guessing the basis 50/50),
    then re‑encodes and forwards new qubits to Bob.
  • Because Eve doesn't know Alice's bases she introduces ~25 % QBER,
    which Alice and Bob can detect.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator

from bb84.protocol import DIAGONAL, generate_random_bases


class Eve:
    """Eavesdropper agent for BB84 attack simulation."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.intercepted_bits: np.ndarray | None = None
        self.eve_bases: np.ndarray | None = None
        self._simulator = AerSimulator()

    # ── Core intercept logic ─────────────────────────────────────────
    def intercept(
        self,
        circuits: list[QuantumCircuit],
        eve_bases: np.ndarray | None = None,
    ) -> list[QuantumCircuit]:
        """
        Intercept qubits in transit from Alice → Bob.

        1. Measure each qubit in a randomly chosen basis.
        2. Re‑encode a *new* qubit from the measured result and forward it.

        This is exactly what a classical MITM would try — but the quantum
        no‑cloning theorem ensures the re‑sent qubits carry errors that
        Alice and Bob will detect via QBER.
        """
        n = len(circuits)
        if eve_bases is None:
            eve_bases = generate_random_bases(n)

        self.eve_bases = eve_bases
        self.intercepted_bits = np.zeros(n, dtype=int)
        forwarded_circuits: list[QuantumCircuit] = []

        for i, (qc, basis) in enumerate(zip(circuits, eve_bases)):
            # ── Measure ──────────────────────────────────────────────
            meas_qc = qc.copy()
            if basis == DIAGONAL:
                meas_qc.h(0)
            meas_qc.measure(0, 0)

            job = self._simulator.run(meas_qc, shots=1, memory=True)
            measured_bit = int(job.result().get_memory()[0])
            self.intercepted_bits[i] = measured_bit

            # ── Re‑encode & forward ─────────────────────────────────
            new_qc = QuantumCircuit(1, 1)
            if measured_bit == 1:
                new_qc.x(0)
            if basis == DIAGONAL:
                new_qc.h(0)
            forwarded_circuits.append(new_qc)

        if self.verbose:
            print(f"[Eve]   Intercepted {n} qubits — "
                  f"measured in random bases and re‑sent.")

        return forwarded_circuits

    # ── Convenience: use as a callback ───────────────────────────────
    def __call__(
        self,
        circuits: list[QuantumCircuit],
        eve_bases: np.ndarray,
    ) -> list[QuantumCircuit]:
        """Allow using  eve_instance  directly as `eve_intercept_fn`."""
        return self.intercept(circuits, eve_bases)


# ── Classical key comparison (for demo) ──────────────────────────────
def classical_predictable_key(length: int = 256, seed: int = 42) -> np.ndarray:
    """
    Generate a *predictable* classical key using a seeded PRNG.
    Used in the demo to contrast with quantum key randomness.
    """
    rng = np.random.RandomState(seed)
    return rng.randint(0, 2, size=length)
