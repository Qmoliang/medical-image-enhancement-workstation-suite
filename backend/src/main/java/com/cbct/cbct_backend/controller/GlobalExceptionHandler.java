package com.cbct.cbct_backend.controller;

import com.cbct.cbct_backend.dto.ApiResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.LinkedHashMap;
import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Map<String, Object>>> handle(Exception ex) {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("trace", ex.getClass().getName());
        return ResponseEntity.ok(ApiResponse.error(ex.getClass().getSimpleName() + ": " + ex.getMessage(), data));
    }
}
