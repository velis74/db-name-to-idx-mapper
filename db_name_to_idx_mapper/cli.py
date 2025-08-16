#!/usr/bin/env python3
"""
Database name to index mapper - CLI interface
"""

import argparse
import sys
from .db_name_to_idx_mapper import DbNameToIdxMapper
from .config_path import resolve_config_path, get_help_text

def main():
    parser = argparse.ArgumentParser(
        description="Database name to index mapper",
        prog="db-name-to-idx-mapper",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--config-path",
        default="{CONFIG}/db-name-to-idx-mapper/config.json",
        help=get_help_text(),
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # add-mapping command
    add_parser = subparsers.add_parser("add-mapping", help="Add new mapping")
    add_parser.add_argument("name", help="Database name to map")

    # ensure-mapping command
    ensure_parser = subparsers.add_parser("ensure-mapping", help="Ensure mapping exists")
    ensure_parser.add_argument("name", help="Database name to map")

    # map command
    map_parser = subparsers.add_parser("map", help="Get index for name")
    map_parser.add_argument("name", help="Database name to look up")

    # list-mappings command
    list_parser = subparsers.add_parser("list-mappings", help="List all mappings")
    list_parser.add_argument("prefix", nargs="?", help="Optional prefix filter")

    # get the maximum mapped  database index
    max_parser = subparsers.add_parser(
        "get-max-index",
        help="Get highest mapping index (number of databases needed - 1)",
    )

    # add-utility-db-param-map command
    add_util_parser = subparsers.add_parser(
        "add-utility-db-param-map",
        help="Add utility parameter mapping"
    )
    add_util_parser.add_argument("utility_name", help="Utility name")
    add_util_parser.add_argument("param_name", help="Parameter name")

    # get-utility-db-param command
    get_util_parser = subparsers.add_parser(
        "get-utility-db-param",
        help="Get utility parameter name"
    )
    get_util_parser.add_argument("utility_name", help="Utility name")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    resolved_config_path = resolve_config_path(args.config_path)
    mapper = DbNameToIdxMapper(config_file=resolved_config_path)

    try:
        if args.command == "add-mapping":
            result = mapper.add_mapping(args.name)
            print(result)  # stdout: just the index
            print(f"Added mapping: {args.name} -> {result}", file=sys.stderr)

        elif args.command == "ensure-mapping":
            result = mapper.ensure_mapping(args.name)
            print(result.index)  # stdout: just the index
            print(
                f"{'Added' if result.created else 'Used existing'} mapping: {args.name} -> {result.index}",
                file=sys.stderr
            )

        elif args.command == "map":
            result = mapper.map(args.name)
            print(result)  # stdout: just the index

        elif args.command == "list-mappings":
            result = mapper.list_mappings(args.prefix)
            for mapping in result:
                print(f"{mapping['name']}:{mapping['index']}")
            if args.prefix:
                print(f"Listed {len(result)} mappings with prefix '{args.prefix}'", file=sys.stderr)
            else:
                print(f"Listed {len(result)} mappings", file=sys.stderr)

        elif args.command == "get-max-index":
            result = mapper.get_max_mapping_index()
            print(result)  # stdout: just the max index

        elif args.command == "add-utility-db-param-map":
            mapper.add_utility_db_param_map(args.utility_name, args.param_name)
            print("OK")  # stdout: confirmation
            print(f"Added utility mapping: {args.utility_name} -> {args.param_name}", file=sys.stderr)

        elif args.command == "get-utility-db-param":
            result = mapper.get_utility_db_param(args.utility_name)
            print(result)  # stdout: just the parameter name

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
