from flask import Flask, request, jsonify, redirect
import hashlib
import dns.resolver
import os
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")
DOMAIN = os.getenv("DOMAIN")

if not CLOUDFLARE_API_TOKEN or not CLOUDFLARE_ZONE_ID or not DOMAIN:
    raise ValueError("Missing necessary environment variables: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID or DOMAIN")

CF_API_BASE = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records"
HEADERS = {
    "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
    "Content-Type": "application/json",
}

def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

def extract_domain(url: str) -> str:
    try:
        parsed_url = urlparse(url)
        return parsed_url.hostname
    except Exception:
        return ""

def generate_hash(url: str, length: int = 4) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:length]

def create_txt_record(subdomain: str, target_url: str):
    data = {
        "type": "TXT",
        "name": f"{subdomain}.{DOMAIN}",
        "content": target_url,
        "ttl": 3600
    }
    response = requests.post(CF_API_BASE, headers=HEADERS, json=data)
    if response.status_code != 200 or not response.json().get("success"):
        raise Exception(f"Error creating TXT record: {response.text}")
    return response.json()

def resolve_txt_record(subdomain: str):
    fqdn = f"{subdomain}.{DOMAIN}"
    try:
        answers = dns.resolver.resolve(fqdn, "TXT")
        for rdata in answers:
            return rdata.to_text().strip('"')
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return None
    except Exception:
        return None

@app.errorhandler(Exception)
def handle_all_errors(e):
    response = {
        "error": str(e),
        "type": type(e).__name__
    }
    return jsonify(response), getattr(e, "code", 500)

@app.errorhandler(404)
def handle_404(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(405)
def handle_405(e):
    return jsonify({"error": "Method not allowed"}), 405

@app.route("/api/create", methods=["POST"])
def create_short_url():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    long_url = data.get("url", "").strip()
    if not long_url or not is_valid_url(long_url):
        return jsonify({"error": "Invalid URL"}), 400

    domain = extract_domain(long_url)
    if not domain:
        return jsonify({"error": "Invalid domain extracted from URL"}), 400

    short_hash = generate_hash(long_url)
    short_url = f"{short_hash}.{DOMAIN}"

    try:
        create_txt_record(short_hash, long_url)
    except Exception as e:
        return jsonify({"error": f"Failed to create TXT record: {str(e)}"}), 500

    return jsonify({
        "short_url": short_url,
        "hash": short_hash,
        "original_url": long_url
    })

@app.route("/<hash_code>")
def redirect_from_hash(hash_code):
    target_url = resolve_txt_record(hash_code)
    if not target_url:
        return jsonify({"error": "URL not found"}), 404

    return jsonify({
        "short_url": f"{hash_code}.{DOMAIN}",
        "redirect_url": target_url
    })


@app.route("/")
def index():
    return jsonify({
        "message": "DNS URL Shortener API is running",
        "endpoints": {
            "POST /api/create": "Create a new short URL (JSON: { url })",
            "GET /<hash>": "Redirect using DNS TXT"
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
