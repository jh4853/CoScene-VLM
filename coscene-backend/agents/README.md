# Agents Module - LangGraph Scene Editor

Conversational 3D scene editing using **LangGraph** + **Claude 4.5 Sonnet**. Generates USD code from natural language prompts.

---

## Architecture

### LangGraph Workflow

```mermaid
  flowchart LR
      Start([User Instruction]) --> ParseIntent[Parse Intent]
      ParseIntent --> RenderInputScene[Render Current Scene<br/>Multi-View]
      RenderInputScene --> GenerateUSD[Generate USD<br/>Claude 4.5 Sonnet]

      GenerateUSD --> ValidateUSD{USD Syntax<br/>Valid?}
      ValidateUSD -->|No| Failed([Failed])
      ValidateUSD -->|Yes| RenderOutput[Render Generated Scene<br/>Multi-View]

      RenderOutput --> VerifyOutput[Vision-Based Verification<br/>Claude 4.5 Sonnet]

      VerifyOutput --> CheckVerification{Verification<br/>Passed?}
      CheckVerification -->|Yes| Complete([Success])
      CheckVerification -->|No| CheckAttempts{Attempts <<br/>Max Iterations?}

      CheckAttempts -->|Yes| FixOutput[Generate Fix<br/>Claude 4.5 Sonnet]
      CheckAttempts -->|No| CompleteWarning([Complete with Warning])

      FixOutput --> ValidateFix{Fix USD<br/>Valid?}
      ValidateFix -->|Yes| RenderOutput
      ValidateFix -->|No| CheckAttempts

      style Start fill:#e1f5ff
      style Complete fill:#d4edda
      style Failed fill:#f8d7da
      style CompleteWarning fill:#fff3cd
      style GenerateUSD fill:#cfe2ff
      style VerifyOutput fill:#cfe2ff
      style FixOutput fill:#cfe2ff
```
