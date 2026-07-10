# ✨ panel-openapi

[![CI](https://img.shields.io/github/actions/workflow/status/panel-extensions/panel-openapi/ci.yml?style=flat-square&branch=main)](https://github.com/panel-extensions/panel-openapi/actions/workflows/ci.yml)
[![conda-forge](https://img.shields.io/conda/vn/conda-forge/panel-openapi?logoColor=white&logo=conda-forge&style=flat-square)](https://prefix.dev/channels/conda-forge/packages/panel-openapi)
[![pypi-version](https://img.shields.io/pypi/v/panel-openapi.svg?logo=pypi&logoColor=white&style=flat-square)](https://pypi.org/project/panel-openapi)
[![python-version](https://img.shields.io/pypi/pyversions/panel-openapi?logoColor=white&logo=python&style=flat-square)](https://pypi.org/project/panel-openapi)


Panel extension to auto-generate Forms from OpenAPI schemas.

## Features

panel-openapi

## Pin your version!

This project is **in its early stages**, so if you find a version that suits your needs, it’s recommended to **pin your version**, as updates may introduce changes.

## Installation

Install it via `pip`:

```bash
pip install panel-openapi
```

## Usage

```python
import panel_openapi
```

## Development

```bash
git clone https://github.com/panel-extensions/panel-openapi
cd panel-openapi
```

For a simple setup use [`uv`](https://docs.astral.sh/uv/):

```bash
uv venv
source .venv/bin/activate # on linux. Similar commands for windows and osx
uv pip install -e .[dev]
pre-commit run install
pytest tests
```

For the full Github Actions setup use [pixi](https://pixi.sh):

```bash
pixi run pre-commit-install
pixi run postinstall
pixi run test
```

This repository is based on [copier-template-panel-extension](https://github.com/panel-extensions/copier-template-panel-extension) (you can create your own Panel extension with it)!

To update to the latest template version run:

```bash
pixi exec --spec copier --spec ruamel.yaml -- copier update --defaults --trust
```

Note: `copier` will show `Conflict` for files with manual changes during an update. This is normal. As long as there are no merge conflict markers, all patches applied cleanly.

## ❤️ Contributing

Contributions are welcome! Please follow these steps to contribute:

1. Fork the repository.
2. Create a new branch: `git checkout -b feature/YourFeature`.
3. Make your changes and commit them: `git commit -m 'Add some feature'`.
4. Push to the branch: `git push origin feature/YourFeature`.
5. Open a pull request.

Please ensure your code adheres to the project's coding standards and passes all tests.
