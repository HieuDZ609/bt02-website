"""Website cá nhân BT-02: Flask + Discord Webhook + trang admin.

Routes:
  GET  /                trang chủ giới thiệu + banner + form gửi thông điệp
  POST /send            khách gửi thông điệp -> push Discord tới điện thoại admin
  GET  /api/banner      lời nhắn mới nhất cho marquee (poll định kỳ)
  GET  /admin           trang quản trị (đăng nhập / cập nhật banner)
  POST /admin/login     xác thực mật khẩu admin
  POST /admin/banner    lưu lời nhắn mới (bắt buộc đã đăng nhập)
  POST /admin/logout    kết thúc phiên
  GET  /health          kiểm tra tình trạng cho Docker healthcheck
"""
import hmac
import logging
import threading
import time

from flask import Flask, jsonify, render_template, request, session

from config import Config
from discord_notify import send_message
from storage import get_banner, set_banner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("web")

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

_RATE_LOCK = threading.Lock()
_LAST_SEND: dict[str, float] = {}
_LOGIN_TRIES: dict[str, dict] = {}


def _client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _rate_ok(ip: str) -> bool:
    now = time.time()
    with _RATE_LOCK:
        last = _LAST_SEND.get(ip, 0.0)
        if now - last < Config.RATE_LIMIT_SECONDS:
            return False
        _LAST_SEND[ip] = now
        if len(_LAST_SEND) > 5000:  # dọn bộ nhớ đệm
            for key, ts in list(_LAST_SEND.items()):
                if now - ts > Config.RATE_LIMIT_SECONDS * 10:
                    _LAST_SEND.pop(key, None)
    return True


def _login_blocked(ip: str) -> bool:
    entry = _LOGIN_TRIES.get(ip)
    if entry and entry.get("until", 0) > time.time():
        return True
    return False


def _login_failed(ip: str):
    now = time.time()
    with _RATE_LOCK:
        entry = _LOGIN_TRIES.get(ip, {"attempts": 0, "until": 0})
        if entry["until"] > now:
            return
        entry["attempts"] += 1
        if entry["attempts"] >= Config.LOGIN_MAX_ATTEMPTS:
            entry["until"] = now + Config.LOGIN_LOCKOUT_SECONDS
            entry["attempts"] = 0
        _LOGIN_TRIES[ip] = entry


def _login_reset(ip: str):
    with _RATE_LOCK:
        _LOGIN_TRIES.pop(ip, None)


def _verify_password(candidate: str) -> bool:
    if not Config.ADMIN_PASSWORD:
        return False
    return hmac.compare_digest(candidate.encode(), Config.ADMIN_PASSWORD.encode())


@app.context_processor
def _inject_globals():
    return {"max_len": Config.MAX_LEN}


@app.get("/")
def index():
    return render_template("index.html", banner=get_banner())


@app.get("/api/banner")
def api_banner():
    return jsonify({"message": get_banner()})


@app.post("/send")
def send():
    payload = request.get_json(silent=True) or request.form
    message = str(payload.get("message", "")).strip()

    if not message:
        return jsonify({"ok": False, "error": "Nội dung không được để trống."}), 400
    if len(message) > Config.MAX_LEN:
        return jsonify(
            {"ok": False, "error": f"Nội dung tối đa {Config.MAX_LEN} ký tự."}
        ), 400
    if not _rate_ok(_client_ip()):
        return jsonify(
            {"ok": False, "error": "Bạn gửi quá nhanh, vui lòng thử lại sau."}
        ), 429

    delivered = send_message(f"📩 Thông điệp mới từ khách:\n\n{message}")
    if not delivered:
        return jsonify(
            {"ok": False, "error": "Không gửi được thông báo, thử lại sau."}
        ), 502
    log.info("Đã chuyển thông điệp từ %s tới Discord", _client_ip())
    return jsonify({"ok": True, "message": "Đã gửi thông điệp, cảm ơn bạn!"})


@app.get("/admin")
def admin_page():
    ip = _client_ip()
    if _login_blocked(ip):
        return render_template(
            "admin.html", mode="login", message="Quá nhiều lần thử, thử lại sau.",
            is_error=True,
        ), 429
    if session.get("admin"):
        return render_template(
            "admin.html", mode="panel", message="", is_error=False,
            banner=get_banner(),
        )
    return render_template("admin.html", mode="login", message="", is_error=False)


@app.post("/admin/login")
def admin_login():
    ip = _client_ip()
    if _login_blocked(ip):
        return render_template(
            "admin.html", mode="login", message="Tạm khoá do nhập sai quá nhiều.",
            is_error=True,
        ), 429

    password = str(request.form.get("password", ""))
    if _verify_password(password):
        _login_reset(ip)
        session["admin"] = True
        log.info("Đăng nhập admin thành công từ %s", ip)
        return render_template(
            "admin.html", mode="panel", message="Đã đăng nhập.",
            is_error=False, banner=get_banner(),
        )

    _login_failed(ip)
    log.warning("Đăng nhập admin thất bại từ %s", ip)
    return render_template(
        "admin.html", mode="login", message="Sai mật khẩu.", is_error=True,
    ), 401


@app.post("/admin/banner")
def admin_set_banner():
    if not session.get("admin"):
        return render_template(
            "admin.html", mode="login", message="Cần đăng nhập.", is_error=True,
        ), 403

    message = str(request.form.get("banner", "")).strip()
    if not message:
        return render_template(
            "admin.html", mode="panel", message="Lời nhắn không được để trống.",
            is_error=True, banner=get_banner(),
        ), 400
    if len(message) > Config.MAX_LEN:
        return render_template(
            "admin.html", mode="panel",
            message=f"Tối đa {Config.MAX_LEN} ký tự.", is_error=True,
            banner=get_banner(),
        ), 400

    set_banner(message)
    log.info("Admin cập nhật banner từ %s", _client_ip())
    return render_template(
        "admin.html", mode="panel", message="Đã cập nhật banner.",
        is_error=False, banner=get_banner(),
    )


@app.post("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return render_template("admin.html", mode="login", message="Đã đăng xuất.",
                           is_error=False)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "notify": Config.NOTIFY_ENABLED})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=False, threaded=True)