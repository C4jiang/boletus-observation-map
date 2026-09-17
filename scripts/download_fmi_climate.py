#!/usr/bin/env python3
"""Resumable download of FMI gridded daily observation NetCDF files."""
from __future__ import annotations

import concurrent.futures
import subprocess
from pathlib import Path

BASE_URL = "https://fmi-gridded-obs-daily-1km.s3.eu-west-1.amazonaws.com"
VARIABLES = {
    "RRday": "rrday",
    "Tday": "tday",
    "Tmin": "tmin",
    "Tmax": "tmax",
}
YEARS = range(2010, 2027)
DESTINATION = Path(__file__).resolve().parents[1] / "data" / "fmi_gridded_obs_daily_1km"


def remote_size(url: str) -> int:
    result = subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--location", "--head", url],
        check=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if line.lower().startswith("content-length:"):
            return int(line.split(":", 1)[1].strip())
    raise RuntimeError(f"No Content-Length received for {url}")


def download(variable: str, stem: str, year: int) -> str:
    filename = f"{stem}_{year}.nc"
    url = f"{BASE_URL}/Netcdf/{variable}/{filename}"
    target = DESTINATION / variable / filename
    partial = target.with_suffix(target.suffix + ".part")
    target.parent.mkdir(parents=True, exist_ok=True)
    expected = remote_size(url)
    if target.exists() and target.stat().st_size == expected:
        return f"SKIP {target.relative_to(DESTINATION)} ({expected} bytes)"
    if target.exists():
        target.unlink()
    subprocess.run(
        [
            "curl", "--fail", "--location", "--retry", "5", "--retry-all-errors",
            "--continue-at", "-", "--output", str(partial), url,
        ],
        check=True,
    )
    actual = partial.stat().st_size
    if actual != expected:
        raise RuntimeError(f"Size mismatch for {partial}: got {actual}, expected {expected}")
    partial.replace(target)
    return f"DONE {target.relative_to(DESTINATION)} ({actual} bytes)"


def main() -> None:
    jobs = [(variable, stem, year) for variable, stem in VARIABLES.items() for year in YEARS]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(download, *job) for job in jobs]
        for future in concurrent.futures.as_completed(futures):
            print(future.result(), flush=True)


if __name__ == "__main__":
    main()
