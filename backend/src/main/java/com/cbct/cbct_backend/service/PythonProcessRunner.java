package com.cbct.cbct_backend.service;

import com.cbct.cbct_backend.config.PythonProperties;
import com.cbct.cbct_backend.dto.ProcessResult;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

@Service
public class PythonProcessRunner {

    private final PythonProperties pythonProperties;

    public PythonProcessRunner(PythonProperties pythonProperties) {
        this.pythonProperties = pythonProperties;
    }

    public ProcessResult runInlineCode(String code) throws Exception {
        List<String> command = new ArrayList<>();
        command.add(pythonProperties.getExecutable());
        command.add("-c");
        command.add(code);
        return runCommand(command, pythonProperties.getWorkingDirectory());
    }

    public ProcessResult runScript(String scriptPath, List<String> args, String workingDirectory) throws Exception {
        List<String> command = new ArrayList<>();
        command.add(pythonProperties.getExecutable());
        command.add(scriptPath);
        if (args != null) {
            command.addAll(args);
        }
        String wd = (workingDirectory == null || workingDirectory.isBlank())
                ? pythonProperties.getWorkingDirectory() : workingDirectory;
        return runCommand(command, wd);
    }

    private ProcessResult runCommand(List<String> command, String workingDirectory) throws Exception {
        ProcessBuilder pb = new ProcessBuilder(command);
        if (workingDirectory != null && !workingDirectory.isBlank()) {
            pb.directory(new File(workingDirectory));
        }
        pb.redirectErrorStream(true);
        Process process = pb.start();
        StringBuilder sb = new StringBuilder();
        try (BufferedReader br = new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = br.readLine()) != null) {
                sb.append(line).append("\n");
            }
        }
        int exitCode = process.waitFor();
        return new ProcessResult(exitCode, command, workingDirectory, sb.toString());
    }
}
