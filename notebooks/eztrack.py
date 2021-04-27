import os
os.environ['GDAL_SKIP'] = 'DODS'
import logging
import isce
root_logger = logging.getLogger()
root_logger.setLevel('WARNING')
from carst import SingleRaster, ConfParams
from carst.libft import ampcor_task, writeout_ampcor_task
from carst.libxyz import AmpcoroffFile

import pandas as pd
import ipyleaflet as ilfl
import ipywidgets as iwg
from geostacks import SpatialIndexLS8, SpatialIndexITSLIVE
import xarray as xr
import rasterio
import fsspec

# Adapted from Alice's AGU talk

class eztrack_ui():
    
    def __init__(self, zoom=4, query_pt=[-50., 69.], spatial_index=None):
        
        self.zoom = zoom
        self.query_pt = query_pt
        self.mainmap = None
        self.marker = None
        self.idxs = None
        self.ui_title = None
        self.prlist = []
        self.menuleft = None     # path / row menu
        self.pr_selection = None
        self.kernelselection = None
        self.datesearch_btn = None
        self.scenelist = []
        self.menuright = None    # scene menu
        self.bandselection = None
        self.runft_btn = None
        self.map_polygon = None
        self.spatial_index = spatial_index
        self.output = None       # print message output
        self.results = None
        
    def init_panelleft(self):
        self.ui_title = iwg.HTML("<h2>Drag the marker to your region of interest</h2>")
        self.idxs = self.spatial_index.query_pathrow(self.query_pt)
        self.prlist = [('{:03d}/{:03d}'.format(self.spatial_index.footprint.loc[i, 'path'], self.spatial_index.footprint.loc[i, 'row']) ,i) for i in self.idxs]
        self.menuleft = iwg.Select(options=self.prlist, description='Path/Row:', rows=15)
        self.kernelselection = iwg.RadioButtons(options=['ITS_LIVE (online ready)', 'CARST'], value='ITS_LIVE (online ready)', description='Data / Kernel:')
        self.datesearch_btn = iwg.Button(description='Search for dates')
        
    def init_panelright(self):
        self.menuright = iwg.SelectMultiple(options=self.scenelist, description='Data entries:', rows=20)
        self.bandselection = iwg.RadioButtons(options=['B4', 'B8'], value='B8', description='Band (LS8):')
        self.runft_btn = iwg.Button(description='Get data / Start feature tracking')

    def init_map(self):
        self.mainmap = ilfl.Map(basemap=ilfl.basemaps.Gaode.Satellite, center=[self.query_pt[-1], self.query_pt[0]], zoom=self.zoom)
        self.marker = ilfl.Marker(location=[self.query_pt[-1], self.query_pt[0]], draggable=True)
        self.mainmap.add_layer(self.marker)
        self.pr_selection = self.idxs[0]
        self.scene_list = pd.DataFrame(columns=('prefix', 'time', 'tier'))
        self.map_polygon = ilfl.WKTLayer(wkt_string=self.spatial_index.footprint.loc[self.pr_selection].geometry.wkt)
        self.mainmap.add_layer(self.map_polygon)
        
    def gen_ui(self, spatial_index=None):
        if self.spatial_index is None:
            self.spatial_index = spatial_index
        
        self.init_panelleft()
        self.init_panelright()
        self.init_map()
        
        self.marker.observe(self._on_location_changed, 'location')
        self.menuleft.observe(self._on_menuleft_selection_changed, names='value')
        self.datesearch_btn.on_click(self._on_searchbutton_clicked)
        self.runft_btn.on_click(self._on_ftbutton_clicked)
        
        leftside = iwg.VBox([self.ui_title, self.menuleft, self.kernelselection, self.datesearch_btn])
        leftside.layout.align_items = 'center'
        rightside = iwg.VBox([self.menuright, self.bandselection, self.runft_btn])
        rightside.layout.align_items = 'center'
        return iwg.AppLayout(left_sidebar=leftside, center=self.mainmap, right_sidebar=rightside)

    # ==== leftmenu update when map marker loc changes
    
    def _on_location_changed(self, event):
        # global query_pt, idx
        self.query_pt = [self.marker.location[-1], self.marker.location[0]]
        self.idxs = self.spatial_index.query_pathrow(self.query_pt)
        self.prlist = [('{:03d}/{:03d}'.format(self.spatial_index.footprint.loc[i, 'path'], self.spatial_index.footprint.loc[i, 'row']) ,i) for i in self.idxs]
        self.menuleft.options = self.prlist
        
    # ==== map polygon update when leftmenu selection changes

    def _on_menuleft_selection_changed(self, change):
        # global pr_selection
        self.pr_selection = change['new']
        self.map_polygon.wkt_string=self.spatial_index.footprint.loc[self.pr_selection].geometry.wkt

    # ==== search button click callback

    def _on_searchbutton_clicked(self, event):
        self.output = iwg.Output()
        # global pr_scene_list
        with self.output:
            if self.kernelselection.value == 'CARST':
                s3_prefix, self.scenelist = self.spatial_index.search_s3(self.pr_selection)
                # print(s3_prefix)
                self.menuright.options = [(record['time'], idx) for idx, record in self.scenelist.loc[self.scenelist['tier'] == 'T1'].iterrows()]
            elif self.kernelselection.value == 'ITS_LIVE (online ready)':
                # query_pt = [mker.location[-1], mker.location[0]]
                polygon_coords = SpatialIndexITSLIVE.get_minimal_bbox(self.query_pt)
                params = {'polygon': polygon_coords, 'percent_valid_pixels': 1, 'start': '2015-01-01', 'end': '2020-01-01'}
                urls = SpatialIndexITSLIVE.get_granule_urls(params)
                self.scenelist = SpatialIndexITSLIVE.parse_urls(urls)
                pr_dict_key = '{:03d}/{:03d}'.format(self.spatial_index.footprint.loc[self.pr_selection, 'path'], self.spatial_index.footprint.loc[self.pr_selection, 'row'])
                self.menuright.options = [(i['entrystr'], i['url']) for i in self.scenelist[pr_dict_key]]
                
    # ==== feature tracking button click callback

    # file1_url  = None 
    # file1_date = None 
    # file2_url  = None 
    # file2_date = None

    def _on_ftbutton_clicked(self, ft):
        # global file1_url, file1_date, file2_url, file2_date
        with self.output:
            if self.kernelselection.value == 'CARST':
                selected_list = self.scenelist.loc[list(self.menuright.value)]
                selected_list_prefix = selected_list['prefix'].tolist()
                selected_list_time = selected_list['time'].tolist()
                file1_url = 'https://landsat-pds.s3.amazonaws.com/' + selected_list_prefix[0] + os.path.basename(selected_list_prefix[0][:-1]) + '_' + self.bandselection.value + '.TIF'
                file2_url = 'https://landsat-pds.s3.amazonaws.com/' + selected_list_prefix[1] + os.path.basename(selected_list_prefix[1][:-1]) + '_' + self.bandselection.value + '.TIF'
                file1_date = selected_list_time[0].strftime('%Y-%m-%d')
                file2_date = selected_list_time[1].strftime('%Y-%m-%d')
                print(file1_url, file1_date, file2_url, file2_date)
                carst_featuretrack(file1_url, file1_date, file2_url, file2_date)
                self.results = rasterio.open(selected_list_time[0].strftime('%Y%m%d') + '-' + selected_list_time[1].strftime('%Y%m%d') + '_velo-raw_mag.tif')
            elif self.kernelselection.value == 'ITS_LIVE (online ready)':
                print(self.menuright.value)
                with fsspec.open(self.menuright.value[0]) as fobj:
                    self.results = xr.open_dataset(fobj)

                    
# CARST feature tracking workflow                    

def carst_featuretrack(file1_url, file1_date, file2_url, file2_date, inipath='param.ini'):
    ini = ConfParams(inipath)
    ini.ReadParam()
    ini.imagepair['image1'] = file1_url
    ini.imagepair['image2'] = file2_url
    ini.imagepair['image1_date'] = file1_date
    ini.imagepair['image2_date'] = file2_date
    ini.VerifyParam()
    a = SingleRaster(file1_url, date=file1_date)
    b = SingleRaster(file2_url, date=file2_date)
    if ini.pxsettings['gaussian_hp']:
        a.GaussianHighPass(sigma=ini.pxsettings['gaussian_hp_sigma'])
        b.GaussianHighPass(sigma=ini.pxsettings['gaussian_hp_sigma'])
    a.AmpcorPrep()
    b.AmpcorPrep()
    task = ampcor_task([a, b], ini)
    writeout_ampcor_task(task, ini)
    ampoff = AmpcoroffFile(ini.rawoutput['label_ampcor'] + '.p')
    ampoff.Load()
    ampoff.SetIni(ini)
    ampoff.FillwithNAN()   # fill holes with nan
    ampoff.Ampcoroff2Velo()
    ampoff.Velo2XYV(generate_xyztext=ini.rawoutput['if_generate_xyztext'])
    ampoff.XYV2Raster()















