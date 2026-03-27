"""
Visualization Dashboard — matplotlib panels for the quantum chat demo.

Panels
------
1. Classical vs Quantum key entropy comparison
2. QBER over multiple key‑exchange rounds
3. Attack event log timeline
4. Key bit distribution histogram
"""

from __future__ import annotations

import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from attacks.eve import classical_predictable_key


# ── Colour palette ───────────────────────────────────────────────────
_BG      = "#0d1117"
_FG      = "#c9d1d9"
_ACCENT  = "#58a6ff"
_DANGER  = "#f85149"
_SUCCESS = "#3fb950"
_MUTED   = "#484f58"


def _style_ax(ax, title: str):
    """Apply dark‑mode styling to an Axes."""
    ax.set_facecolor(_BG)
    ax.set_title(title, color=_FG, fontsize=12, fontweight="bold", pad=10)
    ax.tick_params(colors=_FG, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(_MUTED)


# ── Panel helpers ────────────────────────────────────────────────────

def _panel_entropy(ax, quantum_key: np.ndarray):
    """Panel 1: classical vs quantum key entropy (autocorrelation)."""
    classical = classical_predictable_key(len(quantum_key))

    def autocorr(x, max_lag=50):
        x = x.astype(float) - x.mean()
        result = np.correlate(x, x, mode="full")
        result = result[len(result)//2:]
        result /= result[0] if result[0] != 0 else 1
        return result[:max_lag]

    lags = np.arange(min(50, len(quantum_key)))
    ax.plot(lags, autocorr(classical, len(lags)),
            color=_DANGER, label="Classical (seeded PRNG)", linewidth=1.5)
    ax.plot(lags, autocorr(quantum_key, len(lags)),
            color=_ACCENT, label="Quantum (BB84)", linewidth=1.5)
    ax.axhline(0, color=_MUTED, linewidth=0.5, linestyle="--")
    _style_ax(ax, "Key Autocorrelation — Randomness Quality")
    ax.set_xlabel("Lag", color=_FG, fontsize=9)
    ax.set_ylabel("Autocorrelation", color=_FG, fontsize=9)
    ax.legend(fontsize=8, facecolor=_BG, edgecolor=_MUTED, labelcolor=_FG)


def _panel_qber(ax, qber_history: list[dict]):
    """Panel 2: QBER over time."""
    rounds  = [h["round"] for h in qber_history]
    qbers   = [h["qber"]  for h in qber_history]
    colours = [_DANGER if h.get("eve_active") else _SUCCESS for h in qber_history]

    ax.bar(rounds, qbers, color=colours, width=0.6, edgecolor=_MUTED)
    ax.axhline(0.11, color=_DANGER, linewidth=1, linestyle="--", label="Threshold (11 %)")
    _style_ax(ax, "QBER per Key‑Exchange Round")
    ax.set_xlabel("Round", color=_FG, fontsize=9)
    ax.set_ylabel("QBER", color=_FG, fontsize=9)
    ax.set_ylim(0, max(max(qbers) * 1.3, 0.15))
    ax.legend(fontsize=8, facecolor=_BG, edgecolor=_MUTED, labelcolor=_FG)


def _panel_log(ax, events: list[dict]):
    """Panel 3: Attack event log."""
    ax.axis("off")
    _style_ax(ax, "Attack Event Log")

    if not events:
        ax.text(0.5, 0.5, "No events yet.", color=_MUTED,
                ha="center", va="center", fontsize=10, transform=ax.transAxes)
        return

    lines = []
    for ev in events[-12:]:  # show last 12
        ts   = ev.get("time", "")
        msg  = ev.get("message", "")
        kind = ev.get("kind", "info")
        colour = _DANGER if kind == "danger" else _SUCCESS if kind == "success" else _FG
        lines.append((ts, msg, colour))

    y = 0.95
    for ts, msg, col in lines:
        ax.text(0.02, y, f"[{ts}]", color=_MUTED, fontsize=7,
                transform=ax.transAxes, family="monospace")
        ax.text(0.22, y, msg, color=col, fontsize=8,
                transform=ax.transAxes, family="monospace")
        y -= 0.08


def _panel_distribution(ax, quantum_key: np.ndarray):
    """Panel 4: Key bit distribution histogram."""
    zeros = np.sum(quantum_key == 0)
    ones  = np.sum(quantum_key == 1)
    bars  = ax.bar(["0", "1"], [zeros, ones],
                   color=[_ACCENT, _SUCCESS], edgecolor=_MUTED, width=0.5)
    _style_ax(ax, "Key Bit Distribution (should be ~50/50)")
    ax.set_ylabel("Count", color=_FG, fontsize=9)
    for bar, val in zip(bars, [zeros, ones]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                str(val), ha="center", color=_FG, fontsize=9)


# ── Main dashboard ───────────────────────────────────────────────────

def show_dashboard(
    quantum_key: np.ndarray,
    qber_history: list[dict],
    events: list[dict],
):
    """
    Render the full 4‑panel security dashboard.

    Parameters
    ----------
    quantum_key : ndarray
        Final shared key bits from a successful BB84 run.
    qber_history : list[dict]
        Each dict: {"round": int, "qber": float, "eve_active": bool}
    events : list[dict]
        Each dict: {"time": str, "message": str, "kind": "info"|"success"|"danger"}
    """
    fig = plt.figure(figsize=(14, 8), facecolor=_BG)
    fig.suptitle("🔐 Quantum‑Secured Chat — Security Dashboard",
                 color=_FG, fontsize=16, fontweight="bold", y=0.98)

    gs = gridspec.GridSpec(2, 2, hspace=0.35, wspace=0.3,
                           left=0.06, right=0.96, top=0.90, bottom=0.06)

    _panel_entropy(fig.add_subplot(gs[0, 0]), quantum_key)
    _panel_qber(fig.add_subplot(gs[0, 1]), qber_history)
    _panel_log(fig.add_subplot(gs[1, 0]), events)
    _panel_distribution(fig.add_subplot(gs[1, 1]), quantum_key)

    plt.show()


# ── Standalone quick test ────────────────────────────────────────────
if __name__ == "__main__":
    # Fake data for preview
    fake_key = np.random.randint(0, 2, 128)
    history  = [
        {"round": 1, "qber": 0.02, "eve_active": False},
        {"round": 2, "qber": 0.25, "eve_active": True},
        {"round": 3, "qber": 0.03, "eve_active": False},
    ]
    now = datetime.datetime.now().strftime("%H:%M:%S")
    evts = [
        {"time": now, "message": "Key exchange started",        "kind": "info"},
        {"time": now, "message": "Eavesdropper detected!",      "kind": "danger"},
        {"time": now, "message": "Session aborted — retrying",  "kind": "danger"},
        {"time": now, "message": "New key generated ✓",         "kind": "success"},
    ]
    show_dashboard(fake_key, history, evts)
