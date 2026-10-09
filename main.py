"""CLI: python main.py --input ./resumes --output ./output/results.json"""

import argparse
import logging

from dotenv import load_dotenv

from src.pipeline import screen_batch
from src.report import finalize, render_report, write_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Screen resumes for a Python and AI internship.")
    parser.add_argument("--input", required=True, help="Folder of PDF resumes")
    parser.add_argument("--output", required=True, help="Path to write results JSON")
    return parser


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args()
    report = finalize(screen_batch(args.input))
    write_results(report, args.output)
    print(render_report(report))
    print(f"Wrote {args.output}")
    print(f"Wrote {args.output.rsplit('.', 1)[0]}.txt")


if __name__ == "__main__":
    main()
