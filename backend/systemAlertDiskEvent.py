#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemAlertDiskEvent(Event):
    """
    System.alert.disk event
    """

    EVENT_NAME = 'system.alert.disk'
    EVENT_PROPAGATE = True
    EVENT_PARAMS = ['percent', 'threshold', 'mountpoint']

    def __init__(self, bus, formatters_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
        """
        Event.__init__(self, bus, formatters_broker)

