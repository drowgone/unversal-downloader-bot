# 🎵 Universal Downloader Bot

**Universal Downloader Bot** is a high-performance, scalable Telegram bot designed to download media from **YouTube**, **Instagram**, **TikTok**, and over 1000+ other sites. It supports high-quality video/audio downloads, playlists, and handles large files efficiently using a microservices architecture.

## ✨ Features

- **📺 Multi-Platform Support**:
  - **YouTube**: Videos, Audio (MP3), and Playlists.
  - **Instagram**: Reels, Stories, Posts, and Carousels.
  - **TikTok**: Watermark-free video downloads.
  - **Other**: Support for 1000+ sites via `yt-dlp`.
- **🚀 High Performance**:
  - Asynchronous task processing with **Celery** & **Redis**.
  - scalable worker nodes for handling concurrent downloads.
- **🛠 Advanced Tools**:
  - Format selection (MP3/MP4) and Quality options.
  - Automatic video compression for Telegram limits.
  - Smart link detection and processing.
- **👤 User Management**:
  - Admin panel for broadcasting and user management.
  - Subscription system (Free/Premium/Admin) with usage limits.
  - Ban/Unban functionality.
- **🐳 Dockerized**: Fully containerized for easy deployment.

## 🏗 Tech Stack

- **Language**: Python 3.11+
- **Framework**: [python-telegram-bot](https://python-telegram-bot.org/) (v20+)
- **Task Queue**: Celery & Redis
- **Database**: PostgreSQL (User data & Job persistence)
- **Storage**: Local filesystem / MinIO (S3 compatible) compatible
- **Containerization**: Docker & Docker Compose

## 🚀 Installation & Deployment

### Prerequisites

- Docker & Docker Compose installed on your server.
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather)).

### Quick Start (Docker)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/drowgone/unversal-downloader-bot.git
   cd unversal-downloader-bot
   ```

2. **Configure Environment:**
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your credentials:
   ```env
   # Telegram
   BOT_TOKEN=your_bot_token_here
   ADMIN_IDS=12345678,87654321

   # Database
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=secret
   POSTGRES_DB=media_downloader
   
   # Redis
   REDIS_URL=redis://redis:6379/0
   ```

3. **Run with Docker Compose:**
   ```bash
   docker-compose up -d --build
   ```

4. **Verify:**
   Check if containers are running:
   ```bash
   docker-compose ps
   ```

### Local Development (Manual)

1. **Install System Dependencies:**
   - Python 3.11+
   - FFmpeg (Required for media conversion)
   - Redis Server
   - PostgreSQL Server



## ⚙️ Configuration

The application is configured via the `.env` file. Key settings include:

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram Bot API Token | Required |
| `ADMIN_IDS` | Comma-separated Admin User IDs | Required |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `POSTGRES_URL` | Database connection URL | `postgresql://...` |
| `STORAGE_DIR` | Directory for temporary downloads | `./storage` |
| `MAX_FILE_SIZE_MB` | Max file size for uploads | `50` |
| `MAX_CONCURRENT_JOBS` | Max parallel downloads per user | `2` |

## 📂 Project Structure

```
.
├── app/
│   ├── bot/            # Telegram handlers & keyboards
│   ├── core/           # Config & Logging
│   ├── db/             # Database models & session
│   ├── services/       # Business logic (Instagram, Media, Users)
│   ├── workers/        # Celery tasks
│   └── main.py         # Entry point
├── docker-compose.yml  # Container orchestration
├── Dockerfile          # Image definition
└── requirements.txt    # Python dependencies
```

## 📝 Commands

- `/start` - Start the bot and see status.
- `/stats` - (Admin) View system statistics.
- `/users` - (Admin) Users list
- `/search <username>` - (Admin) search user id
- `/broadcast <message>` - (Admin) Send message to all users.
- `/ban <user_id>` - (Admin) Ban a user.
- `/unban <user_id>` - (Admin) Unban a user.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.
