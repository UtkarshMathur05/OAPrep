"""Judge0 client. The frontend never talks to Judge0 directly.

MVP scope is Python only: Judge0 speaks stdin/stdout, but coding problems are
function-signature shaped, so every extra language needs its own driver that
parses stdin, calls the function and prints the result.

Contract: `test_cases.input` is sent verbatim on stdin; stdout is compared to
`expected_output` after stripping trailing whitespace.

TODO(backend): POST /submissions/batch?base64_encoded=false&wait=true with all
test cases in one request, then aggregate. Cap at MAX_TEST_CASES and set an
explicit httpx timeout — the public CE instance is rate-limited and flaky.
"""

from app.config import JUDGE0_API_HOST, JUDGE0_API_KEY, JUDGE0_URL
from app.schemas.verify import VerifyRequest, VerifyResponse

# Judge0 language ids — see GET {JUDGE0_URL}/languages
LANGUAGE_IDS = {
    "python": 71,
}

MAX_TEST_CASES = 5
JUDGE0_TIMEOUT_SECONDS = 20.0


def run_submission(req: VerifyRequest) -> VerifyResponse:
    # Mocked so the frontend can render results before Judge0 is wired up.
    return VerifyResponse(status="Accepted", passed=12, total=12,
                          runtime="0.21s", memory="18MB")
