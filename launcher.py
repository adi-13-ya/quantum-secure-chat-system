"""
Tkinter Launcher for Quantum Chat.

Provides a unified start screen where the user can choose to be Alice (server)
or Bob (client), configure the host and port, and then launch the appropriate
GUI chat window.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from chat.gui import QuantumChatGUI

# ── Colour theme ─────────────────────────────────────────────────────
_BG       = "#0d1117"
_BG2      = "#161b22"
_FG       = "#c9d1d9"
_ACCENT   = "#58a6ff"
_SUCCESS  = "#3fb950"
_MUTED    = "#484f58"
_INPUT_BG = "#21262d"

class LauncherGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🔐 Quantum Chat — Launcher")
        self.root.configure(bg=_BG)
        self.root.geometry("400x350")
        self.root.resizable(False, False)

        # Basic centering
        self.root.eval('tk::PlaceWindow . center')

        # Header
        header = tk.Label(self.root, text="Quantum-Secured Chat", bg=_BG, fg=_ACCENT, font=("Menlo", 16, "bold"))
        header.pack(pady=(20, 10))

        subtitle = tk.Label(self.root, text="Select your role to begin real-time chat", bg=_BG, fg=_MUTED, font=("Menlo", 10))
        subtitle.pack(pady=(0, 20))

        # Host and Port inputs
        settings_frame = tk.Frame(self.root, bg=_BG)
        settings_frame.pack(fill=tk.X, padx=40, pady=10)

        tk.Label(settings_frame, text="Host IP:", bg=_BG, fg=_FG, font=("Menlo", 10)).grid(row=0, column=0, sticky="w", pady=5)
        self.host_entry = tk.Entry(settings_frame, bg=_INPUT_BG, fg=_FG, insertbackground=_FG, borderwidth=0, font=("Menlo", 10))
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.grid(row=0, column=1, sticky="w", padx=10, pady=5)

        tk.Label(settings_frame, text="Port:", bg=_BG, fg=_FG, font=("Menlo", 10)).grid(row=1, column=0, sticky="w", pady=5)
        self.port_entry = tk.Entry(settings_frame, bg=_INPUT_BG, fg=_FG, insertbackground=_FG, borderwidth=0, font=("Menlo", 10))
        self.port_entry.insert(0, "5555")
        self.port_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)

        # Eve Option
        self.eve_var = tk.BooleanVar(value=False)
        self.eve_check = tk.Checkbutton(settings_frame, text="Simulate Eavesdropper (Eve)", variable=self.eve_var, bg=_BG, fg=_SUCCESS, selectcolor=_BG2, activebackground=_BG, activeforeground=_SUCCESS, font=("Menlo", 10))
        self.eve_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

        # Buttons
        btn_frame = tk.Frame(self.root, bg=_BG)
        btn_frame.pack(fill=tk.X, padx=40, pady=20)

        server_btn = tk.Button(btn_frame, text="Create Session (Alice)", bg=_ACCENT, fg="#0d1117", font=("Menlo", 11, "bold"), borderwidth=0, command=self._launch_server)
        server_btn.pack(fill=tk.X, pady=5, ipady=4)

        client_btn = tk.Button(btn_frame, text="Join Session (Bob)", bg=_SUCCESS, fg="#0d1117", font=("Menlo", 11, "bold"), borderwidth=0, command=self._launch_client)
        client_btn.pack(fill=tk.X, pady=5, ipady=4)

    def _get_config(self):
        host = self.host_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Port must be an integer.")
            return None
        return host, port

    def _launch_server(self):
        config = self._get_config()
        if not config: return
        host, port = config
        eve = self.eve_var.get()
        self.root.destroy()
        gui = QuantumChatGUI(role="server", host=host, port=port, eve_enabled=eve)
        gui.start()

    def _launch_client(self):
        config = self._get_config()
        if not config: return
        host, port = config
        eve = self.eve_var.get()
        self.root.destroy()
        gui = QuantumChatGUI(role="client", host=host, port=port, eve_enabled=eve)
        gui.start()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = LauncherGUI()
    app.run()
