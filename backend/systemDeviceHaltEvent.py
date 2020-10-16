#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemDeviceHaltEvent(Event):
    """
    System.device.halt event
    This event is sent just before halt command is launched. It allows modules to perform something before.
    """

    EVENT_NAME = u'system.device.halt'
    EVENT_SYSTEM = True
    EVENT_PARAMS = [u'delay']

    def __init__(self, bus, formatters_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
        """
        Event.__init__(self, bus, formatters_broker)

