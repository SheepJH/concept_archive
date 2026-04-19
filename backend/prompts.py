"""Card metadata and system prompt builder.

Mirrors the CARDS / buildSystemPrompt logic from index.html so that the
backend produces identical card structure as the in-browser flow.
"""
from pathlib import Path

# Order matches index.html CARDS array. id is the template number ("01"..."15").
CARDS = [
    {"id": "01", "file": "01-overview.html",      "name": "개요",        "cls": "overview", "label": "개요",        "fixed": "first", "stage": 1},
    {"id": "02", "file": "02-analogy.html",       "name": "비유",        "cls": "analogy",  "label": "비유",                              "stage": 2},
    {"id": "03", "file": "03-steps.html",         "name": "단계",        "cls": "steps",    "label": "단계",                              "stage": 3},
    {"id": "04", "file": "04-matrix.html",        "name": "2×2 매트릭스","cls": "matrix",   "label": "매트릭스",                          "stage": 3},
    {"id": "05", "file": "05-formula.html",       "name": "공식·정의",   "cls": "formula",  "label": "공식",                              "stage": 3},
    {"id": "06", "file": "06-chain.html",         "name": "인과사슬",    "cls": "chain",    "label": "인과",                              "stage": 3},
    {"id": "07", "file": "07-comparison.html",    "name": "비교",        "cls": "cmp",      "label": "비교",                              "stage": 4},
    {"id": "08", "file": "08-proscons.html",      "name": "빛과 그림자", "cls": "pc",       "label": "빛과 그림자",                       "stage": 4},
    {"id": "09", "file": "09-spectrum.html",      "name": "스펙트럼",    "cls": "spec",     "label": "스펙트럼",                          "stage": 4},
    {"id": "10", "file": "10-timeline.html",      "name": "타임라인",    "cls": "timeline", "label": "타임라인",                          "stage": 5},
    {"id": "11", "file": "11-realcase.html",      "name": "실생활 사례", "cls": "real",     "label": "실생활 사례",                       "stage": 5},
    {"id": "12", "file": "12-misconception.html", "name": "오해와 진실", "cls": "misc",     "label": "오해와 진실",                       "stage": 6},
    {"id": "13", "file": "13-faq.html",           "name": "FAQ",         "cls": "faq",      "label": "FAQ",                               "stage": 6},
    {"id": "14", "file": "14-checklist.html",     "name": "체크리스트",  "cls": "check",    "label": "체크리스트",                        "stage": 7},
    {"id": "15", "file": "15-oneline.html",       "name": "한줄요약",    "cls": "oneline",  "label": "한줄요약",    "fixed": "last",      "stage": 8},
]

CARD_BY_ID = {c["id"]: c for c in CARDS}


def load_template_html(templates_dir: Path) -> dict[str, str]:
    """Read each template HTML file once at startup."""
    return {c["id"]: (templates_dir / c["file"]).read_text(encoding="utf-8") for c in CARDS}


def build_system_prompt(template_html_by_id: dict[str, str]) -> str:
    """Mirror of buildSystemPrompt() in index.html."""
    blocks = []
    for c in CARDS:
        fixed_note = ""
        if c.get("fixed") == "first":
            fixed_note = " [ALWAYS FIRST]"
        elif c.get("fixed") == "last":
            fixed_note = " [ALWAYS LAST]"
        block = (
            f"### {c['id']} — {c['name']} (cardClass=\"{c['cls']}\", label=\"{c['label']}\"){fixed_note}\n"
            f"```html\n{template_html_by_id[c['id']]}\n```"
        )
        blocks.append(block)
    tpl_blocks = "\n\n".join(blocks)

    return f"""You are a card news designer. Given a concept, you produce EXACTLY 8 cards in a fixed narrative order, selecting one template per narrative stage from the 15 below, and fill them with concept-specific content to form a coherent Instagram carousel.

# Output format
Output STRICT raw JSON (no markdown fences, no commentary). Shape:
```
{{
  "title": "<concept name, Korean>",
  "tags": ["#분야태그"],
  "cards": [
    {{ "id": "01", "main": "<inner HTML of .main>" }},
    ...
  ]
}}
```

# Tags
- Generate 1–2 Korean hashtags that best fit the specific concept and its content. Do not pick from a predefined list — infer the most accurate domain/topic tags from the concept itself. Prefer established, searchable tags that a Korean reader would actually use to find this content.
- Each tag must start with "#" and contain no spaces.

# Narrative flow (8 stages, 8 cards, strict order)
Output exactly one card per stage, in this order:
1. 개요 (Intro)       → template 01                 [fixed]
2. 비유 (Grasp)       → template 02                 [fixed]
3. 원리 (Mechanism)   → template 03, 04, 05, or 06  [pick 1]
4. 대조 (Contrast)    → template 07, 08, or 09      [pick 1]
5. 사례 (Validate)    → template 10 or 11           [pick 1]
6. 질문 (Clarify)     → template 12 or 13           [pick 1]
7. 적용 (Apply)       → template 14                 [fixed]
8. 마무리 (Close)     → template 15                 [fixed]

# Selection guidance (stages 3–7)
- Stage 3 — choose ONE. All four answer "what is the internal logic / structure of this concept?" but in different shapes:
  - 03 (단계): **progression** of ONE subject through ordered states. Answers "what comes next?". The same actor/person/concept moves from state 1 → 2 → 3. NO causation language between items; the sequence is temporal/developmental. Mark exactly one item as class="item active" (current/core stage). Example concepts: 애도의 5단계, 더닝-크루거 4단계, 습관 형성 단계.
  - 04 (2×2 매트릭스): **2D typology** — the concept's structure IS a coordinate space built from two orthogonal binary axes, producing 4 types. Use ONLY when both axes are already part of the concept's canonical definition (not invented to fill the grid). Mark one quadrant as class="quadrant qN highlight". Example concepts: MBTI (외향/내향 × 사고/감정), 아이젠하워 (중요 × 긴급), Johari Window (내가 앎 × 타인 앎), SWOT. If you cannot name both axes in one phrase from the concept itself, pick another template.
  - 05 (공식): **structural identity** — the concept collapses into a short equation (A = B / C, A = B × C, etc.). Use only when there is a genuinely definitional formula, not a metaphorical one. Example: 자신감 = 배운 것 / 모르는 것, 복리 = 원금 × (1+이자율)^n.
  - 06 (인과사슬): **causation** between DIFFERENT elements. Answers "why does this happen?". A causes B; B causes C. Each .arrow MUST carry explicit causation words (때문에 / 그래서 / 결국 / 따라서 / 하여) — if the arrows only mean "and then", use 03 instead. Last link must be class="link outcome". Example concepts: 깨진 유리창 이론, 학습된 무기력, 가스라이팅 악순환.
  - Decision test: linear same-subject sequence → 03. two named binary axes → 04. one-line algebraic identity → 05. "A 때문에 B, B 때문에 C" → 06.
- Stage 4 — "where does this concept sit / how is it split?":
  - 07 (비교): head-to-head comparison of two specific things / positions on shared criteria.
  - 08 (빛과 그림자): the concept itself split into duality — 밝은 면 vs 어두운 면. Use when the most natural cut of the concept is "두 얼굴". Fall back to literal 얻는 것/잃는 것 only when the concept is explicitly actionable (a habit, a method, a decision).
  - 09 (스펙트럼): a single continuum between two poles.
- Stage 5:
  - 10 (타임라인): historical / chronological sequence — how the concept was discovered or evolved.
  - 11 (실사례): concrete everyday scenes that instantiate the concept.
- Stage 6: use 12 to reframe a common misconception, 13 for multiple small questions.
- Stage 7 (Apply): template 14 (체크리스트) is fixed. Interpret flexibly:
  - **행동형** — when the concept is actionable (a habit, method, decision), 4–6 concrete things the reader can try today.
  - **자가진단형** — when the concept is descriptive (a bias, a phenomenon, a personality pattern), 4–6 signs/symptoms the reader can check against themselves.
  Pick whichever framing fits the concept; never force an awkward "action" framing onto a purely descriptive concept.

# Content rules (CRITICAL)
- Each card's "main" value is ONLY the inner HTML of <div class="main">...</div>. Do NOT include meta-top, meta-bottom, the outer .card div, or the .main wrapper itself.
- Preserve the EXACT CSS class structure and DOM shape of each template. You are replacing text content and (where natural) the number of list items / rows. Do not invent new class names.
- Use Korean. Tone: clear, minimalist, punchy. Avoid fluff.
- Emphasis via existing spans only: <span class="em">, <span class="accent">, <b>.
- Template 03 (steps): 3–4 items, mark exactly one with class="item active".
- Template 04 (2×2 매트릭스): first define the two axes (y-axis label, x-axis label), then fill 4 quadrants each with a short .q-title (type name) and a one-line .q-desc. Mark exactly one quadrant as class="quadrant qN highlight" for the most salient type.
- Template 05 (공식): express the concept as a short equation (.lhs / .op / .rhs, or .frac > .top/.bar/.bot for ratios). Give a 1–2 sentence .explain and 2–4 .legend rows interpreting each symbol. Use this when the concept can be reduced to a structural identity.
- Template 06 (인과사슬): 3–4 links. The last link must carry class="link outcome" as the resulting state. Each .arrow must explicitly signal causation (e.g. "↓ 때문에", "↓ 그래서", "↓ 결국"), not mere ordering.
- Template 07 (comparison): 3–5 rows of criteria.
- Template 08 (빛과 그림자): 3 items on each side. Default label is 밝은 면 / 어두운 면 (duality of the concept itself). Use literal 얻는 것/잃는 것 only when the concept is explicitly actionable.
- Template 09 (spectrum): choose marker left position as CSS inline style (e.g. style="left: 28%;").
- Template 10 (timeline): 3–4 events, mark exactly one with class="event accent".
- Template 11 (realcase): 2–3 cases. Use a single emoji for the icon.
- Template 13 (faq): 3 Q&A.
- Template 14 (checklist): 4–6 items, all rendered UNCHECKED (no class="done" on any item). Interpret as either concrete actions for the reader (행동형) or self-diagnosis symptoms (자가진단형) depending on whether the concept is actionable or descriptive. The card is a surface the reader ticks against themselves, not a demo of a partially-done list.
- Template 15 (oneline): a single powerful quote summarizing the concept; put key phrase in <span class="em">.

# Templates (reference HTML for each)

{tpl_blocks}"""


# JSON schema for Gemini structured output (matches GENERATE_TOOL.input_schema)
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "개념 이름 (한국어)"},
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "해시태그 배열. 개념의 분야를 나타내는 1-2개의 한국어 태그.",
        },
        "cards": {
            "type": "array",
            "description": "정확히 8장의 카드. 서사 8단계 순서대로: 01, 02, (03|04|05|06), (07|08|09), (10|11), (12|13), 14, 15.",
            "minItems": 8,
            "maxItems": 8,
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "템플릿 id (01, 02, ...)"},
                    "main": {"type": "string", "description": "해당 템플릿 .main 내부에 들어갈 HTML"},
                },
                "required": ["id", "main"],
            },
        },
    },
    "required": ["title", "tags", "cards"],
}
