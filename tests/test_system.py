#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import logging
import sys
sys.path.append('../')
from backend.system import System
from cleep.exception import InvalidParameter, MissingParameter, CommandError, Unauthorized
from cleep.libs.tests import session
from mock import Mock, patch, MagicMock

class VirtualMemory():
    total = 512
    available = 256

class Datetime():
    year = 2010
    month = 10
    day = 10
    hour = 10
    minute = 10
    second = 10

mock_psutil = MagicMock()
mock_psutil.boot_time = Mock(return_value=1602175545.2728713)
mock_psutil.cpu_percent = Mock(return_value=150)
mock_psutil.virtual_memory = Mock(return_value=VirtualMemory())
mock_psutil.Process.return_value.cpu_percent = Mock(return_value=120)
mock_psutil.Process.return_value.memory_info = Mock(return_value=[400,])
mock_cleepconf = MagicMock()

@patch('backend.system.psutil', mock_psutil)
@patch('backend.system.CleepConf', mock_cleepconf)
class TestSystem(unittest.TestCase):

    def setUp(self):
        self.session = session.TestSession()
        logging.basicConfig(level=logging.DEBUG, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

    def tearDown(self):
        mock_psutil.reset_mock()
        mock_psutil.boot_time.reset_mock()
        mock_psutil.cpu_percent.reset_mock()
        mock_psutil.virtual_memory.reset_mock()
        mock_psutil.Process.return_value.cpu_percent.reset_mock()
        mock_psutil.Process.return_value.memory_info.reset_mock()
        mock_cleepconf.reset_mock()
        self.session.clean()

    def init_session(self, start_module=True):
        self.module = self.session.setup(System)
        if start_module:
            self.session.start_module(self.module)

    def test_configure(self):
        self.init_session(start_module=False)
        self.module.get_module_devices = Mock(return_value={
            '123-123': {'type': 'monitor'},
            '456-456': {'type': 'monitorcpu'},
            '789-789': {'type': 'monitormemory'},
        })
        self.module._add_device = Mock()
        self.module._configure_crash_report = Mock()
        self.module._set_not_renderable_events = Mock()

        self.session.start_module(self.module)

        mock_psutil.Process.assert_called()
        mock_psutil.Process.return_value.cpu_percent.assert_called()
        self.assertEqual(self.module._add_device.call_count, 0)
        self.assertEqual(self.module._System__monitor_memory_uuid, '789-789')
        self.assertEqual(self.module._System__monitor_cpu_uuid, '456-456')
        self.module._configure_crash_report.assert_called_with(True)
        self.module._set_not_renderable_events.assert_called()

    def test_configure_create_all_devices(self):
        self.init_session(start_module=False)
        self.module.get_module_devices = Mock(return_value={})
        self.module._add_device = Mock()

        self.session.start_module(self.module)

        self.assertEqual(self.module._add_device.call_count, 3)

    def test_configure_create_missing_devices(self):
        self.init_session(start_module=False)
        self.module.get_module_devices = Mock(return_value={
            '123-123': {'type': 'monitor'},
            '789-789': {'type': 'monitormemory'},
        })
        self.module._add_device = Mock()

        self.session.start_module(self.module)

        self.assertEqual(self.module._add_device.call_count, 1)

    def test_configure_disable_crash_report_at_startup(self):
        self.init_session(start_module=False)
        self.module.get_module_devices = Mock(return_value={
            '123-123': {'type': 'monitor'},
            '456-456': {'type': 'monitorcpu'},
            '789-789': {'type': 'monitormemory'},
        })
        self.module._configure_crash_report = Mock()
        self.module._get_config_field = Mock(return_value=False)

        self.session.start_module(self.module)

        self.module._configure_crash_report.assert_called_with(False)

    def test_configure_crash_report_enable(self):
        self.init_session()

        self.module._configure_crash_report(True)
        self.assertTrue(self.session.crash_report.enable.called)
        self.assertFalse(self.session.crash_report.disable.called)

    def test_configure_crash_report_disable(self):
        self.init_session()
        self.session.crash_report.is_enabled = Mock(return_value=False)

        self.module._configure_crash_report(False)
        self.assertEqual(self.session.crash_report.enable.call_count, 1) # called during _configure
        self.assertTrue(self.session.crash_report.disable.called)

    def test_get_module_config(self):
        self.init_session()
        mock_cleepconf.is_system_debugged = Mock(return_value=True)
        mock_cleepconf.is_trace_enabled = Mock(return_value=True)

        config = self.module.get_module_config()
        logging.debug('Config: %s' % config)
        self.assertEqual(
            sorted(['needrestart', 'version', 'eventsnotrenderable', 'debug', 'cleepbackupdelay', 'monitoring', 'ssl', 'auth', 'rpcport', 'crashreport', 'needreboot', 'devices']),
            sorted(config.keys()),
        )

    def test_get_module_devices(self):
        self.init_session()

        devices = self.module.get_module_devices()
        logging.debug('Devices: %s' % devices)
        self.assertEqual(len(devices), 3)
        for device_uuid, device in devices.items():
            if device['type'] == 'monitor':
                self.assertEqual(
                    sorted(['type', 'name', 'uptime', 'memory', 'cpu', 'uuid']),
                    sorted(device.keys()),
                )
                break

    def test_event_received_need_restart(self):
        self.init_session()

        self.module.event_received({
            'event': 'system.system.needrestart',
            'params': {}
        })
        
        self.assertTrue(self.module._System__need_restart)

    def test_event_received_need_reboot(self):
        self.init_session()
        self.module._set_config_field = Mock()

        self.module.event_received({
            'event': 'system.system.needreboot',
            'params': {}
        })
        
        self.module._set_config_field.assert_called_with('needreboot', True)

    def test_event_received_backup_config(self):
        self.init_session()
        self.module.backup_cleep_config = Mock()

        self.module.event_received({
            'event': 'parameters.time.now',
            'params': {
                'minute': 5
            }
        })
        self.assertFalse(self.module.backup_cleep_config.called)

        self.module.event_received({
            'event': 'parameters.time.now',
            'params': {
                'minute': 15
            }
        })
        self.module.backup_cleep_config.assert_called()

    def test_set_monitoring(self):
        self.init_session()
        self.module._set_config_field = Mock(return_value=True)

        self.module.set_monitoring(True)
    
        self.module._set_config_field.assert_called_with('monitoring', True)

    def test_set_monitoring_failed(self):
        self.init_session()
        self.module._set_config_field = Mock(return_value=False)

        with self.assertRaises(CommandError) as cm:
            self.module.set_monitoring(True)
        self.assertEqual(str(cm.exception), 'Unable to save configuration')
    
    def test_set_monitoring_exception(self):
        self.init_session()

        with self.assertRaises(MissingParameter) as cm:
            self.module.set_monitoring(None)
        self.assertEqual(str(cm.exception), 'Parameter "monitoring" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_monitoring('ola')
        self.assertEqual(str(cm.exception), 'Parameter "monitoring" is invalid')

    def test_get_monitoring(self):
        self.init_session()
        self.module._get_config_field = Mock(return_value=True)

        self.assertTrue(self.module.get_monitoring())

    @patch('backend.system.Console')
    def test_reboot_device(self, mock_console):
        self.init_session()
        self.module.backup_cleep_config = Mock()

        self.module.reboot_device(delay=10.0)
        
        self.module.backup_cleep_config.assert_called()
        mock_console.return_value.command_delayed.assert_called_with('reboot', 10.0)
        self.assertTrue(self.session.event_called('system.device.reboot'))

    @patch('backend.system.Console')
    def test_halt_device(self, mock_console):
        self.init_session()
        self.module.backup_cleep_config = Mock()

        self.module.halt_device(delay=10.0)
        
        self.module.backup_cleep_config.assert_called()
        mock_console.return_value.command_delayed.assert_called_with('halt', 10.0)
        self.assertTrue(self.session.event_called('system.device.halt'))

    @patch('backend.system.Console')
    def test_restart_cleep(self, mock_console):
        self.init_session()
        self.module.backup_cleep_config = Mock()

        self.module.restart_cleep(delay=10.0)
        
        self.module.backup_cleep_config.assert_called()
        mock_console.return_value.command_delayed.assert_called_with('/etc/cleep/cleephelper.sh restart', 10.0)
        self.assertTrue(self.session.event_called('system.cleep.restart'))

    def test_get_memory_usage(self):
        self.init_session()

        usage = self.module.get_memory_usage()
        logging.debug('Usage: %s' % usage)

        self.assertEqual(usage, {
            'total': 512,
            'cleep': 400,
            'available': 256,
            'availablehr': '256B',
        })

    def test_get_cpu_usage(self):
        self.init_session()

        usage = self.module.get_cpu_usage()
        logging.debug('Cpu usage: %s' % usage)

        self.assertEqual(sorted(['system', 'cleep']), sorted(usage.keys()))
        self.assertEqual(usage['system'], 100)
        self.assertEqual(usage['cleep'], 100)

    @patch('time.time', Mock(return_value=1602175845.2728713))
    def test_get_uptime(self):
        self.init_session()

        uptime = self.module.get_uptime()
        logging.debug('Uptime: %s' % uptime)

        self.assertEqual(sorted(['uptime', 'uptimehr']), sorted(uptime.keys()))
        self.assertEqual(uptime['uptime'], 300)
        self.assertEqual(uptime['uptimehr'], '0d 0h 5m')

    def test_monitoring_cpu_task_enabled(self):
        self.init_session()
        self.module._get_config_field = Mock(return_value=True)

        self.module._monitoring_cpu_task()
        
        self.assertTrue(self.session.event_called('system.monitoring.cpu'))

    def test_monitoring_cpu_task_disabled(self):
        self.init_session()
        self.module._get_config_field = Mock(return_value=False)

        self.module._monitoring_cpu_task()
        
        self.assertFalse(self.session.event_called('system.monitoring.cpu'))

    def test_monitoring_memory_task_enabled(self):
        self.init_session()
        self.module._get_config_field = Mock(return_value=True)
        self.module.get_memory_usage = Mock(return_value={
            'total': 512,
            'available': 256,
        })

        self.module._monitoring_memory_task()

        self.assertFalse(self.session.event_called('system.alert.memory'))
        self.assertTrue(self.session.event_called('system.monitoring.memory'))

    def test_monitoring_memory_task_disabled(self):
        self.init_session()
        self.module._get_config_field = Mock(return_value=False)
        self.module.get_memory_usage = Mock(return_value={
            'total': 512,
            'available': 256,
        })

        self.module._monitoring_memory_task()

        self.assertFalse(self.session.event_called('system.alert.memory'))
        self.assertFalse(self.session.event_called('system.monitoring.memory'))

    def test_monitoring_memory_send_alert(self):
        self.init_session()
        self.module._get_config_field = Mock(return_value=True)
        self.module.get_memory_usage = Mock(return_value={
            'total': 500,
            'available': 50,
        })

        self.module._monitoring_memory_task()

        self.assertTrue(self.session.event_called('system.alert.memory'))
        logging.debug('Event params: %s' % self.session.get_last_event_params('system.alert.memory'))
        self.assertTrue(self.session.event_called_with('system.alert.memory', {'percent': 90.0, 'threshold': 80.0}))

    @patch('os.path.exists', Mock(return_value=True))
    @patch('backend.system.datetime')
    @patch('backend.system.ZipFile')
    def test_download_logs(self, mock_zipfile, mock_datetime):
        mock_datetime.now = Mock(return_value=Datetime())
        self.init_session()

        logs = self.module.download_logs()
        logging.debug('Logs: %s' % logs)

        self.assertEqual(logs['filename'], 'cleep_20101010_101010.zip')
        mock_zipfile.return_value.write.assert_called_with(session.AnyArg(), 'cleep.log')
        mock_zipfile.return_value.close.assert_called()

    @patch('os.path.exists', Mock(side_effect=[True, True, True, True, False]))
    def test_download_logs_exception(self):
        self.init_session()

        with self.assertRaises(CommandError) as cm:
            self.module.download_logs()
        self.assertEqual(str(cm.exception), 'Logs file doesn\'t exist')

    @patch('os.path.exists', Mock(return_value=True))
    def test_get_logs(self):
        self.init_session()
        lines = ['line1', 'line2']
        self.session.cleep_filesystem.read_data = Mock(return_value=lines)

        logs = self.module.get_logs()
        logging.debug('Logs: %s' % logs)
    
        self.assertEqual(logs, lines)

    @patch('os.path.exists', Mock(side_effect=[True, True, True, True, False]))
    def test_get_logs_not_exist(self):
        self.init_session()
        lines = ['line1', 'line2']
        self.session.cleep_filesystem.read_data = Mock(return_value=lines)

        logs = self.module.get_logs()
        logging.debug('Logs: %s' % logs)
    
        self.assertEqual(logs, [])

    @patch('os.path.exists', Mock(return_value=True))
    def test_clear_logs(self):
        self.init_session()

        self.module.clear_logs()
    
        self.session.cleep_filesystem.write_data.assert_called_with('/tmp/cleep.log', '')

    @patch('os.path.exists', Mock(side_effect=[True, True, True, True, False]))
    def test_clear_logs_not_exist(self):
        self.init_session()

        self.module.clear_logs()
    
        self.assertFalse(self.session.cleep_filesystem.write_data.called)

    def test_set_trace_enabled(self):
        self.init_session()

        self.module.set_trace(True)

        self.assertTrue(mock_cleepconf.return_value.enable_trace.called)
        self.assertFalse(mock_cleepconf.return_value.disable_trace.called)
        self.assertTrue(self.module._System__need_restart)
        self.assertTrue(self.session.event_called('system.cleep.needrestart'))

    def test_set_trace_disabled(self):
        self.init_session()

        self.module.set_trace(False)

        self.assertFalse(mock_cleepconf.return_value.enable_trace.called)
        self.assertTrue(mock_cleepconf.return_value.disable_trace.called)
        self.assertTrue(self.module._System__need_restart)
        self.assertTrue(self.session.event_called('system.cleep.needrestart'))

    def test_set_trace_exception(self):
        self.init_session()

        with self.assertRaises(MissingParameter) as cm:
            self.module.set_trace(None)
        self.assertEqual(str(cm.exception), 'Parameter "trace" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_trace('hello')
        self.assertEqual(str(cm.exception), 'Parameter "trace" is invalid')

    def test_set_core_debug_enabled(self):
        self.init_session()

        self.module.set_core_debug(True)

        self.assertTrue(mock_cleepconf.return_value.enable_core_debug.called)
        self.assertFalse(mock_cleepconf.return_value.disable_core_debug.called)

    def test_set_core_debug_disabled(self):
        self.init_session()

        self.module.set_core_debug(False)

        self.assertFalse(mock_cleepconf.return_value.enable_core_debug.called)
        self.assertTrue(mock_cleepconf.return_value.disable_core_debug.called)

    def test_set_core_debug_exception(self):
        self.init_session()

        with self.assertRaises(MissingParameter) as cm:
            self.module.set_core_debug(None)
        self.assertEqual(str(cm.exception), 'Parameter "debug" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_core_debug('hello')
        self.assertEqual(str(cm.exception), 'Parameter "debug" is invalid')

    def test_set_module_debug_enable(self):
        self.init_session()
        self.session.add_mock_command(self.session.make_mock_command('set_debug'))
        self.session.add_mock_command(self.session.make_mock_command('set_rpc_debug'))

        self.module.set_module_debug('dummy', True)

        mock_cleepconf.return_value.enable_module_debug.assert_called_with('dummy')
        self.assertFalse(mock_cleepconf.return_value.disable_module_debug.called)
        self.assertTrue(self.session.command_called_with('set_debug', to='dummy', params={'debug': True}))
        self.assertFalse(self.session.command_call_count('set_rpc_debug'), 0)

    def test_set_module_debug_disable(self):
        self.init_session()
        self.session.add_mock_command(self.session.make_mock_command('set_debug'))
        self.session.add_mock_command(self.session.make_mock_command('set_rpc_debug'))

        self.module.set_module_debug('dummy', False)

        self.assertFalse(mock_cleepconf.return_value.enable_module_debug.called)
        mock_cleepconf.return_value.disable_module_debug.assert_called_with('dummy')
        self.assertTrue(self.session.command_called_with('set_debug', to='dummy', params={'debug': False}))
        self.assertFalse(self.session.command_call_count('set_rpc_debug'), 0)

    def test_set_module_debug_rpc_enable(self):
        self.init_session()
        self.session.add_mock_command(self.session.make_mock_command('set_debug'))
        self.session.add_mock_command(self.session.make_mock_command('set_rpc_debug'))

        self.module.set_module_debug('rpc', True)

        mock_cleepconf.return_value.enable_module_debug.assert_called_with('rpc')
        self.assertFalse(mock_cleepconf.return_value.disable_module_debug.called)
        self.assertTrue(self.session.command_called_with('set_rpc_debug', to='inventory', params={'debug': True}))
        self.assertFalse(self.session.command_call_count('set_debug'), 0)

    def test_set_module_debug_rpc_disable(self):
        self.init_session()
        self.session.add_mock_command(self.session.make_mock_command('set_debug'))
        self.session.add_mock_command(self.session.make_mock_command('set_rpc_debug'))

        self.module.set_module_debug('rpc', False)

        self.assertFalse(mock_cleepconf.return_value.enable_module_debug.called)
        mock_cleepconf.return_value.disable_module_debug.assert_called_with('rpc')
        self.assertTrue(self.session.command_called_with('set_rpc_debug', to='inventory', params={'debug': False}))
        self.assertFalse(self.session.command_call_count('set_debug'), 0)

    def test_set_module_debug_exception(self):
        self.init_session()
        self.session.add_mock_command(self.session.make_mock_command('set_debug', fail=True))
        self.session.add_mock_command(self.session.make_mock_command('set_rpc_debug', fail=True))
        
        with self.assertRaises(MissingParameter) as cm:
            self.module.set_module_debug(None, True)
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.module.set_module_debug('dummy', None)
        self.assertEqual(str(cm.exception), 'Parameter "debug" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_module_debug(True, True)
        self.assertEqual(str(cm.exception), 'Parameter "module_name" is invalid')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_module_debug('dummy', 'hello')
        self.assertEqual(str(cm.exception), 'Parameter "debug" is invalid')

        with self.assertRaises(CommandError) as cm:
            self.module.set_module_debug('dummy', True)
        self.assertEqual(str(cm.exception), 'Update debug failed')

        with self.assertRaises(CommandError) as cm:
            self.module.set_module_debug('rpc', True)
        self.assertEqual(str(cm.exception), 'Update debug failed')

        #self.session.add_mock_command(self.session.make_mock_command('set_debug', data=None))
        #self.session.add_mock_command(self.session.make_mock_command('set_rpc_debug', data=None))

        self.session.set_mock_command_no_response('set_debug')
        with self.assertRaises(CommandError) as cm:
            self.module.set_module_debug('dummy', True)
        self.assertEqual(str(cm.exception), 'No response from "dummy" module')

        self.session.set_mock_command_no_response('set_rpc_debug')
        with self.assertRaises(CommandError) as cm:
            self.module.set_module_debug('rpc', True)
        self.assertEqual(str(cm.exception), 'No response from "rpc" module')

    def test_set_not_renderable_events(self):
        self.init_session()
        self.module.get_not_renderable_events = Mock(return_value=[{
            'renderer': 'renderer1',
            'event': 'event1'
        }, {
            'renderer': 'renderer2',
            'event': 'event2'
        }])
        mock_event1 = Mock()
        mock_event2 = Mock()
        self.module.events_broker.get_event_instance = Mock(side_effect=[mock_event1, mock_event2])

        self.module._set_not_renderable_events()

        mock_event1.set_renderable.assert_called_with('renderer1', False)
        mock_event2.set_renderable.assert_called_with('renderer2', False)

    def test_set_not_renderable_events_delete_unexisting_event(self):
        self.init_session()
        self.module._get_config_field = Mock(return_value=['renderer1__event1', 'renderer2__event2'])
        self.module._set_config_field = Mock()
        self.module.get_not_renderable_events = Mock(return_value=[{
            'renderer': 'renderer1',
            'event': 'event1'
        }, {
            'renderer': 'renderer2',
            'event': 'event2'
        }])
        mock_event1 = Mock()
        self.module.events_broker.get_event_instance = Mock(side_effect=[mock_event1, Exception('Test exception')])

        self.module._set_not_renderable_events()

        mock_event1.set_renderable.assert_called_with('renderer1', False)
        self.module._set_config_field.assert_called_with('eventsnotrenderable', ['renderer1__event1'])

    def test_set_not_renderable_events_delete_edge_case_duplicated_event_in_conf(self):
        self.init_session()
        self.module._get_config_field = Mock(return_value=['renderer1__event1', 'renderer1__event1'])
        self.module._set_config_field = Mock()
        self.module.get_not_renderable_events = Mock(return_value=[{
            'renderer': 'renderer1',
            'event': 'event1'
        }])
        self.module.events_broker.get_event_instance = Mock(side_effect=Exception('Test exception'))

        self.module._set_not_renderable_events()

        self.module._set_config_field.assert_called_with('eventsnotrenderable', ['renderer1__event1'])
        self.assertEqual(self.module._set_config_field.call_count, 1)

    def test_set_renderable_event(self):
        self.init_session()
        mock_event = Mock()
        self.module.events_broker.get_event_instance = Mock(return_value=mock_event)
        self.module._get_config_field = Mock(return_value=[])
        self.module._set_config_field = Mock(return_value=True)
        
        result = self.module.set_renderable_event('renderer1', 'event1', True)
        logging.debug('Not renderable events: %s' % result)

        self.assertEqual(result, [])
        self.module._get_config_field.assert_called_with('eventsnotrenderable')
        self.module._set_config_field.assert_called_with('eventsnotrenderable', [])
        mock_event.set_renderable.assert_called_with('renderer1', True)

    def test_set_renderable_event_not_renderable(self):
        self.init_session()
        mock_event = Mock()
        self.module.events_broker.get_event_instance = Mock(return_value=mock_event)
        self.module._get_config_field = Mock(return_value=['renderer1%sevent1' % self.module.EVENT_SEPARATOR])
        self.module._set_config_field = Mock(return_value=True)
        
        result = self.module.set_renderable_event('renderer1', 'event1', False)
        logging.debug('Not renderable events: %s' % result)

        self.assertEqual(result, [{'renderer': 'renderer1', 'event': 'event1'}])
        self.module._get_config_field.assert_called_with('eventsnotrenderable')
        self.module._set_config_field.assert_called_with('eventsnotrenderable', ['renderer1%sevent1' % self.module.EVENT_SEPARATOR])
        mock_event.set_renderable.assert_called_with('renderer1', False)

    def test_set_renderable_event_already_not_renderable(self):
        self.init_session()
        mock_event = Mock()
        self.module.events_broker.get_event_instance = Mock(return_value=mock_event)
        self.module._get_config_field = Mock(return_value=['renderer1%sevent1' % self.module.EVENT_SEPARATOR])
        self.module._set_config_field = Mock(return_value=True)
        
        result = self.module.set_renderable_event('renderer1', 'event1', False)
        logging.debug('Not renderable events: %s' % result)

        self.assertEqual(result, [{'renderer': 'renderer1', 'event': 'event1'}])
        self.module._get_config_field.assert_called_with('eventsnotrenderable')
        self.module._set_config_field.assert_called_with('eventsnotrenderable', ['renderer1%sevent1' % self.module.EVENT_SEPARATOR])
        mock_event.set_renderable.assert_called_with('renderer1', False)

    def test_set_renderable_event_event_not_found(self):
        self.init_session()
        mock_event = Mock()
        self.module.events_broker.get_event_instance = Mock(side_effect=Exception('Test exception'))
        self.module._get_config_field = Mock(return_value=[])
        self.module._set_config_field = Mock(return_value=True)
        
        with self.assertRaises(CommandError) as cm:
            self.module.set_renderable_event('renderer1', 'event1', True)
        self.assertEqual(str(cm.exception), 'Unable to update event rendering status')

        self.assertFalse(self.module._get_config_field.called)
        self.assertFalse(self.module._set_config_field.called)
        self.assertFalse(mock_event.set_renderable.called)

    def test_set_renderable_event_unable_to_save_config(self):
        self.init_session()
        mock_event = Mock()
        self.module.events_broker.get_event_instance = Mock(return_value=mock_event)
        self.module._get_config_field = Mock(return_value=[])
        self.module._set_config_field = Mock(return_value=False)
        
        with self.assertRaises(CommandError) as cm:
            self.module.set_renderable_event('renderer1', 'event1', True)
        self.assertEqual(str(cm.exception), 'Unable to save configuration')

        self.assertFalse(mock_event.set_renderable.called)

    def test_set_renderable_event_exception(self):
        self.init_session()

        with self.assertRaises(MissingParameter) as cm:
            self.module.set_renderable_event(None, 'event1', True)
        self.assertEqual(str(cm.exception), 'Parameter "renderer_name" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.module.set_renderable_event('renderer1', None, True)
        self.assertEqual(str(cm.exception), 'Parameter "event_name" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.module.set_renderable_event('renderer1', 'event1', None)
        self.assertEqual(str(cm.exception), 'Parameter "renderable" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_renderable_event(123, 'event1', True)
        self.assertEqual(str(cm.exception), 'Parameter "renderer_name" is invalid')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_renderable_event('renderer1', True, True)
        self.assertEqual(str(cm.exception), 'Parameter "event_name" is invalid')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_renderable_event('renderer1', 'event1', 'true')
        self.assertEqual(str(cm.exception), 'Parameter "renderable" is invalid')

    def test_get_renderable_events(self):
        self.init_session()
        self.module._get_config_field = Mock(return_value=['renderer1__event1', 'renderer2__event3', 'renderer1__event2'])

        events = self.module.get_not_renderable_events()
        logging.debug('Events: %s' % events)
        
        self.assertEqual(events, [
            { 'renderer': 'renderer1', 'event': 'event1' },
            { 'renderer': 'renderer2', 'event': 'event3' },
            { 'renderer': 'renderer1', 'event': 'event2' },
        ])

    def test_set_crash_report(self):
        self.init_session()
        self.module.crash_report = Mock()
        self.module._set_config_field = Mock()
        
        self.module.set_crash_report(True)
        self.module.crash_report.enable.assert_called()
        self.assertFalse(self.module.crash_report.disable.called)
        self.module._set_config_field.assert_called_with('crashreport', True)

        self.module.crash_report.reset_mock()
        self.module.set_crash_report(False)
        self.module.crash_report.disable.assert_called()
        self.assertFalse(self.module.crash_report.enable.called)
        self.module._set_config_field.assert_called_with('crashreport', False)

    def test_set_crash_report_failed(self):
        self.init_session()
        self.module._set_config_field = Mock(return_value=False)
        
        with self.assertRaises(CommandError) as cm:
            self.module.set_crash_report(True)
        self.assertEqual(str(cm.exception), 'Unable to save crash report value')

    def test_set_crash_report_exception(self):
        self.init_session()
        
        with self.assertRaises(MissingParameter) as cm:
            self.module.set_crash_report(None)
        self.assertEqual(str(cm.exception), 'Parameter "enable" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_crash_report('hello')
        self.assertEqual(str(cm.exception), 'Parameter "enable" is invalid')

    def test_backup_cleep_config(self):
        self.init_session()
        self.module.cleep_backup = Mock()

        self.module.backup_cleep_config()

        self.module.cleep_backup.backup.assert_called()

    def test_set_cleep_backup_delay(self):
        self.init_session()

        self.module._set_config_field = Mock(return_value=True)
        self.module.set_cleep_backup_delay(5)
        self.assertEqual(self.module.cleep_backup_delay, 5)
        self.module.set_cleep_backup_delay(120)
        self.assertEqual(self.module.cleep_backup_delay, 120)

        self.module._set_config_field = Mock(return_value=False)
        self.module.set_cleep_backup_delay(15)
        self.assertEqual(self.module.cleep_backup_delay, 120)

    def test_set_cleep_backup_delay_exception(self):
        self.init_session()

        with self.assertRaises(MissingParameter) as cm:
            self.module.set_cleep_backup_delay(None)
        self.assertEqual(str(cm.exception), 'Parameter "delay" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_cleep_backup_delay(True)
        self.assertEqual(str(cm.exception), 'Parameter "delay" is invalid')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_cleep_backup_delay(4)
        self.assertEqual(str(cm.exception), 'Parameter "delay" must be 5..120')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_cleep_backup_delay(121)
        self.assertEqual(str(cm.exception), 'Parameter "delay" must be 5..120')

if __name__ == '__main__':
    # coverage run --omit="*lib/python*/*","test_*" --concurrency=thread test_system.py; coverage report -m -i
    unittest.main()
    
