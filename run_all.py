"""Roda toda a bateria de experimentos (local) e grava em results.csv.
Uso: python run_all.py --sizes 5 50 500 --clients 1 5 10 20 --workers 4
"""
import argparse
import os
import socket
import subprocess
import sys
import time

PY = sys.executable


def garantir_arquivo(mb):
    os.makedirs("files", exist_ok=True)
    path = f"files/file_{mb}MB.bin"
    if not os.path.exists(path) or os.path.getsize(path) != mb * 1024 * 1024:
        print(f"Gerando {path}...")
        with open(path, "wb") as f:
            for _ in range(mb):
                f.write(os.urandom(1024 * 1024))
    return path


def esperar_porta(port):
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
            return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("servidor não subiu")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[5, 50, 500])
    ap.add_argument("--clients", type=int, nargs="+", default=[1, 5, 10, 20])
    ap.add_argument("--modes", nargs="+", default=["seq", "thread", "pool", "p2p"])
    ap.add_argument("--workers", type=int, default=4, help="N do pool")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--csv", default="results.csv")
    ap.add_argument("--port", type=int, default=5000)
    a = ap.parse_args()

    for mb in a.sizes:
        path = garantir_arquivo(mb)
        for n in a.clients:
            for _ in range(a.reps):
                for mode in a.modes:
                    if mode == "p2p":
                        subprocess.run([PY, "run_p2p.py", "--file", path, "--clients", str(n),
                                        "--csv", a.csv], check=True)
                        continue
                    srv = subprocess.Popen([PY, "servers.py", "--mode", mode, "--file", path,
                                            "--port", str(a.port), "--workers", str(a.workers)],
                                           stdout=subprocess.DEVNULL)
                    try:
                        esperar_porta(a.port)
                        label = f"{mode}{a.workers}" if mode == "pool" else mode
                        subprocess.run([PY, "client.py", "--port", str(a.port), "--clients", str(n),
                                        "--label", label, "--size-mb", str(mb), "--csv", a.csv],
                                       check=True)
                    finally:
                        srv.terminate()
                        srv.wait()
                    time.sleep(0.5)


if __name__ == "__main__":
    main()
