"""Exercise the workflow's authenticated GHCR manifest guard without network access."""

import io
import json
import os
import re
import sys
import textwrap
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError


WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/publish-lke-publisher.yml"
PRIOR = "sha-9cd00403ecae72f2757adcbc6b44b873231dc944"
TARGET = "sha-8781f32ba1b0fcb2b91d190a5a603b637cccca05"
SCOPE = "repository:ctrl-alt-keith/trusted-network-registry/lke-publisher:pull"
CHALLENGE = f'Bearer realm="https://ghcr.io/token",service="ghcr.io",scope="{SCOPE}"'


def guard_source():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(r"            python3 - \"\$PRIOR_TAG\" \"\$TAG\" <<'PY'\n(.*?)\n          PY", workflow, re.S)
    if match is None:
        raise AssertionError("Workflow manifest guard is missing")
    return textwrap.dedent(match.group(1))


class Response:
    def __init__(self, status, headers=None, body=b""):
        self.status = status
        self.headers = headers or Message()
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.body


class WorkflowManifestGuardTests(unittest.TestCase):
    def run_guard(self, *, prior=200, target=404, challenge=CHALLENGE, token=200):
        requests = []

        def urlopen(request, timeout):
            self.assertEqual(timeout, 15)
            requests.append(request)
            url = request.full_url
            if url.endswith("/manifests/" + PRIOR) and not request.has_header("Authorization"):
                headers = Message()
                headers["WWW-Authenticate"] = challenge
                raise HTTPError(url, 401, "challenge", headers, None)
            if url.startswith("https://ghcr.io/token?"):
                self.assertTrue(request.get_header("Authorization", "").startswith("Basic "))
                if token != 200:
                    raise HTTPError(url, token, "token failure", Message(), None)
                return Response(200, body=json.dumps({"token": "test-token"}).encode())
            self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
            self.assertEqual(request.get_method(), "HEAD")
            status = prior if url.endswith("/manifests/" + PRIOR) else target
            if status != 200:
                raise HTTPError(url, status, "manifest status", Message(), None)
            return Response(200)

        with patch("urllib.request.build_opener") as build_opener, patch.object(
            sys, "argv", ["guard", PRIOR, TARGET]
        ), patch.dict(os.environ, {"GITHUB_ACTOR": "test-actor", "GH_TOKEN": "test-secret"}), patch(
            "sys.stderr", new_callable=io.StringIO
        ) as stderr:
            build_opener.return_value.open.side_effect = urlopen
            try:
                exec(compile(guard_source(), str(WORKFLOW), "exec"), {"__name__": "__main__"})
                exit_code = 0
            except SystemExit as error:
                exit_code = error.code
        self.assertNotIn("test-secret", stderr.getvalue())
        return exit_code, requests

    def test_authenticated_prior_and_explicit_target_404_allow_publication(self):
        code, requests = self.run_guard()
        self.assertEqual(code, 0)
        self.assertEqual(len(requests), 4)

    def test_target_present_or_unknown_refuses_publication(self):
        for status in (200, 302, 401, 403, 429, 500):
            with self.subTest(status=status):
                code, _ = self.run_guard(target=status)
                self.assertEqual(code, 1)

    def test_unreadable_prior_refuses_before_target_check(self):
        for status in (401, 403, 404, 429, 500):
            with self.subTest(status=status):
                code, requests = self.run_guard(prior=status)
                self.assertEqual(code, 1)
                self.assertEqual(len(requests), 3)

    def test_bad_challenge_or_token_refuses_publication(self):
        for challenge in ("", 'Bearer realm="http://ghcr.io/token"',
                          'Bearer realm="https://example.com/token",service="ghcr.io",scope="' + SCOPE + '"'):
            with self.subTest(challenge=challenge):
                code, _ = self.run_guard(challenge=challenge)
                self.assertEqual(code, 1)
        code, _ = self.run_guard(token=403)
        self.assertEqual(code, 1)

    def test_transport_failure_refuses_publication(self):
        with patch("urllib.request.build_opener") as build_opener, patch.object(
            sys, "argv", ["guard", PRIOR, TARGET]
        ), patch.dict(os.environ, {"GITHUB_ACTOR": "test-actor", "GH_TOKEN": "test-secret"}), patch(
            "sys.stderr", new_callable=io.StringIO
        ):
            build_opener.return_value.open.side_effect = URLError("offline")
            with self.assertRaises(SystemExit) as caught:
                exec(compile(guard_source(), str(WORKFLOW), "exec"), {"__name__": "__main__"})
        self.assertEqual(caught.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
