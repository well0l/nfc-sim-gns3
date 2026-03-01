# NFC Payment System — GNS3 Simulation

Sistema di pagamento cashless basato su NFC, simulato con GNS3.

## Avvio rapido

```bash
git clone https://github.com/well0l/nfc-sim-gns3.git
cd nfc-sim-gns3
bash setup.sh
```

Lo script `setup.sh` in automatico:
1. Verifica che Docker sia installato
2. Installa `mkcert` se mancante
3. Installa la CA locale (zero warning nel browser)
4. Genera i certificati TLS per `localhost`
5. Crea il file `.env` con un `HMAC_SECRET` casuale
6. Avvia tutti i container con `docker-compose up --build`

## Servizi (HTTPS)

| Servizio | URL |
|----------|-----|
| Cassa (admin) | https://localhost:5443 |
| Bar POS | https://localhost:5444 |
| Vending Machine | https://localhost:5445 |
| Backend API | https://localhost:8443/api/stats |

## Architettura

```
[Browser Cliente]
       |
    HTTPS (mkcert TLS)
       |
  [Nginx :5443/5444/5445/8443]
       |
    HTTP (rete Docker interna)
       |
  ┌────┴──────────────┐
  │                   │
[cassa:5001]    [bar:5003]  [vending:5002]
  │                   │
  └────────┬──────────┘
           │
    [backend:8080]
      (SQLite DB)
```

## Sicurezza implementata (Layer 1)

- **HMAC-SHA256** — ogni transazione firmata con chiave segreta condivisa
- **Nonce anti-replay** — ogni richiesta ha un nonce monouso (TTL 60s)
- **Rate limiting** — max 10 richieste/min per UID e per IP
- **Velocity check** — stessa carta su 2 device in < 5s → rifiutata
- **Auto-block** — carta bloccata automaticamente dopo 5 denied in 5 min
- **HTTPS/TLS** — traffico cifrato end-to-end tra browser e server

## Variabili d'ambiente

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `HMAC_SECRET` | generato da `setup.sh` | Chiave condivisa per firma HMAC |
| `DB_PATH` | `./data/nfc.db` | Percorso database SQLite |
| `BACKEND_URL` | `http://backend:8080` | URL interno backend |
| `DEVICE_ID` | (per servizio) | Identificativo del terminale |
