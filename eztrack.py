import pandas as pd
import ipyleaflet as ilfl
import ipywidgets as iwg
from geostacks import SpatialIndexLS8, SpatialIndexITSLIVE

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
        
    def _init_panelleft(self):
        self.ui_title = iwg.HTML("<h2>Drag the marker to your region of interest</h2>")
        self.idxs = self.spatial_index.query_pathrow(self.query_pt)
        self.prlist = [('{:03d}/{:03d}'.format(self.spatial_index.footprint.loc[i, 'path'], self.spatial_index.footprint.loc[i, 'row']) ,i) for i in self.idxs]
        self.menuleft = iwg.Select(options=self.prlist, description='Path/Row:', rows=15)
        self.kernelselection = iwg.RadioButtons(options=['ITS_LIVE (online ready)', 'CARST'], value='ITS_LIVE (online ready)', description='Data / Kernel:')
        self.datesearch_btn = iwg.Button(description='Search for dates')
        
    def _init_panelright(self):
        self.menuright = iwg.SelectMultiple(options=self.scenelist, description='Data entries:', rows=20)
        self.bandselection = iwg.RadioButtons(options=['B4', 'B8'], value='B8', description='Band:')
        self.runft_btn = iwg.Button(description='Start feature tracking')

    def _init_map(self):
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
        
        self._init_panelleft()
        self._init_panelright()
        self._init_map()
        
        leftside = iwg.VBox([self.ui_title, self.menuleft, self.kernelselection, self.datesearch_btn])
        leftside.layout.align_items = 'center'
        rightside = iwg.VBox([self.menuright, self.bandselection, self.runft_btn])
        rightside.layout.align_items = 'center'
        return iwg.AppLayout(left_sidebar=leftside, center=self.mainmap, right_sidebar=rightside)

    # ==== map marker callback
        
#     def _on_location_changed(event):
#         global query_pt, idx
#         query_pt = [mker.location[-1], mker.location[0]]
#         idx = ls8_indexquery_pathrow(query_pt)
#         pr_options_new = [('{:03d}/{:03d}'.format(ls8_index.footprint.loc[i, 'path'], ls8_index.footprint.loc[i, 'row']) ,i) for i in idx]
#         pr_menu.options = pr_options_new
        
        
#     def eom
    
    # mker.observe(on_location_changed, 'location')













# # ==== left side menu selection callback

# def on_menu_selection_changed(change):
#     global pr_selection
#     pr_selection = change['new']
#     pr_polygon.wkt_string=ls8_index.footprint.loc[pr_selection].geometry.wkt

# pr_menu.observe(on_menu_selection_changed, names='value')

# # ==== search button click callback

# output = iwg.Output()
# def on_searchbutton_clicked(b):
#     global pr_scene_list
#     with output:
#         if pr_kernel_selection.value == 'CARST':
#             s3_prefix, pr_scene_list = ls8_index.search_s3(pr_selection)
#             # print(s3_prefix)
#             pr_scene_menu.options = [(record['time'], idx) for idx, record in pr_scene_list.loc[pr_scene_list['tier'] == 'T1'].iterrows()]
#         elif pr_kernel_selection.value == 'ITS_LIVE (online ready)':
#             query_pt = [mker.location[-1], mker.location[0]]
#             polygon_coords = itslive_api.get_minimal_bbox(query_pt)
#             params = {'polygon': polygon_coords, 'percent_valid_pixels': 1, 'start': '2015-01-01', 'end': '2020-01-01'}
#             urls = itslive_api.get_granule_urls(params)
#             pr_dict = itslive_api.parse_urls(urls)
#             pr_dict_key = '{:03d}/{:03d}'.format(ls8_gdf.loc[pr_selection, 'path'], ls8_gdf.loc[pr_selection, 'row'])
#             pr_scene_menu.options = pr_dict[pr_dict_key]
            
# pr_scene_button.on_click(on_searchbutton_clicked)

# # ==== feature tracking button click callback

# file1_url  = None 
# file1_date = None 
# file2_url  = None 
# file2_date = None

# def on_ftbutton_clicked(ft):
#     global file1_url, file1_date, file2_url, file2_date
#     with output:
#         selected_list = pr_scene_list.loc[list(pr_scene_menu.value)]
#         selected_list_prefix = selected_list['prefix'].tolist()
#         selected_list_time = selected_list['time'].tolist()
#         file1_url = 'https://landsat-pds.s3.amazonaws.com/' + selected_list_prefix[0] + os.path.basename(selected_list_prefix[0][:-1]) + '_' + band_radiobuttons.value + '.TIF'
#         file2_url = 'https://landsat-pds.s3.amazonaws.com/' + selected_list_prefix[1] + os.path.basename(selected_list_prefix[1][:-1]) + '_' + band_radiobuttons.value + '.TIF'
#         file1_date = selected_list_time[0].strftime('%Y-%m-%d')
#         file2_date = selected_list_time[1].strftime('%Y-%m-%d')
#         print(file1_url, file1_date, file2_url, file2_date)
#         carst_featuretrack(file1_url, file1_date, file2_url, file2_date)

# ft_start_button.on_click(on_ftbutton_clicked)



