"""Peer P2P simples (estilo BitTorrent): arquivo dividido em pedaços de 256 KB.
Cada peer baixa pedaços (em ordem aleatória) de todos os outros peers em paralelo
e já serve os pedaços que possui para os demais. O 'seed' começa com o arquivo completo.
Os pedaços recebidos vão para um arquivo temporário apagado no final.

Seed:    python p2p.py --seed --port 6000 --file files/file_50MB.bin
Leecher: python p2p.py --port 6001 --size <bytes> --peers 127.0.0.1:6000,127.0.0.1:6002
"""
import argparse
import os
import random
import socket
import struct
import tempfile
import threading
import time

from common import recvn

PIECE = 256 * 1024
BINARY = getattr(os, "O_BINARY", 0)   # necessário no Windows


class Peer:
    def __init__(self, port, remotes, path, size, seed, tmpdir=None):
        self.port, self.remotes, self.size = port, remotes, size
        self.num = (size + PIECE - 1) // PIECE
        self.has = bytearray(b"\x01") * self.num if seed else bytearray(self.num)
        self.count = self.num if seed else 0
        self.lock = threading.Lock()
        self.io_lock = threading.Lock()
        self.inflight = set()
        self.done = threading.Event()
        self.tmp = None
        if seed:
            self.fd = os.open(path, os.O_RDONLY | BINARY)
            self.done.set()
        else:
            self.fd, self.tmp = tempfile.mkstemp(dir=tmpdir)
            os.ftruncate(self.fd, size)

    # ---------- E/S portátil (pread/pwrite não existem no Windows) ----------
    def read_at(self, off):
        with self.io_lock:
            os.lseek(self.fd, off, os.SEEK_SET)
            out = b""
            while len(out) < PIECE:
                b = os.read(self.fd, PIECE - len(out))
                if not b:
                    break
                out += b
            return out

    def write_at(self, off, data):
        with self.io_lock:
            os.lseek(self.fd, off, os.SEEK_SET)
            mv = memoryview(data)
            while len(mv):
                mv = mv[os.write(self.fd, mv):]

    # ---------- lado servidor ----------
    def serve(self):
        srv = socket.socket()
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", self.port))
        srv.listen(128)
        while True:
            c, _ = srv.accept()
            threading.Thread(target=self.handle, args=(c,), daemon=True).start()

    def handle(self, c):
        try:
            while True:
                cmd = c.recv(1)
                if not cmd:
                    break
                if cmd == b"B":                      # bitmap de pedaços
                    c.sendall(bytes(self.has))
                elif cmd == b"P":                    # pedido de um pedaço
                    i = struct.unpack(">I", recvn(c, 4))[0]
                    data = self.read_at(i * PIECE)
                    c.sendall(struct.pack(">I", len(data)) + data)
        except OSError:
            pass
        finally:
            c.close()

    # ---------- lado cliente ----------
    def worker(self, host, port):
        s = None
        while not self.done.is_set():
            try:
                s = socket.create_connection((host, port), timeout=60)
                break
            except OSError:
                time.sleep(0.2)
        if s is None:
            return
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        try:
            while not self.done.is_set():
                s.sendall(b"B")
                remote = recvn(s, self.num)
                got_any = False
                while not self.done.is_set():
                    with self.lock:
                        cands = [i for i in range(self.num)
                                 if remote[i] and not self.has[i] and i not in self.inflight]
                        if not cands:
                            break
                        i = random.choice(cands)
                        self.inflight.add(i)
                    try:
                        s.sendall(b"P" + struct.pack(">I", i))
                        n = struct.unpack(">I", recvn(s, 4))[0]
                        data = recvn(s, n)
                    except Exception:
                        with self.lock:
                            self.inflight.discard(i)
                        raise
                    self.write_at(i * PIECE, data)
                    with self.lock:
                        self.has[i] = 1
                        self.inflight.discard(i)
                        self.count += 1
                        if self.count >= self.num:
                            self.done.set()
                    got_any = True
                if not got_any:
                    time.sleep(0.05)
        except Exception:
            pass
        finally:
            s.close()

    def start_download(self):
        for h, p in self.remotes:
            threading.Thread(target=self.worker, args=(h, p), daemon=True).start()

    def cleanup(self):
        os.close(self.fd)
        if self.tmp:
            os.unlink(self.tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--peers", default="", help="host:porta,host:porta,...")
    ap.add_argument("--file", help="arquivo (seed)")
    ap.add_argument("--size", type=int, help="tamanho em bytes (leecher)")
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--tmpdir", default=None, help="pasta do arquivo temporário (leecher)")
    ap.add_argument("--start-at", type=float, default=0, help="epoch para começar (sincroniza peers)")
    ap.add_argument("--linger", type=float, default=30, help="segundos servindo após concluir")
    a = ap.parse_args()

    remotes = [(h, int(p)) for h, p in (x.rsplit(":", 1) for x in a.peers.split(",") if x)]
    size = os.path.getsize(a.file) if a.seed else a.size
    peer = Peer(a.port, remotes, a.file, size, a.seed, a.tmpdir)
    threading.Thread(target=peer.serve, daemon=True).start()

    if a.seed:
        time.sleep(a.linger)
        return
    time.sleep(max(0, a.start_at - time.time()))
    t0 = time.perf_counter()
    peer.start_download()
    peer.done.wait()
    print(f"RESULT {time.perf_counter() - t0:.4f}", flush=True)
    time.sleep(a.linger)         # continua semeando para os outros peers
    peer.cleanup()


if __name__ == "__main__":
    main()
