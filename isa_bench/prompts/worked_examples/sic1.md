You are an expert SIC-1 programmer. Your task is to write subleq programs that transform input sequences into specified output sequences.

# SIC-1 SPECIFICATION

## Architecture
SIC-1 is a Single Instruction Computer. The only instruction is `subleq` (subtract and branch if less than or equal to zero).

- **Memory**: 256 bytes (addresses 0-255), each byte is signed (-128 to 127)
- **Execution**: Programs start at address 0, each instruction is 3 bytes
- **I/O**: Special memory addresses for input/output

## The SUBLEQ Instruction

```
subleq A, B [, C]
```

**Semantics**:
1. `mem[B] = mem[B] - mem[A]`
2. If `mem[B] <= 0`: jump to address C
3. Else: continue to next instruction (PC += 3)

When C is omitted, it defaults to the next instruction (no branch).

## Special Addresses
| Address | Label | Behavior |
|---------|-------|----------|
| 253 | `@IN` | Reading returns next input value |
| 254 | `@OUT` | Writing outputs the value |
| 255 | `@HALT` | Any access halts execution |

## Assembler Syntax
```
@label:              ; define a label
subleq @a, @b, @c    ; subtract and branch
.data 42             ; data value
.data 'A'            ; character (ASCII)
@label+1             ; label with offset
-@label              ; negated address value
```

## Key Patterns

### Pattern 1: Output = 0 - Input (negate)
```
subleq @OUT, @IN     ; @OUT = @OUT - @IN = 0 - input = -input
```

### Pattern 2: Unconditional Jump
```
subleq @zero, @zero, @target   ; 0-0=0, always <=0, so always jumps
@zero: .data 0
```

### Pattern 3: Zero a Memory Location
```
subleq @x, @x        ; x = x - x = 0
```

### Pattern 4: Copy Value (A to B)
```
subleq @B, @B        ; B = 0
subleq @tmp, @tmp    ; tmp = 0
subleq @tmp, @A      ; tmp = 0 - A = -A
subleq @B, @tmp      ; B = 0 - (-A) = A
```

### Pattern 5: Add Two Values
```
; Result = A + B
subleq @result, @result  ; result = 0
subleq @tmp, @tmp        ; tmp = 0
subleq @tmp, @A          ; tmp = -A
subleq @result, @tmp     ; result = A
subleq @tmp, @tmp        ; tmp = 0
subleq @tmp, @B          ; tmp = -B
subleq @result, @tmp     ; result = A + B
```

# WORKED EXAMPLES

## Example 1: Negate Input
Task: Read a value, output its negation.
Input: [3] → Output: [-3]

<think>
subleq @OUT, @IN computes: @OUT = @OUT - @IN = 0 - input = -input.
This directly outputs the negated value. Need to loop for multiple inputs.
</think>

<answer>
@loop:
subleq @OUT, @IN
subleq @zero, @zero, @loop
@zero: .data 0
</answer>

## Example 2: Echo Input (Output = Input)
Task: Read a value, output it unchanged.
Input: [5] → Output: [5]

<think>
I can't output directly. I need to negate twice: tmp = -input, then output = -tmp = input.
1. Clear tmp, subtract input: tmp = -input
2. Clear output (it's always 0), subtract tmp: out = 0 - (-input) = input
</think>

<answer>
@loop:
subleq @tmp, @tmp
subleq @tmp, @IN
subleq @OUT, @tmp
subleq @zero, @zero, @loop
@zero: .data 0
@tmp: .data 0
</answer>

## Example 3: Add Two Inputs
Task: Read two values, output their sum.
Input: [3, 5] → Output: [8]

<think>
1. Get first input, store negated in tmp1: tmp1 = -a
2. Get second input, store negated in tmp2: tmp2 = -b  
3. result = 0, subtract tmp1: result = a
4. subtract tmp2: result = a + b
5. Negate result for output (output = 0 - result won't work directly)

Actually simpler: 
- tmp = -a (from input)
- result = a (0 - tmp)
- tmp = -b (from second input)
- result = a - (-b) = a + b
</think>

<answer>
@loop:
subleq @tmp, @tmp
subleq @tmp, @IN
subleq @result, @result
subleq @result, @tmp
subleq @tmp, @tmp
subleq @tmp, @IN
subleq @result, @tmp
subleq @OUT, @OUT
subleq @neg, @neg
subleq @neg, @result
subleq @OUT, @neg
subleq @zero, @zero, @loop
@zero: .data 0
@tmp: .data 0
@result: .data 0
@neg: .data 0
</answer>

# RESPONSE FORMAT

Reason through the problem in <think> tags, then provide your solution in <answer> tags.
The code inside <answer> will be executed directly.

Remember: subleq is counterintuitive. Think carefully about signs and the subtract-and-branch semantics.
