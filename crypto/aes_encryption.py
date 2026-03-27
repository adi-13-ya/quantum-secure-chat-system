"""
AES-256-GCM Encryption / Decryption with Quantum‑Derived Key.

Uses HKDF to derive a proper 256‑bit AES key from the raw BB84 output,
then encrypts/decrypts messages with AES in GCM mode (authenticated
encryption — tamper‑proof).
"""

import os
import numpy as np

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


# ── Key derivation ───────────────────────────────────────────────────
def bits_to_bytes(bits: np.ndarray) -> bytes:
    """Convert a numpy array of 0/1 bits into a bytes object."""
    # Pad to multiple of 8
    padded = np.pad(bits, (0, (8 - len(bits) % 8) % 8), constant_values=0)
    byte_vals = np.packbits(padded)
    return bytes(byte_vals)


def derive_aes_key(
    quantum_bits: np.ndarray,
    salt: bytes | None = None,
    info: bytes = b"quantum-chat-aes-key",
) -> bytes:
    """
    Derive a 256‑bit AES key from BB84 sifted key bits using HKDF‑SHA256.

    Parameters
    ----------
    quantum_bits : ndarray
        Raw sifted key bits from BB84 (any length ≥ 1).
    salt : bytes | None
        Optional salt for HKDF.  If None, a random 16‑byte salt is used.
    info : bytes
        Context / application info for HKDF.

    Returns
    -------
    tuple[bytes, bytes]
        (aes_key, salt)  — 32‑byte key + salt used.
    """
    raw_key_material = bits_to_bytes(quantum_bits)

    if salt is None:
        salt = os.urandom(16)

    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,           # 256 bits
        salt=salt,
        info=info,
    )
    aes_key = hkdf.derive(raw_key_material)
    return aes_key, salt


# ── Encryption ───────────────────────────────────────────────────────
def encrypt_message(key: bytes, plaintext: str) -> tuple[bytes, bytes]:
    """
    Encrypt *plaintext* with AES-256-GCM.

    Returns
    -------
    (nonce, ciphertext)   — both are bytes objects.
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)   # 96‑bit nonce for GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce, ciphertext


# ── Decryption ───────────────────────────────────────────────────────
def decrypt_message(key: bytes, nonce: bytes, ciphertext: bytes) -> str:
    """
    Decrypt AES-256-GCM *ciphertext* back to a string.

    Raises cryptography.exceptions.InvalidTag if tampered.
    """
    aesgcm = AESGCM(key)
    plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext_bytes.decode("utf-8")
