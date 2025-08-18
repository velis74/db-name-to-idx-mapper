#!/usr/bin/env python3
"""
Database name to index mapper - CLI interface
"""

import argparse
import subprocess
import sys

from .db_name_to_idx_mapper import DbNameToIdxMapper
from .config_path import resolve_config_path, get_help_text

def main():
    from . import __version__

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
    parser.add_argument(
        "--version",
        help="Prints version information and exits.",
        action="version",
        version=__version__
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

    # exec command
    exec_parser = subparsers.add_parser(
        "exec",
        help="Execute utility with mapped database index. if an incomplete db name is given (prefix), runs command for "
             "all databases matching the prefix (see list-mappings)",
    )
    exec_parser.add_argument("utility_name", help="Utility name (e.g., redis-cli)")
    exec_parser.add_argument("args", nargs=argparse.REMAINDER, help="Utility arguments")

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

        elif args.command == "exec":
            db_param = mapper.get_utility_db_param(args.utility_name)

            # Find and replace database parameter
            new_args = []
            mappings = [0]
            db_param_index = None
            i = 0
            while i < len(args.args):
                if args.args[i] == db_param and i + 1 < len(args.args):
                    # Found database parameter, map the next argument
                    mappings = [mapping["index"] for mapping in mapper.list_mappings(args.args[i + 1])]
                    new_args.extend([db_param, ""])
                    db_param_index = len(new_args) - 1
                    if not mappings:
                        mappings = [args.args[i + 1]]
                    i += 2
                else:
                    new_args.append(args.args[i])
                    i += 1

            for mapping in mappings:
                if db_param_index is not None:
                    new_args[db_param_index] = mapping
                subprocess.run([args.utility_name] + new_args)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
