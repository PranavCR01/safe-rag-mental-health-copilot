# Safe RAG for Mental Health Copilot

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40.1-FF4B4B.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **⚠️ DISCLAIMER**: This is a research prototype for academic purposes only. It is NOT a substitute for professional mental health care. If you are experiencing a mental health crisis, please call 988 (Suicide & Crisis Lifeline) or visit [988lifeline.org](https://988lifeline.org/).

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Evaluation Results](#evaluation-results)
- [Safety Mechanisms](#safety-mechanisms)
- [Known Limitations](#known-limitations)
- [Future Work](#future-work)
- [Crisis Resources](#crisis-resources)
- [License](#license)
- [Citation](#citation)

---

## 🎯 Overview

The **Safe RAG Mental Health Copilot** is a human-centered conversational AI system designed to support students experiencing exam anxiety through evidence-based responses while maintaining strict safety protocols.

**Core Components:**
- **3-Tier Risk Classification**: Normal anxiety → Heightened distress → Immediate crisis
- **Crisis Abstention Protocol**: Automatic 988 referral for Tier 3 (no AI advice)
- **RAG Architecture**: 46 curated evidence chunks from WHO, CDC, APA, Harvard Medical School
- **Adaptive Empathy**: 3 levels (informational, supportive, deeply compassionate)
- **Persistent Memory**: SQLite conversation history for personalization
- **Zero Hallucinations**: 100% citation rate with verified evidence

**Authors**: Shobha Rani Ganapati Bhat, Pranav Rajesh Charakondala, Chandra Sekhar Ananthabhotla  

---

## ✨ Key Features

### 🛡️ Safety-First Design
- 40 crisis patterns (explicit + implicit suicidal ideation)
- Immediate 988 referral for Tier 3 (complete abstention)
- Multi-layered safety: Input classification → Generation → Output validation
- Transparent confidence scoring (0.0-1.0)

### 📚 Evidence Grounding
- 46 chunks from 29 verified sources (WHO, CDC, APA, NIH, Harvard)
- FAISS semantic search with OpenAI embeddings
- 100% citation rate ([WHO], [CDC], [APA])
- 0% hallucination rate

### 💬 Adaptive Empathy
- Level 1 (1.0): Informational tone
- Level 2 (2.0): Supportive tone
- Level 3 (3.0): Deeply compassionate tone
- 90% appropriateness in evaluation

### 🧠 Personalization
- Pattern recognition across sessions
- Intervention effectiveness tracking
- Escalation detection (Tier 1 → Tier 2 progression)
- Full audit trail for human review

---

## 🏗️ System Architecture

! [ System Architecture ]( ./images/system_architecture.png )

**Six-Stage Processing Pipeline with Layered Safeguards:**

The system implements a defensive architecture where user queries flow through multiple independent safety checks. Upon receiving a query, the **Risk Classifier** assigns a confidence-scored tier (1, 2, or 3). **Tier 3 (Crisis)** cases immediately trigger abstention—the system provides 988 Suicide & Crisis Lifeline contact information and explicitly states it cannot give advice, encouraging real-world support. No AI-generated response is produced.

For **Tier 1/2 (Safe)** cases, queries enter the RAG + Response Pipeline where the **Tone & Cue Analyzer** detects emotional signals and assigns an empathy score (1-3), selecting the appropriate response template. The system then finds supporting evidence from the curated knowledge base, crafts a helpful response with mandatory citations, and ensures the reply passes safety validation checks (no medical diagnoses, medication advice, or harmful content).

All interactions are logged in the **Audit Log** for human-in-the-loop review, while **Persistent Memory** stores past messages and metadata to enable safe personalization across sessions. The system evaluates performance across seven dimensions including crisis abstention accuracy, hallucination detection, retrieval precision, and confidence calibration—maintaining complete transparency about its limitations while prioritizing user safety above all else.

---

## 📦 Prerequisites

- **Python**: 3.10, 3.11 or 3.12 (REQUIRED - other versions may cause compatibility issues)
- **OpenAI API Key**: Required
- **RAM**: 4GB minimum (8GB recommended)
- **Disk Space**: ~500MB

---

## 🚀 Installation

### 1. Clone Repository

```bash
git clone https://github.com/PranavCR01/safe-rag-mental-health-copilot.git
cd safe-rag-mental-health-copilot
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. ⚙️ Configuration

Create `.env` file:

```bash
OPENAI_API_KEY=sk-your-actual-key-here
```

---

### 5. Set Up Knowledge Base

```bash
python ingest.py
```

Expected output:
```
✓ Loaded 46 chunks from data/sources.yaml
✓ Generated embeddings using text-embedding-3-small
✓ Created FAISS index: data/faiss_index.index
```

---

## 💻 Usage

### Backend API

```bash
uvicorn app:app --reload
```

**Endpoints:**
- `POST /chat` - Main chat
- `GET /health` - Health check
- `GET /history/{user_id}` - Get history

**Swagger**: http://localhost:8000/docs

### Frontend UI

```bash
streamlit run outputs/streamlit_app.py
```

**URL**: http://localhost:8501

**Features:**
- iMessage-style interface
- Real-time streaming
- Crisis warning modals
- Mobile-responsive

---

## 📁 Project Structure

```
safe-rag-mental-health-copilot/
│
├── README.md
├── requirements.txt
├── .env
├── .gitignore
├── app.py                   # FastAPI backend
│
├── core/                    # Core system modules
│   ├── composer.py          # Response generation (GPT-4)
│   ├── persistent_memory.py # SQLite conversation storage
│   ├── retriever.py         # RAG retrieval (FAISS)
│   ├── risk.py              # Risk classification (3-tier)
│   ├── safety.py            # Output safety validation
│   ├── schema.py            # Pydantic data models
│   └── tone.py              # Empathy analysis (1-3 levels)
│
├── data/
│   ├── corpus.jsonl         # Evidence chunks (46 total)
│   └── sources.yaml         # Source metadata
│
├── outputs/
│   └── streamlit_app.py     # Streamlit frontend UI
│
├── scripts/
│   └── ingest.py            # Knowledge base indexing
│
├── storage/
│   ├── audit_log.sqlite     # Audit trail
│   ├── conversation_memory.sqlite  # Chat history
│   ├── meta.npy             # FAISS metadata
│   └── vectordb.faiss       # FAISS vector index
│
└── venv/                    # Virtual environment
    
```

---

## 📊 Evaluation Results

Evaluated on **10 synthetic test cases** across **5 dimensions**:

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Crisis Detection Rate | 50% | 1/2 crisis cases (missed implicit ideation) |
| Crisis Abstention Rate | 100% | Correctly abstained when detected |
| Hallucination Rate | 0% | Perfect evidence grounding |
| Citation Rate | 100% | All responses cited sources |
| Avg Citations/Response | 3.78 | Strong evidence backing |
| Retrieval Success | 100% | Found evidence for every query |
| Retrieval Relevance | 73.3% | Room for improvement |
| Empathy Appropriateness | 90% | 9/10 matched expected level |
| Avg Empathy Level | 2.2/3.0 | Generally supportive |
| Unsafe Output Rate | 0% | No diagnoses/medication advice |

**Key Findings:**
- ✅ Perfect evidence grounding (0% hallucinations)
- ❌ 50% crisis detection (implicit ideation missed)
- ✅ 100% abstention when crisis detected
- ⚠️ Retrieval could be more precise (73.3%)

---

## 🛡️ Safety Mechanisms

### 1. Risk Classification

**Tier 1**: Normal anxiety ("stressed", "worried")  
→ Coping strategies (breathing, study techniques)

**Tier 2**: Heightened distress ("panic attack", "can't sleep")  
→ Intensive support + professional consultation

**Tier 3**: Immediate danger ("kill myself", "no point living")  
→ **Complete abstention + 988 referral**

### 2. Confidence Scoring

```
Confidence = (Avg Pattern Weight + Signal Bonus + LLM Boost) / 1.5
```

- Pattern Weight: 0.3-1.0
- Signal Bonus: +0.10/pattern (max +0.30)
- LLM Boost: +0.20 (Tier 3 only)
- Normalized to 0.0-1.0

**Theory**: Information-theoretic redundancy (Shannon's principle). However, measures *pattern strength* not *classification certainty*.

### 3. Output Validation

Blocks 5 unsafe categories:
1. Medical diagnosis
2. Medication advice
3. Harmful instructions
4. Treatment guarantees
5. Missing disclaimers

### 4. Audit Trail

Logs every interaction:
- Timestamp, user ID, message
- Tier, confidence, empathy level
- Evidence chunks, citations
- Safety check results

---

## ⚠️ Known Limitations

### 1. **Crisis Detection (50%)** ⚠️ CRITICAL
- Missed implicit ideation: "I don't see the point in living"
- Pattern matching can't capture semantic range
- **Risk**: Potential threat to user safety

### 2. **Retrieval Relevance (73.3%)**
- 46 chunks insufficient for query variations
- Chunks too broad (2-3 paragraphs)
- Embedding model trade-offs

### 3. **Confidence Calibration**
- Low confidence ≠ incorrect classification
- "I'm stressed" → 33% confidence (but correct Tier 1)
- Needs ML calibration on labeled data

### 4. **Limited Personalization**
- Basic pattern tracking
- No temporal tier progression analysis
- Escalation detection not fully implemented

### 5. **Population Diversity**
- Trained on exam anxiety only
- Missing cultural variations
- College students only

---

## 🔮 Future Work

### 1. **Semantic Crisis Detection** (PRIORITY)
- Fine-tune BERT/RoBERTa on labeled conversations
- Generalize beyond pattern matching
- Requires IRB-approved dataset

### 2. **Corpus Expansion**
- 46 → 200+ chunks
- Add sleep, nutrition, exercise, social support
- Multiple chunks per topic

### 3. **Confidence Calibration**
- Train meta-classifier on labeled data
- X% confidence → X% actual accuracy
- Similar to clinical Wells Score

### 4. **Human-in-the-Loop**
- Flag low-confidence for review
- Active learning
- Collaborate with clinicians

### 5. **Multi-Modal Detection**
- Typing speed, timing, latency
- Early warning signals

### 6. **Ensemble Methods**
- Pattern matcher + BERT + GPT-4
- Agreement = confidence

---

## 🆘 Crisis Resources

### 988 Suicide & Crisis Lifeline
- **Phone**: 988
- **Text**: "HELLO" to 741741
- **Chat**: [988lifeline.org](https://988lifeline.org/)
- **24/7, free, confidential**

### Crisis Text Line
- Text "HELLO" to 741741

### International
- [iasp.info](https://www.iasp.info/resources/Crisis_Centres/)

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

**Disclaimer**: Research prototype only. NOT for production use or as substitute for professional care.

---

## 📚 Citation

```bibtex
@article{bhat2024safemhcopilot,
  title={Safe RAG for Mental Health Copilot: Supporting Exam Anxiety with Human-Centered AI},
  author={Bhat, Shobha Rani Ganapati and Charakondala, Pranav Rajesh and Ananthabhotla, Chandra Sekhar},
  journal={University of Illinois at Urbana-Champaign, CS 598},
  year={2024}
}
```

---

## 🙏 Acknowledgments

**Evidence Sources**: WHO, CDC, APA, NIH, Harvard, Stanford, Beck Institute, 988 Lifeline

**Technical**: OpenAI (GPT-4, embeddings), FAISS, Streamlit, FastAPI

**Course**: CS 598 Human-Centered Data Science, UIUC, Fall 2024

---

## 📞 Contact

**Research Questions**: srg8@illinois.edu prc4@illinois.edu

**Mental Health Support**: Call 988 or visit [988lifeline.org](https://988lifeline.org/)

---

**Remember**: This is a research prototype. Always prioritize professional mental health care. 💙
