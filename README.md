<p align="center">
  <img src="https://img.shields.io/badge/AI%20for%20Bharat-Hackathon-orange?style=for-the-badge&logo=amazon-aws" alt="AI for Bharat Hackathon"/>
  <img src="https://img.shields.io/badge/Powered%20by-AWS-FF9900?style=for-the-badge&logo=amazon-aws" alt="Powered by AWS"/>
</p>

<h1 align="center">🎓 DigiMasterJi</h1>

<p align="center">
  <strong>Offline-First, Multilingual AI Tutoring System for Rural India</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-19.2-61DAFB?style=flat-square&logo=react" alt="React"/>
  <img src="https://img.shields.io/badge/FastAPI-Latest-009688?style=flat-square&logo=fastapi" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/AWS%20Bedrock-Nova%20Lite-FF9900?style=flat-square&logo=amazon-aws" alt="AWS Bedrock"/>
  <img src="https://img.shields.io/badge/WebLLM-Gemma%202B-4285F4?style=flat-square&logo=google" alt="WebLLM"/>
  <img src="https://img.shields.io/badge/PWA-Offline%20Ready-5A0FC8?style=flat-square&logo=pwa" alt="PWA"/>
</p>

<p align="center">
  <em>🏆 AI for Bharat Hackathon 2025 | Team: OOPs We Coded Again</em>
</p>

---

## 📋 Table of Contents

- [Problem Statement](#-problem-statement)
- [Our Solution](#-our-solution)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [AWS Deployment](#-aws-deployment)
- [Environment Variables](#-environment-variables)
- [API Documentation](#-api-documentation)
- [Cost Analysis](#-cost-analysis)
- [Demo](#-demo)
- [Team](#-team)

---

## 🎯 Problem Statement

**Build an offline-first, multilingual AI tutoring system that delivers curriculum-aligned education to rural students despite limited internet access, teacher shortages, and language barriers.**

### The Challenge: A Deep Divide in Rural Education

| Challenge                            | Impact                                                           |
| ------------------------------------ | ---------------------------------------------------------------- |
| **1 Million+** Teacher Vacancies     | Rural elementary schools face a net deficit of 286,000+ teachers |
| **Less than 4%** High-Speed Internet | Only 3.8% of rural areas have fiber access                       |
| **104,000+** Single-Teacher Schools  | Insufficient resources affect education quality                  |

---

## 💡 Our Solution

**DigiMasterJi** is a voice-first, offline-capable AI tutoring system designed specifically for rural and under-resourced students in India.

### What Makes Us Different?

| Feature                      | Description                                                      |
| ---------------------------- | ---------------------------------------------------------------- |
| 🔌 **Fully Offline Capable** | WebLLM runs Gemma 2B entirely in-browser via WebGPU              |
| 🎤 **Voice-First Interface** | Ask questions by voice in Hindi, English, or regional languages  |
| 📚 **Curriculum-Aligned**    | RAG pipeline with Curriculum textbooks ensures accurate learning |
| 🎮 **Gamified Learning**     | XP, Streaks, Badges, and Leaderboards keep students engaged      |
| 👨‍👩‍👧‍👦 **Multi-Profile Support** | Netflix-style profiles - one device for the whole family         |
| 📱 **PWA + Low Data Mode**   | Works on low-end devices with minimal data usage                 |

---

## ✨ Key Features

### 🤖 AI-Powered Tutoring

- **Online Mode**: Amazon Nova Lite via AWS Bedrock
- **Offline Mode**: Gemma 2B running entirely in-browser via WebLLM
- **RAG Pipeline**: Amazon Titan Text Embeddings V2 + MongoDB Atlas Vector Search
- **Curriculum-Aligned**: Knowledge base fed with curriculum textbooks

### 🎤 Voice-Based Learning

- **Speech-to-Text**: Deepgram (cloud) for 15+ Indian languages
- **Text-to-Speech**: gTTS for natural voice responses
- **Supported Languages**: Hindi, English, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, and more

### 🎮 Gamification System

- **XP Points**: Earn XP for completing quizzes and daily learning
- **Streaks**: Maintain daily learning streaks for bonus rewards
- **Badges**: Unlock achievements like "Week Warrior", "Math Wizard", "Perfect Score"
- **Leaderboard**: Compete with family members and friends

### 📊 AI-Generated Quizzes

- **Personalized**: Generated based on chat history and learning patterns
- **Scheduled**: EventBridge triggers daily quiz generation
- **Revision Mode**: Review incorrect answers with detailed explanations
- **Learning Insights**: AI-powered analysis of strengths and weak areas

### 💾 Offline-First Architecture

- **IndexedDB (Dexie.js)**: Local storage for profiles, conversations, messages, quizzes
- **Service Worker (PWA)**: Caches assets for offline access
- **Data Sync**: Intelligent sync when connection is restored
- **WebLLM**: True offline AI capability with cached model

### 👨‍💼 Admin Dashboard

- **Document Upload**: Upload PDF textbooks for RAG ingestion
- **Knowledge Base**: Manage curriculum content by subject and language
- **Vector Search**: Test and debug RAG retrieval
- **Bedrock Sync**: Trigger knowledge base synchronization

---

## 🏗 Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT DEVICES                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   WebLLM    │  │  IndexedDB  │  │   Service   │  │    React + Vite     │ │
│  │ (Gemma 2B)  │  │  (Dexie.js) │  │   Worker    │  │   (PWA Frontend)    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└────────────────────────────────────────┬────────────────────────────────────┘
                                         │ HTTPS
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS CLOUD INFRASTRUCTURE                             │
│  ┌───────────────┐    ┌───────────────────────────────────────────────────┐ │
│  │  API Gateway  │───▶│              AWS Lambda (FastAPI)                 │ │
│  │  (HTTP API)   │    │  ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │ │
│  └───────────────┘    │  │   Chat   │ │  Quiz    │ │   Admin / Sync     │ │ │
│                       │  │ Service  │ │ Service  │ │     Services       │ │ │
│                       │  └────┬─────┘ └────┬─────┘ └────────────────────┘ │ │
│                       └───────┼────────────┼────────────────────────────┘ │
│                               │            │                               │
│  ┌────────────────────────────┼────────────┼─────────────────────────────┐ │
│  │                    AI/ML SERVICES                                      │ │
│  │  ┌─────────────────────┐  ┌─────────────────────────────────────────┐ │ │
│  │  │   Amazon Bedrock    │  │        Bedrock Knowledge Base           │ │ │
│  │  │  (Nova Lite / Llama)│  │  (Titan Embeddings + MongoDB Atlas)     │ │ │
│  │  └─────────────────────┘  └─────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐│
│  │                        DATA STORAGE                                    ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐ ││
│  │  │   DynamoDB   │  │   Amazon S3  │  │      MongoDB Atlas           │ ││
│  │  │ (App Data)   │  │ (Documents)  │  │   (Vector Embeddings)        │ ││
│  │  └──────────────┘  └──────────────┘  └──────────────────────────────┘ ││
│  └────────────────────────────────────────────────────────────────────────┘│
│                                                                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │  EventBridge     │  │   CloudWatch     │  │      Amazon ECR          │ │
│  │ (Quiz Scheduler) │  │ (Logs/Metrics)   │  │  (Container Registry)    │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User asks a question** (voice or text)
2. **STT Service** converts voice to text (if applicable)
3. **RAG Service** retrieves relevant curriculum content from Knowledge Base
4. **LLM Service** generates a personalized response via Bedrock
5. **TTS Service** converts response to speech
6. **Response delivered** to user with audio playback option

### Offline Flow

1. **WebLLM detects offline** status
2. **Gemma 2B model** (cached in browser) processes the query
3. **Response generated** entirely on-device
4. **Local storage** saves conversation for sync when online

---

## 🛠 Tech Stack

### Frontend

| Technology           | Purpose                 |
| -------------------- | ----------------------- |
| **React 19**         | UI Framework            |
| **Vite 7**           | Build Tool              |
| **TailwindCSS 4**    | Styling                 |
| **@mlc-ai/web-llm**  | In-browser LLM (WebGPU) |
| **Dexie.js**         | IndexedDB Wrapper       |
| **Framer Motion**    | Animations              |
| **React Router DOM** | Routing                 |
| **WaveSurfer.js**    | Audio Visualization     |
| **Axios**            | HTTP Client             |

### Backend

| Technology   | Purpose            |
| ------------ | ------------------ |
| **FastAPI**  | Web Framework      |
| **Mangum**   | AWS Lambda Adapter |
| **Boto3**    | AWS SDK            |
| **PyMuPDF**  | PDF Processing     |
| **gTTS**     | Text-to-Speech     |
| **Deepgram** | Speech-to-Text     |
| **PyMongo**  | MongoDB Driver     |

### AWS Services

| Service                    | Purpose                                                            |
| -------------------------- | ------------------------------------------------------------------ |
| **AWS Lambda**             | Serverless Compute                                                 |
| **API Gateway**            | HTTP API                                                           |
| **DynamoDB**               | NoSQL Database (users, profiles, conversations, messages, quizzes) |
| **S3**                     | Document Storage + Frontend Static Hosting                         |
| **Bedrock**                | LLM (Nova Lite) + Embeddings (Titan V2)                            |
| **Bedrock Knowledge Base** | RAG Pipeline                                                       |
| **EventBridge**            | Quiz Scheduler                                                     |
| **ECR**                    | Container Registry                                                 |
| **CloudWatch**             | Logging & Monitoring                                               |
| **CloudFront**             | CDN for Frontend (S3 Static Hosting)                               |
| **IAM**                    | Security & Access Control                                          |

### External Services

| Service           | Purpose                            |
| ----------------- | ---------------------------------- |
| **MongoDB Atlas** | Vector Search (Bedrock KB Backend) |
| **Deepgram**      | Cloud STT API                      |

> **Note**: Frontend is hosted on AWS S3 + CloudFront for full AWS deployment.

---

## 📁 Project Structure

```
DigiMasterJi/
├── Backend/
│   ├── app/
│   │   ├── database/          # DynamoDB & MongoDB operations
│   │   │   ├── conversations.py
│   │   │   ├── dynamo.py
│   │   │   ├── knowledge_base.py
│   │   │   ├── messages.py
│   │   │   ├── mongodb_embeddings.py
│   │   │   ├── profiles.py
│   │   │   ├── quizzes.py
│   │   │   └── users.py
│   │   ├── models/            # Pydantic Models
│   │   │   ├── auth.py
│   │   │   ├── conversation.py
│   │   │   ├── knowledge_base.py
│   │   │   ├── message.py
│   │   │   ├── profile.py
│   │   │   ├── quiz.py
│   │   │   └── user.py
│   │   ├── routers/           # API Endpoints
│   │   │   ├── admin.py       # Knowledge base management
│   │   │   ├── auth.py        # Authentication
│   │   │   ├── chat.py        # Chat & voice interactions
│   │   │   ├── profiles.py    # Profile management
│   │   │   ├── quizzes.py     # Quiz system
│   │   │   └── sync.py        # Offline sync
│   │   ├── services/          # Business Logic
│   │   │   ├── chat_service.py
│   │   │   ├── llm_service.py
│   │   │   ├── offline_llm_service.py
│   │   │   ├── quiz_scheduler.py
│   │   │   ├── quiz_service.py
│   │   │   ├── quiz_summary_service.py
│   │   │   ├── rag_service.py
│   │   │   ├── stt_service.py
│   │   │   ├── tts_service.py
│   │   │   └── web_search_service.py
│   │   ├── utils/
│   │   │   └── security.py    # JWT authentication
│   │   └── main.py            # FastAPI app
│   ├── Dockerfile             # Lambda container
│   ├── deploy.sh              # Deployment script
│   ├── requirements.txt
│   └── .env.example
│
├── Frontend/
│   ├── public/
│   │   ├── sw.js              # Service Worker
│   │   └── offline.html       # Offline fallback
│   ├── src/
│   │   ├── api/               # API clients
│   │   ├── components/
│   │   │   ├── chat/          # Chat UI components
│   │   │   ├── gamification/  # XP, Streaks, Badges
│   │   │   ├── quiz/          # Quiz components
│   │   │   └── ui/            # Reusable UI components
│   │   ├── contexts/
│   │   │   ├── AuthContext.jsx
│   │   │   ├── NetworkStatusContext.jsx
│   │   │   ├── ProfileContext.jsx
│   │   │   └── WebLLMContext.jsx
│   │   ├── db/
│   │   │   └── index.js       # Dexie.js (IndexedDB)
│   │   ├── hooks/             # Custom React hooks
│   │   ├── pages/             # Route pages
│   │   ├── services/
│   │   │   ├── syncService.js
│   │   │   └── webLLMService.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── Documentation/
│   ├── AWS_SETUP_GUIDE.md     # AWS infrastructure setup
│   └── Costs.md               # Cost analysis
│
├── aws/
│   ├── digimasterji-policy.json
│   └── trust-policy.json
│
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** 18+ (for Frontend)
- **Python** 3.11+ (for Backend)
- **Docker** (for containerized deployment)
- **AWS CLI** v2 (configured with credentials)
- **WebGPU-compatible browser** (Chrome 113+ for offline AI)

### Local Development

#### 1. Clone the Repository

```bash
git clone https://github.com/your-username/DigiMasterJi.git
cd DigiMasterJi
```

#### 2. Backend Setup

```bash
cd Backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your AWS credentials and configuration

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Frontend Setup

```bash
cd Frontend

# Install dependencies
npm install

# Copy environment variables
cp .env.example .env
# Edit .env with your API URL

# Run development server
npm run dev
```

#### 4. Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## ☁️ AWS Deployment

### Quick Deploy

```bash
cd Backend

# Deploy to AWS Lambda
./deploy.sh dev
```

### Full Setup

For complete AWS infrastructure setup, see [AWS_SETUP_GUIDE.md](Documentation/AWS_SETUP_GUIDE.md).

This includes:

1. IAM Role & Policies
2. DynamoDB Tables (6 tables)
3. S3 Bucket for documents
4. Amazon Bedrock configuration
5. Bedrock Knowledge Base setup
6. ECR Repository
7. Lambda Function
8. API Gateway (HTTP API)
9. EventBridge for quiz scheduling

### Frontend Deployment (S3 + CloudFront)

```bash
cd Frontend

# Build the frontend
VITE_API_URL=https://your-api-gateway-url.amazonaws.com npm run build

# Deploy to S3 and invalidate CloudFront cache
./deploy-aws.sh
```

See [AWS_SETUP_GUIDE.md](Documentation/AWS_SETUP_GUIDE.md#frontend-deployment-s3--cloudfront) for detailed setup instructions.

---

## ⚙️ Environment Variables

### Backend (.env)

```env
# AWS Configuration
AWS_REGION=us-east-1

# DynamoDB Tables
DYNAMODB_USERS_TABLE=digimasterji-users
DYNAMODB_PROFILES_TABLE=digimasterji-profiles
DYNAMODB_CONVERSATIONS_TABLE=digimasterji-conversations
DYNAMODB_MESSAGES_TABLE=digimasterji-messages
DYNAMODB_QUIZZES_TABLE=digimasterji-quizzes

# Amazon Bedrock
BEDROCK_MODEL_ID=us.amazon.nova-lite-v1:0
BEDROCK_KNOWLEDGE_BASE_ID=your-kb-id
BEDROCK_DATA_SOURCE_ID=your-ds-id

# MongoDB Atlas (for Bedrock KB)
MONGODB_URI=mongodb+srv://...
MONGODB_KB_DATABASE=digimasterji_kb
MONGODB_KB_COLLECTION=bedrock_embeddings

# S3
S3_KNOWLEDGE_BUCKET=digimasterji-knowledge

# JWT
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# STT Configuration
STT_PROVIDER=deepgram
DEEPGRAM_API_KEY=your-deepgram-key
```

### Frontend (.env)

```env
VITE_API_URL=https://your-api-gateway-url.amazonaws.com
VITE_SYNC_DAYS=180
```

---

## 📚 API Documentation

### Authentication

| Endpoint                | Method | Description                                |
| ----------------------- | ------ | ------------------------------------------ |
| `/auth/register`        | POST   | Register new user (phone/email + password) |
| `/auth/login`           | POST   | Login and get master token                 |
| `/profiles/{id}/access` | POST   | Get profile-specific token                 |

### Profiles

| Endpoint         | Method | Description                |
| ---------------- | ------ | -------------------------- |
| `/profiles`      | GET    | List all profiles for user |
| `/profiles`      | POST   | Create new student profile |
| `/profiles/{id}` | GET    | Get profile details        |
| `/profiles/{id}` | PUT    | Update profile             |
| `/profiles/{id}` | DELETE | Delete profile             |

### Chat

| Endpoint                       | Method | Description                     |
| ------------------------------ | ------ | ------------------------------- |
| `/chat/sessions`               | POST   | Create new conversation         |
| `/chat/sessions`               | GET    | List conversations              |
| `/chat/sessions/{id}/messages` | POST   | Send message (text)             |
| `/chat/sessions/{id}/messages` | GET    | Get conversation messages       |
| `/chat/sessions/{id}/voice`    | POST   | Send voice message (audio file) |
| `/chat/sessions/{id}/speak`    | POST   | Convert text to speech          |

### Quizzes

| Endpoint               | Method | Description           |
| ---------------------- | ------ | --------------------- |
| `/quizzes/today`       | GET    | Get today's quiz      |
| `/quizzes`             | GET    | List all quizzes      |
| `/quizzes/{id}`        | GET    | Get quiz details      |
| `/quizzes/{id}/submit` | POST   | Submit quiz answers   |
| `/quizzes/leaderboard` | GET    | Get leaderboard       |
| `/quizzes/insights`    | GET    | Get learning insights |

### Admin

| Endpoint           | Method | Description             |
| ------------------ | ------ | ----------------------- |
| `/admin/upload`    | POST   | Upload PDF for RAG      |
| `/admin/documents` | GET    | List uploaded documents |
| `/admin/search`    | POST   | Test vector search      |
| `/admin/sync-kb`   | POST   | Trigger KB sync         |

### Sync

| Endpoint       | Method | Description           |
| -------------- | ------ | --------------------- |
| `/sync/pull`   | GET    | Pull data from server |
| `/sync/status` | GET    | Get sync status       |

---

## 💰 Cost Analysis

### Prototype Level (~5-10 test users)

| Service             | Monthly Cost      |
| ------------------- | ----------------- |
| DynamoDB            | $0.19             |
| S3 (KB + Frontend)  | $0.33             |
| CloudFront          | $0.10             |
| Lambda              | $0.00 (free tier) |
| API Gateway         | $0.00 (free tier) |
| Bedrock (Nova Lite) | $0.82             |
| MongoDB Atlas (M0)  | $0.00 (free tier) |
| ECR                 | $0.20             |
| EventBridge         | $0.01             |
| CloudWatch          | $0.06             |
| **Total**           | **~$1.61/month**  |

### Early Product (~500-1000 users)

| Service             | Monthly Cost      |
| ------------------- | ----------------- |
| DynamoDB            | $8.75             |
| S3 (KB + Frontend)  | $2.60             |
| CloudFront          | $13.50            |
| Lambda              | $25.40            |
| API Gateway         | $2.00             |
| Bedrock (Nova Lite) | $16.00            |
| MongoDB Atlas (M2)  | $9.00             |
| ECR                 | $0.50             |
| EventBridge         | $0.50             |
| CloudWatch          | $1.74             |
| **Total**           | **~$79.99/month** |

---

## 🎬 Demo

### Features Showcase

- 🎤 **Voice Chat**: Ask questions by speaking
- 📚 **Curriculum Learning**: Curriculum-aligned content
- 🎮 **Gamification**: Earn XP and badges
- 📊 **Daily Quizzes**: AI-generated assessments
- 🔌 **Offline Mode**: True offline AI capability
- 🌐 **Multilingual**: Hindi, English, and 10+ languages

### 🔗 Links

| Resource          | Link                                                                 |
| ----------------- | -------------------------------------------------------------------- |
| 🎬 Demo Video     | [YouTube](https://youtu.be/h_Y3sgLOPy8)                              |
| 🌐 Live Prototype | [d30acqvu7x6yf.cloudfront.net](https://d30acqvu7x6yf.cloudfront.net) |

---

## 👥 Team

**Team Name**: OOPs We Coded Again

**Team Leader**: Faheemuddin Sayyed

**Team Member**: Sanidhya Awasthi

**Team Member**: Raghav Sonchhatra

---

## 🙏 Acknowledgments

- **AWS** for powering the hackathon and providing Bedrock, Lambda, and other services
- **Hack2Skill** (Innovation Partner) for organizing the hackathon

---

<p align="center">
  <em>DigiMasterJi - Bridging the Education Gap with AI</em>
</p>
