# luki-modules-cognitive  
*Personalised activity creation, cognitive stimulation & wellbeing analytics for ReMeLife*
---

## License

This project is licensed under the [Apache 2.0 License with ReMeLife custom clauses]

---

## 1. Overview  
This module implements LUKi’s **Cognitive Stimulation & Wellbeing** subsystem.  
It generates **personalised activities**, adapts **cognitive difficulty**, analyses **feedback & engagement**, and produces **lightweight wellbeing metrics** — all using a member’s ELR® data and in‑app interactions.

---

## 2. Core Capabilities  
- **Activity Recommendation** – Content‑based + embedding search over an activity catalog.  
- **Adaptive Difficulty** – Incremental adjustment based on performance and engagement history.  
- **NLP Feedback Insight** – Sentiment, topic and entity extraction from user/carer comments.  
- **Behaviour Pattern Detection** – Spot trends/anomalies in participation and scores.  
- **Mini Wellbeing Summaries** – Numeric snapshots or short paragraphs for caregivers.  
- **Agent Tools** – Functions exposed to the LUKi agent (`recommend_activity`, `summarise_feedback`, etc.).

---

## 3. Tech Stack  
- **ML / DL:** PyTorch 2.x (primary), scikit-learn for classic models  
- **Embeddings & Retrieval:** sentence-transformers, ChromaDB/FAISS  
- **NLP:** spaCy for entities; optional transformer classifiers for emotion/sentiment  
- **Orchestration:** LangChain tool wrappers  
- **Data:** pandas for wrangling; pydantic for type validation

---

## 4. Repository Structure  
~~~text
luki_modules_cognitive/
├── __init__.py
├── config.py
├── data/
│   ├── elr_adapter.py          # ingest/clean ELR® & My Story text
│   ├── activity_catalog.py     # curated activities + metadata/tags
│   └── vector_store.py         # Chroma/FAISS wrapper
├── recommender/
│   ├── recommend.py            # hybrid rec engine (content + heuristics)
│   ├── adapt_difficulty.py     # difficulty scaling logic
│   └── feedback_loop.py        # reward/penalty updates
├── nlp/
│   ├── feedback_analyser.py    # sentiment, entities, key phrases
│   └── summariser.py           # short text summaries (template or LLM hook)
├── analytics/
│   ├── pattern_detection.py    # engagement trends/anomalies
│   └── wellbeing_metrics.py    # compute simple wellbeing scores
├── interfaces/
│   ├── agent_tools.py          # LangChain @tool wrappers
│   └── api.py                  # FastAPI endpoints (optional)
└── tests/
~~~

---

## 5. Quick Start  
~~~bash
git clone git@github.com:REMELife/luki-modules-cognitive.git
cd luki-modules-cognitive
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
~~~

### Index the activity catalog  
~~~python
from luki_modules_cognitive.data.activity_catalog import ACTIVITY_CATALOG
from luki_modules_cognitive.recommender.recommend import ActivityRecommender

rec = ActivityRecommender(activity_catalog=ACTIVITY_CATALOG, chroma_path="./chroma")
rec.index_catalog()
print("Catalog indexed.")
~~~

### Recommend an activity  
~~~python
user_profile = {
    "id": "user_123",
    "interests": ["gardening", "music", "reading"]
}

recommended = rec.recommend(user_profile["interests"], k=3)
for a in recommended:
    print(a["title"], "-", a["description"])
~~~

### Analyse feedback & adjust difficulty  
~~~python
from luki_modules_cognitive.recommender.adapt_difficulty import DifficultyScaler
from luki_modules_cognitive.nlp.feedback_analyser import analyse_feedback

feedback_text = "I really enjoyed the gardening quiz today. It was fun but a bit easy."
fb = analyse_feedback(feedback_text)

scaler = DifficultyScaler()
new_level = scaler.adjust(current_level=0.6, performance_score=0.8, sentiment=fb.sentiment)
print("New difficulty:", new_level)
~~~

### Expose tools to the agent  
~~~python
# interfaces/agent_tools.py
from langchain.tools import tool
from .recommender.recommend import ActivityRecommender
from .nlp.feedback_analyser import analyse_feedback

_rec = ActivityRecommender(...)
_rec.index_catalog()

@tool("recommend_activity", return_direct=True)
def recommend_activity(user_id: str, interests_csv: str, k: int = 3) -> str:
    """Return top K activities for a user based on interests."""
    interests = [i.strip() for i in interests_csv.split(",")]
    acts = _rec.recommend(interests, k=k)
    return "\n".join([a["title"] for a in acts])

@tool("analyse_feedback", return_direct=True)
def tool_analyse_feedback(text: str) -> str:
    """Extract sentiment/entities from feedback text."""
    res = analyse_feedback(text)
    return f"sentiment={res.sentiment}; entities={res.entities}"
~~~

---

## 6. Privacy & Data Handling  
- Never store raw ELR text in this public repo; use mock/demo data for examples.  
- Encrypt and keep vector stores in secure storage if they contain personal data.  
- Respect consent flags (e.g., exclude “sensitive” tags).  
- Sanitise logs; no PHI in console or issue tickets.

---

## 7. Roadmap  
- Reinforcement-style policy for difficulty tuning (bandits/RL-lite)  
- Emotion classifiers fine-tuned on senior-care feedback corpora  
- Multilingual activity catalog & templates  
- Voice interaction hooks (Phase 3)  
- Federated preference updates across devices

---

## 8. Contributing  
Public contributions are welcome. Please read `CONTRIBUTING.md`, write tests, and keep docstrings clear.

---

## 9. License  
**Apache-2.0** © 2025 Singularities Ltd / ReMeLife.  
(Add via GitHub “Choose a license template” or paste the standard Apache-2.0 text in `LICENSE`.)

---

**Personalised care. Adaptive stimulation. Real insight.**
