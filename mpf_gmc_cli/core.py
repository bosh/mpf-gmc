import os
import json
import shutil
import sys
import subprocess
import importlib.metadata

CONFIG_FILE = ".mpf-gmc"

def get_cli_version():
    """Dynamically reads package metadata version safely across running modes."""
    try:
        return importlib.metadata.version("mpf-gmc")
    except importlib.metadata.PackageNotFoundError:
        return "1.1.0-editable"

def get_mpf_version():
    """Reads the sibling MPF core package installation version."""
    try:
        return importlib.metadata.version("mpf")
    except importlib.metadata.PackageNotFoundError:
        return None

def load_config():
    """Reads the local project configuration authority file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"godot_path": None, "last_known_source_path": None, "install_mode": "symlink"}

def save_config(config_data):
    """Writes state to the local local project configuration authority file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)

def run_diagnostics():
    """Executes structural health checks against active directories."""
    print("=== MPF-GMC CLI Environment Status ===")
    print(f"CLI Tool Version: {get_cli_version()}")

    # Verify Core MPF Framework Core Pairing
    mpf_ver = get_mpf_version()
    if mpf_ver:
        print(f"Paired Core MPF Version: {mpf_ver}")
    else:
        print("Warning: Sibling core package 'mpf' not detected in active environment path.", file=sys.stderr)
    print()

    # Check directory validity
    if not os.path.exists("project.godot") and not os.path.exists("config"):
        print("Error: Command must be executed from an active game project root directory.", file=sys.stderr)
        return False
    print("Project Directory: Verified")

    # Check addon presence
    target_addon_dir = os.path.join("addons", "mpf-gmc")
    if os.path.islink(target_addon_dir):
        print(f"GMC Library Addon: Linked -> {os.readlink(target_addon_dir)}")
    elif os.path.exists(target_addon_dir):
        print("GMC Library Addon: Installed (Hard Copy Mode)")
    else:
        print("GMC Library Addon: Missing")

    # Check Godot execution mapping
    config = load_config()
    godot_bin = config.get("godot_path") or shutil.which("godot")
    if godot_bin:
        try:
            version_str = subprocess.check_output([godot_bin, "--version"]).decode("utf-8").strip()
            print(f"Godot Binary Found: {godot_bin} (v{version_str})")
        except Exception:
            print(f"Godot Binary Found: {godot_bin} (Execution failed/unresponsive)")
    else:
        print("Godot Binary: Not configured and not found in system PATH")
    return True

def initialize_gmc(source_addon_path, target_project_path, force_copy=False):
    """Deploys or links the embedded wheel core assets directly into the game workspace."""
    target_addon_dir = os.path.abspath(os.path.join(target_project_path, "addons", "mpf-gmc"))

    # Clear out older artifacts safely
    if os.path.islink(target_addon_dir) or os.path.exists(target_addon_dir):
        print("Cleaning old deployment assets at destination...")
        if os.path.islink(target_addon_dir):
            os.unlink(target_addon_dir)
        else:
            shutil.rmtree(target_addon_dir)

    os.makedirs(os.path.dirname(target_addon_dir), exist_ok=True)

    if force_copy:
        print("Deploying framework via hard copy mode...")
        shutil.copytree(source_addon_path, target_addon_dir)
        print("Deployment complete.")
        return

    try:
        print(f"Linking folder: {target_addon_dir} -> {source_addon_path}")
        os.symlink(source_addon_path, target_addon_dir, target_is_directory=True)
        print("\nInitialization complete via automated Symlink! Future PyPI updates will apply instantly.")
    except PermissionError:
        print("\n[Notice] Operating system rejected symlink creation due to profile privileges.")
        print("Falling back to full directory copy...")
        shutil.copytree(source_addon_path, target_addon_dir)
        print("Deployment completed via fallback file transfer.")

def verify_link_integrity(source_addon_path):
    """Verifies that physical directory link paths line up with current live system locations."""
    config = load_config()
    target_addon_dir = os.path.abspath(os.path.join("addons", "mpf-gmc"))

    if config.get("install_mode") == "copy" or not os.path.islink(target_addon_dir):
        return

    current_pointer = os.path.abspath(os.readlink(target_addon_dir))
    resolved_source = os.path.abspath(source_addon_path)

    if current_pointer != resolved_source:
        print("\n[GMC Symlink Source Mismatch Detected]")
        print(f" -> Project expected: {config.get('last_known_source_path')}")
        print(f" -> Current live tool source: {resolved_source}")

        response = input("\nYour python environment path has changed. Update the project symlink? [Y/n]: ").strip().lower()
        if response in ('', 'y', 'yes'):
            initialize_gmc(resolved_source, os.getcwd(), force_copy=False)
            config["last_known_source_path"] = resolved_source
            config["install_mode"] = "symlink"
            save_config(config)
            print("Project linkages healed successfully.")
        else:
            print("\nWarning: Continuing with a mismatched or broken asset path.")
