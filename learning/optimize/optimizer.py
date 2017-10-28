###############################################################################
# The MIT License (MIT)
#
# Copyright (c) 2017 Justin Lovinger
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###############################################################################
"""Numerical optimization methods."""

import logging

import numpy

from learning.optimize import WolfeLineSearch
from learning.optimize import IncrPrevStep, FOChangeInitialStep

# TODO: Numerical Optimization uses ||grad_f_k||_inf < 10^-5 (1 + |f_k|) as a stopping criteria
# Perhaps we should as well
# It also declares failure after 10000 iterations
JACOBIAN_NORM_BREAK = 1e-10


def make_optimizer(num_parameters):
    """Return a new optimizer, using simple heuristics."""
    # TODO: More heuristics

    # If there are too many parameters, use an optimizer that doesn't use hessian matrix
    if num_parameters > 500:  # NOTE: Cutoff value could use more testing
        # Too many weights, don't use hessian matrix
        return LBFGS()
    else:
        # Few enough weights, use hessian matrix
        return BFGS()


################################
# Base Model
################################
class Optimizer(object):
    """Optimizer for optimizing model parameters."""

    def __init__(self):
        self.jacobian = None  # Last computed jacobian
        self.hessian = None  # Last computed hessian

    def reset(self):
        """Reset optimizer parameters."""
        self.jacobian = None
        self.hessian = None

    def next(self, problem, parameters):
        """Return next iteration of this optimizer."""
        raise NotImplementedError()


################################
# Optimizer Implementations
################################
# TODO: Optimize optimizers by re-using objective and jacobians calculated
# during line searches. Such as by caching these values, and checking cache before
# calculating (Problem object can cache these (by parameters), but we need to make sure
# model do not make another instance of an Problem if the problem is the same)
class SteepestDescent(Optimizer):
    """Simple steepest descent with constant step size."""

    def __init__(self, step_size_getter=None):
        super(SteepestDescent, self).__init__()

        if step_size_getter is None:
            step_size_getter = WolfeLineSearch(
                initial_step_getter=FOChangeInitialStep())
        self._step_size_getter = step_size_getter

    def reset(self):
        """Reset optimizer parameters."""
        super(SteepestDescent, self).__init__()
        self._step_size_getter.reset()

    def next(self, problem, parameters):
        """Return next iteration of this optimizer."""
        obj_value, self.jacobian = problem.get_obj_jac(parameters)

        if numpy.linalg.norm(self.jacobian) < JACOBIAN_NORM_BREAK:
            logging.info('Optimizer converged with small jacobian')
            return obj_value, parameters

        step_size = self._step_size_getter(
            parameters, obj_value, self.jacobian, -self.jacobian, problem)

        # Take a step down the first derivative direction
        return obj_value, parameters - step_size * self.jacobian


class SteepestDescentMomentum(Optimizer):
    """Simple gradient descent with constant step size, and momentum."""

    def __init__(self, step_size_getter=None, momentum_rate=0.2):
        super(SteepestDescentMomentum, self).__init__()
        if step_size_getter is None:
            step_size_getter = WolfeLineSearch(
                initial_step_getter=FOChangeInitialStep())
        self._step_size_getter = step_size_getter

        self._momentum_rate = momentum_rate

        # Store previous step (step_size*direction) for momentum
        self._prev_step = None

    def reset(self):
        """Reset optimizer parameters."""
        super(SteepestDescentMomentum, self).reset()
        self._step_size_getter.reset()
        self._prev_step = None

    def next(self, problem, parameters):
        """Return next iteration of this optimizer."""
        obj_value, self.jacobian = problem.get_obj_jac(parameters)

        if numpy.linalg.norm(self.jacobian) < JACOBIAN_NORM_BREAK:
            logging.info('Optimizer converged with small jacobian')
            return obj_value, parameters

        # Setup step for this iteration (step_size*direction)
        # TODO (maybe): step_dir for this iteration should be
        # -self.jacobian - self._momentum_rate*self._prev_jacobian
        # instead of adding self._momentum_rate * self._prev_step after this step
        # This allow the step size finder to account for momentum,
        # and more accurately and efficiently converge
        # However, this may negate the primary purpose of momentum
        # (to prevent convergence to small local optima)
        step_dir = -self.jacobian
        step_size = self._step_size_getter(parameters, obj_value,
                                           self.jacobian, step_dir, problem)
        step = step_size * step_dir

        # Add steps from this and previous iteration
        next_parameters = parameters + step
        if self._prev_step is not None:
            next_parameters += self._momentum_rate * self._prev_step
        self._prev_step = step

        # Take a step down the first derivative direction
        return obj_value, next_parameters


def initial_hessian_identity(parameters, prev_parameters, jacobian,
                             previous_jacobian):
    """Return identity matrix, regardless of arguments."""
    return numpy.identity(parameters.shape[0])


def initial_hessian_scaled_identity(parameters, prev_parameters, jacobian,
                                    previous_jacobian):
    """Return identity matrix, scaled by parameter and jacobian differences.

    scalar gamma = (s_{k-1}^T y_{k_1}) / (y_{k-1}^T y_{k-1}),
    where
    s_{k-1} = x_k - x_{k-1} (x = parameters)
    y_{k-1} = jac_f_k - jac_f_{k-1}
    """
    # Construct diagonal matrix from scalar,
    # instead of multiplying identity by scalar
    return numpy.diag(
        numpy.repeat(
            initial_hessian_gamma_scalar(parameters - self._prev_params,
                                         jacobian - self._prev_jacobian),
            parameters.shape[0]))


class BFGS(Optimizer):
    """Quasi-Newton BFGS optimizer.

    Broyden-Fletcher-Goldfarb-Shanno (BFGS)
    Ref: Numerical Optimization pp. 136

    NOTE: Step size should satisfy Wolfe conditions,
    to ensure curvature condition, y_k^T s_k > 0, is satisfied.
    Otherwise, the BFGS update rule is invalid, and could give
    poor performance.
    """

    def __init__(self,
                 step_size_getter=None,
                 initial_hessian_func=initial_hessian_identity):
        super(BFGS, self).__init__()

        if step_size_getter is None:
            step_size_getter = WolfeLineSearch(
                # Values recommended by Numerical Optimization 2nd, pp. 161
                c_1=1e-4,
                c_2=0.9,
                initial_step_getter=IncrPrevStep())
        self._step_size_getter = step_size_getter

        # NOTE: It is recommended to scale the identiy matrix
        # (Numerical Optimization 2nd, pp. 162)
        # as performed in initial_hessian_scaled_identity,
        # but empirical tests show it is more effective
        # to not scale identity matrix
        # TODO: More testing needed
        self._initial_hessian_func = initial_hessian_func

        # BFGS Parameters
        self._prev_params = None
        self._prev_jacobian = None
        self._prev_inv_hessian = None

    def reset(self):
        """Reset optimizer parameters."""
        super(BFGS, self).reset()
        self._step_size_getter.reset()

        # Reset BFGS Parameters
        self._prev_params = None
        self._prev_jacobian = None
        self._prev_inv_hessian = None

    def next(self, problem, parameters):
        """Return next iteration of this optimizer."""
        obj_value, self.jacobian = problem.get_obj_jac(parameters)

        if numpy.linalg.norm(self.jacobian) < JACOBIAN_NORM_BREAK:
            logging.info('Optimizer converged with small jacobian')
            return obj_value, parameters

        approx_inv_hessian = self._get_approx_inv_hessian(
            parameters, self.jacobian)

        step_dir = -(approx_inv_hessian.dot(self.jacobian))

        step_size = self._step_size_getter(parameters, obj_value,
                                           self.jacobian, step_dir, problem)

        return obj_value, parameters + step_size * step_dir

    def _get_approx_inv_hessian(self, parameters, jacobian):
        """Calculate approx inv hessian for this iteration, and return it."""
        # If first iteration
        if self._prev_params is None:
            # Default to identity for approx inv hessian
            H_kp1 = numpy.identity(parameters.shape[0])

            # Don't save H_kp1, so we can differentiate between first
            # and second iteration
        else:
            # If second iteration
            if self._prev_inv_hessian is None:
                H_kp1 = _bfgs_eq(
                    self._initial_hessian_func(parameters, self._prev_params,
                                               jacobian, self._prev_jacobian),
                    parameters - self._prev_params,
                    jacobian - self._prev_jacobian)

            # Every iteration > 2
            else:
                H_kp1 = _bfgs_eq(self._prev_inv_hessian,
                                 parameters - self._prev_params,
                                 jacobian - self._prev_jacobian)

            # Save inv hessian to update next iteration
            self._prev_inv_hessian = H_kp1

        # Save values from current iteration for next iteration
        self._prev_params = parameters
        self._prev_jacobian = jacobian

        return H_kp1


def _bfgs_eq(H_k, s_k, y_k):
    """Apply the bfgs update rule to obtain the next approx inverse hessian.

    H_{k+1} = (I - p_k s_k y_k^T) H_k (I - p_k y_k s_k^T) + p_k s_k s_k^T
    where
    s_k = x_{k+1} - x_k (x = parameters)
    y_k = jac_f_{k+1} - jac_f_k
    p_k = 1 / (y_k^T s_k)

    Note that all vectors are column vectors (so vec.T is a row vector)

    Note that the current iteration is k+1, and k is the previous iteration.
    However s_k and y_k correspond to he current iteration (and previous).
    """
    # An implementation very close to the original, using matrices, and column matrices:
    # I = numpy.matrix(I)

    # H_k = numpy.matrix(H_k)
    # s_k = numpy.matrix(s_k).T
    # y_k = numpy.matrix(y_k).T

    # p_k = float(1.0 / (y_k.T * s_k))

    # p_k_times_s_k = p_k * s_k
    # return numpy.array(
    #     (I - p_k_times_s_k * y_k.T)
    #     * H_k
    #     * (I - p_k * y_k * s_k.T)
    #     + (p_k_times_s_k * s_k.T)
    # )

    # More efficient implementation with arrays and fast [:, None] transposes
    # Vectors are row vectors (1d, as given)
    I = numpy.identity(s_k.shape[0])

    # Calculate p_k with failsafe for divide by zero errors
    y_k_dot_s_k = y_k.dot(s_k)  # y_k.dot(s_k) == y_k.dot(s_k[:, None])
    # Failsafe for divide by zero errors
    # y_k and s_k are change in jacobian and parameters respectively
    # If these values did not change, we can re-use previous inv hessian
    if y_k_dot_s_k == 0.0:
        return H_k
    p_k = 1.0 / y_k_dot_s_k

    p_k_times_s_k = p_k * s_k
    return (
        (I - p_k_times_s_k[:, None] * y_k)
        .dot(H_k)
        .dot(I - (p_k * y_k)[:, None] * (s_k))
        + (p_k_times_s_k[:, None] * s_k)
    )


def initial_hessian_one_scalar(param_diff, jac_diff):
    """Return 1.0, regardless of arguments."""
    return 1.0


def initial_hessian_gamma_scalar(param_diff, jac_diff):
    """Return identity matrix, scaled by parameter and jacobian differences.

    scalar gamma = (s_{k-1}^T y_{k_1}) / (y_{k-1}^T y_{k-1}),
    where
    s_{k-1} = x_k - x_{k-1} (x = parameters)
    y_{k-1} = jac_f_k - jac_f_{k-1}
    """
    # Note that s_{k-1} = self._prev_param_diffs[0]
    # and y_{k-1} = self._prev_jac_diffs[0]
    return (param_diff.dot(jac_diff)) / (jac_diff.dot(jac_diff))


class LBFGS(Optimizer):
    """Low-memory quasi-Newton L-BFGS optimizer.

    Limited-memory Broyden-Fletcher-Goldfarb-Shanno (L-BFGS)
    Ref: Numerical Optimization pp. 177

    NOTE: Step size should satisfy Wolfe conditions,
    to ensure curvature condition, y_k^T s_k > 0, is satisfied.
    Otherwise, the BFGS update rule is invalid, and could give
    poor performance.
    """

    def __init__(self,
                 step_size_getter=None,
                 num_remembered_iterations=5,
                 initial_hessian_scalar_func=initial_hessian_gamma_scalar):
        super(LBFGS, self).__init__()

        if step_size_getter is None:
            step_size_getter = WolfeLineSearch(
                # Values recommended by Numerical Optimization 2nd, pp. 161
                c_1=1e-4,
                c_2=0.9,
                initial_step_getter=IncrPrevStep())
        self._step_size_getter = step_size_getter

        self._initial_hessian_scalar_func = initial_hessian_scalar_func

        # L-BFGS Parameters
        self._num_remembered_iterations = num_remembered_iterations

        self._prev_params = None
        self._prev_jacobian = None

        self._prev_param_diffs = []  # Previous s_k values
        self._prev_jac_diffs = []  # Previous y_k values

    def reset(self):
        """Reset optimizer parameters."""
        super(LBFGS, self).reset()
        self._step_size_getter.reset()

        # Reset BFGS Parameters
        self._prev_params = None
        self._prev_jacobian = None

        self._prev_param_diffs = []  # Previous s_k values
        self._prev_jac_diffs = []  # Previous y_k values

    def next(self, problem, parameters):
        """Return next iteration of this optimizer."""
        obj_value, self.jacobian = problem.get_obj_jac(parameters)

        if numpy.linalg.norm(self.jacobian) < JACOBIAN_NORM_BREAK:
            logging.info('Optimizer converged with small jacobian')
            return obj_value, parameters

        # Add param and jac diffs for this iteration
        self._update_diffs(parameters, self.jacobian)

        # Approximate step direction, and update parameters
        step_dir = self._lbfgs_step_dir(problem, parameters, self.jacobian)

        step_size = self._step_size_getter(parameters, obj_value,
                                           self.jacobian, step_dir, problem)

        return obj_value, parameters + step_size * step_dir

    def _update_diffs(self, parameters, jacobian):
        """Update stored differences."""
        if self._prev_params is not None:
            self._prev_param_diffs.insert(0, parameters - self._prev_params)
            self._prev_jac_diffs.insert(0, jacobian - self._prev_jacobian)

        # Remove oldest, if over limit
        if len(self._prev_param_diffs) > self._num_remembered_iterations:
            self._prev_param_diffs.pop(-1)
            self._prev_jac_diffs.pop(-1)
        assert len(self._prev_param_diffs) <= self._num_remembered_iterations
        assert len(self._prev_param_diffs) == len(self._prev_jac_diffs)

        # Store parameters and jacobian, for next _update_diffs
        self._prev_params = parameters
        self._prev_jacobian = jacobian

    def _lbfgs_step_dir(self, problem, parameters, jacobian):
        """Return step_dir, approximated from previous param and jac differences."""
        # First pass, backwards pass (from latest to oldest)
        newton_grad = numpy.copy(jacobian)
        # 1 / (y_k^T s_k), where y_k^T = jac_diff, and s_k = param_diff
        rhos = []
        alphas = []  # rho_i s_i^T q
        for param_diff, jac_diff in zip(self._prev_param_diffs,
                                        self._prev_jac_diffs):
            # alpha_i <- rho_i s_i^T q, where q = newton_grad
            # q <- q - alpha_i y_i
            rho = 1.0 / (jac_diff.dot(param_diff))
            alpha = rho * param_diff.dot(newton_grad)
            newton_grad -= alpha * jac_diff

            # Save rho and alpha, for second pass
            rhos.append(rho)
            alphas.append(alpha)

        # Second pass, forwards pass (from oldest to latest)
        newton_grad *= self._initial_inv_hessian_scalar()
        for param_diff, jac_diff, rho, alpha in reversed(
                zip(self._prev_param_diffs, self._prev_jac_diffs, rhos,
                    alphas)):
            # beta <- rho_i y_i^T r, where r = newton_grad
            # r <- r + s_i (alpha_i - beta)
            newton_grad += param_diff * (
                alpha - rho * jac_diff.dot(newton_grad))

        # Step direction is down the gradient
        return -newton_grad

    def _initial_inv_hessian_scalar(self):
        """Return scalar of identity matrix, for initial approximate inv-hessian.

        Note that approximate hessian is typically a diagonal matrix,
        with the same value, gamma, on each diagonal.
        So we can calculate H_0.dot(vec) as gamma * vec,
        without requiring the allocation and calculation of a full matrix.
        """
        # Handle first iteration (when no previous diffs)
        if len(self._prev_param_diffs) == 0:
            return 1.0
        else:
            return self._initial_hessian_scalar_func(self._prev_param_diffs[0],
                                                     self._prev_jac_diffs[0])
