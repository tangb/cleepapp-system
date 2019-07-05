#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.event import Event

class SystemDriverUninstallEvent(Event):
    """
    System.driver.uninstall event
    This event is sent just before restart command is launched. It allows modules to perform something before.
    """

    EVENT_NAME = u'system.driver.uninstall'
    EVENT_SYSTEM = True
    EVENT_PARAMS = [u'drivertype', u'drivername', u'uninstalling', u'success', u'message']

    def __init__(self, bus, formatters_broker, events_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
            events_broker (EventsBroker): events broker instance
        """
        Event.__init__(self, bus, formatters_broker, events_broker)

