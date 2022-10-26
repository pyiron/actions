# pyiron_github
A centralized location for our GitHub actions to perform CI on python modules.
It includes both custom actions, which we strive to make reusable everywhere (but whose default values are optimized for our repositories), and custom reusable workflows that are tuned specifically for our other pyiron repositories.

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
```

By default, some of our actions add to the environment, e.g. `build-docs` uses the file `.support/environment-docs.yml` in this repository to add `nbsphinx` to the environment with the `standard-docs-env-file` input argument.
In these situations you can always add additional files to the environment in the `env-files` argument, or stop these "standard" modules from getting added by overriding these arguments with an empty string.

Similarly, other defaults like where the docs or notebooks directories are, or even where the final environment file resides can always be overriden for each action.


## Secrets

Some actions require secrets to work. 
You will need to pass these in as arguments, and they will first need to be added to your GitHub repository in the settings page.

Requirements:
- `<some action>`: `<some secret>`
