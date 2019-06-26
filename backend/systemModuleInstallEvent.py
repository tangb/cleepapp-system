#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.events.event import Event

class SystemModuleInstallEvent(Event):
    """
    System.module.install event
    """

    EVENT_NAME = u'system.module.install'
    EVENT_SYSTEM = True

    def __init__(self, bus, formatters_broker, events_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
            events_broker (EventsBroker): events broker instance
        """
        Event.__init__(self, bus, formatters_broker, events_broker)

    def _check_params(self, params):
        """
        Check event parameters

        Args:
            params (dict): event parameters

        Return:
            bool: True if params are valid, False otherwise
        """
        keys = [
            u'module',
            u'status',
            u'stdout',
            u'stderr',
            u'updateprocess',
            u'process'
        ]
        return all(key in keys for key in params.keys())

