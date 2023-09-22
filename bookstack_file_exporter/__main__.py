import argparse
import logging
from typing import Dict, List, Union

from bookstack_file_exporter import run
from bookstack_file_exporter import run_args

def main():
    args: argparse.Namespace = run_args.get_args()

    logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s',
                    level=run_args.get_log_level(args.log_level), datefmt='%Y-%m-%d %H:%M:%S')
    
    run.exporter(args)


if __name__ == '__main__':
    main()