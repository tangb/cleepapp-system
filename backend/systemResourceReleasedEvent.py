#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemResourceReleasedEvent(Event):
    """
    system.resource.released event
    """

    EVENT_NAME = u'system.resource.released'
    EVENT_SYSTEM = True
    EVENT_PARAMS = [u'resource', u'module']

    def __init__(self, bus, formatters_broker):
        """
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
        """
        Event.__init__(self, bus, formatters_broker)

