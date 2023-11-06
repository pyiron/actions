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
            name_mapping_file
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
        with open(name_mapping_file, 'r') as f:
            self._name_conversion_dict = json.load(f)

        with open(environment_file, 'r') as f:
            self.environment = yaml.safe_load(f)

        self.package_name = self._convert_package_name(package_name)

    def _convert_package_name(self, name):
        if name in self._name_conversion_dict.keys():
            result = self._name_conversion_dict[name]
        else:
            result = name
        return result

    def _update_dependencies(self):
        updated_dependencies = []

        for dep in self.environment['dependencies']:
            updated_dependencies.append(re.sub(
                r'(' + self.package_name + '.*)' + self.from_version,
                r'\g<1>' + self.to_version,
                dep
            ))

        self.environment['dependencies'] = updated_dependencies

    def _write(self):
        with open(environment_file, 'w') as f:
            yaml.safe_dump(self.environment, f)

    def update_dependencies(self):
        """Update the version of the requested dependency in the environment file"""
        self._update_dependencies()
        self._write()


def ends_in_yml(s):
    return s.endswith('.yml') or s.endswith('.yaml')


def pattern_is_bump_from_to(list_):
    if len(list_) < 10:
        return False
    return all(
        [
            list_[1] == 'Bump',
            list_[3] == 'from',
            list_[5] == 'to',
            ends_in_yml(list_[7])
        ]
    )


def pattern_is_update_requirement_from_to(list_):
    if len(list_) < 11:
        return False
    return all(
        [
            list_[1] == 'Update',
            list_[3] == 'requirement',
            list_[4] == 'from',
            list_[6] == 'to',
            ends_in_yml(list_[8])
        ]
    )


if pattern_is_bump_from_to(sys.argv):
    package_to_update = sys.argv[2]
    from_version = sys.argv[4]
    to_version = sys.argv[6]
    environment_files = sys.argv[7:-1]
    name_mapping_file = sys.argv[-1]
elif pattern_is_update_requirement_from_to(sys.argv):
    package_to_update = sys.argv[2]
    from_version = sys.argv[5]
    to_version = sys.argv[7]
    environment_files = sys.argv[8:-1]
    name_mapping_file = sys.argv[-1]
else:
    raise ValueError(f"Title of a dependabot PR 'Bump <package> from <version> to <version>' expected, "
                     f"but got {' '.join(sys.argv[1:])}")

for environment_file in environment_files:
    updater = EnvironmentUpdater(package_to_update, from_version, to_version, environment_file, name_mapping_file)
    updater.update_dependencies()
