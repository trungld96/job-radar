# Job Radar

Quét bài đăng outsource/remote từ 9 nguồn → score theo stack của team → bắn qua Telegram.

## Nguồn đã tích hợp

| Nguồn | Loại | Auth cần? |
|---|---|---|
| Hacker News "Who is hiring" | Algolia API | không |
| RemoteOK | JSON API | không |
| Remotive | JSON API | không |
| We Work Remotely | RSS (5 categories) | không |
| Reddit r/forhire, r/hireaprogrammer, r/jobbit, r/remotejs | JSON | không |
| Upwork | RSS (đôi khi bị rate-limit) | không |
| Freelancer.com | Public API | không |
| PeoplePerHour | RSS | không |
| Guru | RSS | không |

## Setup (một lần)

```bash
cd d:\CODE\OS\job-radar

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Cấu hình Telegram
Token đã có sẵn trong `.env`. Cần lấy `chat_id`:

1. Mở Telegram, tìm bot của anh (bot đã tạo), nhấn **Start** hoặc gửi bất kỳ tin nhắn nào.
2. Chạy:
   ```bash
   python setup_chat_id.py
   ```
   Script sẽ tự động ghi `TELEGRAM_CHAT_ID` vào `.env`.

## Chạy thử

```bash
python main.py
```

Log sẽ in ra: fetched bao nhiêu / kept bao nhiêu / dropped vì lý do gì / sent bao nhiêu.

## Chạy định kỳ — 2 lựa chọn

### Option A: Local (Windows Task Scheduler) — 10 phút/lần
1. Mở **Task Scheduler** → **Create Task**.
2. Tab **Triggers** → **New** → `On a schedule` → Daily → **Repeat task every: 10 minutes**, Duration: **Indefinitely**.
3. Tab **Actions** → **New** → **Start a program**:
   - Program: `d:\CODE\OS\job-radar\run.bat`
   - Start in: `d:\CODE\OS\job-radar`
4. Tab **Conditions** → bỏ tick "Start only if AC power" (nếu laptop).
5. Folder `logs\` đã có sẵn.

### Option B: GitHub Actions (free, không cần máy anh bật) — recommend
Xem section **Deploy** bên dưới.

## Deploy free lên GitHub Actions

1. **Tạo GitHub repo** (private hoặc public đều được — private cũng free 2000 min/tháng):
   ```bash
   cd d:\CODE\OS\job-radar
   git init
   git add .
   git commit -m "init job-radar"
   git branch -M main
   git remote add origin https://github.com/<username>/job-radar.git
   git push -u origin main
   ```
   File `.env` sẽ tự bị bỏ qua theo `.gitignore` — token an toàn.

2. **Thêm secrets** trên GitHub: Repo → Settings → Secrets and variables → Actions → **New repository secret**:
   - `TELEGRAM_BOT_TOKEN` = token từ @BotFather
   - `TELEGRAM_CHAT_ID` = chat id (lấy bằng `python setup_chat_id.py`)

3. **Enable Actions**: Repo → Actions tab → nếu bị disable, nhấn **I understand my workflows, enable them**.

4. **Trigger thử**: Actions → chọn workflow "Job Radar" → **Run workflow** → chọn branch main → Run. Xem log realtime.

5. **Sau đó tự động chạy** mỗi 10 phút.

**Cách hoạt động:**
- Mỗi lần chạy: checkout repo → cài deps → chạy `main.py` → nếu có job mới bắn Telegram thì commit `storage.db` back để lần sau không trùng.
- Repo sẽ có commit auto `chore: update dedup state` — bình thường.

**Alternatives khác** (nếu không muốn dùng GHA):
| Platform | Free tier | Setup |
|---|---|---|
| Oracle Cloud Free VM (Arm) | Vĩnh viễn free | Setup VM + cron, ~30 phút |
| Fly.io | Không còn free cho user mới | - |
| Railway | $5 credit/tháng | 1 click deploy |
| Render Cron | Cron jobs chỉ có ở plan trả phí | ❌ |
| PythonAnywhere | 1 scheduled task/ngày | ❌ (không đủ 10 phút) |

## Cấu hình

Sửa `config.yaml`:
- `min_score`: raise nếu quá nhiều noise (default 40)
- `max_age_hours`: bỏ qua job cũ hơn N giờ (default 72)
- `sources`: tắt nguồn không dùng
- `scoring.*.keywords`: thêm/bớt keyword — mỗi match cộng `weight` điểm
- `scoring.blacklist`: hard-drop nếu match

## Cấu trúc

```
job-radar/
├── main.py              orchestrator
├── setup_chat_id.py     helper Telegram
├── config.yaml          keywords + scoring
├── .env                 secrets (không commit)
├── run.bat              entry cho Task Scheduler
├── core/
│   ├── models.py        Job dataclass
│   ├── config.py        load config
│   ├── dedup.py         SQLite: seen_jobs
│   ├── filter.py        blacklist + age filter
│   └── scorer.py        keyword scoring
├── scrapers/            9 file, mỗi nguồn 1 file
└── notifier/telegram.py Telegram Bot API client
```

## Thêm nguồn mới

1. Tạo file `scrapers/newsource.py`, kế thừa `BaseScraper`, implement `fetch() -> list[Job]`.
2. Đăng ký trong `scrapers/__init__.py` → `ALL_SCRAPERS`.
3. Bật trong `config.yaml` → `sources.newsource: true`.

## Troubleshooting

- **Upwork trả 403/429**: RSS của họ chống bot rất nhạy. Có thể tắt trong config nếu spam log.
- **Không có job nào được gửi**: hạ `min_score` xuống ~25 để test, sau đó nâng dần.
- **Trùng lặp**: `storage.db` (SQLite) lưu `dedup_key = source:external_id`. Xoá file này để reset.
