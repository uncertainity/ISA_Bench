# ISA Bench Software

ISA Bench is an executable harness for five instruction-set puzzle games. It
accepts game-language source code, parses it, runs it in a deterministic Python
emulator or simulator, and compares the resulting outputs with the puzzle
oracle.

The software release deliberately separates two operations:

- `isa-bench check` grades code that already exists. It makes no LLM call and
  does not use a prompt.
- `isa-bench solve` prompts an OpenAI-compatible model, extracts its code,
  grades it with the same checker, and optionally returns execution feedback for
  another attempt.

Supported games are Human Resource Machine (`hrm`), SIC-1 (`sic1`), TIS-100
(`tis100`), BOX-256 (`box256`), and MHRD (`mhrd`).

## Installation

Python 3.10 or newer is required. A plain virtual environment is sufficient;
Docker is not required.

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

Conda is also supported:

```bash
conda create -n isa-bench python=3.10 -y
conda activate isa-bench
python -m pip install -r requirements.txt
python -m pip install -e .
```

Verify the installation:

```bash
isa-bench list-games
python -m pytest -q
```

## Check an existing solution

Inspect available puzzles and their public specifications:

```bash
isa-bench list-puzzles --game hrm
isa-bench show --game hrm --puzzle hrm_level_1
```

Grade a source file:

```bash
isa-bench check \
  --game hrm \
  --puzzle hrm_level_1 \
  --solution examples/hrm_mail_room.hrm
```

The `examples/` directory contains one checker-verified solution for each game:

```bash
isa-bench check --game hrm --puzzle hrm_level_1 --solution examples/hrm_mail_room.hrm
isa-bench check --game sic1 --puzzle sic1_subleq_instruction_and_output --solution examples/sic1_subleq_instruction_and_output.sic
isa-bench check --game tis100 --puzzle tis100_signal_amplifier --solution examples/tis100_signal_amplifier.tis
isa-bench check --game box256 --puzzle box256_checkerboard --solution examples/box256_checkerboard.box
isa-bench check --game mhrd --puzzle mhrd_not --solution examples/mhrd_not.hdl
```

Use `--json` for a stable machine-readable result containing `success`, test
counts, parse/runtime errors, per-test outputs, and game-specific metrics:

```bash
isa-bench check \
  --game hrm \
  --puzzle hrm_level_1 \
  --solution examples/hrm_mail_room.hrm \
  --json
```

The checker returns exit status 0 for a correct solution, 1 for an incorrect or
non-executable solution, and 2 for command or resource errors. Pass `-` as the
solution path to read source code from standard input. Canonical execution
budgets are 10,000 cycles for BOX-256 and 100,000 steps/cycles for the other
instruction-based games; `--max-steps` provides an explicit override.

Submissions are game-specific DSL files, not Python programs. Suggested file
extensions are `.hrm`, `.sic`, `.tis`, `.box`, and `.hdl`.

## Ask an LLM to solve

`solve` works with Ollama and other OpenAI-compatible chat-completion endpoints.
Its default base URL is `http://localhost:11434/v1`.

```bash
isa-bench solve \
  --game hrm \
  --puzzle hrm_level_1 \
  --model qwen3-coder:30b \
  --track spec_only \
  --max-attempts 5 \
  --json
```

Configure another endpoint through flags or environment variables:

```bash
export ISA_BENCH_BASE_URL=https://example.invalid/v1
export ISA_BENCH_API_KEY=your-key
```

`OPENAI_BASE_URL` and `OPENAI_API_KEY` are accepted as fallbacks. API keys are
never included in result output.

Use a custom system prompt without changing the checker:

```bash
isa-bench solve \
  --game hrm \
  --puzzle hrm_level_1 \
  --model my-model \
  --system-prompt-file my_prompt.md \
  --retry 3
```

Every JSON solve result records the selected track, whether the system prompt
was overridden, and a SHA-256 hash of the exact system prompt.

## Prompt tracks

The exact reference system prompts are versioned under `isa_bench/prompts/`:

- `spec_only`: ISA semantics, syntax, puzzle specification, and response format;
  no worked solution programs or strategy demonstrations.
- `worked_examples`: the corresponding system prompt with worked solution
  demonstrations.

These are separate benchmark protocols. A custom prompt is supported, but it is
not a canonical run unless its exact contents match the released prompt hash.
The checker itself is independent of both tracks.

## Python API

```python
from isa_bench import check_solution

code = """\
loop:
    INBOX
    OUTBOX
    JUMP loop
"""

result = check_solution("hrm", "hrm_level_1", code)
assert result.success
print(result.tests_passed, result.tests_total)
```

For multi-attempt environment interaction:

```python
from isa_bench.openenv import ISAAction, ISAEnvironment

env = ISAEnvironment(game="hrm", max_attempts=5)
observation = env.reset(puzzle_id="hrm_level_1")
observation = env.step(ISAAction(code=code))
```

## Correctness path

```text
game source
   -> game parser / assembler
   -> Python VM / circuit simulator
   -> puzzle test cases or target state
   -> exact output comparison
   -> structured ExecutionResult
```

Correctness is determined by the per-game adapter. Reward shaping and LLM output
generation do not change the boolean `success` result.

## Repository scope

```text
isa_bench/games/       parsers, emulators/simulators, puzzle definitions
isa_bench/openenv/     common environment, adapters, results, rewards
isa_bench/prompts/     two frozen reference prompt tracks
isa_bench/inference/   optional OpenAI-compatible client and retry agent
isa_bench/cli.py       public command-line interface
tests/                 compact integration-focused release suite
```



## Testing policy

This initial release carries the smaller integration-focused suite covering the
public API, adapters, environment, rewards, prompts, retry behavior, and CLI.

Run the release suite with:

```bash
python -m pytest -q
```



