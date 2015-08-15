#!/usr/bin/env python3

""" handle gpx file """

import os
from xml.etree import ElementTree as ET
from datetime import datetime
from tile import TileSystem, GeoPoint
from PIL import Image
import xml.dom.minidom

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

    def __init__(self, tz=None):
        self.__tz = tz

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
                print("Warning: the root element's namespace is not 'gpx'")

        #load data
        self.loadMetadata(xml_root)
        self.loadWpt(xml_root)
        self.loadTrk(xml_root)

        #for wpt in self.__wpts:
            #print(wpt.time.strftime("%c"), wpt.name, wpt.lon, wpt.lat, wpt.ele)

        #for trk in self.__trks:
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
            if elem is not None and elem.text is not None:
                wpt.ele = float(elem.text)

            elem = wpt_elem.find("./gpx:time", self.ns)
            if elem is not None and elem.text is not None:
                wpt.time = datetime.strptime(elem.text, "%Y-%m-%dT%H:%M:%SZ")
            else:
                wpt.time = self.toUTC(datetime.now())

            elem = wpt_elem.find("./gpx:name", self.ns)
            if elem is not None and elem.text is not None:
                wpt.name = elem.text

            elem = wpt_elem.find("./gpx:cmt", self.ns)
            if elem is not None and elem.text is not None:
                wpt.cmt = elem.text

            elem = wpt_elem.find("./gpx:desc", self.ns)
            if elem is not None and elem.text is not None:
                wpt.desc = elem.text

            elem = wpt_elem.find("./gpx:sym", self.ns)
            if elem is not None and elem.text is not None:
                wpt.sym = elem.text

            self.addWpt(wpt)
            

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

            self.__trks.append(trk)

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

            self.addTrkPt(trk, pt)

    def addWpt(self, wpt):
        self.__wpts.append(wpt)
        self.__updateBounds(wpt) #maintain bounds (gpx file may not have metadata)

    def addTrkPt(self, trk, pt):
        trk.addTrackPoint(pt)
        self.__updateBounds(pt) #maintain bounds (gpx file may not have metadata)

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

        #tree = ET.ElementTree(element=gpx)
        #tree.write(path, encoding="UTF-8", xml_declaration=True)#, default_namespace=self.ns['gpx'])

        #write
        txt = ET.tostring(gpx, method='xml', encoding="UTF-8")
        txt = xml.dom.minidom.parseString(txt).toprettyxml(encoding="UTF-8") # prettify!!  #the encoding is for xml-declaration
        with open(path, 'wb') as gpx_file:
            gpx_file.write(txt)

    def genRootElement(self):
        gpx = ET.Element('gpx')
        gpx.set("xmlns", self.ns['gpx'])
        gpx.set("creator", "GisEditor");
        gpx.set("version", "1.1");
        gpx.set("xmlns:xsi", self.ns['xsi'])
        gpx.set('xsi:schemaLocation', "http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd")
        return gpx

    def toUTC(self, time):
        if self.__tz:
            return time - self.__tz
        return time

    def subMetadataElement(self, parent):
        metadata = ET.SubElement(parent, 'metadata')
        link = ET.SubElement(metadata, 'link')
        link.set("href", "http://www.garmin.com");
        text = ET.SubElement(link, "text");
        text.text = "Garmin International";

        time = ET.SubElement(metadata, 'time')
        time.text = self.toUTC(datetime.now()).strftime("%Y-%m-%dT%H:%M:%SZ");

        if self.maxlat and self.maxlon and self.minlat and self.minlon:
            bounds = ET.SubElement(metadata, 'bounds')
            bounds.set("maxlat", str(self.maxlat))
            bounds.set("maxlon", str(self.maxlon))
            bounds.set("minlat", str(self.minlat))
            bounds.set("minlon", str(self.minlon))

    def subWptElement(self, parent):
        for w in self.__wpts:
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

    def subTrkElement(self, parent):
        for t in self.__trks:
            trk = ET.SubElement(parent, 'trk')

            #name
            name = ET.SubElement(trk, 'name')
            name.text = t.name

            #color
            extensions = ET.SubElement(trk, "extensions");
            trk_ext = ET.SubElement(extensions, "gpxx:TrackExtension")
            trk_ext.set('xmlns:gpxx', self.ns['gpxx'])
            disp_color = ET.SubElement(trk_ext, "gpxx:DisplayColor")
            disp_color.text = t.color;

            #trk seg
            self.subTrkSegElement(trk, t)

    def subTrkSegElement(self, parent, t):
        trkseg = ET.SubElement(parent, 'trkseg')
        for pt in t:
            trkpt = ET.SubElement(trkseg, "trkpt");
            trkpt.set("lat", str(pt.lat))
            trkpt.set("lon", str(pt.lon))

            ele = ET.SubElement(trkpt, "ele");
            ele.text = str(pt.ele)

            time = ET.SubElement(trkpt, "time");
            time.text = pt.time.strftime("%Y-%m-%dT%H:%M:%SZ");

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
        self.__trkseg[idx] = value

    def __delitem__(self, idx):
        del self.__trkseg[idx]

    def __len__(self):
        return len(self.__trkseg)

    def addTrackPoint(self, pt):
        self.__trkseg.append(pt)

    def remove(self, pt):
        self.__trkseg.remove(pt)

class TrackPoint:
    @property
    def lat(self): return self.__geo.lat
    @property
    def lon(self): return self.__geo.lon

    def __init__(self, lat, lon):
        self.__geo = GeoPoint(lat=lat, lon=lon)
        self.ele = 0.0
        self.time = None

    def getPixel(self, level):
        self.__geo.level = level
        return (self.__geo.px, self.__geo.py)

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
