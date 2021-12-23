import itertools
import numpy as np
from typing import Dict, List, Optional

from autoconf import cached_property

from autoarray.inversion.linear_obj import LinearObj
from autoarray.inversion.linear_obj import UniqueMappings
from autoarray.structures.grids.two_d.grid_2d_pixelization import Grid2DRectangular
from autoarray.structures.grids.two_d.grid_2d_pixelization import Grid2DDelaunay
from autoarray.structures.grids.two_d.grid_2d_pixelization import Grid2DVoronoi

from autoarray.numba_util import profile_func
from autoarray.inversion.mappers import mapper_util


class AbstractMapper(LinearObj):
    def __init__(
        self,
        source_grid_slim,
        source_pixelization_grid,
        data_pixelization_grid=None,
        hyper_image=None,
        profiling_dict: Optional[Dict] = None,
    ):
        """
        To understand a `Mapper` one must be familiar `Pixelization` objects and the `pixelization` package, where
        the following four grids are explained: `data_grid_slim`, `source_grid_slim`, `data_pixelization_grid` and
        `source_pixelization_grid`. If you are not familiar with these grids, read the docstrings of the
        `pixelization` package first.

        A `Mapper` determines the mappings between the masked data grid's pixels (`data_grid_slim` and
        `source_grid_slim`) and the pxelization's pixels (`data_pixelization_grid` and `source_pixelization_grid`).

        The 1D Indexing of each grid is identical in the `data` and `source` frames (e.g. the transformation does not
        change the indexing, such that `source_grid_slim[0]` corresponds to the transformed value
        of `data_grid_slim[0]` and so on).

        A mapper therefore only needs to determine the index mappings between the `grid_slim` and `pixelization_grid`,
        noting that associations are made by pairing `source_pixelization_grid` with `source_grid_slim`.

        Mappings are represented in the 2D ndarray `pix_indexes_for_sub_slim_index`, whereby the index of
        a pixel on the `pixelization_grid` maps to the index of a pixel on the `grid_slim` as follows:

        - pix_indexes_for_sub_slim_index[0, 0] = 0: the data's 1st sub-pixel (index 0) maps to the
        pixelization's 1st pixel (index 0).
        - pix_indexes_for_sub_slim_index[1, 0] = 3: the data's 2nd sub-pixel (index 1) maps to the
        pixelization's 4th pixel (index 3).
        - pix_indexes_for_sub_slim_index[2, 0] = 1: the data's 3rd sub-pixel (index 2) maps to the
        pixelization's 2nd pixel (index 1).

        The second dimension of this array (where all three examples above are 0) is used for cases where a
        single pixel on the `grid_slim` maps to multiple pixels on the `pixelization_grid`. For example, using a
        `Delaunay` pixelization, where every `grid_slim` pixel maps to three Delaunay pixels (the corners of the
        triangles):

        - pix_indexes_for_sub_slim_index[0, 0] = 0: the data's 1st sub-pixel (index 0) maps to the
        pixelization's 1st pixel (index 0).
        - pix_indexes_for_sub_slim_index[0, 1] = 3: the data's 1st sub-pixel (index 0) also maps to the
        pixelization's 2nd pixel (index 3).
        - pix_indexes_for_sub_slim_index[0, 2] = 5: the data's 1st sub-pixel (index 0) also maps to the
        pixelization's 6th pixel (index 5).

        The mapper allows us to create a mapping matrix, which is a matrix representing the mapping between every
        unmasked data pixel annd the pixels of a pixelization. This matrix is the basis of performing an `Inversion`,
        which reconstructs the data using the `source_pixelization_grid`.

        Parameters
        ----------
        source_grid_slim
            A 2D grid of (y,x) coordinates associated with the unmasked 2D data after it has been transformed to the
            `source` reference frame.
        source_pixelization_grid
            The 2D grid of (y,x) centres of every pixelization pixel in the `source` frame.
        data_pixelization_grid
            The sparse set of (y,x) coordinates computed from the unmasked data in the `data` frame. This has a
            transformation applied to it to create the `source_pixelization_grid`.
        hyper_image
            An image which is used to determine the `data_pixelization_grid` and therefore adapt the distribution of
            pixels of the Delaunay grid to the data it discretizes.
        profiling_dict
            A dictionary which contains timing of certain functions calls which is used for profiling.
        """

        self.source_grid_slim = source_grid_slim
        self.source_pixelization_grid = source_pixelization_grid
        self.data_pixelization_grid = data_pixelization_grid

        self.hyper_image = hyper_image
        self.profiling_dict = profiling_dict

    @property
    def pixels(self) -> int:
        return self.source_pixelization_grid.pixels

    @property
    def slim_index_for_sub_slim_index(self) -> np.ndarray:
        return self.source_grid_slim.mask.slim_index_for_sub_slim_index

    @property
    def pix_indexes_for_sub_slim_index(self) -> "PixForSub":
        raise NotImplementedError

    @cached_property
    @profile_func
    def pix_weights_for_sub_slim_index(self) -> np.ndarray:
        raise NotImplementedError

    @property
    def sub_slim_indexes_for_pix_index(self) -> List[List]:
        """
        Returns the index mappings between each of the pixelization's pixels and the masked data's sub-pixels.

        Given that even pixelization pixel maps to multiple data sub-pixels, index mappings are returned as a list of
        lists where the first entries are the pixelization index and second entries store the data sub-pixel indexes.

        For example, if `sub_slim_indexes_for_pix_index[2][4] = 10`, the pixelization pixel with index 2
        (e.g. `pixelization_grid[2,:]`) has a mapping to a data sub-pixel with index 10 (e.g. `grid_slim[10, :]).

        This is effectively a reversal of the array `pix_indexes_for_sub_slim_index`.
        """
        sub_slim_indexes_for_pix_index = [[] for _ in range(self.pixels)]

        pix_indexes_for_sub_slim_index = self.pix_indexes_for_sub_slim_index.mappings
        sizes = self.pix_indexes_for_sub_slim_index.sizes

        for slim_index, pix_index in enumerate(pix_indexes_for_sub_slim_index):
            for k in range(sizes[slim_index]):
                sub_slim_indexes_for_pix_index[pix_index[k]].append(slim_index)

        return sub_slim_indexes_for_pix_index

    @cached_property
    @profile_func
    def data_unique_mappings(self) -> "UniqueMappings":
        """
        Returns the unique mappings of every unmasked data pixel's (e.g. `grid_slim`) sub-pixels (e.g. `grid_sub_slim`)
        to their corresponding pixelization pixels (e.g. `pixelization_grid`).

        A full description of these mappings is given in the
        function `mapper_util.data_slim_to_pixelization_unique_from()`.

        For convenience, these mappings and associated metadata are packaged into the class `UniqueMappings`.

        To perform an `Inversion` efficiently the linear algebra can be expressed using what it called the w-tilde
        formalism, which uses these unique mappings to perform certain calculations efficiently.
        """

        (
            data_to_pix_unique,
            data_weights,
            pix_lengths,
        ) = mapper_util.data_slim_to_pixelization_unique_from(
            data_pixels=self.source_grid_slim.shape_slim,
            pix_indexes_for_sub_slim_index=self.pix_indexes_for_sub_slim_index.mappings,
            pix_indexes_for_sub_slim_sizes=self.pix_indexes_for_sub_slim_index.sizes,
            pix_weights_for_sub_slim_index=self.pix_weights_for_sub_slim_index,
            sub_size=self.source_grid_slim.sub_size,
        )

        return UniqueMappings(
            data_to_pix_unique=data_to_pix_unique,
            data_weights=data_weights,
            pix_lengths=pix_lengths,
        )

    @cached_property
    @profile_func
    def mapping_matrix(self) -> np.ndarray:
        """
        The `mapping_matrix` is a matrix that represents the image-pixel to pixelization-pixel mappings above in a
        2D matrix. It in the following paper as matrix `f` https://arxiv.org/pdf/astro-ph/0302587.pdf.

        A full description is given in `mapper_util.mapping_matrix_from()`.
        """
        return mapper_util.mapping_matrix_from(
            pix_weights_for_sub_slim_index=self.pix_weights_for_sub_slim_index,
            pixels=self.pixels,
            total_mask_sub_pixels=self.source_grid_slim.mask.pixels_in_mask,
            slim_index_for_sub_slim_index=self.slim_index_for_sub_slim_index,
            pix_indexes_for_sub_slim_index=self.pix_indexes_for_sub_slim_index.mappings,
            pix_size_for_sub_slim_index=self.pix_indexes_for_sub_slim_index.sizes,
            sub_fraction=self.source_grid_slim.mask.sub_fraction,
        )

    def pixel_signals_from(self, signal_scale) -> np.ndarray:
        """
        Returns the (hyper) signal in each pixelization pixel, where this signal is an estimate of the expected signal
        each pixelization pixel contains given the data pixels it maps too.

        A full description of this is given in the function `mapper_util.adaptive_pixel_signals_from().
        """
        return mapper_util.adaptive_pixel_signals_from(
            pixels=self.pixels,
            signal_scale=signal_scale,
            pixel_weights=self.pix_weights_for_sub_slim_index,
            pix_indexes_for_sub_slim_index=self.pix_indexes_for_sub_slim_index.mappings,
            pix_size_for_sub_slim_index=self.pix_indexes_for_sub_slim_index.sizes,
            slim_index_for_sub_slim_index=self.source_grid_slim.mask.slim_index_for_sub_slim_index,
            hyper_image=self.hyper_image,
        )

    def pix_indexes_for_slim_indexes(self, pix_indexes) -> List[List]:

        image_for_source = self.sub_slim_indexes_for_pix_index

        if not any(isinstance(i, list) for i in pix_indexes):
            return list(
                itertools.chain.from_iterable(
                    [image_for_source[index] for index in pix_indexes]
                )
            )
        else:
            indexes = []
            for source_pixel_index_list in pix_indexes:
                indexes.append(
                    list(
                        itertools.chain.from_iterable(
                            [
                                image_for_source[index]
                                for index in source_pixel_index_list
                            ]
                        )
                    )
                )
            return indexes


class PixForSub:
    def __init__(self, mappings, sizes):
        """
        Packages the following two quantities of the ndarray `pix_indexes_for_sub_slim_index`:

        - `mappings`: the mapping of every `sub_slim_index` to the `pix_indexes`.
        - `sizes`: the number of `pix_indexes` each `sub_slim_index` maps too.

        The need to store separately the mappings and sizes is so that the `sizes` can be easy iterated over when
        perform calculations for efficiency.

        See the mapper properties `pix_indexes_for_sub_slim_index()` for a description of the mappings array.

        Parameters
        ----------
        mappings
            The mappings of the masked data's sub-pixels to the pixelization's pixels.
        sizes
            The number of pixelizaiton pixels each masked data sub-pixel maps too.
        """
        self.mappings = mappings
        self.sizes = sizes
