# Nécessite l'installation de 'apscheduler: pip install apscheduler

import logging
import requests
import json
import os
from apscheduler.schedulers.background import BackgroundScheduler
from freebox_dashboard_app import freebox, API_BASE

# ---------------- Logging ----------------
LOG_FILE = os.path.join(os.path.dirname(__file__), "freebox_poll.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()]
)
logger = logging.getLogger("freebox.poll")

# ---------------- Fonction utilitaire ----------------
def save_data(name, data):
    """
    Sauvegarde les données Freebox dans un fichier JSON avec timestamp.
    """
    entry = {"ts": int(time.time()), "data": data}
    file_path = os.path.join(os.path.dirname(__file__), f"data_{name}.json")
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

# ---------------- Tâches Freebox ----------------
def poll_status():
    try:
        r = requests.get(f"{API_BASE}/connection/", headers=freebox.headers(), timeout=5)
        r.raise_for_status()
        data = r.json()
        logger.info("Poll status OK")
        save_data("status", data)
    except Exception as e:
        logger.error(f"Erreur poll_status: {e}")

def poll_wifi():
    try:
        r = requests.get(f"{API_BASE}/wifi/config/", headers=freebox.headers(), timeout=5)
        r.raise_for_status()
        data = r.json()
        logger.info("Poll WiFi OK")
        save_data("wifi", data)
    except Exception as e:
        logger.error(f"Erreur poll_wifi: {e}")

def poll_dhcp():
    try:
        r = requests.get(f"{API_BASE}/dhcp/config/", headers=freebox.headers(), timeout=5)
        r.raise_for_status()
        data = r.json()
        logger.info("Poll DHCP OK")
        save_data("dhcp", data)
    except Exception as e:
        logger.error(f"Erreur poll_dhcp: {e}")

# ---------------- Scheduler ----------------
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(poll_status, 'interval', seconds=30, id='poll_status')
    scheduler.add_job(poll_wifi, 'interval', minutes=5, id='poll_wifi')
    scheduler.add_job(poll_dhcp, 'interval', minutes=5, id='poll_dhcp')
    scheduler.start()
    logger.info("Scheduler Freebox démarré")
    return scheduler

# ---------------- Lancement direct ----------------
if __name__ == "__main__":
    start_scheduler()
    # Boucle infinie pour garder le script vivant
    import time
    try:
        while True:
            time.sleep(10)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Arrêt du scheduler")
