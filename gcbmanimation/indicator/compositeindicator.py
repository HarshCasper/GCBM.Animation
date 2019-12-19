import os
from glob import glob
from gcbmanimation.indicator.indicator import Indicator
from gcbmanimation.indicator.indicator import Units
from gcbmanimation.provider.spatialgcbmresultsprovider import SpatialGcbmResultsProvider
from gcbmanimation.plot.basicresultsplot import BasicResultsPlot
from gcbmanimation.layer.layercollection import LayerCollection
from gcbmanimation.layer.layer import Layer

class CompositeIndicator(Indicator):
    '''
    A spatial-only indicator that combines multiple GCBM outputs into a single one,
    i.e. all of the components that make up NBP into NBP.

    Arguments:
    'indicator' -- the short name of the indicator.
    'patterns' -- a dictionary of file pattern (including directory path) in glob
        format to blend mode, where the file pattern is used to find the spatial
        outputs for an indicator, i.e. "c:\\my_run\\NPP_*.tif", and the blend mode
        is used to combine the indicator into a composite value.
    'title' -- the indicator title for presentation - uses the indicator name if
        not provided.
    'graph_units' -- a Units enum value for the graph units - result values will
        be divided by this amount.
    'map_units' -- a Units enum value for the map units - spatial output values
        will not be modified, but it is important for this to match the spatial
        output units for the correct unit labels to be displayed in the rendered
        Frames.
    'palette' -- the color palette to use for the rendered map frames - can be the
        name of any seaborn palette (deep, muted, bright, pastel, dark, colorblind,
        hls, husl) or matplotlib colormap. To find matplotlib colormaps:
        from matplotlib import cm; dir(cm)
    'background_color' -- the background (bounding box) color to use for the map
        frames.
    '''

    def __init__(self, indicator, patterns, title=None, graph_units=Units.Tc,
                 map_units=Units.TcPerHa, palette="Greens", background_color=(255, 255, 255)):
        super().__init__(indicator, None, None, None, title, graph_units, map_units,
                         palette, background_color)

        self._patterns = patterns
        self._composite_layers = None

    def render_map_frames(self, bounding_box=None):
        '''
        Renders the indicator's spatial output into colorized Frame objects.

        Arguments:
        'bounding_box' -- optional bounding box Layer; spatial output will be
            cropped to the bounding box's minimum spatial extent and nodata pixels.

        Returns a list of colorized Frames, one for each year of output, and a
        legend in dictionary format describing the colors.
        '''
        self._init()
        start_year, end_year = self._results_provider.simulation_years
        
        return self._composite_layers.render(bounding_box, start_year, end_year)

    def render_graph_frames(self, **kwargs):
        '''
        Renders the indicator's non-spatial output into a graph.

        Arguments:
        Any accepted by GCBMResultsProvider and subclasses.

        Returns a list of Frames, one for each year of output.
        '''
        self._init()
        plot = BasicResultsPlot(self._indicator, self._results_provider, self._graph_units)
        
        return plot.render(**kwargs)

    def _init(self):
        if not self._composite_layers:
            self._composite_layers = LayerCollection(
                palette=self._palette, background_color=self._background_color)

            for pattern, blend_mode in self._patterns.items():
                layers = self._find_layers(pattern)
                self._composite_layers = self._composite_layers.blend(layers, blend_mode)

            self._results_provider = SpatialGcbmResultsProvider(
                layers=self._composite_layers.layers,
                per_hectare=self._map_units == Units.TcPerHa)
       
    def _find_layers(self, pattern):
        layers = LayerCollection(palette=self._palette, background_color=self._background_color)
        for layer_path in glob(pattern):
            year = os.path.splitext(layer_path)[0][-4:]
            layer = Layer(layer_path, year)
            layers.append(layer)

        if not layers:
            raise IOError(f"No spatial output found for pattern: {pattern}")

        return layers
