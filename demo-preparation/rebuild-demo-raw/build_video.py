#!/usr/bin/env python3
"""
Build the CodeMemory demo video from screenshots with cinematic zooms.
"""

import subprocess
import os

REPO_ROOT = r"C:\Users\Jay Janardan Patil\Desktop\CodeMemory"
RAW_DIR = os.path.join(REPO_ROOT, "demo-preparation", "rebuild-demo-raw")
SCREENS_DIR = os.path.join(RAW_DIR, "screens")
RECORDINGS_DIR = os.path.join(REPO_ROOT, "demo-preparation", "recordings")
OUTPUT_DIR = os.path.join(RAW_DIR, "final")
FFMPEG = r"C:\Users\Jay Janardan Patil\ffmeg\ffmpeg-7.1.1-full_build\bin\ffmpeg.exe"

# Scene definition: list of (screen_file, duration, zoom_factor, x_pct, y_pct)
# x_pct and y_pct are 0.0-1.0, specifying the zoom center in image coordinates
SCENES = [
    # Scene 1: Landing (3s) - wide view, slow zoom in
    [("01-landing.png", 3, 1.0, 0.5, 0.5)],
    
    # Scene 2: LeetCode Connect (12s)
    [
        ("02-connect-empty.png", 1.5, 1.0, 0.5, 0.5),          # Wide view
        ("02b-username-typed.png", 2.5, 1.5, 0.35, 0.55),     # Zoom on username
        ("02c-connect-button-hover.png", 2.0, 1.8, 0.75, 0.70),  # Zoom on button
        ("02d-connect-processing.png", 2.0, 1.2, 0.5, 0.5),    # Center view
        ("02e-connect-success.png", 4.0, 1.0, 0.5, 0.5),      # Full view
    ],
    
    # Scene 3: Settings (8s)
    [
        ("03-settings-page.png", 1.5, 1.2, 0.5, 0.3),          # Wide view
        ("03b-settings-auth-section.png", 3.0, 1.5, 0.55, 0.6), # Zoom on account
        ("03d-settings-sync-btn.png", 3.5, 1.8, 0.75, 0.65),    # Zoom on sync btn
    ],
    
    # Scene 4: Dashboard (5s)
    [
        ("04-dashboard-populated.png", 3.0, 1.0, 0.5, 0.3),    # Wide view
        ("04b-dashboard-insights.png", 2.0, 1.3, 0.5, 0.6),    # Zoom on insights
    ],
    
    # Scene 5: Problems (5s)
    [
        ("05-problems-list.png", 2.0, 1.0, 0.5, 0.4),           # Wide view
        ("05b-problems-filtered.png", 3.0, 1.5, 0.3, 0.5),     # Zoom on filtered
    ],
    
    # Scene 6: Problem Detail (5s)
    [
        ("06-problem-detail.png", 3.0, 1.3, 0.4, 0.35),       # Zoom on title
        ("06b-problem-submissions.png", 2.0, 1.0, 0.5, 0.6),  # Wide view
    ],
    
    # Scene 7: Search (4s)
    [("07-search-results.png", 4.0, 1.5, 0.5, 0.45)],
    
    # Scene 8: Analytics (5s)
    [
        ("08-analytics-charts.png", 2.5, 1.0, 0.5, 0.4),
        ("08b-analytics-insights.png", 2.5, 1.3, 0.5, 0.6),
    ],
    
    # Scene 9: Knowledge Graph (4s)
    [("09-knowledge-graph.png", 4.0, 1.5, 0.5, 0.5)],
    
    # Scene 10: Revision (4s)
    [("10-revision-queue.png", 4.0, 1.3, 0.4, 0.5)],
    
    # Scene 11: Closing (3s)
    [("11-closing.png", 3, 1.0, 0.5, 0.5)],
]


def build_clip(screen_file, duration, zoom_factor, x_pct, y_pct, output_path):
    """Build a single clip with zoom effect."""
    screen_path = os.path.join(SCREENS_DIR, screen_file)
    
    if not os.path.exists(screen_path):
        print(f"  WARNING: {screen_file} not found!")
        return False
    
    # Calculate x, y for zoom centering
    # For a 1910x... image scaled to 1920x1080:
    # x = floor((W - 1920/z) * x_pct)  where W is the scaled width
    # y = floor((H - 1080/z) * y_pct) where H is the scaled height
    
    # Build the zoompan filter
    # z = constant zoom factor for this clip
    # x, y = position to show (centered around x_pct, y_pct of the image)
    # d = 0.5 means zoom transitions every 0.5 seconds
    
    vf = (
        f"scale=1920:1080,"
        f"zoompan=z={zoom_factor}:d=0.5:s=1920x1080:fps=30:"
        f"x='floor((W-1920/z)*{x_pct})':y='floor((H-1080/z)*{y_pct})'"
    )
    
    cmd = [
        FFMPEG, "-y",
        "-loop", "1",
        "-i", screen_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-t", str(int(duration)),
        "-pix_fmt", "yuv420p",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FFmpeg error: {result.stderr[:300]}")
        return False
    return True


def build_simple_clip(screen_file, duration, output_path):
    """Build a simple clip without zoom (fallback)."""
    screen_path = os.path.join(SCREENS_DIR, screen_file)
    
    if not os.path.exists(screen_path):
        print(f"  WARNING: {screen_file} not found!")
        return False
    
    cmd = [
        FFMPEG, "-y",
        "-loop", "1",
        "-i", screen_path,
        "-vf", "scale=1920:1080,setsar=1",
        "-c:v", "libx264",
        "-t", str(int(duration)),
        "-pix_fmt", "yuv420p",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("=== Building CodeMemory Demo Video ===\n")
    
    scene_clips = []
    all_clips = []
    
    for scene_idx, scene in enumerate(SCENES):
        print(f"Scene {scene_idx + 1}:")
        clips = []
        
        for i, (screen_file, duration, zoom, x_pct, y_pct) in enumerate(scene):
            clip_name = f"scene{scene_idx+1}_{i}.mp4"
            clip_path = os.path.join(OUTPUT_DIR, clip_name)
            
            print(f"  {clip_name}: {duration}s, zoom={zoom}, ({x_pct},{y_pct})")
            
            if zoom > 1.0:
                success = build_clip(screen_file, duration, zoom, x_pct, y_pct, clip_path)
                if not success:
                    print(f"  Zoom failed, using simple clip")
                    build_simple_clip(screen_file, duration, clip_path)
            else:
                build_simple_clip(screen_file, duration, clip_path)
            
            clips.append(clip_path)
            all_clips.append(clip_path)
        
        # Concatenate clips in this scene
        if len(clips) == 1:
            scene_clip = clips[0]
        else:
            concat_file = os.path.join(OUTPUT_DIR, f"concat_s{scene_idx+1}.txt")
            with open(concat_file, "w") as f:
                for clip in clips:
                    f.write(f"file '{clip}'\n")
            
            scene_clip = os.path.join(OUTPUT_DIR, f"scene{scene_idx+1}.mp4")
            cmd = [
                FFMPEG, "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                scene_clip
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  Concat error: {result.stderr[:200]}")
        
        scene_clips.append(scene_clip)
    
    # Build final video with intro and outro
    print("\n=== Combining all scenes ===")
    concat_file = os.path.join(OUTPUT_DIR, "concat_final.txt")
    
    with open(concat_file, "w") as f:
        # Intro
        intro_path = os.path.join(RECORDINGS_DIR, "intro-smooth.mp4")
        if os.path.exists(intro_path):
            f.write(f"file '{intro_path}'\n")
        
        # Scenes
        for clip in scene_clips:
            if os.path.exists(clip):
                f.write(f"file '{clip}'\n")
        
        # Outro
        outro_path = os.path.join(RECORDINGS_DIR, "outro-smooth.mp4")
        if os.path.exists(outro_path):
            f.write(f"file '{outro_path}'\n")
    
    final_path = os.path.join(OUTPUT_DIR, "codememory-demo-rebuild-novoice.mp4")
    
    cmd = [
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        final_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0 and os.path.exists(final_path):
        size = os.path.getsize(final_path)
        print(f"\nFinal video: {final_path}")
        print(f"Size: {size / 1024 / 1024:.2f} MB")
        
        # Get duration
        cmd_info = [FFMPEG, "-i", final_path, "-hide_banner"]
        result_info = subprocess.run(cmd_info, capture_output=True, text=True)
        for line in (result_info.stderr + result_info.stdout).split('\n'):
            if 'Duration' in line:
                print(f"Duration: {line.strip()}")
    else:
        print(f"ERROR: {result.stderr[:500]}")
        print("Failed to create final video!")


if __name__ == "__main__":
    main()
