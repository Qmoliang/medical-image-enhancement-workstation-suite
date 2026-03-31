import torch
from .base_model import BaseModel
from . import networks

class CycleGANInferModel(BaseModel):
    """
    Inference-only CycleGAN:
    - Only uses G_B (B→A) to generate fake_A from real_B (CBCT).
    - Ignores any mask even if provided.
    - No discriminators, no losses, no training.
    """

    @staticmethod
    def modify_commandline_options(parser, is_train=False):
        parser.set_defaults(no_dropout=True)
        return parser

    def __init__(self, opt):
        super().__init__(opt)
        self.loss_names = []                      # no losses
        self.visual_names = ['real_B', 'fake_A']  # only show input & output
        self.model_names = ['G_B']                # single generator

        # define generator (B → A)
        self.netG_B = networks.define_G(
            opt.output_nc, opt.input_nc, opt.ngf,
            opt.netG, opt.norm, not opt.no_dropout,
            opt.init_type, opt.init_gain, self.gpu_ids
        )

    def set_input(self, input):
        """Only accepts CBCT (B). Mask, if present, is ignored."""
        self.real_B = input['B'].to(self.device)
        self.image_paths = input.get('B_paths', [""])

    @torch.no_grad()
    def forward(self):
        """Forward: CBCT (B) → fake CT (A); mask is NOT used."""
        self.fake_A = self.netG_B(self.real_B)

    def test(self):
        self.forward()

    def optimize_parameters(self):
        pass
