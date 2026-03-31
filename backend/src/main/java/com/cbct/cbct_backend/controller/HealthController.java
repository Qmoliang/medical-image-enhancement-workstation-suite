package com.cbct.cbct_backend.controller;

import com.cbct.cbct_backend.config.AppPathProperties;
import com.cbct.cbct_backend.dto.ApiResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class HealthController {
    private final AppPathProperties appPathProperties;

    public HealthController(AppPathProperties appPathProperties) {
        this.appPathProperties = appPathProperties;
    }

    @GetMapping("/health")
    public ResponseEntity<ApiResponse<Map<String, Object>>> health() {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("status", "UP");
        data.put("projectRoot", appPathProperties.getProjectRoot());
        data.put("pythonRoot", appPathProperties.getPythonRoot());
        data.put("workspaceRoot", appPathProperties.getWorkspaceRoot());
        data.put("legacyProjectRoot", appPathProperties.getLegacyProjectRoot());
        data.put("dataRoot", appPathProperties.getDataRoot());
        data.put("testPatientRoot", appPathProperties.getTestPatientRoot());
        data.put("dicomResultsDir", appPathProperties.getDicomResultsDir());
        data.put("rawRoot", appPathProperties.getRawRoot());
        data.put("dicomRoot", appPathProperties.getDicomRoot());
        data.put("patientParamsJson", appPathProperties.getPatientParamsJson());
        data.put("patientRenameJson", appPathProperties.getPatientRenameJson());
        data.put("processPipelineScript", appPathProperties.getProcessPipelineScript());
        data.put("extractMergeScript", appPathProperties.getExtractMergeScript());
        return ResponseEntity.ok(ApiResponse.success("ok", data));
    }
}
