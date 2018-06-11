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

//
#[pyclass]
struct MapDescriptor{
    #[prop(get, set)]
    enabled: bool,
    alpha: u8,     
    #[prop(clone_get, set)]
    map_id: String,
    #[prop(get)]
    min_zoom: u8, // 0 ~ 24 
    #[prop(get)]
    max_zoom: u8, // 0 ~ 24 
    #[prop(clone_get, set)]
    tile_format: String,
    #[prop(clone_get, set)]
    url_template: String,
    server_parts: Vec<String>,
    #[prop(get, set)]
    invert_y: bool,
    #[prop(clone_get, set)]
    coord_sys: String,
    #[prop(get)]
    lower_corner: (f32, f32), // (-180 ~ 180, -85 ~ 85)
    #[prop(get)]
    upper_corner: (f32, f32), // (-180 ~ 180, -85 ~ 85)
    #[prop(get, set)]
    expire_sec: u64,
    token: PyToken
}

#[pymethods]
impl MapDescriptor{
    #[new]
    fn __new__(obj: &PyRawObject) -> PyResult<()> 
    {
        obj.init(|t| MapDescriptor{
            enabled: false, 
            alpha: 255, 
            map_id: String::new(),
            min_zoom: 0, 
            max_zoom: 0,
            tile_format: String::new(),
            url_template: String::new(),
            server_parts: Vec::new(),
            invert_y: true,
            coord_sys: String::new(),
            lower_corner: (-180.0, -85.0),
            upper_corner: (180.0, 85.0),
            expire_sec: 0,
            token: t
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

    #[setter]
    fn set_min_zoom(&mut self, value: u8) -> PyResult<()> {
        let normal_value = std::cmp::min(24, std::cmp::max(0, value));
        if normal_value > self.max_zoom {
            self.min_zoom = self.max_zoom;
        }
        self.max_zoom = normal_value;
        Ok(())
    }

    #[setter]
    fn set_max_zoom(&mut self, value: u8) -> PyResult<()> {
        let normal_value = std::cmp::min(24, std::cmp::max(0, value));
        if normal_value < self.min_zoom{
            self.max_zoom = self.min_zoom;
        }
        self.min_zoom = normal_value;
        Ok(())
    }

    #[setter]
    fn set_lower_corner(&mut self, value: (f32, f32)) -> PyResult<()> {
        self.lower_corner.0 = 180f32.min(-180f32.max(value.0));
        self.lower_corner.1 = 85f32.min(-85f32.max(value.1));
        Ok(())
    }

    #[setter]
    fn set_upper_corner(&mut self, value: (f32, f32)) -> PyResult<()> {
        self.upper_corner.0 = 180f32.min(-180f32.max(value.0));
        self.upper_corner.1 = 85f32.min(-85f32.max(value.1));
        Ok(())
    }

    fn save(&self, output_folder: String, file_name: String) -> PyResult<()> {
        Ok(_map_descriptor_save(
                output_folder.as_str(),
                file_name.as_str(),
                self.map_id.as_str(),
                &self.min_zoom,
                &self.max_zoom,
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

    fn read(&mut self, file_path: Option<String>, xml_str: Option<String>, map_id: Option<String>) -> PyResult<()>{
        match map_id {
            Some(id) => { self.map_id = "id".to_string(); },
            None => { self.map_id = Path::new(&file_path.clone().unwrap()).file_stem().unwrap().to_str().unwrap().to_string(); }
        }
        let mut file = File::open(file_path.unwrap())?;
        let mut xml_content = String::new();
        file.read_to_string(&mut xml_content)?;
        _map_descriptor_read(&xml_content, &mut self.min_zoom, &mut self.max_zoom, &mut self.tile_format, &mut self.url_template, 
                             &mut self.server_parts, &mut self.invert_y, &mut self.coord_sys, &mut self.lower_corner.0, 
                             &mut self.lower_corner.1, &mut self.upper_corner.0, &mut self.upper_corner.1, &mut self.expire_sec);
        Ok(())
    }

    // CamelStyle is not suitable for python
    // This function may deprecated
    // please call read method
    fn parseXml(&mut self, file_path: Option<String>, xml_str: Option<String>, map_id: Option<String>) -> PyResult<()>{
        println!("mal nameing function: parseXml is some day");
        self.read(file_path, xml_str, map_id)
    }

    // XXX: not sure clone is nessary
    // fn clone(&self){
    //     println!("clone is not implement");
    // }
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
}
fn _map_descriptor_read(xml_content: &String, min_zoom: &mut u8, max_zoom: &mut u8, 
                        tile_type: &mut str, url: &mut str, server_parts: &mut Vec<String>, invert_y: &mut bool, coordinatesystem: &mut str, 
                        lower_corner_x: &mut f32, lower_corner_y: &mut f32, upper_corner_x: &mut f32, upper_corner_y: &mut f32, expire_sec: &mut u64) {
    // TODO: implement the reader
}

fn _map_descriptor_save(output_folder: &str, file_name: &str, map_title: &str, min_zoom: &u8, max_zoom: &u8, 
                        tile_type: &str, url: &str, server_parts: &str, invert_y: &bool, coordinatesystem: &str, 
                        lower_corner_x: &f32, lower_corner_y: &f32, upper_corner_x: &f32, upper_corner_y: &f32, expire_sec: &u64) {
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
            Ok(e) => assert!(writer.write_event(&e).is_ok()),
            Err(e) => panic!("Error at position {}: {:?}", reader.buffer_position(), e),
        }
        buf.clear();
    }

    let result = writer.into_inner().into_inner();
    fs::write(Path::new(output_folder).join(file_name).with_extension("xml"), result);
}

#[pymodinit(_tile)]
fn init_mod(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<DiskCache>()?;
    m.add_class::<MapDescriptor>()?;

    Ok(())
}
