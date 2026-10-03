"""Sobe 1 seed + N peers (processos) e coleta o tempo de conclusão de cada peer.
Uso: python run_p2p.py --file files/file_50MB.bin --clients 10
"""
import argparse
import os
import shutil
import subprocess
import tempfile
import sys
import time

from common import append_csv

PY = sys.executable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--clients", type=int, required=True)
    ap.add_argument("--base-port", type=int, default=6000)
    ap.add_argument("--csv", default="results.csv")
    a = ap.parse_args()

    size = os.path.getsize(a.file)
    size_mb = round(size / 1024 / 1024)
    ports = [a.base_port + i for i in range(a.clients + 1)]     # ports[0] = seed
    start_at = time.time() + 3 + 0.1 * a.clients
    tmpdir = tempfile.mkdtemp(prefix="p2p_")                    # apagada no final, mesmo com erro
    procs, leechers, tempos = [], [], []
    try:
        procs.append(subprocess.Popen([PY, "p2p.py", "--seed", "--port", str(ports[0]),
                                       "--file", a.file, "--linger", "3600"]))
        for p in ports[1:]:
            peers = ",".join(f"127.0.0.1:{q}" for q in ports if q != p)
            pr = subprocess.Popen([PY, "p2p.py", "--port", str(p), "--size", str(size),
                                   "--peers", peers, "--start-at", str(start_at),
                                   "--linger", "3600", "--tmpdir", tmpdir],
                                  stdout=subprocess.PIPE, text=True)
            procs.append(pr)
            leechers.append(pr)
        for pr in leechers:
            linha = pr.stdout.readline().strip()
            tempos.append(float(linha.split()[1]) if linha.startswith("RESULT") else None)
    finally:
        for pr in procs:
            pr.terminate()
        for pr in procs:
            pr.wait()
        shutil.rmtree(tmpdir, ignore_errors=True)

    st = append_csv(a.csv, "p2p", size_mb, a.clients, tempos)
    if st:
        print(f"[p2p] {size_mb}MB x {a.clients} peers -> min={st[0]:.2f}s médio={st[1]:.2f}s máx={st[2]:.2f}s")


if __name__ == "__main__":
    main()
