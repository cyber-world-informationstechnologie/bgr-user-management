"""Entry point for the BGR user onboarding script."""

import logging
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

from src.onboarding import run_onboarding  # noqa: E402

if __name__ == "__main__":
    run_onboarding()
