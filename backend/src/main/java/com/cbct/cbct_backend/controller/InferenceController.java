package com.cbct.cbct_backend.controller;

import com.cbct.cbct_backend.dto.ApiResponse;
import com.cbct.cbct_backend.dto.InferenceRequest;
import com.cbct.cbct_backend.service.InferenceService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.Map;

@RestController
@RequestMapping("/api/inference")
@CrossOrigin
public class InferenceController {
    private final InferenceService inferenceService;

    public InferenceController(InferenceService inferenceService) {
        this.inferenceService = inferenceService;
    }

    @PostMapping("/run")
    public ResponseEntity<ApiResponse<Map<String, Object>>> run(@RequestBody InferenceRequest request) {
        return inferenceService.run(request);
    }

    @PostMapping("/stream")
    public SseEmitter runStream(@RequestBody InferenceRequest request) {
        return inferenceService.runStream(request);
    }

    @PostMapping("/merge")
    public ResponseEntity<ApiResponse<Map<String, Object>>> merge(@RequestBody InferenceRequest request) {
        return inferenceService.merge(request);
    }
}
