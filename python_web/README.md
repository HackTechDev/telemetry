# Luanti Telemetry — Interface Web (Flask + JS)

Interface web en temps réel (SSE) pour visualiser les positions envoyées par le mod Luanti.

## Installation
```bash
python3 -m pip install flask
```

## Lancement
```bash
python3 app.py
```
- Ouvre http://127.0.0.1:8080/ dans ton navigateur.
- Le mod envoie vers `http://127.0.0.1:8080/collect` (même schéma JSON).

## Personnalisation
- Modifie `HOST`, `PORT` en haut de `app.py` (exposer sur `0.0.0.0` si autre machine).
- Style/JS : édite `static/styles.css` et `static/app.js`.
