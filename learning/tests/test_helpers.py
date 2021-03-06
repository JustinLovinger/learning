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

import copy
import math
import random

import numpy

from learning.testing import helpers


def test_SaneEqualityArray():
    assert helpers.sane_equality_array(
        [0, 1, 2]) == helpers.sane_equality_array([0, 1, 2])
    assert helpers.sane_equality_array([0]) == helpers.sane_equality_array([0])

    assert not helpers.sane_equality_array([0]) == helpers.sane_equality_array(
        [0, 1, 2])
    assert not helpers.sane_equality_array(
        [0, 1, 2]) == helpers.sane_equality_array([0])


def test_fix_numpy_array_equality():
    complex_obj = [(numpy.array([0, 1, 2]), 'thing', []),
                   numpy.array([0, 1]),
                   [numpy.array([0, 1]),
                    numpy.array([0]), [0, 1, 2]]]

    assert helpers.fix_numpy_array_equality(complex_obj) == \
        [(helpers.sane_equality_array([0, 1, 2]), 'thing', []), helpers.sane_equality_array([0, 1]),
         [helpers.sane_equality_array([0, 1]), helpers.sane_equality_array([0]), [0, 1, 2]]]


###########################
# Gradient checking
###########################
def test_check_gradient_scalar_vector_arg():
    helpers.check_gradient(
        lambda x: numpy.sum(x**2),
        lambda x: 2.0 * x,
        f_arg_tensor=numpy.random.random(random.randint(1, 10)),
        f_shape='scalar')


def test_check_gradient_scalar_matrix_arg():
    helpers.check_gradient(
        lambda x: numpy.sum(x**2),
        lambda x: 2.0 * x,
        f_arg_tensor=numpy.random.random(
            (random.randint(1, 10), random.randint(1, 10))),
        f_shape='scalar')


def test_check_gradient_scalar_3tensor_arg():
    helpers.check_gradient(
        lambda x: numpy.sum(x**2),
        lambda x: 2.0 * x,
        f_arg_tensor=numpy.random.random(
            (random.randint(1, 10), random.randint(1, 10), random.randint(1, 10))),
        f_shape='scalar')


def test_check_gradient_lin_vector_arg():
    helpers.check_gradient(
        lambda x: x**2,
        lambda x: 2.0 * x,
        f_arg_tensor=numpy.random.random(random.randint(1, 10)),
        f_shape='lin')
    helpers.check_gradient(
        lambda x: numpy.sqrt(x),
        lambda x: 1.0 / (2 * numpy.sqrt(x)),
        f_arg_tensor=numpy.random.random(random.randint(1, 10)),
        f_shape='lin')


def test_check_gradient_lin_matrix_arg():
    helpers.check_gradient(
        lambda x: x**2,
        lambda x: 2.0 * x,
        f_arg_tensor=numpy.random.random(
            (random.randint(1, 10), random.randint(1, 10))),
        f_shape='lin')
    helpers.check_gradient(
        lambda x: numpy.sqrt(x),
        lambda x: 1.0 / (2 * numpy.sqrt(x)),
        f_arg_tensor=numpy.random.random(
            (random.randint(1, 10), random.randint(1, 10))),
        f_shape='lin')


def test_check_gradient_lin_3tensor_arg():
    helpers.check_gradient(
        lambda x: x**2,
        lambda x: 2.0 * x,
        f_arg_tensor=numpy.random.random(
            (random.randint(1, 10), random.randint(1, 10), random.randint(1, 10))),
        f_shape='lin')
    helpers.check_gradient(
        lambda x: numpy.sqrt(x),
        lambda x: 1.0 / (2 * numpy.sqrt(x)),
        f_arg_tensor=numpy.random.random(
            (random.randint(1, 10), random.randint(1, 10), random.randint(1, 10))),
        f_shape='lin')


def test_check_gradient_jacobian_vector_arg():
    helpers.check_gradient(lambda x: numpy.array([x[0]**2*x[1], 5*x[0]+math.sin(x[1])]),
                           lambda x: numpy.array([[2*x[0]*x[1], x[0]**2       ],
                                                  [5.0,         math.cos(x[1])]]),
                           f_arg_tensor=numpy.random.random(2),
                           f_shape='jac')


def test_check_gradient_jacobian_matrix_arg():
    helpers.check_gradient(lambda x: numpy.array([x[0][0]**2 + x[1][0]**2, x[0][1]**2 + x[1][1]**2]),
                           lambda x: numpy.array(
                                [
                                    [[2 * x[0][0], 0],
                                     [2 * x[1][0], 0]],
                                    [[0, 2 * x[0][1]],
                                     [0, 2 * x[1][1]]]
                                ]),
                           f_arg_tensor=numpy.random.random((2, 2)),
                           f_shape='jac')

    helpers.check_gradient(lambda x: numpy.array([numpy.sum(x**2), numpy.sum(x**3)]),
                           lambda x: numpy.array([2 * x, 3 * x**2]),
                           f_arg_tensor=numpy.random.random(
                               (random.randint(1, 10), random.randint(1, 10))),
                           f_shape='jac')


def test_check_gradient_jacobian_3tensor_arg():
    helpers.check_gradient(lambda x: numpy.array([numpy.sum(x**2), numpy.sum(x**3)]),
                           lambda x: numpy.array([2 * x, 3 * x**2]),
                           f_arg_tensor=numpy.random.random(
                               (random.randint(1, 10), random.randint(1, 10), random.randint(1, 10))),
                           f_shape='jac')


def test_check_gradient_jacobian_matrix_arg_matrix_out():
    helpers.check_gradient(lambda x: numpy.array([[numpy.sum(x**2), numpy.sum(x**3)], [numpy.sum(x**4), numpy.sum(x**5)]]),
                           lambda x: numpy.array([[2 * x, 3 * x**2], [4 * x**3, 5 * x**4]]),
                           f_arg_tensor=numpy.random.random(
                               (random.randint(1, 10), random.randint(1, 10))),
                           f_shape='jac')


def test_check_gradient_jac_stack():
    helpers.check_gradient(lambda x: numpy.hstack([numpy.sum(x**2, axis=1, keepdims=True), numpy.sum(x**3, axis=1, keepdims=True)]),
                           lambda x: numpy.array([[2 * x[i], 3 * x[i]**2] for i in range(x.shape[0])]),
                           f_arg_tensor=numpy.random.random(
                               (random.randint(1, 10), random.randint(1, 10))),
                           f_shape='jac-stack')
