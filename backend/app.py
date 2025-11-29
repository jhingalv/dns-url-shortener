from flask import Flask, redirect, request, jsonify
import os
import requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")
DOMAIN = os.getenv("DOMAIN")

HEADERS = {
    "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
    "Content-Type": "application/json",
}

CF_API_BASE = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records"

@app.route("/<short_path>")
def redirect_short(short_path):
    # Lookup TXT record
    try:
        resp = requests.get(
            CF_API_BASE,
            headers=HEADERS,
            params={"type": "TXT", "name": short_path}
        )
        data = resp.json()
        if not data.get("success") or len(data.get("result", [])) == 0:
            return jsonify({"error": "Short URL not found"}), 404
        long_url = data["result"][0]["content"]
        return redirect(long_url, code=302)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/create", methods=["POST"])
def create_short():
    # Input JSON: { "path": "abc", "url": "https://..." }
    data = request.get_json()
    if not data or "path" not in data or "url" not in data:
        return jsonify({"error": "Missing 'path' or 'url'"}), 400
    path = data["path"].strip()
    url = data["url"].strip()
    
    payload = {
        "type": "TXT",
        "name": path,
        "content": url,
        "ttl": 3600
    }
    
    try:
        resp = requests.post(CF_API_BASE, headers=HEADERS, json=payload)
        result = resp.json()
        if not result.get("success"):
            return jsonify({"error": result}), 500
        return jsonify({"short_url": f"{path}.{DOMAIN}", "original_url": url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def index():
    return jsonify({"message": "DNS TXT URL Shortener running"})
