import os.path
from data.base_dataset import BaseDataset, get_transform
from data.image_folder import make_dataset
from PIL import Image
import random
import pydicom
import torch
import numpy as np
from skimage.transform import resize
from scipy.ndimage import rotate
class UnalignedDataset(BaseDataset):
    """
    This dataset class can load unaligned/unpaired datasets.

    It requires two directories to host training images from domain A '/path/to/data/trainA'
    and from domain B '/path/to/data/trainB' respectively.
    You can train the model with the dataset flag '--dataroot /path/to/data'.
    Similarly, you need to prepare two directories:
    '/path/to/data/testA' and '/path/to/data/testB' during test time.
    """

    def __init__(self, opt):
        """Initialize this dataset class.

        Parameters:
            opt (Option class) -- stores all the experiment flags; needs to be a subclass of BaseOptions
        """
        BaseDataset.__init__(self, opt)
        if opt.phase == 'train':
            self.dir_A = os.path.join(opt.dataroot, opt.phase + 'A')  # create a path '/path/to/data/trainA'
            self.dir_B = os.path.join(opt.dataroot, opt.phase + 'B')  # create a path '/path/to/data/trainB'
            self.mask = os.path.join(opt.dataroot, 'masks')

            self.A_paths = sorted(make_dataset(self.dir_A, opt.max_dataset_size))   # load images from '/path/to/data/trainA'
            self.B_paths = sorted(make_dataset(self.dir_B, opt.max_dataset_size))    # load images from '/path/to/data/trainB'
            self.mask_paths = sorted(make_dataset(self.mask, opt.max_dataset_size))
            self.A_size = len(self.A_paths)  # get the size of dataset A
            self.B_size = len(self.B_paths)  # get the size of dataset B
        else:
            self.dir_A = os.path.join(opt.dataroot, opt.phase + 'A')  # create a path '/path/to/data/trainA'
            self.dir_B = os.path.join(opt.dataroot, opt.phase + 'B')  # create a path '/path/to/data/trainB'
            self.mask = os.path.join(opt.dataroot, 'masks_test')

            self.A_paths = sorted(make_dataset(self.dir_A, opt.max_dataset_size))   # load images from '/path/to/data/trainA'
            self.B_paths = sorted(make_dataset(self.dir_B, opt.max_dataset_size))    # load images from '/path/to/data/trainB'
            self.mask_paths = sorted(make_dataset(self.mask, opt.max_dataset_size))
            self.A_size = len(self.A_paths)  # get the size of dataset A
            self.B_size = len(self.B_paths)  # get the size of dataset B

        btoA = self.opt.direction == 'BtoA'
        input_nc = self.opt.output_nc if btoA else self.opt.input_nc       # get the number of channels of input image
        output_nc = self.opt.input_nc if btoA else self.opt.output_nc      # get the number of channels of output image
        self.status = opt.phase
        self.transform_A = get_transform(self.opt, grayscale=(input_nc == 1))
        self.transform_B = get_transform(self.opt, grayscale=(output_nc == 1))

    def __getitem__(self, index):
        """Return a data point and its metadata information.

        Parameters:
            index (int)      -- a random integer for data indexing

        Returns a dictionary that contains A, B, A_paths and B_paths
            A (tensor)       -- an image in the input domain
            B (tensor)       -- its corresponding image in the target domain
            A_paths (str)    -- image paths
            B_paths (str)    -- image paths
        """
        if self.status=='test':
            A_path = self.A_paths[index]
            B_path = self.B_paths[index]
            mask_path = self.mask_paths[index]
        else:

            A_path = self.A_paths[index % self.A_size]  # make sure index is within then range
            if self.opt.serial_batches:   # make sure index is within then range
                index_B = index % self.B_size
            else:   # randomize the index for domain B to avoid fixed pairs.
                index_B = random.randint(0, self.B_size - 1)
            B_path = self.B_paths[index_B]
            mask_path = self.mask_paths[index % self.A_size]
    


        # A_img = Image.open(A_path).convert('RGB')
        # B_img = Image.open(B_path).convert('RGB')
        

        
        #apply image transformation
        A_img = np.fromfile(A_path,dtype='float32')
        B_img = np.fromfile(B_path,dtype='float32')
        mask_img = np.fromfile(mask_path,dtype='float32')
        # A_img = A_img + 1000.0
        # B_img = B_img + 1000.0

        input_size = 512
        output_size = 512

        A_img = np.reshape(A_img,(1,output_size,output_size))
        B_img = np.reshape(B_img,(1,output_size,output_size))
        mask_img = np.reshape(mask_img,(1,input_size, input_size))

        # print("CTxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx:",A_img.max(),A_img.min()) #1746.0 -1024.0
        # print("CTxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx:",B_img.max(),B_img.min()) 
        B_img = np.clip(B_img, -1000, 3000)
        min_val_B = -1000#B_img.min()
        max_val_B = 3000#B_img.max()
        B_img = (B_img - min_val_B) / (max_val_B - min_val_B) * 2 - 1
        A_img = np.clip(A_img, -1024, 3071)
        # print(min_val_B, max_val_B)
        min_val_A = -1024#A_img.min()
        max_val_A = 3071#A_img.max()
        A_img = (A_img - min_val_A) / (max_val_A - min_val_A) * 2 - 1

        # A_img = (A_img-1000.0)/1000.0
        # B_img = (B_img-1000.0)/1000.0
        # print(A_img.min(),A_img.max(), B_img.min(),B_img.max())
        if self.opt.phase == 'train':
            rotation_angle = random.uniform(-3, 3)
            A_img = rotate(A_img, angle=rotation_angle, axes=(1, 2), reshape=False, mode='nearest')
            B_img = rotate(B_img, angle=rotation_angle, axes=(1, 2), reshape=False, mode='nearest')
            mask_img = rotate(mask_img, angle=rotation_angle, axes=(1, 2), reshape=False, mode='nearest')
            mask_img = (mask_img >= 0.5).astype(np.int32)
            # translation
            row_offset = random.randint(-10, 10)
            col_offset = random.randint(-10, 10)
            start_row = 128 + row_offset
            end_row = start_row + 256
            start_col = 128 + col_offset
            end_col = start_col + 256
            A = torch.from_numpy(A_img[:, start_row:end_row, start_col:end_col])
            B = torch.from_numpy(B_img[:, start_row:end_row, start_col:end_col])
            mask_img = torch.from_numpy(mask_img[:, start_row:end_row, start_col:end_col])
        else:
            A = torch.from_numpy(A_img[:,128:384,128:384])
            B = torch.from_numpy(B_img[:,128:384,128:384])
            mask_img = torch.from_numpy(mask_img[:,128:384,128:384])
        ####### for test phase ####### 
        # A = torch.from_numpy(A_img[:,128:384,128:384])
        # B = torch.from_numpy(B_img[:,128:384,128:384])
         ###### for test phase ####### 
        # A = self.transform_A(A_img)
        # B = self.transform_B(B_img)
        # if self.opt.isTrain:
        #     return {'A': A, 'B': B, 'A_paths': A_path, 'B_paths': B_path}
        # else:
        return {
            'A': A,
            'B': B,
            'mask_img':mask_img,
            'A_paths': A_path,
            'B_paths': B_path,
            'min_val_A': min_val_A,
            'max_val_A': max_val_A,
            'min_val_B': min_val_B,
            'max_val_B': max_val_B,
            'mask_paths': mask_path
        }

    def __len__(self):
        """Return the total number of images in the dataset.

        As we have two datasets with potentially different number of images,
        we take a maximum of
        """
        return max(self.A_size, self.B_size)
