from hooks.pytest_hooks import _skip_reason


def testSkipReasonMatchesCaseIdWithoutMatchingLongerIds() -> None:
    node_id = "testCases.e2eTests.testFlight::testE10HotelBooking"

    assert _skip_reason(node_id, ["E1"]) is None
    assert _skip_reason(node_id, ["e10"]) == "Skipped by --skip-case: e10"


def testSkipReasonMatchesCaseIdsAndNodeText() -> None:
    node_id = "testCases.e2eTests.testCriticalFlows::testC8HotelRecovery[chromium]"

    assert _skip_reason(node_id, ["C8"]) == "Skipped by --skip-case: C8"
    assert _skip_reason(node_id, ["hotelrecovery"]) == (
        "Skipped by --skip-case: hotelrecovery"
    )
    assert _skip_reason(node_id, []) is None
