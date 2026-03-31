package com.cbct.cbct_backend.service;

import com.cbct.cbct_backend.dto.PipelineRequest;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@Service
public class PipelineService {
    private final PythonBridgeService pythonBridgeService;

    public PipelineService(PythonBridgeService pythonBridgeService) {
        this.pythonBridgeService = pythonBridgeService;
    }

    public SseEmitter run(PipelineRequest request) {
        return pythonBridgeService.invokePipelineRun(request);
    }
}
