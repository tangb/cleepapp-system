/**
 * System config directive
 * Handle system configuration
 */
var systemConfigDirective = function($rootScope, $filter, $timeout, $q, toast, systemService, cleepService, confirm, $mdDialog, $location)
{
    var systemController = ['$scope', function($scope)
    {
        var self = this;
        self.systemService = systemService;
        self.tabIndex = 'update';
        self.monitoring = false;
        self.uptime = 0;
        self.needRestart = false;
        self.needReboot = false;
        self.logs = '';
        self.codemirrorInstance = null;
        self.codemirrorOptions = {
            lineNumbers: true,
            tabSize: 2,
            readOnly: true,
            onLoad: function(cmInstance) {
                self.codemirrorInstance = cmInstance;
                cmInstance.focus();
            }
        };
        self.debugs = {};
        self.debugSystem = false;
        self.debugTrace = false;
        self.renderings = [];
        self.eventsNotRendered = [];
        self.cleepUpdateEnabled = false;
        self.modulesUpdateEnabled = false;
        self.cleepUpdateAvailable = null;
        self.cleepUpdateChangelog = null;
        self.modulesUpdateAvailable = false;
        self.lastCleepUpdate = null;
        self.lastCheckCleep = null;
        self.lastCheckModules = null;
        self.version = '';
        self.crashReport = false;
        self.lastModulesProcessing = {};
        self.cleepUpdatePending = false;
        self.backupDelay = 15;

        /************
         * Update tab
         ************/

        /**
         * Set automatic update
         */
        self.setAutomaticUpdate = function(row)
        {
            //toggle value if row clicked
            if( row==='cleep' )
            {
                self.cleepUpdateEnabled = !self.cleepUpdateEnabled;
            }
            else if( row==='modules' )
            {
                self.modulesUpdateEnabled = !self.modulesUpdateEnabled;
            }

            //perform update
            systemService.setAutomaticUpdate(self.cleepUpdateEnabled, self.modulesUpdateEnabled)
                .then(function(resp) {
                    if( resp.data===true )
                    {
                        toast.success('New value saved');
                    }
                    else
                    {
                        toast.error('Unable to save new value');
                    }
                });
        };

        /**
         * Check for cleep updates
         */
        self.checkCleepUpdates = function() {
            toast.loading('Checking cleep update...');
            var message = null;
            systemService.checkCleepUpdates()
                .then(function(resp) {
                     
                    if( resp.data.cleepupdateavailable===null )
                    {
                        message = 'No update available';
                    }
                    else
                    {
                        message = 'Update available';
                    }

                    //refresh system module config
                    return cleepService.reloadModuleConfig('system');
                })
                .then(function(config) {
                    //set config
                    self.setConfig(config);
                })
                .finally(function() {
                    if( message )
                    {
                        toast.info(message);
                    }
                });
        };

        /**
         * Check for modules updates
         */
        self.checkModulesUpdates = function() {
            toast.loading('Checking modules updates...');
            var message = null;
            systemService.checkModulesUpdates()
                .then(function(resp) {
                    //update current status
                    self.lastCheckModules = resp.data.lastcheckmodules;

                    //user message
                    if( resp.data.modulesupdateavailable===true )
                    {
                        //priority to installed module updates
                        message = 'Update(s) available. Please check installed modules list';
                    }
                    else if( resp.data.moduleslistupdated===true )
                    {
                        //if no installed modules update, display new modules are available
                        message = 'No installed modules update but new modules available for install';
                    }
                    else {
                        message = 'No update available';
                    }

                    return cleepService.loadConfig();
                })
                .finally(function() {
                    if( message )
                    {
                        toast.info(message);
                    }
                });
        };

        /**
         * Close logs dialog
         */
        self.closeDialog = function() {
            $mdDialog.hide();
        };

        /**
         * Show update logs
         */
        self.showLogsDialog = function(ev) {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'updateLogsCtl',
                templateUrl: 'logs.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true
            })
            .then(function() {}, function() {});
        };

        /**
         * Show update dialog
         */
        self.showUpdateDialog = function(ev) {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'updateCtl',
                templateUrl: 'update.dialog.html',
                parent: angular.element(document.body),
                targetEvent: ev,
                clickOutsideToClose: true,
                fullscreen: true
            })
            .then(function() {}, function() {});
        };

        /**
         * Update cleep
         */
        self.updateCleep = function() {
            toast.loading('Updating device application...');
            systemService.updateCleep();
        };

        /** 
         * Watch for config changes
         */
        $rootScope.$watchCollection(function() {
            return cleepService.modules['system'];
        }, function(newConfig, oldConfig) {
            if( newConfig )
            {   
                self.setConfig(newConfig.config);
            }   
        });


        /**************
         * Backup tab
         **************/

        /**
         * Trigger configuration backup
         */
        self.backupConfiguration = function() {
            systemService.backupCleepConfig()
                .then(function() {
                    toast.success('Configuration saved');
                });
        };

        /**
         * Set backup config delay
         */
        self.setBackupDelay = function() {
            systemService.setCleepBackupDelay(Number(self.backupDelay))
                .then(function() {
                    toast.success('Delay saved');
                });
        };

        /**
         * Set filesystem protection
         */
        self.setFilesystemProtection = function() {
            //TODO
        };

        /**************
         * Advanced tab
         **************/

        /**
         * Save monitoring
         */
        self.updateMonitoring = function(fromCheckbox) {
            if( !fromCheckbox )
            {
                //row clicked, we need to update flag
                self.monitoring = !self.monitoring;
            }

            //delay update to make sure model value is updated
            $timeout(function() {
                systemService.setMonitoring(self.monitoring)
                    .then(function(resp) {
                        return cleepService.reloadModuleConfig('system');
                    })
                    .then(function(config) {
                        //set config
                        self.setConfig(config);
                    })
                    .finally(function() {
                        //user message
                        toast.success('Monitoring updated');
                    });
            }, 250);
        };

        /**
         * Save crash report
         */
        self.updateCrashReport = function(fromCheckbox) {
            if( !fromCheckbox )
            {
                //row clicked, we need to update flag
                self.crashReport = !self.crashReport;
            }

            //delay update to make sure model value is updated
            $timeout(function() {
                systemService.setCrashReport(self.crashReport)
                    .then(function(resp) {
                        return cleepService.reloadModuleConfig('system');
                    })
                    .then(function(config) {
                        //set config
                        self.setConfig(config);
                    })
                    .finally(function() {
                        //user message
                        if( self.crashReport )
                        {
                            toast.success('Crash report enabled');
                        }
                        else
                        {
                            toast.success('Crash report disabled');
                        }
                    });
            }, 250);
        };


        /**
         * Reboot system
         */
        self.reboot = function() {
            confirm.open('Confirm device reboot?', null, 'Reboot device')
                .then(function() {
                    return systemService.reboot();
                })
                .then(function() {
                    toast.success('System will reboot');
                });
        };

        /**
         * Halt system
         */
        self.halt = function() {
            confirm.open('Confirm device shutdown?', null, 'Halt device')
                .then(function() {
                    systemService.halt();
                })
                .then(function() {
                    toast.success('System will halt');
                });
        };

        /**
         * Restart cleep
         */
        self.restart = function() {
            confirm.open('Confirm application restart?', null, 'Restart software')
                .then(function() {
                    systemService.restart();
                })
                .then(function() {
                    toast.success('Software will restart');
                });
        };

        
        /************
         * Renderings
         ************/

        /**
         * Update renderings
         */
        self.updateRendering = function(rendering, fromCheckbox) {
            if( !fromCheckbox )
            {
                //row clicked, we need to update flag
                rendering.disabled = !rendering.disabled;
            }

            //update events not rendered status
            $timeout(function() {
                systemService.setEventNotRendered(rendering.renderer, rendering.event, rendering.disabled)
                    .then(function(resp) {
                        return cleepService.reloadModuleConfig('system');
                    })
                    .then(function(config) {
                        //set config
                        self.setConfig(config);
                    });
            }, 250);
        };

        /**
         * Is event not rendered ?
         * @param renderer: renderer name
         * @param event: event name
         * @return: true if event is not rendered, false otherwise
         */
        self._isEventNotRendered = function(renderer, event)
        {
            for( var i=0; i<self.eventsNotRendered.length; i++ )
            {
                if( self.eventsNotRendered[i].renderer===renderer && self.eventsNotRendered[i].event===event )
                {
                    //found
                    return true;
                }
            }

            return false;
        };

        /**
         * Init useable renderings list
         * @param events: list of events
         * @param renderers: list of renderers
         */
        self._initRenderings = function(events, renderers)
        {
            //prepare renderings list
            //for each renderer search handled events via profile matching
            for( var renderer in renderers )
            {
                for( i=0; i<renderers[renderer].length; i++ )
                {
                    var renderer_profile = renderers[renderer][i];
                    for( var event in events )
                    {
                        for( var j=0; j<events[event]['profiles'].length; j++ )
                        {
                            var event_profile = events[event]['profiles'][j];
                            if( event_profile===renderer_profile )
                            {
                                //match found, save new entry
                                self.renderings.push({
                                    'renderer': renderer,
                                    'event': event,
                                    'disabled': self._isEventNotRendered(renderer, event)
                                });
                                break;
                            }
                        }
                    }
                }
            }
        };

        /******************
         * Troubleshoot tab
         ******************/

        /**
         * Download logs
         */
        self.downloadLogs = function() {
            systemService.downloadLogs();
        };

        /**
         * Get logs
         */
        self.getLogs = function() {
            systemService.getLogs()
                .then(function(resp) {
                    self.logs = resp.data.join('');
                    self.refreshEditor();
                });
        };

        /**
         * Refresh editor
         */
        self.refreshEditor = function()
        {
            self.codemirrorInstance.refresh();
        };

        /**
         * Module debug changed
         */
        self.moduleDebugChanged = function(module)
        {
            systemService.setModuleDebug(module, self.debugs[module].debug);
        };

        /**
         * System debug changed
         */
        self.systemDebugChanged = function()
        {
            systemService.setSystemDebug(self.debugSystem);
        };

        /**
         * Trace changed
         */
        self.traceChanged = function()
        {
            systemService.setTrace(self.debugTrace)
                .then(function() {
                    var message = 'Trace enabled';
                    if( !self.debugTrace )
                        message = 'Trace disabled';
                        
                    toast.success('' + message +'. Please restart application');
                });
        };

        /**
         * Set module config
         */
        self.setConfig = function(config)
        {
            //save data
            self.monitoring = config.monitoring;
            self.uptime = config.uptime;
            self.needRestart = config.needrestart;
            self.needReboot = config.needreboot;
            self.crashReport = config.crashreport;
            self.version = config.version;
            self.eventsNotRendered = config.eventsnotrendered;
            self.debugSystem = config.debug.system;
            self.debugTrace = config.debug.trace;
            self.lastCheckCleep = config.lastcheckcleep;
            self.lastCheckModules = config.lastcheckmodules;
            self.cleepUpdateEnabled = config.cleepupdateenabled;
            self.modulesUpdateEnabled = config.modulesupdateenabled;
            self.cleepUpdateAvailable = config.cleepupdateavailable;
            self.cleepUpdateChangelog = config.cleepupdatechangelog;
            self.modulesUpdateAvailable = config.modulesupdateavailable;
            self.lastCleepUpdate = config.lastcleepupdate;
            self.lastCleepUpdate.stdoutStr = config.lastcleepupdate.stdout.join('\n');
            self.lastCleepUpdate.stderrStr = config.lastcleepupdate.stderr.join('\n');
            self.lastCleepUpdate.processStr = config.lastcleepupdate.process ? config.lastcleepupdate.process.join('\n') : '';
            self.lastModulesProcessing = config.lastmodulesprocessing;
            self.cleepUpdatePending = config.cleepupdatepending;
            self.backupDelay = config.cleepbackupdelay;
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            //get preselected tab index
            if( $location.search().tab )
            {
                console.log('tab = ', $location.search())
                self.tabIndex = $location.search().tab;
            }

            //init
            $q.all([cleepService.getEvents(), cleepService.getRenderers()])
                .then(function(resps) {
                    self._initRenderings(resps[0], resps[1]);

                    //get system config
                    return cleepService.getModuleConfig('system');
                })
                .then(function(config) {
                    //set module config
                    self.setConfig(config);
                    
                    //request for modules debug status
                    return cleepService.getModulesDebug();
                })
                .then(function(debug) {
                    self.debugs = debug.data;
                });
        };

    }];

    var systemLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        templateUrl: 'system.config.html',
        replace: true,
        scope: true,
        controller: systemController,
        controllerAs: 'systemCtl',
        link: systemLink
    };
};

var Cleep = angular.module('Cleep');
Cleep.directive('systemConfigDirective', ['$rootScope', '$filter', '$timeout', '$q', 'toastService', 'systemService', 'cleepService', 'confirmService', '$mdDialog', '$location', systemConfigDirective]);

