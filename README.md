# 🔐 Quantum-Secured Chat Application

A real-time, GUI-based encrypted chat application that uses **BB84 Quantum Key Distribution (QKD)** for key exchange and **AES-256-GCM** for message encryption. It includes a built-in **MITM attack simulator** that demonstrates exactly why quantum cryptography guarantees absolute secrecy by detecting eavesdropping attempts through physical quantum interference (No-Cloning Theorem).

## Architecture

```
quantum_chat/
├── bb84/              ← BB84 QKD protocol (Qiskit simulation)
│   ├── __init__.py
│   └── protocol.py    ← generate_qubits, measure, sift, QBER calculation
├── crypto/            ← Classical Cryptography
│   ├── __init__.py
│   └── aes_encryption.py  ← HKDF key derivation, AES-256-GCM encrypt/decrypt
├── chat/              ← Communication Layer & GUI
│   ├── __init__.py
│   ├── server.py      ← Alice (TCP server - CLI)
│   ├── client.py      ← Bob (TCP client - CLI)
│   └── gui.py         ← Tkinter GUI for unified chatting
├── attacks/           ← Security Evaluation
│   ├── __init__.py
│   └── eve.py         ← Eve MITM interceptor class
├── viz/               ← Matplotlib security dashboard
│   ├── __init__.py
│   └── dashboard.py   ← 4-panel visualizer
├── main.py            ← Universal Entry Point
├── launcher.py        ← Beautiful GUI Setup Wizard
└── requirements.txt
```

## Quick Start (GUI Mode)

The easiest way to experience the project is through the unified graphical user interface (GUI).

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the application!
python3 main.py
```

### Starting a Chat Session
1. **Window 1 (Alice):** Run `python3 main.py`, optionally check the **Simulate Eavesdropper (Eve)** box if you want to test the attack, and click **Create Session (Alice)**.
2. **Window 2 (Bob):** Run `python3 main.py` in a separate terminal and click **Join Session (Bob)**.
3. The quantum handshake will run automatically in the background, derive a secure AES-256 key if the quantum link is uncompromised, and allow you to chat in real-time!

## Usage Modes (CLI)

If you prefer using the terminal over the GUI, you can access the core modules directly:

### 1. Terminal Chat (Two terminals)

```bash
# Terminal 1 — Alice (server)
python3 main.py server

# Terminal 2 — Bob (client)
python3 main.py client
```

### 2. Eavesdropping Attack Simulation (Command Line)

```bash
# Terminal 1 — Alice with Eve maliciously tapping the wire
python3 main.py server --eve

# Terminal 2 — Bob
python3 main.py client
```

### 3. Verification Dashboard

Run the standalone verification dashboard to see real-time plots of Quantum vs Classical key exchanges, QBER thresholds, and probability matrices:
```bash
python3 main.py dashboard
```

## How It Works

### BB84 Quantum Key Exchange
1. **Alice** generates random bits & random bases, encodes them into qubits, and transmits them to Bob.
2. **Bob** receives the quantum states and measures each qubit in a randomly chosen basis.
3. They publicly compare their chosen bases (not the bit values) over a classical channel → the bits where their bases matched perfectly form the **sifted key**.
4. **QBER Analysis** — they compare a subset of the sifted key. If the Quantum Bit Error Rate (QBER) exceeds ~11%, it mathematically guarantees an eavesdropper is present, and the system aborts.

### AES-256-GCM Encryption
- **HKDF** securely derives a uniform 256-bit AES cryptographic session key purely from the unpredictable quantum sifted key.
- Every message sent over the TCP socket is encrypted using **AES-GCM (Galois/Counter Mode)**, preventing both decryption and malicious tampering/forging of messages (Authenticated Encryption).

### Eve Attack Detection (MITM)
- Because of Quantum Mechanics (specifically the *No-Cloning Theorem*), Eve cannot physically duplicate an unknown quantum state.
- She is forced to intercept the qubits, measure them (guessing the basis 50% of the time), and re-transmit new qubits to Bob.
- This physical interference irreversibly collapses the quantum states, inherently introducing a ~25% QBER (far above the safe 11% threshold).
- Alice & Bob instantly detect the anomaly on the wire, loudly reject the handshake, and drop the connection.

## Dependencies

- `qiskit` + `qiskit-aer` — Hardware-accurate quantum circuit simulation
- `cryptography` — Military-grade AES-256-GCM authenticated encryption + HKDF
- `numpy` — Fast numerical operations and bit logic
- `matplotlib` — Verification dashboard visualization
- `tkinter` — Front-end GUI (Built-in with Python distributions)
