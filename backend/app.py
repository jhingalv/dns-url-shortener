from flask import Flask, request, jsonify, redirect
import hashlib
import dns.resolver
import os
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# --- Configuración Cloudflare ---
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")
DOMAIN = os.getenv("DOMAIN")

CF_API_BASE = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records"
HEADERS = {
    "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
    "Content-Type": "application/json",
}


# --- Funciones auxiliares ---

def is_valid_url(url: str) -> bool:
    """Valida URL básica (http o https)"""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except:
        return False


def generate_hash(url: str, length: int = 4) -> str:
    """Genera hash corto a partir de la URL"""
    return hashlib.sha256(url.encode()).hexdigest()[:length]


def create_txt_record(subdomain: str, target_url: str):
    """Crea registro TXT en Cloudflare"""
    data = {
        "type": "TXT",
        "name": f"{subdomain}.{DOMAIN}",
        "content": target_url,
        "ttl": 3600
    }
    response = requests.post(CF_API_BASE, headers=HEADERS, json=data)
    if response.status_code != 200 or not response.json().get("success"):
        raise Exception(f"Error creando TXT: {response.text}")
    return response.json()


def resolve_txt_record(subdomain: str):
    """Resuelve un TXT via DNS"""
    fqdn = f"{subdomain}.{DOMAIN}"
    try:
        answers = dns.resolver.resolve(fqdn, "TXT")
        for rdata in answers:
            # dns.resolver devuelve bytes, eliminamos comillas
            txt_value = rdata.to_text().strip('"')
            return txt_value
    except Exception as e:
        print(f"[WARN] No se pudo resolver {fqdn}: {e}")
        return None


# --- Endpoints ---

@app.route("/api/create", methods=["POST"])
def create_short_url():
    data = request.get_json()
    long_url = data.get("url", "").strip()

    if not long_url or not is_valid_url(long_url):
        return jsonify({"error": "URL inválida"}), 400

    short_hash = generate_hash(long_url)
    short_url = f"https://{DOMAIN}/{short_hash}"

    try:
        create_txt_record(short_hash, long_url)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "short_url": short_url,
        "hash": short_hash,
        "original_url": long_url
    })


@app.route("/<hash_code>")
def redirect_from_hash(hash_code):
    target_url = resolve_txt_record(hash_code)
    if not target_url:
        return jsonify({"error": "URL no encontrada"}), 404
    return redirect(target_url, code=302)


@app.route("/")
def index():
    return jsonify({
        "message": "API DNS URL Shortener funcionando 🚀",
        "endpoints": {
            "POST /api/create": "Crea una nueva URL corta (JSON: { url })",
            "GET /<hash>": "Redirige usando DNS TXT"
        }
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
