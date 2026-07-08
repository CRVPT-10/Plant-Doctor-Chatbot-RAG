import os
import sys

# Add project root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.ingest import ingest_directory

if __name__ == "__main__":
    # Check if --rebuild is passed
    rebuild = "--rebuild" in sys.argv
    print(f"\nRunning Vector Index Builder (Force Rebuild: {rebuild})...")
    ingest_directory(force_rebuild=rebuild)
    print("Build index process completed.\n")
