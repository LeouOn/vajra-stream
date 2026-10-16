"""The knowledge blessing populations load into the PopulationManager."""

import json
from pathlib import Path

from backend.core.services.population_manager import PopulationManager

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge" / "blessing_populations"


def test_every_knowledge_target_has_a_name_intention_and_priority():
    for path in sorted(KNOWLEDGE_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["targets"], path.name
        for target in data["targets"]:
            assert target["name"].strip(), path.name
            assert target["intention"].strip(), f"{path.name}: {target['name']}"
            assert 1 <= target["priority"] <= 10, f"{path.name}: {target['name']}"


def test_depression_and_total_loss_targets_are_seeded(tmp_path):
    manager = PopulationManager(str(tmp_path / "populations.json"))
    names = {
        pop.name for pop_id, pop in manager.populations.items() if pop_id.startswith("kp_depression_and_total_loss_")
    }
    assert {"Those Living with Depression", "Those Who Have Lost Everything", "Those in Suicidal Despair"} <= names
