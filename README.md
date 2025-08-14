# Grapheus the Scribe

## Use the Quickstart to start backend & frontend

## With Docker, preferred
For Linux/MacOS, be careful with the `.env` files being used:
> - Create network if starting for the first time using `make create-network`
> - Create volume if starting for the first time using `make create-volume`
> - From the root directory run `make start-services` & `make stop-services` to start & stop common services
> - From the root directory run `make start-dev-application` & `make stop-dev-application` to start the application backend & frontend respectively

For Windows, be careful with the `.env` files being used:
> - From the root directory run `docker compose --project-name bot_main -f docker-compose-main.yml up -d --build` & `docker compose --project-name bot_main -f docker-compose-main.yml down` to start & stop the application backend & frontend respectively
> - From the root directory run `docker compose --project-name bot_main -f docker-compose-service.yml up -d --build` & `docker compose --project-name bot_main -f docker-compose-service.yml down` to start & stop common services


**_NOTE : Running `make clean-docker-cache` or `docker buildx prune -a` & `docker builder prune -a` allows your system to be cleaned time to time_**

## With Local resources
>- Create a virtual environment using conda or venv or pipenv, for venv use `python3 -m venv myenv`
>- Activate the virtual environment using `source path/to/venv/myenv/bin/activate` for Linux/macOS & `path\to\venv\Scripts\activate` for Windows

For Linux/MacOS:
> - From the root directory run `make run-application-backend` to start application backend local
> - From the root directory run `make run-application-frontend` to start application frontend

For Windows:
> - Navigate to `./bot_service/src/backend` & install all the dependencies using `pip3 install -r requirements.txt -U`
> - From the same directory use `python3 main.py -e  "./path/to/.env/file"`
to start application backend
> -  Navigate to `./bot_service/src/frontend` & install all the dependencies using `npm install`
> - From the same directory use `npm start`


## Reading the docs locally:
>   For Linux/MacOS:
>   - From root dir run `make docs` & `make deploy-docs` to serve & deploy docs repectively
>
>   For Windows
>   - Use `pip3 install mkdocs-material` to install mkdocs
>   - Use `python3 -m mkdocs serve -a localhost:8001` to start serving documentation locally
>   - Use `mkdocs gh-deploy --force` to deploy the docs to GitHub pages

## Running code quality tools:
>   For Linux/MacOS:
>   - From root dir run `make pre-commit` to run & install pre-commit hooks respectively
>
>   For Windows
>   - Use `pip3 install pre-commit` to install pre-commit hooks & navigate to `./bot_service/`
>   - Use `pre-commit install` & go ahead with regular git workflow upon which these rules will now be run automatically whenever code is committed or use `pre-commit run -a` to run them manually


## Running data migration using alembic:
>  - From root dir run `make add-alembic-revision` 
>
>   OR
> - Keep db migration update to date, navigate to `./bot_service/src/backend` and `alembic revision --autogenerate  -m "Done some foo bar changes in db"`
> - Use `alembic upgrade head` before conscutive application start to keep db schema updated
> - Make sure that every model's base is referenced in `./bot_service/src/backend/alembic/env.py` file for alembic to detect changes for.


## Keeping dependicies up to date for uv:
>   For Linux/MacOS:
>   - From root run `make sync-uv-depenencies`
>
>   For Windows
>   - Add new dependencies in `./bot_service/src/backend/requirements.txt` &  update dependencies by navigating to `./bot_service/src/backend` & using `uv pip compile requirements.txt -o requirements.in`