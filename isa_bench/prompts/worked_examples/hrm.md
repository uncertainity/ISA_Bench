You are an expert Human Resource Machine (HRM) programmer. Your task is to write programs that transform input sequences into specified output sequences.

# HRM SPECIFICATION

## Architecture
- **Hands (Accumulator)**: Holds exactly one value. Operations require data in hands.
- **Floor Tiles (Memory)**: Numbered slots (0, 1, 2, ...) for storing values.
- **INBOX**: Input conveyor. Reading when empty terminates the program.
- **OUTBOX**: Output conveyor. Program must produce exact expected sequence.
- **Values**: Integers (-999 to 999) or single uppercase letters (A-Z).

## Instruction Set

### Input/Output
| Instruction | Effect |
|-------------|--------|
| `INBOX` | Take next value from INBOX into hands. Empty INBOX terminates program. |
| `OUTBOX` | Put value from hands onto OUTBOX. Hands become empty. |

### Memory Access
| Instruction | Effect |
|-------------|--------|
| `COPYFROM n` | Copy value from tile n into hands. |
| `COPYFROM [n]` | Indirect: tile n contains address, copy from that address. |
| `COPYTO n` | Copy value from hands to tile n. Hands keep the value. |
| `COPYTO [n]` | Indirect addressing for destination. |

### Arithmetic
| Instruction | Effect |
|-------------|--------|
| `ADD n` | hands = hands + tile[n]. Works with [n] for indirect. |
| `SUB n` | hands = hands - tile[n]. Works with [n] for indirect. |
| `BUMPUP n` | Increment tile[n] by 1, copy result to hands. |
| `BUMPDN n` | Decrement tile[n] by 1, copy result to hands. |

### Control Flow
| Instruction | Effect |
|-------------|--------|
| `JUMP label` | Unconditional jump to label. |
| `JUMPZ label` | Jump if hands == 0. |
| `JUMPN label` | Jump if hands < 0. |

## Syntax
Labels are defined with a trailing colon on their own line:
```
myLabel:
    INBOX
    OUTBOX
    JUMP myLabel
```

# WORKED EXAMPLES

## Example 1: Mail Room (Echo All Inputs)
Task: Grab each thing from the INBOX and drop it into the OUTBOX.
Input: [1, 9, 4] → Output: [1, 9, 4]

<think>
I need to repeatedly: take from INBOX, put to OUTBOX, loop.
When INBOX is empty, the program terminates automatically.
</think>

<answer>
loop:
    INBOX
    OUTBOX
    JUMP loop
</answer>

## Example 2: Scrambler Handler (Reverse Pairs)
Task: Grab the first TWO things from INBOX and drop them in reverse order. Repeat.
Input: [4, 8, 'A', 'E'] → Output: [8, 4, 'E', 'A']

<think>
For each pair: get first value, store it in tile 0, get second value, output it, 
then retrieve first value from tile 0 and output it. Loop.
</think>

<answer>
loop:
    INBOX
    COPYTO 0
    INBOX
    OUTBOX
    COPYFROM 0
    OUTBOX
    JUMP loop
</answer>

## Example 3: Rainy Summer (Add Pairs)
Task: For each two things in INBOX, add them together and put result in OUTBOX.
Input: [3, 3, 1, 4] → Output: [6, 5]

<think>
Get first value, store in tile 0. Get second value (now in hands).
ADD 0 adds tile 0 to hands. Output result. Loop.
</think>

<answer>
loop:
    INBOX
    COPYTO 0
    INBOX
    ADD 0
    OUTBOX
    JUMP loop
</answer>

## Example 4: Zero Exterminator (Filter Non-Zeros)
Task: Send all non-zero values to OUTBOX. Discard zeros.
Input: [5, 0, -2, 0, 3] → Output: [5, -2, 3]

<think>
Get value. If zero, skip output and loop. If not zero, output then loop.
JUMPZ skips to loop start when hands == 0.
</think>

<answer>
loop:
    INBOX
    JUMPZ loop
    OUTBOX
    JUMP loop
</answer>

## Example 5: Tripler Room (Triple Each Value)
Task: For each value in INBOX, multiply it by 3 and output.
Input: [2, 5] → Output: [6, 15]

<think>
No MUL instruction, so I use ADD. Get value, store in tile 0.
ADD 0 doubles it (hands = hands + tile0). ADD 0 again triples it.
</think>

<answer>
loop:
    INBOX
    COPYTO 0
    ADD 0
    ADD 0
    OUTBOX
    JUMP loop
</answer>

# RESPONSE FORMAT

Reason through the problem in <think> tags, then provide your solution in <answer> tags.
The code inside <answer> will be executed directly.
