import os, glob
import numpy as np
import torch
from tqdm import tqdm
from options.test_options import TestOptions
from models import create_model
from PIL import Image
import sys, importlib

def use_cstgan_model():
    import models.cycle_gan_model_cstganwithmask as cmodel
    import models.networks_cstganwithmask as cnet
    sys.modules['models.cycle_gan_model'] = cmodel
    sys.modules['models.networks'] = cnet

def preprocess_cbct_unaligned(path, dtype=np.float32):
    """完全复刻 unaligned_dataset.py 中 B_img 的处理逻辑"""
    input_size = 512
    crop_start, crop_end = 128, 384
    data = np.fromfile(path, dtype=dtype)
    data = np.reshape(data, (1, input_size, input_size))
    data = np.clip(data, -1000, 3000)
    data = (data - (-1000)) / (3000 - (-1000)) * 2 - 1
    data = data[:, crop_start:crop_end, crop_start:crop_end]
    tensor = torch.from_numpy(data).unsqueeze(0)  # [1,1,256,256]
    return tensor

def save_raw(array, path):
    array.astype(np.float32).tofile(path)

if __name__ == '__main__':
    opt = TestOptions().parse()

    if 'cstgan_c' in opt.checkpoints_dir or 'cstgan_c' in opt.name:
        use_cstgan_model()
        print("Using CSTGAN-with-mask model definitions.")
    opt.num_threads = 0
    opt.batch_size = 1
    opt.serial_batches = True
    opt.no_flip = True
    opt.display_id = -1
    opt.model = "cycle_gan_infer"

    model = create_model(opt)
    model.setup(opt)
    model.eval()

    testB_dir = os.path.join(opt.dataroot, 'testB')
    results_dir = os.path.join(opt.results_dir, opt.name, 'images')
    os.makedirs(results_dir, exist_ok=True)

    cbct_files = sorted(glob.glob(os.path.join(testB_dir, '*.raw')))
    print(f"Found {len(cbct_files)} CBCT files in {testB_dir}")

    for cbct_path in tqdm(cbct_files):
        fname = os.path.basename(cbct_path)
        cbct_tensor = preprocess_cbct_unaligned(cbct_path)

        data = {'B': cbct_tensor, 'B_paths': cbct_path}
        model.set_input(data)
        model.test()

        visuals = model.get_current_visuals()
        fake_A = visuals['fake_A']
        if isinstance(fake_A, torch.Tensor):
            fake_A = fake_A.detach().cpu().numpy()
        elif isinstance(fake_A, dict):
            # 有时 fake_A 是 dict，例如 {'fake_A': tensor}
            for v in fake_A.values():
                if isinstance(v, torch.Tensor):
                    fake_A = v.detach().cpu().numpy()
                    break

        # 保证最终是 numpy 数组
        if isinstance(fake_A, np.ndarray) and fake_A.ndim == 4:
            fake_A = fake_A[0, 0]
        elif isinstance(fake_A, np.ndarray) and fake_A.ndim == 3:
            fake_A = fake_A[0]


        # 保存 RAW
        raw_out = os.path.join(results_dir, fname)
        save_raw(fake_A, raw_out)

        # 同时生成 PNG 预览
        vis = fake_A
        vmin, vmax = np.percentile(vis, 1), np.percentile(vis, 99)
        vis = np.clip(vis, vmin, vmax)
        vis = (vis - vis.min()) / (vis.max() - vis.min() + 1e-6)
        png_out = os.path.join(results_dir, fname.replace('.raw', '.png'))
        Image.fromarray((vis * 255).astype(np.uint8)).save(png_out)

        print(f"Saved: {raw_out} / {png_out}")

    print("All testB images processed.")
