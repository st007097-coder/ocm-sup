"""
OCM Sup Graph Integration
========================

Integrates the continuity layer with the OCM Sup Knowledge Graph.

This module allows:
1. Storing pending topics as wiki entities
2. Querying pending topics using Triple-Stream Search
3. Updating entity status based on hook lifecycle
4. Using graph relationships for context

The integration leverages the existing OCM Sup infrastructure:
- Triple-Stream Search for finding relevant pending topics
- Knowledge Graph for storing continuity state entities
- Confidence/Decay for natural closure of stale items
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import re

# Add OCM Sup scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class OCMGraphIntegration:
    """
    Integrates continuity layer with OCM Sup Knowledge Graph.
    
    Usage:
        graph = OCMGraphIntegration(
            wiki_path="/path/to/wiki",
            ocm_sup_path="/path/to/OCM-Sup"
        )
        
        # Create continuity entity in wiki
        entity_id = graph.create_continuity_entity(
            topic="OCM Sup 融合研究",
            event_type="delegated_task",
            status="active"
        )
        
        # Find related pending topics
        related = graph.find_related_pending(user_query="OCM Sup")
        
        # Update entity status
        graph.update_entity_status(entity_id, "closed")
        
        # Get all pending topics from graph
        all_pending = graph.get_all_pending_entities()
    """
    
    def __init__(
        self,
        wiki_path: str = "/home/jacky/.openclaw/workspace/wiki",
        ocm_sup_path: str = "/home/jacky/.openclaw/workspace/OCM-Sup"
    ):
        self.wiki_path = Path(wiki_path)
        self.ocm_sup_path = Path(ocm_sup_path)
        
        # Ensure directories exist
        self.entities_path = self.wiki_path / "entities"
        self.entities_path.mkdir(parents=True, exist_ok=True)
        
        # Load OCM Sup graph search if available
        self._graph_search = None
        self._triple_stream = None
    
    def _get_graph_search(self):
        """Lazy load the graph search module"""
        if self._graph_search is None:
            try:
                from graph_search import GraphSearchChannel
                self._graph_search = GraphSearchChannel(str(self.wiki_path))
            except Exception as e:
                print(f"Warning: Could not load graph search: {e}")
                return None
        return self._graph_search
    
    def _get_triple_stream(self):
        """Lazy load the triple stream search module"""
        if self._triple_stream is None:
            try:
                from triple_stream_search import TripleStreamSearch
                self._triple_stream = TripleStreamSearch(str(self.wiki_path))
            except Exception as e:
                print(f"Warning: Could not load triple stream: {e}")
                return None
        return self._triple_stream
    
    def create_continuity_entity(
        self,
        topic: str,
        event_type: str,
        status: str = "active",
        followup_focus: Optional[str] = None,
        causal_memory: Optional[Dict] = None,
        context_before: Optional[str] = None
    ) -> str:
        """
        Create a continuity entity in the wiki.
        
        Creates a wiki entity file that stores the continuity state.
        
        Args:
            topic: The topic/entity name
            event_type: Type (parked_topic, delegated_task, etc.)
            status: Current status (active, closed, etc.)
            followup_focus: What to follow up on
            causal_memory: Structured causal memory
            context_before: Context before this topic
            
        Returns:
            The entity ID
        """
        import uuid
        
        # Create safe filename
        safe_topic = re.sub(r'[^\w\s]', '', topic)[:30]
        safe_topic = re.sub(r'\s+', '_', safe_topic)
        timestamp = datetime.now().strftime("%Y%m%d")
        entity_id = f"continuity_{safe_topic}_{timestamp}_{uuid.uuid4().hex[:4]}"
        
        # Build frontmatter
        frontmatter = {
            "title": f"Continuity: {topic}",
            "id": entity_id,
            "type": "continuity",
            "subtype": event_type,
            "status": status,
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "followup_focus": followup_focus or topic,
            "context_before": context_before,
        }
        
        # Add causal memory if provided
        if causal_memory:
            frontmatter["causal_memory"] = causal_memory
        
        # Add confidence with decay metadata
        frontmatter["confidence"] = 1.0
        frontmatter["last_accessed"] = datetime.now().strftime("%Y-%m-%d")
        
        # Build entity content
        content_lines = [
            "---",
        ]
        for key, value in frontmatter.items():
            if isinstance(value, dict):
                content_lines.append(f"{key}:")
                for k, v in value.items():
                    content_lines.append(f"  {k}: {v}")
            elif isinstance(value, list):
                content_lines.append(f"{key}:")
                for item in value:
                    content_lines.append(f"  - {item}")
            else:
                content_lines.append(f"{key}: {value}")
        content_lines.append("---")
        content_lines.append("")
        content_lines.append(f"# {topic}")
        content_lines.append("")
        content_lines.append(f"**Status:** {status}")
        content_lines.append(f"**Event Type:** {event_type}")
        content_lines.append(f"**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        content_lines.append("")
        if followup_focus:
            content_lines.append(f"**Follow-up Focus:** {followup_focus}")
        if context_before:
            content_lines.append(f"**Context Before:** {context_before}")
        content_lines.append("")
        content_lines.append("## Notes")
        content_lines.append("")
        content_lines.append("Content here...")
        
        # Write entity file
        entity_file = self.entities_path / f"{entity_id}.md"
        entity_file.write_text("\n".join(content_lines), encoding="utf-8")
        
        return entity_id
    
    def update_entity_status(
        self,
        entity_id: str,
        new_status: str,
        closure_reason: Optional[str] = None
    ) -> bool:
        """
        Update the status of a continuity entity.
        
        Args:
            entity_id: The entity ID
            new_status: New status (active, closed, etc.)
            closure_reason: Reason for closure if applicable
            
        Returns:
            True if successful, False if entity not found
        """
        entity_file = self.entities_path / f"{entity_id}.md"
        
        if not entity_file.exists():
            # Try to find it
            for f in self.entities_path.glob("*.md"):
                content = f.read_text(encoding="utf-8")
                if f"id: {entity_id}" in content or f"id:{entity_id}" in content:
                    entity_file = f
                    break
            else:
                return False
        
        try:
            content = entity_file.read_text(encoding="utf-8")
            
            # Update status in frontmatter
            content = re.sub(
                r'^status: .+$',
                f'status: {new_status}',
                content,
                flags=re.MULTILINE
            )
            
            # Update timestamp
            content = re.sub(
                r'^updated: .+$',
                f'updated: {datetime.now().isoformat()}',
                content,
                flags=re.MULTILINE
            )
            
            # Add closure reason if provided
            if closure_reason:
                if "closure_reason" in content:
                    content = re.sub(
                        r'^closure_reason: .+$',
                        f'closure_reason: {closure_reason}',
                        content,
                        flags=re.MULTILINE
                    )
                else:
                    # Insert after updated line
                    content = re.sub(
                        r'^(updated: .+)$',
                        r'\1\nclosure_reason: ' + closure_reason,
                        content,
                        flags=re.MULTILINE
                    )
            
            entity_file.write_text(content, encoding="utf-8")
            return True
        
        except Exception as e:
            print(f"Error updating entity: {e}")
            return False
    
    def get_entity(self, entity_id: str) -> Optional[Dict]:
        """
        Get entity data by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            Dict with entity data, or None if not found
        """
        entity_file = self.entities_path / f"{entity_id}.md"
        
        if not entity_file.exists():
            # Search for it
            for f in self.entities_path.glob("*.md"):
                if entity_id in f.stem:
                    entity_file = f
                    break
            else:
                return None
        
        try:
            content = entity_file.read_text(encoding="utf-8")
            return self._parse_entity_content(content, entity_file.stem)
        except:
            return None
    
    def _parse_entity_content(self, content: str, default_id: str) -> Dict:
        """Parse entity content into a dict"""
        result = {"id": default_id}
        
        # Extract frontmatter
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if match:
            frontmatter_text = match.group(1)
            
            for line in frontmatter_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if value:  # Skip empty values
                        result[key] = value
        
        # Extract markdown content
        content_match = re.search(r'^---\n.*?\n---\n(.*)$', content, re.DOTALL)
        if content_match:
            result["content"] = content_match.group(1).strip()
        
        return result
    
    def find_related_pending(
        self,
        user_query: str,
        event_types: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Find pending topics related to a user query.
        
        Uses Triple-Stream Search to find relevant continuity entities.
        
        Args:
            user_query: The user's query
            event_types: Filter by event types (e.g., ["delegated_task"])
            limit: Maximum number of results
            
        Returns:
            List of pending topics
        """
        # Try using triple stream search
        ts = self._get_triple_stream()
        if ts:
            try:
                # Search for matching entities
                results = ts.search(user_query, top_k=limit * 2)
                
                # Filter to continuity entities only
                pending = []
                for r in results:
                    if r.get("path", "").startswith("entities/continuity_"):
                        # Filter by event type if specified
                        if event_types:
                            # Check if any event type matches
                            entity = self.get_entity_from_path(r.get("path", ""))
                            if entity and entity.get("subtype") in event_types:
                                pending.append(entity)
                        else:
                            entity = self.get_entity_from_path(r.get("path", ""))
                            if entity:
                                pending.append(entity)
                
                return pending[:limit]
            except Exception as e:
                print(f"Triple stream search error: {e}")
        
        # Fallback: scan entity files directly
        return self._scan_continuity_entities(event_types=event_types, limit=limit)
    
    def get_entity_from_path(self, path: str) -> Optional[Dict]:
        """Get entity from a wiki path"""
        if not path:
            return None
        
        # Extract filename from path
        filename = Path(path).stem
        return self.get_entity(filename)
    
    def _scan_continuity_entities(
        self,
        event_types: Optional[List[str]] = None,
        status_filter: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Scan all continuity entities directly from files.
        
        Fallback method when Triple-Stream Search is not available.
        """
        entities = []
        
        for entity_file in self.entities_path.glob("continuity_*.md"):
            try:
                content = entity_file.read_text(encoding="utf-8")
                entity = self._parse_entity_content(content, entity_file.stem)
                
                # Filter by event type
                if event_types and entity.get("subtype") not in event_types:
                    continue
                
                # Filter by status
                if status_filter and entity.get("status") != status_filter:
                    continue
                
                entities.append(entity)
                
                if len(entities) >= limit:
                    break
            except:
                continue
        
        # Sort by created date (newest first)
        entities.sort(key=lambda x: x.get("created", ""), reverse=True)
        
        return entities[:limit]
    
    def get_all_pending_entities(
        self,
        event_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get all pending (active) continuity entities.
        
        Args:
            event_types: Filter by event types
            
        Returns:
            List of active pending entities
        """
        return self._scan_continuity_entities(
            event_types=event_types,
            status_filter="active",
            limit=50
        )
    
    def apply_confidence_decay(self, entity_id: str, decay: float = 0.02) -> bool:
        """
        Apply confidence decay to an entity.
        
        Entities that haven't been accessed recently naturally decay.
        
        Args:
            entity_id: The entity ID
            decay: Decay amount (default 0.02 = 2%)
            
        Returns:
            True if decayed, False if entity not found or already at minimum
        """
        entity = self.get_entity(entity_id)
        if not entity:
            return False
        
        current_conf = float(entity.get("confidence", 1.0))
        min_conf = 0.1
        
        if current_conf <= min_conf:
            # Entity is already at minimum, close it
            self.update_entity_status(entity_id, "closed", "expired")
            return True
        
        new_conf = max(min_conf, current_conf - decay)
        
        entity_file = self.entities_path / f"{entity_id}.md"
        if not entity_file.exists():
            return False
        
        try:
            content = entity_file.read_text(encoding="utf-8")
            
            # Update confidence
            content = re.sub(
                r'^confidence: .+$',
                f'confidence: {new_conf:.2f}',
                content,
                flags=re.MULTILINE
            )
            
            entity_file.write_text(content, encoding="utf-8")
            return True
        
        except:
            return False
    
    def cleanup_stale_entities(self, days_threshold: int = 30) -> int:
        """
        Clean up stale continuity entities.
        
        Removes entities that:
        - Have been closed for more than N days
        - Have confidence below threshold
        
        Args:
            days_threshold: Days after which closed entities are removed
            
        Returns:
            Number of entities cleaned up
        """
        cleaned = 0
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        for entity_file in self.entities_path.glob("continuity_*.md"):
            try:
                content = entity_file.read_text(encoding="utf-8")
                entity = self._parse_entity_content(content, entity_file.stem)
                
                status = entity.get("status", "active")
                
                if status == "closed":
                    # Check closure time
                    closure_time_str = entity.get("closure_time") or entity.get("updated")
                    if closure_time_str:
                        try:
                            closure_date = datetime.fromisoformat(closure_time_str.replace("Z", "+00:00"))
                            # Handle naive datetime
                            if closure_date.tzinfo is None:
                                closure_date = closure_date
                            
                            if closure_date < cutoff_date:
                                entity_file.unlink()
                                cleaned += 1
                        except:
                            pass
                
                elif status == "active":
                    # Check confidence
                    conf = float(entity.get("confidence", 1.0))
                    if conf < 0.2:
                        entity_file.unlink()
                        cleaned += 1
            
            except:
                continue
        
        return cleaned


def main():
    """Test the OCM Graph integration"""
    graph = OCMGraphIntegration()
    
    print("=== OCM Graph Integration Test ===\n")
    
    # Test 1: Create continuity entity
    print("--- Create Entity ---")
    entity_id = graph.create_continuity_entity(
        topic="OCM Sup 融合研究",
        event_type="delegated_task",
        status="active",
        followup_focus="繼續分析 Phase 2 實現",
        causal_memory={
            "facts": ["OCM Sup + openclaw-continuity"],
            "state": "delegated",
            "time_anchor": "2026-04-24",
        }
    )
    print(f"Created entity: {entity_id}")
    print()
    
    # Test 2: Get entity
    print("--- Get Entity ---")
    entity = graph.get_entity(entity_id)
    print(f"Entity: {entity}")
    print()
    
    # Test 3: Find related pending
    print("--- Find Related Pending ---")
    related = graph.find_related_pending("OCM Sup")
    print(f"Found: {len(related)} related")
    for r in related[:3]:
        print(f"  - {r.get('title', 'N/A')}: {r.get('status', 'N/A')}")
    print()
    
    # Test 4: Get all pending
    print("--- Get All Pending ---")
    all_pending = graph.get_all_pending_entities()
    print(f"Total pending: {len(all_pending)}")
    print()
    
    # Test 5: Update status
    print("--- Update Status ---")
    result = graph.update_entity_status(entity_id, "closed", "resolved")
    print(f"Updated: {result}")
    print()
    
    # Test 6: Apply decay
    print("--- Apply Confidence Decay ---")
    entity_id2 = graph.create_continuity_entity(
        topic="測試主題",
        event_type="parked_topic",
        status="active"
    )
    for i in range(5):
        decayed = graph.apply_confidence_decay(entity_id2)
        entity = graph.get_entity(entity_id2)
        print(f"  Decay {i+1}: confidence = {entity.get('confidence', 'N/A')}")
    print()


if __name__ == "__main__":
    main()
