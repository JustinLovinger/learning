import numpy

from pynn import network
from pynn.architecture import transfer

class AddBias(network.ParallelLayer):
    def __init__(self, layer):
        self.layer = layer

    def reset(self):
        self.layer.reset()

    def activate(self, inputs):
        # Add an extra input, always set to 1
        return self.layer.activate(numpy.hstack((inputs, [1])))

    def get_prev_errors(self, all_inputs, all_errors, outputs):
        # Clip the last delta, which was for bias input
        return self.layer.get_prev_errors(all_inputs, all_errors, outputs)[:-1]

    def update(self, all_inputs, outputs, all_errors):
        assert len(all_inputs) == 1
        inputs = all_inputs[0]
        self.layer.update([numpy.hstack((inputs, [1]))], outputs, all_errors)

class Perceptron(network.Layer):
    def __init__(self, inputs, outputs, 
                 learn_rate=0.5, momentum_rate=0.1, initial_weights_range=0.25):
        super(Perceptron, self).__init__()

        self.learn_rate = learn_rate
        self.momentum_rate = momentum_rate
        self.initial_weights_range = initial_weights_range

        self._size = (inputs, outputs)

        # Build weights matrix
        self._weights = numpy.zeros(self._size)
        self.reset()

        # Initial momentum
        self._momentums = numpy.zeros(self._size)

    def reset(self):
        # Randomize weights, between -initial_weights_range and initial_weights_range
        # TODO: randomize with Gaussian distribution instead of uniform. Mean = 0, small variance.
        random_matrix = numpy.random.random(self._size)
        self._weights = (2*random_matrix-1)*self.initial_weights_range

    def activate(self, inputs):
        return numpy.dot(inputs, self._weights)

    def get_prev_errors(self, all_inputs, all_errors, outputs):
        errors = self._avg_all_errors(all_errors, outputs.shape)
        return numpy.dot(errors, self._weights.T)

    def update(self, all_inputs, outputs, all_errors):
        assert len(all_inputs) == 1
        inputs = all_inputs[0]
        deltas = self._avg_all_errors(all_errors, outputs.shape)

        # Update, [:,None] quickly transposes an array to a col vector
        changes = inputs[:,None] * deltas
        self._weights += self.learn_rate*changes + self.momentum_rate*self._momentums

        # Save change as momentum for next backpropogate
        self._momentums = changes


################################################
# Transfer functions with perceptron error rule
################################################
# The perceptron learning rule states that its errors
# are multiplied by the derivative of the transfers output.
# The output learning for an rbf, by contrast, does not.
class TanhTransferPerceptron(transfer.TanhTransfer):
    def get_prev_errors(self, all_inputs, all_errors, outputs):
        return super(TanhTransferPerceptron, self).get_prev_errors(all_inputs, all_errors, outputs) * transfer.dtanh(outputs)


class ReluTransferPerceptron(transfer.ReluTransfer):
    def get_prev_errors(self, all_inputs, all_errors, outputs):
        return super(ReluTransferPerceptron, self).get_prev_errors(all_inputs, all_errors, outputs) * transfer.drelu(outputs)


class LogitTransfer(transfer.LogitTransfer):
    def get_prev_errors(self, all_inputs, all_errors, outputs):
        return super(LogitTransfer, self).get_prev_errors(all_inputs, all_errors, outputs) * transfer.dlogit(outputs)


class GaussianTransfer(transfer.GaussianTransfer):
    def get_prev_errors(self, all_inputs, all_errors, outputs):
        return super(GaussianTransfer, self).get_prev_errors(all_inputs, all_errors, outputs) * transfer.dgaussian_vec(outputs)
