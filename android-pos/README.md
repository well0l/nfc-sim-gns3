# Android NFC Portal (WebView) + NFC su Bar

Questa app Android apre il **portal** del progetto dentro una WebView (quindi la dashboard resta identica) e abilita la lettura NFC quando sei nel servizio **Bar** (`/service/bar` oppure `/bar/`).

## Cosa fa
1. Al primo avvio chiede l'URL del portal (es. `https://IP_DEL_PC/`)
2. Apre la dashboard in WebView (login, navigazione identica al browser)
3. Quando entri nel servizio Bar, abilita NFC reader mode
4. Al tap NFC legge l'UID e lo passa alla pagina Bar che avvia il pagamento

## Setup
1. Avvia lo stack Docker sul PC (`bash setup.sh` nel branch `feature/portal`)
2. Trova l'IP LAN del PC (`ip addr show | grep "inet " | grep -v 127`)
3. Installa l'app su telefono/Waydroid
4. Al primo avvio inserisci `https://<IP_DEL_PC>/`
5. Login → Dashboard → Bar → conferma importo → tap NFC

## Debug
- Long-press sulla pagina: modifica URL base
- In debug la WebView accetta certificati self-signed

## Requisiti
- Android Studio
- Telefono con NFC (o Waydroid per test UI)
- Stack Docker avviato sul PC (nginx su 443)
