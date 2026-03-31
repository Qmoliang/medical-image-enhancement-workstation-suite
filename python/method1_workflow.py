
from __future__ import annotations

import base64
import io
import json
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pydicom
from PIL import Image
from scipy import ndimage

DEFAULT_SOURCE_ROOT = Path(r"F:\mimi0209\HeadNeck-selected")
DEFAULT_WORKSPACE_ROOT = Path(r"F:\mimi0209\output-test")


@dataclass
class Method1Selection:
    patient_folder: str
    cbct_name: str
    qact_name: str
    match_text: str


def _safe_mkdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _selection_from_payload(data: dict[str, Any]) -> Method1Selection:
    patient_folder = str(data.get("patientFolder") or "").strip()
    cbct_name = str(data.get("cbctName") or "").strip()
    qact_name = str(data.get("qactName") or "").strip()
    match_text = str(data.get("matchText") or "").strip()

    if not patient_folder:
        raise ValueError("patientFolder 不能为空")
    if not cbct_name or not qact_name:
        if " matched with " in match_text:
            cbct_name, qact_name = [x.strip() for x in match_text.split(" matched with ", 1)]
        else:
            raise ValueError("cbctName / qactName 缺失，且无法从 matchText 解析")
    if not match_text:
        match_text = f"{cbct_name} matched with {qact_name}"

    return Method1Selection(
        patient_folder=patient_folder,
        cbct_name=cbct_name,
        qact_name=qact_name,
        match_text=match_text,
    )


def _series_folders(patient_dir: Path) -> tuple[list[Path], list[Path]]:
    cbcts, qacts = [], []
    for p in sorted([x for x in patient_dir.iterdir() if x.is_dir()]):
        name = p.name.upper()
        if name.startswith("CBCT_"):
            cbcts.append(p)
        elif name.startswith("QACT_"):
            qacts.append(p)
    return cbcts, qacts


def _series_date(name: str) -> str | None:
    # CBCT_20000121-1035 -> 20000121
    if "_" not in name:
        return None
    rest = name.split("_", 1)[1]
    if "-" not in rest:
        return None
    return rest.split("-", 1)[0]


def generate_matches(source_root: Path, workspace_root: Path) -> tuple[list[dict[str, Any]], Path]:
    source_root = Path(source_root)
    workspace_root = Path(workspace_root)
    if not source_root.exists():
        raise FileNotFoundError(f"sourceRoot 不存在: {source_root}")
    if not source_root.is_dir():
        raise NotADirectoryError(f"sourceRoot 不是文件夹: {source_root}")

    _safe_mkdir(workspace_root)
    txt_path = workspace_root / "matched_folders.txt"

    results: list[dict[str, Any]] = []
    lines: list[str] = []

    for patient_dir in sorted([p for p in source_root.iterdir() if p.is_dir()]):
        cbcts, qacts = _series_folders(patient_dir)
        by_date_q = {}
        for q in qacts:
            d = _series_date(q.name)
            if d:
                by_date_q.setdefault(d, []).append(q)

        matches = []
        for c in cbcts:
            d = _series_date(c.name)
            if not d:
                continue
            for q in by_date_q.get(d, []):
                match_text = f"{c.name} matched with {q.name}"
                matches.append(
                    {
                        "cbctName": c.name,
                        "qactName": q.name,
                        "matchText": match_text,
                    }
                )

        if matches:
            lines.append(f"Patient folder: {patient_dir.name}")
            for m in matches:
                lines.append(m["matchText"])
            lines.append("")
            results.append(
                {
                    "patientFolder": patient_dir.name,
                    "matches": matches,
                }
            )

    txt_path.write_text("\n".join(lines), encoding="utf-8")
    return results, txt_path


def _ct_dcm_files(series_dir: Path) -> list[Path]:
    files = [p for p in series_dir.iterdir() if p.is_file() and p.suffix.lower() == ".dcm" and p.name.upper().startswith("CT")]
    def inst_num(p: Path) -> int:
        try:
            ds = pydicom.dcmread(str(p), stop_before_pixels=True)
            return int(getattr(ds, "InstanceNumber", 0))
        except Exception:
            return 0
    return sorted(files, key=inst_num)


def _read_series_raw(series_dir: Path, intercept_override: float | None = None, reverse_z: bool = False) -> tuple[np.ndarray, dict[str, Any]]:
    dcm_files = _ct_dcm_files(series_dir)
    if not dcm_files:
        raise FileNotFoundError(f"未找到 CT*.dcm: {series_dir}")

    first = pydicom.dcmread(str(dcm_files[0]))
    rows, cols = int(first.Rows), int(first.Columns)
    arr = np.zeros((len(dcm_files), rows, cols), dtype=np.float32)

    sop_to_index = {}
    for i, p in enumerate(dcm_files):
        ds = pydicom.dcmread(str(p))
        px = ds.pixel_array.astype(np.float32)
        px[px == -2000] = 0
        intercept = float(getattr(ds, "RescaleIntercept", 0.0))
        slope = float(getattr(ds, "RescaleSlope", 1.0))
        if intercept_override is not None:
            intercept = intercept_override
            slope = 1.0
        if slope != 1:
            px = (px * slope).astype(np.float32)
        px = px + np.float32(intercept)
        arr[i] = px
        sop_to_index[str(ds.SOPInstanceUID)] = i

    if reverse_z:
        arr = arr[::-1]
        sop_to_index = {k: len(dcm_files) - 1 - v for k, v in sop_to_index.items()}

    meta = {
        "rows": rows,
        "cols": cols,
        "pixel_spacing": [float(x) for x in getattr(first, "PixelSpacing", [1.0, 1.0])],
        "slice_thickness": float(getattr(first, "SliceThickness", 1.0)),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "sop_to_index": sop_to_index,
        "image_position_patient": [float(x) for x in getattr(first, "ImagePositionPatient", [0.0, 0.0, 0.0])],
    }
    return arr, meta


def _resize_slices_to_512(data: np.ndarray) -> np.ndarray:
    n_slices, height, width = data.shape
    target_h, target_w = 512, 512
    out = np.full((n_slices, target_h, target_w), -1000, dtype=data.dtype)

    for i in range(n_slices):
        s = data[i]
        if height <= target_h and width <= target_w:
            start_y = (target_h - height) // 2
            start_x = (target_w - width) // 2
            out[i, start_y:start_y + height, start_x:start_x + width] = s
        else:
            sy = max((height - target_h) // 2, 0)
            sx = max((width - target_w) // 2, 0)
            crop = s[sy:sy + target_h, sx:sx + target_w]
            out[i, :crop.shape[0], :crop.shape[1]] = crop
    return out


def run_step1(source_root: Path, workspace_root: Path, selection: Method1Selection) -> dict[str, Any]:
    source_root = Path(source_root)
    workspace_root = Path(workspace_root)
    patient_dir = source_root / selection.patient_folder
    cbct_dir = patient_dir / selection.cbct_name
    qact_dir = patient_dir / selection.qact_name

    cbct_out_dir = _safe_mkdir(workspace_root / selection.patient_folder / selection.cbct_name)
    qact_out_dir = _safe_mkdir(workspace_root / selection.patient_folder / selection.qact_name)

    cbct_raw, cbct_meta = _read_series_raw(cbct_dir, intercept_override=-1000.0, reverse_z=True)
    qact_raw, qact_meta = _read_series_raw(qact_dir, intercept_override=-1024.0, reverse_z=False)

    cbct_raw_path = cbct_out_dir / f"{selection.cbct_name}.raw"
    qact_raw_path = qact_out_dir / f"{selection.qact_name}.raw"
    cbct_raw.astype(np.float32).tofile(cbct_raw_path)
    qact_raw.astype(np.float32).tofile(qact_raw_path)

    old_slice = float(cbct_meta["slice_thickness"])
    old_ps = [float(x) for x in cbct_meta["pixel_spacing"]]
    new_slice = float(qact_meta["slice_thickness"])
    new_ps = [float(x) for x in qact_meta["pixel_spacing"]]

    scale_z = old_slice / new_slice
    scale_xy = old_ps[0] / new_ps[0]
    resampled = ndimage.zoom(cbct_raw, (scale_z, scale_xy, scale_xy), order=3)
    resampled = np.clip(resampled, cbct_meta["min"], cbct_meta["max"])
    interpolated = _resize_slices_to_512(resampled)
    interpolated = np.clip(interpolated, cbct_meta["min"], cbct_meta["max"]).astype(np.float32)

    interp_path = cbct_out_dir / "interpolated_CBCT_b_spline.raw"
    interpolated.tofile(interp_path)

    step1_info = {
        "patientFolder": selection.patient_folder,
        "cbctName": selection.cbct_name,
        "qactName": selection.qact_name,
        "cbctRawPath": str(cbct_raw_path),
        "qactRawPath": str(qact_raw_path),
        "interpolatedPath": str(interp_path),
        "oldPixelSpacing": old_ps,
        "oldSliceThickness": old_slice,
        "newPixelSpacing": new_ps,
        "newSliceThickness": new_slice,
        "scaleZ": float(scale_z),
        "scaleXY": float(scale_xy),
        "cbctMinMax": [float(cbct_raw.min()), float(cbct_raw.max())],
        "qactMinMax": [float(qact_raw.min()), float(qact_raw.max())],
    }

    info_path = _safe_mkdir(workspace_root / selection.patient_folder / "_method1_meta") / "step1_info.json"
    info_path.write_text(json.dumps(step1_info, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "summary": {
            "cbctRaw": str(cbct_raw_path),
            "qactRaw": str(qact_raw_path),
            "interpolatedCbct": str(interp_path),
            "pixelSpacing": {"cbct": old_ps, "qact": new_ps},
            "sliceThickness": {"cbct": old_slice, "qact": new_slice},
            "scale": {"z": float(scale_z), "xy": float(scale_xy)},
        },
        "generatedFiles": [
            str(cbct_raw_path),
            str(qact_raw_path),
            str(interp_path),
            str(info_path),
        ],
        "savedLocations": {
            "cbctDir": str(cbct_out_dir),
            "qactDir": str(qact_out_dir),
            "metaDir": str(info_path.parent),
        },
        "message": "Step 1 完成：已生成 CBCT/QACT raw 与 interpolated_CBCT_b_spline.raw",
    }


def list_roi_options(source_root: Path, selection: Method1Selection) -> list[str]:
    source_root = Path(source_root)
    qact_dir = source_root / selection.patient_folder / selection.qact_name
    rs_file = next((p for p in qact_dir.iterdir() if p.is_file() and p.name.upper().startswith("RS") and p.suffix.lower() == ".dcm"), None)
    if rs_file is None:
        raise FileNotFoundError(f"未找到 RS*.dcm: {qact_dir}")
    ds = pydicom.dcmread(str(rs_file))
    roi_names = [str(roi.ROIName) for roi in ds.StructureSetROISequence]
    return sorted(roi_names)


def _find_rs_file(qact_dir: Path) -> Path:
    rs_file = next((p for p in qact_dir.iterdir() if p.is_file() and p.name.upper().startswith("RS") and p.suffix.lower() == ".dcm"), None)
    if rs_file is None:
        raise FileNotFoundError(f"未找到 RS*.dcm: {qact_dir}")
    return rs_file


def _map_points_to_pixels(points_xyz: np.ndarray, image_position_patient: list[float], pixel_spacing: list[float]) -> np.ndarray:
    xs = np.round((points_xyz[:, 0] - image_position_patient[0]) / pixel_spacing[0]).astype(np.int32)
    ys = np.round((points_xyz[:, 1] - image_position_patient[1]) / pixel_spacing[1]).astype(np.int32)
    return np.stack([xs, ys], axis=1)


def _build_roi_mask_stack(qact_dir: Path, roi_name: str) -> np.ndarray:
    rs_file = _find_rs_file(qact_dir)
    rs_dataset = pydicom.dcmread(str(rs_file))
    ct_files = _ct_dcm_files(qact_dir)
    if not ct_files:
        raise FileNotFoundError(f"未找到 CT*.dcm: {qact_dir}")

    first_ct = pydicom.dcmread(str(ct_files[0]), stop_before_pixels=True)
    rows, cols = int(first_ct.Rows), int(first_ct.Columns)
    pixel_spacing = [float(x) for x in first_ct.PixelSpacing]
    image_position_patient = [float(x) for x in first_ct.ImagePositionPatient]

    sop_to_index: dict[str, int] = {}
    for idx, p in enumerate(ct_files):
        ds = pydicom.dcmread(str(p), stop_before_pixels=True)
        sop_to_index[str(ds.SOPInstanceUID)] = idx

    roi_number = None
    for roi in rs_dataset.StructureSetROISequence:
        if str(roi.ROIName) == roi_name:
            roi_number = int(roi.ROINumber)
            break
    if roi_number is None:
        raise ValueError(f"ROI '{roi_name}' 不存在")

    contours = []
    for contour in rs_dataset.ROIContourSequence:
        if int(contour.ReferencedROINumber) == roi_number:
            contours = list(contour.ContourSequence)
            break

    mask_stack = np.zeros((len(ct_files), rows, cols), dtype=np.float32)
    if not contours:
        return mask_stack

    for contour in contours:
        sop_uid = str(contour.ContourImageSequence[0].ReferencedSOPInstanceUID)
        if sop_uid not in sop_to_index:
            continue
        slice_idx = sop_to_index[sop_uid]
        contour_xyz = np.array(contour.ContourData, dtype=np.float32).reshape(-1, 3)
        pts = _map_points_to_pixels(contour_xyz, image_position_patient, pixel_spacing)
        pts[:, 0] = np.clip(pts[:, 0], 0, cols - 1)
        pts[:, 1] = np.clip(pts[:, 1], 0, rows - 1)
        poly = pts.reshape((-1, 1, 2)).astype(np.int32)
        cv2.fillPoly(mask_stack[slice_idx], [poly], 1.0)

    return mask_stack.astype(np.float32)


def run_step2(source_root: Path, workspace_root: Path, selection: Method1Selection, roi_name: str) -> dict[str, Any]:
    source_root = Path(source_root)
    workspace_root = Path(workspace_root)
    qact_dir = source_root / selection.patient_folder / selection.qact_name
    temp_dir = _safe_mkdir(workspace_root / selection.patient_folder / "_method1_temp")

    roi_options = list_roi_options(source_root, selection)
    if roi_name not in roi_options:
        raise ValueError(f"ROI '{roi_name}' 不在可用列表中")

    roi_mask = _build_roi_mask_stack(qact_dir, roi_name)
    patient_mask = _build_roi_mask_stack(qact_dir, "Patient") if "Patient" in roi_options else np.zeros_like(roi_mask)

    roi_mask_path = temp_dir / "output_processed.raw"
    patient_mask_path = temp_dir / "output_processed_Patient.raw"
    roi_mask.tofile(roi_mask_path)
    patient_mask.tofile(patient_mask_path)

    return {
        "ok": True,
        "summary": {
            "selectedRoi": roi_name,
            "alsoGenerated": "Patient" if "Patient" in roi_options else None,
            "tempDir": str(temp_dir),
        },
        "generatedFiles": [
            str(roi_mask_path),
            str(patient_mask_path),
        ],
        "savedLocations": {
            "tempDir": str(temp_dir),
        },
        "message": "Step 2 完成：已生成所选 ROI 与 Patient 的中间 mask 文件（后续病人可能覆盖）",
    }


def _norm_uint8(img: np.ndarray) -> np.ndarray:
    img = img.astype(np.float32)
    mn, mx = float(img.min()), float(img.max())
    if mx <= mn:
        return np.zeros_like(img, dtype=np.uint8)
    return ((img - mn) / (mx - mn) * 255.0).clip(0, 255).astype(np.uint8)


def _best_orb_shift(cbct: np.ndarray, ct: np.ndarray, n_slices: int = 80) -> tuple[int, int]:
    orb = cv2.ORB_create()
    ct_uint8 = [_norm_uint8(s) for s in ct]
    diffs = []
    start_idx = 0
    total = len(ct_uint8)

    max_n = min(n_slices, len(cbct))
    for n in range(max_n):
        cb = _norm_uint8(cbct[n])
        kp1, des1 = orb.detectAndCompute(cb, None)
        if des1 is None or len(kp1) < 5:
            continue
        best_idx = None
        best_score = float("inf")
        for idx in range(start_idx, total):
            kp2, des2 = orb.detectAndCompute(ct_uint8[idx], None)
            if des2 is None or len(kp2) < 5:
                continue
            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)
            if not matches:
                continue
            score = sum(m.distance for m in matches) / len(matches)
            if score < best_score:
                best_score = score
                best_idx = idx
        if best_idx is not None:
            diffs.append(best_idx - n)
            start_idx = best_idx

    if not diffs:
        return 0, 0
    most_common, count = Counter(diffs).most_common(1)[0]
    return int(most_common), int(count)


def run_step3(source_root: Path, workspace_root: Path, selection: Method1Selection) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    cbct_path = workspace_root / selection.patient_folder / selection.cbct_name / "interpolated_CBCT_b_spline.raw"
    qact_path = workspace_root / selection.patient_folder / selection.qact_name / f"{selection.qact_name}.raw"
    if not cbct_path.exists() or not qact_path.exists():
        raise FileNotFoundError("Step 3 需要先完成 Step 1")

    cbct = np.fromfile(cbct_path, dtype=np.float32).reshape(-1, 512, 512)
    ct = np.fromfile(qact_path, dtype=np.float32).reshape(-1, 512, 512)

    shift, count = _best_orb_shift(cbct, ct)
    return {
        "ok": True,
        "summary": {
            "recommendedShift": int(shift),
            "count": int(count),
        },
        "generatedFiles": [],
        "savedLocations": {
            "cbctPath": str(cbct_path),
            "ctPath": str(qact_path),
        },
        "message": f"Step 3 完成：推荐 shift = {shift}，count = {count}",
    }


def _compute_translation(cbct_img: np.ndarray, ct_img: np.ndarray) -> tuple[int, int]:
    orb = cv2.ORB_create()
    img1 = _norm_uint8(cbct_img)
    img2 = _norm_uint8(ct_img)
    kp1, des1 = orb.detectAndCompute(img1, None)
    kp2, des2 = orb.detectAndCompute(img2, None)
    if des1 is None or des2 is None:
        return 0, 0
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    if not matches:
        return 0, 0
    src = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 2)
    dst = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 2)
    translation = np.mean(dst - src, axis=0).astype(int)
    return int(translation[0]), int(translation[1])


def _window_to_png_base64(img: np.ndarray, wl: float = -300.0, ww: float = 1500.0) -> str:
    lo = wl - ww / 2.0
    hi = wl + ww / 2.0
    out = ((img.astype(np.float32) - lo) / (hi - lo) * 255.0).clip(0, 255).astype(np.uint8)
    pil = Image.fromarray(out)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def run_step4(
    source_root: Path,
    workspace_root: Path,
    selection: Method1Selection,
    shift: int,
    cbct_y_extra: int,
    ct_y_shift: int,
    apply_ct_mask: bool = False,
) -> dict[str, Any]:
    workspace_root = Path(workspace_root)

    patient_root = _safe_mkdir(workspace_root / selection.patient_folder)
    cbct_dir = _safe_mkdir(patient_root / selection.cbct_name)
    qact_dir = _safe_mkdir(patient_root / selection.qact_name)
    temp_dir = _safe_mkdir(patient_root / "_method1_temp")

    cbct_file_path = cbct_dir / "interpolated_CBCT_b_spline.raw"
    ct_file_path = qact_dir / f"{selection.qact_name}.raw"
    mask_file_path = temp_dir / "output_processed.raw"
    mask_patient_path = temp_dir / "output_processed_Patient.raw"

    if not cbct_file_path.exists() or not ct_file_path.exists():
        raise FileNotFoundError("Step 4 需要先完成 Step 1")
    if not mask_file_path.exists() or not mask_patient_path.exists():
        raise FileNotFoundError("Step 4 需要先完成 Step 2")

    cbct = np.fromfile(cbct_file_path, dtype=np.float32).reshape(-1, 512, 512)
    ct = np.fromfile(ct_file_path, dtype=np.float32).reshape(-1, 512, 512)
    mask = np.fromfile(mask_file_path, dtype=np.float32).reshape(-1, 512, 512)
    mask_p = np.fromfile(mask_patient_path, dtype=np.float32).reshape(-1, 512, 512)

    total_slice = min(len(cbct), len(ct) - max(shift, 0), len(mask) - max(shift, 0), len(mask_p) - max(shift, 0))
    if total_slice <= 0:
        raise ValueError("shift 导致没有可对齐的切片")

    mid_idx = min(70, total_slice - 1)
    ct_mid = ct[mid_idx + shift]
    tx, ty = _compute_translation(cbct[mid_idx], ct_mid)

    aligned_cbct = np.zeros_like(cbct[:total_slice], dtype=np.float32)
    aligned_ct = np.zeros_like(cbct[:total_slice], dtype=np.float32)
    mask_new = np.zeros_like(cbct[:total_slice], dtype=np.float32)

    ct_masked = ct.copy()
    ct_masked[mask_p == 0] = -1000
    ct_base = ct_masked if apply_ct_mask else ct

    for i in range(total_slice):
        cbct_img = cbct[i]
        ct_img = ct_base[i + shift]
        mask_img = mask[i + shift]

        aligned_cbct[i] = np.roll(cbct_img, shift=(ty + cbct_y_extra, tx), axis=(0, 1))
        aligned_ct[i] = np.roll(ct_img, shift=(ct_y_shift, 0), axis=(0, 1))
        mask_new[i] = np.roll(mask_img, shift=(ct_y_shift, 0), axis=(0, 1))

    cbct_centered_path = cbct_dir / "interpolated_CBCT_b_spline_centered.raw"
    ct_centered_path = qact_dir / f"{selection.qact_name}_centered.raw"
    mask_raw_path = cbct_dir / "interpolated_CBCT_b_spline_mask.raw"
    patient_masked_ct_path = qact_dir / f"{selection.qact_name}_Patientmasked.raw"

    aligned_cbct.tofile(cbct_centered_path)
    aligned_ct.tofile(ct_centered_path)
    mask_new.tofile(mask_raw_path)
    ct_masked.astype(np.float32).tofile(patient_masked_ct_path)

    cropped_cbct = aligned_cbct[:, 128:384, 128:384].astype(np.float32)
    cropped_ct = aligned_ct[:, 128:384, 128:384].astype(np.float32)
    cbct_cropped_path = cbct_dir / "interpolated_CBCT_b_spline_cropped_centered.raw"
    ct_cropped_path = qact_dir / f"{selection.qact_name}_cropped_centered.raw"
    cropped_cbct.tofile(cbct_cropped_path)
    cropped_ct.tofile(ct_cropped_path)

    cbct_slices_dir = _safe_mkdir(cbct_dir / selection.cbct_name)
    ct_slices_dir = _safe_mkdir(qact_dir / selection.cbct_name)
    masks_dir = _safe_mkdir(cbct_dir / "masks")

    for i in range(total_slice):
        filename = f"{selection.patient_folder}_{selection.cbct_name}_{i}.raw"
        cropped_ct[i].astype(np.float32).tofile(ct_slices_dir / filename)
        aligned_cbct[i].astype(np.float32).tofile(cbct_slices_dir / filename)
        mask_new[i, 128:384, 128:384].astype(np.float32).tofile(masks_dir / filename)

    preview_idx = min(70, total_slice - 1)
    cbct_preview = _window_to_png_base64(cropped_cbct[preview_idx], wl=-300.0, ww=1500.0)
    ct_preview = _window_to_png_base64(cropped_ct[preview_idx], wl=-300.0, ww=1500.0)

    return {
        "ok": True,
        "summary": {
            "translationVector": {"x": tx, "y": ty},
            "usedShift": int(shift),
            "usedCbctYExtra": int(cbct_y_extra),
            "usedCtYShift": int(ct_y_shift),
            "applyCtMask": bool(apply_ct_mask),
            "totalSlices": int(total_slice),
        },
        "generatedFiles": [
            str(cbct_file_path.parent / f"{selection.cbct_name}.raw"),
            str(cbct_file_path),
            str(cbct_centered_path),
            str(cbct_cropped_path),
            str(mask_raw_path),
            str(ct_file_path),
            str(ct_centered_path),
            str(ct_cropped_path),
            str(patient_masked_ct_path),
        ],
        "savedLocations": {
            "cbctDir": str(cbct_dir),
            "ctDir": str(qact_dir),
            "cbctSlicesDir": str(cbct_slices_dir),
            "ctSlicesDir": str(ct_slices_dir),
            "masksDir": str(masks_dir),
        },
        "preview": {
            "sliceIndex": int(preview_idx),
            "windowLevel": -300,
            "windowWidth": 1500,
            "cbctPng": cbct_preview,
            "ctPng": ct_preview,
        },
        "message": "Step 4 完成：已生成 centered / cropped / mask raw，以及最终 2D 数据集预览",
    }



def _sorted_any_dcm_files(series_dir: Path) -> list[Path]:
    files = [p for p in series_dir.iterdir() if p.is_file() and p.suffix.lower() == '.dcm']
    def inst_num(p: Path) -> int:
        try:
            ds = pydicom.dcmread(str(p), stop_before_pixels=True)
            return int(getattr(ds, 'InstanceNumber', 0))
        except Exception:
            return 0
    return sorted(files, key=inst_num)


def _window_to_png_base64_general(img: np.ndarray, wl: float = -300.0, ww: float = 1500.0) -> str:
    lo = wl - ww / 2.0
    hi = wl + ww / 2.0
    out = ((img.astype(np.float32) - lo) / (hi - lo) * 255.0).clip(0, 255).astype(np.uint8)
    pil = Image.fromarray(out)
    buf = io.BytesIO()
    pil.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def run_step5(
    source_root: Path,
    workspace_root: Path,
    selection: Method1Selection,
    shift: int,
    cbct_y_extra: int,
    processed_raw_path: str | None = None,
) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    patient_root = workspace_root / selection.patient_folder
    cbct_dir = patient_root / selection.cbct_name
    qact_dir = patient_root / selection.qact_name

    original_path = cbct_dir / 'interpolated_CBCT_b_spline.raw'
    centered_path = cbct_dir / 'interpolated_CBCT_b_spline_centered.raw'
    processed_path = Path(processed_raw_path) if processed_raw_path else centered_path
    if not processed_path.is_absolute():
        processed_path = (workspace_root / processed_path).resolve()
    if not original_path.exists():
        raise FileNotFoundError(f'未找到原始插值 CBCT: {original_path}')
    if not processed_path.exists():
        raise FileNotFoundError(f'未找到待回插 raw: {processed_path}')

    cbct = np.fromfile(original_path, dtype=np.float32).reshape(-1, 512, 512)
    ct_path = qact_dir / f'{selection.qact_name}.raw'
    if not ct_path.exists():
        raise FileNotFoundError(f'未找到 CT raw: {ct_path}')
    ct = np.fromfile(ct_path, dtype=np.float32).reshape(-1, 512, 512)

    total_slice = min(len(cbct), len(ct) - max(shift, 0))
    if total_slice <= 0:
        raise ValueError('shift 导致没有可对齐的切片，无法计算回插参数')
    mid_idx = min(70, total_slice - 1)
    tx, ty = _compute_translation(cbct[mid_idx], ct[mid_idx + shift])

    dy = ty + cbct_y_extra
    dx = tx
    row_start = 128 - dy
    row_end = 384 - dy
    col_start = 128 - dx
    col_end = 384 - dx
    if not (0 <= row_start < row_end <= 512 and 0 <= col_start < col_end <= 512):
        raise ValueError(f'回插窗口越界: rows {row_start}:{row_end}, cols {col_start}:{col_end}')

    processed_raw = np.fromfile(processed_path, dtype=np.float32)
    if processed_raw.size % (512 * 512) == 0:
        processed_source = processed_raw.reshape(-1, 512, 512)
        processed = processed_source[:, 128:384, 128:384].astype(np.float32)
        processed_source_type = 'centered_512_crop_to_256'
    elif processed_raw.size % (256 * 256) == 0:
        processed = processed_raw.reshape(-1, 256, 256).astype(np.float32)
        processed_source_type = 'direct_256'
    else:
        raise ValueError('待回插 raw 既不能按 512x512 也不能按 256x256 切片解释')

    z_len = min(len(cbct), len(processed))
    if z_len <= 0:
        raise ValueError('待回插 raw 没有可用切片')

    reinserted = cbct.copy()
    reinserted[:z_len, row_start:row_end, col_start:col_end] = processed[:z_len]

    out_path = cbct_dir / 'interpolated_CBCT_b_spline_reinserted_preview.raw'
    reinserted.astype(np.float32).tofile(out_path)

    preview_idx = min(70, z_len - 1)
    original_preview = _window_to_png_base64_general(cbct[preview_idx], wl=-300.0, ww=1500.0)
    processed_preview = _window_to_png_base64_general(processed[preview_idx], wl=-300.0, ww=1500.0)
    reinserted_preview = _window_to_png_base64_general(reinserted[preview_idx], wl=-300.0, ww=1500.0)

    return {
        'ok': True,
        'summary': {
            'translationVector': {'x': int(tx), 'y': int(ty)},
            'usedShift': int(shift),
            'usedCbctYExtra': int(cbct_y_extra),
            'computedDy': int(dy),
            'computedDx': int(dx),
            'offset_x': int(-dy),
            'offset_y': int(-dx),
            'processedSourceType': processed_source_type,
            'reinsertWindow': {
                'rowStart': int(row_start),
                'rowEnd': int(row_end),
                'colStart': int(col_start),
                'colEnd': int(col_end),
            },
            'zLen': int(z_len),
        },
        'generatedFiles': [str(out_path)],
        'savedLocations': {
            'originalCbct': str(original_path),
            'processedRaw': str(processed_path),
            'reinsertedPreviewRaw': str(out_path),
        },
        'preview': {
            'sliceIndex': int(preview_idx),
            'windowLevel': -300,
            'windowWidth': 1500,
            'originalPng': original_preview,
            'processedPng': processed_preview,
            'reinsertedPng': reinserted_preview,
        },
        'message': 'Step 5 完成：已按 offset 将 centered 区域的 128:384 裁剪结果回插到原始 interpolated_CBCT_b_spline.raw',
    }
def _backend_dir() -> Path:
    return Path(__file__).resolve().parent


def increment_uid(uid: str, step: int = 1) -> str:
    parts = uid.split('.')
    try:
        last = int(parts[-1])
        parts[-1] = str(last + step)
    except ValueError:
        parts.append(str(step))
    return '.'.join(parts)


def uid_last_number(uid: str):
    try:
        return int(uid.split('.')[-1])
    except Exception:
        return None


def collect_existing_uid_suffixes(uid_registry: dict) -> set:
    suffixes = set()
    for pid, pdata in uid_registry.items():
        if not isinstance(pdata, dict):
            continue
        orig = pdata.get('original', {})
        for k in ('StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID'):
            val = orig.get(k)
            if isinstance(val, str):
                n = uid_last_number(val)
                if n is not None:
                    suffixes.add(n)
        gen = pdata.get('generated', {})
        if isinstance(gen, dict):
            for _, rec in gen.items():
                if not isinstance(rec, dict):
                    continue
                for k in ('StudyInstanceUID', 'SeriesInstanceUID', 'BaseSOPInstanceUID'):
                    val = rec.get(k)
                    if isinstance(val, str):
                        n = uid_last_number(val)
                        if n is not None:
                            suffixes.add(n)
    return suffixes


def generate_unique_uid_not_in(uid_registry: dict) -> str:
    existing = set()
    for pid, pdata in uid_registry.items():
        if not isinstance(pdata, dict):
            continue
        orig = pdata.get('original', {})
        for k in ('StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID'):
            v = orig.get(k)
            if isinstance(v, str):
                existing.add(v)
        gen = pdata.get('generated', {})
        if isinstance(gen, dict):
            for _, rec in gen.items():
                if not isinstance(rec, dict):
                    continue
                for k in ('StudyInstanceUID', 'SeriesInstanceUID', 'BaseSOPInstanceUID'):
                    v = rec.get(k)
                    if isinstance(v, str):
                        existing.add(v)
    while True:
        candidate = pydicom.uid.generate_uid()
        if candidate not in existing:
            return candidate


def generate_nonconflicting_base_sop_uid(uid_registry: dict, margin: int = 107) -> str:
    suffixes = collect_existing_uid_suffixes(uid_registry)
    while True:
        candidate = pydicom.uid.generate_uid()
        n = uid_last_number(candidate)
        if n is None:
            continue
        if all(abs(n - s) > margin for s in suffixes):
            return candidate


def _load_uid_registry() -> tuple[dict[str, Any], Path]:
    path = _backend_dir() / 'Patient_rename.json'
    if path.exists():
        try:
            return json.loads(path.read_text(encoding='utf-8')), path
        except Exception:
            return {}, path
    return {}, path


def _get_original_uid_block(source_root: Path, selection: Method1Selection, uid_registry: dict[str, Any]) -> dict[str, str]:
    if selection.patient_folder in uid_registry and isinstance(uid_registry[selection.patient_folder], dict):
        orig = uid_registry[selection.patient_folder].get('original')
        if isinstance(orig, dict) and all(k in orig for k in ('StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID')):
            return orig

    dcm_dir = Path(source_root) / selection.patient_folder / selection.cbct_name
    dcm_files = _sorted_any_dcm_files(dcm_dir)
    if not dcm_files:
        raise FileNotFoundError(f'未找到原始 DICOM 用于提取 UID: {dcm_dir}')
    ds = pydicom.dcmread(str(dcm_files[0]), stop_before_pixels=True)
    return {
        'StudyInstanceUID': str(ds.get('StudyInstanceUID', '')),
        'SeriesInstanceUID': str(ds.get('SeriesInstanceUID', '')),
        'SOPInstanceUID': str(ds.get('SOPInstanceUID', '')),
    }


def run_step6(
    source_root: Path,
    workspace_root: Path,
    selection: Method1Selection,
    shift: int,
    cbct_y_extra: int,
    model_name: str,
) -> dict[str, Any]:
    source_root = Path(source_root)
    workspace_root = Path(workspace_root)
    model_name = (model_name or '').strip()
    if not model_name:
        raise ValueError('modelName 不能为空')

    patient_root = workspace_root / selection.patient_folder
    meta_path = patient_root / '_method1_meta' / 'step1_info.json'
    if not meta_path.exists():
        raise FileNotFoundError('Step 6 需要先完成 Step 1，缺少 step1_info.json')
    step1_info = json.loads(meta_path.read_text(encoding='utf-8'))

    # 用和 Step 5 相同的逻辑反推出 offset_x / offset_y
    cbct_path = patient_root / selection.cbct_name / 'interpolated_CBCT_b_spline.raw'
    qact_path = patient_root / selection.qact_name / f'{selection.qact_name}.raw'
    if not cbct_path.exists() or not qact_path.exists():
        raise FileNotFoundError('Step 6 需要先完成 Step 1')
    cbct = np.fromfile(cbct_path, dtype=np.float32).reshape(-1, 512, 512)
    ct = np.fromfile(qact_path, dtype=np.float32).reshape(-1, 512, 512)
    total_slice = min(len(cbct), len(ct) - max(shift, 0))
    if total_slice <= 0:
        raise ValueError('shift 导致没有可用于总结参数的切片')
    mid_idx = min(70, total_slice - 1)
    tx, ty = _compute_translation(cbct[mid_idx], ct[mid_idx + shift])
    dy = ty + cbct_y_extra
    dx = tx
    offset_x = -dy
    offset_y = -dx

    patient_params_entry = {
        selection.patient_folder: {
            'offset_x': int(offset_x),
            'offset_y': int(offset_y),
            'old_spacing': step1_info['oldPixelSpacing'],
            'old_thickness': step1_info['oldSliceThickness'],
            'new_spacing': step1_info['newPixelSpacing'],
            'new_thickness': step1_info['newSliceThickness'],
            'target_slices': int(np.fromfile(cbct_path, dtype=np.float32).size // (512 * 512)),
            'raw_relpath': f"{selection.patient_folder}/{selection.cbct_name}/interpolated_CBCT_b_spline.raw",
            'dicom_relpath': f"{selection.patient_folder}/{selection.cbct_name}",
        }
    }

    uid_registry, uid_path = _load_uid_registry()
    original_block = _get_original_uid_block(source_root, selection, uid_registry)
    uid_registry.setdefault(selection.patient_folder, {})
    uid_registry[selection.patient_folder].setdefault('original', original_block)
    uid_registry[selection.patient_folder].setdefault('generated', {})

    existing = uid_registry[selection.patient_folder]['generated'].get(model_name)
    if isinstance(existing, dict) and all(k in existing for k in ('StudyInstanceUID', 'SeriesInstanceUID', 'BaseSOPInstanceUID')):
        generated_block = existing
        from_registry = True
    else:
        generated_block = {
            'StudyInstanceUID': generate_unique_uid_not_in(uid_registry),
            'SeriesInstanceUID': generate_unique_uid_not_in(uid_registry),
            'BaseSOPInstanceUID': generate_nonconflicting_base_sop_uid(uid_registry, margin=107),
        }
        from_registry = False

    patient_rename_entry = {
        selection.patient_folder: {
            'original': original_block,
            'generated': {
                model_name: generated_block
            }
        }
    }

    return {
        'ok': True,
        'summary': {
            'modelName': model_name,
            'offset_x': int(offset_x),
            'offset_y': int(offset_y),
            'uidRegistryPath': str(uid_path),
            'renameFromExistingRegistry': bool(from_registry),
        },
        'generatedFiles': [],
        'savedLocations': {
            'patientParamsSource': str(meta_path),
            'patientRenameRegistry': str(uid_path),
        },
        'patientParamsEntry': patient_params_entry,
        'patientRenameEntry': patient_rename_entry,
        'message': 'Step 6 完成：已根据当前 workflow 总结出 patient_params.json 与 Patient_rename.json 建议条目',
    }
