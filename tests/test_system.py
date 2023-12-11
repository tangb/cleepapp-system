#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import logging
import sys
import os
sys.path.append('../')
from backend.system import System
from cleep.exception import InvalidParameter, MissingParameter, CommandError, Unauthorized, CommandInfo, NoResponse
from cleep.libs.tests import session
from cleep.libs.tests.common import get_log_level
from mock import Mock, patch, MagicMock

LOG_LEVEL = get_log_level()

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

class DummyDriver():
    def __init__(self, require_reboot):
        self.__require_reboot = require_reboot

    def require_reboot(self):
        return self.__require_reboot

mock_psutil = MagicMock()
mock_psutil.boot_time = Mock(return_value=1602175545.2728713)
mock_psutil.cpu_percent = Mock(return_value=150)
mock_psutil.virtual_memory = Mock(return_value=VirtualMemory())
mock_psutil.Process.return_value.cpu_percent = Mock(return_value=120)
mock_psutil.Process.return_value.memory_info = Mock(return_value=[400,])
mock_cleepconf = MagicMock()

@patch('backend.system.psutil', mock_psutil)
@patch('backend.system.CleepConf', mock_cleepconf)
class TestsSystem(unittest.TestCase):

    def setUp(self):
        self.session = session.TestSession(self)
        logging.basicConfig(level=LOG_LEVEL, format=u'%(asctime)s %(name)s:%(lineno)d %(levelname)s : %(message)s')

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
            self.module.set_trace(False)
            self.module.set_core_debug(False)

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

    def test_on_start(self):
        self.init_session(start_module=False)
        self.module._System__start_monitoring_tasks = Mock()

        self.session.start_module(self.module)

        self.assertTrue(self.module._System__start_monitoring_tasks.called)

    def test_get_module_config(self):
        self.init_session()
        mock_cleepconf.is_system_debugged = Mock(return_value=True)
        mock_cleepconf.is_trace_enabled = Mock(return_value=True)

        config = self.module.get_module_config()
        logging.debug('Config: %s' % config)
        self.assertCountEqual(
            [
                'needrestart',
                'version',
                'eventsnotrenderable',
                'debug',
                'cleepbackupdelay',
                'monitoring',
                'ssl',
                'auth',
                'rpcport',
                'crashreport',
                'needreboot',
                'devices',
                'enablepowerled',
                'enableactivityled'
            ],
            config.keys(),
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

    def test_on_event_need_restart(self):
        self.init_session()

        self.module.on_event({
            'event': 'system.cleep.needrestart',
            'params': {}
        })
        
        self.assertTrue(self.module._System__need_restart)

    def test_on_event_need_reboot(self):
        self.init_session()
        self.module._set_config_field = Mock()

        self.module.on_event({
            'event': 'system.device.needreboot',
            'params': {}
        })
        
        self.module._set_config_field.assert_called_with('needreboot', True)

    def test_on_event_backup_config(self):
        self.init_session()
        self.module.backup_cleep_config = Mock()

        self.module.on_event({
            'event': 'parameters.time.now',
            'params': {
                'minute': 5
            }
        })
        self.assertFalse(self.module.backup_cleep_config.called)

        self.module.on_event({
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
        self.assertEqual(str(cm.exception), 'Parameter "monitoring" must be of type "bool"')

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
        mock_console.return_value.command_delayed.assert_called_with('reboot -f', 10.0)
        self.assertTrue(self.session.event_called('system.device.reboot'))

    @patch('backend.system.Console')
    def test_poweroff_device(self, mock_console):
        self.init_session()
        self.module.backup_cleep_config = Mock()

        self.module.poweroff_device(delay=10.0)
        
        self.module.backup_cleep_config.assert_called()
        mock_console.return_value.command_delayed.assert_called_with('poweroff -f', 10.0)
        self.assertTrue(self.session.event_called('system.device.poweroff'))

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
        mock_zipfile.return_value.__enter__.return_value.write.assert_called_with(session.AnyArg(), 'cleep.log')

    def test_download_logs_exception(self):
        self.init_session()

        with patch('os.path.exists') as mock_path_exists:
            mock_path_exists.return_value = False
            with self.assertRaises(CommandError) as cm:
                self.module.download_logs()
        self.assertEqual(str(cm.exception), 'Logs file doesn\'t exist')

    def test_get_logs(self):
        self.init_session()
        lines = ['line1', 'line2']
        self.session.cleep_filesystem.read_data = Mock(return_value=lines)

        with patch('os.path.exists') as mock_path_exists:
            mock_path_exists.return_value = True
            logs = self.module.get_logs()
            logging.debug('Logs: %s' % logs)
    
        self.assertEqual(logs, lines)

    def test_get_logs_not_exist(self):
        self.init_session()
        lines = ['line1', 'line2']
        self.session.cleep_filesystem.read_data = Mock(return_value=lines)

        with patch('os.path.exists') as mock_path_exists:
            mock_path_exists.return_value = False
            logs = self.module.get_logs()
            logging.debug('Logs: %s' % logs)
    
        self.assertEqual(logs, [])

    def test_clear_logs(self):
        self.init_session()

        with patch('os.path.exists') as mock_path_exists:
            mock_path_exists.return_value = True
            self.module.clear_logs()
    
        self.session.cleep_filesystem.write_data.assert_called_with('/tmp/cleep.log', '')

    def test_clear_logs_not_exist(self):
        self.init_session()

        with patch('os.path.exists') as mock_path_exists:
            mock_path_exists.return_value = False
            self.module.clear_logs()
    
        self.assertFalse(self.session.cleep_filesystem.write_data.called)

    def test_set_trace_enabled(self):
        self.init_session()

        self.module.set_trace(True)

        self.assertTrue(mock_cleepconf.return_value.enable_trace.called)
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
        self.assertEqual(str(cm.exception), 'Parameter "trace" must be of type "bool"')

    def test_set_core_debug_enabled(self):
        self.init_session()

        self.module.set_core_debug(True)

        self.assertTrue(mock_cleepconf.return_value.enable_core_debug.called)

    def test_set_core_debug_disabled(self):
        self.init_session()

        self.module.set_core_debug(False)

        self.assertTrue(mock_cleepconf.return_value.disable_core_debug.called)

    def test_set_core_debug_exception(self):
        self.init_session()

        with self.assertRaises(MissingParameter) as cm:
            self.module.set_core_debug(None)
        self.assertEqual(str(cm.exception), 'Parameter "debug" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_core_debug('hello')
        self.assertEqual(str(cm.exception), 'Parameter "debug" must be of type "bool"')

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
        self.assertEqual(str(cm.exception), 'Parameter "module_name" must be of type "str"')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_module_debug('dummy', 'hello')
        self.assertEqual(str(cm.exception), 'Parameter "debug" must be of type "bool"')

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
        self.assertEqual(str(cm.exception), 'Update debug failed')

        self.session.set_mock_command_no_response('set_rpc_debug')
        with self.assertRaises(CommandError) as cm:
            self.module.set_module_debug('rpc', True)
        self.assertEqual(str(cm.exception), 'Update debug failed')

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

    def test_set_event_renderable(self):
        self.init_session()
        self.module._get_config_field = Mock(return_value=['renderer1%sevent1' % self.module.EVENT_SEPARATOR])
        self.module._set_config_field = Mock(return_value=True)
        self.module.events_broker = Mock()
        
        result = self.module.set_event_renderable('renderer1', 'event1', True)
        logging.debug('Not renderable events: %s' % result)

        self.assertEqual(result, [])
        self.module._get_config_field.assert_called_with('eventsnotrenderable')
        self.module._set_config_field.assert_called_with('eventsnotrenderable', [])
        self.module.events_broker.set_event_renderable.assert_called_with('event1', 'renderer1', True)

    def test_set_event_renderable_not_renderable(self):
        self.init_session()
        self.module._get_config_field = Mock(return_value=[])
        self.module._set_config_field = Mock(return_value=True)
        self.module.events_broker = Mock()
        
        result = self.module.set_event_renderable('renderer1', 'event1', False)
        logging.debug('Not renderable events: %s' % result)

        self.assertEqual(result, [{'renderer': 'renderer1', 'event': 'event1'}])
        self.module._get_config_field.assert_called_with('eventsnotrenderable')
        self.module._set_config_field.assert_called_with('eventsnotrenderable', ['renderer1%sevent1' % self.module.EVENT_SEPARATOR])
        self.module.events_broker.set_event_renderable.assert_called_with('event1', 'renderer1', False)

    def test_set_event_renderable_already_not_renderable(self):
        self.init_session()
        self.module.events_broker = Mock()
        self.module._get_config_field = Mock(return_value=['renderer1%sevent1' % self.module.EVENT_SEPARATOR])
        self.module._set_config_field = Mock(return_value=True)
        
        result = self.module.set_event_renderable('renderer1', 'event1', False)
        logging.debug('Not renderable events: %s' % result)

        self.assertEqual(result, [{'renderer': 'renderer1', 'event': 'event1'}])
        self.module._get_config_field.assert_called_with('eventsnotrenderable')
        self.module._set_config_field.assert_called_with('eventsnotrenderable', ['renderer1%sevent1' % self.module.EVENT_SEPARATOR])
        self.module.events_broker.set_event_renderable.assert_called_with('event1', 'renderer1', False)

    def test_set_event_renderable_unable_to_save_config(self):
        self.init_session()
        mock_event = Mock()
        self.module.events_broker.get_event_instance = Mock(return_value=mock_event)
        self.module._get_config_field = Mock(return_value=[])
        self.module._set_config_field = Mock(return_value=False)
        
        with self.assertRaises(CommandError) as cm:
            self.module.set_event_renderable('renderer1', 'event1', True)
        self.assertEqual(str(cm.exception), 'Unable to save configuration')

        self.assertFalse(mock_event.set_renderable.called)

    def test_set_event_renderable_exception(self):
        self.init_session()

        with self.assertRaises(MissingParameter) as cm:
            self.module.set_event_renderable(None, 'event1', True)
        self.assertEqual(str(cm.exception), 'Parameter "renderer_name" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.module.set_event_renderable('renderer1', None, True)
        self.assertEqual(str(cm.exception), 'Parameter "event_name" is missing')

        with self.assertRaises(MissingParameter) as cm:
            self.module.set_event_renderable('renderer1', 'event1', None)
        self.assertEqual(str(cm.exception), 'Parameter "renderable" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_event_renderable(123, 'event1', True)
        self.assertEqual(str(cm.exception), 'Parameter "renderer_name" must be of type "str"')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_event_renderable('renderer1', True, True)
        self.assertEqual(str(cm.exception), 'Parameter "event_name" must be of type "str"')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_event_renderable('renderer1', 'event1', 'true')
        self.assertEqual(str(cm.exception), 'Parameter "renderable" must be of type "bool"')

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
        self.assertEqual(str(cm.exception), 'Parameter "enable" must be of type "bool"')

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
        self.assertEqual(str(cm.exception), 'Parameter "delay" is invalid (specified="True")')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_cleep_backup_delay(4)
        self.assertEqual(str(cm.exception), 'Parameter "delay" is invalid (specified="4")')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.set_cleep_backup_delay(121)
        self.assertEqual(str(cm.exception), 'Parameter "delay" is invalid (specified="121")')

    def test_install_driver_terminated_success_no_reboot_required(self):
        self.init_session()
        self.module.reboot_device = Mock()
        self.module.drivers = Mock()
        self.module.drivers.get_driver.return_value = DummyDriver(False)

        self.module._install_driver_terminated('dummy', 'dummy-driver', True, '')

        self.assertTrue(self.session.event_called_with('system.driver.install', {
            'drivertype': 'dummy',
            'drivername': 'dummy-driver',
            'installing': False,
            'success': True,
            'message': '',
        }))
        self.assertFalse(self.module.reboot_device.called)
        self.assertTrue(self.module.drivers.get_driver.called)

    def test_install_driver_terminated_success_reboot_required(self):
        self.init_session()
        self.module.reboot_device = Mock()
        self.module.drivers = Mock()
        self.module.drivers.get_driver.return_value = DummyDriver(True)

        self.module._install_driver_terminated('dummy', 'dummy-driver', True, '')

        self.assertTrue(self.session.event_called_with('system.driver.install', {
            'drivertype': 'dummy',
            'drivername': 'dummy-driver',
            'installing': False,
            'success': True,
            'message': '',
        }))
        self.assertTrue(self.module.reboot_device.called)
        self.assertTrue(self.module.drivers.get_driver.called)

    def test_install_driver_terminated_failure(self):
        self.init_session()
        self.module.reboot_device = Mock()
        self.module.drivers = Mock()

        self.module._install_driver_terminated('dummy', 'dummy-driver', False, 'error occured')

        self.assertTrue(self.session.event_called_with('system.driver.install', {
            'drivertype': 'dummy',
            'drivername': 'dummy-driver',
            'installing': False,
            'success': False,
            'message': 'error occured',
        }))
        self.assertFalse(self.module.reboot_device.called)
        self.assertFalse(self.module.drivers.get_driver.called)

    def test_install_driver(self):
        self.init_session()
        driver = Mock()
        driver.is_installed = Mock(return_value=False)
        self.module.drivers.get_driver = Mock(return_value=driver)

        self.module.install_driver('dummy', 'dummy-driver')

        driver.install.assert_called()
        self.session.event_called_with('system.driver.install', {
            'drivertype': 'dummy',
            'drivername': 'dummy-driver',
            'installing': True,
            'success': None,
            'message': None,
        })

    def test_install_driver_already_installed(self):
        self.init_session()
        driver = Mock()
        driver.is_installed = Mock(return_value=True)
        self.module.drivers.get_driver = Mock(return_value=driver)

        with self.assertRaises(CommandInfo) as cm:
            self.module.install_driver('dummy', 'dummy-driver')
        self.assertEqual(str(cm.exception), 'Driver is already installed')

    def test_install_driver_exception(self):
        self.init_session()
        self.module.drivers.get_driver = Mock(return_value=None)

        with self.assertRaises(InvalidParameter) as cm:
            self.module.install_driver('dummy', 'dummy-driver')
        self.assertEqual(str(cm.exception), 'No driver found for specified parameters')

        with self.assertRaises(MissingParameter) as cm:
            self.module.install_driver(None, 'dummy-driver')
        self.assertEqual(str(cm.exception), 'Parameter "driver_type" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.install_driver(123, 'dummy-driver')
        self.assertEqual(str(cm.exception), 'Parameter "driver_type" must be of type "str"')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.install_driver('', 'dummy-driver')
        self.assertEqual(str(cm.exception), 'Parameter "driver_type" is invalid (specified="")')

        with self.assertRaises(MissingParameter) as cm:
            self.module.install_driver('dummy', None)
        self.assertEqual(str(cm.exception), 'Parameter "driver_name" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.install_driver('dummy', 123)
        self.assertEqual(str(cm.exception), 'Parameter "driver_name" must be of type "str"')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.install_driver('dummy', '')
        self.assertEqual(str(cm.exception), 'Parameter "driver_name" is invalid (specified="")')

    def test_uninstall_driver_terminated_success_no_reboot_required(self):
        self.init_session()
        self.module.reboot_device = Mock()
        self.module.drivers = Mock()
        self.module.drivers.get_driver.return_value = DummyDriver(False)

        self.module._uninstall_driver_terminated('dummy', 'dummy-driver', True, '')

        self.assertTrue(self.session.event_called_with('system.driver.uninstall', {
            'drivertype': 'dummy',
            'drivername': 'dummy-driver',
            'uninstalling': False,
            'success': True,
            'message': '',
        }))
        self.assertFalse(self.module.reboot_device.called)
        self.assertTrue(self.module.drivers.get_driver.called)

    def test_uninstall_driver_terminated_success_reboot_required(self):
        self.init_session()
        self.module.reboot_device = Mock()
        self.module.drivers = Mock()
        self.module.drivers.get_driver.return_value = DummyDriver(True)

        self.module._uninstall_driver_terminated('dummy', 'dummy-driver', True, '')

        self.assertTrue(self.session.event_called_with('system.driver.uninstall', {
            'drivertype': 'dummy',
            'drivername': 'dummy-driver',
            'uninstalling': False,
            'success': True,
            'message': '',
        }))
        self.assertTrue(self.module.reboot_device.called)
        self.assertTrue(self.module.drivers.get_driver.called)

    def test_uninstall_driver_terminated_failure(self):
        self.init_session()
        self.module.reboot_device = Mock()

        self.module._uninstall_driver_terminated('dummy', 'dummy-driver', False, 'error occured')

        self.assertTrue(self.session.event_called_with('system.driver.uninstall', {
            'drivertype': 'dummy',
            'drivername': 'dummy-driver',
            'uninstalling': False,
            'success': False,
            'message': 'error occured',
        }))
        self.assertFalse(self.module.reboot_device.called)

    def test_uninstall_driver(self):
        self.init_session()
        driver = Mock()
        driver.is_installed = Mock(return_value=True)
        self.module.drivers.get_driver = Mock(return_value=driver)

        self.module.uninstall_driver('dummy', 'dummy-driver')

        driver.uninstall.assert_called()
        self.session.event_called_with('system.driver.uninstall', {
            'drivertype': 'dummy',
            'drivername': 'dummy-driver',
            'uninstalling': True,
            'success': None,
            'message': None,
        })

    def test_uninstall_driver_already_uninstalled(self):
        self.init_session()
        driver = Mock()
        driver.is_installed = Mock(return_value=False)
        self.module.drivers.get_driver = Mock(return_value=driver)

        with self.assertRaises(CommandInfo) as cm:
            self.module.uninstall_driver('dummy', 'dummy-driver')
        self.assertEqual(str(cm.exception), 'Driver is not installed')

    def test_uninstall_driver_exception(self):
        self.init_session()
        self.module.drivers.get_driver = Mock(return_value=None)

        with self.assertRaises(InvalidParameter) as cm:
            self.module.uninstall_driver('dummy', 'dummy-driver')
        self.assertEqual(str(cm.exception), 'No driver found for specified parameters')

        with self.assertRaises(MissingParameter) as cm:
            self.module.uninstall_driver(None, 'dummy-driver')
        self.assertEqual(str(cm.exception), 'Parameter "driver_type" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.uninstall_driver(123, 'dummy-driver')
        self.assertEqual(str(cm.exception), 'Parameter "driver_type" must be of type "str"')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.uninstall_driver('', 'dummy-driver')
        self.assertEqual(str(cm.exception), 'Parameter "driver_type" is invalid (specified="")')

        with self.assertRaises(MissingParameter) as cm:
            self.module.uninstall_driver('dummy', None)
        self.assertEqual(str(cm.exception), 'Parameter "driver_name" is missing')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.uninstall_driver('dummy', 123)
        self.assertEqual(str(cm.exception), 'Parameter "driver_name" must be of type "str"')

        with self.assertRaises(InvalidParameter) as cm:
            self.module.uninstall_driver('dummy', '')
        self.assertEqual(str(cm.exception), 'Parameter "driver_name" is invalid (specified="")')

    def test_apply_tweaks(self):
        self.init_session()
        self.module.tweak_power_led = Mock()
        self.module.tweak_activity_led = Mock()
        self.module._get_config_field = Mock(side_effect=[True, True])

        self.module._System__apply_tweaks()

        self.module.tweak_power_led.assert_called()
        self.module.tweak_activity_led.assert_called()

    @patch('backend.system.Console')
    def test_tweak_power_led_turn_on(self, mock_console):
        self.init_session()
        self.module._set_config_field = Mock()
        mock_console.return_value.command.return_value = { 'returncode': 0 }

        self.module.tweak_power_led(True)

        self.module._set_config_field.assert_called_with('enablepowerled', True)
        mock_console.return_value.command.assert_called_with(session.PatternArg('.*echo 1.*'))

    @patch('backend.system.Console')
    def test_tweak_power_led_turn_off(self, mock_console):
        self.init_session()
        self.module._set_config_field = Mock()
        mock_console.return_value.command.return_value = { 'returncode': 0 }

        self.module.tweak_power_led(False)

        self.module._set_config_field.assert_called_with('enablepowerled', False)
        mock_console.return_value.command.assert_called_with(session.PatternArg('.*echo 0.*'))

    @patch('backend.system.Console')
    def test_tweak_power_led_failed(self, mock_console):
        self.init_session()
        self.module._set_config_field = Mock()
        mock_console.return_value.command.return_value = { 'returncode': 1 }

        with self.assertRaises(CommandError) as cm:
            self.module.tweak_power_led(True)
        self.assertEqual(str(cm.exception), 'Error tweaking power led')

        self.assertFalse(self.module._set_config_field.called)

    def test_tweak_power_led_no_file(self):
        self.init_session()
        self.module._set_config_field = Mock()

        with patch('backend.system.Console') as mock_console:
            with patch('os.path.exists', Mock(return_value=False)):
                self.module.tweak_power_led(True)

        self.assertFalse(self.module._set_config_field.called)
        self.assertFalse(mock_console.return_value.command.called)

    @patch('backend.system.Console')
    def test_tweak_activity_led_turn_on(self, mock_console):
        self.init_session()
        self.module._set_config_field = Mock()
        mock_console.return_value.command.return_value = { 'returncode': 0 }

        self.module.tweak_activity_led(True)

        self.module._set_config_field.assert_called_with('enableactivityled', True)
        mock_console.return_value.command.assert_any_call(session.PatternArg('.*echo 1.*'))
        mock_console.return_value.command.assert_any_call(session.PatternArg('.*echo mmc0.*'))

    @patch('backend.system.Console')
    def test_tweak_activity_led_turn_off(self, mock_console):
        self.init_session()
        self.module._set_config_field = Mock()
        mock_console.return_value.command.return_value = { 'returncode': 0 }

        self.module.tweak_activity_led(False)

        self.module._set_config_field.assert_called_with('enableactivityled', False)
        mock_console.return_value.command.assert_called_with(session.PatternArg('.*echo 0.*'))
        # check echo mmc0 not called using number of time mock was called (but do not check args list)
        logging.debug('Mock calls args list: %s', mock_console.return_value.command.call_args_list)
        self.assertEqual(mock_console.return_value.command.call_count, 3)

    @patch('backend.system.Console')
    def test_tweak_activity_led_failed(self, mock_console):
        self.init_session()
        self.module._set_config_field = Mock()
        mock_console.return_value.command.return_value = { 'returncode': 1 }

        with self.assertRaises(CommandError) as cm:
            self.module.tweak_activity_led(True)
        self.assertEqual(str(cm.exception), 'Error tweaking activity led')

        self.assertFalse(self.module._set_config_field.called)

    def test_tweak_activity_led_no_file(self):
        self.init_session()
        self.module._set_config_field = Mock()

        with patch('backend.system.Console') as mock_console:
            with patch('os.path.exists', Mock(return_value=False)):
                self.module.tweak_activity_led(True)

        self.assertFalse(self.module._set_config_field.called)
        self.assertFalse(mock_console.return_value.command.called)

if __name__ == '__main__':
    # coverage run --omit="*lib/python*/*","test_*" --concurrency=thread test_system.py; coverage report -m -i
    unittest.main()
    
