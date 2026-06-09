# Vajra.Stream Developer's Handbook

This document outlines git workflows, developer setup guidelines, offline content expansion guidelines, testing protocols, and future refactoring roadmaps for the **Vajra.Stream Sacred Technology Platform**.

---

## 1. Local Setup & GitHub Workflow

Vajra.Stream uses a Git-based version control loop. Follow these commands to initialize and track your changes:

```bash
# Initialize local repository
git init

# Track all source files and documentation
git add .
git commit -m "Initial commit: Vajra.Stream Core System"

# Link to your remote repository on GitHub
git remote add origin https://github.com/YOUR_USERNAME/vajra-stream.git
git branch -M main
git push -u origin main
```

### Git Best Practices
- **Commit Early:** Group commits by logical boundaries (e.g. backend websocket routing, frontend types, UI widgets).
- **Preserve Documentation Integrity:** Ensure that main-level indices are kept up-to-date when deleting or introducing modules.
- **Maintain Clean Settings:** Avoid committing local DB paths or absolute API keys. Use the `.env.example` as a template for local `.env` variables.

---

## 2. Offline Content Development Guidelines

A major portion of Vajra.Stream relies on structured JSON knowledge bases. Developers can expand the files locally:

### A. Expanding `knowledge/healing_knowledge.json`
- **Chakra Specifications:** Map associated deities, yantra geometries, gemstone correspondences, essential oils, and physical/spiritual blocks for all 7 chakras.
- **Meridian Acupoints:** Map the 361 classical points (LU1 to LU11, LI1 to LI20, etc.) with Chinese Pinyin names, precise locations, and contraindications.
- **Protocols:** Add structured symptom sheets (Respiratory, Digestive, Cardiovascular, Chronic pain) specifying affected chakras, key acupoints, and recommended frequencies.

### B. Creating Session Templates (`knowledge/session_templates/`)
Create JSON objects following this standard structure to introduce new protocols:
```json
{
  "session_name": "Heart Healing Protocol",
  "duration_minutes": 30,
  "intention": "Open and heal the heart center",
  "systems_addressed": {
    "chakras": ["anahata"],
    "meridians": ["heart"]
  },
  "phases": [
    {
      "phase": "Opening",
      "duration": 5,
      "frequencies": [7.83],
      "guidance": "Settle mind, set intention."
    }
  ]
}
```

---

## 3. Testing & Verification Guide

Always run tests before committing code changes to verify system integrity:

### A. Timing Verification
Run the timing tests to verify that the Chaldean planetary hour calculations and the `lunar-python` calculations succeed:
```bash
python scripts/test_timing.py
```

### B. Integration Flow Verification
Run the terminal-based UI simulation to verify that the orchestrator loads the databases and executes tools cleanly:
```bash
python scripts/test_orchestration_cmd.py
python scripts/test_backend_peace.py
```

### C. Frontend Types check
Navigate to `frontend/` and execute compilation to ensure TypeScript interfaces and WebSocket hook variables are synchronized:
```bash
npm run build
```

---

## 4. Development Roadmap & Milestones

The roadmap outlines the maturation of the platform:

```
┌───────────────────────────┐      ┌───────────────────────────┐
│     Phase 1: MVP Core     │ ───> │   Phase 2: UI Expansion   │
│  - Carrier wave synthesis │      │  - React Dashboard panels │
│  - Basic Crystal Grids    │      │  - Interactive RNG needle │
└───────────────────────────┘      └───────────────────────────┘
                                                 │
                                                 ▼
┌───────────────────────────┐      ┌───────────────────────────┐
│   Phase 4: Scaling Out    │ <─── │   Phase 3: Integration    │
│  - Distributed networks   │      │  - WebSocket state loops  │
│  - Mobile client outputs  │      │  - Lunar calendar engines │
└───────────────────────────┘      └───────────────────────────┘
```

-   **Phase 1 (Completed):** Sound synthesis engines, E-meter simulation math, and terminal commands.
-   **Phase 2 (Completed):** React UI widgets, Three.js 3D canvas renderers, and SQLite schema integration.
-   **Phase 3 (Current):** WebSocket real-time event broadcasting, `lunar-python` Saka Dawa integration, and cleaning up documentation drift.
-   **Phase 4 (Future):** Porting outputs to mobile devices, connecting actual hardware transmitters, and implementing multi-session network broadcasting.
