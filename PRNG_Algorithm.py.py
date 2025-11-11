#!/usr/bin/env python3
"""XorWeyMix PRNG
A lightweight, non-cryptographic pseudorandom number generator combining:
 - a xorshift-style state update,
 - a Weyl sequence increment (adds a fixed odd constant modulo 2^64),
 - a nonlinear scramble step inspired by SplitMix/PCG mix functions.

This is intended for simulation/games/experimentation only — NOT for cryptographic use.

API:
    pr = XorWeyMixPRNG(seed)
    pr.rand_uint64()    -> 64-bit unsigned integer
    pr.rand()           -> float in [0, 1)
    pr.randint(a, b)    -> integer in [a, b]
    pr.choice(seq)      -> random element from sequence
    pr.shuffle(list)    -> in-place shuffle
    pr.seed(seed)       -> reseed the generator

Design notes:
 - Uses a 128-bit internal state split into two uint64 values (state and weyl).
 - state evolves with xorshift-like ops then is mixed with weyl and scrambled.
 - The scramble uses shifts and multiplications to spread bits.
 - A single 'step' returns a 64-bit value.
 - Period is large (theoretical: period affected by Weyl increment and state transitions),
   but no formal proof provided. Statistical testing (e.g., TestU01/Dieharder) is recommended
   if used for serious simulations.
"""

from typing import Sequence, Any
import time
import struct

MASK64 = (1 << 64) - 1

def _rotl64(x, k):
    return ((x << k) & MASK64) | (x >> (64 - k))

class XorWeyMixPRNG:
    """Simple 64-bit PRNG combining xorshift, Weyl increment, and nonlinear mixing."""
    def __init__(self, seed: int = None):
        if seed is None:
            # use high-resolution time-based seed if none provided
            seed = int(time.time_ns()) & MASK64
        self.seed(seed)

    def seed(self, seed: int):
        # initialize two 64-bit states derived from the seed using splitmix64-like mixing
        def splitmix64(x):
            x = (x + 0x9E3779B97F4A7C15) & MASK64
            x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9 & MASK64
            x = (x ^ (x >> 27)) * 0x94D049BB133111EB & MASK64
            return x ^ (x >> 31)

        s = seed & MASK64
        self._state = splitmix64(s) or 1  # avoid zero state
        self._weyl = splitmix64(s ^ 0xFACEB00CDEADBEEF) or 1
        # choose a Weyl step (must be odd); it's fixed per instance but could be randomized
        self._weyl_step = 0x9E3779B97F4A7C15  # golden ratio-based
        # small counter to avoid trivial cycles
        self._counter = 0

    def _step(self) -> int:
        """Advance internal state and produce a 64-bit raw output."""
        # xorshift-ish update to _state
        x = self._state
        x ^= (x << 13) & MASK64
        x ^= (x >> 7) & MASK64
        x ^= (x << 17) & MASK64
        x &= MASK64
        self._state = x if x != 0 else 0xFFFFFFFFFFFFFFFF  # avoid zero sticky state

        # advance Weyl sequence (add constant modulo 2^64)
        self._weyl = (self._weyl + self._weyl_step) & MASK64

        # combine components
        z = (x + self._weyl + self._counter) & MASK64
        self._counter = (self._counter + 1) & MASK64

        # nonlinear scramble (inspired by SplitMix and PCG)
        z = (z ^ (z >> 30)) & MASK64
        z = (z * 0xBF58476D1CE4E5B9) & MASK64
        z = (z ^ (z >> 27)) & MASK64
        z = (z * 0x94D049BB133111EB) & MASK64
        z = z ^ (z >> 31)
        return z & MASK64

    def rand_uint64(self) -> int:
        """Return a 64-bit unsigned integer."""
        return self._step()

    def rand(self) -> float:
        """Return a float in [0, 1). Uses 53 bits of precision (IEEE double mantissa)."""
        # take top 53 bits of a 64-bit random value
        rv = self.rand_uint64() >> 11  # 64 - 53 = 11
        return rv / float(1 << 53)

    def randint(self, a: int, b: int) -> int:
        """Return integer in [a, b] inclusive. Uses rejection sampling to avoid bias."""
        if a > b:
            raise ValueError("a must be <= b")
        width = b - a + 1
        if width <= 0:
            # width too large for python int bounds? fallback
            return a + (self.rand_uint64() % (b - a + 1))
        # rejection sampling
        mask = (1 << (width.bit_length())) - 1
        while True:
            r = self.rand_uint64() & mask
            if r < width:
                return a + r

    def choice(self, seq: Sequence[Any]) -> Any:
        if not seq:
            raise IndexError('choice from empty sequence')
        idx = self.randint(0, len(seq)-1)
        return seq[idx]

    def shuffle(self, lst):
        """In-place Fisher-Yates shuffle."""
        n = len(lst)
        for i in range(n-1, 0, -1):
            j = self.randint(0, i)
            lst[i], lst[j] = lst[j], lst[i]

# Quick self-test when run as script
if __name__ == '__main__':
    pr = XorWeyMixPRNG(123456789)
    print('Sample uint64s:')
    for _ in range(5):
        print(hex(pr.rand_uint64()))
    print('\nSample floats:')
    for _ in range(5):
        print(pr.rand())

    # basic distribution checks
    pr = XorWeyMixPRNG(987654321)
    N = 200000
    s = 0.0
    ones = 0
    zeros = 0
    topbits = 0
    for _ in range(N):
        v = pr.rand_uint64()
        s += (v >> 11) / float(1 << 53)
        # count low bit distribution
        if v & 1:
            ones += 1
        else:
            zeros += 1
        topbits += (v >> 63) & 1
    mean = s / N
    print('\nBasic stats for N=%d' % N)
    print('mean ~', mean)
    print('low bit ones:', ones, 'zeros:', zeros)
    print('top bit ones count:', topbits)
