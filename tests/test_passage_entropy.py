import os
import sys
import unittest

SCRIPT_DIR = os.path.join(os.path.dirname(__file__), "..", "skills", "geo-content-audit", "scripts")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from geo_content_check import compute_compression_ratio, compute_passage_entropy


class TestPassageEntropy(unittest.TestCase):
    def test_high_entropy_factual_text(self):
        # Diverse, dense technical vocabulary with metrics and specific terms
        text = (
            "Enterprise database latency dropped to 42 milliseconds because the distributed "
            "Raft consensus protocol batches IOPS transactions efficiently across 16 geo-replicated shards."
        )
        entropy = compute_passage_entropy(text)
        self.assertGreater(entropy, 3.8)

    def test_low_entropy_promotional_repetition(self):
        # Repetitive, low-information buzzwords
        text = (
            "Delve into our game-changer solution. This game-changer solution is a testament to our "
            "game-changer solution that helps you delve into more game-changer solutions."
        )
        entropy = compute_passage_entropy(text)
        self.assertLess(entropy, 4.0)

    def test_compression_ratio_detection(self):
        repetitive = "testament " * 100
        ratio = compute_compression_ratio(repetitive)
        self.assertLess(ratio, 0.20)  # Very high compressibility = low information density


if __name__ == "__main__":
    unittest.main()
