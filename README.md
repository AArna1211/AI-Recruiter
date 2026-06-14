# 🏰 Talent Quest: AI-Powered Recruitment Ranking System

**A dungeon-crawler inspired AI system that ranks candidates like a great recruiter would — not by keywords, but by understanding who truly fits the role.**

---

## 🌟 **What We’re Building**
Talent Quest replaces **keyword-based recruitment** with a **context-aware AI pipeline** that:
- **Understands job descriptions (JDs)** beyond just words.
- **Analyzes candidate profiles** holistically (skills, career history, behavioral signals).
- **Ranks candidates** using semantic search, feature engineering, and composite scoring.
- **Visualizes the process** as a **dungeon-crawler/RPG quest** in Godot 4.

**Why?**
Recruiters sift through hundreds of profiles but often miss the right fit because **keyword filters fail to capture nuance**. Talent Quest uses AI to **mimic a great recruiter’s intuition**.

---

## 🎯 **Key Features**
   Feature               | Description                                                                                     |
 |-----------------------|-------------------------------------------------------------------------------------------------|
 | **Semantic Search**   | Uses **BGE embeddings + Qdrant** to match JDs and candidates based on meaning, not just keywords. |
 | **Multi-Stage Pipeline** | Filters candidates through **5 stages**: JD parsing → semantic search → career scoring → behavioral signals → final ranking. |
 | **Honeypot Detection** | Flags **keyword stuffers, ghost candidates, and consulting-only profiles** to avoid false positives. |
 | **Composite Scoring** | Combines **semantic similarity (35%)**, **career depth (25%)**, **behavioral signals (20%)**, and **location fit (10%)**. |
 | **Dungeon-Crawler UI** | Visualizes candidates as **adventurer cards** and the pipeline as a **5-room dungeon** in Godot 4. |
 | **FastAPI Bridge**    | Connects Godot to the Python backend for real-time ranking.                                      |
 | **CPU-Optimized**     | Runs **<5 min for 100K candidates** on CPU (no GPU required).                                   |

---

## 🏗️ **System Architecture**
### **High-Level Overview**
The system consists of:
1. **Backend (Python)**:
   - **Ranking Pipeline**: Semantic search (Qdrant) + feature engineering + XGBoost scoring.
   - **FastAPI Server**: Exposes endpoints for Godot to fetch ranked candidates.
2. **Vector Database (Qdrant)**:
   - Stores **candidate embeddings** for fast semantic search.
3. **Frontend (Godot 4)**:
   - **Quest Board**: Displays candidates as adventurer cards.
   - **Dungeon Map**: Visualizes the 5-stage filtering pipeline.
4. **Data**:
   - **Job Descriptions (JD)**: Structured JSON.
   - **Candidate Profiles**: CSV with skills, career history, and behavioral signals.

---

### **System Diagram**
```mermaid
flowchart TD
    subgraph Inputs
        A[Job Description\n(JD JSON)] -->|Parsed| B[Python Backend]
        C[Candidate Profiles\n(CSV)] -->|Loaded| B
    end

    subgraph Backend["Python Backend (FastAPI)"]
        B --> D[1. JD Embedding\n(BGE-small-en-v1.5)]
        B --> E[2. Candidate Embedding\n(BGE-small-en-v1.5)]
        D --> F[Qdrant\n(Semantic Search)]
        E --> F
        F --> G[Top-500 Candidates\n(FAISS/ANN)]
        G --> H[Feature Engineering\n(Career Depth, Behavioral Signals)]
        H --> I[Composite Scoring\n(XGBoost/Weighted Sum)]
        I --> J[Ranked Output\n(CSV)]
    end

    subgraph Frontend["Godot 4 Frontend"]
        J --> K[FastAPI Bridge\n(HTTP Requests)]
        K --> L[Quest Board\n(Adventurer Cards)]
        K --> M[Dungeon Map\n(5-Room Pipeline)]
    end

    subgraph Outputs
        L --> N[Recruiter UI\n(Interactive Ranking)]
        M --> N
        J --> O[ranked_output.csv\n(Top 100 Candidates)]
    end

    style A fill:#f9f,stroke:#333
    style C fill:#bbf,stroke:#333
    style F fill:#9f9,stroke:#333
    style L fill:#ff9,stroke:#333
    style M fill:#ff9,stroke:#333