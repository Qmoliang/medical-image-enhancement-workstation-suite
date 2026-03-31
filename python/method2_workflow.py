from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any

import numpy as np
import pydicom
from PIL import Image
from scipy.ndimage import center_of_mass

from method1_workflow import (
    Method1Selection,
    _selection_from_payload,
    _safe_mkdir,
    _window_to_png_base64,
    generate_matches,
    list_roi_options,
    run_step1 as method1_run_step1,
    run_step2 as method1_run_step2,
)

DEFAULT_SOURCE_ROOT = Path(r"G:\mimi0209\HeadNeck-selected")
DEFAULT_WORKSPACE_ROOT = Path(r"G:\mimi0209\output-test")


def run_step1(source_root: Path, workspace_root: Path, selection: Method1Selection) -> dict[str, Any]:
    return method1_run_step1(source_root, workspace_root, selection)


def run_step2(source_root: Path, workspace_root: Path, selection: Method1Selection, roi_name: str) -> dict[str, Any]:
    return method1_run_step2(source_root, workspace_root, selection, roi_name)


def _load_step1_info(workspace_root: Path, selection: Method1Selection) -> dict[str, Any]:
    info_path = Path(workspace_root) / selection.patient_folder / "_method1_meta" / "step1_info.json"
    if not info_path.exists():
        raise FileNotFoundError(f"缺少 Step 1 信息文件: {info_path}")
    return json.loads(info_path.read_text(encoding="utf-8"))


def _read_raw_image(raw_path: Path, size_xyz: list[int], pixel_spacing_xyz: list[float]):
    import SimpleITK as sitk

    data = np.fromfile(raw_path, dtype=np.float32)
    expected = size_xyz[0] * size_xyz[1] * size_xyz[2]
    if data.size != expected:
        raise ValueError(f"raw 尺寸不匹配: {raw_path} 期望 {expected} 实际 {data.size}")
    img = sitk.GetImageFromArray(data.reshape(size_xyz[2], size_xyz[1], size_xyz[0]))
    img.SetSpacing(pixel_spacing_xyz)
    return img


def _save_raw_image(img, file_path: Path) -> None:
    import SimpleITK as sitk

    arr = sitk.GetArrayFromImage(img).astype(np.float32)
    arr.tofile(file_path)


def run_step3(source_root: Path, workspace_root: Path, selection: Method1Selection) -> dict[str, Any]:
    import SimpleITK as sitk

    workspace_root = Path(workspace_root)
    patient_root = _safe_mkdir(workspace_root / selection.patient_folder)
    qact_dir = _safe_mkdir(patient_root / selection.qact_name)
    cbct_dir = _safe_mkdir(patient_root / selection.cbct_name)
    temp_dir = _safe_mkdir(patient_root / "_method2_temp")

    step1_info = _load_step1_info(workspace_root, selection)
    pixel_spacing = [
        float(step1_info["newPixelSpacing"][0]),
        float(step1_info["newPixelSpacing"][1]),
        float(step1_info["newSliceThickness"]),
    ]

    moving_raw_path = qact_dir / f"{selection.qact_name}.raw"
    fixed_raw_path = cbct_dir / "interpolated_CBCT_b_spline.raw"
    roi_mask_path = patient_root / "_method1_temp" / "output_processed.raw"
    patient_mask_path = patient_root / "_method1_temp" / "output_processed_Patient.raw"

    if not moving_raw_path.exists() or not fixed_raw_path.exists():
        raise FileNotFoundError("Step 3 需要先完成 Step 1")
    if not roi_mask_path.exists() or not patient_mask_path.exists():
        raise FileNotFoundError("Step 3 需要先完成 Step 2")

    qact_size = int(np.fromfile(moving_raw_path, dtype=np.float32).size // (512 * 512))
    cbct_size = int(np.fromfile(fixed_raw_path, dtype=np.float32).size // (512 * 512))

    moving_image = _read_raw_image(moving_raw_path, [512, 512, qact_size], pixel_spacing)
    fixed_image = _read_raw_image(fixed_raw_path, [512, 512, cbct_size], pixel_spacing)
    roi_mask_img = _read_raw_image(roi_mask_path, [512, 512, qact_size], pixel_spacing)
    patient_mask_img = _read_raw_image(patient_mask_path, [512, 512, qact_size], pixel_spacing)

    initial_transform = sitk.CenteredTransformInitializer(
        fixed_image,
        moving_image,
        sitk.Euler3DTransform(),
        sitk.CenteredTransformInitializerFilter.GEOMETRY,
    )

    registration_method = sitk.ImageRegistrationMethod()
    registration_method.SetMetricAsMeanSquares()
    registration_method.SetMetricSamplingStrategy(registration_method.RANDOM)
    registration_method.SetMetricSamplingPercentage(0.01)
    registration_method.SetInterpolator(sitk.sitkLinear)
    registration_method.SetOptimizerAsGradientDescent(
        learningRate=1.0,
        numberOfIterations=100,
        convergenceMinimumValue=1e-6,
        convergenceWindowSize=10,
    )
    registration_method.SetOptimizerScalesFromPhysicalShift()
    registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[4, 2, 1])
    registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[2, 1, 0])
    registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()
    registration_method.SetInitialTransform(initial_transform, inPlace=False)

    final_transform = registration_method.Execute(
        sitk.Cast(fixed_image, sitk.sitkFloat32),
        sitk.Cast(moving_image, sitk.sitkFloat32),
    )

    moving_resampled = sitk.Resample(
        moving_image, fixed_image, final_transform, sitk.sitkLinear, -1000.0, moving_image.GetPixelID()
    )
    roi_mask_registered = sitk.Resample(
        roi_mask_img, fixed_image, final_transform, sitk.sitkNearestNeighbor, 0.0, roi_mask_img.GetPixelID()
    )
    patient_mask_registered = sitk.Resample(
        patient_mask_img, fixed_image, final_transform, sitk.sitkNearestNeighbor, 0.0, patient_mask_img.GetPixelID()
    )

    registered_ct_path = patient_root / "registered_QACT_to_CBCT.raw"
    registered_roi_mask_path = temp_dir / "registered_binary_mask_ROI.raw"
    registered_patient_mask_path = temp_dir / "registered_binary_mask.raw"
    transform_info_path = temp_dir / "registration_info.json"

    _save_raw_image(moving_resampled, registered_ct_path)
    _save_raw_image(roi_mask_registered, registered_roi_mask_path)
    _save_raw_image(patient_mask_registered, registered_patient_mask_path)

    transform_info = {
        "patientFolder": selection.patient_folder,
        "cbctName": selection.cbct_name,
        "qactName": selection.qact_name,
        "pixelSpacing": pixel_spacing,
        "registeredCtPath": str(registered_ct_path),
        "registeredRoiMaskPath": str(registered_roi_mask_path),
        "registeredPatientMaskPath": str(registered_patient_mask_path),
        "optimizerStop": registration_method.GetOptimizerStopConditionDescription(),
        "metricValue": float(registration_method.GetMetricValue()),
    }
    transform_info_path.write_text(json.dumps(transform_info, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "summary": {
            "pixelSpacing": pixel_spacing,
            "metricValue": float(registration_method.GetMetricValue()),
            "optimizerStop": registration_method.GetOptimizerStopConditionDescription(),
        },
        "generatedFiles": [
            str(registered_ct_path),
            str(registered_roi_mask_path),
            str(registered_patient_mask_path),
            str(transform_info_path),
        ],
        "savedLocations": {
            "patientRoot": str(patient_root),
            "tempDir": str(temp_dir),
        },
        "message": "Step 3 完成：已用 SimpleITK 将 QACT 配准到 CBCT，并生成注册后的 CT / mask 文件",
    }


def run_step4(source_root: Path, workspace_root: Path, selection: Method1Selection) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    patient_root = _safe_mkdir(workspace_root / selection.patient_folder)
    cbct_dir = _safe_mkdir(patient_root / selection.cbct_name)
    qact_dir = _safe_mkdir(patient_root / selection.qact_name)
    temp_dir = _safe_mkdir(patient_root / "_method2_temp")
    final_dir = _safe_mkdir(patient_root / "registrated_data")

    cbct_path = cbct_dir / "interpolated_CBCT_b_spline.raw"
    qact_path = qact_dir / f"{selection.qact_name}.raw"
    registered_path = patient_root / "registered_QACT_to_CBCT.raw"
    mask_roi_path = temp_dir / "registered_binary_mask_ROI.raw"
    mask_patient_path = temp_dir / "registered_binary_mask.raw"

    for p in [cbct_path, qact_path, registered_path, mask_roi_path, mask_patient_path]:
        if not p.exists():
            raise FileNotFoundError(f"Step 4 缺少文件: {p}")

    cbct = np.fromfile(cbct_path, dtype=np.float32).reshape(-1, 512, 512)
    ct = np.fromfile(qact_path, dtype=np.float32).reshape(-1, 512, 512)
    registered_ct = np.fromfile(registered_path, dtype=np.float32).reshape(-1, 512, 512)
    mask = np.fromfile(mask_roi_path, dtype=np.float32).reshape(-1, 512, 512)
    mask_p = np.fromfile(mask_patient_path, dtype=np.float32).reshape(-1, 512, 512)

    z, y, x = center_of_mass(mask_p)
    center_of_mass_coords = (int(round(z)), int(round(y)), int(round(x)))
    image_center = np.array([ct.shape[0] // 2, 256, 256])
    shift = image_center - np.array(center_of_mass_coords)

    ct_masked_centered = np.zeros_like(registered_ct)
    cbct_centered = np.zeros_like(cbct)
    mask_centered = np.zeros_like(mask)

    for i in range(registered_ct.shape[0]):
        ct_masked_centered[i] = np.roll(registered_ct[i], shift=(int(shift[1]), int(shift[2])), axis=(0, 1))
    for i in range(cbct.shape[0]):
        cbct_centered[i] = np.roll(cbct[i], shift=(int(shift[1]), int(shift[2])), axis=(0, 1))
    for i in range(mask.shape[0]):
        mask_centered[i] = np.roll(mask[i], shift=(int(shift[1]), int(shift[2])), axis=(0, 1))

    cbct_centered_path = final_dir / f"cbct_{selection.cbct_name}.raw"
    ct_centered_path = final_dir / f"qact_{selection.cbct_name}.raw"
    mask_centered_path = final_dir / f"mask_{selection.cbct_name}.raw"

    cbct_centered.astype(np.float32).tofile(cbct_centered_path)
    ct_masked_centered.astype(np.float32).tofile(ct_centered_path)
    mask_centered.astype(np.float32).tofile(mask_centered_path)

    cbct_2d_dir = _safe_mkdir(final_dir / "cbct")
    ct_2d_dir = _safe_mkdir(final_dir / "ct")
    mask_2d_dir = _safe_mkdir(final_dir / "mask")

    total_slices = cbct_centered.shape[0]
    for i in range(total_slices):
        filename = f"{selection.cbct_name}_{i:03d}.raw"
        cbct_centered[i].astype(np.float32).tofile(cbct_2d_dir / filename)
        ct_masked_centered[i].astype(np.float32).tofile(ct_2d_dir / filename)
        mask_centered[i].astype(np.float32).tofile(mask_2d_dir / filename)

    info = {
        "computedShift": {"z": int(shift[0]), "y": int(shift[1]), "x": int(shift[2])},
        "centerOfMass": {"z": center_of_mass_coords[0], "y": center_of_mass_coords[1], "x": center_of_mass_coords[2]},
        "totalSlices": int(total_slices),
        "cbctCenteredPath": str(cbct_centered_path),
        "ctCenteredPath": str(ct_centered_path),
        "maskCenteredPath": str(mask_centered_path),
    }
    (temp_dir / "step4_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")

    preview_idx = min(70, total_slices - 1)
    cbct_preview = _window_to_png_base64(cbct_centered[preview_idx], wl=-300.0, ww=1500.0)
    ct_preview = _window_to_png_base64(ct_masked_centered[preview_idx], wl=-300.0, ww=1500.0)

    return {
        "ok": True,
        "summary": {
            "ComputedShift": {"z": int(shift[0]), "y": int(shift[1]), "x": int(shift[2])},
            "totalSlices": int(total_slices),
        },
        "generatedFiles": [
            str(cbct_centered_path),
            str(ct_centered_path),
            str(mask_centered_path),
        ],
        "savedLocations": {
            "finalDir": str(final_dir),
            "cbct2dDir": str(cbct_2d_dir),
            "ct2dDir": str(ct_2d_dir),
            "mask2dDir": str(mask_2d_dir),
        },
        "preview": {
            "sliceIndex": int(preview_idx),
            "windowLevel": -300,
            "windowWidth": 1500,
            "cbctPng": cbct_preview,
            "ctPng": ct_preview,
        },
        "message": "Step 4 完成：已根据注册后的 mask 质心完成 centered，并生成最终数据集",
    }


def run_step5(source_root: Path, workspace_root: Path, selection: Method1Selection, processed_raw_path: str | None = None) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    patient_root = workspace_root / selection.patient_folder
    cbct_dir = patient_root / selection.cbct_name
    final_dir = patient_root / "registrated_data"
    temp_dir = _safe_mkdir(patient_root / "_method2_temp")

    original_path = cbct_dir / "interpolated_CBCT_b_spline.raw"
    default_processed = final_dir / f"cbct_{selection.cbct_name}.raw"
    processed_path = Path(processed_raw_path) if processed_raw_path else default_processed
    step4_info_path = temp_dir / "step4_info.json"

    if not original_path.exists():
        raise FileNotFoundError(f"缺少原始 CBCT: {original_path}")
    if not processed_path.exists():
        raise FileNotFoundError(f"缺少待回插 raw: {processed_path}")
    if not step4_info_path.exists():
        raise FileNotFoundError("Step 5 需要先完成 Step 4")

    info = json.loads(step4_info_path.read_text(encoding="utf-8"))
    shift_y = int(info["computedShift"]["y"])
    shift_x = int(info["computedShift"]["x"])

    original = np.fromfile(original_path, dtype=np.float32).reshape(-1, 512, 512)
    processed = np.fromfile(processed_path, dtype=np.float32).reshape(-1, 512, 512)

    row_start = 128 - shift_y
    row_end = 384 - shift_y
    col_start = 128 - shift_x
    col_end = 384 - shift_x

    reinserted = original.copy()
    z_len = min(processed.shape[0], reinserted.shape[0])
    reinserted[:z_len, row_start:row_end, col_start:col_end] = processed[:z_len, 128:384, 128:384]

    preview_path = temp_dir / "interpolated_CBCT_b_spline_reinserted_preview.raw"
    reinserted.astype(np.float32).tofile(preview_path)

    preview_idx = min(70, z_len - 1)
    return {
        "ok": True,
        "summary": {
            "shift": {"y": shift_y, "x": shift_x},
            "reinsertWindow": {
                "rowStart": int(row_start),
                "rowEnd": int(row_end),
                "colStart": int(col_start),
                "colEnd": int(col_end),
            },
        },
        "generatedFiles": [str(preview_path)],
        "savedLocations": {"tempDir": str(temp_dir)},
        "preview": {
            "sliceIndex": int(preview_idx),
            "windowLevel": -300,
            "windowWidth": 1500,
            "cbctOriginalPng": _window_to_png_base64(original[preview_idx]),
            "processedPng": _window_to_png_base64(processed[preview_idx]),
            "reinsertedPng": _window_to_png_base64(reinserted[preview_idx]),
        },
        "message": "Step 5 完成：已根据方法二的 centered 结果执行回插验证",
    }


def _collect_all_uids(uid_registry: dict[str, Any]) -> set[str]:
    used: set[str] = set()
    for patient_data in uid_registry.values():
        if not isinstance(patient_data, dict):
            continue
        for section_name in ["original", "generated"]:
            section = patient_data.get(section_name, {})
            if section_name == "generated":
                for model_info in section.values():
                    if isinstance(model_info, dict):
                        used.update(str(v) for v in model_info.values() if v)
            elif isinstance(section, dict):
                used.update(str(v) for v in section.values() if v)
    return used


def _generate_unique_uid_not_in(uid_registry: dict[str, Any]) -> str:
    from pydicom.uid import generate_uid

    used = _collect_all_uids(uid_registry)
    while True:
        uid = generate_uid()
        if uid not in used:
            return uid


def _increment_uid(base_uid: str, increment: int) -> str:
    parts = base_uid.split('.')
    last_num = int(parts[-1])
    new_last_num = last_num + increment
    return '.'.join(parts[:-1] + [str(new_last_num)])


def _generate_nonconflicting_base_sop_uid(uid_registry: dict[str, Any], margin: int = 107) -> str:
    used = _collect_all_uids(uid_registry)
    from pydicom.uid import generate_uid
    while True:
        candidate = generate_uid()
        try:
            last_num = int(candidate.split('.')[-1])
        except Exception:
            continue
        conflict = False
        for uid in used:
            try:
                used_last = int(str(uid).split('.')[-1])
                if abs(last_num - used_last) < margin:
                    conflict = True
                    break
            except Exception:
                continue
        if not conflict and candidate not in used:
            return candidate


def run_step6(source_root: Path, workspace_root: Path, selection: Method1Selection, model_name: str) -> dict[str, Any]:
    workspace_root = Path(workspace_root)
    patient_id = selection.patient_folder
    patient_root = workspace_root / patient_id
    cbct_dir = patient_root / selection.cbct_name
    step1_info = _load_step1_info(workspace_root, selection)
    step4_info = json.loads((patient_root / "_method2_temp" / "step4_info.json").read_text(encoding="utf-8"))

    shift_y = int(step4_info["computedShift"]["y"])
    shift_x = int(step4_info["computedShift"]["x"])
    offset_x = -shift_y
    offset_y = -shift_x

    patient_params_entry = {
        patient_id: {
            "offset_x": int(offset_x),
            "offset_y": int(offset_y),
            "old_spacing": [float(x) for x in step1_info["oldPixelSpacing"]],
            "old_thickness": float(step1_info["oldSliceThickness"]),
            "new_spacing": [float(x) for x in step1_info["newPixelSpacing"]],
            "new_thickness": float(step1_info["newSliceThickness"]),
            "target_slices": int(np.fromfile(cbct_dir / "interpolated_CBCT_b_spline.raw", dtype=np.float32).size // (512 * 512)),
            "raw_relpath": f"{patient_id}/{selection.cbct_name}/interpolated_CBCT_b_spline.raw",
            "dicom_relpath": f"{patient_id}/{selection.cbct_name}",
        }
    }

    uid_path = Path(__file__).resolve().parent / "Patient_rename.json"
    uid_registry: dict[str, Any] = {}
    if uid_path.exists():
        try:
            uid_registry = json.loads(uid_path.read_text(encoding="utf-8"))
        except Exception:
            uid_registry = {}

    patient_entry = uid_registry.get(patient_id, {}) if isinstance(uid_registry, dict) else {}
    original_entry = patient_entry.get("original") if isinstance(patient_entry, dict) else None
    if not original_entry:
        qact_dir = Path(source_root) / patient_id / selection.qact_name
        ct_dcms = sorted([p for p in qact_dir.iterdir() if p.is_file() and p.suffix.lower() == ".dcm" and p.name.upper().startswith("CT")])
        if not ct_dcms:
            raise FileNotFoundError(f"未找到原始 CT DICOM: {qact_dir}")
        ds = pydicom.dcmread(str(ct_dcms[0]), stop_before_pixels=True)
        original_entry = {
            "StudyInstanceUID": str(ds.StudyInstanceUID),
            "SeriesInstanceUID": str(ds.SeriesInstanceUID),
            "SOPInstanceUID": str(ds.SOPInstanceUID),
        }

    generated_entry = {
        model_name: {
            "StudyInstanceUID": _generate_unique_uid_not_in(uid_registry),
            "SeriesInstanceUID": _generate_unique_uid_not_in(uid_registry),
            "BaseSOPInstanceUID": _generate_nonconflicting_base_sop_uid(uid_registry),
        }
    }

    patient_rename_entry = {
        patient_id: {
            "original": original_entry,
            "generated": generated_entry,
        }
    }

    return {
        "ok": True,
        "summary": {
            "patientId": patient_id,
            "modelName": model_name,
            "offset": {"x": int(offset_x), "y": int(offset_y)},
        },
        "patientParamsEntry": patient_params_entry,
        "patientRenameEntry": patient_rename_entry,
        "generatedFiles": [],
        "savedLocations": {
            "patientRoot": str(patient_root),
            "uidRegistryPath": str(uid_path),
        },
        "message": "Step 6 完成：已生成 patient_params.json 与 Patient_rename.json 建议条目",
    }
