"""
Memory System - Hierarchical memory for context and learning
"""

import json
import logging
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    """A single memory item."""
    id: str
    content: str
    memory_type: str  # semantic, episodic, procedural
    importance: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    embedding: Optional[list] = None


class MemorySystem:
    """
    Hierarchical memory system with:
    - Semantic memory: Facts, knowledge, domain expertise
    - Episodic memory: Past experiences and executions
    - Procedural memory: Learned patterns and workflows
    - Working memory: Current context
    """
    
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        self._init_database()
        self.working_memory = {}
        
    def _init_database(self):
        """Initialize memory database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                metadata TEXT,
                embedding BLOB
            )
        """)
        
        # Create index for semantic search
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_type 
            ON memories(memory_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_importance 
            ON memories(importance DESC)
        """)
        
        conn.commit()
        conn.close()
        
    async def store(
        self,
        content: str,
        memory_type: str = "semantic",
        importance: float = 0.5,
        metadata: Optional[dict] = None
    ) -> str:
        """Store a memory item."""
        memory_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO memories (id, content, memory_type, importance, created_at, last_accessed, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (memory_id, content, memory_type, importance, now, now, json.dumps(metadata or {})))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Stored memory: {memory_id} ({memory_type})")
        return memory_id
    
    async def retrieve(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> list[dict]:
        """Retrieve relevant memories."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Simple keyword-based retrieval
        # In production, use vector embeddings for semantic search
        query_terms = query.lower().split()
        conditions = ["importance >= ?"]
        params = [min_importance]
        
        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type)
        
        # Build LIKE conditions for each query term
        like_conditions = " OR ".join(["content LIKE ?" for _ in query_terms])
        conditions.append(f"({like_conditions})")
        for term in query_terms:
            params.append(f"%{term}%")
        
        where_clause = " AND ".join(conditions)
        
        cursor.execute(f"""
            SELECT id, content, memory_type, importance, created_at, metadata
            FROM memories
            WHERE {where_clause}
            ORDER BY importance DESC
            LIMIT ?
        """, (*params, limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "content": row[1],
                "memory_type": row[2],
                "importance": row[3],
                "created_at": row[4],
                "metadata": json.loads(row[5]) if row[5] else {}
            })
        
        conn.close()
        
        return results
    
    async def store_experience(
        self,
        task: str,
        outcome: str,
        steps: list,
        tools_used: list,
        confidence: float,
        metadata: Optional[dict] = None
    ) -> str:
        """Store an episodic memory of an execution."""
        content = f"Task: {task}\nOutcome: {outcome}\nTools: {', '.join(tools_used)}\nConfidence: {confidence}"
        
        importance = 0.8 if outcome == "success" else 0.9  # Failures are more important
        
        experience_metadata = {
            "outcome": outcome,
            "steps": steps,
            "tools_used": tools_used,
            "confidence": confidence,
            **(metadata or {})
        }
        
        return await self.store(
            content=content,
            memory_type="episodic",
            importance=importance,
            metadata=experience_metadata
        )
    
    async def store_knowledge(
        self,
        fact: str,
        category: str = "general",
        importance: float = 0.5
    ) -> str:
        """Store a piece of knowledge in semantic memory."""
        return await self.store(
            content=fact,
            memory_type="semantic",
            importance=importance,
            metadata={"category": category}
        )
    
    async def store_procedure(
        self,
        name: str,
        description: str,
        steps: list,
        success_rate: float = 0.0
    ) -> str:
        """Store a learned procedure."""
        content = f"Procedure: {name}\nDescription: {description}\nSteps: {json.dumps(steps)}"
        
        return await self.store(
            content=content,
            memory_type="procedural",
            importance=success_rate,
            metadata={"steps": steps, "success_rate": success_rate}
        )
    
    def set_working_memory(self, key: str, value: Any):
        """Set a working memory value."""
        self.working_memory[key] = value
        
    def get_working_memory(self, key: str, default: Any = None) -> Any:
        """Get a working memory value."""
        return self.working_memory.get(key, default)
    
    def clear_working_memory(self):
        """Clear all working memory."""
        self.working_memory = {}
    
    async def get_episodes(self, limit: int = 20) -> list[dict]:
        """Get recent episodic memories."""
        return await self.retrieve("", memory_type="episodic", limit=limit)
    
    async def get_procedures(self) -> list[dict]:
        """Get all stored procedures."""
        return await self.retrieve("", memory_type="procedural", limit=50)
    
    async def get_statistics(self) -> dict:
        """Get memory statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT memory_type, COUNT(*), AVG(importance)
            FROM memories
            GROUP BY memory_type
        """)
        
        stats = {}
        for row in cursor.fetchall():
            stats[row[0]] = {
                "count": row[1],
                "avg_importance": row[2]
            }
        
        conn.close()
        
        stats["working_memory"] = len(self.working_memory)
        return stats
    
    async def consolidate(self):
        """Consolidate memories - remove duplicates, update importance."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Simple consolidation: update last_accessed
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE memories 
            SET last_accessed = ?
            WHERE datetime(last_accessed) < datetime(?, '-30 days')
        """, (now, now))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Consolidated memories: removed/updated {deleted} old entries")
