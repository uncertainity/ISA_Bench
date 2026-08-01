"""BOX-256 puzzle schema."""

from dataclasses import dataclass


@dataclass
class Puzzle:
    """BOX-256 puzzle definition."""

    id: str
    name: str
    description: str
    target: bytes  # 256 bytes = 16x16 pixel target image
    index: int = 0

    def score(self, output: bytes) -> float:
        """Calculate pixel match score (0.0 to 1.0)."""
        if len(output) != 256 or len(self.target) != 256:
            return 0.0
        matches = sum(
            1 for a, b in zip(output, self.target) if (a & 0x0F) == (b & 0x0F)
        )
        return matches / 256.0

    def matches(self, output: bytes) -> bool:
        """Check if output matches target exactly."""
        return self.score(output) == 1.0
