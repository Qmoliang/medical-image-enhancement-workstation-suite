from __future__ import annotations

# backend/process_pipeline.py
# ==========================================
# 自动化 CBCT→CT DICOM 生成脚本（路径解耦版）
# ==========================================

import argparse
import glob
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pydicom
from pydicom.uid import generate_uid
from scipy.ndimage import zoom

from config import (
    DICOM_ROOT,
    PARAM_PATH,
    RAW_ROOT,
    RESULTS_BASE,
    TEST_PATIENT_ROOT,
    TMP_DIR,
    UID_PATH,
)

sys.stdout.reconfigure(encoding="utf-8")

MODEL_MAP = {
    "model_cstgan": {
        "cstgan_c": TEST_PATIENT_ROOT / "cyclegan-swin-mask",
        "mb_taylor": TEST_PATIENT_ROOT / "cyclegan-swin",
    },
    "model_attn_vit": {
        "vit-unet": TEST_PATIENT_ROOT / "cyclegan-vit",
        "attn": TEST_PATIENT_ROOT / "cycleattn0220",
    },
    "model_mask": {
        "0106": TEST_PATIENT_ROOT / "cyclegan_mask_HN005_HN023",
    },
}

STATIC_DATASET_MAP = {
    "005_046": ["HN005", "HN007", "HN040", "HN041", "HN042", "HN043", "HN044", "HN046"],
    "048_050": ["HN048", "HN049", "HN050"],
    "046_047": ["HN046", "HN047"],
    "029_031": ["HN029", "HN030", "HN031"],
}


def resolve_patients(dataset_label: str) -> list[str]:
    if dataset_label in STATIC_DATASET_MAP:
        return STATIC_DATASET_MAP[dataset_label]
    if "_" in dataset_label and len(dataset_label.split("_")) == 2:
        a, b = dataset_label.split("_")
        if a.isdigit() and b.isdigit():
            start, end = int(a), int(b)
            if start <= end:
                return [f"HN{n:03d}" for n in range(start, end + 1)]
    parts = [x.strip() for x in dataset_label.split(",") if x.strip()]
    if parts and all(p.isdigit() and len(p) <= 3 for p in parts):
        return [f"HN{int(p):03d}" for p in parts]
    raise ValueError(f"Unknown dataset label: {dataset_label}")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def resolve_original_raw(params: dict) -> Path:
    # New preferred format: relative path under RAW_ROOT
    if "raw_relpath" in params and params["raw_relpath"]:
        return (RAW_ROOT / params["raw_relpath"]).resolve()
    # Backward compatibility with your old JSON
    if "original_raw" in params and params["original_raw"]:
        return Path(params["original_raw"]).expanduser().resolve()
    raise KeyError("missing raw_relpath/original_raw in patient_params.json")


def resolve_original_dicom(params: dict) -> Path:
    # New preferred format: relative path under DICOM_ROOT
    if "dicom_relpath" in params and params["dicom_relpath"]:
        return (DICOM_ROOT / params["dicom_relpath"]).resolve()
    # Backward compatibility with your old JSON
    if "original_dicom" in params and params["original_dicom"]:
        return Path(params["original_dicom"]).expanduser().resolve()
    raise KeyError("missing dicom_relpath/original_dicom in patient_params.json")


def copy_original_raw(patient_id: str, params: dict, model_dir: Path) -> Path | None:
    """Copy original raw into model dir with HNxxx_ prefix, without renaming the source file."""
    src = resolve_original_raw(params)
    if not src.exists():
        print(f" {patient_id}: source raw not found → {src}", flush=True)
        return None

    filename = src.name
    dst_name = filename if filename.startswith(f"{patient_id}_") else f"{patient_id}_{filename}"
    dst = model_dir / dst_name

    if dst.exists():
        print(f" {patient_id}: {dst.name} already exists in model dir, skip copy.", flush=True)
        return dst

    model_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f" {patient_id}: copied original raw → {dst}", flush=True)
    return dst


def insert_processed_cbct(
    processed_path: Path,
    original_path: Path,
    output_path: Path,
    offset_x: int = 0,
    offset_y: int = 0,
) -> None:
    processed = np.fromfile(processed_path, dtype=np.float32).reshape(-1, 256, 256)
    original = np.fromfile(original_path, dtype=np.float32).reshape(-1, 512, 512)
    z_len = min(original.shape[0], processed.shape[0])
    x0, x1 = 128 + offset_x, 384 + offset_x
    y0, y1 = 128 + offset_y, 384 + offset_y
    original[:z_len, x0:x1, y0:y1] = processed[:z_len]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    original.astype(np.float32).tofile(output_path)
    print(f" insert_processed_cbct → {output_path}", flush=True)


def crop_to_512(data: np.ndarray) -> np.ndarray:
    z, h, w = data.shape
    target_h = target_w = 512
    out = np.zeros((z, target_h, target_w), dtype=data.dtype)
    if h >= 512 and w >= 512:
        sh = (h - 512) // 2
        sw = (w - 512) // 2
        out[:] = data[:, sh : sh + 512, sw : sw + 512]
    else:
        sh = max((512 - h) // 2, 0)
        sw = max((512 - w) // 2, 0)
        out[:, sh : sh + h, sw : sw + w] = data
        if h < 512:
            out[:, :sh, :] = out[:, sh : sh + 1, :]
            out[:, sh + h :, :] = out[:, sh + h - 1 : sh + h, :]
        if w < 512:
            out[:, :, :sw] = out[:, :, sw : sw + 1]
            out[:, :, sw + w :] = out[:, :, sw + w - 1 : sw + w]
    return out


def restore_to_original_resolution_with_exact_slices(
    raw_path: Path,
    output_path: Path,
    old_spacing,
    old_thickness,
    new_spacing,
    new_thickness,
    target_slices: int,
) -> None:
    raw = np.fromfile(raw_path, dtype=np.float32).reshape(-1, 512, 512)
    scale_xy = 1.0 / (old_spacing[0] / new_spacing[0])
    scale_z = target_slices / raw.shape[0]
    zoomed = zoom(raw, (scale_z, scale_xy, scale_xy), order=1)
    zoomed = np.clip(zoomed, a_min=-1000, a_max=None)
    zoomed = crop_to_512(zoomed)
    if zoomed.shape[0] > target_slices:
        zoomed = zoomed[:target_slices]
    elif zoomed.shape[0] < target_slices:
        pad = target_slices - zoomed.shape[0]
        zoomed = np.pad(zoomed, ((0, pad), (0, 0), (0, 0)), mode="edge")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    zoomed.astype(np.float32).tofile(output_path)
    print(
        f" restore_to_original_resolution_with_exact_slices → {output_path}  shape={zoomed.shape}",
        flush=True,
    )


def raw_to_dicom_with_float32(raw_path: Path, original_dicom_path: Path, output_folder: Path) -> None:
    output_folder.mkdir(parents=True, exist_ok=True)

    data = np.fromfile(raw_path, dtype=np.float32).reshape(-1, 512, 512)

    dcm_files = sorted(
        [f for f in os.listdir(original_dicom_path) if f.lower().endswith(".dcm")],
        key=lambda x: int(pydicom.dcmread(original_dicom_path / x).InstanceNumber),
    )
    if not dcm_files:
        raise FileNotFoundError(f"No DICOM found in {original_dicom_path}")

    num_slices = data.shape[0]

    for name in dcm_files:
        ds = pydicom.dcmread(original_dicom_path / name)
        instance_number = int(ds.InstanceNumber)

        # 与你旧脚本一致：根据 InstanceNumber 反推 raw 的切片索引
        # 旧逻辑是：slice_index = 105 - instance_number + 1
        # 这里改成与当前体数据 slice 数自适应一致
        slice_index = num_slices - instance_number

        if slice_index < 0:
            slice_index = 0
        elif slice_index >= num_slices:
            slice_index = num_slices - 1

        float32_slice = data[slice_index]

        ri = float(ds.get("RescaleIntercept", -1000.0))
        rs = float(ds.get("RescaleSlope", 1.0))
        if rs == 0:
            rs = 1.0

        stored_slice = np.round((float32_slice - ri) / rs)

        # 跟原始 DICOM 的像素表示保持一致
        pixel_repr = int(ds.get("PixelRepresentation", 1))
        if pixel_repr == 0:
            pixel_array = stored_slice.astype(np.uint16)
        else:
            pixel_array = stored_slice.astype(np.int16)

        ds.PixelData = pixel_array.tobytes()
        ds.Rows, ds.Columns = pixel_array.shape

        # 像素字段与写入数据保持一致
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"

        # 尽量沿用原始 DICOM 的位深；没有就按 16 位兜底
        ds.BitsAllocated = int(ds.get("BitsAllocated", 16))
        ds.BitsStored = int(ds.get("BitsStored", 16))
        ds.HighBit = int(ds.get("HighBit", ds.BitsStored - 1))
        ds.PixelRepresentation = pixel_repr

        # 写成更标准的 DICOM，避免后续读回来时报 DICM/file meta 问题
        ds.save_as(output_folder / name, write_like_original=False)

    print(f" raw_to_dicom_with_float32 → {output_folder}", flush=True)


def increment_uid(uid: str, step: int = 1) -> str:
    parts = uid.split(".")
    try:
        last = int(parts[-1])
        parts[-1] = str(last + step)
    except ValueError:
        parts.append(str(step))
    return ".".join(parts)


def uid_last_number(uid: str) -> int | None:
    try:
        return int(uid.split(".")[-1])
    except Exception:
        return None


def collect_existing_uid_suffixes(uid_registry: dict) -> set[int]:
    suffixes: set[int] = set()
    for _, pdata in uid_registry.items():
        if not isinstance(pdata, dict):
            continue
        orig = pdata.get("original", {})
        for k in ("StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID"):
            val = orig.get(k)
            if isinstance(val, str):
                n = uid_last_number(val)
                if n is not None:
                    suffixes.add(n)
        gen = pdata.get("generated", {})
        if isinstance(gen, dict):
            for _, rec in gen.items():
                if not isinstance(rec, dict):
                    continue
                for k in ("StudyInstanceUID", "SeriesInstanceUID", "BaseSOPInstanceUID"):
                    val = rec.get(k)
                    if isinstance(val, str):
                        n = uid_last_number(val)
                        if n is not None:
                            suffixes.add(n)
    return suffixes


def generate_unique_uid_not_in(uid_registry: dict) -> str:
    existing: set[str] = set()
    for _, pdata in uid_registry.items():
        if not isinstance(pdata, dict):
            continue
        orig = pdata.get("original", {})
        for k in ("StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID"):
            v = orig.get(k)
            if isinstance(v, str):
                existing.add(v)
        gen = pdata.get("generated", {})
        if isinstance(gen, dict):
            for _, rec in gen.items():
                if not isinstance(rec, dict):
                    continue
                for k in ("StudyInstanceUID", "SeriesInstanceUID", "BaseSOPInstanceUID"):
                    v = rec.get(k)
                    if isinstance(v, str):
                        existing.add(v)
    while True:
        candidate = generate_uid()
        if candidate not in existing:
            return candidate


def generate_nonconflicting_base_sop_uid(uid_registry: dict, margin: int = 107) -> str:
    suffixes = collect_existing_uid_suffixes(uid_registry)
    while True:
        candidate = generate_uid()
        n = uid_last_number(candidate)
        if n is None:
            continue
        if all(abs(n - s) > margin for s in suffixes):
            return candidate


def update_dicom_uids_safe(
    dicom_folder: Path,
    output_folder: Path,
    patient_id: str,
    model_name: str,
    uid_registry: dict,
) -> None:
    output_folder.mkdir(parents=True, exist_ok=True)
    files = sorted(
        [f for f in os.listdir(dicom_folder) if f.lower().endswith(".dcm")],
        key=lambda x: int(pydicom.dcmread(dicom_folder / x).InstanceNumber),
    )
    if not files:
        raise FileNotFoundError("No DICOM files found.")
    first_ds = pydicom.dcmread(dicom_folder / files[0])
    uid_registry.setdefault(patient_id, {})
    if "original" not in uid_registry[patient_id]:
        uid_registry[patient_id]["original"] = {
            "StudyInstanceUID": str(first_ds.get("StudyInstanceUID", "")),
            "SeriesInstanceUID": str(first_ds.get("SeriesInstanceUID", "")),
            "SOPInstanceUID": str(first_ds.get("SOPInstanceUID", "")),
        }
    uid_registry[patient_id].setdefault("generated", {})
    if model_name not in uid_registry[patient_id]["generated"]:
        study_uid = generate_unique_uid_not_in(uid_registry)
        series_uid = generate_unique_uid_not_in(uid_registry)
        base_sop_uid = generate_nonconflicting_base_sop_uid(uid_registry, margin=107)
        uid_registry[patient_id]["generated"][model_name] = {
            "StudyInstanceUID": study_uid,
            "SeriesInstanceUID": series_uid,
            "BaseSOPInstanceUID": base_sop_uid,
        }
    uids = uid_registry[patient_id]["generated"][model_name]
    base_sop_uid = uids["BaseSOPInstanceUID"]
    for i, name in enumerate(files):
        ds = pydicom.dcmread(dicom_folder / name, force=True)
        ds.StudyInstanceUID = uids["StudyInstanceUID"]
        ds.SeriesInstanceUID = uids["SeriesInstanceUID"]
        ds.SOPInstanceUID = increment_uid(base_sop_uid, i)
        ds.save_as(output_folder / name)
    print(f" update_dicom_uids_safe: {patient_id} / {model_name} → {output_folder}", flush=True)


def run_pipeline(dataset_label: str, model_category: str, model_name: str) -> None:
    try:
        patients = resolve_patients(dataset_label)
    except Exception as e:
        print(f" invalid dataset: {e}", flush=True)
        return

    if model_category not in MODEL_MAP or model_name not in MODEL_MAP[model_category]:
        print(f" invalid model: {model_category}/{model_name}", flush=True)
        return

    model_dir: Path = MODEL_MAP[model_category][model_name]
    model_dir.mkdir(parents=True, exist_ok=True)
    params_all = load_json(PARAM_PATH)
    uid_registry = load_json(UID_PATH)
    results_dir = RESULTS_BASE / model_name
    results_dir.mkdir(parents=True, exist_ok=True)

    for pid in patients:
        params = params_all.get(pid)
        if not params:
            print(f" {pid}: missing params in patient_params.json, skip.", flush=True)
            continue

        try:
            original_raw = resolve_original_raw(params)
            original_dicom = resolve_original_dicom(params)
        except Exception as e:
            print(f" {pid}: path resolve failed → {e}", flush=True)
            continue

        print(f"\n========== Processing {pid} ==========", flush=True)
        print(f"original_raw: {original_raw}", flush=True)
        print(f"original_dicom: {original_dicom}", flush=True)
        print(f"model_dir: {model_dir}", flush=True)

        dst = copy_original_raw(pid, params, model_dir)
        if dst is None:
            print(f" {pid}: copy original_raw failed, skip pipeline.", flush=True)
            continue

        pattern = str(model_dir / f"{pid}_CBCT_*_3d_fake_B.raw")
        fake_candidates = sorted(glob.glob(pattern))
        if not fake_candidates:
            print(f" {pid}: fake_B not found in model_dir with pattern: {pattern}", flush=True)
            continue

        processed_path = Path(fake_candidates[0])
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        inter = TMP_DIR / f"interpolated_CBCT_b_spline_centered_updated_{pid}.raw"
        rest = TMP_DIR / f"restored_CBCT_{pid}.raw"

        insert_processed_cbct(
            processed_path,
            dst,
            inter,
            params.get("offset_x", 0),
            params.get("offset_y", 0),
        )
        restore_to_original_resolution_with_exact_slices(
            inter,
            rest,
            params["old_spacing"],
            params["old_thickness"],
            params["new_spacing"],
            params["new_thickness"],
            params["target_slices"],
        )

        dicom_folder = TMP_DIR / f"new_CBCT_DICOM_{pid}"
        raw_to_dicom_with_float32(rest, original_dicom, dicom_folder)

        out_folder = results_dir / f"updated_CBCT_DICOM_{pid}"
        update_dicom_uids_safe(dicom_folder, out_folder, pid, model_name, uid_registry)

        shutil.rmtree(dicom_folder, ignore_errors=True)
        if inter.exists():
            inter.unlink(missing_ok=True)
        if rest.exists():
            rest.unlink(missing_ok=True)
        print(f" cleared tmp artifacts for {pid}", flush=True)

    save_json(uid_registry, UID_PATH)
    print("\n All done.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run CBCT→CT pipeline (path-decoupled)")
    parser.add_argument("--dataset", required=True, help="e.g. 029_031 / 005_046 / 04850 / 04647 / or 029,031")
    parser.add_argument("--modelCategory", required=True, help="e.g. model_cstgan / model_attn_vit / model_mask")
    parser.add_argument("--modelName", required=True, help="e.g. mb_taylor / cstgan_c / vit-unet / attn / 0106")
    args = parser.parse_args()
    run_pipeline(args.dataset, args.modelCategory, args.modelName)
