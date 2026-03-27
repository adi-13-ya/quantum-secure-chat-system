"""
Chat Server — Hosts the quantum‑secured chat session (Alice's side).

Architecture
────────────
• The server creates a TCP socket and waits for a client (Bob) to connect.
• On connection, BB84 key exchange runs automatically.
• After a shared AES key is established, all messages are encrypted
  with AES-256-GCM before being sent over the wire.
• An optional Eve interceptor can be toggled for demo purposes.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import datetime
import numpy as np

from bb84.protocol import run_bb84
from crypto.aes_encryption import derive_aes_key, encrypt_message, decrypt_message
from attacks.eve import Eve


class ChatServer:
    """TCP chat server with BB84‑derived AES encryption."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5555,
        num_qubits: int = 256,
        eve_enabled: bool = False,
    ):
        self.host = host
        self.port = port
        self.num_qubits = num_qubits
        self.eve_enabled = eve_enabled

        self.aes_key: bytes | None = None
        self.salt: bytes | None = None
        self.conn: socket.socket | None = None
        self.running = False

        # Logging
        self.qber_history: list[dict] = []
        self.events: list[dict] = []
        self.shared_key: np.ndarray | None = None

    # ── Helpers ──────────────────────────────────────────────────────
    def _log(self, message: str, kind: str = "info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        entry = {"time": ts, "message": message, "kind": kind}
        self.events.append(entry)
        symbol = {"info": "ℹ️ ", "success": "✅", "danger": "⚠️ "}
        print(f"  {symbol.get(kind, '')} [{ts}] {message}")

    @staticmethod
    def _send_frame(sock: socket.socket, data: bytes):
        """Send a length‑prefixed frame."""
        sock.sendall(struct.pack("!I", len(data)) + data)

    @staticmethod
    def _recv_frame(sock: socket.socket) -> bytes:
        """Receive a length‑prefixed frame."""
        raw_len = b""
        while len(raw_len) < 4:
            chunk = sock.recv(4 - len(raw_len))
            if not chunk:
                raise ConnectionError("Connection closed")
            raw_len += chunk
        msg_len = struct.unpack("!I", raw_len)[0]
        data = b""
        while len(data) < msg_len:
            chunk = sock.recv(msg_len - len(data))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        return data

    # ── Key exchange ─────────────────────────────────────────────────
    def _perform_key_exchange(self) -> bool:
        """Run BB84 and derive AES key. Returns True on success."""
        eve = Eve(verbose=True) if self.eve_enabled else None
        self._log("Starting BB84 key exchange …")

        result = run_bb84(
            num_qubits=self.num_qubits,
            eve_intercept_fn=eve,
            verbose=True,
        )

        round_num = len(self.qber_history) + 1
        self.qber_history.append({
            "round":      round_num,
            "qber":       result["qber"],
            "eve_active": result["eve_active"],
        })

        if not result["success"]:
            self._log(
                f"Eavesdropper detected! QBER = {result['qber']:.2%}  — aborting.",
                "danger",
            )
            return False

        # Derive AES key
        self.shared_key = result["shared_key"]
        self.aes_key, self.salt = derive_aes_key(result["shared_key"])

        # Send salt to Bob so he can derive the same key
        self._send_frame(self.conn, self.salt)

        # Also send the shared key bits to Bob
        self._send_frame(self.conn, self.shared_key.astype(np.uint8).tobytes())

        self._log(
            f"Secure key established — {len(result['shared_key'])} shared bits, "
            f"QBER = {result['qber']:.2%}",
            "success",
        )
        return True

    # ── Receive loop ─────────────────────────────────────────────────
    def _receive_loop(self):
        """Background thread: receive and decrypt messages."""
        while self.running:
            try:
                frame = self._recv_frame(self.conn)
                payload = json.loads(frame)
                nonce = bytes.fromhex(payload["nonce"])
                ct    = bytes.fromhex(payload["ciphertext"])
                plaintext = decrypt_message(self.aes_key, nonce, ct)
                print(f"\n  📩 [Bob] {plaintext}")
            except ConnectionError:
                self._log("Bob disconnected.", "danger")
                self.running = False
                break
            except Exception as e:
                self._log(f"Receive error: {e}", "danger")
                self.running = False
                break

    # ── Send ─────────────────────────────────────────────────────────
    def send(self, plaintext: str):
        """Encrypt and send a message to Bob."""
        nonce, ct = encrypt_message(self.aes_key, plaintext)
        payload = json.dumps({
            "nonce":      nonce.hex(),
            "ciphertext": ct.hex(),
        }).encode()
        self._send_frame(self.conn, payload)

    # ── Main loop ────────────────────────────────────────────────────
    def start(self):
        """Start the server, accept a connection, and enter chat mode."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(1)
        self._log(f"Server listening on {self.host}:{self.port} …")

        self.conn, addr = srv.accept()
        self._log(f"Bob connected from {addr}", "success")

        # Key exchange (retry if Eve is detected)
        while not self._perform_key_exchange():
            self._log("Retrying key exchange …")

        # Start background receiver
        self.running = True
        rx = threading.Thread(target=self._receive_loop, daemon=True)
        rx.start()

        # Interactive send loop
        print("\n  💬  Type messages to send to Bob (Ctrl+C to quit):\n")
        try:
            while self.running:
                msg = input("  [Alice] > ")
                if msg.strip():
                    self.send(msg)
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self.running = False
            self.conn.close()
            srv.close()
            self._log("Server shut down.", "info")
