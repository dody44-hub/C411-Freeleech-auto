# ─────────────────────────────────────────────
#  config.py  –  remplis uniquement ce fichier
# ─────────────────────────────────────────────

# Ton login sdedi
SDEDI_LOGIN    = "ton mail "
SDEDI_PASSWORD = "ton mot de passe"

# Cookie complet récupéré depuis Firefox (à recopier si ça expire)
SDEDI_COOKIE = "   "

# URL exacte de l'API httprpc ruTorrent (trouvée dans les requêtes réseau)
RUTORRENT_URL = "https://sb23100.sdedi.com/plugins/httprpc/action.php"

# Referer exact
RUTORRENT_REFERER = "https://sb23100.sdedi.com/index.php?no-header"

# Ta clé API c411.org
C411_API_KEY   = "ton api "

# Seuil upload minimum (100 Ko/s)
MIN_UPLOAD_SPEED  = 100 * 1024

# Limite totale de stockage en Go
MAX_TOTAL_SIZE_GB = 35

# Intervalle entre chaque cycle en minutes
CHECK_INTERVAL    = 1
