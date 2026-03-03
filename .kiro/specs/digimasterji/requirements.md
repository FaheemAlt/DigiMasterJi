# Requirements Document

## Project Status

**STATUS: COMPLETE AND DEPLOYED TO AWS**

This project has been successfully implemented and deployed to production on AWS infrastructure. All requirements have been fulfilled with some technology adaptations made during implementation to optimize for cloud-native architecture, scalability, and production reliability.

### Implementation Technology Changes

The following technology changes were made during implementation while maintaining all functional requirements:

- **Database**: MongoDB Atlas → **DynamoDB** (AWS native, serverless)
- **AI Service**: Ollama → **AWS Bedrock** (Amazon Nova Lite, Titan Text Embeddings v2)
- **Scheduling**: APScheduler → **EventBridge** (serverless, event-driven)
- **Speech-to-Text**: OpenAI Whisper local → **Deepgram Cloud** (production-grade, primary service)
- **Backend Framework**: Node.js/Express → **Python FastAPI** with Mangum adapter for AWS Lambda

These changes enhance the system's scalability, reliability, and maintainability while preserving all original functional requirements and user experience goals.

## Introduction

DigiMasterJi is a voice-first, offline-first, multilingual AI-powered tutoring platform specifically designed for rural education in India, with advanced features addressing India's unique educational challenges. The system provides comprehensive educational support through curriculum-grounded AI responses, gamified learning experiences, sophisticated offline capabilities with browser-based LLM, and AI-powered learning analytics. The platform ensures educational continuity in environments with unreliable internet connectivity, limited English proficiency, and resource constraints while providing engaging, personalized learning experiences.

## Glossary

- **DigiMasterJi_System**: The complete tutoring platform including PWA frontend, backend services, dual-mode AI, and offline capabilities
- **Voice_Interface**: Enhanced speech-to-text and text-to-speech components supporting 12+ Indian languages with audio visualization
- **RAG_Engine**: Curriculum-grounded Retrieval-Augmented Generation system using NCERT textbook content with 1024-dimensional embeddings (AWS Titan Text Embeddings v2)
- **Student_Profile**: Individual learning progress, gamification data, and preferences stored per student with Netflix-style switching
- **Dual_Layer_Offline**: System architecture with browser-based LLM (WebLLM) and cloud AI (AWS Bedrock with Amazon Nova Lite) for seamless online/offline operation
- **Sync_Manager**: Enhanced component for merging offline data with cloud storage including conflict resolution for multi-day offline usage
- **NCERT_Content**: National Council of Educational Research and Training curriculum materials processed with optimized chunking strategy
- **PWA**: Progressive Web App with Workbox service workers providing native-like experience
- **Admin_Dashboard**: Web interface for content management and system administration
- **Gamification_Engine**: Comprehensive system for XP, badges, streaks, and family leaderboards
- **Learning_Analytics**: AI-powered insights generation with RAG-enhanced recommendations
- **Night_School_Mode**: Audio-only functionality for late-night study or visual impairments
- **WebLLM**: Browser-based AI using Gemma-2B-it model running entirely offline with WebGPU acceleration

## Requirements

### Requirement 1: Enhanced Voice-First Multilingual Interface

**User Story:** As a rural student, I want to interact with the tutoring system using my native language through voice commands with real-time audio visualization, so that I can learn effectively without language barriers or typing requirements.

#### Acceptance Criteria

1. WHEN a student speaks in any of 12+ supported Indian languages (Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi, Odia, Urdu, Nepali), THE Voice_Interface SHALL convert speech to text using Deepgram Cloud API with 90% accuracy
   - **Implementation Note**: Deepgram Cloud is used as the primary service for production reliability and accuracy
2. WHEN Whisper processing fails, THE Voice_Interface SHALL fallback to Deepgram Cloud API maintaining 85% accuracy
   - **Implementation Note**: Deepgram is the primary service; fallback mechanisms handle service unavailability
3. WHEN the system generates a response, THE Voice_Interface SHALL convert text to natural-sounding speech using Google TTS in the student's preferred language
4. WHEN a student switches languages mid-session, THE DigiMasterJi_System SHALL adapt and continue the conversation in the new language without losing context
5. WHEN audio input is detected, THE Voice_Interface SHALL provide real-time audio visualization using WaveSurfer.js for visual feedback
6. WHEN "Night School" mode is enabled, THE DigiMasterJi_System SHALL provide complete functionality through audio-only interaction without visual elements

### Requirement 2: Dual-Layer Offline-First Architecture

**User Story:** As a rural student with unreliable internet, I want the tutoring system to work completely offline with instant AI responses, so that I can continue learning regardless of connectivity issues.

#### Acceptance Criteria

1. WHEN internet connectivity is unavailable, THE DigiMasterJi_System SHALL provide full tutoring functionality using WebLLM with Gemma-2B-it model running in browser
2. WHEN operating offline, THE DigiMasterJi_System SHALL deliver zero-latency AI responses using the browser-based LLM with WebGPU acceleration
3. WHEN connectivity is restored, THE Sync_Manager SHALL seamlessly switch to cloud-based AWS Bedrock with Amazon Nova Lite for enhanced responses
   - **Implementation Note**: AWS Bedrock replaces Ollama for production-grade, scalable AI inference
4. WHEN the system is first installed, THE PWA SHALL cache the WebLLM model (~1.5GB) and essential content for immediate offline availability
5. WHEN storage space is limited, THE DigiMasterJi_System SHALL prioritize caching based on student's current curriculum level using intelligent cache management
6. WHEN operating offline for multiple days, THE DigiMasterJi_System SHALL maintain full functionality including quiz generation, progress tracking, and gamification features

### Requirement 3: Enhanced Curriculum-Grounded Content Generation

**User Story:** As an educator, I want the AI responses to be strictly aligned with NCERT curriculum using optimized retrieval methods, so that students receive accurate and syllabus-appropriate information without hallucinations.

#### Acceptance Criteria

1. WHEN a student asks a question, THE RAG_Engine SHALL generate responses using only NCERT textbook content processed with 500-token chunks and 50-token overlap
2. WHEN processing NCERT content, THE RAG_Engine SHALL use AWS Titan Text Embeddings v2 for 1024-dimensional embeddings with DynamoDB vector search capabilities
   - **Implementation Note**: AWS Titan embeddings replace sentence-transformers; DynamoDB replaces MongoDB for serverless architecture
3. WHEN the RAG_Engine cannot find relevant NCERT content, THE DigiMasterJi_System SHALL inform the student that the topic is outside the current curriculum
4. WHEN generating explanations, THE RAG_Engine SHALL cite specific NCERT textbook sections and page numbers with confidence scores
5. WHEN content is retrieved, THE RAG_Engine SHALL ensure responses align with the student's grade level and subject using contextual filtering
6. WHEN identifying weak topics, THE RAG_Engine SHALL provide RAG-enhanced learning insights with contextual educational content for improvement

### Requirement 4: Netflix-Style Multi-Student Profile Management

**User Story:** As a family sharing one device, we want Netflix-style individual student profiles with separate progress tracking and gamification, so that each student can have personalized learning experiences.

#### Acceptance Criteria

1. WHEN a new student uses the device, THE DigiMasterJi_System SHALL create a unique Student_Profile with voice recognition for identification and independent gamification data
2. WHEN a student logs in through voice, THE DigiMasterJi_System SHALL load their individual progress, preferences, XP points, badges, and learning history
3. WHEN multiple students use the device, THE DigiMasterJi_System SHALL maintain separate progress tracking, streaks, and achievements without cross-contamination
4. WHEN switching between profiles, THE DigiMasterJi_System SHALL complete the transition within 3 seconds with Netflix-style profile selection interface
5. WHEN operating offline, THE DigiMasterJi_System SHALL maintain profile separation and sync individual gamification data when connectivity returns
6. WHEN displaying family leaderboards, THE DigiMasterJi_System SHALL show competitive rankings while maintaining individual privacy

### Requirement 5: Advanced Gamified Daily Quizzes

**User Story:** As a student, I want engaging daily quizzes with comprehensive gamification including XP, badges, and streaks, so that I can reinforce concepts and stay motivated through competitive learning.

#### Acceptance Criteria

1. WHEN a student completes a learning session, THE DigiMasterJi_System SHALL generate quiz questions using EventBridge scheduled events based on covered topics
   - **Implementation Note**: EventBridge replaces APScheduler for serverless, event-driven scheduling
2. WHEN generating quizzes, THE DigiMasterJi_System SHALL adapt difficulty based on the student's performance history and award appropriate XP points
3. WHEN a student answers correctly, THE DigiMasterJi_System SHALL award XP points, update streaks, and check for badge eligibility from 15+ available achievements
4. WHEN a student misses daily quizzes, THE DigiMasterJi_System SHALL maintain quiz backlog and provide streak recovery mechanisms
5. WHEN operating offline, THE DigiMasterJi_System SHALL generate quizzes using cached content and sync gamification data when online
6. WHEN students achieve milestones, THE DigiMasterJi_System SHALL award badges including "First Steps", "On Fire", "Week Warrior", "Perfectionist", and "Math Wizard"

### Requirement 6: AI-Powered Learning Analytics

**User Story:** As a student and parent, I want AI-generated learning insights with performance analysis and personalized recommendations, so that I can understand learning patterns and focus study efforts effectively.

#### Acceptance Criteria

1. WHEN a student completes quizzes or learning activities, THE DigiMasterJi_System SHALL automatically generate learning insights as background tasks
2. WHEN analyzing performance, THE Learning_Analytics SHALL identify weak topics and provide RAG-enhanced contextual educational content for improvement
3. WHEN generating insights, THE DigiMasterJi_System SHALL create subject-wise performance analysis with trend visualization and bilingual reports (English/Hindi)
4. WHEN learning difficulties are detected, THE Learning_Analytics SHALL recommend additional practice sessions with specific NCERT content references
5. WHEN operating offline, THE DigiMasterJi_System SHALL store generated insights locally and sync analytics when connectivity returns
6. WHEN displaying analytics, THE DigiMasterJi_System SHALL present actionable recommendations in the student's preferred language with visual performance trends

### Requirement 7: Privacy-Conscious Audio Processing

**User Story:** As a parent concerned about privacy, I want audio data to be processed securely and not stored permanently, so that my child's voice data remains private.

#### Acceptance Criteria

1. WHEN processing voice input, THE Voice_Interface SHALL convert audio to text using local Whisper processing and immediately discard the audio data
2. WHEN using cloud-based speech processing as fallback, THE DigiMasterJi_System SHALL encrypt audio data during transmission to Deepgram
3. WHEN operating offline, THE Voice_Interface SHALL process speech locally using WebLLM without sending data to external servers
4. WHEN storing user data, THE DigiMasterJi_System SHALL store only learning progress, gamification data, and preferences, never raw audio
5. WHEN a student profile is deleted, THE DigiMasterJi_System SHALL permanently remove all associated data including analytics and insights within 24 hours
6. WHEN using "Night School" mode, THE DigiMasterJi_System SHALL ensure all audio processing remains local without cloud transmission

### Requirement 8: Enhanced Resilient Data Synchronization

**User Story:** As a student who studies offline for days, I want my progress, gamification data, and learning insights to sync properly when internet returns, so that I don't lose any learning achievements or analytics.

#### Acceptance Criteria

1. WHEN connectivity is restored after multi-day offline usage, THE Sync_Manager SHALL detect and resolve data conflicts automatically using custom conflict resolution algorithms
2. WHEN syncing offline data, THE Sync_Manager SHALL preserve the most recent learning progress, XP points, badges, and streaks for each student profile
3. WHEN sync conflicts occur, THE Sync_Manager SHALL prioritize local data over cloud data to prevent progress loss while merging non-conflicting gamification data
4. WHEN syncing fails due to network issues, THE Sync_Manager SHALL retry with exponential backoff up to 5 attempts while maintaining pending operations queue
5. WHEN sync is in progress, THE DigiMasterJi_System SHALL continue normal operation without blocking user interactions or gamification updates
6. WHEN syncing learning insights, THE Sync_Manager SHALL merge AI-generated analytics and maintain insight history across devices

### Requirement 9: Enhanced Administrative Content Management

**User Story:** As a system administrator, I want to upload and manage NCERT textbooks with optimized processing and curriculum content, so that the system stays updated with latest educational materials using efficient chunking strategies.

#### Acceptance Criteria

1. WHEN an administrator uploads NCERT PDFs, THE Admin_Dashboard SHALL process content using 500-token chunks with 50-token overlap and generate 1024-dimensional embeddings using AWS Titan
   - **Implementation Note**: AWS Titan Text Embeddings v2 provides production-grade embeddings; EventBridge handles background processing
2. WHEN content is updated, THE Admin_Dashboard SHALL version the changes and notify connected devices for cache updates with EventBridge scheduled events
   - **Implementation Note**: EventBridge replaces APScheduler for serverless task scheduling
3. WHEN managing curriculum, THE Admin_Dashboard SHALL allow mapping of content to specific grades and subjects with enhanced metadata
4. WHEN content processing fails, THE Admin_Dashboard SHALL provide detailed error messages and retry options with processing status tracking
5. WHEN new content is available, THE DigiMasterJi_System SHALL update offline caches during the next sync opportunity prioritizing student's current curriculum level
6. WHEN processing large textbooks, THE Admin_Dashboard SHALL use background processing to avoid blocking the interface and provide progress indicators

### Requirement 10: Web Search Integration and Enhanced Accessibility

**User Story:** As a student seeking comprehensive information and studying in various conditions, I want optional web search capabilities and complete audio-only functionality, so that I can access broader knowledge while learning effectively without visual dependence.

#### Acceptance Criteria

1. WHEN a student needs additional information, THE DigiMasterJi_System SHALL provide optional web search using DuckDuckGo API accessible via button near chat prompt
2. WHEN web search is enabled, THE DigiMasterJi_System SHALL integrate search results with RAG responses while maintaining curriculum alignment
3. WHEN "Night School" audio-only mode is enabled, THE DigiMasterJi_System SHALL provide all functionality including web search through voice interaction only
4. WHEN device storage is limited, THE DigiMasterJi_System SHALL operate with minimum 100MB storage requirement while maintaining WebLLM functionality
5. WHEN network bandwidth is constrained, THE DigiMasterJi_System SHALL prioritize essential content downloads and optimize web search queries
6. WHEN using older devices, THE DigiMasterJi_System SHALL maintain responsive performance on devices with 2GB RAM while running WebLLM with WebGPU acceleration


## Deployment Architecture

### AWS Infrastructure Overview

The DigiMasterJi system is deployed on AWS using a serverless, cloud-native architecture optimized for scalability, reliability, and cost-efficiency.

### Core Services

**Compute Layer:**
- **AWS Lambda**: Serverless compute for backend API (Python FastAPI with Mangum adapter)
- **API Gateway**: RESTful API endpoint management and request routing
- **CloudFront**: Global CDN for PWA frontend distribution with edge caching

**Data Layer:**
- **DynamoDB**: NoSQL database for student profiles, progress tracking, gamification data, and learning analytics
- **S3**: Object storage for NCERT PDF content, processed embeddings, and static assets
- **DynamoDB Streams**: Real-time data synchronization and event processing

**AI/ML Services:**
- **AWS Bedrock**: Managed AI service using Amazon Nova Lite for curriculum-grounded responses
- **Titan Text Embeddings v2**: 1024-dimensional embeddings for RAG engine vector search
- **Deepgram Cloud**: Primary speech-to-text service for multilingual voice interface

**Orchestration & Scheduling:**
- **EventBridge**: Serverless event bus for quiz generation, analytics processing, and content updates
- **Step Functions**: Workflow orchestration for complex multi-step processes (content ingestion, sync operations)

**Monitoring & Operations:**
- **CloudWatch**: Centralized logging, metrics, and alerting
- **X-Ray**: Distributed tracing for performance monitoring and debugging
- **CloudWatch Alarms**: Automated alerts for system health and performance thresholds

### Architecture Benefits

**Scalability:**
- Automatic scaling based on demand without manual intervention
- Pay-per-use pricing model optimizes costs for variable usage patterns
- Global distribution via CloudFront ensures low latency for rural users

**Reliability:**
- Multi-AZ deployment for high availability
- Managed services reduce operational overhead and maintenance burden
- Automated backups and point-in-time recovery for DynamoDB

**Security:**
- IAM roles and policies for fine-grained access control
- Encryption at rest (DynamoDB, S3) and in transit (TLS/HTTPS)
- VPC integration for network isolation where needed

**Performance:**
- Lambda cold start optimization with provisioned concurrency for critical paths
- DynamoDB on-demand capacity for unpredictable traffic patterns
- CloudFront edge caching reduces backend load and improves response times

### Deployment Pipeline

**CI/CD:**
- Infrastructure as Code using AWS CDK or Terraform
- Automated testing and deployment via GitHub Actions or AWS CodePipeline
- Blue-green deployments for zero-downtime updates
- Automated rollback on deployment failures

### Cost Optimization

- Serverless architecture eliminates idle resource costs
- DynamoDB on-demand pricing for variable workloads
- S3 lifecycle policies for archiving old content
- CloudWatch log retention policies to manage storage costs
- Reserved capacity for predictable baseline traffic

---

**Document Version:** 2.0 (Production Deployment)  
**Last Updated:** January 2025  
**Status:** Complete and Deployed to AWS
