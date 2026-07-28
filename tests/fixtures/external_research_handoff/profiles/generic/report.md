# Rate limiting for a multi-tenant API gateway — candidate synthesis

This is a candidate research synthesis only. Nothing below is verified evidence; every numeric claim
is re-checked downstream against the exact source text before it can ever be treated as verified.

Token-bucket limiters allow short bursts up to the bucket size before throttling, which tends to
produce lower tail latency for bursty tenants than a strict fixed-window counter. Sliding-window
counters reduce the boundary-doubling problem that fixed windows have at window edges, at the cost of
slightly more bookkeeping per request. Neither algorithm alone addresses cross-tenant fairness; that
typically requires a separate per-tenant quota layer on top of whichever limiter is chosen.

One open question this pass did not resolve: how these algorithms interact with a gateway that
shards limiter state across multiple nodes without a shared clock. That is left as an open gap rather
than an invented answer.
