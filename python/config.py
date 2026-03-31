from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

PYTHON_ROOT = Path(__file__).resolve().parent
SPRING_PROJECT_ROOT = PYTHON_ROOT.parent

# ============================================================
# 路径如果变了，优先改这个文件。
# 不要去 inference / merge / dicom 业务脚本里找硬编码路径。
# ============================================================


def _resolve_path(value: str | None, default: str | Path) -> Path:
    raw = value.strip() if isinstance(value, str) else ""
    if raw:
        return Path(raw).expanduser().resolve()
    if isinstance(default, Path):
        return default.expanduser().resolve()
    return (SPRING_PROJECT_ROOT / default).resolve()


# ============================================================
# 【老项目目录：只借用 model 和 Data】
# ============================================================
LEGACY_CBCT_ROOT = _resolve_path(
    os.getenv("LEGACY_CBCT_ROOT"),
    r"G:\CBCTtoCT"
)

# 模型目录根，例如 G:\CBCTtoCT
MODEL_PROJECT_ROOT = _resolve_path(
    os.getenv("MODEL_PROJECT_ROOT"),
    LEGACY_CBCT_ROOT
)

# 推断数据目录，例如 G:\CBCTtoCT\Data
DATA_ROOT = _resolve_path(
    os.getenv("DATA_ROOT"),
    LEGACY_CBCT_ROOT / "Data"
)


# ============================================================
# 【原始 raw 来源】
# process_pipeline.py 会按：
#   RAW_ROOT / raw_relpath
# 找原始 interpolated_CBCT_b_spline.raw
# 当前你确认来源是：
#   F:\mimi0209\output
# ============================================================
RAW_ROOT = _resolve_path(
    os.getenv("RAW_ROOT"),
    r"F:\mimi0209\output"
)


# ============================================================
# 【Spring 自己的工作目录】
# 除了 model 和 data，其余尽量都放这里
# ============================================================
WORKSPACE_ROOT = _resolve_path(
    os.getenv("WORKSPACE_ROOT"),
    SPRING_PROJECT_ROOT / "workspace"
)

# merge 后的 3D raw、复制出来的原始 raw，都放这里
TEST_PATIENT_ROOT = _resolve_path(
    os.getenv("TEST_PATIENT_ROOT"),
    WORKSPACE_ROOT / "TestPatient"
)

# pipeline 中间文件目录，最后会清理
TMP_DIR = _resolve_path(
    os.getenv("TMP_DIR"),
    WORKSPACE_ROOT / "tmp"
)


# ============================================================
# 【DICOM 相关】
# ============================================================
# 原始 DICOM 来源根目录
# process_pipeline.py 会按：
#   DICOM_ROOT / dicom_relpath
# 去找原始 DICOM 文件夹
DICOM_ROOT = _resolve_path(
    os.getenv("DICOM_ROOT"),
    r"F:\mimi0209\HeadNeck-selected"
)

RESULTS_BASE = _resolve_path(
    os.getenv("DICOM_RESULTS_DIR"),
    SPRING_PROJECT_ROOT / "DICOM_results"
)

PIPELINE_PATH = _resolve_path(
    os.getenv("PROCESS_PIPELINE_SCRIPT"),
    PYTHON_ROOT / "process_pipeline.py"
)

EXTRACT_MERGE_SCRIPT = _resolve_path(
    os.getenv("EXTRACT_MERGE_SCRIPT"),
    PYTHON_ROOT / "extract_and_merge.py"
)

PARAM_PATH = _resolve_path(
    os.getenv("PATIENT_PARAM_PATH"),
    PYTHON_ROOT / "patient_params.json"
)

UID_PATH = _resolve_path(
    os.getenv("PATIENT_UID_PATH"),
    PYTHON_ROOT / "Patient_rename.json"
)

# 兼容旧代码，后续可删除
PROJECT_ROOT = SPRING_PROJECT_ROOT