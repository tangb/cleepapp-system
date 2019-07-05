#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.event import Event

class SystemMonitoringMemoryEvent(Event):
    """
    System.monitoring.memory event
    """

    EVENT_NAME = u'system.monitoring.memory'
    EVENT_SYSTEM = True
    EVENT_PARAMS = [u'total', u'available', u'availablehr', u'raspiot']
    EVENT_CHARTABLE = True

    def __init__(self, bus, formatters_broker, events_broker):
        """ 
        Constructor

        Args:
            bus (MessageBus): message bus instance
            formatters_broker (FormattersBroker): formatters broker instance
            events_broker (EventsBroker): events broker instance
        """
        Event.__init__(self, bus, formatters_broker, events_broker)

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
        raspiot = float(params[u'raspiot'])
        total = float(params[u'total'])
        available = float(params[u'available'])
        others = total - available - raspiot

        return [
            {u'field': u'raspiot', u'value': raspiot},
            {u'field': u'others', u'value': others},
            {u'field': u'available', u'value': available}
        ]

