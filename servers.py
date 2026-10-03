"""Servidor cliente-servidor com 3 variações:
  seq    -> atende 1 cliente por vez
  thread -> 1 thread por cliente (todos de uma vez)
  pool   -> no máximo N clientes simultâneos (pool de threads)
Uso: python servers.py --mode pool --workers 4 --file files/file_50MB.bin --port 5000
"""
import argparse
import os
import socket
import threading
from concurrent.futures import ThreadPoolExecutor

CHUNK = 256 * 1024


def handle(conn, path):
    try:
        with conn:
            if not conn.recv(1024):      # pedido do cliente (ou conexão de teste)
                return
            conn.sendall(os.path.getsize(path).to_bytes(8, "big"))
            with open(path, "rb") as f:
                while True:
                    b = f.read(CHUNK)
                    if not b:
                        break
                    conn.sendall(b)
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["seq", "thread", "pool"], required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--workers", type=int, default=4, help="N do modo pool")
    a = ap.parse_args()

    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", a.port))
    srv.listen(1024)
    pool = ThreadPoolExecutor(a.workers) if a.mode == "pool" else None
    print(f"Servidor [{a.mode}] na porta {a.port}, arquivo {a.file}", flush=True)

    while True:
        conn, _ = srv.accept()
        if a.mode == "seq":
            handle(conn, a.file)
        elif a.mode == "thread":
            threading.Thread(target=handle, args=(conn, a.file), daemon=True).start()
        else:
            pool.submit(handle, conn, a.file)


if __name__ == "__main__":
    main()
