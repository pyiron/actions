"""
Merges an arbitrary number of conda environment yaml files and sends the merged result to stdout.
"""

import argparse
import sys

import yaml


def read_file(path):
    with open(path) as f:
        return yaml.safe_load(f)


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('env_files', nargs='*', help='Conda environment yaml files to merge')
    return parser.parse_args(argv)


def split_dependencies(env):
    plain = []
    pip = []
    for f in env:
        if isinstance(f, dict):
            if 'pip' not in f:
                raise ValueError("Unrecognized section {f} in environment file.")
            pip += f['pip']
        else:
            plain.append(f)
    def _split(deps):
        return {d.split()[0]: d for d in deps}
    return _split(plain), _split(pip)

def merge_dependencies(env_base, *envs):
    def _update(base, add):
        for k, v in add.items():
            if k not in base:
                base[k] = v
    base_dict, base_pip_dict = split_dependencies(env_base)
    for env_add in envs:
        add_dict, add_pip_dict = split_dependencies(env_add)
        _update(base_dict, add_dict)
        _update(base_pip_dict, add_pip_dict)
    deps = list(base_dict.values())
    if base_pip_dict:
        deps.append(
                {'pip': list(base_pip_dict.values())}
        )
    return deps


def merge_channels(env_base, *envs):
    for env_add in envs:
        for c in env_add:
            if c not in env_base:
                env_base.append(c)
    return env_base


def merge_env(env_base, *envs):
    return {
        "channels": merge_channels(
            env_base['channels'],
            *[env_add['channels'] for env_add in envs]
        ),
        'dependencies': merge_dependencies(
            env_base['dependencies'],
            *[env_add['dependencies'] for env_add in envs]
        )
    }


if __name__ == '__main__':
    arguments = parse_args(argv=None)
    if len(arguments.env_files) == 0:
        raise ValueError("Expected at least one environment file.")
    yaml.dump(
        merge_env(
            read_file(arguments.env_files[0]),
            *[read_file(env_add) for env_add in arguments.env_files[1:]]
        ),
        sys.stdout, 
        indent=2, 
        default_flow_style=False
    )
