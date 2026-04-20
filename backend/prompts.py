"""Card metadata and system prompt builder.

Mirrors the CARDS / buildSystemPrompt logic from index.html so that the
backend produces identical card structure as the in-browser flow.

Metadata is loaded from templates/manifest.json (Single Source of Truth).
"""
import json
from pathlib import Path


def load_manifest(templates_dir: Path) -> dict:
    """Load templates/manifest.json. Returns dict with 'cards' and 'stages'."""
    data = json.loads((templates_dir / "manifest.json").read_text(encoding="utf-8"))
    validate_manifest(data)
    return data


def validate_manifest(manifest: dict) -> None:
    """Fail fast on misconfiguration: missing stages, fixed stages with !=1 card."""
    cards = manifest["cards"]
    stages = manifest["stages"]
    stage_nums = {s["num"] for s in stages}
    for c in cards:
        if c["stage"] not in stage_nums:
            raise ValueError(f"card {c['id']} references unknown stage {c['stage']}")
    for s in stages:
        ids = [c["id"] for c in cards if c["stage"] == s["num"]]
        if not ids:
            raise ValueError(f"stage {s['num']} ({s['name']}) has no cards")
        if s["policy"] == "fixed" and len(ids) != 1:
            raise ValueError(
                f"stage {s['num']} ({s['name']}) has policy=fixed but {len(ids)} cards: {ids}"
            )


def load_template_html(templates_dir: Path, cards: list[dict]) -> dict[str, str]:
    """Read each template HTML file once at startup."""
    return {c["id"]: (templates_dir / c["file"]).read_text(encoding="utf-8") for c in cards}


def build_narrative_flow(cards: list[dict], stages: list[dict]) -> str:
    """Generate the 'X. name (Intent) → template ids [mark]' lines from manifest."""
    lines = []
    for s in stages:
        ids = [c["id"] for c in cards if c["stage"] == s["num"]]
        if s["policy"] == "fixed":
            mark = "[fixed]"
            if len(ids) == 1:
                target = f"template {ids[0]}"
            else:
                target = f"template {' or '.join(ids)}"
        else:
            mark = "[pick 1]"
            if len(ids) == 1:
                target = f"template {ids[0]}"
            elif len(ids) == 2:
                target = f"template {ids[0]} or {ids[1]}"
            else:
                target = f"template {', '.join(ids[:-1])}, or {ids[-1]}"
        lines.append(f"{s['num']}. {s['name']} ({s['intent']})  → {target}  {mark}")
    return "\n".join(lines)


def build_system_prompt(
    template_html_by_id: dict[str, str],
    cards: list[dict],
    stages: list[dict],
) -> str:
    """Mirror of buildSystemPrompt() in index.html."""
    first_stage_num = stages[0]["num"]
    last_stage_num = stages[-1]["num"]

    blocks = []
    for c in cards:
        fixed_note = ""
        # Preserve legacy FIRST/LAST markers for cards sitting alone in the
        # first/last stage (which must be policy=fixed by validation).
        stage_policy = next(s["policy"] for s in stages if s["num"] == c["stage"])
        if stage_policy == "fixed":
            if c["stage"] == first_stage_num:
                fixed_note = " [ALWAYS FIRST]"
            elif c["stage"] == last_stage_num:
                fixed_note = " [ALWAYS LAST]"
        block = (
            f"### {c['id']} — {c['name']} (cardClass=\"{c['cls']}\", label=\"{c['label']}\"){fixed_note}\n"
            f"```html\n{template_html_by_id[c['id']]}\n```"
        )
        blocks.append(block)
    tpl_blocks = "\n\n".join(blocks)

    total_cards = len(stages)
    total_templates = len(cards)
    narrative_flow = build_narrative_flow(cards, stages)

    return f"""You are a card news designer. Given a concept, you produce EXACTLY {total_cards} cards in a fixed narrative order, selecting one template per narrative stage from the {total_templates} below, and fill them with concept-specific content to form a coherent Instagram carousel.

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

# Narrative flow ({total_cards} stages, {total_cards} cards, strict order)
Output exactly one card per stage, in this order:
{narrative_flow}

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
            "description": "정확히 8장의 카드. 서사 8단계 순서대로: 01, 02, (03|04|05|06), (07|08|09), (10|11), 13, 14, 15.",
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
