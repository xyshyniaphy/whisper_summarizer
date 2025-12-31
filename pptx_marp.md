---
marp: true
theme: gaia
paginate: true
backgroundColor: #fff
color: #333
style: |
  section {
    font-family: 'Helvetica', sans-serif;
    font-size: 24px;
  }
  h1 {
    color: #1971c2;
  }
  h2 {
    color: #1864ab;
  }
  strong {
    color: #1971c2;
  }
---

<!-- _class: lead -->

# Automated Presentation Synthesis

## Architectural Patterns and Best Practices for LLM-Driven PowerPoint Generation

---

# Overview

The convergence of Large Language Models (LLMs) and programmatic document generation has fundamentally reshaped corporate communication.

**Key Topics:**
- Python ecosystem for PowerPoint automation
- LLM-to-JSON-to-PPTX architecture
- python-pptx technical deep dive
- Visual data integration
- Production considerations

---

# 1. The Paradigm Shift

**Historical Context:**
- VBA macros and COM automation (legacy)
- Direct XML manipulation of .pptx files
- Modern: GenAI integration for content synthesis

**The Challenge:**
- From "how to generate a file" to "how to generate meaningful content"
- Bridging content rendering and document manipulation

---

# 2. Python Libraries Landscape

**Four Primary Categories:**

| Category | Examples | Use Case |
|----------|----------|----------|
| Native Object Manipulation | python-pptx | Enterprise templates |
| Markdown Converters | Marp, Slidev | Rapid prototyping |
| Cloud APIs | Aspose.Slides | High-fidelity conversion |
| GenAI Wrappers | Various | AI-integrated workflows |

---

# python-pptx vs Marp

**python-pptx**
- ✅ Native PowerPoint objects
- ✅ Template support (Slide Masters)
- ✅ Native charts
- ❌ Steep learning curve
- ❌ No rendering engine

**Marp**
- ✅ Easy (Markdown-based)
- ✅ LLM-friendly
- ✅ Fast prototyping
- ❌ Limited editability
- ❌ Flattened layouts

---

# 3. python-pptx Object Model

**Hierarchy:**
```
Presentation
  └── Slide Masters
      └── Slide Layouts
          └── Slides
              └── Shapes
                  └── TextFrame
                      └── Paragraphs
                          └── Runs
```

**Key Insight:** Load existing templates rather than creating from scratch.

---

# Slide Layouts & Placeholders

**Best Practices:**
- Identify layouts by **name**, not index
- Use placeholders for consistent design
- Populate `slide.shapes.title` and `slide.placeholders`

**Placeholder Types:**
- Title, Body, Content
- Picture, Chart, Table
- Custom placeholders

---

# 4. The Golden Path Architecture

**LLM-to-JSON-to-PPTX Pipeline:**

```
LLM (Content) → JSON (Schema) → Python (Render) → PPTX
```

**Why this works:**
- Separates concerns: reasoning vs. rendering
- Enables validation with Pydantic
- Ensures template compliance
- Reduces hallucination risk

---

# Data Schema Design

**Pydantic Model Example:**

```python
class SlideContent(BaseModel):
    layout: str           # "Title and Content"
    title: str            # Headline
    body: List[str]       # Bullet points (max 5)
    speaker_notes: str    # Presenter script
    image_description: str # Image generation prompt
```

**Benefits:** Forces structured thinking, enables validation.

---

# Rendering Loop

1. **Load template** → Build layout map
2. **Validate JSON** → Pydantic model check
3. **Iterate slides** → For each slide:
   - Match layout by name
   - Populate title placeholder
   - Add paragraphs to body
   - Insert charts/images if specified

---

# 5. Prompt Engineering

**Effective System Prompt:**

> "You are a Senior Strategy Consultant. Synthesize complex information into high-impact, executive-level slides. Use **telegraphic style** (concise phrases, no full sentences)."

**Key Techniques:**
- Set quantitative limits (max 5 bullets, 15 words each)
- Chain-of-thought: outline first, then generate
- Use speaker notes for verbose explanations

---

# 6. Charts & Data Visualization

**Native Chart Creation:**

```python
chart_data = CategoryChartData()
chart_data.categories = ["Q1", "Q2", "Q3", "Q4"]
chart_data.add_series("2024", (100, 120, 140, 160))
slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    chart_data, x, y, w, h
)
```

**LLM Role:** Generate structured data, not visuals.

---

# Table Automation

**Workflow:**
1. LLM outputs 2D array: `[[headers], [row1], [row2]]`
2. Python creates table: `slide.shapes.add_table(rows, cols)`
3. Iterate and populate cells
4. Handle overflow with font heuristics

---

# 7. Media & Graphics

**Generative Images:**
- LLM generates `image_prompt`
- Call DALL-E/Midjourney API
- Download to BytesIO stream
- Insert via `placeholder.insert_picture()`

**Math Equations:**
- LLM outputs LaTeX: `$$f(x) = \int e^{-x} dx$$`
- Render with matplotlib to PNG
- Insert as picture

---

# 8. When to Use Which Tool?

| Use Case | Recommended Tool |
|----------|------------------|
| Corporate templates | python-pptx |
| Native editable charts | python-pptx |
| Quick developer summary | Marp |
| Code-heavy presentation | Marp |
| Collaborative editing | python-pptx |

---

# 9. Production Considerations

**Text Overflow Solutions:**
- Character limits with auto-split
- `MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE` flag

**Cost Optimization:**
- Tiered models: GPT-4o-mini for outline, GPT-4o for content
- Async image generation (parallel processing)

---

# Error Handling

**Validation Loop:**
```
LLM Output → Pydantic Validation
              ↓ (if fail)
    Feed error back to LLM → Retry
```

**Common Issues:**
- Missing fields
- Invalid layout names
- Malformed JSON

---

# 10. Future Directions

**Agentic Workflows:**
- Research agents (web browsing)
- Design agents (layout critique)
- Multi-modal AI integration

**Microsoft Copilot:**
- Great for interactive use
- Not viable for bulk/server-side generation

---

# 11. Key Takeaways

**✅ Use python-pptx for:**
- Enterprise applications
- Template compliance
- Native charts & editability

**✅ Architecture:**
- LLM → JSON → Python → PPTX
- Pydantic validation
- Template-based rendering

**✅ Visuals:**
- Native charts for data
- GenAI images for narrative
- Aspect ratio management

---

# Final Recommendations

1. **Library:** Standardize on python-pptx
2. **Architecture:** Strict JSON Schema with Pydantic
3. **Templates:** Always hydrate existing .pptx Masters
4. **Images:** Use placeholders for proper scaling
5. **Testing:** Validate all generated JSON before rendering

---

<!-- _class: lead -->

# Thank You

**Questions?**
