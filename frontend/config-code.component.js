/**
 * config-code
 * Display content formatted with codemirror
 * You can add button to interact with code
 *
 * Component example:
 * <config-code cl-title="..." cl-buttons="..."></config-code>
 * With:
 *  - cl-title (string): toolbar title (default empty string)
 *  - cl-buttons (array): list of buttons to display on toolbar right side
 *      {
 *          label: button label,
 *          icon: button icon,
 *          style: button style (md-accent, md-raised...) (default "md-primary md-raised"),
 *          click: button click action,
 *          meta: button meta to pass as click parameters (optional),
 *      }
 *  - cl-config (dict): codemirror configuration. See https://codemirror.net/1/manual.html#configuration
 *  - cl-model (any): content displayed in code editor
 */
angular.module('Cleep').component('configCode', {
    template: `
    <md-content layout-fill>
        <md-toolbar class="md-hue-3">
            <div class="md-toolbar-tools">
                <h2 flex md-truncate>{{ $ctrl.clTitle }}</h2>
                <md-button
                    ng-repeat="btn in $ctrl.btns"
                    ng-class="btn.style"
                    ng-click="$ctrl.onClick($event, btn)"
                >
                    <cl-icon ng-if="btn.icon" class="icon-white" cl-mdi="{{ btn.icon }}"></cl-icon>
                    {{ btn.label }}
                </md-button>
            </div>
        </md-toolbar>
        <div ui-codemirror ui-codemirror-opts="$ctrl.config" ng-model="$ctrl.clModel" class="codemirror-code">
    </md-content>
    `,
    bindings: {
        clTitle: '@?',
        clButtons: '<?',
        clConfig: '<?',
        clModel: '<',
    },
    controller: function ($rootScope, cleepService, rpcService, confirmService, toastService) {
        const ctrl = this;
        ctrl.btns = [];
        ctrl.config = {};
        ctrl.cmInstance = null;

        ctrl.$onChanges = function (changes) {
            if (changes.clButtons?.currentValue) {
                ctrl.prepareButtons(changes.clButtons.currentValue);
            }
            if (changes.clConfig?.currentValue) {
                ctrl.prepareConfig(changes.clConfig.currentValue);
            }
            if (changes.clModel?.currentValue) {
                ctrl.refreshEditor();
            }
        };

        ctrl.prepareConfig = function (config) {
            const customOnLoad = config.onLoad;
            ctrl.config = {
                ...config,
                onLoad: (cmInstance) => {
                    ctrl.cmInstance = cmInstance;
                    cmInstance.focus();
                    (customOnLoad || angular.noop)(cmInstance);
                },
            }
        };

        ctrl.prepareButtons = function (buttons) {
            for (const btn of buttons) {
                ctrl.btns.push({
                    label: btn.label ?? '',
                    style: btn.style ?? 'md-primary md-raised',
                    icon: btn.icon,
                    click: btn.click,
                });
            }
        };

        ctrl.refreshEditor = function () {
            ctrl.cmInstance?.refresh();
        };

        ctrl.onClick = ($event, button) => {
            (button.click || angular.noop)(button.meta);
        };
    },
});

