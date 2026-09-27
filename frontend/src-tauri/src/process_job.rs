//! The kernel terminates the full PyInstaller tree even if the GUI crashes.
#[cfg(windows)]
pub struct ProcessJob(isize);

#[cfg(windows)]
impl ProcessJob {
    pub fn new(child: &std::process::Child) -> Result<Self, String> {
        use std::{mem, os::windows::io::AsRawHandle};
        use windows_sys::Win32::{Foundation::CloseHandle, System::JobObjects::*};
        unsafe {
            let handle = CreateJobObjectW(std::ptr::null(), std::ptr::null());
            if handle.is_null() { return Err(std::io::Error::last_os_error().to_string()); }
            let mut limits: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = mem::zeroed();
            limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            if SetInformationJobObject(handle, JobObjectExtendedLimitInformation,
                &limits as *const _ as *const _, mem::size_of_val(&limits) as u32) == 0
                || AssignProcessToJobObject(handle, child.as_raw_handle()) == 0 {
                let error = std::io::Error::last_os_error().to_string();
                CloseHandle(handle);
                return Err(error);
            }
            Ok(Self(handle as isize))
        }
    }
}

#[cfg(windows)]
impl Drop for ProcessJob {
    fn drop(&mut self) {
        unsafe { windows_sys::Win32::Foundation::CloseHandle(self.0 as _); }
    }
}
