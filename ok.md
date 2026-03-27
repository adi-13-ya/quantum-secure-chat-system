Phase 1 — Day 1: Quantum foundations + environment setup
What you need to learn (quantum basics — taught here):
You already know cryptography, so think in terms of keys and bits. Here's what's new:
A qubit is like a classical bit (0 or 1), but before you measure it, it exists in superposition — simultaneously 0 and 1 with some probability. The moment you measure it, it collapses to one value. This is not a software trick — it's a physical property. The key insight for security: if an attacker measures a qubit in transit, the qubit's state is permanently disturbed. You can detect the interference.
A quantum basis is the "angle" at which you measure a qubit. BB84 uses two bases — rectilinear (+) and diagonal (×). If Alice sends a qubit in one basis and Bob measures in the wrong basis, his result is random noise. This is the foundation of BB84.
What you'll do:

Spend 3–4 hours reading BB84 theory (IBM Qiskit documentation is excellent)
Install tools: pip install qiskit cryptography and pip install matplotlib for visualization later
Create your project folder structure:

quantum_chat/
├── bb84/          ← key exchange logic
├── crypto/        ← AES encryption
├── chat/          ← socket server & client
├── attacks/       ← MITM simulation
├── viz/           ← dashboard & graphs
└── main.py
What you'll have at end of Day 1: A working Qiskit installation, understanding of BB84 protocol, and project skeleton ready.

Phase 2 — Day 2: Implement BB84 key exchange
What you'll build: A Python module that simulates Alice and Bob performing BB84.
The BB84 protocol works like this:

Alice generates random bits and random bases, encodes qubits and sends them
Bob measures each qubit in a randomly chosen basis
They publicly compare which bases they used (not the bits themselves)
Where bases matched → those bits form the shared secret key
They calculate QBER (Quantum Bit Error Rate) — if it's above ~11%, an eavesdropper is present

You'll implement this entirely in simulation using Qiskit's QuantumCircuit. No real quantum hardware needed — the simulator gives you true quantum randomness behavior.
Key functions to write: generate_qubits(), measure_qubits(), sift_key(), calculate_qber()
Required: Qiskit, NumPy
End of Day 2: A standalone bb84.py that produces a shared secret key between two parties.

Phase 3 — Day 3: AES encryption + key derivation
What you'll build: Bridge between the quantum key and actual message encryption.
BB84 gives you a string of bits — but AES-256 needs exactly 256 bits. You'll use HKDF (HMAC-based Key Derivation Function) from Python's cryptography library to stretch/derive a proper AES key from the BB84 output. Then implement:

encrypt_message(key, plaintext) → returns ciphertext
decrypt_message(key, ciphertext) → returns plaintext
Use AES in GCM mode (provides both encryption and authentication — resists tampering)

Why this matters for your project: This is where you fix the "predictable key generation" weakness. Classical apps use random.random() or system clocks. Your app uses quantum measurement — which is fundamentally unpredictable even in principle.
Required: cryptography library (pip install cryptography)
End of Day 3: Full encryption pipeline — quantum key in, encrypted message out.

Phase 4 — Day 4: Chat application
What you'll build: A two-terminal chat app using Python sockets.
The flow when two users connect:

Handshake → BB84 key exchange runs automatically
Key derived → AES-256 session key established
Every message typed → encrypted before sending over socket
Receiver → decrypts and displays

Use Python's socket and threading libraries. For the UI, a Tkinter window is enough for a demo — gives you a proper GUI without a web framework. Run Alice in one terminal/window, Bob in another on the same machine (localhost) or two machines on the same network.
End of Day 4: Two people can chat. Messages are encrypted. An observer sniffing the network sees only ciphertext.

Phase 5 — Day 5: Attack simulation module ⬅ This is your star feature
What you'll build: An Eve class that intercepts and demonstrates why QKD defeats MITM.
This is what makes your demo unforgettable. Here's the attack and why it fails:
A classical MITM attack works because the attacker intercepts and re-forwards messages without leaving a trace. In BB84, Eve cannot do this — if she intercepts qubits and measures them, she must re-send new qubits to Bob. But she doesn't know Alice's basis, so she guesses wrong ~50% of the time, and re-sends incorrect qubits. When Alice and Bob compare a random sample of their key bits, they find errors. QBER spikes above the safe threshold → they abort and try again.
What your module will show:

Eve.intercept() — randomly measures and resends qubits
After Eve is active, QBER jumps from ~1% to ~25%
System detects anomaly → prints "⚠ Eavesdropper detected. Key exchange aborted."
Without Eve → QBER stays low → chat proceeds normally

End of Day 5: You can toggle Eve on/off and demonstrate the detection live.

Phase 6 — Day 6: Comparison dashboard + visualization
What you'll build: A matplotlib dashboard that makes the security story visual.
Panels to include:

Panel 1: Classical key (predictable pseudo-random) vs Quantum key (entropy plot) — show the difference in randomness quality
Panel 2: QBER over time — flat line (no attack) vs spike (Eve present)
Panel 3: Attack log — timestamped events like "Key exchange started", "Eavesdropper detected", "Session aborted", "New key generated"
Panel 4: Key bit distribution histogram — showing quantum keys are uniformly distributed

This dashboard is what you show in your viva or demo. It tells the whole story visually.

Phase 7 — Day 7: Testing, documentation, demo prep
What you'll do:

Run full end-to-end tests: normal chat, chat with Eve active, chat with network noise
Write a 1–2 page project report covering: problem statement, BB84 explanation, system design, attack demo results, comparison with classical systems
Prepare a 5-minute live demo script (see below)


How to demonstrate it
Here is your exact demo script for presenting to evaluators:
Step 1 — Normal chat (2 min): Open Alice and Bob terminals. Show them exchanging messages. Open Wireshark or just show the raw socket log — evaluator sees only gibberish ciphertext. Say: "All messages are AES-256 encrypted with a quantum-generated key."
Step 2 — Activate Eve (2 min): Run the attack simulation. Show QBER rising on the dashboard. System prints the warning message. Key exchange is aborted. Say: "Eve measured the qubits. This disturbed their quantum state — exactly as quantum mechanics predicts. The system detected the anomaly and refused to establish the session."
Step 3 — Classical comparison (1 min): Show a classical key generator producing a predictable sequence (seed the random number generator with a fixed value). Compare entropy plots. Say: "A classical system's key can be predicted if the seed is known. Our quantum key has no seed — it's generated from quantum measurement outcomes."
This three-step demo answers every evaluator question before they ask it.

Quick quantum glossary (save this)
TermWhat it meansQubitQuantum bit — can be 0, 1, or superposition of bothSuperpositionExisting in multiple states simultaneously until measuredMeasurement collapseMeasuring a qubit forces it to pick a definite value — and disturbs itBasisThe "direction" you measure in — rectilinear (+) or diagonal (×) in BB84QBERQuantum Bit Error Rate — the percentage of mismatched bits; high QBER = eavesdropperKey siftingKeeping only the bits where Alice and Bob used the same basis