from unittest.mock import MagicMock, patch

from voicecart.nlu import parse_grocery_request


def _mock_client(json_text: str):
    response = MagicMock()
    response.text = json_text
    client = MagicMock()
    client.models.generate_content.return_value = response
    return client


def test_parses_common_grocery_request():
    json_body = """{
      "language": "en",
      "items": [
        {"name": "milk", "quantity": "2", "unit": "packets"},
        {"name": "atta", "quantity": "1", "unit": "kg"},
        {"name": "tomatoes", "quantity": "1", "unit": ""},
        {"name": "bananas", "quantity": "6", "unit": ""}
      ]
    }"""
    with patch("google.genai.Client", return_value=_mock_client(json_body)):
        request = parse_grocery_request(
            "Add two packets of milk, 1 kg atta, tomatoes, and six bananas",
            api_key="test",
        )

    assert request.language == "en"
    assert [(item.quantity, item.name) for item in request.items] == [
        ("2 packets", "milk"),
        ("1 kg", "atta"),
        ("1", "tomatoes"),
        ("6", "bananas"),
    ]


def test_parses_telugu_script_request():
    json_body = """{
      "language": "te",
      "items": [
        {"name": "milk", "quantity": "2", "unit": "packets"},
        {"name": "rice", "quantity": "1", "unit": "kg"}
      ]
    }"""
    with patch("google.genai.Client", return_value=_mock_client(json_body)):
        request = parse_grocery_request(
            "రెండు ప్యాకెట్లు పాలు, ఒక కిలో బియ్యం",
            api_key="test",
        )

    assert request.language == "te"
    assert [(item.quantity, item.name) for item in request.items] == [
        ("2 packets", "milk"),
        ("1 kg", "rice"),
    ]


def test_parses_mixed_telugu_english_request():
    json_body = """{
      "language": "mixed",
      "items": [
        {"name": "milk", "quantity": "2", "unit": "packets"},
        {"name": "curd", "quantity": "1", "unit": "packet"}
      ]
    }"""
    with patch("google.genai.Client", return_value=_mock_client(json_body)):
        request = parse_grocery_request(
            "paalu two packets and perugu one packet add cheyyi",
            api_key="test",
        )

    assert request.language == "mixed"
    assert [(item.quantity, item.name) for item in request.items] == [
        ("2 packets", "milk"),
        ("1 packet", "curd"),
    ]


def test_handles_markdown_fenced_response():
    fenced = "```json\n{\"language\": \"en\", \"items\": [{\"name\": \"onions\", \"quantity\": \"3\", \"unit\": \"\"}]}\n```"
    with patch("google.genai.Client", return_value=_mock_client(fenced)):
        request = parse_grocery_request("three onions", api_key="test")

    assert request.items[0].name == "onions"
    assert request.items[0].quantity == "3"
