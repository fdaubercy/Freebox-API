# Installer: pip install fpdf

import os
import zipfile
from fpdf import FPDF

# Nom du projet
project_name = "flask-nginx-prod"

# Création des dossiers
folders = ["app", "nginx", "config", "html"]
os.makedirs(project_name, exist_ok=True)
for folder in folders:
    os.makedirs(os.path.join(project_name, folder), exist_ok=True)

# 1. Fichier config.json
config_json = """{
  "project_name": "flask-nginx-prod",
  "domains": ["monsite.com", "blog.monsite.com"],
  "flask_port": 5000,
  "email": "admin@example.com"
}"""
with open(os.path.join(project_name, "config", "config.json"), "w") as f:
    f.write(config_json)

# 2. Flask app.py
app_py = """from flask import Flask
from flask_caching import Cache
import time
import json

with open('../config/config.json') as f:
    config = json.load(f)

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 60})

@app.route('/')
@cache.cached()
def index():
    return f"Site {config['domains'][0]} en ligne ! Heure : {time.ctime()}"

@app.route('/refresh_cache')
def refresh_cache():
    cache.clear()
    return "Cache purgé !"

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=config['flask_port'])
"""
with open(os.path.join(project_name, "app", "app.py"), "w") as f:
    f.write(app_py)

# 3. Script setup-nginx.sh
setup_nginx = """#!/bin/bash
CONFIG_FILE="../config/config.json"
DOMAINS=$(jq -r '.domains[]' $CONFIG_FILE)
FLASK_PORT=$(jq -r '.flask_port' $CONFIG_FILE)
EMAIL=$(jq -r '.email' $CONFIG_FILE)

sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx brotli jq

sudo mkdir -p /var/www/html
sudo cp ../html/404.html /var/www/html/404.html
sudo cp ../html/50x.html /var/www/html/50x.html

for SITE in $DOMAINS; do
sudo tee /etc/nginx/sites-available/$SITE > /dev/null <<EOL
server {
    listen 80;
    server_name $SITE www.$SITE;
    if (\$host ~* ^www\.(.*)\$) { return 301 https://\$1\$request_uri; }
    return 301 https://\$host\$request_uri;
}
server {
    listen 443 ssl http2;
    server_name $SITE www.$SITE;
    ssl_certificate /etc/letsencrypt/live/$SITE/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$SITE/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    gzip on;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;
    gzip_min_length 256;
    brotli on;
    brotli_types text/plain text/css application/javascript application/json image/svg+xml;
    brotli_comp_level 6;
    location / {
        proxy_pass http://127.0.0.1:$FLASK_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
    location ~* \\\.(jpg|jpeg|png|gif|ico|css|js|svg|woff2?)\$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
    location ~* \\\.(html|php)\$ {
        expires 1h;
        add_header Cache-Control "private, no-transform";
    }
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
    location = /404.html { root /var/www/html; internal; }
    location = /50x.html { root /var/www/html; internal; }
    http2_push_preload on;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header Host \$host;
}
EOL
sudo ln -sf /etc/nginx/sites-available/$SITE /etc/nginx/sites-enabled/
done

sudo nginx -t
sudo systemctl reload nginx

sudo certbot --nginx $(printf -- "-d %s " $DOMAINS) --email $EMAIL --agree-tos --no-eff-email --redirect
"""
with open(os.path.join(project_name, "nginx", "setup-nginx.sh"), "w") as f:
    f.write(setup_nginx)

# 4. Pages d'erreur
error_404 = "<!DOCTYPE html><html><head><title>404</title></head><body><h1>404 - Page non trouvée</h1></body></html>"
error_50x = "<!DOCTYPE html><html><head><title>50x</title></head><body><h1>Erreur serveur</h1></body></html>"
with open(os.path.join(project_name, "html", "404.html"), "w") as f:
    f.write(error_404)
with open(os.path.join(project_name, "html", "50x.html"), "w") as f:
    f.write(error_50x)

# 5. Générer PDF tutoriel
pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", 'B', 16)
pdf.cell(0, 10, "Tuto Installation Flask + Nginx Reverse Proxy", ln=1, align='C')
pdf.set_font("Arial", '', 12)
pdf.ln(5)
pdf.multi_cell(0, 6, 
"1. Modifier le fichier config/config.json selon vos besoins (domaines, port Flask, email Certbot).\n"
"2. Installer Python, pip et Flask sur le serveur.\n"
"3. Installer les dépendances : Flask-Caching, Nginx, Certbot, Brotli, jq.\n"
"4. Lancer l'application Flask : python app/app.py\n"
"5. Lancer le script Nginx : bash nginx/setup-nginx.sh\n"
"6. Vérifier que les sites sont accessibles en HTTPS.\n"
"7. Purger le cache Flask via /refresh_cache si nécessaire.\n"
"8. Tous les logs Nginx se trouvent dans /var/www/<domaine>/logs.\n"
"9. Les pages d'erreur 404 et 50x sont personnalisables dans html/.\n"
"10. Le système est compatible CDN et HTTP/2 push pour les assets critiques.\n"
)
pdf.output(os.path.join(project_name, "README.pdf"))

# 6. Créer zip
zip_filename = f"{project_name}.zip"
with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(project_name):
        for file in files:
            filepath = os.path.join(root, file)
            zipf.write(filepath, os.path.relpath(filepath, project_name))

print(f"Fichier zip généré : {zip_filename}")
