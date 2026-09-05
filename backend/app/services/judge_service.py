"""Judge0 client. The frontend never talks to Judge0 directly.

TODO(backend): POST /submissions?base64_encoded=false&wait=true per test case
(or use the batch endpoint) and aggregate the results.
"""

from app.config import JUDGE0_API_HOST, JUDGE0_API_KEY, JUDGE0_URL
from app.schemas.verify import VerifyRequest, VerifyResponse

# Judge0 language ids — see GET {JUDGE0_URL}/languages
LANGUAGE_IDS = {
    "python": 71,
    "java": 62,
    "cpp": 54,
    "c": 50,
    "javascript": 63,
    "typescript": 74,
}


def run_submission(req: VerifyRequest) -> VerifyResponse:
    # Mocked so the frontend can render results before Judge0 is wired up.
    return VerifyResponse(status="Accepted", passed=12, total=12,
                          runtime="0.21s", memory="18MB")
