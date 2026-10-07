from locust import tag, task

from integration_tests.tasks.base import BaseTaskSet


@tag("me")
class Me(BaseTaskSet):
    path = "/me"

    def _validate_payload_structure(self, payload) -> bool:
        me = payload.get("me") if isinstance(payload, dict) else None
        return isinstance(me, list)

    @task
    def team_member_request_to_me_endpoint(self):
        url = self.user.base_url + "me"
        self.client.headers.update({"Authorization": f"Bearer {self.user.environment.team_token}"})
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve data")

            if (
                response.status_code == 200
                and response["teams"][0]["id"] == 6
                and len(response["teams"]) == 1
            ):
                response.success()

    @task
    def team_member_request_to_other_team_me_endpoint(self):
        url = self.user.base_url + "me?teams=12"
        self.client.headers.update({"Authorization": f"Bearer {self.user.environment.team_token}"})
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve data")

            if response.status_code == 200 and response["teams"][0]["id"] != 12:
                response.success()

    @task
    def admin_request_to_me_endpoint(self):
        url = self.user.base_url + "me"
        self.client.headers.update(
            {"Authorization": f"Bearer {self.user.environment.admin_token}"}
        )
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve data")

            if (
                response.status_code == 200 and len(response["teams"]) > 1
            ):  # and {"teams":[],"products":{"count":0,"next":null,"previous":null,"results":[]}}
                response.success()

    @task
    def anonymous_request_to_me_endpoint(self):
        url = self.user.base_url + "me"
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve product data")

            if response.status_code == 200 and response["teams"] == []:
                response.success()
