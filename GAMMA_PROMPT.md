# Gamma Presentation Prompt — git-developer

Copy the prompt below into [gamma.app](https://gamma.app) → **Create** → **Generate from prompt**.

---

## Prompt

Create a professional 11-slide presentation for **git-developer**, an AI-powered README generator built on LangGraph and Gemini 2.5 Flash. Use a modern dark theme with blue (#0066CC), green (#28A745), and gray (#6A737D) accents. Font: Segoe UI for body, monospace for code. Format: 16:9 widescreen.

---

### Slide 1 — Title

**git-developer**
*AI-Powered README Generator for GitHub Repositories*

Subtitle: Generate professional, AI-driven READMEs in 30 seconds — with competitive analysis, quality scoring, and one-click GitHub PR publishing.

Badges: Python 3.10+ · Node 18+ · Gemini 2.5 Flash · LangGraph · MIT License

Visual: Dark background, glowing terminal/code motif, subtle GitHub octocat watermark.

---

### Slide 2 — Problem Statement

**Why Professional READMEs Matter**

Three-column layout:

**The Cost of Bad Documentation**
- 67% of developers abandon projects with poor READMEs
- Manual README writing takes 2–4 hours per repository
- Inconsistent standards across org repos create onboarding friction
- Stale documentation loses contributor trust

**The Status Quo**
- Copy-paste from generic templates
- Forgotten sections (API reference, architecture diagrams)
- No competitive positioning
- No quality measurement

**The Business Impact**
- Slower open-source adoption
- Increased support overhead
- Reduced developer credibility
- Lost contributions and integrations

Speaker note: This is not a vanity problem — documentation quality directly correlates with project adoption and organizational developer experience scores.

---

### Slide 3 — Solution Overview

**How git-developer Works**

Five-step horizontal flow diagram:

1. **Authenticate** → Paste GitHub token
2. **Select Repo** → Browse public repositories
3. **Generate** → Multi-agent AI pipeline runs (25–35s)
4. **Review** → Split view: preview + quality metrics
5. **Publish** → One-click GitHub pull request

Key stats callout boxes:
- ⚡ 30 seconds average generation time
- 🏆 Quality score 0–100 on every README
- 🤖 6 specialized AI agents in the pipeline
- 🔗 Direct GitHub PR creation — no copy-paste

Visual: Clean flow diagram with icons, connected by arrows, dark background.

---

### Slide 4 — Key Features

**Six Core Capabilities**

Two-row, three-column card grid:

**Multi-Agent Orchestration**
LangGraph StateGraph coordinates 6 agents in a DAG. Falls back to sequential execution if the graph engine is unavailable — generation always completes.

**Competitive Intelligence**
Searches GitHub for similar repos, ranks by stars, and generates a positioning section highlighting what makes your project unique.

**Real-Time Progress Streaming**
Server-Sent Events stream live stage updates (percent, message, timestamp) across the 30-second generation window — no blind spinners.

**Mermaid Validation & Auto-Repair**
Validates all Mermaid diagram blocks before delivery. Invalid syntax is auto-repaired via a targeted Gemini repair prompt and re-validated.

**One-Click PR Publishing**
Commit and open a GitHub PR directly from the UI. Configure branch, commit message, PR title, and PR body before publishing.

**Quality Scoring**
Every README receives an overall score (0–100), completeness %, reading time estimate, section coverage checklist, and improvement suggestions.

---

### Slide 5 — Architecture

**System Design**

Split layout — left 60% diagram, right 40% bullet explanation.

**Architecture layers (top to bottom):**
```
User Browser
    ↓ REST + SSE
Next.js 14 Frontend (Vercel)
    ↓ HTTP
FastAPI Backend (GCP Cloud Run)
    ↓
LangGraph StateGraph Orchestrator
    ↓
6 Specialized Agents
    ↓                    ↓
GitHub REST API     Gemini 2.5 Flash
```

Right side bullets:
- **Frontend**: Next.js 14 + Tailwind CSS + Zustand + react-markdown
- **Backend**: FastAPI + Uvicorn, stateless, auto-scales 0–5 instances
- **Orchestrator**: LangGraph DAG with sequential fallback
- **Agents**: repo_analyzer → competitive_analyzer → best_practices_advisor → topical_insights → readme_composer → quality_gate
- **External**: PyGithub 2.2.0 + google-genai 1.73.1

---

### Slide 6 — Tech Stack

**Technology Choices**

Four-column table layout:

| Layer | Technology | Version | Why |
|-------|-----------|---------|-----|
| Frontend | Next.js | 14.2.3 | SSR, routing, Vercel-native |
| | React | 18+ | Component model |
| | Tailwind CSS | 3.4.1 | Rapid utility-first styling |
| | Zustand | 5.0.12 | Lightweight state |
| Backend | FastAPI | 0.110.1 | Async Python, auto-docs |
| | Python | 3.10+ | Agent implementation |
| AI / LLM | Gemini 2.5 Flash | Latest | Speed + accuracy |
| | google-genai | 1.73.1 | Official SDK |
| Orchestration | LangGraph | Latest | DAG agent coordination |
| GitHub | PyGithub | 2.2.0 | PR creation, repo read |
| Real-time | Server-Sent Events | Native | Progress streaming |
| Deploy | GCP Cloud Run | — | Scale to zero |
| | Vercel | — | Frontend CDN |

Callout: "Every technology choice prioritizes operational simplicity and cloud-native scalability."

---

### Slide 7 — Quick Start

**Up and Running in 5 Minutes**

Two-column layout: left = prerequisites, right = commands.

**Prerequisites**
- Python 3.10+
- Node.js 18+
- GitHub Personal Access Token (scopes: `repo`, `public_repo`)
- Gemini API Key (free tier at aistudio.google.com)

**Commands**
```bash
git clone https://github.com/ramamurthy-540835/git-developer.git
cd git-developer

# Backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Configure
echo "GEMINI_API_KEY=your_key" >> .env.local
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" >> frontend/.env.local

# Run
uvicorn api.main:app --reload --port 8000 &
cd frontend && npm run dev
```

Open: `http://localhost:3000`

---

### Slide 8 — Demo Walkthrough

**Step-by-Step User Journey**

Six numbered steps in a horizontal timeline:

**1. Authenticate**
Paste GitHub token → system validates and shows username + repo count

**2. Select Repository**
Searchable repo list → click any card to select

**3. Generate**
Click Generate → SSE stream opens → 6 agent stages stream live

**4. Watch Progress**
Real-time stage bar: Analysis → Competitive → Best Practices → Insights → Compose → QC

**5. Review**
Split view: markdown preview (left) + quality score panel (right)

**6. Publish**
Configure PR metadata → Create PR → get PR URL — done

Bottom callout: "Total time from token paste to merged PR: under 5 minutes."

---

### Slide 9 — Governance & OSSA Compliance

**Enterprise-Grade AI Governance**

Three-column layout:

**OSSA Integration**
git-developer ships with an OSSA (Open Standard for Service Agents) manifest defining:
- LLM model + temperature
- Token budget per execution (8,192 tokens)
- Daily spend limit ($20.00)
- Audit event types
- Data retention (30 days)

```yaml
apiVersion: ossa/v0.4.6
kind: Agent
metadata:
  name: git-developer-readme-generator
spec:
  llm:
    model: gemini-2.5-flash
  cost:
    tokenBudget:
      perExecution: 8192
    spendLimits:
      daily: 20.00
  audit:
    enabled: true
    retention: 90days
```

**Cost Controls**
- Per-execution token budget enforced
- Daily and monthly spend limits
- Alert threshold at $15/day
- Average cost: $0.02–0.05 per README

**Audit & Compliance**
- Every generation, publish, merge, close logged
- 90-day audit trail retention
- SOC2 Type II alignment
- Mandatory human review before any GitHub write (HITL)
- Secrets via GCP Secret Manager — never in images

---

### Slide 10 — Roadmap

**What's Next**

Two-column layout: Near-term (Q2–Q3 2026) and Future (Q4 2026+)

**Near-Term**
- [ ] GitHub OAuth — eliminate manual token paste
- [ ] Batch processing — generate for all repos in a YAML list via UI
- [ ] Generation history — versioned archive per repository
- [ ] Custom prompt templates — organization-branded schemas

**Future**
- [ ] PDF and DOCX export
- [ ] Multi-language README support (ES, FR, JP)
- [ ] Webhook trigger — auto-regenerate on push to `main`
- [ ] Advanced analytics dashboard (token usage, quality trends, cost)
- [ ] Team workspace — shared token pool, role-based access

Timeline visual: horizontal bar chart with milestones marked Q2/Q3/Q4 2026.

---

### Slide 11 — Call to Action

**Get Started Today**

Three-column action cards:

**Use It**
```bash
git clone https://github.com/ramamurthy-540835/git-developer
```
Get a professional README for your repo in 30 seconds.

**Contribute**
1. Fork the repository
2. Create a feature branch
3. Open a pull request

See `CONTRIBUTING.md` for guidelines.

**Integrate with OSSA**
Deploy the included `ossa-manifest.yaml` to your OSSA governance layer for cost controls, audit logging, and compliance enforcement across your team.

---

Center bottom: github.com/ramamurthy-540835/git-developer · MIT License · v1.0.0 · May 2026

Visual: Dark slide with three glowing card panels, subtle animated gradient background.

---

*Generated: May 5, 2026 · For use with gamma.app presentation generator*
