use tauri::Manager;

use std::process::Child;
use std::sync::Mutex;
use std::time::Duration;

const HEALTH_URL: &str = "http://127.0.0.1:8000/api/v1/health";
const STARTUP_TIMEOUT_SECS: u64 = 30;

pub struct SidecarState {
    pub child: Mutex<Option<Child>>,
}

pub fn sidecar_path() -> std::path::PathBuf {
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
        let exe = std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|d| d.to_path_buf()))
            .unwrap_or_else(|| std::path::PathBuf::from("."));
        exe.join("codememory-api.exe")
    }
}

pub fn start(handle: &tauri::AppHandle) -> Result<(), String> {
    let exe_path = sidecar_path();

    if !exe_path.exists() {
        log::warn!(
            "Sidecar executable not found at {:?}; skipping sidecar launch.",
            exe_path
        );
        return Ok(());
    }

    log::info!("Starting sidecar: {:?}", exe_path);

    let current_dir = std::env::current_dir().unwrap_or_else(|_| std::path::PathBuf::from("."));

    let mut child = std::process::Command::new(&exe_path)
        .args(["--host", "127.0.0.1", "--port", "8000"])
        .current_dir(&current_dir)
        .spawn()
        .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

    log::info!(
        "Sidecar process spawned (pid={}), waiting for health check...",
        child.id()
    );

    let start = std::time::Instant::now();
    loop {
        if start.elapsed() > Duration::from_secs(STARTUP_TIMEOUT_SECS) {
            let _ = child.kill();
            return Err(format!(
                "Sidecar health check timed out after {} seconds",
                STARTUP_TIMEOUT_SECS
            ));
        }

        match reqwest::blocking::get(HEALTH_URL) {
            Ok(resp) => {
                if resp.status().is_success() {
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
    });

    Ok(())
}

pub fn stop(handle: &tauri::AppHandle) {
    if let Some(state) = handle.try_state::<SidecarState>() {
        if let Some(mut child) = state.child.lock().unwrap().take() {
            let pid = child.id();
            log::info!("Terminating sidecar process (pid={})...", pid);
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}
