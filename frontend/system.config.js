/**
 * System config component
 * Handle system configuration
 */
angular
.module('Cleep')
.directive('systemConfigComponent', ['$rootScope', '$timeout', '$q', 'toastService', 'systemService', 'cleepService', 'confirmService', '$location',
function($rootScope, $timeout, $q, toast, systemService, cleepService, confirm, $location) {
    var systemController = ['$scope', function($scope) {
        var self = this;
        self.config = {};
        self.systemService = systemService;
        self.tabIndex = 'drivers';
        self.needRestart = false;
        self.debugs = {};
        self.renderings = [];

        self.codemirrorInstance = null;
        self.codemirrorOptions = {
            lineWrapping: true,
            lineNumbers: true,
            tabSize: 2,
            readOnly: true,
            onLoad: function(cmInstance) {
                self.codemirrorInstance = cmInstance;
                cmInstance.focus();
            }
        };

        /**************
         * Backup tab
         **************/

        /**
         * Trigger configuration backup
         */
        self.backupConfiguration = function() {
            systemService.backupCleepConfig()
                .then(function() {
                    toast.success('Configuration backuped');
                });
        };

        /**
         * Set backup config delay
         */
        self.setBackupDelay = function() {
            systemService.setCleepBackupDelay(Number(self.config.cleepbackupdelay))
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
            if( !fromCheckbox ) {
                // row clicked, we need to update flag
                self.config.monitoring = !self.config.monitoring;
            }

            // delay update to make sure model value is updated
            systemService.setMonitoring(self.config.monitoring)
                .then(function(resp) {
                    cleepService.reloadModuleConfig('system');
                    toast.success('Monitoring updated');
                });
        };

        /**
         * Save crash report
         */
        self.updateCrashReport = function(fromCheckbox) {
            if( !fromCheckbox ) {
                // row clicked, we need to update flag
                self.config.crashreport = !self.config.crashreport;
            }

            //delay update to make sure model value is updated
            $timeout(function() {
                systemService.setCrashReport(self.config.crashreport)
                    .then(function(resp) {
                        cleepService.reloadModuleConfig('system');

                        // user message
                        if( self.config.crashreport ) {
                            toast.success('Crash report enabled');
                        } else {
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
            if( !fromCheckbox ) {
                //row clicked, we need to update flag
                rendering.disabled = !rendering.disabled;
            }

            //update events not rendered status
            $timeout(function() {
                systemService.setEventNotRendered(rendering.renderer, rendering.event, rendering.disabled)
                    .then(function(resp) {
                        cleepService.reloadModuleConfig('system');
                    });
            }, 250);
        };

        /**
         * Is event not rendered ?
         * @param renderer: renderer name
         * @param event: event name
         * @return: true if event is not rendered, false otherwise
         */
        self._isEventNotRendered = function(renderer, event) {
            for( var i=0; i<self.eventsNotRendered.length; i++ ) {
                if( self.eventsNotRendered[i].renderer===renderer && self.eventsNotRendered[i].event===event ) {
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
        self._initRenderings = function(events, renderers) {
            // prepare renderings list
            // for each renderer search handled events via profile matching
            for( var renderer in renderers ) {
                for( i=0; i<renderers[renderer].length; i++ ) {
                    var renderer_profile = renderers[renderer][i];
                    for( var event in events ) {
                        for( var j=0; j<events[event]['profiles'].length; j++ ) {
                            var event_profile = events[event]['profiles'][j];
                            if( event_profile===renderer_profile ) {
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
        self.refreshEditor = function() {
            self.codemirrorInstance.refresh();
        };

        /**
         * Module debug changed
         */
        self.moduleDebugChanged = function(module) {
            systemService.setModuleDebug(module, self.debugs[module].debug);
        };

        /**
         * System debug changed
         */
        self.systemDebugChanged = function() {
            systemService.setSystemDebug(self.debugSystem);
        };

        /**
         * Trace changed
         */
        self.traceChanged = function() {
            systemService.setTrace(self.debugTrace)
                .then(function() {
                    var message = 'Trace enabled';
                    if( !self.debugTrace )
                        message = 'Trace disabled';
                        
                    toast.success('' + message +'. Please restart application');
                });
        };

        /**
         * Init controller
         */
        self.$onInit = function() {
            // get preselected tab index
            if( $location.search().tab ) {
                self.tabIndex = $location.search().tab;
            }

            // load all needed stuff
            $q.all([cleepService.getEvents(), cleepService.getRenderers(), cleepService.getModulesDebug()])
                .then(function(resps) {
                    self._initRenderings(resps[0], resps[1]);
                    self.debugs = resps[2].data;
                });
        };

        /** 
         * Watch configuration changes
         */
        $rootScope.$watch(
            function() {
                return cleepService.modules['system'].config;
            },  
            function(newVal, oldVal) {
                if( newVal && Object.keys(newVal).length ) { 
                    Object.assign(self.config, newVal);
                }   
            }   
        );

    }];

    return {
        templateUrl: 'system.config.html',
        replace: true,
        scope: true,
        controller: systemController,
        controllerAs: 'systemCtl',
    };
}]);

