import os
import pandas as pd
import geopandas as gpd
import itertools
from shapely.geometry import Point, Polygon, MultiPolygon, box
import numpy as np
from sklearn.neighbors import BallTree
import requests
import boto3
import botocore
from datetime import datetime


class SpatialIndex:

    def __init__(self, fname=None):

        self.fname = fname
        self.corner_pts_df = None
        self.footprint = None

    @staticmethod
    def _check_crossing(lon_list):
        """
        Checks if the antimeridian is crossed.
        lon_list has four elements: [lon_UL, lon_UR, lon_LR, lon_LL]
        which defines an image boundary.
        """
        return any(abs(pair[0] - pair[1]) >
                   180.0 for pair in itertools.combinations(lon_list, 2))


class SpatialIndexLS8(SpatialIndex):

    def gen_geometries(self):
        """
        Create a polygon object for each LS8 grid point.
        If the polygon runs across the antimeridian, The polygon will be
        separated into two adjacent polygons along the antimeridian, and these
        two polygons will be grouped into a single MultiPolygon object.
        """
        geometry_collection = []
        for index, row in self.corner_pts_df.iterrows():
            lon_list = [row.lon_UL, row.lon_UR, row.lon_LR, row.lon_LL]
            if self._check_crossing(lon_list):
                set1 = [x % 360.0 for x in lon_list]
                set2 = [x % -360.0 for x in lon_list]
                poly1 = Polygon([(set1[0], row.lat_UL),
                                 (set1[1], row.lat_UR),
                                 (set1[2], row.lat_LR),
                                 (set1[3], row.lat_LL)])
                poly2 = Polygon([(set2[0], row.lat_UL),
                                 (set2[1], row.lat_UR),
                                 (set2[2], row.lat_LR),
                                 (set2[3], row.lat_LL)])
                feature_geometry = MultiPolygon([poly1, poly2])
            else:
                feature_geometry = Polygon([(row.lon_UL, row.lat_UL),
                                            (row.lon_UR, row.lat_UR),
                                            (row.lon_LR, row.lat_LR),
                                            (row.lon_LL, row.lat_LL)])
            geometry_collection.append(feature_geometry)

        return geometry_collection

    def read(self):
        
        if self.fname.endswith('.xls'):
            self.corner_pts_df = pd.read_excel(self.fname)
        elif self.fname.endswith('.csv'):
            self.corner_pts_df = pd.read_csv(self.fname)
        else:
            print('Error: unsupported file format')
        self.corner_pts_df = self.corner_pts_df.astype({'path': int, 'row': int})
        geometry_collection = self.gen_geometries()
        self.footprint = gpd.GeoDataFrame(self.corner_pts_df,
                                          geometry=geometry_collection)
        self.footprint = self.footprint.drop(['lat_UL', 'lon_UL', 'lat_UR',
                                              'lon_UR', 'lat_LL', 'lon_LL',
                                              'lat_LR', 'lon_LR'], axis=1)

    def query_pathrow(self, point_geometry):
        '''
        Query available LS8 Path/Row combinations for a point in [lon, lat].
        We use a two-step process:
        (1) a ball tree search for all of the LS8 center points that are
            within 0.05 radians (~2.85 degrees) from the query point.
        (2) a point-in-polygon search using the results from (1).

        input:
            points_geometry: 2-element list showing [lon, lat]
            self.footprint (polygon_data): the LS8 footprint (GeoDataFrame)
        output:
            selection_idx: index numbers for the right Path/Row.
        '''

        # (1) Ball Tree
        points = np.vstack((self.footprint.lon_CTR.values,
                            self.footprint.lat_CTR.values)).T
        points *= np.pi/180.
        LSBall = BallTree(points, metric='haversine')

        q = np.array(point_geometry)
        q *= np.pi/180.
        if type(point_geometry) is Point:
            pt = point_geometry
        else:
            pt = Point(point_geometry)

        pre_selection = LSBall.query_radius(q.reshape(1, -1),
                                            r=0.05,
                                            return_distance=False)
        pre_selection_idx = pre_selection[0]
        pre_selection_idx.sort()
        polygon_pre_selection = self.footprint.loc[pre_selection_idx]

        # (2) Point-in-polygon
        selection_idx = []
        for idx, row in polygon_pre_selection.iterrows():
            if pt.within(row.geometry):
                selection_idx.append(idx)

        return selection_idx

    def search_s3(self, pr_idx):
        s3_pathrow = '{:03d}/{:03d}'.format(self.footprint.loc[pr_idx].path,
                                            self.footprint.loc[pr_idx].row)
        s3_prefix = 'c1/L8/' + s3_pathrow + '/LC08_L1TP_'
        # print(s3_prefix)

        # according to https://github.com/boto/boto3/issues/1200
        s3 = boto3.client('s3', region_name='us-west-2',
                          config=botocore.config.Config(
                            signature_version=botocore.UNSIGNED))

        # https://towardsdatascience.com/
        #        working-with-amazon-s3-buckets-with-boto3-785252ea22e0
        response = s3.list_objects_v2(Bucket="landsat-pds", MaxKeys=1000,
                                      Prefix=s3_prefix, Delimiter='/')

        scene_list = pd.DataFrame(columns=('prefix', 'time', 'tier'))
        scene_idx = 0

        if response.get('CommonPrefixes') is None:
            # print('No available scenes!')
            pass
        else:
            for scene in response.get('CommonPrefixes'):
                scene_prefix = scene.get('Prefix')
                # print(scene.get('Prefix'))
                timestamp = scene_prefix.split('_')[3]
                timestamp = datetime.strptime(timestamp, '%Y%m%d')
                timestamp = timestamp.date()
                tierstate = scene_prefix.split('_')[6][:-1]
                # print(timestamp, tierstate)
                scene_list.loc[scene_idx] = [scene_prefix,
                                             timestamp, tierstate]
                scene_idx += 1

        return s3_prefix, scene_list


class SpatialIndexITSLIVE(SpatialIndex):
    # modified from https://github.com/nasa-jpl/itslive
    @staticmethod
    def get_granule_urls(params):
        '''
        params example:
        params = {'polygon': '-50.0783,69.6975,-50.0783,69.6995,
                              -50.0763,69.6995,-50.0763,69.6975,
                              -50.0783,69.6975',
            'percent_valid_pixels': 1, 'start': '2017-08-29',
                                        'end': '2019-03-31'}
        '''
        base_url = 'https://nsidc.org/apps/itslive-search/velocities/urls'
        resp = requests.get(base_url, params=params, verify=False)
        return resp.json()

    @staticmethod
    def get_minimal_bbox(query_pt):
        """
        a very rough approximation of a small bbox less than 1km
        of a given lon-lat point

        params: geometry, a geojson point geometry
        """
        lon = query_pt[0]
        lat = query_pt[1]
        lon_offset = -0.001 if lon < 0.0 else 0.001
        lat_offset = -0.001 if lat < 0.0 else 0.001

        bbox = box(lon - lon_offset,
                   lat - lat_offset,
                   lon + lon_offset, lat + lat_offset)
        coords = [[str(float("{:.4f}".format(coord[0]))),
                   str(float("{:.4f}".format(coord[1])))]
                  for coord in bbox.exterior.coords]
        coords = list(itertools.chain.from_iterable(coords))
        return ','.join(coords)

    @staticmethod
    def parse_urls(urls):
        '''
        parse urls
        '''
        pr_dict = {}
        for url_dict in urls:
            file_name = os.path.basename(url_dict['url'])
            file_components = file_name.split('_')
            prstr = file_components[2]
            prstr = prstr[:3] + '/' + prstr[-3:]
            start_date = datetime.strptime(file_components[11],
                                           "%Y%m%d").date()
            end_date = datetime.strptime(file_components[3],
                                         "%Y%m%d").date()
            pair_days = end_date - start_date
            img1_tier = file_components[14]
            img2_tier = file_components[6]
            # For now let's show results using T1 images only
            if img1_tier != 'RT' and img2_tier != 'RT':
                # if prstr == '083/232':
                #     print(url_dict['url'])
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = end_date.strftime('%Y-%m-%d')
                entrystr = ' / '.join((start_date_str,
                                       end_date_str,
                                       f'{pair_days.days} days'))
                pr_dict_entry = {'entrystr': entrystr, 'url': url_dict['url']}
                if prstr in pr_dict:
                    pr_dict[prstr].append(pr_dict_entry)
                else:
                    pr_dict[prstr] = [pr_dict_entry]

        for key in pr_dict:
            pr_dict[key].sort(key=lambda x: x.get('entrystr'))
        return pr_dict
