import numpy as np

from autolens.model.inversion.util import regularization_util

class Regularization(object):

    def __init__(self, coefficients=(1.0,)):
        """ Abstract base class for a regularization-scheme, which is applied to a pixelization to enforce a \
        smooth-source solution and prevent over-fitting noise_map in the hyper. This is achieved by computing a \
        'regularization term' - which is the sum of differences in reconstructed flux between every set of neighboring \
        pixels. This regularization term is added to the solution's chi-squared as a penalty term. This effects \
        a pixelization in the following ways:

        1) The regularization matrix (see below) is added to the curvature matrix used by the inversion to \
           linearly invert and fit the hyper. Thus, it changes the pixelization in a linear manner, ensuring that \
           the minimum chi-squared solution is achieved accounting for the penalty term.

        2) The likelihood of the pixelization's fit to the hyper changes from L = -0.5 *(chi^2 + noise_normalization) \
           to L = -0.5 (chi^2 + coefficients * regularization_term + noise_normalization). The regularization \
           coefficient is a 'hyper-parameter' which determines how strongly we smooth the pixelization's reconstruction.

        The value of the coefficients(s) is set using the Bayesian framework of (Suyu 2006) and this \
        is described further in the (*inversion.Inversion* class).

        The regularization matrix, H, is calculated by defining a set of B matrices which describe how the \
        pixels neighbor one another. For example, lets take a 3x3 square grid:
        ______
        |0|1|2|
        |3|4|5|
        |6|7|8|
        ^^^^^^^

        We want to regularize this grid such that each pixel is regularized with the pixel to its right and below it \
        (provided there are pixels in that direction). This means that:

        - pixel 0 is regularized with pixel 1 (to the right) and pixel 3 (below).
        - pixel 1 is regularized with pixel 2 (to the right) and pixel 4 (below),
        - Pixel 2 is only regularized with pixel 5, as there is no pixel to its right.
        - and so on.

        We make two 9 x 9 B matrices, which describe regularization in each direction (i.e. rightwards and downwards). \
        We simply put a -1 and 1 in each row of a pixel index where it has a neighbor, where the value 1 goes in the \
        column of its neighbor's index. Thus, the B matrix describing neighboring pixels to their right looks like:

        B_x = [-1,  1,  0,  0,  0,  0,  0,  0,  0] # [0->1]
              [ 0, -1,  1,  0,  0,  0,  0,  0,  0] # [1->2]
              [ 0,  0, -1,  0,  0,  0,  0,  0,  0] # [] NOTE - no pixel neighbor.
              [ 0,  0,  0, -1,  1,  0,  0,  0,  0] # [3->4]
              [ 0,  0,  0,  0, -1,  1,  0,  0,  0] # [4->5]
              [ 0,  0,  0,  0,  0, -1,  0,  0,  0] # [] NOTE - no pixel neighbor.
              [ 0,  0,  0,  0,  0,  0, -1,  1,  0] # [6->7]
              [ 0,  0,  0,  0,  0,  0,  0, -1,  1] # [7->8]
              [ 0,  0,  0,  0,  0,  0,  0,  0, -1] # [] NOTE - no pixel neighbor.

        We now make another B matrix for the regularization downwards:

        B_y = [-1,  0,  0,  1,  0,  0,  0,  0,  0] # [0->3]
              [ 0, -1,  0,  0,  1,  0,  0,  0,  0] # [1->4]
              [ 0,  0, -1,  0,  0,  1,  0,  0,  0] # [2->5]
              [ 0,  0,  0, -1,  0,  0,  1,  0,  0] # [3->6]
              [ 0,  0,  0,  0, -1,  0,  0,  1,  0] # [4->7]
              [ 0,  0,  0,  0,  0, -1,  0,  0,  1] # [5->8]
              [ 0,  0,  0,  0,  0,  0, -1,  0,  0] # [] NOTE - no pixel neighbor.
              [ 0,  0,  0,  0,  0,  0,  0, -1,  0] # [] NOTE - no pixel neighbor.
              [ 0,  0,  0,  0,  0,  0,  0,  0, -1] # [] NOTE - no pixel neighbor.

        After making the B matrices that represent our pixel neighbors, we can compute the regularization matrix, H, \
        of each direction as H = B * B.T (matrix multiplication).

        E.g.

        H_x = B_x.T, * B_x
        H_y = B_y.T * B_y
        H = H_x + H_y

        Whilst the example above used a square-grid with regularization to the right and downwards, this matrix \
        formalism can be extended to describe regularization in more directions (e.g. upwards, to the left).

        It can also describe irregular pixelizations, e.g. an irregular Voronoi pixelization, where a B matrix is \
        computed for every shared Voronoi vertex of each Voronoi pixel. The number of B matrices is now equal to the \
        number of Voronoi vertices in the pixel with the most Voronoi vertices. However, we describe below a scheme to \
        compute this solution more efficiently.

        ### COMBINING B MATRICES ###

        The B matrices above each had the -1's going down the diagonal. This is not necessary, and it is valid to put \
        each pixel pairing anywhere. So, if we had a 4x4 B matrix, where:

        - pixel 0 regularizes with pixel 1
        - pixel 2 regularizes with pixel 3
        - pixel 3 regularizes with pixel 0

        We can still set this up as one matrix (even though the pixel 0 comes up twice):

        B = [-1, 1,  0 , 0] # [0->1]
            [ 0, 0,  0 , 0] # We can skip rows by making them all zeros.
            [ 0, 0, -1 , 1] # [2->3]
            [ 1, 0,  0 ,-1] # [3->0] This is valid!

        So, for a Voronoi pixelzation, we don't have to make the same number of B matrices as Voronoi vertices,  \
        we can combine them into fewer B matrices as above.

        # SKIPPING THE B MATRIX CALCULATION #

        Infact, going through the rigmarole of computing and multiplying B matrices like this is uncessary. It is \
        more computationally efficiently to directly compute H. This is possible, provided you know know all of the \
        neighboring pixel pairs (which, by definition, you need to know to set up the B matrices anyway). Thus, the \
       'regularization_matrix_from_pixel_neighbors' functions in this module directly compute H from the pixel \
        neighbors.

        # POSITIVE DEFINITE MATRIX #

        The regularization matrix must be positive-definite, as the Bayesian framework of Suyu 2006 requires that we \
        use its determinant in the calculation.

        Parameters
        -----------
        shape : (int, int)
            The dimensions of the rectangular grid of pixels (x_pixels, y_pixel)
        coefficients : (float,)
            The regularization_matrix coefficients used to smooth the pix reconstructed_inversion_image.
            
        """
        self.coefficients = coefficients

    def regularization_matrix_from_pixel_neighbors(self, pixel_neighbors, pixel_neighbors_size):
        raise NotImplementedError("regularization_matrix_from_pixel_neighbors should be overridden")


class Constant(Regularization):

    def __init__(self, coefficients=(1.0,)):
        """A constant-regularization scheme (regularization is described in the *Regularization* class above).

        For the constant regularization_matrix scheme, there is only 1 regularization coefficient that is applied to \
        all neighboring pixels. This means that we when write B, we only need to regularize pixels in one direction \
        (e.g. pixel 0 regularizes pixel 1, but NOT visa versa). For example:

        B = [-1, 1]  [0->1]
            [0, -1]  1 does not regularization with 0

        A small numerical value of 1.0e-8 is added to all elements in a constant regularization matrix, to ensure that \
        it is positive definite.

        Parameters
        -----------
        coefficients : (float,)
            The regularization coefficient which controls the degree of smooth of the inversion reconstruction.
        """
        super(Constant, self).__init__(coefficients)

    def regularization_matrix_from_pixel_neighbors(self, pixel_neighbors, pixel_neighbors_size):
        return regularization_util.constant_regularization_matrix_from_pixel_neighbors(coefficients=self.coefficients,
               pixel_neighbors=pixel_neighbors, pixel_neighbors_size=pixel_neighbors_size)


class Weighted(Regularization):

    def __init__(self, coefficients=(1.0, 1.0), signal_scale=1.0):
        """ A constant-regularization scheme (regularization is described in the *Regularization* class above).

        For the weighted regularization scheme, each pixel is given an 'effective regularization weight', which is \
        applied when each set of pixel neighbors are regularized with one another. The motivation of this is that \
        different regions of a pixelization require different levels of regularization (e.g., high smoothing where the \
        no signal is present and less smoothing where it is, see (Nightingale, Dye and Massey 2018)).

        Unlike the constant regularization_matrix scheme, neighboring pixels must now be regularized with one another \
        in both directions (e.g. if pixel 0 regularizes pixel 1, pixel 1 must also regularize pixel 0). For example:

        B = [-1, 1]  [0->1]
            [-1, -1]  1 now also regularizes 0

        For a constant regularization coefficient this would NOT produce a positive-definite matrix. However, for
        the weighted scheme, it does!

        The regularize weights change the B matrix as shown below - we simply multiply each pixel's effective \
        regularization weight by each row of B it has a -1 in, so:

        regularization_weights = [1, 2, 3, 4]

        B = [-1, 1, 0 ,0] # [0->1]
            [0, -2, 2 ,0] # [1->2]
            [0, 0, -3 ,3] # [2->3]
            [4, 0, 0 ,-4] # [3->0]

        If our -1's werent down the diagonal this would look like:

        B = [4, 0, 0 ,-4] # [3->0]
            [0, -2, 2 ,0] # [1->2]
            [-1, 1, 0 ,0] # [0->1]
            [0, 0, -3 ,3] # [2->3] This is valid!

        Parameters
        -----------
        coefficients : (float, float)
            The regularization coefficients which controls the degree of smoothing of the inversion reconstruction in \
            high and low signal regions of the reconstruction.
        signal_scale : float
            A factor which controls how rapidly the smoothness of regularization varies from high signal regions to \
            low signal regions.
        """
        super(Weighted, self).__init__(coefficients)
        self.signal_scale = signal_scale

    def pixel_signals_from_images(self, pixels, regular_to_pix, galaxy_image):
        return regularization_util.weighted_pixel_signals_from_images(pixels=pixels, signal_scale=self.signal_scale,
                                                                      regular_to_pix=regular_to_pix,
                                                                      galaxy_image=galaxy_image)

    def regularization_weights_from_pixel_signals(self, pixel_signals):
        return regularization_util.weighted_regularization_weights_from_pixel_signals(coefficients=self.coefficients,
                                                                                      pixel_signals=pixel_signals)

    def regularization_matrix_from_pixel_neighbors(self, regularization_weights, pixel_neighbors, pixel_neighbors_size):
        return regularization_util.weighted_regularization_matrix_from_pixel_neighbors(
            regularization_weights=regularization_weights, pixel_neighbors=pixel_neighbors,
                                                 pixel_neighbors_size=pixel_neighbors_size)
