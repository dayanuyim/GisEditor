#!/usr/bin/env python3
# -*- coding: utf8 -*-

""" handle gpx file """

import os
from xml.etree import ElementTree as ET
from datetime import datetime
from tile import TileSystem, GeoPoint
from PIL import Image

class GpsDocument:
    @property
    def maxlon(self): return self.__maxlon
    @property
    def minlon(self): return self.__minlon
    @property
    def maxlat(self): return self.__maxlat
    @property
    def minlat(self): return self.__minlat

    @property
    def way_points(self): return self.wpts

    @property
    def tracks(self): return self.trks

    def __init__(self, tz=None):
        self.__tz = tz

        self.wpts = []
        self.trks = []
        self.__maxlon = None
        self.__minlon = None
        self.__maxlat = None
        self.__minlat = None

        #set ns
        self.ns = {}
        self.ns['gpx'] = "http://www.topografix.com/GPX/1/1"
        self.ns['xsi'] = "http://www.w3.org/2001/XMLSchema-instance"
        self.ns['gpxx'] = "http://www.garmin.com/xmlschemas/GpxExtensions/v3"

    def load(self, filename=None, filestring=None):
        #get root element
        xml_root = None
        if filename is not None:
            xml_root = ET.parse(filename).getroot()
        elif filestring is not None:
            xml_root = ET.fromstring(filestring)
        else:
            raise ValueError("Gpx filename and filestring both None")

        #override 'gpx ns
        if xml_root.tag[0] == '{':
            ns, name = xml_root.tag[1:].split("}")
            self.ns["gpx"] = ns 
            if name != "gpx":
                print("Warning: the root element's namespace is not 'gpx'")

        #load data
        self.loadMetadata(xml_root)
        self.loadWpt(xml_root)
        self.loadTrk(xml_root)

        #for wpt in self.wpts:
            #print(wpt.time.strftime("%c"), wpt.name, wpt.lon, wpt.lat, wpt.ele)

        #for trk in self.trks:
            #print(trk.name, trk.color)
            #for pt in trk:
                #print("  ", pt.time.strftime("%c"), pt.lon, pt.lat, pt.ele)

    def loadMetadata(self, xml_root):
        #bounds = xml_root.find("./gpx:metadata/gpx:bounds", self.ns)  #gpx1.1
        #bounds = xml_root.findall("./gpx:bounds", self.ns)  #gpx1.0 
        bounds = xml_root.find(".//gpx:bounds", self.ns)  #for gpx1.0/gpx1.1
        self.__maxlat = float(bounds.attrib['maxlat']) if bounds is not None else None
        self.__maxlon = float(bounds.attrib['maxlon']) if bounds is not None else None
        self.__minlat = float(bounds.attrib['minlat']) if bounds is not None else None
        self.__minlon = float(bounds.attrib['minlon']) if bounds is not None else None

    def loadWpt(self, xml_root):
        wpt_elems = xml_root.findall("./gpx:wpt", self.ns)
        if wpt_elems is None:
            return

        for wpt_elem in wpt_elems:
            wpt = WayPoint(
                float(wpt_elem.attrib['lat']),
                float(wpt_elem.attrib['lon']))

            #child element
            elem = wpt_elem.find("./gpx:ele", self.ns)
            if elem is not None: wpt.ele = float(elem.text)

            elem = wpt_elem.find("./gpx:time", self.ns)
            if elem is not None: wpt.time = datetime.strptime(elem.text, "%Y-%m-%dT%H:%M:%SZ")

            elem = wpt_elem.find("./gpx:name", self.ns)
            if elem is not None: wpt.name = elem.text

            elem = wpt_elem.find("./gpx:cmt", self.ns)
            if elem is not None: wpt.cmt = elem.text

            elem = wpt_elem.find("./gpx:desc", self.ns)
            if elem is not None: wpt.desc = elem.text

            elem = wpt_elem.find("./gpx:sym", self.ns)
            if elem is not None: wpt.sym = elem.text

            self.wpts.append(wpt)

            #update bounds (metadata may not have)
            self.__updateBounds(wpt)

    def loadTrk(self, xml_root):
        trk_elems = xml_root.findall("./gpx:trk", self.ns)
        if trk_elems is None:
            return

        for trk_elem in trk_elems:
            trk = Track()

            elem = trk_elem.find("./gpx:name", self.ns)
            trk.name = elem.text if elem is not None else "(No Title)"

            elem = trk_elem.find("./gpx:extensions/gpxx:TrackExtension/gpxx:DisplayColor", self.ns)
            trk.color = elem.text if elem is not None else "DarkMagenta"

            #may have multi trkseg
            elems = trk_elem.findall("./gpx:trkseg", self.ns)
            if elems is not None:
                for elem in elems:
                    self.loadTrkSeg(elem, trk)

            self.trks.append(trk)

    def loadTrkSeg(self, trkseg_elem, trk):
        trkpt_elems = trkseg_elem.findall("./gpx:trkpt", self.ns)
        if trkpt_elems is None:
            return

        for trkpt_elem in trkpt_elems:
            pt = TrackPoint(float(trkpt_elem.attrib["lat"]), float(trkpt_elem.attrib["lon"]))

            elem = trkpt_elem.find("./gpx:ele", self.ns)
            pt.ele = None if elem is None else float(elem.text)

            elem = trkpt_elem.find("./gpx:time", self.ns)
            pt.time = None if elem is None else datetime.strptime(elem.text, "%Y-%m-%dT%H:%M:%SZ")

            trk.addTrackPoint(pt)

            #update bounds (metadata may not have)
            self.__updateBounds(pt)

    def __updateBounds(self, pt):
        if self.__maxlat is None or pt.lat >= self.__maxlat:
            self.__maxlat = pt.lat
        if self.__minlat is None or pt.lat <= self.__minlat:
            self.__minlat = pt.lat

        if self.__maxlon is None or pt.lon >= self.__maxlon:
            self.__maxlon = pt.lon
        if self.__minlon is None or pt.lon <= self.__minlon:
            self.__minlon = pt.lon

    def save(self, path):
        gpx = self.genRootElement()
        self.subMetadataElement(gpx)
        self.subWptElement(gpx)

        #write
        doc = ET.ElementTree(element=gpx)
        doc.write(path, encoding="UTF-8", xml_declaration=True)#, default_namespace=self.ns['gpx'])

    def genRootElement(self):
        gpx = ET.Element('gpx')
        gpx.set("xmlns", self.ns['gpx'])
        gpx.set("creator", "TT GpsToolset");
        gpx.set("version", "1.1");
        gpx.set("xmlns:xsi", self.ns['xsi'])
        gpx.set('xsi:schemaLocation', "http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd")
        return gpx

    def subMetadataElement(self, parent):
        metadata = ET.SubElement(parent, 'metadata')
        link = ET.SubElement(metadata, 'link')
        link.set("href", "http://www.garmin.com");
        text = ET.SubElement(link, "text");
        text.text = "Garmin International";

        time = ET.SubElement(metadata, 'time')
        if self.__tz is not None:
            utc = datetime.now() - self.__tz
        else:
            utc = datetime.now()
        time.text = utc.strftime("%Y-%m-%dT%H:%M:%SZ");

        bounds = ET.SubElement(metadata, 'bounds')
        bounds.set("maxlat", str(self.maxlat))
        bounds.set("maxlon", str(self.maxlon))
        bounds.set("minlat", str(self.minlat))
        bounds.set("minlon", str(self.minlon))

    def subWptElement(self, parent):
        for w in self.wpts:
            wpt = ET.SubElement(parent, 'wpt')
            wpt.set("lat", str(w.lat))
            wpt.set("lon", str(w.lon))

            ele = ET.SubElement(wpt, "ele");
            ele.text = str(w.ele);

            time = ET.SubElement(wpt, "time");
            time.text = w.time.strftime("%Y-%m-%dT%H:%M:%SZ");

            name = ET.SubElement(wpt, "name");
            name.text = w.name;

            if len(w.cmt) > 0:
                cmt = ET.SubElement(wpt, "cmt");
                cmt.text = w.cmt;

            if len(w.desc) > 0:
                desc = ET.SubElement(wpt, "desc");
                desc.text = w.desc;

            sym = ET.SubElement(wpt, "sym");
            sym.text = w.sym;

            #extension =====
            extensions = ET.SubElement(wpt, "extensions");
            wpt_ext = ET.SubElement(extensions, "gpxx:WaypointExtension")
            wpt_ext.set('xmlns:gpxx', self.ns['gpxx'])
            disp_mode = ET.SubElement(wpt_ext, "gpxx:DisplayMode")
            disp_mode.text = "SymbolAndName";


class WayPoint:
    @property
    def lat(self): return self.__geo.lat
    @property
    def lon(self): return self.__geo.lon

    def __init__(self, lat, lon):
        self.__geo = GeoPoint(lat=lat, lon=lon)
        self.ele = 0.0
        self.time = None
        self.name = ""
        self.desc = ""
        self.cmt = ""
        self.sym = ""

    def getPixel(self, level):
        self.__geo.level = level
        return (self.__geo.px, self.__geo.py)

class Track:
    def __init__(self):
        self.__trkseg = []
        self.name = None
        self.color = None

    def __iter__(self):
        return iter(self.__trkseg)

    def __len__(self):
        return len(self.__trkseg)

    def addTrackPoint(self, pt):
        self.__trkseg.append(pt)

class TrackPoint:
    @property
    def lat(self): return self.__geo.lat
    @property
    def lon(self): return self.__geo.lon

    def __init__(self, lat, lon):
        self.__geo = GeoPoint(lat=lat, lon=lon)
        self.ele = None
        self.time = None

    def getPixel(self, level):
        self.__geo.level = level
        return (self.__geo.px, self.__geo.py)

if __name__ == '__main__':
    #gpx = GpsDocument("bak/2015_0101-04.gpx")
    gpx = GpsDocument()
    gpx.load('bak/test.gpx')
    gpx.save('out.gpx')

