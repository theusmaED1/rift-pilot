"""Entry point: `python -m rift_pilot` abre a GUI."""
import logging
import sys

from rift_pilot.presentation.gui import run_app

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('rift_pilot.log', encoding='utf-8'),
    ],
)

if __name__ == "__main__":
    run_app()
