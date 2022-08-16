import torch

from fanjiang.config import LazyCall as L
from fanjiang.core import gradient_clipping, get_default_optimizer_params

SGD = L(torch.optim.SGD)(
    params=L(get_default_optimizer_params)(
        # params.model is meant to be set to the model object, before instantiating
        # the optimizer.
        weight_decay_norm=0.0
    ),
    lr=0.02,
    momentum=0.9,
    weight_decay=1e-4,
)


AdamW = L(torch.optim.AdamW)(
    params=L(get_default_optimizer_params)(
        # params.model is meant to be set to the model object, before instantiating
        # the optimizer.
        base_lr="${..lr}",
        weight_decay_norm=0.0,
        weight_decay_bias=0.0001,
    ),
    lr=1e-4,
    betas=(0.9, 0.999),
    weight_decay=0.1,
)

