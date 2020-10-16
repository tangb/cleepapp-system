#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemDeviceNeedrebootEvent(Event):
    """
    System.device.needreboot event
    """

    EVENT_NAME = u'system.device.needreboot'
    EVENT_SYSTEM = True
    EVENT_PARAMS = []

    def __init__(self, bus, formatters_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
        """
        Event.__init__(self, bus, formatters_broker)

