from flask import Flask, request, jsonify
import hashlib
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
    raise ValueError("Missing environment variables: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID or DOMAIN")

CF_API_BASE = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records"
HEADERS = {
    "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
    "Content-Type": "application/json",
}

def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except:
        return False

def generate_hash(url: str, length: int = 4) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:length]

def create_txt_record(subdomain: str, target_url: str):
    name = f"{subdomain}.urlshorten"
    data = {
        "type": "TXT",
        "name": name,
        "content": target_url,
        "ttl": 3600
    }
    resp = requests.post(CF_API_BASE, headers=HEADERS, json=data)
    result = resp.json()
    if not result.get("success"):
        raise Exception(f"Cloudflare API error: {result}")
    return name

@app.route("/api/create", methods=["POST"])
def create_short_url():
    data = request.get_json(silent=True)
    if not data or "url" not in data:
        return jsonify({"error": "Missing JSON body with 'url'"}), 400

    long_url = data["url"].strip()
    if not is_valid_url(long_url):
        return jsonify({"error": "Invalid URL"}), 400

    short_hash = generate_hash(long_url)

    try:
        short_name = create_txt_record(short_hash, long_url)
    except Exception as e:
        return jsonify({"error": f"Failed to create TXT record: {str(e)}"}), 500

    short_url = f"{short_hash}.urlshorten.{DOMAIN}"

    return jsonify({
        "short_url": short_url,
        "hash": short_hash,
        "original_url": long_url
    })

@app.route("/<hash_code>", methods=["GET"])
def get_short_url(hash_code):
    name = f"{hash_code}.urlshorten"
    try:
        url = f"{CF_API_BASE}?type=TXT&name={name}"
        resp = requests.get(url, headers=HEADERS)
        data = resp.json()
        if not data.get("success") or len(data.get("result", [])) == 0:
            return jsonify({"error": "Short URL not found"}), 404
        target_url = data["result"][0]["content"]
    except Exception as e:
        return jsonify({"error": f"Failed to fetch TXT record: {str(e)}"}), 500

    return jsonify({
        "short_url": f"{hash_code}.urlshorten.{DOMAIN}",
        "redirect_url": target_url
    })

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "message": "DNS URL Shortener API running",
        "endpoints": {
            "POST /api/create": "Create a new short URL (JSON: { url })",
            "GET /<hash>": "Get original URL from TXT record"
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
