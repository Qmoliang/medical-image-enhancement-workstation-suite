package com.cbct.cbct_backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "app.paths")
public class AppPathProperties {
    private String projectRoot;
    private String pythonRoot;
    private String workspaceRoot;
    private String legacyProjectRoot;
    private String dataRoot;
    private String testPatientRoot;
    private String dicomResultsDir;
    private String rawRoot;
    private String dicomRoot;
    private String patientParamsJson;
    private String patientRenameJson;
    private String processPipelineScript;
    private String extractMergeScript;

    public String getProjectRoot() { return projectRoot; }
    public void setProjectRoot(String projectRoot) { this.projectRoot = projectRoot; }
    public String getPythonRoot() { return pythonRoot; }
    public void setPythonRoot(String pythonRoot) { this.pythonRoot = pythonRoot; }
    public String getWorkspaceRoot() { return workspaceRoot; }
    public void setWorkspaceRoot(String workspaceRoot) { this.workspaceRoot = workspaceRoot; }
    public String getLegacyProjectRoot() { return legacyProjectRoot; }
    public void setLegacyProjectRoot(String legacyProjectRoot) { this.legacyProjectRoot = legacyProjectRoot; }
    public String getDataRoot() { return dataRoot; }
    public void setDataRoot(String dataRoot) { this.dataRoot = dataRoot; }
    public String getTestPatientRoot() { return testPatientRoot; }
    public void setTestPatientRoot(String testPatientRoot) { this.testPatientRoot = testPatientRoot; }
    public String getDicomResultsDir() { return dicomResultsDir; }
    public void setDicomResultsDir(String dicomResultsDir) { this.dicomResultsDir = dicomResultsDir; }
    public String getRawRoot() { return rawRoot; }
    public void setRawRoot(String rawRoot) { this.rawRoot = rawRoot; }
    public String getDicomRoot() { return dicomRoot; }
    public void setDicomRoot(String dicomRoot) { this.dicomRoot = dicomRoot; }
    public String getPatientParamsJson() { return patientParamsJson; }
    public void setPatientParamsJson(String patientParamsJson) { this.patientParamsJson = patientParamsJson; }
    public String getPatientRenameJson() { return patientRenameJson; }
    public void setPatientRenameJson(String patientRenameJson) { this.patientRenameJson = patientRenameJson; }
    public String getProcessPipelineScript() { return processPipelineScript; }
    public void setProcessPipelineScript(String processPipelineScript) { this.processPipelineScript = processPipelineScript; }
    public String getExtractMergeScript() { return extractMergeScript; }
    public void setExtractMergeScript(String extractMergeScript) { this.extractMergeScript = extractMergeScript; }
}
