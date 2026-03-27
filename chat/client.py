"""
Chat Client — Connects to the quantum‑secured chat server (Bob's side).

On connection Bob receives:
  1. The HKDF salt used by Alice.
  2. The shared key bits (simulation shortcut — in real QKD Bob already
     has his copy from the BB84 measurement).

He then derives the same AES key and enters encrypted chat mode.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import numpy as np

from crypto.aes_encryption import derive_aes_key, encrypt_message, decrypt_message


class ChatClient:
    """TCP chat client with BB84‑derived AES encryption."""

    def __init__(self, host: str = "127.0.0.1", port: int = 5555):
        self.host = host
        self.port = port
        self.aes_key: bytes | None = None
        self.sock: socket.socket | None = None
        self.running = False

    # ── Frame helpers (same as server) ───────────────────────────────
    @staticmethod
    def _send_frame(sock: socket.socket, data: bytes):
        sock.sendall(struct.pack("!I", len(data)) + data)

    @staticmethod
    def _recv_frame(sock: socket.socket) -> bytes:
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

    # ── Key derivation ───────────────────────────────────────────────
    def _receive_key(self):
        """Receive salt + shared bits from server, derive the same AES key."""
        salt = self._recv_frame(self.sock)
        key_bytes = self._recv_frame(self.sock)
        shared_bits = np.frombuffer(key_bytes, dtype=np.uint8)

        self.aes_key, _ = derive_aes_key(shared_bits, salt=salt)
        print("  ✅ Secure AES‑256 key derived from quantum exchange.")

    # ── Receive loop ─────────────────────────────────────────────────
    def _receive_loop(self):
        while self.running:
            try:
                frame = self._recv_frame(self.sock)
                payload = json.loads(frame)
                nonce = bytes.fromhex(payload["nonce"])
                ct    = bytes.fromhex(payload["ciphertext"])
                plaintext = decrypt_message(self.aes_key, nonce, ct)
                print(f"\n  📩 [Alice] {plaintext}")
            except ConnectionError:
                print("  ⚠️  Alice disconnected.")
                self.running = False
                break
            except Exception as e:
                print(f"  ⚠️  Receive error: {e}")
                self.running = False
                break

    # ── Send ─────────────────────────────────────────────────────────
    def send(self, plaintext: str):
        nonce, ct = encrypt_message(self.aes_key, plaintext)
        payload = json.dumps({
            "nonce":      nonce.hex(),
            "ciphertext": ct.hex(),
        }).encode()
        self._send_frame(self.sock, payload)

    # ── Connect and chat ─────────────────────────────────────────────
    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        print(f"  ✅ Connected to server {self.host}:{self.port}")

        self._receive_key()

        self.running = True
        rx = threading.Thread(target=self._receive_loop, daemon=True)
        rx.start()

        print("\n  💬  Type messages to send to Alice (Ctrl+C to quit):\n")
        try:
            while self.running:
                msg = input("  [Bob] > ")
                if msg.strip():
                    self.send(msg)
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            self.running = False
            self.sock.close()
            print("  Client disconnected.")
