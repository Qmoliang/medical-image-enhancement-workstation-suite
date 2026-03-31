import os, shutil, subprocess
from pathlib import Path
import numpy as np
import streamlit as st
import torch
from PIL import Image

st.set_page_config(page_title="CBCT→CT Demo", layout="wide")
st.title("CBCT → CT (CycleGAN) Demo")
st.caption("上传 CBCT.raw 与 Mask.raw，自动创建 testB/masks_test，并运行模型。")

# ========== Sidebar 参数 ==========
st.sidebar.header("路径与参数")
data_root = Path(st.sidebar.text_input("输入文件夹 (--dataroot)", "./demo"))
output_dir = Path(st.sidebar.text_input("输出文件夹 (--results_dir)", "./results_demo"))
exp_name = st.sidebar.text_input("实验名称 (--name)", "mb_taylor")
gpu_ids = st.sidebar.text_input("GPU IDs (--gpu_ids)", "0")
dtype_opt = st.sidebar.selectbox("RAW 数据类型", ("float32", "uint16", "int16", "uint8"), index=0)

# ========== 上传区域 ==========
col1, col2 = st.columns(2)
with col1:
    cbct_file = st.file_uploader("上传 CBCT `.raw` 文件", type=["raw"], key="cbct")
with col2:
    mask_file = st.file_uploader("上传 Mask `.raw` 文件", type=["raw"], key="mask")

# ========== 工具函数 ==========
def load_raw_preview(raw_bytes, dtype):
    n = len(raw_bytes)
    dtype_size = np.dtype(dtype).itemsize
    pixels = n // dtype_size
    side = int(np.sqrt(pixels))
    arr = np.frombuffer(raw_bytes, dtype=dtype, count=side * side).reshape(side, side)
    return arr

def normalize_gray(arr):
    arr = arr.astype(np.float32)
    low, high = np.percentile(arr, 1), np.percentile(arr, 99)
    arr = np.clip((arr - low) / (high - low + 1e-6), 0, 1)
    return arr

def tensor2im(image_tensor, min_val=None, max_val=None):
    """将网络输出从[-1,1]映射回原始值域"""
    if not isinstance(image_tensor, np.ndarray):
        if isinstance(image_tensor, torch.Tensor):
            image_numpy = image_tensor[0].cpu().float().numpy()
        else:
            return image_tensor
        if isinstance(min_val, torch.Tensor):
            min_val = min_val.cpu().numpy()
        if isinstance(max_val, torch.Tensor):
            max_val = max_val.cpu().numpy()
        if min_val is not None and max_val is not None:
            image_numpy = (image_numpy + 1) / 2 * (max_val - min_val) + min_val
    else:
        image_numpy = image_tensor
    return image_numpy

def apply_window_level(arr, window, level):
    arr = np.asarray(arr).astype(np.float32)
    vmin, vmax = float(arr.min()), float(arr.max())
    if vmax <= 2 and vmin >= -1:
        arr = arr * 1000  # 将[-1,1]映射到HU尺度近似范围
    low = level - window / 2.0
    high = level + window / 2.0
    out = np.clip(arr, low, high)
    out = (out - low) / (high - low + 1e-6)
    return np.clip(out, 0.0, 1.0)

def overlay_mask(cbct, mask):
    mask_bin = (mask > 0.5).astype(np.float32)
    rgb = np.stack([cbct, cbct, cbct], axis=-1)
    rgb[..., 0] = np.maximum(rgb[..., 0], mask_bin)
    return rgb

def crop_center_256(arr):
    """完全复刻 test_simple 的裁剪逻辑：取中心 256x256"""
    h, w = arr.shape
    crop_start, crop_end = 128, 384
    if h >= 384 and w >= 384:
        return arr[crop_start:crop_end, crop_start:crop_end]
    else:
        start_h = max((h - 256)//2, 0)
        start_w = max((w - 256)//2, 0)
        return arr[start_h:start_h+256, start_w:start_w+256]

# ========== 上传后读取图像 ==========
cbct_arr, mask_arr = None, None
if cbct_file:
    cbct_arr = load_raw_preview(cbct_file.getvalue(), dtype_opt)
    st.session_state["cbct_min"] = float(cbct_arr.min())
    st.session_state["cbct_max"] = float(cbct_arr.max())

if mask_file:
    mask_arr = load_raw_preview(mask_file.getvalue(), dtype_opt)

# ========== 左右显示 ==========
if cbct_arr is not None and mask_arr is not None:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.image(normalize_gray(cbct_arr), caption=f"CBCT 预览 ({cbct_arr.shape[0]}×{cbct_arr.shape[1]})",
                 use_container_width=True, clamp=True)
    with c2:
        st.image(mask_arr, caption="Mask 预览", use_container_width=True, clamp=True)
    st.image(overlay_mask(normalize_gray(cbct_arr), mask_arr > 0.5), caption="CBCT + Mask 叠加")

# ========== 运行推理 ==========
if st.button("运行推理", type="primary"):
    testB_dir = data_root / "testB"
    mask_dir = data_root / "masks_test"
    for d in [testB_dir, mask_dir]:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    cbct_path = testB_dir / (cbct_file.name if cbct_file else "cbct.raw")
    mask_path = mask_dir / (mask_file.name if mask_file else "mask.raw")
    cbct_path.write_bytes(cbct_file.getvalue())
    mask_path.write_bytes(mask_file.getvalue())

    cmd = (
        f"python test_simple.py "
        f"--dataroot {data_root} "
        f"--results_dir {output_dir} "
        f"--name {exp_name} "
        f"--model cycle_gan_infer "
        f"--input_nc 1 --output_nc 1 "
        f"--netG swin --direction BtoA --gpu_ids {gpu_ids}"
    )
    st.code(cmd, language="bash")

    with st.spinner("正在运行模型，请稍候..."):
        proc = subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    st.text_area("运行日志", proc.stdout, height=300)

    # 缓存推理结果
    raws = list(output_dir.rglob("*.raw"))
    if raws:
        st.session_state["gen_raws"] = [str(p) for p in raws]
        st.success("✅ 推理完成，结果已缓存。")

# ========== 如果已有结果，显示 ==========
if "gen_raws" in st.session_state:
    raws = [Path(p) for p in st.session_state["gen_raws"]]
    ww = st.number_input("窗宽 (Window)", value=1600.0, step=50.0)
    wl = st.number_input("窗位 (Level)", value=-400.0, step=10.0)

    p = sorted(raws)[0]
    arr = np.fromfile(p, dtype=np.float32)
    side = int(np.sqrt(len(arr)))
    img = arr.reshape(side, side)

    # 还原真实值域
    min_val = st.session_state.get("cbct_min", -1000.0)
    max_val = st.session_state.get("cbct_max", 3000.0)
    img_restored = tensor2im(torch.from_numpy(img).unsqueeze(0), min_val=min_val, max_val=max_val)

    # === 中心裁剪 ===
    cbct_crop = crop_center_256(cbct_arr)
    ct_crop = crop_center_256(img_restored)
    mask_crop = crop_center_256(mask_arr) if mask_arr is not None else None

    # === 应用 W/L ===
    cbct_show = apply_window_level(cbct_crop, ww, wl)
    ct_show = apply_window_level(ct_crop, ww, wl)

    # === 叠加图 ===
    if mask_crop is not None:
        overlay_cbct = overlay_mask(cbct_show, mask_crop)
        overlay_ct = overlay_mask(ct_show, mask_crop)
    else:
        overlay_cbct = cbct_show
        overlay_ct = ct_show

    # === 2x2 布局展示 ===
    col_top = st.columns(2)
    col_bottom = st.columns(2)

    with col_top[0]:
        st.image(cbct_show, caption=f"CBCT (W={ww:.1f}, L={wl:.1f})", clamp=True, use_container_width=True)
    with col_top[1]:
        st.image(ct_show, caption=f"生成 CT (W={ww:.1f}, L={wl:.1f})", clamp=True, use_container_width=True)

    with col_bottom[0]:
        st.image(overlay_cbct, caption="CBCT + Mask", clamp=True, use_container_width=True)
    with col_bottom[1]:
        st.image(overlay_ct, caption="生成 CT + Mask", clamp=True, use_container_width=True)
