import bisect
import math
from bisect import bisect_right
from typing import List, Optional, Sequence, Union

import torch

# pyre-ignore-all-errors[58]   # handle optional

__all__ = ["WarmupParamScheduler", "CosineParamScheduler", "LRMultiplier"]


class CyclicScheduler(torch.optim.lr_scheduler._LRScheduler):
    def __init__(
        self,
        optimizer,
        base_lr,
        anneal_decay=0.01,
        anneal_iters=10,
        anneal_strategy='cos',
        last_epoch=-1
    ):
        base_lrs = self._format_param(optimizer, base_lr)

        for base_lr, group in zip(base_lrs, optimizer.param_groups):
            group['start_lr'] = base_lr
            group['end_lr'] = base_lr * anneal_decay

        if anneal_strategy not in ['cos', 'linear']:
            raise ValueError("anneal_strategy must by one of 'cos' or 'linear', "
                             "instead got {}".format(anneal_strategy))
        elif anneal_strategy == 'cos':
            self.anneal_func = self._cosine_anneal
        elif anneal_strategy == 'linear':
            self.anneal_func = self._linear_anneal
        if not isinstance(anneal_iters, int) or anneal_iters < 0:
            raise ValueError("anneal_iters must be equal or greater than 0, got {}".format(
                             anneal_iters))
        self.anneal_iters = anneal_iters
        super(CyclicScheduler, self).__init__(optimizer, last_epoch)

    @staticmethod
    def _format_param(optimizer, lrs):
        if isinstance(lrs, (list, tuple)):
            if len(lrs) != len(optimizer.param_groups):
                raise ValueError("lrs must have the same length as "
                                 "optimizer.param_groups: lrs has {}, "
                                 "optimizer.param_groups has {}".format(
                                     len(lrs), len(optimizer.param_groups)))
            return lrs
        else:
            return [lrs] * len(optimizer.param_groups)

    @staticmethod
    def _linear_anneal(t):
        return t

    @staticmethod
    def _cosine_anneal(t):
        return (1 - math.cos(math.pi * t)) / 2

    def get_lr(self):
        progress = self._step_count % self.anneal_iters

        t = max(0, min(1, progress / max(1, self.anneal_iters)))
        alpha = self.anneal_func(t)

        return [group['end_lr'] * alpha + group["start_lr"] * (1 - alpha)
                for group in self.optimizer.param_groups]


class ParamScheduler:
    """
    Base class for parameter schedulers.
    A parameter scheduler defines a mapping from a progress value in [0, 1) to
    a number (e.g. learning rate).
    """

    # To be used for comparisons with where
    WHERE_EPSILON = 1e-6

    def __call__(self, where: float) -> float:
        """
        Get the value of the param for a given point at training.

        We update params (such as learning rate) based on the percent progress
        of training completed. This allows a scheduler to be agnostic to the
        exact length of a particular run (e.g. 120 epochs vs 90 epochs), as
        long as the relative progress where params should be updated is the same.
        However, it assumes that the total length of training is known.

        Args:
            where: A float in [0,1) that represents how far training has progressed

        """
        raise NotImplementedError("Param schedulers must override __call__")


class ConstantParamScheduler(ParamScheduler):
    """
    Returns a constant value for a param.
    """

    def __init__(self, value: float) -> None:
        self._value = value

    def __call__(self, where: float) -> float:
        if where >= 1.0:
            raise RuntimeError(
                f"where in ParamScheduler must be in [0, 1]: got {where}"
            )
        return self._value


class CosineParamScheduler(ParamScheduler):
    """
    Cosine decay or cosine warmup schedules based on start and end values.
    The schedule is updated based on the fraction of training progress.
    The schedule was proposed in 'SGDR: Stochastic Gradient Descent with
    Warm Restarts' (https://arxiv.org/abs/1608.03983). Note that this class
    only implements the cosine annealing part of SGDR, and not the restarts.

    Example:

        .. code-block:: python

          CosineParamScheduler(start_value=0.1, end_value=0.0001)
    """

    def __init__(
        self,
        start_value: float,
        end_value: float,
    ) -> None:
        self._start_value = start_value
        self._end_value = end_value

    def __call__(self, where: float) -> float:
        return self._end_value + 0.5 * (self._start_value - self._end_value) * (
            1 + math.cos(math.pi * where)
        )


class ExponentialParamScheduler(ParamScheduler):
    """
    Exponetial schedule parameterized by a start value and decay.
    The schedule is updated based on the fraction of training
    progress, `where`, with the formula
    `param_t = start_value * (decay ** where)`.

    Example:

        .. code-block:: python
            ExponentialParamScheduler(start_value=2.0, decay=0.02)

    Corresponds to a decreasing schedule with values in [2.0, 0.04).
    """

    def __init__(
        self,
        start_value: float,
        decay: float,
    ) -> None:
        self._start_value = start_value
        self._decay = decay

    def __call__(self, where: float) -> float:
        return self._start_value * (self._decay ** where)


class LinearParamScheduler(ParamScheduler):
    """
    Linearly interpolates parameter between ``start_value`` and ``end_value``.
    Can be used for either warmup or decay based on start and end values.
    The schedule is updated after every train step by default.

    Example:

        .. code-block:: python

            LinearParamScheduler(start_value=0.0001, end_value=0.01)

    Corresponds to a linear increasing schedule with values in [0.0001, 0.01)
    """

    def __init__(
        self,
        start_value: float,
        end_value: float,
    ) -> None:
        self._start_value = start_value
        self._end_value = end_value

    def __call__(self, where: float) -> float:
        # interpolate between start and end values
        return self._end_value * where + self._start_value * (1 - where)


class MultiStepParamScheduler(ParamScheduler):
    """
    Takes a predefined schedule for a param value, and a list of epochs or steps
    which stand for the upper boundary (excluded) of each range.

    Example:

        .. code-block:: python

          MultiStepParamScheduler(
            values=[0.1, 0.01, 0.001, 0.0001],
            milestones=[30, 60, 80, 120]
          )

    Then the param value will be 0.1 for epochs 0-29, 0.01 for
    epochs 30-59, 0.001 for epochs 60-79, 0.0001 for epochs 80-120.
    Note that the length of values must be equal to the length of milestones
    plus one.
    """

    def __init__(
        self,
        values: List[float],
        num_updates: Optional[int] = None,
        milestones: Optional[List[int]] = None,
    ) -> None:
        """
        Args:
            values: param value in each range
            num_updates: the end of the last range. If None, will use ``milestones[-1]``
            milestones: the boundary of each range. If None, will evenly split ``num_updates``

        For example, all the following combinations define the same scheduler:

        * num_updates=90, milestones=[30, 60], values=[1, 0.1, 0.01]
        * num_updates=90, values=[1, 0.1, 0.01]
        * milestones=[30, 60, 90], values=[1, 0.1, 0.01]
        * milestones=[3, 6, 9], values=[1, 0.1, 0.01]  (ParamScheduler is scale-invariant)
        """
        if num_updates is None and milestones is None:
            raise ValueError("num_updates and milestones cannot both be None")
        if milestones is None:
            # Default equispaced drop_epochs behavior
            milestones = []
            step_width = math.ceil(num_updates / float(len(values)))
            for idx in range(len(values) - 1):
                milestones.append(step_width * (idx + 1))
        else:
            if not (
                isinstance(milestones, Sequence)
                and len(milestones) == len(values) - int(num_updates is not None)
            ):
                raise ValueError(
                    "MultiStep scheduler requires a list of %d miletones"
                    % (len(values) - int(num_updates is not None))
                )

        if num_updates is None:
            num_updates, milestones = milestones[-1], milestones[:-1]
        if num_updates < len(values):
            raise ValueError(
                "Total num_updates must be greater than length of param schedule"
            )

        self._param_schedule = values
        self._num_updates = num_updates
        self._milestones: List[int] = milestones

        start_epoch = 0
        for milestone in self._milestones:
            # Do not exceed the total number of epochs
            if milestone >= self._num_updates:
                raise ValueError(
                    "Milestone must be smaller than total number of updates: "
                    "num_updates=%d, milestone=%d" % (self._num_updates, milestone)
                )
            # Must be in ascending order
            if start_epoch >= milestone:
                raise ValueError(
                    "Milestone must be smaller than start epoch: start_epoch=%d, milestone=%d"
                    % (start_epoch, milestone)
                )
            start_epoch = milestone

    def __call__(self, where: float) -> float:
        if where > 1.0:
            raise RuntimeError(
                f"where in ParamScheduler must be in [0, 1]: got {where}"
            )
        epoch_num = int((where + self.WHERE_EPSILON) * self._num_updates)
        return self._param_schedule[bisect.bisect_right(self._milestones, epoch_num)]


class PolynomialDecayParamScheduler(ParamScheduler):
    """
    Decays the param value after every epoch according to a
    polynomial function with a fixed power.
    The schedule is updated after every train step by default.

    Example:

        .. code-block:: python

          PolynomialDecayParamScheduler(base_value=0.1, power=0.9)

    Then the param value will be 0.1 for epoch 0, 0.099 for epoch 1, and
    so on.
    """

    def __init__(
        self,
        base_value: float,
        power: float,
    ) -> None:
        self._base_value = base_value
        self._power = power

    def __call__(self, where: float) -> float:
        return self._base_value * (1 - where) ** self._power


class StepParamScheduler(ParamScheduler):
    """
    Takes a fixed schedule for a param value.  If the length of the
    fixed schedule is less than the number of epochs, then the epochs
    are divided evenly among the param schedule.
    The schedule is updated after every train epoch by default.

    Example:

        .. code-block:: python

          StepParamScheduler(values=[0.1, 0.01, 0.001, 0.0001], num_updates=120)

    Then the param value will be 0.1 for epochs 0-29, 0.01 for
    epochs 30-59, 0.001 for epoch 60-89, 0.0001 for epochs 90-119.
    """

    def __init__(
        self,
        num_updates: Union[int, float],
        values: List[float],
    ) -> None:
        if num_updates <= 0:
            raise ValueError("Number of updates must be larger than 0")
        if not (isinstance(values, Sequence) and len(values) > 0):
            raise ValueError(
                "Step scheduler requires a list of at least one param value"
            )
        self._param_schedule = values

    def __call__(self, where: float) -> float:
        ind = int((where + self.WHERE_EPSILON) * len(self._param_schedule))
        return self._param_schedule[ind]


class StepWithFixedGammaParamScheduler(ParamScheduler):
    """
    Decays the param value by gamma at equal number of steps so as to have the
    specified total number of decays.

    Example:

        .. code-block:: python

          StepWithFixedGammaParamScheduler(
            base_value=0.1, gamma=0.1, num_decays=3, num_updates=120)

    Then the param value will be 0.1 for epochs 0-29, 0.01 for
    epochs 30-59, 0.001 for epoch 60-89, 0.0001 for epochs 90-119.
    """

    def __init__(
        self,
        base_value: float,
        num_decays: int,
        gamma: float,
        num_updates: int,
    ) -> None:
        for k in [base_value, gamma]:
            if not (isinstance(k, (int, float)) and k > 0):
                raise ValueError("base_value and gamma must be positive numbers")
        for k in [num_decays, num_updates]:
            if not (isinstance(k, int) and k > 0):
                raise ValueError("num_decays and num_updates must be positive integers")

        self.base_value = base_value
        self.num_decays = num_decays
        self.gamma = gamma
        self.num_updates = num_updates
        values = [base_value]
        for _ in range(num_decays):
            values.append(values[-1] * gamma)

        self._step_param_scheduler = StepParamScheduler(
            num_updates=num_updates, values=values
        )

    def __call__(self, where: float) -> float:
        return self._step_param_scheduler(where)


class CompositeParamScheduler(ParamScheduler):
    """
    Composite parameter scheduler composed of intermediate schedulers.
    Takes a list of schedulers and a list of lengths corresponding to
    percentage of training each scheduler should run for. Schedulers
    are run in order. All values in lengths should sum to 1.0.

    Each scheduler also has a corresponding interval scale. If interval
    scale is 'fixed', the intermediate scheduler will be run without any rescaling
    of the time. If interval scale is 'rescaled', intermediate scheduler is
    run such that each scheduler will start and end at the same values as it
    would if it were the only scheduler. Default is 'rescaled' for all schedulers.

    Example:

        .. code-block:: python

              schedulers = [
                ConstantParamScheduler(value=0.42),
                CosineParamScheduler(start_value=0.42, end_value=1e-4)
              ]
              CompositeParamScheduler(
                schedulers=schedulers,
                interval_scaling=['rescaled', 'rescaled'],
                lengths=[0.3, 0.7])

    The parameter value will be 0.42 for the first [0%, 30%) of steps,
    and then will cosine decay from 0.42 to 0.0001 for [30%, 100%) of
    training.
    """

    def __init__(
        self,
        schedulers: Sequence[ParamScheduler],
        lengths: List[float],
        interval_scaling: Sequence[str],
    ) -> None:
        if len(schedulers) != len(lengths):
            raise ValueError("Schedulers and lengths must be same length")
        if len(schedulers) == 0:
            raise ValueError(
                "There must be at least one scheduler in the composite scheduler"
            )
        if abs(sum(lengths) - 1.0) >= 1e-3:
            raise ValueError("The sum of all values in lengths must be 1")
        if sum(lengths) != 1.0:
            lengths[-1] = 1.0 - sum(lengths[:-1])
        for s in interval_scaling:
            if s not in ["rescaled", "fixed"]:
                raise ValueError(f"Unsupported interval_scaling: {s}")

        self._lengths = lengths
        self._schedulers = schedulers
        self._interval_scaling = interval_scaling

    def __call__(self, where: float) -> float:
        # Find scheduler corresponding to where
        i = 0
        running_total = self._lengths[i]
        while (where + self.WHERE_EPSILON) > running_total and i < len(
            self._schedulers
        ) - 1:
            i += 1
            running_total += self._lengths[i]
        scheduler = self._schedulers[i]
        scheduler_where = where
        interval_scale = self._interval_scaling[i]
        if interval_scale == "rescaled":
            # Calculate corresponding where % for scheduler
            scheduler_start = running_total - self._lengths[i]
            scheduler_where = (where - scheduler_start) / self._lengths[i]
        return scheduler(scheduler_where)




class WarmupParamScheduler(CompositeParamScheduler):
    """
    Add an initial warmup stage to another scheduler.
    """

    def __init__(
        self,
        scheduler: ParamScheduler,
        warmup_factor: float,
        warmup_length: float,
        warmup_method: str = "linear",
    ):
        """
        Args:
            scheduler: warmup will be added at the beginning of this scheduler
            warmup_factor: the factor w.r.t the initial value of ``scheduler``, e.g. 0.001
            warmup_length: the relative length (in [0, 1]) of warmup steps w.r.t the entire
                training, e.g. 0.01
            warmup_method: one of "linear" or "constant"
        """
        end_value = scheduler(warmup_length)  # the value to reach when warmup ends
        start_value = warmup_factor * scheduler(0.0)
        if warmup_method == "constant":
            warmup = ConstantParamScheduler(start_value)
        elif warmup_method == "linear":
            warmup = LinearParamScheduler(start_value, end_value)
        else:
            raise ValueError("Unknown warmup method: {}".format(warmup_method))
        super().__init__(
            [warmup, scheduler],
            interval_scaling=["rescaled", "fixed"],
            lengths=[warmup_length, 1 - warmup_length],
        )


class LRMultiplier(torch.optim.lr_scheduler._LRScheduler):
    """
    A LRScheduler which uses fvcore :class:`ParamScheduler` to multiply the
    learning rate of each param in the optimizer.
    Every step, the learning rate of each parameter becomes its initial value
    multiplied by the output of the given :class:`ParamScheduler`.

    The absolute learning rate value of each parameter can be different.
    This scheduler can be used as long as the relative scale among them do
    not change during training.

    Examples:
    ::
        LRMultiplier(
            opt,
            WarmupParamScheduler(
                MultiStepParamScheduler(
                    [1, 0.1, 0.01],
                    milestones=[60000, 80000],
                    num_updates=90000,
                ), 0.001, 100 / 90000
            ),
            max_iter=90000
        )
    """

    # NOTES: in the most general case, every LR can use its own scheduler.
    # Supporting this requires interaction with the optimizer when its parameter
    # group is initialized. For example, classyvision implements its own optimizer
    # that allows different schedulers for every parameter group.
    # To avoid this complexity, we use this class to support the most common cases
    # where the relative scale among all LRs stay unchanged during training.  In this
    # case we only need a total of one scheduler that defines the relative LR multiplier.

    def __init__(
        self,
        optimizer: torch.optim.Optimizer,
        multiplier: ParamScheduler,
        max_iter: int,
        last_iter: int = -1,
    ):
        """
        Args:
            optimizer, last_iter: See ``torch.optim.lr_scheduler._LRScheduler``.
                ``last_iter`` is the same as ``last_epoch``.
            multiplier: a fvcore ParamScheduler that defines the multiplier on
                every LR of the optimizer
            max_iter: the total number of training iterations
        """
        if not isinstance(multiplier, ParamScheduler):
            raise ValueError(
                "_LRMultiplier(multiplier=) must be an instance of fvcore "
                f"ParamScheduler. Got {multiplier} instead."
            )
        self._multiplier = multiplier
        self._max_iter = max_iter
        super().__init__(optimizer, last_epoch=last_iter)

    def state_dict(self):
        # fvcore schedulers are stateless. Only keep pytorch scheduler states
        return {"base_lrs": self.base_lrs, "last_epoch": self.last_epoch}

    def get_lr(self) -> List[float]:
        multiplier = self._multiplier(self.last_epoch / self._max_iter)
        return [base_lr * multiplier for base_lr in self.base_lrs]
