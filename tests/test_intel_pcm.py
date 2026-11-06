from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from aab_framework.intel_pcm import read_intel_pcm_metrics


class IntelPcmParserTests(unittest.TestCase):
    def test_reads_system_totals_from_multisocket_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "intel_pcm_memory.csv"
            path.write_text(
                ",,SKT0,SKT0,SKT0,SKT0,SKT0,SKT1,SKT1,SKT1,SKT1,SKT1,System,System,System,System,System,System,System\n"
                "Date,Time,Mem Read (MB/s),Mem Write (MB/s),PMM_Read (MB/s), PMM_Write (MB/s),Memory (MB/s),Mem Read (MB/s),Mem Write (MB/s),PMM_Read (MB/s), PMM_Write (MB/s),Memory (MB/s),DRAMRead,DRAMWrite,PMMREAD,PMMWrite,Read,Write,Memory\n"
                "2026-11-05,06:00:00,3089.38,1371.19,0,0,4460.57,4076.51,2111.47,0,0,6187.98,7165.88,3482.67,0,0,7165.88,3482.67,10648.55\n",
                encoding="utf-8",
            )
            metrics = read_intel_pcm_metrics(path)

        self.assertEqual(metrics["memory_bw_gbps"], [10.64855])
        self.assertEqual(metrics["read_bw_gbps"], [7.16588])
        self.assertEqual(metrics["write_bw_gbps"], [3.48267])


if __name__ == "__main__":
    unittest.main()
