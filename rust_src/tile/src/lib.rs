#![feature(proc_macro, specialization)]
#![feature(const_fn, const_align_of, const_size_of, const_ptr_null, const_ptr_null_mut)]

extern crate pyo3;

use std::fs::File;
use std::io::prelude::*;

use pyo3::prelude::*;

use pyo3::py::methods as pymethods;
use pyo3::py::class as pyclass;
use pyo3::py::modinit as pymodinit;


// class DiskCache:
//     def start(self):
//         pass

//     def close(self):
//         pass

//     def put(self, level, x, y, data):
//         pass

//     def get(self, level, x, y):
//         pass

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

#[pymodinit(_tile)]
fn init_mod(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<DiskCache>()?;

    Ok(())
}
