"""Flask app serving the chat widget and the /chat API."""

import os
import sys
import time
import uuid
from collections import OrderedDict, defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify, request, send_from_directory

from chatbot.responses import get_reply, new_session_state

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"

MAX_MESSAGE_LENGTH = 500
MAX_SESSION_ID_LENGTH = 128
MAX_SESSIONS = 5000
RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 10

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024  # reject oversized request bodies

# In-memory session store: session_id -> dialog state dict. Capped and
# FIFO-evicted so a flood of fake session ids can't grow this unbounded.
# Fine for a single-process demo; a real deployment would use Redis with TTLs.
sessions = OrderedDict()

# In-memory per-IP request timestamps for basic abuse/DoS mitigation.
request_log = defaultdict(deque)


def _rate_limited(ip):
    now = time.time()
    log = request_log[ip]
    while log and now - log[0] > RATE_LIMIT_WINDOW_SECONDS:
        log.popleft()
    if len(log) >= RATE_LIMIT_REQUESTS:
        return True
    log.append(now)
    return False


def _get_session_state(session_id):
    if session_id in sessions:
        sessions.move_to_end(session_id)
        return sessions[session_id]

    if len(sessions) >= MAX_SESSIONS:
        sessions.popitem(last=False)

    state = new_session_state()
    sessions[session_id] = state
    return state


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.route("/chat", methods=["POST"])
def chat():
    if _rate_limited(request.remote_addr):
        return jsonify({"error": "Too many requests, please slow down."}), 429

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    message = payload.get("message")
    if message is None:
        message = ""
    if not isinstance(message, str):
        return jsonify({"error": "'message' must be a string."}), 400
    message = message.strip()[:MAX_MESSAGE_LENGTH]

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id or len(session_id) > MAX_SESSION_ID_LENGTH:
        session_id = str(uuid.uuid4())

    if not message:
        return jsonify({"session_id": session_id, "reply": "Please type a message.", "intent": None})

    state = _get_session_state(session_id)

    try:
        reply, intent = get_reply(state, message)
    except Exception:
        app.logger.exception("Unhandled error while generating a reply")
        return jsonify({
            "session_id": session_id,
            "reply": "Sorry, something went wrong on my end. Please try again.",
            "intent": None,
        }), 500

    return jsonify({"session_id": session_id, "reply": reply, "intent": intent})


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    app.run(debug=debug, host=host, port=port)
