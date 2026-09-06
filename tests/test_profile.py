"""Author profile & voice grounding tests.

Run: python -m unittest tests/test_profile.py
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from content_machine.schemas import ProfileData, UpdateProfileRequest  # noqa: E402


class TestProfile(unittest.TestCase):
    def test_voice_guide_seed_file(self):
        voice_guide_path = Path(__file__).resolve().parent.parent / "knowledge" / "02_voice-guide.md"
        self.assertTrue(voice_guide_path.exists(), "knowledge/02_voice-guide.md must exist")
        content = voice_guide_path.read_text(encoding="utf-8")

        # Assert core sections
        self.assertIn("# Voice & Persona Guide — Prasad Rane", content)
        self.assertIn("## 1. Core Identity & Stance", content)
        self.assertIn("## 2. Voice Invariants & Negative Constraints (NON-NEGOTIABLE)", content)
        self.assertIn("## 3. Communication Cadence & Tone", content)
        self.assertIn("## 4. Technical Grounding & Architectural Beliefs", content)

        # Assert 5 non-negotiable negative constraints
        self.assertIn("Zero Company Attribution", content)
        self.assertIn("No False Corporate Employment", content)
        self.assertIn("Job-Status Agnostic Technical Tone", content)
        self.assertIn("Zero Fluff or Generic Praise", content)
        self.assertIn("No Emoji Overload", content)

    def test_profile_schemas(self):
        # Test ProfileData defaults and validation
        profile = ProfileData(
            current_focus="Building agentic systems"
        )
        self.assertEqual(profile.name, "Prasad Rane")
        self.assertEqual(profile.headline, "Senior Software & AI Systems Engineer")
        self.assertEqual(profile.current_focus, "Building agentic systems")
        self.assertEqual(profile.technical_domains, [])
        self.assertEqual(profile.hard_invariants, [])
        self.assertEqual(profile.full_markdown, "")

        # Test custom fields and serialization
        custom_profile = ProfileData(
            name="Custom Name",
            headline="Custom Headline",
            current_focus="Distributed Systems",
            technical_domains=["Distributed Systems", "Agentic AI"],
            hard_invariants=["No fluff"],
            full_markdown="# Custom Profile"
        )
        data = custom_profile.model_dump()
        self.assertEqual(data["name"], "Custom Name")
        self.assertEqual(data["technical_domains"], ["Distributed Systems", "Agentic AI"])
        restored = ProfileData.model_validate(data)
        self.assertEqual(restored, custom_profile)

        # Test UpdateProfileRequest defaults and partial update
        update_req = UpdateProfileRequest()
        self.assertIsNone(update_req.current_focus)
        self.assertIsNone(update_req.technical_domains)
        self.assertIsNone(update_req.custom_notes)

        update_req_with_values = UpdateProfileRequest(
            current_focus="New focus",
            technical_domains=["Kafka", "DynamoDB"],
            custom_notes="Focus on resilience"
        )
        self.assertEqual(update_req_with_values.current_focus, "New focus")
        self.assertEqual(update_req_with_values.technical_domains, ["Kafka", "DynamoDB"])
        self.assertEqual(update_req_with_values.custom_notes, "Focus on resilience")
        req_data = update_req_with_values.model_dump()
        self.assertEqual(req_data["current_focus"], "New focus")
        self.assertEqual(UpdateProfileRequest.model_validate(req_data), update_req_with_values)


if __name__ == "__main__":
    unittest.main()
