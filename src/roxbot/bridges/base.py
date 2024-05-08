#!/usr/bin/env python3
"""
base classes for roxbot.
Provides interface definitions for bridges, drivers etc.

Copyright (c) 2023 ROX Automation - Jev Kuznetsov
"""

import asyncio
import json
import logging
from logging.handlers import QueueHandler
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from roxbot.interfaces import JsonSerializableType


LOG_Q_LENGTH = 50

LOG_FMT = "%(asctime)s [%(name)s] %(levelname)s %(message)s"
DATE_FMT = "%H:%M:%S"


class CommandNotRegisteredError(Exception):
    """Exception raised when a command is not registered."""


class Bridge(ABC):
    """base class for creating websocket bridges"""

    def __init__(self, name: str = "Bridge") -> None:
        self._log = logging.getLogger(name)
        self._topic_callbacks: Dict[str, Callable] = {}  # topic callbacks

        # logging queue
        self._log_q: asyncio.Queue = asyncio.Queue(LOG_Q_LENGTH)
        self._log_handler: Optional[QueueHandler] = None

    @abstractmethod
    def send(self, topic: str, data: JsonSerializableType) -> None:
        """send data to topic

        Args:
            topic (str): topic to post on
            data (any): json serializable data payload
        """

    def register_callback(self, topic: str, fcn: Callable) -> None:
        """add callback to topic."""
        if topic in self._topic_callbacks:
            raise ValueError(f"Topic {topic} already has a callback registered")

        self._topic_callbacks[topic] = fcn

    def remove_callback(self, topic: str) -> None:
        """remove topic callback"""
        del self._topic_callbacks[topic]

    def _execute_command(self, message: str) -> Any:
        """execute command from message, message is a string for a simple command or
        a [cmd, args] string for a command with arguments. Returns the result of the command
        """
        self._log.debug("%s", f"executing {message=}")
        ret = None
        # try to parse message as json
        try:
            cmd, args = json.loads(message)
        except json.JSONDecodeError:  # if not json, assume simple command
            self._log.warning(
                "Message is not json, assuming simple command. Simple commands are deprecated. Use json format."
            )
            cmd = message
            args = None
        self._log.debug(f"{cmd=}, {args=}")

        try:
            # check if command is registered
            if cmd not in self._topic_callbacks:
                raise CommandNotRegisteredError(
                    f"command {cmd} is not registered, cannot execute"
                )

            if args is not None:
                self._log.info("%s", f"Running {cmd=} {args=}")
                ret = self._topic_callbacks[cmd](args)
            else:
                self._log.info("%s", f"Running {cmd=}")
                ret = self._topic_callbacks[cmd]()

        except CommandNotRegisteredError as e:
            self._log.warning("%s", e)
        except Exception as e:  # pylint: disable=broad-except
            self._log.exception("%s", e)

        return ret

    @abstractmethod
    async def main(self) -> None:
        """main coroutine"""
