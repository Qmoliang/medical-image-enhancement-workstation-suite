import torch
from .base_model import BaseModel
from . import networks
import six
import os
import cv2
import time
import SimpleITK as sitk
# import radiomics
# from radiomics import featureextractor
import numpy as np
from torch.nn import CrossEntropyLoss
import torch.nn.functional as F
# settings = {}
# settings['binWidth'] = 16
# extractor = featureextractor.RadiomicsFeatureExtractor(**settings)
# extractor.disableAllFeatures()
# extractor.enableFeaturesByName(firstorder=['Median'])

class Pix2PixModel(BaseModel):
    """ This class implements the pix2pix model, for learning a mapping from input images to output images given paired data.

    The model training requires '--dataset_mode aligned' dataset.
    By default, it uses a '--netG unet256' U-Net generator,
    a '--netD basic' discriminator (PatchGAN),
    and a '--gan_mode' vanilla GAN loss (the cross-entropy objective used in the orignal GAN paper).

    pix2pix paper: https://arxiv.org/pdf/1611.07004.pdf
    """
    @staticmethod
    def modify_commandline_options(parser, is_train=True):
        """Add new dataset-specific options, and rewrite default values for existing options.

        Parameters:
            parser          -- original option parser
            is_train (bool) -- whether training phase or test phase. You can use this flag to add training-specific or test-specific options.

        Returns:
            the modified parser.

        For pix2pix, we do not use image buffer
        The training objective is: GAN Loss + lambda_L1 * ||G(A)-B||_1
        By default, we use vanilla GAN loss, UNet with batchnorm, and aligned datasets.
        """
        # changing the default values to match the pix2pix paper (https://phillipi.github.io/pix2pix/)
        parser.set_defaults(norm='batch', netG='unet_256', dataset_mode='aligned')
        if is_train:
            parser.set_defaults(pool_size=0, gan_mode='vanilla')
            parser.add_argument('--lambda_L1', type=float, default=100.0, help='weight for L1 loss')

        return parser

    def __init__(self, opt):
        """Initialize the pix2pix class.

        Parameters:
            opt (Option class)-- stores all the experiment flags; needs to be a subclass of BaseOptions
        """
        BaseModel.__init__(self, opt)
        # specify the training losses you want to print out. The training/test scripts will call <BaseModel.get_current_losses>
        self.loss_names = ['G_GAN', 'G_L1', 'D_real', 'D_fake']
        # specify the images you want to save/display. The training/test scripts will call <BaseModel.get_current_visuals>
        self.visual_names = ['real_A', 'fake_B', 'real_B']
        # specify the models you want to save to the disk. The training/test scripts will call <BaseModel.save_networks> and <BaseModel.load_networks>
        if self.isTrain:
            self.model_names = ['G', 'D']
        else:  # during test time, only load G
            self.model_names = ['G']
        # define networks (both generator and discriminator)
        self.netG = networks.define_G(opt.input_nc, opt.output_nc, opt.ngf, opt.netG, opt.norm,
                                      not opt.no_dropout, opt.init_type, opt.init_gain, self.gpu_ids)

        if self.isTrain:  # define a discriminator; conditional GANs need to take both input and output images; Therefore, #channels for D is input_nc + output_nc
            self.netD = networks.define_D(opt.input_nc + opt.output_nc, opt.ndf, opt.netD,
                                          opt.n_layers_D, opt.norm, opt.init_type, opt.init_gain, self.gpu_ids)

        if self.isTrain:
            # define loss functions
            self.criterionGAN = networks.GANLoss(opt.gan_mode).to(self.device)
            self.criterionL1 = torch.nn.L1Loss()
            # initialize optimizers; schedulers will be automatically created by function <BaseModel.setup>.
            self.optimizer_G = torch.optim.Adam(self.netG.parameters(), lr=opt.lr, betas=(opt.beta1, 0.999))
            self.optimizer_D = torch.optim.Adam(self.netD.parameters(), lr=opt.lr, betas=(opt.beta1, 0.999))
            self.optimizers.append(self.optimizer_G)
            self.optimizers.append(self.optimizer_D)

    def set_input(self, input):
        """Unpack input data from the dataloader and perform necessary pre-processing steps.

        Parameters:
            input (dict): include the data itself and its metadata information.

        The option 'direction' can be used to swap images in domain A and domain B.
        """
        AtoB = self.opt.direction == 'AtoB'
        self.real_A = input['A' if AtoB else 'B'].to(self.device)
        self.real_B = input['B' if AtoB else 'A'].to(self.device)
        self.image_paths = input['A_paths' if AtoB else 'B_paths']

        #self.mask_img = input['mask_img'].to(self.device)
        ########################
        #self.real_A = self.real_A*self.mask_img
        #self.real_B = self.real_B*self.mask_img

    def forward(self):
        """Run forward pass; called by both functions <optimize_parameters> and <test>."""
        self.fake_B = self.netG(self.real_A)  # G(A)

    def backward_D(self):
        """Calculate GAN loss for the discriminator"""
        # Fake; stop backprop to the generator by detaching fake_B
        fake_AB = torch.cat((self.real_A, self.fake_B), 1)  # we use conditional GANs; we need to feed both input and output to the discriminator
        pred_fake = self.netD(fake_AB.detach())
        self.loss_D_fake = self.criterionGAN(pred_fake, False)
        # Real
        real_AB = torch.cat((self.real_A, self.real_B), 1)#*self.mask_img
        pred_real = self.netD(real_AB)
        self.loss_D_real = self.criterionGAN(pred_real, True)
        # combine loss and calculate gradients
        self.loss_D = (self.loss_D_fake + self.loss_D_real) * 0.5
        self.loss_D.backward()

    def backward_G(self):
        """Calculate GAN and L1 loss for the generator"""
        # First, G(A) should fake the discriminator
        fake_AB = torch.cat((self.real_A, self.fake_B), 1)#*self.mask_img
        pred_fake = self.netD(fake_AB)
        self.loss_G_GAN = self.criterionGAN(pred_fake, True)
        # Second, G(A) = B
        
        #self.loss_G_L1 = self.criterionL1(self.fake_B*self.mask_img, self.real_B*self.mask_img) * self.opt.lambda_L1
        self.loss_G_L1 = self.criterionL1(self.fake_B, self.real_B) * self.opt.lambda_L1
        #print("loss_g_l1:",self.loss_G_L1.shape)
        #print(self.loss_G_L1.dtype)
        #print(self.loss_G_L1)
        #print(self.loss_G_L1.requires_grad)
        #print(self.loss_G_L1.grad)
        #print("part1: calculate")
        lena_rot45_1 = self.fake_B.detach().to("cpu").numpy()
        #print(lena_rot45_1.shape)
        lena_rot45 = cv2.normalize(lena_rot45_1, None, 0, 255, cv2.NORM_MINMAX).astype('uint8')
        lena_rot45 = lena_rot45.reshape(512,512)
        original_lena_1 = self.real_B.detach().to("cpu").numpy()
        original_lena = cv2.normalize(original_lena_1, None, 0, 255, cv2.NORM_MINMAX).astype('uint8')
        original_lena = original_lena.reshape(512,512)
        sift = cv2.xfeatures2d.SIFT_create()
        (kp1, des1) = sift.detectAndCompute(original_lena, None)
        (kp2, des2) = sift.detectAndCompute(lena_rot45, None)
        start = time.time()     # calculate matching time
        bf = cv2.BFMatcher()
        matches1 = bf.knnMatch(des1, des2, k=2)
        #print('image matching No. of SIFT point:', len(matches1))
        matches = bf.match(des1,des2)
        matches = sorted(matches, key = lambda x:x.distance)
        ratio1 = 0.6
        good1 = []
        for m1, n1 in matches1:
        # If the ratio of the closest to the next is greater than a predetermined value, then we keep the closest value and consider the point that it matches with it as good_match
            if m1.distance < ratio1 * n1.distance:
                good1.append([m1])
        end = time.time()
        #print("matching time:%.4fs" % (end-start))
        #print(len(good1))
        if(len(good1)!=0):
            """ output = des2[good1[0][0].trainIdx,:]-des1[good1[0][0].queryIdx,:]
            for i in range(1,len(good1)):
                output += des2[good1[i][0].trainIdx,:]-des1[good1[i][0].queryIdx,:]
            result = np.mean(output)
            #x = np.ones(1)
            #x[0] = 10/abs(result)
            #print(x)
            #y = torch.from_numpy(x)
            loss_test = self.loss_G_L1.clone()
            #print(loss_test.requires_grad)
            loss_test =torch.tensor(abs(result), requires_grad=True).to(loss_test)
            #print("12345678",loss_test)
            #print(loss_test) """
            loss_test = torch.tensor([0.0]).requires_grad_().to(self.device)
            for j in range(len(good1)):
                for i in range(16):
                    loss_test1 = torch.tensor([0.0]).requires_grad_().to(self.device)
                    if(sum(des2[good1[j][0].trainIdx,8*i:8*(i+1)])!=0):
                        x2 = des2[good1[j][0].trainIdx,8*i:8*(i+1)]/sum(des2[good1[j][0].trainIdx,8*i:8*(i+1)])
                    else:
                        x2 = des2[good1[j][0].trainIdx,8*i:8*(i+1)]
                    if(sum(des1[good1[j][0].queryIdx,8*i:8*(i+1)])!=0):
                        y2 = des1[good1[j][0].queryIdx,8*i:8*(i+1)]/sum(des1[good1[j][0].queryIdx,8*i:8*(i+1)])
                    else:
                        y2 = des1[good1[j][0].queryIdx,8*i:8*(i+1)]
                    # if(sum(des2[good1[j][0].trainIdx,8*i:8*(i+1)])==0):
                    #     print(j,des2[good1[j][0].trainIdx,8*i:8*(i+1)])
            #        print(x2,y2)
                    x1 = torch.tensor(x2).to(self.device)
                    y1 = torch.tensor(y2).to(self.device)
                    t = F.kl_div(x1.softmax(dim=-1).log(), y1.softmax(dim=-1), reduction='sum')
                    loss_test1 += t
                loss_test += torch.div(loss_test1,16)
                # print (loss_test,j)
            loss_test = torch.div(loss_test1,len(good1))

            ############one try#################    
            # x1 = torch.tensor(des2[good1[0][0].trainIdx,64:80]).to(self.device)
            # y1 = torch.tensor(des1[good1[0][0].queryIdx,64:80]).to(self.device)
            # loss1 = self.criterionGAN(torch.tensor(des2[good1[0][0].trainIdx,:]).to(self.device), True)
            # loss2 = self.criterionGAN(torch.tensor(des1[good1[0][0].queryIdx,:]).to(self.device), True)
            # loss3 = F.binary_cross_entropy_with_logits(torch.tensor(des2[good1[0][0].trainIdx,:]).to(self.device),torch.tensor(des1[good1[0][0].queryIdx,:]).to(self.device))
            # loss4 = F.kl_div(x1.reshape(15,8).softmax(dim=-1).log(), y1.reshape(15,8).softmax(dim=-1), reduction='sum')
            # print("result: ", loss4)
            ###################################
            
        #ROI_fake_B = self.fake_B#*self.mask_img
        #ROI_real_B = self.real_B#*self.mask_img
        
        # median_loss = torch.median(ROI_fake_B[ROI_fake_B!=0])-torch.median(ROI_real_B[ROI_real_B!=0])
        

        #fake_B_kurtosis = torch.mean(torch.pow(((ROI_fake_B[ROI_fake_B!=0]-torch.mean(ROI_fake_B[ROI_fake_B!=0]))/(torch.std(ROI_fake_B[ROI_fake_B!=0])+1e-8)),4))
        #real_B_kurtosis = torch.mean(torch.pow(((ROI_real_B[ROI_real_B!=0]-torch.mean(ROI_real_B[ROI_real_B!=0]))/(torch.std(ROI_real_B[ROI_real_B!=0])+1e-8)),4))

        #kurtosis_loss = torch.abs(fake_B_kurtosis-real_B_kurtosis)
        
        # self.loss_G_L1 = torch.abs(median_loss)
        #print(real_B_kurtosis)
        
        
        # combine loss and calculate gradients
        #self.loss_G = self.loss_G_L1 + self.loss_G_L1_WB*0.1 + self.loss_G_GAN*0.1
        if(len(good1)==0):
            self.loss_G = self.loss_G_L1
        else:
            self.loss_G = self.loss_G_L1*0.2+loss_test*0.8
        self.loss_G.backward()

    def optimize_parameters(self):
        self.forward()                   # compute fake images: G(A)
        # update D
        self.set_requires_grad(self.netD, True)  # enable backprop for D
        self.optimizer_D.zero_grad()     # set D's gradients to zero
        self.backward_D()                # calculate gradients for D
        self.optimizer_D.step()          # update D's weights
        # update G
        self.set_requires_grad(self.netD, False)  # D requires no gradients when optimizing G
        self.optimizer_G.zero_grad()        # set G's gradients to zero
        self.backward_G()                   # calculate graidents for G
        self.optimizer_G.step()             # udpate G's weights
        
