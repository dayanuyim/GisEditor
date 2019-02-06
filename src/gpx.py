#!/usr/bin/env python3

""" handle gpx file """

import os
import logging
import pytz
from xml.etree import ElementTree as ET
from datetime import datetime
from PIL import Image
import xml.dom.minidom
from util import GeoPoint, saveXml
from coord import TileSystem

def hasText(elem):
    return elem is not None and elem.text

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
    def way_points(self): return self.__wpts

    @property
    def tracks(self): return self.__trks

    def __init__(self):

        self.__wpts = []
        self.__trks = []
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
                logging.warning("Warning: the root element's namespace is not 'gpx'")

        #load data
        self.__loadMetadata(xml_root)
        self.__loadWpt(xml_root)
        self.__loadTrk(xml_root)

        '''
        #debug outptu
        for wpt in self.__wpts:
            print(wpt.time.strftime("%c"), wpt.name, wpt.lon, wpt.lat, wpt.ele)

        for trk in self.__trks:
            print(trk.name, trk.color)
            for pt in trk:
                print("  ", pt.time.strftime("%c"), pt.lon, pt.lat, pt.ele)
        '''

    def __loadMetadata(self, xml_root):
        #bounds = xml_root.find("./gpx:metadata/gpx:bounds", self.ns)  #gpx1.1
        #bounds = xml_root.findall("./gpx:bounds", self.ns)  #gpx1.0 
        bounds = xml_root.find(".//gpx:bounds", self.ns)  #for gpx1.0/gpx1.1
        self.__maxlat = float(bounds.attrib['maxlat']) if bounds is not None else None
        self.__maxlon = float(bounds.attrib['maxlon']) if bounds is not None else None
        self.__minlat = float(bounds.attrib['minlat']) if bounds is not None else None
        self.__minlon = float(bounds.attrib['minlon']) if bounds is not None else None

    def __loadWpt(self, xml_root):
        wpt_elems = xml_root.findall("./gpx:wpt", self.ns)
        if wpt_elems is None:
            return

        for wpt_elem in wpt_elems:
            #read lat, lon, necessarily
            wpt = WayPoint(
                float(wpt_elem.attrib['lat']),
                float(wpt_elem.attrib['lon']))

            #read info from child elements, if any
            elem = wpt_elem.find("./gpx:ele", self.ns)
            wpt.ele = float(elem.text) if hasText(elem) else 0.0

            elem = wpt_elem.find("./gpx:time", self.ns)
            wpt.time = self.__toUTCTime(elem.text) if hasText(elem) else None

            elem = wpt_elem.find("./gpx:name", self.ns)
            wpt.name = elem.text if hasText(elem) else ""

            elem = wpt_elem.find("./gpx:sym", self.ns)
            wpt.sym = elem.text if hasText(elem) else ""

            elem = wpt_elem.find("./gpx:cmt", self.ns)
            wpt.cmt = elem.text if hasText(elem) else ""

            elem = wpt_elem.find("./gpx:desc", self.ns)
            wpt.desc = elem.text if hasText(elem) else ""

            self.addWpt(wpt)

    def __loadTrk(self, xml_root):
        trk_elems = xml_root.findall("./gpx:trk", self.ns)
        if trk_elems is None:
            return

        for trk_elem in trk_elems:
            elem = trk_elem.find("./gpx:name", self.ns)
            name = elem.text if hasText(elem) else "(No Title)"

            elem = trk_elem.find("./gpx:extensions/gpxx:TrackExtension/gpxx:DisplayColor", self.ns)
            color = elem.text if hasText(elem) else "DarkMagenta"

            trk_idx = self.genTrk(name, color)

            #may have multi trkseg
            elems = trk_elem.findall("./gpx:trkseg", self.ns)
            if elems is not None:
                for elem in elems:
                    self.__loadTrkSeg(elem, trk_idx)

    def __loadTrkSeg(self, trkseg_elem, trk_idx):
        trkpt_elems = trkseg_elem.findall("./gpx:trkpt", self.ns)
        if trkpt_elems is None:
            return

        for trkpt_elem in trkpt_elems:
            pt = TrackPoint(float(trkpt_elem.attrib["lat"]), float(trkpt_elem.attrib["lon"]))

            elem = trkpt_elem.find("./gpx:ele", self.ns)
            pt.ele = float(elem.text) if hasText(elem) else None

            elem = trkpt_elem.find("./gpx:time", self.ns)
            pt.time = self.__toUTCTime(elem.text) if hasText(elem) else None

            self.addTrkpt(trk_idx, pt)

    #should not allow users to create Track() by themself, because we want to force users to user addTrkpt()
    def genTrk(self, name, color):
        trk = Track()
        trk.name = name
        trk.color = color
        self.__trks.append(trk)
        return self.__trks.index(trk)

    def delTrk(self, idx):
        del self.__trks[idx]
        
    def addTrkpt(self, trk_idx, pt):
        self.__trks[trk_idx].add(pt)
        self.__updateBounds(pt) #maintain bounds (gpx file may not have metadata)

    def addWpt(self, wpt):
        self.__wpts.append(wpt)
        self.__updateBounds(wpt) #maintain bounds (gpx file may not have metadata)

    def __updateBounds(self, pt):
        if self.__maxlat is None or pt.lat >= self.__maxlat:
            self.__maxlat = pt.lat
        if self.__minlat is None or pt.lat <= self.__minlat:
            self.__minlat = pt.lat

        if self.__maxlon is None or pt.lon >= self.__maxlon:
            self.__maxlon = pt.lon
        if self.__minlon is None or pt.lon <= self.__minlon:
            self.__minlon = pt.lon

    def merge(self, rhs):
        self.__minlat = self.safe_min(self.minlat, rhs.minlat)
        self.__maxlat = self.safe_max(self.maxlat, rhs.maxlat)
        self.__minlon = self.safe_min(self.minlon, rhs.minlon)
        self.__maxlon = self.safe_max(self.maxlon, rhs.maxlon)

        self.__wpts.extend(rhs.__wpts)
        self.__trks.extend(rhs.__trks)

    @staticmethod
    def safe_min(v1, v2):
        if v1 is None: return v2
        if v2 is None: return v1
        return min(v1, v2)

    @staticmethod
    def safe_max(v1, v2):
        if v1 is None: return v2
        if v2 is None: return v1
        return max(v1, v2)

    def save(self, path):
        gpx = self.genRootElement()
        self.subMetadataElement(gpx)
        self.subWptElement(gpx)
        self.subTrkElement(gpx)

        saveXml(gpx, path)

    def genRootElement(self):
        gpx = ET.Element('gpx')
        gpx.set("xmlns", self.ns['gpx'])
        gpx.set("creator", "GisEditor")
        gpx.set("version", "1.1")
        gpx.set("xmlns:xsi", self.ns['xsi'])
        gpx.set('xsi:schemaLocation', "http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd")
        return gpx

    # if year is < 1900 or < 1000, strftime() may not pad zero for year, which cause strptime() exception.
    # [ref] https://docs.python.org/3.5/library/datetime.html#strftime-and-strptime-behavior
    def __toUTCFormat(self, time):
        txt = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        #padding zero if year's length < 4
        return "0" * ( 4 - txt.index('-')) + txt

    def __toUTCTime(self, txt):
        fmt = "%Y-%m-%dT%H:%M:%S.%fZ" if "." in txt else "%Y-%m-%dT%H:%M:%SZ"
        return datetime.strptime(txt, fmt).replace(tzinfo=pytz.utc)

    def subMetadataElement(self, parent):
        metadata = ET.SubElement(parent, 'metadata')
        link = ET.SubElement(metadata, 'link')
        link.set("href", "http://www.garmin.com")
        text = ET.SubElement(link, "text")
        text.text = "Garmin International"

        time = ET.SubElement(metadata, 'time')
        time.text = self.__toUTCFormat(datetime.utcnow())

        if self.maxlat and self.maxlon and self.minlat and self.minlon:
            bounds = ET.SubElement(metadata, 'bounds')
            bounds.set("maxlat", str(self.maxlat))
            bounds.set("maxlon", str(self.maxlon))
            bounds.set("minlat", str(self.minlat))
            bounds.set("minlon", str(self.minlon))

    def subWptElement(self, parent):
        #
        # Notice: The order of elements matters.
        # ref: http://www.topografix.com/GPX/1/1/#type_wptType
        #
        for w in self.__wpts:
            wpt = ET.SubElement(parent, 'wpt')
            wpt.set("lat", str(w.lat))
            wpt.set("lon", str(w.lon))

            ele = ET.SubElement(wpt, "ele")
            ele.text = str(w.ele)

            if w.time:
                time = ET.SubElement(wpt, "time")
                time.text = self.__toUTCFormat(w.time)

            name = ET.SubElement(wpt, "name")
            name.text = w.name

            if w.cmt:
                cmt = ET.SubElement(wpt, "cmt")
                cmt.text = w.cmt

            if w.desc:
                desc = ET.SubElement(wpt, "desc")
                desc.text = w.desc

            sym = ET.SubElement(wpt, "sym")
            sym.text = w.sym

            #extension =====
            extensions = ET.SubElement(wpt, "extensions")
            wpt_ext = ET.SubElement(extensions, "gpxx:WaypointExtension")
            wpt_ext.set('xmlns:gpxx', self.ns['gpxx'])
            disp_mode = ET.SubElement(wpt_ext, "gpxx:DisplayMode")
            disp_mode.text = "SymbolAndName"

    def subTrkElement(self, parent):
        for t in self.__trks:
            trk = ET.SubElement(parent, 'trk')

            #name
            name = ET.SubElement(trk, 'name')
            name.text = t.name

            #color
            extensions = ET.SubElement(trk, "extensions")
            trk_ext = ET.SubElement(extensions, "gpxx:TrackExtension")
            trk_ext.set('xmlns:gpxx', self.ns['gpxx'])
            disp_color = ET.SubElement(trk_ext, "gpxx:DisplayColor")
            disp_color.text = t.color

            #trk seg
            self.subTrkSegElement(trk, t)

    def subTrkSegElement(self, parent, t):
        trkseg = ET.SubElement(parent, 'trkseg')
        for pt in t:
            trkpt = ET.SubElement(trkseg, "trkpt")
            trkpt.set("lat", str(pt.lat))
            trkpt.set("lon", str(pt.lon))

            if pt.ele:
                ele = ET.SubElement(trkpt, "ele")
                ele.text = str(pt.ele)

            if pt.time:
                time = ET.SubElement(trkpt, "time")
                time.text = self.__toUTCFormat(pt.time)

    def sortWpt(self, name=None, time=None):
        if name is not None:
            self.__wpts = sorted(self.__wpts, key=lambda wpt: wpt.name)
        elif time is not None:
            self.__wpts = sorted(self.__wpts, key=lambda wpt: wpt.time)

    def sortTrk(self, name=None, time=None):
        if name is not None:
            self.__trks = sorted(self.__trks, key=lambda trk: trk.name)
        elif time is not None:
            self.__trks = sorted(self.__trks, key=lambda trk: trk.time)

    def splitTrk(self, split_fn):
        sp_trks = []
        for trk in self.__trks:
            sp_trks.extend(trk.split(split_fn))

        #replace
        has_split = len(self.__trks) != len(sp_trks)
        self.__trks = sp_trks
        return has_split

class Track:
    @property
    def time(self):
        return self.__trkseg[0].time if len(self.__trkseg) > 0 else datetime.min

    def __init__(self):
        self.__trkseg = []
        self.name = ''
        self.color = 'DarkMagenta'

    def __iter__(self):
        return iter(self.__trkseg)

    def __getitem__(self, idx):
        return self.__trkseg[idx]

    def __setitem__(self, idx, val):
        self.__trkseg[idx] = val

    def __delitem__(self, idx):
        del self.__trkseg[idx]

    def __len__(self):
        return len(self.__trkseg)

    def add(self, pt):
        self.__trkseg.append(pt)

    def remove(self, pt):
        self.__trkseg.remove(pt)

    def split(self, split_fn):
        sp_trks = []

        last_pt = None
        for pt in self.__trkseg:
            #create new trk
            if last_pt is None or split_fn(last_pt, pt):
                trk=Track()
                trk.name = "%s-%d" % (self.name, len(sp_trks)+1)
                trk.color = self.color
                sp_trks.append(trk)
            #append trkpt
            sp_trks[-1].add(pt)
            #iterate
            last_pt = pt

        return sp_trks

class TrackPoint(GeoPoint):
    #property lat
    #property lon
    def __init__(self, lat, lon):
        super().__init__(lat=lat, lon=lon)
        self.ele = 0.0
        self.time = None

class WayPoint(TrackPoint):
    def __init__(self, lat, lon):
        super().__init__(lat, lon)
        self.name = ""
        self.desc = ""
        self.cmt = ""
        self.sym = ""

if __name__ == '__main__':
    #gpx = GpsDocument("bak/2015_0101-04.gpx")
    gpx = GpsDocument()
    gpx.load('bak/test.gpx')
    gpx.sortTrk(time=True)
    gpx.sortWpt(time=True)
    gpx.save('out.gpx')

