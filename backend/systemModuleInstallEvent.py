#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.event import Event

class SystemModuleInstallEvent(Event):
    """
    System.module.install event
    """

    EVENT_NAME = u'system.module.install'
    EVENT_SYSTEM = True
    EVENT_PARAMS = [u'module', u'status', u'stdout', u'stderr', u'updateprocess', u'process']

    def __init__(self, bus, formatters_broker, events_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
            events_broker (EventsBroker): events broker instance
        """
        Event.__init__(self, bus, formatters_broker, events_broker)

