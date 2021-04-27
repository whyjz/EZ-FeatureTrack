# EZ-FeatureTrack
An interactive, highly customizable, and easy-to-use workflow for glacier velocity mapping using feature tracking technique and satellite images. 

Try the demo notebook!

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/whyjz/EZ-FeatureTrack/HEAD?urlpath=lab/tree/notebooks/arcticworkshop_demo.ipynb)

In this demo, users can choose to explore the ITS_LIVE velocity dataset or the Landsat 8 imagery and perform feature tracking for the latter. The feature tracking kernel and all related filters, masks, and interpolation processes are from CARST, but users can easily replace any of them or the entire package with their algorithms or a different feature tracking package. The modules used by this demo notebook, including the GeoStacks and CARST packages, are open-source software and welcome community contributions. The demo notebook represents a way to integrate the entire feature tracking application. Users can also access the same modular content from the tools we use and adopt them in their own projects. Future integration of this work into a numerical glacier model or a web-based feature tracking service is also possible.

[Here](https://instaar.colorado.edu/meetings/AW2021/abstract_details.php?abstract_id=59) is the full project abstract presented at the 50th Arctic Workshop, April 16, 2021.