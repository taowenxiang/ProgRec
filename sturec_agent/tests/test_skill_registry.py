"""Tests for sturec_agent.skill_registry."""

from __future__ import annotations

import unittest

from sturec_agent.skill_registry import SKILL_REGISTRY, get_skill, list_skills


class TestSkillRegistry(unittest.TestCase):
    def test_list_skills_five_identifiers(self) -> None:
        ids = list_skills()
        self.assertEqual(len(ids), 5)
        self.assertIn("/mentor-discovery", ids)

    def test_registry_keys_match_list(self) -> None:
        for sid in list_skills():
            self.assertIn(sid, SKILL_REGISTRY)

    def test_each_skill_has_contract_fields(self) -> None:
        for sid in list_skills():
            meta = get_skill(sid)
            for key in ("name", "entrypoint", "input_contract", "output_contract"):
                self.assertIn(key, meta, f"{sid} missing {key}")
                self.assertTrue(str(meta[key]).strip(), f"{sid} empty {key}")

    def test_get_skill_unknown(self) -> None:
        with self.assertRaises(KeyError):
            get_skill("/unknown-skill")


if __name__ == "__main__":
    unittest.main()
