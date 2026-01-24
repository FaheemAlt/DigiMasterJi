"""
Diagram Service - Data-Light Visual Explanations
=================================================
Generates lightweight SVG diagrams and ASCII art for visual learning.
Optimized for low-bandwidth scenarios in rural areas.

DigiMasterJi - Multilingual AI Tutor for Rural Education

Features:
- SVG diagrams (5-10KB each, text-based)
- ASCII art for ultra-low-bandwidth mode
- LLM-powered diagram generation
- Pre-built diagram templates for common STEM concepts
"""

import re
import logging
from typing import Optional, Dict, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class DiagramType(str, Enum):
    """Types of diagrams that can be generated."""
    FLOWCHART = "flowchart"
    CYCLE = "cycle"
    HIERARCHY = "hierarchy"
    COMPARISON = "comparison"
    PROCESS = "process"
    STRUCTURE = "structure"
    GRAPH = "graph"
    NONE = "none"


# Keywords that suggest a diagram would be helpful
DIAGRAM_TRIGGER_KEYWORDS = {
    # Process/Cycle keywords
    "process": DiagramType.PROCESS,
    "cycle": DiagramType.CYCLE,
    "steps": DiagramType.PROCESS,
    "stages": DiagramType.PROCESS,
    "phases": DiagramType.PROCESS,
    "how does": DiagramType.PROCESS,
    "how do": DiagramType.PROCESS,
    "kaise": DiagramType.PROCESS,  # Hindi: how
    
    # Structure keywords
    "structure": DiagramType.STRUCTURE,
    "parts": DiagramType.STRUCTURE,
    "anatomy": DiagramType.STRUCTURE,
    "components": DiagramType.STRUCTURE,
    "layers": DiagramType.STRUCTURE,
    "sanrachna": DiagramType.STRUCTURE,  # Hindi: structure
    
    # Comparison keywords
    "difference": DiagramType.COMPARISON,
    "compare": DiagramType.COMPARISON,
    "versus": DiagramType.COMPARISON,
    "vs": DiagramType.COMPARISON,
    "antar": DiagramType.COMPARISON,  # Hindi: difference
    
    # Flowchart keywords
    "flow": DiagramType.FLOWCHART,
    "sequence": DiagramType.FLOWCHART,
    "order": DiagramType.FLOWCHART,
    
    # Hierarchy keywords
    "classification": DiagramType.HIERARCHY,
    "types": DiagramType.HIERARCHY,
    "categories": DiagramType.HIERARCHY,
    "prakar": DiagramType.HIERARCHY,  # Hindi: types
    
    # Specific STEM topics that benefit from diagrams
    "photosynthesis": DiagramType.PROCESS,
    "prakash sanshleshan": DiagramType.PROCESS,  # Hindi: photosynthesis
    "water cycle": DiagramType.CYCLE,
    "jal chakra": DiagramType.CYCLE,  # Hindi: water cycle
    "food chain": DiagramType.HIERARCHY,
    "digestive system": DiagramType.PROCESS,
    "cell": DiagramType.STRUCTURE,
    "atom": DiagramType.STRUCTURE,
    "solar system": DiagramType.STRUCTURE,
    "plant": DiagramType.STRUCTURE,
    "circuit": DiagramType.FLOWCHART,
    "fraction": DiagramType.STRUCTURE,
    "equation": DiagramType.GRAPH,
}


def should_generate_diagram(query: str, response: str) -> Tuple[bool, DiagramType]:
    """
    Determine if a diagram would be helpful for the given query/response.
    
    Args:
        query: User's question
        response: AI's text response
        
    Returns:
        Tuple of (should_generate, diagram_type)
    """
    combined_text = f"{query} {response}".lower()
    
    # Check for diagram triggers
    for keyword, diagram_type in DIAGRAM_TRIGGER_KEYWORDS.items():
        if keyword in combined_text:
            # Additional check: response should be explaining something substantial
            if len(response) > 200:  # Only for detailed explanations
                logger.info(f"[DIAGRAM] Triggered by keyword '{keyword}' -> {diagram_type}")
                return True, diagram_type
    
    return False, DiagramType.NONE


def generate_svg_diagram(
    diagram_type: DiagramType,
    title: str,
    elements: list,
    colors: Optional[Dict[str, str]] = None
) -> str:
    """
    Generate a minimal SVG diagram.
    
    Args:
        diagram_type: Type of diagram to generate
        title: Diagram title
        elements: List of elements/steps to include
        colors: Optional color scheme
        
    Returns:
        SVG string (typically 5-10KB)
    """
    # Default color scheme (accessible, works on dark backgrounds)
    default_colors = {
        "primary": "#10b981",      # Emerald green
        "secondary": "#6366f1",    # Indigo
        "accent": "#f59e0b",       # Amber
        "text": "#ffffff",         # White
        "background": "#1e1b4b",   # Dark indigo
        "border": "#4f46e5",       # Indigo border
    }
    colors = colors or default_colors
    
    if diagram_type == DiagramType.PROCESS:
        return _generate_process_svg(title, elements, colors)
    elif diagram_type == DiagramType.CYCLE:
        return _generate_cycle_svg(title, elements, colors)
    elif diagram_type == DiagramType.STRUCTURE:
        return _generate_structure_svg(title, elements, colors)
    elif diagram_type == DiagramType.COMPARISON:
        return _generate_comparison_svg(title, elements, colors)
    elif diagram_type == DiagramType.HIERARCHY:
        return _generate_hierarchy_svg(title, elements, colors)
    elif diagram_type == DiagramType.FLOWCHART:
        return _generate_flowchart_svg(title, elements, colors)
    else:
        return ""


def _generate_process_svg(title: str, steps: list, colors: Dict[str, str]) -> str:
    """Generate a horizontal process/steps diagram with larger, more readable boxes."""
    num_steps = min(len(steps), 5)  # Max 5 steps for horizontal layout
    if num_steps == 0:
        return ""
    
    # Larger dimensions for better readability
    step_width = 160
    step_height = 100
    gap = 50
    
    width = 80 + num_steps * step_width + (num_steps - 1) * gap
    height = 220
    
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        f'<rect width="100%" height="100%" fill="{colors["background"]}" rx="12"/>',
        f'<text x="{width/2}" y="32" text-anchor="middle" fill="{colors["text"]}" font-size="18" font-weight="bold">{_escape_xml(title)}</text>',
    ]
    
    start_x = 40
    y = 60
    
    for i, step in enumerate(steps[:num_steps]):
        x = start_x + i * (step_width + gap)
        
        # Step box with subtle gradient effect
        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{step_width}" height="{step_height}" rx="12" '
            f'fill="{colors["primary"]}" stroke="{colors["border"]}" stroke-width="2"/>'
        )
        
        # Highlight effect
        svg_parts.append(
            f'<rect x="{x + 2}" y="{y + 2}" width="{step_width - 4}" height="20" rx="10" '
            f'fill="white" opacity="0.1"/>'
        )
        
        # Step number badge
        svg_parts.append(
            f'<circle cx="{x + 20}" cy="{y + 20}" r="14" fill="{colors["secondary"]}" stroke="{colors["border"]}" stroke-width="1"/>'
            f'<text x="{x + 20}" y="{y + 25}" text-anchor="middle" fill="{colors["text"]}" font-size="12" font-weight="bold">{i + 1}</text>'
        )
        
        # Step text (wrapped to multiple lines)
        step_text = str(step)
        wrapped_text = _wrap_text(step_text, 18)  # Characters per line
        
        # Center text block
        num_lines = min(len(wrapped_text), 4)
        line_height = 16
        text_start_y = y + 50
        
        for j, line in enumerate(wrapped_text[:4]):  # Up to 4 lines
            clean_line = line.replace("**", "")
            font_size = 12 if j == 0 else 11
            svg_parts.append(
                f'<text x="{x + step_width/2}" y="{text_start_y + j * line_height}" text-anchor="middle" '
                f'fill="{colors["text"]}" font-size="{font_size}">{_escape_xml(clean_line)}</text>'
            )
        
        # Arrow to next step
        if i < num_steps - 1:
            arrow_x_start = x + step_width + 8
            arrow_x_end = arrow_x_start + gap - 16
            arrow_y = y + step_height / 2
            
            svg_parts.append(
                f'<path d="M{arrow_x_start},{arrow_y} L{arrow_x_end},{arrow_y}" '
                f'stroke="{colors["accent"]}" stroke-width="3" marker-end="url(#arrowhead)"/>'
            )
    
    # Larger arrow marker
    svg_parts.append(
        f'<defs><marker id="arrowhead" markerWidth="12" markerHeight="9" refX="10" refY="4.5" orient="auto">'
        f'<polygon points="0 0, 12 4.5, 0 9" fill="{colors["accent"]}"/></marker></defs>'
    )
    
    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)


def _generate_cycle_svg(title: str, steps: list, colors: Dict[str, str]) -> str:
    """Generate a circular cycle diagram with larger, more readable nodes."""
    num_steps = min(len(steps), 6)
    if num_steps == 0:
        return ""
    
    # Larger size for better readability
    size = 480
    center_x, center_y = size / 2, size / 2 + 20
    radius = 150  # Larger radius for bigger nodes
    
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">',
        f'<rect width="100%" height="100%" fill="{colors["background"]}" rx="12"/>',
        f'<text x="{center_x}" y="35" text-anchor="middle" fill="{colors["text"]}" font-size="18" font-weight="bold">{_escape_xml(title)}</text>',
    ]
    
    import math
    angle_step = 2 * math.pi / num_steps
    node_radius = 55  # Larger nodes
    
    for i, step in enumerate(steps[:num_steps]):
        angle = -math.pi / 2 + i * angle_step  # Start from top
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        
        # Node circle with border
        svg_parts.append(
            f'<circle cx="{x}" cy="{y}" r="{node_radius}" fill="{colors["primary"]}" stroke="{colors["border"]}" stroke-width="2"/>'
        )
        
        # Highlight effect
        svg_parts.append(
            f'<circle cx="{x}" cy="{y - 15}" r="{node_radius - 10}" fill="white" opacity="0.08"/>'
        )
        
        # Step number
        svg_parts.append(
            f'<text x="{x}" y="{y - 20}" text-anchor="middle" fill="{colors["accent"]}" font-size="14" font-weight="bold">Step {i + 1}</text>'
        )
        
        # Step text (wrapped, more lines)
        step_text = str(step).replace("**", "")
        wrapped = _wrap_text(step_text, 14)  # More chars per line
        for j, line in enumerate(wrapped[:3]):  # Up to 3 lines
            svg_parts.append(
                f'<text x="{x}" y="{y + 2 + j * 15}" text-anchor="middle" '
                f'fill="{colors["text"]}" font-size="11">{_escape_xml(line)}</text>'
            )
        
        # Arrow to next
        if num_steps > 1:
            next_angle = -math.pi / 2 + ((i + 1) % num_steps) * angle_step
            arrow_radius = radius + node_radius + 15
            arrow_start_x = center_x + arrow_radius * math.cos(angle + angle_step * 0.25)
            arrow_start_y = center_y + arrow_radius * math.sin(angle + angle_step * 0.25)
            arrow_end_x = center_x + arrow_radius * math.cos(next_angle - angle_step * 0.25)
            arrow_end_y = center_y + arrow_radius * math.sin(next_angle - angle_step * 0.25)
            
            # Curved arrow
            ctrl_x = center_x + (arrow_radius + 30) * math.cos(angle + angle_step * 0.5)
            ctrl_y = center_y + (arrow_radius + 30) * math.sin(angle + angle_step * 0.5)
            svg_parts.append(
                f'<path d="M{arrow_start_x},{arrow_start_y} Q{ctrl_x},{ctrl_y} {arrow_end_x},{arrow_end_y}" '
                f'fill="none" stroke="{colors["accent"]}" stroke-width="3" marker-end="url(#arrowhead)"/>'
            )
    
    # Larger arrow marker
    svg_parts.append(
        f'<defs><marker id="arrowhead" markerWidth="12" markerHeight="9" refX="10" refY="4.5" orient="auto">'
        f'<polygon points="0 0, 12 4.5, 0 9" fill="{colors["accent"]}"/></marker></defs>'
    )
    
    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)


def _generate_structure_svg(title: str, parts: list, colors: Dict[str, str]) -> str:
    """Generate a labeled structure diagram with larger, more readable sections."""
    num_parts = min(len(parts), 8)
    if num_parts == 0:
        return ""
    
    # Larger dimensions
    width = 500
    row_height = 60
    header_height = 60
    height = header_height + num_parts * row_height + 20
    
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        f'<rect width="100%" height="100%" fill="{colors["background"]}" rx="12"/>',
        f'<text x="{width/2}" y="38" text-anchor="middle" fill="{colors["text"]}" font-size="18" font-weight="bold">{_escape_xml(title)}</text>',
    ]
    
    y = header_height
    for i, part in enumerate(parts[:num_parts]):
        # Alternating colors
        fill = colors["primary"] if i % 2 == 0 else colors["secondary"]
        
        # Row background
        svg_parts.append(
            f'<rect x="25" y="{y}" width="{width - 50}" height="{row_height - 8}" rx="10" fill="{fill}" stroke="{colors["border"]}" stroke-width="1"/>'
        )
        
        # Number badge
        svg_parts.append(
            f'<circle cx="55" cy="{y + (row_height - 8) / 2}" r="14" fill="{colors["accent"]}"/>'
            f'<text x="55" y="{y + (row_height - 8) / 2 + 5}" text-anchor="middle" fill="{colors["text"]}" font-size="12" font-weight="bold">{i + 1}</text>'
        )
        
        # Part text (wrapped if needed)
        part_text = str(part).replace("**", "")
        wrapped = _wrap_text(part_text, 50)
        for j, line in enumerate(wrapped[:2]):
            svg_parts.append(
                f'<text x="85" y="{y + 25 + j * 18}" fill="{colors["text"]}" font-size="13">{_escape_xml(line)}</text>'
            )
        
        y += row_height
    
    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)


def _generate_comparison_svg(title: str, items: list, colors: Dict[str, str]) -> str:
    """Generate a side-by-side comparison diagram with larger boxes and more features."""
    if len(items) < 2:
        return ""
    
    # Larger dimensions
    width = 580
    height = 350
    
    item1, item2 = items[0], items[1]
    box_width = 220
    box_height = 260
    
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        f'<rect width="100%" height="100%" fill="{colors["background"]}" rx="12"/>',
        f'<text x="{width/2}" y="35" text-anchor="middle" fill="{colors["text"]}" font-size="18" font-weight="bold">{_escape_xml(title)}</text>',
        
        # Left box
        f'<rect x="30" y="55" width="{box_width}" height="{box_height}" rx="12" fill="{colors["primary"]}" stroke="{colors["border"]}" stroke-width="2"/>',
        f'<rect x="32" y="57" width="{box_width - 4}" height="25" rx="10" fill="white" opacity="0.1"/>',
        f'<text x="{30 + box_width/2}" y="85" text-anchor="middle" fill="{colors["text"]}" font-size="15" font-weight="bold">{_escape_xml(str(item1.get("name", "Item 1")))}</text>',
        
        # Right box  
        f'<rect x="{width - 30 - box_width}" y="55" width="{box_width}" height="{box_height}" rx="12" fill="{colors["secondary"]}" stroke="{colors["border"]}" stroke-width="2"/>',
        f'<rect x="{width - 28 - box_width}" y="57" width="{box_width - 4}" height="25" rx="10" fill="white" opacity="0.1"/>',
        f'<text x="{width - 30 - box_width/2}" y="85" text-anchor="middle" fill="{colors["text"]}" font-size="15" font-weight="bold">{_escape_xml(str(item2.get("name", "Item 2")))}</text>',
        
        # VS badge in center
        f'<circle cx="{width/2}" cy="180" r="28" fill="{colors["accent"]}" stroke="{colors["border"]}" stroke-width="2"/>',
        f'<text x="{width/2}" y="186" text-anchor="middle" fill="{colors["text"]}" font-size="14" font-weight="bold">VS</text>',
    ]
    
    # Add features for item 1
    y = 115
    for idx, feature in enumerate(item1.get("features", [])[:6]):
        feature_text = str(feature).replace("**", "")[:35]
        svg_parts.append(
            f'<text x="50" y="{y}" fill="{colors["text"]}" font-size="12">• {_escape_xml(feature_text)}</text>'
        )
        y += 25
    
    # Add features for item 2
    y = 115
    for idx, feature in enumerate(item2.get("features", [])[:6]):
        feature_text = str(feature).replace("**", "")[:35]
        svg_parts.append(
            f'<text x="{width - 30 - box_width + 20}" y="{y}" fill="{colors["text"]}" font-size="12">• {_escape_xml(feature_text)}</text>'
        )
        y += 25
    
    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)


def _generate_hierarchy_svg(title: str, items: list, colors: Dict[str, str]) -> str:
    """Generate a tree/hierarchy diagram with larger nodes and better layout."""
    if not items:
        return ""
    
    # Larger dimensions
    width = 600
    height = 320
    
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        f'<rect width="100%" height="100%" fill="{colors["background"]}" rx="12"/>',
        
        # Root node (title)
        f'<rect x="{width/2 - 100}" y="25" width="200" height="55" rx="12" fill="{colors["primary"]}" stroke="{colors["border"]}" stroke-width="2"/>',
        f'<rect x="{width/2 - 98}" y="27" width="196" height="18" rx="10" fill="white" opacity="0.1"/>',
        f'<text x="{width/2}" y="58" text-anchor="middle" fill="{colors["text"]}" font-size="15" font-weight="bold">{_escape_xml(title)}</text>',
    ]
    
    # Child nodes
    num_children = min(len(items), 4)
    child_width = 120
    child_height = 100
    gap = 25
    total_width = num_children * child_width + (num_children - 1) * gap
    start_x = (width - total_width) / 2
    
    for i, item in enumerate(items[:num_children]):
        x = start_x + i * (child_width + gap)
        
        # Connecting line from root to child
        svg_parts.append(
            f'<line x1="{width/2}" y1="80" x2="{x + child_width/2}" y2="130" stroke="{colors["accent"]}" stroke-width="3"/>'
        )
        
        # Child box
        svg_parts.append(
            f'<rect x="{x}" y="130" width="{child_width}" height="{child_height}" rx="10" fill="{colors["secondary"]}" stroke="{colors["border"]}" stroke-width="2"/>'
        )
        svg_parts.append(
            f'<rect x="{x + 2}" y="132" width="{child_width - 4}" height="18" rx="8" fill="white" opacity="0.1"/>'
        )
        
        # Child text (wrapped)
        item_text = str(item).replace("**", "")
        wrapped = _wrap_text(item_text, 14)
        for j, line in enumerate(wrapped[:5]):
            font_size = 12 if j == 0 else 11
            svg_parts.append(
                f'<text x="{x + child_width/2}" y="{155 + j * 16}" text-anchor="middle" fill="{colors["text"]}" font-size="{font_size}">{_escape_xml(line)}</text>'
            )
    
    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)


def _generate_flowchart_svg(title: str, steps: list, colors: Dict[str, str]) -> str:
    """Generate a vertical flowchart with larger, more readable boxes."""
    num_steps = min(len(steps), 6)
    if num_steps == 0:
        return ""
    
    # Much larger dimensions for better readability
    width = 500
    box_width = 400
    box_height = 80  # Taller boxes for more text
    spacing = 30  # Space between boxes for arrows
    header_height = 50
    
    # Calculate dynamic height based on number of steps
    height = header_height + num_steps * (box_height + spacing) + 20
    
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        f'<rect width="100%" height="100%" fill="{colors["background"]}" rx="12"/>',
        f'<text x="{width/2}" y="32" text-anchor="middle" fill="{colors["text"]}" font-size="18" font-weight="bold">{_escape_xml(title)}</text>',
    ]
    
    y = header_height
    x = (width - box_width) / 2
    
    for i, step in enumerate(steps[:num_steps]):
        # Box shape: rounded pill for start/end, rounded rect for middle
        rx = 25 if i == 0 or i == num_steps - 1 else 10
        
        # Box with gradient-like effect (slightly lighter top)
        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{box_width}" height="{box_height}" rx="{rx}" '
            f'fill="{colors["primary"]}" stroke="{colors["border"]}" stroke-width="2"/>'
        )
        
        # Add subtle highlight at top of box
        svg_parts.append(
            f'<rect x="{x + 2}" y="{y + 2}" width="{box_width - 4}" height="20" rx="{rx - 2}" '
            f'fill="white" opacity="0.1"/>'
        )
        
        # Step text - wrap to multiple lines for better readability
        step_text = str(step)
        wrapped = _wrap_text(step_text, 45)  # More characters per line
        
        # Center the text block vertically
        num_lines = min(len(wrapped), 3)
        line_height = 18
        start_y = y + (box_height / 2) - ((num_lines - 1) * line_height / 2)
        
        for j, line in enumerate(wrapped[:3]):
            font_weight = "bold" if j == 0 and "**" in step_text else "normal"
            clean_line = line.replace("**", "")  # Remove markdown bold markers
            svg_parts.append(
                f'<text x="{width/2}" y="{start_y + j * line_height}" text-anchor="middle" '
                f'fill="{colors["text"]}" font-size="14" font-weight="{font_weight}">{_escape_xml(clean_line)}</text>'
            )
        
        # Arrow to next step
        if i < num_steps - 1:
            arrow_y_start = y + box_height
            arrow_y_end = y + box_height + spacing - 5
            
            # Larger, more prominent arrow
            svg_parts.append(
                f'<path d="M{width/2},{arrow_y_start + 5} L{width/2},{arrow_y_end}" '
                f'stroke="{colors["accent"]}" stroke-width="3" marker-end="url(#arrowhead)"/>'
            )
        
        y += box_height + spacing
    
    # Larger arrow marker
    svg_parts.append(
        f'<defs><marker id="arrowhead" markerWidth="12" markerHeight="9" refX="10" refY="4.5" orient="auto">'
        f'<polygon points="0 0, 12 4.5, 0 9" fill="{colors["accent"]}"/></marker></defs>'
    )
    
    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)


def generate_ascii_art(diagram_type: DiagramType, title: str, elements: list) -> str:
    """
    Generate ASCII art for ultra-low-bandwidth mode.
    
    Args:
        diagram_type: Type of diagram
        title: Diagram title
        elements: List of elements
        
    Returns:
        ASCII art string
    """
    if diagram_type == DiagramType.PROCESS:
        return _generate_process_ascii(title, elements)
    elif diagram_type == DiagramType.CYCLE:
        return _generate_cycle_ascii(title, elements)
    elif diagram_type == DiagramType.HIERARCHY:
        return _generate_hierarchy_ascii(title, elements)
    elif diagram_type == DiagramType.COMPARISON:
        return _generate_comparison_ascii(title, elements)
    else:
        return _generate_generic_ascii(title, elements)


def _generate_process_ascii(title: str, steps: list) -> str:
    """Generate ASCII process diagram."""
    lines = [f"┌{'─' * (len(title) + 2)}┐", f"│ {title} │", f"└{'─' * (len(title) + 2)}┘", ""]
    
    for i, step in enumerate(steps[:6], 1):
        step_text = str(step)[:40]  # Truncate long text
        lines.append(f"  [{i}] {step_text}")
        if i < len(steps[:6]):
            lines.append("      ↓")
    
    return "\n".join(lines)


def _generate_cycle_ascii(title: str, steps: list) -> str:
    """Generate ASCII cycle diagram."""
    lines = [f"    ╔══ {title} ══╗", ""]
    
    num_steps = min(len(steps), 6)
    for i, step in enumerate(steps[:num_steps]):
        step_text = str(step)[:30]
        if i == 0:
            lines.append(f"    ┌─→ {step_text}")
        elif i == num_steps - 1:
            lines.append(f"    │   {step_text} ─┐")
            lines.append(f"    └─────────────────────┘")
        else:
            lines.append(f"    │   ↓")
            lines.append(f"    │   {step_text}")
    
    return "\n".join(lines)


def _generate_hierarchy_ascii(title: str, items: list) -> str:
    """Generate ASCII hierarchy/tree."""
    lines = [f"        [{title}]", "            │"]
    
    num_items = min(len(items), 4)
    for i, item in enumerate(items[:num_items]):
        item_text = str(item)[:25]
        connector = "├──" if i < num_items - 1 else "└──"
        lines.append(f"        {connector} {item_text}")
    
    return "\n".join(lines)


def _generate_comparison_ascii(title: str, items: list) -> str:
    """Generate ASCII comparison."""
    if len(items) < 2:
        return _generate_generic_ascii(title, items)
    
    item1 = items[0] if isinstance(items[0], dict) else {"name": items[0]}
    item2 = items[1] if isinstance(items[1], dict) else {"name": items[1]}
    
    name1 = str(item1.get("name", "Item 1"))[:15]
    name2 = str(item2.get("name", "Item 2"))[:15]
    
    lines = [
        f"╔═══════════════════════════════════════╗",
        f"║            {title:^25} ║",
        f"╠═══════════════════╦═══════════════════╣",
        f"║  {name1:^15}  ║  {name2:^15}  ║",
        f"╠═══════════════════╬═══════════════════╣",
    ]
    
    features1 = item1.get("features", [])[:3]
    features2 = item2.get("features", [])[:3]
    
    for i in range(max(len(features1), len(features2), 1)):
        f1 = str(features1[i])[:15] if i < len(features1) else ""
        f2 = str(features2[i])[:15] if i < len(features2) else ""
        lines.append(f"║ • {f1:<14}  ║ • {f2:<14}  ║")
    
    lines.append(f"╚═══════════════════╩═══════════════════╝")
    
    return "\n".join(lines)


def _generate_generic_ascii(title: str, items: list) -> str:
    """Generate generic ASCII list."""
    lines = [f"┌─ {title} ─┐", ""]
    
    for item in items[:8]:
        item_text = str(item)[:50]
        lines.append(f"  • {item_text}")
    
    return "\n".join(lines)


def _wrap_text(text: str, max_chars: int) -> list:
    """Wrap text into lines of max_chars."""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= max_chars:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word)
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines


def _escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


def extract_diagram_elements_from_response(response: str, diagram_type: DiagramType) -> list:
    """
    Extract diagram elements from the LLM response.
    
    This analyzes the response text to find numbered steps, bullet points,
    or key concepts that can be visualized.
    
    Args:
        response: The AI response text
        diagram_type: Type of diagram to extract elements for
        
    Returns:
        List of elements for the diagram
    """
    elements = []
    
    # Pattern for numbered steps (1. Step, 1) Step, Step 1:)
    numbered_pattern = r'(?:^|\n)\s*(?:\d+[\.\)]\s*|Step\s*\d+:?\s*)([^\n]+)'
    numbered_matches = re.findall(numbered_pattern, response, re.IGNORECASE)
    
    if numbered_matches:
        elements = [match.strip() for match in numbered_matches[:6]]
        return elements
    
    # Pattern for bullet points
    bullet_pattern = r'(?:^|\n)\s*[•\-\*]\s*([^\n]+)'
    bullet_matches = re.findall(bullet_pattern, response)
    
    if bullet_matches:
        elements = [match.strip() for match in bullet_matches[:6]]
        return elements
    
    # Pattern for key concepts (bold or capitalized phrases)
    bold_pattern = r'\*\*([^\*]+)\*\*'
    bold_matches = re.findall(bold_pattern, response)
    
    if bold_matches:
        elements = [match.strip() for match in bold_matches[:6]]
        return elements
    
    # Fallback: Split by sentences and take key ones
    sentences = re.split(r'[।\.\?\!]', response)
    key_sentences = [s.strip() for s in sentences if 10 < len(s.strip()) < 100][:5]
    
    return key_sentences


# Singleton instance
class DiagramService:
    """Service class for diagram generation."""
    
    def should_include_diagram(self, query: str, response: str) -> Tuple[bool, DiagramType]:
        """Check if a diagram should be included."""
        return should_generate_diagram(query, response)
    
    def generate_diagram(
        self,
        query: str,
        response: str,
        low_bandwidth: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a diagram for the response if appropriate.
        
        Args:
            query: User's question
            response: AI response text
            low_bandwidth: If True, generate ASCII art instead of SVG
            
        Returns:
            Dictionary with diagram data or None if no diagram needed
        """
        should_gen, diagram_type = self.should_include_diagram(query, response)
        
        if not should_gen:
            return None
        
        # Extract elements from response
        elements = extract_diagram_elements_from_response(response, diagram_type)
        
        if not elements or len(elements) < 2:
            logger.info("[DIAGRAM] Not enough elements extracted from response")
            return None
        
        # Generate title from query
        title = self._generate_title(query, diagram_type)
        
        if low_bandwidth:
            # Generate ASCII art
            ascii_art = generate_ascii_art(diagram_type, title, elements)
            return {
                "type": "ascii",
                "diagram_type": diagram_type.value,
                "content": ascii_art,
                "title": title
            }
        else:
            # Generate SVG
            svg = generate_svg_diagram(diagram_type, title, elements)
            if svg:
                return {
                    "type": "svg",
                    "diagram_type": diagram_type.value,
                    "content": svg,
                    "title": title,
                    "size_bytes": len(svg.encode('utf-8'))
                }
        
        return None
    
    def _generate_title(self, query: str, diagram_type: DiagramType) -> str:
        """Generate a diagram title from the query."""
        # Clean up query
        title = query.strip()
        
        # Remove question marks and common prefixes
        title = re.sub(r'^(what is|how does|explain|kya hai|kaise|bataiye)\s*', '', title, flags=re.IGNORECASE)
        title = title.rstrip('?।')
        
        # Capitalize and truncate
        title = title.capitalize()
        if len(title) > 40:
            title = title[:37] + "..."
        
        return title or diagram_type.value.capitalize()


# Global instance
diagram_service = DiagramService()
