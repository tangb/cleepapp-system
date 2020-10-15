# cleepmod-system

System application for Cleep.

This application groups some useful features to manage your device.

## Drivers panel

This panel displays all drivers installed and allow you to repair it reinstalling them in case of problem.

You can also uninstall them (without uninstalling the driver application)

##  Backup panel

SD-card is the weakness of the raspberry. To reduce SD-card corruption, Cleep runs by default on a read-only filesystem.
All configuration is stored in a versatile memory and cleared each time device restarts.

The backup feature writes data on SD-card after a delay and allow you to trigger manually a backup.

## Renderings panel

This panel displays all event with associated renderer and give you a way to disable it.

It is useful when you install a renderer and a service and you don't want to render service event on the renderer.
For example you installed a screen app and a weather service app and you don't want to render weather data on the screen.

## Advanced options panel

Options in this panel allows you to restart or halt properly the device.
Properly means Cleep configuration will be saved before action.

It also allow you to restart Cleep application.

Crash report is an option to send data to our server to report fatal errors. It doesn't send private informations.
This feature allows Cleep team to know a problem occured and improve the application in next releases.

Monitoring option add a feature to monitor CPU and memory of the device creating charts and adding a widget on the device dashboard.

## Troubleshoot

This panel is used to watch Cleep logs to investigate on a problem.

It also offers possibilty to enable debug on installed applications or on core modules.

