from pathlib import Path
from .ingest import ingest_files

def ingest_mnt_data(verbose=True):
    data_dir = Path("/mnt/data")
    files = sorted(list(data_dir.glob("*.md")) + list(data_dir.glob("*.txt")))
    if not files:
        if verbose:
            print("No files in /mnt/data to ingest.")
        return 0
    paths = [str(p) for p in files]
    return ingest_files(paths, verbose=verbose)

if __name__ == "__main__":
    ingest_mnt_data()
