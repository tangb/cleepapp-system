#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemDriverInstallEvent(Event):
    """
    System.driver.install event
    This event is sent just before restart command is launched. It allows modules to perform something before.
    """

    EVENT_NAME = 'system.driver.install'
    EVENT_PROPAGATE = False
    EVENT_PARAMS = ['drivertype', 'drivername', 'installing', 'success', 'message']

    def __init__(self, bus, formatters_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
        """
        Event.__init__(self, bus, formatters_broker)

