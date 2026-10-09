"""Write a detailed PDF from a saved results JSON file.

Does not screen resumes and does not change the JSON or the short text report.

    python pdf_report.py --input ./output/results.json --output ./output/results-detailed.pdf
"""

import argparse

from src.pdf_report import load_report, write_detailed_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a detailed PDF from screening results JSON.")
    parser.add_argument("--input", required=True, help="Existing results JSON")
    parser.add_argument("--output", required=True, help="PDF path to write")
    args = parser.parse_args()
    write_detailed_pdf(load_report(args.input), args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
