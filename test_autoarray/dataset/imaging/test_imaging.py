import os
from os import path

import numpy as np
import pytest
import shutil

import autoarray as aa

test_data_dir = path.join(
    "{}".format(path.dirname(path.realpath(__file__))),
    "files",
)


def test__psf_and_mask_hit_edge__automatically_pads_image_and_noise_map():

    image = aa.Array2D.ones(shape_native=(3, 3), pixel_scales=1.0)
    noise_map = aa.Array2D.ones(shape_native=(3, 3), pixel_scales=1.0)
    psf = aa.Kernel2D.ones(shape_native=(3, 3), pixel_scales=1.0)

    imaging = aa.Imaging(
        image=image, noise_map=noise_map, psf=psf, pad_for_convolver=False
    )

    assert imaging.image.shape_native == (3, 3)
    assert imaging.noise_map.shape_native == (3, 3)

    imaging = aa.Imaging(
        image=image, noise_map=noise_map, psf=psf, pad_for_convolver=True
    )

    assert imaging.image.shape_native == (5, 5)
    assert imaging.noise_map.shape_native == (5, 5)
    assert imaging.image.mask[0, 0] == True
    assert imaging.image.mask[1, 1] == False


def test__signal_to_noise_limited_from():

    image = aa.Array2D.full(fill_value=20.0, shape_native=(2, 2), pixel_scales=1.0)
    image[3] = 5.0

    noise_map_array = aa.Array2D.full(
        fill_value=5.0, shape_native=(2, 2), pixel_scales=1.0
    )
    noise_map_array[3] = 2.0

    imaging = aa.Imaging(
        image=image,
        psf=aa.Kernel2D.zeros(shape_native=(3, 3), pixel_scales=1.0),
        noise_map=noise_map_array,
    )

    imaging = imaging.signal_to_noise_limited_from(signal_to_noise_limit=100.0)

    assert (imaging.image.slim == np.array([20.0, 20.0, 20.0, 5.0])).all()

    assert (imaging.noise_map.slim == np.array([5.0, 5.0, 5.0, 2.0])).all()

    assert (imaging.signal_to_noise_map.slim == np.array([4.0, 4.0, 4.0, 2.5])).all()

    image = aa.Array2D.full(fill_value=20.0, shape_native=(2, 2), pixel_scales=1.0)
    image[3] = 5.0

    noise_map_array = aa.Array2D.full(
        fill_value=5.0, shape_native=(2, 2), pixel_scales=1.0
    )
    noise_map_array[3] = 2.0

    imaging = aa.Imaging(
        image=image,
        psf=aa.Kernel2D.zeros(shape_native=(3, 3), pixel_scales=1.0),
        noise_map=noise_map_array,
    )

    imaging_capped = imaging.signal_to_noise_limited_from(signal_to_noise_limit=2.0)

    assert (imaging_capped.image.native == np.array([[20.0, 20.0], [20.0, 5.0]])).all()

    assert (
        imaging_capped.noise_map.native == np.array([[10.0, 10.0], [10.0, 2.5]])
    ).all()

    assert (
        imaging_capped.signal_to_noise_map.native == np.array([[2.0, 2.0], [2.0, 2.0]])
    ).all()

    image = aa.Array2D.full(fill_value=20.0, shape_native=(2, 2), pixel_scales=1.0)
    image[2] = 5.0
    image[3] = 5.0

    noise_map_array = aa.Array2D.full(
        fill_value=5.0, shape_native=(2, 2), pixel_scales=1.0
    )
    noise_map_array[2] = 2.0
    noise_map_array[3] = 2.0

    mask = aa.Mask2D.manual(mask=[[True, False], [False, True]], pixel_scales=1.0)

    imaging = aa.Imaging(
        image=image,
        psf=aa.Kernel2D.zeros(shape_native=(3, 3), pixel_scales=1.0),
        noise_map=noise_map_array,
    )

    imaging_capped = imaging.signal_to_noise_limited_from(
        signal_to_noise_limit=2.0, mask=mask
    )

    assert (imaging_capped.image.native == np.array([[20.0, 20.0], [5.0, 5.0]])).all()

    assert (
        imaging_capped.noise_map.native == np.array([[5.0, 10.0], [2.5, 2.0]])
    ).all()

    assert (
        imaging_capped.signal_to_noise_map.native == np.array([[4.0, 2.0], [2.0, 2.5]])
    ).all()


def test__from_fits():

    imaging = aa.Imaging.from_fits(
        pixel_scales=0.1,
        image_path=path.join(test_data_dir, "3x3_ones.fits"),
        psf_path=path.join(test_data_dir, "3x3_twos.fits"),
        noise_map_path=path.join(test_data_dir, "3x3_threes.fits"),
    )

    assert (imaging.image.native == np.ones((3, 3))).all()
    assert (imaging.psf.native == (1.0 / 9.0) * np.ones((3, 3))).all()
    assert (imaging.noise_map.native == 3.0 * np.ones((3, 3))).all()

    assert imaging.pixel_scales == (0.1, 0.1)
    assert imaging.psf.mask.pixel_scales == (0.1, 0.1)
    assert imaging.noise_map.mask.pixel_scales == (0.1, 0.1)

    imaging = aa.Imaging.from_fits(
        pixel_scales=0.1,
        image_path=path.join(test_data_dir, "3x3_multiple_hdu.fits"),
        image_hdu=0,
        psf_path=path.join(test_data_dir, "3x3_multiple_hdu.fits"),
        psf_hdu=1,
        noise_map_path=path.join(test_data_dir, "3x3_multiple_hdu.fits"),
        noise_map_hdu=2,
    )

    assert (imaging.image.native == np.ones((3, 3))).all()
    assert (imaging.psf.native == (1.0 / 9.0) * np.ones((3, 3))).all()
    assert (imaging.noise_map.native == 3.0 * np.ones((3, 3))).all()

    assert imaging.pixel_scales == (0.1, 0.1)
    assert imaging.psf.mask.pixel_scales == (0.1, 0.1)
    assert imaging.noise_map.mask.pixel_scales == (0.1, 0.1)


def test__output_to_fits():

    imaging = aa.Imaging.from_fits(
        pixel_scales=0.1,
        image_path=path.join(test_data_dir, "3x3_ones.fits"),
        psf_path=path.join(test_data_dir, "3x3_twos.fits"),
        noise_map_path=path.join(test_data_dir, "3x3_threes.fits"),
    )

    output_data_dir = path.join(
        "{}".format(os.path.dirname(os.path.realpath(__file__))),
        "files",
        "array",
        "output_test",
    )

    if os.path.exists(output_data_dir):
        shutil.rmtree(output_data_dir)

    os.makedirs(output_data_dir)

    imaging.output_to_fits(
        image_path=path.join(output_data_dir, "image.fits"),
        psf_path=path.join(output_data_dir, "psf.fits"),
        noise_map_path=path.join(output_data_dir, "noise_map.fits"),
    )

    imaging = aa.Imaging.from_fits(
        pixel_scales=0.1,
        image_path=path.join(output_data_dir, "image.fits"),
        psf_path=path.join(output_data_dir, "psf.fits"),
        noise_map_path=path.join(output_data_dir, "noise_map.fits"),
    )

    assert (imaging.image.native == np.ones((3, 3))).all()
    assert (imaging.psf.native == (1.0 / 9.0) * np.ones((3, 3))).all()
    assert (imaging.noise_map.native == 3.0 * np.ones((3, 3))).all()

    assert imaging.pixel_scales == (0.1, 0.1)
    assert imaging.psf.mask.pixel_scales == (0.1, 0.1)
    assert imaging.noise_map.mask.pixel_scales == (0.1, 0.1)


def test__apply_mask(imaging_7x7, sub_mask_2d_7x7, psf_3x3):

    masked_imaging_7x7 = imaging_7x7.apply_mask(mask=sub_mask_2d_7x7)

    assert (masked_imaging_7x7.image.slim == np.ones(9)).all()

    assert (
        masked_imaging_7x7.image.native == np.ones((7, 7)) * np.invert(sub_mask_2d_7x7)
    ).all()

    assert (masked_imaging_7x7.noise_map.slim == 2.0 * np.ones(9)).all()
    assert (
        masked_imaging_7x7.noise_map.native
        == 2.0 * np.ones((7, 7)) * np.invert(sub_mask_2d_7x7)
    ).all()

    assert (masked_imaging_7x7.psf.slim == (1.0 / 3.0) * psf_3x3.slim).all()

    assert type(masked_imaging_7x7.psf) == aa.Kernel2D
    assert type(masked_imaging_7x7.convolver) == aa.Convolver
    assert masked_imaging_7x7.w_tilde.curvature_preload.shape == (35,)
    assert masked_imaging_7x7.w_tilde.indexes.shape == (35,)
    assert masked_imaging_7x7.w_tilde.lengths.shape == (9,)


def test__apply_mask__apply_settings__grids(
    imaging_7x7,
    sub_mask_2d_7x7,
    grid_2d_7x7,
    sub_grid_2d_7x7,
    blurring_grid_2d_7x7,
    grid_2d_iterate_7x7,
):

    masked_imaging_7x7 = imaging_7x7.apply_mask(mask=sub_mask_2d_7x7)
    masked_imaging_7x7 = masked_imaging_7x7.apply_settings(
        settings=aa.SettingsImaging(grid_class=aa.Grid2D, sub_size=2)
    )

    assert isinstance(masked_imaging_7x7.grid, aa.Grid2D)
    assert (masked_imaging_7x7.grid.binned == grid_2d_7x7).all()
    assert (masked_imaging_7x7.grid.slim == sub_grid_2d_7x7).all()
    assert isinstance(masked_imaging_7x7.blurring_grid, aa.Grid2D)
    assert (masked_imaging_7x7.blurring_grid.slim == blurring_grid_2d_7x7).all()

    masked_imaging_7x7 = imaging_7x7.apply_mask(mask=sub_mask_2d_7x7)
    masked_imaging_7x7 = masked_imaging_7x7.apply_settings(
        settings=aa.SettingsImaging(grid_class=aa.Grid2DIterate)
    )

    assert isinstance(masked_imaging_7x7.grid, aa.Grid2DIterate)
    assert (masked_imaging_7x7.grid.binned == grid_2d_iterate_7x7).all()
    assert isinstance(masked_imaging_7x7.blurring_grid, aa.Grid2DIterate)
    assert (masked_imaging_7x7.blurring_grid.slim == blurring_grid_2d_7x7).all()


def test__masked_imaging__signal_to_noise_limited_from(imaging_7x7, mask_2d_7x7):

    masked_imaging_7x7 = imaging_7x7.apply_mask(mask=mask_2d_7x7)
    masked_imaging_7x7 = masked_imaging_7x7.apply_settings(
        settings=aa.SettingsImaging(grid_class=aa.Grid2D, signal_to_noise_limit=0.1)
    )

    imaging_snr_limit = imaging_7x7.signal_to_noise_limited_from(
        signal_to_noise_limit=0.1
    )

    assert (
        masked_imaging_7x7.image.native
        == imaging_snr_limit.image.native * np.invert(mask_2d_7x7)
    ).all()
    assert (
        masked_imaging_7x7.noise_map.native
        == imaging_snr_limit.noise_map.native * np.invert(mask_2d_7x7)
    ).all()

    masked_imaging_7x7 = imaging_7x7.apply_mask(mask=mask_2d_7x7)
    masked_imaging_7x7 = masked_imaging_7x7.apply_settings(
        settings=aa.SettingsImaging(
            grid_class=aa.Grid2D,
            signal_to_noise_limit=0.1,
            signal_to_noise_limit_radii=1.0,
        )
    )

    assert (
        masked_imaging_7x7.noise_map.native[3, 3] != imaging_7x7.noise_map.native[3, 3]
    )
    assert masked_imaging_7x7.noise_map.native[3, 3] == 10.0
    assert masked_imaging_7x7.noise_map.native[3, 4] == 10.0
    assert masked_imaging_7x7.noise_map.native[4, 4] == 2.0


def test__different_imaging_without_mock_objects__customize_constructor_inputs():

    psf = aa.Kernel2D.ones(shape_native=(7, 7), pixel_scales=3.0)

    imaging = aa.Imaging(
        image=aa.Array2D.ones(shape_native=(19, 19), pixel_scales=3.0),
        psf=psf,
        noise_map=aa.Array2D.full(
            fill_value=2.0, shape_native=(19, 19), pixel_scales=3.0
        ),
    )
    mask = aa.Mask2D.unmasked(
        shape_native=(19, 19), pixel_scales=1.0, invert=True, sub_size=8
    )
    mask[9, 9] = False

    masked_imaging = imaging.apply_mask(mask=mask)

    assert masked_imaging.psf.native == pytest.approx(
        (1.0 / 49.0) * np.ones((7, 7)), 1.0e-4
    )
    assert masked_imaging.convolver.kernel.shape_native == (7, 7)
    assert (masked_imaging.image == np.array([1.0])).all()
    assert (masked_imaging.noise_map == np.array([2.0])).all()
