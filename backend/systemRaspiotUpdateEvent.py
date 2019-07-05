#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.event import Event
import logging

class SystemRaspiotUpdateEvent(Event):
    """
    System.raspiot.update event
    """

    EVENT_NAME = u'system.raspiot.update'
    EVENT_SYSTEM = True
    EVENT_PARAMS = [u'status']

    def __init__(self, bus, formatters_broker, events_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
            events_broker (EventsBroker): events broker instance
        """
        Event.__init__(self, bus, formatters_broker, events_broker)

        #logger
        self.logger = logging.getLogger(self.__class__.__name__)

