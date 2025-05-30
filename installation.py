import os
import subprocess


def install_packages(requirements_file):
    """Install packages from the requirements file."""
    try:
        print(f"Reading packages from '{requirements_file}'...")
        with open(requirements_file, "r") as file:
            packages = file.read().splitlines()

        for package in packages:
            if package.strip():  # Skip empty lines
                print(f"Installing package: {package}...")
                subprocess.run(["pip", "install", package], check=True)
                print(f"Package '{package}' installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing package: {e}")
        exit(1)
    except FileNotFoundError:
        print(f"Error: '{requirements_file}' not found.")
        exit(1)

def run_db_creation_script(db_creation_script):
    """Run the dbCreation.py script."""
    try:
        print(f"Running database creation script '{db_creation_script}'...")
        subprocess.run(["python", db_creation_script], check=True)
        print("Database creation script executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running database creation script: {e}")
        exit(1)



if __name__ == "__main__":
    REQUIREMENTS_FILE = "packages.txt"
    DB_CREATION_SCRIPT = "DB/dbCreation.py"
    

    # Check if packages.txt exists
    if not os.path.exists(REQUIREMENTS_FILE):
        print(f"Error: '{REQUIREMENTS_FILE}' not found in the root directory.")
        exit(1)

    # Check if dbCreation.py exists
    if not os.path.exists(DB_CREATION_SCRIPT):
        print(f"Error: '{DB_CREATION_SCRIPT}' not found in the specified directory.")
        exit(1)

   

    # Install packages
    install_packages(REQUIREMENTS_FILE)

    # Run the database creation script
    run_db_creation_script(DB_CREATION_SCRIPT)

   