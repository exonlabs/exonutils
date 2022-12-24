.PHONY: clean clean-dist clean-dev clean-all \
	setup-dev build release


clean:
	@rm -rf build/ build_src/
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -type f -name '*.pyc' -exec rm -f {} +

clean-dist:
	@rm -rf dist/

clean-dev: clean
	@find . -type d -name '*.egg-info' -exec rm -rf {} +
	@find . -type d -name '*.dist-info' -exec rm -rf {} +

clean-all: clean-dev clean-dist

setup-dev: clean-dev
	@bash scripts/setup_dev.sh

build: clean
	@bash scripts/build.sh

release: clean
	@bash scripts/release.sh

pip-update:
	pip install -U pip $$(pip freeze |grep -v '-e ' |cut -d'=' -f1 |xargs)
