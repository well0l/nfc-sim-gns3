# Android NFC Portal (WebView) + NFC su Bar

Questa app Android apre il **portal** del progetto dentro una WebView (quindi la dashboard resta identica) e abilita la lettura NFC quando sei nel servizio **Bar** (`/service/bar` oppure `/bar/`).

## Cosa fa
- Apre `https://<IP_DEL_PC>/` (porta 443 del reverse proxy Nginx)
- Mantiene login/cookie come nel browser
- Quando sei nel Bar, al tap NFC legge l'UID e lo inoltra alla pagina (che può usarlo per avviare il pagamento)

## Debug
- Long-press sulla pagina: imposti la Base URL
- In build debug la WebView accetta certificati self-signed (solo per sviluppo)

## Requisiti
- Android Studio
- Telefono con NFC
- Stack Docker avviato sul PC (nginx su 443)
