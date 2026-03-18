import requests
import time
import logging
import json
import os
from xml.etree import ElementTree as ET
from config import *

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
log = logging.getLogger(__name__)

requests.packages.urllib3.disable_warnings()

session = requests.Session()
session.headers.update({
    "Cookie": SDEDI_COOKIE,
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Referer": RUTORRENT_REFERER,
    "X-Requested-With": "XMLHttpRequest",
})

# Cookie pour sb23100 (ruTorrent / addtorrent)
SB_COOKIE = "emailsdedi=75ff51b04817e8a2c4117ac14d180ede; idsdedi=TVVDRzZIdmRTVkt6LzJzTGppVy9kZz09; Language=fr; PHPSESSID=hoefi3gjb7pkvkjf96n7s4r2b1"

# ─────────────────────────────────────────────
#  TELEGRAM NOTIFICATIONS
# ─────────────────────────────────────────────

TG_TOKEN   = "8581674091:AAHLky0Cz-t3RGnPQNblEtWtSoOpnlKRvG0"
TG_CHAT_ID = "5296733290"

def notify(msg, silent=False):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={
                "chat_id": TG_CHAT_ID,
                "text": msg,
                "parse_mode": "HTML",
                "disable_notification": silent
            },
            timeout=10
        )
    except Exception as e:
        log.error(f"Erreur Telegram: {e}")


BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
LOG_FILE    = os.path.join(BASE_DIR, "activity.json")
IGNORE_FILE = os.path.join(BASE_DIR, "ignore.json")
TIMER_FILE  = os.path.join(BASE_DIR, "timers.json")
STATS_FILE  = os.path.join(BASE_DIR, "torrent_stats.json")

# ─────────────────────────────────────────────
#  STATS HISTORIQUES (pour prédiction ratio)
# ─────────────────────────────────────────────

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE) as f:
                return json.load(f)
        except:
            pass
    return []

def record_torrent_added(infohash, title, size_bytes, seeders=0):
    """Enregistre un torrent au moment de son ajout."""
    stats = load_stats()
    stats.append({
        "infohash":   infohash,
        "title":      title,
        "size_bytes": size_bytes,
        "seeders":    seeders,
        "added_at":   time.time(),
        "removed_at": None,
        "upload_bytes": 0,
        "seed_minutes": 0,
        "ratio":       0.0,
    })
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

def record_torrent_removed(t_hash, upload_bytes=0):
    """Met à jour les stats au moment de la suppression."""
    stats = load_stats()
    h = t_hash.lower()
    for s in stats:
        if s["infohash"] == h and s["removed_at"] is None:
            s["removed_at"]  = time.time()
            s["upload_bytes"] = upload_bytes
            s["seed_minutes"] = (s["removed_at"] - s["added_at"]) / 60
            s["ratio"]        = upload_bytes / s["size_bytes"] if s["size_bytes"] > 0 else 0
            break
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


# ─────────────────────────────────────────────
#  TIMERS — suivi du temps depuis l'ajout
# ─────────────────────────────────────────────

def load_timers():
    if os.path.exists(TIMER_FILE):
        try:
            with open(TIMER_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}

def save_timers(timers):
    with open(TIMER_FILE, "w") as f:
        json.dump(timers, f)

def register_torrent(t_hash):
    """Enregistre l'heure d'ajout d'un torrent."""
    timers = load_timers()
    if t_hash not in timers:
        timers[t_hash] = time.time()
        save_timers(timers)

def get_age_minutes(t_hash):
    """Retourne l'âge du torrent en minutes depuis son enregistrement."""
    timers = load_timers()
    if t_hash not in timers:
        return 9999  # inconnu = vieux
    return (time.time() - timers[t_hash]) / 60

def cleanup_timers(active_hashes):
    """Supprime les timers des torrents qui n'existent plus."""
    timers = load_timers()
    for h in list(timers.keys()):
        if h not in active_hashes:
            del timers[h]
    save_timers(timers)

# ─────────────────────────────────────────────
#  LOGS D'ACTIVITE
# ─────────────────────────────────────────────

def load_activity():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE) as f:
                return json.load(f)
        except:
            pass
    return []

def add_activity(action, name, detail=""):
    logs = load_activity()
    logs.insert(0, {"time": time.strftime("%d/%m %H:%M"), "action": action, "name": name, "detail": detail})
    logs = logs[:50]
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f)

# ─────────────────────────────────────────────
#  LISTE IGNORE
# ─────────────────────────────────────────────

def load_ignore():
    if os.path.exists(IGNORE_FILE):
        try:
            with open(IGNORE_FILE) as f:
                return json.load(f)
        except:
            pass
    return []

def save_ignore(lst):
    with open(IGNORE_FILE, "w") as f:
        json.dump(lst, f)

def is_ignored(name):
    return name in load_ignore()

# ─────────────────────────────────────────────
#  RUTORRENT
# ─────────────────────────────────────────────

def get_all_torrents():
    try:
        r = session.post(RUTORRENT_URL, data={"mode": "list"}, verify=False, timeout=15)
        if r.status_code != 200:
            log.error(f"Erreur HTTP {r.status_code}")
            return []
        data = r.json()
        t_data = data.get('t', {})
        if isinstance(t_data, list):
            return []
        torrents = []
        for t_hash, v in t_data.items():
            try:
                size       = int(v[5])
                downloaded = int(v[8]) if len(v) > 8 else 0
                # complete = téléchargé >= taille totale
                complete   = (downloaded >= size) if size > 0 else False
                torrents.append({
                    "hash":       t_hash,
                    "name":       v[4],
                    "size":       size,
                    "downloaded": downloaded,
                    "up_speed":   int(v[10]),
                    "dn_speed":   int(v[11]) if len(v) > 11 else 0,
                    "state":      int(v[0]),
                    "complete":   complete,
                    "ignored":    is_ignored(v[4]),
                })
            except:
                continue
        return torrents
    except Exception as e:
        log.error(f"Erreur récup: {e}")
        return []

def remove_torrent(t_hash, name, reason="", upload_bytes=0):
    try:
        h = t_hash.lower()
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<methodCall><methodName>system.multicall</methodName>'
            '<params><param><value><array><data>'
            '<value><struct>'
            '<member><name>methodName</name><value><string>d.custom5.set</string></value></member>'
            '<member><name>params</name><value><array><data>'
            '<value><string>' + h + '</string></value>'
            '<value><string>2</string></value>'
            '</data></array></value></member></struct></value>'
            '<value><struct>'
            '<member><name>methodName</name><value><string>d.delete_tied</string></value></member>'
            '<member><name>params</name><value><array><data>'
            '<value><string>' + h + '</string></value>'
            '</data></array></value></member></struct></value>'
            '<value><struct>'
            '<member><name>methodName</name><value><string>d.erase</string></value></member>'
            '<member><name>params</name><value><array><data>'
            '<value><string>' + h + '</string></value>'
            '</data></array></value></member></struct></value>'
            '</data></array></value></param></params></methodCall>'
        )
        session.post(RUTORRENT_URL, data=xml, verify=False, timeout=15)
        timers = load_timers()
        timers.pop(t_hash, None)
        timers.pop(h, None)
        save_timers(timers)
        record_torrent_removed(t_hash, upload_bytes)
        log.info(f"[SUPPR] {name} — {reason}")
        add_activity("suppr", name, reason)
        notify(f"🗑️ <b>Suppression</b> — {name}\n{reason}", silent=True)
        return True
    except Exception as e:
        log.error(f"Erreur suppression {name}: {e}")
    return False

def add_torrent_file(infohash, title, size_gb):
    """Télécharge le .torrent via API c411 puis upload sur ruTorrent."""
    try:
        if not infohash:
            log.error(f"Pas de infohash pour {title}")
            return False

        # 1. Télécharger le vrai fichier .torrent via API c411
        download_url = f"https://c411.org/api?t=download&apikey={C411_API_KEY}&id={infohash}"
        torrent_resp = requests.get(download_url, headers={"User-Agent": "Mozilla/5.0"}, verify=False, timeout=30)
        if torrent_resp.status_code != 200 or not torrent_resp.content.startswith(b'd'):
            log.error(f"Téléchargement .torrent échoué pour {title}")
            return False

        filename = title[:80].replace("/", "_") + ".torrent"

        # 2. Upload multipart vers sb23100.sdedi.com/php/addtorrent.php
        hdrs = {
            "Cookie": SB_COOKIE,
            "Referer": "https://sb23100.sdedi.com/index.php?no-header",
            "User-Agent": "Mozilla/5.0"
        }
        files = {"torrent_file[]": (filename, torrent_resp.content, "application/x-bittorrent")}
        r = requests.post(
            "https://sb23100.sdedi.com/php/addtorrent.php",
            files=files, data={"dir_edit": "", "tadd_label": ""},
            headers=hdrs, verify=False, timeout=30, allow_redirects=False
        )

        location = r.headers.get("Location", "")
        if "Success" in location:
            log.info(f"[AJOUT] {title} ({size_gb:.2f} Go)")
            add_activity("ajout", title, f"{size_gb:.2f} Go")
            record_torrent_added(infohash, title, int(size_gb * 1024**3))
            notify(f"✅ <b>Ajout</b> — {title}\n{size_gb:.2f} Go", silent=True)
            return True
        else:
            log.error(f"Upload échoué pour {title} : {location}")
            return False

    except Exception as e:
        log.error(f"Erreur ajout {title}: {e}")
        return False

# ─────────────────────────────────────────────
#  C411 TORZNAB
# ─────────────────────────────────────────────

def search_torznab(limit=50):
    results = []
    seen = set()
    categories = ["movie", "tv", "music", "pc", "other"]
    ns = {"torznab": "http://torznab.com/schemas/2015/feed"}
    for cat in categories:
        try:
            params = {"t": cat, "apikey": C411_API_KEY, "limit": limit, "q": ""}
            r = requests.get("https://c411.org/api", params=params, verify=False, timeout=15)
            root = ET.fromstring(r.content)
            for item in root.findall(".//item"):
                title    = item.findtext("title", "")
                size     = 0
                infohash = ""
                for attr in item.findall("torznab:attr", ns):
                    if attr.get("name") == "size":
                        try: size = int(attr.get("value", 0))
                        except: pass
                    if attr.get("name") == "infohash":
                        infohash = attr.get("value", "")
                if title and infohash and infohash not in seen:
                    seen.add(infohash)
                    results.append({"title": title, "infohash": infohash, "size": size})
        except Exception as e:
            log.error(f"Erreur Torznab {cat}: {e}")
    log.info(f"Torznab : {len(results)} résultats ({', '.join(categories)})")
    return results

def update_web_data(torrents, free_gb):
    try:
        data = {
            "torrents": torrents,
            "activity": load_activity(),
            "ignore_list": load_ignore(),
            "stats": {
                "total_count": len(torrents),
                "total_size":  sum(t["size"] for t in torrents) / (1024**3),
                "max_size":    MAX_TOTAL_SIZE_GB,
                "free_gb":     free_gb,
                "total_up":    sum(t["up_speed"] for t in torrents) / 1024,
                "slow_count":  sum(1 for t in torrents
                                   if t["complete"] and t["up_speed"] < MIN_UPLOAD_SPEED and not t["ignored"]),
            }
        }
        with open(os.path.join(BASE_DIR, "data.json"), "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log.error(f"Erreur JSON: {e}")

# ─────────────────────────────────────────────
#  CYCLE PRINCIPAL
# ─────────────────────────────────────────────

# Délais en minutes
DELAY_SLOW_COMPLETE   = 10   # torrent terminé mais upload faible → supprimer après 10 min
DELAY_STUCK_DOWNLOAD  = 3    # torrent en cours mais bloqué (dn_speed=0) → supprimer après 3 min
MAX_SIZE_GB           = 20   # limite stricte disque pour éviter de planter sdedi

def run_cycle():
    log.info("━━━━━━━━━━━━ Nouveau cycle ━━━━━━━━━━━━")
    torrents = get_all_torrents()

    # Enregistrer les timers pour les nouveaux torrents
    for t in torrents:
        register_torrent(t["hash"])

    # Nettoyer les vieux timers
    cleanup_timers({t["hash"] for t in torrents})

    if not torrents:
        log.warning("Aucun torrent sur la seedbox — recherche sur C411...")
        notify("⚠️ <b>DODAR</b> — Aucun torrent détecté\nCookie peut-être expiré — vérifie sdedi", silent=True)
        free_gb = MAX_SIZE_GB
        nouveaux = search_torznab(limit=10)
        ajoutes = 0
        noms = set()
        for item in nouveaux:
            if free_gb < 0.5:
                break
            taille_gb = item["size"] / (1024**3) if item["size"] else 0
            if item["title"].lower() in noms or is_ignored(item["title"]):
                continue
            if taille_gb and taille_gb > free_gb:
                continue
            if add_torrent_file(item["infohash"], item["title"], taille_gb):
                free_gb -= taille_gb
                ajoutes += 1
                noms.add(item["title"].lower())
        log.info(f"{ajoutes} torrent(s) ajouté(s)")
        update_web_data([], free_gb)
        return

    total_gb = sum(t["size"] for t in torrents) / (1024**3)
    free_gb  = MAX_SIZE_GB - total_gb
    log.info(f"Torrents : {len(torrents)} | {total_gb:.2f} / {MAX_SIZE_GB} Go | Libre : {free_gb:.2f} Go")

    # ── 1. Supprimer les torrents terminés mais upload trop faible depuis > 10 min ──
    for t in torrents:
        if t["ignored"]:
            continue
        age = get_age_minutes(t["hash"])
        if t["complete"] and t["up_speed"] < MIN_UPLOAD_SPEED and age >= DELAY_SLOW_COMPLETE:
            reason = f"Seed faible ({t['up_speed']} Ko/s) depuis {age:.0f} min"
            if remove_torrent(t["hash"], t["name"], reason):
                total_gb -= t["size"] / (1024**3)
                free_gb  += t["size"] / (1024**3)
                torrents = [x for x in torrents if x["hash"] != t["hash"]]
        elif t["complete"] and t["up_speed"] < MIN_UPLOAD_SPEED:
            log.info(f"[ATTENTE] {t['name']} — seed faible, attente {DELAY_SLOW_COMPLETE - age:.0f} min avant suppression")

    # ── 2. Supprimer les téléchargements bloqués depuis > 3 min ──
    for t in torrents:
        if t["ignored"]:
            continue
        age = get_age_minutes(t["hash"])
        if not t["complete"] and t["dn_speed"] == 0 and age >= DELAY_STUCK_DOWNLOAD:
            reason = f"Téléchargement bloqué depuis {age:.0f} min"
            if remove_torrent(t["hash"], t["name"], reason):
                total_gb -= t["size"] / (1024**3)
                free_gb  += t["size"] / (1024**3)
                torrents = [x for x in torrents if x["hash"] != t["hash"]]
        elif not t["complete"] and t["dn_speed"] == 0:
            log.info(f"[ATTENTE] {t['name']} — téléchargement bloqué, attente {DELAY_STUCK_DOWNLOAD - age:.0f} min")

    # ── 3. Respecter la limite stricte de stockage ──
    if total_gb > MAX_SIZE_GB:
        log.info(f"Dépassement ({total_gb:.2f} Go > {MAX_SIZE_GB} Go) — nettoyage forcé...")
        candidats = sorted([t for t in torrents if not t["ignored"]], key=lambda x: x["up_speed"])
        for t in candidats:
            if total_gb <= MAX_SIZE_GB:
                break
            if remove_torrent(t["hash"], t["name"], f"Dépassement quota ({total_gb:.1f} Go)"):
                total_gb -= t["size"] / (1024**3)
                free_gb  += t["size"] / (1024**3)
                torrents = [x for x in torrents if x["hash"] != t["hash"]]

    # ── 4. Ajouter de nouveaux torrents ──
    if free_gb >= 1.0:
        log.info(f"Espace libre : {free_gb:.2f} Go — recherche sur C411...")
        nouveaux = search_torznab(limit=10)
        noms_existants = {t["name"].lower() for t in torrents}
        ajoutes = 0
        for item in nouveaux:
            if free_gb < 0.5:
                break
            taille_gb = item["size"] / (1024**3) if item["size"] else 0
            if item["title"].lower() in noms_existants or is_ignored(item["title"]):
                continue
            if taille_gb and taille_gb > free_gb:
                continue
            if add_torrent_file(item["infohash"], item["title"], taille_gb):
                free_gb -= taille_gb
                ajoutes += 1
                noms_existants.add(item["title"].lower())
        log.info(f"{ajoutes} torrent(s) ajouté(s)")
    else:
        log.info("Pas assez d'espace pour ajouter")

    torrents = get_all_torrents()
    total_gb = sum(t["size"] for t in torrents) / (1024**3)
    free_gb  = MAX_SIZE_GB - total_gb
    update_web_data(torrents, free_gb)
    log.info("━━━━━━━━━━━━ Fin du cycle ━━━━━━━━━━━━\n")

# ─────────────────────────────────────────────
#  BOUCLE
# ─────────────────────────────────────────────

if __name__ == "__main__":
    log.info(f"Démarrage DODAR bot — cycle toutes les {CHECK_INTERVAL} min")
    while True:
        try:
            run_cycle()
        except Exception as e:
            log.error(f"Erreur inattendue : {e}")
            notify(f"🔴 <b>DODAR ERREUR</b>\n{e}")
        time.sleep(CHECK_INTERVAL * 60)
