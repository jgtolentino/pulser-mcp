# Voice Agent MCP - Arkie Auto-SDR

Real-time voice agent for automated sales development with LiveKit, AssemblyAI, and intelligent call handling.

## Features

- **Real-Time Voice**: LiveKit-powered voice calls
- **Speech Recognition**: AssemblyAI transcription with speaker labels
- **Call Analytics**: Sentiment, summary, and action items
- **Contact Discovery**: Web crawling for prospect information
- **CRM Integration**: Auto-update Salesforce, HubSpot, Pipedrive

## Quick Start

1. **Setup**:
   ```bash
   cd tools/js/mcp/voice_agent_mcp
   ./scripts/setup.sh
   ```

2. **Configure API Keys**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Start Services**:
   ```bash
   docker-compose up -d
   source venv/bin/activate
   python src/voice_server.py
   ```

4. **Test Voice Call**:
   ```bash
   # Start a session
   curl -X POST http://localhost:8003/mcp/tools/start_voice_session \
     -H "Content-Type: application/json" \
     -d '{
       "participant_name": "Test Lead",
       "context": {
         "company": "Acme Corp",
         "purpose": "discovery"
       }
     }'
   ```

## Available Tools

### start_voice_session
Initialize a voice call:
```json
{
  "tool": "start_voice_session",
  "params": {
    "participant_name": "John Smith",
    "context": {
      "lead_id": "lead_123",
      "company": "TechCorp",
      "purpose": "demo"
    },
    "language": "en"
  }
}
```

### transcribe_audio
Convert speech to text:
```json
{
  "tool": "transcribe_audio",
  "params": {
    "audio_url": "https://storage.example.com/call_123.wav",
    "session_id": "session_abc",
    "speaker_labels": true
  }
}
```

### analyze_call
Extract insights from calls:
```json
{
  "tool": "analyze_call",
  "params": {
    "session_id": "session_abc",
    "analysis_type": "summary"
  }
}
```

### crawl_for_contacts
Discover contacts from websites:
```json
{
  "tool": "crawl_for_contacts",
  "params": {
    "url": "https://example-company.com",
    "extract_contacts": true,
    "max_depth": 2
  }
}
```

## Voice Interaction Flow

```
┌──────────┐     ┌─────────┐     ┌────────────┐
│  Caller  │────▶│ LiveKit │────▶│ Voice Agent│
└──────────┘     └─────────┘     └────────────┘
                       │                 │
                       ▼                 ▼
                ┌─────────────┐   ┌────────────┐
                │ AssemblyAI  │   │  Supabase  │
                └─────────────┘   └────────────┘
```

## WebSocket Integration

Connect for real-time transcription:
```javascript
const ws = new WebSocket('ws://localhost:8003/ws/voice/session_123');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'transcription') {
    console.log('Transcript:', data.text);
  }
};

// Send audio chunks
ws.send(audioBlob);
```

## Call Scripts

Customize call flows in `data/call_scripts/`:
```json
{
  "greeting": "Custom greeting",
  "discovery_questions": [...],
  "objection_handlers": {...},
  "closing": "Schedule next steps"
}
```

## CRM Integration

### Salesforce
```python
# Auto-sync to Salesforce
context = {
  "crm": "salesforce",
  "lead_id": "00Q123456",
  "auto_update": true
}
```

### HubSpot
```python
# Update HubSpot contact
context = {
  "crm": "hubspot", 
  "contact_id": "123456",
  "properties": ["call_notes", "next_step"]
}
```

## Analytics Dashboard

View call metrics at http://localhost:8003/dashboard:
- Call volume and duration
- Sentiment trends
- Conversion rates
- Agent performance

## Best Practices

1. **Call Recording Compliance**:
   - Always announce recording
   - Respect opt-out requests
   - Store securely

2. **Voice Quality**:
   - Use noise cancellation
   - Monitor connection quality
   - Fallback to text if needed

3. **Follow-up Actions**:
   - Schedule within 24 hours
   - Send summary emails
   - Update CRM immediately

## Troubleshooting

- **LiveKit Connection**: Check Docker containers running
- **No Audio**: Verify microphone permissions
- **Transcription Errors**: Check AssemblyAI quota
- **CRM Sync Failed**: Verify API credentials

## Advanced Configuration

### Custom Voice Models
```yaml
voice_settings:
  provider: elevenlabs
  voice_id: custom_voice_id
  language_model: gpt-4-voice
```

### Call Routing Rules
```yaml
routing:
  inbound:
    default: discovery_flow
    vip: executive_flow
  outbound:
    cold: qualification_flow
    warm: demo_flow
```

## License

Part of InsightPulseAI SKR - Proprietary