# coding: utf-8
# Copyright (c) Max-Planck-Institut für Eisenforschung GmbH - Computational Materials Design (CM) Department
# Distributed under the terms of "New BSD License", see the LICENSE file.

import json
import re
import sys

import yaml


class EnvironmentUpdater:
    def __init__(
        self,
        package_name,
        from_version,
        to_version,
        environment_file,
        name_mapping_file,
    ):
        """
        Updates the version of a package in the conda environment file.

        Parameters:
            package_name: Name of the package to update as available on PyPI
            from_version: Version the package is before the update
            to_version: Version to which the package should be updated
            environment_file: The file to update
            name_mapping_file: A JSon file with the renaming map
        """
        self.from_version = from_version
        self.to_version = to_version
        with open(name_mapping_file, "r") as f:
            self._name_conversion_dict = json.load(f)

        with open(environment_file, "r") as f:
            self.environment = yaml.safe_load(f)

        is_pip_package = False
        for dep in self.environment["dependencies"]:
            if isinstance(dep, dict) and "pip" in dep:
                is_pip_package = any(
                    pip_dep.startswith(package_name) for pip_dep in dep["pip"]
                )
        if not is_pip_package:
            self.package_name = self._convert_package_name(package_name)

    def _convert_package_name(self, name):
        if name in self._name_conversion_dict.keys():
            result = self._name_conversion_dict[name]
        else:
            result = name
        return result

    def _update_dependencies(self):
        updated_dependencies = []

        def bump_version(dep):
            return re.sub(
                r"(" + self.package_name + ".*)" + self.from_version,
                r"\g<1>" + self.to_version,
                dep,
            )

        for dep in self.environment["dependencies"]:
            if isinstance(dep, str):
                updated_dependencies.append(bump_version(dep))
            # in case the env file has a pip section, it will end up here as a
            # dict
            elif isinstance(dep, dict) and "pip" in dep:
                pip = dep["pip"]
                dep["pip"] = [bump_version(pip_dep) for pip_dep in pip]
                updated_dependencies.append(dep)
            else:
                assert False, f"depencies should always be str/dict, not {dep}"

        self.environment["dependencies"] = updated_dependencies

    def _write(self):
        with open(environment_file, "w") as f:
            yaml.safe_dump(self.environment, f)

    def update_dependencies(self):
        """Update the version of the requested dependency in the environment file"""
        self._update_dependencies()
        self._write()


def ends_in_yml(s):
    return s.endswith(".yml") or s.endswith(".yaml")


# Dependabot may put a commit-message prefix such as "build(deps): " before the
# (then lower-case) verb, so anything before the verb is accepted
TITLE_PATTERNS = (
    # "bump" PR titles take the form "bump PKG from V1 to V2"
    re.compile(r"(?:.*\s)?bump\s+(\S+)\s+from\s+(\S+)\s+to\s+(\S+)", re.IGNORECASE),
    # "update" PR titles take the form "update PKG requirement from V1 to V2"
    re.compile(
        r"(?:.*\s)?update\s+(\S+)\s+requirement\s+from\s+(\S+)\s+to\s+(\S+)",
        re.IGNORECASE,
    ),
)


def parse_title(title):
    for pattern in TITLE_PATTERNS:
        match = pattern.fullmatch(title)
        if match is not None:
            return match.groups()
    raise ValueError(
        "Title of a dependabot PR '[<prefix>] Bump <package> from <version> to "
        "<version>' or '[<prefix>] Update <package> requirement from <version> to "
        f"<version>' expected, but got {title!r}"
    )


if len(sys.argv) < 4 or not all(ends_in_yml(f) for f in sys.argv[2:-1]):
    raise ValueError(
        "Expected a PR title, environment file(s) and a name mapping file, "
        f"but got {sys.argv[1:]}"
    )
package_to_update, from_version, to_version = parse_title(sys.argv[1])
environment_files = sys.argv[2:-1]
name_mapping_file = sys.argv[-1]

for environment_file in environment_files:
    updater = EnvironmentUpdater(
        package_to_update, from_version, to_version, environment_file, name_mapping_file
    )
    updater.update_dependencies()
