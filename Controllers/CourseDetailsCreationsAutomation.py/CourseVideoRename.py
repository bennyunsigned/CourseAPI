import os
import re
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CourseVideoRenamer:
    def __init__(self, folder_path):
        """
        Initialize the video renamer with the target folder path.
        
        Args:
            folder_path (str): Path to the folder containing video files
        """
        self.folder_path = Path(folder_path)
        if not self.folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        if not self.folder_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {folder_path}")
    
    def get_video_files(self):
        """
        Get all video files in the folder that match the pattern.
        
        Returns:
            list: List of video files matching the pattern
        """
        video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
        video_files = []
        
        for file_path in self.folder_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in video_extensions:
                # Check if filename starts with digits followed by a space
                if re.match(r'^\d+\s+', file_path.name):
                    video_files.append(file_path)
        
        return sorted(video_files, key=lambda x: x.name)
    
    def extract_number_and_name(self, filename):
        """
        Extract the number and remaining filename from a video file.
        
        Args:
            filename (str): Original filename
            
        Returns:
            tuple: (number, remaining_name) or (None, None) if pattern doesn't match
        """
        # Pattern to match number at the beginning followed by space and rest of filename
        pattern = r'^(\d+)\s+(.+)$'
        match = re.match(pattern, filename)
        
        if match:
            number_str = match.group(1)
            remaining_name = match.group(2)
            # Convert to integer to remove leading zeros, then back to string
            number = str(int(number_str))
            return number, remaining_name
        
        return None, None
    
    def rename_file(self, old_path, new_name):
        """
        Rename a single file.
        
        Args:
            old_path (Path): Current file path
            new_name (str): New filename
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            new_path = old_path.parent / new_name
            
            # Check if new filename already exists
            if new_path.exists():
                logger.warning(f"File already exists: {new_name}. Skipping rename of {old_path.name}")
                return False
            
            old_path.rename(new_path)
            logger.info(f"Renamed: {old_path.name} → {new_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error renaming {old_path.name}: {str(e)}")
            return False
    
    def rename_all_videos(self, dry_run=True):
        """
        Rename all video files in the folder.
        
        Args:
            dry_run (bool): If True, only show what would be renamed without actually renaming
            
        Returns:
            dict: Summary of the renaming operation
        """
        video_files = self.get_video_files()
        
        if not video_files:
            logger.info("No video files found matching the pattern.")
            return {"total": 0, "renamed": 0, "skipped": 0, "errors": 0}
        
        logger.info(f"Found {len(video_files)} video files to process.")
        
        renamed_count = 0
        skipped_count = 0
        error_count = 0
        
        for video_file in video_files:
            filename = video_file.name
            number, remaining_name = self.extract_number_and_name(video_file.stem)
            
            if number is None:
                logger.warning(f"Could not extract number from: {filename}")
                skipped_count += 1
                continue
            
            # Create new filename: number.remaining_name.extension
            new_filename = f"{number}.{remaining_name}{video_file.suffix}"
            
            if dry_run:
                logger.info(f"[DRY RUN] Would rename: {filename} → {new_filename}")
                renamed_count += 1
            else:
                if self.rename_file(video_file, new_filename):
                    renamed_count += 1
                else:
                    error_count += 1
        
        summary = {
            "total": len(video_files),
            "renamed": renamed_count,
            "skipped": skipped_count,
            "errors": error_count
        }
        
        logger.info(f"Summary: {summary}")
        return summary

def rename_course_videos(folder_path, dry_run=True):
    """
    Convenience function to rename course videos.
    
    Args:
        folder_path (str): Path to the folder containing video files
        dry_run (bool): If True, only show what would be renamed without actually renaming
        
    Returns:
        dict: Summary of the renaming operation
    """
    try:
        renamer = CourseVideoRenamer(folder_path)
        return renamer.rename_all_videos(dry_run=dry_run)
    except Exception as e:
        logger.error(f"Error initializing video renamer: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    # Example usage
    folder_path = input("Enter the folder path containing video files: ").strip()
    
    if not folder_path:
        print("No folder path provided. Exiting.")
        exit(1)
    
    # First run in dry-run mode to show what would be renamed
    print("\n=== DRY RUN (Preview) ===")
    summary = rename_course_videos(folder_path, dry_run=True)
    
    if "error" in summary:
        print(f"Error: {summary['error']}")
        exit(1)
    
    if summary["total"] == 0:
        print("No files to rename.")
        exit(0)
    
    # Ask for confirmation
    print(f"\nFound {summary['total']} files to rename.")
    confirm = input("Do you want to proceed with the actual renaming? (y/N): ").strip().lower()
    
    if confirm in ['y', 'yes']:
        print("\n=== ACTUAL RENAMING ===")
        final_summary = rename_course_videos(folder_path, dry_run=False)
        print(f"Renaming completed: {final_summary}")
    else:
        print("Renaming cancelled.")