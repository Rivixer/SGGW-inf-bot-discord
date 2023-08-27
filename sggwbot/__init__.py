"""
SGGW-inf-bot-discord
--------------------

A Discord bot created to manage the Discord server for computer
science students at the Warsaw University of Life Sciences.

Features
--------
- role assigment based on reactions
- event management, such as a test or exam
- bot messaging, including embeds
- registering users with the student's email address
- setting bot's status
- management of voice channels
"""

__title__ = "SGGW-inf-bot-discord"
__author__ = "Wiktor Jaworski"
__license__ = "MIT"
__copyright__ = "Copyright 2023 Wiktor Jaworski"
__version__ = "0.7.4"

from . import console, errors, utils
from .sggw_bot import SGGWBot
