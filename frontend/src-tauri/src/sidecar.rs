use tauri::Manager;

use std::process::Child;
use std::sync::Mutex;
use std::time::Duration;

const HEALTH_URL: &str = "http://127.0.0.1:8000/api/v1/health";
const STARTUP_TIMEOUT_SECS: u64 = 30;

pub struct SidecarState {
    pub child: Mutex<Option<Child>>,
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
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .output();
        if let Err(error) = result {
            log::error!("Failed to terminate sidecar process tree: {}", error);
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

        match reqwest::blocking::get(HEALTH_URL) {
            Ok(resp) => {
                if resp.status().is_success() {
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
    });

    Ok(())
}

pub fn stop(handle: &tauri::AppHandle) {
    if let Some(state) = handle.try_state::<SidecarState>() {
        if let Some(mut child) = state.child.lock().unwrap().take() {
            terminate_sidecar(&mut child);
        }
    }
}
