import argparse
import sys
from orders.extract import extract
from orders.transform import transform
from orders import api

def main():
    """ Main function"""

    parser = argparse.ArgumentParser(description="ETL Pipeline for order data")
    sub = parser.add_subparsers(dest="command")

    load_cmd = sub.add_parser("load", help="Extract, transform, and load CSV data")
    load_cmd.add_argument("filepath", help="Path to the CSV file")

    args = parser.parse_args()

    if args.command == "load":
        df = extract(args.filepath)
        df = transform(df)
        api.save_orders(df)
        print(f"Loaded {len(df)} rows into SQLite.")
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
