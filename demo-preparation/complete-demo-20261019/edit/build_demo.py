from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "recordings"
ASSETS = ROOT / "assets"
EDIT = ROOT / "edit"
SCENES = EDIT / "scenes"
FFMPEG = Path(r"C:\Users\Jay Janardan Patil\ffmeg\ffmpeg-7.1.1-full_build\bin\ffmpeg.exe")
FPS = 30
SIZE = "1920x1080"


def run(args: list[str]) -> None:
    subprocess.run(args, check=True)


def zoom_filter(duration: float, center: tuple[int, int], zoom: float = 1.35) -> str:
    x, y = center
    # Smooth three-second push in and three-second pull back, then hold wide.
    curve = f"if(lte(on,90),1+({zoom}-1)*on/90,if(lte(on,180),{zoom}-({zoom}-1)*(on-90)/90,1))"
    left = f"min(iw-iw/zoom,max(0,{x}-iw/zoom/2))"
    top = f"min(ih-ih/zoom,max(0,{y}-ih/zoom/2))"
    return f"zoompan=z='{curve}':x='{left}':y='{top}':d=1:s={SIZE}:fps={FPS},fps={FPS},format=yuv420p"


def render_still(name: str, image: Path, seconds: float) -> Path:
    output = SCENES / f"{name}.mp4"
    frames = round(seconds * FPS)
    vf = f"zoompan=z='1+0.015*sin(PI*on/{frames})':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={SIZE}:fps={FPS},fps={FPS},format=yuv420p,fade=t=in:st=0:d=0.45"
    run([str(FFMPEG), "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(image), "-vf", vf, "-frames:v", str(frames), "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(output)])
    return output


def render_clip(
    name: str,
    source: Path,
    start: float,
    seconds: float,
    *,
    crop: str | None = None,
    focus: tuple[int, int] | None = None,
    pad: float = 0,
    final_seconds: float | None = None,
) -> Path:
    output = SCENES / f"{name}.mp4"
    filters = []
    if crop:
        filters.append(f"crop={crop}")
    if focus:
        filters.append(zoom_filter(seconds, focus))
    else:
        filters.extend([f"scale={SIZE}:flags=lanczos", f"fps={FPS}", "format=yuv420p"])
    if pad:
        filters.append(f"tpad=stop_mode=clone:stop_duration={pad}")
    target = final_seconds if final_seconds is not None else seconds + pad
    frames = round(target * FPS)
    run([
        # Keep -t off the output side: it would trim the filter output before
        # tpad can supply the intentional holds. Frame count below controls
        # the exact finished duration.
        str(FFMPEG), "-y", "-ss", str(start), "-i", str(source),
        "-vf", ",".join(filters), "-frames:v", str(frames), "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        str(output),
    ])
    return output


def main() -> None:
    SCENES.mkdir(parents=True, exist_ok=True)
    clips: list[Path] = []
    clips.append(render_still("01-intro", ASSETS / "intro.png", 4.0))

    # Brief view of the real landing page, cropped to its product statement so
    # the illustrative example metrics are not presented as this user's data.
    clips.append(render_clip("02-landing", REC / "test-capture.mp4", 0, 3.0, crop="1200:675:200:220"))

    # The app was genuinely empty before the public-profile import. Hold the
    # empty overview long enough to read while keeping the captured cursor.
    clips.append(render_clip("03-empty", REC / "test-capture.mp4", 14, 6.0, crop="1706:960:20:120", pad=8.0))

    # Real username form interaction, followed by the actual public-import
    # progress state. The pull-back returns the full connection screen.
    clips.append(render_clip("04-connect-close", REC / "connection-flow.mp4", 1, 10.0, focus=(950, 610)))
    clips.append(render_clip("05-connect-progress", REC / "connection-flow.mp4", 11, 14.0))

    # Actual result after the 20-record public import.
    clips.append(render_clip("06-import-result", REC / "dashboard-settings.mkv", 20, 10.0, pad=10.0))

    # The form itself was recorded before credentials were entered. The later
    # Settings status is genuine: validation failed and no authenticated sync
    # was claimed. No private value appears in either recording.
    clips.append(render_clip("07-settings-account", REC / "dashboard-settings.mkv", 30, 16.0, focus=(1220, 430)))
    clips.append(render_clip("08-auth-outcome", REC / "dashboard-settings.mkv", 38, 12.0, focus=(1220, 430), pad=4.0))

    # Search the real submission table, then open the matching imported item.
    clips.append(render_clip("09-search", REC / "history-search-insight.mkv", 20, 13.0, focus=(490, 380), pad=11.0))
    clips.append(render_clip("10-problem-detail", REC / "history-search-insight.mkv", 33, 11.0, focus=(1480, 440), pad=15.0))

    # Show the analytics summary, then the real click that expands evidence for
    # the Array topic insight. A short hold lets the viewer read the result.
    clips.append(render_clip("11-analytics-summary", REC / "dashboard-settings.mkv", 0, 18.0))
    clips.append(render_clip("12-analytics-insight", REC / "history-search-insight.mkv", 50, 10.0, focus=(860, 700), pad=24.0))
    clips.append(render_still("13-outro", ASSETS / "outro.png", 5.2))

    concat_file = EDIT / "scenes.txt"
    concat_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips), encoding="utf-8")
    picture = EDIT / "picture-only.mp4"
    run([str(FFMPEG), "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", "-movflags", "+faststart", str(picture)])

    final = ROOT / "CodeMemory-product-demo.mp4"
    narration = ROOT / "narration.mp3"
    run([
        str(FFMPEG), "-y", "-i", str(picture), "-i", str(narration),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-ar", "44100", "-shortest", "-movflags", "+faststart", str(final),
    ])
    print(final)


if __name__ == "__main__":
    main()
