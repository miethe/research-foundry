# Rate limiting for a multi-tenant API gateway — candidate synthesis (Perplexity)

Sliding window counters reduce the boundary-doubling problem that fixed windows have at window
edges [1]. Token bucket limiters are commonly used where short bursts should be tolerated up to a
configured bucket size [2]. Perplexity's own citation numbering and source-panel ordering above is a
UI display convenience only — it is not evidence of importance and is treated as such downstream.
