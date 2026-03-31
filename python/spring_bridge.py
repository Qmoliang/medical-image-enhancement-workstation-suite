from __future__ import annotations

import argparse
import json
import subprocess
import sys
import traceback

sys.stdout.reconfigure(encoding="utf-8")


def ok(data):
    return {"ok": True, "message": "ok", "data": data}


def fail(message, data=None):
    return {"ok": False, "message": message, "data": data or {}}


def payload_from_args(args):
    return {
        "sourceRoot": args.sourceRoot,
        "workspaceRoot": args.workspaceRoot,
        "patientFolder": args.patientFolder,
        "cbctName": args.cbctName,
        "qactName": args.qactName,
        "matchText": args.matchText,
        "roiName": args.roiName,
    }


def run_method1(action, args):
    from pathlib import Path
    from method1_workflow import (
        DEFAULT_SOURCE_ROOT, DEFAULT_WORKSPACE_ROOT, _selection_from_payload,
        generate_matches, list_roi_options, run_step1, run_step2,
        run_step3, run_step4, run_step5, run_step6
    )

    if action == "defaults":
        return {"sourceRoot": str(DEFAULT_SOURCE_ROOT), "workspaceRoot": str(DEFAULT_WORKSPACE_ROOT)}

    data = payload_from_args(args)
    source_root = Path(args.sourceRoot or DEFAULT_SOURCE_ROOT)
    workspace_root = Path(args.workspaceRoot or DEFAULT_WORKSPACE_ROOT)

    if action == "run_match":
        if not source_root.exists():
            return {"ok": False, "error": f"sourceRoot 不存在: {source_root}"}
        if not source_root.is_dir():
            return {"ok": False, "error": f"sourceRoot 不是文件夹: {source_root}"}
        matches, txt_path = generate_matches(source_root, workspace_root)
        return {
            "ok": True,
            "sourceRoot": str(source_root),
            "workspaceRoot": str(workspace_root),
            "matchedTxt": str(txt_path),
            "matches": matches,
            "message": f"Run Match 完成，共找到 {len(matches)} 个病人分组",
        }

    selection = _selection_from_payload(data)

    if action == "roi_options":
        return {"ok": True, "roiOptions": list_roi_options(source_root, selection)}
    if action == "step1":
        return run_step1(source_root, workspace_root, selection)
    if action == "step2":
        return run_step2(source_root, workspace_root, selection, str(args.roiName or "").strip())
    if action == "step3":
        return run_step3(source_root, workspace_root, selection)
    if action == "step4":
        return run_step4(
            source_root,
            workspace_root,
            selection,
            int(args.shift or 108),
            int(args.cbctYExtra or 44),
            int(args.ctYShift or 50),
            str(args.applyCtMask).lower() == "true",
        )
    if action == "step5":
        return run_step5(
            source_root,
            workspace_root,
            selection,
            int(args.shift or 108),
            int(args.cbctYExtra or 44),
            args.processedRawPath,
        )
    if action == "step6":
        return run_step6(
            source_root,
            workspace_root,
            selection,
            int(args.shift or 108),
            int(args.cbctYExtra or 44),
            str(args.modelName or "mb_taylor"),
        )

    raise ValueError(f"Unsupported method1 action: {action}")


def run_method2(action, args):
    from pathlib import Path
    from method1_workflow import _selection_from_payload, generate_matches, list_roi_options
    from method2_workflow import (
        DEFAULT_SOURCE_ROOT, DEFAULT_WORKSPACE_ROOT,
        run_step1, run_step2, run_step3, run_step4, run_step5, run_step6
    )

    if action == "defaults":
        return {"sourceRoot": str(DEFAULT_SOURCE_ROOT), "workspaceRoot": str(DEFAULT_WORKSPACE_ROOT)}

    data = payload_from_args(args)
    source_root = Path(args.sourceRoot or DEFAULT_SOURCE_ROOT)
    workspace_root = Path(args.workspaceRoot or DEFAULT_WORKSPACE_ROOT)

    if action == "run_match":
        if not source_root.exists():
            return {"ok": False, "error": f"sourceRoot 不存在: {source_root}"}
        if not source_root.is_dir():
            return {"ok": False, "error": f"sourceRoot 不是文件夹: {source_root}"}
        matches, txt_path = generate_matches(source_root, workspace_root)
        return {
            "ok": True,
            "sourceRoot": str(source_root),
            "workspaceRoot": str(workspace_root),
            "matchedTxt": str(txt_path),
            "matches": matches,
            "message": f"Run Match 完成，共找到 {len(matches)} 个病人分组",
        }

    selection = _selection_from_payload(data)

    if action == "roi_options":
        return {"ok": True, "roiOptions": list_roi_options(source_root, selection)}
    if action == "step1":
        return run_step1(source_root, workspace_root, selection)
    if action == "step2":
        return run_step2(source_root, workspace_root, selection, str(args.roiName or "").strip())
    if action == "step3":
        return run_step3(source_root, workspace_root, selection)
    if action == "step4":
        return run_step4(source_root, workspace_root, selection)
    if action == "step5":
        return run_step5(source_root, workspace_root, selection, str(args.processedRawPath or "").strip() or None)
    if action == "step6":
        return run_step6(source_root, workspace_root, selection, str(args.modelName or "mb_taylor").strip() or "mb_taylor")

    raise ValueError(f"Unsupported method2 action: {action}")


def run_inference_json(action, args):
    from config import EXTRACT_MERGE_SCRIPT, MODEL_PROJECT_ROOT, PIPELINE_PATH
    from inference_core import run_inference_once

    if action == "run":
        return run_inference_once(
            model_dir=args.modelDir,
            model_kind=args.modelKind,
            dataset_name=args.datasetName,
            gpu_ids=args.gpuIds or "0",
        )

    if action == "merge":
        cmd = [
            sys.executable,
            str(EXTRACT_MERGE_SCRIPT),
            args.modelDir,
            args.modelKind,
            args.datasetName,
        ]
        proc = subprocess.run(
            cmd,
            cwd=MODEL_PROJECT_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="ignore",
        )
        return {"cmd": " ".join(cmd), "stdout": proc.stdout, "returncode": proc.returncode}

    raise ValueError(f"Unsupported inference action: {action}")


def stream_inference(args):
    from inference_core import stream_inference_run

    stream_inference_run(
        model_dir=args.modelDir,
        model_kind=args.modelKind,
        dataset_name=args.datasetName,
        gpu_ids=args.gpuIds or "0",
    )


def run_dicom_json(args):
    from config import PIPELINE_PATH, SPRING_PROJECT_ROOT

    cmd = [
        sys.executable,
        str(PIPELINE_PATH),
        "--dataset", args.dataset,
        "--modelCategory", args.modelCategory,
        "--modelName", args.modelName,
    ]
    proc = subprocess.run(
        cmd,
        cwd=SPRING_PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="ignore",
    )
    return {"cmd": " ".join(cmd), "stdout": proc.stdout, "returncode": proc.returncode}


def stream_pipeline(args):
    from config import PIPELINE_PATH, SPRING_PROJECT_ROOT

    cmd = [
        sys.executable,
        str(PIPELINE_PATH),
        "--dataset", args.dataset,
        "--modelCategory", args.modelCategory,
        "--modelName", args.modelName,
    ]

    process = subprocess.Popen(
        cmd,
        cwd=SPRING_PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    try:
        for line in iter(process.stdout.readline, ""):
            if not line:
                break
            print(line.rstrip(), flush=True)
    finally:
        if process.stdout:
            process.stdout.close()
        process.wait()
        print("✅ Pipeline finished successfully.", flush=True)
        print("__DONE__", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True, choices=["method1", "method2", "inference", "dicom", "pipeline"])
    parser.add_argument("--action", required=True)

    parser.add_argument("--sourceRoot")
    parser.add_argument("--workspaceRoot")
    parser.add_argument("--patientFolder")
    parser.add_argument("--cbctName")
    parser.add_argument("--qactName")
    parser.add_argument("--matchText")
    parser.add_argument("--roiName")
    parser.add_argument("--shift", type=int)
    parser.add_argument("--cbctYExtra", type=int)
    parser.add_argument("--ctYShift", type=int)
    parser.add_argument("--applyCtMask")
    parser.add_argument("--processedRawPath")
    parser.add_argument("--modelName")
    parser.add_argument("--offsetX", type=int)
    parser.add_argument("--offsetY", type=int)

    parser.add_argument("--modelDir")
    parser.add_argument("--modelKind")
    parser.add_argument("--datasetName")
    parser.add_argument("--gpuIds")

    parser.add_argument("--dataset")
    parser.add_argument("--modelCategory")

    args = parser.parse_args()

    try:
        if args.workflow == "method1":
            print(json.dumps(ok(run_method1(args.action, args)), ensure_ascii=False))
            return

        if args.workflow == "method2":
            print(json.dumps(ok(run_method2(args.action, args)), ensure_ascii=False))
            return

        if args.workflow == "inference":
            if args.action == "stream":
                stream_inference(args)
                return
            print(json.dumps(ok(run_inference_json(args.action, args)), ensure_ascii=False))
            return

        if args.workflow == "dicom":
            if args.action == "defaults":
                print(json.dumps(ok({"dataset": "", "modelCategory": "", "modelName": ""}), ensure_ascii=False))
                return
            if args.action == "export":
                print(json.dumps(ok(run_dicom_json(args)), ensure_ascii=False))
                return
            raise ValueError(f"Unsupported dicom action: {args.action}")

        if args.workflow == "pipeline":
            if args.action != "run":
                raise ValueError(f"Unsupported pipeline action: {args.action}")
            stream_pipeline(args)
            return

        raise ValueError(f"Unsupported workflow: {args.workflow}")

    except Exception as e:
        print(
            json.dumps(
                fail(f"{type(e).__name__}: {e}", {"traceback": traceback.format_exc()}),
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()