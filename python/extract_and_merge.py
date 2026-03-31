# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import numpy as np
# ============================================================
# 注意：
# 这里不要自己写死 G:/CBCTtoCT。
# merge 输入结果目录、TestPatient 输出目录，都统一从 config.py 读取。
# 以后路径变化时，只改 config.py。
# ============================================================
from config import MODEL_PROJECT_ROOT, TEST_PATIENT_ROOT

sys.stdout.reconfigure(encoding="utf-8")

MODEL_OUTPUT_FOLDER = {
    "attn": "cycleattn0220",
    "0106": "cyclegan_mask_HN005_HN023",
    "mb_taylor": "cyclegan-swin",
    "cstgan_c": "cyclegan-swin-mask",
    "vit-unet": "cyclegan-vit",
}

RESULT_FOLDER_MAP = {
    "vit-unet": "cycle_vit1",
    "attn": "cycle_attn",
    "0106": "cycle_gan_0106",
}

SUFFIXES = ["fake_B", "real_A", "real_B"]
SLICE_SHAPE = (256, 256)


def parse_dataset_range(dataset_name: str):
    nums = re.findall(r"\d+", dataset_name)
    if len(nums) < 2:
        raise ValueError(f"无法从数据集名称解析范围: {dataset_name}")
    start = int(nums[0])
    end = int(nums[1])
    return list(range(start, end + 1))


def find_images_dir(model_dir: str, model_kind: str) -> Path:
    folder_name = RESULT_FOLDER_MAP.get(model_kind, model_kind)

    # 这里的 MODEL_PROJECT_ROOT 通常就是老项目根目录，比如 G:/CBCTtoCT
    # 如果未来 results 目录整体搬家，不改这里，去 config.py 改 MODEL_PROJECT_ROOT
    p = MODEL_PROJECT_ROOT / model_dir / "results" / folder_name / "test_latest" / "images"

    if not p.exists():
        raise FileNotFoundError(f"未找到图像目录: {p}")
    return p

def stack_3d_and_save(files, images_dir: Path, out_path: Path):
    slices = []
    h, w = SLICE_SHAPE
    for filename in files:
        data = np.fromfile(images_dir / filename, dtype=np.float32)
        try:
            data = data.reshape(h, w)
        except Exception as e:
            print(f"  [ERROR] {filename} reshape 失败: {e}")
            continue
        slices.append(data)

    if not slices:
        print("  [WARN] 没有有效切片，跳过写出。")
        return False

    volume = np.stack(slices, axis=0).astype(np.float32)
    volume.tofile(out_path)
    return True


def run(model_dir: str, model_kind: str, dataset_name: str):
    patient_ids = parse_dataset_range(dataset_name)

    out_folder_name = MODEL_OUTPUT_FOLDER.get(model_kind, model_kind)
    out_dir = TEST_PATIENT_ROOT / out_folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    images_dir = find_images_dir(model_dir, model_kind)

    print(f"[INFO] 模型目录: {model_dir}")
    print(f"[INFO] 模型类型(kind): {model_kind}")
    print(f"[INFO] 数据集: {dataset_name} -> 病人 {patient_ids[0]:03d}..{patient_ids[-1]:03d}")
    print(f"[INFO] 源目录: {images_dir}")
    print(f"[INFO] 输出目录: {out_dir}\n")

    for pid in patient_ids:
        pid_prefix = f"HN{pid:03d}_CBCT_"
        patient_files = [f for f in os.listdir(images_dir) if f.startswith(pid_prefix)]
        if not patient_files:
            print(f"[WARN] 未找到 {pid_prefix} 对应文件，跳过。")
            continue

        example = patient_files[0]
        m = re.match(r"^(HN\d{3}_CBCT_\d{8}-\d{4})_", example)
        if not m:
            print(f"[WARN] 无法解析病人名: {example}，跳过。")
            continue

        patient_name = m.group(1)
        print(f"[INFO] 处理病人: {patient_name}")

        for suf in SUFFIXES:
            suf_files = [f for f in patient_files if f.endswith(f"_{suf}.raw")]
            if not suf_files:
                print(f"  [WARN] {suf} 无文件。")
                continue

            def slice_index(fn):
                m2 = re.search(r"_(\d+)_" + re.escape(suf) + r"\.raw$", fn)
                return int(m2.group(1)) if m2 else 0

            suf_files.sort(key=slice_index)

            out_name = f"{patient_name}_3d_{suf}.raw"
            out_path = out_dir / out_name
            ok = stack_3d_and_save(suf_files, images_dir, out_path)
            if ok:
                print(f"  [OK] 保存: {out_name} (slices={len(suf_files)})")
        print("")

    print("[DONE] 全部处理完成。输出目录:", out_dir)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("用法: python extract_and_merge.py <model_dir> <model_kind> <dataset_name>")
        print("示例: python extract_and_merge.py model_cstgan mb_taylor 046_047")
        sys.exit(1)

    run(sys.argv[1], sys.argv[2], sys.argv[3])