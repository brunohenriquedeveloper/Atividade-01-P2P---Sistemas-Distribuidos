import csv
import os
import statistics


def recvn(sock, n):
    """Lê exatamente n bytes do socket."""
    buf = bytearray(n)
    mv = memoryview(buf)
    got = 0
    while got < n:
        r = sock.recv_into(mv[got:], n - got)
        if r == 0:
            raise ConnectionError("conexão fechada antes do fim")
        got += r
    return bytes(buf)


def append_csv(path, modo, tamanho_mb, clientes, tempos):
    """Salva min/médio/máx dos tempos (ignora falhas = None) e devolve as estatísticas."""
    ok = [t for t in tempos if t is not None]
    if not ok:
        print("Nenhum download concluído!")
        return None
    novo = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["modo", "tamanho_mb", "clientes", "concluidos", "min_s", "medio_s", "max_s"])
        w.writerow([modo, tamanho_mb, clientes, len(ok),
                    f"{min(ok):.3f}", f"{statistics.mean(ok):.3f}", f"{max(ok):.3f}"])
    return min(ok), statistics.mean(ok), max(ok)
