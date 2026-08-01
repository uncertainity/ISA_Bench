"""Focused test for LLM extraction, execution feedback, and retry behavior."""

from isa_bench.inference.agent import ISAAgent
from isa_bench.inference.client import CompletionResponse


class FakeClient:
    def __init__(self):
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        if len(self.calls) == 1:
            return CompletionResponse(
                content="<answer>INBOX</answer>",
                model="fake",
            )
        return CompletionResponse(
            content="""<think>Retry after feedback.</think>
<answer>
loop:
INBOX
OUTBOX
JUMP loop
</answer>""",
            model="fake",
        )


def test_agent_retries_with_execution_feedback():
    client = FakeClient()
    agent = ISAAgent(
        client,
        game="hrm",
        max_attempts=2,
        track="spec_only",
    )

    result = agent.solve(puzzle_id="hrm_level_1")

    assert result.solved
    assert result.attempts == 2
    assert result.track == "spec_only"
    assert len(result.system_prompt_sha256) == 64
    assert len(result.puzzle_prompt_sha256) == 64
    assert "Tests passed:" in client.calls[1][-1].content
