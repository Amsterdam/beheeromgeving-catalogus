from locust import tag, task

from integration_tests.tasks.base import BaseTaskSet

# Als admin wil ik een succesvol get request kunnen maken naar het /me endpoint met een
# entra authorisatie token.
# Als teamlid wil ik een succesvol get request kunnen maken naar het /me endpoint met een entra
# authorisatie token.


@tag("me")
class Me(BaseTaskSet):
    path = "/me"

    def _validate_payload_structure(self, payload) -> bool:
        me = payload.get("me") if isinstance(payload, dict) else None
        return isinstance(me, list)

    @task
    def authorized_team_member_request_to_me_endpoint(self):
        url = self.user.base_url + "me"
        # team member entra token?
        self.client.headers.update(
            {"Authorization": f"Bearer {self.user.environment.entra_token}"}
        )
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve data")

    @task
    def authorized_admin_request_to_me_endpoint(self):
        url = self.user.base_url + "me"
        # admin user entra token?
        self.client.headers.update(
            {"Authorization": f"Bearer {self.user.environment.entra_token}"}
        )
        with self.client.get(url, catch_response=True) as response:
            self.response_json_or_failure(response, "Failed to retrieve data")
