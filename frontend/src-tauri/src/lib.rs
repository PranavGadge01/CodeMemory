mod sidecar;

use tauri::Manager;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      sidecar::start(app.handle())?;

      Ok(())
    })
    .on_window_event(|window, event| {
      if let tauri::WindowEvent::Destroyed = event {
        sidecar::stop(window.app_handle());
      }
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
