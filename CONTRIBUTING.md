# Contributing to RevenueOS

Thank you for your interest in contributing to **RevenueOS**! We welcome contributions from data engineers, analytics engineers, business analysts, and developers.

---

## 🛠 Development Workflow

### 1. Fork and Clone
```bash
git clone https://github.com/25sarvesh2005/RevenueOS.git
cd RevenueOS
```

### 2. Environment Setup
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
pip install pytest pytest-cov
```

### 3. Running the Test Suite
All PRs must maintain 100% test passing rate:
```bash
python -m pytest tests/ -v
```

---

## 📐 Coding & SQL Standards

1. **Python**:
   - Follow PEP 8 style guidelines.
   - Use explicit type annotations where possible.
   - Ensure stdout messages handle Windows console encoding safely.
2. **SQL (PostgreSQL)**:
   - Use uppercase for all SQL keywords (`SELECT`, `JOIN`, `WHERE`, `GROUP BY`).
   - Prefix CTEs clearly with descriptive names.
   - Guard against divide-by-zero errors using `NULLIF(denominator, 0)`.
   - Prevent multi-line order cross-joins by specifying exact grain conditions.
3. **DAX**:
   - Format DAX measures with explicit line breaks for complex filters.
   - Keep transformations in SQL/Python; reserve DAX for dynamic aggregation.

---

## 🔀 Branch & Commit Conventions

- `feature/<feature-name>`: New analytical models, pipelines, or DAX measures.
- `fix/<bug-name>`: Bug fixes or calculation corrections.
- `docs/<doc-name>`: Documentation, guides, or data dictionary updates.

### Commit Messages
Use conventional commits:
- `feat: add demand elasticity metrics to product profitability`
- `fix: resolve multi-line order fanout in customer health returns CTE`
- `docs: update runbook with Docker restart procedures`
- `test: add unit tests for Isolation Forest multivariate detector`

---

## 📝 Pull Request Guidelines

1. Ensure all 51+ unit tests pass locally before opening a PR.
2. Document new columns in [`docs/data_dictionary.md`](docs/data_dictionary.md).
3. If introducing an estimation methodology, update [`docs/assumptions.md`](docs/assumptions.md).
