package com.cbct.cbct_backend.service;

import com.cbct.cbct_backend.dto.ApiResponse;
import com.cbct.cbct_backend.dto.DicomRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class DicomService {
    private final PythonBridgeService pythonBridgeService;

    public DicomService(PythonBridgeService pythonBridgeService) {
        this.pythonBridgeService = pythonBridgeService;
    }

    public ResponseEntity<ApiResponse<Map<String, Object>>> defaults() {
        return pythonBridgeService.invokeDicomDefaults();
    }

    public ResponseEntity<ApiResponse<Map<String, Object>>> export(DicomRequest request) {
        return pythonBridgeService.invokeDicomExport(request);
    }
}
