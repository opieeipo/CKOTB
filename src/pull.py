"""Source -> data/raw/. The only networked step besides model calls.

NIST SP 800-53 Rev. 5 OSCAL catalog (control text, parameters, 800-53A objectives)
and the FedRAMP Rev. 5 Moderate baseline workbook + SSP Appendix A template. The
GSA/fedramp-automation repo (OSCAL baselines) was removed from GitHub; FedRAMP's own
docs-legacy repo still publishes the same Rev. 5 baseline as a workbook. Cached
files are never fetched twice.
"""

import argparse
import hashlib
from pathlib import Path

import requests

from src.config import data_path, load_config

FEDRAMP = "https://raw.githubusercontent.com/FedRAMP/docs-legacy/main/overrides/assets/"
SOURCES = {
    "NIST_SP-800-53_rev5_catalog.json":
        "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json/"
        "NIST_SP-800-53_rev5_catalog.json",
    "FedRAMP_Security_Controls_Baseline.xlsx": FEDRAMP + "LEGACY%20FedRAMP_Security_Controls_Baseline.xlsx",
    "FedRAMP_SSP_AppendixA_Moderate.docx": FEDRAMP + "LEGACY%20SSP-Appendix-A-Moderate-FedRAMP-Security-Controls.docx",
}


def fetch(url: str, dest: Path, force: bool = False) -> Path:
    """Download url to dest unless it is already cached. Writes atomically."""
    if dest.exists() and dest.stat().st_size > 0 and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.rename(dest)
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, help="ignored; accepted for run_spike.sh symmetry")
    args = ap.parse_args()
    raw = data_path(load_config(), "raw")
    for name, url in SOURCES.items():
        p = fetch(url, raw / name, args.force)
        print(f"{hashlib.sha256(p.read_bytes()).hexdigest()[:16]}  {p.stat().st_size:>10}  {name}")


if __name__ == "__main__":
    main()
