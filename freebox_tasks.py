# Nécessite l'installation de 'apscheduler: pip install apscheduler

import time
import logging
from freebox_dashboard_app import freebox, API_BASE

logger = logging.getLogger("freebox.tasks")

def poll_status():
    try:
        r = requests.get(
            f"{API_BASE}/connection/",
            headers=freebox.headers(),
            timeout=5
        )
        data = r.json()
        logger.info(f"Freebox status: {data}")
    except Exception as e:
        logger.error(f"Erreur poll_status: {e}")

def poll_wifi():
    try:
        r = requests.get(
            f"{API_BASE}/wifi/config/",
            headers=freebox.headers(),
            timeout=5
        )
        logger.info("WiFi OK")
    except Exception as e:
        logger.error(f"Erreur poll_wifi: {e}")
