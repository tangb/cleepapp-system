#!/usr/bin/env python
# -*- coding: utf-8 -*-

from raspiot.libs.internals.event import Event

class SystemMonitoringCpuEvent(Event):
    """
    System.monitoring.cpu event
    """

    EVENT_NAME = u'system.monitoring.cpu'
    EVENT_SYSTEM = True
    EVENT_PARAMS = [u'system', u'raspiot']
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
            list: list of field+value or None if no value ::

                [
                    {
                        field (string): field name,
                        value (any): value
                    },
                    ...
                ]
             
        """
        raspiot = float(params[u'raspiot'])
        system = float(params[u'system'])
        others = float('{0:.2f}'.format(system - raspiot))
        if others<0.0:
            others = 0.0 
        idle = 100.0 - raspiot - others

        return [
            {u'field': u'raspiot', u'value': raspiot},
            {u'field': u'others', u'value': others},
            {u'field': u'idle', u'value': idle}
        ]

