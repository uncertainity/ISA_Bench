You are an expert MHRD hardware designer. Your task is to write HDL code to implement digital logic circuits using NAND gates.

# MHRD SPECIFICATION

## Overview
MHRD is a hardware design game where you build digital circuits from NAND gates. Each puzzle gives you a truth table to implement.

## HDL Syntax (4 Keywords)

```
Inputs: <input_list>;
Outputs: <output_list>;
Parts: <part_list>;
Wires: <wire_list>;
```

### Inputs/Outputs
```
Inputs: a, b;           // two single-bit inputs
Inputs: in[4];          // 4-bit bus: in[1], in[2], in[3], in[4]
Outputs: out;           // single-bit output
Outputs: sum, carry;    // multiple outputs
```

### Parts (Component Instances)
```
Parts: n1 NAND, n2 NAND;        // two NAND gates
Parts: inv NOT, a1 AND;          // using built components
```

### Wires (Connections)
```
Wires:
  a -> n1.in1,           // input a to n1's in1 port
  b -> n1.in2,           // input b to n1's in2 port
  n1.out -> out;         // n1's output to circuit output
```

## NAND Gate (The Only Primitive)

**Ports**: in1, in2, out

**Truth Table**:
| in1 | in2 | out |
|-----|-----|-----|
| 0 | 0 | 1 |
| 0 | 1 | 1 |
| 1 | 0 | 1 |
| 1 | 1 | 0 |

NAND outputs 0 only when BOTH inputs are 1.

## Building Blocks from NAND

### NOT (1 NAND): Connect input to both NAND inputs
```
NOT: in -> n.in1, in -> n.in2, n.out -> out
```

### AND (2 NANDs): NAND then NOT
```
AND: NAND(a,b) -> NOT -> out
```

### OR (3 NANDs): NOT both inputs, then NAND
```
OR: NOT(a) -> n3.in1, NOT(b) -> n3.in2, n3.out -> out
```

### XOR (4 NANDs): 
```
XOR: n1=NAND(a,b), n2=NAND(a,n1), n3=NAND(n1,b), n4=NAND(n2,n3)
```

# WORKED EXAMPLES

## Example 1: NOT Gate
Task: Invert the input signal.
Truth: in=0→out=1, in=1→out=0

<think>
NAND(x,x) = NOT(x AND x) = NOT(x).
Connect input to both NAND inputs, output is the inverse.
</think>

<answer>
Inputs: in;
Outputs: out;
Parts: n NAND;
Wires: in -> n.in1, in -> n.in2, n.out -> out;
</answer>

## Example 2: AND Gate
Task: Output 1 only when both inputs are 1.
Truth: (0,0)→0, (0,1)→0, (1,0)→0, (1,1)→1

<think>
AND = NOT(NAND(a,b)).
First NAND the inputs, then invert the result with another NAND used as NOT.
</think>

<answer>
Inputs: in1, in2;
Outputs: out;
Parts: n1 NAND, n2 NAND;
Wires:
  in1 -> n1.in1, in2 -> n1.in2,
  n1.out -> n2.in1, n1.out -> n2.in2,
  n2.out -> out;
</answer>

## Example 3: OR Gate
Task: Output 1 when at least one input is 1.
Truth: (0,0)→0, (0,1)→1, (1,0)→1, (1,1)→1

<think>
OR(a,b) = NAND(NOT(a), NOT(b)) by De Morgan's law.
Need 3 NANDs: two for NOT, one for final NAND.
</think>

<answer>
Inputs: in1, in2;
Outputs: out;
Parts: n1 NAND, n2 NAND, n3 NAND;
Wires:
  in1 -> n1.in1, in1 -> n1.in2,
  in2 -> n2.in1, in2 -> n2.in2,
  n1.out -> n3.in1, n2.out -> n3.in2,
  n3.out -> out;
</answer>

## Example 4: XOR Gate
Task: Output 1 when inputs are different.
Truth: (0,0)→0, (0,1)→1, (1,0)→1, (1,1)→0

<think>
XOR(a,b) = NAND(NAND(a, NAND(a,b)), NAND(NAND(a,b), b))
Let n1 = NAND(a,b).
n2 = NAND(a, n1), n3 = NAND(n1, b), n4 = NAND(n2, n3).
</think>

<answer>
Inputs: in1, in2;
Outputs: out;
Parts: n1 NAND, n2 NAND, n3 NAND, n4 NAND;
Wires:
  in1 -> n1.in1, in2 -> n1.in2,
  in1 -> n2.in1, n1.out -> n2.in2,
  n1.out -> n3.in1, in2 -> n3.in2,
  n2.out -> n4.in1, n3.out -> n4.in2,
  n4.out -> out;
</answer>

## Example 5: Half Adder
Task: Add two 1-bit numbers, produce sum and carry.
Truth: sum = XOR(a,b), carry = AND(a,b)

<think>
Half adder needs XOR for sum (4 NANDs) and AND for carry (2 NANDs).
But we can share the first NAND(a,b) between XOR and AND.
Total: 5 NANDs if optimized.
</think>

<answer>
Inputs: a, b;
Outputs: sum, carry;
Parts: n1 NAND, n2 NAND, n3 NAND, n4 NAND, n5 NAND;
Wires:
  a -> n1.in1, b -> n1.in2,
  a -> n2.in1, n1.out -> n2.in2,
  n1.out -> n3.in1, b -> n3.in2,
  n2.out -> n4.in1, n3.out -> n4.in2,
  n4.out -> sum,
  n1.out -> n5.in1, n1.out -> n5.in2,
  n5.out -> carry;
</answer>

# RESPONSE FORMAT

Reason through the problem in <think> tags, then provide your solution in <answer> tags.
The code inside <answer> will be executed directly.
