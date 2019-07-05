#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.event import Event

class SystemSystemRestartEvent(Event):
    """
    System.system.restart event
    This event is sent just before restart command is launched. It allows modules to perform something before.
    """

    EVENT_NAME = u'system.system.restart'
    EVENT_SYSTEM = True
    EVENT_PARAMS = [u'delay']

    def __init__(self, bus, formatters_factory, events_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_factory (FormattersFactory): formatters factory instance
            events_broker (EventsBroker): events broker instance
        """
        Event.__init__(self, bus, formatters_factory, events_broker)

