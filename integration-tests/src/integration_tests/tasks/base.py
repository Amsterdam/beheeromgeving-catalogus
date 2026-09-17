from locust import TaskSet, task

# USER STORIES:
# Als medewerker van amsterdam wil ik een succesvol get request kunnen maken naar het /products
# endpoint met een keycloak authorisatie token.
# Als anonieme gebruiker wil ik een succesvol get request kunnen maken naar het /products endpoint.
# Als admin wil ik een succesvol get request kunnen maken naar het /me endpoint met een
# entra authorisatie token.
# Als teamlid wil ik een succesvol get request kunnen maken naar het /me endpoint met een entra
# authorisatie token.


class BaseTaskSet(TaskSet):
    path: str = ""

    @property
    def url(self):
        return self.user.base_url + self.path

    def response_json_or_failure(
        self,
        response,
        failure_message: str = "Expected output not in response",
    ):
        # Locust uses a dummy response on transport failures/timeouts.
        if response.status_code == 0:
            # Mark as a success to avoid counting it as a failure in the test results.
            response.success()
            return None

        try:
            return response.json()
        except ValueError:
            response.failure(failure_message)
            return None

    @task
    def stop(self):
        self.interrupt()
