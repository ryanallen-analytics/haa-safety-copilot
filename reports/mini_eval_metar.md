# Mini eval: LLM METAR parsing vs API decoded fields

10 METARs from `evals\metar_snapshot.json`. Model: `claude-haiku-5-5`. Parse failures: 0.

| Field | Correct |
| --- | --- |
| station | 10/10 |
| observed_at | 10/10 |
| wind_dir | 10/10 |
| wind_speed | 10/10 |
| wind_gust | 10/10 |
| visibility | 10/10 |
| ceiling | 9/10 |

## Mismatches

| METAR | Field | API (expected) | LLM |
| --- | --- | --- | --- |
| `METAR KBTV 230254Z 00000KT 10SM BKN220 12/04 A2986 RMK AO2 SLP112 T01170044 56028` | ceiling | 22000 | 2200 |

## Conclusion
Weather data comes from the API’s decoded fields plus my tested flight_conditions.py code. The LLM decides which data to fetch and explains it.  It doesn’t decode METARs.
