"""
Nate — Real-Time Audio-In Audio-Out Conversational AI Assistant.

Entry point for the application.
Phase 1: Loads configuration, initializes logging, verifies dependencies.
"""

import sys

import config
from utils.logger import setup_logger
from utils.verify import run_verification


# ─── Startup Banner ──────────────────────────────────────────────────────────

BANNER: str = r"""
 ╔══════════════════════════════════════════════════════════╗
 ║                                                          ║
 ║     ███╗   ██╗ █████╗ ████████╗███████╗                  ║
 ║     ████╗  ██║██╔══██╗╚══██╔══╝██╔════╝                  ║
 ║     ██╔██╗ ██║███████║   ██║   █████╗                    ║
 ║     ██║╚██╗██║██╔══██║   ██║   ██╔══╝                    ║
 ║     ██║ ╚████║██║  ██║   ██║   ███████╗                  ║
 ║     ╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝   ╚══════╝                  ║
 ║                                                          ║
 ║     Real-Time Conversational AI Assistant                ║
 ║     Phase 1 — Project Initialization                     ║
 ║                                                          ║
 ╚══════════════════════════════════════════════════════════╝
"""


def main() -> None:
    """Application entry point.

    Displays the startup banner, validates configuration,
    initializes logging, and runs dependency verification.
    """
    print(BANNER)

    # ── Initialize Logger ────────────────────────────────────────────────
    logger = setup_logger(
        name="nate",
        level=config.LOG_LEVEL,
        log_dir=config.LOG_DIR,
    )

    logger.info("Starting Nate AI Assistant — Phase 1")

    # ── Validate Configuration ───────────────────────────────────────────
    logger.info("Validating configuration...")
    config_ok = config.validate_config()

    if config_ok:
        logger.info("Configuration valid. Gemini API key loaded.")
    else:
        logger.warning("Configuration incomplete. See errors above.")

    # ── Dependency Verification ──────────────────────────────────────────
    logger.info("Running dependency verification...")
    deps_ok = run_verification()

    # ── Summary ──────────────────────────────────────────────────────────
    if config_ok and deps_ok:
        logger.info("Nate is correctly configured and ready for Phase 2.")
    else:
        logger.warning("Setup incomplete. Resolve issues before proceeding.")

    logger.info("Phase 1 initialization complete.")


if __name__ == "__main__":
    main()
