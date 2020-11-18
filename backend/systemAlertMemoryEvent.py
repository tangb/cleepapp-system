#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemAlertMemoryEvent(Event):
    """
    System.alert.memory event
    """

    EVENT_NAME = 'system.alert.memory'
    EVENT_PROPAGATE = True
    EVENT_PARAMS = ['percent', 'threshold']

    def __init__(self, bus, formatters_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
        """
        Event.__init__(self, bus, formatters_broker)

