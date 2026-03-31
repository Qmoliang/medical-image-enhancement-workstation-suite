package com.cbct.cbct_backend.dto;

import java.util.List;

public class ProcessResult {
    private int exitCode;
    private List<String> command;
    private String workingDirectory;
    private String output;

    public ProcessResult() {}

    public ProcessResult(int exitCode, List<String> command, String workingDirectory, String output) {
        this.exitCode = exitCode;
        this.command = command;
        this.workingDirectory = workingDirectory;
        this.output = output;
    }

    public int getExitCode() { return exitCode; }
    public void setExitCode(int exitCode) { this.exitCode = exitCode; }
    public List<String> getCommand() { return command; }
    public void setCommand(List<String> command) { this.command = command; }
    public String getWorkingDirectory() { return workingDirectory; }
    public void setWorkingDirectory(String workingDirectory) { this.workingDirectory = workingDirectory; }
    public String getOutput() { return output; }
    public void setOutput(String output) { this.output = output; }
}
