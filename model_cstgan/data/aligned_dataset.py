import os.path
from data.base_dataset import BaseDataset, get_params, get_transform
from data.image_folder import make_dataset
from PIL import Image
import pydicom
import numpy as np
import torch
import cv2
import scipy.io
import scipy.ndimage 
import numpy.random

def create_circular_mask(h, w, center=None, radius=None):

    if center is None: # use the middle of the image
        center = (int(w/2), int(h/2))
    if radius is None: # use the smallest distance between the center and image walls
        radius = min(center[0], center[1], w-center[0], h-center[1])

    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - center[0])**2 + (Y-center[1])**2)

    mask = dist_from_center <= radius
    return mask
maskcir = create_circular_mask(256,256)

class AlignedDataset(BaseDataset):
    """A dataset class for paired image dataset.

    It assumes that the directory '/path/to/data/train' contains image pairs in the form of {A,B}.
    During test time, you need to prepare a directory '/path/to/data/test'.
    """

    def __init__(self, opt):
        """Initialize this dataset class.

        Parameters:
            opt (Option class) -- stores all the experiment flags; needs to be a subclass of BaseOptions
        """
        BaseDataset.__init__(self, opt)
        #self.dir_AB = os.path.join(opt.dataroot, opt.phase)  # get the image directory
        if opt.phase == 'train':
            self.dir_A = os.path.join(opt.dataroot, 'trainA')
            self.dir_B = os.path.join(opt.dataroot, 'trainB')
            #self.mask = os.path.join(opt.dataroot, 'masks')



            #self.AB_paths = sorted(make_dataset(self.dir_AB, opt.max_dataset_size))  # get image paths
            self.A_paths = sorted(make_dataset(self.dir_A, opt.max_dataset_size))
            self.B_paths = sorted(make_dataset(self.dir_B, opt.max_dataset_size))
            #self.mask_paths = sorted(make_dataset(self.mask, opt.max_dataset_size))

            self.A_size = len(self.A_paths)  # get the size of dataset A
            self.B_size = len(self.B_paths)  # get the size of dataset B

        else:
            self.dir_A = os.path.join(opt.dataroot, 'testA')
            self.dir_B = os.path.join(opt.dataroot, 'testB')
            #self.mask = os.path.join(opt.dataroot, 'masks_test')

            self.A_paths = sorted(make_dataset(self.dir_A, opt.max_dataset_size))
            self.B_paths = sorted(make_dataset(self.dir_B, opt.max_dataset_size))
            #self.mask_paths = sorted(make_dataset(self.mask, opt.max_dataset_size))


        assert(self.opt.load_size >= self.opt.crop_size)   # crop_size should be smaller than the size of loaded image
        self.input_nc = self.opt.output_nc if self.opt.direction == 'BtoA' else self.opt.input_nc
        self.output_nc = self.opt.input_nc if self.opt.direction == 'BtoA' else self.opt.output_nc
        self.status = opt.phase
    def __getitem__(self, index):
        """Return a data point and its metadata information.

        Parameters:
            index - - a random integer for data indexing

        Returns a dictionary that contains A, B, A_paths and B_paths
            A (tensor) - - an image in the input domain
            B (tensor) - - its corresponding image in the target domain
            A_paths (str) - - image paths
            B_paths (str) - - image paths (same as A_paths)
        """
        # read a image given a random integer index
        #AB_path = self.AB_paths[index]
        if self.status=='test':
            A_path = self.A_paths[index]
            B_path = self.B_paths[index]
            #mask_path = self.mask_paths[0]
        else:
            A_path = self.A_paths[index % self.A_size]
            B_path = self.B_paths[index % self.A_size]
            #mask_path = self.mask_paths[0]


        #train
        #A_img = scipy.io.loadmat(A_path)['imgData']
        #B_img = scipy.io.loadmat(B_path)['FDK']
        #mask_img = scipy.io.loadmat(mask_path)['ptv']
        #test
        A_img = np.fromfile(A_path,dtype='float32')
        B_img = np.fromfile(B_path,dtype='float32')
        #mask_img = scipy.io.loadmat(mask_path)['ptv']





        #edited 02/18/21
        
        # input_size = 512
        # output_size = 512

        # transform_params = get_params(self.opt, (input_size,output_size))
        # transform = get_transform(self.opt, transform_params, grayscale=(self.input_nc == 1))

        
        # A_img = transform(A_img)
        # B_img = transform(B_img)
        # mask_img = transform(mask_img)

#################################################

        input_size = 512
        output_size = 512
        # #train
        # #patient 107 40:60
        # #patient 108 48:64
        # #patient 111 35:55
        # #patient 109 55:91

        # ind = numpy.random.randint(55,high=91)
        # A_img = np.reshape(A_img,(1, input_size, input_size,96))
        # B_img = np.reshape(B_img,(1,input_size, input_size,96))
        # mask_img = np.reshape(mask_img,(1,input_size, input_size,96))


        # #scale CBCT B_img to (0,2000)
        # #patient 109
        # B_img[:,:,:,55:91] = (B_img[:,:,:,55:91] - np.min(B_img[:,:,:,55:91])) / (np.max(B_img[:,:,:,55:91]) - np.min(B_img[:,:,:,55:91]))
        # B_img = B_img*2000


        # # #scale CBCT B_img to (0,2000)

        # # B_img = (B_img - np.min(B_img)) / (np.max(B_img) - np.min(B_img))
        # # B_img = B_img*2000

        # #mask_img = np.reshape(mask_img,(96, input_size, input_size))

        # A_img = (A_img - 1000.0) / 1000.0
        # B_img = (B_img - 1000.0) / 1000.0

        # A_img = np.moveaxis(A_img,-1,1)
        # B_img = np.moveaxis(B_img,-1,1)
        # mask_img = np.moveaxis(mask_img,-1,1)

        # A_img = maskcir*A_img
        # B_img = maskcir*B_img


        # #train
        
        # A = torch.Tensor(A_img[:,ind,:,:])
        # B = torch.Tensor(B_img[:,ind,:,:])
        # mask_img = scipy.ndimage.shift(mask_img[:, 17,:,:],[0, 10,20])
        # mask_img = torch.Tensor(mask_img)
        

        #test
        input_size = 512
        output_size = 512



        A_img = np.reshape(A_img,(1, input_size, input_size))
        B_img = np.reshape(B_img,(1,input_size, input_size))
        #mask_img = np.reshape(mask_img,(1,input_size, input_size,np.shape(mask_img)[2]))

        #scale CBCT B_img to (0,2000)

        #B_img = (B_img - np.min(B_img)) / (np.max(B_img) - np.min(B_img))
        #B_img = B_img*2000

        #mask_img = np.reshape(mask_img,(96, input_size, input_size))

        A_img = A_img / 1000.0
        B_img = B_img / 1000.0
        #A_img = np.moveaxis(A_img,-1,1)
        #B_img = np.moveaxis(B_img,-1,1)
        #mask_img = np.moveaxis(mask_img,-1,1)

        #A_img = maskcir*A_img
        #B_img = maskcir*B_img


        A = torch.Tensor(A_img)
        B = torch.Tensor(B_img)
        #mask_img = scipy.ndimage.shift(mask_img[:, 17,:,:],[0, 10,20])
        #mask_img = torch.Tensor(mask_img)

        return {'A': A, 'B': B,  'A_paths': A_path, 'B_paths': B_path}#'mask_img':mask_img,, 'mask_paths': mask_path

    def __len__(self):
        """Return the total number of images in the dataset."""
        return len(self.A_paths)
