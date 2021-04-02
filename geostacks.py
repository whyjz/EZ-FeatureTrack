import pandas as pd
import geopandas as gpd
import itertools
from shapely.geometry import Point, Polygon, MultiPolygon
import numpy as np
from sklearn.neighbors import BallTree

class SpatialIndex:
    
    def __init__(self, fname):
        
        self.fname = fname
        self.corner_pts_df = None
        self.footprint = None
        
    @staticmethod        
    def _check_crossing(lon_list):
        """
        Checks if the antimeridian is crossed.
        lon_list has four elements: [lon_UL, lon_UR, lon_LR, lon_LL] which defines an image boundary.
        """
        return any(abs(pair[0] - pair[1]) > 180.0 for pair in itertools.combinations(lon_list, 2))


class SpatialIndexLS8(SpatialIndex):
    
    def gen_geometries(self):
        """
        Create a polygon object for each LS8 grid point. 
        If the polygon runs across the antimeridian, The polygon will be separated into two 
        adjacent polygons along the antimeridian, and these two polygons will be grouped into
        a single MultiPolygon object.
        """
        geometry_collection = []
        for index, row in self.corner_pts_df.iterrows():
            lon_list = [row.lon_UL, row.lon_UR, row.lon_LR, row.lon_LL]
            if self._check_crossing(lon_list):
                set1 = [x % 360.0 for x in lon_list]
                set2 = [x % -360.0 for x in lon_list]
                poly1 = Polygon([(set1[0], row.lat_UL), (set1[1], row.lat_UR), (set1[2], row.lat_LR), (set1[3], row.lat_LL)])
                poly2 = Polygon([(set2[0], row.lat_UL), (set2[1], row.lat_UR), (set2[2], row.lat_LR), (set2[3], row.lat_LL)])
                feature_geometry = MultiPolygon([poly1, poly2])
            else:
                feature_geometry = Polygon([(row.lon_UL, row.lat_UL), (row.lon_UR, row.lat_UR), (row.lon_LR, row.lat_LR), (row.lon_LL, row.lat_LL)])
            geometry_collection.append(feature_geometry)

        return geometry_collection
    
    def read(self):
        
        self.corner_pts_df = pd.read_excel(self.fname)
        geometry_collection = self.gen_geometries()
        self.footprint = gpd.GeoDataFrame(self.corner_pts_df, geometry=geometry_collection)
        self.footprint = self.footprint.drop(['lat_UL', 'lon_UL', 'lat_UR', 'lon_UR', 'lat_LL', 'lon_LL', 'lat_LR', 'lon_LR'], axis=1)
        
    def query_pathrow(self, point_geometry):
        '''
        Query the available LS8 Path/Row combinations for a given point in [lon, lat].
        We use a two-step process:
        (1) a ball tree search for all of the LS8 center points that are within 0.05 radians 
            (~2.85 degrees) from the query point.
        (2) a point-in-polygon search using the results from (1). 

        input:
            points_geometry: 2-element list showing [lon, lat]
            self.footprint (polygon_data): the LS8 footprint (GeoDataFrame object)
        output:
            selection_idx: index numbers for the right Path/Row.
        '''

        # (1) Ball Tree
        points = np.vstack((self.footprint.lon_CTR.values, self.footprint.lat_CTR.values)).T
        points *= np.pi/180.
        LSBall = BallTree(points, metric='haversine')

        q = np.array(point_geometry)
        q *= np.pi/180.
        if type(point_geometry) is Point:
            pt = point_geometry
        else:
            pt = Point(point_geometry)

        pre_selection = LSBall.query_radius(q.reshape(1,-1), r=0.05, return_distance=False)
        pre_selection_idx = pre_selection[0]
        pre_selection_idx.sort()
        polygon_pre_selection = self.footprint.loc[pre_selection_idx]

        # (2) Point-in-polygon
        selection_idx = []
        for idx, row in polygon_pre_selection.iterrows():
            if pt.within(row.geometry):
                selection_idx.append(idx)

        return selection_idx