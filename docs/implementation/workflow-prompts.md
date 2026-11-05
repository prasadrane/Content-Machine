# Workflow agent prompt templates

Date 2026-11-05

The controller renders these templates with one checkpoint from [the task manifest](workflow-tasks.json). Resolve every placeholder before dispatch. Each prompt includes only the relevant contract excerpt and code context. The controller retains the full product plan and review record.

## Implementation prompt

~~~text
You implement checkpoint {{task_id}} for Content Machine.

Work in {{worker_root}}.
Read the applicable AGENTS.md and the attached contract excerpt.
The controller has accepted prerequisite checkpoints {{accepted_dependencies}}.
The implementation base is {{accepted_commit}} with tree digest {{baseline_digest}}.
Your request nonce is {{request_nonce}}.

User outcome
{{task_title}}
{{specific_user_problem}}

Files you may change
{{allowed_write_paths}}

Relevant current source and contract
{{read_context}}
{{contract_excerpt}}

Do these steps in order
{{numbered_steps}}

Acceptance cases
{{numbered_acceptance_cases}}

Required focused checks
{{resolved_check_commands}}

For behavioral implementation, write a failing test first, run it and capture the failure.
For a documentation or controller decision packet, run its specified document checks.
Implement the smallest change that makes the case pass.
Run the focused checks again and inspect the actual diff.
Preserve current callers except behavior expressly changed by this checkpoint.
Use existing project seams, readable names and the shared cm-* theme.
Use isolated CONTENT_MACHINE_HOME before storage imports.
Keep credentials and actual author data outside test fixtures.
The controller owns scope changes, branch operations, dependency decisions and release actions.
If a required interface or decision is missing, report blocked with the exact missing input.
If the implementation budget is insufficient, request a smaller packet.

Return a worker-report.json to {{worker_report_path}} with the schema below.
Include actual command outcomes and remaining problems.
The report submits your work for controller review.
Finish this checkpoint and wait for the controller's response.
~~~

## Worker report schema

~~~json
{
  "task_id": "C05",
  "request_nonce": "controller-supplied",
  "attempt": 1,
  "base_commit": "exact-dispatch-base",
  "status": "ready_for_review",
  "changed_files": ["content_machine/workflow/items.py", "tests/test_workflow_items.py"],
  "red_evidence": {
    "argv": ["resolved-python", "-m", "pytest", "tests/test_workflow_items.py", "-q"],
    "exit_code": 1,
    "failing_test_ids": ["example_case"],
    "failure_reason": "Observed missing owner isolation"
  },
  "checks": [
    {
      "argv": ["resolved-python", "-m", "pytest", "tests/test_workflow_items.py", "-q"],
      "exit_code": 0,
      "collected_tests": 4,
      "passed_tests": 4
    }
  ],
  "acceptance_notes": ["Specific case and observed outcome"],
  "remaining_problems": [],
  "blocked_on": null
}
~~~

Use status blocked when required input is missing. A command that was unavailable is recorded with its actual error and without a fabricated exit code. The controller captures independent transcripts and check results. A worker report supplies evidence to investigate.

## Reviewer prompt

~~~text
Review checkpoint {{task_id}} as the independent Content Machine moderator.

Review the frozen dispatch packet, the accepted baseline, actual changed source,
staged/unstaged/untracked content and controller-captured command evidence.
The proposed tree digest is {{candidate_tree_digest}}.
Use the normal app/API entry points and the supplied acceptance counterexamples.

Check all requested behavior, every changed caller, legacy input compatibility,
owner isolation, exact version approval, asynchronous ownership and recovery.
Verify target tests were collected and initially failed for the intended reason.
Rerun the focused tests independently. Select additional regression checks based
on the changed behavior. Keep broader suite results associated with this revision.
For UI work inspect the actual interaction and rendered evidence when required.
Check the scope allowlist, readable implementation, file-size constraints and cm-* use.
Evaluate every acceptance case and explain any unmet case.

Return accept, repair or blocked for this exact tree.
For repair, identify a concrete failing scenario, file/function, expected result,
smallest correction scope and a regression check.
Record missing environment credentials or browser/screen-reader evidence accurately.
Acceptance advances only after all required checks for this checkpoint are satisfied.
~~~

## Repair prompt

~~~text
Repair checkpoint {{task_id}}, attempt {{next_attempt}}.
Your previous work is preserved in {{worker_root}}.
The controller reviewed tree {{reviewed_tree_digest}}.

Observed failure
{{reproduction_steps}}
{{actual_behavior}}

Expected behavior
{{expected_behavior}}

Relevant location
{{file_and_function}}

Correction scope
{{repair_allowlist}}

Regression proof
{{test_to_add_or_fix}}
{{resolved_check_commands}}

Keep accepted prerequisite behavior intact.
Retain tests that represent the required user behavior.
Report the new diff, actual failing-then-passing evidence and remaining problems.
Submit the same checkpoint for review and wait.
~~~

The reviewer supplies a precise repair. A repeated identical failure triggers task splitting or an environment investigation. Three repair attempts is the initial controller policy.

## Reviewer acceptance record

~~~json
{
  "task_id": "C05",
  "request_nonce": "controller-supplied",
  "base_commit": "accepted-baseline",
  "reviewed_tree_digest": "digest-of-all-reviewed-content",
  "decision": "accept",
  "verified_test_ids": ["actual-collected-case"],
  "independent_check_artifacts": ["evidence/controller-pytest.txt"],
  "manual_scenarios": [
    {"id": "app-entry-resume", "status": "not_required_for_this_checkpoint"}
  ],
  "findings": [],
  "next_task": "C06"
}
~~~

The controller owns this record. Recompute the tree digest before advancing. A changed tree needs review of its new content.

## Example focused repair

A save response for item A replaces the editor after the user opened item B.

Reproduce by delaying A's save, opening B and then resolving A's response.
Expected behavior keeps B's text and status and associates A's acknowledgement with A.
Limit the repair to useWorkflowSession and its existing delayed-request test file.
Add a test asserting B's text and approval stay unchanged, then rerun that file.
Inspect the real request/item generation guard in the diff before acceptance.
