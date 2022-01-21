import numpy as np
from typing import Tuple

from autoarray import numba_util

from autofit import exc


def reg_split_from(
    splitted_mappings: np.ndarray,
    splitted_sizes: np.ndarray,
    splitted_weights: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    For each source pixel centre which has already been split into a cross of four points (whose size is based on the
    area of the source pixel) this function applies the weights of each cross, where a weight is given by the distance
    of each point to the source pixel centre.

    There are cases where a grid has over 100 neighbors, corresponding to very coordinate transformations. In such
    extreme cases, we raise a `exc.FitException`.

    Parameters
    ----------
    splitted_mappings
    splitted_sizes
    splitted_weights

    Returns
    -------

    """

    max_j = np.shape(splitted_weights)[1] - 1

    splitted_weights *= -1.0

    for i in range(len(splitted_mappings)):

        pixel_index = i // 4

        flag = 0

        for j in range(splitted_sizes[i]):

            if splitted_mappings[i][j] == pixel_index:
                splitted_weights[i][j] += 1.0
                flag = 1

            if j >= max_j:
                raise exc.FitException("neighbours exceeds!")

        if flag == 0:
            splitted_mappings[i][j + 1] = pixel_index
            splitted_sizes[i] += 1
            splitted_weights[i][j + 1] = 1.0

    return splitted_mappings, splitted_sizes, splitted_weights


@numba_util.jit()
def constant_regularization_matrix_from(
    coefficient: float, pixel_neighbors: np.ndarray, pixel_neighbors_sizes: np.ndarray
) -> np.ndarray:
    """
    From the pixel-neighbors array, setup the regularization matrix using the instance regularization scheme.

    A complete description of regularizatin and the ``regularization_matrix`` can be found in the ``Regularization``
    class in the module ``autoarray.inversion.regularization``.

    Parameters
    ----------
    coefficients
        The regularization coefficients which controls the degree of smoothing of the inversion reconstruction.
    pixel_neighbors
        An array of length (total_pixels) which provides the index of all neighbors of every pixel in
        the Voronoi grid (entries of -1 correspond to no neighbor).
    pixel_neighbors_sizes
        An array of length (total_pixels) which gives the number of neighbors of every pixel in the
        Voronoi grid.

    Returns
    -------
    np.ndarray
        The regularization matrix computed using a constant regularization scheme where the effective regularization
        coefficient of every source pixel is the same.
    """

    pixels = len(pixel_neighbors)

    regularization_matrix = np.zeros(shape=(pixels, pixels))

    regularization_coefficient = coefficient ** 2.0

    for i in range(pixels):
        regularization_matrix[i, i] += 1e-8
        for j in range(pixel_neighbors_sizes[i]):
            neighbor_index = pixel_neighbors[i, j]
            regularization_matrix[i, i] += regularization_coefficient
            regularization_matrix[i, neighbor_index] -= regularization_coefficient

    return regularization_matrix


@numba_util.jit()
def constant_pixel_splitted_regularization_matrix_from(
    coefficient: float, splitted_mappings, splitted_sizes, splitted_weights
) -> np.ndarray:

    pixels = int(len(splitted_mappings) / 4)

    regularization_matrix = np.zeros(shape=(pixels, pixels))

    regularization_coefficient = coefficient ** 2.0

    for i in range(pixels):

        regularization_matrix[i, i] += 2e-8

        for j in range(4):

            k = i * 4 + j

            temp_size = splitted_sizes[k]
            temp_mapping = splitted_mappings[k]
            temp_weight = splitted_weights[k]

            for l in range(temp_size):
                for m in range(temp_size - l):
                    regularization_matrix[temp_mapping[l], temp_mapping[l + m]] += (
                        temp_weight[l] * temp_weight[l + m] * regularization_coefficient
                    )
                    regularization_matrix[temp_mapping[l + m], temp_mapping[l]] += (
                        temp_weight[l] * temp_weight[l + m] * regularization_coefficient
                    )

    for i in range(pixels):
        regularization_matrix[i, i] /= 2.0

    return regularization_matrix


def adaptive_regularization_weights_from(
    inner_coefficient: float, outer_coefficient: float, pixel_signals: np.ndarray
) -> np.ndarray:
    """
    Returns the regularization weight_list (the effective regularization coefficient of every pixel). They are computed
    using the pixel-signal of each pixel.

    Two regularization coefficients are used, corresponding to the:

    1) (pixel_signals) - pixels with a high pixel-signal (i.e. where the signal is located in the pixelization).
    2) (1.0 - pixel_signals) - pixels with a low pixel-signal (i.e. where the signal is not located in the
     pixelization).

    Parameters
    ----------
    coefficients
        The regularization coefficients which controls the degree of smoothing of the inversion reconstruction.
    pixel_signals
        The estimated signal in every pixelization pixel, used to change the regularization weighting of high signal
        and low signal pixelizations.

    Returns
    -------
    np.ndarray
        The weight_list of the adaptive regularization scheme which act as the effective regularization coefficients of
        every source pixel.
    """
    return (
        inner_coefficient * pixel_signals + outer_coefficient * (1.0 - pixel_signals)
    ) ** 2.0


@numba_util.jit()
def weighted_regularization_matrix_from(
    regularization_weights: np.ndarray,
    pixel_neighbors: np.ndarray,
    pixel_neighbors_sizes: np.ndarray,
) -> np.ndarray:
    """
    From the pixel-neighbors, setup the regularization matrix using the weighted regularization scheme.

    Parameters
    ----------
    regularization_weights
        The regularization_ weight of each pixel, which governs how much smoothing is applied to that individual pixel.
    pixel_neighbors
        An array of length (total_pixels) which provides the index of all neighbors of every pixel in
        the Voronoi grid (entries of -1 correspond to no neighbor).
    pixel_neighbors_sizes
        An array of length (total_pixels) which gives the number of neighbors of every pixel in the
        Voronoi grid.

    Returns
    -------
    np.ndarray
        The regularization matrix computed using an adaptive regularization scheme where the effective regularization
        coefficient of every source pixel is different.
    """

    pixels = len(regularization_weights)

    regularization_matrix = np.zeros(shape=(pixels, pixels))

    regularization_weight = regularization_weights ** 2.0

    for i in range(pixels):
        regularization_matrix[i, i] += 1e-8
        for j in range(pixel_neighbors_sizes[i]):
            neighbor_index = pixel_neighbors[i, j]
            regularization_matrix[i, i] += regularization_weight[neighbor_index]
            regularization_matrix[
                neighbor_index, neighbor_index
            ] += regularization_weight[neighbor_index]
            regularization_matrix[i, neighbor_index] -= regularization_weight[
                neighbor_index
            ]
            regularization_matrix[neighbor_index, i] -= regularization_weight[
                neighbor_index
            ]

    return regularization_matrix


# @numba_util.jit()
def weighted_pixel_splitted_regularization_matrix_from(
    regularization_weights: np.ndarray,
    splitted_mappings,
    splitted_sizes,
    splitted_weights,
) -> np.ndarray:

    # I'm not sure what is the best way to add surface brightness weight to the regularization scheme here.
    # Currently, I simply mulitply the i-th weight to the i-th source pixel, but there should be different ways.
    # Need to keep an eye here.

    pixels = int(len(splitted_mappings) / 4)

    regularization_matrix = np.zeros(shape=(pixels, pixels))

    regularization_weight = regularization_weights ** 2.0

    for i in range(pixels):

        regularization_matrix[i, i] += 2e-8

        for j in range(4):

            k = i * 4 + j

            temp_size = splitted_sizes[k]
            temp_mapping = splitted_mappings[k]
            temp_weight = splitted_weights[k]

            for l in range(temp_size):
                for m in range(temp_size - l):
                    regularization_matrix[temp_mapping[l], temp_mapping[l + m]] += (
                        temp_weight[l] * temp_weight[l + m] * regularization_weight[i]
                    )
                    regularization_matrix[temp_mapping[l + m], temp_mapping[l]] += (
                        temp_weight[l] * temp_weight[l + m] * regularization_weight[i]
                    )

    for i in range(pixels):
        regularization_matrix[i, i] /= 2.0

    return regularization_matrix
