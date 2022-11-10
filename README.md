# pyiron actions
A centralized location for our GitHub actions to perform CI on python modules.
It includes both custom actions, which we strive to make reusable everywhere (but whose default values are optimized for our repositories), and custom reusable workflows that are tuned specifically for our other pyiron repositories.

Note that for both security (i.e. use in pr-target triggered workflows) and flexibility, none of the actions call `actions/checkout`.
You will need to do this yourself in the calling workflow in order for these actions to be productive.

## The Actions

### `build-docs`

Combines your code's environment file with a separate environment file for building documentation (`.support/environment-docs.yml` from this repo by default) and uses [sphinx](https://www.sphinx-doc.org) to build a set of HTML documentation.

These docs wind up getting discarded when the virtual machine (VM) for your job shuts down, so the purpose of this action is to make sure that an external builder, e.g. [readthedocs](https://readthedocs.org) will also succeed.

### `build-notebooks`

Uses [papermill](https://papermill.readthedocs.io) to make sure that selected notebooks in your repository build and execute OK.
You can exclude a notebook from this check by naming it in an exclusion file (this is empty by default, but for repos inside the pyiron organization using the workflow here that calls this action, the default location is `.ci_support/exclude`)

### `cached-mamba`

Probably one of our most generically useful actions: it uses any number (>=1) of conda environment yaml files to build a cached conda environment with mambaforge.

### `pip-check`

Builds your environment with the `cached-mamba` action and then runs `pip check`.

### `pyiron-config`

Necessary only if you plan to execute pyiron code -- perhaps as part of a `build-notebooks` call.
It configures the pyiron environment for the VM. 

### `unit-tests`

Uses [coverage](https://coverage.readthedocs.io/) to run python's `unittest`.

For pyiron repos, more detailed [coveralls](https://coveralls.io) and [codacy](https://www.codacy.com) reports are generated in the same job that calls this action over in our reusable workflows.
However, those elements require secrets and these actions are secret-free, so if you're not operating inside the pyiron organization you'll need to set that part up yourself.

### `update-env-files`

Updates the environment file based on patterns in the PR title.
Intended to be used in conjuction with [Dependabot](https://github.com/dependabot).

### `write-docs-env`

Combines your environment file(s) and an additional environment file(s) and writes them, by default, to `docs/environment.yaml`.
Intended to be committed to the repo and later read by, e.g., readthedocs.

### `write-environment`

Another extremely versatile action: merges an arbitrary number of conda environment yaml files and writes them to a single `environment.yml`.

Smartly handles multiple channels and avoids duplicate dependencies, but doesn't do any environment pre-solving, so don't expect it to save you from incompatible version demands or anything like that.
Still, extremely useful for common use cases like adding `nbsphinx` to your environment before building docs, etc.

## Expected repository structure and defaults

To make full use of default values with these actions, your repository should have the following structure:

```
your_module/
|-- .ci_support/
|     |-- environment.yml  # The conda environment file for your module
|-- docs/  # Necessary files for sphinx to built HTML documentation
|     |-- conf.py
|     |-- index.rst
|-- !environment.yml  # You MUST NOT have 'environment.yml' in your repo root -- our actions write to this location
|-- tests/  # The directory containing your test files
|     |-- benchmark/  # A total test suite under a time limit
|     |-- unit/  # To run on a variety of systems 
|-- your_module/  # The directory for your python module
|     |-- _version.py  # We will assume you are using versioneer and will ignore this when calculating coverage
```

By default, some of our actions add to the environment, e.g. `build-docs` uses the file `.support/environment-docs.yml` in this repository to add `nbsphinx` to the environment with the `standard-docs-env-file` input argument.
In these situations you can always add additional files to the environment in the `env-files` argument, or stop these "standard" modules from getting added by overriding these arguments with an empty string.

Similarly, other defaults like where the docs or notebooks directories are, or even where the final environment file resides can always be overriden for each action.

## Workflows (pyiron-organization specific)

Unlike the actions, reusable workflows in the `.github/workflows` directory enforce expectations about repository structure and lean heavily on the default values.
Some properties, such as which env files to use, are still exposed, although in most cases you can continue to rely on the default values.

These workflows are (mostly) named based on the expected `on` values for triggering the workflow and ought to be applicable to any pyiron module.

Further, various workflows rely on the following repository secrets, all of which are organization wide inside the pyiron group (or generated by GitHub by default), but you'll need to specify them to use these workflows outside pyiron:
- `CODACY_PROJECT_TOKEN` (Organization-wide)
- `DEPENDABOT_WORKFLOW_TOKEN` (Organization-wide)
- `PYPI_PASSWORD` (Organization-wide)
- `GITHUB_TOKEN` (Don't worry about this, GitHub will produce it automatically)

Thankfully, if you're running these workflows for a pyiron-organization module, all you need to do in your calling workflow is set `secrets: inherit`.

Putting it all together, we get caller scripts that look like this:

```yaml
# This runs jobs which pyiron modules should run on pushes or PRs to main

name: Push-Pull-main

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  pyiron:
    uses: pyiron/actions/.github/workflows/push-pull-main.yml@main
    secrets: inherit
```
