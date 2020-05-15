#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemMonitoringCpuEvent(Event):
    """
    System.monitoring.cpu event
    """

    EVENT_NAME = u'system.monitoring.cpu'
    EVENT_SYSTEM = True
    EVENT_PARAMS = [u'system', u'cleep']
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
            list: list of field+value or None if no value ::

                [
                    {
                        field (string): field name,
                        value (any): value
                    },
                    ...
                ]
             
        """
        cleep = float(params[u'cleep'])
        system = float(params[u'system'])
        others = float('{0:.2f}'.format(system - cleep))
        if others<0.0:
            others = 0.0 
        idle = 100.0 - cleep - others

        return [
            {u'field': u'cleep', u'value': cleep},
            {u'field': u'others', u'value': others},
            {u'field': u'idle', u'value': idle}
        ]

