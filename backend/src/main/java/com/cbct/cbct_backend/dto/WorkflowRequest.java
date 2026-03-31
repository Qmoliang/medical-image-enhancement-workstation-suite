package com.cbct.cbct_backend.dto;

public class WorkflowRequest {
    private String sourceRoot;
    private String workspaceRoot;
    private String patientFolder;
    private String cbctName;
    private String qactName;
    private String matchText;
    private String roiName;
    private Integer shift;
    private Integer cbctYExtra;
    private Integer ctYShift;
    private Boolean applyCtMask;
    private String processedRawPath;
    private String modelName;
    private Integer offsetX;
    private Integer offsetY;

    public String getSourceRoot() { return sourceRoot; }
    public void setSourceRoot(String sourceRoot) { this.sourceRoot = sourceRoot; }
    public String getWorkspaceRoot() { return workspaceRoot; }
    public void setWorkspaceRoot(String workspaceRoot) { this.workspaceRoot = workspaceRoot; }
    public String getPatientFolder() { return patientFolder; }
    public void setPatientFolder(String patientFolder) { this.patientFolder = patientFolder; }
    public String getCbctName() { return cbctName; }
    public void setCbctName(String cbctName) { this.cbctName = cbctName; }
    public String getQactName() { return qactName; }
    public void setQactName(String qactName) { this.qactName = qactName; }
    public String getMatchText() { return matchText; }
    public void setMatchText(String matchText) { this.matchText = matchText; }
    public String getRoiName() { return roiName; }
    public void setRoiName(String roiName) { this.roiName = roiName; }
    public Integer getShift() { return shift; }
    public void setShift(Integer shift) { this.shift = shift; }
    public Integer getCbctYExtra() { return cbctYExtra; }
    public void setCbctYExtra(Integer cbctYExtra) { this.cbctYExtra = cbctYExtra; }
    public Integer getCtYShift() { return ctYShift; }
    public void setCtYShift(Integer ctYShift) { this.ctYShift = ctYShift; }
    public Boolean getApplyCtMask() { return applyCtMask; }
    public void setApplyCtMask(Boolean applyCtMask) { this.applyCtMask = applyCtMask; }
    public String getProcessedRawPath() { return processedRawPath; }
    public void setProcessedRawPath(String processedRawPath) { this.processedRawPath = processedRawPath; }
    public String getModelName() { return modelName; }
    public void setModelName(String modelName) { this.modelName = modelName; }
    public Integer getOffsetX() { return offsetX; }
    public void setOffsetX(Integer offsetX) { this.offsetX = offsetX; }
    public Integer getOffsetY() { return offsetY; }
    public void setOffsetY(Integer offsetY) { this.offsetY = offsetY; }
}
