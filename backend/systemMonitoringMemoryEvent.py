#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemMonitoringMemoryEvent(Event):
    """
    System.monitoring.memory event
    """

    EVENT_NAME = u'system.monitoring.memory'
    EVENT_SYSTEM = True
    EVENT_PARAMS = [u'total', u'available', u'availablehr', u'cleep']
    EVENT_CHARTABLE = True

    def __init__(self, bus, formatters_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
        """
        Event.__init__(self, bus, formatters_broker)

    def get_chart_values(self, params):
        """
        Returns chart values

        Args:
            params (dict): event parameters

        Returns:
            list: list of field+value ::

                [
                    {
                        field (string): field name,
                        value (any): value
                    },
                    ...
                ]

        """
        cleep = float(params[u'cleep'])
        total = float(params[u'total'])
        available = float(params[u'available'])
        others = total - available - cleep

        return [
            {u'field': u'cleep', u'value': cleep},
            {u'field': u'others', u'value': others},
            {u'field': u'available', u'value': available}
        ]

