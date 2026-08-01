"""ISA Agent that connects LLM to puzzle environments."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from hashlib import sha256
from typing import List, Optional

from ..openenv import ISAEnvironment, ISAAction, ISAObservation
from ..prompts import get_system_prompt
from .client import LLMClient, Message


@dataclass
class AgentResult:
    """Result from agent solving a puzzle."""

    puzzle_id: str
    puzzle_name: str
    solved: bool
    attempts: int
    final_reward: float
    best_reward: float
    codes: List[str] = field(default_factory=list)
    raw_responses: List[str] = field(default_factory=list)
    observations: List[ISAObservation] = field(default_factory=list)
    total_tokens: int = 0
    track: str = "spec_only"
    system_prompt_sha256: str = ""
    puzzle_prompt_sha256: str = ""
    error: Optional[str] = None


class ISAAgent:
    """Agent that uses an LLM to solve ISA puzzles.

    Example:
        client = LLMClient(model="qwen2.5-coder:7b")
        agent = ISAAgent(client, game="hrm")

        result = agent.solve(puzzle_id="hrm_level_1")
        print(f"Solved: {result.solved}, Attempts: {result.attempts}")
    """

    def __init__(
        self,
        client: LLMClient,
        game: str = "hrm",
        max_attempts: int = 5,
        verbose: bool = False,
        track: str = "spec_only",
        system_prompt: Optional[str] = None,
    ):
        """Initialize agent.

        Args:
            client: LLM client for inference
            game: Game identifier
            max_attempts: Maximum attempts per puzzle
            verbose: Print progress
            track: Canonical prompt track (``spec_only`` or ``worked_examples``)
            system_prompt: Optional exact prompt override for custom experiments
        """
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        self.client = client
        self.game = game
        self.max_attempts = max_attempts
        self.verbose = verbose
        self.track = track

        self.env = ISAEnvironment(game=game, max_attempts=max_attempts)
        self.system_prompt = (
            system_prompt
            if system_prompt is not None
            else get_system_prompt(game, track)
        )
        self.system_prompt_sha256 = sha256(
            self.system_prompt.encode("utf-8")
        ).hexdigest()

    def _format_puzzle_prompt(self, obs: ISAObservation) -> str:
        """Format puzzle description for LLM."""
        prompt = f"# Puzzle: {obs.puzzle_name}\n\n"
        prompt += f"{obs.puzzle_description}\n\n"

        if obs.available_commands:
            prompt += f"Available commands: {', '.join(obs.available_commands)}\n\n"

        if obs.par:
            prompt += f"Optimization targets: {obs.par}\n\n"

        prompt += "Write the solution code:"
        return prompt

    def _format_feedback_prompt(self, obs: ISAObservation) -> str:
        """Format feedback from failed attempt."""
        prompt = f"Your code did not solve the puzzle.\n\n"

        if obs.parse_error:
            prompt += f"Parse error: {obs.parse_error}\n\n"
        elif obs.runtime_error:
            prompt += f"Runtime error: {obs.runtime_error}\n\n"
        else:
            prompt += f"Tests passed: {obs.tests_passed}/{obs.tests_total}\n\n"

            if obs.test_results:
                prompt += "Test results:\n"
                for i, tr in enumerate(obs.test_results[:3]):  # Show first 3
                    status = "PASS" if tr.passed else "FAIL"
                    prompt += f"  {i+1}. [{status}] "
                    prompt += f"Input: {tr.input_values} -> "
                    prompt += f"Expected: {tr.expected_output}, "
                    prompt += f"Got: {tr.actual_output}\n"
                if len(obs.test_results) > 3:
                    prompt += f"  ... and {len(obs.test_results) - 3} more tests\n"
                prompt += "\n"

        prompt += f"Attempt {obs.attempt}/{obs.max_attempts}. Try again:"
        return prompt

    def _extract_code(self, response: str) -> str:
        """Extract code from LLM response.

        Handles various model output formats:
        - <answer>...</answer> tags (our v2 prompts)
        - <think>...</think> followed by code (phi4-reasoning, deepseek-r1)
        - ```...``` markdown code fences
        - Raw code (fallback)
        """
        import re

        text = response.strip()

        # 1. Try <answer> tags first (v2 prompt format)
        answer_match = re.search(r"<answer>\s*(.*?)\s*</answer>", text, re.DOTALL)
        if answer_match:
            return answer_match.group(1).strip()

        # 2. Handle <think>...</think> format (phi4-reasoning, etc.)
        #    Extract everything AFTER </think> tag
        if "</think>" in text:
            after_think = text.split("</think>", 1)[1].strip()
            if after_think:
                # The content after </think> might still have markdown fences
                if "```" in after_think:
                    return self._extract_from_markdown(after_think)
                # Or it might be raw code (possibly with explanation text before)
                # Try to find where the code starts (skip explanation lines)
                lines = after_think.split("\n")
                code_start = 0
                for i, line in enumerate(lines):
                    # Skip empty lines and lines that look like explanations
                    stripped = line.strip()
                    if stripped and not stripped.startswith(
                        ("Here", "Below", "The ", "This ", "Explanation", "•", "-", "*")
                    ):
                        code_start = i
                        break
                return "\n".join(lines[code_start:]).strip()

        # 3. Try markdown code fences
        if "```" in text:
            return self._extract_from_markdown(text)

        # 4. Fallback: return as-is (might be raw code)
        return text.strip()

    def _extract_from_markdown(self, text: str) -> str:
        """Extract code from markdown fences."""
        lines = text.split("\n")
        in_block = False
        code_lines = []
        for line in lines:
            if line.strip().startswith("```"):
                if in_block:
                    break  # End of code block
                in_block = True
                continue
            if in_block:
                code_lines.append(line)
        if code_lines:
            return "\n".join(code_lines).strip()
        return text.strip()

    def solve(
        self,
        puzzle_id: Optional[str] = None,
        puzzle_index: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> AgentResult:
        """Solve a puzzle using the LLM.

        Args:
            puzzle_id: Specific puzzle by ID
            puzzle_index: Specific puzzle by index
            seed: Random seed for puzzle selection

        Returns:
            AgentResult with solution details
        """
        obs = self.env.reset(puzzle_id=puzzle_id, puzzle_index=puzzle_index, seed=seed)

        if self.verbose:
            print(f"[{self.game.upper()}] Puzzle: {obs.puzzle_name}")

        puzzle_prompt = self._format_puzzle_prompt(obs)
        result = AgentResult(
            puzzle_id=obs.puzzle_id,
            puzzle_name=obs.puzzle_name,
            solved=False,
            attempts=0,
            final_reward=0.0,
            best_reward=0.0,
            track=self.track,
            system_prompt_sha256=self.system_prompt_sha256,
            puzzle_prompt_sha256=sha256(puzzle_prompt.encode("utf-8")).hexdigest(),
        )

        messages: List[Message] = [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=puzzle_prompt),
        ]

        while not obs.done:
            # Get LLM response
            try:
                response = self.client.chat(messages)
            except Exception as e:
                result.error = str(e)
                if self.verbose:
                    print(f"  LLM error: {e}")
                break

            result.total_tokens += response.usage.get("total_tokens", 0)

            # Save raw response and extract code
            result.raw_responses.append(response.content)
            code = self._extract_code(response.content)
            result.codes.append(code)

            if self.verbose:
                print(f"  Attempt {result.attempts + 1}: {len(code)} chars")

            # Execute code
            obs = self.env.step(ISAAction(code=code))
            result.observations.append(obs)
            result.attempts += 1
            result.final_reward = obs.reward
            result.best_reward = max(result.best_reward, obs.reward)

            if self.verbose:
                print(
                    f"    Tests: {obs.tests_passed}/{obs.tests_total}, Reward: {obs.reward:.2f}"
                )

            if obs.done:
                result.solved = (
                    obs.tests_passed == obs.tests_total and obs.tests_total > 0
                )
                break

            # Add feedback for next attempt
            messages.append(Message(role="assistant", content=response.content))
            messages.append(
                Message(role="user", content=self._format_feedback_prompt(obs))
            )

        if self.verbose:
            status = "SOLVED" if result.solved else "FAILED"
            print(f"  Result: {status} in {result.attempts} attempts")

        return result


def _solve_puzzle(client, game, puzzle_id, max_attempts, verbose, track, system_prompt):
    """Solve a single puzzle in its own agent instance (thread-safe)."""
    agent = ISAAgent(
        client,
        game=game,
        max_attempts=max_attempts,
        verbose=verbose,
        track=track,
        system_prompt=system_prompt,
    )
    return puzzle_id, agent.solve(puzzle_id=puzzle_id)


def run_evaluation(
    client: LLMClient,
    game: str = "hrm",
    puzzle_ids: Optional[List[str]] = None,
    num_puzzles: Optional[int] = None,
    max_attempts: int = 5,
    verbose: bool = True,
    track: str = "spec_only",
    system_prompt: Optional[str] = None,
    num_parallel: int = 1,
) -> List[AgentResult]:
    """Run evaluation on multiple puzzles.

    Args:
        client: LLM client
        game: Game identifier
        puzzle_ids: Specific puzzles to evaluate
        num_puzzles: Number of random puzzles (if puzzle_ids not specified)
        max_attempts: Max attempts per puzzle
        verbose: Print progress
        track: Canonical prompt track (``spec_only`` or ``worked_examples``)
        system_prompt: Optional exact prompt override for custom experiments
        num_parallel: Number of puzzles to solve concurrently (default=1)

    Returns:
        List of AgentResult for each puzzle
    """
    # Get puzzle list
    if puzzle_ids is None:
        env = ISAEnvironment(game=game)
        puzzles = env._adapter.load_puzzles()
        if num_puzzles:
            puzzles = puzzles[:num_puzzles]
        puzzle_ids = [env._adapter.get_puzzle_id(p) for p in puzzles]

    results_by_id = {}
    workers = min(num_parallel, len(puzzle_ids))

    if workers <= 1:
        agent = ISAAgent(
            client,
            game=game,
            max_attempts=max_attempts,
            verbose=verbose,
            track=track,
            system_prompt=system_prompt,
        )
        for pid in puzzle_ids:
            results_by_id[pid] = agent.solve(puzzle_id=pid)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _solve_puzzle,
                    client,
                    game,
                    pid,
                    max_attempts,
                    verbose,
                    track,
                    system_prompt,
                ): pid
                for pid in puzzle_ids
            }
            for future in as_completed(futures):
                pid, result = future.result()
                results_by_id[pid] = result

    results = [results_by_id[pid] for pid in puzzle_ids]

    if verbose:
        solved = sum(1 for r in results if r.solved)
        print(f"\n{'='*50}")
        print(f"Summary: {solved}/{len(results)} puzzles solved")
        print(f"Avg attempts: {sum(r.attempts for r in results) / len(results):.1f}")
        print(
            f"Avg best reward: {sum(r.best_reward for r in results) / len(results):.2f}"
        )

    return results
