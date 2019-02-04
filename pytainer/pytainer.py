# -*- coding: utf-8 -*-

"""Main module."""
import json
import os

import requests


class Portainer:
    def __init__(self, host):
        self.token = None
        self.host = host

    def login(self, username, password):
        data = {"Username": username, "Password": password}
        r = self.request("api/auth", method="POST", data=data)
        print(r)
        self.token = r.get("jwt")

    def status_check(self, expected_version) -> bool:
        r = self.request("api/status")
        print(r)
        return r.get("Version") == expected_version

    def get_stacks(self):
        return self.request("api/endpoints/1/stacks")

    def get_endpoints(self):
        return self.request("api/endpoints")

    def get_stacks(self):
        return self.request("api/stacks")

    def get_env_vars(self, stack_id: str) -> dict:
        response = self.request(f"api/endpoints/1/stacks/{stack_id}")
        return {item["name"]: item["value"] for item in response["Env"]}

    def update_stack(
        self, stack_id, stack_file_content, env_vars=None, prune=False
    ) -> dict:
        url = "api/endpoints/1/stacks/{}".format(stack_id)
        data = {
            "StackFileContent": stack_file_content,
            "Prune": prune,
            "Env": [{"name": k, "value": v} for k, v in env_vars.items()],
        }
        return self.request(url, method="PUT", data=data)

    def update_stack_with_file(
        self,
        stack_id: str,
        stack_file_path: str,
        env_vars: dict = None,
        prune: bool = False,
    ):

        with open(stack_file_path, "r") as f:
            stackfile = f.read()
        return self.update_stack(stack_id, stackfile, env_vars=env_vars, prune=prune)

    def endpoints(self):
        return self.request("api/endpoints")

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

