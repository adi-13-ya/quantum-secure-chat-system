"""
BB84 Quantum Key Distribution Protocol — Simulation using Qiskit.

This module implements the full BB84 protocol:
  1. Alice generates random bits & random bases, encodes qubits
  2. Bob measures qubits in randomly chosen bases
  3. Key sifting — keep bits where bases matched
  4. QBER calculation to detect eavesdroppers
"""

import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator


# ── Constants ────────────────────────────────────────────────────────
RECTILINEAR = 0   # + basis  (standard |0⟩, |1⟩)
DIAGONAL    = 1   # × basis  (Hadamard rotated)

QBER_THRESHOLD = 0.11   # ~11 % — abort if above this


# ── Qubit generation (Alice) ─────────────────────────────────────────
def generate_random_bits(n: int) -> np.ndarray:
    """Generate *n* random classical bits (0 or 1)."""
    return np.random.randint(0, 2, size=n)


def generate_random_bases(n: int) -> np.ndarray:
    """Generate *n* random bases (0 = rectilinear, 1 = diagonal)."""
    return np.random.randint(0, 2, size=n)


def encode_qubits(bits: np.ndarray, bases: np.ndarray) -> list[QuantumCircuit]:
    """
    Encode classical bits into single‑qubit quantum circuits.

    • Rectilinear (+):  bit 0 → |0⟩ ,  bit 1 → |1⟩
    • Diagonal    (×):  bit 0 → |+⟩ ,  bit 1 → |−⟩
    """
    circuits = []
    for bit, basis in zip(bits, bases):
        qc = QuantumCircuit(1, 1)
        if bit == 1:
            qc.x(0)          # flip to |1⟩
        if basis == DIAGONAL:
            qc.h(0)          # rotate into diagonal basis
        circuits.append(qc)
    return circuits


# ── Measurement (Bob) ────────────────────────────────────────────────
def measure_qubits(
    circuits: list[QuantumCircuit],
    bob_bases: np.ndarray,
) -> np.ndarray:
    """
    Bob measures each qubit in his randomly chosen basis.
    Returns array of measured bit values.
    """
    simulator = AerSimulator()
    results = []

    for qc, basis in zip(circuits, bob_bases):
        meas_qc = qc.copy()
        if basis == DIAGONAL:
            meas_qc.h(0)     # rotate back before measurement
        meas_qc.measure(0, 0)

        job = simulator.run(meas_qc, shots=1, memory=True)
        result = job.result()
        measured_bit = int(result.get_memory()[0])
        results.append(measured_bit)

    return np.array(results)


# ── Key sifting ──────────────────────────────────────────────────────
def sift_key(
    alice_bits: np.ndarray,
    alice_bases: np.ndarray,
    bob_bits: np.ndarray,
    bob_bases: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Keep only the bits where Alice and Bob used the same basis.
    Returns (alice_sifted_key, bob_sifted_key).
    """
    matching = alice_bases == bob_bases
    return alice_bits[matching], bob_bits[matching]


# ── QBER ─────────────────────────────────────────────────────────────
def calculate_qber(
    alice_key: np.ndarray,
    bob_key: np.ndarray,
    sample_fraction: float = 0.5,
) -> tuple[float, np.ndarray, np.ndarray]:
    """
    Estimate the QBER by publicly comparing a random sample of the
    sifted key.

    Returns
    -------
    qber : float
        Quantum Bit Error Rate of the sampled bits.
    alice_final : ndarray
        Remaining key bits (not sampled) — Alice side.
    bob_final : ndarray
        Remaining key bits (not sampled) — Bob side.
    """
    n = len(alice_key)
    sample_size = max(1, int(n * sample_fraction))

    sample_indices = np.random.choice(n, size=sample_size, replace=False)
    remaining_indices = np.setdiff1d(np.arange(n), sample_indices)

    errors = np.sum(alice_key[sample_indices] != bob_key[sample_indices])
    qber = errors / sample_size

    return qber, alice_key[remaining_indices], bob_key[remaining_indices]


# ── Full BB84 session ────────────────────────────────────────────────
def run_bb84(
    num_qubits: int = 256,
    eve_intercept_fn=None,
    verbose: bool = True,
) -> dict:
    """
    Run a complete BB84 key exchange session.

    Parameters
    ----------
    num_qubits : int
        Number of qubits Alice transmits (more → longer key after sifting).
    eve_intercept_fn : callable | None
        If provided, called as  eve_intercept_fn(circuits, eve_bases)
        to simulate eavesdropping.  Must return the (possibly disturbed)
        list of circuits.
    verbose : bool
        Print progress messages.

    Returns
    -------
    dict with keys:
        success        – bool, True if key exchange succeeded
        shared_key     – ndarray of final key bits (empty if failed)
        qber           – float, measured QBER
        alice_bits     – full original bits
        alice_bases    – full original bases
        bob_bases      – full original bases
        bob_bits       – measured bits
        eve_active     – bool
        num_qubits     – int
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"  BB84 Key Exchange  —  {num_qubits} qubits")
        print(f"{'='*60}")

    # Step 1 — Alice
    alice_bits  = generate_random_bits(num_qubits)
    alice_bases = generate_random_bases(num_qubits)
    circuits    = encode_qubits(alice_bits, alice_bases)
    if verbose:
        print("[Alice] Generated qubits and sent to Bob.")

    # Step 1.5 — Eve (optional)
    eve_active = eve_intercept_fn is not None
    if eve_active:
        eve_bases = generate_random_bases(num_qubits)
        circuits  = eve_intercept_fn(circuits, eve_bases)
        if verbose:
            print("[Eve]   Intercepted and re-sent qubits!")

    # Step 2 — Bob
    bob_bases = generate_random_bases(num_qubits)
    bob_bits  = measure_qubits(circuits, bob_bases)
    if verbose:
        print("[Bob]   Measured qubits.")

    # Step 3 — Sift
    alice_sifted, bob_sifted = sift_key(alice_bits, alice_bases, bob_bits, bob_bases)
    if verbose:
        print(f"[Sift]  Matching bases: {len(alice_sifted)} / {num_qubits}")

    # Step 4 — QBER
    qber, alice_final, bob_final = calculate_qber(alice_sifted, bob_sifted)
    success = qber < QBER_THRESHOLD

    if verbose:
        status = "✅ SECURE" if success else "⚠️  EAVESDROPPER DETECTED"
        print(f"[QBER]  {qber:.2%}  →  {status}")
        if success:
            print(f"[Key]   Final shared key length: {len(alice_final)} bits")
        else:
            print("[Key]   Key exchange ABORTED — starting over.")

    return {
        "success":     success,
        "shared_key":  alice_final if success else np.array([], dtype=int),
        "qber":        qber,
        "alice_bits":  alice_bits,
        "alice_bases": alice_bases,
        "bob_bases":   bob_bases,
        "bob_bits":    bob_bits,
        "eve_active":  eve_active,
        "num_qubits":  num_qubits,
    }
