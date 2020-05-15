/**
 * System service
 * Handle system module requests
 */
var systemService = function($rootScope, rpcService, cleepService, toast, appToolbarService)
{
    var self = this;
    self.cleepInstallStatus = 0; //idle status
    self.modulesInstallStatus = {};
    self.restartButtonId = null;
    self.rebootButtonId = null;
    self.monitoring = false;
    
    /**
     * Get filesystem infos
     */
    self.getFilesystemInfos = function()
    {
        return rpcService.sendCommand('get_filesystem_infos', 'system', 30000);
    };

    /**
     * Set monitoring
     */
    self.setMonitoring = function(monitoring)
    {
        return rpcService.sendCommand('set_monitoring', 'system', {'monitoring': monitoring});
    };

    /**
     * Reboot system
     */
    self.reboot = function()
    {
        return rpcService.sendCommand('reboot_system', 'system');
    };

    /**
     * Halt system
     */
    self.halt = function()
    {
        return rpcService.sendCommand('halt_system', 'system');
    };

    /**
     * Restart cleep
     */
    self.restart = function()
    {
        return rpcService.sendCommand('restart', 'system');
    };

    /**
     * Install module
     */
    self.installModule = function(module)
    {
        return rpcService.sendCommand('install_module', 'system', {'module':module}, 300);
    };

    /**
     * Uninstall module
     */
    self.uninstallModule = function(module) {
        return rpcService.sendCommand('uninstall_module', 'system', {'module':module}, 300);
    };

    /**
     * Update module
     */
    self.updateModule = function(module)
    {
        return rpcService.sendCommand('update_module', 'system', {'module':module}, 300);
    };

    /**
     * Update cleep
     */
    self.updateCleep = function()
    {
        return rpcService.sendCommand('update_cleep', 'system', null, 300);
    };

    /**
     * Download logs
     */
    self.downloadLogs = function()
    {
        rpcService.download('download_logs', 'system');
    };

    /**
     * Get logs
     */
    self.getLogs = function()
    {
        return rpcService.sendCommand('get_logs', 'system');
    };

    /**
     * Clear logs
     */
    self.clearLogs = function()
    {
        return rpcService.sendCommand('clear_logs', 'system');
    };

    /**
     * Set module debug
     */
    self.setModuleDebug = function(module, debug)
    {
        return rpcService.sendCommand('set_module_debug', 'system', {'module':module, 'debug':debug});
    };

    /**
     * Set system debug
     */
    self.setSystemDebug = function(debug)
    {
        return rpcService.sendCommand('set_system_debug', 'system', {'debug':debug});
    };

    /**
     * Set trace
     */
    self.setTrace = function(trace)
    {
        return rpcService.sendCommand('set_trace', 'system', {'trace':trace})
            .then(function() {
                return cleepService.reloadModuleConfig('system');
            });
    };

    /**
     * Set hostname
     */
    self.setHostname = function(hostname)
    {
        return rpcService.sendCommand('set_hostname', 'system', {'hostname':hostname});
    };

    /**
     * Set event not rendered
     */
    self.setEventNotRendered = function(renderer, event, disabled)
    {
        return rpcService.sendCommand('set_event_not_rendered', 'system', {'renderer':renderer, 'event':event, 'disabled':disabled})
            .then(function(resp) {
                //overwrite system event_not_rendered config value
                cleepService.modules.system.config.eventsnotrendered = resp.data;
            });
    };

    /**
     * Check for cleep updates
     */
    self.checkCleepUpdates = function()
    {
        return rpcService.sendCommand('check_cleep_updates', 'system');
    };

    /**
     * Check for modules updates
     */
    self.checkModulesUpdates = function()
    {
        return rpcService.sendCommand('check_modules_updates', 'system', null, 30);
    };

    /**
     * Set automatic update
     */
    self.setAutomaticUpdate = function(cleepUpdateEnabled, modulesUpdateEnabled)
    {
        return rpcService.sendCommand('set_automatic_update', 'system', {'cleep_update_enabled':cleepUpdateEnabled, 'modules_update_enabled':modulesUpdateEnabled});
    };

    /**
     * Enable/disable crash report
     */
    self.setCrashReport = function(enable)
    {
        return rpcService.sendCommand('set_crash_report', 'system', {'enable':enable});
    };

    /**
     * Set backup update time
     */
    self.setCleepBackupDelay = function(delay)
    {
        return rpcService.sendCommand('set_cleep_backup_delay', 'system', {'delay': delay});
    };

    /**
     * Make backup of cleep configuration files
     */
    self.backupCleepConfig = function()
    {
        return rpcService.sendCommand('backup_cleep_config', 'system', {});
    };

    /**
     * Update pending module status after install
     * Everything will be reloaded automatically after page reloading
     * @param module: module name
     */
    self.updateModulePendingStatus = function(module, pending)
    {   
        //update pending status in cleepService
        if( cleepService.modules[module] ) {
            cleepService.modules[module].pending = pending;
        }
    };

    /** 
     * Update processing status
     * @param module (string): module name
     * @param processing (bool): processing value
     */
    self.updateModuleProcessingStatus = function(module, processing)
    {
        //update pending status in cleepService
        if( cleepService.modules[module] ) {
            cleepService.modules[module].processing = processing;
        }
    };

    /**
     * Watch for system config changes to add restart/reboot buttons if restart/reboot is needed
     */
    $rootScope.$watchCollection(
        function() {
            return cleepService.modules['system'];
        },
        function(newConfig) {
            if( !angular.isUndefined(newConfig) && newConfig.config )
            {
                //handle restart button
                if( !newConfig.config.needrestart && self.restartButtonId )
                {
                    appToolbarService.removeButton(self.restartButtonId);
                    self.restartButtonId = null;
                }
                else if( newConfig.config.needrestart && !self.restartButtonId )
                {
                    self.restartButtonId = appToolbarService.addButton('Restart to apply changes', 'restart', cleepService.restart, 'md-accent');
                }

                //handle reboot button
                if( !newConfig.config.needreboot && self.rebootButtonId )
                {
                    appToolbarService.removeButton(self.rebootButtonId);
                    self.rebootButtonId = null;
                }
                else if( newConfig.config.needreboot && !self.rebootButtonId )
                {
                    self.rebootButtonId = appToolbarService.addButton('Reboot to apply changes', 'restart', cleepService.reboot, 'md-accent');
                }

                //store monitoring flag to display or not monitor widget
                self.monitoring = newConfig.config.monitoring;
            }
        }
    );

    /**
     * Catch cpu monitoring event
     */
    $rootScope.$on('system.monitoring.cpu', function(event, uuid, params) {
        for( var i=0; i<cleepService.devices.length; i++ )
        {
            if( cleepService.devices[i].type==='monitor' )
            {
                cleepService.devices[i].cpu = params;
                break;
            }
        }
    });

    /**
     * Catch memory monitoring event
     */
    $rootScope.$on('system.monitoring.memory', function(event, uuid, params) {
        for( var i=0; i<cleepService.devices.length; i++ )
        {
            if( cleepService.devices[i].type==='monitor' )
            {
                cleepService.devices[i].memory = params;
                break;
            }
        }
    });

    /**
     * Handle cleep update event
     */
    $rootScope.$on('system.cleep.update', function(event, uuid, params) {
        if( params.status===null || params.status===undefined )
        {
            return;
        }

        self.cleepInstallStatus = params.status;
        if( params.status==0 || params.status==1 )
        {
            //idle status or installing update
        }
        else if( params.status==2 )
        {   
            toast.success('Cleep has been updated successfully. Device will reboot.');
            //reset install status to remove item from ui
            self.cleepInstallStatus = 0;
        }   
        else
        {   
            toast.error('Error during Cleep update. See logs for details.');
            //reset install status to remove item from ui
            self.cleepInstallStatus = 0;
        }   
    });

    /**
     * Handle module install event
     */
    $rootScope.$on('system.module.install', function(event, uuid, params) {
    	//drop useless status
        if( !params.status )
        {
            return;
        }

        //drop module install triggered during module install 
        if( params.updateprocess===true )
		{
			return;
		}

		if( params.status===1 )
		{
			//processing status
            self.updateModuleProcessingStatus(params.module, 'install');
		}
		else if( params.status===2 )
		{
	        //error occured during module install, reload config to get install outputs
            cleepService.loadConfig()
                .then(function() {
                    //update processing status to false
                    self.updateModuleProcessingStatus(params.module, null);
                    
                    //user message
                    toast.error('Error during app "' + params.module + '" install. See logs for details.');
                });
		}
        else if( params.status===3 )
        {
            //module installed successfully, reload config to get clean modules list updated
            cleepService.loadConfig()
                .then(function() {
                    //update pending+processing status
                    self.updateModuleProcessingStatus(params.module, null);
                    self.updateModulePendingStatus(params.module, true);
                    
                    //user message
                    toast.success('App "' + params.module + '" installed successfully. Restart to apply changes.');
                });
        }
        else if( params.status===4 )
        {
            //module installation canceled (not supported yet)
            self.updateModuleProcessingStatus(params.module, null);
        }
    });

    /**
     * Handle module update event
     */
    $rootScope.$on('system.module.update', function(event, uuid, params) {
    	//drop useless status
        if( !params.status )
        {
            return;
        }

		if( params.status===1 )
		{
			//processing status
            self.updateModuleProcessingStatus(params.module, 'update');
		}
		else if( params.status===2 )
		{
	        //error occured during module update, reload config to get install outputs
            cleepService.loadConfig()
                .then(function() {
                    //update processing status to false
                    self.updateModuleProcessingStatus(params.module, null);
                    
                    //user message
                    toast.error('Error during app "' + params.module + '" update. See logs for details.');
                });
		}
        else if( params.status===3 )
        {
            //module updated successfully, reload config to get clean modules list updated
            cleepService.loadConfig()
                .then(function() {
                    //update pending+processing status
                    self.updateModuleProcessingStatus(params.module, null);
                    self.updateModulePendingStatus(params.module, true);
                    
                    //user message
                    toast.success('App "' + params.module + '" updated successfully. Restart to apply changes.');
                });
        }
        else if( params.status===4 )
        {
            //module update canceled (not supported yet)
            self.updateModuleProcessingStatus(params.module, null);
        }
    });

    /**
     * Handle module uninstall event
     */
    $rootScope.$on('system.module.uninstall', function(event, uuid, params) {
    	//drop useless status
        if( !params.status )
        {
            return;
        }

		if( params.status===1 )
		{
			//processing status
            self.updateModuleProcessingStatus(params.module, 'uninstall');
		}
		else if( params.status===2 )
		{
	        //error occured during module uninstall, reload config to get uninstall outputs
            cleepService.loadConfig()
                .then(function() {
                    //update processing status to false
                    self.updateModuleProcessingStatus(params.module, null);
                    
                    //user message
                    toast.error('Error during app "' + params.module + '" uninstall. See logs for details.');
                });
		}
        else if( params.status===3 )
        {
            //module uninstalled successfully, reload config to get clean modules list updated
            cleepService.loadConfig()
                .then(function() {
                    //update pending+processing status
                    self.updateModuleProcessingStatus(params.module, null);
                    self.updateModulePendingStatus(params.module, true);
                    
                    //user message
                    toast.success('App "' + params.module + '" uninstall successfully. Restart to apply changes.');
                });
        }
    });

};
    
var Cleep = angular.module('Cleep');
Cleep.service('systemService', ['$rootScope', 'rpcService', 'cleepService', 'toastService', 'appToolbarService', systemService]);

