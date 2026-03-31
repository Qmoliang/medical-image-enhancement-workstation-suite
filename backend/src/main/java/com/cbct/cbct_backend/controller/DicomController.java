package com.cbct.cbct_backend.controller;

import com.cbct.cbct_backend.dto.ApiResponse;
import com.cbct.cbct_backend.dto.DicomRequest;
import com.cbct.cbct_backend.service.DicomService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/dicom")
@CrossOrigin
public class DicomController {
    private final DicomService dicomService;

    public DicomController(DicomService dicomService) {
        this.dicomService = dicomService;
    }

    @PostMapping("/defaults")
    public ResponseEntity<ApiResponse<Map<String, Object>>> defaults() { return dicomService.defaults(); }

    @PostMapping("/export")
    public ResponseEntity<ApiResponse<Map<String, Object>>> export(@RequestBody DicomRequest request) {
        return dicomService.export(request);
    }
}
