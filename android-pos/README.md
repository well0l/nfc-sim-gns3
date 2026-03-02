# Android NFC POS (solo NFC)

Questa cartella contiene un'app Android (Kotlin) che simula il POS del bar:
- inserisci l'importo (come centesimi tramite tastierino)
- premi "Conferma" e l'app entra in modalità **attesa NFC**
- al tap della carta legge l'UID e chiama il backend `/api/purchase`

## Requisiti
- Android Studio (consigliato)
- Telefono con NFC
- Backend in esecuzione (container `backend` del progetto)

## Config
Nell'app puoi impostare:
- Base URL backend (default: `http://10.10.100.10:8080`)
- HMAC secret (default: `change_me_in_production`)

Apri l'app, fai long-press sul titolo per aprire la schermata di configurazione.
