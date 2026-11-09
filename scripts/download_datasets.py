"""Compatibility entry point for real, attributed multilingual data imports.

The old script generated illustrative samples with fabricated attestation counts.
Use the official data importer instead; original legacy files are not overwritten.
"""
from expand_datasets import download, build

if __name__ == "__main__":
    print("Downloading official language data into data/raw/expanded")
    download()
    build()
