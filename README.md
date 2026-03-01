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
4. Genera i certificati TLS per `localhost` (opzionale: anche IP LAN via `SERVER_IP=...`)
5. Crea il file `.env` con `HMAC_SECRET` e `SECRET_KEY` casuali
6. Avvia tutti i container con `docker compose up --build`

## Accesso (entrypoint unico)

- Portal (Login + Dashboard + Admin): https://localhost/

I servizi **non** sono più esposti direttamente su porte dedicate (5001/5002/5003): sono raggiungibili solo tramite il Portal (reverse proxy Nginx) e protetti da RBAC.

## Architettura (V3 — Portal + RBAC)

```
[Browser touch / terminali]
        |
      HTTPS
        |
 [Nginx :443]  (entrypoint unico)
        |
   HTTP (rete Docker)
        |
  ┌──────┼─────────┬──────────┐
[portal] [cassa]   [bar]   [vending]
             \        |        /
              \       |       /
                 [backend]
                 (SQLite DB)
```

## Sicurezza implementata

- HMAC-SHA256: ogni transazione firmata con chiave segreta condivisa
- Nonce anti-replay: ogni richiesta ha un nonce monouso (TTL 60s)
- Rate limiting: max 10 richieste/min per UID e per IP
- Velocity check: stessa carta su 2 device in < 5s → rifiutata
- Auto-block: carta bloccata automaticamente dopo 5 denied in 5 min
- HTTPS/TLS: traffico cifrato tra browser e entrypoint (Nginx)
- RBAC (Portal): login e permessi per servizio (cassa/bar/vending)

## Variabili d'ambiente

| Variabile | Default | Descrizione |
|-----------|---------|-------------|
| `HMAC_SECRET` | generato da `setup.sh` | Chiave condivisa per firma HMAC |
| `SECRET_KEY` | generato da `setup.sh` | Chiave sessione Portal |
| `SERVER_IP` | (vuoto) | Se impostata, `setup.sh` include anche l'IP nei certificati mkcert |
| `INIT_ADMIN_USER` | `admin` | Username admin iniziale (Portal) |
| `INIT_ADMIN_PASSWORD` | `admin` | Password admin iniziale (Portal) |
| `DB_PATH` | `./data/nfc.db` | Percorso database SQLite (backend) |
| `BACKEND_URL` | `http://backend:8080` | URL interno backend |
| `DEVICE_ID` | (per servizio) | Identificativo del terminale |
