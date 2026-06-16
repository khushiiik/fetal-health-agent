import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

class MockPart:
    def __init__(self, text):
        self.text = text

class MockContent:
    def __init__(self, parts):
        self.parts = parts

class MockFunctionResponse:
    def __init__(self, name, response):
        self.name = name
        self.response = response

class MockEvent:
    def __init__(self, text=None, function_responses=None):
        self.content = MockContent([MockPart(text)]) if text else None
        self._function_responses = function_responses or []

    def get_function_responses(self):
        return self._function_responses


@pytest.fixture
def mock_diagnostic_report_data():
    return {
        "header": {
            "fetus_id": "FET-1001",
            "patient_id": "PAT-2031",
            "scan_date": "2026-05-14",
            "gestational_age_weeks": 32,
            "report_generated_at": "2026-06-15T12:00:00"
        },
        "summary": "Fetus parameters are within the expected physiological range.",
        "vitals_breakdown": [
            {
                "vital_name": "fetal_heart_rate_bpm",
                "measured_value": 140,
                "unit": "bpm",
                "reference_min": 110,
                "reference_max": 160,
                "status": "normal",
                "deviation_note": None
            }
        ],
        "analysis": {
            "fetus_id": "FET-1001",
            "vital_results": [
                {
                    "vital_name": "fetal_heart_rate_bpm",
                    "measured_value": 140,
                    "reference_range": {
                        "vital_name": "fetal_heart_rate_bpm",
                        "min_value": 110.0,
                        "max_value": 160.0,
                        "unit": "bpm"
                    },
                    "status": "normal",
                    "deviation_note": None
                }
            ],
            "overall_classification": "healthy",
            "classification_reason": "All parameters normal"
        },
        "notes": "Routine scan"
    }


def test_health_check():
    """Verify health check root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "AI Fetal Health Assistant API is running"}


@pytest.mark.asyncio
async def test_chat_endpoint_with_session_id(mock_diagnostic_report_data):
    """Test /api/chat with a provided session_id."""
    session_id = "test-session-123"
    message = "Analyze fetus FET-1001"

    # Define mock events returned by run_async
    mock_events = [
        MockEvent(text="Starting vitals analysis..."),
        MockEvent(
            text="# Fetal Health Diagnostic Report\n\n## Header\n- **Fetus ID:** FET-1001",
            function_responses=[
                MockFunctionResponse(
                    name="format_report",
                    response={
                        "report": mock_diagnostic_report_data,
                        "report_markdown": "# Fetal Health Diagnostic Report\n\n## Header\n- **Fetus ID:** FET-1001"
                    }
                )
            ]
        )
    ]

    async def mock_run_async(*args, **kwargs):
        for event in mock_events:
            yield event

    with patch("app.api.endpoints.runner.run_async", side_effect=mock_run_async) as mock_run:
        response = client.post(
            "/api/chat",
            json={"session_id": session_id, "message": message}
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["session_id"] == session_id
        assert "response" not in json_data
        assert json_data["report_markdown"] == "# Fetal Health Diagnostic Report\n\n## Header\n- **Fetus ID:** FET-1001"
        assert json_data["report"] is not None
        assert json_data["report"]["header"]["fetus_id"] == "FET-1001"
        assert json_data["report"]["header"]["gestational_age_weeks"] == 32
        
        # Verify runner was called correctly
        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        assert kwargs["session_id"] == session_id
        assert kwargs["user_id"] == "default_user"


@pytest.mark.asyncio
async def test_chat_endpoint_auto_session_id(mock_diagnostic_report_data):
    """Test /api/chat auto-generates a session_id when none is provided."""
    message = "FET-1001"

    mock_events = [
        MockEvent(
            text="# Fetal Health Diagnostic Report\n\n## Header\n- **Fetus ID:** FET-1001",
            function_responses=[
                MockFunctionResponse(
                    name="format_report",
                    response={
                        "report": mock_diagnostic_report_data,
                        "report_markdown": "# Fetal Health Diagnostic Report\n\n## Header\n- **Fetus ID:** FET-1001"
                    }
                )
            ]
        )
    ]

    async def mock_run_async(*args, **kwargs):
        for event in mock_events:
            yield event

    with patch("app.api.endpoints.runner.run_async", side_effect=mock_run_async) as mock_run:
        response = client.post(
            "/api/chat",
            json={"message": message}
        )

        assert response.status_code == 200
        json_data = response.json()
        assert "session_id" in json_data
        assert json_data["session_id"] != ""
        # Should be a valid UUID
        import uuid
        try:
            uuid.UUID(json_data["session_id"])
        except ValueError:
            pytest.fail("session_id is not a valid UUID")

        assert "response" not in json_data
        assert json_data["report_markdown"] == "# Fetal Health Diagnostic Report\n\n## Header\n- **Fetus ID:** FET-1001"
        assert json_data["report"] is not None
        mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_chat_endpoint_error_handling():
    """Test /api/chat handles errors correctly and returns 500."""
    async def mock_run_async_raise(*args, **kwargs):
        # We must yield at least one thing, or directly raise exception
        raise Exception("Gemini API Quota Exceeded")
        yield  # make it a generator

    with patch("app.api.endpoints.runner.run_async", side_effect=mock_run_async_raise):
        response = client.post(
            "/api/chat",
            json={"message": "FET-1001"}
        )
        assert response.status_code == 500
        assert "Gemini API Quota Exceeded" in response.json()["detail"]
