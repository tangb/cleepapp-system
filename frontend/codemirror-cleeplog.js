(function(mod) {
  if (typeof exports == "object" && typeof module == "object") // CommonJS
    mod(require("../../lib/codemirror"));
  else if (typeof define == "function" && define.amd) // AMD
    define(["../../lib/codemirror"], mod);
  else // Plain browser env
    mod(CodeMirror);
})(function(CodeMirror) {
    "use strict";
    CodeMirror.defineMode("cleeplog", function() {
        var logMessageStyle = '';
        return {
            token: function(stream, state) {
                var logInfo = stream.match(/\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\s+(.*?)\s+\[.*\] /);
                if (logInfo) {
                    return 'styleLogInfo'
                }
                var logType = stream.match(/TRACE|DEBUG|INFO|WARNING|WARN|ERROR|FATAL|CRITICAL/)
                if(logType) {
                    logMessageStyle = 'styleLogMessage'+logType;
                    return 'styleLogType'+logType;
                }
                var logMessage = stream.match(/.*/);
                if(logMessage) {
                    return logMessageStyle;
                }
                stream.next();
            }
        };
    });
});

