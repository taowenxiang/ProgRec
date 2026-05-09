#!/usr/bin/env python3
"""
Regenerate synthetic CS faculty corpus (~200 mentors) plus aligned graph seeds.

Inspired by typical North American faculty pages (research group overview, themes,
student expectations, recent directions). Run from repo root:

  python3 scripts/generate_mentor_pool.py

References (style): public faculty research blurbs such as Stanford SAIL / VT CS /
Northeastern Khoury faculty pages — content here is fully synthetic and not copied.
"""

from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path

RNG_SEED = 42
NUM_MENTORS = 200

_REPO = Path(__file__).resolve().parents[1]
_SEEDS = _REPO / "data" / "seeds"


def _wcsv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


FIRST_NAMES = [
    "James",
    "Emily",
    "Michael",
    "Priya",
    "Daniel",
    "Mei",
    "Olivia",
    "Carlos",
    "Hannah",
    "Arjun",
    "Sophia",
    "Ethan",
    "Yuki",
    "Noah",
    "Amelia",
    "Diego",
    "Fatima",
    "Lucas",
    "Rachel",
    "Henry",
    "Ava",
    "Benjamin",
    "Zara",
    "Matthew",
    "Chloe",
    "Andrew",
    "Nina",
    "Ryan",
    "Sofia",
    "William",
    "Isabella",
    "Thomas",
    "Maya",
    "David",
    "Elena",
    "Joseph",
    "Leah",
    "Christopher",
    "Grace",
    "Kevin",
    "Victoria",
    "Brian",
    "Harper",
    "Jonathan",
    "Camila",
    "Stephen",
    "Anna",
    "Eric",
    "Naomi",
    "Joshua",
    "Maria",
    "Jason",
    "Angela",
    "Justin",
    "Rosa",
    "Aaron",
    "Claire",
    "Brandon",
    "Julia",
    "Tyler",
    "Alice",
    "Jordan",
    "Sara",
    "Peter",
    "Keiko",
    "Samuel",
    "Layla",
    "Gregory",
    "Nadia",
    "Charles",
    "Brooke",
]

LAST_NAMES = [
    "Bennett",
    "Park",
    "Nguyen",
    "Patel",
    "Rodriguez",
    "Kim",
    "Martinez",
    "Singh",
    "Johnson",
    "Li",
    "Anderson",
    "Brown",
    "Garcia",
    "Lee",
    "Wilson",
    "Chen",
    "Taylor",
    "Gupta",
    "Moore",
    "Wright",
    "Scott",
    "Clark",
    "Lewis",
    "Walker",
    "Hall",
    "Young",
    "Allen",
    "King",
    "Wright",
    "Green",
    "Baker",
    "Adams",
    "Nelson",
    "Hill",
    "Campbell",
    "Rivera",
    "Collins",
    "Murphy",
    "Rogers",
    "Cook",
    "Morgan",
    "Bell",
    "Bailey",
    "Cooper",
    "Richardson",
    "Cox",
    "Howard",
    "Ward",
    "Torres",
    "Peterson",
    "Ramirez",
    "James",
    "Watson",
    "Brooks",
    "Kelly",
    "Sanders",
    "Price",
    "Wood",
    "Ross",
    "Hughes",
    "Butler",
    "Simmons",
    "Foster",
    "Gonzalez",
    "Bryant",
    "Alexander",
    "Russell",
    "Griffin",
    "West",
    "Cole",
    "Hayes",
    "Chavez",
    "Gibson",
    "Ellis",
    "Tran",
    "Owens",
    "Perry",
    "Powell",
    "Long",
    "Jenkins",
]

DEPTS = [
    "Department of Computer Science",
    "Department of Electrical Engineering & Computer Science",
    "School of Computer Science",
    "Department of Computer & Information Science",
    "Department of Computing",
    "College of Computing & Informatics",
    "Department of Computer Science & Engineering",
]

TRACK_ORDER = [
    ("ml_ai", 48),
    ("cv", 30),
    ("nlp", 30),
    ("systems", 32),
    ("theory_algo", 30),
    ("security", 18),
    ("hci", 12),
]

SHARED_PARAS = [
    (
        "The group actively participates in department reading groups, artifact reviews, and undergraduate research "
        "symposia so students experience the social norms of scientific criticism—not only isolated coding tasks."
    ),
    (
        "Collaborations extend to neighboring engineering departments, clinics, libraries, and civic partners when "
        "projects require domain expertise; students are expected to document assumptions gathered from stakeholders."
    ),
    (
        "Funding mixes federal grants, industry partnerships, and internal fellowships; undergraduates may contribute "
        "to grant reporting artifacts, milestones, and reproducibility supplements when appropriate."
    ),
    (
        "Software stewardship matters: repositories include contribution guidelines, pinned environments, and archived "
        "experiment snapshots so future students can continue rather than restart."
    ),
    (
        "The lab maintains explicit policies on authorship credit, noting that meaningful intellectual contributions—not "
        " merely routine engineering—guide ordering conversations."
    ),
    (
        "Community norms emphasize kindness rigor: critiques target claims and methods, not individuals; disagreement "
        "is modeled as a productive part of research meetings."
    ),
    (
        "Students are encouraged to present at internal seminars before external deadlines, practicing clarity under "
        "questions from faculty outside their immediate specialty."
    ),
    (
        "Where feasible, projects publish negative results, ablation catalogs, and limitation sections that later cohorts "
        "can build upon without repeating dead ends."
    ),
    (
        "International readers are considered default: documentation strives for precise terminology, neutral examples, "
        "and careful handling of culturally sensitive applications."
    ),
    (
        "Career mentoring includes guidance on graduate school timing, portfolio construction, and translating research "
        "experience into interviews—without guaranteeing outcomes."
    ),
    (
        "Accessibility is treated as an engineering constraint: interfaces, tutorial videos, and written instructions "
        "aim for inclusive defaults rather than retrofits."
    ),
    (
        "The lab tracks emerging ethics guidance from professional societies and updates study protocols when norms evolve."
    ),
    (
        "When hardware dependencies arise, students learn budgeting basics, cluster etiquette, and carbon-aware "
        "experiment planning as part of responsible systems citizenship."
    ),
    (
        "Outreach includes mentoring novice programmers in adjacent majors when projects demand interdisciplinary teams."
    ),
    (
        "Alumni stay loosely connected through shared Slack archives and annual reunions; returning visitors often "
        "co-advise capstone threads tied to earlier codebases."
    ),
]


def _compose_track_profile(rng: random.Random, track: str, name: str, lab: str) -> dict[str, object]:
    """Return rich English fields for one mentor."""
    pools = TRACK_COPY[track]
    opening = rng.choice(pools["openings"]).format(name=name, lab=lab)
    methods = rng.choice(pools["methods"])
    applications = rng.choice(pools["applications"])
    challenges = rng.choice(pools["challenges"])
    mentoring = rng.choice(pools["mentoring"]).format(name=name)
    teaching = rng.choice(pools["teaching"])
    roadmap = rng.choice(pools["roadmap"])
    extra = " ".join(rng.sample(SHARED_PARAS, k=rng.randint(2, 3)))
    profile_text = " ".join(
        [opening, methods, applications, challenges, mentoring, teaching, roadmap, extra]
    )
    research_areas = rng.sample(pools["areas"], k=min(len(pools["areas"]), rng.randint(3, 5)))
    keywords = rng.sample(pools["keywords"], k=min(len(pools["keywords"]), rng.randint(6, 10)))
    required_skills = rng.sample(pools["skills"], k=min(len(pools["skills"]), rng.randint(3, 6)))
    preferred_background = rng.choice(pools["preferred"])
    experience_summary = rng.choice(pools["experience"]).format(name=name, lab=lab)
    advising_style = rng.choice(pools["advising_style"])
    weekly = rng.choice(pools["weekly"])
    lab_focus = rng.choice(pools["lab_focus"]).format(lab=lab)
    return {
        "research_areas": research_areas,
        "keywords": keywords,
        "profile_text": profile_text,
        "required_skills": required_skills,
        "preferred_background": preferred_background,
        "experience_summary": experience_summary,
        "advising_style": advising_style,
        "weekly_time_expectation": weekly,
        "lab_focus": lab_focus,
    }


TRACK_COPY: dict[str, dict[str, list[str]]] = {}

TRACK_COPY["ml_ai"] = {
    "lab_names": [
        "{last} Lab for Adaptive ML",
        "Laboratory for Reliable Learning",
        "{last} Research Group on Decision Systems",
        "Center-scale ML Research Studio ({last})",
    ],
    "areas": [
        "machine learning foundations",
        "deep representation learning",
        "probabilistic modeling",
        "trustworthy ML",
        "learning from weak supervision",
        "optimization for large models",
        "dataset and benchmark design",
        "evaluation methodology",
        "generative modeling",
        "self-supervised learning",
        "sequential decision making",
        "interpretability and auditing",
    ],
    "keywords": [
        "PyTorch",
        "JAX",
        "diffusion models",
        "transformers",
        "variational inference",
        "uncertainty estimation",
        "robustness",
        "dataset curation",
        "causal ML",
        "RLHF",
        "benchmarking",
        "representation geometry",
        "learning theory hooks",
        "large-scale training",
        "efficient finetuning",
        "model merging",
        "latent variable models",
        "graph representation learning",
        "equivariance",
        "information bottleneck",
    ],
    "skills": [
        "Python",
        "linear algebra",
        "probability",
        "multivariate calculus",
        "PyTorch or JAX",
        "LaTeX",
        "scientific writing",
        "experiment tracking",
        "Unix tooling",
        "basic systems literacy",
    ],
    "preferred": [
        "Strong programming maturity and careful experimental habits; comfortable reading NeurIPS/ICML-style papers and reproducing baselines.",
        "Prior coursework in ML + algorithms; interest in either theory-backed empirical work or careful systems-aware ML research.",
        "Students who can translate vague ideas into measurable hypotheses, document failures, and iterate with statistical discipline.",
    ],
    "openings": [
        (
            "Dr. {name} leads the {lab} and studies learning algorithms that remain reliable when data are biased, "
            "partially labeled, or collected under shifting conditions."
        ),
        (
            "Dr. {name} directs the {lab}, focusing on representation learning pipelines where scale, compute budgets, "
            "and evaluation integrity must be co-designed rather than treated as afterthoughts."
        ),
        (
            "Dr. {name} runs the {lab} with an emphasis on empirical ML that still respects identifiability constraints, "
            "proper ablations, and honest reporting of negative results."
        ),
    ],
    "methods": [
        (
            "Methodologically, the group combines modern deep architectures with careful probabilistic framing, "
            "stress-testing claims through synthetic controls and targeted interventions rather than leaderboard chasing alone."
        ),
        (
            "The research program mixes large-scale training insights with smaller diagnostic studies that isolate "
            "failure modes in optimization, generalization, or calibration."
        ),
        (
            "Recent technical themes include structured latent variables, representation alignment under distribution shift, "
            "and practical tooling for reproducible experimentation."
        ),
    ],
    "applications": [
        (
            "Application targets span scientific computing assistants, decision-support tools, and safety-critical "
            "settings where uncertainty communication matters as much as raw accuracy."
        ),
        (
            "The lab collaborates with campus partners on climate modeling workflows, biomedical signal pipelines, "
            "and education technologies where data governance is non-negotiable."
        ),
        (
            "Impact is pursued through open benchmarks, reference implementations, and documentation aimed at lowering "
            "the barrier for responsible adoption."
        ),
    ],
    "challenges": [
        (
            "A recurring challenge is separating incidental correlations from stable mechanisms—students are encouraged "
            "to treat surprising gains as hypotheses that demand mechanism-level scrutiny."
        ),
        (
            "The group invests heavily in measurement: defining tasks beyond single-number scores, auditing slices, "
            "and studying intervention sensitivity."
        ),
        (
            "Another emphasis is compute-aware research: understanding when scaling helps, when it obscures bugs, "
            "and how to prioritize experiments under deadline pressure."
        ),
    ],
    "mentoring": [
        (
            "Undergraduate researchers typically begin with reproduction and auditing tasks, then graduate to proposing "
            "extensions; Dr. {name} prioritizes weekly technical checkpoints and written milestone notes."
        ),
        (
            "Mentorship emphasizes readable code, experiment manifests, and crisp writeups—skills that transfer regardless "
            "of whether a project ends in a publication or a strong technical report."
        ),
    ],
    "teaching": [
        (
            "Teaching interfaces include graduate seminars on probabilistic ML and undergraduate courses that foreground "
            "debugging culture and scientific communication."
        ),
        (
            "Course connections emphasize bridging mathematical intuition with hands-on labs that mirror research workflows."
        ),
    ],
    "roadmap": [
        (
            "Near-term directions include richer evaluation for generative systems, improved protocols for human-in-the-loop "
            "supervision, and tooling that makes robust experimentation teachable—not only feasible for experts."
        ),
        (
            "Students interested in interdisciplinary projects should expect to spend time understanding domain constraints "
            "before proposing model changes."
        ),
    ],
    "experience": [
        (
            "{name} has published extensively in top ML venues; the {lab} routinely releases artifacts and participates "
            "in community benchmarking efforts."
        ),
        (
            "{name} advises thesis work spanning theory-informed empirical ML and applied collaborations; alumni have "
            "joined both academic labs and industry research teams."
        ),
    ],
    "advising_style": [
        "Structured weekly meetings with rolling agendas; prefers shared notebooks and documented experiment plans.",
        "Hands-on debugging sessions early in a project, transitioning to student-led ownership after Milestone 1.",
        "Explicit expectations around timelines, risk disclosure, and proactive communication when experiments stall.",
    ],
    "weekly": [
        "Expect ~10–14 focused hours/week during steady semesters; heavier spikes near deadlines are avoided via earlier checkpoints.",
        "Expect ~8–12 hours/week for coursework-heavy terms, with flexible scheduling around exams.",
        "Expect ~12–16 hours/week when approaching a submission-quality milestone (by mutual agreement).",
    ],
    "lab_focus": [
        "{lab} emphasizes reproducible ML research with measurable claims and collaborative tooling.",
        "{lab} balances ambitious modeling ideas with mundane-but-critical validation discipline.",
    ],
}

TRACK_COPY["cv"] = {
    "lab_names": [
        "{last} Vision & Perception Lab",
        "Imaging Intelligence Group ({last})",
        "{last} Lab for 3D Understanding",
    ],
    "areas": [
        "computer vision",
        "3D reconstruction",
        "video understanding",
        "robust perception",
        "efficient vision models",
        "sensor fusion",
        "visual reasoning",
        "dataset bias mitigation",
    ],
    "keywords": [
        "PyTorch",
        "OpenCV",
        "NeRF",
        "diffusion",
        "detection",
        "segmentation",
        "self-supervised vision",
        "domain adaptation",
        "multi-view geometry",
        "transformers for vision",
        "real-time inference",
        "annotation pipelines",
    ],
    "skills": [
        "Python",
        "linear algebra",
        "multivariate calculus",
        "PyTorch",
        "basic C++ (optional)",
        "camera geometry intuition",
        "data hygiene",
    ],
    "preferred": [
        "Strong linear algebra and comfort with probability; willingness to build data pipelines and sanity-check visual outputs.",
        "Prior exposure to CV coursework or robotics perception; interest in both modeling and evaluation protocols.",
    ],
    "openings": [
        (
            "Dr. {name} leads the {lab}, developing perception models that remain dependable across lighting, sensor noise, "
            "and deployment constraints common in mobile and robotics settings."
        ),
        (
            "Dr. {name} directs the {lab} with a focus on 3D scene understanding, integrating learning-based inference "
            "with geometric priors when they are trustworthy."
        ),
    ],
    "methods": [
        (
            "The group combines modern representation learning with classical geometry and careful dataset audits; "
            "students learn to question shortcuts like overly tidy benchmarks."
        ),
        (
            "Method work spans efficient architectures, training curricula, and post-training calibration for deployed stacks."
        ),
    ],
    "applications": [
        (
            "Applications include assistive technologies, autonomous systems research platforms, and scientific imaging "
            "where interpretability and failure visibility matter."
        ),
    ],
    "challenges": [
        (
            "Key challenges include domain shift, label noise, and defining realistic evaluation scenarios beyond curated sets."
        ),
    ],
    "mentoring": [
        (
            "Undergraduates often begin by reproducing baselines on internal datasets, then implement diagnostics "
            "(slice analysis, failure clustering); Dr. {name} emphasizes milestone demos."
        ),
    ],
    "teaching": [
        (
            "Teaching bridges classical vision with contemporary deep learning labs emphasizing debugging and visualization."
        ),
    ],
    "roadmap": [
        (
            "Near-term directions include robust multimodal perception, efficient training for edge devices, "
            "and evaluation tooling for long-tail behaviors."
        ),
    ],
    "experience": [
        "{name} publishes in CVPR/ICCV-style venues; {lab} regularly releases datasets and reference training scripts.",
    ],
    "advising_style": [
        "Biweekly deep dives plus asynchronous code review; prefers demo-driven progress checks.",
    ],
    "weekly": [
        "Expect ~10–14 hours/week depending on dataset construction phases.",
    ],
    "lab_focus": [
        "{lab} focuses on perception stacks where visual correctness must be validated, not assumed.",
    ],
}

TRACK_COPY["nlp"] = {
    "lab_names": [
        "{last} Language Technologies Group",
        "{last} Lab for Grounded NLP",
    ],
    "areas": [
        "natural language processing",
        "structured language understanding",
        "alignment and evaluation",
        "multilingual modeling",
        "retrieval-augmented systems",
        "human-centered NLP",
    ],
    "keywords": [
        "transformers",
        "tokenization",
        "evaluation suites",
        "hallucination mitigation",
        "summarization",
        "information extraction",
        "speech-text interfaces",
        "dataset documentation",
        "benchmark contamination",
        "prompting protocols",
    ],
    "skills": [
        "Python",
        "PyTorch",
        "probability",
        "linguistics basics (helpful)",
        "scientific writing",
        "data annotation literacy",
    ],
    "preferred": [
        "Comfortable reading ACL-style papers; cares about evaluation design and responsible deployment narratives.",
        "Interest in either modeling or tooling for reproducible NLP experiments.",
    ],
    "openings": [
        (
            "Dr. {name} leads the {lab}, focusing on language technologies where grounding, attribution, and evaluation "
            "honesty are first-class requirements—not optional polish."
        ),
    ],
    "methods": [
        (
            "Research mixes transformer-era modeling with careful dataset governance, human protocols, and targeted "
            "stress tests for brittleness."
        ),
    ],
    "applications": [
        (
            "Applications include decision-support assistants, scientific literature workflows, and accessibility tools "
            "with explicit uncertainty handling."
        ),
    ],
    "challenges": [
        (
            "Open challenges include contamination-aware benchmarking, multilingual fairness, and scaling supervision "
            "without amplifying silent biases."
        ),
    ],
    "mentoring": [
        (
            "Students typically begin with reproduction and error analysis, then move to benchmark proposals; "
            "Dr. {name} emphasizes writing-as-thinking."
        ),
    ],
    "teaching": [
        (
            "Courses emphasize NLP evaluation literacy and the sociology of dataset creation."
        ),
    ],
    "roadmap": [
        (
            "Roadmap themes include retrieval-first architectures, structured reasoning interfaces, "
            "and lightweight auditing tools for classroom deployments."
        ),
    ],
    "experience": [
        "{name} publishes across ACL/EMNLP/NAACL venues; {lab} collaborates with HCI and policy scholars on deployment studies.",
    ],
    "advising_style": [
        "Paper-style milestone memos; prefers annotated bibliographies early in a project.",
    ],
    "weekly": [
        "Expect ~9–13 hours/week with heavier reading loads early on.",
    ],
    "lab_focus": [
        "{lab} treats language models as systems requiring measurement programs, not single-score comparisons.",
    ],
}

TRACK_COPY["systems"] = {
    "lab_names": [
        "{last} Systems Research Lab",
        "{last} Lab for Distributed & Cloud Systems",
        "{last} High-Performance Computing Group",
    ],
    "areas": [
        "operating systems",
        "distributed systems",
        "cloud infrastructure",
        "parallel computing",
        "storage systems",
        "systems for ML",
        "performance engineering",
    ],
    "keywords": [
        "Rust",
        "C++",
        "Linux kernel",
        "RDMA",
        "Kubernetes",
        "scheduling",
        "microservices",
        "distributed consensus",
        "profiling",
        "GPU kernels",
        "NVMe",
        "network stacks",
    ],
    "skills": [
        "C/C++",
        "Rust or Go",
        "Linux",
        "computer architecture intuition",
        "debugging concurrent systems",
        "performance profiling",
    ],
    "preferred": [
        "Strong systems programming maturity and patience for long debugging cycles; coursework in OS + networking helps substantially.",
        "Students comfortable reading OSDI/SOSP-style papers and annotating design tradeoffs.",
    ],
    "openings": [
        (
            "Dr. {name} directs the {lab}, building systems where latency tails, resource fairness, and operational "
            "observability are engineered—not bolted on after deployment."
        ),
    ],
    "methods": [
        (
            "The group combines kernel/user-space prototyping with rigorous benchmarking and failure injection; "
            "students learn to distrust cached conclusions without flamegraphs."
        ),
    ],
    "applications": [
        (
            "Targets include ML training clusters, edge inference stacks, and campus-scale research platforms requiring reliability."
        ),
    ],
    "challenges": [
        (
            "Core challenges include tail latency under contention, safe upgrades in distributed settings, "
            "and reproducible performance evaluation."
        ),
    ],
    "mentoring": [
        (
            "Undergraduates often start with instrumented micro-benchmarks and bug fixes; Dr. {name} emphasizes "
            "incremental commits and design docs."
        ),
    ],
    "teaching": [
        (
            "Teaching emphasizes OS internals, concurrency reasoning, and performance culture grounded in measurement."
        ),
    ],
    "roadmap": [
        (
            "Roadmap themes include systems support for large-model training, energy-aware scheduling, "
            "and verified rollback tooling."
        ),
    ],
    "experience": [
        "{name} publishes in OSDI/SOSP/NSDI-class venues; {lab} ships artifacts used by partner research groups.",
    ],
    "advising_style": [
        "Issue-tracker driven development; expects design notes before large refactors.",
    ],
    "weekly": [
        "Expect ~12–18 hours/week during kernel-heavy phases; schedules adjust around compile/debug cycles.",
    ],
    "lab_focus": [
        "{lab} treats systems research as principled engineering with scientific measurement obligations.",
    ],
}

TRACK_COPY["theory_algo"] = {
    "lab_names": [
        "{last} Algorithms & Theory Group",
        "{last} Lab for Discrete Structures & Optimization",
    ],
    "areas": [
        "algorithms",
        "data structures",
        "combinatorial optimization",
        "approximation algorithms",
        "randomized algorithms",
        "online algorithms",
        "fine-grained complexity",
        "graph algorithms",
    ],
    "keywords": [
        "dynamic graphs",
        "shortest paths",
        "matchings",
        "LP relaxations",
        "spectral methods",
        "lower bounds",
        "amortized analysis",
        "probabilistic inequalities",
        "sketching",
        "streaming algorithms",
    ],
    "skills": [
        "discrete mathematics",
        "proof writing",
        "algorithms",
        "probability",
        "LaTeX",
        "Mathematical maturity",
    ],
    "preferred": [
        "Comfortable with rigorous proofs and iterative refinement of definitions; expects clarity over speed.",
        "Strong performance in algorithms/theory coursework and willingness to read classical references.",
    ],
    "openings": [
        (
            "Dr. {name} leads the {lab}, investigating fundamental computation limits and designing algorithms "
            "with provable guarantees under realistic constraints."
        ),
    ],
    "methods": [
        (
            "Research blends classical discrete optimization with modern probabilistic tools and structured instance analyses."
        ),
    ],
    "applications": [
        (
            "Motivating domains include routing, scheduling, learning-adjacent subroutines, and resource allocation "
            "where constants and logarithmic factors genuinely matter."
        ),
    ],
    "challenges": [
        (
            "Students confront tension between worst-case guarantees and empirical structure—projects clarify assumptions explicitly."
        ),
    ],
    "mentoring": [
        (
            "Mentorship emphasizes lemma notebooks, proof sketches before details, and seminar-style presentations; "
            "Dr. {name} coaches undergraduates toward incremental publishable lemmas when appropriate."
        ),
    ],
    "teaching": [
        (
            "Teaching stresses mathematical communication and proof hygiene alongside algorithm design patterns."
        ),
    ],
    "roadmap": [
        (
            "Directions include dynamic graph algorithms under partial observability, approximation schemes for "
            "structured clustering, and bridges to ML theory."
        ),
    ],
    "experience": [
        "{name} publishes in STOC/FOCS/SODA-class venues; {lab} welcomes careful undergraduate collaborators on theory-meets-systems bridges.",
    ],
    "advising_style": [
        "Weekly proof meetings with collaborative whiteboarding and explicit dependency graphs for lemmas.",
    ],
    "weekly": [
        "Expect ~8–12 hours/week for theory-heavy reading and problem sessions.",
    ],
    "lab_focus": [
        "{lab} foregrounds crisp problem formulation and honest theorem statements.",
    ],
}

TRACK_COPY["security"] = {
    "lab_names": [
        "{last} Security & Privacy Lab",
        "{last} Systems Security Group",
    ],
    "areas": [
        "systems security",
        "applied cryptography",
        "software security",
        "network security",
        "privacy-enhancing technologies",
        "threat modeling",
    ],
    "keywords": [
        "memory safety",
        "fuzzing",
        "symbolic execution",
        "TLS",
        "trusted computing",
        "differential privacy",
        "secure protocols",
        "intrusion detection",
        "supply chain security",
        "formal methods hooks",
    ],
    "skills": [
        "C/C++",
        "Python",
        "discrete math",
        "networking basics",
        "Linux security tooling",
        "careful reasoning about adversaries",
    ],
    "preferred": [
        "Security mindset: assumes attackers exploit ambiguity; expects precise threat models and cautious claims.",
        "Prior coursework in security or systems; patience for responsible disclosure norms.",
    ],
    "openings": [
        (
            "Dr. {name} directs the {lab}, studying defenses that survive motivated adversaries rather than nominal benchmarks."
        ),
    ],
    "methods": [
        (
            "Methods combine empirical attack surfaces with principled mitigations and measurable residual risk articulation."
        ),
    ],
    "applications": [
        (
            "Applications span campus infrastructure hardening, privacy-preserving analytics, and secure ML deployment pipelines."
        ),
    ],
    "challenges": [
        (
            "Key tensions include usability vs. assurance, patch latency vs. verification, and evaluating defenses under adaptive attackers."
        ),
    ],
    "mentoring": [
        (
            "Undergraduates begin with reproduction of CVE analyses and controlled experiments; Dr. {name} emphasizes ethics training."
        ),
    ],
    "teaching": [
        (
            "Courses integrate threat modeling exercises with hands-on labs in a supervised environment."
        ),
    ],
    "roadmap": [
        (
            "Roadmap directions include supply-chain transparency tooling, privacy for graph analytics, "
            "and robustness of ML systems under prompt injection."
        ),
    ],
    "experience": [
        "{name} publishes in IEEE S&P/CCS/USENIX Security circles; {lab} collaborates with systems and policy researchers.",
    ],
    "advising_style": [
        "Structured threat-model reviews; expects careful logging of assumptions and ethical boundaries.",
    ],
    "weekly": [
        "Expect ~10–14 hours/week; lab work may include supervised penetration-testing exercises on isolated testbeds.",
    ],
    "lab_focus": [
        "{lab} treats security research as adversarial measurement science.",
    ],
}

TRACK_COPY["hci"] = {
    "lab_names": [
        "{last} Human-Centered Computing Lab",
        "{last} Interactive Systems Group",
    ],
    "areas": [
        "human-computer interaction",
        "usable privacy",
        "interactive ML",
        "visualization",
        "accessibility",
        "social computing",
    ],
    "keywords": [
        "user studies",
        "mixed methods",
        "prototyping",
        "Figma",
        "Eye tracking",
        "Wizard-of-Oz",
        "participatory design",
        "explainability UX",
        "mixed-initiative interfaces",
    ],
    "skills": [
        "Python or JavaScript prototyping",
        "study design basics",
        "statistics intuition",
        "writing for HCI venues",
        "ethical IRB literacy",
    ],
    "preferred": [
        "Comfort translating qualitative insights into design iterations; respects participant consent and privacy.",
        "Interest in combining lightweight engineering with rigorous study protocols.",
    ],
    "openings": [
        (
            "Dr. {name} leads the {lab}, designing interactive systems where human workflows—not model scores—define success."
        ),
    ],
    "methods": [
        (
            "Research mixes iterative prototyping with controlled studies and field deployments when feasible."
        ),
    ],
    "applications": [
        (
            "Domains include education technologies, developer tools, healthcare workflows, and civic participation interfaces."
        ),
    ],
    "challenges": [
        (
            "Challenges include generalizing findings across populations and avoiding 'demo bait' without measurable outcomes."
        ),
    ],
    "mentoring": [
        (
            "Students often begin with literature syntheses and pilot studies; Dr. {name} coaches storytelling for mixed-methods results."
        ),
    ],
    "teaching": [
        (
            "Teaching emphasizes design rationales, ethics, and statistical humility."
        ),
    ],
    "roadmap": [
        (
            "Directions include human-AI teaming interfaces, accessibility-first AI assistants, "
            "and governance tooling for classroom deployments."
        ),
    ],
    "experience": [
        "{name} publishes in CHI/CSCW/UIST venues; {lab} collaborates with education and clinical partners under IRB oversight.",
    ],
    "advising_style": [
        "Studio-style critiques plus structured study milestones; encourages reflective design notebooks.",
    ],
    "weekly": [
        "Expect ~8–12 hours/week; study seasons may require coordinated scheduling with participants.",
    ],
    "lab_focus": [
        "{lab} emphasizes accountable UX research grounded in participant-centered evidence.",
    ],
}


TOPICS_ROWS = [
    ("t_ml_core", "Machine learning (core)"),
    ("t_deep", "Deep learning & representation learning"),
    ("t_prob_ml", "Probabilistic modeling & Bayesian ML"),
    ("t_cv", "Computer vision"),
    ("t_nlp", "Natural language processing"),
    ("t_robot", "Robotics & embodied AI"),
    ("t_sys", "Systems & operating systems"),
    ("t_dist", "Distributed systems & cloud infrastructure"),
    ("t_arch", "Computer architecture & hardware–software co-design"),
    ("t_theory", "Algorithms & computational complexity"),
    ("t_opt", "Discrete optimization & mathematical programming"),
    ("t_sec", "Security & privacy"),
    ("t_crypto", "Cryptography (applied & theoretical hooks)"),
    ("t_hci", "Human–computer interaction"),
    ("t_vis", "Visualization & visual analytics"),
    ("t_db", "Databases & data management"),
    ("t_edtech", "Computing education & HCI for learning"),
    ("t_health", "Computing for health & biomedicine"),
]


def topic_ids_for_track(track: str) -> list[str]:
    m = {
        "ml_ai": ["t_ml_core", "t_deep", "t_prob_ml"],
        "cv": ["t_cv", "t_robot"],
        "nlp": ["t_nlp", "t_ml_core"],
        "systems": ["t_sys", "t_dist", "t_arch"],
        "theory_algo": ["t_theory", "t_opt", "t_ml_core"],
        "security": ["t_sec", "t_crypto", "t_sys"],
        "hci": ["t_hci", "t_vis", "t_edtech"],
    }
    return m[track]


def main() -> None:
    rng = random.Random(RNG_SEED)

    # --- mentors ---
    mentors_csv: list[dict[str, str]] = []
    profiles: list[dict[str, object]] = []
    mentor_track: list[str] = []
    track_to_indices: dict[str, list[int]] = defaultdict(list)

    track_list: list[str] = []
    for tname, cnt in TRACK_ORDER:
        track_list.extend([tname] * cnt)
    assert len(track_list) == NUM_MENTORS
    rng.shuffle(track_list)

    used_names: set[tuple[str, str]] = set()
    for i in range(NUM_MENTORS):
        mid = f"m_{i+1:03d}"
        track = track_list[i]
        mentor_track.append(track)
        track_to_indices[track].append(i)

        while True:
            fn = rng.choice(FIRST_NAMES)
            ln = rng.choice(LAST_NAMES)
            if (fn, ln) not in used_names:
                used_names.add((fn, ln))
                break
        name = f"{fn} {ln}"
        dept = rng.choice(DEPTS)
        hidx = int(rng.triangular(10, 75, 28))  # bias toward mid-career density

        lab_tpl = rng.choice(TRACK_COPY[track]["lab_names"])
        lab = lab_tpl.format(last=ln)

        body = _compose_track_profile(rng, track, f"Dr. {name}", lab)
        mentors_csv.append(
            {
                "mentor_id": mid,
                "name": name,
                "department": dept,
                "h_index": str(hidx),
            }
        )
        profiles.append({"mentor_id": mid, **body})

    _wcsv(_SEEDS / "topics.csv", [{"topic_id": a, "label": b} for a, b in TOPICS_ROWS], ["topic_id", "label"])
    _wcsv(_SEEDS / "mentors.csv", mentors_csv, ["mentor_id", "name", "department", "h_index"])

    with (_SEEDS / "mentor_profiles.json").open("w", encoding="utf-8") as f:
        json.dump({"version": "1.0", "mentors": profiles}, f, ensure_ascii=False, indent=2)

    # --- papers & authorship (dense within track, occasional cross-track) ---
    papers: list[dict[str, str]] = []
    paper_authors: list[dict[str, str]] = []
    paper_topics: list[dict[str, str]] = []
    pid = 0
    for _ in range(900):
        pid += 1
        paper_id = f"p_{pid:05d}"
        year = str(rng.randint(2018, 2026))
        venue_pool = [
            "NeurIPS",
            "ICML",
            "ICLR",
            "CVPR",
            "ICCV",
            "ACL",
            "EMNLP",
            "OSDI",
            "SOSP",
            "NSDI",
            "SIGCOMM",
            "EuroSys",
            "STOC",
            "FOCS",
            "SODA",
            "IEEE S&P",
            "USENIX Security",
            "CCS",
            "CHI",
            "UIST",
            "VLDB",
            "SIGMOD",
        ]
        venue = rng.choice(venue_pool)
        title = (
            f"{rng.choice(['Towards', 'On', 'Scalable', 'Robust', 'Efficient'])} "
            f"{rng.choice(['Learning', 'Inference', 'Scheduling', 'Verification', 'Indexing'])} "
            f"{rng.choice(['for', 'under', 'with'])} "
            f"{rng.choice(['Modern', 'Large-scale', 'Distributed', 'Structured', 'Streaming'])} "
            f"{rng.choice(['Workloads', 'Models', 'Systems', 'Graphs', 'Interfaces'])}"
        )
        papers.append({"paper_id": paper_id, "title": title, "year": year, "venue": venue})

        if rng.random() < 0.07:
            t1, t2 = rng.sample(list(track_to_indices.keys()), 2)
            pool = track_to_indices[t1] + track_to_indices[t2]
            tr_for_topic = rng.choice([t1, t2])
        else:
            tr_for_topic = rng.choice(list(track_to_indices.keys()))
            pool = track_to_indices[tr_for_topic]
        k_auth = rng.randint(2, 4)
        authors = [mentors_csv[j]["mentor_id"] for j in rng.sample(pool, k=min(k_auth, len(pool)))]
        for aid in authors:
            paper_authors.append({"paper_id": paper_id, "mentor_id": aid})
        tid = rng.choice(topic_ids_for_track(tr_for_topic))
        paper_topics.append({"paper_id": paper_id, "topic_id": tid})

    _wcsv(_SEEDS / "papers.csv", papers, ["paper_id", "title", "year", "venue"])
    _wcsv(_SEEDS / "paper_authors.csv", paper_authors, ["paper_id", "mentor_id"])
    _wcsv(_SEEDS / "paper_topics.csv", paper_topics, ["paper_id", "topic_id"])

    # --- projects ---
    projects: list[dict[str, str]] = []
    proj_id = 0
    skill_bank = [
        "Python",
        "C++",
        "Rust",
        "Linear algebra",
        "Probability",
        "Algorithms",
        "Systems programming",
        "PyTorch",
        "CUDA",
        "Networking",
        "Statistics",
        "LaTeX",
        "HCI study methods",
    ]
    for i in range(NUM_MENTORS):
        if rng.random() > 0.46:
            continue
        proj_id += 1
        mid = mentors_csv[i]["mentor_id"]
        tr = mentor_track[i]
        tid = rng.choice(topic_ids_for_track(tr))
        skills = "|".join(rng.sample(skill_bank, k=rng.randint(2, 4)))
        title = (
            f"Undergraduate research studio: {rng.choice(['benchmark', 'prototype', 'analysis', 'tooling'])} "
            f"for {rng.choice(['learning', 'vision', 'language', 'systems', 'security', 'HCI'])} workflows"
        )
        projects.append(
            {
                "project_id": f"proj_{proj_id:04d}",
                "title": title,
                "mentor_id": mid,
                "topic_ids": tid,
                "required_skills": skills,
            }
        )
    _wcsv(_SEEDS / "projects.csv", projects, ["project_id", "title", "mentor_id", "topic_ids", "required_skills"])

    # --- students ---
    NUM_STUDENTS = 140
    grades = ["Year 1", "Year 2", "Year 3", "Year 4"]
    majors = [
        "Computer Science",
        "Computer Engineering",
        "Data Science",
        "Mathematics & Computer Science",
        "Electrical & Computer Engineering",
    ]
    interest_bank = [
        "machine learning",
        "computer vision",
        "NLP",
        "robotics",
        "systems",
        "security",
        "HCI",
        "theory",
        "graphics",
        "PL",
    ]
    skill_bank_st = [
        "Python",
        "Java",
        "C++",
        "Rust",
        "JavaScript",
        "TensorFlow",
        "PyTorch",
        "SQL",
        "Linux",
        "algorithms",
        "probability",
    ]
    students: list[dict[str, str]] = []
    for si in range(NUM_STUDENTS):
        sid = f"s_{si+1:03d}"
        students.append(
            {
                "student_id": sid,
                "grade": rng.choice(grades),
                "major": rng.choice(majors),
                "skills": "|".join(rng.sample(skill_bank_st, k=rng.randint(3, 6))),
                "interests": "|".join(rng.sample(interest_bank, k=rng.randint(2, 4))),
            }
        )
    _wcsv(_SEEDS / "students.csv", students, ["student_id", "grade", "major", "skills", "interests"])

    # --- project participation ---
    parts: list[dict[str, str]] = []
    for pr in projects:
        pid_ = pr["project_id"]
        k = rng.randint(1, 4)
        studs = rng.sample([s["student_id"] for s in students], k=k)
        for sid in studs:
            parts.append({"project_id": pid_, "student_id": sid})
    _wcsv(_SEEDS / "project_participants.csv", parts, ["project_id", "student_id"])

    # --- advising ---
    advising: list[dict[str, str]] = []
    for mid in rng.sample([m["mentor_id"] for m in mentors_csv], k=120):
        sid = rng.choice(students)["student_id"]
        advising.append({"mentor_id": mid, "student_id": sid})
    _wcsv(_SEEDS / "advising.csv", advising, ["mentor_id", "student_id"])

    # --- aliases (synthetic) ---
    aliases = []
    for j in range(10):
        aliases.append(
            {
                "canonical_type": "mentor",
                "canonical_id": mentors_csv[j]["mentor_id"],
                "alias_source": "openalex",
                "alias_id": f"A{rng.randint(10**8, 10**9-1)}",
            }
        )
    for j in range(3):
        aliases.append(
            {
                "canonical_type": "paper",
                "canonical_id": papers[j]["paper_id"],
                "alias_source": "doi",
                "alias_id": f"10.1000/synth.{j+1:03d}",
            }
        )
    _wcsv(_SEEDS / "entity_aliases.csv", aliases, ["canonical_type", "canonical_id", "alias_source", "alias_id"])

    print(f"Wrote {NUM_MENTORS} mentors + aligned seeds to {_SEEDS}")


if __name__ == "__main__":
    main()
