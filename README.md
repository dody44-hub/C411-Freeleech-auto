
---

# 📦 Torrent Manager — README

Gestionnaire de torrents automatisé en Python, conçu pour tourner en continu sur une seedbox ou un serveur Linux.  
Il surveille les tâches, gère les téléchargements, centralise les logs et peut être adapté facilement à n’importe quel fournisseur (Seedbox.io, Pulsed Media, UltraSeedbox, etc.).

---

## ✨ Features

- Surveillance continue des torrents  
- Ajout automatique de tâches via configuration  
- Gestion des erreurs et reprise propre  
- Logs centralisés (`bot.log`)  
- Exécution en arrière‑plan via `nohup`  
- Configuration simple (cookies, chemins, options)  
- Compatible avec toutes les seedbox supportant une interface web torrent (ruTorrent, qBittorrent, Transmission…)

---

# 🚀 Installation

### 1. Installer les dépendances
Assure-toi d’avoir Python 3 installé :

```bash
sudo apt update
sudo apt install python3 python3-pip -y
```

Installe les dépendances du script :

```bash
pip3 install -r requirements.txt
```

---

# 📁 Structure du projet

```
dodar/
 ├── torrent_manager.py
 ├── config.json
 ├── requirements.txt
 └── README.md
```

---

# ⚙️ Configuration

Tout se passe dans `config.json`.

Exemple minimal :

```json
{
  "base_url": "https://votre-seedbox.com/rutorrent/",
  "cookie": "SID=xxxxxxxxxxxxxxxxxxxx",
  "download_path": "/downloads/",
  "interval": 30
}
```

### 🔑 Comment récupérer votre cookie (ruTorrent / Seedbox)

1. Ouvre ton navigateur  
2. Connecte-toi à ton interface torrent (ruTorrent, qBittorrent WebUI…)  
3. Ouvre les **Outils développeur**  
   - Chrome/Edge : `F12` → onglet **Application** → **Cookies**  
   - Firefox : `F12` → **Stockage** → **Cookies**  
4. Trouve le cookie de session (souvent `SID`, `PHPSESSID`, `session`, etc.)  
5. Copie la valeur et colle-la dans `config.json`

⚠️ **Ne partage jamais ton cookie publiquement.**  
Il donne accès complet à ta seedbox.

---

# ▶️ Lancement

### 1. Arrêter proprement l’ancienne instance

```bash
sudo pkill -f torrent_manager
```

### 2. Lancer en arrière‑plan

```bash
cd ~/dodar && nohup python3 torrent_manager.py > bot.log 2>&1 &
```

### 3. Suivre les logs en direct

```bash
tail -f bot.log
```

---

# 🔧 Dépannage

### ❌ `tail: cannot open 'bot.log'`
→ Le script n’a pas démarré.  
Lance-le sans nohup pour voir l’erreur :

```bash
cd ~/dodar
python3 torrent_manager.py
```

### ❌ `Exit 143`
→ Le script a crashé immédiatement.  
Vérifie :
- le chemin du dossier  
- la présence de `torrent_manager.py`  
- la validité du cookie  
- les permissions d’écriture

---

# 🛠️ Modifier le comportement

Tu peux adapter :
- l’intervalle de vérification (`interval`)  
- les chemins de téléchargement  
- les règles d’ajout automatique  
- les actions à effectuer après téléchargement  

Le script est conçu pour être facilement modifiable.

---

# 📄 Licence

Libre d’utilisation et de modification.  
Merci de conserver un lien vers le repo original.

---

