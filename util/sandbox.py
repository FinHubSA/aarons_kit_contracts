from os import environ
import pty
from subprocess import run


def call_sandbox_command(*args):
    """Call and return sandbox command composed from provided arguments."""

    return run(
        [environ.get("ALGORAND_SANDBOX_PATH"), *args],
        stdin=pty.openpty()[1],
        capture_output=True,
    )
