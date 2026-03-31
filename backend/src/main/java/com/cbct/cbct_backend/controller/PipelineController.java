package com.cbct.cbct_backend.controller;

import com.cbct.cbct_backend.dto.PipelineRequest;
import com.cbct.cbct_backend.service.PipelineService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api/pipeline")
@CrossOrigin
public class PipelineController {
    private final PipelineService pipelineService;

    public PipelineController(PipelineService pipelineService) {
        this.pipelineService = pipelineService;
    }

    @PostMapping(value = "/run", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter run(@RequestBody PipelineRequest request) {
        return pipelineService.run(request);
    }
}
