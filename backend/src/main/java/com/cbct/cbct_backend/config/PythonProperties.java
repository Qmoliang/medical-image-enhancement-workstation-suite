package com.cbct.cbct_backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "app.python")
public class PythonProperties {
    private String executable;
    private String workingDirectory;
    private String bridgeScript;

    public String getExecutable() {
        return executable;
    }

    public void setExecutable(String executable) {
        this.executable = executable;
    }

    public String getWorkingDirectory() {
        return workingDirectory;
    }

    public void setWorkingDirectory(String workingDirectory) {
        this.workingDirectory = workingDirectory;
    }

    public String getBridgeScript() {
        return bridgeScript;
    }

    public void setBridgeScript(String bridgeScript) {
        this.bridgeScript = bridgeScript;
    }
}