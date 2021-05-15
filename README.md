# EZ-FeatureTrack

An open-source, interactive, and highly customizable workflow for glacier velocity mapping using feature tracking technique and satellite images. 

Try the demo notebook!

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/whyjz/EZ-FeatureTrack/HEAD?urlpath=lab/tree/notebooks/WZ_01_mapping_ice_flow_velocity.ipynb)

## About this project

Observations of ice flow velocity provide a key component for modeling glacier dynamics and mass balance. The feature tracking technique is one of the most commonly used methods for deriving ice flow velocity from remote sensing data. Despite being cost-effective compared to field measurements, running a feature tracking workflow is not easy because 1) searching for good data can be time-consuming; 2) fetching data can be challenging because the source images often have a large size; and, 3) there is no standardized pipeline for feature tracking processes. 

Here we present an interactive, notebook-based interface that deploys the entire feature tracking workflow. This open-source tool aims to provide researchers, educators, and other users an easy way to perform glacier feature tracking. 

In our demo notebook, we query data over Jakobshavn Isbræ, a large outlet glacier of the Greenland Ice Sheet with a history of seasonal flow speed variation. Users can choose to explore the readily available ITS_LIVE velocity or perform feature tracking using the Landsat 8 imagery. In this mini-study, We derive the spring speed change of Jakobshavn Isbræ during 2015-2021 (a few weeks before the EC meeting) using both ITS_LIVE and CARST-derived data, and find that the slowdown event at Jakobshavn in 2017/2018 seems to not last long. In 2021, Jakobshavn's spring speed increases and likely reaches back to the peak between 2013 and 2016.

This demo notebook provide an easy and interactive way to deploy the entire feature tracking application. We expect to see it opens a way for researchers to explore new data, compare different algorithms, and visualize and validate their results. This tool also shows a full potential on education uses since it lowers the technical threshold for manipulating satellite data and deriving glacier speeds. The modules used by this demo notebook, including the GeoStacks and CARST packages, are open-source software and welcome community contributions.

## Meeting records

[Here](https://instaar.colorado.edu/meetings/AW2021/abstract_details.php?abstract_id=59) is the full project abstract presented at the 50th Arctic Workshop, April 16, 2021.