import os
import re
import shutil
import logging
from pathlib import Path
from typing import List, Tuple, Dict

"""
BatchCourseVideosFinderAndRenamer

Given a base folder that contains multiple course/video folders, this script:
  1) Loops through each immediate subfolder and treats it as a "video folder"
  2) Recursively finds all video files inside that folder (including nested subfolders)
  3) Moves (flattens) those videos into the video folder root ("paste in that folder only")
  4) Applies the CourseVideoRename pattern-based renaming per folder

Usage:
  - Interactive:
      python BatchCourseVideosFinderAndRenamer.py
    Then follow prompts for the base folder and renaming confirmation.

  - CLI (non-interactive):
      python BatchCourseVideosFinderAndRenamer.py --base /path/to/base --apply-rename

Notes:
  - Only MOVE (not copy) is performed when flattening, matching the requested behavior.
  - Renaming follows the logic from CourseVideoRename.py:
      Files with names starting with digits + space will be renamed to
      "<number>.<rest-of-original-stem><extension>" where leading zeros in number are removed.
"""

# Common video file extensions
VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv',
    '.m4v', '.3gp', '.3g2', '.mxf', '.roq', '.nsv', '.f4v',
    '.f4p', '.f4a', '.f4b', '.ts', '.m2ts', '.mts', '.vob',
    '.ogv', '.drc', '.gif', '.gifv', '.mng', '.qt', '.yuv',
    '.rm', '.rmvb', '.asf', '.amv', '.mpg', '.mp2', '.mpeg',
    '.mpe', '.mpv', '.m2v', '.svi', '.3gpp', '.3g2', '.mxf',
    '.roq', '.nsv'
}

# Set up logging (console + file)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_video_process.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def is_video_file(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in VIDEO_EXTENSIONS


def find_video_files(source_folder: str) -> List[str]:
    video_files: List[str] = []
    for root, _, files in os.walk(source_folder):
        for f in files:
            p = os.path.join(root, f)
            if is_video_file(p):
                video_files.append(p)
    return video_files


def create_unique_filename(output_folder: str, filename: str) -> str:
    base_name = Path(filename).stem
    extension = Path(filename).suffix
    counter = 1
    new_filename = filename
    while os.path.exists(os.path.join(output_folder, new_filename)):
        new_filename = f"{base_name}_{counter}{extension}"
        counter += 1
    return new_filename


def move_videos_to_folder_root(video_folder: str) -> Tuple[List[str], List[str]]:
    """Flatten videos found under video_folder into its root directory."""
    moved, failed = [], []
    videos = find_video_files(video_folder)
    if not videos:
        logger.info(f"No videos found under: {video_folder}")
        return moved, failed

    for v in videos:
        try:
            src = Path(v)
            # If already in root, skip moving
            if src.parent == Path(video_folder):
                logger.debug(f"Already at root, skipping move: {src}")
                continue

            dest_name = create_unique_filename(video_folder, src.name)
            dest_path = Path(video_folder) / dest_name
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(src), str(dest_path))
            moved.append(str(dest_path))
            logger.info(f"Moved: {src} -> {dest_path}")
        except Exception as e:
            failed.append(v)
            logger.error(f"Failed to move {v}: {e}")
    return moved, failed


# --- Renaming logic (mirrors CourseVideoRename.py) ---
NUMBER_PREFIX_PATTERN = re.compile(r'^(\d+)\s+(.+)$')
BASIC_VIDEO_EXTS_FOR_RENAME = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}


def get_candidate_video_files(folder_path: Path) -> List[Path]:
    candidates: List[Path] = []
    for file_path in folder_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in BASIC_VIDEO_EXTS_FOR_RENAME:
            if NUMBER_PREFIX_PATTERN.match(file_path.stem):
                candidates.append(file_path)
    # Sort by name for stable ordering
    return sorted(candidates, key=lambda x: x.name)


def rename_all_videos_in_folder(folder_path: str, dry_run: bool = True) -> Dict[str, int]:
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        logger.error(f"Folder not found or not a directory: {folder_path}")
        return {"total": 0, "renamed": 0, "skipped": 0, "errors": 0}

    files = get_candidate_video_files(folder)
    if not files:
        logger.info(f"No rename-candidate videos in: {folder}")
        return {"total": 0, "renamed": 0, "skipped": 0, "errors": 0}

    renamed, skipped, errors = 0, 0, 0
    logger.info(f"Found {len(files)} rename candidates in {folder}")

    for f in files:
        m = NUMBER_PREFIX_PATTERN.match(f.stem)
        if not m:
            skipped += 1
            continue
        number_str, rest_name = m.group(1), m.group(2)
        try:
            number = str(int(number_str))  # remove leading zeros
        except Exception:
            number = number_str  # fallback: keep as-is

        new_filename = f"{number}.{rest_name}{f.suffix}"
        new_path = f.parent / new_filename

        if new_path.exists():
            logger.warning(f"Target exists, skipping: {new_path.name}")
            skipped += 1
            continue

        if dry_run:
            logger.info(f"[DRY RUN] Would rename: {f.name} -> {new_filename}")
            renamed += 1
        else:
            try:
                f.rename(new_path)
                logger.info(f"Renamed: {f.name} -> {new_filename}")
                renamed += 1
            except Exception as e:
                logger.error(f"Error renaming {f.name}: {e}")
                errors += 1

    summary = {"total": len(files), "renamed": renamed, "skipped": skipped, "errors": errors}
    logger.info(f"Rename summary for {folder}: {summary}")
    return summary


def process_base_folder(base_folder: str, apply_rename: bool = False) -> None:
    base = Path(base_folder)
    if not base.exists() or not base.is_dir():
        logger.error(f"Base folder not found or not a directory: {base_folder}")
        return

    # Enumerate immediate subdirectories only
    subfolders = [p for p in base.iterdir() if p.is_dir()]
    if not subfolders:
        logger.warning("No subfolders found to process.")
        return

    logger.info(f"Discovered {len(subfolders)} folders under base: {base}")

    for folder in subfolders:
        logger.info("\n========================================")
        logger.info(f"Processing folder: {folder}")

        # 1) Move/flatten videos into this folder's root
        moved, failed = move_videos_to_folder_root(str(folder))
        logger.info(f"Flatten result: moved={len(moved)} failed={len(failed)}")

        # 2) Dry-run rename summary
        summary_preview = rename_all_videos_in_folder(str(folder), dry_run=True)

        # 3) Apply rename if requested
        if apply_rename and summary_preview.get("total", 0) > 0:
            logger.info("Applying actual renames...")
            rename_all_videos_in_folder(str(folder), dry_run=False)
        else:
            logger.info("Rename not applied (dry-run only). Use --apply-rename to perform renaming.")


def _interactive_main() -> None:
    base_folder = input("Enter the BASE folder path containing multiple video folders: ").strip()
    if not base_folder:
        print("No base folder provided. Exiting.")
        return

    # Always do dry-run previews first
    apply = input("Do you want to APPLY renaming after preview for all folders? (y/N): ").strip().lower() in {"y", "yes"}
    process_base_folder(base_folder, apply_rename=apply)


if __name__ == "__main__":
    # Optional argparse for non-interactive usage
    try:
        import argparse
        parser = argparse.ArgumentParser(description="Flatten and rename videos across multiple folders.")
        parser.add_argument("--base", dest="base", help="Base folder containing multiple subfolders", default=None)
        parser.add_argument("--apply-rename", dest="apply", help="Apply actual renaming after dry-run previews", action="store_true")
        args = parser.parse_args()

        if args.base:
            process_base_folder(args.base, apply_rename=args.apply)
        else:
            _interactive_main()
    except SystemExit:
        # argparse already printed help/version as needed
        pass
