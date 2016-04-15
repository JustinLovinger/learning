from pynn import network

class SetOutputLayer(network.Layer):
    def __init__(self, output):
        super(SetOutputLayer, self).__init__()

        self.output = output

    def activate(self, inputs):
        return self.output

    def reset(self):
        pass

    def update(self, inputs, outputs, errors):
        pass

def approx_equal(a, b, tol=0.001):
    """Check if two numbers are about the same.

    Useful to correct for floating point errors.
    """
    return abs(a - b) < tol