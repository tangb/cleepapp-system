#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event
import logging

class SystemCleepUpdateEvent(Event):
    """
    System.cleep.update event
    """

    EVENT_NAME = u'system.cleep.update'
    EVENT_SYSTEM = True
    EVENT_PARAMS = [u'status']

    def __init__(self, bus, formatters_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
        """
        Event.__init__(self, bus, formatters_broker)

        #logger
        self.logger = logging.getLogger(self.__class__.__name__)

