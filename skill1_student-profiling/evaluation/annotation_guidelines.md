# Gold Annotation Guidelines
# Student Profiling Skill — Evaluation

## Purpose

These guidelines define how to manually annotate student profiles for evaluating the extraction pipeline. Annotations serve as the gold standard for computing Precision, Recall, and F1 on the `skills`, `interests`, and `availability` fields.

---

## Annotation Task

For each student record (raw JSON), annotate:
1. `skills[]` — things the student **can do** (demonstrated ability or competence)
2. `interests[]` — things the student **wants to explore** (curiosity, passion, fascination)
3. `availability` — how available they are for research (`high` / `moderate` / `low`)

---

## Field Definitions

### skills[]

A skill is something the student **can do** — a demonstrated ability, competence, or technical capability.

**Include:**
- Academic/technical abilities implied by their major (e.g., Biochemistry → "laboratory techniques")
- Abilities explicitly mentioned in the story (e.g., "she designed posters" → "graphic design")
- Abilities implied by Unique Quality if it describes a competence (e.g., "Graphic design guru" → "graphic design")
- Abilities implied by hobbies if they require skill (e.g., "programming" → "software development")

**Exclude:**
- Personality traits ("natural leader", "hard worker")
- Generic terms ("research", "learning", "communication")
- Things they want to do but haven't done yet

**Format:** lowercase, 1–4 words, specific enough to match a research domain
- Good: "laboratory techniques", "graphic design", "data analysis"
- Bad: "science", "art", "things"

**Count:** 3–8 skills per profile

---

### interests[]

An interest is something the student **wants to explore** — a topic they are curious about, passionate about, or fascinated by.

**Include:**
- Hobbies (always count as interests)
- Topics explicitly described as passions/fascinations in the story
- Research areas implied by Unique Quality if it describes a passion (e.g., "Wildlife conservationist" → "wildlife conservation")
- Topics the student is "dedicated to" or "committed to"

**Note:** A topic can be both a skill AND an interest simultaneously (e.g., photography can be both)

**Format:** lowercase, 1–4 words
- Good: "wildlife conservation", "photography", "astronomy"
- Bad: "nature", "things", "the world"

**Count:** 2–8 interests per profile

---

### availability

How available is this student for research engagement?

| Value | Criteria |
|-------|----------|
| `high` | Freshman/Sophomore with no major time constraints; OR any year actively seeking research/internship opportunities |
| `moderate` | Junior/Senior with normal workload; OR student with some constraints (busy schedule, part-time job) but no graduation plans |
| `low` | Senior with job offer accepted, graduation plans, or explicitly moving away; OR student with severe time constraints |

**Default:** When uncertain, use `moderate`

---

## Annotation Process

### Step 1: Read the full record
Read Name, Major, Year, GPA, Hobbies, Unique Quality, and Story.

### Step 2: Annotate skills
1. Start with Major → what academic skills does this major imply? (3–4 terms)
2. Check Unique Quality → does it describe a skill? Add 1–2 terms if yes
3. Check Story → any explicit skill demonstrations? Add 0–3 terms
4. Check Hobbies → do any require technical skill? Add 0–1 terms

### Step 3: Annotate interests
1. Start with Hobbies → always add as interests (2 terms)
2. Check Unique Quality → does it describe a passion/interest? Add 1–2 terms if yes
3. Check Story → any explicit passions/fascinations? Add 0–3 terms

### Step 4: Annotate availability
1. Check Year → Freshman/Sophomore = lean high; Junior = lean moderate; Senior = lean moderate
2. Check Story for signals:
   - Job offer accepted / moving after graduation → `low`
   - "busy schedule" / "juggling" / part-time job → one level down
   - "eager to learn" / "seeking research" / "looking for opportunities" → one level up

---

## Example Annotation

**Record:**
```json
{
  "Name": "Nancy Brown",
  "Major": "Archaeology",
  "Year": "Sophomore",
  "GPA": 3.44,
  "Hobbies": ["dancing", "bouldering"],
  "Unique Quality": "Graphic design guru",
  "Story": "Nancy was fascinated by the history of her hometown. She designed posters for the university archaeology exhibition. Her professor recommended her for an internship at a local museum."
}
```

**Gold annotation:**
```json
{
  "student_id": "nancy-brown-00002",
  "skills": ["field excavation", "artifact analysis", "historical research", "spatial data analysis", "graphic design"],
  "interests": ["dancing", "bouldering", "archaeology", "history"],
  "availability": "high"
}
```

**Reasoning:**
- Skills: Archaeology major → 4 taxonomy skills; "Graphic design guru" → "graphic design"; "designed posters" corroborates
- Interests: Hobbies → dancing, bouldering; "fascinated by history" → archaeology, history
- Availability: Sophomore + internship opportunity → high

---

## Sampling Strategy (50 records)

Stratified by Year (12–13 per year) and signal density:
- **Research-rich** (4–5 per year): Story has explicit research/project signals
- **Mixed** (4–5 per year): Story has some signals but mostly narrative
- **Hobby-focused** (4–5 per year): Story is mostly about hobbies/personal life

---

## Output Format

Save annotations as `evaluation/gold_annotations.json`:

```json
[
  {
    "student_id": "nancy-brown-00002",
    "skills": ["field excavation", "artifact analysis", "historical research", "spatial data analysis", "graphic design"],
    "interests": ["dancing", "bouldering", "archaeology", "history"],
    "availability": "high",
    "annotator_notes": "optional notes"
  },
  ...
]
```

---

## Inter-Annotator Agreement (if 2 annotators)

- **Skills/Interests**: Jaccard similarity = |A ∩ B| / |A ∪ B| (target: > 0.5)
- **Availability**: Cohen's kappa (target: > 0.6)

If agreement is low on a record, discuss and reach consensus before finalizing.
