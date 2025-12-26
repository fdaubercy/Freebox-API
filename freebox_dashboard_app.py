# Pré-requis:
# pip install PyJWT
# python -m pip install Flask

import os, json, logging, requests, jwt, time
from functools import wraps
from flask import Flask, request, redirect, url_for, make_response, render_template
from apscheduler.schedulers.background import BackgroundScheduler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
APP_TOKEN_FILE = os.path.join(BASE_DIR, "app_token.json")

with open(CONFIG_FILE, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

FREEBOX_URL = CONFIG["freebox_url"]
API_BASE = f"{FREEBOX_URL}/api/{CONFIG['api_version']}"

# ---------------- Logging ----------------
LOG_FILE = os.path.join(BASE_DIR, "freebox.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()]
)
logger = logging.getLogger("freebox")

app = Flask(__name__)

# ---------------- Freebox Auth ----------------
class FreeboxAuth:
    def __init__(self):
        with open(APP_TOKEN_FILE, "r") as f:
            self.app_token = json.load(f)["app_token"]
        self.session_token = None
        self.expire = 0

    def _open(self):
        challenge = requests.get(f"{API_BASE}/login/").json()["result"]["challenge"]
        pwd = requests.hmac.new(self.app_token.encode(), challenge.encode(), digestmod="sha1").hexdigest()
        r = requests.post(
            f"{API_BASE}/login/session/",
            json={"app_id": CONFIG["app_id"], "password": pwd}
        ).json()
        self.session_token = r["result"]["session_token"]
        self.expire = time.time() + r["result"].get("expires", 3600)

    def headers(self):
        if not self.session_token or time.time() > self.expire - 30:
            self._open()
        return {"X-Fbx-App-Auth": self.session_token}

freebox = FreeboxAuth()

# ---------------- JWT helpers ----------------
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
@app.route("/")
def index():
    return redirect(url_for("dashboard") if request.cookies.get("jwt") else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    if request.form["username"] == CONFIG["local_user"] and \
       request.form["password"] == CONFIG["local_password"]:
        token = generate_jwt(request.form["username"])
        resp = make_response(render_template(
            "login_success.html",
            user=request.form["username"],
            token=token
        ))
        resp.set_cookie("jwt", token)
        return resp

    return render_template("login.html", error=True), 401

@app.route("/dashboard")
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

@app.route("/category/<name>")
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
    r = requests.get(url, headers=freebox.headers())
    return render_template("category.html", title=name.capitalize(), data=r.json())

# ---------------- Scheduler ----------------
def save_data(name, data):
    path = os.path.join(BASE_DIR, f"data_{name}.json")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": int(time.time()), "data": data}) + "\n")

def poll_status():
    try:
        r = requests.get(f"{API_BASE}/connection/", headers=freebox.headers(), timeout=5)
        r.raise_for_status()
        save_data("status", r.json())
        logger.info("Poll status OK")
    except Exception as e:
        logger.error(f"Erreur poll_status: {e}")

def poll_wifi():
    try:
        r = requests.get(f"{API_BASE}/wifi/config/", headers=freebox.headers(), timeout=5)
        r.raise_for_status()
        save_data("wifi", r.json())
        logger.info("Poll WiFi OK")
    except Exception as e:
        logger.error(f"Erreur poll_wifi: {e}")

def poll_dhcp():
    try:
        r = requests.get(f"{API_BASE}/dhcp/config/", headers=freebox.headers(), timeout=5)
        r.raise_for_status()
        save_data("dhcp", r.json())
        logger.info("Poll DHCP OK")
    except Exception as e:
        logger.error(f"Erreur poll_dhcp: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(poll_status, 'interval', seconds=30)
scheduler.add_job(poll_wifi, 'interval', minutes=5)
scheduler.add_job(poll_dhcp, 'interval', minutes=5)
scheduler.start()
logger.info("Scheduler Freebox démarré")

# ---------------- Run Flask ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
