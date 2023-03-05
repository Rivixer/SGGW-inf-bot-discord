# SPDX-License-Identifier: MIT
"""Main module for SGGWBot."""

import logging

from sggwbot.sggw_bot import SGGWBot


def main() -> None:
    """Run the bot."""
    logging.basicConfig(
        level=logging.WARN,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%d.%m.%y %H:%M:%S",
    )
    bot = SGGWBot()
    bot.main()


if __name__ == "__main__":
    main()
