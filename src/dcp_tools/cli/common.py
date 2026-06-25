import argparse

from dcp_tools.gcp_utilities import KGSettings, get_kg_settings


def load_settings_from_args(args: argparse.Namespace) -> KGSettings:
    if args.settings_file:
        return get_kg_settings(source="json", file=args.settings_file)
    return get_kg_settings(env_file=args.env_file)
