"""
Quantum‑Secured Chat — Main Entry Point
════════════════════════════════════════

Usage
─────
  python main.py server                  # Start Alice (server)
  python main.py server --eve            # Start Alice with Eve active
  python main.py client                  # Start Bob  (client)
  python main.py demo                    # Run non‑interactive demo
  python main.py dashboard              # Show visualization dashboard
"""

from __future__ import annotations

import argparse
import datetime
import sys
import numpy as np

from bb84.protocol import run_bb84
from attacks.eve import Eve, classical_predictable_key
from crypto.aes_encryption import derive_aes_key, encrypt_message, decrypt_message
from chat.server import ChatServer
from chat.client import ChatClient
from viz.dashboard import show_dashboard


def _demo():
    """Run a self‑contained demo: normal exchange → attack → comparison."""
    print("\n" + "═" * 64)
    print("  QUANTUM‑SECURED CHAT — FULL DEMO")
    print("═" * 64)

    events: list[dict] = []
    qber_history: list[dict] = []
    ts = lambda: datetime.datetime.now().strftime("%H:%M:%S")

    # ── Round 1: Normal exchange ─────────────────────────────────────
    events.append({"time": ts(), "message": "Round 1 — Normal key exchange", "kind": "info"})
    r1 = run_bb84(num_qubits=256, eve_intercept_fn=None, verbose=True)
    qber_history.append({"round": 1, "qber": r1["qber"], "eve_active": False})

    if r1["success"]:
        events.append({"time": ts(), "message": f"Key established — {len(r1['shared_key'])} bits", "kind": "success"})

        # Encrypt / decrypt a sample message
        aes_key, salt = derive_aes_key(r1["shared_key"])
        original = "Hello Bob! This is a quantum‑secured message."
        nonce, ct = encrypt_message(aes_key, original)
        decrypted = decrypt_message(aes_key, nonce, ct)

        print(f"\n  Original : {original}")
        print(f"  Encrypted: {ct[:40].hex()}…")
        print(f"  Decrypted: {decrypted}")
        events.append({"time": ts(), "message": "Sample message encrypted & decrypted ✓", "kind": "success"})
    else:
        events.append({"time": ts(), "message": "Unexpected failure in clean round", "kind": "danger"})

    # ── Round 2: Eve intercepts ──────────────────────────────────────
    print("\n")
    events.append({"time": ts(), "message": "Round 2 — Eve intercepts", "kind": "danger"})
    eve = Eve(verbose=True)
    r2 = run_bb84(num_qubits=256, eve_intercept_fn=eve, verbose=True)
    qber_history.append({"round": 2, "qber": r2["qber"], "eve_active": True})

    if not r2["success"]:
        events.append({"time": ts(), "message": f"Eavesdropper detected! QBER = {r2['qber']:.2%}", "kind": "danger"})
        events.append({"time": ts(), "message": "Key exchange ABORTED", "kind": "danger"})
    else:
        events.append({"time": ts(), "message": "Eve got lucky — rare but possible", "kind": "info"})

    # ── Round 3: Recovery ────────────────────────────────────────────
    print("\n")
    events.append({"time": ts(), "message": "Round 3 — Recovery (no Eve)", "kind": "info"})
    r3 = run_bb84(num_qubits=256, eve_intercept_fn=None, verbose=True)
    qber_history.append({"round": 3, "qber": r3["qber"], "eve_active": False})

    if r3["success"]:
        events.append({"time": ts(), "message": "New secure key generated ✓", "kind": "success"})

    # ── Classical comparison ─────────────────────────────────────────
    classical = classical_predictable_key(256)
    print(f"\n  Classical key (seed 42, first 32 bits): {classical[:32]}")
    print(f"  Quantum key  (first 32 bits):           {r1['shared_key'][:32] if r1['success'] else 'N/A'}")
    events.append({"time": ts(), "message": "Classical vs Quantum comparison shown", "kind": "info"})

    # ── Dashboard ────────────────────────────────────────────────────
    key_for_viz = r1["shared_key"] if r1["success"] else (r3["shared_key"] if r3["success"] else np.random.randint(0, 2, 64))
    show_dashboard(key_for_viz, qber_history, events)


def _dashboard_only():
    """Quick dashboard with synthetic data."""
    from viz.dashboard import show_dashboard
    fake = np.random.randint(0, 2, 128)
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    show_dashboard(
        fake,
        [
            {"round": 1, "qber": 0.02, "eve_active": False},
            {"round": 2, "qber": 0.26, "eve_active": True},
            {"round": 3, "qber": 0.01, "eve_active": False},
        ],
        [
            {"time": ts, "message": "Key exchange started",       "kind": "info"},
            {"time": ts, "message": "Eavesdropper detected!",     "kind": "danger"},
            {"time": ts, "message": "Session aborted — retrying", "kind": "danger"},
            {"time": ts, "message": "New key generated ✓",        "kind": "success"},
        ],
    )


def main():
    parser = argparse.ArgumentParser(
        description="Quantum‑Secured Chat Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="mode")

    # server
    sp = sub.add_parser("server", help="Start as Alice (server)")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=5555)
    sp.add_argument("--qubits", type=int, default=256)
    sp.add_argument("--eve", action="store_true", help="Enable Eve interceptor")

    # client
    cp = sub.add_parser("client", help="Start as Bob (client)")
    cp.add_argument("--host", default="127.0.0.1")
    cp.add_argument("--port", type=int, default=5555)

    # demo
    sub.add_parser("demo", help="Run non‑interactive full demo")

    # dashboard
    sub.add_parser("dashboard", help="Show visualization dashboard")

    args = parser.parse_args()

    if args.mode == "server":
        srv = ChatServer(args.host, args.port, args.qubits, args.eve)
        srv.start()
    elif args.mode == "client":
        cl = ChatClient(args.host, args.port)
        cl.start()
    elif args.mode == "demo":
        _demo()
    elif args.mode == "dashboard":
        _dashboard_only()
    else:
        # Default to Launcher GUI if no args provided
        from launcher import LauncherGUI
        app = LauncherGUI()
        app.run()


if __name__ == "__main__":
    main()
