"""Tests for the workflow domain schemas and capability registry (contract C02).

These tests pin the frozen workflow contract:
- item/context/artifact/snapshot/review/approval record and input shapes;
- exact string preservation (no whitespace normalization, ever);
- explicit destination/format pairs and server-assigned ownership/timestamps;
- approval refusal for blank final artifacts;
- the initial backend capability registry.

All tests are offline and touch no storage or provider.
"""

from __future__ import annotations

import os
import sys
import unittest

from pydantic import ValidationError

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from content_machine.workflow.format_registry import (  # noqa: E402
    CANONICAL_PAIRS,
    UnknownFormatPairError,
    capability_payloads,
    get_capability,
    is_thread_format,
    resolve_legacy_format,
    resolve_pair,
    supports_thread,
)
from content_machine.workflow.schemas import (  # noqa: E402
    Approval,
    ApproveRequest,
    Artifact,
    ContentItem,
    ContentVersion,
    Context,
    FinalArtifactError,
    GenerateRequest,
    IdempotencyRecord,
    ItemCreate,
    ItemPatch,
    Operation,
    Principal,
    Proposal,
    RestoreRequest,
    Review,
    ReviewRequest,
    SkipReviewRequest,
    SourceRef,
    ensure_approvable,
    utc_timestamp,
)

TS = "2026-11-05T09:12:00.000Z"
DIGEST = "sha256:" + ("a" * 64)


def principal() -> Principal:
    return Principal(owner_id="own_01", mode="trusted_local", display_name=None)


def create_payload() -> ItemCreate:
    return ItemCreate(
        title="Indexing tradeoffs",
        destination="linkedin",
        format="linkedin_post",
    )


def new_item(**overrides):
    kwargs = dict(
        item_id="itm_01",
        principal=principal(),
        payload=create_payload(),
        now=TS,
    )
    kwargs.update(overrides)
    return ContentItem.new(**kwargs)


def make_version(**overrides) -> ContentVersion:
    kwargs = dict(
        version_id="ver_02",
        item_id="itm_01",
        owner_id="own_01",
        revision=2,
        context=Context(notes="Indexing cost"),
        artifact=Artifact.from_text("Exact text."),
        destination="linkedin",
        format="linkedin_post",
        artifact_digest=DIGEST,
        purpose="review",
        created_by="own_01",
        created_at=TS,
    )
    kwargs.update(overrides)
    return ContentVersion(**kwargs)


def make_approval(**overrides) -> Approval:
    kwargs = dict(
        approval_id="apr_01",
        owner_id="own_01",
        item_id="itm_01",
        version_id="ver_02",
        artifact_digest=DIGEST,
        destination="linkedin",
        format="linkedin_post",
        approved_by="own_01",
        approved_at=TS,
    )
    kwargs.update(overrides)
    return Approval(**kwargs)


def source_ref(source_id: str = "src_01", excerpt: str = "  excerpt\t\n") -> SourceRef:
    return SourceRef(
        source_id=source_id,
        url="https://example.test/post?q=1",
        title="Real source",
        excerpt=excerpt,
        fetched_at=TS,
    )


class TestItemOwnershipAndRevisions(unittest.TestCase):
    def test_new_item_defaults_to_idea_with_server_ownership(self):
        item = new_item()

        self.assertEqual(item.item_id, "itm_01")
        self.assertEqual(item.owner_id, "own_01")
        self.assertEqual(item.working_revision, 1)
        self.assertEqual(item.stage, "idea")
        self.assertEqual(item.artifact.segments, [])
        self.assertEqual(item.context.notes, "")
        self.assertIsNone(item.active_approval_id)
        self.assertIsNone(item.parent_version_id)
        self.assertEqual(item.created_at, TS)
        self.assertEqual(item.updated_at, TS)

    def test_inputs_reject_client_supplied_ownership_and_timestamps(self):
        for extra in (
            {"owner_id": "attacker"},
            {"created_at": "1999-01-01T00:00:00.000Z"},
            {"updated_at": "1999-01-01T00:00:00.000Z"},
        ):
            with self.subTest(extra=extra):
                with self.assertRaises(ValidationError):
                    ItemCreate(
                        title="Indexing tradeoffs",
                        destination="linkedin",
                        format="linkedin_post",
                        **extra,
                    )

        # Server-assigned fields never exist on client input models.
        for excluded in ("owner_id", "created_at", "updated_at"):
            self.assertNotIn(excluded, ItemCreate.model_fields)

        for request_model in (GenerateRequest, ReviewRequest, SkipReviewRequest):
            self.assertNotIn("owner_id", request_model.model_fields)

    def test_authenticated_principal_is_the_only_ownership_source(self):
        item = new_item(principal=Principal(owner_id="own_42", mode="trusted_local"))
        self.assertEqual(item.owner_id, "own_42")

        # A payload cannot smuggle a replacement owner past the principal.
        with self.assertRaises(ValidationError):
            ItemCreate.model_validate(
                {
                    "title": "Indexing tradeoffs",
                    "destination": "linkedin",
                    "format": "linkedin_post",
                    "owner_id": "own_42",
                }
            )

    def test_invalid_revision_numbers_are_rejected(self):
        for revision in (0, -1):
            with self.subTest(kind="actual", revision=revision):
                with self.assertRaises(ValidationError):
                    ContentItem(
                        item_id="itm_01",
                        owner_id="own_01",
                        title="Indexing tradeoffs",
                        destination="linkedin",
                        format="linkedin_post",
                        working_revision=revision,
                        created_at=TS,
                        updated_at=TS,
                    )
            with self.subTest(kind="version", revision=revision):
                with self.assertRaises(ValidationError):
                    make_version(revision=revision)
            with self.subTest(kind="expected", revision=revision):
                with self.assertRaises(ValidationError):
                    ItemPatch(expected_revision=revision)
                with self.assertRaises(ValidationError):
                    GenerateRequest(expected_revision=revision)

    def test_unknown_platform_format_pairs_are_rejected(self):
        with self.assertRaises(ValidationError):
            ItemCreate(
                title="Wrong pair",
                destination="linkedin",
                format="x_thread",
            )
        with self.assertRaises(ValidationError):
            ItemCreate(
                title="Unknown destination",
                destination="tiktok",
                format="x_thread",
            )
        with self.assertRaises(ValidationError):
            ItemPatch(expected_revision=1, destination="x", format="linkedin_post")

    def test_all_canonical_pairs_are_accepted(self):
        for destination, fmt in CANONICAL_PAIRS:
            with self.subTest(destination=destination, format=fmt):
                payload = ItemCreate(title="Pair", destination=destination, format=fmt)
                item = ContentItem.new(
                    item_id="itm_01",
                    principal=principal(),
                    payload=payload,
                    now=TS,
                )
                self.assertEqual((item.destination, item.format), (destination, fmt))

    def test_stage_is_an_explicit_enum(self):
        self.assertEqual(new_item().stage, "idea")
        with self.assertRaises(ValidationError):
            ItemPatch(expected_revision=1, stage="published")
        self.assertEqual(ItemPatch(expected_revision=1, stage="export").stage, "export")

    def test_title_and_notes_never_normalize_whitespace(self):
        title = "  Indexing   tradeoffs\n"
        notes = " line one \nline two\t"
        payload = ItemCreate(
            title=title,
            destination="linkedin",
            format="linkedin_post",
        )
        self.assertEqual(payload.title, title)

        item = ContentItem.new(
            item_id="itm_01",
            principal=principal(),
            payload=payload,
            now=TS,
        )
        item = item.model_copy(update={"context": Context(notes=notes)})
        self.assertEqual(item.title, title)
        self.assertEqual(item.context.notes, notes)
        self.assertEqual(item.model_dump()["title"], title)

    def test_timestamps_are_iso8601_utc_with_milliseconds(self):
        with self.assertRaises(ValidationError):
            ContentItem(
                item_id="itm_01",
                owner_id="own_01",
                title="Indexing tradeoffs",
                destination="linkedin",
                format="linkedin_post",
                created_at="2026-11-05 09:12:00",
                updated_at=TS,
            )
        stamp = utc_timestamp()
        self.assertRegex(stamp, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


class TestContextAndArtifactSegments(unittest.TestCase):
    def test_context_defaults_and_source_identity_round_trip(self):
        self.assertEqual(Context().notes, "")
        self.assertEqual(Context().sources, [])

        excerpt = "  quoted excerpt\t\n"
        source = SourceRef(
            source_id="src_01",
            url="https://example.test/post?q=1",
            title="Real source",
            excerpt=excerpt,
            fetched_at=TS,
        )
        context = Context(notes="", sources=[source])
        self.assertEqual(context.sources[0].excerpt, excerpt)

        with self.assertRaises(ValidationError):
            SourceRef(
                source_id="src_01",
                title="Missing URL",
                excerpt="x",
                fetched_at=TS,
            )

    def test_single_text_artifact_is_exactly_one_segment(self):
        text = "First paragraph.\n\nSecond paragraph.  "
        artifact = Artifact.from_text(text)

        self.assertEqual(artifact.segments, [text])
        self.assertEqual(len(artifact.segments), 1)
        self.assertEqual(artifact.segments[0], text)

    def test_thread_artifact_preserves_order_and_exact_text(self):
        segments = ["1/ Hook.  ", "2/ Middle\nwith break", "\t3/ End\t"]
        artifact = Artifact.from_thread(segments)

        self.assertEqual(artifact.segments, segments)
        self.assertEqual(list(artifact.segments), segments)

    def test_artifact_rejects_unknown_fields_and_oversized_segments(self):
        with self.assertRaises(ValidationError):
            Artifact(segments=["text"], trailing_newline=True)
        with self.assertRaises(ValidationError):
            Artifact(segments=["x" * 100_001])

    def test_empty_artifact_is_valid_while_editing(self):
        self.assertEqual(Artifact().segments, [])
        self.assertEqual(Artifact.from_text("").segments, [""])


class TestApprovalInputs(unittest.TestCase):
    def test_approve_request_requires_revision_digest_and_consent(self):
        with self.assertRaises(ValidationError):
            ApproveRequest(artifact_digest=DIGEST, consent=True)
        with self.assertRaises(ValidationError):
            ApproveRequest(expected_revision=2, consent=True)
        with self.assertRaises(ValidationError):
            ApproveRequest(expected_revision=2, artifact_digest=DIGEST)
        with self.assertRaises(ValidationError):
            ApproveRequest(expected_revision=0, artifact_digest=DIGEST, consent=True)

        request = ApproveRequest(expected_revision=2, artifact_digest=DIGEST, consent=True)
        self.assertTrue(request.consent)

    def test_artifact_digest_must_be_sha256_hex(self):
        for bad in ("sha256:abc", "md5:" + "a" * 64, "sha256:" + "g" * 64):
            with self.subTest(digest=bad):
                with self.assertRaises(ValidationError):
                    ApproveRequest(expected_revision=2, artifact_digest=bad, consent=True)

    def test_whitespace_only_final_artifacts_cannot_be_approved(self):
        for segments in ([""], ["   "], ["\n\t "], [], ["valid text", "  \n"]):
            with self.subTest(segments=segments):
                with self.assertRaises(FinalArtifactError):
                    ensure_approvable(
                        Artifact.from_thread(segments),
                        "linkedin",
                        "linkedin_post",
                    )
        ensure_approvable(Artifact.from_text("Exact text."), "linkedin", "linkedin_post")

        with self.assertRaises(UnknownFormatPairError):
            ensure_approvable(Artifact.from_text("Exact text."), "linkedin", "x_thread")

    def test_non_thread_final_artifacts_must_be_exactly_one_segment(self):
        artifact = Artifact(segments=["First post", "Second post"])
        for destination, fmt in (
            ("linkedin", "linkedin_post"),
            ("instagram", "instagram_caption"),
            ("instagram", "instagram_reel_script"),
            ("youtube", "youtube_short_script"),
            ("youtube", "youtube_long_script"),
            ("newsletter", "newsletter_draft"),
            ("generic_video", "generic_short_video_script"),
        ):
            with self.subTest(destination=destination, format=fmt):
                with self.assertRaises(FinalArtifactError):
                    ensure_approvable(artifact, destination, fmt)
                self.assertEqual(
                    artifact.segments,
                    ["First post", "Second post"],
                    "final validation must not rewrite stored text",
                )
                ensure_approvable(Artifact.from_text("Exact text."), destination, fmt)

    def test_thread_final_artifact_keeps_ordered_nonblank_segments(self):
        segments = ["1/ Hook.  ", "2/ Body\n", "\t3/ End\t"]
        artifact = Artifact.from_thread(segments)
        ensure_approvable(artifact, "x", "x_thread")
        self.assertEqual(artifact.segments, segments)

    def test_approval_and_version_records_are_immutable(self):
        approval = make_approval()
        with self.assertRaises(ValidationError):
            approval.approval_id = "apr_02"

        version = make_version()
        with self.assertRaises(ValidationError):
            version.revision = 3

    def test_approval_matches_contract_fields(self):
        self.assertEqual(
            set(make_approval().model_dump()),
            {
                "approval_id",
                "owner_id",
                "item_id",
                "version_id",
                "artifact_digest",
                "destination",
                "format",
                "approved_by",
                "approved_at",
            },
        )
        with self.assertRaises(ValidationError):
            make_approval(destination="tiktok")


class TestSnapshotReviewAndOperation(unittest.TestCase):
    def test_content_version_freezes_context_and_artifact(self):
        version = make_version()
        self.assertEqual(version.context.notes, "Indexing cost")
        self.assertEqual(version.artifact.segments, ["Exact text."])
        self.assertEqual(version.revision, 2)
        self.assertEqual(version.purpose, "review")

        with self.assertRaises(ValidationError):
            make_version(purpose="publish")
        with self.assertRaises(ValidationError):
            make_version(artifact_digest="sha256:short")
        with self.assertRaises(ValidationError):
            make_version(destination="x", format="linkedin_post")

    def test_version_owns_deep_context_and_artifact_snapshots(self):
        working_context = Context(notes="Indexing cost\n", sources=[source_ref()])
        working_artifact = Artifact.from_thread(["1/ Hook.  ", "2/ Body\n"])
        version = make_version(context=working_context, artifact=working_artifact)

        # Working objects mutate after the snapshot: the version must not move.
        working_context.notes = "mutated"
        working_context.sources[0].excerpt = "mutated"
        working_context.sources.append(source_ref(source_id="src_02"))
        working_artifact.segments[0] = "mutated"
        working_artifact.segments.append("3/ Appended")

        self.assertEqual(version.context.notes, "Indexing cost\n")
        self.assertEqual(len(version.context.sources), 1)
        self.assertEqual(version.context.sources[0].excerpt, "  excerpt\t\n")
        self.assertEqual(version.artifact.segments, ["1/ Hook.  ", "2/ Body\n"])

        wire = version.model_dump(mode="json")
        self.assertIsInstance(wire["artifact"]["segments"], list)
        self.assertTrue(all(isinstance(part, str) for part in wire["artifact"]["segments"]))
        self.assertEqual(wire["artifact"]["segments"], ["1/ Hook.  ", "2/ Body\n"])

        restored = ContentVersion.model_validate(wire)
        self.assertEqual(restored.context.notes, "Indexing cost\n")
        self.assertEqual(restored.context.sources[0].excerpt, "  excerpt\t\n")
        self.assertEqual(restored.artifact.segments, ["1/ Hook.  ", "2/ Body\n"])

        # Snapshot-side edits stay local to the snapshot's own nested objects.
        version.context.notes = "snapshot only"
        version.context.sources[0].title = "snapshot only"
        version.artifact.segments[0] = "snapshot only"
        self.assertEqual(working_context.notes, "mutated")
        self.assertEqual(working_context.sources[0].title, "Real source")
        self.assertEqual(working_artifact.segments[0], "mutated")

    def test_operation_records_kind_context_snapshot_and_envelope(self):
        operation = Operation(
            operation_id="op_01",
            owner_id="own_01",
            item_id="itm_01",
            kind="generate",
            input_version_id="ver_02",
            context_snapshot=Context(notes="Indexing cost"),
            state="completed",
            request_id="req_01",
            result={"segments": ["Draft text."]},
            error=None,
            started_at=TS,
            finished_at=TS,
        )
        self.assertEqual(operation.kind, "generate")
        self.assertEqual(operation.context_snapshot.notes, "Indexing cost")
        self.assertEqual(operation.result, {"segments": ["Draft text."]})

        with self.assertRaises(ValidationError):
            Operation(
                operation_id="op_02",
                owner_id="own_01",
                item_id="itm_01",
                kind="publish",
                input_version_id="ver_02",
                context_snapshot=Context(),
                request_id="req_02",
            )
        with self.assertRaises(ValidationError):
            Operation(
                operation_id="op_02",
                owner_id="own_01",
                item_id="itm_01",
                kind="review",
                input_version_id="ver_02",
                request_id="req_02",
            )

    def test_review_proposals_keep_current_and_proposed_text_exactly(self):
        proposal = Proposal(
            segment=0,
            current="Exact text.  ",
            proposed="Exact text\t",
        )
        review = Review(
            review_id="rev_01",
            owner_id="own_01",
            item_id="itm_01",
            input_version_id="ver_02",
            request_id="req_02",
            state="completed",
            actions={"apply": False},
            score_basis={
                "rubric": "council",
                "judge_slot": "judge_1",
                "dimensions": [{"name": "clarity", "raw": 7.5, "z": 0.6}],
            },
            proposals=[proposal],
            started_at=TS,
            finished_at=TS,
        )
        self.assertEqual(review.proposals[0].current, "Exact text.  ")
        self.assertEqual(review.proposals[0].proposed, "Exact text\t")
        self.assertEqual(review.score_basis["dimensions"][0]["z"], 0.6)

        with self.assertRaises(ValidationError):
            Review(
                review_id="rev_02",
                owner_id="own_01",
                item_id="itm_01",
                input_version_id="ver_02",
                request_id="req_03",
                state="superseded",
            )

    def test_review_serializes_contract_model_config_field(self):
        review = Review.model_validate(
            {
                "review_id": "rev_01",
                "owner_id": "own_01",
                "item_id": "itm_01",
                "input_version_id": "ver_02",
                "request_id": "req_02",
                "state": "pending",
                "model_config": "judge_1",
            }
        )
        dumped = review.model_dump(by_alias=True)
        self.assertEqual(dumped["model_config"], "judge_1")
        self.assertNotIn("llm_config", dumped)

    def test_skip_review_and_restore_inputs(self):
        self.assertEqual(SkipReviewRequest(expected_revision=2).expected_revision, 2)
        restore = RestoreRequest(expected_revision=3, version_id="ver_02")
        self.assertEqual(restore.version_id, "ver_02")
        with self.assertRaises(ValidationError):
            RestoreRequest(expected_revision=0, version_id="ver_02")

    def test_idempotency_record_requires_owner_request_and_response(self):
        record = IdempotencyRecord(
            owner_id="own_01",
            request_id="req_01",
            method="POST",
            resource_path="/api/workflow/items/itm_01/approve",
            request_digest="sha256:" + "b" * 64,
            response_status=200,
            response_body={"item": {"working_revision": 2}},
            created_at=TS,
        )
        self.assertEqual(record.response_status, 200)

        with self.assertRaises(ValidationError):
            IdempotencyRecord(
                owner_id="own_01",
                request_id="req_01",
                method="post",
                resource_path="/api/workflow/items",
                request_digest="digest",
                response_status=200,
                response_body={},
                created_at=TS,
            )
        with self.assertRaises(ValidationError):
            IdempotencyRecord(
                owner_id="own_01",
                request_id="req_01",
                method="POST",
                resource_path="/api/workflow/items",
                request_digest="digest",
                response_status=99,
                response_body={},
                created_at=TS,
            )


class TestFormatRegistry(unittest.TestCase):
    def test_registry_exposes_the_approved_retained_pairs(self):
        self.assertEqual(
            set(CANONICAL_PAIRS),
            {
                ("linkedin", "linkedin_post"),
                ("x", "x_thread"),
                ("youtube", "youtube_short_script"),
                ("youtube", "youtube_long_script"),
                ("instagram", "instagram_caption"),
                ("instagram", "instagram_reel_script"),
                ("newsletter", "newsletter_draft"),
                ("generic_video", "generic_short_video_script"),
            },
        )

    def test_capability_readiness_is_explicit_per_pair(self):
        x_thread = get_capability("x", "x_thread")
        self.assertTrue(x_thread.can_edit)
        self.assertTrue(x_thread.can_generate)
        self.assertTrue(x_thread.can_approve)
        self.assertEqual(
            x_thread.limits["max_chars_per_segment"].as_dict(),
            {
                "value": 280,
                "source": "configured_adapter",
                "measurement": "unicode_code_points",
            },
        )

        instagram = get_capability("instagram", "instagram_caption")
        self.assertTrue(instagram.can_edit)
        self.assertFalse(instagram.can_generate)
        self.assertTrue(instagram.can_approve)
        self.assertEqual(
            instagram.limits["max_chars"].as_dict(),
            {
                "value": 2200,
                "source": "configured_adapter",
                "measurement": "unicode_code_points",
            },
        )

        self.assertFalse(get_capability("instagram", "instagram_reel_script").can_generate)
        self.assertFalse(get_capability("youtube", "youtube_short_script").can_generate)
        self.assertTrue(get_capability("youtube", "youtube_long_script").can_generate)
        self.assertTrue(get_capability("linkedin", "linkedin_post").can_generate)
        self.assertTrue(get_capability("newsletter", "newsletter_draft").can_generate)
        self.assertTrue(
            get_capability("generic_video", "generic_short_video_script").can_generate
        )

    def test_registry_rejects_unknown_pairs(self):
        for destination, fmt in (
            ("linkedin", "x_thread"),
            ("tiktok", "x_thread"),
            ("x", "linkedin_post"),
        ):
            with self.subTest(destination=destination, format=fmt):
                with self.assertRaises(UnknownFormatPairError):
                    resolve_pair(destination, fmt)
                with self.assertRaises(UnknownFormatPairError):
                    get_capability(destination, fmt)

    def test_legacy_aliases_are_retained_without_guessing(self):
        self.assertEqual(
            resolve_legacy_format("linkedin"), ("linkedin", "linkedin_post")
        )
        self.assertEqual(resolve_legacy_format("x_thread"), ("x", "x_thread"))
        self.assertEqual(
            resolve_legacy_format("video_script_long"),
            ("youtube", "youtube_long_script"),
        )
        self.assertEqual(
            resolve_legacy_format("video_script_short"),
            ("generic_video", "generic_short_video_script"),
        )
        self.assertEqual(
            resolve_legacy_format("video_script"),
            ("generic_video", "generic_short_video_script"),
        )
        self.assertEqual(
            resolve_legacy_format("newsletter"), ("newsletter", "newsletter_draft")
        )

        # A conflicting known destination is never silently remapped.
        with self.assertRaises(UnknownFormatPairError):
            resolve_legacy_format("video_script", destination="youtube")
        self.assertEqual(
            resolve_legacy_format("video_script", destination="generic_video"),
            ("generic_video", "generic_short_video_script"),
        )

    def test_capability_payloads_serialize_for_the_endpoint(self):
        payloads = capability_payloads()
        self.assertEqual(len(payloads), len(CANONICAL_PAIRS))
        instagram = next(p for p in payloads if p["format"] == "instagram_caption")
        self.assertEqual(
            instagram,
            {
                "destination": "instagram",
                "format": "instagram_caption",
                "can_edit": True,
                "can_generate": False,
                "can_approve": True,
                "limits": {
                    "max_chars": {
                        "value": 2200,
                        "source": "configured_adapter",
                        "measurement": "unicode_code_points",
                    }
                },
            },
        )

    def test_thread_formats_are_explicit(self):
        self.assertTrue(is_thread_format("x_thread"))
        self.assertFalse(is_thread_format("linkedin_post"))
        self.assertTrue(supports_thread("x", "x_thread"))
        self.assertFalse(supports_thread("linkedin", "linkedin_post"))


if __name__ == "__main__":
    unittest.main()
