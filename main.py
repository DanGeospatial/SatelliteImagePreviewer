# Set imports
import sys
import time

import odc.geo.xr
import odc.stac
import planetary_computer
import pystac_client
import rasterio
from PySide6.QtCore import QSize, QDateTime
from PySide6.QtWidgets import QApplication, QPushButton, QMainWindow, QDateEdit, QComboBox, QLabel, \
    QVBoxLayout, QLineEdit, QWidget, QFileDialog, QStatusBar
from pystac.extensions.eo import EOExtension as eo
from rasterio.plot import show

# Set global variables
today = QDateTime.currentDateTime()
start = QDateTime(today.addDays(-40))
end = QDateTime(today.addDays(-30))
sat = "Landsat"
cloud = 10
bb = [-122.2751, 47.5469, -121.9613, 47.7458]
selectedImage = None


def getMODIS(area_of_interest, time_of_interest):
    # Handle selecting MODIS catalog
    search = catalog.search(collections=["modis-09A1-061"],
                            bbox=area_of_interest,
                            datetime=time_of_interest)
    items = search.item_collection()
    least_cloudy_item = items[0]
    print(least_cloudy_item)
    asset_href = least_cloudy_item.assets["rendered_preview"].href

    global selectedImage
    selectedImage = least_cloudy_item

    return asset_href


def getLandsat(area_of_interest, time_of_interest):
    # Handle selecting Landsat catalog
    search = catalog.search(collections=["landsat-c2-l2"],
                            bbox=area_of_interest,
                            datetime=time_of_interest,
                            # sort by cloud cover percent
                            query={"eo:cloud_cover": {"lt": cloud}}, )
    items = search.item_collection()
    least_cloudy_item = min(items, key=lambda item: eo.ext(item).cloud_cover)
    print(least_cloudy_item)
    asset_href = least_cloudy_item.assets["rendered_preview"].href

    global selectedImage
    selectedImage = least_cloudy_item

    return asset_href


def getSentinel2(area_of_interest, time_of_interest):
    # Handle selecting Sentinel 2 catalog
    search = catalog.search(collections=["sentinel-2-l2a"],
                            bbox=area_of_interest,
                            datetime=time_of_interest,
                            # sort by cloud cover percent
                            query={"eo:cloud_cover": {"lt": cloud}}, )
    items = search.item_collection()
    least_cloudy_item = min(items, key=lambda item: eo.ext(item).cloud_cover)
    asset_href = least_cloudy_item.assets["rendered_preview"].href
    print(least_cloudy_item)

    global selectedImage
    selectedImage = least_cloudy_item

    return asset_href


def previewRGB(asset_href):
    with rasterio.open(asset_href) as ds:
        show(ds)


def prepPreview():
    timed = start.toString("yyyy-MM-dd") + "/" + end.toString("yyyy-MM-dd")

    if sat == "Landsat":
        previewRGB(getLandsat(bb, timed))
    elif sat == "Sentinel 2":
        previewRGB(getSentinel2(bb, timed))
    else:
        previewRGB(getMODIS(bb, timed))


def text_changed(i):
    global sat
    sat = i


def start_changed(i):
    global start
    start = i


def end_changed(i):
    global end
    end = i


def bb_changed(i):
    global bb
    bb = i


def cloud_changed(i):
    global cloud
    cloud = i


def downloadLandsat(item, saveloc):
    imagels = odc.stac.stac_load([item]).isel(time=0)
    imagearray = imagels.to_array()
    print(imagels)
    odc.geo.xr.write_cog(geo_im=imagearray, fname=saveloc)


def downloadSentinel2(item, saveloc):
    allbands = ["AOT", "B01", "B02", "B03", "B04", "B05",
                "B06", "B07", "B08", "B09", "B11", "B12", "B8A", "SCL", "WVP"]
    imagels = odc.stac.stac_load([item], bands=allbands).isel(time=0)
    imagearray = imagels.to_array()
    print(imagels)
    odc.geo.xr.write_cog(geo_im=imagearray, fname=saveloc)


def downloadMODIS(item, saveloc):
    allbands = ["sur_refl_b01", "sur_refl_b02", "sur_refl_b03", "sur_refl_b04", "sur_refl_b05", "sur_refl_b06",
                "sur_refl_b07", "sur_refl_raz", "sur_refl_szen", "sur_refl_vzen"]
    imagels = odc.stac.stac_load([item], bands=allbands, crs="EPSG:3857").isel(time=0)
    imagearray = imagels.to_array()
    print(imagels)
    odc.geo.xr.write_cog(geo_im=imagearray, fname=saveloc)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Satellite Image Previewer")
        self.setStyleSheet("background-color: #D3D3D3;")
        self.setFixedSize(QSize(250, 350))

        self.startdatemsg = QLabel("<h3>Start Date</h3>")
        self.enddatemsg = QLabel("<h3>End Date</h3>")

        self.startdate = QDateEdit()
        self.startdate.dateChanged.connect(start_changed)
        self.enddate = QDateEdit()
        self.enddate.dateChanged.connect(end_changed)

        self.collectionmsg = QLabel("<h3>Satellite Catalog</h3>")
        self.satselector = QComboBox()
        self.satselector.addItems(["Landsat", "Sentinel 2", "MODIS"])
        self.satselector.currentTextChanged.connect(text_changed)

        self.cloudmsg = QLabel("<h3>Cloud Cover</h3>")
        self.clouds = QLineEdit("Enter Cloud Cover Percentage")
        self.clouds.textChanged.connect(cloud_changed)

        self.pointmsg = QLabel("<h3>Image Coordinates</h3>")
        self.bby = QLineEdit("Enter Bounding Box")
        self.bby.textChanged.connect(bb_changed)

        self.button = QPushButton("Preview Image")
        self.button.setStyleSheet("border:2px solid #000000;")

        self.buttondl = QPushButton("Download Image")
        self.buttondl.setStyleSheet("border:2px solid #000000;")

        # self.imagestatus = QStatusBar()
        # self.imagestatus.showMessage("Ready")
        # self.setStatusBar(self.imagestatus)

        # Set the central widget of the Window.
        vlayout = QVBoxLayout()
        vlayout.addWidget(self.startdatemsg)
        vlayout.addWidget(self.startdate)
        vlayout.addWidget(self.enddatemsg)
        vlayout.addWidget(self.enddate)
        vlayout.addWidget(self.collectionmsg)
        vlayout.addWidget(self.satselector)
        vlayout.addWidget(self.cloudmsg)
        vlayout.addWidget(self.clouds)
        vlayout.addWidget(self.pointmsg)
        vlayout.addWidget(self.bby)
        vlayout.addWidget(self.button)
        vlayout.addWidget(self.buttondl)

        widgetbox = QWidget()
        widgetbox.setLayout(vlayout)
        self.setCentralWidget(widgetbox)

        def downloadImage():
            dirname = QFileDialog.getSaveFileName(self, "Save File", filter=".tif")
            dirfile = ''.join(dirname)
            time.sleep(10)

            global selectedImage
            if sat == "Landsat":
                downloadLandsat(selectedImage, dirfile)
                print(dirname)
            elif sat == "Sentinel 2":
                downloadSentinel2(selectedImage, dirfile)
            else:
                downloadMODIS(selectedImage, dirfile)

        self.button.clicked.connect(prepPreview)
        self.buttondl.clicked.connect(downloadImage)


if __name__ == '__main__':
    # Not using planetary_computer hub so must set api key
    # Try to do this by asking the user for input
    planetary_computer.settings.set_subscription_key('INSERT YOUR KEY HERE')
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec())
