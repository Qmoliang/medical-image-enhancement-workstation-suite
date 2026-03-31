package com.cbct.cbct_backend.service;

import com.cbct.cbct_backend.dto.ApiResponse;
import com.cbct.cbct_backend.dto.InferenceRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.Map;

@Service
public class InferenceService {
    private final PythonBridgeService pythonBridgeService;

    public InferenceService(PythonBridgeService pythonBridgeService) {
        this.pythonBridgeService = pythonBridgeService;
    }

    public ResponseEntity<ApiResponse<Map<String, Object>>> run(InferenceRequest request) {
        return pythonBridgeService.invokeInferenceRun(request);
    }

    public SseEmitter runStream(InferenceRequest request) {
        return pythonBridgeService.invokeInferenceStream(request);
    }

    public ResponseEntity<ApiResponse<Map<String, Object>>> merge(InferenceRequest request) {
        return pythonBridgeService.invokeInferenceMerge(request);
    }
}
