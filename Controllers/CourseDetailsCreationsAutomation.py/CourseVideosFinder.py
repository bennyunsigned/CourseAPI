import os
import shutil
import logging
from pathlib import Path
from typing import List, Tuple
import uuid

class CourseVideosFinder:
    """
    A class to find video files in a directory and its subdirectories,
    and move them to a specified output location.
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
    
    def __init__(self, log_level=logging.INFO):
        """Initialize the CourseVideosFinder with logging configuration."""
        self.setup_logging(log_level)
        self.logger = logging.getLogger(__name__)
    
    def setup_logging(self, log_level):
        """Setup logging configuration."""
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('video_finder.log'),
                logging.StreamHandler()
            ]
        )
    
    def is_video_file(self, file_path: str) -> bool:
        """
        Check if a file is a video file based on its extension.
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            bool: True if the file is a video file, False otherwise
        """
        return Path(file_path).suffix.lower() in self.VIDEO_EXTENSIONS
    
    def find_video_files(self, source_folder: str) -> List[str]:
        """
        Recursively find all video files in the source folder and its subfolders.
        
        Args:
            source_folder (str): Path to the source folder to search
            
        Returns:
            List[str]: List of paths to video files found
        """
        video_files = []
        
        if not os.path.exists(source_folder):
            self.logger.error(f"Source folder does not exist: {source_folder}")
            return video_files
        
        if not os.path.isdir(source_folder):
            self.logger.error(f"Source path is not a directory: {source_folder}")
            return video_files
        
        self.logger.info(f"Searching for video files in: {source_folder}")
        
        try:
            for root, dirs, files in os.walk(source_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self.is_video_file(file_path):
                        video_files.append(file_path)
                        self.logger.info(f"Found video file: {file_path}")
            
            self.logger.info(f"Total video files found: {len(video_files)}")
            
        except Exception as e:
            self.logger.error(f"Error while searching for video files: {str(e)}")
        
        return video_files
    
    def create_unique_filename(self, output_folder: str, filename: str) -> str:
        """
        Create a unique filename in the output folder to avoid conflicts.
        
        Args:
            output_folder (str): Path to the output folder
            filename (str): Original filename
            
        Returns:
            str: Unique filename
        """
        base_name = Path(filename).stem
        extension = Path(filename).suffix
        counter = 1
        new_filename = filename
        
        while os.path.exists(os.path.join(output_folder, new_filename)):
            new_filename = f"{base_name}_{counter}{extension}"
            counter += 1
        
        return new_filename
    
    def move_video_files(self, source_folder: str, output_folder: str, 
                        preserve_structure: bool = False) -> Tuple[List[str], List[str]]:
        """
        Find and move all video files from source folder to output folder.
        
        Args:
            source_folder (str): Path to the source folder to search
            output_folder (str): Path to the output folder where files will be moved
            preserve_structure (bool): Whether to preserve the folder structure
            
        Returns:
            Tuple[List[str], List[str]]: Lists of successfully moved files and failed files
        """
        # Create output folder if it doesn't exist
        try:
            os.makedirs(output_folder, exist_ok=True)
            self.logger.info(f"Output folder created/verified: {output_folder}")
        except Exception as e:
            self.logger.error(f"Failed to create output folder: {str(e)}")
            return [], []
        
        # Find all video files
        video_files = self.find_video_files(source_folder)
        
        if not video_files:
            self.logger.warning("No video files found to move.")
            return [], []
        
        moved_files = []
        failed_files = []
        
        for video_file in video_files:
            try:
                if preserve_structure:
                    # Preserve folder structure
                    relative_path = os.path.relpath(video_file, source_folder)
                    destination_path = os.path.join(output_folder, relative_path)
                    destination_dir = os.path.dirname(destination_path)
                    os.makedirs(destination_dir, exist_ok=True)
                else:
                    # Flatten all files to output folder
                    filename = os.path.basename(video_file)
                    unique_filename = self.create_unique_filename(output_folder, filename)
                    destination_path = os.path.join(output_folder, unique_filename)
                
                # Move the file
                shutil.move(video_file, destination_path)
                moved_files.append(destination_path)
                self.logger.info(f"Moved: {video_file} -> {destination_path}")
                
            except Exception as e:
                failed_files.append(video_file)
                self.logger.error(f"Failed to move {video_file}: {str(e)}")
        
        self.logger.info(f"Successfully moved {len(moved_files)} files")
        self.logger.info(f"Failed to move {len(failed_files)} files")
        
        return moved_files, failed_files
    
    def copy_video_files(self, source_folder: str, output_folder: str, 
                        preserve_structure: bool = False) -> Tuple[List[str], List[str]]:
        """
        Find and copy all video files from source folder to output folder.
        
        Args:
            source_folder (str): Path to the source folder to search
            output_folder (str): Path to the output folder where files will be copied
            preserve_structure (bool): Whether to preserve the folder structure
            
        Returns:
            Tuple[List[str], List[str]]: Lists of successfully copied files and failed files
        """
        # Create output folder if it doesn't exist
        try:
            os.makedirs(output_folder, exist_ok=True)
            self.logger.info(f"Output folder created/verified: {output_folder}")
        except Exception as e:
            self.logger.error(f"Failed to create output folder: {str(e)}")
            return [], []
        
        # Find all video files
        video_files = self.find_video_files(source_folder)
        
        if not video_files:
            self.logger.warning("No video files found to copy.")
            return [], []
        
        copied_files = []
        failed_files = []
        
        for video_file in video_files:
            try:
                if preserve_structure:
                    # Preserve folder structure
                    relative_path = os.path.relpath(video_file, source_folder)
                    destination_path = os.path.join(output_folder, relative_path)
                    destination_dir = os.path.dirname(destination_path)
                    os.makedirs(destination_dir, exist_ok=True)
                else:
                    # Flatten all files to output folder
                    filename = os.path.basename(video_file)
                    unique_filename = self.create_unique_filename(output_folder, filename)
                    destination_path = os.path.join(output_folder, unique_filename)
                
                # Copy the file
                shutil.copy2(video_file, destination_path)
                copied_files.append(destination_path)
                self.logger.info(f"Copied: {video_file} -> {destination_path}")
                
            except Exception as e:
                failed_files.append(video_file)
                self.logger.error(f"Failed to copy {video_file}: {str(e)}")
        
        self.logger.info(f"Successfully copied {len(copied_files)} files")
        self.logger.info(f"Failed to copy {len(failed_files)} files")
        
        return copied_files, failed_files
    
    def get_video_info(self, source_folder: str) -> dict:
        """
        Get information about video files in the source folder.
        
        Args:
            source_folder (str): Path to the source folder to analyze
            
        Returns:
            dict: Information about video files found
        """
        video_files = self.find_video_files(source_folder)
        
        info = {
            'total_files': len(video_files),
            'files_by_extension': {},
            'total_size_bytes': 0,
            'files_list': video_files
        }
        
        for video_file in video_files:
            try:
                # Get file extension
                extension = Path(video_file).suffix.lower()
                if extension in info['files_by_extension']:
                    info['files_by_extension'][extension] += 1
                else:
                    info['files_by_extension'][extension] = 1
                
                # Get file size
                file_size = os.path.getsize(video_file)
                info['total_size_bytes'] += file_size
                
            except Exception as e:
                self.logger.error(f"Error getting info for {video_file}: {str(e)}")
        
        # Convert total size to human readable format
        info['total_size_mb'] = round(info['total_size_bytes'] / (1024 * 1024), 2)
        info['total_size_gb'] = round(info['total_size_bytes'] / (1024 * 1024 * 1024), 2)
        
        return info

# Example usage and utility functions
def main():
    """Example usage of the CourseVideosFinder class."""
    finder = CourseVideosFinder()
    
    # Example folder paths (you can modify these)
    source_folder = input("Enter the source folder path: ").strip()
    output_folder = input("Enter the output folder path: ").strip()
    
    # Get video information first
    print("\nAnalyzing source folder...")
    info = finder.get_video_info(source_folder)
    print(f"Found {info['total_files']} video files")
    print(f"Total size: {info['total_size_mb']} MB ({info['total_size_gb']} GB)")
    print("Files by extension:", info['files_by_extension'])
    
    if info['total_files'] > 0:
        action = input("\nDo you want to (m)ove or (c)opy the files? [m/c]: ").strip().lower()
        preserve = input("Preserve folder structure? [y/n]: ").strip().lower() == 'y'
        
        if action == 'm':
            moved, failed = finder.move_video_files(source_folder, output_folder, preserve)
            print(f"\nOperation completed: {len(moved)} moved, {len(failed)} failed")
        elif action == 'c':
            copied, failed = finder.copy_video_files(source_folder, output_folder, preserve)
            print(f"\nOperation completed: {len(copied)} copied, {len(failed)} failed")
        else:
            print("Invalid action selected.")

if __name__ == "__main__":
    main()