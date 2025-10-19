# FastNPC

<div align="center">

**[简体中文](README.md) | English**

---

**Intelligent AI Character Auto-Construction System Based on Encyclopedia Data**

A complete solution for rapidly automating the construction of interactive AI characters, supporting the full pipeline from encyclopedia data to structured character profiles.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.112+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.1+-61DAFB.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

### 🌐 Online Experience

**Try Now: [https://changan00.cn](https://changan00.cn)**

Welcome to try online and quickly create and chat with your AI characters!

</div>

---

## 📖 Introduction

FastNPC is an innovative AI character automation platform that can automatically scrape character information from knowledge sources such as Baidu Baike and Wikipedia, intelligently generate structured character profiles through Large Language Models (LLM), and provide complete conversational interaction capabilities.

### 🎯 Core Value

- **Automated Construction**: Just enter a character name to automatically complete data scraping, structured processing, and character generation
- **High-Quality Profiles**: Professional character personality profiles based on 8 structured dimensions
- **Intelligent Memory System**: Three-layer memory architecture (session/short-term/long-term) for coherent long-term conversations
- **Multi-Character Group Chat**: Support for multi-character group chat scenarios with intelligent moderation for speaking order
- **Ready to Use**: Complete front-end and back-end separation architecture with a friendly Web interface

---

## ✨ Core Features

### 🤖 Character Construction

- **Multi-Source Data Scraping**
  - Support for Baidu Baike (including disambiguation)
  - Support for Chinese Wikipedia
  - Intelligent selection of candidate entries
  
- **Structured Processing**
  - 9 character profile categories: Basic Identity, Personality, Background, Appearance, Behavior, Relationships, Skills, Values, Emotions
  - Concurrent generation optimization (configurable concurrency)
  - Automatic character bio generation
  - Avatar upload support (crop, compress, format conversion)

### 💬 Dialogue System

- **Single Character Chat**
  - Six-part System Prompt (Rules + Profile + Memory + Subject + Session)
  - Three-layer memory system (Session Memory → Short-term Memory → Long-term Memory)
  - Automatic memory compression and integration
  - Streaming response support

- **Multi-Character Group Chat**
  - Intelligent moderation for next speaker
  - Role selection based on plot logic
  - Independent memory management (each character has independent memory)
  - Dynamic group member management

### 🔐 User System

- Complete user authentication (registration/login)
- Privatized character management
- Admin backend (user management, character review)
- Personalized configuration (model selection, memory budget, personal bio)

### 🎯 Prompt Version Management

- **Database-Driven Prompt System**
  - All LLM prompts stored in database
  - 9 structured generation prompt categories
  - Single/group chat system prompts
  - Memory compression and integration prompts
  
- **Complete Version Control**
  - Auto-create new version on each edit
  - Full version history retention
  - One-click activate/rollback any version
  - Version comparison and diff view

### 🧪 Testing & Evaluation System

- **Test Case Management**
  - Support for character and group test cases
  - Full CRUD operations
  - Test case version control
  - Quick test environment reset

- **Intelligent Evaluators**
  - 15 specialized evaluators (9 for structured gen + 6 others)
  - LLM-driven automatic evaluation
  - Structured scoring (score, strengths, weaknesses, suggestions)
  - Evaluator prompt version management

- **Test Execution**
  - Single/batch/category execution
  - Flexible version selection (prompts + evaluators)
  - Real-time execution status
  - Dual view: raw text + structured results

### ⚡ Performance Optimization

- **Database Support**
  - PostgreSQL (production recommended)
  - SQLite (development environment)
  - Optimized connection pooling (10-50 connections)
  - Automatic connection leak detection

- **Caching System**
  - Redis for hot data caching
  - Character list cache
  - Prompt cache
  - Auto cache invalidation

- **Monitoring Tools**
  - Connection pool status monitoring
  - Stress test scripts
  - Real-time log tracking

---

## 🛠️ Tech Stack

### Backend

- **Framework**: FastAPI 0.112+ & Gunicorn
- **Database**: PostgreSQL 13+ / SQLite3
- **Cache**: Redis 6+
- **LLM API**: OpenRouter API (compatible with OpenAI SDK)
- **Web Scraping**: Requests + BeautifulSoup4 + Playwright (optional)
- **Authentication**: Cookie signing (itsdangerous) + Bcrypt password hashing
- **Connection Pool**: psycopg2 ThreadedConnectionPool

### Frontend

- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite 7
- **HTTP Client**: Axios
- **Styling**: CSS Modules
- **Image Processing**: Cropper.js

### Core Dependencies

```
fastapi>=0.112.0          # Web framework
uvicorn[standard]>=0.30.0 # ASGI server
gunicorn>=23.0.0          # WSGI server
openai>=1.40.0            # LLM SDK
psycopg2-binary>=2.9.0    # PostgreSQL driver
redis>=5.0.0              # Redis client
beautifulsoup4>=4.12.3    # HTML parsing
sqlalchemy>=2.0.32        # ORM
passlib[bcrypt]>=1.7.4    # Password encryption
python-dotenv>=1.0.1      # Environment variable management
pillow>=10.0.0            # Image processing
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn

### 1. Clone the Project

```bash
git clone https://github.com/changan593/FastNPC.git
cd FastNPC
```

### 2. Configure Environment Variables

Copy the example environment file and edit it:

```bash
cp env.example .env
```

Edit the `.env` file and fill in the required configuration:

```ini
# Required: Secret key (for Cookie signing, recommend using a random string)
FASTNPC_SECRET=your-random-secret-key-here

# Required: OpenRouter API key
OPENROUTER_API_KEY=sk-or-v1-xxxxx

# Optional: Admin username
FASTNPC_ADMIN_USER=admin

# Optional: Frontend URL (CORS configuration)
FASTNPC_FRONTEND_ORIGIN=http://localhost:5173

# Optional: Structuring concurrency (default 4, recommend 2-8)
FASTNPC_MAX_CONCURRENCY=4
```

### 3. Install Backend Dependencies

Using a virtual environment is recommended:

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Start Backend Service

```bash
uvicorn fastnpc.api.server:app --host 0.0.0.0 --port 8000 --reload
```

The backend service will start at `http://localhost:8000`.

### 5. Install Frontend Dependencies

```bash
cd web/fastnpc-web
npm install
```

### 6. Start Frontend Development Server

```bash
npm run dev -- --host --port 5173
```

The frontend service will start at `http://localhost:5173`.

### 7. Access the Application

- **Frontend Interface**: http://localhost:5173
- **Backend API Docs**: http://localhost:8000/docs

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FASTNPC_SECRET` | ✅ | None | Cookie signing key, must set a strong random string |
| `OPENROUTER_API_KEY` | ✅ | None | OpenRouter API key for LLM calls |
| `USE_POSTGRESQL` | ❌ | `false` | Use PostgreSQL (`true` recommended for production) |
| `POSTGRES_HOST` | ❌ | `localhost` | PostgreSQL host address |
| `POSTGRES_PORT` | ❌ | `5432` | PostgreSQL port |
| `POSTGRES_DB` | ❌ | `fastnpc` | PostgreSQL database name |
| `POSTGRES_USER` | ❌ | `fastnpc` | PostgreSQL username |
| `POSTGRES_PASSWORD` | ❌ | None | PostgreSQL password |
| `REDIS_HOST` | ❌ | `localhost` | Redis host address (optional) |
| `REDIS_PORT` | ❌ | `6379` | Redis port |
| `USE_DB_PROMPTS` | ❌ | `true` | Use database prompt system |
| `DB_POOL_MIN_CONN` | ❌ | `10` | Database connection pool min size |
| `DB_POOL_MAX_CONN` | ❌ | `50` | Database connection pool max size |
| `FASTNPC_ADMIN_USER` | ❌ | None | Admin username, first registered user with this name will get admin privileges |
| `FASTNPC_FRONTEND_ORIGIN` | ❌ | `http://localhost:5173` | Frontend URL for CORS, supports comma-separated multiple URLs |
| `FASTNPC_MAX_CONCURRENCY` | ❌ | `4` | Structuring concurrency, controls max concurrent LLM calls |
| `FASTNPC_ROOT` | ❌ | Auto-inferred | Project root directory, usually no need to set |

### User Configuration (In-App Settings)

After logging in, users can configure in settings:

- **Default Model**: Select preferred LLM model
- **Memory Budget**: Set character limits for session/short-term/long-term memory
- **Personal Bio**: For other characters to understand you in group chats
- **Max Group Chat Reply Rounds**: Control consecutive character replies (default 3 rounds)

---

## 📚 User Guide

### 📹 Video Demonstrations

<div align="center">

#### User Features Demo

<video src="https://github.com/changan593/FastNPC/raw/main/images/用户.mp4" controls width="100%" style="max-width: 800px;">
  Your browser does not support the video tag. Please <a href="images/用户.mp4">click here to download the video</a>.
</video>

*Complete user features demonstration: Character creation, single chat, group chat interaction*

---

#### Admin Features Demo

<video src="https://github.com/changan593/FastNPC/raw/main/images/管理员.mp4" controls width="100%" style="max-width: 800px;">
  Your browser does not support the video tag. Please <a href="images/管理员.mp4">click here to download the video</a>.
</video>

*Advanced admin features: Prompt management, test case management, test execution & evaluation*

</div>

---

### Create Character

1. Click the **"📝 Character"** button in the bottom left
2. Enter character name (e.g., Sun Wukong, Li Bai, Jack Ma)
3. Select data source:
   - **Baidu Baike**: Suitable for Chinese figures
   - **Chinese Wikipedia**: Suitable for international figures
4. Select structuring level:
   - **Concise**: Quick generation, core information
   - **Detailed**: Complete generation, includes all details
5. If there are characters with the same name, a disambiguation selection interface will appear
6. Wait for automatic generation to complete (30 seconds - 2 minutes)

**Step-by-step illustration:**

<div align="center">

#### Step 1: Enter Character Name

![Enter Character Name](images/自动创建角色-输入角色名称.png)

#### Step 2: Disambiguation Selection (if applicable)

![Select Character](images/自动创建角色-选择角色.png)

#### Step 3: Auto-Creating

![Creating](images/自动创建角色-自动创建角色中.png)

</div>

### Single Character Chat

1. Select a character from the left panel
2. Enter a message in the bottom input box
3. Press Enter or click the "Send" button
4. Streaming responses supported, displayed in real-time
5. Right panel shows character bio

<div align="center">

![Private Chat Interface](images/私聊.png)

*Single Character Chat Interface*

</div>

### Create Group Chat

1. Click the **"💬 Group Chat"** button in the bottom left
2. Enter group chat name
3. Check the characters to add (multiple selection supported)
4. Click the "Create" button
5. The group chat will appear in the left panel

<div align="center">

![Create Group Chat](images/创建群聊.png)

*Create Group Chat Interface*

</div>

### Group Chat Interaction

1. After selecting a group chat, enter and send a message
2. The system automatically determines the next speaking character
3. Characters reply automatically based on plot logic
4. After reaching max reply rounds, waits for user input
5. Right panel shows all member bios

<div align="center">

![Group Chat Interface](images/群聊.png)

*Group Chat Interaction Interface*

</div>

### Character Management

- **Rename**: Right-click character → Select "Rename"
- **Copy**: Right-click character → Select "Copy"
- **Delete**: Right-click character → Select "Delete" (will delete all messages)
- **Edit Configuration**: Right panel "Manage" button → Open character configuration page

<div align="center">

#### View/Edit Character Configuration

![View/Edit Character Configuration](images/查看或编辑角色配置.png)

*Character Structured Configuration Interface*

#### Manage Group Members

![Manage Group Members](images/管理群成员.png)

*Group Chat Member Management Interface*

</div>

---

## 🏗️ Project Architecture

### Directory Structure

```
FastNPC/
├── fastnpc/                    # Backend core
│   ├── api/                    # FastAPI routes
│   │   ├── routes/            # Function route modules
│   │   ├── server.py          # Main server entry
│   │   ├── auth.py            # Authentication & database
│   │   ├── state.py           # Task state management
│   │   └── utils.py           # API utilities
│   ├── chat/                   # Chat system
│   │   ├── prompt_builder.py  # Prompt building (six-part)
│   │   ├── memory_manager.py  # Three-layer memory management
│   │   └── group_moderator.py # Group chat moderation
│   ├── datasources/            # Data source scrapers
│   │   ├── baike.py           # Baidu Baike
│   │   └── zhwiki.py          # Wikipedia
│   ├── llm/                    # LLM call wrapper
│   │   └── openrouter.py      # OpenRouter client
│   ├── pipeline/               # Data processing pipeline
│   │   ├── collect.py         # Data collection
│   │   └── structure/         # Structured processing
│   │       ├── core.py        # Main process
│   │       ├── prompts.py     # Prompt templates
│   │       └── processors.py  # Text processing
│   ├── utils/                  # Utilities
│   ├── web/                    # Backend templates (optional)
│   └── config.py               # Configuration management
├── web/fastnpc-web/            # Frontend React app
│   ├── src/
│   │   ├── App.tsx            # Main app component
│   │   ├── types.ts           # TypeScript type definitions
│   │   └── main.tsx           # Entry file
│   ├── public/                # Static assets
│   └── package.json           # Frontend dependencies
├── Characters/                 # Character data storage
├── Test/                       # Test scripts
├── logs/                       # Runtime logs
├── fastnpc.db                  # SQLite database
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (create yourself)
└── README.md                   # This file
```

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Browser                           │
│                    http://localhost:5173                      │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/WebSocket
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)                    │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Character   │  │  Single Chat  │  │  Group Chat  │       │
│  │  Management  │  │  Interface    │  │  Interface   │       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              API Route Layer                          │    │
│  │  auth / character / chat / group / task ...          │    │
│  └────────┬──────────────────┬─────────────────────────┘    │
│           ↓                  ↓                               │
│  ┌──────────────┐   ┌─────────────────┐                     │
│  │  Data Scraper│   │   Chat System    │                     │
│  │ baike/zhwiki │   │ prompt/memory    │                     │
│  └──────┬───────┘   └────────┬────────┘                     │
│         ↓                    ↓                               │
│  ┌──────────────────────────────────┐                       │
│  │        Structured Pipeline        │                       │
│  │   Concurrent LLM → 8 Categories   │                       │
│  └──────────────────────────────────┘                       │
└────────────┬───────────────────┬────────────────────────────┘
             │                   │
             ↓                   ↓
    ┌────────────────┐   ┌──────────────────┐
    │  SQLite DB     │   │  OpenRouter API  │
    │  User/Char/Msg │   │   (LLM Service)  │
    └────────────────┘   └──────────────────┘
```

### Core Processes

#### 1. Character Creation Process

```
User inputs character name
    ↓
Data source selection (baike/zhwiki)
    ↓
[Optional] Disambiguation selection
    ↓
Data scraping (HTML → JSON)
    ↓
JSON → Markdown conversion
    ↓
Concurrent LLM calls to generate 8 categories
    ↓
Generate character bio
    ↓
Save to database + JSON file
```

#### 2. Chat Process (Single)

```
User sends message → Save to database
    ↓
Check session memory size
    ↓
[Over budget] Compress to short-term memory
    ↓
Build six-part System Prompt
    ├─ ① Fixed rules layer
    ├─ ② Structured profile (8 categories)
    ├─ ③ Long-term memory
    ├─ ④ Short-term memory
    ├─ ⑤ User bio
    └─ ⑥ Session memory (recent conversations)
    ↓
Call LLM for streaming response
    ↓
Save response to database
    ↓
[Periodically] Integrate short-term → long-term memory
```

#### 3. Group Chat Process

```
User sends message
    ↓
Call moderator to judge next speaker
    ├─ Topic relevance
    ├─ Character motivation
    ├─ Plot driving force
    └─ Dialogue coherence
    ↓
[Confidence ≥0.8] Clearly select character
[Confidence 0.5-0.8] Random selection
[Confidence <0.5] Wait for user
    ↓
Build group chat specific prompt for that character
    ↓
Stream generate response
    ↓
[Loop] Until max rounds reached
```

---

## 🔧 Development Guide

### Local Development

#### Backend Hot Reload

```bash
# Use --reload parameter
uvicorn fastnpc.api.server:app --host 0.0.0.0 --port 8000 --reload
```

After modifying Python code, the server will automatically restart.

#### Frontend Hot Reload

```bash
cd web/fastnpc-web
npm run dev -- --host --port 5173
```

After modifying React code, the page will automatically refresh.

### Test Scripts

The Test directory provides independent test scripts:

```bash
# Test Baidu Baike scraping
python Test/test_baidubaike.py

# Test Wikipedia scraping
python Test/test_zhwikiapi.py

# Test structured processing
python Test/test_structure.py

# Test chat system
python Test/test_chat.py
```

### Adding New Data Sources

1. Create a new module in `fastnpc/datasources/`
2. Implement the `get_full(keyword, ...)` function
3. Return data dictionary in standard format
4. Register the new data source in `fastnpc/pipeline/collect.py`

### Adjusting Structured Categories

Edit the `_category_prompts()` function in `fastnpc/pipeline/structure/prompts.py`.

---

## 📊 API Documentation

After starting the backend service, visit the following addresses to view complete API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Main API Endpoints

#### Authentication

- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `GET /auth/me` - Get current user info

#### Character Management

- `GET /api/characters` - Get character list
- `POST /api/characters` - Create new character (async task)
- `GET /api/characters/{role}/structured` - Get character structured info
- `PUT /api/characters/{role}/structured` - Update character info
- `PUT /api/characters/{old_name}/rename` - Rename character
- `DELETE /api/characters/{name}` - Delete character

#### Chat

- `GET /api/chat/{role}/messages` - Get chat history
- `POST /api/chat/{role}/messages` - Send message (non-streaming)
- `GET /api/chat/{role}/stream` - Send message (streaming)
- `POST /api/chat/{role}/compress-all` - Compress session memory

#### Group Chat

- `GET /api/groups` - Get group chat list
- `POST /api/groups` - Create group chat
- `GET /api/groups/{group_id}` - Get group chat details
- `DELETE /api/groups/{group_id}` - Delete group chat
- `POST /api/groups/{group_id}/members` - Add member
- `DELETE /api/groups/{group_id}/members/{member_name}` - Remove member
- `GET /api/groups/{group_id}/messages` - Get group chat messages
- `POST /api/groups/{group_id}/messages` - Send group chat message
- `POST /api/groups/{group_id}/judge-next` - Moderator judges next speaker
- `POST /api/groups/{group_id}/generate-reply` - Generate character reply (streaming)

#### Prompt Management (Admin)

- `GET /admin/prompts` - Get prompt list
- `POST /admin/prompts` - Create new prompt
- `GET /admin/prompts/{id}` - Get prompt details
- `PUT /admin/prompts/{id}` - Update prompt
- `DELETE /admin/prompts/{id}` - Delete prompt
- `POST /admin/prompts/{id}/activate` - Activate specific version
- `GET /admin/prompts/{id}/versions` - Get version history
- `POST /admin/prompts/{id}/duplicate` - Duplicate prompt

#### Test Case Management (Admin)

- `GET /admin/test-cases` - Get test case list
- `POST /admin/test-cases` - Create test case
- `GET /admin/test-cases/{id}` - Get test case details
- `PUT /admin/test-cases/{id}` - Update test case
- `DELETE /admin/test-cases/{id}` - Delete test case
- `POST /admin/test-cases/{id}/execute` - Execute single test
- `POST /admin/test-cases/batch-execute` - Batch execute tests
- `POST /admin/test-cases/reset-character/{id}` - Reset character state
- `POST /admin/test-cases/reset-group/{id}` - Reset group state

#### Avatar Management

- `POST /api/avatars/upload` - Upload avatar
- `GET /api/avatars/{filename}` - Get avatar

---

## 💡 FAQ

### Q: Frontend shows "Cannot access this site/ERR_CONNECTION_REFUSED"

**A:** Frontend service is not started or port is not listening.

Solution:
```bash
cd web/fastnpc-web
npm run dev -- --host --port 5173
```

### Q: Frontend console shows "proxy error ECONNREFUSED 127.0.0.1:8000"

**A:** Backend service is not started.

Solution:
```bash
# Make sure you're in the project root
uvicorn fastnpc.api.server:app --host 0.0.0.0 --port 8000 --reload

# Test if backend is working
curl http://localhost:8000/health
# Should return: {"ok":true}
```

### Q: "API call error" when creating character

**A:** OpenRouter API key is not configured or invalid.

Solution:
1. Check `OPENROUTER_API_KEY` in `.env` file
2. Confirm the key is valid and has sufficient quota
3. Check backend logs for detailed error information

### Q: Character creation failed with "403 Forbidden"

**A:** Baidu Baike triggered anti-scraping mechanism.

Solution:
1. Wait a few minutes and retry
2. Switch to Wikipedia data source
3. Check network connection

### Q: Cannot access frontend from host machine in WSL environment

**A:** Need to ensure frontend listens on `0.0.0.0`.

Solution:
```bash
# Use --host parameter
npm run dev -- --host --port 5173
```

### Q: How to backup data?

**A:** Backup the following files and directories:
- `fastnpc.db` - Database file
- `Characters/` - Character data directory
- `.env` - Environment configuration (contains keys)

### Q: How to change default ports?

**A:** 
- Backend: Modify the `--port` parameter in the startup command
- Frontend: Modify `server.port` in `web/fastnpc-web/vite.config.ts`

### Q: Which LLM models are supported?

**A:** All models compatible with OpenAI API format are supported. Default recommendations:
- `z-ai/glm-4-32b`
- `z-ai/glm-4.5-air:free`
- `deepseek/deepseek-chat-v3.1:free`
- `tencent/hunyuan-a13b-instruct:free`

You can select other models in the app settings.

### Q: Should I use PostgreSQL or SQLite for production?

**A:** **PostgreSQL is strongly recommended**:
- PostgreSQL supports better concurrency and performance
- Supports connection pool optimization
- More suitable for multi-user production environment
- SQLite is only recommended for development and testing

### Q: Do I need to restart the service after modifying prompts?

**A:** **No!** Prompts are stored in the database and take effect immediately:
1. Modify prompts in admin interface
2. Click "Activate" for the new version
3. Takes effect immediately, no restart needed
4. Can roll back to old versions anytime

### Q: How to view database contents?

**A:** Use Adminer database management tool:
```bash
./scripts/start_adminer.sh
# Visit http://localhost:8080
```
See `docs/DATABASE_MANAGEMENT.md` for details

### Q: What to do about "connection pool exhausted" error?

**A:** See `docs/CONNECTION_POOL_QUICK_FIX.md`, usually solved by:
1. Increase pool size (environment variable `DB_POOL_MAX_CONN`)
2. Use pool monitoring tool: `python fastnpc/scripts/monitor_pool.py`
3. Check for connection leaks

### Q: How to create an admin account?

**A:** Two ways:
1. First registered user automatically becomes admin
2. Set `FASTNPC_ADMIN_USER=admin` in environment variables, then register that username

### Q: Is Redis required?

**A:** **Not required, but strongly recommended**:
- Without Redis: System still works normally
- With Redis: Significantly improves performance, especially for character list loading and prompt queries
- Recommended for production environments

---

## 🤝 Contributing

Contributions, issue reports, and suggestions are welcome!

### Reporting Issues

Please submit on GitHub Issues, including:
- Issue description
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment info (Python version, OS, etc.)

### Submitting Code

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Create a Pull Request

### Code Style

- Python: Follow PEP 8
- TypeScript: Follow project ESLint configuration
- Commit messages: Use clear descriptive messages

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 📞 Contact

For questions or suggestions, feel free to contact us through:

- 💬 Submit an Issue
- 📧 Send email to [liyanghui2025@163.com](mailto:liyanghui2025@163.com)
- 👥 Join the discussion group

<div align="center">

### Scan to Join Discussion Group

<img src="images/讨论群二维码.jpg" alt="Discussion Group QR Code" width="300"/>

*Scan with WeChat to join FastNPC technical discussion group*

</div>

---

## 🙏 Acknowledgements

### Data Sources

Thanks to the following platforms for providing character information data:

- [Baidu Baike](https://baike.baidu.com/) - Provides rich Chinese character information
- [Wikipedia](https://zh.wikipedia.org/) - Provides global encyclopedia data

### Open Source Projects

Thanks to the following open source projects for their support:

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python Web framework
- [React](https://react.dev/) - User interface library
- [OpenAI](https://openai.com/) - LLM API standard
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing library
- [Playwright](https://playwright.dev/) - Automation testing and scraping tool
- [Vite](https://vitejs.dev/) - Frontend build tool

---

<div align="center">

---

### 🎉 Welcome to Try

**Online Experience: [https://changan00.cn](https://changan00.cn)**

Quickly create your exclusive AI characters and start your intelligent conversation journey!

---

**⭐ If this project helps you, please give it a Star! ⭐**

Made with ❤️ by FastNPC Team

</div>

