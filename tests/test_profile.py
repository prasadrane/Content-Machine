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


class TestProfileManager(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.TemporaryDirectory()
        self.home_root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_get_profile_parses_markdown(self):
        from content_machine.profile.manager import ProfileManager

        manager = ProfileManager(home_root=self.home_root)
        runtime_file = self.home_root / "knowledge" / "02_voice-guide.md"
        self.assertTrue(runtime_file.exists(), "Runtime file should be copied from seed")

        profile = manager.get_profile()
        self.assertEqual(profile.name, "Prasad Rane")
        self.assertEqual(profile.headline, "Senior Software & AI Systems Engineer")
        self.assertIn("Relentless hands-on builder", profile.current_focus)
        self.assertTrue(len(profile.technical_domains) >= 5)
        self.assertIn(".NET Core", profile.technical_domains)
        self.assertEqual(len(profile.hard_invariants), 5)

        # Check that the 5 non-negotiable negative constraints are present
        invariants_text = " ".join(profile.hard_invariants)
        self.assertIn("Zero Company Attribution", invariants_text)
        self.assertIn("No False Corporate Employment", invariants_text)
        self.assertIn("Job-Status Agnostic Technical Tone", invariants_text)
        self.assertIn("Zero Fluff or Generic Praise", invariants_text)
        self.assertIn("No Emoji Overload", invariants_text)

        self.assertIn("# Voice & Persona Guide — Prasad Rane", profile.full_markdown)

    def test_update_profile_preserves_invariants(self):
        from content_machine.profile.manager import ProfileManager

        manager = ProfileManager(home_root=self.home_root)
        new_focus = "Actively evaluating local multi-model routing and agentic workflows."
        new_domains = ["Distributed Systems", "Kafka", "Agentic AI", "FastAPI"]
        notes = "Focus on production resilience and backpressure patterns."

        update_req = UpdateProfileRequest(
            current_focus=new_focus,
            technical_domains=new_domains,
            custom_notes=notes,
        )
        updated_profile = manager.update_profile(update_req)

        self.assertEqual(updated_profile.current_focus, new_focus)
        self.assertEqual(updated_profile.technical_domains, new_domains)
        self.assertIn(notes, updated_profile.full_markdown)

        # Invariants must still be strictly 5 and intact
        self.assertEqual(len(updated_profile.hard_invariants), 5)
        invariants_text = " ".join(updated_profile.hard_invariants)
        self.assertIn("Zero Company Attribution", invariants_text)
        self.assertIn("No False Corporate Employment", invariants_text)
        self.assertIn("Job-Status Agnostic Technical Tone", invariants_text)
        self.assertIn("Zero Fluff or Generic Praise", invariants_text)
        self.assertIn("No Emoji Overload", invariants_text)

        # Re-read from disk to ensure persistence
        fresh_profile = manager.get_profile()
        self.assertEqual(fresh_profile.current_focus, new_focus)
        self.assertEqual(fresh_profile.technical_domains, new_domains)
        self.assertIn(notes, fresh_profile.full_markdown)
        self.assertEqual(len(fresh_profile.hard_invariants), 5)

    def test_get_voice_guide_text(self):
        from content_machine.profile.manager import ProfileManager

        manager = ProfileManager(home_root=self.home_root)
        text = manager.get_voice_guide_text()
        self.assertIsInstance(text, str)
        self.assertIn("# Voice & Persona Guide — Prasad Rane", text)
        self.assertIn("## 2. Voice Invariants & Negative Constraints (NON-NEGOTIABLE)", text)

    def test_default_voice_guide_creation_without_seed(self):
        from content_machine.profile.manager import ProfileManager

        empty_seed = self.home_root / "nonexistent_seed.md"
        manager = ProfileManager(home_root=self.home_root / "isolated", seed_path=empty_seed)
        profile = manager.get_profile()

        self.assertEqual(profile.name, "Prasad Rane")
        self.assertEqual(profile.headline, "Senior Software & AI Systems Engineer")
        self.assertEqual(len(profile.hard_invariants), 5)
        self.assertTrue((self.home_root / "isolated" / "knowledge" / "02_voice-guide.md").exists())

    def test_update_profile_partial_updates(self):
        from content_machine.profile.manager import ProfileManager

        manager = ProfileManager(home_root=self.home_root)

        # Update only focus
        p1 = manager.update_profile(UpdateProfileRequest(current_focus="Focus only update"))
        self.assertEqual(p1.current_focus, "Focus only update")
        self.assertIn(".NET Core", p1.technical_domains)

        # Update only domains
        p2 = manager.update_profile(UpdateProfileRequest(technical_domains=["Rust", "Wasm"]))
        self.assertEqual(p2.current_focus, "Focus only update")
        self.assertEqual(p2.technical_domains, ["Rust", "Wasm"])

        # Update only custom notes
        p3 = manager.update_profile(UpdateProfileRequest(custom_notes="Only note"))
        self.assertEqual(p3.current_focus, "Focus only update")
        self.assertEqual(p3.technical_domains, ["Rust", "Wasm"])
        self.assertIn("Only note", p3.full_markdown)

        # Ensure all 5 invariants remained intact
        self.assertEqual(len(p3.hard_invariants), 5)

    def test_mirror_to_seed_in_dev_mode(self):
        from content_machine.profile.manager import ProfileManager

        custom_seed = self.home_root / "mock_seed.md"
        custom_seed.write_text("# Voice & Persona Guide — Prasad Rane\n", encoding="utf-8")

        manager = ProfileManager(
            home_root=self.home_root / "dev_home",
            seed_path=custom_seed,
            dev_mode=True,
        )

        manager.update_profile(UpdateProfileRequest(current_focus="Dev focus mirrored"))
        seed_content = custom_seed.read_text(encoding="utf-8")
        self.assertIn("Dev focus mirrored", seed_content)


if __name__ == "__main__":
    unittest.main()


