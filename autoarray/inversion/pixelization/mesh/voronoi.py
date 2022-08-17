import copy
import numpy as np
from typing import Dict, Optional, Tuple

from autoarray.structures.grids.uniform_2d import Grid2D
from autoarray.structures.grids.sparse_2d import Grid2DSparse
from autoarray.structures.mesh.voronoi_2d import Mesh2DVoronoi
from autoarray.inversion.pixelization.mesh.triangulation import Triangulation
from autoarray.inversion.pixelization.settings import SettingsPixelization

from autoarray.numba_util import profile_func


class Voronoi(Triangulation):
    def __init__(self):
        """
        A mesh associates a 2D grid of (y,x) coordinates (which are expected to be aligned with a masked
        dataset) with a 2D grid of pixels. The Voronoi mesh represents pixels as an irregular grid of Voronoi
        cells which can form any shape, size or tesselation.

        Both of these grids (e.g. the masked dataset's 2D grid and the grid of the Voronoi mesh's pixels)
        have (y,x) coordinates in two reference frames:

        - `data`: the original reference frame of the masked data.

        - `source`: a reference frame where grids in the `data` reference frame are transformed to a new reference
        frame (e.g. their (y,x) coordinates may be shifted, stretched or have a more complicated operation performed
        on them).

        The grid associated with the masked dataset and Voronoi mesh have the following variable names:

        - `grid_slim`: the (y,x) grid of coordinates of the original masked data (which can be in the data frame and
        given the variable name `data_grid_slim` or in the transformed source frame with the variable
        name `source_grid_slim`).

        - `mesh_grid`: the (y,x) grid of Voronoi pixels which are associated with the `grid_slim` (y,x)
        coordinates (association is always performed in the `source` reference frame).

        A Voronoi mesh has four grids associated with it: `data_grid_slim`, `source_grid_slim`,
        `data_mesh_grid` and `source_mesh_grid`.

        If a transformation of coordinates is not applied, the `data` frame and `source` frames are identical.

        Each (y,x) coordinate in the `source_grid_slim` is associated with the Voronoi pixel whose centre is its
        nearest neighbor. Voronoi pixelizations do not use a weighted interpolation scheme (unlike the `Delaunay`)
        mesh.

        In the project `PyAutoLens`, one's data is a masked 2D image. Its `data_grid_slim` is a 2D grid where every
        (y,x) coordinate is aligned with the centre of every unmasked image pixel. A "lensing operation" transforms
        this grid of (y,x) coordinates from the `data` frame to a new grid of (y,x) coordinates in the `source` frame.
        The mesh is then applied in the source frame.. In lensing terminology, the `data` frame is
        the `image-plane` and `source` frame the `source-plane`.
        """
        super().__init__()

    @property
    def uses_interpolation(self):
        return False

    @profile_func
    def mesh_grid_from(
        self,
        source_grid_slim=None,
        source_mesh_grid=None,
        sparse_index_for_slim_index=None,
    ) -> Mesh2DVoronoi:
        """
        Return the Voronoi `source_mesh_grid` as a `Mesh2DVoronoi` object, which provides additional
        functionality for performing operations that exploit the geometry of a Voronoi pixelization.

        The array `sparse_index_for_slim_index` encodes the closest source pixel of every pixel on the
        (full resolution) sub image-plane grid. This is used for efficiently pairing every image-plane pixel to its
        corresponding source-plane pixel.

        Parameters
        ----------
        source_grid_slim
            A 2D grid of (y,x) coordinates associated with the unmasked 2D data after it has been transformed to the
            `source` reference frame.
        source_mesh_grid
            The centres of every Voronoi pixel in the `source` frame, which are initially derived by computing a sparse
            set of (y,x) coordinates computed from the unmasked data in the `data` frame and applying a transformation
            to this.
        settings
            Settings controlling the pixelization for example if a border is used to relocate its exterior coordinates.
        """

        return Mesh2DVoronoi(
            grid=source_mesh_grid,
            nearest_pixelization_index_for_slim_index=sparse_index_for_slim_index,
            uses_interpolation=self.uses_interpolation,
        )


class VoronoiMagnification(Voronoi):
    def __init__(self, shape: Tuple[int, int] = (3, 3)):
        """
        A pixelization associates a 2D grid of (y,x) coordinates (which are expected to be aligned with a masked
        dataset) with a 2D grid of pixels.

        The Voronoi pixelization represents pixels as an irregular grid of Voronoi cells which can form any shape,
        size or tesselation.

        Both of these grids (e.g. the masked dataset's 2D grid and the grid of the Voronoi pixelization's pixels)
        have (y,x) coordinates in two reference frames:

        - `data`: the original reference frame of the masked data.

        - `source`: a reference frame where grids in the `data` reference frame are transformed to a new reference
        frame (e.g. their (y,x) coordinates may be shifted, stretched or have a more complicated operation performed
        on them).

        The grid associated with the masked dataset and Voronoi pixelization have the following variable names:

        - `grid_slim`: the (y,x) grid of coordinates of the original masked data (which can be in the data frame and
        given the variable name `data_grid_slim` or in the transformed source frame with the variable
        name `source_grid_slim`).

        - `mesh_grid`: the (y,x) grid of Voronoi pixels which are associated with the `grid_slim` (y,x)
        coordinates (association is always performed in the `source` reference frame).

        A Voronoi pixelization has four grids associated with it: `data_grid_slim`, `source_grid_slim`,
        `data_mesh_grid` and `source_mesh_grid`.

        If a transformation of coordinates is not applied, the `data` frame and `source` frames are identical.

        The (y,x) coordinates of the `source_mesh_grid` represent the centres of the Voronoi pixels on the
        Voronoi mesh.

        Each (y,x) coordinate in the `source_grid_slim` is associated with the Voronoi pixel whose centre is its
        nearest neighbor. Voronoi pixelizations do not use a weighted interpolation scheme (unlike the `Delaunay`)
        pixelization.

        For the `VoronoiMagnification` pixelization the centres of the Voronoi grid are derived in the `data` frame,
        by overlaying a uniform grid with the input `shape` over the masked data's grid. All coordinates in this
        uniform grid which are contained within the mask are kept, have the same transformation applied to them as the
        masked data's grid to map them to the source frame, where they form the pixelization's Voronoi pixel centres.

        In the project `PyAutoLens`, one's data is a masked 2D image. Its `data_grid_slim` is a 2D grid where every
        (y,x) coordinate is aligned with the centre of every unmasked image pixel. A "lensing operation" transforms
        this grid of (y,x) coordinates from the `data` frame to a new grid of (y,x) coordinates in the `source` frame.
        The pixelization is then applied in the source frame.. In lensing terminology, the `data` frame is
        the `image-plane` and `source` frame the `source-plane`.

        Parameters
        ----------
        shape
            The shape of the unmasked `mesh_grid` in the `data` frame which is laid over the masked image, in
            order to derive the centres of the Voronoi pixels in the `data` frame.
        """
        super().__init__()

        self.shape = (int(shape[0]), int(shape[1]))
        self.pixels = self.shape[0] * self.shape[1]

    def data_mesh_grid_from(
        self,
        data_grid_slim: Grid2D,
        hyper_data: np.ndarray = None,
        settings=SettingsPixelization(),
    ) -> Grid2DSparse:
        """
        Computes the `mesh_grid` in the `data` frame, by overlaying a uniform grid of coordinates over the
        masked 2D data (see `Grid2DSparse.from_grid_and_unmasked_2d_grid_shape()`).

        For a `VoronoiMagnification` this grid is computed by overlaying a 2D grid with dimensions `shape` over the
        masked 2D data in the `data` frame, whereby all (y,x) coordinates in this grid which are not masked are
        retained.

        Parameters
        ----------
        data_mesh_grid
            The sparse set of (y,x) coordinates computed from the unmasked data in the `data` frame. This has a
            transformation applied to it to create the `source_mesh_grid`.
        hyper_data
            An image which is used to determine the `data_mesh_grid` and therefore adapt the distribution of
            pixels of the Voronoi grid to the data it discretizes.
        settings
            Settings controlling the pixelization for example if a border is used to relocate its exterior coordinates.
        """
        return Grid2DSparse.from_grid_and_unmasked_2d_grid_shape(
            grid=data_grid_slim, unmasked_sparse_shape=self.shape
        )


class VoronoiBrightnessImage(Voronoi):
    def __init__(self, pixels=10, weight_floor: float = 0.0, weight_power: float = 0.0):
        """
        A pixelization associates a 2D grid of (y,x) coordinates (which are expected to be aligned with a masked
        dataset) with a 2D grid of pixels. The Voronoi pixelization represents pixels as an irregular grid of Voronoi
        cells which can form any shape, size or tesselation.

        Both of these grids (e.g. the masked dataset's 2D grid and the grid of the Voronoi pixelization's pixels)
        have (y,x) coordinates in two reference frames:

        - `data`: the original reference frame of the masked data.

        - `source`: a reference frame where grids in the `data` reference frame are transformed to a new reference
        frame (e.g. their (y,x) coordinates may be shifted, stretched or have a more complicated operation performed
        on them).

        The grid associated with the masked dataset and Voronoi pixelization have the following variable names:

        - `grid_slim`: the (y,x) grid of coordinates of the original masked data (which can be in the data frame and
        given the variable name `data_grid_slim` or in the transformed source frame with the variable
        name `source_grid_slim`).

        - `mesh_grid`: the (y,x) grid of Voronoi pixels which are associated with the `grid_slim` (y,x)
        coordinates (association is always performed in the `source` reference frame).

        A Voronoi pixelization has four grids associated with it: `data_grid_slim`, `source_grid_slim`,
        `data_mesh_grid` and `source_mesh_grid`.

        If a transformation of coordinates is not applied, the `data` frame and `source` frames are identical.

        Each (y,x) coordinate in the `source_grid_slim` is associated with the Voronoi pixel whose centre is its
        nearest neighbor. Voronoi pixelizations do not use a weighted interpolation scheme (unlike the `Delaunay`)
        pixelization.

        For the `VoronoiBrightnessImage` pixelization the centres of the Voronoi grid are derived in the `data` frame,
        by applying a KMeans clustering algorithm to the masked data's values. These values are use compute `pixels`
        number of pixels, where the `weight_floor` and `weight_power` allow the KMeans algorithm to adapt the derived
        pixel centre locations to the data's brighest or faintest values.

        In the project `PyAutoLens`, one's data is a masked 2D image. Its `data_grid_slim` is a 2D grid where every
        (y,x) coordinate is aligned with the centre of every unmasked image pixel. A "lensing operation" transforms
        this grid of (y,x) coordinates from the `data` frame to a new grid of (y,x) coordinates in the `source` frame.
        The pixelization is then applied in the source frame.. In lensing terminology, the `data` frame is
        the `image-plane` and `source` frame the `source-plane`.

        Parameters
        ----------
        pixels
            The total number of pixels in the Voronoi pixelization, which is therefore also the number of (y,x)
            coordinates computed via the KMeans clustering algorithm in data frame.
        weight_floor
            A parameter which reweights the data values the KMeans algorithm is applied too; as the floor increases
            more weight is applied to values with lower values thus allowing Voronoi pixels to be placed in these
            regions of the data.
        weight_power
            A parameter which reweights the data values the KMeans algorithm is applied too; as the power increases
            more weight is applied to values with higher values thus allowing Voronoi pixels to be placed in these
            regions of the data.
        """
        super().__init__()

        self.pixels = int(pixels)
        self.weight_floor = weight_floor
        self.weight_power = weight_power

    def weight_map_from(self, hyper_data: np.ndarray) -> np.ndarray:
        """
        Computes a `weight_map` from an input `hyper_data`, where this image represents components in the masked 2d
        data in the `data` frame. This applies the `weight_floor` and `weight_power` attributes of the class, which
        scale the weights to make different components upweighted relative to one another.

        Parameters
        ----------
        hyper_data
            A image which represents one or more components in the masked 2D data in the `data` frame.

        Returns
        -------
        The weight map which is used to adapt the Voronoi pixels in the `data` frame to components in the data.
        """
        weight_map = (hyper_data - np.min(hyper_data)) / (
            np.max(hyper_data) - np.min(hyper_data)
        ) + self.weight_floor * np.max(hyper_data)

        return np.power(weight_map, self.weight_power)

    def data_mesh_grid_from(
        self,
        data_grid_slim: Grid2D,
        hyper_data: np.ndarray,
        settings=SettingsPixelization(),
    ):
        """
        Computes the `mesh_grid` in the `data` frame, by overlaying a uniform grid of coordinates over the
        masked 2D data (see `Grid2DSparse.from_grid_and_unmasked_2d_grid_shape()`).

        The `data_pixelization_grid` is transformed to the `source_mesh_grid`, and it is these (y,x) values
        which then act the centres of the Voronoi pixelization's pixels.

        For a `VoronoiBrightnessImage` this grid is computed by applying a KMeans clustering algorithm to the masked
        data's values, where these values are reweighted by the `hyper_data` so that the algorithm can adapt to
        specific parts of the data.

        Parameters
        ----------
        data_mesh_grid
            The sparse set of (y,x) coordinates computed from the unmasked data in the `data` frame. This has a
            transformation applied to it to create the `source_mesh_grid`.
        hyper_data
            An image which is used to determine the `data_mesh_grid` and therefore adapt the distribution of
            pixels of the Voronoi grid to the data it discretizes.
        settings
            Settings controlling the pixelization for example if a border is used to relocate its exterior coordinates.
        """
        weight_map = self.weight_map_from(hyper_data=hyper_data)

        return Grid2DSparse.from_total_pixels_grid_and_weight_map(
            total_pixels=self.pixels,
            grid=data_grid_slim,
            weight_map=weight_map,
            seed=settings.kmeans_seed,
            stochastic=settings.is_stochastic,
        )

    @property
    def is_stochastic(self) -> bool:
        return True