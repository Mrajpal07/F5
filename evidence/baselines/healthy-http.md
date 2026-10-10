# NetReliant — Healthy HTTP Baseline

## Environment
- Service: NetReliant FastAPI
- Endpoint: GET /health
- Transport: HTTP over TCP
- Client target: localhost:8000

## Results
- Requests: 10
- Successful HTTP responses: 10
- Success rate: 100%
- Minimum observed total time: 1.277 ms
- Maximum observed total time: 3.125 ms
- Mean observed total time: 1.9353 ms

## Individual observations
| Request | HTTP status | Total time (ms) |
|---:|---:|---:|
| 1 | 200 | 2.694 |
| 2 | 200 | 1.867 |
| 3 | 200 | 3.125 |
| 4 | 200 | 1.789 |
| 5 | 200 | 2.562 |
| 6 | 200 | 1.390 |
| 7 | 200 | 1.383 |
| 8 | 200 | 1.510 |
| 9 | 200 | 1.277 |
| 10 | 200 | 1.756 |

## Limitations
This is a small local-development sample, not a production SLA.
Measurements include curl's total request time and may be affected by
local scheduling, connection setup, and Docker/WSL networking.
