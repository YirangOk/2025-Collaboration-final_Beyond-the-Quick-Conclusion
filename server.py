# server.py
import os, openai, requests, random
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv

# ── ENV & OPENAI ──────────────────────────────────────────────────────────────
load_dotenv(override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:  # pragma: no cover
    raise SystemExit("OPENAI_API_KEY missing in .env")

client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ── FLASK APP ─────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates")
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# ── PROMPTS ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a proactive companion AI.
Answer the user's request clearly and help them keep momentum by suggesting next steps.
Return ONLY the main answer text; UI buttons are handled separately.
"""

STYLE = {
    "self_reflect": """
You are a reflective coach.
• ask 2-3 why/how questions to deepen self-insight.
• never jump to ready-made solutions.
""",
    "build_together": """
You are a collaborative facilitator.
• break ideas into steps.
• prefix each step with “→ Next step:”.
""",
    "challenge_me": """
You are a playful challenger.
• offer a fresh angle or one mini-mission.
• use light humour, finish with an action prompt.
"""
}

DEFAULT_BUTTONS = [
    {"id": "self_reflect",   "label": "Self reflect"},
    {"id": "build_together", "label": "Build together"},
    {"id": "challenge_me",   "label": "Challenge me!"}
]

# ── RESOURCE FETCHERS (stub + sample) ─────────────────────────────────────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # optional, for real articles

def fetch_articles(query: str):
    if NEWS_API_KEY:
        url = "https://newsapi.org/v2/everything"
        params = {"q": query, "sortBy": "relevancy", "pageSize": 5, "apiKey": NEWS_API_KEY}
        r = requests.get(url, params=params, timeout=8).json()
        return [{"title":a["title"], "source":a["source"]["name"],
                 "url":a["url"], "summary":a["description"] or ""} for a in r.get("articles", [])]
    # sample fallback
    return [
        {"title":"Sample article A", "source":"Demo News",
         "url":"https://example.com/a", "summary":"Demo summary …"},
        {"title":"Sample article B","source":"Demo News",
         "url":"https://example.com/b","summary":"Demo summary …"}
    ]

def fetch_books(query: str):
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": query, "maxResults": 5}
    r = requests.get(url, params=params, timeout=8).json()
    items = []
    for v in r.get("items", []):
        info = v["volumeInfo"]
        items.append({
            "title": info.get("title"),
            "source": ", ".join(info.get("authors", [])) or "Unknown",
            "url": info.get("infoLink"),
            "summary": info.get("description", "")[:160]
        })
    return items or [{"title":"No books found","source":"","url":"","summary":""}]

def fetch_experts(query: str):
    # simple random demo data
    names = ["Dr. Kim","Prof. Janssen","Alex Rivera","Samira Al-Hashimi"]
    random.shuffle(names)
    return [{"title": n, "source":"Expert", "url":"mailto:contact@example.com",
             "summary":f"{n} may help with “{query}”. Contact for advice."}
            for n in names[:3]]

# ── ROUTES ────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data       = request.get_json(force=True) or {}
    text       = (data.get("text") or "").strip()
    mode       = data.get("mode", "self_reflect")
    if not text:
        return jsonify({"error":"No input"}), 400
    prompt = SYSTEM_PROMPT + STYLE.get(mode, "")
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"system","content":prompt},
                  {"role":"user","content":text}]
    )
    answer = completion.choices[0].message.content.strip()
    return jsonify({"response":answer,"suggested_buttons":DEFAULT_BUTTONS})

@app.route("/resources", methods=["POST"])
def resources():
    data   = request.get_json(force=True) or {}
    q      = (data.get("query") or "").strip()
    rtype  = data.get("resource_type")
    if not q or rtype not in ("articles","books","experts"):
        return jsonify({"error":"bad request"}), 400
    if rtype=="articles": items = fetch_articles(q)
    elif rtype=="books":  items = fetch_books(q)
    else:                 items = fetch_experts(q)
    return jsonify({"resources":items})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))