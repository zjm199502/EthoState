import tempfile
import unittest
from pathlib import Path
import numpy as np
from analysis_core import analyze, read_matrix
from report import summary


class AnalysisTests(unittest.TestCase):
    def test_decode_and_gaps(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"trace.csv"
            rng = np.random.default_rng(42)
            truth = np.repeat([0, 1, 0, 1], 30)
            values = rng.poisson(np.where(truth==0, 4, 120))
            lines = ["A,B"]
            for i, value in enumerate(values):
                lines.append(f"{value if i!=10 else ''},{values[-i-1]}")
            path.write_text("\n".join(lines))
            result = analyze(path)
        names, raw, states, posterior, meta = result
        self.assertEqual(names, ["A","B"])
        self.assertEqual(meta["sequences"], 3)
        self.assertEqual(states[10,0], -1)
        self.assertTrue(np.isnan(posterior[10,0]))
        self.assertGreater((states[:,0]==truth).mean(), .98)
        np.testing.assert_allclose(np.sum(meta["transition"],axis=1),1)
        self.assertEqual(summary(result,1)[0][-1],3)

    def test_no_header_and_invalid_cells(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"noheader.csv"
            path.write_text("1,2\n3,4")
            self.assertEqual(read_matrix(path)[1].shape, (2,2))
            path.write_text("1,2\n3,text")
            with self.assertRaisesRegex(ValueError,"第 2 行"):
                read_matrix(path)


if __name__ == "__main__":
    unittest.main()

