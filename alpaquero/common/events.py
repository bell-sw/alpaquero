#  SPDX-FileCopyrightText: 2022 BellSoft
#  SPDX-License-Identifier:  AGPL-3.0-or-later

import abc
import logging

log = logging.getLogger('common.events')



class EventReceiver(abc.ABC):

    @abc.abstractmethod
    def start_event(self, msg):
        pass

    @abc.abstractmethod
    def stop_event(self):
        pass

    @abc.abstractmethod
    def add_log_line(self, msg):
        pass


class LoggingReceiver(EventReceiver):
    def start_event(self, msg):
        log.debug(msg)

    def stop_event(self):
        pass

    def add_log_line(self, msg):
        log.debug(msg)
