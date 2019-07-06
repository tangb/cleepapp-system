/**
 * Monitor widget directive
 * Display system monitor dashboard widget
 */
var widgetMonitorDirective = function(raspiotService, $mdDialog, systemService, $q) {

    var widgetMonitorController = ['$scope', function($scope) {
        var self = this;
        self.device = $scope.device;
        self.hasCharts = raspiotService.isAppInstalled('charts');
        self.monitoring = systemService.monitoring;
        //self.tabIndex = 'hardware';
        self.monitorCpu = null;
        self.monitorMemory = null;
        //self.monitorDiskSystem = null;
        self.chartCpuOptions = {
            type: 'line',
            label: '%',
            height: 200,
            format: function(v) {
                return Math.round(v);
            },
            title: 'CPU usage',
            showControls: false
        };
        self.chartMemoryOptions = {
            type: 'line',
            format: function(v) {
                //bytes to Mo (1024*1024)
                return Math.round(v / 1048576);
            },
            label: 'Mo',
            height: 200,
            title: 'Memory usage',
            showControls: false
        };
        /*self.graphDiskSystemDeferred = null;
        self.graphDiskSystemOptions = {
            type: 'pie',
            height: 200,
            loadData: function(start, end) {
                return self.graphDiskSystemDeferred.promise;
            },
            format: function(v) {
                //bytes to Mo
                tmp = v / 1048576;
                if( tmp>1000 )
                {
                    //bytes to Go
                    tmp = v / 1073741824;
                }
                return tmp;
            },
            title: 'System partition (/)',
            showControls: false
        };
        self.graphDistExt1Show = true;
        self.graphDiskExt1Deferred = null;
        self.graphDiskExt1Options = {
            type: 'pie',
            height: 200,
            loadData: function(start, end) {
                return self.graphDiskExt1Deferred.promise;
            },
            format: function(v) {
                //bytes to Mo
                tmp = v / 1048576;
                if( tmp>1000 )
                {
                    //bytes to Go
                    tmp = v / 1073741824;
                }
                return tmp;
            },
            title: 'External1 ()',
            showControls: false
        };
        self.graphDistExt2Show = true;
        self.graphDiskExt2Deferred = null;
        self.graphDiskExt2Options = {
            type: 'pie',
            height: 200,
            loadData: function(start, end) {
                return self.graphDiskExt2Deferred.promise;
            },
            format: function(v) {
                //bytes to Mo
                tmp = v / 1048576;
                if( tmp>1000 )
                {
                    //bytes to Go
                    tmp = v / 1073741824;
                }
                return tmp;
            },
            title: 'External2 ()',
            showControls: false
        };*/

        /**
         * Return partition data for pie chart (internal use)
         */
        self.__getPartitionData = function(used, free)
        {
            return {
                used: {
                    name: 'used',
                    value: used
                },
                free: {
                    name: 'free',
                    value: free
                }
            };
        };

        /**
         * Load dialog data
         */
        self.loadDialogData = function()
        {
        };

        /**
         * Show dialog event
         */
        self.showDialog = function()
        {
        };

        /**
         * Cancel dialog
         */
        self.cancelDialog = function()
        {
            $mdDialog.cancel();
        };

        /**
         * Open dialog
         */
        self.openDialog = function() {
            $mdDialog.show({
                controller: function() { return self; },
                controllerAs: 'monitorCtl',
                templateUrl: 'monitorDialog.widget.html',
                parent: angular.element(document.body),
                clickOutsideToClose: true,
                onShowing: self.showDialog,                
                onComplete: self.loadDialogData
            });
        };

        /**
         * Init controller
         */
        self.init = function()
        {
            //get cpu and memory devices
            for( var i=0; i<raspiotService.devices.length; i++ )
            {
                if( raspiotService.devices[i].type==='monitorcpu' )
                {
                    self.monitorCpu = raspiotService.devices[i];
                }
                else if( raspiotService.devices[i].type==='monitormemory' )
                {
                    self.monitorMemory = raspiotService.devices[i];
                }
            }
        };

    }];

    var widgetMonitorLink = function(scope, element, attrs, controller) {
        controller.init();
    };

    return {
        restrict: 'EA',
        templateUrl: 'monitor.widget.html',
        replace: true,
        scope: {
            'device': '='
        },
        controller: widgetMonitorController,
        controllerAs: 'widgetCtl',
        link: widgetMonitorLink
    };
};

var RaspIot = angular.module('RaspIot');
RaspIot.directive('widgetMonitorDirective', ['raspiotService', '$mdDialog', 'systemService', '$q', widgetMonitorDirective]);

