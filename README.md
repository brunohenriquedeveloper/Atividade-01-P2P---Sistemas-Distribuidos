# Atividade 01 – U2 – Cliente-servidor vs P2P (Sistemas Distribuídos – UFS)

Medição do tempo de transferência de arquivo (5MB, 50MB, 500MB) com 1..N clientes.
O arquivo recebido é descartado (nunca é salvo em disco no cliente).

## Arquivos
- `servers.py` – servidor TCP: `seq` (1 por vez), `thread` (1 thread/cliente), `pool` (máx. N simultâneos)
- `client.py` – dispara N clientes simultâneos e registra min/médio/máx em `results.csv`
- `p2p.py` – peer P2P próprio (pedaços de 256KB, troca entre peers, estilo BitTorrent)
- `run_p2p.py` – sobe 1 seed + N peers e mede o tempo de cada um
- `run_all.py` – roda toda a bateria e gera `results.csv`
- `common.py` – utilitários

## Rodar tudo (local)
    python run_all.py --sizes 5 50 500 --clients 1 5 10 20 --workers 4 --reps 3

## Rodar manualmente em máquinas diferentes (recomendado para o relatório)
Servidor:   python servers.py --mode pool --workers 4 --file arquivo.bin --port 5000
Clientes:   python client.py --host IP_SERVIDOR --port 5000 --clients 10 --label pool4 --size-mb 50
P2P seed:   python p2p.py --seed --port 6000 --file arquivo.bin
P2P peer:   python p2p.py --port 6000 --size BYTES_DO_ARQUIVO --peers IP_SEED:6000,IP_OUTRO_PEER:6000 --start-at EPOCH
(`--start-at` sincroniza a largada; use `date +%s` + alguns segundos, com relógios sincronizados.)

## Dicas para o relatório
- Rode cada experimento 3+ vezes e reporte a média.
- Informe o ambiente (CPU, rede, localhost ou máquinas distintas, valor de N do pool).
- Em localhost tudo divide a mesma CPU/loopback, então o P2P perde a vantagem de banda extra; discuta isso.
