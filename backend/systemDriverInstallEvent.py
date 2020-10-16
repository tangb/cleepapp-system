#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemDriverInstallEvent(Event):
    """
    System.driver.install event
    This event is sent just before restart command is launched. It allows modules to perform something before.
    """

    EVENT_NAME = u'system.driver.install'
    EVENT_SYSTEM = True

    def __init__(self, bus, formatters_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
        """
        Event.__init__(self, bus, formatters_broker)

    def _check_params(self, params):
        """
        Check event parameters

        Args:
            params (dict): event parameters

        Return:
            bool: True if params are valid, False otherwise
        """
        keys = [
            u'drivertype',
            u'drivername',
            u'installing',
            u'success',
            u'message',
        ]
        return all(key in keys for key in params.keys())

