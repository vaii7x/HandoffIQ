"""
Entry point for the calculator application.
"""

from calculator.cli import run_cli

if __name__ == "__main__":
    try:
        run_cli()
    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting...")
