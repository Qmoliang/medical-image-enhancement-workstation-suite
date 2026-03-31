package com.cbct.cbct_backend.dto;

public class InferenceRequest {
    private String modelDir;
    private String modelKind;
    private String datasetName;
    private String gpuIds;

    public String getModelDir() { return modelDir; }
    public void setModelDir(String modelDir) { this.modelDir = modelDir; }
    public String getModelKind() { return modelKind; }
    public void setModelKind(String modelKind) { this.modelKind = modelKind; }
    public String getDatasetName() { return datasetName; }
    public void setDatasetName(String datasetName) { this.datasetName = datasetName; }
    public String getGpuIds() { return gpuIds; }
    public void setGpuIds(String gpuIds) { this.gpuIds = gpuIds; }
}
