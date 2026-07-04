# AGENTS.md — AI Agent Guide for controle_app

This document helps AI coding agents (Copilot, Claude, etc.) be immediately productive in the APDPVP controle_app Django project. For full architecture and conventions, refer to [CLAUDE.md](CLAUDE.md).

---

## Quick Start

```bash
# Setup
python -m venv .venv
.venv\Scripts\activate                    # Windows
source .venv/bin/activate                 # macOS/Linux
pip install -r requirements.txt

# Develop
python manage.py runserver               # Dev server on 127.0.0.1:8000
python manage.py migrate                 # Apply migrations
python manage.py setup_groups             # Create role groups (custom command)
python manage.py sync_agents              # Sync agent pool from API/mock (custom command)
python manage.py test                     # Run tests

# Admin & debugging
python manage.py createsuperuser          # Create admin account
python manage.py shell                    # Interactive Django shell
```

---

**Language**: French (Gabon APDPVP authority). Model/view labels & docstrings use French.

---

## Architecture & Locked Decisions

Full project structure, the locked architectural decisions (relational
schema, soft-delete scope, lock-on-generation, dual audit trail, 3-manager
pattern), and the permissions matrix live in [CLAUDE.md](CLAUDE.md) — read
it first, don't re-derive these here. This file only adds the AI-agent
operational layer on top: quick start, checklists, and navigation.

---

## Before You Code: Workflow Checklist

### Adding a New Model

- [ ] Is it "catalog" or "transactional"?
  - **Catalog** → Apply `SoftDeleteMixin` + 3 managers
  - **Transactional** → Use `soft_delete=False` or no soft-delete
- [ ] Does it have an immutability rule? → Add `est_verrouillee` check in `clean()`
- [ ] Does it need field-level audit? → Add `HistoricalRecords()` (django-simple-history)
- [ ] Should its creation/deletion be logged? → Add `JournalAction` entry in `post_save`/`post_delete` signal
- [ ] Copy the pattern from [code_examples.md](code_examples.md); **don't invent a new one**

### Adding a View or Form

- [ ] Does it modify locked fields? → Must check `mission.est_verrouillee` before allowing edits
- [ ] Does the user need permissions? → Use `@require_membre_mission` or `@require_chef_mission` decorator
- [ ] Is it part of the questionnaire? → Use HTMX for page-by-page submission (see templates/)
- [ ] Link to [CLAUDE.md § Permissions](CLAUDE.md#permissions) for role matrix

### Implementing Compliance Scoring

- [ ] Read [reponse_traitement_fields.md](reponse_traitement_fields.md) for all 50 field definitions
- [ ] Identify which fields map to compliance rules (a–j treatments)
- [ ] See [CLAUDE.md § Tâches en attente](CLAUDE.md#tâches-en-attente) for spec placeholder

### Generating Word Report

- [ ] Await user-provided template + placeholder mapping
- [ ] Implement via `python-docx` or `docxtpl`
- [ ] See [CLAUDE.md § Tâches en attente](CLAUDE.md#tâches-en-attente) for placeholder reference

---

## Task-Specific Navigation

| Task | Read | Key Files | Links |
|------|------|-----------|-------|
| **Model design** | code_examples.md | `core/models.py`, `missions/models.py` | [Managers pattern](code_examples.md#1-sofeldeletemixin-coretransformpy), [Signals](code_examples.md#signals) |
| **Questionnaire fields** | reponse_traitement_fields.md | `missions/models.py` (ReponsePage1–5) | [Field mappings by treatment](reponse_traitement_fields.md) |
| **Permissions & roles** | CLAUDE.md § Permissions | `core/permissions.py`, views.py | 3 roles: Administrateur, Chef de mission, Agent contrôleur |
| **Lock-on-generation** | code_examples.md § Lock | `missions/models.py` | [Immutability validator](code_examples.md#lock-on-generation) |
| **Audit trail** | CLAUDE.md § Traçabilité | `missions/models.py` (HistoricalRecords), `models.py` (JournalAction) | django-simple-history + JournalAction |
| **Auto-creation signals** | code_examples.md § Signals | `missions/signals.py` | ReponseTraitement + ReponsePage1–5 post_save |
| **Report generation** | CLAUDE.md § Word Template | (pending spec) | Awaits user template + placeholder mapping |
| **HTMX forms** | templates/ | (pending) | See rh_app reference if needed |

---

## Key Files to Know

### Core Models & Utilities
- **[core/models.py](../core/models.py)** — `SoftDeleteMixin`, `JournalAction`
- **[core/permissions.py](../core/permissions.py)** — Role decorators (`@require_membre_mission`, etc.)
- **[core/signals.py](../core/signals.py)** — Auto-creation signals

### Business Logic
- **[missions/models.py](../missions/models.py)** — All mission-related models + immutability rules
- **[missions/signals.py](../missions/signals.py)** — Auto-creation of responses post mission
- **[missions/views.py](../missions/views.py)** — Mission CRUD + questionnaire workflow
- **[missions/forms.py](../missions/forms.py)** — Formsets for multi-page questionnaire

### Documentation
- **[CLAUDE.md](CLAUDE.md)** — Full architecture (French) + pending tasks
- **[code_examples.md](code_examples.md)** — Patterns to copy (SoftDelete, managers, signals, forms)
- **[reponse_traitement_fields.md](reponse_traitement_fields.md)** — Questionnaire field schema (50 fields × 10 treatments)

---

## Common Patterns (Copy-Paste Reference)

**Before writing custom code, check [code_examples.md](code_examples.md) for:**

1. ✅ **SoftDeleteMixin + 3 managers** — Standard for catalog models
2. ✅ **Lock-on-generation validator** — Check `est_verrouillee` in `clean()`
3. ✅ **Signals for auto-creation** — ReponseTraitement + ReponsePage1–5 post_save
4. ✅ **Permission decorators** — `@require_membre_mission`, `@require_chef_mission`
5. ✅ **FormSets** — Multi-page questionnaire workflow
6. ✅ **HistoricalRecords** — Audit trail on response models

If a pattern isn't in [code_examples.md](code_examples.md) yet, propose it to the user instead of inventing one.

---

## Environment & Testing

### Test Execution
```bash
# All tests
python manage.py test

# Specific app
python manage.py test missions

# Specific test class
python manage.py test missions.tests.TestMissionCreation

# Verbose output
python manage.py test -v 2
```

### Database
- **Dev**: SQLite (default), auto-created
- **Test**: In-memory SQLite (fast)
- **Prod**: PostgreSQL (config in settings)

### Logging & Debugging
```bash
# Django shell with context
python manage.py shell

# Examples
>>> from missions.models import MissionControle
>>> m = MissionControle.objects.first()
>>> m.est_verrouillee  # Is mission locked?
>>> m.responsetraitement_set.all()  # Get responses
>>> from django.contrib.auth.models import Group
>>> Group.objects.values_list('name', flat=True)  # Check role groups exist
```

---

## Pre-Coding Validation

Before starting a task, AI agents should verify:

1. **Is django-simple-history installed?**
   ```bash
   pip list | grep django-simple-history
   ```
   If missing: Add to `requirements.txt` and run `pip install -r requirements.txt`

2. **Are role groups created?**
   ```bash
   python manage.py setup_groups
   ```
   Should create: `Administrateur`, `Chef de mission`, `Agent contrôleur`

3. **Are migrations up-to-date?**
   ```bash
   python manage.py migrate
   ```
   Watch for: "Applying X migrations..."

4. **Does the task require the user-provided Word template?**
   Check [CLAUDE.md § Tâches en attente](CLAUDE.md#tâches-en-attente). If yes, pause and ask for template + placeholder spec.

---

## Red Flags (When to Ask Before Coding)

- ❌ Task asks to use JSONField for questionnaire responses → **Violates decision #1 (relational schema)**
- ❌ Task asks to add soft-delete to `PersonneInterrogee` → **Violates decision #2 (protection by lock)**
- ❌ Task asks to skip immutability checks in views → **Violates decision #3 (model-level enforcement)**
- ❌ Task mentions report generation without Word template → **Pause, ask for user template**
- ❌ Task doesn't mention audit trail → **Ask: Which model needs history/JournalAction?**

---

## References

- **[CLAUDE.md](CLAUDE.md)** — Full architecture & decisions (French)
- **[code_examples.md](code_examples.md)** — Patterns to copy
- **[reponse_traitement_fields.md](reponse_traitement_fields.md)** — Questionnaire schema
- **Django docs** → https://docs.djangoproject.com/
- **django-simple-history** → https://django-simple-history.readthedocs.io/
- **HTMX** → https://htmx.org/

---

## Contact & Feedback

If you encounter a pattern, convention, or gotcha not documented here, **update this file** so future AI agents benefit. Suggest updates to the user via:

```
/create-instruction 'Update AGENTS.md with ...'
```

Last updated: 2026-07-03
