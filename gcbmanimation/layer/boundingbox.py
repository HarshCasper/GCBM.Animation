import os
import gdal
import numpy as np
from osgeo.scripts import gdal_calc
from gcbmanimation.layer.layer import Layer
from gcbmanimation.util.tempfile import TempFileManager

class BoundingBox(Layer):
    '''
    A type of Layer that can crop other Layer objects to its minimum spatial extent
    and nodata pixels.

    Arguments:
    'path' -- path to a raster file to use as a bounding box.
    '''

    def __init__(self, path):
        super().__init__(path, 0)
        self._min_pixel_bounds = None
        self._min_geographic_bounds = None
        self._initialized = False
    
    @property
    def min_pixel_bounds(self):
        '''
        The minimum pixel bounds of the bounding box: the minimum box surrounding
        the non-nodata pixels in the layer.
        '''
        if not self._min_pixel_bounds:
            raster_data = gdal.Open(self._path).ReadAsArray()
            x_min = raster_data.shape[1]
            x_max = 0
            y_min = 0
            y_max = 0
            for i, row in enumerate(raster_data):
                x_index = np.where(row != self.nodata_value)[0] # First non-null value per row.
                if len(x_index) == 0:
                    continue

                x_index_min = np.min(x_index)
                x_index_max = np.max(x_index)
                y_min = i           if y_min == 0          else y_min
                x_min = x_index_min if x_index_min < x_min else x_min
                x_max = x_index_max if x_index_max > x_max else x_max
                y_max = i

            self._min_pixel_bounds = [x_min - 1, x_max + 1, y_min - 1, y_max + 1]

        return self._min_pixel_bounds

    @property
    def min_geographic_bounds(self):
        '''
        The minimum spatial extent of the bounding box: the minimum box surrounding
        the non-nodata pixels in the layer.
        '''
        if not self._min_geographic_bounds:
            x_min, x_max, y_min, y_max = self.min_pixel_bounds
            origin_x, x_size, _, origin_y, _, y_size, *_ = gdal.Open(self._path).GetGeoTransform()
        
            x_min_proj = origin_x + x_min * x_size
            x_max_proj = origin_x + x_max * x_size
            y_min_proj = origin_y + y_min * y_size
            y_max_proj = origin_y + y_max * y_size

            self._min_geographic_bounds = [x_min_proj, y_min_proj, x_max_proj, y_max_proj]

        return self._min_geographic_bounds

    def crop(self, layer):
        '''
        Crops a Layer to the minimum spatial extent and nodata pixels of this
        bounding box.

        Arguments:
        'layer' -- the layer to crop.

        Returns a new cropped Layer object.
        '''
        if not self._initialized:
            bbox_path = TempFileManager.mktmp(suffix=".tif")
            gdal.Translate(bbox_path, gdal.Open(self._path), projWin=self.min_geographic_bounds)
            self._path = bbox_path
            self._initialized = True

        # Clip to bounding box geographical area.
        tmp_path = TempFileManager.mktmp(suffix=".tif")
        gdal.Translate(tmp_path, gdal.Open(layer.path), projWin=self.min_geographic_bounds)
        
        # Clip to bounding box nodata mask.
        calc = "A * (B != {0}) + ((B == {0}) * {1})".format(
            self.nodata_value, layer.nodata_value)

        output_path = TempFileManager.mktmp(suffix=".tif")
        gdal_calc.Calc(calc, output_path, layer.nodata_value, quiet=True,
                       creation_options=["BIGTIFF=YES", "COMPRESS=DEFLATE"],
                       overwrite=True, A=tmp_path, B=self.path)

        cropped_layer = Layer(output_path, layer.year, layer.interpretation)

        return cropped_layer
