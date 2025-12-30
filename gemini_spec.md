# Gemini API Specification

This document describes all the technical details of calling the Google Gemini API in this project.

## Configuration

### Environment Variables

| Variable | Description | Source |
|----------|-------------|--------|
| `GEMINI_API_ENDPOINT` | Gemini API base URL | Loaded via `load_config()` |
| `GEMINI_API_KEY` | Gemini API authentication key | Loaded via `load_config()` |

**IMPORTANT**: Never use `os.getenv()` directly. Always retrieve these values through the `load_config()` function from `scraper.py`.

## API Call Details

### Endpoint

```
{GEMINI_API_ENDPOINT}/models/{model}:generateContent?key={GEMINI_API_KEY}
```

### Model

| Parameter | Value |
|-----------|-------|
| Model ID | `gemini-flash-latest-non-thinking` |
| Constraint | **DO NOT** change to a thinking model |

### HTTP Request

| Property | Value |
|----------|-------|
| Method | `POST` |
| Content-Type | `application/json` |
| Timeout | 60 seconds |

### Request Body Structure

```json
{
    "contents": [{
        "parts": [{"text": "<prompt>"}]
    }]
}
```

## Prompts

### One-Way Flight Prompt

Used when `trip_type != 'round_trip'`.

```
You are a flight analysis assistant. Analyze the flight data and provide a detailed summary and individual flight comments in Chinese.

DATA:
```json
{json_flights_data}
```

OUTPUT FORMAT (valid JSON only, no markdown):
```json
{
    "summary_note": "Brief note about the flights (e.g., self-transfer requirements, best value recommendations, price differences)",
    "flight_comments": [
        "Comment for flight 1 in markdown format - discuss transfer info, what to watch out for, pros/cons",
        "Comment for flight 2 in markdown format - discuss transfer info, what to watch out for, pros/cons",
        "Comment for flight 3 in markdown format - discuss transfer info, what to watch out for, pros/cons"
    ]
}
```

IMPORTANT: Each flight comment should include:
- Transfer information (if any): self-transfer or protected transfer
- What travelers should watch out for: layover time, visa requirements, terminal changes
- Pros: price, timing, airline quality
- Cons: long layover, early departure, etc.

Use markdown formatting: **bold**, *italic*, - bullets, numbered lists.

Keep the summary_note concise (under 100 Chinese characters). Keep each flight comment under 150 Chinese characters.
```

### Round-Trip Flight Prompt

Used when `trip_type == 'round_trip'`.

```
You are a flight analysis assistant. Analyze the round-trip flight data and provide a detailed summary and individual flight comments in Chinese.

DATA:
```json
{json_flights_data}
```

OUTPUT FORMAT (valid JSON only, no markdown):
```json
{
    "summary_note": "Brief note about the round-trip flights (e.g., self-transfer requirements, best value recommendations, stay duration)",
    "outbound_comments": [
        "Comment for outbound flight 1 in markdown format - discuss transfer info, what to watch out for, pros/cons",
        "Comment for outbound flight 2 in markdown format",
        "Comment for outbound flight 3 in markdown format"
    ],
    "return_comments": [
        "Comment for return flight 1 in markdown format - discuss transfer info, what to watch out for, pros/cons",
        "Comment for return flight 2 in markdown format",
        "Comment for return flight 3 in markdown format"
    ]
}
```

IMPORTANT: Each flight comment should include:
- Transfer information (if any): self-transfer or protected transfer
- What travelers should watch out for: layover time, visa requirements, terminal changes
- Pros: price, timing, airline quality
- Cons: long layover, early departure, etc.

Use markdown formatting: **bold**, *italic*, - bullets, numbered lists.

Keep the summary_note concise (under 100 Chinese characters). Keep each flight comment under 150 Chinese characters.
```

## Response Handling

### Response Parsing

The response is extracted from:
```
result['candidates'][0]['content']['parts'][0]['text']
```

### JSON Extraction

```python
# Extract JSON from markdown code block
if '```json' in llm_response:
    json_str = llm_response.split('```json')[1].split('```')[0].strip()
else:
    json_str = llm_response.strip()

summary_data = json.loads(json_str)
```

### Default Values

If the API call fails, these defaults are used:

| Field | Default Value |
|-------|---------------|
| `summary_note` | `"以上为最便宜的三个航班选项，请根据个人需求选择。"` |
| `flight_comments` (one-way) | `["暂无详细信息", "暂无详细信息", "暂无详细信息"]` |
| `outbound_comments` (round-trip) | `["暂无详细信息", "暂无详细信息", "暂无详细信息"]` |
| `return_comments` (round-trip) | `["暂无详细信息", "暂无详细信息", "暂无详细信息"]` |

## Post-Processing

1. Markdown comments are converted to HTML using the `markdown` library
2. HTML is inserted into flight card templates
3. Final HTML report is generated via `template.html`

## Code Location

The Gemini API call is implemented in `scraper.py` in the `generate_report()` function (lines 452-685).

Key code section (lines 552-596):

```python
api_host = config.get("GEMINI_API_ENDPOINT")
api_key = config.get("GEMINI_API_KEY")
model = "gemini-flash-latest-non-thinking"

url = f"{api_host}/models/{model}:generateContent?key={api_key}"
headers = {"Content-Type": "application/json"}
data = {
    "contents": [{
        "parts": [{"text": prompt}]
    }]
}

response = requests.post(url, headers=headers, json=data, timeout=60)
response.raise_for_status()
result = response.json()
llm_response = result['candidates'][0]['content']['parts'][0]['text']
```
