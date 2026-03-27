"""
Tkinter GUI Chat Application — Quantum‑Secured Chat with BB84.

Provides a proper windowed GUI for both Alice (server) and Bob (client),
with visual indicators for quantum key exchange status, QBER, and
encrypted message display.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import datetime
import tkinter as tk
from tkinter import scrolledtext, messagebox
import numpy as np

from bb84.protocol import run_bb84
from crypto.aes_encryption import derive_aes_key, encrypt_message, decrypt_message
from attacks.eve import Eve


# ── Colour theme ─────────────────────────────────────────────────────
_BG       = "#0d1117"
_BG2      = "#161b22"
_FG       = "#c9d1d9"
_ACCENT   = "#58a6ff"
_SUCCESS  = "#3fb950"
_DANGER   = "#f85149"
_MUTED    = "#484f58"
_INPUT_BG = "#21262d"


class QuantumChatGUI:
    """Tkinter GUI for the quantum‑secured chat."""

    def __init__(self, role: str = "server", host: str = "127.0.0.1",
                 port: int = 5555, num_qubits: int = 256,
                 eve_enabled: bool = False):
        self.role = role
        self.host = host
        self.port = port
        self.num_qubits = num_qubits
        self.eve_enabled = eve_enabled

        self.aes_key: bytes | None = None
        self.sock: socket.socket | None = None
        self.conn: socket.socket | None = None
        self.running = False

        self.qber_history: list[dict] = []
        self.events: list[dict] = []
        self.shared_key: np.ndarray | None = None

        self._build_ui()

    # ── UI Construction ──────────────────────────────────────────────
    def _build_ui(self):
        self.root = tk.Tk()
        name = "Alice (Server)" if self.role == "server" else "Bob (Client)"
        self.root.title(f"🔐 Quantum Chat — {name}")
        self.root.configure(bg=_BG)
        self.root.geometry("700x600")
        self.root.minsize(500, 400)

        # ── Header ───────────────────────────────────────────────────
        header = tk.Frame(self.root, bg=_BG2, pady=8)
        header.pack(fill=tk.X)

        tk.Label(header, text=f"🔐 Quantum‑Secured Chat — {name}",
                 bg=_BG2, fg=_ACCENT, font=("Menlo", 14, "bold")).pack(side=tk.LEFT, padx=12)

        self.status_label = tk.Label(header, text="● Disconnected",
                                     bg=_BG2, fg=_DANGER, font=("Menlo", 10))
        self.status_label.pack(side=tk.RIGHT, padx=12)

        # ── QBER indicator ───────────────────────────────────────────
        info_bar = tk.Frame(self.root, bg=_BG, pady=4)
        info_bar.pack(fill=tk.X)

        self.qber_label = tk.Label(info_bar, text="QBER: —",
                                    bg=_BG, fg=_MUTED, font=("Menlo", 9))
        self.qber_label.pack(side=tk.LEFT, padx=12)

        self.key_label = tk.Label(info_bar, text="Key: —",
                                   bg=_BG, fg=_MUTED, font=("Menlo", 9))
        self.key_label.pack(side=tk.RIGHT, padx=12)

        # ── Chat display ─────────────────────────────────────────────
        self.chat_display = scrolledtext.ScrolledText(
            self.root, bg=_BG, fg=_FG, font=("Menlo", 11),
            insertbackground=_FG, selectbackground=_ACCENT,
            wrap=tk.WORD, state=tk.DISABLED, borderwidth=0,
            padx=12, pady=8,
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 0))

        # Tag styles
        self.chat_display.tag_config("system",  foreground=_MUTED, font=("Menlo", 9, "italic"))
        self.chat_display.tag_config("success", foreground=_SUCCESS)
        self.chat_display.tag_config("danger",  foreground=_DANGER)
        self.chat_display.tag_config("sent",    foreground=_ACCENT)
        self.chat_display.tag_config("received",foreground=_SUCCESS)
        self.chat_display.tag_config("crypto",  foreground=_MUTED, font=("Menlo", 8))

        # ── Input area ───────────────────────────────────────────────
        input_frame = tk.Frame(self.root, bg=_BG, pady=8)
        input_frame.pack(fill=tk.X, padx=8)

        self.msg_entry = tk.Entry(
            input_frame, bg=_INPUT_BG, fg=_FG, font=("Menlo", 11),
            insertbackground=_FG, borderwidth=0, relief=tk.FLAT,
        )
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=6)
        self.msg_entry.bind("<Return>", self._on_send)

        self.send_btn = tk.Button(
            input_frame, text="Send 🔒", bg=_ACCENT, fg="#0d1117",
            font=("Menlo", 10, "bold"), borderwidth=0,
            activebackground="#79c0ff", command=self._on_send,
            padx=16, pady=4,
        )
        self.send_btn.pack(side=tk.RIGHT)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Chat display helpers ─────────────────────────────────────────
    def _append(self, text: str, tag: str = ""):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, text + "\n", tag)
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def _set_status(self, text: str, color: str):
        self.status_label.config(text=text, fg=color)

    # ── Frame helpers ────────────────────────────────────────────────
    @staticmethod
    def _send_frame(sock: socket.socket, data: bytes):
        sock.sendall(struct.pack("!I", len(data)) + data)

    @staticmethod
    def _recv_frame(sock: socket.socket) -> bytes:
        raw_len = b""
        while len(raw_len) < 4:
            try:
                chunk = sock.recv(4 - len(raw_len))
            except OSError:
                raise ConnectionError("Connection closed")
            if not chunk:
                raise ConnectionError("Connection closed")
            raw_len += chunk
        msg_len = struct.unpack("!I", raw_len)[0]
        data = b""
        while len(data) < msg_len:
            try:
                chunk = sock.recv(msg_len - len(data))
            except OSError:
                raise ConnectionError("Connection closed")
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        return data

    # ── Server logic ─────────────────────────────────────────────────
    def _server_thread(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(1)

        self.root.after(0, lambda: self._append(
            f"  Listening on {self.host}:{self.port} …", "system"))
        self.root.after(0, lambda: self._set_status("● Waiting …", _MUTED))

        self.conn, addr = srv.accept()
        self.root.after(0, lambda: self._append(
            f"  Bob connected from {addr}", "success"))
        self.root.after(0, lambda: self._set_status("● Connected", _SUCCESS))

        # BB84 key exchange
        self.root.after(0, lambda: self._append(
            "  Starting BB84 quantum key exchange …", "system"))

        try:
            config_frame = self._recv_frame(self.conn)
            config = json.loads(config_frame)
        except ConnectionError:
            self.root.after(0, lambda: self._append("  ❌ Client disconnected early", "danger"))
            return

        eve_active = self.eve_enabled or config.get("eve_enabled", False)
        eve = Eve(verbose=False) if eve_active else None
        result = run_bb84(self.num_qubits, eve_intercept_fn=eve, verbose=False)

        qber = result["qber"]
        self.root.after(0, lambda: self.qber_label.config(
            text=f"QBER: {qber:.2%}", fg=_DANGER if qber >= 0.11 else _SUCCESS))

        # Send result to Bob so he can also see the error
        result_payload = json.dumps({"success": bool(result["success"]), "qber": float(qber)}).encode()
        try:
            self._send_frame(self.conn, result_payload)
        except ConnectionError:
            return

        if not result["success"]:
            self.root.after(0, lambda: self._append(
                f"  ⚠️  EAVESDROPPER DETECTED! QBER = {qber:.2%}", "danger"))
            self.root.after(0, lambda: self._append(
                "  Key exchange ABORTED.", "danger"))
            self.root.after(0, lambda: self._set_status("● COMPROMISED", _DANGER))
            if self.conn:
                self.conn.close()
            srv.close()
            return

        self.shared_key = result["shared_key"]
        self.aes_key, salt = derive_aes_key(result["shared_key"])
        self._send_frame(self.conn, salt)
        self._send_frame(self.conn, self.shared_key.astype(np.uint8).tobytes())

        key_hex = self.aes_key[:8].hex() + "…"
        self.root.after(0, lambda: self.key_label.config(
            text=f"Key: {key_hex}", fg=_SUCCESS))
        self.root.after(0, lambda: self._append(
            f"  ✅ Secure key established — {len(result['shared_key'])} bits", "success"))
        self.root.after(0, lambda: self._set_status("● Secure 🔒", _SUCCESS))

        self.running = True
        self._receive_loop(self.conn)

    # ── Client logic ─────────────────────────────────────────────────
    def _client_thread(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.host, self.port))
        except ConnectionRefusedError:
            self.root.after(0, lambda: self._append(
                "  ❌ Could not connect — is the server running?", "danger"))
            return

        self.root.after(0, lambda: self._append(
            f"  Connected to {self.host}:{self.port}", "success"))
        self.root.after(0, lambda: self._set_status("● Connected", _SUCCESS))

        # Send initial config to server
        config_payload = json.dumps({"eve_enabled": self.eve_enabled}).encode()
        try:
            self._send_frame(self.sock, config_payload)
            # Receive BB84 result
            result_frame = self._recv_frame(self.sock)
            result = json.loads(result_frame)
        except ConnectionError:
            self.root.after(0, lambda: self._append("  ❌ Connection closed by server", "danger"))
            self.root.after(0, lambda: self._set_status("● Disconnected", _DANGER))
            return

        qber = result["qber"]
        self.root.after(0, lambda: self.qber_label.config(
            text=f"QBER: {qber:.2%}", fg=_DANGER if qber >= 0.11 else _SUCCESS))

        if not result["success"]:
            self.root.after(0, lambda: self._append(
                f"  ⚠️  EAVESDROPPER DETECTED! QBER = {qber:.2%}", "danger"))
            self.root.after(0, lambda: self._append("  Key exchange ABORTED.", "danger"))
            self.root.after(0, lambda: self._set_status("● COMPROMISED", _DANGER))
            self.sock.close()
            return

        # Receive key material
        salt = self._recv_frame(self.sock)
        key_bytes = self._recv_frame(self.sock)

        shared_bits = np.frombuffer(key_bytes, dtype=np.uint8)
        self.aes_key, _ = derive_aes_key(shared_bits, salt=salt)

        key_hex = self.aes_key[:8].hex() + "…"
        self.root.after(0, lambda: self.key_label.config(
            text=f"Key: {key_hex}", fg=_SUCCESS))
        self.root.after(0, lambda: self._append(
            "  ✅ Secure AES‑256 key derived from quantum exchange", "success"))
        self.root.after(0, lambda: self._set_status("● Secure 🔒", _SUCCESS))

        self.running = True
        self._receive_loop(self.sock)

    # ── Receive loop ─────────────────────────────────────────────────
    def _receive_loop(self, sock: socket.socket):
        other = "Bob" if self.role == "server" else "Alice"
        while self.running:
            try:
                frame = self._recv_frame(sock)
                payload = json.loads(frame)
                nonce = bytes.fromhex(payload["nonce"])
                ct = bytes.fromhex(payload["ciphertext"])
                plaintext = decrypt_message(self.aes_key, nonce, ct)

                ct_preview = ct[:20].hex() + "…"
                self.root.after(0, lambda p=plaintext: self._append(
                    f"  [{other}] {p}", "received"))
                self.root.after(0, lambda c=ct_preview: self._append(
                    f"      cipher: {c}", "crypto"))
            except ConnectionError:
                self.root.after(0, lambda: self._append(
                    f"  {other} disconnected.", "danger"))
                self.root.after(0, lambda: self._set_status("● Disconnected", _DANGER))
                self.running = False
                break
            except Exception as e:
                self.root.after(0, lambda err=str(e): self._append(
                    f"  Error: {err}", "danger"))
                self.running = False
                break

    # ── Send ─────────────────────────────────────────────────────────
    def _on_send(self, event=None):
        msg = self.msg_entry.get().strip()
        if not msg or not self.aes_key:
            return
        self.msg_entry.delete(0, tk.END)

        nonce, ct = encrypt_message(self.aes_key, msg)
        payload = json.dumps({
            "nonce": nonce.hex(),
            "ciphertext": ct.hex(),
        }).encode()

        me = "Alice" if self.role == "server" else "Bob"
        target = self.conn if self.role == "server" else self.sock
        try:
            self._send_frame(target, payload)
            ct_preview = ct[:20].hex() + "…"
            self._append(f"  [{me}] {msg}", "sent")
            self._append(f"      cipher: {ct_preview}", "crypto")
        except Exception as e:
            self._append(f"  Send error: {e}", "danger")

    # ── Close ────────────────────────────────────────────────────────
    def _on_close(self):
        self.running = False
        try:
            if self.conn:
                self.conn.close()
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.root.destroy()

    # ── Start ────────────────────────────────────────────────────────
    def start(self):
        target = self._server_thread if self.role == "server" else self._client_thread
        t = threading.Thread(target=target, daemon=True)
        t.start()
        self.root.mainloop()
