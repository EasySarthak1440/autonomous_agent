"""
Memory System - Hierarchical memory for context and learning with Knowledge Graph capabilities
"""

import json
import logging
import os
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional, Tuple

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
    # Knowledge Graph fields
    entities: List[dict] = field(default_factory=list)  # Extracted entities
    relationships: List[dict] = field(default_factory=list)  # Extracted relationships


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
        print(f"Database initialized at {self.db_path}")  # Debug line
        
    def _init_database(self):
        """Initialize memory database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create memories table with knowledge graph fields
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                last_accessed TEXT NOT NULL,
                metadata TEXT,
                embedding BLOB,
                entities TEXT,  -- JSON array of extracted entities
                relationships TEXT  -- JSON array of extracted relationships
            )
        """)
        
        # Create indexes for semantic search and knowledge graph queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_type 
            ON memories(memory_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_importance 
            ON memories(importance DESC)
        """)
        
        # Index for entity-based queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities 
            ON memories(entities)
        """)
        
        conn.commit()
        conn.close()
        
    async def store(
        self,
        content: str,
        memory_type: str = "semantic",
        importance: float = 0.5,
        metadata: Optional[dict] = None,
        entities: Optional[List[dict]] = None,
        relationships: Optional[List[dict]] = None
    ) -> str:
        """Store a memory item with optional knowledge graph data."""
        memory_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO memories (id, content, memory_type, importance, created_at, last_accessed, metadata, entities, relationships)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (memory_id, content, memory_type, importance, now, now, json.dumps(metadata or {}), 
              json.dumps(entities or []), json.dumps(relationships or [])))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Stored memory: {memory_id} ({memory_type}) with {len(entities or [])} entities and {len(relationships or [])} relationships")
        return memory_id

    def _extract_entities_and_relationships(self, text: str) -> Tuple[List[dict], List[dict]]:
        """
        Extract entities and relationships from text.
        This is a simplified implementation - in production, use NER models like spaCy or Stanza.
        
        Returns:
            Tuple of (entities, relationships) where:
            - entities: List of dicts with keys: 'text', 'type', 'start', 'end'
            - relationships: List of dicts with keys: 'source', 'target', 'type', 'confidence'
        """
        entities = []
        relationships = []
        
        # Simple entity extraction based on patterns
        # This is a placeholder - replace with proper NER in production
        
        # Extract potential person names (capitalized words)
        person_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        for match in re.finditer(person_pattern, text):
            # Filter out common false positives
            if match.group() not in ['The', 'This', 'That', 'And', 'Or', 'But']:
                entities.append({
                    'text': match.group(),
                    'type': 'PERSON',
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.8
                })
        
        # Extract potential organizations (words with Inc, Corp, Ltd, etc.)
        org_pattern = r'\b[A-Z][a-zA-Z0-9&\s]*(?:Inc|Corp|Ltd|LLC|Company|Co\.|Group)\b'
        for match in re.finditer(org_pattern, text):
            entities.append({
                'text': match.group(),
                'type': 'ORGANIZATION',
                'start': match.start(),
                'end': match.end(),
                'confidence': 0.7
            })
        
        # Extract potential locations (capitalized words often followed by state/country)
        location_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*(?:[A-Z]{2}|[A-Z][a-z]+(?:,\s*[A-Z][a-z]+)*)\b'
        for match in re.finditer(location_pattern, text):
            entities.append({
                'text': match.group(),
                'type': 'LOCATION',
                'start': match.start(),
                'end': match.end(),
                'confidence': 0.6
            })
        
        # Simple relationship extraction based on verb patterns
        # Subject-Verb-Object patterns
        sv_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(is|was|are|were|has|have|had|works\s+for|employed\s+at|located\s+in|based\s+in|founded\s+in|founded\s+by|owned\s+by|managed\s+by)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        for match in re.finditer(sv_pattern, text, re.IGNORECASE):
            relationships.append({
                'source': match.group(1),
                'target': match.group(3),
                'type': match.group(2).upper().replace(' ', '_'),
                'confidence': 0.7
            })
        
        return entities, relationships
    
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
        query_terms = [t for t in query.lower().split() if t]
        conditions = ["importance >= ?"]
        params = [min_importance]
        
        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type)
        
        # Build LIKE conditions for each query term
        if query_terms:
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
                "metadata": json.loads(row[5]) if row[5] else {},
                "entities": json.loads(row[6]) if row[6] else [],
                "relationships": json.loads(row[7]) if row[7] else []
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
        
        # Extract entities and relationships from the content
        entities, relationships = self._extract_entities_and_relationships(content)
        
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
            metadata=experience_metadata,
            entities=entities,
            relationships=relationships
        )
    
    async def store_knowledge(
        self,
        fact: str,
        category: str = "general",
        importance: float = 0.5
    ) -> str:
        """Store a piece of knowledge in semantic memory."""
        # Extract entities and relationships from the fact
        entities, relationships = self._extract_entities_and_relationships(fact)
        
        return await self.store(
            content=fact,
            memory_type="semantic",
            importance=importance,
            metadata={"category": category},
            entities=entities,
            relationships=relationships
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

    async def query_entities(self, entity_type: Optional[str] = None, limit: int = 10) -> List[dict]:
        """
        Query memories by entity type or get all entities.
        
        Args:
            entity_type: Optional entity type to filter by (PERSON, ORGANIZATION, LOCATION, etc.)
            limit: Maximum number of entities to return
            
        Returns:
            List of entity dictionaries with memory context
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if entity_type:
            # Query for memories containing entities of specific type
            cursor.execute("""
                SELECT id, content, memory_type, importance, created_at, metadata, entities
                FROM memories
                WHERE entities LIKE ?
                ORDER BY importance DESC
                LIMIT ?
            """, (f'%"{entity_type}%"', limit))
        else:
            # Get all memories with entities
            cursor.execute("""
                SELECT id, content, memory_type, importance, created_at, metadata, entities
                FROM memories
                WHERE entities IS NOT NULL AND entities != '[]'
                ORDER BY importance DESC
                LIMIT ?
            """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            entities_list = json.loads(row[6]) if row[6] else []
            # Filter entities by type if specified
            if entity_type:
                entities_list = [e for e in entities_list if e.get('type') == entity_type]
            
            for entity in entities_list:
                results.append({
                    "entity": entity,
                    "memory_id": row[0],
                    "memory_content": row[1][:100] + "..." if len(row[1]) > 100 else row[1],
                    "memory_type": row[2],
                    "importance": row[3],
                    "created_at": row[4],
                    "metadata": json.loads(row[5]) if row[5] else {}
                })
        
        conn.close()
        return results

    async def query_relationships(self, relationship_type: Optional[str] = None, limit: int = 10) -> List[dict]:
        """
        Query memories by relationship type or get all relationships.
        
        Args:
            relationship_type: Optional relationship type to filter by
            limit: Maximum number of relationships to return
            
        Returns:
            List of relationship dictionaries with memory context
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if relationship_type:
            # Query for memories containing relationships of specific type
            cursor.execute("""
                SELECT id, content, memory_type, importance, created_at, metadata, relationships
                FROM memories
                WHERE relationships LIKE ?
                ORDER BY importance DESC
                LIMIT ?
            """, (f'%"{relationship_type}%"', limit))
        else:
            # Get all memories with relationships
            cursor.execute("""
                SELECT id, content, memory_type, importance, created_at, metadata, relationships
                FROM memories
                WHERE relationships IS NOT NULL AND relationships != '[]'
                ORDER BY importance DESC
                LIMIT ?
            """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            relationships_list = json.loads(row[6]) if row[6] else []
            # Filter relationships by type if specified
            if relationship_type:
                relationships_list = [r for r in relationships_list if r.get('type') == relationship_type]
            
            for relationship in relationships_list:
                results.append({
                    "relationship": relationship,
                    "memory_id": row[0],
                    "memory_content": row[1][:100] + "..." if len(row[1]) > 100 else row[1],
                    "memory_type": row[2],
                    "importance": row[3],
                    "created_at": row[4],
                    "metadata": json.loads(row[5]) if row[5] else {}
                })
        
        conn.close()
        return results

    async def get_knowledge_graph_stats(self) -> dict:
        """
        Get statistics about the knowledge graph stored in memory.
        
        Returns:
            Dictionary with knowledge graph statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count memories with entities/relationships
        cursor.execute("""
            SELECT 
                COUNT(*) as total_memories,
                SUM(CASE WHEN entities != '[]' THEN 1 ELSE 0 END) as memories_with_entities,
                SUM(CASE WHEN relationships != '[]' THEN 1 ELSE 0 END) as memories_with_relationships
            FROM memories
        """)
        
        row = cursor.fetchone()
        total_memories = row[0] if row[0] else 0
        memories_with_entities = row[1] if row[1] else 0
        memories_with_relationships = row[2] if row[2] else 0
        
        # Get unique entity types
        cursor.execute("""
            SELECT entities FROM memories 
            WHERE entities IS NOT NULL AND entities != '[]'
        """)
        
        entity_types = set()
        for row in cursor.fetchall():
            try:
                entities_list = json.loads(row[0])
                for entity in entities_list:
                    entity_types.add(entity.get('type', 'UNKNOWN'))
            except:
                pass
        
        # Get unique relationship types
        cursor.execute("""
            SELECT relationships FROM memories 
            WHERE relationships IS NOT NULL AND relationships != '[]'
        """)
        
        relationship_types = set()
        for row in cursor.fetchall():
            try:
                relationships_list = json.loads(row[0])
                for relationship in relationships_list:
                    relationship_types.add(relationship.get('type', 'UNKNOWN'))
            except:
                pass
        
        conn.close()
        
        return {
            "total_memories": total_memories,
            "memories_with_entities": memories_with_entities,
            "memories_with_relationships": memories_with_relationships,
            "unique_entity_types": list(entity_types),
            "unique_relationship_types": list(relationship_types),
            "entity_coverage": memories_with_entities / max(total_memories, 1) * 100,
            "relationship_coverage": memories_with_relationships / max(total_memories, 1) * 100
        }
    
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
    
    def clear_all(self):
        """Clear all memories from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM memories")
        conn.commit()
        conn.close()
        
        self.working_memory = {}
        logger.info("All memories cleared")
