package com.cbct.cbct_backend.controller;

import com.cbct.cbct_backend.dto.ApiResponse;
import com.cbct.cbct_backend.dto.WorkflowRequest;
import com.cbct.cbct_backend.service.PythonBridgeService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/method2")
@CrossOrigin
public class Method2Controller {
    private final PythonBridgeService pythonBridgeService;

    public Method2Controller(PythonBridgeService pythonBridgeService) {
        this.pythonBridgeService = pythonBridgeService;
    }

    @PostMapping("/defaults")
    public ResponseEntity<ApiResponse<Map<String, Object>>> defaults() { return pythonBridgeService.invokeMethod2Defaults(); }
    @PostMapping("/run_match")
    public ResponseEntity<ApiResponse<Map<String, Object>>> runMatch(@RequestBody WorkflowRequest request) { return pythonBridgeService.invokeMethod2("run_match", request); }
    @PostMapping("/roi_options")
    public ResponseEntity<ApiResponse<Map<String, Object>>> roiOptions(@RequestBody WorkflowRequest request) { return pythonBridgeService.invokeMethod2("roi_options", request); }
    @PostMapping("/step1")
    public ResponseEntity<ApiResponse<Map<String, Object>>> step1(@RequestBody WorkflowRequest request) { return pythonBridgeService.invokeMethod2("step1", request); }
    @PostMapping("/step2")
    public ResponseEntity<ApiResponse<Map<String, Object>>> step2(@RequestBody WorkflowRequest request) { return pythonBridgeService.invokeMethod2("step2", request); }
    @PostMapping("/step3")
    public ResponseEntity<ApiResponse<Map<String, Object>>> step3(@RequestBody WorkflowRequest request) { return pythonBridgeService.invokeMethod2("step3", request); }
    @PostMapping("/step4")
    public ResponseEntity<ApiResponse<Map<String, Object>>> step4(@RequestBody WorkflowRequest request) { return pythonBridgeService.invokeMethod2("step4", request); }
    @PostMapping("/step5")
    public ResponseEntity<ApiResponse<Map<String, Object>>> step5(@RequestBody WorkflowRequest request) { return pythonBridgeService.invokeMethod2("step5", request); }
    @PostMapping("/step6")
    public ResponseEntity<ApiResponse<Map<String, Object>>> step6(@RequestBody WorkflowRequest request) { return pythonBridgeService.invokeMethod2("step6", request); }
}
