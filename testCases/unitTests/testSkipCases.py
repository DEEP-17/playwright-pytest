from pytestHooks.pytestHooks import _skip_reason, _skip_selectors

def testSkipReasonMatchesCaseIdWithoutMatchingLongerIds() -> None:
    node_id = "testCases.endToEndTests.testFlight::testE10HotelBooking"
    assert _skip_reason(node_id, ["E1"]) is None
    assert _skip_reason(node_id, ["e10"]) == "Skipped by --skip-case: e10"

def testSkipReasonMatchesCaseIdsAndNodeText() -> None:
    node_id = "testCases.endToEndTests.testCriticalFlows::testC8HotelRecovery[chromium]"
    assert _skip_reason(node_id, ["C8"]) == "Skipped by --skip-case: C8"
    assert _skip_reason(node_id, ["hotelrecovery"]) == (
        "Skipped by --skip-case: hotelrecovery"
    )
    assert _skip_reason(node_id, []) is None

def testSkipReasonPreservesProvidedFollowUpReason() -> None:
    node_id = "testCases.endToEndTests.testCriticalFlows::testC8HotelRecovery[chromium]"
    assert _skip_reason(node_id, ["C8=waiting for QA data"]) == (
        "Skipped by --skip-case: C8 (waiting for QA data)"
    )

def testSkipSelectorsKeepCommasInsideExplicitReasons() -> None:
    selectors = _skip_selectors(
        ["C8=waiting for QA, fix in progress", "E2, E10"]
    )
    assert selectors == ["C8=waiting for QA, fix in progress", "E2", "E10"]
