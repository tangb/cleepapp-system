#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event

class SystemMonitoringCpuEvent(Event):
    """
    System.monitoring.cpu event
    """

    EVENT_NAME = 'system.monitoring.cpu'
    EVENT_PROPAGATE = False
    EVENT_PARAMS = ['system', 'cleep']
    EVENT_CHARTABLE = True

    def __init__(self, params):
        """
        Constructor

        Args:
            params (dict): event parameters
        """
        Event.__init__(self, params)

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
        cleep = float(params['cleep'])
        system = float(params['system'])
        others = float('{0:.2f}'.format(system - cleep))
        if others<0.0:
            others = 0.0
        idle = 100.0 - cleep - others

        return [
            {'field': 'cleep', 'value': cleep},
            {'field': 'others', 'value': others},
            {'field': 'idle', 'value': idle}
        ]

