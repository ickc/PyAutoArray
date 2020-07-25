import logging

import numpy as np
import copy

from autoarray import exc
from autoarray.dataset import abstract_dataset, preprocess
from autoarray.mask import mask as msk
from autoarray.structures import arrays, grids, kernel
from autoarray.operators import convolver

logger = logging.getLogger(__name__)


class AbstractImaging(abstract_dataset.AbstractDataset):
    def __init__(self, image, noise_map, psf=None, positions=None, name=None):
        """A class containing the data, noise-map and point spread function of a 2D imaging dataset.

        Parameters
        ----------
        image : aa.Array
            The array of the image data, in units of electrons per second.
        noise_map : aa.Array
            An array describing the RMS standard deviation error in each pixel in units of electrons per second.
        psf : aa.Array
            An array describing the Point Spread Function kernel of the image.
        """

        super().__init__(
            data=image, noise_map=noise_map, positions=positions, name=name
        )

        self.psf = psf

    def __array_finalize__(self, obj):
        if isinstance(obj, Imaging):
            try:
                for key, value in obj.__dict__.items():
                    setattr(self, key, value)
            except AttributeError:
                logger.debug(
                    "Original object in Imaging.__array_finalize__ missing one or more attributes"
                )

    @property
    def shape_2d(self):
        return self.data.shape_2d

    @property
    def image(self):
        return self.data

    @property
    def pixel_scales(self):
        return self.data.pixel_scales

    def binned_from_bin_up_factor(self, bin_up_factor):

        imaging = copy.deepcopy(self)

        imaging.data = self.image.binned_from_bin_up_factor(
            bin_up_factor=bin_up_factor, method="mean"
        )
        imaging.psf = self.psf.rescaled_with_odd_dimensions_from_rescale_factor(
            rescale_factor=1.0 / bin_up_factor, renormalize=False
        )
        imaging.noise_map = (
            self.noise_map.binned_from_bin_up_factor(
                bin_up_factor=bin_up_factor, method="quadrature"
            )
            if self.noise_map is not None
            else None
        )

        return imaging

    def signal_to_noise_limited_from_signal_to_noise_limit(self, signal_to_noise_limit):

        imaging = copy.deepcopy(self)

        noise_map_limit = np.where(
            self.signal_to_noise_map > signal_to_noise_limit,
            np.abs(self.image) / signal_to_noise_limit,
            self.noise_map,
        )

        imaging.noise_map = arrays.Array.manual_mask(
            array=noise_map_limit,
            mask=self.image.mask,
            store_in_1d=self.noise_map.store_in_1d,
        )

        return imaging


class AbstractMaskedImaging(abstract_dataset.AbstractMaskedDataset):
    def __init__(
        self,
        imaging,
        mask,
        grid_class=grids.Grid,
        grid_inversion_class=grids.Grid,
        fractional_accuracy=0.9999,
        sub_steps=None,
        pixel_scales_interp=None,
        psf_shape_2d=None,
        inversion_pixel_limit=None,
        inversion_uses_border=True,
        renormalize_psf=True,
    ):
        """
        The lens dataset is the collection of data_type (image, noise-map, PSF), a mask, grid, convolver \
        and other utilities that are used for modeling and fitting an image of a strong lens.

        Whilst the image, noise-map, etc. are loaded in 2D, the lens dataset creates reduced 1D arrays of each \
        for lens calculations.

        Parameters
        ----------
        imaging: im.Imaging
            The imaging data_type all in 2D (the image, noise-map, PSF, etc.)
        mask: msk.Mask
            The 2D mask that is applied to the image.
        psf_shape_2d : (int, int)
            The shape of the PSF used for convolving model image generated using analytic light profiles. A smaller \
            shape will trim the PSF relative to the input image PSF, giving a faster analysis run-time.
        pixel_scales_interp : float
            If *True*, expensive to compute mass profile deflection angles will be computed on a sparse grid and \
            interpolated to the grid, sub and blurring grids.
        inversion_pixel_limit : int or None
            The maximum number of pixels that can be used by an inversion, with the limit placed primarily to speed \
            up run.
        """

        super().__init__(
            dataset=imaging,
            mask=mask,
            grid_class=grid_class,
            grid_inversion_class=grid_inversion_class,
            fractional_accuracy=fractional_accuracy,
            sub_steps=sub_steps,
            pixel_scales_interp=pixel_scales_interp,
            inversion_pixel_limit=inversion_pixel_limit,
            inversion_uses_border=inversion_uses_border,
        )

        self.image = arrays.Array.manual_mask(
            array=imaging.image.in_2d,
            mask=mask.mask_sub_1,
            store_in_1d=imaging.image.store_in_1d,
        )

        self.noise_map = arrays.Array.manual_mask(
            array=imaging.noise_map.in_2d,
            mask=mask.mask_sub_1,
            store_in_1d=imaging.noise_map.store_in_1d,
        )

        self.pixel_scales_interp = pixel_scales_interp

        ### PSF TRIMMING + CONVOLVER ###

        if imaging.psf is not None:

            if psf_shape_2d is None:
                self.psf_shape_2d = imaging.psf.shape_2d
            else:
                self.psf_shape_2d = psf_shape_2d

            self.psf = kernel.Kernel.manual_2d(
                array=imaging.psf.resized_from_new_shape(
                    new_shape=self.psf_shape_2d
                ).in_2d,
                renormalize=renormalize_psf,
            )

            self.convolver = convolver.Convolver(mask=mask, kernel=self.psf)

            if mask.pixel_scales is not None:

                self.blurring_grid = self.grid.blurring_grid_from_kernel_shape(
                    kernel_shape_2d=self.psf_shape_2d
                )

        else:

            self.psf = None

    @property
    def imaging(self):
        return self.dataset

    @property
    def data(self):
        return self.image

    def signal_to_noise_map(self):
        return self.image / self.noise_map

    def modify_image_and_noise_map(self, image, noise_map):

        masked_imaging = copy.deepcopy(self)

        masked_imaging.image = image
        masked_imaging.noise_map = noise_map

        return masked_imaging


class AbstractSimulatorImaging:
    def __init__(
        self,
        exposure_time_map=None,
        background_sky_map=None,
        psf=None,
        renormalize_psf=True,
        read_noise=None,
        add_noise=True,
        noise_if_add_noise_false=0.1,
        noise_seed=-1,
    ):
        """A class representing a Imaging observation, using the shape of the image, the pixel scale,
        psf, exposure time, etc.

        Parameters
        ----------
        shape_2d : (int, int)
            The shape of the observation. Note that we do not simulator a full Imaging frame (e.g. 2000 x 2000 pixels for \
            Hubble imaging), but instead just a cut-out around the strong lens.
        pixel_scales : float
            The size of each pixel in arc seconds.
        psf : PSF
            An arrays describing the PSF kernel of the image.
        exposure_time_map : float
            The exposure time of an observation using this data_type.
        background_sky_map : float
            The level of the background sky of an observationg using this data_type.
        """

        self.exposure_time_map = exposure_time_map

        if psf is not None and renormalize_psf:
            psf = psf.renormalized

        self.psf = psf
        self.background_sky_map = background_sky_map
        self.read_noise = read_noise
        self.add_noise = add_noise
        self.noise_if_add_noise_false = noise_if_add_noise_false
        self.noise_seed = noise_seed


class Imaging(AbstractImaging):
    @classmethod
    def from_fits(
        cls,
        image_path,
        pixel_scales=None,
        image_hdu=0,
        noise_map_path=None,
        noise_map_hdu=0,
        psf_path=None,
        psf_hdu=0,
        positions_path=None,
        name=None,
    ):
        """Factory for loading the imaging data_type from .fits files, as well as computing properties like the noise-map,
        exposure-time map, etc. from the imaging-data.

        This factory also includes a number of routines for converting the imaging-data from unit_label not supported by PyAutoLens \
        (e.g. adus, electrons) to electrons per second.

        Parameters
        ----------
        renormalize_psf
        noise_map_non_constant
        name
        image_path : str
            The path to the image .fits file containing the image (e.g. '/path/to/image.fits')
        pixel_scales : float
            The size of each pixel in arc seconds.
        image_hdu : int
            The hdu the image is contained in the .fits file specified by *image_path*.
        psf_path : str
            The path to the psf .fits file containing the psf (e.g. '/path/to/psf.fits')
        psf_hdu : int
            The hdu the psf is contained in the .fits file specified by *psf_path*.
        noise_map_path : str
            The path to the noise_map .fits file containing the noise_map (e.g. '/path/to/noise_map.fits')
        noise_map_hdu : int
            The hdu the noise_map is contained in the .fits file specified by *noise_map_path*.
        """

        image = arrays.Array.from_fits(
            file_path=image_path, hdu=image_hdu, pixel_scales=pixel_scales
        )

        noise_map = arrays.Array.from_fits(
            file_path=noise_map_path, hdu=noise_map_hdu, pixel_scales=pixel_scales
        )

        if psf_path is not None:

            psf = kernel.Kernel.from_fits(
                file_path=psf_path,
                hdu=psf_hdu,
                pixel_scales=pixel_scales,
                renormalize=True,
            )

        else:

            psf = None

        if positions_path is not None:

            positions = grids.GridCoordinates.from_file(file_path=positions_path)

        else:

            positions = None

        return Imaging(
            image=image, noise_map=noise_map, psf=psf, positions=positions, name=name
        )

    def output_to_fits(
        self, image_path, psf_path=None, noise_map_path=None, overwrite=False
    ):
        self.image.output_to_fits(file_path=image_path, overwrite=overwrite)

        if self.psf is not None and psf_path is not None:
            self.psf.output_to_fits(file_path=psf_path, overwrite=overwrite)

        if self.noise_map is not None and noise_map_path is not None:
            self.noise_map.output_to_fits(file_path=noise_map_path, overwrite=overwrite)


class MaskedImaging(AbstractMaskedImaging):

    pass


class SimulatorImaging(AbstractSimulatorImaging):
    def from_image(self, image, name=None):
        """
        Create a realistic simulated image by applying effects to a plain simulated image.

        Parameters
        ----------
        noise_if_add_noise_false
        background_level
        exposure_time_
        name
        image : ndarray
            The image before simulating (e.g. the lens and source galaxies before optics blurring and Imaging read-out).
        exposure_time_map : ndarray
            An array representing the effective exposure time of each pixel.
        psf: PSF
            An array describing the PSF the simulated image is blurred with.
        background_sky_map : ndarray
            The value of background sky in every image pixel (electrons per second).
        add_noise: Bool
            If True poisson noise_maps is simulated and added to the image, based on the total counts in each image
            pixel
        noise_seed: int
            A seed for random noise_maps generation
        """

        if self.background_sky_map is not None:
            background_sky_map = self.background_sky_map
        else:
            background_sky_map = arrays.Array.zeros(
                shape_2d=image.shape_2d, pixel_scales=image.pixel_scales
            )

        if self.psf is not None:
            psf = self.psf
        else:
            psf = kernel.Kernel.no_blur(pixel_scales=image.pixel_scales)

        image = psf.convolved_array_from_array(array=image)

        image = image + background_sky_map

        image = image.trimmed_from_kernel_shape(kernel_shape_2d=psf.shape_2d)
        exposure_time_map = self.exposure_time_map.trimmed_from_kernel_shape(
            kernel_shape_2d=psf.shape_2d
        )
        background_sky_map = background_sky_map.trimmed_from_kernel_shape(
            kernel_shape_2d=psf.shape_2d
        )

        if self.add_noise is True:
            image = preprocess.data_with_poisson_noise_added(
                data=image, exposure_time_map=exposure_time_map, seed=self.noise_seed
            )

            noise_map = preprocess.noise_map_from_data_and_exposure_time_map(
                data=image, exposure_time_map=exposure_time_map
            )

        else:
            noise_map = arrays.Array.full(
                fill_value=self.noise_if_add_noise_false,
                shape_2d=image.shape_2d,
                pixel_scales=image.pixel_scales,
            )

        if np.isnan(noise_map).any():
            raise exc.DataException(
                "The noise-map has NaN values in it. This suggests your exposure time and / or"
                "background sky levels are too low, creating signal counts at or close to 0.0."
            )

        image = image - background_sky_map

        mask = msk.Mask.unmasked(
            shape_2d=image.shape_2d, pixel_scales=image.pixel_scales
        )

        image = arrays.Array.manual_mask(array=image, mask=mask)

        return Imaging(image=image, psf=self.psf, noise_map=noise_map, name=name)
