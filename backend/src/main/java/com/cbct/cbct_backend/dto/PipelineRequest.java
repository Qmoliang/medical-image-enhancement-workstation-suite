package com.cbct.cbct_backend.dto;

public class PipelineRequest {
    private String dataset;
    private String modelCategory;
    private String modelName;

    public String getDataset() { return dataset; }
    public void setDataset(String dataset) { this.dataset = dataset; }
    public String getModelCategory() { return modelCategory; }
    public void setModelCategory(String modelCategory) { this.modelCategory = modelCategory; }
    public String getModelName() { return modelName; }
    public void setModelName(String modelName) { this.modelName = modelName; }
}
