#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.event import Event

class SystemSystemHaltEvent(Event):
    """
    System.system.halt event
    This event is sent just before halt command is launched. It allows modules to perform something before.
    """

    EVENT_NAME = u'system.system.halt'
    EVENT_SYSTEM = True
    EVENT_PARAMS = [u'delay']

    def __init__(self, bus, formatters_broker, events_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
            events_broker (EventsBroker): events broker instance
        """
        Event.__init__(self, bus, formatters_broker, events_broker)

