"""
The intent of this script is to allow a fixed-dependency (`==`) pyproject.toml file
to be modified to use bound dependencies (`>=` and `<`) on-the-fly to make releasing
to PyPi as powerful and painless as possible.

Explicit upper and lower bounds can be passed as yaml environment files, but otherwise
any semantic versions (cf. :func:`is_semantic`) get their lower bound set as the input
file, and their upper bound can be controlled by a flag ranging from pinning the exact
patch, to the minor or major version, or no upper limit at all. Any other format for
the version will just get pinned exactly (of course you can always work around this by
manually specifying other bounds in the upper/lower environment files).

Args:
    input_toml (str): The toml input toml file; must have field `project.dependencies`,
        and dependencies are expected to all be in the form `{NAME}=={VERSION}`. I.e.
        a pyproject.toml file with strictly pinned dependencies.
        (Default is "pyproject.toml")
    lower_bound_yaml (str): A yaml file with the field `dependencies` specified in the
        format `{NAME} ={VERSION}`. This is optional, but if provided, these versions
        will be used as the (inclusive) lower bound wherever `{NAME}` matches a package
        `{NAME}` in the input toml. Ignored if `"none"` (actual string, not python
        `None`). (Default is "none", use `input_toml` version as lower bound.)
    upper_bound_yaml (str): A yaml file with the field `dependencies` specified in the
        format `{NAME} ={VERSION}`. This is optional, but if provided, these versions
        will be used as the (exclusive) upper bound wherever `{NAME}` matches a package
        `{NAME}` in the input toml. Ignored if `"none"` (actual string, not python
        `None`). (Default is "none", use `semantic_upper_bound` criteria or pin to
        `input_toml` values.)
    semantic_upper_bound ("patch"|"minor"|"major"|"none"): How strictly to pin the
        upper bound relative to the input version if no explicit bound was provided by
        `upper_bound_yaml`. "patch" gives an upper bound "<=" the input version;
        "minor" and "major" give "<" bounds to Z.Y+1.0 and Z+1.0.0, respectively;
        "none" gives no uppoer bound.
    always_pin_unstable ("yes"|"no"): Whether or not to override non-`"none"`
        `semantic_upper_bound` and always pin unstable dependencies (0.Y.Z) all the way
        down to the patch level. (Default is "yes".)
    output_toml (str): Where to write the updated toml file -- all the same content as
        the input, but with dependency versions modified (and possible reformatted,
        since we just use `toml.dump`). If `"none"` (actual string, not python `None`),
        the input file variable is used and that file gets overwritten. (Default is
        "none", use the same value as `input_toml`)
    pypi_to_conda_name_map_file (str): A JSON file containing any necessary map between
        pypi package names in the toml file(s) and conda package names used in the
        yaml environment files. Any toml dependency found as a key in the map file will
        be converted to its value before searching for it in either of the yaml files.
        (Default is "none", don't load a file or do any conversions.)
"""

import argparse
import json

import toml
import yaml


def write_updated_toml(
    input_toml: str,
    lower_bound_yaml: str,
    upper_bound_yaml: str,
    semantic_upper_bound: str,
    always_pin_unstable: str,
    output_toml: str,
    pypi_to_conda_name_map_file: str
) -> None:

    with open(input_toml, "r") as file:
        data = toml.load(file)

    lower_bound_data = load_yaml(lower_bound_yaml)
    upper_bound_data = load_yaml(upper_bound_yaml)

    if pypi_to_conda_name_map_file != "none":
        with open(pypi_to_conda_name_map_file, "r") as f:
            pypi_to_conda_map = json.load(f)

    semantic_upper_bound = (
        None if semantic_upper_bound == "none" else semantic_upper_bound
    )

    if always_pin_unstable == "yes":
        always_pin_unstable = True
    elif always_pin_unstable == "no":
        always_pin_unstable = False
    else:
        raise ValueError(
            f"Expected 'yes' or 'no' for always_pin_unstable but got "
            f"{always_pin_unstable}"
        )

    dependencies = data["project"]["dependencies"]

    for i, dependency in enumerate(dependencies):
        package, version = split_dependency(dependency, "==")

        dependencies[i] = update_dependency(
            package,
            version,
            lower_bound_data,
            upper_bound_data,
            semantic_upper_bound,
            always_pin_unstable,
            pypi_to_conda_map,
        )

    with open(input_toml if output_toml == "none" else output_toml, "w") as file:
        toml.dump(data, file)


def load_yaml(yaml_file: str) -> dict:
    if yaml_file == "none":
        return {}
    else:
        with open(yaml_file, "r") as file:
            data = yaml.safe_load(file)

    yaml_bounds = {}
    for dependency in data["dependencies"]:
        package, version = split_dependency(dependency, "=", allow_no_version=True)
        yaml_bounds[package] = version
    return yaml_bounds


def split_dependency(
    dependency: str, delimiter: str, allow_no_version: bool = False
) -> tuple[str, str]:
    split = dependency.replace(" ", "").split(delimiter)
    if len(split) != 2:
        if len(split) == 1 and allow_no_version:
            return split[0], None
        else:
            raise ValueError(
                f"Expected input dependencies to take the form `PACKAGE{delimiter}VERSION` "
                f"but got {dependency}"
            )
    return split[0], split[1]


def update_dependency(
    package_name: str,
    input_version: str,
    lower_bound_data: dict[str, str],
    upper_bound_data: dict[str, str],
    semantic_upper_bound: str | None,
    always_pin_unstable: bool,
    pypi_to_conda_map: dict[str, str]
):
    explicit_lower_bound = get_explicit_bound(
        lower_bound_data,
        package_name,
        pypi_to_conda_map
    )
    explicit_upper_bound = get_explicit_bound(
        upper_bound_data,
        package_name,
        pypi_to_conda_map
    )

    lower_bound = (
        input_version if explicit_lower_bound is None else explicit_lower_bound
    )

    if explicit_upper_bound is None:
        bound_type, upper_bound = get_semantic_upper_bound(
            input_version,
            semantic_upper_bound,
            always_pin_unstable
        )
    else:
        bound_type, upper_bound = "<", explicit_upper_bound

    if upper_bound == lower_bound:
        return f"{package_name}=={lower_bound}"
    else:
        return f"{package_name}>={lower_bound},{bound_type}{upper_bound}"


def get_explicit_bound(
    yaml_data: dict[str, str],
    package_name: str,
    pypi_to_conda_map: dict[str, str]
) -> str | None:
    try:
        conda_package_name = pypi_to_conda_map[package_name]
    except KeyError:
        conda_package_name = package_name

    try:
        return yaml_data[conda_package_name]
    except KeyError:
        # If it's not there, that's fine
        return None


def get_semantic_upper_bound(
    input_version: str,
    semantic_upper_bound: str | None,
    always_pin_unstable: bool
) -> tuple[str, str]:
    if not is_semantic(input_version):
        # Just short-circuit return the input if we can't parse it semantically
        return "<=", input_version

    z, y, x = input_version.split(".")
    if semantic_upper_bound is not None and z == "0" and always_pin_unstable:
        return "<=", input_version

    if semantic_upper_bound == "patch":
        return "<=", input_version
    elif semantic_upper_bound == "minor":
        return "<", f"{z}.{int(y) + 1}.0"
    elif semantic_upper_bound == "major":
        return "<", f"{int(z) + 1}.0.0"
    elif semantic_upper_bound is None:
        return "", ""
    else:
        raise ValueError(
            f"Expected the semantic_upper_bound to be in "
            f"['patch', 'major', 'minor', None] but got {semantic_upper_bound}"
        )


def is_semantic(version: str):
    """
    Anything in the format `{integer}.{integer}.{whatever}` will pass.

    This is not quite as strict as [the official definition](https://semver.org/), but
    is a pretty good proxy.
    """
    split = version.split(".")
    return len(split) == 3 and split[0].isdigit() and split[1].isdigit()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Update dependency versions in a pyproject.toml file."
    )
    parser.add_argument(
        "--input_toml",
        type=str,
        default="pyproject.toml",
        help="Input TOML file with `project.dependencies` and `==` pinned dependencies."
    )
    parser.add_argument(
        "--lower_bound_yaml",
        type=str,
        default="none",
        help="Optional YAML conda environment file with lower bounds for select "
             "dependencies."
    )
    parser.add_argument(
        "--upper_bound_yaml",
        type=str,
        default="none",
        help="Optional YAML conda environment file with upper bounds for select "
             "dependencies."
    )
    parser.add_argument(
        "--semantic_upper_bound",
        choices=["patch", "minor", "major", "none"],
        default="minor",
        help="Upper bound policy for semantically versioned dependencies."
    )
    parser.add_argument(
        "--always_pin_unstable",
        choices=["yes", "no"],
        default="yes",
        help="Whether to always pin unstable dependencies (0.Y.Z) all the way to patch."
    )
    parser.add_argument(
        "--output_toml",
        type=str,
        default="none",
        help="Optional output destination for toml with updated dependency versions."
    )
    parser.add_argument(
        "--pypi_to_conda_name_map_file",
        type=str,
        default="none",
        help="Optional JSON file to remap pypi package names in the toml file(s) to "
             "conda package names in the yaml file(s)."
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    write_updated_toml(
        args.input_toml,
        args.lower_bound_yaml,
        args.upper_bound_yaml,
        args.semantic_upper_bound,
        args.always_pin_unstable,
        args.output_toml,
        args.pypi_to_conda_name_map_file
    )
