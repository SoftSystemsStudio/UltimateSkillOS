"""
UltimateSkillOS - Project Structure Documentation

PROJECT OVERVIEW
================
UltimateSkillOS is an agent-based skill execution framework with autonomous 
routing, persistent memory, and tool integration capabilities.

DIRECTORY STRUCTURE
===================

/workspaces/UltimateSkillOS/
│
├── core/                          # Core routing and utilities
│   ├── __init__.py               # Package initialization
│   ├── router.py                 # Intent-based skill router
│   ├── loader.py                 # Markdown skill loader
│   └── self_eval_harness.py      # Self-evaluation framework
│
├── skill_engine/                 # Skill execution engine
│   ├── __init__.py
│   ├── agent.py                  # Main agent loop (agentic framework)
│   ├── base.py                   # BaseSkill abstract class
│   ├── engine.py                 # Dynamic skill loader and executor
│   ├── executor.py               # Task executor (coordinator)
│   ├── cli.py                    # Command-line interface
│   ├── utils.py                  # Utility functions
│   └── memory/                   # Short-term memory subsystem
│       ├── __init__.py
│       ├── memory_manager.py     # High-level memory API
│       ├── vector_memory.py      # Vector-based semantic memory
│       └── sqlite_memory.py      # SQLite persistence layer
│
├── skills/                       # Skill implementations
│   ├── __init__.py
│   ├── autofix.py               # Auto-fix skill (typo correction)
│   ├── file_tool.py             # File read/write operations
│   ├── memory_search.py         # Memory query skill
│   ├── meta_interpreter.py      # Meta-skill for plan generation
│   ├── planner.py               # Task planner skill
│   ├── reflection.py            # Reflection/criticism skill
│   ├── research.py              # Web research (Tavily integration)
│   ├── summarize.py             # Text summarization skill
│   └── research.md              # Research skill documentation
│
├── memory/                       # Long-term memory subsystem
│   ├── __init__.py
│   ├── short_term.py            # Short-term rolling buffer
│   └── long_term/               # Persistent vector memory
│       ├── __init__.py
│       ├── embeddings.py        # SentenceTransformer wrapper
│       ├── embedding_store.py   # FAISS-backed embedding storage
│       ├── vector_store.py      # JSON-backed vector metadata store
│       ├── ingest.py            # Data ingestion pipeline
│       └── ingest_all_mnt_data.py # Bulk ingestion utility
│
├── data/                         # Data directory
│   ├── skills.json              # Skill registry
│   └── [self-eval reports]
│
├── memory_store/                 # Persistent memory storage
│   ├── memory.json              # JSON memory store
│   └── memory.index             # FAISS index file
│
├── tests/                        # Test suite
│   ├── __init__.py
│   └── test_memory.py           # Memory module tests
│
├── README.md                     # Project readme
├── __init__.py                   # Root package initialization
└── db/                          # Database directory (reserved)


ARCHITECTURE OVERVIEW
=====================

1. AGENT (skill_engine/agent.py)
   └─> Routes queries using Router
   └─> Executes skills via SkillEngine
   └─> Persists memories via MemoryManager
   └─> Returns structured results

2. ROUTER (core/router.py)
   └─> Keyword-based skill matching
   └─> Confidence scoring
   └─> Fallback handling

3. SKILL ENGINE (skill_engine/engine.py)
   └─> Dynamic skill discovery (pkgutil)
   └─> Skill instantiation and execution
   └─> Error handling wrapper

4. SKILLS (skills/*.py)
   └─> All inherit from BaseSkill
   └─> Implement run(params: dict) -> dict
   └─> Support name, description, keywords

5. MEMORY SYSTEM
   └─> Short-term: Rolling buffer (skill_engine/memory/vector_memory.py)
   └─> Long-term: FAISS + JSON (memory/long_term/)
   └─> Access: MemoryManager unified API


KEY INTERFACES
==============

BaseSkill (skill_engine/base.py):
    name: str
    description: str
    keywords: List[str]
    input_schema: Optional[Dict]
    
    def run(params: Dict[str, Any]) -> Dict[str, Any]
    def safe_run(params: Dict[str, Any]) -> Dict[str, Any]
    def validate(params: Dict[str, Any]) -> None

Agent (skill_engine/agent.py):
    def __init__(max_steps: int = 6)
    def run(task: str, verbose: bool = False) -> Dict

Router (core/router.py):
    def route(text: str) -> Dict[str, Any]
    # Returns: {"use_skill": str, "params": dict, "confidence": float}

MemoryManager (skill_engine/memory/memory_manager.py):
    def add(text: str) -> None
    def search(query: str, k: int = 5) -> List[Dict]
    def get() -> List[str]


DEPENDENCIES
============

Core:
  - Python 3.12
  - NumPy 2.3.4
  - PyTorch 2.9.1
  - Transformers 4.57.1
  - Sentence-Transformers 5.1.2
  - FAISS-CPU 1.12.0
  - Hugging Face Hub 0.36.0

Optional:
  - Tavily (for web research)


DESIGN PATTERNS
===============

1. Strategy Pattern: Skills (pluggable implementations)
2. Factory Pattern: SkillEngine (dynamic skill loading)
3. Chain of Responsibility: Agent loop (multi-step reasoning)
4. Decorator Pattern: BaseSkill.safe_run (error handling wrapper)
5. Command Pattern: Router (intent -> skill mapping)
6. Observer Pattern: Memory (store on action completion)


DATA FLOW
=========

User Query
    ↓
Agent.run(task)
    ↓
Router.route(query) → skill_name, params
    ↓
SkillEngine.run(skill_name, params)
    ↓
Skill.run(params) → result
    ↓
MemoryManager.add(result)
    ↓
Return result to user


BEST PRACTICES
==============

1. All skills should inherit from BaseSkill
2. Implement meaningful keywords for routing
3. Use type hints in run() method
4. Handle missing parameters gracefully
5. Return structured dicts from run()
6. Log important operations
7. Use np.ascontiguousarray() with FAISS operations
8. Add # type: ignore for third-party C++ bindings


CONFIGURATION
=============

Vector Model: all-MiniLM-L6-v2 (384 dims)
FAISS Index: IndexFlatL2 (for cosine similarity after normalize)
Memory Retention: 20 recent items (get_recent)
Search Top-K: 5 default results


DEVELOPMENT WORKFLOW
====================

1. Create new skill in skills/
2. Inherit from BaseSkill
3. Implement run() method
4. Add to keywords list
5. Router will auto-discover
6. Test via Agent.run() or CLI

Example:
    from skill_engine.base import BaseSkill
    
    class MySkill(BaseSkill):
        name = "my_skill"
        keywords = ["my", "keyword"]
        
        def run(self, params: dict):
            # Implementation
            return {"result": ...}
"""
