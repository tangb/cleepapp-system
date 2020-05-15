#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemAlertMemoryEvent(Event):
    """
    System.alert.memory event
    """

    EVENT_NAME = u'system.alert.memory'
    EVENT_SYSTEM = True
    EVENT_PARAMS = [u'percent', u'threshold']

    def __init__(self, bus, formatters_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
        """
        Event.__init__(self, bus, formatters_broker)

