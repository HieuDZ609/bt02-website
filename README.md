# BT-02 — Website cá nhân trên Docker

Website giới thiệu cá nhân chạy trong **Docker** trên **Ubuntu Server (VMware)**, báo tin nhắn từ khách tới điện thoại qua **Discord Webhook + Telegram Bot**, admin cập nhật banner từ xa (kể cả nhắn Telegram từ điện thoại), image đẩy lên **Docker Hub**, và phát hành ra Internet qua **Ngrok**. 

> 🔗 **Link trực tiếp (live, cố định):** **https://tint-humped-december.ngrok-free.dev**
>
> _Ngrok free tier hiển thị trang cảnh báo "Visit Site" một lần cho khách bằng trình duyệt._

---

## 1. Tính năng

- Trang chủ giới thiệu cá nhân: **HÀ ĐIỀN TRUNG HIẾU**, sinh viên năm 3 trường **VKU - Đại học Việt - Hàn**, kỹ sư phần mềm — tông màu terminal ENCOM OS12.
- Form **liên hệ**: khách điền tên + thông điệp → gửi về **Discord Webhook** và **Telegram Bot** (điện thoại nhận thông báo tức thì).
- Trang **admin** (`/admin`): đăng nhập bằng mật khẩu → cập nhật **banner** hiển thị trên trang chủ từ bất kỳ đâu (kể cả điện thoại qua Internet).
- **Đổi banner từ điện thoại qua Telegram**: admin nhắn `/banner <nội dung>` cho bot → banner trang chủ cập nhật trong vài giây (không cần mở web).
- Chống spam: giới hạn tần suất gửi (mặc định 1 lần/5 giây), chống brute-force đăng nhập (khoá IP sau 5 lần sai).
- Chạy container phi-root (non-root user), healthcheck, `restart: unless-stopped`.

## 2. Công nghệ

| Thành phần | Công nghệ |
|---|---|
| Backend | Python 3.11 + Flask 3.0 + gunicorn |
| Frontend | HTML/CSS/JS thuần, responsive |
| Thông báo | Discord Webhook + Telegram Bot API (long-poll) |
| Triển khai | Docker (Dockerfile), Docker Compose |
| Cơ sở dữ liệu | File JSON (`data/banner.json`) |
| Public | Ngrok static domain (`ngrok/ngrok`) |

## 3. Cấu trúc thư mục

```
BaiTap2/
├── app.py               # Flask app - routes chính
├── config.py            # Cấu hình (webhook, Telegram, mật khẩu, giới hạn tần suất...)
├── storage.py           # Đọc/ghi banner.json (atomic)
├── discord_notify.py    # Gửi tin nhắn tới Discord Webhook
├── telegram_notify.py   # Gửi tin nhắn tới Telegram (sendMessage)
├── telegram_poller.py   # Long-poll getUpdates: admin /banner <nội dung> -> đổi banner
├── notify.py            # Điều phối gửi song song Discord + Telegram
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
| `DISCORD_WEBHOOK_URL` | URL Discord Webhook nhận tin nhắn liên hệ (tuỳ chọn) |
| `TELEGRAM_BOT_TOKEN` | Token bot Telegram (từ @BotFather) — tuỳ chọn |
| `TELEGRAM_ADMIN_ID` | chat_id Telegram của admin (được phép đổi banner) |
| `TELEGRAM_CHAT_ID` | Nơi nhận thông báo khách (bỏ trống = dùng `TELEGRAM_ADMIN_ID`) |
| `ADMIN_PASSWORD` | Mật khẩu trang admin |
| `SECRET_KEY` | Khóa bảo mật Flask (đổi ngẫu nhiên) |
| `RATE_LIMIT_SECONDS` | Số giây tối thiểu giữa 2 lần gửi (mặc định 5) |
| `LOGIN_MAX_ATTEMPTS` | Số lần sai trước khi khoá IP |
| `LOGIN_LOCKOUT_SECONDS` | Thời gian khoá IP (giây) |

> ⚠️ **Không bao giờ commit `.env`** — đã có trong `.gitignore` và `.dockerignore`.
>
> 🚨 **ĐỪNG chạy `cp .env.example .env` khi `.env` đã tồn tại** — lệnh này sẽ **ghi đè
> và xoá sạch secrets** (Discord/Telegram/Ngrok) khiến link chết. Chỉ tạo lần đầu bằng
> `cp -n .env.example .env` (không ghi đè), hoặc sửa trực tiếp `.env` bằng editor.

### Thiết lập Telegram Bot (đổi banner từ điện thoại)

1. Nhắn **@BotFather** trên Telegram → `/newbot` → đặt tên → nhận `BOT_TOKEN`.
2. Nhắn `/start` cho bot vừa tạo, rồi lấy `chat_id`:
   ```bash
   curl -s "https://api.telegram.org/bot<BOT_TOKEN>/getUpdates"
   # đọc result[].message.chat.id   (hoặc nhắn @userinfobot để lấy id)
   ```
3. Điền `TELEGRAM_BOT_TOKEN` và `TELEGRAM_ADMIN_ID` vào `.env` rồi khởi động lại.
4. Đổi banner từ điện thoại: nhắn **`/banner <nội dung>`** cho bot. Banner trang chủ
   cập nhật trong vài giây. Bot cũng gửi thông báo khi khách điền form.

> Cơ chế: app chạy một thread nền long-poll `getUpdates` (không cần webhook/public URL).
> Chỉ tin từ `TELEGRAM_ADMIN_ID` mới đổi được banner; tin từ người khác bị bỏ qua.
> Offset lưu tại `data/telegram_offset.json` nên không xử lý lại sau khi restart.

## 5. Chạy local (không Docker)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp -n .env.example .env   # -n = chỉ tạo nếu chưa có (KHÔNG ghi đè .env cũ); rồi điền giá trị thật
python app.py             # -> http://localhost:8000
```

## 6. Chạy bằng Docker

```bash
docker login            # đăng nhập Docker Hub
docker build -t krone1/bt02-website:1.0 .
docker run -d --name bt02-website --env-file .env \
  -v ./data:/data -p 8000:8000 --restart unless-stopped \
  krone1/bt02-website:1.0
```

Hoặc bằng Compose:

```bash
docker compose up -d --build
```

> ⚠️ **Chọn 1 trong 2 cách, đừng chạy cả hai.** Compose đã tạo container tên
> `bt02-website` chiếm cổng `8000`. Nếu chạy thêm `docker run` cùng tên/cổng sẽ lỗi:
> `Conflict. The container name "/bt02-website" is already in use` hoặc
> `Bind for 0.0.0.0:8000 failed: port is already allocated`.
> Dọn dẹp: `docker rm -f bt02-website1 bt02-website2` và `docker rmi <image-rác>`.

Kiểm tra: `curl http://localhost:8000/health` → `{"status":"ok","notify":true,"channels":{"discord":true,"telegram":true},"poller":true}`

## 7. Triển khai lên VM (Ubuntu Server trên VMware)

```bash
# 1) cài Docker
curl -fsSL https://get.docker.com | sh

# 2) copy project lên VM (/opt/bt02) bằng rsync/scp/git (xem mục 7.1)
#    LƯU Ý: KHÔNG copy đè file .env đang có secrets lên.

# 3) tạo .env lần đầu (chỉ khi CHƯA có), rồi điền giá trị thật
cp -n .env.example .env && nano .env      # -n: không ghi đè nếu .env đã tồn tại

# 4) chạy stack (web + ngrok)
docker compose up -d --build

# 5) cấp quyền ghi cho volume (container chạy non-root UID 100/GID 101)
chown -R 100:101 /opt/bt02/data

# 6) backup image lên Docker Hub
docker push krone1/bt02-website:1.0
```

### 7.1 Chuyển code từ laptop lên VM

```bash
# rsync (khuyên dùng): đồng bộ code nhưng BỎ QUA .env và data để không mất secrets/banner
rsync -az --delete \
  --exclude='.env' --exclude='.git' --exclude='.venv' \
  --exclude='data' --exclude='__pycache__' \
  ./ root@<ip-vm>:/opt/bt02/
```

> 🚨 Tuyệt đối không để `.env` bị ghi đè. Nếu lỡ mất secrets, phải điền lại
> `DISCORD_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_ID`, `NGROK_AUTHTOKEN`,
> `ADMIN_PASSWORD`, `SECRET_KEY` rồi `docker compose up -d --force-recreate`.

### Public ra Internet (Ngrok — URL cố định, không cần mở cổng, chạy được sau CGNAT)

Dịch vụ `ngrok` được thêm vào `docker-compose.yml`, dùng **static domain** cố định nên URL **không đổi** khi khởi động lại:

```yaml
  ngrok:
    image: ngrok/ngrok:latest
    container_name: bt02-ngrok
    restart: unless-stopped
    depends_on:
      - web
    command: ["http", "web:8000", "--url=https://tint-humped-december.ngrok-free.dev", "--log", "stdout"]
    environment:
      NGROK_AUTHTOKEN: ${NGROK_AUTHTOKEN}
```

```bash
# thêm NGROK_AUTHTOKEN vào .env rồi:
docker compose up -d
```

> **Lưu ý free tier:** trình duyệt của khách sẽ gặp trang cảnh báo "You are about to visit…" bấm **Visit Site** mới vào. Client gửi header `ngrok-skip-browser-warning: true` sẽ bỏ qua. Muốn URL sạch không cảnh báo → dùng **Cloudflare Named Tunnel + tên miền**.

### (Tuỳ chọn) Cloudflare Quick Tunnel

Có thể chạy song song Cloudflare Quick Tunnel để có link dự phòng không cảnh báo (nhưng URL đổi mỗi lần restart):

```bash
apt install cloudflared
# systemd unit: cloudflared tunnel --url http://localhost:8000 --no-autoupdate
journalctl -u cloudflared-quick --no-pager | grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" | head -1
```

## 8. Minh chứng / Screenshot

Xem thư mục `.preview/`:
- `shot-desktop.png` — giao diện desktop
- `shot-mobile.png` — giao diện mobile
- `shot-tablet.png` — giao diện tablet

## 9. API tóm tắt

| Route | Phương thức | Ý nghĩa |
|---|---|---|
| `/` | GET | Trang chủ giới thiệu |
| `/send` | POST | Gửi liên hệ -> Discord + Telegram (JSON `{name, message}`) |
| `/api/banner` | GET | Đọc banner hiện tại |
| `/admin` | GET/POST | Đăng nhập quản trị |
| `/admin/banner` | POST | Cập nhật banner (cần đăng nhập, xác thực qua session) |
| `/health` | GET | Healthcheck |

## 10. Rubric báo cáo liên quan

- Image Docker Hub: `krone1/bt02-website:1.0` — https://hub.docker.com/r/krone1/bt02-website
- GitHub: https://github.com/HieuDZ609/bt02-website
- Server: Ubuntu 26.04 LTS trên VMware; container `bt02-website` Up (healthy), port `8000`.
- Backup nhanh: `docker pull krone1/bt02-website:1.0 && docker compose up -d`

## 11. Xử lý sự cố (troubleshooting)

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| `Conflict. The container name "/bt02-website" is already in use` | Đã có container (compose) cùng tên | Dùng compose **hoặc** `docker run`, đừng cả hai; hoặc `docker rm -f <tên>` |
| `Bind for 0.0.0.0:8000 failed: port is already allocated` | Cổng 8000 đang bị container khác chiếm | `docker compose down` rồi `docker compose up -d`, hoặc đổi `-p 8001:8000` |
| `docker compose ps` thấy `ngrok ... Restarting` | Thiếu `NGROK_AUTHTOKEN` trong `.env` | Điền lại token rồi `docker compose up -d --force-recreate` |
| `/health` báo `discord:false, telegram:false` | `.env` bị ghi đè/rỗng | Khôi phục secrets trong `.env` rồi recreate |
| `Permission denied` khi ghi `/data` | Sai chủ sở hữu volume | `chown -R 100:101 /opt/bt02/data` |
| Link ngrok chết | VM tắt hoặc container ngrok down | Bật VM, `docker compose up -d` (URL cố định nên vẫn cũ) |
| Banner không đổi khi nhắn `/banner` | Sai `TELEGRAM_ADMIN_ID` | So lại chat_id trong `getUpdates`, khởi động lại |
| Poller báo lỗi `409 Conflict` | Có nơi khác cũng gọi `getUpdates` | Chỉ để 1 poller chạy; tránh gọi `getUpdates` thủ công |

> 🚨 Lỗi phổ biến nhất: chạy `cp .env.example .env` khi `.env` đã tồn tại → **mất secrets**.
> Luôn dùng `cp -n` hoặc sửa trực tiếp `.env`.