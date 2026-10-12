# BT-02 — Website cá nhân trên Docker

Website giới thiệu cá nhân chạy trong **Docker** trên **Ubuntu Server (VMware)**, báo tin nhắn từ khách tới điện thoại qua **Discord Webhook**, admin cập nhật banner từ xa, image đẩy lên **Docker Hub**, và phát hành ra Internet qua **Cloudflare Tunnel**.

> 🔗 **Link trực tiếp (live):** **https://reasons-messages-titanium-juice.trycloudflare.com**

---

## 1. Tính năng

- Trang chủ giới thiệu cá nhân: **HÀ ĐIỀN TRUNG HIẾU**, sinh viên năm 3 trường **VKU - Đại học Việt - Hàn**, kỹ sư phần mềm — tông màu terminal ENCOM OS12.
- Form **liên hệ**: khách điền tên + thông điệp → gửi về **Discord Webhook** (điện thoại nhận thông báo tức thì).
- Trang **admin** (`/admin`): đăng nhập bằng mật khẩu → cập nhật **banner** hiển thị trên trang chủ từ bất kỳ đâu (kể cả điện thoại qua Internet).
- Chống spam: giới hạn tần suất gửi (mặc định 1 lần/5 giây), chống brute-force đăng nhập (khoá IP sau 5 lần sai).
- Chạy container phi-root (non-root user), healthcheck, `restart: unless-stopped`.

## 2. Công nghệ

| Thành phần | Công nghệ |
|---|---|
| Backend | Python 3.11 + Flask 3.0 + gunicorn |
| Frontend | HTML/CSS/JS thuần, responsive |
| Thông báo | Discord Webhook (requests) |
| Triển khai | Docker (Dockerfile), Docker Compose |
| Cơ sở dữ liệu | File JSON (`data/banner.json`) |
| Public | Cloudflare Quick Tunnel (`cloudflared`) |

## 3. Cấu trúc thư mục

```
BaiTap2/
├── app.py               # Flask app - routes chính
├── config.py            # Cấu hình (webhook, mật khẩu, giới hạn tần suất...)
├── storage.py           # Đọc/ghi banner.json (atomic)
├── discord_notify.py    # Gửi tin nhắn tới Discord Webhook
├── requirements.txt     # Flask, gunicorn, requests, python-dotenv
├── Dockerfile           # Image krone1/bt02-website:1.0
├── docker-compose.yml   # Orchestration + volume data
├── .env.example         # Mẫu biến môi trường (copy -> .env)
├── templates/           # index.html, admin.html
├── static/              # css/style.css, js/main.js, img/avatar.png
├── data/                # banner.json (volume, giữ khi restart)
└── .preview/            # Screenshot minh chứng
```

## 4. Cấu hình môi trường

Copy `.env.example` → `.env` và điền giá trị thật:

| Biến | Ý nghĩa |
|---|---|
| `DISCORD_WEBHOOK_URL` | URL Discord Webhook nhận tin nhắn liên hệ |
| `ADMIN_PASSWORD` | Mật khẩu trang admin |
| `SECRET_KEY` | Khóa bảo mật Flask (đổi ngẫu nhiên) |
| `RATE_LIMIT_SECONDS` | Số giây tối thiểu giữa 2 lần gửi (mặc định 5) |
| `LOGIN_MAX_ATTEMPTS` | Số lần sai trước khi khoá IP |
| `LOGIN_LOCKOUT_SECONDS` | Thời gian khoá IP (giây) |

> ⚠️ **Không bao giờ commit `.env`** — đã có trong `.gitignore` và `.dockerignore`.

## 5. Chạy local (không Docker)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # rồi điền giá trị thật
python app.py          # -> http://localhost:8000
```

## 6. Chạy bằng Docker

```bash
docker login            # đăng nhập Docker Hub
docker build -t krone1/bt02-website:1.0 .
docker run -d --name bt02-website --env-file .env \
  -v ./data:/data -p 8000:8000 krone1/bt02-website:1.0
```

Hoặc bằng Compose:

```bash
docker compose up -d --build
```

Kiểm tra: `curl http://localhost:8000/health` → `{"notify":true,"status":"ok"}`

## 7. Triển khai lên VM (Ubuntu Server trên VMware)

```bash
# cài Docker
curl -fsSL https://get.docker.com | sh

# copy project lên VM (/opt/bt02) rồi
docker compose up -d --build
docker push krone1/bt02-website:1.0    # backup lên Docker Hub

# cấp quyền ghi cho volume (image chạy non-root UID 100/GID 101)
chown -R 100:101 /opt/bt02/data
```

### Public ra Internet (Cloudflare Quick Tunnel — không cần mở cổng, chạy được cả sau CGNAT)

```bash
apt install cloudflared
# chạy nền bền vững qua systemd:
vim /etc/systemd/system/cloudflared-quick.service
```

`cloudflared-quick.service`:

```ini
[Unit]
Description=Cloudflare Quick Tunnel for BT-02
After=network-online.target docker.service

[Service]
ExecStart=/usr/local/bin/cloudflared tunnel --url http://localhost:8000 --no-autoupdate
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload && systemctl enable --now cloudflared-quick
```

**Lấy URL hiện tại** (Quick Tunnel đổi URL mỗi lần cloudflared/VM khởi động lại):

```bash
journalctl -u cloudflared-quick --no-pager | grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" | head -1
```

> Muốn URL cố định + HTTPS: cần 1 tên miền (ví dụ `eu.org` miễn phí hoặc domain mua rẻ) rồi dùng **Cloudflare Named Tunnel**.

## 8. Minh chứng / Screenshot

Xem thư mục `.preview/`:
- `shot-desktop.png` — giao diện desktop
- `shot-mobile.png` — giao diện mobile
- `shot-tablet.png` — giao diện tablet

## 9. API tóm tắt

| Route | Phương thức | Ý nghĩa |
|---|---|---|
| `/` | GET | Trang chủ giới thiệu |
| `/send` | POST | Gửi liên hệ -> Discord (JSON `{name, message}`) |
| `/api/banner` | GET | Đọc banner hiện tại |
| `/admin` | GET/POST | Đăng nhập quản trị |
| `/admin/banner` | POST | Cập nhật banner (cần đăng nhập, xác thực qua session) |
| `/health` | GET | Healthcheck |

## 10. Rubric báo cáo liên quan

- Image Docker Hub: `krone1/bt02-website:1.0` — https://hub.docker.com/r/krone1/bt02-website
- GitHub: https://github.com/HieuDZ609/bt02-website
- Server: Ubuntu 26.04 LTS trên VMware; container `bt02-website` Up (healthy), port `8000`.
- Backup nhanh: `docker pull krone1/bt02-website:1.0 && docker compose up -d`