import numpy as np
from os import path
import pytest

import autoarray as aa

from autoarray import exc


directory = path.dirname(path.realpath(__file__))


def test__has():

    reg = aa.m.MockRegularization()

    inversion = aa.m.MockInversion(regularization_list=[reg, None])

    assert inversion.has(cls=aa.AbstractRegularization) is True

    inversion = aa.m.MockInversion(regularization_list=[None, None])

    assert inversion.has(cls=aa.AbstractRegularization) is False


def test__total_regularizations():

    reg = aa.m.MockRegularization()

    inversion = aa.m.MockInversion(regularization_list=[reg, None])

    assert inversion.total_regularizations == 1

    inversion = aa.m.MockInversion(regularization_list=[reg, reg])

    assert inversion.total_regularizations == 2

    inversion = aa.m.MockInversion(regularization_list=[None, None])

    assert inversion.total_regularizations == 0


def test__no_regularization_index_list():

    inversion = aa.m.MockInversion(
        linear_obj_list=[aa.m.MockLinearObj(pixels=2), aa.m.MockLinearObj(pixels=1)],
        regularization_list=[None, None],
    )

    assert inversion.no_regularization_index_list == [0, 1, 2]

    inversion = aa.m.MockInversion(
        linear_obj_list=[
            aa.m.MockMapper(pixels=10),
            aa.m.MockLinearObj(pixels=3),
            aa.m.MockMapper(pixels=20),
            aa.m.MockLinearObj(pixels=4),
        ],
        regularization_list=[
            aa.m.MockRegularization(),
            None,
            aa.m.MockRegularization(),
            None,
        ],
    )

    assert inversion.no_regularization_index_list == [10, 11, 12, 33, 34, 35, 36]


def test__mapping_matrix():

    mapper_0 = aa.m.MockMapper(mapping_matrix=np.ones((2, 2)))
    mapper_1 = aa.m.MockMapper(mapping_matrix=2.0 * np.ones((2, 3)))

    inversion = aa.m.MockInversion(linear_obj_list=[mapper_0, mapper_1])

    mapping_matrix = np.array([[1.0, 1.0, 2.0, 2.0, 2.0], [1.0, 1.0, 2.0, 2.0, 2.0]])

    assert inversion.mapping_matrix == pytest.approx(mapping_matrix, 1.0e-4)


def test__curvature_matrix__via_w_tilde__identical_to_mapping():
    mask = aa.Mask2D.manual(
        mask=[
            [True, True, True, True, True, True, True],
            [True, True, True, True, True, True, True],
            [True, True, True, False, True, True, True],
            [True, True, False, False, False, True, True],
            [True, True, True, False, True, True, True],
            [True, True, True, True, True, True, True],
            [True, True, True, True, True, True, True],
        ],
        pixel_scales=2.0,
        sub_size=1,
    )

    grid = aa.Grid2D.from_mask(mask=mask)

    pix_0 = aa.mesh.Rectangular(shape=(3, 3))
    pix_1 = aa.mesh.Rectangular(shape=(4, 4))

    mapper_0 = pix_0.mapper_from(
        source_grid_slim=grid,
        source_mesh_grid=None,
        settings=aa.SettingsPixelization(use_border=False),
    )

    mapper_1 = pix_1.mapper_from(
        source_grid_slim=grid,
        source_mesh_grid=None,
        settings=aa.SettingsPixelization(use_border=False),
    )

    reg = aa.reg.Constant(coefficient=1.0)

    image = aa.Array2D.manual_native(array=np.random.random((7, 7)), pixel_scales=1.0)
    noise_map = aa.Array2D.manual_native(
        array=np.random.random((7, 7)), pixel_scales=1.0
    )
    kernel = np.array([[0.0, 1.0, 0.0], [1.0, 1.0, 1.0], [0.0, 1.0, 0.0]])
    psf = aa.Kernel2D.manual_native(array=kernel, pixel_scales=1.0)

    imaging = aa.Imaging(image=image, noise_map=noise_map, psf=psf)

    masked_imaging = imaging.apply_mask(mask=mask)

    inversion_w_tilde = aa.Inversion(
        dataset=masked_imaging,
        linear_obj_list=[mapper_0, mapper_1],
        regularization_list=[reg, reg],
        settings=aa.SettingsInversion(use_w_tilde=True, check_solution=False),
    )

    inversion_mapping = aa.Inversion(
        dataset=masked_imaging,
        linear_obj_list=[mapper_0, mapper_1],
        regularization_list=[reg, reg],
        settings=aa.SettingsInversion(use_w_tilde=False, check_solution=False),
    )

    assert inversion_w_tilde.curvature_matrix == pytest.approx(
        inversion_mapping.curvature_matrix, 1.0e-4
    )


def test__curvature_matrix_via_w_tilde__includes_source_interpolation__identical_to_mapping():
    mask = aa.Mask2D.manual(
        mask=[
            [True, True, True, True, True, True, True],
            [True, True, True, True, True, True, True],
            [True, True, True, False, True, True, True],
            [True, True, False, False, False, True, True],
            [True, True, True, False, True, True, True],
            [True, True, True, True, True, True, True],
            [True, True, True, True, True, True, True],
        ],
        pixel_scales=2.0,
        sub_size=1,
    )

    grid = aa.Grid2D.from_mask(mask=mask)

    pix_0 = aa.mesh.DelaunayMagnification(shape=(3, 3))
    pix_1 = aa.mesh.DelaunayMagnification(shape=(4, 4))

    sparse_grid_0 = aa.Grid2DSparse.from_grid_and_unmasked_2d_grid_shape(
        grid=grid, unmasked_sparse_shape=pix_0.shape
    )

    sparse_grid_1 = aa.Grid2DSparse.from_grid_and_unmasked_2d_grid_shape(
        grid=grid, unmasked_sparse_shape=pix_1.shape
    )

    mapper_0 = pix_0.mapper_from(
        source_grid_slim=grid,
        source_mesh_grid=sparse_grid_0,
        settings=aa.SettingsPixelization(use_border=False),
    )

    mapper_1 = pix_1.mapper_from(
        source_grid_slim=grid,
        source_mesh_grid=sparse_grid_1,
        settings=aa.SettingsPixelization(use_border=False),
    )

    reg = aa.reg.Constant(coefficient=1.0)

    image = aa.Array2D.manual_native(array=np.random.random((7, 7)), pixel_scales=1.0)
    noise_map = aa.Array2D.manual_native(
        array=np.random.random((7, 7)), pixel_scales=1.0
    )
    kernel = np.array([[0.0, 1.0, 0.0], [1.0, 1.0, 1.0], [0.0, 1.0, 0.0]])
    psf = aa.Kernel2D.manual_native(array=kernel, pixel_scales=1.0)

    imaging = aa.Imaging(image=image, noise_map=noise_map, psf=psf)

    masked_imaging = imaging.apply_mask(mask=mask)

    inversion_w_tilde = aa.Inversion(
        dataset=masked_imaging,
        linear_obj_list=[mapper_0, mapper_1],
        regularization_list=[reg, reg],
        settings=aa.SettingsInversion(use_w_tilde=True, check_solution=False),
    )

    inversion_mapping = aa.Inversion(
        dataset=masked_imaging,
        linear_obj_list=[mapper_0, mapper_1],
        regularization_list=[reg, reg],
        settings=aa.SettingsInversion(use_w_tilde=False, check_solution=False),
    )

    assert inversion_w_tilde.curvature_matrix == pytest.approx(
        inversion_mapping.curvature_matrix, 1.0e-4
    )


def test__curvature_reg_matrix_reduced():

    curvature_reg_matrix = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]])

    linear_obj_list = [aa.m.MockLinearObj(pixels=2), aa.m.MockLinearObj(pixels=1)]

    regularization_list = [1, None]

    inversion = aa.m.MockInversion(
        linear_obj_list=linear_obj_list,
        regularization_list=regularization_list,
        curvature_reg_matrix=curvature_reg_matrix,
    )

    assert (
        inversion.curvature_reg_matrix_reduced == np.array([[1.0, 2.0], [4.0, 5.0]])
    ).all()


def test__regularization_matrix():

    reg_0 = aa.m.MockRegularization(regularization_matrix=np.ones((2, 2)))
    reg_1 = aa.m.MockRegularization(regularization_matrix=2.0 * np.ones((3, 3)))

    inversion = aa.m.MockInversion(
        linear_obj_list=[aa.m.MockMapper(), aa.m.MockMapper()],
        regularization_list=[reg_0, reg_1],
    )

    regularization_matrix = np.array(
        [
            [1.0, 1.0, 0.0, 0.0, 0.0],
            [1.0, 1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 2.0, 2.0, 2.0],
            [0.0, 0.0, 2.0, 2.0, 2.0],
            [0.0, 0.0, 2.0, 2.0, 2.0],
        ]
    )

    assert inversion.regularization_matrix == pytest.approx(regularization_matrix)


def test__preloads__operated_mapping_matrix_and_curvature_matrix_preload():

    operated_mapping_matrix = 2.0 * np.ones((9, 3))

    curvature_matrix_preload, curvature_matrix_counts = aa.util.inversion.curvature_matrix_preload_from(
        mapping_matrix=operated_mapping_matrix
    )

    preloads = aa.Preloads(
        operated_mapping_matrix=operated_mapping_matrix,
        curvature_matrix_preload=curvature_matrix_preload.astype("int"),
        curvature_matrix_counts=curvature_matrix_counts.astype("int"),
    )

    # noinspection PyTypeChecker
    inversion = aa.m.MockInversionImaging(
        noise_map=np.ones(9), linear_obj_list=aa.m.MockMapper(), preloads=preloads
    )

    assert inversion.operated_mapping_matrix[0, 0] == 2.0
    assert inversion.curvature_matrix[0, 0] == 36.0


def test__preload_of_regularization_matrix__overwrites_calculation():

    inversion = aa.m.MockInversion(
        preloads=aa.Preloads(regularization_matrix=np.ones((2, 2)))
    )

    assert (inversion.regularization_matrix == np.ones((2, 2))).all()


def test__reconstruction_reduced():

    inversion = aa.m.MockInversion(
        linear_obj_list=[aa.m.MockMapper(pixels=2), aa.m.MockLinearObj()]
    )

    linear_obj_list = [aa.m.MockLinearObj(pixels=2), aa.m.MockLinearObj(pixels=1)]

    regularization_list = [aa.m.MockRegularization(), None]

    inversion = aa.m.MockInversion(
        linear_obj_list=linear_obj_list,
        regularization_list=regularization_list,
        reconstruction=np.array([1.0, 2.0, 3.0]),
    )

    assert (inversion.reconstruction_reduced == np.array([1.0, 2.0])).all()


def test__reconstruction_dict():

    reconstruction = np.array([0.0, 1.0, 1.0, 1.0])

    linear_obj = aa.m.MockLinearObj(pixels=1)
    mapper = aa.m.MockMapper(pixels=3)

    inversion = aa.m.MockInversion(
        linear_obj_list=[linear_obj, mapper], reconstruction=reconstruction
    )

    assert (inversion.reconstruction_dict[linear_obj] == np.zeros(1)).all()
    assert (inversion.reconstruction_dict[mapper] == np.ones(3)).all()

    reconstruction = np.array([0.0, 1.0, 1.0, 2.0, 2.0, 2.0])

    linear_obj = aa.m.MockLinearObj(pixels=1)
    mapper_0 = aa.m.MockMapper(pixels=2)
    mapper_1 = aa.m.MockMapper(pixels=3)

    inversion = aa.m.MockInversion(
        linear_obj_list=[linear_obj, mapper_0, mapper_1], reconstruction=reconstruction
    )

    assert (inversion.reconstruction_dict[linear_obj] == np.zeros(1)).all()
    assert (inversion.reconstruction_dict[mapper_0] == np.ones(2)).all()
    assert (inversion.reconstruction_dict[mapper_1] == 2.0 * np.ones(3)).all()


def test__mapped_reconstructed_data():

    linear_obj_0 = aa.m.MockLinearObj()

    mapped_reconstructed_data_dict = {linear_obj_0: np.ones(3)}

    # noinspection PyTypeChecker
    inversion = aa.m.MockInversion(
        mapped_reconstructed_data_dict=mapped_reconstructed_data_dict,
        reconstruction=np.ones(3),
        reconstruction_dict=[None],
    )

    assert (inversion.mapped_reconstructed_data_dict[linear_obj_0] == np.ones(3)).all()
    assert (inversion.mapped_reconstructed_data == np.ones(3)).all()

    linear_obj_1 = aa.m.MockLinearObj()

    mapped_reconstructed_data_dict = {
        linear_obj_0: np.ones(2),
        linear_obj_1: 2.0 * np.ones(2),
    }

    # noinspection PyTypeChecker
    inversion = aa.m.MockInversion(
        mapped_reconstructed_data_dict=mapped_reconstructed_data_dict,
        reconstruction=np.array([1.0, 1.0, 2.0, 2.0]),
        reconstruction_dict=[None, None],
    )

    assert (inversion.mapped_reconstructed_data_dict[linear_obj_0] == np.ones(2)).all()
    assert (
        inversion.mapped_reconstructed_data_dict[linear_obj_1] == 2.0 * np.ones(2)
    ).all()
    assert (inversion.mapped_reconstructed_data == 3.0 * np.ones(2)).all()


def test__mapped_reconstructed_image():

    linear_obj_0 = aa.m.MockLinearObj()

    mapped_reconstructed_image_dict = {linear_obj_0: np.ones(3)}

    # noinspection PyTypeChecker
    inversion = aa.m.MockInversion(
        mapped_reconstructed_image_dict=mapped_reconstructed_image_dict,
        reconstruction=np.ones(3),
        reconstruction_dict=[None],
    )

    assert (inversion.mapped_reconstructed_image_dict[linear_obj_0] == np.ones(3)).all()
    assert (inversion.mapped_reconstructed_image == np.ones(3)).all()

    linear_obj_1 = aa.m.MockLinearObj()

    mapped_reconstructed_image_dict = {
        linear_obj_0: np.ones(2),
        linear_obj_1: 2.0 * np.ones(2),
    }

    # noinspection PyTypeChecker
    inversion = aa.m.MockInversion(
        mapped_reconstructed_image_dict=mapped_reconstructed_image_dict,
        reconstruction=np.array([1.0, 1.0, 2.0, 2.0]),
        reconstruction_dict=[None, None],
    )

    assert (inversion.mapped_reconstructed_image_dict[linear_obj_0] == np.ones(2)).all()
    assert (
        inversion.mapped_reconstructed_image_dict[linear_obj_1] == 2.0 * np.ones(2)
    ).all()
    assert (inversion.mapped_reconstructed_image == 3.0 * np.ones(2)).all()


def test__reconstruction_raises_exception_for_linalg_error():

    # noinspection PyTypeChecker
    inversion = aa.m.MockInversion(
        data_vector=np.ones(3), curvature_reg_matrix=np.ones((3, 3))
    )

    with pytest.raises(exc.InversionException):

        # noinspection PyStatementEffect
        inversion.reconstruction


def test__regularization_term():

    reconstruction = np.array([1.0, 1.0, 1.0])

    regularization_matrix = np.array(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    )

    inversion = aa.m.MockInversion(linear_obj_list=[aa.m.MockMapper()])

    inversion = aa.m.MockInversion(
        reconstruction=reconstruction,
        linear_obj_list=[aa.m.MockLinearObj(pixels=3)],
        regularization_list=[aa.m.MockRegularization()],
        regularization_matrix=regularization_matrix,
    )

    # G_l term, Warren & Dye 2003 / Nightingale /2015 2018

    # G_l = s_T * H * s

    # Matrix multiplication:

    # s_T * H = [1.0, 1.0, 1.0] * [1.0, 1.0, 1.0] = [(1.0*1.0) + (1.0*0.0) + (1.0*0.0)] = [1.0, 1.0, 1.0]
    #                             [1.0, 1.0, 1.0]   [(1.0*0.0) + (1.0*1.0) + (1.0*0.0)]
    #                             [1.0, 1.0, 1.0]   [(1.0*0.0) + (1.0*0.0) + (1.0*1.0)]

    # (s_T * H) * s = [1.0, 1.0, 1.0] * [1.0] = 3.0
    #                                   [1.0]
    #                                   [1.0]

    assert inversion.regularization_term == 3.0

    reconstruction = np.array([2.0, 3.0, 5.0])

    regularization_matrix = np.array(
        [[2.0, -1.0, 0.0], [-1.0, 2.0, -1.0], [0.0, -1.0, 2.0]]
    )

    inversion = aa.m.MockInversion(linear_obj_list=[aa.m.MockMapper()])

    inversion = aa.m.MockInversion(
        reconstruction=reconstruction,
        linear_obj_list=[aa.m.MockLinearObj(pixels=3)],
        regularization_list=[aa.m.MockRegularization()],
        regularization_matrix=regularization_matrix,
    )

    # G_l term, Warren & Dye 2003 / Nightingale /2015 2018

    # G_l = s_T * H * s

    # Matrix multiplication:

    # s_T * H = [2.0, 3.0, 5.0] * [2.0,  -1.0,  0.0] = [(2.0* 2.0) + (3.0*-1.0) + (5.0 *0.0)] = [1.0, -1.0, 7.0]
    #                             [-1.0,  2.0, -1.0]   [(2.0*-1.0) + (3.0* 2.0) + (5.0*-1.0)]
    #                             [ 0.0, -1.0,  2.0]   [(2.0* 0.0) + (3.0*-1.0) + (5.0 *2.0)]

    # (s_T * H) * s = [1.0, -1.0, 7.0] * [2.0] = 34.0
    #                                    [3.0]
    #                                    [5.0]

    assert inversion.regularization_term == 34.0


def test__preload_of_log_det_regularization_term_overwrites_calculation():

    inversion = aa.m.MockInversion(linear_obj_list=[aa.m.MockMapper()])

    inversion = aa.m.MockInversion(
        linear_obj_list=[aa.m.MockLinearObj(pixels=3)],
        regularization_list=[aa.m.MockRegularization()],
        preloads=aa.Preloads(log_det_regularization_matrix_term=1.0),
    )

    assert inversion.log_det_regularization_matrix_term == 1.0


def test__determinant_of_positive_definite_matrix_via_cholesky():

    matrix = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])

    inversion = aa.m.MockInversion(
        linear_obj_list=[None],
        regularization_list=[aa.m.MockRegularization()],
        curvature_reg_matrix=matrix,
    )

    log_determinant = np.log(np.linalg.det(matrix))

    assert log_determinant == pytest.approx(
        inversion.log_det_curvature_reg_matrix_term, 1e-4
    )

    matrix = np.array([[2.0, -1.0, 0.0], [-1.0, 2.0, -1.0], [0.0, -1.0, 2.0]])

    inversion = aa.m.MockInversion(
        linear_obj_list=[None],
        regularization_list=[aa.m.MockRegularization()],
        curvature_reg_matrix=matrix,
    )

    log_determinant = np.log(np.linalg.det(matrix))

    assert log_determinant == pytest.approx(
        inversion.log_det_curvature_reg_matrix_term, 1e-4
    )


def test__errors_and_errors_with_covariance():

    curvature_reg_matrix = np.array([[1.0, 1.0, 1.0], [1.0, 2.0, 1.0], [1.0, 1.0, 3.0]])

    inversion = aa.m.MockInversion(curvature_reg_matrix=curvature_reg_matrix)

    assert inversion.errors_with_covariance == pytest.approx(
        np.array([[2.5, -1.0, -0.5], [-1.0, 1.0, 0.0], [-0.5, 0.0, 0.5]]), 1.0e-2
    )
    assert inversion.errors == pytest.approx(np.array([2.5, 1.0, 0.5]), 1.0e-3)


def test__brightest_reconstruction_pixel_and_centre():

    mapper = aa.m.MockMapper(
        source_mesh_grid=aa.Mesh2DVoronoi.manual_slim(
            [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [5.0, 0.0]]
        )
    )

    inversion = aa.m.MockInversion(
        linear_obj_list=[mapper], reconstruction=np.array([2.0, 3.0, 5.0, 0.0])
    )

    assert inversion.brightest_reconstruction_pixel_list[0] == 2

    assert inversion.brightest_reconstruction_pixel_centre_list[0].in_list == [
        (5.0, 6.0)
    ]


def test__interpolated_reconstruction_list_from():

    interpolated_array = np.array([0.0, 1.0, 1.0, 1.0])

    mapper = aa.m.MockMapper(pixels=3, interpolated_array=interpolated_array)

    inversion = aa.m.MockInversion(
        linear_obj_list=[mapper], reconstruction=interpolated_array
    )

    interpolated_reconstruction_list = inversion.interpolated_reconstruction_list_from(
        shape_native=(3, 3), extent=(-0.2, 0.2, -0.3, 0.3)
    )

    assert (interpolated_reconstruction_list[0] == np.array([0.0, 1.0, 1.0, 1.0])).all()


def test__interpolated_errors_list_from():

    interpolated_array = np.array([0.0, 1.0, 1.0, 1.0])

    mapper = aa.m.MockMapper(pixels=3, interpolated_array=interpolated_array)

    inversion = aa.m.MockInversion(linear_obj_list=[mapper], errors=interpolated_array)

    interpolated_errors_list = inversion.interpolated_errors_list_from(
        shape_native=(3, 3), extent=(-0.2, 0.2, -0.3, 0.3)
    )

    assert (interpolated_errors_list[0] == np.array([0.0, 1.0, 1.0, 1.0])).all()
