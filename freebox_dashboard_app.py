# Pré-requis:
# pip install PyJWT
# python -m pip install Flask
# pip install flask-socketio (vérification par: pip show flask-socketio)
# Si fonctionnement sous windows: pip install eventlet
# pip install -r requirements.txt


# freebox_dashboard_app.py - version finale complète
import os, json, logging, requests, jwt, hmac, hashlib, time, smtplib
from functools import wraps
from flask import Flask, request, redirect, url_for, make_response, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from flask_socketio import SocketIO, emit
from email.mime.text import MIMEText

# ---------------- Paths & Config ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
APP_TOKEN_FILE = os.path.join(BASE_DIR, "app_token.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
ALERT_DIR = os.path.join(BASE_DIR, "alerts")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ALERT_DIR, exist_ok=True)

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

FREEBOX_URL = CONFIG["freebox_url"]
API_BASE = f"{FREEBOX_URL}/api/{CONFIG['api_version']}"

# ---------------- Logging ----------------
LOG_FILE = os.path.join(BASE_DIR, "freebox.log")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()])
logger = logging.getLogger("freebox")

# ---------------- Flask & WebSocket ----------------
app = Flask(__name__)
socketio = SocketIO(app)

# ---------------- Anti-spam alertes ----------------
LAST_ALERTS = {}
def can_send_alert(key):
    cooldown = CONFIG.get("alerts", {}).get("cooldown_seconds", 300)
    now = time.time()
    last = LAST_ALERTS.get(key, 0)
    if now - last >= cooldown:
        LAST_ALERTS[key] = now
        return True
    return False

# ---------------- Freebox Auth ----------------
class FreeboxAuth:
    def __init__(self):
        with open(APP_TOKEN_FILE, "r") as f:
            self.app_token = json.load(f)["app_token"]
        self.session_token = None
        self.expire = 0
        self.retry_delay = 5
        self.max_retry_delay = 300

    def _open(self):
        try:
            r = requests.get(f"{API_BASE}/login/", timeout=5)
            r.raise_for_status()
            data = r.json()
            if "result" not in data or "challenge" not in data["result"]:
                raise RuntimeError("Challenge Freebox manquant")
            challenge = data["result"]["challenge"]
            pwd = hmac.new(
                self.app_token.encode(),
                challenge.encode(),
                hashlib.sha1
            ).hexdigest()
            r = requests.post(
                f"{API_BASE}/login/session/",
                json={"app_id": CONFIG["app_id"], "password": pwd},
                timeout=5
            )
            r.raise_for_status()
            result = r.json()["result"]
            if "session_token" not in result:
                raise RuntimeError("session_token manquant")
            self.session_token = result["session_token"]
            self.expire = time.time() + result.get("expires", 3600)
            self.retry_delay = 5
            logger.info("🔐 Session Freebox établie")
        except Exception as e:
            logger.error(f"Freebox auth failed: {e}")
            time.sleep(self.retry_delay)
            self.retry_delay = min(self.retry_delay * 2, self.max_retry_delay)
            raise

    def headers(self):
        try:
            if not self.session_token or time.time() > self.expire - 30:
                self._open()
        except Exception as e:
            logger.error(f"Freebox auth error: {e}")
            raise
        return {"X-Fbx-App-Auth": self.session_token}

freebox = FreeboxAuth()

# ---------------- JWT ----------------
def generate_jwt(user):
    payload = {"user": user, "exp": int(time.time()) + CONFIG["jwt_exp"]}
    return jwt.encode(payload, CONFIG["jwt_secret"], algorithm="HS256")

def jwt_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.cookies.get("jwt")
        if not token:
            return redirect(url_for("login"))
        try:
            jwt.decode(token, CONFIG["jwt_secret"], algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

# ---------------- Routes ----------------
@app.route('/')
def index():
    return redirect(url_for("dashboard") if request.cookies.get("jwt") else url_for("login"))

@app.route('/login', methods=["GET","POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    if request.form["username"] == CONFIG["local_user"] and request.form["password"] == CONFIG["local_password"]:
        token = generate_jwt(request.form["username"])
        resp = make_response(render_template("login_success.html", user=request.form["username"], token=token))
        resp.set_cookie("jwt", token)
        return resp
    return render_template("login.html", error=True), 401

@app.route('/dashboard')
@jwt_required
def dashboard():
    buttons = [
        ("Caractéristiques DHCP", "/category/dhcp", "📡"),
        ("Configuration", "/category/config", "⚙️"),
        ("Téléchargements", "/category/downloads", "⬇️"),
        ("Système de fichiers", "/category/filesystem", "🗂️"),
        ("AirMedia", "/category/airmedia", "📶"),
        ("Appels & Contacts", "/category/calls", "📞"),
        ("Stockage", "/category/storage", "💾"),
        ("Filtre parental", "/category/parental", "🛡️"),
    ]
    return render_template("dashboard.html", buttons=buttons)

@app.route('/category/<name>')
@jwt_required
def category(name):
    endpoints = {
        "dhcp": f"{API_BASE}/dhcp/config/",
        "config": f"{API_BASE}/system/",
        "downloads": f"{API_BASE}/downloads/",
        "filesystem": f"{API_BASE}/fs/",
        "airmedia": f"{API_BASE}/airmedia/",
        "calls": f"{API_BASE}/calllog/",
        "storage": f"{API_BASE}/storage/",
        "parental": f"{API_BASE}/parental/"
    }
    url = endpoints.get(name)
    if not url:
        return "Catégorie inconnue", 404
    r = requests.get(url, headers=freebox.headers(), timeout=5)
    data = r.json()
    return render_template("category.html", title=name.capitalize(), data=data)

from datetime import datetime, timedelta

@app.route("/history/<datatype>")
@jwt_required
def history(datatype):
    period = request.args.get("period", "24h")
    file_path = os.path.join(DATA_DIR, f"data_{datatype}.json")
    if not os.path.exists(file_path):
        return {"error":"no data"}, 404

    now = datetime.now()
    if period=="24h":
        cutoff = now - timedelta(hours=24)
    elif period=="7d":
        cutoff = now - timedelta(days=7)
    else:
        cutoff = now - timedelta(hours=24)

    history_data = []
    with open(file_path,"r") as f:
        for line in f:
            entry = json.loads(line)
            ts = datetime.fromtimestamp(entry["ts"])
            if ts >= cutoff:
                history_data.append(entry)
    return {"data": history_data}

@app.route("/metrics")
def prometheus_metrics():
    def safe_count(file):
        try:
            with open(file,"r") as f:
                return sum(1 for _ in f)
        except:
            return 0

    metrics = ""
    metrics += f"# HELP freebox_dhcp_clients Nombre de clients DHCP actifs\n"
    metrics += f"# TYPE freebox_dhcp_clients gauge\n"
    metrics += f"freebox_dhcp_clients {safe_count(os.path.join(DATA_DIR,'data_dhcp.json'))}\n"

    metrics += f"# HELP freebox_wifi_clients Nombre de clients WiFi\n"
    metrics += f"# TYPE freebox_wifi_clients gauge\n"
    metrics += f"freebox_wifi_clients {safe_count(os.path.join(DATA_DIR,'data_wifi.json'))}\n"

    return metrics, 200, {"Content-Type":"text/plain; version=0.0.4"}

@app.route("/settings")
@jwt_required
def settings():
    return render_template("settings.html", config=CONFIG)

@app.route("/save_settings", methods=["POST"])
@jwt_required
def save_settings():
    # Alertes activées
    CONFIG["alerts"]["enabled"] = "alerts_enabled" in request.form
    CONFIG["alerts"]["cooldown_seconds"] = int(request.form.get("cooldown_seconds", 300))

    # Seuils
    CONFIG["alerts"]["thresholds"]["download_min_mbps"] = float(request.form.get("download_min_mbps", 5))
    CONFIG["alerts"]["thresholds"]["upload_min_mbps"] = float(request.form.get("upload_min_mbps", 1))
    CONFIG["alerts"]["thresholds"]["wifi_enabled_required"] = "wifi_enabled_required" in request.form

    # Sauvegarder dans config.json
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(CONFIG, f, indent=4)

    return redirect(url_for("settings"))

# ---------------- Scheduler & Data ----------------
def save_data(name, data):
    path = os.path.join(DATA_DIR, f"data_{name}.json")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": int(time.time()), "data": data}) + "\n")
    socketio.emit("realtime", {"type": name, "timestamp": int(time.time()), "data": data})

# ---- Tâches ----
def poll_status():
    try:
        r = requests.get(f"{API_BASE}/connection/", headers=freebox.headers(), timeout=5)
        r.raise_for_status()
        data = r.json()
        save_data("status", data)
        down = data["result"].get("rate_down", 0)/1_000_000
        up = data["result"].get("rate_up", 0)/1_000_000
        t = CONFIG["alerts"]["thresholds"]
        if down < t["download_min_mbps"] and can_send_alert("low_download"):
            send_alert(f"Débit descendant faible : {down:.2f} Mbps")
        if up < t["upload_min_mbps"] and can_send_alert("low_upload"):
            send_alert(f"Débit montant faible : {up:.2f} Mbps")
        logger.info(f"Poll status OK ↓{down:.2f} ↑{up:.2f}")
    except Exception as e:
        logger.error(f"poll_status error: {e}")

def poll_wifi():
    try:
        r = requests.get(f"{API_BASE}/wifi/config/", headers=freebox.headers(), timeout=5)
        r.raise_for_status()
        data = r.json()
        save_data("wifi", data)
        clients = data["result"].get("stations_count", 0)
        socketio.emit("wifi_stats", {"timestamp": int(time.time()), "clients": clients, "enabled": data["result"].get("enabled", False)})
        if CONFIG["alerts"]["thresholds"]["wifi_enabled_required"] and not data["result"].get("enabled"):
            if can_send_alert("wifi_down"):
                send_alert("🚨 WiFi désactivé ou indisponible")
        logger.info("Poll WiFi OK")
    except Exception as e:
        logger.error(f"poll_wifi error: {e}")

def poll_dhcp():
    try:
        r = requests.get(f"{API_BASE}/dhcp/config/", headers=freebox.headers(), timeout=5)
        r.raise_for_status()
        data = r.json()
        save_data("dhcp", data)
        # Nombre de clients DHCP actifs
        clients = len(data["result"].get("leases", []))
        socketio.emit("dhcp_stats", {"timestamp": int(time.time()), "clients": clients})
        logger.info("Poll DHCP OK")
    except Exception as e:
        logger.error(f"poll_dhcp error: {e}")

# ---------------- Alertes ----------------
def send_alert(message):
    if not CONFIG.get("alerts", {}).get("enabled", False):
        return
    alerts = CONFIG["alerts"]
    # Mail
    if alerts.get("mail", {}).get("enabled", False):
        try:
            msg = MIMEText(message)
            msg["Subject"] = "Freebox Alert"
            msg["From"] = alerts["mail"]["from"]
            msg["To"] = ",".join(alerts["mail"]["to"])
            server = smtplib.SMTP(alerts["mail"]["server"], alerts["mail"]["port"])
            if alerts["mail"].get("tls", False):
                server.starttls()
            if alerts["mail"].get("username"):
                server.login(alerts["mail"]["username"], alerts["mail"]["password"])
            server.send_message(msg)
            server.quit()
            logger.info(f"Alert sent via mail: {message}")
        except Exception as e:
            logger.error(f"Erreur alerte mail: {e}")
    # Discord
    if alerts.get("discord", {}).get("enabled", False):
        try:
            requests.post(alerts["discord"]["webhook"], json={"content": f"🚨 Freebox Alert\n{message}"}, timeout=5)
            logger.info(f"Alert sent via Discord: {message}")
        except Exception as e:
            logger.error(f"Erreur alerte Discord: {e}")

# ---------------- Scheduler ----------------
scheduler = BackgroundScheduler()
scheduler.add_job(poll_status, 'interval', seconds=30)
scheduler.add_job(poll_wifi, 'interval', minutes=5)
scheduler.add_job(poll_dhcp, 'interval', minutes=5)
scheduler.start()
logger.info("Scheduler Freebox démarré")

# ---------------- WebSocket ----------------
@socketio.on('connect')
def ws_connect():
    logger.info('Client WebSocket connecté')

# ---------------- Run ----------------
# Connexion HTTP
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=CONFIG.get("web_port", 5000))

