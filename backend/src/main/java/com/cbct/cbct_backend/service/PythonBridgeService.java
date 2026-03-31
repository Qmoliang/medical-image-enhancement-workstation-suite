package com.cbct.cbct_backend.service;

import com.cbct.cbct_backend.dto.*;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

@Service
public class PythonBridgeService {
    @Value("${app.python.executable:python}")
    private String pythonExecutable;

    @Value("${app.python.working-directory:.}")
    private String workingDirectory;

    @Value("${app.python.bridge-script:spring_bridge.py}")
    private String bridgeScript;

    private final ObjectMapper objectMapper = new ObjectMapper();

    private ProcessBuilder processBuilder(List<String> args) {
        List<String> cmd = new ArrayList<>();
        cmd.add(pythonExecutable);
        cmd.add(bridgeScript);
        cmd.addAll(args);
        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.directory(new File(workingDirectory));
        pb.redirectErrorStream(true);
        return pb;
    }

    private Map<String, Object> runJsonInternal(List<String> args) throws Exception {
        Process process = processBuilder(args).start();
        StringBuilder sb = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) sb.append(line).append("\n");
        }
        int exit = process.waitFor();
        String raw = sb.toString().trim();
        if (raw.isEmpty()) throw new RuntimeException("Python bridge returned empty output, exit=" + exit);
        return objectMapper.readValue(raw, new TypeReference<>() {});
    }

    public SseEmitter stream(List<String> args) {
        SseEmitter emitter = new SseEmitter(0L);
        new Thread(() -> {
            Process process = null;
            try {
                process = processBuilder(args).start();
                try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = reader.readLine()) != null) emitter.send(SseEmitter.event().data(line));
                }
                process.waitFor();
                emitter.complete();
            } catch (Exception e) {
                try { emitter.send(SseEmitter.event().data("ERROR: " + e.getMessage())); } catch (Exception ignored) {}
                emitter.completeWithError(e);
            } finally {
                if (process != null) process.destroy();
            }
        }).start();
        return emitter;
    }

    private ResponseEntity<ApiResponse<Map<String, Object>>> ok(Map<String, Object> result) {
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    private ResponseEntity<ApiResponse<Map<String, Object>>> fail(String workflow, String action, Exception e) {
        return ResponseEntity.ok(ApiResponse.error("Python bridge failed", Map.of(
                "workflow", workflow,
                "action", action,
                "error", e.getMessage()
        )));
    }

    private void addWorkflowArgs(List<String> args, WorkflowRequest r) {
        if (r == null) return;
        if (r.getSourceRoot() != null) { args.add("--sourceRoot"); args.add(r.getSourceRoot()); }
        if (r.getWorkspaceRoot() != null) { args.add("--workspaceRoot"); args.add(r.getWorkspaceRoot()); }
        if (r.getPatientFolder() != null) { args.add("--patientFolder"); args.add(r.getPatientFolder()); }
        if (r.getCbctName() != null) { args.add("--cbctName"); args.add(r.getCbctName()); }
        if (r.getQactName() != null) { args.add("--qactName"); args.add(r.getQactName()); }
        if (r.getMatchText() != null) { args.add("--matchText"); args.add(r.getMatchText()); }
        if (r.getRoiName() != null) { args.add("--roiName"); args.add(r.getRoiName()); }
        if (r.getShift() != null) { args.add("--shift"); args.add(String.valueOf(r.getShift())); }
        if (r.getCbctYExtra() != null) { args.add("--cbctYExtra"); args.add(String.valueOf(r.getCbctYExtra())); }
        if (r.getCtYShift() != null) { args.add("--ctYShift"); args.add(String.valueOf(r.getCtYShift())); }
        if (r.getApplyCtMask() != null) { args.add("--applyCtMask"); args.add(String.valueOf(r.getApplyCtMask())); }
        if (r.getProcessedRawPath() != null) { args.add("--processedRawPath"); args.add(r.getProcessedRawPath()); }
        if (r.getModelName() != null) { args.add("--modelName"); args.add(r.getModelName()); }
        if (r.getOffsetX() != null) { args.add("--offsetX"); args.add(String.valueOf(r.getOffsetX())); }
        if (r.getOffsetY() != null) { args.add("--offsetY"); args.add(String.valueOf(r.getOffsetY())); }
    }

    private void addInferenceArgs(List<String> args, InferenceRequest r) {
        if (r == null) return;
        if (r.getModelDir() != null) { args.add("--modelDir"); args.add(r.getModelDir()); }
        if (r.getModelKind() != null) { args.add("--modelKind"); args.add(r.getModelKind()); }
        if (r.getDatasetName() != null) { args.add("--datasetName"); args.add(r.getDatasetName()); }
        if (r.getGpuIds() != null) { args.add("--gpuIds"); args.add(r.getGpuIds()); }
    }

    private void addPipelineArgs(List<String> args, PipelineRequest r) {
        if (r == null) return;
        if (r.getDataset() != null) { args.add("--dataset"); args.add(r.getDataset()); }
        if (r.getModelCategory() != null) { args.add("--modelCategory"); args.add(r.getModelCategory()); }
        if (r.getModelName() != null) { args.add("--modelName"); args.add(r.getModelName()); }
    }

    private void addDicomArgs(List<String> args, DicomRequest r) {
        if (r == null) return;
        if (r.getDataset() != null) { args.add("--dataset"); args.add(r.getDataset()); }
        if (r.getModelCategory() != null) { args.add("--modelCategory"); args.add(r.getModelCategory()); }
        if (r.getModelName() != null) { args.add("--modelName"); args.add(r.getModelName()); }
    }

    public ResponseEntity<ApiResponse<Map<String, Object>>> invokeMethod1Defaults() {
        try { return ok(runJsonInternal(List.of("--workflow", "method1", "--action", "defaults"))); }
        catch (Exception e) { return fail("method1", "defaults", e); }
    }

    public ResponseEntity<ApiResponse<Map<String, Object>>> invokeMethod1(String action, WorkflowRequest request) {
        try {
            List<String> args = new ArrayList<>(List.of("--workflow", "method1", "--action", action));
            addWorkflowArgs(args, request);
            return ok(runJsonInternal(args));
        } catch (Exception e) { return fail("method1", action, e); }
    }

    public ResponseEntity<ApiResponse<Map<String, Object>>> invokeMethod2Defaults() {
        try { return ok(runJsonInternal(List.of("--workflow", "method2", "--action", "defaults"))); }
        catch (Exception e) { return fail("method2", "defaults", e); }
    }

    public ResponseEntity<ApiResponse<Map<String, Object>>> invokeMethod2(String action, WorkflowRequest request) {
        try {
            List<String> args = new ArrayList<>(List.of("--workflow", "method2", "--action", action));
            addWorkflowArgs(args, request);
            return ok(runJsonInternal(args));
        } catch (Exception e) { return fail("method2", action, e); }
    }

    public ResponseEntity<ApiResponse<Map<String, Object>>> invokeInferenceRun(InferenceRequest request) {
        try {
            List<String> args = new ArrayList<>(List.of("--workflow", "inference", "--action", "run"));
            addInferenceArgs(args, request);
            return ok(runJsonInternal(args));
        } catch (Exception e) { return fail("inference", "run", e); }
    }

    public ResponseEntity<ApiResponse<Map<String, Object>>> invokeInferenceMerge(InferenceRequest request) {
        try {
            List<String> args = new ArrayList<>(List.of("--workflow", "inference", "--action", "merge"));
            addInferenceArgs(args, request);
            return ok(runJsonInternal(args));
        } catch (Exception e) { return fail("inference", "merge", e); }
    }

    public SseEmitter invokeInferenceStream(InferenceRequest request) {
        List<String> args = new ArrayList<>(List.of("--workflow", "inference", "--action", "stream"));
        addInferenceArgs(args, request);
        return stream(args);
    }

    public ResponseEntity<ApiResponse<Map<String, Object>>> invokeDicomDefaults() {
        try { return ok(runJsonInternal(List.of("--workflow", "dicom", "--action", "defaults"))); }
        catch (Exception e) { return fail("dicom", "defaults", e); }
    }

    public ResponseEntity<ApiResponse<Map<String, Object>>> invokeDicomExport(DicomRequest request) {
        try {
            List<String> args = new ArrayList<>(List.of("--workflow", "dicom", "--action", "export"));
            addDicomArgs(args, request);
            return ok(runJsonInternal(args));
        } catch (Exception e) { return fail("dicom", "export", e); }
    }

    public SseEmitter invokePipelineRun(PipelineRequest request) {
        List<String> args = new ArrayList<>(List.of("--workflow", "pipeline", "--action", "run"));
        addPipelineArgs(args, request);
        return stream(args);
    }
}
