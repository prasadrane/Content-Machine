"""Capability readiness, registry limits and authentication."""

import unittest

from content_machine.api.app import app

from workflow_action_fixtures import ActionApiFixture


class WorkflowActionsCapabilityTest(ActionApiFixture, unittest.TestCase):
    def test_capabilities_require_authentication(self):
        response = self.client.get("/api/workflow/capabilities")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["principal"]["owner_id"], self.fixture.a.owner_id
        )
        self.assertTrue(response.json()["pairs"])
        self.assertTrue(
            all(not pair["can_generate"] for pair in response.json()["pairs"])
        )
        app.state.workflow_authenticator = lambda request: None
        self.assertEqual(self.client.get("/api/workflow/capabilities").status_code, 401)

    # -- C10 action boundary ------------------------------------------------

    def test_capabilities_report_truthful_readiness_and_registry_limits(self):
        first = self.client.get("/api/workflow/capabilities")
        second = self.client.get("/api/workflow/capabilities")
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json(), second.json())
        pairs = first.json()["pairs"]
        self.assertTrue(pairs)
        self.assertTrue(all(pair["can_generate"] is False for pair in pairs))
        self.assertTrue(
            all(
                pair["can_edit"] is True and pair["can_approve"] is True
                for pair in pairs
            )
        )
        self.assertEqual(
            [(pair["destination"], pair["format"]) for pair in pairs],
            [
                ("linkedin", "linkedin_post"),
                ("x", "x_thread"),
                ("youtube", "youtube_short_script"),
                ("youtube", "youtube_long_script"),
                ("instagram", "instagram_caption"),
                ("instagram", "instagram_reel_script"),
                ("newsletter", "newsletter_draft"),
                ("generic_video", "generic_short_video_script"),
            ],
        )
        by_pair = {(pair["destination"], pair["format"]): pair for pair in pairs}
        self.assertEqual(
            by_pair[("instagram", "instagram_caption")]["limits"],
            {
                "max_chars": {
                    "value": 2200,
                    "source": "configured_adapter",
                    "measurement": "unicode_code_points",
                }
            },
        )
        self.assertEqual(
            by_pair[("x", "x_thread")]["limits"],
            {
                "max_chars_per_segment": {
                    "value": 280,
                    "source": "configured_adapter",
                    "measurement": "unicode_code_points",
                }
            },
        )
        self.assertEqual(
            first.json()["principal"],
            {
                "owner_id": self.fixture.a.owner_id,
                "mode": "hosted_verified",
                "display_name": None,
            },
        )


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
