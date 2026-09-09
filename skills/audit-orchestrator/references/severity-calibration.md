# Severity Calibration

| Signal | Default treatment | Reason |
|---|---|---|
| Effective retrieval block on an intended page | Critical | Directly prevents the scoped retrieval path |
| Effective noindex on an intended page | Critical | Direct exclusion signal |
| Raw HTML shell or content under the calibrated threshold | High | Strong risk, but render context must be checked |
| Conflicting first-party price or lifecycle facts | High | Can cause inaccurate AI answers |
| Missing or incomplete entity markup | Medium | Extraction weakness, not universal invisibility |
| Missing causal depth or statistical density | Medium | Citability opportunity requiring page context |
| Broken authority anchor | Medium | Observable hygiene defect with bounded impact |
| Missing sameAs or author metadata | Low/advisory | Intent and brand maturity matter |
| Training-bot policy choice | Informational | Not equivalent to search retrieval blocking |

Severity is evidence-scoped. A heuristic alone cannot establish a high-severity site-wide claim, and unknown access or intent is reported as inconclusive or advisory.
