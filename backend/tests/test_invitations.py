from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import pytest
from google.genai import errors

from app.services.ai_service import AIService
from app.services.invitation_service import compute_devanagari_ratio, validate_invitation_text


def test_devanagari_ratio_and_validator():
    hindi_sample = "सस्नेह नमस्कार। हमारे परिवार में विवाह का शुभ आयोजन है।"
    assert compute_devanagari_ratio(hindi_sample) > 0.8
    is_valid, err = validate_invitation_text(hindi_sample + " आप सपरिवार सादर आमंत्रित हैं।", "Hindi")
    assert is_valid is True
    assert err is None

    # Latin text for Hindi fails
    latin_hindi = "Aap sabhi parivaar sahit aamantrit hain hamare ghar par."
    is_valid, err = validate_invitation_text(latin_hindi, "Hindi")
    assert is_valid is False
    assert "authentic Devanagari" in err

    # English with English text passes
    english_sample = "Cordially invited to our grand wedding reception at Taj Palace on Saturday."
    is_valid, err = validate_invitation_text(english_sample, "English")
    assert is_valid is True
    assert err is None


def test_invitation_demo_mode(client, freeze_today):
    freeze_today(date(2026, 10, 30))
    with patch("app.config.settings.gemini_api_key", ""):
        # 1. English Demo
        res_en = client.post(
            "/api/invitations/generate",
            json={
                "event_type": "Wedding",
                "host_name": "Sharma Family",
                "event_date": "2026-11-20",
                "event_time": "18:30",
                "location": "ITC Maurya, New Delhi",
                "language": "English",
                "tone": "Elegant",
            },
        )
        assert res_en.status_code == 200
        data_en = res_en.json()
        assert data_en["source"] == "demo"
        assert "Sharma Family" in data_en["invitation_text"]
        assert "18:30" in data_en["invitation_text"]
        assert "ITC Maurya" in data_en["invitation_text"]

        # 2. Hindi Demo
        res_hi = client.post(
            "/api/invitations/generate",
            json={
                "event_type": "Wedding",
                "host_name": "शर्मा परिवार",
                "event_date": "2026-11-20",
                "event_time": "19:00",
                "location": "होटल क्लार्क्स, जयपुर",
                "language": "Hindi",
                "tone": "Traditional",
            },
        )
        assert res_hi.status_code == 200
        data_hi = res_hi.json()
        assert data_hi["source"] == "demo"
        assert compute_devanagari_ratio(data_hi["invitation_text"]) > 0.5


def test_invitation_validation_errors(client, freeze_today):
    freeze_today(date(2026, 10, 30))

    # Missing host_name
    res = client.post(
        "/api/invitations/generate",
        json={
            "event_type": "Wedding",
            "host_name": "  ",
            "event_date": "2026-11-20",
            "event_time": "18:30",
            "location": "Venue",
        },
    )
    assert res.status_code == 422

    # Invalid time "25:99"
    res = client.post(
        "/api/invitations/generate",
        json={
            "event_type": "Wedding",
            "host_name": "Host",
            "event_date": "2026-11-20",
            "event_time": "25:99",
            "location": "Venue",
        },
    )
    assert res.status_code == 422

    # Past date
    res = client.post(
        "/api/invitations/generate",
        json={
            "event_type": "Wedding",
            "host_name": "Host",
            "event_date": "2026-10-20",  # before today 2026-10-30
            "event_time": "18:30",
            "location": "Venue",
        },
    )
    assert res.status_code == 422

    # Invalid language
    res = client.post(
        "/api/invitations/generate",
        json={
            "event_type": "Wedding",
            "host_name": "Host",
            "event_date": "2026-11-20",
            "event_time": "18:30",
            "location": "Venue",
            "language": "French",
        },
    )
    assert res.status_code == 422


def test_invitation_mocked_gemini_success_and_hindi_repair_retry(client, freeze_today):
    freeze_today(date(2026, 10, 30))

    # Case 1: Hindi output where first attempt is Latin transliteration, retry produces real Devanagari
    bad_latin_text = '{"invitation_text": "Aap sabhi ko hamare parivaar ki shadi me aana hoga. Venue Taj Palace. Time 19:00."}'
    good_hindi_text = '{"invitation_text": "॥ श्री गणेशाय नमः ॥\\n\\nआप सभी सपरिवार हमारे विवाह समारोह में सादर आमंत्रित हैं।\\nस्थान: ताज पैलेस\\nसमय: 19:00 बजे।"}'

    with patch("app.config.settings.gemini_api_key", "test_key"):
        with patch.object(AIService, "is_configured", True):
            with patch("app.services.ai_service.genai.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.models.generate_content.side_effect = [
                    MagicMock(text=bad_latin_text),
                    MagicMock(text=good_hindi_text),
                ]
                mock_client_cls.return_value = mock_client

                res = client.post(
                    "/api/invitations/generate",
                    json={
                        "event_type": "Wedding",
                        "host_name": "राजेश गुप्ता",
                        "event_date": "2026-11-25",
                        "event_time": "19:00",
                        "location": "ताज पैलेस, नई दिल्ली",
                        "language": "Hindi",
                        "tone": "Traditional",
                    },
                )
                assert res.status_code == 200
                data = res.json()
                assert data["source"] == "gemini"
                assert "श्री गणेशाय नमः" in data["invitation_text"]
                assert mock_client.models.generate_content.call_count == 2


def test_invitation_hindi_fails_after_retry_yields_502(client, freeze_today):
    freeze_today(date(2026, 10, 30))
    bad_latin_text = '{"invitation_text": "Aap sabhi ko hamare parivaar ki shadi me aana hoga. Venue Taj Palace. Time 19:00."}'

    with patch("app.config.settings.gemini_api_key", "test_key"):
        with patch.object(AIService, "is_configured", True):
            with patch("app.services.ai_service.genai.Client") as mock_client_cls:
                mock_client = MagicMock()
                # Both attempts return Latin
                mock_client.models.generate_content.side_effect = [
                    MagicMock(text=bad_latin_text),
                    MagicMock(text=bad_latin_text),
                ]
                mock_client_cls.return_value = mock_client

                res = client.post(
                    "/api/invitations/generate",
                    json={
                        "event_type": "Wedding",
                        "host_name": "राजेश गुप्ता",
                        "event_date": "2026-11-25",
                        "event_time": "19:00",
                        "location": "ताज पैलेस, नई दिल्ली",
                        "language": "Hindi",
                        "tone": "Traditional",
                    },
                )
                assert res.status_code == 502
                assert "Devanagari" in res.json()["detail"]

