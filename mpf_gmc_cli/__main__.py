import argparse
import sys
import os
import shutil
import subprocess
from importlib.resources import files
from .core import load_config, save_config, initialize_gmc, run_diagnostics, verify_link_integrity

def main():
    parser = argparse.ArgumentParser(
        prog="mpf-gmc",
        description="Management CLI and component engine for the Mission Pinball Framework Godot Media Controller (GMC).",
        epilog="Run 'mpf-gmc' (no arguments) for health check, paths, and version info, and symlink integrity.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", metavar="{init,config,run}")

    init_parser = subparsers.add_parser(
        "init",
        help="Link or copy GMC framework into your game directory. HELP",
        description="Link or copy GMC framework into your game directory. DESC",
        epilog="Note: 'init' linking creates a symbolic link pointing into your active Python package environment. You may need to relink after updating versions.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    init_parser.add_argument("--copy", "-c", action="store_true", help="Hard copy the addon code into your project instead of symlinking. This is harder to upgrade over time.")
    init_parser.add_argument("--force", "-f", action="store_true", help="Wipe and overwrite any existing assets or links at the target path, to perform a clean repair or upgrade.")

    config_parser = subparsers.add_parser(
        "config",
        help="Read or modify variables inside the local project configuration file.",
        description="Read or modify variables inside the local project configuration file.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    config_parser.add_argument("--godot", "-g", metavar="PATH", help="Manually specify and save the absolute path to your local 'godot' engine binary executable.")

    subparsers.add_parser(
        "run",
        help="Launch the Godot graphical front-end application.",
        description="Triggers process execution for testing and framework launching.",
        epilog="Note: If no arguments are passed, 'run' defaults to securely launching just the standalone Godot application targeted specifically at the local directory root.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    args = parser.parse_args()

    try:
        source_addon_path = os.path.abspath(
            str(files("mpf_gmc_cli").joinpath("../../addons/mpf-gmc").resolve())
        )
    except Exception as e:
        print(f"Fatal Error locating internal wheel assets: {e}", file=sys.stderr)
        sys.exit(1)

    if not args.command:
        if not run_diagnostics():
            sys.exit(1)
        if sys.stdin.isatty():
            verify_link_integrity(source_addon_path)
        else:
            print("[Headless Guard] Non-interactive environment context. Path validation skipped.")
        sys.exit(0)

    if args.command == "init":
        force_copy = args.copy
        initialize_gmc(source_addon_path, os.getcwd(), force_copy=force_copy)
        config = load_config()
        config["last_known_source_path"] = source_addon_path
        config["install_mode"] = "copy" if force_copy else "symlink"
        save_config(config)

    elif args.command == "config":
        config = load_config()
        if args.godot:
            config["godot_path"] = os.path.abspath(args.godot)
            save_config(config)
            print(f"Config successfully written: godot_path -> {config['godot_path']}")
        else:
            print(f"Current Environment Configuration File ({os.path.abspath(CONFIG_FILE)}):")
            for key, val in config.items():
                print(f"  {key}: {val}")

    elif args.command == "run":
        config = load_config()
        godot_bin = config.get("godot_path") or shutil.which("godot")
        if not godot_bin:
            print("Error: Godot executable path could not be resolved.", file=sys.stderr)
            print("Please configure manually: mpf-gmc config --godot /path/to/godot", file=sys.stderr)
            sys.exit(1)

        print(f"Spawning async graphical interface via: {godot_bin} ...")
        try:
            subprocess.Popen([godot_bin], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"Execution Error: Subprocess failed to initialize engine: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
