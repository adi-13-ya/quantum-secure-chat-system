"""
Tkinter GUI Launcher — Start the quantum chat GUI from the command line.

Usage
─────
  python gui_launcher.py server                  # Alice (server) GUI
  python gui_launcher.py server --eve            # Alice with Eve active
  python gui_launcher.py client                  # Bob   (client) GUI
"""

import argparse
from chat.gui import QuantumChatGUI


def main():
    parser = argparse.ArgumentParser(description="Quantum Chat GUI Launcher")
    sub = parser.add_subparsers(dest="mode")

    sp = sub.add_parser("server", help="Start as Alice (server)")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=5555)
    sp.add_argument("--qubits", type=int, default=256)
    sp.add_argument("--eve", action="store_true", help="Enable Eve interceptor")

    cp = sub.add_parser("client", help="Start as Bob (client)")
    cp.add_argument("--host", default="127.0.0.1")
    cp.add_argument("--port", type=int, default=5555)

    args = parser.parse_args()

    if args.mode == "server":
        gui = QuantumChatGUI("server", args.host, args.port, args.qubits, args.eve)
        gui.start()
    elif args.mode == "client":
        gui = QuantumChatGUI("client", args.host, args.port)
        gui.start()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
