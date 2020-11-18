#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemDevicePoweroffEvent(Event):
    """
    System.device.poweroff event
    This event is sent just before poweroff command is launched. It allows modules to perform something before.
    """

    EVENT_NAME = 'system.device.poweroff'
    EVENT_PROPAGATE = False
    EVENT_PARAMS = ['delay']

    def __init__(self, bus, formatters_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
        """
        Event.__init__(self, bus, formatters_broker)

