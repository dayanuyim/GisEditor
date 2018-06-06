#![feature(proc_macro, specialization)]
#![feature(const_fn, const_align_of, const_size_of, const_ptr_null, const_ptr_null_mut)]

use std::fs;
use std::path::Path;

extern crate quick_xml;
use quick_xml::Writer;
use quick_xml::Reader;
use quick_xml::events::{Event, BytesEnd, BytesStart, BytesText};
use std::io::Cursor;
use std::iter;

extern crate pyo3;

use std::fs::File;
use std::io::prelude::*;

use pyo3::prelude::*;

use pyo3::py::methods as pymethods;
use pyo3::py::class as pyclass;
use pyo3::py::modinit as pymodinit;


#[pyclass]
struct DiskCache{
    token: PyToken,
}

#[pymethods]
impl DiskCache{
    #[new]
    fn __new__(obj: &PyRawObject) -> PyResult<()> {
        obj.init(|t| DiskCache {token: t})
    }

    fn start(&self) -> PyResult<()> {
        Ok(())
    }

    fn close(&self) -> PyResult<()> {
        Ok(())
    }

    fn put (&self, level: String, x: i32, y: i32, data: String) -> PyResult<()> {
        Ok(())
    }

    fn get(&self, level: String, x: i32, y: i32) -> PyResult<()> {
        Ok(())
    }
}

#[pyclass]
struct MapDescriptor{
    token: PyToken,
    enabled: bool,
    alpha: u8,     
    map_title: String,
    level_min: u32,
    level_max: u32,
    tile_format: String,
    url_template: String,
    server_parts: Vec<String>,
    invert_y: bool,
    coord_sys: String,
    lower_corner: (f32, f32),
    upper_corner: (f32, f32),
    expire_sec: u64
}

#[pymethods]
impl MapDescriptor{
    #[new]
    fn __new__(obj: &PyRawObject) -> PyResult<()> 
    {
        obj.init(|t| MapDescriptor{
            token: t, 
            enabled: false, 
            alpha: 255, 
            map_title: String::new(),
            level_min: 0,
            level_max: 0,
            tile_format: String::new(),
            url_template: String::new(),
            server_parts: Vec::new(),
            invert_y: true,
            coord_sys: String::new(),
            lower_corner: (-180.0, -85.0),
            upper_corner: (180.0, 85.0),
            expire_sec: 0
        })
    }

    #[getter]
    fn get_alpha(&self) -> PyResult<f32> {
        Ok(self.alpha as f32 / 255.0)
    }

    #[setter]
    fn set_alpha(&mut self, value: f32) -> PyResult<()> {
        self.alpha = (value * 255.0) as u8;
        Ok(())
    }

    fn save(&self, output_folder: String, file_name: String) -> PyResult<()>
    {
        Ok(_map_descriptor_save(
                output_folder.as_str(),
                file_name.as_str(),
                self.map_title.as_str(),
                &self.level_min,
                &self.level_max,
                self.tile_format.as_str(),
                self.url_template.as_str(),
                &self.server_parts.join(" "),
                &self.invert_y,
                &self.coord_sys,
                &self.lower_corner.0,
                &self.lower_corner.1,
                &self.upper_corner.0,
                &self.upper_corner.1,
                &self.expire_sec
                ))
    }
}

fn _map_descriptor_save(output_folder: &str, file_name: &str, map_title: &str, min_zoom: &u32, max_zoom: &u32, 
                        tile_type: &str, url: &str, server_parts: &str, invert_y: &bool, coordinatesystem: &str, 
                        lower_corner_x: &f32, lower_corner_y: &f32, upper_corner_x: &f32, upper_corner_y: &f32, expire_sec: &u64)
{
    let xml = r#"
<customMapSource>
    <name></name>
    <minZoom></minZoom>
    <maxZoom></maxZoom>
    <tileType></tileType>
    <tileUpdate></tileUpdate>
    <url></url>
	<serverParts></serverParts>
    <invertYCoordinate></invertYCoordinate>
    <coordinatesystem></coordinatesystem>
    <lowerCorner></lowerCorner>
    <expireDays></expireDays>
    <backgroundColor></backgroundColor>
</customMapSource>
        "#;
    let mut reader = Reader::from_str(xml);
    reader.trim_text(true);
    let mut writer = Writer::new(Cursor::new(Vec::new()));
    let mut buf = Vec::new();
    let mut field = String::new();
    loop {
        match reader.read_event(&mut buf) {
            // XXX 
            Ok(Event::Start(ref e)) if e.name()  == b"name" => { 
                field = std::str::from_utf8(e.name()).unwrap().to_string();
                writer.write_event(Event::Start(BytesStart::owned(b"name".to_vec(), "name".len())));
            },
            Ok(Event::Start(ref e)) if e.name()  == b"minZoom" => { 
                field = std::str::from_utf8(e.name()).unwrap().to_string();
                writer.write_event(Event::Start(BytesStart::owned(b"minZoom".to_vec(), "minZoom".len())));
            },
            Ok(Event::Start(ref e)) if e.name()  == b"maxZoom" => { 
                field = std::str::from_utf8(e.name()).unwrap().to_string();
                writer.write_event(Event::Start(BytesStart::owned(b"maxZoom".to_vec(), "maxZoom".len())));
            },
            Ok(Event::Start(ref e)) if e.name()  == b"tileType" => { 
                field = std::str::from_utf8(e.name()).unwrap().to_string();
                writer.write_event(Event::Start(BytesStart::owned(b"tileType".to_vec(), "tileType".len())));
            },
            Ok(Event::Start(ref e)) if e.name()  == b"url" => { 
                field = std::str::from_utf8(e.name()).unwrap().to_string();
                writer.write_event(Event::Start(BytesStart::owned(b"url".to_vec(), "url".len())));
            },
            Ok(Event::Start(ref e)) if e.name()  == b"serverParts" => { 
                field = std::str::from_utf8(e.name()).unwrap().to_string();
                writer.write_event(Event::Start(BytesStart::owned(b"serverParts".to_vec(), "serverParts".len())));
            },
            Ok(Event::Start(ref e)) if e.name()  == b"invertYCoordinate" => { 
                field = std::str::from_utf8(e.name()).unwrap().to_string();
                writer.write_event(Event::Start(BytesStart::owned(b"invertYCoordinate".to_vec(), "invertYCoordinate".len())));
            },
            Ok(Event::Start(ref e)) if e.name()  == b"coordinatesystem" => { 
                field = std::str::from_utf8(e.name()).unwrap().to_string();
                writer.write_event(Event::Start(BytesStart::owned(b"coordinatesystem".to_vec(), "coordinatesystem".len())));
            },
            Ok(Event::Start(ref e)) if e.name()  == b"lowerCorner" => { 
                field = std::str::from_utf8(e.name()).unwrap().to_string();
                writer.write_event(Event::Start(BytesStart::owned(b"lowerCorner".to_vec(), "lowerCorner".len())));
            },
            Ok(Event::Start(ref e)) if e.name()  == b"upperCorner" => { 
                field = std::str::from_utf8(e.name()).unwrap().to_string();
                writer.write_event(Event::Start(BytesStart::owned(b"upperCorner".to_vec(), "upperCorner".len())));
            },
            Ok(Event::Start(ref e)) if e.name()  == b"expireDays" => { 
                field = std::str::from_utf8(e.name()).unwrap().to_string();
                writer.write_event(Event::Start(BytesStart::owned(b"expireDays".to_vec(), "expireDays".len())));
            },
            Ok(Event::Text(_)) => {
                match &field as &str  {
                    "name" => {
                        writer.write_event(Event::Text(BytesText::from_plain_str(&map_title)));
                    },
                    "minZoom" => {
                        writer.write_event(Event::Text(BytesText::from_plain_str(min_zoom.to_string().as_str())));
                    },
                    "maxZoom" => {
                        writer.write_event(Event::Text(BytesText::from_plain_str(max_zoom.to_string().as_str())));
                    },
                    "tileType" => {
                        writer.write_event(Event::Text(BytesText::from_plain_str(&tile_type)));
                    },
                    "url" => {
                        writer.write_event(Event::Text(BytesText::from_plain_str(&url)));
                    },
                    "serverParts" => {
                        writer.write_event(Event::Text(BytesText::from_plain_str(&server_parts)));
                    },
                    "invertYCoordinate" => {
                        if *invert_y {
                            writer.write_event(Event::Text(BytesText::from_plain_str("true")));
                        } else {
                            writer.write_event(Event::Text(BytesText::from_plain_str("false")));
                        }
                    },
                    "coordinatesystem" => {
                        writer.write_event(Event::Text(BytesText::from_plain_str(&coordinatesystem)));
                    },
                    "lowerCorner" => {
                        writer.write_event(Event::Text(BytesText::from_plain_str(&format!("{} {}", &lower_corner_x, &lower_corner_y))));
                    },
                    "upperCorner" => {
                        writer.write_event(Event::Text(BytesText::from_plain_str(&format!("{} {}", &upper_corner_x, &upper_corner_y))));
                    },
                    "expireDays" => {
                        let day = expire_sec / 86400;
                        writer.write_event(Event::Text(BytesText::from_plain_str(day.to_string().as_str())));
                    },
                    _ => {}
                }
                field = String::new();
            },
            Ok(Event::Eof) => break,
            // you can use either `e` or `&e` if you don't want to move the event
            Ok(e) => assert!(writer.write_event(&e).is_ok()),
            Err(e) => panic!("Error at position {}: {:?}", reader.buffer_position(), e),
        }
        buf.clear();
    }

    let result = writer.into_inner().into_inner();
    fs::write(Path::new(output_folder).join(file_name).with_extension("xml"), result);
}




//     def clone(self):
//         desc = MapDescriptor()
//         desc.map_id = self.map_id
//         desc.map_title = self.map_title
//         desc.level_min = self.level_min
//         desc.level_max = self.level_max
//         desc.tile_format = self.tile_format
//         desc.url_template = self.url_template
//         desc.server_parts = self.server_parts
//         desc.invert_y = self.invert_y
//         desc.coord_sys = self.coord_sys
//         desc.lower_corner = self.lower_corner
//         desc.upper_corner = self.upper_corner
//         desc.expire_sec = self.expire_sec
//         desc.alpha = self.alpha
//         desc.enabled = self.enabled
//         return desc

//     # satic method #######################################
//     @classmethod
//     def __getElemText(cls, root, tag_path, def_value=None, errmsg=None):
//         elem = root.find(tag_path)
//         if elem is not None:
//             return elem.text
//         else:
//             if errmsg:
//                 logging.warning(errmsg)
//             return def_value

//     @classmethod
//     def __cropValue(cls, val, low, up, errmsg=None):
//         _val = min(max(low, val), up)
//         if _val != val and errmsg:
//             logging.warning(errmsg)
//         return _val

//     @classmethod
//     def __parseLatlon(cls, latlon_str, def_latlon):
//         tokens = latlon_str.split(' ')
//         if len(tokens) != 2:
//             logging.info("not valid lat lon string: '%s'" % (latlon_str,))
//             return def_latlon

//         try:
//             lat = float(tokens[0])
//             lon = float(tokens[1])
//             lat = cls.__cropValue(lat, -180, 180, "not valid lat value: %f" % (lat,))
//             lon = cls.__cropValue(lon, -85, 85, "not valid lon value: %f" % (lon,))
//             return (lat, lon)
//         except Exception as ex:
//             logging.error("parsing latlon string '%s' error: '%s'" % (latlon_str, str(ex)))

//         return def_latlon

//     @classmethod
//     def __parseExpireDays(cls, expire_txt, id):
//         try:
//             expire_val = float(expire_txt)
//             return int(expire_val * 86400)
//         except Exception as ex:
//             logging.warning("[map desc '%s'] parsing expire_days '%s', error: %s" % (id, expire_txt, str(ex)))
//         return 0

//     @classmethod
//     def __parseXml(cls, xml_root, id):
//         if not id:
//             raise ValueError("[map desc] map id is empty")

//         name = cls.__getElemText(xml_root, "./name", "")
//         if not name:
//             raise ValueError("[map desc '%s'] no map name" % (id,))

//         min_zoom = int(cls.__getElemText(xml_root, "./minZoom", "0", "[map desc '%s'] invalid min zoom, set to 0" % (id,)))
//         max_zoom = int(cls.__getElemText(xml_root, "./maxZoom", "24", "[map desc '%s'] invalid max zoom, set to 24" % (id,)))
//         min_zoom = cls.__cropValue(min_zoom, 0, 24, "[map desc '%s'] min zoom should be in 0~24" % (id,))
//         max_zoom = cls.__cropValue(max_zoom, 0, 24, "[map desc '%s'] max zoom should be in 0~24" % (id,))
//         if min_zoom > max_zoom:
//             raise ValueError("[map desc '%s'] min_zoom(%d) is larger tahn max_zoom(%d)" % (id, min_zoom, max_zoom))

//         tile_type = cls.__getElemText(xml_root, "./tileType", "").lower()
//         if tile_type not in ("jpg", "png"):
//             raise ValueError("[map desc '%s'] not support tile format '%s'" % (id, tile_type))

//         url = cls.__getElemText(xml_root, "./url", "")
//         if not url or ("{$x}" not in url) or ("{$y}" not in url) or ("{$z}" not in url):
//             raise ValueError("[map desc '%s'] url not catains {$x}, {$y}, or {$z}: %s" % (id, url))

//         server_parts = cls.__getElemText(xml_root, "./serverParts", "")

//         invert_y = cls.__getElemText(xml_root, "./invertYCoordinate", "false").lower()
//         if invert_y not in ("false", "true"):
//             logging.warning("[map desc '%s'] invalid invertYCoordinate value: '%s', set to 'false'" % (id, invert_y))


//         coord_sys = cls.__getElemText(xml_root, "./coordinatesystem", "EPSG:4326").upper()

//         lower_corner = cls.__parseLatlon(cls.__getElemText(xml_root, "./lowerCorner", ""), (-180, -85))
//         upper_corner = cls.__parseLatlon(cls.__getElemText(xml_root, "./upperCorner", ""), (180, 85))

//         expire_days = cls.__getElemText(xml_root, "./expireDays", "0")
//         expire_sec = cls.__parseExpireDays(expire_days, id)

//         #collection data
//         desc = MapDescriptor()
//         desc.map_id = id
//         desc.map_title = name
//         desc.level_min = min_zoom
//         desc.level_max = max_zoom
//         desc.url_template = url
//         desc.server_parts = server_parts.split(' ') if server_parts else None
//         desc.invert_y = (invert_y == "true")
//         desc.coord_sys = coord_sys
//         desc.lower_corner = lower_corner
//         desc.upper_corner = upper_corner
//         desc.expire_sec = expire_sec
//         desc.tile_format = tile_type
//         return desc

//     @classmethod
//     def parseXml(cls, filepath=None, xmlstr=None, id=None):
//         if filepath is not None:
//             xml_root = ET.parse(filepath).getroot()
//             if not id:
//                 id = os.path.splitext(os.path.basename(filepath))[0]
//             return cls.__parseXml(xml_root, id)
//         elif xmlstr is not None:
//             xml_root = ET.fromstring(xmlstr)
//             return cls.__parseXml(xml_root, id)
//         else:
//             return None

#[pymodinit(_tile)]
fn init_mod(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<DiskCache>()?;
    m.add_class::<MapDescriptor>()?;

    Ok(())
}
