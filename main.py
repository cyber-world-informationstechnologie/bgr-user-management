"""Entry point for the BGR user management scripts (onboarding & offboarding)."""

import argparse
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def setup_logging(mode: str) -> None:
    """Set up logging to both console and file.

    Creates logs/ directory if it doesn't exist and logs to a timestamped file.
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Timestamped log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{mode}_{timestamp}.log"

    # Create logger with both console and file handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Console handler (INFO level)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (DEBUG level - captures everything)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Log startup info
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("BGR User Management — %s Process Started", mode.upper())
    logger.info("Log file: %s", log_file)
    logger.info("=" * 80)

    return logger


from src.onboarding import run_onboarding  # noqa: E402
from src.offboarding import run_offboarding  # noqa: E402


def main() -> None:
    """Parse arguments and run the appropriate process."""
    parser = argparse.ArgumentParser(
        prog="bgr-user-management",
        description="BGR User Onboarding & Offboarding Automation",
    )
    parser.add_argument(
        "mode",
        choices=["onboarding", "offboarding"],
        help="Choose the process to run",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for user input before exiting (useful for debugging)",
    )

    args = parser.parse_args()
    logger = setup_logging(args.mode)

    try:
        if args.mode == "onboarding":
            run_onboarding()
        elif args.mode == "offboarding":
            run_offboarding()
        logger.info("Process completed successfully")
    except Exception as e:
        logger.error("Process failed with exception: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        logger.info("=" * 80)
        if args.wait:
            input("Press Enter to exit...")


if __name__ == "__main__":
    main()
