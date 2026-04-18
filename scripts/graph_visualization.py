#!/usr/bin/env python3
"""
Knowledge Graph Visualization
OCM Sup 7-Dir 7: Visualize entity relationships

Usage:
    python3 graph_visualization.py                 # Generate Mermaid diagram
    python3 graph_visualization.py --format dot    # Generate Graphviz DOT
    python3 graph_visualization.py --format html   # Generate HTML viewer
    python3 graph_visualization.py --focus 期哥    # Focus on specific entity
    python3 graph_visualization.py --depth 2       # Show 2-degree connections
"""

import sys
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Optional

sys.path.insert(0, '/root/.openclaw/workspace/skills/triple-stream-search/scripts')

from triple_stream_search import TripleStreamSearch

class GraphVisualization:
    """
    Generate visualizations of the knowledge graph.
    
    Supports multiple output formats:
    - Mermaid: Flowchart/Mindmap diagrams
    - DOT: Graphviz format
    - HTML: Interactive viewer
    """
    
    def __init__(self, wiki_path: str = "/root/.openclaw/workspace/wiki"):
        self.wiki_path = Path(wiki_path)
        self.search = TripleStreamSearch(wiki_path=wiki_path)
        self.graph = self.search.graph_channel
        
        # Entity colors by type
        self.type_colors = {
            'person': '#FF6B6B',      # Red
            'project': '#4ECDC4',     # Teal
            'system': '#45B7D1',     # Blue
            'concept': '#96CEB4',    # Green
            'document_title': '#FFEAA7',  # Yellow
            'entity': '#DDA0DD',     # Plum
            'unknown': '#E0E0E0',    # Gray
        }
        
        # Relationship colors
        self.rel_colors = {
            'works_on': '#FF6B6B',
            'uses': '#45B7D1',
            'involves': '#4ECDC4',
            'manages': '#FFA07A',
            'related_to': '#E0E0E0',
            'integrates_with': '#9B59B6',
            'default': '#C0C0C0',
        }
    
    def get_entity_color(self, entity_type: str) -> str:
        """Get color for entity type"""
        return self.type_colors.get(entity_type.lower(), self.type_colors['unknown'])
    
    def get_rel_color(self, rel_type: str) -> str:
        """Get color for relationship type"""
        return self.rel_colors.get(rel_type.lower(), self.rel_colors['default'])
    
    def get_reachable_entities(self, start_entity: str, depth: int = 1) -> Set[str]:
        """Get all entities reachable within N degrees"""
        reachable = {start_entity}
        current_level = {start_entity}
        
        for _ in range(depth):
            next_level = set()
            for node_id in current_level:
                for edge in self.graph.edges:
                    if edge.source_id == node_id:
                        next_level.add(edge.target_id)
                    elif edge.target_id == node_id:
                        next_level.add(edge.source_id)
            reachable.update(next_level)
            current_level = next_level
        
        return reachable
    
    def generate_mermaid(self, focus_entity: Optional[str] = None, depth: int = 1) -> str:
        """Generate Mermaid flowchart diagram"""
        lines = ["```mermaid", "flowchart LR"]
        
        # Determine which entities to include
        if focus_entity:
            entities_to_show = self.get_reachable_entities(focus_entity, depth)
            lines.append(f"    %% Focus: {focus_entity} (depth={depth})")
        else:
            entities_to_show = set(self.graph.nodes.keys())
        
        # Add nodes
        for node_id in entities_to_show:
            node = self.graph.nodes.get(node_id)
            if not node:
                continue
            
            color = self.get_entity_color(node.entity_type)
            # Escape special characters in name
            name = node.name.replace('"', "'").replace('[', '(').replace(']', ')')
            lines.append(f"    {node_id.replace(' ', '_')}[\"{name}\"]")
        
        # Add edges
        for edge in self.graph.edges:
            if edge.source_id in entities_to_show and edge.target_id in entities_to_show:
                color = self.get_rel_color(edge.relationship_type)
                src = edge.source_id.replace(' ', '_')
                tgt = edge.target_id.replace(' ', '_')
                rel = edge.relationship_type.replace(' ', '_')
                lines.append(f"    {src} --{rel}--> {tgt}")
        
        lines.append("```")
        return "\n".join(lines)
    
    def generate_dot(self, focus_entity: Optional[str] = None, depth: int = 1) -> str:
        """Generate Graphviz DOT format"""
        lines = [
            "digraph KnowledgeGraph {",
            "    rankdir=LR;",
            "    node [shape=box, style=filled, fontname=\"Arial\"];",
            "    edge [fontname=\"Arial\", fontsize=10];",
        ]
        
        # Determine which entities to include
        if focus_entity:
            entities_to_show = self.get_reachable_entities(focus_entity, depth)
            lines.append(f"    // Focus: {focus_entity} (depth={depth})")
        else:
            entities_to_show = set(self.graph.nodes.keys())
        
        # Add nodes
        for node_id in entities_to_show:
            node = self.graph.nodes.get(node_id)
            if not node:
                continue
            
            color = self.get_entity_color(node.entity_type)
            name = node.name.replace('"', '\\"').replace('<', '\\<').replace('>', '\\>')
            lines.append(f'    "{node_id}" [label="{name}", fillcolor="{color}"];')
        
        # Add edges
        for edge in self.graph.edges:
            if edge.source_id in entities_to_show and edge.target_id in entities_to_show:
                color = self.get_rel_color(edge.relationship_type)
                rel = edge.relationship_type
                lines.append(f'    "{edge.source_id}" -> "{edge.target_id}" [label="{rel}", color="{color}"];')
        
        lines.append("}")
        return "\n".join(lines)
    
    def generate_html(self, focus_entity: Optional[str] = None, depth: int = 1) -> str:
        """Generate interactive HTML viewer with Mermaid.js"""
        mermaid_code = self.generate_mermaid(focus_entity, depth)
        
        # Determine which entities to include
        if focus_entity:
            entities_to_show = self.get_reachable_entities(focus_entity, depth)
        else:
            entities_to_show = set(self.graph.nodes.keys())
        
        # Count entities and relationships
        entity_count = len(entities_to_show)
        rel_count = sum(1 for e in self.graph.edges 
                       if e.source_id in entities_to_show and e.target_id in entities_to_show)
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCM Sup Knowledge Graph</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #4ECDC4;
            margin: 0 0 10px 0;
        }}
        .stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 20px;
        }}
        .stat {{
            background: rgba(255,255,255,0.1);
            padding: 10px 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #4ECDC4;
        }}
        .stat-label {{
            font-size: 0.9em;
            color: #aaa;
        }}
        .legend {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9em;
        }}
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
        }}
        .graph-container {{
            background: rgba(255,255,255,0.95);
            border-radius: 12px;
            padding: 20px;
            margin: 0 auto;
            max-width: 1200px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        .mermaid {{
            display: flex;
            justify-content: center;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: #666;
            font-size: 0.8em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 OCM Sup Knowledge Graph</h1>
        <p>Triple-Stream Search + Proactive Discovery</p>
    </div>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-value">{entity_count}</div>
            <div class="stat-label">Entities</div>
        </div>
        <div class="stat">
            <div class="stat-value">{len(self.graph.edges)}</div>
            <div class="stat-label">Relationships</div>
        </div>
        {f'<div class="stat"><div class="stat-value">{focus_entity}</div><div class="stat-label">Focus Entity</div></div>' if focus_entity else ''}
    </div>
    
    <div class="legend">
        <div class="legend-item">
            <div class="legend-color" style="background: #FF6B6B"></div>
            <span>Person (人)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #4ECDC4"></div>
            <span>Project (項目)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #45B7D1"></div>
            <span>System (系統)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #96CEB4"></div>
            <span>Concept (概念)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #FFEAA7"></div>
            <span>Document (文檔)</span>
        </div>
    </div>
    
    <div class="graph-container">
        <div class="mermaid">
{mermaid_code.replace('```mermaid', '').replace('```', '')}
        </div>
    </div>
    
    <div class="footer">
        <p>Generated by OCM Sup Graph Visualization | {len(self.graph.nodes)} total nodes, {len(self.graph.edges)} edges</p>
    </div>
    
    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'base',
            flowchart: {{
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            }},
            themeVariables: {{
                fontFamily: 'Arial, sans-serif',
                fontSize: '14px'
            }}
        }});
    </script>
</body>
</html>"""
        return html
    
    def save_output(self, format: str, output_path: Path, focus_entity: Optional[str] = None, depth: int = 1):
        """Save visualization to file"""
        if format == 'mermaid':
            content = self.generate_mermaid(focus_entity, depth)
        elif format == 'dot':
            content = self.generate_dot(focus_entity, depth)
        elif format == 'html':
            content = self.generate_html(focus_entity, depth)
        else:
            raise ValueError(f"Unknown format: {format}")
        
        output_path.write_text(content, encoding='utf-8')
        print(f"✅ Saved {format.upper()} visualization to: {output_path}")
    
    def print_summary(self):
        """Print graph summary"""
        print(f"📊 Knowledge Graph Summary:")
        print(f"   Total entities: {len(self.graph.nodes)}")
        print(f"   Total relationships: {len(self.graph.edges)}")
        
        # Count by type
        type_counts = defaultdict(int)
        for node in self.graph.nodes.values():
            type_counts[node.entity_type] += 1
        
        print(f"\n   Entities by type:")
        for t, c in sorted(type_counts.items()):
            print(f"      {t}: {c}")
        
        # Count by relationship type
        rel_counts = defaultdict(int)
        for edge in self.graph.edges:
            rel_counts[edge.relationship_type] += 1
        
        print(f"\n   Relationships by type:")
        for t, c in sorted(rel_counts.items()):
            print(f"      {t}: {c}")

def main():
    parser = argparse.ArgumentParser(description='Knowledge Graph Visualization')
    parser.add_argument('--format', choices=['mermaid', 'dot', 'html'], default='html',
                       help='Output format')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--focus', help='Focus on specific entity')
    parser.add_argument('--depth', type=int, default=1, help='Depth for focused view')
    parser.add_argument('--no-save', action='store_true', help='Print but do not save')
    
    args = parser.parse_args()
    
    viz = GraphVisualization()
    viz.print_summary()
    
    print()
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        suffix = args.format
        if args.focus:
            suffix = f"{args.focus}_{suffix}"
        output_path = Path(f"/root/.openclaw/scripts/knowledge_graph_{suffix}.{args.format if args.format != 'html' else 'html'}")
    
    if not args.no_save:
        viz.save_output(args.format, output_path, args.focus, args.depth)
        print()
        
        if args.format == 'html':
            print(f"🌐 Open in browser: file://{output_path}")
    
    # Print the content
    print()
    print(f"=== {args.format.upper()} Output ===")
    print()
    
    if args.format == 'mermaid':
        print(viz.generate_mermaid(args.focus, args.depth))
    elif args.format == 'dot':
        print(viz.generate_dot(args.focus, args.depth))
    elif args.format == 'html':
        print(viz.generate_html(args.focus, args.depth)[:2000])
        print("... (truncated, see full output in file)")

if __name__ == '__main__':
    main()