# -*- coding: utf-8 -*-

"""Main module."""
import json
import os
import random
import string
from configparser import ConfigParser, NoSectionError

import requests


class Portainer:
    def __init__(self, host):
        self.token = None
        self.host = host

    def login(self, username, password):
        r = self.request(
            "api/auth", method="POST", data={"Username": username, "Password": password}
        )
        try:
            self.token = r["jwt"]
        except KeyError:
            self.log("No token found in response")

    def status_check(self, expected_version):
        r = self.request("api/status")
        if r["Version"] == expected_version:
            self.log("Portainer version checks out")
            return True
        else:
            self.log(
                "Portainer version mismatch: {}, expected {}".format(
                    r["Version"], expected_version
                )
            )
            return False

    def get_stacks(self):
        r = self.request("api/endpoints/1/stacks")
        return r

    def update_stack(self, stack_id, content, env_vars, prune=False):
        self.log("Updating stack on Portainer [{}]".format(self.host))
        url = "api/endpoints/1/stacks/{}".format(stack_id)
        data = {
            "StackFileContent": content,
            "Prune": prune,
            "Env": [{"name": k, "value": v} for k, v in env_vars.items()],
        }
        response = self.request(url, method="PUT", data=data)
        print(response)

    def endpoints(self):
        r = self.request("api/endpoints")
        return r

    def request(self, path, method="GET", data=None):
        url = os.path.join(self.host, path)
        headers = {}
        if self.token:
            headers["Authorization"] = "Bearer {}".format(self.token)

        response = requests.request(method, url, json=data, headers=headers)
        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            return response.content

    #  Convenience methods

    def print_json(self, d):
        self.log(json.dumps(d, indent=4, sort_keys=True))

    def log(self, message):
        print(message)


if __name__ == "__main__":

    try:
        configuration = ConfigParser()
        configuration.read("stack-acpt.ini")
        local_config = dict(configuration.items("default"))
    except NoSectionError:
        local_config = {}

    def load_config(key, default=None, required=False):
        """Load an environment variable, using the values
        in the ini file as a fallback"""
        value = os.environ.get(key, default=local_config.get(key.lower()))
        if required and not value:
            raise LookupError("Error: no value found for key {}".format(key))

        return value if value else default

    # We need some environment variables before we can continue
    # When running a pipeline, these are either set in the CI settings of the project
    # in Gitlab, or in the .gitlab-cy.yml in the variables section

    # We also want to set a number of environment variables in the stack
    # to make them available when running the container. These too can be set in the CI settings
    # of the project or in .gitlab-ci.yml in the variables section

    # For local development, you can create a .ini file with these variables so you don't have
    # to load them all into the env...

    portainer_version = load_config("PORTAINER_VERSION", default="1.17.1")
    portainer_user = load_config("PORTAINER_USERNAME", required=True)
    portainer_pass = load_config("PORTAINER_PASSWORD", required=True)
    portainer_host = load_config("PORTAINER_HOST", required=True)
    portainer_stack_id = load_config("PORTAINER_STACK_ID", required=True)
    portainer = Portainer(host=portainer_host)

    portainer.login(portainer_user, portainer_pass)
    status = portainer.status_check(portainer_version)
    base_path = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(base_path, "stackfile.yaml"), "r") as f:
        stackfile = f.read()

    generated_key = "".join(
        [
            random.SystemRandom().choice(string.ascii_letters + string.digits)
            for _ in range(50)
        ]
    )

    # Get current env vars
    response = portainer.request("api/endpoints/1/stacks/{}".format(portainer_stack_id))
    current_env_vars = {item["name"]: item["value"] for item in response["Env"]}

    env_vars = {
        "DJANGO_SETTINGS_MODULE": load_config("DJANGO_SETTINGS_MODULE"),
        "DEBUG": load_config("DEBUG", default="False"),
        "CMS2_TAG": load_config("CMS2_TAG"),
        "DJANGO_SECRET_KEY": load_config("DJANGO_SECRET_KEY", generated_key),
        "HOSTNAME_SUFFIX": load_config("HOSTNAME_SUFFIX"),
        "SLACK_HOOK_URL": load_config("SLACK_HOOK_URL"),
        "STAGE": load_config("STAGE"),
        "INCROWD_API_URL": load_config("INCROWD_API_URL"),
    }

    set_env_vars = {**current_env_vars, **env_vars}
    portainer.update_stack(portainer_stack_id, stackfile, set_env_vars)
