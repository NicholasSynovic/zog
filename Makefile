build:
	git --no-pager tag | tail -n 1 | xargs -I % poetry version %
	poetry version --short > zog/_version
	poetry build
	pip install dist/*.tar.gz

create-dev:
	pre-commit install
	pre-commit autoupdate
	rm -rf env
	python3.13 -m venv env
	( \
		. env/bin/activate; \
		pip install -r requirements.txt; \
		poetry install; \
		deactivate; \
	)
