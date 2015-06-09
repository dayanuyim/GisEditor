#!/usr/bin/env python3
# -*- coding: utf8 -*-

""" handle gpx file """

from xml.etree import ElementTree
from datetime import datetime
from tile import TileSystem, GeoPoint

class GpsDocument:
    def getMaxLon(self): return self.maxlon
    def getMaxLat(self): return self.maxlat
    def getMinLon(self): return self.minlon
    def getMinLat(self): return self.minlat

    def getWayPoints(self):
        return self.wpts

    def getTracks(self):
        return self.trks

    def __init__(self, filename):
        self.wpts = []
        self.trks = []

        xml_root = ElementTree.parse(filename).getroot()

        #set ns
        self.ns = {}
        if xml_root.tag[0] == '{':
            ns, name = xml_root.tag[1:].split("}")
            self.ns["gpx"] = ns
            if name != "gpx":
                print("Warning: the root element's namespace is not 'gpx'")

        self.ns['xsi'] = "http://www.w3.org/2001/XMLSchema-instance"
        self.ns['gpxx'] = "http://www.garmin.com/xmlschemas/GpxExtensions/v3"

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
        self.maxlat = float(bounds.attrib['maxlat'])
        self.maxlon = float(bounds.attrib['maxlon'])
        self.minlat = float(bounds.attrib['minlat'])
        self.minlon = float(bounds.attrib['minlon'])

    def loadWpt(self, xml_root):
        wpt_elems = xml_root.findall("./gpx:wpt", self.ns)
        if wpt_elems is None:
            return

        for wpt_elem in wpt_elems:
            wpt = WayPoint()

            #attr
            wpt.lat = float(wpt_elem.attrib['lat'])
            wpt.lon = float(wpt_elem.attrib['lon'])

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

            elem = trk_elem.find("./gpx:trkseg", self.ns)
            if elem is not None: self.loadTrkSeg(elem, trk)

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

class WayPoint:
    def __init__(self):
        self.lon = None
        self.lat = None
        self.ele = None
        self.time = None
        self.name = None
        self.desc = None
        self.cmt = None
        self.sym = None

class Track:
    def __init__(self):
        self.__trkseg = []
        self.name = None
        self.color = None
        self.__maxlon = None
        self.__minlon = None
        self.__maxlat = None
        self.__minlat = None

    def __iter__(self):
        return iter(self.__trkseg)

    @property
    def maxlon(self): return self.__maxlon
    @property
    def minlon(self): return self.__minlon
    @property
    def maxlat(self): return self.__maxlat
    @property
    def minlat(self): return self.__minlat

    def addTrackPoint(self, pt):
        self.__trkseg.append(pt)
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
    gpx = GpsDocument("bak/2015_0101-04.gpx")
