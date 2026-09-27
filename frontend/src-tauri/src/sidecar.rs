use tauri::Manager;

use std::process::Child;
use std::sync::Mutex;
use std::time::Duration;
#[cfg(windows)]
use std::os::windows::process::CommandExt;

const HEALTH_URL: &str = "http://127.0.0.1:8000/api/v1/health";
const STARTUP_TIMEOUT_SECS: u64 = 90;

pub struct SidecarState {
    pub child: Mutex<Option<Child>>,
    #[cfg(windows)]
    pub _job: crate::process_job::ProcessJob,
}

fn terminate_sidecar(child: &mut Child) {
    let pid = child.id();
    log::info!("Terminating sidecar process tree (pid={})...", pid);

    #[cfg(windows)]
    {
        // PyInstaller's one-file bootloader starts the actual server as a
        // separate child process. Killing only the bootloader leaves FastAPI
        // listening after the Tauri app closes, so terminate the full tree.
        let result = std::process::Command::new("taskkill")
            .creation_flags(0x08000000)
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .output();
        if !matches!(result, Ok(ref output) if output.status.success()) {
            log::error!("Failed to terminate sidecar process tree");
            let _ = child.kill();
        }
    }

    #[cfg(not(windows))]
    {
        let _ = child.kill();
    }

    let _ = child.wait();
}

pub fn sidecar_path(handle: &tauri::AppHandle) -> std::path::PathBuf {
    if cfg!(debug_assertions) {
        let manifest_dir =
            std::env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| ".".to_string());
        let project_root = std::path::Path::new(&manifest_dir)
            .join("..")
            .join("..")
            .canonicalize()
            .map(|p| p.to_path_buf())
            .unwrap_or_else(|_| {
                std::path::Path::new(&manifest_dir)
                    .join("..")
                    .join("..")
                    .to_path_buf()
            });
        project_root.join("dist").join("codememory-api.exe")
    } else {
        let resource_dir = match handle.path().resource_dir() {
            Ok(dir) => dir,
            Err(_) => std::path::PathBuf::from("."),
        };

        let candidates = [
            resource_dir.join("codememory-api.exe"),
            resource_dir.join("dist").join("codememory-api.exe"),
            resource_dir.join("_up_").join("_up_").join("dist").join("codememory-api.exe"),
        ];

        for path in &candidates {
            if path.exists() {
                return path.to_path_buf();
            }
        }

        resource_dir.join("codememory-api.exe")
    }
}

pub fn start(handle: &tauri::AppHandle) -> Result<(), String> {
    let exe_path = sidecar_path(handle);

    if !exe_path.exists() {
        if cfg!(debug_assertions) {
            log::warn!(
                "Sidecar executable not found at {:?}; skipping sidecar launch.",
                exe_path
            );
            return Ok(());
        } else {
            log::error!(
                "Production sidecar executable not found at {:?}. \
                The application cannot start without its backend service.",
                exe_path
            );
            return Err(format!(
                "Required sidecar executable not found at {:?}. \
                Production builds require the bundled sidecar to be present.",
                exe_path
            ));
        }
    }

    log::info!("Starting sidecar: {:?}", exe_path);

    let current_dir = std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from("."));
    if std::net::TcpStream::connect_timeout(&"127.0.0.1:8000".parse().unwrap(), Duration::from_millis(500)).is_ok() {
        return Err("Port 8000 is already in use. Close the other CodeMemory/backend process and reopen CodeMemory. No existing process was terminated.".into());
    }
    let instance_id = format!("{}-{}", std::process::id(), std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_nanos());
    let mut command = std::process::Command::new(&exe_path);
    command.args(["--host", "127.0.0.1", "--port", "8000"])
        .current_dir(&current_dir).env("CODEMEMORY_SIDECAR_ID", &instance_id);
    if !cfg!(debug_assertions) {
        command.env("CODEMEMORY_DESKTOP", "1");
        if std::env::var_os("CODEMEMORY_LEGACY_DIR").is_none() {
            let install_dir = std::env::current_exe().ok().and_then(|p| p.parent().map(|p| p.to_path_buf()));
            let legacy = if current_dir.join("data").exists() { current_dir.clone() }
                else { install_dir.unwrap_or(current_dir.clone()) };
            command.env("CODEMEMORY_LEGACY_DIR", legacy);
        }
    }
    #[cfg(windows)]
    command.creation_flags(0x08000000);
    let mut child = command.spawn()
        .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;
    #[cfg(windows)]
    let job = match crate::process_job::ProcessJob::new(&child) {
        Ok(job) => job,
        Err(error) => { terminate_sidecar(&mut child); return Err(error); }
    };
    let client = reqwest::blocking::Client::builder().timeout(Duration::from_secs(2)).no_proxy()
        .build().map_err(|e| e.to_string())?;

    log::info!(
        "Sidecar process spawned (pid={}), waiting for health check...",
        child.id()
    );

    let start = std::time::Instant::now();
    loop {
        // Do not accept a pre-existing server on port 8000 as evidence that
        // this sidecar started successfully. In particular, fail if the child
        // exited after a bind failure instead of connecting the UI to an
        // unrelated backend.
        if let Some(status) = child
            .try_wait()
            .map_err(|e| format!("Failed to check sidecar process: {}", e))?
        {
            return Err(format!(
                "FastAPI sidecar exited during startup with status {}",
                status
            ));
        }

        if start.elapsed() > Duration::from_secs(STARTUP_TIMEOUT_SECS) {
            terminate_sidecar(&mut child);
            return Err(format!(
                "Sidecar health check timed out after {} seconds",
                STARTUP_TIMEOUT_SECS
            ));
        }

        match client.get(HEALTH_URL).send() {
            Ok(resp) => {
                if resp.status().is_success() {
                    let body = resp.text().unwrap_or_default();
                    let health: serde_json::Value = serde_json::from_str(&body).unwrap_or_default();
                    if health["instance_id"].as_str() != Some(instance_id.as_str()) || health["overall"] != "ok" {
                        std::thread::sleep(Duration::from_millis(200));
                        continue;
                    }
                    if let Some(status) = child
                        .try_wait()
                        .map_err(|e| format!("Failed to check sidecar process: {}", e))?
                    {
                        return Err(format!(
                            "FastAPI sidecar exited during startup with status {}",
                            status
                        ));
                    }
                    log::info!("Sidecar is healthy and ready!");
                    break;
                }
            }
            Err(_) => {}
        }

        std::thread::sleep(Duration::from_millis(500));
    }

    handle.manage(SidecarState {
        child: Mutex::new(Some(child)),
        #[cfg(windows)]
        _job: job,
    });

    let app = handle.clone();
    std::thread::spawn(move || loop {
        std::thread::sleep(Duration::from_secs(1));
        let state = app.state::<SidecarState>();
        let mut slot = match state.child.lock() { Ok(slot) => slot, Err(_) => return };
        let Some(child) = slot.as_mut() else { return };
        if matches!(child.try_wait(), Ok(Some(_))) {
            slot.take();
            drop(slot);
            show_error("The local CodeMemory service stopped. Your saved data is retained. Reopen CodeMemory; diagnostics are in LocalAppData/CodeMemory/logs.");
            app.exit(1);
            return;
        }
    });

    Ok(())
}

pub fn show_error(message: &str) {
    log::error!("{}", message);
    #[cfg(windows)]
    unsafe {
        use windows_sys::Win32::UI::WindowsAndMessaging::{MessageBoxW, MB_ICONERROR, MB_OK};
        let text: Vec<u16> = message.encode_utf16().chain(Some(0)).collect();
        let title: Vec<u16> = "CodeMemory".encode_utf16().chain(Some(0)).collect();
        MessageBoxW(std::ptr::null_mut(), text.as_ptr(), title.as_ptr(), MB_OK | MB_ICONERROR);
    }
}

pub fn stop(handle: &tauri::AppHandle) {
    if let Some(state) = handle.try_state::<SidecarState>() {
        if let Some(mut child) = state.child.lock().unwrap().take() {
            terminate_sidecar(&mut child);
        }
    }
}
