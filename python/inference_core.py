from __future__ import annotations

import subprocess
import sys
from pathlib import Path


# ============================================================
# 注意：
# 这里不要自己写死 G:/xxx 路径。
# 所有将来可能变化的模型目录、数据目录，都统一去 config.py 里改。
# ============================================================
from config import DATA_ROOT, MODEL_PROJECT_ROOT

PYTHON_EXE = sys.executable

# 这里表示模型项目根目录，例如：
#   G:/CBCTtoCT
# 以后如果 model_cstgan / model_attn_vit 整体搬家，
# 不要改本文件，去改 config.py 里的 MODEL_PROJECT_ROOT。
CWD = MODEL_PROJECT_ROOT


def prepare_dataset(data_root: Path, dataset_name: str):
    """
    临时把 testA_xxx / testB_xxx / masks_test_xxx
    改名为 testA / testB / masks_test
    """
    rename_map = []
    suffixes = ["testA", "testB", "masks_test"]

    for prefix in suffixes:
        src = data_root / f"{prefix}_{dataset_name}"
        dst = data_root / prefix

        if not src.exists():
            raise RuntimeError(f"数据集缺失: {src} 不存在。")

        if dst.exists():
            backup = data_root / f"{dst.name}_backup"
            if backup.exists():
                raise RuntimeError(f"备份目录已存在，请先清理: {backup}")
            dst.rename(backup)
            rename_map.append((backup, dst))

        src.rename(dst)
        rename_map.append((dst, src))

    return rename_map


def restore_dataset(rename_map):
    for a, b in reversed(rename_map):
        if a.exists():
            a.rename(b)


def _safe_rename(src: Path, dst: Path):
    if not src.exists():
        raise RuntimeError(f"待重命名文件不存在: {src}")
    if dst.exists():
        raise RuntimeError(f"目标已存在，避免覆盖: {dst}")
    src.rename(dst)


def switch_models_for_run(model_dir_path: Path, model_dir: str, model_kind: str):
    """
    按你原来的规则做模型文件切换。
    这里只迁移原 server.py 里真正的推断工具逻辑，不含 Flask。
    """
    models_dir = model_dir_path / "models"
    restore_plan = []

    if model_dir == "model_cstgan" and model_kind == "cstgan_c":
        cg = models_dir / "cycle_gan_model.py"
        cg_backup = models_dir / "cycle_gan_model_backup.py"
        cg_with = models_dir / "cycle_gan_model_cstganwithmask.py"

        net = models_dir / "networks.py"
        net_backup = models_dir / "networks_backup.py"
        net_with = models_dir / "networks_cstganwithmask.py"

        _safe_rename(cg, cg_backup)
        _safe_rename(cg_with, cg)
        _safe_rename(net, net_backup)
        _safe_rename(net_with, net)

        restore_plan = [
            (models_dir / "networks.py", models_dir / "networks_cstganwithmask.py"),
            (models_dir / "networks_backup.py", models_dir / "networks.py"),
            (models_dir / "cycle_gan_model.py", models_dir / "cycle_gan_model_cstganwithmask.py"),
            (models_dir / "cycle_gan_model_backup.py", models_dir / "cycle_gan_model.py"),
        ]

    elif model_dir == "model_attn_vit" and model_kind == "attn":
        cg = models_dir / "cycle_gan_model.py"
        cg_backup = models_dir / "cycle_gan_model_backup.py"
        cg_attn = models_dir / "cycle_gan_model_attn.py"

        _safe_rename(cg, cg_backup)
        _safe_rename(cg_attn, cg)

        restore_plan = [
            (models_dir / "cycle_gan_model.py", models_dir / "cycle_gan_model_attn.py"),
            (models_dir / "cycle_gan_model_backup.py", models_dir / "cycle_gan_model.py"),
        ]

    return restore_plan


def restore_models_after_run(restore_plan):
    for src, dst in restore_plan:
        if not src.exists():
            raise RuntimeError(f"恢复失败：缺少 {src}")
        if dst.exists():
            raise RuntimeError(f"恢复失败：目标已存在，避免覆盖 {dst}")
        src.rename(dst)


def build_command(model_dir_path: Path, model_dir: str, model_kind: str, dataroot: Path, gpu_ids: str):
    if model_dir == "model_cstgan":
        name_arg = model_kind
        return [
            PYTHON_EXE, "test.py",
            "--dataroot", str(dataroot),
            "--name", name_arg,
            "--model", "cycle_gan",
            "--input_nc", "1", "--output_nc", "1",
            "--netG", "swin",
            "--direction", "BtoA",
            "--gpu_ids", gpu_ids,
        ]

    if model_dir == "model_attn_vit":
        if model_kind == "vit-unet":
            name_arg, netg_arg = "cycle_vit1", "vit-unet"
        elif model_kind == "attn":
            name_arg, netg_arg = "cycle_attn", "attn"
        else:
            raise RuntimeError(f"不支持的模型类型：{model_kind}")

        return [
            PYTHON_EXE, "test.py",
            "--dataroot", str(dataroot),
            "--name", name_arg,
            "--model", "cycle_gan",
            "--input_nc", "1", "--output_nc", "1",
            "--netG", netg_arg,
            "--direction", "BtoA",
            "--gpu_ids", gpu_ids,
        ]

    if model_dir == "model_mask":
        if model_kind != "0106":
            raise RuntimeError("model_mask 仅支持模型类型 0106")

        return [
            PYTHON_EXE, "test.py",
            "--dataroot", str(dataroot),
            "--name", "cycle_gan_0106",
            "--model", "cycle_gan",
            "--input_nc", "1", "--output_nc", "1",
            "--netG", "resnet_9blocks",
            "--direction", "BtoA",
            "--gpu_ids", gpu_ids,
        ]

    raise RuntimeError(f"不支持的模型目录：{model_dir}")


def run_inference_once(model_dir: str, model_kind: str, dataset_name: str, gpu_ids: str = "0"):
    data_root = DATA_ROOT
    model_dir_path = CWD / model_dir

    rename_map = []
    restore_plan = []
    logs = []
    cmd = []
    returncode = -1

    try:
        logs.append("[阶段1] 正在重命名数据集...")
        rename_map = prepare_dataset(data_root, dataset_name)
        logs.append(f"✔ 数据集 {dataset_name} 已重命名为标准 testA/testB/masks_test")

        logs.append("[阶段2] 切换模型文件...")
        restore_plan = switch_models_for_run(model_dir_path, model_dir, model_kind)
        logs.append(f"✔ 已切换至模型类型: {model_kind}")

        logs.append("[阶段3] 构建推理命令...")
        cmd = build_command(model_dir_path, model_dir, model_kind, data_root, gpu_ids)
        logs.append("CMD: " + " ".join(cmd))

        logs.append("[阶段4] 执行推理中...")
        proc = subprocess.run(
            cmd,
            cwd=model_dir_path,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="ignore",
        )
        if proc.stdout:
            logs.append(proc.stdout.rstrip("\n"))
        returncode = proc.returncode

    finally:
        logs.append("[阶段5] 恢复文件状态...")
        try:
            if restore_plan:
                restore_models_after_run(restore_plan)
                logs.append("✔ 模型文件已恢复。")
        except Exception as e:
            logs.append(f"⚠ 模型恢复失败: {e}")

        try:
            if rename_map:
                restore_dataset(rename_map)
                logs.append("✔ 数据集文件夹已恢复。")
        except Exception as e:
            logs.append(f"⚠ 数据集恢复失败: {e}")

    return {
        "cmd": " ".join(cmd),
        "stdout": "\n".join(logs),
        "returncode": returncode,
    }


def stream_inference_run(model_dir: str, model_kind: str, dataset_name: str, gpu_ids: str = "0"):
    data_root = DATA_ROOT
    model_dir_path = CWD / model_dir

    rename_map = []
    restore_plan = []

    try:
        print("[阶段1] 正在重命名数据集...", flush=True)
        rename_map = prepare_dataset(data_root, dataset_name)
        print(f"✔ 数据集 {dataset_name} 已重命名为标准 testA/testB/masks_test", flush=True)

        print("[阶段2] 切换模型文件...", flush=True)
        restore_plan = switch_models_for_run(model_dir_path, model_dir, model_kind)
        print(f"✔ 已切换至模型类型: {model_kind}", flush=True)

        print("[阶段3] 构建推理命令...", flush=True)
        cmd = build_command(model_dir_path, model_dir, model_kind, data_root, gpu_ids)
        print("CMD: " + " ".join(cmd), flush=True)

        print("[阶段4] 执行推理中...", flush=True)
        with subprocess.Popen(
            cmd,
            cwd=model_dir_path,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            encoding="utf-8",
            errors="ignore",
        ) as p:
            for line in p.stdout or []:
                print(line.rstrip(), flush=True)
            p.wait()

    except Exception as e:
        print(f"❌ 错误: {e}", flush=True)

    finally:
        print("[阶段5] 恢复文件状态...", flush=True)
        try:
            if restore_plan:
                restore_models_after_run(restore_plan)
                print("✔ 模型文件已恢复。", flush=True)
        except Exception as e:
            print(f"⚠ 模型恢复失败: {e}", flush=True)

        try:
            if rename_map:
                restore_dataset(rename_map)
                print("✔ 数据集文件夹已恢复。", flush=True)
        except Exception as e:
            print(f"⚠ 数据集恢复失败: {e}", flush=True)

        print("__DONE__", flush=True)