"""Dispara N clientes simultâneos contra o servidor e mede o tempo de cada download.
O arquivo recebido é descartado (não vai para o disco).
Uso: python client.py --host 127.0.0.1 --port 5000 --clients 10 --label seq --size-mb 50
"""
import argparse
import socket
import threading
import time

from common import append_csv, recvn


def baixar(host, port, res, i, barrier):
    barrier.wait()                       # todos começam juntos
    t0 = time.perf_counter()
    try:
        s = socket.create_connection((host, port), timeout=3600)
        s.sendall(b"GET\n")
        size = int.from_bytes(recvn(s, 8), "big")
        buf = bytearray(256 * 1024)
        got = 0
        while got < size:
            r = s.recv_into(buf, min(len(buf), size - got))
            if r == 0:
                raise ConnectionError("conexão fechada")
            got += r
        s.close()
        res[i] = time.perf_counter() - t0
    except Exception as e:
        print(f"cliente {i} falhou: {e}")
        res[i] = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--clients", type=int, default=1)
    ap.add_argument("--label", default="cs")
    ap.add_argument("--size-mb", type=int, default=0)
    ap.add_argument("--csv", default="results.csv")
    a = ap.parse_args()

    res = [None] * a.clients
    barrier = threading.Barrier(a.clients)
    ts = [threading.Thread(target=baixar, args=(a.host, a.port, res, i, barrier)) for i in range(a.clients)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    st = append_csv(a.csv, a.label, a.size_mb, a.clients, res)
    if st:
        print(f"[{a.label}] {a.size_mb}MB x {a.clients} clientes -> min={st[0]:.2f}s médio={st[1]:.2f}s máx={st[2]:.2f}s")


if __name__ == "__main__":
    main()
