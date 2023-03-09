#!/usr/bin/env python
# -*- coding: utf-8 -*-

from cleep.libs.internals.event import Event


class SystemMonitoringMemoryEvent(Event):
    """
    System.monitoring.memory event
    """

    EVENT_NAME = "system.monitoring.memory"
    EVENT_PROPAGATE = False
    EVENT_PARAMS = ["total", "available", "availablehr", "cleep"]
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
            list: list of field+value ::

                [
                    {
                        field (string): field name,
                        value (any): value
                    },
                    ...
                ]

        """
        cleep = float(params["cleep"])
        total = float(params["total"])
        available = float(params["available"])
        others = total - available - cleep

        return [
            {"field": "cleep", "value": cleep},
            {"field": "others", "value": others},
            {"field": "available", "value": available},
        ]
