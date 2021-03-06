import numpy as np
import pytest

from autolens.data import ccd, convolution
from autolens.data.array.util import grid_util
from autolens.data.array import scaled_array
from autolens.data.array import mask as msk
from autolens.lens import lens_data as ld
from autolens.model.inversion import convolution as inversion_convolution


@pytest.fixture(name='ccd')
def make_ccd():

    image = scaled_array.ScaledSquarePixelArray(array=np.ones((4, 4)), pixel_scale=3.0)
    psf = ccd.PSF(array=np.ones((3, 3)), pixel_scale=3.0, renormalize=False)
    noise_map = ccd.NoiseMap(array=2.0 * np.ones((4, 4)), pixel_scale=3.0)
    background_noise_map = ccd.NoiseMap(array=3.0 * np.ones((4, 4)), pixel_scale=3.0)
    poisson_noise_map = ccd.PoissonNoiseMap(array=4.0 * np.ones((4, 4)), pixel_scale=3.0)
    exposure_time_map = ccd.ExposureTimeMap(array=5.0 * np.ones((4, 4)), pixel_scale=3.0)
    background_sky_map = scaled_array.ScaledSquarePixelArray(array=6.0 * np.ones((4, 4)), pixel_scale=3.0)

    return ccd.CCDData(image=image, pixel_scale=3.0, psf=psf, noise_map=noise_map,
                       background_noise_map=background_noise_map, poisson_noise_map=poisson_noise_map,
                       exposure_time_map=exposure_time_map, background_sky_map=background_sky_map)

@pytest.fixture(name="mask")
def make_mask():
    return msk.Mask(np.array([[True, True, True, True],
                              [True, False, False, True],
                              [True, False, False, True],
                              [True, True, True, True]]), pixel_scale=3.0)

@pytest.fixture(name="lens_data")
def make_lens_ccd(ccd, mask):
    return ld.LensData(ccd_data=ccd, mask=mask)


class TestLensData(object):

    def test_attributes(self, ccd, lens_data):

        assert lens_data.pixel_scale == ccd.pixel_scale
        assert lens_data.pixel_scale == 3.0

        assert (lens_data.image == ccd.image).all()
        assert (lens_data.image == np.ones((4,4))).all()

        assert (lens_data.psf == ccd.psf).all()
        assert (lens_data.psf == np.ones((3,3))).all()

        assert (lens_data.noise_map == ccd.noise_map).all()
        assert (lens_data.noise_map == 2.0*np.ones((4,4))).all()

        assert lens_data.image_psf_shape == (3,3)
        assert lens_data.mapping_matrix_psf_shape == (3,3)

    def test_masking(self, lens_data):

        assert (lens_data.image_1d == np.ones(4)).all()
        assert (lens_data.noise_map_1d == 2.0*np.ones(4)).all()
        assert (lens_data.mask_1d == np.array([False, False, False, False])).all()

    def test_grids(self, lens_data):

        assert (lens_data.grid_stack.regular == np.array([[1.5, -1.5], [1.5, 1.5], [-1.5, -1.5], [-1.5, 1.5]])).all()
        assert (lens_data.grid_stack.sub == np.array([[2.0, -2.0], [2.0, -1.0], [1.0, -2.0], [1.0, -1.0],
                                                     [2.0, 1.0], [2.0, 2.0], [1.0, 1.0], [1.0, 2.0],
                                                     [-1.0, -2.0], [-1.0, -1.0], [-2.0, -2.0], [-2.0, -1.0],
                                                     [-1.0, 1.0], [-1.0, 2.0], [-2.0, 1.0], [-2.0, 2.0]])).all()
        assert (lens_data.grid_stack.blurring == np.array([[4.5, -4.5], [4.5, -1.5], [4.5, 1.5], [4.5, 4.5],
                                                          [1.5, -4.5], [1.5, 4.5], [-1.5, -4.5], [-1.5, 4.5],
                                                          [-4.5, -4.5], [-4.5, -1.5], [-4.5, 1.5], [-4.5, 4.5]])).all()

    def test_padded_grid_stack(self, lens_data):

        padded_image_util = grid_util.regular_grid_1d_masked_from_mask_pixel_scales_and_origin(mask=np.full((6, 6), False),
                                                                        pixel_scales=lens_data.image.pixel_scales)

        assert (lens_data.padded_grid_stack.regular == padded_image_util).all()
        assert lens_data.padded_grid_stack.regular.image_shape == (4, 4)
        assert lens_data.padded_grid_stack.regular.padded_shape == (6, 6)

        padded_sub_util = grid_util.sub_grid_1d_masked_from_mask_pixel_scales_and_sub_grid_size(
            mask=np.full((6, 6), False), pixel_scales=lens_data.image.pixel_scales,
            sub_grid_size=lens_data.grid_stack.sub.sub_grid_size)

        assert lens_data.padded_grid_stack.sub == pytest.approx(padded_sub_util, 1e-4)
        assert lens_data.padded_grid_stack.sub.image_shape == (4, 4)
        assert lens_data.padded_grid_stack.sub.padded_shape == (6, 6)

        assert (lens_data.padded_grid_stack.blurring == np.array([[0.0, 0.0]])).all()

    def test_border(self, lens_data):
        assert (lens_data.border == np.array([0, 1, 2, 3])).all()

    def test_convolvers(self, lens_data):
        assert type(lens_data.convolver_image) == convolution.ConvolverImage
        assert type(lens_data.convolver_mapping_matrix) == inversion_convolution.ConvolverMappingMatrix

    def test__constructor_inputs(self):

        psf = ccd.PSF(np.ones((7, 7)), 1)
        image = ccd.CCDData(np.ones((51, 51)), pixel_scale=3., psf=psf, noise_map=np.ones((51, 51)))
        mask = msk.Mask.unmasked_for_shape_and_pixel_scale(shape=(51, 51), pixel_scale=1.0, invert=True)
        mask[26, 26] = False

        lens_data = ld.LensData(image, mask, sub_grid_size=8, image_psf_shape=(5, 5),
                                 mapping_matrix_psf_shape=(3, 3), positions=[np.array([[1.0, 1.0]])])

        assert lens_data.sub_grid_size == 8
        assert lens_data.convolver_image.psf_shape == (5, 5)
        assert lens_data.convolver_mapping_matrix.psf_shape == (3, 3)
        assert (lens_data.positions[0] == np.array([[1.0, 1.0]])).all()

        assert lens_data.image_psf_shape == (5,5)
        assert lens_data.mapping_matrix_psf_shape == (3,3)

    def test_lens_data_with_modified_image(self, lens_data):

        lens_data = lens_data.new_lens_data_with_modified_image(modified_image=8.0 * np.ones((4, 4)))

        assert (lens_data.image == 8.0*np.ones((4,4))).all()
        assert (lens_data.image_1d == 8.0*np.ones(4)).all()

@pytest.fixture(name="lens_data_hyper")
def make_lens_hyper_image(ccd, mask):

    return ld.LensDataHyper(ccd_data=ccd, mask=mask, hyper_model_image=10.0 * np.ones((4, 4)),
                            hyper_galaxy_images=[11.0*np.ones((4,4)), 12.0*np.ones((4,4))],
                            hyper_minimum_values=[0.1, 0.2])


class TestLensDataHyper(object):

    def test_attributes(self, ccd, lens_data_hyper):

        assert lens_data_hyper.pixel_scale == ccd.pixel_scale

        assert (lens_data_hyper.image == ccd.image).all()
        assert (lens_data_hyper.image == np.ones((4,4))).all()

        assert (lens_data_hyper.psf == ccd.psf).all()
        assert (lens_data_hyper.psf == np.ones((3,3))).all()

        assert (lens_data_hyper.noise_map == ccd.noise_map).all()
        assert (lens_data_hyper.noise_map == 2.0*np.ones((4,4))).all()

        assert (lens_data_hyper.hyper_model_image == 10.0*np.ones((4,4))).all()
        assert (lens_data_hyper.hyper_galaxy_images[0] == 11.0*np.ones((4,4))).all()
        assert (lens_data_hyper.hyper_galaxy_images[1] == 12.0*np.ones((4,4))).all()

        assert lens_data_hyper.hyper_minimum_values == [0.1, 0.2]

    def test_masking(self, lens_data_hyper):

        assert (lens_data_hyper.image_1d == np.ones(4)).all()
        assert (lens_data_hyper.noise_map_1d == 2.0*np.ones(4)).all()

        assert (lens_data_hyper.hyper_model_image_1d == 10.0*np.ones(4)).all()
        assert (lens_data_hyper.hyper_galaxy_images_1d[0] == 11.0*np.ones(4)).all()
        assert (lens_data_hyper.hyper_galaxy_images_1d[1] == 12.0*np.ones(4)).all()
