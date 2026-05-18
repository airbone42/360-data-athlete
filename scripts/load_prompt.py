"""Load and resolve a prompt template (Layer-1 config injection applied).

Outputs the fully resolved template text to stdout — ready to use as
agent instructions without needing to manually substitute config placeholders.

Usage:
    python3 coach/scripts/load_prompt.py --name specialist_endurance
    python3 coach/scripts/load_prompt.py --name specialist_complementary
    python3 coach/scripts/load_prompt.py --name specialist_ninja
    python3 coach/scripts/load_prompt.py --name sub_lap_summarizer
    python3 coach/scripts/load_prompt.py --name final_coach_analysis
    python3 coach/scripts/load_prompt.py --name first_feedback
"""

from __future__ import annotations

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.prompt_loader import load_prompt


from app.utils.alerts import alert_on_failure


@alert_on_failure
def main() -> None:
    parser = argparse.ArgumentParser(description="Output resolved prompt template")
    parser.add_argument("--name", required=True, help="Prompt name e.g. specialist_endurance")
    args = parser.parse_args()

    cfg = load_prompt(args.name)
    print(f"# Prompt: {args.name}")
    print(f"# Model: {cfg.model} | Temp: {cfg.temperature} | MaxTokens: {cfg.max_tokens}")
    print()
    print(cfg.template)


if __name__ == "__main__":
    main()
