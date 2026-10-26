import argparse
import logging
import math

from dcp_tools.gcp_utilities import KGSettings, get_kg_settings
from dcp_tools.gcp_utilities.ingestion import DEFAULT_POLL_INTERVAL, wait_for_ingestion

logger = logging.getLogger(__name__)


def load_settings_from_args(args: argparse.Namespace) -> KGSettings:
    if args.settings_file:
        return get_kg_settings(source="json", file=args.settings_file)
    return get_kg_settings(env_file=args.env_file)


def _seconds(text: str) -> float:
    try:
        seconds = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"invalid number of seconds: {text!r}"
        ) from None
    if not math.isfinite(seconds):
        raise argparse.ArgumentTypeError("must be a finite number of seconds")
    return seconds


def _non_negative_seconds(text: str) -> float:
    seconds = _seconds(text)
    if seconds < 0:
        raise argparse.ArgumentTypeError("must not be negative")
    return seconds


def _positive_seconds(text: str) -> float:
    seconds = _seconds(text)
    if seconds <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return seconds


def add_wait_arguments(parser: argparse.ArgumentParser) -> None:
    """Register ``--wait``, ``--timeout`` and ``--poll-interval``."""
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Block until the ingestion execution finishes; exit non-zero if "
        "it does not succeed",
    )
    parser.add_argument(
        "--timeout",
        type=_non_negative_seconds,
        metavar="SECONDS",
        help="With --wait, give up and exit non-zero after this many seconds. "
        "Waits indefinitely if omitted",
    )
    parser.add_argument(
        "--poll-interval",
        type=_positive_seconds,
        metavar="SECONDS",
        help="With --wait, seconds between state checks "
        f"(default: {DEFAULT_POLL_INTERVAL})",
    )


def check_wait_arguments(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> None:
    """Exit with a usage error on ``--timeout`` or ``--poll-interval`` without ``--wait``."""
    if args.wait:
        return
    for flag, value in (
        ("--timeout", args.timeout),
        ("--poll-interval", args.poll_interval),
    ):
        if value is not None:
            parser.error(f"{flag} requires --wait")


def wait_for_execution(
    settings: KGSettings, execution_name: str, args: argparse.Namespace
) -> int:
    """Wait for an ingestion execution and return the command's exit code."""
    poll_interval = (
        DEFAULT_POLL_INTERVAL if args.poll_interval is None else args.poll_interval
    )
    try:
        execution_state = wait_for_ingestion(
            settings, execution_name, timeout=args.timeout, poll_interval=poll_interval
        )
    except TimeoutError as e:
        logger.error(str(e))
        return 1

    if execution_state.state == "SUCCEEDED":
        logger.info(f"Execution '{execution_name}' succeeded")
        return 0
    message = f"Execution '{execution_name}' finished as {execution_state.state}"
    if execution_state.error:
        message += f": {execution_state.error}"
    logger.error(message)
    return 1
