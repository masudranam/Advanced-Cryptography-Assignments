
import time
from typing import Sequence, Any

_U64_MASK = (1 << 64) - 1


def _rotl64(x: int, r: int) -> int:
    """Rotate left (64-bit)."""
    return ((x << r) & _U64_MASK) | (x >> (64 - r))


class XorWeyGen:

    def __init__(self, seed: int | None = None):
        if seed is None:
            seed = time.time_ns() & _U64_MASK
        self.reseed(seed)

    def _mix64(self, x: int) -> int:
        """SplitMix-style bit mixing."""
        x = (x + 0x9E3779B97F4A7C15) & _U64_MASK
        x ^= x >> 30
        x = (x * 0xBF58476D1CE4E5B9) & _U64_MASK
        x ^= x >> 27
        x = (x * 0x94D049BB133111EB) & _U64_MASK
        x ^= x >> 31
        return x & _U64_MASK

    def reseed(self, seed: int):
        """Reset internal state from seed."""
        seed &= _U64_MASK
        self._state = self._mix64(seed) or 1
        self._weyl = self._mix64(seed ^ 0xA5A5A5A5A5A5A5A5) or 1
        self._weyl_step = 0x9E3779B97F4A7C15  # odd constant
        self._count = 0

    def _advance(self) -> int:
        """Single state transition, returning a 64-bit integer."""
        s = self._state
        s ^= (s << 13) & _U64_MASK
        s ^= (s >> 7) & _U64_MASK
        s ^= (s << 17) & _U64_MASK
        s &= _U64_MASK
        self._state = s or 0xFFFFFFFFFFFFFFFF

        self._weyl = (self._weyl + self._weyl_step) & _U64_MASK
        z = (s + self._weyl + self._count) & _U64_MASK
        self._count = (self._count + 1) & _U64_MASK

        # nonlinear output mixing
        z ^= z >> 30
        z = (z * 0xBF58476D1CE4E5B9) & _U64_MASK
        z ^= z >> 27
        z = (z * 0x94D049BB133111EB) & _U64_MASK
        z ^= z >> 31
        return z & _U64_MASK

    # === Public API ===

    def next_u64(self) -> int:
        """Return a raw 64-bit unsigned integer."""
        return self._advance()

    def random(self) -> float:
        """Return float in [0, 1) with 53-bit precision."""
        return (self.next_u64() >> 11) / float(1 << 53)

    def randint(self, a: int, b: int) -> int:
        """Random integer in [a, b]."""
        if a > b:
            raise ValueError("Invalid range: a > b")
        rng = b - a + 1
        mask = (1 << rng.bit_length()) - 1
        while True:
            val = self.next_u64() & mask
            if val < rng:
                return a + val

    def choice(self, seq: Sequence[Any]) -> Any:
        """Return random element from non-empty sequence."""
        if not seq:
            raise IndexError("Cannot choose from empty sequence")
        return seq[self.randint(0, len(seq) - 1)]

    def shuffle(self, arr: list):
        """Fisher–Yates in-place shuffle."""
        n = len(arr)
        for i in range(n - 1, 0, -1):
            j = self.randint(0, i)
            arr[i], arr[j] = arr[j], arr[i]

if __name__ == "__main__":
    gen = XorWeyGen(123456789)
    print("Sample uint64 outputs:")
    for _ in range(5):
        print(hex(gen.next_u64()))

    print("\nSample float outputs:")
    for _ in range(5):
        print(gen.random())

    # Small distribution check
    N = 200_000
    ones = zeros = topbit = 0
    acc = 0.0
    g2 = XorWeyGen(987654321)
    for _ in range(N):
        v = g2.next_u64()
        acc += (v >> 11) / float(1 << 53)
        if v & 1:
            ones += 1
        else:
            zeros += 1
        topbit += (v >> 63) & 1

    print("\nStats for N =", N)
    print(f"mean ≈ {acc/N:.6f}")
    print(f"low bit: ones={ones} zeros={zeros}")
    print(f"top bit ones: {topbit}")
