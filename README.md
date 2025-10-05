# Luanti Telemetry Viewer

Un petit système de **télémétrie temps réel** pour [Luanti (anciennement Minetest)](https://www.luanti.org), permettant d’afficher la **position des joueurs** dans une **interface graphique Python/Tkinter**.

## 🧩 Structure du projet

```
luanti_telemetry/
├── init.lua                  # Mod Luanti qui envoie la position des joueurs
├── luanti_positions_tk.py    # Serveur HTTP + interface Tkinter (visualisation)
└── README.md                 # Ce fichier
```

---

## ⚙️ Fonctionnement

### 1. Le mod Lua (init.lua)
- Le mod utilise l’API HTTP de Luanti (`minetest.request_http_api()`).
- Toutes les 5 secondes, il envoie au serveur local un JSON contenant :
  - le nom des joueurs connectés ;
  - leurs coordonnées X, Y, Z ;
  - l’horodatage (`os.time()`).

Exemple de payload :
```json
{
  "type": "players_pos",
  "t": 1728162850,
  "data": [
    {"name": "Player1", "x": 12.3, "y": 7.0, "z": -45.2},
    {"name": "Player2", "x": -20.1, "y": 8.0, "z": 18.6}
  ]
}
```

L’URL d’envoi par défaut est :
```
http://127.0.0.1:8080/collect
```

⚠️ Si ton serveur Python n’est pas sur la même machine que Luanti, change l’IP dans :
```lua
local endpoint = "http://<ip_du_serveur>:8080/collect"
```
ou ajoute dans `minetest.conf` :
```
collect_endpoint = http://<ip_du_serveur>:8080/collect
```

---

### 2. Le serveur Python (luanti_positions_tk.py)

Ce script joue deux rôles :
- Il démarre un petit **serveur HTTP** (threadé) sur `127.0.0.1:8080/collect`.
- Il affiche en temps réel les positions reçues dans une **interface Tkinter** :
  - un **tableau** listant les joueurs et leurs coordonnées ;
  - une **carte vue de dessus (X/Z)** avec les positions actualisées.

#### Dépendances

Python ≥ 3.8  
Aucune librairie externe n’est requise (uniquement la stdlib + tkinter).

#### Démarrage

```bash
python3 luanti_positions_tk.py
```

> 💡 Si le port 8080 est déjà utilisé, modifie les constantes `HOST` et `PORT` en haut du fichier, et adapte l’URL côté mod Lua.

#### Interface

- **Tableau** : affiche le nom, les coordonnées X/Y/Z et l’âge des données (en secondes).  
- **Carte** : vue du dessus, chaque joueur est représenté par un point bleu et un label.  
- **Bouton** « Effacer inactifs » : supprime les joueurs non mis à jour depuis 60 s.

#### Exemple d’écran

```
+-------------------------------------------------------------+
| Écoute sur http://127.0.0.1:8080/collect       [Effacer...] |
|-------------------------------------------------------------|
| Joueur     |   X   |   Y   |   Z   | Âge (s)               |
|-------------------------------------------------------------|
| Player1    |  12.3 |  7.0  | -45.2 |  1.2                  |
| Player2    | -20.1 |  8.0  |  18.6 |  4.8                  |
|-------------------------------------------------------------|
|                       Carte (vue X/Z)                       |
|         ● Player1 (12, -45)                                 |
|                ● Player2 (-20, 18)                          |
+-------------------------------------------------------------+
```

---

## 🔍 Dépannage

| Problème | Cause probable | Solution |
|-----------|----------------|-----------|
| `Couldn't connect to server` dans Luanti | Le serveur Python n’est pas lancé ou écoute sur la mauvaise IP | Lancer `luanti_positions_tk.py` avant Luanti, ou corriger `endpoint` |
| Fenêtre vide | Aucun joueur connecté / mod non chargé | Vérifier que le mod est bien activé dans le monde |
| Port déjà utilisé | Un autre service occupe 8080 | Modifier `PORT` dans `luanti_positions_tk.py` |
| Erreur `_canvas_text_center` | Version précédente du script | Mettre à jour avec la version corrigée (ou ajouter la méthode `_canvas_text_center`) |

---

## 💡 Conseils

- Tu peux personnaliser l’intervalle d’envoi dans `init.lua` (par défaut 5 s).  
- Pour afficher d’autres infos (vitesse, santé…), ajoute-les simplement au JSON côté mod et adapte le tableau dans `luanti_positions_tk.py`.  
- L’application peut aussi être portée vers une interface web (Flask + JS) si besoin d’un affichage distant.

---

## 🧑‍💻 Auteur
Projet de démonstration créé avec [ChatGPT GPT-5] pour Luanti (Minetest).  
Licence libre (MIT) — à modifier selon ton usage.
