import os

import numpy as np
import pytest


from autolens.imaging.util import mapping_util

test_data_dir = "{}/../test_files/array/".format(os.path.dirname(os.path.realpath(__file__)))


class TestSubToImage(object):

    def test__3x3_mask_with_1_pixel__2x2_sub_grid__correct_sub_to_image(self):
        mask = np.array([[True, True, True],
                         [True, False, True],
                         [True, True, True]])

        sub_to_image = mapping_util.sub_to_image_from_mask(mask, sub_grid_size=2)

        assert (sub_to_image == np.array([0, 0, 0, 0])).all()

    def test__3x3_mask_with_row_of_pixels_pixel__2x2_sub_grid__correct_sub_to_image(self):
        mask = np.array([[True, True, True],
                         [False, False, False],
                         [True, True, True]])

        sub_to_image = mapping_util.sub_to_image_from_mask(mask, sub_grid_size=2)

        assert (sub_to_image == np.array([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2])).all()

    def test__3x3_mask_with_row_of_pixels_pixel__3x3_sub_grid__correct_sub_to_image(self):
        mask = np.array([[True, True, True],
                         [False, False, False],
                         [True, True, True]])

        sub_to_image = mapping_util.sub_to_image_from_mask(mask, sub_grid_size=3)

        assert (sub_to_image == np.array([0, 0, 0, 0, 0, 0, 0, 0, 0,
                                          1, 1, 1, 1, 1, 1, 1, 1, 1,
                                          2, 2, 2, 2, 2, 2, 2, 2, 2])).all()


class TestMap2DArrayTo1d(object):

    def test__setup_3x3_data(self):
        array_2d = np.array([[1, 2, 3],
                             [4, 5, 6],
                             [7, 8, 9]])

        mask = np.array([[True, True, True],
                         [True, False, True],
                         [True, True, True]])

        array_1d = mapping_util.map_2d_array_to_masked_1d_array_from_array_2d_and_mask(mask, array_2d)

        assert (array_1d == np.array([5])).all()

    def test__setup_3x3_array__five_now_in_mask(self):
        array_2d = np.array([[1, 2, 3],
                             [4, 5, 6],
                             [7, 8, 9]])

        mask = np.array([[True, False, True],
                         [False, False, False],
                         [True, False, True]])

        array_1d = mapping_util.map_2d_array_to_masked_1d_array_from_array_2d_and_mask(mask, array_2d)

        assert (array_1d == np.array([2, 4, 5, 6, 8])).all()

    def test__setup_3x4_array(self):
        array_2d = np.array([[1, 2, 3, 4],
                             [5, 6, 7, 8],
                             [9, 10, 11, 12]])

        mask = np.array([[True, False, True, True],
                         [False, False, False, True],
                         [True, False, True, False]])

        array_1d = mapping_util.map_2d_array_to_masked_1d_array_from_array_2d_and_mask(mask, array_2d)

        assert (array_1d == np.array([2, 5, 6, 7, 10, 12])).all()

    def test__setup_4x3_array__five_now_in_mask(self):
        array_2d = np.array([[1, 2, 3],
                             [4, 5, 6],
                             [7, 8, 9],
                             [10, 11, 12]])

        mask = np.array([[True, False, True],
                         [False, False, False],
                         [True, False, True],
                         [True, True, True]])

        array_1d = mapping_util.map_2d_array_to_masked_1d_array_from_array_2d_and_mask(mask, array_2d)

        assert (array_1d == np.array([2, 4, 5, 6, 8])).all()


class TestMapMasked1DArrayTo2d(object):

    def test__2d_array_is_2x2__is_not_masked__maps_correctly(self):
        array_1d = np.array([1.0, 2.0, 3.0, 4.0])

        one_to_two = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
        shape = (2, 2)

        array_2d = mapping_util.map_masked_1d_array_to_2d_array_from_array_1d_shape_and_one_to_two(array_1d, shape, one_to_two)

        assert (array_2d == np.array([[1.0, 2.0],
                                      [3.0, 4.0]])).all()

    def test__2d_array_is_2x2__is_masked__maps_correctly(self):
        array_1d = np.array([1.0, 2.0, 3.0])

        one_to_two = np.array([[0, 0], [0, 1], [1, 0]])
        shape = (2, 2)

        array_2d = mapping_util.map_masked_1d_array_to_2d_array_from_array_1d_shape_and_one_to_two(array_1d, shape, one_to_two)

        assert (array_2d == np.array([[1.0, 2.0],
                                      [3.0, 0.0]])).all()

    def test__different_shape_and_mappings(self):
        array_1d = np.array([1.0, 2.0, 3.0, -1.0, -2.0, -3.0])

        one_to_two = np.array([[0, 0], [0, 1], [1, 0], [2, 0], [2, 1], [2, 3]])
        shape = (3, 4)

        array_2d = mapping_util.map_masked_1d_array_to_2d_array_from_array_1d_shape_and_one_to_two(array_1d, shape, one_to_two)

        assert (array_2d == np.array([[1.0, 2.0, 0.0, 0.0],
                                      [3.0, 0.0, 0.0, 0.0],
                                      [-1.0, -2.0, 0.0, -3.0]])).all()


class TestMapUnmasked1dArrayTo2d(object):

    def test__1d_array_in__maps_it_to_4x4_2d_array(self):
        array_1d = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0])
        array_2d = mapping_util.map_unmasked_1d_array_to_2d_array_from_array_1d_and_shape(array_1d, shape=(4, 4))

        assert (array_2d == np.array([[1.0, 2.0, 3.0, 4.0],
                                      [5.0, 6.0, 7.0, 8.0],
                                      [9.0, 10.0, 11.0, 12.0],
                                      [13.0, 14.0, 15.0, 16.0]])).all()

    def test__1d_array_in__can_map_it_to_2x3_2d_array(self):
        array_1d = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        array_2d = mapping_util.map_unmasked_1d_array_to_2d_array_from_array_1d_and_shape(array_1d, shape=(2, 3))

        assert (array_2d == np.array([[1.0, 2.0, 3.0],
                                      [4.0, 5.0, 6.0]])).all()

    def test__1d_array_in__can_map_it_to_3x2_2d_array(self):
        array_1d = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        array_2d = mapping_util.map_unmasked_1d_array_to_2d_array_from_array_1d_and_shape(array_1d, shape=(3, 2))

        assert (array_2d == np.array([[1.0, 2.0],
                                      [3.0, 4.0],
                                      [5.0, 6.0]])).all()