#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemDeviceRebootEvent(Event):
    """
    System.device.reboot event
    This event is sent just before reboot command is launched. It allows modules to perform something before.
    """

    EVENT_NAME = 'system.device.reboot'
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

